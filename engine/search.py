# engine/search.py
import logging
import copy
from .constants import RED, WHITE, COORD_TO_ACF

# Get the same logger used by the board for consistent output
logger = logging.getLogger('board')

def get_all_move_sequences(board, color):
    """
    The single, authoritative function for generating all legal move sequences for a given color.
    It correctly handles the mandatory jump rule by separating the logic for jumps and slides.
    """
    all_paths = []
    forced_jumps_found = False

    # First, iterate through every piece to see if any jumps are possible.
    for piece in board.get_all_pieces(color):
        # Check for initial jumps from the original board state.
        jumps = board._get_moves_for_piece(piece, find_jumps=True)
        if jumps:
            forced_jumps_found = True
            start_pos = (piece.row, piece.col)
            # For each initial jump, recursively find all possible multi-jump extensions.
            for end_pos in jumps:
                initial_path = [start_pos, end_pos]
                # The recursive helper function will explore from this starting jump.
                all_paths.extend(_find_all_paths_from(board, initial_path))

    # If jumps were found, the rules of checkers state you MUST make a jump.
    # Therefore, we completely ignore any non-jump "slide" moves.
    if forced_jumps_found:
        logger.debug(f"MOVE_GEN: Jumps are mandatory. Returning {len(all_paths)} jump sequences.")
        for path in all_paths:
            yield path
        return

    # If we get here, it means no jumps were found for any piece.
    # Now, we can generate all the simple, non-jump "slide" moves.
    logger.debug("MOVE_GEN: No jumps found. Generating all slide moves.")
    for piece in board.get_all_pieces(color):
        slides = board._get_moves_for_piece(piece, find_jumps=False)
        if slides:
            start_pos = (piece.row, piece.col)
            for end_pos in slides:
                # A slide is always a simple path of length 2.
                yield [start_pos, end_pos]

def _find_all_paths_from(original_board, current_path):
    """
    A recursive helper function to find all possible multi-jump extensions from a given path.
    This function simulates the path on a temporary board to find the next move.
    """
    paths = []
    
    # Simulate the current jump sequence on a fresh, temporary board.
    temp_board = copy.deepcopy(original_board)
    
    start_pos = current_path[0]
    piece_to_move = temp_board.get_piece(start_pos[0], start_pos[1])

    # Safety check: If the piece doesn't exist, the path is invalid.
    if piece_to_move == 0:
        return [current_path] # End the search here.

    # Apply the move and remove captured pieces on the temporary board.
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

    # After simulating the path, check for MORE jumps from the final position.
    more_jumps = temp_board._get_moves_for_piece(piece_to_move, find_jumps=True)

    # If there are no more jumps, this path is a complete move. We're done.
    if not more_jumps:
        paths.append(current_path)
    else:
        # If there are more jumps, recursively call this function for each new jump.
        for next_pos in more_jumps:
            new_path = current_path + [next_pos]
            # Add the complete multi-jump sequences found by the recursive call.
            paths.extend(_find_all_paths_from(original_board, new_path))
            
    return paths

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    The core recursive search algorithm. This definitive version removes hardcoded
    colors and correctly generates moves for the player whose turn it is on the
    current board state.
    """
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    # Determine which color we are generating moves for based on the board's state.
    color_to_move = board.turn

    if maximizing_player:
        max_eval = float('-inf')
        best_path = []
        # Generate moves for the correct color.
        for path in get_all_move_sequences(board, color_to_move):
            move_board = board.apply_move(path)
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_path = path + subsequent_path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval, best_path
    else:  # Minimizing player
        min_eval = float('inf')
        best_path = []
        # Generate moves for the correct color.
        for path in get_all_move_sequences(board, color_to_move):
            move_board = board.apply_move(path)
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_path

def get_ai_move_analysis(board, depth, color_to_move, evaluate_func):
    """
    The top-level AI function. This remains unchanged and is correct.
    """
    is_maximizing = color_to_move == WHITE
    possible_moves = list(get_all_move_sequences(board, color_to_move))

    if not possible_moves:
        logger.warning(f"AI ANALYSIS: No possible moves found for {'White' if is_maximizing else 'Red'}.")
        return [], []

    all_scored_moves = []
    for move_path in possible_moves:
        move_board = board.apply_move(move_path)
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_path_for_display = move_path + subsequent_path
        all_scored_moves.append((score, full_path_for_display, move_path))

    if not all_scored_moves:
        logger.error("AI ANALYSIS: Moves were possible, but none were scored. THIS IS A BUG.")
        return [], []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    best_path_for_execution = all_scored_moves[0][2]
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves]
    
    return best_path_for_execution, top_5_for_display[:5]
