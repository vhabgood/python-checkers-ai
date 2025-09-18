# engine/search.py
import logging
from .constants import RED, WHITE

search_logger = logging.getLogger('search')

# Transposition Table
transposition_table = {}

def clear_transposition_table():
    global transposition_table
    transposition_table = {}

def minimax(board, depth, alpha, beta, evaluate_func):
    """
    Minimax with Alpha-Beta Pruning and a Transposition Table.
    """
    # Use the pre-computed Zobrist hash from the board object
    alpha_orig = alpha
    hash_key = board.get_hash()

    # --- Transposition Table Lookup ---
    if hash_key in transposition_table:
        entry = transposition_table[hash_key]
        if entry['depth'] >= depth:
            if entry['flag'] == 'EXACT':
                return entry['score'], entry['best_move']
            elif entry['flag'] == 'LOWERBOUND':
                alpha = max(alpha, entry['score'])
            elif entry['flag'] == 'UPPERBOUND':
                beta = min(beta, entry['score'])
            
            if alpha >= beta:
                return entry['score'], entry['best_move']

    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), None

    best_move = None
    all_moves = board.get_all_move_sequences(board.turn)
    if not all_moves:
        return evaluate_func(board), None

    if board.turn == WHITE: # Maximizing player
        max_eval = float('-inf')
        for path in all_moves:
            move_board = board.apply_move(path)
            evaluation, _ = minimax(move_board, depth - 1, alpha, beta, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_move = path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        score = max_eval
    else: # Minimizing player
        min_eval = float('inf')
        for path in all_moves:
            move_board = board.apply_move(path)
            evaluation, _ = minimax(move_board, depth - 1, alpha, beta, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_move = path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        score = min_eval

    # --- Transposition Table Store ---
    flag = 'EXACT'
    if score <= alpha_orig:
        flag = 'UPPERBOUND'
    elif score >= beta:
        flag = 'LOWERBOUND'
    
    transposition_table[hash_key] = {'score': score, 'depth': depth, 'flag': flag, 'best_move': best_move}
    
    return score, best_move

def get_ai_move_analysis(board, max_depth, color_to_move, evaluate_func):
    """
    Main entry point for the AI.
    """
    search_logger.info(f"--- GET AI MOVE (color: {color_to_move}, depth: {max_depth}) ---")
    clear_transposition_table() # Clear the table for each new move
    
    score, best_move = minimax(board, max_depth, float('-inf'), float('inf'), evaluate_func)

    if best_move is None:
        search_logger.warning(f"Minimax returned no best move for {color_to_move}.")
        # If no move is found, pick the first legal one as a fallback
        all_moves = board.get_all_move_sequences(color_to_move)
        if all_moves:
            return all_moves[0], []
        return None, []
        
    search_logger.info(f"Best move for {color_to_move} is {best_move} with score {score:.2f}")
    return best_move, []
