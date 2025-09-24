# engine/evaluation.py
import logging
import sqlite3
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF
from .search import _get_all_moves_for_color

eval_logger = logging.getLogger('eval')

# --- Piece Square Tables (PST) ---
PST_TIER_1_SCORE, PST_TIER_2_SCORE, PST_TIER_3_SCORE = 3.0, 1.5, 0.5
TIER_1_SQUARES = {14, 15, 18, 19} # Center squares
TIER_2_SQUARES = {1, 2, 3, 5, 16, 17, 30, 31, 32} # Key edge and setup squares
MAN_PST, KING_PST = [0.0] * 33, [0.0] * 33
for i in range(1, 33):
    if i in TIER_1_SQUARES: MAN_PST[i], KING_PST[i] = PST_TIER_1_SCORE, PST_TIER_1_SCORE * 1.5
    elif i in TIER_2_SQUARES: MAN_PST[i], KING_PST[i] = PST_TIER_2_SCORE, PST_TIER_2_SCORE
    else: MAN_PST[i], KING_PST[i] = PST_TIER_3_SCORE, PST_TIER_3_SCORE

# ======================================================================================
# --- CONFIGURATIONS FOR DIFFERENT ENGINE VERSIONS ---
# ======================================================================================

V1_CONFIG = {
    "MATERIAL_MULTIPLIER": 3.0, 
    "POSITIONAL_MULTIPLIER": 0.42, 
    "BLOCKADE_MULTIPLIER": 0.7, 
    "MOBILITY_MULTIPLIER": 0.12, 
    "ADVANCEMENT_MULTIPLIER": 0.07, 
    "PATHS_TO_KING_MULTIPLIER": 0.7,
    "MAN_VALUE": 1.7, 
    "KING_VALUE": 2.8, 
    "FIRST_KING_BONUS": 25.0, #beat 50 by 1 game, tied with 30 & 20, beat 5 by 1 game 11/23/2025
    "SIMPLIFICATION_BONUS": 0.1, #champ beat .05 by 1 game and .15 by 1 game 11/23/2025
    "BLOCKADE_SCORE": 9.0 #beat 10 by 3 games. tied with 8.
}

V2_CONFIG = {
    "MATERIAL_MULTIPLIER": 2.0,   #starting with 3   
    "POSITIONAL_MULTIPLIER": 0.42,   
    "BLOCKADE_MULTIPLIER": 0.7,    
    "MOBILITY_MULTIPLIER": 0.12,     
    "ADVANCEMENT_MULTIPLIER": 0.07, 
    "PATHS_TO_KING_MULTIPLIER": 0.7, 
    "MAN_VALUE": 1.7,
    "KING_VALUE": 2.8,
    "FIRST_KING_BONUS": 20.0,
    "SIMPLIFICATION_BONUS": 0.25,   
    "BLOCKADE_SCORE": 12.0          
}
#left is NONE, right mat mul =3
def _calculate_score(board, config):
    material_score, positional_score, advancement_score = 0, 0, 0
    red_men, white_men, red_kings, white_kings = [], [], [], []

    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if not piece: continue

            acf_pos = COORD_TO_ACF.get((r, c), 0)
            if piece.color == RED:
                material_score += (config["KING_VALUE"] if piece.king else config["MAN_VALUE"])
                positional_score += (KING_PST[acf_pos] if piece.king else MAN_PST[acf_pos])
                advancement_score += r if not piece.king else 0
                if piece.king: red_kings.append(piece)
                else: red_men.append(piece)
            else:
                material_score -= (config["KING_VALUE"] if piece.king else config["MAN_VALUE"])
                positional_score -= (KING_PST[acf_pos] if piece.king else MAN_PST[acf_pos])
                advancement_score -= (7 - r) if not piece.king else 0
                if piece.king: white_kings.append(piece)
                else: white_men.append(piece)

    blockade_score = 0
    if board.turn == RED:
        temp_board = board.copy()
        temp_board.turn = WHITE
        for piece in white_kings + white_men:
            if not temp_board.get_valid_moves(piece):
                blockade_score += config["BLOCKADE_SCORE"]
    else:
        temp_board = board.copy()
        temp_board.turn = RED
        for piece in red_kings + red_men:
            if not temp_board.get_valid_moves(piece):
                blockade_score -= config["BLOCKADE_SCORE"]

    # --- Paths to King Score Calculation ---
    paths_to_king_score = 0
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if piece and not piece.king:
                if piece.color == RED:
                    # --- FIX: Added boundary checks ---
                    path1_clear = (r + 1 < ROWS and c - 1 >= 0 and not board.get_piece(r + 1, c - 1))
                    path2_clear = (r + 1 < ROWS and c + 1 < COLS and not board.get_piece(r + 1, c + 1))
                    # ---------------------------------
                    if path1_clear and path2_clear: paths_to_king_score += (r * 0.2)
                    elif path1_clear or path2_clear: paths_to_king_score += (r * 0.1)
                else: # Piece is WHITE
                    # --- FIX: Added boundary checks ---
                    path1_clear = (r - 1 >= 0 and c - 1 >= 0 and not board.get_piece(r - 1, c - 1))
                    path2_clear = (r - 1 >= 0 and c + 1 < COLS and not board.get_piece(r - 1, c + 1))
                    # ---------------------------------
                    advancement = 7 - r
                    if path1_clear and path2_clear: paths_to_king_score -= (advancement * 0.2)
                    elif path1_clear or path2_clear: paths_to_king_score -= (advancement * 0.1)

    temp_board = board.copy()
    temp_board.turn = RED
    red_moves = _get_all_moves_for_color(temp_board, None, [])
    temp_board.turn = WHITE
    white_moves = _get_all_moves_for_color(temp_board, None, [])
    mobility_score = len(red_moves) - len(white_moves)

    first_king_bonus = 0
    if board.red_kings > 0 and board.white_kings == 0:
        first_king_bonus = config["FIRST_KING_BONUS"]
    elif board.white_kings > 0 and board.red_kings == 0:
        first_king_bonus = -config["FIRST_KING_BONUS"]

    simplification_bonus = 0
    if material_score != 0:
        total_pieces = board.red_left + board.white_left
        simplification_bonus = (material_score / abs(material_score)) * (32 - total_pieces) * config["SIMPLIFICATION_BONUS"]

    final_score = (
        (material_score * config["MATERIAL_MULTIPLIER"]) +
        (positional_score * config["POSITIONAL_MULTIPLIER"]) +
        (blockade_score * config["BLOCKADE_MULTIPLIER"]) +
        (mobility_score * config["MOBILITY_MULTIPLIER"]) +
        (advancement_score * config["ADVANCEMENT_MULTIPLIER"]) +
        (paths_to_king_score * config["PATHS_TO_KING_MULTIPLIER"]) +
        first_king_bonus +
        simplification_bonus
    )
    
    eval_logger.debug(f"Raw score (Red's perspective): {final_score:.4f}")
    return final_score if board.turn == RED else -final_score


def evaluate_board_v1(board):
    #eval_logger.debug(f"--- V1 (STABLE) EVALUATION CALLED for {board.turn} ---")
    return _calculate_score(board, V1_CONFIG)

def evaluate_board_v2_experimental(board):
    #eval_logger.debug(f"--- V2 (EXPERIMENTAL) EVALUATION CALLED for {board.turn} ---")
    return _calculate_score(board, V2_CONFIG)
