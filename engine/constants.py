# engine/constants.py
import pygame

# --- Game Settings ---
FPS = 60

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
BLACK = (0, 0, 0) # General purpose color
BLUE = (0, 0, 255)  # General purpose color
GREY = (128, 128, 128) # General purpose color

# --- AI and Game Logic Constants ---
FUTILITY_MARGIN = 300 # Margin for futility pruning in AI
EMPTY = 0
RED_KING = 3
WHITE_KING = -3

# --- Board Coordinate Mappings ---
# These are likely placeholders and may need adjustment based on your board's specific notation
COORD_TO_ACF = {}
ACF_TO_COORD = {}
