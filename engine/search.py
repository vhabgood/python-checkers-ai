# engine/search.py
"""
Contains the AI's search algorithm (minimax with alpha-beta pruning).
"""
from .constants import RED, WHITE
import copy

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    Minimax algorithm with alpha-beta pruning to find the best move.

    Args:
        board (Board): The current board state.
        depth (int): The maximum depth to search.
        alpha (float): The best value for the maximizer found so far.
        beta (float): The best value for the minimizer found so far.
        maximizing_player (bool): True if the current player is the maximizer (White).
        evaluate_func (function): The function to score a board state.

    Returns:
        tuple: A tuple containing the best score and the best move (Board object).
    """
    # Base case: if we've reached the depth limit or the game is over, return the score
    if depth == 0 or board.get_all_valid_moves_for_color(board.turn) == {}:
        return evaluate_func(board), board

    if maximizing_player:
        max_eval = float('-inf')
        best_move_board = None
        # Get all valid moves for the current player (White)
        for move_board in get_all_moves_as_boards(board, WHITE):
            evaluation = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)[0]
            if evaluation > max_eval:
                max_eval = evaluation
                best_move_board = move_board
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break # Prune
        return max_eval, best_move_board
    else: # Minimizing player
        min_eval = float('inf')
        best_move_board = None
        # Get all valid moves for the current player (Red)
        for move_board in get_all_moves_as_boards(board, RED):
            evaluation = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)[0]
            if evaluation < min_eval:
                min_eval = evaluation
                best_move_board = move_board
            beta = min(beta, evaluation)
            if beta <= alpha:
                break # Prune
        return min_eval, best_move_board

def get_all_moves_as_boards(board, color):
    """
    Generator function that yields a new Board object for each possible move.
    """
    all_moves = board.get_all_valid_moves_for_color(color)
    for start_pos, end_positions in all_moves.items():
        for end_pos in end_positions:
            # Create a deep copy of the board to simulate the move on
            temp_board = copy.deepcopy(board)
            piece = temp_board.get_piece(start_pos[0], start_pos[1])
            temp_board.move(piece, end_pos[0], end_pos[1])
            # Switch the turn on the temporary board
            temp_board.turn = RED if color == WHITE else WHITE
            yield temp_board
