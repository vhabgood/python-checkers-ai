# engine/search.py
from .constants import RED, WHITE
import copy

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    """
    The top-level AI function. It initiates the minimax search for each possible
    first move and returns the best move path found, along with other top moves for analysis.
    """
    is_maximizing = ai_color == WHITE
    
    possible_moves = list(get_all_moves(board, ai_color))

    if not possible_moves:
        print("DEBUG: AI found no valid moves. Returning empty path.")
        return [], []

    all_scored_moves = []
    for move_path, move_board in possible_moves:
        # The main recursive call to evaluate the outcome of this move
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_path = move_path + subsequent_path
        all_scored_moves.append((score, full_path))
    
    # Sort moves from best to worst based on the final evaluation score
    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    
    best_path = all_scored_moves[0][1]
    top_5_paths = all_scored_moves[:5]
    return best_path, top_5_paths

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    The core recursive search algorithm. It explores the game tree to a specified
    depth, using alpha-beta pruning to cut off branches that are not promising.
    """
    # Base case: stop searching if depth is 0 or a player has won
    if depth == 0 or board.winner() is not None:
        return evaluate_func(board), []

    best_path = []
    if maximizing_player:
        max_eval = float('-inf')
        for path, move_board in get_all_moves(board, WHITE):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_path = path + subsequent_path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break # Prune this branch
        return max_eval, best_path
    else: # Minimizing player
        min_eval = float('inf')
        for path, move_board in get_all_moves(board, RED):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break # Prune this branch
        return min_eval, best_path

def get_all_moves(board, color):
    """
    A generator that yields all possible next board states for a given color.
    This version corrects a critical bug by ensuring every move is simulated
    on a unique copy of the board.
    """
    # The move data is a dictionary: { start_pos: { end_pos: [captured], ... } }
    for start_pos, end_positions in board.get_all_valid_moves_for_color(color).items():
        # The inner loop iterates through each possible destination for the piece
        for end_pos, captured_pieces in end_positions.items():
            # CRITICAL FIX: Create a fresh deepcopy for EVERY potential move.
            temp_board = copy.deepcopy(board)
            piece = temp_board.get_piece(start_pos[0], start_pos[1])
            
            if piece == 0: continue

            # If the move involves a capture, explore further multi-jumps recursively
            if captured_pieces:
                temp_board.move(piece, end_pos[0], end_pos[1])
                temp_board._remove(captured_pieces)
                yield from _get_jump_sequences(temp_board, [start_pos, end_pos])
            else: # It's a simple slide
                temp_board.move(piece, end_pos[0], end_pos[1])
                temp_board.turn = RED if color == WHITE else WHITE
                yield [start_pos, end_pos], temp_board

def _get_jump_sequences(board, path):
    """
    A recursive generator that explores multi-jump paths, now correctly using
    the board's new `get_valid_moves` method.
    """
    current_pos = path[-1]
    
    # Get the piece at the end of the current path
    piece = board.get_piece(current_pos[0], current_pos[1])
    if piece == 0: # Safety check in case the piece is gone
        yield path, board
        return

    # Use the new, correct method to get all moves for this piece
    all_possible_moves = board.get_valid_moves(piece)
    # A jump is a move where the 'captured' list is not empty. Filter for those.
    more_jumps = {dest: captured for dest, captured in all_possible_moves.items() if captured}

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
