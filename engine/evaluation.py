# engine/evaluation.py
import logging
import sqlite3
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF
from .board import Board

eval_logger = logging.getLogger('eval')

# --- Piece Square Tables (PST) ---
PST_TIER_1_SCORE, PST_TIER_2_SCORE, PST_TIER_3_SCORE = 1.0, .7, 0.6
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
    "MATERIAL_MULTIPLIER": 0.2, #2025-09-29 06:46:40,537 - Final Score: [.25] 130 - V2 [.2] - Draws 71 (between .2 and .25 next)
    "POSITIONAL_MULTIPLIER": 0.35, #beat .55 25 straight games. Beat .1 by 25 games and only 50 games in..4 beat .3, beat .4 by 3 games!
    "BLOCKADE_MULTIPLIER": 0.5, #.5 destroyed .25, even worse to 1.0, beat .75 also badly
    "MOBILITY_MULTIPLIER": 0.25,     
    "ADVANCEMENT_MULTIPLIER": 0.05, 
    "PATHS_TO_KING_MULTIPLIER": 0.40, 
    "MAN_VALUE": 1, #set
    "KING_VALUE": 1.6, #set
    "FIRST_KING_BONUS": .4,
    "SIMPLIFICATION_BONUS": 0.25,   
    "BLOCKADE_SCORE": 0.50 
}

V2_CONFIG = {
    "MATERIAL_MULTIPLIER": 0.2,
    "POSITIONAL_MULTIPLIER": 0.35,
    "BLOCKADE_MULTIPLIER": 0.6,    
    "MOBILITY_MULTIPLIER": 0.25,     
    "ADVANCEMENT_MULTIPLIER": 0.05, 
    "PATHS_TO_KING_MULTIPLIER": 0.40, 
    "MAN_VALUE": 1,
    "KING_VALUE": 1.6,
    "FIRST_KING_BONUS": .4,
    "SIMPLIFICATION_BONUS": 0.25,   
    "BLOCKADE_SCORE": 0.50          
}
#left is NONE, right mat mul =3
def _calculate_score(board, config):
    # --- THIS IS THE FIX ---
    # Check for a terminal node (a win/loss) first.
    # If a winner exists, it means the current player to move has no legal moves and has lost.
    # The evaluation should be from the perspective of the player whose turn it is,
    # so we return a massive negative score indicating a loss.
    if board.winner() is not None:
        return -99999
    # -----------------------
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

    paths_to_king_score = 0
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if piece and not piece.king:
                if piece.color == RED:
                    path1_clear = (r + 1 < ROWS and c - 1 >= 0 and not board.get_piece(r + 1, c - 1))
                    path2_clear = (r + 1 < ROWS and c + 1 < COLS and not board.get_piece(r + 1, c + 1))
                    if path1_clear and path2_clear: paths_to_king_score += (r * 0.2)
                    elif path1_clear or path2_clear: paths_to_king_score += (r * 0.1)
                else: # Piece is WHITE
                    path1_clear = (r - 1 >= 0 and c - 1 >= 0 and not board.get_piece(r - 1, c - 1))
                    path2_clear = (r - 1 >= 0 and c + 1 < COLS and not board.get_piece(r - 1, c + 1))
                    advancement = 7 - r
                    if path1_clear and path2_clear: paths_to_king_score -= (advancement * 0.2)
                    elif path1_clear or path2_clear: paths_to_king_score -= (advancement * 0.1)

    temp_board = board.copy()
    temp_board.turn = RED
    red_moves = temp_board.get_all_valid_moves(RED)
    temp_board.turn = WHITE
    white_moves = temp_board.get_all_valid_moves(WHITE)
    mobility_score = len(red_moves) - len(white_moves)

    first_king_bonus = 0
    if board.red_kings > 0 and board.white_kings == 0:
        first_king_bonus = config["FIRST_KING_BONUS"]
    elif board.white_kings > 0 and board.red_kings == 0:
        first_king_bonus = -config["FIRST_KING_BONUS"]

    # --- FIX: Check if the current position is "quiet" before adding bonuses ---
    is_tactical = any(abs(move[0][0] - move[1][0]) == 2 for move in red_moves + white_moves)
    simplification_bonus = 0
    if material_score != 0 and not is_tactical:
    # -------------------------------------------------------------------------
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
