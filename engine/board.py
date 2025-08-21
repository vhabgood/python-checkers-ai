#engine/board.py
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
