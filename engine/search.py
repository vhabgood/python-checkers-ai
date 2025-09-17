# engine/search.py
import logging
import copy
from .constants import RED, WHITE, ROWS, COLS

logger = logging.getLogger('board')

# ======================================================================================
# --- History Heuristic Table (Unchanged) ---
# ======================================================================================
history_table = [[[[0] * COLS for _ in range(ROWS)] for _ in range(COLS)] for _ in range(ROWS)]

def clear_history_table():
    """Resets all history scores to zero before a new search begins."""
    global history_table
    history_table = [[[[0] * COLS for _ in range(ROWS)] for _ in range(COLS)] for _ in range(ROWS)]

# ======================================================================================
# --- Core Search Algorithms (Unchanged) ---
# ======================================================================================
def quiescence_search(board, alpha, beta, maximizing_player, evaluate_func):
    """A specialized search that correctly handles forced captures."""
    if board.winner() is not None:
        return evaluate_func(board), []

    color_to_move = board.turn
    capture_moves = [path for path in board.get_all_move_sequences(color_to_move) if abs(path[0][0] - path[1][0]) == 2]

    if not capture_moves:
        return evaluate_func(board), []

    best_move_sequence = []
    
    if maximizing_player:
        max_eval = float('-inf')
        for path in capture_moves:
            move_board = board.apply_move(path)
            score, subsequent_sequence = quiescence_search(move_board, alpha, beta, not maximizing_player, evaluate_func)
            if score > max_eval: max_eval = score; best_move_sequence = [path] + subsequent_sequence
            alpha = max(alpha, max_eval)
            if beta <= alpha: break
        return max_eval, best_move_sequence
    else: # Minimizing player
        min_eval = float('inf')
        for path in capture_moves:
            move_board = board.apply_move(path)
            score, subsequent_sequence = quiescence_search(move_board, alpha, beta, not maximizing_player, evaluate_func)
            if score < min_eval: min_eval = score; best_move_sequence = [path] + subsequent_sequence
            beta = min(beta, min_eval)
            if beta <= alpha: break
        return min_eval, best_move_sequence

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """The main search function, now upgraded with a more robust PVS/LMR hybrid."""
    if board.winner() is not None:
        score = evaluate_func(board)
        return (score - depth) if score > 0 else (score + depth), []
        
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
                history_table[path[0][0]][path[0][1]][path[-1][0]][path[-1][1]] += depth * depth
                break
        return min_eval, best_move_sequence

# ======================================================================================
# --- REWRITTEN: Top-Level AI Interface with a Stable, Two-Pass Aspiration Search ---
# ======================================================================================

def get_ai_move_analysis(board, max_depth, color_to_move, evaluate_func):
    """
    Initiates the AI's thinking process using iterative deepening and a stable,
    two-pass aspiration window implementation.
    """
    is_maximizing = color_to_move == WHITE
    clear_history_table()
    
    all_sequences = board.get_all_move_sequences(color_to_move)
    captures = [p for p in all_sequences if abs(p[0][0]-p[1][0])==2]
    quiet_moves = [p for p in all_sequences if abs(p[0][0]-p[1][0])!=2]
    possible_moves = captures + quiet_moves

    if not possible_moves: return None, []

    best_path_for_execution = possible_moves[0]
    all_scored_moves_final = []
    
    ASPIRATION_WINDOW_DELTA = 0.5
    last_score = 0
    
    # --- Iterative Deepening Loop ---
    for depth in range(1, max_depth + 1):
        
        # --- Pass 1: The Fast "Scout" Search ---
        alpha, beta = last_score - ASPIRATION_WINDOW_DELTA, last_score + ASPIRATION_WINDOW_DELTA
        
        all_scored_moves_current_depth = []
        for move_path in possible_moves:
            move_board = board.apply_move(move_path)
            score, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, not is_maximizing, evaluate_func)
            all_scored_moves_current_depth.append((score, [move_path] + subsequent_sequence, move_path))
            
        all_scored_moves_current_depth.sort(key=lambda x: x[0], reverse=is_maximizing)
        current_best_score = all_scored_moves_current_depth[0][0]

        # --- Pass 2: The Definitive Re-Search (only if needed) ---
        if current_best_score <= alpha or current_best_score >= beta:
            logger.warning(f"Aspiration window failed at depth {depth}. Re-searching with full window.")
            all_scored_moves_current_depth = [] # Clear the failed results
            alpha, beta = float('-inf'), float('inf') # Use a full window
            
            for move_path in possible_moves:
                move_board = board.apply_move(move_path)
                score, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, not is_maximizing, evaluate_func)
                all_scored_moves_current_depth.append((score, [move_path] + subsequent_sequence, move_path))
            
            all_scored_moves_current_depth.sort(key=lambda x: x[0], reverse=is_maximizing)

        if not all_scored_moves_current_depth: break
        
        possible_moves = [move for _, _, move in all_scored_moves_current_depth]
        best_path_for_execution = all_scored_moves_current_depth[0][2]
        last_score = all_scored_moves_current_depth[0][0]
        
        all_scored_moves_final = all_scored_moves_current_depth
        
    top_5_for_display = [(score, seq) for score, seq, _ in all_scored_moves_final[:5]]
    return best_path_for_execution, top_5_for_display


