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
    # 1. Material Score (heavily weighted)
    white_material = (board.white_left - board.white_kings) * 1.0 + board.white_kings * 1.5
    red_material = (board.red_left - board.red_kings) * 1.0 + board.red_kings * 1.5
    material_score = white_material - red_material

    # 2. Positional & Tactical Scores
    white_moves = board.get_all_valid_moves_for_color(WHITE)
    red_moves = board.get_all_valid_moves_for_color(RED)
    
    # Mobility Score: bonus for having more moves
    mobility_score = 0.1 * (len(white_moves) - len(red_moves))
    
    # Jump Potential Score: bonus for having available captures
    white_jumps = sum(1 for moves in white_moves.values() if abs(list(moves.keys())[0][0] - list(white_moves.keys())[0][0]) > 1)
    red_jumps = sum(1 for moves in red_moves.values() if abs(list(moves.keys())[0][0] - list(red_moves.keys())[0][0]) > 1)
    jump_score = 0.5 * (white_jumps - red_jumps)

    # Final Score Calculation
    final_score = (material_score * 100) + mobility_score + jump_score
    
    # Logging is removed from here to keep log files small.
    # We can add it back temporarily if we need to debug the evaluation itself.
    
    return final_score
