# engine/constants.py
# Board dimensions
WIDTH = 800
HEIGHT = 600
BOARD_SIZE = 400
SQUARE_SIZE = BOARD_SIZE // 8
INFO_WIDTH = WIDTH - BOARD_SIZE
MENU_BAR_HEIGHT = HEIGHT - BOARD_SIZE
PIECE_RADIUS=100 #no idea what this is supposed to be

# Colors
COLOR_LIGHT_SQUARE = (240, 217, 181)  # Light tan for checkers board
COLOR_DARK_SQUARE = (181, 136, 99)   # Dark brown for checkers board
COLOR_RED_P = (200, 0, 0)            # Red pieces
COLOR_WHITE_P = (255, 255, 255)      # White pieces
COLOR_CROWN = (255, 215, 0)          # Gold for king crowns
COLOR_VALID_MOVE = (0, 255, 0, 100)  # Green with alpha for valid move highlights
COLOR_LAST_MOVE = (255, 255, 0, 100) # Yellow with alpha for last move highlight
COLOR_BUTTON = (100, 100, 100)       # Gray for buttons
COLOR_BUTTON_HOVER = (150, 150, 150) # Lighter gray for button hover
COLOR_BUTTON_DISABLED = (50, 50, 50) # Dark gray for disabled buttons
COLOR_TEXT = (255, 255, 255)         # White for text
COLOR_BG = (0, 0, 0)                 # Black background
COLOR_HIGHLIGHT = (0, 255, 0)
# Piece types
RED = 'r'
WHITE = 'w'
RED_KING = 'R'
WHITE_KING = 'W'
EMPTY = '.'

# Player names
PLAYER_NAMES = {RED: "Red", WHITE: "White"}

# Coordinate to ACF notation mapping
COORD_TO_ACF = {
    (0, 1): 1, (0, 3): 2, (0, 5): 3, (0, 7): 4,
    (1, 0): 5, (1, 2): 6, (1, 4): 7, (1, 6): 8,
    (2, 1): 9, (2, 3): 10, (2, 5): 11, (2, 7): 12,
    (3, 0): 13, (3, 2): 14, (3, 4): 15, (3, 6): 16,
    (4, 1): 17, (4, 3): 18, (4, 5): 19, (4, 7): 20,
    (5, 0): 21, (5, 2): 22, (5, 4): 23, (5, 6): 24,
    (6, 1): 25, (6, 3): 26, (6, 5): 27, (6, 7): 28,
    (7, 0): 29, (7, 2): 30, (7, 4): 31, (7, 6): 32
}
ACF_TO_COORD = {v: k for k, v in COORD_TO_ACF.items()}

# Evaluation constants
FUTILITY_MARGIN = 200
