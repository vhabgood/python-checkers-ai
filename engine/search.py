# engine/search.py
import logging
from .constants import RED, WHITE

logger = logging.getLogger('board')

def _find_jump_paths(board, path_so_far):
    """
    Recursive helper to find all possible multi-jump paths.
    """
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
    """
    Generator that finds all possible complete move sequences (including multi-jumps).
    """
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

# --- START: DEFINITIVE AI LOGIC FIX ---

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    The core recursive search algorithm. This version correctly alternates
    between maximizing and minimizing players.
    """
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    best_path = []
    
    if maximizing_player:
        max_eval = float('-inf')
        for path in get_all_move_sequences(board, WHITE):
            move_board = board.apply_move(path)
            # The recursive call must be for the MINIMIZING player (False)
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_path = path + subsequent_path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval, best_path
    else:  # Minimizing player (Red)
        min_eval = float('inf')
        for path in get_all_move_sequences(board, RED):
            move_board = board.apply_move(path)
            # The recursive call must be for the MAXIMIZING player (True)
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
    The top-level AI function.
    """
    is_maximizing = color_to_move == WHITE
    possible_moves = list(get_all_move_sequences(board, color_to_move))

    if not possible_moves:
        logger.debug(f"AI SEARCH (depth {depth}, color {color_to_move}): No moves found.")
        return [], []

    all_scored_moves = []
    for move_path in possible_moves:
        move_board = board.apply_move(path)
        # The first call to minimax correctly flips the perspective to the opponent
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_path_for_display = move_path + subsequent_path
        all_scored_moves.append((score, full_path_for_display, move_path))

    if not all_scored_moves:
        return [], []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    best_path_for_execution = all_scored_moves[0][2] 
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves[:5]]
    
    current_turn_color = "W" if color_to_move == WHITE else "R"
    # Use a helper to format the path for the log
    log_path_str = " ".join([f"{board.COORD_TO_ACF.get(p, '?')}" for p in best_path_for_execution])
    logger.debug(f"AI SEARCH (depth {depth}, {current_turn_color}): Best path chosen: {log_path_str}")
    return best_path_for_execution, top_5_for_display

# --- END: DEFINITIVE AI LOGIC FIX ---
