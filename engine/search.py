# engine/search.py
from .constants import RED, WHITE
import logging

logger = logging.getLogger('board')

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    """
    The top-level AI function. Returns the best move and top 5 analysis lines.
    """
    is_maximizing = ai_color == WHITE
    
    # Use the new, authoritative generator from the board class
    possible_moves = list(board.get_all_next_board_states(ai_color))

    if not possible_moves:
        logger.debug("AI SEARCH: No possible moves found.")
        return [], []

    all_scored_moves = []
    for move_path, move_board in possible_moves:
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_path_for_display = move_path + subsequent_path
        all_scored_moves.append((score, full_path_for_display, move_path))
    
    if not all_scored_moves:
        return [], []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    best_path_for_execution = all_scored_moves[0][2] 
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves[:5]]
    
    logger.debug(f"AI SEARCH: Best path chosen for execution: {best_path_for_execution}")

    return best_path_for_execution, top_5_for_display

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    The core recursive search algorithm.
    """
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    best_path = []
    color_to_move = WHITE if maximizing_player else RED
    
    if maximizing_player:
        max_eval = float('-inf')
        # The generator now provides the final board state of any multi-jump sequence
        for path, move_board in board.get_all_next_board_states(color_to_move):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_path = path + subsequent_path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval, best_path
    else: # Minimizing player
        min_eval = float('inf')
        for path, move_board in board.get_all_next_board_states(color_to_move):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_path

