# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS, ACF_TO_COORD

logger = logging.getLogger('board')

def evaluate_board(board):
    """
    Calculates the static score of the board from White's perspective.
    This is the AI's "brain" and includes multiple strategic heuristics.
    """
    # --- Material Score ---
    white_men = board.white_left - board.white_kings
    red_men = board.red_left - board.red_kings
    material_score = (white_men - red_men) + (board.white_kings - board.red_kings) * 1.5

    # --- Positional Scores ---
    white_pos_score = 0
    red_pos_score = 0
    
    # Heuristics:
    BACK_ROW_BONUS = 0.2
    CENTER_CONTROL_BONUS = 0.1
    PROMOTION_PROGRESS_BONUS = 0.1
    KING_ADVANTAGE_BONUS = 1.0

    # Evaluate White's pieces
    for piece in board.get_all_pieces(WHITE):
        white_pos_score += (ROWS - 1 - piece.row) * PROMOTION_PROGRESS_BONUS
        if piece.row in {2, 3, 4, 5} and piece.col in {2, 3, 4, 5}:
            white_pos_score += CENTER_CONTROL_BONUS

    # Evaluate Red's pieces
    for piece in board.get_all_pieces(RED):
        red_pos_score += piece.row * PROMOTION_PROGRESS_BONUS
        if piece.row == 0:
            red_pos_score += BACK_ROW_BONUS
        if piece.row in {2, 3, 4, 5} and piece.col in {2, 3, 4, 5}:
            red_pos_score += CENTER_CONTROL_BONUS

    positional_score = white_pos_score - red_pos_score

    # --- King Advantage Score ---
    king_advantage = 0
    if board.white_kings > 0 and board.red_kings == 0:
        king_advantage = KING_ADVANTAGE_BONUS
    elif board.red_kings > 0 and board.white_kings == 0:
        king_advantage = -KING_ADVANTAGE_BONUS

    # --- Final Score Combination ---
    final_score = (material_score * 100) + positional_score + king_advantage
    
    return final_score
