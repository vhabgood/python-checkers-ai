# engine/evaluation.py
import logging
import sqlite3
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF

logger = logging.getLogger('board')

# ======================================================================================
# --- 1. Piece-Square Tables (PSTs) & Configurations ---
# ======================================================================================
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

# V1 is our stable champion.
V1_CONFIG = {
    "MATERIAL_WEIGHT": 10.0,
    "POSITIONAL_WEIGHT": 0.15,
    "BLOCKADE_WEIGHT": 0.75,
    "FIRST_KING_BONUS": 7.5,
    "SIMPLIFICATION_BONUS": 0.3,
    "MOBILITY_WEIGHT": 0.1
}

# V2 is the new challenger with a stronger focus on blockade and first king bonus
V2_CONFIG = {
    "MATERIAL_WEIGHT": 10.0,
    "POSITIONAL_WEIGHT": 0.15,  
    "BLOCKADE_WEIGHT": 0.95,
    "FIRST_KING_BONUS": 8.5,
    "SIMPLIFICATION_BONUS": 0.3,
    "MOBILITY_WEIGHT": 0.1   
}


# ======================================================================================
# --- 2. Core Evaluation Logic (Unified for all engines) ---
# ======================================================================================

def _calculate_score(board, config):
    """
    The single, core evaluation function.
    Calculates the board score based on the provided configuration weights.
    """
    # --- Phase 1: Endgame Database Check ---
    if hasattr(board, 'db_conn') and board.db_conn:
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

    # --- Phase 2: Material, Positional, and First King Score ---
    material_score = 0
    positional_score = 0
    first_king_bonus = 0
    if board.white_kings > 0 and board.red_kings == 0:
        first_king_bonus = config["FIRST_KING_BONUS"]
    elif board.red_kings > 0 and board.white_kings == 0:
        first_king_bonus = -config["FIRST_KING_BONUS"]

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
                blocker1, blocker2 = board.get_piece(r + 1, c - 1), board.get_piece(r + 1, c + 1)
                if blocker1 and blocker1.color == WHITE: white_blockade_bonus += 1
                if blocker2 and blocker2.color == WHITE: white_blockade_bonus += 1
            else:
                blocker1, blocker2 = board.get_piece(r - 1, c - 1), board.get_piece(r - 1, c + 1)
                if blocker1 and blocker1.color == RED: red_blockade_bonus += 1
                if blocker2 and blocker2.color == RED: red_blockade_bonus += 1
    blockade_score = white_blockade_bonus - red_blockade_bonus
    
    # --- Phase 4: Mobility Score ---
    white_moves_count = len(board.get_all_move_sequences(WHITE))
    red_moves_count = len(board.get_all_move_sequences(RED))
    mobility_score = white_moves_count - red_moves_count

    # --- Phase 5: Combine Scores ---
    final_score = (material_score * config["MATERIAL_WEIGHT"]) + \
                  (positional_score * config["POSITIONAL_WEIGHT"]) + \
                  (blockade_score * config["BLOCKADE_WEIGHT"]) + \
                  (mobility_score * config["MOBILITY_WEIGHT"]) + \
                  first_king_bonus

    # --- Phase 6: Endgame Principles ---
    if final_score > 1.5:
        final_score += (12 - board.red_left) * config["SIMPLIFICATION_BONUS"]
    elif final_score < -1.5:
        final_score -= (12 - board.white_left) * config["SIMPLIFICATION_BONUS"]

    return final_score

# ======================================================================================
# --- 3. Public-Facing Evaluation Functions ---
# ======================================================================================

def evaluate_board_v1(board):
    """The stable engine, our promoted champion."""
    return _calculate_score(board, V1_CONFIG)

def evaluate_board_v2_experimental(board):
    """
    The new experimental engine with doubled positional and mobility weights.
    """
    return _calculate_score(board, V2_CONFIG)


