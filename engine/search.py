# engine/search.py
import logging
import copy
from .constants import RED, WHITE

logger = logging.getLogger('board')

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    color_to_move = board.turn
    best_move_sequence = []

    if maximizing_player:
        max_eval = float('-inf')
        for path in board.get_all_move_sequences(color_to_move):
            move_board = board.apply_move(path)
            evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_move_sequence = [path] + subsequent_sequence
            alpha = max(alpha, evaluation)
            if beta <= alpha: break
        return max_eval, best_move_sequence
    else: # Minimizing player
        min_eval = float('inf')
        for path in board.get_all_move_sequences(color_to_move):
            move_board = board.apply_move(path)
            evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_move_sequence = [path] + subsequent_sequence
            beta = min(beta, evaluation)
            if beta <= alpha: break
        return min_eval, best_move_sequence

def get_ai_move_analysis(board, depth, color_to_move, evaluate_func):
    is_maximizing = color_to_move == WHITE
    
    possible_moves = list(board.get_all_move_sequences(color_to_move))

    if not possible_moves: return None, []

    all_scored_moves = []
    for move_path in possible_moves:
        move_board = board.apply_move(move_path)
        score, subsequent_sequence = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_sequence_for_display = [move_path] + subsequent_sequence
        all_scored_moves.append((score, full_sequence_for_display, move_path))

    if not all_scored_moves: return None, []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    best_path_for_execution = all_scored_moves[0][2]
    top_5_for_display = [(score, seq) for score, seq, _ in all_scored_moves[:5]]
    
    return best_path_for_execution, top_5_for_display
