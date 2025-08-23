# engine/search.py
"""
Contains the AI's search algorithm (minimax with alpha-beta pruning).
"""
from .constants import RED, WHITE
import copy

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    """
    Analyzes the board to find the best move for the AI.
    Returns the best move path and a list of the top 5 move paths with their scores.
    """
    is_maximizing = True if ai_color == WHITE else False
    
    all_scored_moves = []
    
    for move_path, move_board in get_all_moves(board, ai_color):
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_path = move_path + subsequent_path
        all_scored_moves.append((score, full_path))
            
    if not all_scored_moves:
        return None, []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)

    best_path = all_scored_moves[0][1]
    top_5_paths = all_scored_moves[:5]

    return best_path, top_5_paths

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    Recursive minimax algorithm. Returns the best score and the path to get there.
    """
    if depth == 0:
        # Once max depth is reached, run a quiescence search to stabilize the evaluation
        score, path = quiescence_search(board, 4, alpha, beta, maximizing_player, evaluate_func)
        return score, path

    valid_moves = board.get_all_valid_moves_for_color(board.turn)
    if not valid_moves:
        return evaluate_func(board), []

    best_path = []
    if maximizing_player:
        max_eval = float('-inf')
        for path, move_board in get_all_moves(board, WHITE):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_path = path + subsequent_path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break # Alpha-beta pruning
        return max_eval, best_path
    else: # Minimizing player
        min_eval = float('inf')
        for path, move_board in get_all_moves(board, RED):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break # Alpha-beta pruning
        return min_eval, best_path

def quiescence_search(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    A recursive search that only considers capture moves to stabilize the evaluation.
    """
    stand_pat_eval = evaluate_func(board)

    if depth == 0:
        return stand_pat_eval, []

    if maximizing_player:
        if stand_pat_eval >= beta: return stand_pat_eval, []
        alpha = max(alpha, stand_pat_eval)
    else:
        if stand_pat_eval <= alpha: return stand_pat_eval, []
        beta = min(beta, stand_pat_eval)

    # In quiescence, we only care about jumps.
    all_moves = board.get_all_valid_moves_for_color(board.turn)
    is_jump = any(abs(start[0] - end[0]) > 1 for start, ends in all_moves.items() for end in ends)

    if not is_jump:
        return stand_pat_eval, []

    best_path = []
    if maximizing_player:
        for path, move_board in get_all_moves(board, WHITE):
            score, subsequent_path = quiescence_search(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if score > alpha:
                alpha = score
                best_path = path + subsequent_path
            if beta <= alpha:
                break
        return alpha, best_path
    else: # Minimizing player
        for path, move_board in get_all_moves(board, RED):
            score, subsequent_path = quiescence_search(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if score < beta:
                beta = score
                best_path = path + subsequent_path
            if beta <= alpha:
                break
        return beta, best_path

def get_all_moves(board, color):
    """
    Generator that yields a move path (list of coordinates) and a new Board object.
    """
    for start_pos, end_positions in board.get_all_valid_moves_for_color(color).items():
        for end_pos in end_positions:
            temp_board = copy.deepcopy(board)
            piece = temp_board.get_piece(start_pos[0], start_pos[1])
            temp_board.move(piece, end_pos[0], end_pos[1])
            
            is_jump = abs(start_pos[0] - end_pos[0]) > 1
            if is_jump:
                yield from _get_jump_sequences(temp_board, [start_pos, end_pos])
            else:
                temp_board.turn = RED if color == WHITE else WHITE
                yield [start_pos, end_pos], temp_board

def _get_jump_sequences(board, path):
    """
    Recursive helper to find all possible multi-jump sequences.
    """
    current_pos = path[-1]
    more_jumps = board._get_jumps_for_piece(current_pos[0], current_pos[1])

    if not more_jumps:
        yield path, board
        return

    for next_pos in more_jumps:
        temp_board = copy.deepcopy(board)
        temp_piece = temp_board.get_piece(current_pos[0], current_pos[1])
        temp_board.move(temp_piece, next_pos[0], next_pos[1])
        
        new_path = path + [next_pos]
        yield from _get_jump_sequences(temp_board, new_path)
