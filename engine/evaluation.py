# engine/evaluation.py
"""
Contains the evaluation function for the AI.
This function analyzes a board state and returns a score.
"""
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS

logger = logging.getLogger('board')

def evaluate_board(board):
    """
    Analyzes the board and returns a score from the perspective of the White player.
    """
    # --- 1. Material Score (heavily weighted) ---
    white_material = (board.white_left - board.white_kings) * 1.0 + board.white_kings * 1.5
    red_material = (board.red_left - board.red_kings) * 1.0 + board.red_kings * 1.5
    material_score = white_material - red_material

    # --- 2. Positional & Mobility Scores ---
    center_control_score = 0
    
    # Calculate mobility for both sides
    white_moves_count = len(board.get_all_valid_moves_for_color(WHITE))
    red_moves_count = len(board.get_all_valid_moves_for_color(RED))
    mobility_score = 0.1 * (white_moves_count - red_moves_count)

    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if isinstance(piece, Piece):
                # Center Control Bonus: add a small bonus for pieces in or near the center
                if c in [2, 3, 4, 5]:
                    if piece.color == WHITE:
                        center_control_score += 0.1
                    else:
                        center_control_score -= 0.1

    # --- Final Score Calculation ---
    # Material score is multiplied by 100 to make it the dominant factor.
    final_score = (material_score * 100) + center_control_score + mobility_score
    
    logger.debug(f"Eval Breakdown: Material={material_score*100:.2f}, Center={center_control_score:.2f}, Mobility={mobility_score:.2f} | Final={final_score:.2f}")
    
    return final_score
