# engine/search.py
import logging
import copy
from .constants import RED, WHITE, ROWS, COLS

logger = logging.getLogger('search_detail')

# ======================================================================================
# --- History Heuristic Table (Unchanged) ---
# ======================================================================================
history_table = [[[[0] * COLS for _ in range(ROWS)] for _ in range(COLS)] for _ in range(ROWS)]
def clear_history_table():
    global history_table
    history_table = [[[[0] * COLS for _ in range(ROWS)] for _ in range(COLS)] for _ in range(ROWS)]

# ======================================================================================
# --- Core Search Algorithms ---
# ======================================================================================
def quiescence_search(board, alpha, beta, maximizing_player, evaluate_func):
    """A specialized search that correctly handles forced captures."""
    # (This function is correct and unchanged)
    pass

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    The main search function, now upgraded with Futility Pruning.
    """
    if board.winner() is not None:
        score = evaluate_func(board)
        return (score - depth) if score > 0 else (score + depth), []
        
    # --- NEW: Futility Pruning ---
    # If we are at a shallow depth and the static evaluation is already much worse
    # than the best score we've found so far (alpha), then this position is likely
    # "futile" and we can prune it early to save time.
    FUTILITY_MARGIN = 0.3 # A tunable parameter
    if depth <= 2:
        eval_score = evaluate_func(board)
        if maximizing_player and eval_score + FUTILITY_MARGIN * depth <= alpha:
            return alpha, []
        if not maximizing_player and eval_score - FUTILITY_MARGIN * depth >= beta:
            return beta, []

    if depth == 0:
        return quiescence_search(board, alpha, beta, maximizing_player, evaluate_func)

    best_move_sequence = []
    
    all_moves = board.get_all_move_sequences(board.turn)
    all_moves.sort(key=lambda path: history_table[path[0][0]][path[0][1]][path[-1][0]][path[-1][1]], reverse=True)

    if not all_moves:
        return evaluate_func(board), []

    PATH_TO_VICTORY_BONUS = 50.0 

    if maximizing_player:
        max_eval = float('-inf')
        for i, path in enumerate(all_moves):
            move_board = board.apply_move(path)
            evaluation, subsequent_sequence = 0, []

            if i < 3:
                evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            else:
                evaluation, _ = minimax(move_board, depth - 1, alpha, alpha + 1, False, evaluate_func)
                if alpha < evaluation < beta:
                    evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)

            if evaluation > 900: evaluation += PATH_TO_VICTORY_BONUS
            if evaluation > max_eval: max_eval = evaluation; best_move_sequence = [path] + subsequent_sequence
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                is_capture = abs(path[0][0] - path[1][0]) == 2
                if not is_capture:
                    history_table[path[0][0]][path[0][1]][path[-1][0]][path[-1][1]] += depth * depth
                break
        return max_eval, best_move_sequence
    else: # Minimizing player
        min_eval = float('inf')
        for i, path in enumerate(all_moves):
            move_board = board.apply_move(path)
            evaluation, subsequent_sequence = 0, []

            if i < 3:
                evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            else:
                evaluation, _ = minimax(move_board, depth - 1, beta - 1, beta, True, evaluate_func)
                if alpha < evaluation < beta:
                    evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)

            if evaluation < -900: evaluation -= PATH_TO_VICTORY_BONUS
            if evaluation < min_eval: min_eval = evaluation; best_move_sequence = [path] + subsequent_sequence
            beta = min(beta, evaluation)
            if beta <= alpha:
                is_capture = abs(path[0][0] - path[1][0]) == 2
                if not is_capture:
                    history_table[path[0][0]][path[0][1]][path[-1][0]][path[-1][1]] += depth * depth
                break
        return min_eval, best_move_sequence

# ======================================================================================
# --- Top-Level AI Interface (Unchanged) ---
# ======================================================================================
def get_ai_move_analysis(board, max_depth, color_to_move, evaluate_func):
    # ... (This function is correct and unchanged)
    pass


