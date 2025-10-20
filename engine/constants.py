# engine/constants.py
# This file defines constants used throughout the application, including
# UI dimensions, colors, and the crucial board coordinate mappings.

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
RED, WHITE = 'red', 'white'
COLOR_BG = (50, 50, 50)
COLOR_PANEL_BG = (65, 65, 65)
COLOR_DEV_PANEL_BG = (85, 85, 85)
COLOR_TEXT = (248, 248, 242)
COLOR_BUTTON = (90, 90, 90)
COLOR_BUTTON_HOVER = (110, 110, 110)
COLOR_SQUARE_DARK = (55, 55, 55)
COLOR_SQUARE_LIGHT = (180, 180, 180)
DARK_YELLOW = (200, 180, 0)
GREY = (128, 128, 128)
COLOR_RED = (255, 85, 85)
COLOR_WHITE = (248, 248, 242)

# --- Endgame Database Constants ---
DB_UNKNOWN, DB_WIN, DB_LOSS, DB_DRAW, DB_UNAVAILABLE = 0, 1, 2, 3, 4
RESULT_MAP = {
    DB_UNKNOWN: "UNKNOWN", DB_WIN: "WIN", DB_LOSS: "LOSS",
    DB_DRAW: "DRAW", DB_UNAVAILABLE: "UNAVAILABLE"
}

# --- THE FINAL FIX: Board Mapping (Kingsrow Standard) ---
# This mapping is crucial. It translates the engine's (row, col) coordinates
# to the 1-32 square numbering system used by the Kingsrow endgame database.
# The numbering starts at the bottom-right from White's perspective.
COORD_TO_ACF = {
    (0, 1): 29, (0, 3): 30, (0, 5): 31, (0, 7): 32,
    (1, 0): 25, (1, 2): 26, (1, 4): 27, (1, 6): 28,
    (2, 1): 21, (2, 3): 22, (2, 5): 23, (2, 7): 24,
    (3, 0): 17, (3, 2): 18, (3, 4): 19, (3, 6): 20,
    (4, 1): 13, (4, 3): 14, (4, 5): 15, (4, 7): 16,
    (5, 0): 9,  (5, 2): 10, (5, 4): 11, (5, 6): 12,
    (6, 1): 5,  (6, 3): 6,  (6, 5): 7,  (6, 7): 8,
    (7, 0): 1,  (7, 2): 2,  (7, 4): 3,  (7, 6): 4,
}
# Create the reverse mapping automatically
ACF_TO_COORD = {v: k for k, v in COORD_TO_ACF.items()}


