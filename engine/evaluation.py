# engine/evaluation.py
"""
Contains the evaluation function for the AI.
This function analyzes a board state and returns a score.
"""
import logging
from .piece import Piece

logger = logging.getLogger('board')

def evaluate_board(board):
    """
    Analyzes the board and returns a score from the perspective of the White player.

    A positive score indicates an advantage for White.
    A negative score indicates an advantage for Red.
    """
    # Simple material score: kings are worth more than regular men.
    white_score = (board.white_left - board.white_kings) * 1.0 + board.white_kings * 1.5
    red_score = (board.red_left - board.red_kings) * 1.0 + board.red_kings * 1.5
    
    final_score = white_score - red_score
    
    logger.debug(f"Evaluation: White Score={white_score:.2f}, Red Score={red_score:.2f}, Final Score={final_score:.2f}")
    
    return final_score
