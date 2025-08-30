# engine/search.py
import logging
from .constants import RED, WHITE, COORD_TO_ACF

logger = logging.getLogger('board')

def _find_jump_paths(board, path_so_far, piece):
    """
    Recursively finds all possible multi-jump sequences for a single piece.
    It simulates jumps on a temporary board copy without changing the turn state.
    """
    last_pos = path_so_far[-1]
    
    # Simulate the path so far on a fresh copy to check for more jumps
    temp_board = copy.deepcopy(board)
    
    # Remove pieces captured along the path so far
    captured_on_path = []
    for i in range(len(path_so_far) - 1):
        p_start, p_end = path_so_far[i], path_so_far[i+1]
        mid_row, mid_col = (p_start[0] + p_end[0]) // 2, (p_start[1] + p_end[1]) // 2
        captured = temp_board.get_piece(mid_row, mid_col)
        if captured: captured_on_path.append(captured)
    temp_board._remove(captured_on_path)
    
    # Move the piece to its current position in the sequence
    temp_board.move(temp_board.get_piece(piece.row, piece.col), last_pos[0], last_pos[1])

    # Now, check for more jumps from this new position
    piece_at_last_pos = temp_board.get_piece(last_pos[0], last_pos[1])
    more_jumps = temp_board._get_moves_for_piece(piece_at_last_pos, find_jumps=True)

    # If there are no more jumps, this path is complete.
    if not more_jumps:
        yield path_so_far
        return

    # If there are more jumps, explore them recursively.
    for next_pos in more_jumps:
        new_path = path_so_far + [next_pos]
        yield from _find_jump_paths(board, new_path, piece)


def get_all_move_sequences(board, color):
    """
    The main move generation function. It correctly finds all legal move sequences
    (slides or multi-jumps) for a given color.
    """
    all_pieces = board.get_all_pieces(color)
    
    # First, check if any jumps are available for any piece.
    forced_jumps = []
    for piece in all_pieces:
        jumps = board._get_moves_for_piece(piece, find_jumps=True)
        if jumps:
            forced_jumps.append((piece, jumps))
    
    # If jumps exist, only generate jump sequences (mandatory jump rule).
    if forced_jumps:
        for piece, jumps in forced_jumps:
            for end_pos in jumps:
                # Start the recursive search for each initial jump.
                yield from _find_jump_paths(board, [ (piece.row, piece.col), end_pos ], piece)
        return

    # If no jumps are found, generate all simple slide moves.
    for piece in all_pieces:
        slides = board._get_moves_for_piece(piece, find_jumps=False)
        if slides:
            for end_pos in slides:
                yield [ (piece.row, piece.col), end_pos ]

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    if maximizing_player:
        max_eval = float('-inf')
        best_path = []
        for move_path in get_all_move_sequences(board, WHITE): # AI is WHITE
            new_board = board.apply_move(move_path)
            # CORRECTED LINE: The last parameter is now 'False'
            evaluation, path = minimax(new_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_path = move_path + path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval, best_path
    else: # Minimizing player
        min_eval = float('inf')
        best_path = []
        for move_path in get_all_move_sequences(board, RED): # Player is RED
            new_board = board.apply_move(move_path)
            # CORRECTED LINE: The last parameter is now 'True'
            evaluation, path = minimax(new_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = move_path + path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_path

def get_ai_move_analysis(board, depth, color_to_move, evaluate_func):
    """
    The top-level AI function. This version correctly handles the (score, path)
    tuple returned by the new minimax function.
    """
    is_maximizing = color_to_move == WHITE
    possible_moves = list(get_all_move_sequences(board, color_to_move))

    if not possible_moves:
        logger.warning(f"AI ANALYSIS: No possible moves found for {'White' if is_maximizing else 'Red'}.")
        return [], []

    all_scored_moves = []
    for move_path in possible_moves:
        move_board = board.apply_move(move_path)
        # Call the corrected minimax, which returns both score and the full subsequent path
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        
        # The full path for display is the AI's first move plus the predicted continuation.
        full_path_for_display = move_path + subsequent_path
        
        # Store the score, the full path for display, and just the first move for execution.
        all_scored_moves.append((score, full_path_for_display, move_path))

    if not all_scored_moves:
        logger.error("AI ANALYSIS: Moves were possible, but none were scored. THIS IS A BUG.")
        return [], []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    # The move to execute is just the first part of the best path.
    best_path_for_execution = all_scored_moves[0][2] 
    
    # The paths for display are the full sequences.
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves]
    
    return best_path_for_execution, top_5_for_display[0:5]

# --- END: DEFINITIVE AI LOGIC FIX ---
