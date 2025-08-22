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
# NOTE: New color for valid move highlights
COLOR_VALID_MOVE_HIGHLIGHT = (100, 255, 100)

# Sizes
BOARD_SIZE = 576
INFO_WIDTH = 192
SQUARE_SIZE = 72
PIECE_RADIUS = 31

# --- RGB Colors ---
RED = (255, 0, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
# Player names
PLAYER_NAMES = {RED: "Red", WHITE: "White"}

# ACF numbering: 1 at Red's right double corner (7,6), zigzagging left to right, up to 32 at White's top-left (0,1)
# All coordinates are dark squares ((row + col) % 2 == 1)
COORD_TO_ACF = {
    (5,1): 12, (5,3): 11, (5,5): 10, (5,7): 9,
    (6,0): 8, (6,2): 7, (6,4): 6, (6,6): 5,
    (7,1): 4, (7,3): 3, (7,5): 2, (7,7): 1,
    (0,0): 32, (0,2): 31, (0,4): 30, (0,6): 29,
    (1,1): 28, (1,3): 27, (1,5): 26, (1,7): 25,
    (2,0): 24, (2,2): 23, (2,4): 22, (2,6): 21
}
ACF_TO_COORD = {v: k for k, v in COORD_TO_ACF.items()}

FUTILITY_MARGIN = 100000

