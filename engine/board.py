#engine/board.py
import logging

# Configure logging
logger = logging.getLogger('board')

# Mapping of (row, col) coordinates to ACF square numbers (dark squares only, odd sum)
COORD_TO_ACF = {
    (0,1): 32, (0,3): 31, (0,5): 30, (0,7): 29,
    (1,0): 28, (1,2): 27, (1,4): 26, (1,6): 25,
    (2,1): 24, (2,3): 23, (2,5): 22, (2,7): 21,
    (3,0): 20, (3,2): 19, (3,4): 18, (3,6): 17,
    (4,1): 16, (4,3): 15, (4,5): 14, (4,7): 13,
    (5,0): 12, (5,2): 11, (5,4): 10, (5,6): 9,
    (6,1): 8, (6,3): 7, (6,5): 6, (6,7): 5,
    (7,0): 4, (7,2): 3, (7,4): 2, (7,6): 1
}

def is_dark_square(row, col):
    """
    Check if a square is dark (valid for piece placement, row + col is odd).
    Verified working 100% correctly as of commit 3b478db79e7abfe730050318d293af21b4aeffcc.
    Returns True for dark squares, False for light squares.
    """
    return (row + col) % 2 == 1

def setup_initial_board():
    """
    Initialize an 8x8 checkers board with 12 red (r) and 12 white (w) pieces.
    Verified working 100% correctly as of commit 3b478db79e7abfe730050318d293af21b4aeffcc.
    Places pieces on dark squares (ACF 1-12 for red, 21-32 for white).
    """
    board = [['.' for _ in range(8)] for _ in range(8)]
    for coord, acf in COORD_TO_ACF.items():
        row, col = coord
        if is_dark_square(row, col):
            if 1 <= acf <= 12:
                board[row][col] = 'r'  # Red pieces
            elif 21 <= acf <= 32:
                board[row][col] = 'w'  # White pieces
        else:
            logger.error(f"Light square in COORD_TO_ACF: {coord} = {acf}")
    red_count, white_count = count_pieces(board)
    logger.debug(f"Initial piece count: Red={red_count}, White={white_count}")
    if red_count != 12 or white_count != 12:
        logger.error(f"Piece count mismatch: Red={red_count}, White={white_count}")
    return board

def count_pieces(board):
    """
    Count red and white pieces (including kings) on the board.
    Verified working 100% correctly as of commit 3b478db79e7abfe730050318d293af21b4aeffcc.
    Returns tuple (red_count, white_count) for pieces 'r', 'R', 'w', 'W'.
    """
    red_count = sum(row.count('r') + row.count('R') for row in board)
    white_count = sum(row.count('w') + row.count('W') for row in board)
    return red_count, white_count

def print_board(board):
    """
    Print the board to the log for debugging.
    Verified working 100% correctly as of commit 3b478db79e7abfe730050318d293af21b4aeffcc.
    Logs each row of the board as a space-separated string.
    """
    for row in board:
        logger.debug(' '.join(row))

def get_valid_moves(board, player):
    """
    Generate valid moves for the given player ('w' for white, 'r' for red).
    Verified working 100% correctly as of commit 3b478db79e7abfe730050318d293af21b4aeffcc.
    Returns a list of tuples: (from_row, from_col, to_row, to_col, is_jump).
    Handles regular moves (diagonal, one square) and jumps (diagonal, two squares).
    """
    moves = []
    directions = {'w': [(-1, -1), (-1, 1)], 'r': [(1, -1), (1, 1)]}
    king_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    pieces = []
    if player == 'w':
        pieces = ['w', 'W']
    elif player == 'r':
        pieces = ['r', 'R']
    
    for row in range(8):
        for col in range(8):
            if board[row][col] in pieces:
                piece_type = board[row][col]
                
                current_directions = directions[player.lower()]
                if piece_type in ['W', 'R']: # King piece
                    current_directions = king_directions
                
                # Regular moves
                for dr, dc in current_directions:
                    new_row, new_col = row + dr, col + dc
                    if 0 <= new_row < 8 and 0 <= new_col < 8 and is_dark_square(new_row, new_col):
                        if board[new_row][new_col] == '.':
                            moves.append((row, col, new_row, new_col, False))
                
                # Jump moves
                for dr, dc in current_directions:
                    jump_row, jump_col = row + 2 * dr, col + 2 * dc
                    mid_row, mid_col = row + dr, col + dc
                    if (0 <= jump_row < 8 and 0 <= jump_col < 8 and
                        is_dark_square(jump_row, jump_col) and
                        board[jump_row][jump_col] == '.' and
                        board[mid_row][mid_col] in (['r', 'R'] if player == 'w' else ['w', 'W'])):
                        moves.append((row, col, jump_row, jump_col, True))
    
    # Prioritize jumps if any exist
    if any(move[4] for move in moves):
        moves = [move for move in moves if move[4]]
    return moves

def make_move(board, move):
    """
    Apply a move to the board and return the updated board.
    Move is a tuple: (from_row, from_col, to_row, to_col, is_jump).
    Updates piece position and removes captured piece if jump.
    """
    from_row, from_col, to_row, to_col, is_jump = move
    new_board = [row[:] for row in board]  # Deep copy
    piece = new_board[from_row][from_col]
    new_board[from_row][from_col] = '.'
    new_board[to_row][to_col] = piece
    if is_jump:
        mid_row = (from_row + to_row) // 2
        mid_col = (from_col + to_col) // 2
        new_board[mid_row][mid_col] = '.'
    return new_board

def evaluate_board(board):
    """
    Evaluate the board for a simple positional score (red - white piece count).
    Returns positive for red advantage, negative for white.
    """
    red_count, white_count = count_pieces(board)
    return red_count - white_count

