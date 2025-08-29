# engine/search.py
import logging
from .constants import RED, WHITE, COORD_TO_ACF

logger = logging.getLogger('board')

def _find_jump_paths(board, path_so_far):
    # This helper function is correct and remains unchanged.
    last_pos = path_so_far[-1]
    temp_board = board.apply_move(path_so_far)
    piece_at_last_pos = temp_board.get_piece(last_pos[0], last_pos[1])

    if piece_at_last_pos == 0 or temp_board.turn != board.turn:
        yield path_so_far
        return

    more_jumps = temp_board._get_moves_for_piece(piece_at_last_pos, find_jumps=True)

    if not more_jumps:
        yield path_so_far
        return

    for next_pos in more_jumps:
        new_path = path_so_far + [next_pos]
        yield from _find_jump_paths(board, new_path)

def get_all_move_sequences(board, color):
    # This helper function is correct and remains unchanged.
    valid_moves = board.get_all_valid_moves(color)
    is_jump = any(any(val for val in v.values()) for v in valid_moves.values())

    if is_jump:
        for start_pos, end_positions in valid_moves.items():
            if any(end_positions.values()):
                for end_pos in end_positions:
                    yield from _find_jump_paths(board, [start_pos, end_pos])
    else:
        for start_pos, end_positions in valid_moves.items():
            for end_pos in end_positions:
                yield [start_pos, end_pos]

# engine/search.py

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    The core recursive search algorithm. This version correctly implements
    alpha-beta pruning and returns the proper values and paths.
    """
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    best_path = []
    
    if maximizing_player:
        max_eval = float('-inf')
        for path in get_all_move_sequences(board, WHITE):
            move_board = board.apply_move(path)
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            
            # --- COMMENT: This is the critical change. ---
            # We check if the new evaluation score is better than any we've seen at this level.
            if evaluation > max_eval:
                max_eval = evaluation
                # The best path is the current move ('path') followed by the best path found from the subsequent recursive call.
                best_path = path + subsequent_path
            
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break # Prune the search tree
        return max_eval, best_path
    else:  # Minimizing player (Red)
        min_eval = float('inf')
        for path in get_all_move_sequences(board, RED):
            move_board = board.apply_move(path)
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            
            # --- COMMENT: This is the critical change. ---
            # We check if the new evaluation score is better (lower) for the minimizing player.
            if evaluation < min_eval:
                min_eval = evaluation
                # The best path is the current move ('path') followed by the best path found from the subsequent recursive call.
                best_path = path + subsequent_path

            beta = min(beta, evaluation)
            if beta <= alpha:
                break # Prune the search tree
        return min_eval, best_path
def get_ai_move_analysis(board, depth, color_to_move, evaluate_func):
    """
    The top-level AI function. This remains the same but will now receive correct data from minimax.
    """
    is_maximizing = color_to_move == WHITE
    possible_moves = list(get_all_move_sequences(board, color_to_move))

    if not possible_moves:
        logger.warning(f"AI SEARCH: No possible moves found for {'White' if is_maximizing else 'Red'}.")
        return [], []

    all_scored_moves = []
    for move_path in possible_moves:
        move_board = board.apply_move(move_path)
        # The first call to minimax correctly flips the perspective to the opponent.
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_path_for_display = move_path + subsequent_path
        all_scored_moves.append((score, full_path_for_display, move_path))

    if not all_scored_moves:
        logger.error("AI SEARCH: Moves were possible, but none were scored. This indicates a search error.")
        return [], []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)

    best_path_for_execution = all_scored_moves[0][2]
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves[:5]]

    return best_path_for_execution, top_5_for_display

# --- END: DEFINITIVE AI LOGIC FIX ---
