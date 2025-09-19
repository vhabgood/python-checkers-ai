import logging
from .constants import RED, WHITE, ROWS, COLS

search_logger = logging.getLogger('search')

transposition_table = {}
history_table = [[[[0] * COLS for _ in range(ROWS)] for _ in range(COLS)] for _ in range(ROWS)]

def clear_transposition_table():
    """Resets only the transposition table for a new search."""
    global transposition_table
    transposition_table = {}

def clear_history_table():
    """Resets only the history heuristic table for a new game."""
    global history_table
    history_table = [[[[0] * COLS for _ in range(ROWS)] for _ in range(COLS)] for _ in range(ROWS)]

def pvs_search(board, depth, alpha, beta, evaluate_func):
    hash_key = board.get_hash()
    alpha_orig = alpha

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

    all_moves.sort(key=lambda m: history_table[m[0][0]][m[0][1]][m[-1][0]][m[-1][1]], reverse=True)

    is_pv_node = True
    for move_path in all_moves:
        move_board = board.apply_move(move_path)
        
        if is_pv_node:
            score, _ = pvs_search(move_board, depth - 1, -beta, -alpha, evaluate_func)
            score = -score
        else:
            score, _ = pvs_search(move_board, depth - 1, -alpha - 1, -alpha, evaluate_func)
            score = -score
            if alpha < score < beta:
                score, _ = pvs_search(move_board, depth - 1, -beta, -score, evaluate_func)
                score = -score

        if score > alpha:
            alpha = score
            best_move = move_path
            is_pv_node = False
        
        if alpha >= beta:
            history_table[move_path[0][0]][move_path[0][1]][move_path[-1][0]][move_path[-1][1]] += depth * depth
            break

    flag = 'EXACT'
    if alpha <= alpha_orig:
        flag = 'UPPERBOUND'
    elif alpha >= beta:
        flag = 'LOWERBOUND'
    
    transposition_table[hash_key] = {'score': alpha, 'depth': depth, 'flag': flag, 'best_move': best_move}
    
    return alpha, best_move

def get_ai_move_analysis(board, max_depth, color_to_move, evaluate_func):
    clear_transposition_table() # Correctly clear only this table per move
    score, best_move = pvs_search(board, max_depth, float('-inf'), float('inf'), evaluate_func)

    if best_move is None:
        all_moves = board.get_all_move_sequences(color_to_move)
        return (all_moves[0], []) if all_moves else (None, [])
        
    return best_move, []
