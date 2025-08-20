# engine/constants.py
import pygame

# Game constants
RED = 'r'
WHITE = 'w'
RED_KING = 'R'
WHITE_KING = 'W'
EMPTY = '.'

# Colors
COLOR_RED_P = (200, 0, 0)
COLOR_WHITE_P = (255, 255, 255)
COLOR_LIGHT_SQUARE = (255, 206, 158)
COLOR_DARK_SQUARE = (209, 139, 71)
COLOR_HIGHLIGHT = (0, 255, 0)
COLOR_SELECTED = (0, 0, 255)
COLOR_CROWN = (255, 215, 0)
COLOR_TEXT = (0, 0, 0)
COLOR_BG = (200, 200, 200)
COLOR_BUTTON = (150, 150, 150)
COLOR_BUTTON_HOVER = (180, 180, 180)

# Sizes
BOARD_SIZE = 576
INFO_WIDTH = 192
SQUARE_SIZE = 72
PIECE_RADIUS = 31

# Player names
PLAYER_NAMES = {RED: "Red", WHITE: "White"}

# ACF numbering: 1 at Red's right double corner (7,7), zigzagging left to right, up to 32 at White's top-left (0,0)
# All coordinates are dark squares ((row + col) % 2 == 1)
COORD_TO_ACF = {
    # Row 1 (bottom, row 7): right to left
    (7,7): '1', (7,5): '2', (7,3): '3', (7,1): '4',
    # Row 2 (row 6): left to right
    (6,6): '5', (6,4): '6', (6,2): '7', (6,0): '8',
    # Row 3 (row 5): right to left
    (5,7): '9', (5,5): '10', (5,3): '11', (5,1): '12',
    # Row 4 (row 4): left to right
    (4,6): '13', (4,4): '14', (4,2): '15', (4,0): '16',
    # Row 5 (row 3): right to left
    (3,7): '17', (3,5): '18', (3,3): '19', (3,1): '20',
    # Row 6 (row 2): left to right
    (2,6): '21', (2,4): '22', (2,2): '23', (2,0): '24',
    # Row 7 (row 1): right to left
    (1,7): '25', (1,5): '26', (1,3): '27', (1,1): '28',
    # Row 8 (row 0): left to right
    (0,6): '29', (0,4): '30', (0,2): '31', (0,0): '32'
}

FUTILITY_MARGIN = 100000
