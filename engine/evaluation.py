# engine/evaluation.py
from .constants import *
from .checkers_game import Checkers

def evaluate_board_static(board, turn_to_move):
    gs = Checkers(board, turn_to_move, load_resources=False)
    red_moves, white_moves = gs.get_all_possible_moves(RED), gs.get_all_possible_moves(WHITE)
    red_jumps, white_jumps = any(abs(s[0]-e[0])==2 for s,e in red_moves), any(abs(s[0]-e[0])==2 for s,e in white_moves)
    is_tactical = red_jumps or white_jumps
    mat_score, pos_score = 0, 0
    for r, row in enumerate(board):
        for c, piece in enumerate(row):
            if piece == EMPTY: continue
            is_red = piece.lower() == RED
            mat_score += PIECE_VALUES[piece] if is_red else -PIECE_VALUES[piece]
            if not is_tactical and not piece.isupper():
                acf_pos = COORD_TO_ACF.get((r, c))
                if piece == RED and acf_pos in {1, 3}: pos_score += BACK_ROW_CORNER_BONUS
                elif piece == WHITE and acf_pos in {30, 32}: pos_score -= BACK_ROW_CORNER_BONUS
    if not is_tactical:
        red_kings = sum(row.count(RED_KING) for row in board)
        white_kings = sum(row.count(WHITE_KING) for row in board)
        if red_kings > 0 and white_kings == 0: pos_score += 0.5 * red_kings
        elif white_kings > 0 and red_kings == 0: pos_score -= 0.5 * white_kings
    return (mat_score * MATERIAL_MULTIPLIER) + pos_score
