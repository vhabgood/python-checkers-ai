# engine/evaluation.py
from .constants import *
from .board import Board

def evaluate_board_static(board, turn_to_move):
    """
    Calculates the static evaluation of a given board state.
    This is the "brain" of the AI.
    """
    gs = Board(board_state=board, turn=turn_to_move)
    red_moves = gs.get_all_possible_moves(RED)
    white_moves = gs.get_all_possible_moves(WHITE)
    
    red_jumps = any(abs(s[0] - e[0]) == 2 for s, e in red_moves)
    white_jumps = any(abs(s[0] - e[0]) == 2 for s, e in white_moves)
    is_tactical = red_jumps or white_jumps

    mat_score, pos_score = 0, 0
    
    # Define positional bonuses
    CENTER_MAN_BONUS = 0.05
    CENTER_KING_BONUS = 0.1
    BRIDGEHEAD_BONUS = 0.1
    DOG_BONUS = 0.05
    KING_MOBILITY_BONUS = 0.02
    MAN_MOBILITY_BONUS = 0.01

    red_kings = sum(row.count(RED_KING) for row in board)
    white_kings = sum(row.count(WHITE_KING) for row in board)

    for r, row in enumerate(board):
        for c, piece in enumerate(row):
            if piece == EMPTY:
                continue
            
            is_red = piece.lower() == RED
            
            # 1. Material Score (Always counted)
            mat_score += PIECE_VALUES[piece] if is_red else -PIECE_VALUES[piece]
            
            # 2. Positional Score (Only apply nuanced details in quiet positions)
            if not is_tactical:
                pps = 0 # per-piece-score
                if piece.isupper(): # King positional logic
                    if r in {3,4} and c in {2,3,4,5}: pps += CENTER_KING_BONUS
                else: # Man positional logic
                    # Bridgehead bonus for safely reaching the other side
                    if (is_red and r in {4,5}) or (not is_red and r in {2,3}): pps += BRIDGEHEAD_BONUS
                    # Center control for men
                    if r in {2,3,4,5} and c in {2,3,4,5}: pps += CENTER_MAN_BONUS
                    # Dog / Triangle bonus for defensive structure
                    if is_red:
                        if r > 0 and ((c > 0 and board[r-1][c-1].lower()=='r') or (c < 7 and board[r-1][c+1].lower()=='r')): pps += DOG_BONUS
                    else: # White
                        if r < 7 and ((c > 0 and board[r+1][c-1].lower()=='w') or (c < 7 and board[r+1][c+1].lower()=='w')): pps += DOG_BONUS
                
                pos_score += pps if is_red else -pps

    if not is_tactical:
        # Safe mobility bonus, calculated once for the whole board
        pos_score += (len(red_moves) * MAN_MOBILITY_BONUS)
        pos_score -= (len(white_moves) * MAN_MOBILITY_BONUS)
        # Extra bonus for king mobility
        pos_score += (len([m for m in red_moves if board[m[0][0]][m[0][1]].isupper()]) * KING_MOBILITY_BONUS)
        pos_score -= (len([m for m in white_moves if board[m[0][0]][m[0][1]].isupper()]) * KING_MOBILITY_BONUS)

        # King advantage bonus
        if red_kings > 0 and white_kings == 0:
            pos_score += 0.5 * red_kings
        elif white_kings > 0 and red_kings == 0:
            pos_score -= 0.5 * white_kings
            
    return (mat_score * MATERIAL_MULTIPLIER) + pos_score
