# engine/evaluation.py
import logging
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF

logger = logging.getLogger('board')

# ======================================================================================
# --- 1. Piece-Square Tables (PSTs) & Configurations ---
# ======================================================================================
# These tables assign a strategic value to each square for each piece type,
# reflecting the strategic understanding you provided.

PST_TIER_1_SCORE = 3.0
PST_TIER_2_SCORE = 1.5
PST_TIER_3_SCORE = 0.5

TIER_1_SQUARES = {14, 15, 18, 19}
TIER_2_SQUARES = {1, 2, 3, 5, 16, 17, 30, 31, 32}

MAN_PST = [0.0] * 33
KING_PST = [0.0] * 33

for i in range(1, 33):
    if i in TIER_1_SQUARES:
        MAN_PST[i] = PST_TIER_1_SCORE
        KING_PST[i] = PST_TIER_1_SCORE * 1.5
    elif i in TIER_2_SQUARES:
        MAN_PST[i] = PST_TIER_2_SCORE
        KING_PST[i] = PST_TIER_2_SCORE
    else:
        MAN_PST[i] = PST_TIER_3_SCORE
        KING_PST[i] = PST_TIER_3_SCORE

# --- Engine Configuration Dictionaries ---
# To test a new idea, simply change a weight in the V2_CONFIG.

V1_CONFIG = {
    "MATERIAL_WEIGHT": 10.0,
    "POSITIONAL_WEIGHT": 0.1,
    "BLOCKADE_WEIGHT": 0.5,
    "SIMPLIFICATION_BONUS": 0.2 # Bonus for trading pieces when ahead
}

V2_CONFIG = {
    "MATERIAL_WEIGHT": 10.0,
    "POSITIONAL_WEIGHT": 0.15, # EXPERIMENTAL: Higher positional value
    "BLOCKADE_WEIGHT": 0.75,   # EXPERIMENTAL: Higher blockade value
    "SIMPLIFICATION_BONUS": 0.2
}

# ======================================================================================
# --- 2. Core Evaluation Logic ---
# ======================================================================================

def _calculate_score(board, config):
    """
    The single, core evaluation function.
    Calculates the board score based on the provided configuration weights.
    """
    # --- Phase 1: Endgame Database Check ---
    if board.db_conn:
        try:
            table_name, key_tuple = board._get_endgame_key()
            if table_name and key_tuple:
                num_pieces = len(key_tuple) - 1
                where_clause = ' AND '.join([f'p{i + 1}_pos = ?' for i in range(num_pieces)])
                sql = f"SELECT result FROM {table_name} WHERE {where_clause} AND turn = ?"
                params = key_tuple
                cursor = board.db_conn.cursor()
                cursor.execute(sql, params)
                result = cursor.fetchone()
                if result:
                    db_score = int(result[0])
                    if db_score > 0: return 1000 - db_score
                    if db_score < 0: return -1000 - db_score
                    return 0
        except Exception as e:
            logger.error(f"DATABASE: Error during query: {e}", exc_info=True)

    # --- Phase 2: Material and Positional Score ---
    material_score = 0
    positional_score = 0
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if not piece: continue
            
            is_white = piece.color == WHITE
            material_value = 1.5 if piece.king else 1.0
            material_score += material_value if is_white else -material_value
            
            acf_pos = COORD_TO_ACF.get((r, c))
            if not acf_pos: continue
            
            pst_score = KING_PST[acf_pos] if piece.king else MAN_PST[acf_pos]
            positional_score += pst_score if is_white else -pst_score

    # --- Phase 3: Blockade Score ---
    red_blockade_bonus = 0
    white_blockade_bonus = 0
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if not piece or piece.king: continue

            if piece.color == RED:
                blocker1 = board.get_piece(r + 1, c - 1)
                blocker2 = board.get_piece(r + 1, c + 1)
                if blocker1 and blocker1.color == WHITE: white_blockade_bonus += 1
                if blocker2 and blocker2.color == WHITE: white_blockade_bonus += 1
            else: # White piece
                blocker1 = board.get_piece(r - 1, c - 1)
                blocker2 = board.get_piece(r - 1, c + 1)
                if blocker1 and blocker1.color == RED: red_blockade_bonus += 1
                if blocker2 and blocker2.color == RED: red_blockade_bonus += 1

    blockade_score = white_blockade_bonus - red_blockade_bonus

    # --- Phase 4: Combine Scores using Config Weights ---
    final_score = (material_score * config["MATERIAL_WEIGHT"]) + \
                  (positional_score * config["POSITIONAL_WEIGHT"]) + \
                  (blockade_score * config["BLOCKADE_WEIGHT"])

    # --- Phase 5: State-Dependent Adjustments ---
    # Encourage trading pieces when ahead to simplify to a winning endgame
    if final_score > 1.5: # White is winning
        return final_score + ((12 - board.red_left) * config["SIMPLIFICATION_BONUS"])
    elif final_score < -1.5: # Red is winning
        return final_score - ((12 - board.white_left) * config["SIMPLIFICATION_BONUS"])

    return final_score

# ======================================================================================
# --- 3. Public-Facing Evaluation Functions ---
# ======================================================================================

def evaluate_board_v1(board):
    """
    This is the STABLE version of your evaluation function.
    It uses the V1_CONFIG weights.
    """
    return _calculate_score(board, V1_CONFIG)

def evaluate_board_v2_experimental(board):
    """
    This is the EXPERIMENTAL version for testing new ideas.
    It uses the V2_CONFIG weights.
    """
    return _calculate_score(board, V2_CONFIG)


