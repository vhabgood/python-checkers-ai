#engine/board.py
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('board')

# Mapping of (row, col) coordinates to ACF square numbers (dark squares only)
COORD_TO_ACF = {
    (5,1): 12, (5,3): 11, (5,5): 10, (5,7): 9,
    (6,0): 8, (6,2): 7, (6,4): 6, (6,6): 5,
    (7,1): 4, (7,3): 3, (7,5): 2, (7,7): 1,
    (0,0): 32, (0,2): 31, (0,4): 30, (0,6): 29,
    (1,1): 28, (1,3): 27, (1,5): 26, (1,7): 25,
    (2,0): 24, (2,2): 23, (2,4): 22, (2,6): 21
}

def is_dark_square(row, col):
    # Check if a square is dark (valid for piece placement)
    return (row + col) % 2 == 1

def setup_initial_board():
    # Initialize an 8x8 checkers board with Red (r) and White (w) pieces
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
    # Count Red and White pieces on the board
    red_count = sum(row.count('r') + row.count('R') for row in board)
    white_count = sum(row.count('w') + row.count('W') for row in board)
    return red_count, white_count

def print_board(board):
    # Print the board for debugging
    for row in board:
        logger.debug(' '.join(row))
