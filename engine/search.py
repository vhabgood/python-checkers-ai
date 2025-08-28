# engine/search.py
import logging
from .constants import RED, WHITE

logger = logging.getLogger('board')

def get_ai_move_analysis(board, depth, color_to_move, evaluate_func):
    """
    The top-level AI function. It sets up the search and returns the best move
    and top 5 analysis lines for the given color.
    """
    possible_moves = list(get_all_move_sequences(board, color_to_move))

    if not possible_moves:
        logger.debug(f"AI SEARCH (depth {depth}, color {color_to_move}): No moves found.")
        return [], []

    all_scored_moves = []
    for move_path in possible_moves:
        move_board = board.apply_move(move_path)
        # The initial call to the new, simpler minimax function
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), evaluate_func)
        full_path_for_display = move_path + subsequent_path
        all_scored_moves.append((score, full_path_for_display, move_path))

    if not all_scored_moves:
        return [], []

    # Sort the results from the perspective of the player making the move
    is_maximizing_sort = color_to_move == WHITE
    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing_sort)

    best_path_for_execution = all_scored_moves[0][2]
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves[:5]]
    
    logger.debug(f"AI SEARCH (depth {depth}, {'W' if color_to_move == WHITE else 'R'}): Best path found: {best_path_for_execution}")
    return best_path_for_execution, top_5_for_display


def minimax(board, depth, alpha, beta, evaluate_func):
    """
    The core recursive search algorithm. It is now "pure" and only depends
    on the board state and the rules of the game.
    """
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    # White is always the maximizing player because our evaluation function is from White's perspective.
    is_maximizing = board.turn == WHITE
    best_path = []

    if is_maximizing:
        max_eval = float('-inf')
        for path in get_all_move_sequences(board, WHITE):
            move_board = board.apply_move(path)
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, evaluate_func)
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
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_path

# This helper function and the one below it remain unchanged.
def get_all_move_sequences(board, color):
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


def _find_jump_paths(board, path_so_far):
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
    
    found_longer_path = False
    for next_pos in more_jumps:
        found_longer_path = True
        new_path = path_so_far + [next_pos]
        yield from _find_jump_paths(board, new_path)

    if not found_longer_path:
        yield path_so_far
