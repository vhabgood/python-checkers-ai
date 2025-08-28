# engine/search.py
from .constants import RED, WHITE
import logging

logger = logging.getLogger('board')

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    """
    The top-level AI function. Returns the best move and top 5 analysis lines.
    """
    is_maximizing = ai_color == WHITE
    
    # Generate all possible move sequences (including multi-jumps)
    possible_moves = list(get_all_move_sequences(board, ai_color))

    if not possible_moves:
        logger.debug(f"AI SEARCH (depth {depth}, {ai_color}): No possible moves found.")
        return [], []

    all_scored_moves = []
    for move_path in possible_moves:
        # Get the final board state for this move sequence using the authoritative function
        move_board = board.apply_move(move_path)
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), ai_color, evaluate_func)
        full_path_for_display = move_path + subsequent_path
        all_scored_moves.append((score, full_path_for_display, move_path))
    
    if not all_scored_moves:
        return [], []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    best_path_for_execution = all_scored_moves[0][2] 
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves[:5]]
    
    current_turn_color = "W" if board.turn == WHITE else "R"
    logger.debug(f"AI SEARCH (depth {depth}, {current_turn_color}): Best path chosen: {best_path_for_execution}")

    return best_path_for_execution, top_5_for_display

def minimax(board, depth, alpha, beta, ai_color, evaluate_func):
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    # DETERMINE who is maximizing based on the current board's turn
    maximizing_player = board.turn == ai_color

    best_path = []
    
    if maximizing_player:
        max_eval = float('-inf')
        # ALWAYS generate moves for the player whose turn it is on the board
        for path in get_all_move_sequences(board, board.turn):
            move_board = board.apply_move(path)
            # PASS ai_color down, don't flip a boolean
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, ai_color, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_path = path + subsequent_path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval, best_path
    else: # Minimizing player
        min_eval = float('inf')
        for path in get_all_move_sequences(board, board.turn):
            move_board = board.apply_move(path)
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, ai_color, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_path

def get_all_move_sequences(board, color):
    """
    Generator that finds all possible complete move sequences (including multi-jumps)
    and yields them as paths.
    """
    valid_moves = board.get_all_valid_moves(color)
    is_jump = any(any(val for val in v.values()) for v in valid_moves.values())

    # --- FIX: Ensure all valid moves are considered ---
    if is_jump:
        # If there's a jump, we only need to yield the jump paths
        for start_pos, end_positions in valid_moves.items():
            if any(end_positions.values()): # This ensures we only process pieces that can jump
                for end_pos in end_positions:
                    yield from _find_jump_paths(board, [start_pos, end_pos])
    else:
        # If there are no jumps, yield all the simple slide moves
        for start_pos, end_positions in valid_moves.items():
            for end_pos in end_positions:
                yield [start_pos, end_pos]

def _find_jump_paths(board, path_so_far):
    """
    Recursive helper to find all possible multi-jump paths.
    """
    last_pos = path_so_far[-1]
    
    # Create a temporary board state reflecting the path so far
    temp_board = board.apply_move(path_so_far)
    piece_at_last_pos = temp_board.get_piece(last_pos[0], last_pos[1])
    
    # If there's no piece or the turn has flipped (e.g. promotion), the path ends
    if piece_at_last_pos == 0 or temp_board.turn != board.turn:
        yield path_so_far
        return

    # Check for more jumps from this new position
    more_jumps = temp_board._get_moves_for_piece(piece_at_last_pos, find_jumps=True)

    # If there are no further jumps, this path is complete
    if not more_jumps:
        yield path_so_far
        return
    
    # If there are more jumps, explore each one recursively
    found_longer_path = False
    for next_pos in more_jumps:
        found_longer_path = True
        new_path = path_so_far + [next_pos]
        yield from _find_jump_paths(board, new_path)

    # This handles cases where a jump is possible but not taken, ending the sequence.
    if not found_longer_path:
        yield path_so_far
