# engine/constants.py
import pygame

# --- UI Layout & Dimensions ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 850
BOARD_SIZE = 700

BOARD_RECT = pygame.Rect(0, 0, BOARD_SIZE, BOARD_SIZE)
SIDE_MENU_WIDTH = SCREEN_WIDTH - BOARD_SIZE
SIDE_MENU_RECT = pygame.Rect(BOARD_SIZE, 0, SIDE_MENU_WIDTH, SCREEN_HEIGHT)
DEV_PANEL_HEIGHT = SCREEN_HEIGHT - BOARD_SIZE
DEV_PANEL_RECT = pygame.Rect(0, BOARD_SIZE, BOARD_SIZE, DEV_PANEL_HEIGHT)

# --- Board Dimensions ---
ROWS, COLS = 8, 8
SQUARE_SIZE = BOARD_SIZE // COLS

# --- Game Logic & Colors ---
DEFAULT_AI_DEPTH = 5
RED, WHITE = 'red', 'white'

# --- FIX: Updated background colors to a more silver hue ---
COLOR_BG = (50, 50, 50)          # Dark grey for the main window background
COLOR_PANEL_BG = (65, 65, 65)    # Slightly lighter grey for the side menu
COLOR_DEV_PANEL_BG = (85, 85, 85) # Even lighter grey for the developer panel
# -----------------------------------------------------------

COLOR_TEXT = (248, 248, 242)     # White/off-white for text
COLOR_BUTTON = (90, 90, 90)      # Medium grey for buttons
COLOR_BUTTON_HOVER = (110, 110, 110) # Lighter grey for button hover
COLOR_SQUARE_DARK = (55, 55, 55) # Dark checkerboard squares (can remain distinct)
COLOR_SQUARE_LIGHT = (180, 180, 180) # Light checkerboard squares
DARK_YELLOW = (200, 180, 0)      # Highlight color (can remain)
GREY = (128, 128, 128)           # General grey
COLOR_RED = (255, 85, 85)        # Red pieces (can remain)
COLOR_WHITE = (248, 248, 242)    # White pieces (can remain)

# --- Board Mapping (ACF Notation) ---
ACF_TO_COORD, COORD_TO_ACF = {}, {}
num = 1
for r in range(ROWS):
    for c in range(COLS):
        if (r + c) % 2 == 1:
            ACF_TO_COORD[num], COORD_TO_ACF[(r, c)] = (r, c), num
            num += 1
