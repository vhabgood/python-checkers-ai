# engine/search.py
from .constants import RED, WHITE
import logging

logger = logging.getLogger('board')

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    """
    The top-level AI function. Returns the best move and top 5 analysis lines.
    """
    is_maximizing = ai_color == WHITE
    
    # Use the new, simplified generator to get possible first moves
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
        # The evaluation function needs the original board context for piece counts
        return evaluate_func(board), []

    best_path = []
    color_to_move = WHITE if maximizing_player else RED
    
    # --- SIMPLIFIED LOGIC ---
    # We now get all possible resulting board states directly
    for path, move_board in get_all_moves(board, color_to_move):
        evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, not maximizing_player, evaluate_func)
        
        if maximizing_player:
            if evaluation > alpha:
                alpha = evaluation
                best_path = path + subsequent_path
        else:
            if evaluation < beta:
                beta = evaluation
                best_path = path + subsequent_path
        
        if beta <= alpha:
            break
            
    eval_to_return = alpha if maximizing_player else beta
    return eval_to_return, best_path

def get_all_moves(board, color):
    """
    A generator that yields all possible next board states for a given color.
    This is now much simpler and relies on the Board class for all game logic.
    """
    # Get all valid starting moves from the authoritative board function
    valid_moves = board.get_all_valid_moves(color)
    
    for start_pos, end_positions in valid_moves.items():
        for end_pos in end_positions:
            move_path = [start_pos, end_pos]
            
            # Use the new authoritative simulation function
            temp_board = board.simulate_move(move_path)
            
            # If the move was a jump, we need to check for multi-jumps
            is_jump = abs(start_pos[0] - end_pos[0]) == 2
            if is_jump:
                # The turn doesn't change after the first jump, so we check for more
                # jumps for the same color from the new board state.
                yield from _get_jump_sequences(temp_board, move_path)
            else:
                # If it was a simple slide, the turn is over.
                yield move_path, temp_board

def _get_jump_sequences(board, path):
    """
    A recursive generator that explores multi-jump paths.
    """
    current_pos = path[-1]
    piece = board.get_piece(current_pos[0], current_pos[1])
    
    if piece == 0:
        # This can happen if a piece jumps off the board to be kinged
        yield path, board
        return

    # Check for more jumps from the current position
    more_jumps = board._get_moves_for_piece(piece, find_jumps=True)

    # Base case: if there are no more jumps, this sequence is complete.
    if not more_jumps:
        yield path, board
        return

    # Recursive step: for each available jump, create a new state and recurse.
    for next_pos in more_jumps:
        new_path = path + [next_pos]
        # Create the next board state by simulating this next jump
        next_board = board.simulate_move([current_pos, next_pos])
        yield from _get_jump_sequences(next_board, new_path)

