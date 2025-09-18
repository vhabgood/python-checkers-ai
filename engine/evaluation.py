# engine/evaluation.py
import logging
import sqlite3
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF

# --- Get the dedicated evaluation logger ---
eval_logger = logging.getLogger('eval')

# ======================================================================================
# --- Piece-Square Tables (PSTs) & Configurations (Unchanged) ---
# ======================================================================================
PST_TIER_1_SCORE = 3.0
PST_TIER_2_SCORE = 1.5
PST_TIER_3_SCORE = 0.5
TIER_1_SQUARES = {14, 15, 18, 19}
TIER_2_SQUARES = {1, 2, 3, 5, 16, 17, 30, 31, 32}
MAN_PST, KING_PST = [0.0] * 33, [0.0] * 33
for i in range(1, 33):
    if i in TIER_1_SQUARES: MAN_PST[i], KING_PST[i] = PST_TIER_1_SCORE, PST_TIER_1_SCORE * 1.5
    elif i in TIER_2_SQUARES: MAN_PST[i], KING_PST[i] = PST_TIER_2_SCORE, PST_TIER_2_SCORE
    else: MAN_PST[i], KING_PST[i] = PST_TIER_3_SCORE, PST_TIER_3_SCORE

V1_CONFIG = {"MATERIAL_WEIGHT": 10.0, "POSITIONAL_WEIGHT": 0.15, "BLOCKADE_WEIGHT": 0.75, "FIRST_KING_BONUS": 7.5, "SIMPLIFICATION_BONUS": 0.3, "MOBILITY_WEIGHT": 0.1, "ADVANCEMENT_WEIGHT": 0.05}
V2_CONFIG = {"MATERIAL_WEIGHT": 10.0, "POSITIONAL_WEIGHT": 0.15, "BLOCKADE_WEIGHT": 0.75, "FIRST_KING_BONUS": 7.5, "SIMPLIFICATION_BONUS": 0.3, "MOBILITY_WEIGHT": 0.1, "ADVANCEMENT_WEIGHT": 0.1}

# ======================================================================================
# --- REWRITTEN: Core Evaluation Logic with Upfront Logging ---
# ======================================================================================
def _calculate_score(board, config):
    """
    The single, core evaluation function. Now with detailed logging capabilities
    that correctly handle database hits.
    """
    engine_name = "V2_exp" if config["ADVANCEMENT_WEIGHT"] > 0.05 else "V1_stable"
    is_logging_enabled = eval_logger.hasHandlers()
    fen = board.get_fen() if is_logging_enabled else None

    # --- Phase 1: Endgame Database Check ---
    if hasattr(board, 'db_conn') and board.db_conn:
        try:
            table_name, key_tuple = board._get_endgame_key()
            if table_name and key_tuple:
                num_pieces = len(key_tuple) - 1
                where_clause = ' AND '.join([f'p{i + 1}_pos = ?' for i in range(num_pieces)])
                sql = f"SELECT result FROM {table_name} WHERE {where_clause} AND turn = ?"
                cursor = board.db_conn.cursor()
                cursor.execute(sql, key_tuple)
                result = cursor.fetchone()
                if result:
                    db_score = int(result[0])
                    final_score = (1000 - abs(db_score)) if db_score > 0 else (-1000 + abs(db_score))
                    if is_logging_enabled:
                        log_data = [engine_name, fen, f"{final_score:.4f}"] + ["DB_HIT"] * 7
                        eval_logger.info(",".join(log_data))
                    return final_score
        except Exception as e:
            logger.error(f"DATABASE: Error during query: {e}", exc_info=True)

    # --- Phase 2: Static Evaluation Components ---
    material_score, positional_score, advancement_score = 0, 0, 0
    first_king_bonus = 0
    if board.white_kings > 0 and board.red_kings == 0: first_king_bonus = config["FIRST_KING_BONUS"]
    elif board.red_kings > 0 and board.white_kings == 0: first_king_bonus = -config["FIRST_KING_BONUS"]

    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if not piece: continue
            is_white = piece.color == WHITE
            material_value = 1.5 if piece.king else 1.0
            material_score += material_value if is_white else -material_value
            acf_pos = COORD_TO_ACF.get((r, c));
            if not acf_pos: continue
            pst_score = KING_PST[acf_pos] if piece.king else MAN_PST[acf_pos]
            positional_score += pst_score if is_white else -pst_score
            if not piece.king: advancement_score += (7 - r) if is_white else -r
    
    red_blockade_bonus, white_blockade_bonus = 0, 0
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if not piece or piece.king: continue
            if piece.color == RED:
                b1, b2 = board.get_piece(r + 1, c - 1), board.get_piece(r + 1, c + 1)
                if b1 and b1.color == WHITE: white_blockade_bonus += 1
                if b2 and b2.color == WHITE: white_blockade_bonus += 1
            else:
                b1, b2 = board.get_piece(r - 1, c - 1), board.get_piece(r - 1, c + 1)
                if b1 and b1.color == RED: red_blockade_bonus += 1
                if b2 and b2.color == RED: red_blockade_bonus += 1
    blockade_score = white_blockade_bonus - red_blockade_bonus
    
    # --- MODIFIED: Use the new override parameter ---
    mobility_score = len(board.get_all_move_sequences(WHITE, override_turn_check=True)) - len(board.get_all_move_sequences(RED, override_turn_check=True))

    # --- Combine Weighted Scores ---
    w_material = material_score * config["MATERIAL_WEIGHT"]
    w_positional = positional_score * config["POSITIONAL_WEIGHT"]
    w_blockade = blockade_score * config["BLOCKADE_WEIGHT"]
    w_mobility = mobility_score * config["MOBILITY_WEIGHT"]
    w_advancement = advancement_score * config["ADVANCEMENT_WEIGHT"]
    
    final_score = w_material + w_positional + w_blockade + w_mobility + w_advancement + first_king_bonus

    # --- REVISED: Endgame Principles with Smoothed Scaling ---
    # This new logic removes the hard "cliff" at +/- 1.5, which was causing
    # the aspiration search to oscillate. The bonus now scales smoothly with
    # the material advantage, creating a stable evaluation.
    simplification_bonus = 0
    # Check for a material advantage BEFORE applying the bonus.
    # The bonus is proportional to the number of pieces traded off.
    if material_score > 0: # White has a material advantage
        # The bonus is scaled by the material score itself. A larger lead gives a stronger incentive to simplify.
        scaling_factor = min(1.0, material_score / 2.0) # Scale up to a 2-pawn advantage
        simplification_bonus = (12 - board.red_left) * config["SIMPLIFICATION_BONUS"] * scaling_factor
    elif material_score < 0: # Red has a material advantage
        scaling_factor = min(1.0, -material_score / 2.0)
        simplification_bonus = -((12 - board.white_left) * config["SIMPLIFICATION_BONUS"]) * scaling_factor
    
    final_score += simplification_bonus

    # --- NEW: Detailed Debug Logging ---
    eval_logger.debug(f"--- EVAL START for {board.turn} ---")
    eval_logger.debug(f"FEN: {board.get_fen()}")
    eval_logger.debug(f"Material: {material_score:.2f} -> Weighted: {w_material:.2f}")
    eval_logger.debug(f"Positional: {positional_score:.2f} -> Weighted: {w_positional:.2f}")
    eval_logger.debug(f"Blockade: {blockade_score:.2f} -> Weighted: {w_blockade:.2f}")
    eval_logger.debug(f"Mobility: {mobility_score:.2f} -> Weighted: {w_mobility:.2f}")
    eval_logger.debug(f"Advancement: {advancement_score:.2f} -> Weighted: {w_advancement:.2f}")
    eval_logger.debug(f"First King Bonus: {first_king_bonus:.2f}")
    eval_logger.debug(f"Simplification Bonus: {simplification_bonus:.2f}")
    eval_logger.debug(f"FINAL SCORE: {final_score:.4f}")
    eval_logger.debug("--- EVAL END ---")
    # --- END of new block ---

    return final_score

# ======================================================================================
# --- Public-Facing Evaluation Functions (Unchanged) ---
# ======================================================================================
def evaluate_board_v1(board):
    """The stable engine, using V1_CONFIG."""
    return _calculate_score(board, V1_CONFIG)

def evaluate_board_v2_experimental(board):
    """The experimental engine, using V2_CONFIG."""
    return _calculate_score(board, V2_CONFIG)


