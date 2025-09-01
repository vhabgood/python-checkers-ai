# engine/search.py
import logging
import copy
from .constants import RED, WHITE, COORD_TO_ACF

logger = logging.getLogger('board')

def get_all_move_sequences(board, color):
    """
    The single, authoritative function for generating all legal move sequences for a given color.
    """
    all_paths = []
    forced_jumps_found = False

    for piece in board.get_all_pieces(color):
        jumps = board._get_moves_for_piece(piece, find_jumps=True)
        if jumps:
            forced_jumps_found = True
            start_pos = (piece.row, piece.col)
            for end_pos in jumps:
                initial_path = [start_pos, end_pos]
                all_paths.extend(_find_all_paths_from(board, initial_path))

    if forced_jumps_found:
        for path in all_paths:
            yield path
        return

    for piece in board.get_all_pieces(color):
        slides = board._get_moves_for_piece(piece, find_jumps=False)
        if slides:
            start_pos = (piece.row, piece.col)
            for end_pos in slides:
                yield [start_pos, end_pos]

def _find_all_paths_from(original_board, current_path):
    """
    A recursive helper to find all possible multi-jump extensions from a given path.
    """
    paths = []
    temp_board = copy.deepcopy(original_board)
    start_pos = current_path[0]
    piece_to_move = temp_board.get_piece(start_pos[0], start_pos[1])

    if piece_to_move == 0:
        return [current_path]

    captured_pieces = []
    for i in range(len(current_path) - 1):
        p_start, p_end = current_path[i], current_path[i+1]
        mid_row, mid_col = (p_start[0] + p_end[0]) // 2, (p_start[1] + p_end[1]) // 2
        captured = temp_board.get_piece(mid_row, mid_col)
        if captured: captured_pieces.append(captured)
    
    if captured_pieces:
        temp_board._remove(captured_pieces)

    final_pos = current_path[-1]
    temp_board.move(piece_to_move, final_pos[0], final_pos[1])
    more_jumps = temp_board._get_moves_for_piece(piece_to_move, find_jumps=True)

    if not more_jumps:
        paths.append(current_path)
    else:
        for next_pos in more_jumps:
            new_path = current_path + [next_pos]
            paths.extend(_find_all_paths_from(original_board, new_path))
            
    return paths

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    MODIFIED MINIMAX: Now returns a list of move segments (a list of lists)
    to avoid the phantom move bug.
    """
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    color_to_move = board.turn
    best_move_sequence = []

    if maximizing_player:
        max_eval = float('-inf')
        for path in get_all_move_sequences(board, color_to_move):
            move_board = board.apply_move(path)
            evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                # Create a new sequence: [current_move, next_move, next_next_move, ...]
                best_move_sequence = [path] + subsequent_sequence
            alpha = max(alpha, evaluation)
            if beta <= alpha: break
        return max_eval, best_move_sequence
    else: # Minimizing player
        min_eval = float('inf')
        for path in get_all_move_sequences(board, color_to_move):
            move_board = board.apply_move(path)
            evaluation, subsequent_sequence = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_move_sequence = [path] + subsequent_sequence
            beta = min(beta, evaluation)
            if beta <= alpha: break
        return min_eval, best_move_sequence

def get_ai_move_analysis(board, depth, color_to_move, evaluate_func):
    """
    MODIFIED AI ANALYSIS: Correctly processes the list of move segments and
    filters for unique moves before analysis.
    """
    is_maximizing = color_to_move == WHITE
    
    # Filter for unique moves to prevent duplicate analysis
    possible_moves_raw = get_all_move_sequences(board, color_to_move)
    seen_moves = set()
    possible_moves = []
    for move in possible_moves_raw:
        move_tuple = tuple(tuple(coord) for coord in move)
        if move_tuple not in seen_moves:
            seen_moves.add(move_tuple)
            possible_moves.append(move)

    if not possible_moves: return [], []

    all_scored_moves = []
    for move_path in possible_moves:
        move_board = board.apply_move(move_path)
        score, subsequent_sequence = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        
        full_sequence_for_display = [move_path] + subsequent_sequence
        
        all_scored_moves.append((score, full_sequence_for_display, move_path))

    if not all_scored_moves: return [], []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    best_path_for_execution = all_scored_moves[0][2]
    
    top_5_for_display = []
    for score, sequence, _ in all_scored_moves[:5]:
        top_5_for_display.append((score, sequence))
    
    return best_path_for_execution, top_5_for_display
