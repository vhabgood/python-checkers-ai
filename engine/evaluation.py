# engine/evaluation.py
import logging
import sqlite3
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF
from .search import _get_all_moves_for_color

eval_logger = logging.getLogger('eval')

PST_TIER_1_SCORE, PST_TIER_2_SCORE, PST_TIER_3_SCORE = 3.0, 1.5, 0.5
TIER_1_SQUARES = {14, 15, 18, 19}
TIER_2_SQUARES = {1, 2, 3, 5, 16, 17, 30, 31, 32}
MAN_PST, KING_PST = [0.0] * 33, [0.0] * 33
for i in range(1, 33):
    if i in TIER_1_SQUARES: MAN_PST[i], KING_PST[i] = PST_TIER_1_SCORE, PST_TIER_1_SCORE * 1.5
    elif i in TIER_2_SQUARES: MAN_PST[i], KING_PST[i] = PST_TIER_2_SCORE, PST_TIER_2_SCORE
    else: MAN_PST[i], KING_PST[i] = PST_TIER_3_SCORE, PST_TIER_3_SCORE

V1_CONFIG = {"MATERIAL_MULTIPLIER":10.0,"POSITIONAL_MULTIPLIER":0.15,"BLOCKADE_MULTIPLIER":0.75,"MOBILITY_MULTIPLIER":0.10,"ADVANCEMENT_MULTIPLIER":0.05,"FIRST_KING_BONUS":7.5,"SIMPLIFICATION_BONUS":0.3}
V2_CONFIG = {"MATERIAL_MULTIPLIER":10.0,"POSITIONAL_MULTIPLIER":0.45,"BLOCKADE_MULTIPLIER":0.75,"MOBILITY_MULTIPLIER":0.10,"ADVANCEMENT_MULTIPLIER":0.85,"FIRST_KING_BONUS":7.5,"SIMPLIFICATION_BONUS":0.3}

def _calculate_score(board, config):
    if board.winner() is not None:
        return float('inf') if board.winner() == RED else -float('inf')

    material_score = (board.red_left + board.red_kings * 0.5) - (board.white_left + board.white_kings * 0.5)
    
    positional_score = 0
    advancement_score = 0
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if piece:
                pos = COORD_TO_ACF.get((r,c))
                pst = KING_PST if piece.king else MAN_PST
                score_modifier = 1 if piece.color == RED else -1
                positional_score += pst[pos] * score_modifier
                if not piece.king:
                    advancement_score += ((ROWS - 1 - r) if piece.color == RED else -r)

    original_turn = board.turn
    board.turn = RED
    red_moves = _get_all_moves_for_color(board)
    board.turn = WHITE
    white_moves = _get_all_moves_for_color(board)
    board.turn = original_turn
    mobility_score = len(red_moves) - len(white_moves)

    # --- CRITICAL FIX: Use the 'config' dictionary for bonus calculations ---
    first_king_bonus = 0
    if board.red_kings > 0 and board.white_kings == 0: first_king_bonus = config["FIRST_KING_BONUS"]
    elif board.white_kings > 0 and board.red_kings == 0: first_king_bonus = -config["FIRST_KING_BONUS"]

    simplification_bonus = 0
    if material_score != 0:
        total_pieces = board.red_left + board.white_left
        simplification_bonus = (material_score / abs(material_score)) * (32 - total_pieces) * config["SIMPLIFICATION_BONUS"]
    # --- END FIX ---

    final_score = (material_score * config["MATERIAL_MULTIPLIER"] +
                   positional_score * config["POSITIONAL_MULTIPLIER"] +
                   mobility_score * config["MOBILITY_MULTIPLIER"] +
                   advancement_score * config["ADVANCEMENT_MULTIPLIER"] +
                   first_king_bonus + simplification_bonus)
    
    eval_logger.debug(f"Raw score (Red's perspective): {final_score:.4f}")

    return final_score if board.turn == RED else -final_score

def evaluate_board_v1(board):
    eval_logger.debug(f"--- V1 (STABLE) EVALUATION CALLED for {board.turn} ---")
    return _calculate_score(board, V1_CONFIG)

def evaluate_board_v2_experimental(board):
    eval_logger.debug(f"--- V2 (EXPERIMENTAL) EVALUATION CALLED for {board.turn} ---")
    return _calculate_score(board, V2_CONFIG)
