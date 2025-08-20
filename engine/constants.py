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

# ACF numbering: Double corner on right, single corner on left, unflipped (Red at bottom)
# All coordinates are dark squares (row + col) % 2 == 0
COORD_TO_ACF = {
    # Row 0: White (25-26, double corner on right)
    (0,1): '30', (0,3): '29', (0,5): '26', (0,7): '25',
    # Row 1: White (27-28, single corner on left)
    (1,0): '28', (1,2): '27',
    # Row 2: White (21-24, double corner on right)
    (2,1): '24', (2,3): '23', (2,5): '22', (2,7): '21',
    # Row 3: Middle (17-20)
    (3,0): '20', (3,2): '19', (3,4): '18', (3,6): '17',
    # Row 4: Middle (13-16)
    (4,1): '16', (4,3): '15',
    # Row 5: Red (1-4, double corner on right)
    (5,0): '4', (5,2): '3', (5,4): '2', (5,6): '1',
    # Row 6: Red (5-8, single corner on left)
    (6,1): '8', (6,3): '7',
    # Row 7: Red (9-12, double corner on right)
    (7,0): '12', (7,2): '11', (7,4): '10', (7,6): '9'
}

FUTILITY_MARGIN = 100000
