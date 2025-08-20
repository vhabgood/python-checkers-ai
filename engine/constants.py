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

# ACF numbering: Double corner on right, Red at bottom (unflipped)
# All coordinates are dark squares (row + col) % 2 == 0
COORD_TO_ACF = {
    # Row 0: White (25-26, double corner on right)
    (0,0): '29', (0,2): '30', (0,4): '25', (0,6): '26',
    # Row 1: White (27-28, single corner on left)
    (1,1): '27', (1,3): '28',
    # Row 2: White (21-24, double corner on right)
    (2,0): '21', (2,2): '22', (2,4): '23', (2,6): '24',
    # Row 3: Middle (17-20)
    (3,0): '17', (3,2): '18', (3,4): '19', (3,6): '20',
    # Row 4: Middle (13-16)
    (4,1): '15', (4,3): '16',
    # Row 5: Red (1-4, double corner on right)
    (5,1): '5', (5,3): '6', (5,5): '1', (5,7): '2',
    # Row 6: Red (7-8, single corner on left)
    (6,0): '7', (6,2): '8',
    # Row 7: Red (9-12, double corner on right)
    (7,1): '9', (7,3): '10', (7,5): '11', (7,7): '12'
}

FUTILITY_MARGIN = 100000
