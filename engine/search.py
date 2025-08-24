# engine/search.py
import copy
from .constants import RED, WHITE

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    is_maximizing = ai_color == WHITE
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
    if depth == 0 or not board.get_all_valid_moves_for_color(board.turn):
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
                break
        return max_eval, best_path
    else:
        min_eval = float('inf')
        for path, move_board in get_all_moves(board, RED):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_path

def get_all_moves(board, color):
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
