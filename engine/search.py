# engine/search.py
from .constants import RED, WHITE
import copy
import logging # <--- Add this import

logger = logging.getLogger('board') # <--- Add this line

# engine/search.py

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    """
    The top-level AI function. It now returns both the best move to execute
    and the top 5 full sequences for the developer panel to display.
    """
    is_maximizing = ai_color == WHITE
    
    possible_moves = list(get_all_moves(board, ai_color))

    if not possible_moves:
        logger.debug("AI SEARCH: No possible moves found.")
        return [], []

    all_scored_moves = []
    # This loop gets the full predicted sequence for each possible first move
    for move_path, move_board in possible_moves:
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_path_for_display = move_path + subsequent_path
        # We store three things: the score, the full path for display, and the simple first move for execution
        all_scored_moves.append((score, full_path_for_display, move_path))
    
    # Sort all the potential outcomes by their score
    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    # The best path FOR EXECUTION is just the first move from the top-scoring sequence
    best_path_for_execution = all_scored_moves[0][2] 
    
    # The top 5 moves FOR DISPLAY are the scores and the full predicted paths
    top_5_for_display = [(item[0], item[1]) for item in all_scored_moves[:5]]
    
    logger.debug(f"AI SEARCH: Best path chosen for execution: {best_path_for_execution}")

    return best_path_for_execution, top_5_for_display

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    The core recursive search algorithm. It's now restored to return the
    full predicted path for analysis purposes.
    """
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    best_path = []
    if maximizing_player:
        max_eval = float('-inf')
        for path, move_board in get_all_moves(board, WHITE):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                # Restore path concatenation to build the full sequence for analysis
                best_path = path + subsequent_path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval, best_path
    else: # Minimizing player
        min_eval = float('inf')
        for path, move_board in get_all_moves(board, RED):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                # Restore path concatenation to build the full sequence for analysis
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_path

def get_all_moves(board, color):
    """
    A generator that yields all possible next board states for a given color,
    now using the new authoritative move generation from the board.
    """
    # FIX: Changed to call the new, correct function name
    for start_pos, end_positions in board.get_all_valid_moves(color).items():
        for end_pos, captured_pieces in end_positions.items():
            temp_board = copy.deepcopy(board)
            piece = temp_board.get_piece(start_pos[0], start_pos[1])
            
            if piece == 0: continue

            if captured_pieces:
                temp_board.move(piece, end_pos[0], end_pos[1])
                temp_board._remove(captured_pieces)
                yield from _get_jump_sequences(temp_board, [start_pos, end_pos])
            else: 
                temp_board.move(piece, end_pos[0], end_pos[1])
                temp_board.turn = RED if color == WHITE else WHITE
                yield [start_pos, end_pos], temp_board

def _get_jump_sequences(board, path):
    """
    A recursive generator that explores multi-jump paths, now correctly using
    the board's new, unified move logic.
    """
    current_pos = path[-1]
    
    piece = board.get_piece(current_pos[0], current_pos[1])
    if piece == 0:
        yield path, board
        return

    # FIX: Use the new, correct helper function to find only jumps.
    more_jumps = board._get_moves_for_piece(piece, find_jumps=True)

    # Base case: if there are no more jumps, the sequence is complete.
    if not more_jumps:
        board.turn = RED if board.turn == WHITE else WHITE
        yield path, board
        return

    # Recursive step: for each available jump, create a new board state and recurse.
    for next_pos, jumped_pieces in more_jumps.items():
        temp_board = copy.deepcopy(board)
        temp_piece = temp_board.get_piece(current_pos[0], current_pos[1])

        if temp_piece != 0:
            temp_board.move(temp_piece, next_pos[0], next_pos[1])
            temp_board._remove(jumped_pieces)
            
            new_path = path + [next_pos]
            yield from _get_jump_sequences(temp_board, new_path)
