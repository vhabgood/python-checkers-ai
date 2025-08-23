# engine/constants.py
"""
Stores all the global constants for the game.
"""
import pygame

# --- Game Settings ---
FPS = 60
DEFAULT_AI_DEPTH = 5

# --- Dimensions ---
BOARD_SIZE = 480
INFO_WIDTH = 120
WIDTH, HEIGHT = BOARD_SIZE + INFO_WIDTH, BOARD_SIZE
ROWS, COLS = 8, 8
SQUARE_SIZE = BOARD_SIZE // COLS
PIECE_RADIUS = SQUARE_SIZE // 2 - 6

# --- Player and Piece Identifiers ---
RED = (255, 0, 0)
WHITE = (255, 255, 255)
PLAYER_NAMES = {RED: 'Red', WHITE: 'White'}

# --- Colors ---
COLOR_RED_P = (210, 0, 0)
COLOR_WHITE_P = (245, 245, 245)
COLOR_LIGHT_SQUARE = (227, 206, 187)
COLOR_DARK_SQUARE = (181, 136, 99)
COLOR_HIGHLIGHT = (255, 255, 0)
COLOR_SELECTED = (0, 200, 0)
COLOR_CROWN = (255, 215, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_BG = (20, 20, 20)
COLOR_BUTTON = (100, 100, 100)
COLOR_BUTTON_HOVER = (150, 150, 150)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREY = (128, 128, 128)

# --- AI and Game Logic Constants ---
FUTILITY_MARGIN = 300
EMPTY = 0
RED_KING = 3
WHITE_KING = -3

# --- Board Coordinate Mappings ---
COORD_TO_ACF = {}
ACF_TO_COORD = {}
square_num = 1
for r in range(ROWS):
    for c in range(COLS):
        if (r + c) % 2 == 1:
            COORD_TO_ACF[(r, c)] = square_num
            ACF_TO_COORD[square_num] = (r, c)
            square_num += 1
