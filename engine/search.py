# engine/search.py
import logging
from .constants import RED, WHITE, ROWS, COLS

search_logger = logging.getLogger('search')

# --- Transposition Table ---
transposition_table = {}

# --- History Heuristic Table ---
# This table stores scores for moves that have caused cutoffs.
# The format is [from_row][from_col][to_row][to_col]
history_table = [[[[0] * COLS for _ in range(ROWS)] for _ in range(COLS)] for _ in range(ROWS)]

def clear_search_tables():
    """Resets both the transposition table and the history heuristic table."""
    global transposition_table, history_table
    transposition_table = {}
    history_table = [[[[0] * COLS for _ in range(ROWS)] for _ in range(COLS)] for _ in range(ROWS)]

def pvs_search(board, depth, alpha, beta, evaluate_func):
    """
    Principal Variation Search (PVS) with a Transposition Table and History Heuristic.
    """
    hash_key = board.get_hash()
    alpha_orig = alpha

    # --- Transposition Table Lookup ---
    if hash_key in transposition_table and transposition_table[hash_key]['depth'] >= depth:
        entry = transposition_table[hash_key]
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

    # --- Move Ordering using History Heuristic ---
    all_moves.sort(key=lambda m: history_table[m[0][0]][m[0][1]][m[-1][0]][m[-1][1]], reverse=True)

    is_pv_node = True
    for move_path in all_moves:
        move_board = board.apply_move(move_path)
        
        # Determine the sign for the recursive call based on whose turn it is
        sign = -1 if board.turn == WHITE else 1
        
        if is_pv_node:
            score, _ = pvs_search(move_board, depth - 1, -beta, -alpha, evaluate_func)
            score = -score
        else:
            score, _ = pvs_search(move_board, depth - 1, -alpha - 1, -alpha, evaluate_func)
            score = -score
            if alpha < score < beta:
                search_logger.debug(f"PVS re-search at depth {depth}")
                score, _ = pvs_search(move_board, depth - 1, -beta, -score, evaluate_func)
                score = -score

        if score > alpha:
            alpha = score
            best_move = move_path
            is_pv_node = False
        
        if alpha >= beta:
            # --- Update History Heuristic Table on Cutoff ---
            # We reward moves that cause a cutoff with a score based on the depth
            history_table[move_path[0][0]][move_path[0][1]][move_path[-1][0]][move_path[-1][1]] += depth * depth
            break

    # --- Transposition Table Store ---
    flag = 'EXACT'
    if alpha <= alpha_orig:
        flag = 'UPPERBOUND'
    elif alpha >= beta:
        flag = 'LOWERBOUND'
    
    transposition_table[hash_key] = {'score': alpha, 'depth': depth, 'flag': flag, 'best_move': best_move}
    
    return alpha, best_move

def get_ai_move_analysis(board, max_depth, color_to_move, evaluate_func):
    """
    Top-level AI interface using Aspiration Windows around PVS.
    """
    search_logger.info(f"--- GET AI MOVE (color: {color_to_move}, depth: {max_depth}) ---")
    clear_search_tables()

    # --- Aspiration Window Logic ---
    # Widened the window from 25.0 to 40.0 for more robust initial searches.
    ASPIRATION_WINDOW_SIZE = 40.0
    
    score_guess, _ = pvs_search(board, max_depth - 2, float('-inf'), float('inf'), evaluate_func)

    alpha = score_guess - ASPIRATION_WINDOW_SIZE
    beta = score_guess + ASPIRATION_WINDOW_SIZE
    
    search_logger.debug(f"Aspiration window initial guess: {score_guess:.2f}, window: [{alpha:.2f}, {beta:.2f}]")

    score, best_move = pvs_search(board, max_depth, alpha, beta, evaluate_func)

    if score <= alpha:
        search_logger.warning("Aspiration search failed low. Re-searching with wider window.")
        score, best_move = pvs_search(board, max_depth, float('-inf'), score, evaluate_func)
    elif score >= beta:
        search_logger.warning("Aspiration search failed high. Re-searching with wider window.")
        score, best_move = pvs_search(board, max_depth, score, float('inf'), evaluate_func)

    if best_move is None:
        search_logger.error(f"Search returned no best move for {color_to_move}. Falling back to first legal move.")
        all_moves = board.get_all_move_sequences(color_to_move)
        return (all_moves[0], []) if all_moves else (None, [])
        
    search_logger.info(f"Best move found with score {score:.2f}")
    return best_move, []
