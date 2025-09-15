# engine/search.py
import logging
import copy
from .constants import RED, WHITE

logger = logging.getLogger('board')

# ======================================================================================
# --- 1. Quiescence Search (Corrected Again) ---
# ======================================================================================

def quiescence_search(board, alpha, beta, maximizing_player, evaluate_func):
    """
    A specialized search that correctly handles forced captures. It explores
    all capture sequences until a "quiet" position (no captures) is reached
    before returning a stable evaluation.
    """
    # --- CRITICAL FIX: Check for a terminal (win/loss) node first ---
    # This handles cases where a capture sequence ends the game.
    if board.winner() is not None:
        return evaluate_func(board), []

    # --- Now, check for forced captures ---
    color_to_move = board.turn
    capture_moves = [path for path in board.get_all_move_sequences(color_to_move) if abs(path[0][0] - path[1][0]) == 2]

    # If there are no captures, this is a "quiet" position. We can return the static evaluation.
    if not capture_moves:
        return evaluate_func(board), []

    # If captures ARE available, we must explore them and ignore the static evaluation.
    best_move_sequence = []
    
    if maximizing_player:
        max_eval = float('-inf')
        for path in capture_moves:
            move_board = board.apply_move(path)
            # Recurse with quiescence_search to follow the entire capture chain
            score, subsequent_sequence = quiescence_search(move_board, alpha, beta, not maximizing_player, evaluate_func)
            if score > max_eval:
                max_eval = score
                best_move_sequence = [path] + subsequent_sequence
            alpha = max(alpha, max_eval)
            if beta <= alpha:
                break # Alpha-beta cutoff
        return max_eval, best_move_sequence
    else: # Minimizing player
        min_eval = float('inf')
        for path in capture_moves:
            move_board = board.apply_move(path)
            score, subsequent_sequence = quiescence_search(move_board, alpha, beta, not maximizing_player, evaluate_func)
            if score < min_eval:
                min_eval = score
                best_move_sequence = [path] + subsequent_sequence
            beta = min(beta, min_eval)
            if beta <= alpha:
                break # Alpha-beta cutoff
        return min_eval, best_move_sequence


# ======================================================================================
# --- 2. Main Minimax Search ---
# ======================================================================================

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    The main search function. Now includes a "Path to Victory" bonus to
    encourage simplifying into a won endgame database position.
    """
    if board.winner() is not None:
        score = evaluate_func(board)
        return (score - depth) if score > 0 else (score + depth), []
        
    if depth == 0:
        return quiescence_search(board, alpha, beta, maximizing_player, evaluate_func)

    color_to_move = board.turn
    best_move_sequence = []
    
    all_moves = board.get_all_move_sequences(color_to_move)
    if not all_moves:
        return evaluate_func(board), []

    PATH_TO_VICTORY_BONUS = 50.0 

    if maximizing_player:
        max_eval = float('-inf')
        for path in all_moves:
            move_board = board.apply_move(path)
            evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > 900: evaluation += PATH_TO_VICTORY_BONUS
            if evaluation > max_eval: max_eval = evaluation; best_move_sequence = [path] + subsequent_sequence
            alpha = max(alpha, evaluation)
            if beta <= alpha: break
        return max_eval, best_move_sequence
    else: # Minimizing player
        min_eval = float('inf')
        for path in all_moves:
            move_board = board.apply_move(path)
            evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < -900: evaluation -= PATH_TO_VICTORY_BONUS
            if evaluation < min_eval: min_eval = evaluation; best_move_sequence = [path] + subsequent_sequence
            beta = min(beta, evaluation)
            if beta <= alpha: break
        return min_eval, best_move_sequence


# ======================================================================================
# --- 3. Top-Level AI Interface ---
# ======================================================================================

def get_ai_move_analysis(board, max_depth, color_to_move, evaluate_func):
    """
    Initiates the AI's thinking process using iterative deepening and aspiration windows.
    """
    is_maximizing = color_to_move == WHITE
    possible_moves = list(board.get_all_move_sequences(color_to_move))
    if not possible_moves: return None, []

    # Start with a random best move in case the search is interrupted.
    best_move_path = possible_moves[0]
    best_sequence = []
    
    # Define the initial aspiration window size.
    ASPIRATION_WINDOW_DELTA = 0.25
    
    # Iterative deepening loop
    last_score = 0
    for depth in range(1, max_depth + 1):
        
        # --- Aspiration Window Logic ---
        alpha = last_score - ASPIRATION_WINDOW_DELTA
        beta = last_score + ASPIRATION_WINDOW_DELTA
        
        all_scored_moves = []
        
        # We must still search all root moves
        for move_path in possible_moves:
            move_board = board.apply_move(move_path)
            
            # Search with the narrow window first
            score, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, not is_maximizing, evaluate_func)
            
            # --- Handle Aspiration Search Failures ---
            # If the score is outside our window, we must re-search with a wider window.
            if score <= alpha or score >= beta:
                logger.warning(f"Aspiration search failed at depth {depth}. (Score: {score}, Window: [{alpha:.2f}, {beta:.2f}]). Re-searching.")
                # Re-search with a full window
                score, subsequent_sequence = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)

            all_scored_moves.append((score, [move_path] + subsequent_sequence, move_path))

        if not all_scored_moves: break # No moves found, stop deepening

        # Sort moves based on the latest search results
        all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
        
        # Update the best move found so far
        best_path_for_execution = all_scored_moves[0][2]
        best_sequence_for_display = all_scored_moves[0][1]
        last_score = all_scored_moves[0][0]
        
        # For the final report, we only care about the results from the max depth
        if depth == max_depth:
            top_5_for_display = [(score, seq) for score, seq, _ in all_scored_moves[:5]]
            return best_path_for_execution, top_5_for_display

    # Fallback in case loop finishes unexpectedly
    return best_move_path, [(last_score, best_sequence)]

