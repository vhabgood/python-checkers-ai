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

# ACF numbering: As per user (1 at Red's right double corner, increasing leftward, zigzagging up to 32 at White's left top corner)
# All coordinates are dark squares ((row + col) % 2 == 1)
COORD_TO_ACF = {
    (7,7): '1', (7,5): '2', (7,3): '3', (7,1): '4',  # Row 1 from bottom (row 7): right to left
    (6,6): '5', (6,4): '6',  # Row 2 from bottom (row 6): left to right
    (5,7): '7', (5,5): '8', (5,3): '9', (5,1): '10',  # Row 3 from bottom (row 5): right to left
    (4,6): '11', (4,4): '12',  # Row 4 from bottom (row 4): left to right
    (3,7): '13', (3,5): '14', (3,3): '15', (3,1): '16',  # Row 5 from bottom (row 3): right to left
    (2,6): '17', (2,4): '18', (2,2): '19', (2,0): '20',  # Row 6 from bottom (row 2): left to right
    (1,7): '21', (1,5): '22',  # Row 7 from bottom (row 1): right to left
    (0,6): '23', (0,4): '24', (0,2): '25', (0,0): '26'  # Row 8 from bottom (row 0): left to right
}

FUTILITY_MARGIN = 100000
