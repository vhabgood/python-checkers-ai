# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS, ACF_TO_COORD

logger = logging.getLogger('board')

def evaluate_board(board):
    white_material = (board.white_left - board.white_kings) * 1.0 + board.white_kings * 1.5
    red_material = (board.red_left - board.red_kings) * 1.0 + board.red_kings * 1.5
    material_score = white_material - red_material
    
    white_moves = board.get_all_valid_moves_for_color(WHITE)
    red_moves = board.get_all_valid_moves_for_color(RED)
    mobility_score = 0.1 * (len(white_moves) - len(red_moves))
    
    white_jumps = sum(1 for moves in white_moves.values() if abs(list(moves.keys())[0][0] - list(white_moves.keys())[0][0]) > 1)
    red_jumps = sum(1 for moves in red_moves.values() if abs(list(moves.keys())[0][0] - list(red_moves.keys())[0][0]) > 1)
    jump_score = 0.5 * (white_jumps - red_jumps)

    final_score = (material_score * 100) + mobility_score + jump_score
    
    return final_score