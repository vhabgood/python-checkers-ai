# engine/search.py
from .constants import RED, WHITE
import logging

logger = logging.getLogger('board')

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    """
    The top-level AI function. Returns the best move and top 5 analysis lines.
    """
    is_maximizing = ai_color == WHITE
    
    possible_moves = list(get_all_moves(board, ai_color))

    if not possible_moves:
        logger.debug("AI SEARCH: No possible moves found.")
        return [], []

    all_scored_moves = []
    for move_path, move_board in possible_moves:
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_path_for_display = move_path + subsequent_path
        all_scored_moves.append((score, full_path_for_display, move_path))
    
    if not all_scored_moves:
        return [], []

    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    best_path_for_execution = all_scored_moves[0][2] 
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves[:5]]
    
    logger.debug(f"AI SEARCH: Best path chosen for execution: {best_path_for_execution}")

    return best_path_for_execution, top_5_for_display

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    The core recursive search algorithm.
    """
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    best_path = []
    color_to_move = WHITE if maximizing_player else RED
    
    if maximizing_player:
        max_eval = float('-inf')
        for path, move_board in get_all_moves(board, color_to_move):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_path = path + subsequent_path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval, best_path
    else: # Minimizing player
        min_eval = float('inf')
        for path, move_board in get_all_moves(board, color_to_move):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_path

def get_all_moves(board, color):
    """
    A generator that yields all possible next board states for a given color.
    """
    valid_moves = board.get_all_valid_moves(color)
    
    for start_pos, end_positions in valid_moves.items():
        for end_pos in end_positions:
            move_path = [start_pos, end_pos]
            
            is_jump = abs(start_pos[0] - end_pos[0]) == 2
            if is_jump:
                yield from _get_jump_sequences(board, move_path)
            else:
                temp_board = board.simulate_move(move_path)
                yield move_path, temp_board

def _get_jump_sequences(board, path):
    """
    A recursive generator that explores multi-jump paths.
    """
    # --- AI LOGIC FIX ---
    # Always simulate the path from the original board to get the current state
    simulated_board = board.simulate_move(path)
    
    # If the turn has changed, it means the sequence ended (e.g., by kinging)
    if simulated_board.turn != board.turn:
        yield path, simulated_board
        return

    current_pos = path[-1]
    piece = simulated_board.get_piece(current_pos[0], current_pos[1])
    
    if piece == 0:
        yield path, simulated_board
        return

    more_jumps = simulated_board._get_moves_for_piece(piece, find_jumps=True)

    # Base case: if there are no more jumps, this sequence is complete.
    if not more_jumps:
        yield path, simulated_board
        return

    # Recursive step: for each available jump, explore the new path
    for next_pos in more_jumps:
        new_path = path + [next_pos]
        # IMPORTANT: Recurse using the original board, but the *new, longer* path
        yield from _get_jump_sequences(board, new_path)

