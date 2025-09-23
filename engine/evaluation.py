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
    "MATERIAL_MULTIPLIER": 15.0, #already tuned, please do not change. 11/22/2025 MM=15
    "POSITIONAL_MULTIPLIER": 0.12, #new champ 11/22/2025 2023 by 2 games over .10, beat .13 by 1
    "BLOCKADE_MULTIPLIER": 0.8, # (.07 tied with .10) (.8 beat .9 by 1 game)
    "MOBILITY_MULTIPLIER": 0.12, #already tuned, please do not change. 11/22. beat .13 by 2 games.
    "ADVANCEMENT_MULTIPLIER": 0.07, #champ 11/22/2025 2026 beat .08 by 1 game
    "MAN_VALUE": 1.7, #current champ, beat 2.0 by 4 games, beat 1.8 by 5 games.
    "KING_VALUE": 2.8, #current champ
    "FIRST_KING_BONUS": 25.0, #beat 50 by 1 game, tied with 30 & 20, beat 5 by 1 game 11/23/2025
    "SIMPLIFICATION_BONUS": 0.1, #champ beat .05 by 1 game and .15 by 1 game 11/23/2025
    "BLOCKADE_SCORE": 9.0 #beat 10 by 3 games. tied with 8.
}

V2_CONFIG = {
    "MATERIAL_MULTIPLIER": 15.0, #already tuned
    "POSITIONAL_MULTIPLIER": 0.12, #already tuned
    "BLOCKADE_MULTIPLIER": 0.8, #begin tuning from 1.0 upwards, 1.5 lost by 11 games, 1.2 lost by 5 games, .10 and .07 tied,.8 beat .9
    "MOBILITY_MULTIPLIER": 0.12, # between .12-.13 for future testing, tuned enough for now
    "ADVANCEMENT_MULTIPLIER": 0.07, #already tuned
    "MAN_VALUE": 1.7, #try between 1.2-1.6 later
    "KING_VALUE": 2.8, #change last
    "FIRST_KING_BONUS": 25.0, #50 lost to 25 by 1 game. 30 tied with 25. 20 also tied with 25. 25 beat 5 by 1 game
    "SIMPLIFICATION_BONUS": 0.1, #(.5 lost to .05 by 2 games)(.15 lost to .1 by 1 game)
    "BLOCKADE_SCORE": 9.0 #begin from 15 down, 20 got beat by 9 games. 10 got beat by 1 game by 9. 8 vs 9 tied.
}
#left is first king bonus=5, right simp bonus =.15
def _calculate_score(board, config):
    """
    Refactored evaluation logic to accept a configuration dictionary.
    """
    material_score = 0
    positional_score = 0
    advancement_score = 0
    red_men, white_men, red_kings, white_kings = [], [], [], []

    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if not piece:
                continue

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

    temp_board = board.copy()
    temp_board.turn = RED
    red_moves = _get_all_moves_for_color(temp_board)
    temp_board.turn = WHITE
    white_moves = _get_all_moves_for_color(temp_board)
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
