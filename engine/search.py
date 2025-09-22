# engine/search.py
import logging
from .constants import RED, WHITE, ROWS, COLS
import copy

search_logger = logging.getLogger('search')
transposition_table = {}

def clear_transposition_table():
    global transposition_table
    transposition_table = {}

def _get_all_moves_for_color(board):
    all_jumps = []
    all_simple_moves = []
    search_logger.debug(f"Finding moves for {board.turn}...")
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if piece and piece.color == board.turn:
                valid_moves_for_piece = board.get_valid_moves(piece)
                if not valid_moves_for_piece: continue
                first_move = valid_moves_for_piece[0]
                if abs(first_move[0][0] - first_move[1][0]) == 2:
                    all_jumps.extend(valid_moves_for_piece)
                else:
                    all_simple_moves.extend(valid_moves_for_piece)
    moves = all_jumps if all_jumps else all_simple_moves
    search_logger.debug(f"Found {len(moves)} moves for {board.turn}")
    return moves

def pvs_search(board, depth, alpha, beta, evaluate_func):
    hash_key = board.get_hash()
    if hash_key in transposition_table and transposition_table[hash_key]['depth'] >= depth:
        entry = transposition_table[hash_key]
        if entry['flag'] == 'EXACT': return entry['score'], entry['best_move']
        elif entry['flag'] == 'LOWERBOUND': alpha = max(alpha, entry['score'])
        elif entry['flag'] == 'UPPERBOUND': beta = min(beta, entry['score'])
        if alpha >= beta: return entry['score'], entry['best_move']

    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), None

    all_move_paths = _get_all_moves_for_color(board)
    if not all_move_paths: return -float('inf'), None
    
    best_move = all_move_paths[0]
    
    for i, move_path in enumerate(all_move_paths):
        move_board = board.apply_move(move_path)
        if i == 0: # Full window search for the first move
            score, _ = pvs_search(move_board, depth - 1, -beta, -alpha, evaluate_func)
            score = -score
        else: # Null window search for subsequent moves
            score, _ = pvs_search(move_board, depth - 1, -alpha - 1, -alpha, evaluate_func)
            score = -score
            if alpha < score < beta:
                score, _ = pvs_search(move_board, depth - 1, -beta, -score, evaluate_func)
                score = -score
        if score > alpha:
            alpha = score
            best_move = move_path
        if alpha >= beta:
            break
            
    flag = 'EXACT'
    if alpha <= -float('inf'): flag = 'UPPERBOUND'
    elif alpha >= float('inf'): flag = 'LOWERBOUND'
    transposition_table[hash_key] = {'score': alpha, 'depth': depth, 'flag': flag, 'best_move': best_move}
    return alpha, best_move

def get_ai_move_analysis(board, max_depth, color_to_move, evaluate_func):
    clear_transposition_table()
    score, best_move = pvs_search(board, max_depth, -float('inf'), float('inf'), evaluate_func)
    return score, best_move
