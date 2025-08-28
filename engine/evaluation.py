# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS, ACF_TO_COORD

logger = logging.getLogger('board')

def evaluate_board(board):
    white_material = (board.white_left - board.white_kings) * 1.0 + board.white_kings * 1.5
    red_material = (board.red_left - board.red_kings) * 1.0 + board.red_kings * 1.5
    material_score = white_material - red_material
    
    white_moves = board.get_all_valid_moves(WHITE)
    red_moves = board.get_all_valid_moves(RED)
    mobility_score = 0.1 * (len(white_moves) - len(red_moves))
    
   # CORRECTED JUMP COUNTING LOGIC
    white_jumps = 0
    for start_pos, end_positions in white_moves.items():
        if any(abs(start_pos[0] - end_pos[0]) == 2 for end_pos in end_positions):
            white_jumps += 1

    red_jumps = 0
    for start_pos, end_positions in red_moves.items():
        if any(abs(start_pos[0] - end_pos[0]) == 2 for end_pos in end_positions):
            red_jumps += 1
            
    jump_score = 0.5 * (white_jumps - red_jumps)

    final_score = (material_score * 100) + mobility_score + jump_score
    
    return final_score
