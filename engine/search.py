# engine/search.py
"""
Contains the AI's search algorithm (minimax with alpha-beta pruning).
"""
from .constants import RED, WHITE, COORD_TO_ACF
import copy

def get_ai_move_analysis(board, depth, ai_color, evaluate_func, analysis_queue=None):
    """
    Analyzes the board to find the best move for the AI.
    Returns the best move and a list of the top 5 move sequences with their scores.
    """
    is_maximizing = True if ai_color == WHITE else False
    
    all_scored_moves = []
    
    # get_all_moves now returns full jump sequences, so we iterate through them
    for move_path, move_board in get_all_moves(board, ai_color):
        score, _ = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        all_scored_moves.append((score, move_path))

        if analysis_queue:
            all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
            analysis_queue.put(all_scored_moves[:5])
            
    if not all_scored_moves:
        return None, []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)

    best_path = all_scored_moves[0][1]
    best_first_move = (best_path[0], best_path[1])
    top_5_paths = all_scored_moves[:5]

    return best_first_move, top_5_paths

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    Recursive minimax algorithm. Returns the best score and the path to get there.
    """
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

def _get_jump_sequences(board, path):
    """
    A recursive helper to find all possible multi-jump sequences from a starting point.
    """
    current_pos = path[-1]
    piece = board.get_piece(current_pos[0], current_pos[1])
    
    # If the piece was removed (e.g., in a complex undo), stop.
    if piece == 0:
        return

    more_jumps = board._get_jumps_for_piece(current_pos[0], current_pos[1])

    if not more_jumps:
        # This is the end of a jump sequence
        yield path, board
        return

    for next_pos in more_jumps:
        temp_board = copy.deepcopy(board)
        temp_piece = temp_board.get_piece(current_pos[0], current_pos[1])
        temp_board.move(temp_piece, next_pos[0], next_pos[1])
        
        new_path = path + [next_pos]
        # Continue searching for more jumps from the new position
        yield from _get_jump_sequences(temp_board, new_path)

def get_all_moves(board, color):
    """
    Generator that yields a move path and a new Board object for that move.
    Correctly handles multi-jumps by generating the full sequence.
    """
    all_valid_moves = board.get_all_valid_moves_for_color(color)
    is_jump = any(abs(start[0] - end[0]) > 1 for start, ends in all_valid_moves.items() for end in ends)

    if not is_jump:
        # If there are no jumps, yield all the simple slide moves
        for start_pos, end_positions in all_valid_moves.items():
            for end_pos in end_positions:
                temp_board = copy.deepcopy(board)
                piece = temp_board.get_piece(start_pos[0], start_pos[1])
                temp_board.move(piece, end_pos[0], end_pos[1])
                temp_board.turn = RED if color == WHITE else WHITE
                yield [start_pos, end_pos], temp_board
    else:
        # If there are jumps, generate the full jump sequences
        for start_pos, end_positions in all_valid_moves.items():
            for end_pos in end_positions:
                temp_board = copy.deepcopy(board)
                piece = temp_board.get_piece(start_pos[0], start_pos[1])
                temp_board.move(piece, end_pos[0], end_pos[1])
                
                # Start the recursive search for the rest of the sequence
                for final_path, final_board in _get_jump_sequences(temp_board, [start_pos, end_pos]):
                    final_board.turn = RED if color == WHITE else WHITE
                    yield final_path, final_board
