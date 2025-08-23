# engine/search.py
"""
Contains the AI's search algorithm (minimax with alpha-beta pruning).
"""
from .constants import RED, WHITE, COORD_TO_ACF
import copy

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    """
    Analyzes the board to find the best move for the AI.
    Returns the best move and a list of the top 5 moves with their scores.
    """
    is_maximizing = True if ai_color == WHITE else False
    
    all_scored_moves = []
    # Get all possible first moves for the AI
    for move, move_board in get_all_moves_as_boards(board, ai_color):
        # For each possible move, call minimax to get its score after searching deeper
        score = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        all_scored_moves.append((score, move))

    if not all_scored_moves:
        return None, []

    # Sort moves by score (descending for white, ascending for red)
    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)

    best_move = all_scored_moves[0][1]
    top_5_moves = all_scored_moves[:5]

    return best_move, top_5_moves

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    """
    Recursive minimax algorithm with alpha-beta pruning.
    Returns only the score of a board state.
    """
    # Base case: if we've reached the depth limit or the game is over, return the score
    if depth == 0 or not board.get_all_valid_moves_for_color(board.turn):
        return evaluate_func(board)

    if maximizing_player:
        max_eval = float('-inf')
        for _, move_board in get_all_moves_as_boards(board, WHITE):
            evaluation = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            max_eval = max(max_eval, evaluation)
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval
    else: # Minimizing player
        min_eval = float('inf')
        for _, move_board in get_all_moves_as_boards(board, RED):
            evaluation = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            min_eval = min(min_eval, evaluation)
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval

def get_all_moves_as_boards(board, color):
    """
    Generator function that yields a move tuple and a new Board object for that move.
    """
    all_moves = board.get_all_valid_moves_for_color(color)
    for start_pos, end_positions in all_moves.items():
        for end_pos in end_positions:
            temp_board = copy.deepcopy(board)
            piece = temp_board.get_piece(start_pos[0], start_pos[1])
            temp_board.move(piece, end_pos[0], end_pos[1])
            temp_board.turn = RED if color == WHITE else WHITE
            
            # Yield the move itself along with the resulting board
            yield (start_pos, end_pos), temp_board
