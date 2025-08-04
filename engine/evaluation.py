# engine/evaluation.py
from .constants import (
    Checkers, EMPTY, RED, WHITE, RED_KING, WHITE_KING,
    COORD_TO_ACF, PIECE_VALUES, MATERIAL_MULTIPLIER,
    BACK_ROW_CORNER_BONUS
)

def evaluate_board_static(board, turn_to_move):
    """
    Calculates the static evaluation of a given board state.
    This is the "brain" of the AI.
    """
    # Create a temporary, lightweight game state to access move generation
    gs = Checkers(board, turn_to_move, load_resources=False)
    red_moves = gs.get_all_possible_moves(RED)
    white_moves = gs.get_all_possible_moves(WHITE)
    
    red_jumps = any(abs(s[0] - e[0]) == 2 for s, e in red_moves)
    white_jumps = any(abs(s[0] - e[0]) == 2 for s, e in white_moves)
    is_tactical = red_jumps or white_jumps

    mat_score, pos_score = 0, 0
    
    for r, row in enumerate(board):
        for c, piece in enumerate(row):
            if piece == EMPTY:
                continue
            
            is_red = piece.lower() == RED
            
            # 1. Material Score (Always counted)
            mat_score += PIECE_VALUES[piece] if is_red else -PIECE_VALUES[piece]
            
            # 2. Positional Score (Only in quiet, non-tactical positions)
            if not is_tactical:
                if not piece.isupper(): # Man positional logic
                    acf_pos = COORD_TO_ACF.get((r, c))
                    if piece == RED and acf_pos in {1, 3}:
                        pos_score += BACK_ROW_CORNER_BONUS
                    elif piece == WHITE and acf_pos in {30, 32}:
                        pos_score -= BACK_ROW_CORNER_BONUS
                        
    if not is_tactical:
        # King advantage bonus
        red_kings = sum(row.count(RED_KING) for row in board)
        white_kings = sum(row.count(WHITE_KING) for row in board)
        if red_kings > 0 and white_kings == 0:
            pos_score += 0.5 * red_kings
        elif white_kings > 0 and red_kings == 0:
            pos_score -= 0.5 * white_kings
            
    return (mat_score * MATERIAL_MULTIPLIER) + pos_score
