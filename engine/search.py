# engine/search.py
from .constants import RED, WHITE
import logging

logger = logging.getLogger('board')

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    """
    The top-level AI function. Returns the best move and top 5 analysis lines.
    This version is corrected to use the board's turn as the source of truth.
    """
    # Generate all possible move sequences for the player whose turn it currently is.
    # This should be the AI's turn at the start of the analysis.
    possible_moves = list(get_all_move_sequences(board, board.turn))

    if not possible_moves:
        logger.debug(f"AI SEARCH (depth {depth}, {ai_color}): No possible moves found.")
        return [], []

    all_scored_moves = []
    for move_path in possible_moves:
        # Get the final board state for this move sequence
        move_board = board.apply_move(move_path)
        
        # Call the corrected minimax function
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), ai_color, evaluate_func)
        full_path_for_display = move_path + subsequent_path
        all_scored_moves.append((score, full_path_for_display, move_path))
    
    if not all_scored_moves:
        return [], []

    # Sort the results based on the AI's perspective (maximize if AI is White, minimize if AI is Red)
    is_maximizing = ai_color == WHITE
    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    best_path_for_execution = all_scored_moves[0][2] 
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves[:5]]
    
    current_turn_color = "W" if board.turn == WHITE else "R"
    logger.debug(f"AI SEARCH (depth {depth}, {current_turn_color}): Best path chosen: {best_path_for_execution}")

    return best_path_for_execution, top_5_for_display

def minimax(board, depth, alpha, beta, ai_color, evaluate_func):
    """
    The core recursive search algorithm.
    This version derives whose turn it is directly from the board state, fixing the bug.
    """
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    # THE CORE FIX: Determine if we are maximizing based on the AI's color
    # and whose turn it is on the CURRENT board state.
    maximizing_player = board.turn == ai_color

    best_path = []
    
    # Generate moves for the player whose turn it ACTUALLY is on the simulated board.
    possible_moves = get_all_move_sequences(board, board.turn)

    if maximizing_player:
        max_eval = float('-inf')
        for path in possible_moves:
            move_board = board.apply_move(path)
            # Pass ai_color down through the recursion, do not flip a boolean.
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
        for path in possible_moves:
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
    and yields them as paths. This version is corrected to properly iterate all valid moves.
    """
    # Get all valid moves. The board object correctly handles the mandatory jump rule.
    valid_moves = board.get_all_valid_moves(color)

    # --- START: THE DEFINITIVE FIX ---
    # Iterate through all pieces that have moves.
    for start_pos, end_positions in valid_moves.items():
        # Check if the move is a jump by looking at the distance.
        # A jump is a move of 2 rows.
        is_jump = abs(list(end_positions.keys())[0][0] - start_pos[0]) == 2

        if is_jump:
            # If it's a jump, we must find all possible multi-jump paths.
            for end_pos in end_positions:
                yield from _find_jump_paths(board, [start_pos, end_pos])
        else:
            # If it's a simple slide, yield each move as a complete path.
            for end_pos in end_positions:
                yield [start_pos, end_pos]
    # --- END: THE DEFINITIVE FIX ---

def _find_jump_paths(board, path_so_far):
    """
    Recursive helper to find all possible multi-jump paths.
    """
    last_pos = path_so_far[-1]
    
    # Create a temporary board state reflecting the path so far
    temp_board = board.apply_move(path_so_far)
    piece_at_last_pos = temp_board.get_piece(last_pos[0], last_pos[1])
    
    # If the turn has flipped on the new board (e.g., due to promotion), the multi-jump ends.
    if piece_at_last_pos == 0 or temp_board.turn != board.turn:
        yield path_so_far
        return

    # Check for more available jumps from the piece's new position
    more_jumps = temp_board._get_moves_for_piece(piece_at_last_pos, find_jumps=True)

    if not more_jumps:
        # If there are no more jumps, this path is complete.
        yield path_so_far
        return
    
    # If there are more jumps, explore each one recursively.
    for next_pos in more_jumps:
        new_path = path_so_far + [next_pos]
        yield from _find_jump_paths(board, new_path)
