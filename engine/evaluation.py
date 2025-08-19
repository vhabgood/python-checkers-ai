# engine/evaluation.py
from .constants import RED, WHITE, RED_KING, WHITE_KING, EMPTY

def evaluate_board_static(board, turn, piece_values):
    mat_score = 0
    pos_score = 0
    is_red = turn == RED

    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece == EMPTY:
                continue
            mat_score += piece_values[piece] if is_red else -piece_values[piece]
            if piece.lower() == RED:
                pos_score += (7 - r) * 0.1 if is_red else r * 0.1
            else:
                pos_score += r * 0.1 if is_red else (7 - r) * 0.1
            if piece.isupper():
                pos_score += 0.2

    return (mat_score + pos_score) * 1500.0
