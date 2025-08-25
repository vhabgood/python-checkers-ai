# engine/constants.py
import pygame

FPS = 60
DEFAULT_AI_DEPTH = 5
BOARD_SIZE = 480
INFO_WIDTH = 220
WIDTH, HEIGHT = BOARD_SIZE + INFO_WIDTH, BOARD_SIZE + 120
ROWS, COLS = 8, 8
SQUARE_SIZE = BOARD_SIZE // COLS
RED = (255, 0, 0)
WHITE = (255, 255, 255)
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
square_num = 1
for r in range(ROWS):
    for c in range(COLS):
        if (r + c) % 2 == 1:
            COORD_TO_ACF[(r, c)] = square_num
            ACF_TO_COORD[square_num] = (r, c)
            square_num += 1
