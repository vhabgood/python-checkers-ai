# engine/constants.py
import pygame
from .zobrist import generate_zobrist_keys 

FPS = 60
DEFAULT_AI_DEPTH = 5
BOARD_SIZE = 600
SIDE_PANEL_WIDTH = 200
INFO_WIDTH = 220
SCREEN_WIDTH=800
WIDTH, HEIGHT = BOARD_SIZE + INFO_WIDTH, BOARD_SIZE + 120
ROWS, COLS = 8, 8
SCREEN_HEIGHT = 800
SQUARE_SIZE = BOARD_SIZE // ROWS
# --- Zobrist Hashing Keys ---
# This generates a unique set of random keys every time the program starts.
ZOBRIST_KEYS = generate_zobrist_keys()

RED = 'red'
WHITE = 'white'
# --- Pygame Display Colors ---
# Use these RGB tuples ONLY for drawing things on the screen.
COLOR_RED = (255, 0, 0)
COLOR_WHITE = (255, 255, 255)
PLAYER_NAMES = {RED: 'Red', WHITE: 'White'}
COLOR_CROWN = (255, 215, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_BG = (20, 20, 20)
COLOR_BUTTON = (100, 100, 100)
COLOR_BUTTON_HOVER = (150, 150, 150)
BLACK = (0, 0, 0)
GREY = (128, 128, 128)
YELLOW = (255, 255, 0) 
COORD_TO_ACF = {}
ACF_TO_COORD = {}
DARK_YELLOW = (200, 200, 0)
square_num = 1
for r in range(ROWS):
    for c in range(COLS):
        if (r + c) % 2 == 1:
            COORD_TO_ACF[(r, c)] = square_num
            ACF_TO_COORD[square_num] = (r, c)
            square_num += 1
