# engine/search.py
import logging
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF
import copy

search_logger = logging.getLogger('search')

# --- Global variables for advanced search techniques ---
transposition_table = {}
killer_moves = [[(None, None)] * 2 for _ in range(15)]
principal_variation_table = {}

def _format_move_for_log(path):
    """Helper function to convert a move path to ACF notation for logging."""
    if not path: return "None"
    sep = 'x' if abs(path[0][0] - path[1][0]) == 2 else '-'
    return sep.join(str(COORD_TO_ACF.get(pos, "??")) for pos in path)

def clear_search_data():
    """Resets all search-related data structures."""
    global transposition_table, killer_moves, principal_variation_table
    transposition_table = {}
    killer_moves = [[(None, None)] * 2 for _ in range(15)]
    principal_variation_table = {}

def _get_all_moves_for_color(board, pv_move, killers):
    """
    Gets all legal moves and sorts them for optimal alpha-beta pruning.
    Order: PV Move -> Captures (longest first) -> Killer Moves -> Other moves.
    """
    all_jumps, all_simple_moves = [], []
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if piece and piece.color == board.turn:
                valid_moves = board.get_valid_moves(piece)
                if not valid_moves: continue
                is_jump = abs(valid_moves[0][0][0] - valid_moves[0][1][0]) == 2
                if is_jump: all_jumps.extend(valid_moves)
                else: all_simple_moves.extend(valid_moves)

    if all_jumps:
        all_jumps.sort(key=len, reverse=True)
        return all_jumps

    ordered_moves = []
    if pv_move and pv_move in all_simple_moves:
        ordered_moves.append(pv_move)
    for move in killers:
        if move and move in all_simple_moves and move not in ordered_moves:
            ordered_moves.append(move)
    for move in all_simple_moves:
        if move not in ordered_moves:
            ordered_moves.append(move)
            
    return ordered_moves

def get_ai_move_analysis(board, depth, result_queue, evaluate_func):
    """
    Top-level function that uses Iterative Deepening to find the best moves.
    """
    clear_search_data()
    
    top_moves = []
    for i in range(1, depth + 1):
        search_logger.debug(f"Starting Iterative Deepening search to depth {i}")
        top_moves = _pvs_search_top_moves(board, i, evaluate_func)
        if top_moves:
            best_move = top_moves[0][0]
            principal_variation_table[board.get_hash()] = best_move

    best_move_info = top_moves[0] if top_moves else (None, -float('inf'))
    
    # --- FIX: Use the new helper function to format the log message ---
    log_move_str = _format_move_for_log(best_move_info[0])
    search_logger.debug(f"Search complete. Best move: {log_move_str} with score: {best_move_info[1]:.4f}")
    # -----------------------------------------------------------------
    
    if result_queue:
        result_queue.put(top_moves)
    else: # For gauntlet mode
        return best_move_info[1], best_move_info[0]

def _pvs_search_top_moves(board, depth, evaluate_func):
    """
    Gets the top 5 moves by scoring each initial move with the optimized PVS search.
    """
    pv_move = principal_variation_table.get(board.get_hash())
    moves = _get_all_moves_for_color(board, pv_move, killer_moves[depth])
    if not moves: return []
    
    scored_moves = []
    for move in moves:
        move_board = board.apply_move(move)
        score, _ = _pvs_search_recursive(move_board, depth - 1, -float('inf'), float('inf'), evaluate_func, depth - 1)
        scored_moves.append((move, -score))
        
    scored_moves.sort(key=lambda item: item[1], reverse=True)
    return scored_moves[:5]

def _pvs_search_recursive(board, depth, alpha, beta, evaluate_func, ply):
    """
    High-performance PVS search with Transposition Table, PV, and Killer Move support.
    """
    hash_key = board.get_hash()
    if hash_key in transposition_table and transposition_table[hash_key]['depth'] >= depth:
        entry = transposition_table[hash_key]
        if entry['flag'] == 'EXACT': return entry['score'], entry['best_move']
        elif entry['flag'] == 'LOWERBOUND': alpha = max(alpha, entry['score'])
        elif entry['flag'] == 'UPPERBOUND': beta = min(beta, entry['score'])
        if alpha >= beta: return entry['score'], entry['best_move']

    if depth <= 0 or board.winner() is not None:
        return evaluate_func(board), None

    pv_move = principal_variation_table.get(board.get_hash())
    moves = _get_all_moves_for_color(board, pv_move, killer_moves[ply])
    if not moves: return -float('inf'), None

    best_move = moves[0]
    for i, move in enumerate(moves):
        move_board = board.apply_move(move)
        
        if i == 0:
            score, _ = _pvs_search_recursive(move_board, depth - 1, -beta, -alpha, evaluate_func, ply - 1)
            score = -score
        else:
            score, _ = _pvs_search_recursive(move_board, depth - 1, -alpha - 1, -alpha, evaluate_func, ply - 1)
            score = -score
            if alpha < score < beta:
                score, _ = _pvs_search_recursive(move_board, depth - 1, -beta, -score, evaluate_func, ply - 1)
                score = -score
        
        if score > alpha:
            alpha = score
            best_move = move
            principal_variation_table[board.get_hash()] = best_move
        
        if alpha >= beta:
            is_jump = abs(move[0][0] - move[1][0]) == 2
            if not is_jump:
                killer_moves[ply][1] = killer_moves[ply][0]
                killer_moves[ply][0] = move
            break

    flag = 'EXACT'
    if alpha <= -float('inf'): flag = 'UPPERBOUND'
    elif alpha >= beta: flag = 'LOWERBOUND'
    transposition_table[hash_key] = {'score': alpha, 'depth': depth, 'flag': flag, 'best_move': best_move}

    return alpha, best_move
