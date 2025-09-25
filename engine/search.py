# engine/search.py
import logging
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF
import copy
from . import egdb # Import our egdb module

search_logger = logging.getLogger('search')

# --- Global variables for search ---
transposition_table = {}
killer_moves = [[(None, None)] * 2 for _ in range(15)]
principal_variation_table = {}

# --- EGDB Driver Initialization ---
egdb_driver = egdb.EGDBDriver()

def quiescence_search(board, alpha, beta, evaluate_func):
    """
    A specialized search that only explores capture sequences from a given position
    to ensure the final evaluation is based on a "quiet" board state.
    """
    stand_pat_score = evaluate_func(board)
    if stand_pat_score >= beta:
        return beta, None
    if alpha < stand_pat_score:
        alpha = stand_pat_score

    # Only generate and look at capture moves
    moves = _get_all_moves_for_color(board, None, [])
    is_jump = any(abs(move[0][0] - move[1][0]) == 2 for move in moves) if moves else False
    
    if not is_jump:
        return alpha, None # If no captures, return the static evaluation

    for move in moves:
        move_board = board.apply_move(move)
        score, _ = quiescence_search(move_board, -beta, -alpha, evaluate_func)
        score = -score
        
        if score >= beta:
            return beta, None
        if score > alpha:
            alpha = score
            
    return alpha, None

def _format_move_for_log(path):
    if not path: return "None"
    sep = 'x' if abs(path[0][0] - path[1][0]) == 2 else '-'
    return sep.join(str(COORD_TO_ACF.get(pos, "??")) for pos in path)

def clear_search_data():
    global transposition_table, killer_moves, principal_variation_table
    transposition_table, killer_moves, principal_variation_table = {}, [[(None, None)] * 2 for _ in range(15)], {}

def _get_all_moves_for_color(board, pv_move, killers):
    # ... (This function remains unchanged)
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
    if pv_move and pv_move in all_simple_moves: ordered_moves.append(pv_move)
    for move in killers:
        if move and move in all_simple_moves and move not in ordered_moves: ordered_moves.append(move)
    for move in all_simple_moves:
        if move not in ordered_moves: ordered_moves.append(move)
    return ordered_moves

def find_egdb_winning_move(board):
    """
    Finds a move that leads to a position recognized by the EGDB as a loss
    for the opponent. This ensures the engine stays on the winning path.
    """
    moves = _get_all_moves_for_color(board, None, [])
    winning_moves = []
    
    for move in moves:
        # Create a new board state for the position *after* our move
        next_board = board.apply_move(move)
        
        # Now, from this new position, it's the opponent's turn.
        # We probe the database to see if their position is a loss.
        result = egdb_driver.probe(next_board)
        
        # If the database says the opponent is in a losing position, this is a good move.
        if result == egdb.DB_LOSS:
            winning_moves.append(move)
            
    # We can return any of the winning moves. Returning the first one is simplest.
    if winning_moves:
        return winning_moves[0]
        
    # As a fallback, if no move leads to a direct known win (which is rare
    # in a winning endgame), just make any valid move to continue.
    return moves[0] if moves else None

def get_ai_move_analysis(board, depth, result_queue, evaluate_func):
    clear_search_data()
    
    total_pieces = board.red_left + board.white_left
    
    # --- FIX: Add a check to ensure the position has no captures before probing ---
    # The EGDB documentation explicitly forbids probing positions with pending captures.
    all_moves = _get_all_moves_for_color(board, None, [])
    is_tactical = any(abs(move[0][0] - move[1][0]) == 2 for move in all_moves) if all_moves else False

    # --- CHANGE: Target 7 pieces to match your available database files ---
    # Only probe if the piece count is in range AND it's a quiet position (no jumps).
    if total_pieces <= 8 and not is_tactical and egdb_driver.initialized:
    # --------------------------------------------------------------------------
        search_logger.info(f"Piece count ({total_pieces}) is within EGDB range. Probing...")
        result = egdb_driver.probe(board)
        
        if result in [egdb.DB_WIN, egdb.DB_LOSS, egdb.DB_DRAW]:
            search_logger.info(f"EGDB Result found: {['UNKNOWN','WIN','LOSS','DRAW'][result]}. Finding best move...")
            if result == egdb.DB_WIN:
                best_move, score = find_egdb_winning_move(board), 9999
            else:
                moves = _get_all_moves_for_color(board, None, [])
                best_move = moves[0] if moves else None
                score = -9999 if result == egdb.DB_LOSS else 0
            
            top_moves = [(best_move, score)]
            if result_queue: result_queue.put(top_moves)
            else: return score, best_move
            return

    # If no EGDB hit, proceed with the normal search
    top_moves = []
    for i in range(1, depth + 1):
        top_moves = _pvs_search_top_moves(board, i, evaluate_func)
        if top_moves:
            principal_variation_table[board.get_hash()] = top_moves[0][0]

    best_move_info = top_moves[0] if top_moves else (None, -float('inf'))
    log_move_str = _format_move_for_log(best_move_info[0])
    search_logger.debug(f"Search complete. Best move: {log_move_str} with score: {best_move_info[1]:.4f}")
    
    if result_queue: result_queue.put(top_moves)
    else: return best_move_info[1], best_move_info[0]

def _pvs_search_top_moves(board, depth, evaluate_func):
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
    hash_key = board.get_hash()
    if hash_key in transposition_table and transposition_table[hash_key]['depth'] >= depth:
        entry = transposition_table[hash_key]
        if entry['flag'] == 'EXACT': return entry['score'], entry['best_move']
        elif entry['flag'] == 'LOWERBOUND': alpha = max(alpha, entry['score'])
        elif entry['flag'] == 'UPPERBOUND': beta = min(beta, entry['score'])
        if alpha >= beta: return entry['score'], entry['best_move']
    if depth <= 0 or board.winner() is not None:
        return quiescence_search(board, alpha, beta, evaluate_func)
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
