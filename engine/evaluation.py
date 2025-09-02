# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS

logger = logging.getLogger('board')

def evaluate_board(board):
    """
    Calculates the static score of the board from White's perspective.
    This is a stable base evaluation without database lookups.
    """
    # --- 1. Material Score: Kings are worth 1.5x a regular piece ---
    white_men = board.white_left - board.white_kings
    red_men = board.red_left - board.red_kings
    material_score = (white_men - red_men) + (board.white_kings - board.red_kings) * 1.5

    # --- 2. Positional Scores ---
    white_pos_score = 0
    red_pos_score = 0
    
    PROMOTION_PROGRESS_BONUS = 0.1  # Reward for pieces nearing the king row.
    CENTER_CONTROL_BONUS = 0.1    # Reward for pieces in the center.
    KING_ADVANTAGE_BONUS = 1.0      # Bonus for having the only kings.

    for piece in board.get_all_pieces(WHITE):
        # Add bonus for advancing towards the king row
        white_pos_score += (ROWS - 1 - piece.row) * PROMOTION_PROGRESS_BONUS
        # Add bonus for controlling the center
        if piece.col in {2, 3, 4, 5}:
            white_pos_score += CENTER_CONTROL_BONUS

    for piece in board.get_all_pieces(RED):
        red_pos_score += piece.row * PROMOTION_PROGRESS_BONUS
        if piece.col in {2, 3, 4, 5}:
            red_pos_score += CENTER_CONTROL_BONUS

    positional_score = white_pos_score - red_pos_score

    # --- 3. King Advantage Score ---
    king_advantage = 0
    if board.white_kings > 0 and board.red_kings == 0:
        king_advantage = KING_ADVANTAGE_BONUS
    elif board.red_kings > 0 and board.white_kings == 0:
        king_advantage = -KING_ADVANTAGE_BONUS
        
    final_score = (material_score * 10) + positional_score + king_advantage
    return final_score
