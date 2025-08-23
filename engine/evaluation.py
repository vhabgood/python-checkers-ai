# engine/evaluation.py
"""
Contains the evaluation function for the AI.
This function analyzes a board state and returns a score.
"""
from .piece import Piece

def evaluate_board(board):
    """
    Analyzes the board and returns a score from the perspective of the White player.

    A positive score indicates an advantage for White.
    A negative score indicates an advantage for Red.

    Args:
        board (Board): The board object to evaluate.

    Returns:
        float: The calculated score for the board position.
    """
    # Simple material score: kings are worth more than regular men.
    white_score = (board.white_left - board.white_kings) * 1.0 + board.white_kings * 1.5
    red_score = (board.red_left - board.red_kings) * 1.0 + board.red_kings * 1.5
    
    # TODO: We can add more advanced positional scoring here based on your feedback.
    
    return white_score - red_score
