# engine/piece.py
import pygame
import math
from .constants import SQUARE_SIZE, GREY, DARK_YELLOW, RED, COLOR_RED, COLOR_WHITE

class Piece:
    PADDING = 15
    OUTLINE = 2

    def __init__(self, row, col, color):
        self.row = row
        self.col = col
        self.color = color
        self.king = False
        self.x = 0
        self.y = 0
        self.calc_pos()

    def copy(self):
        """Creates a new, independent Piece instance with the same attributes."""
        new_piece = Piece(self.row, self.col, self.color)
        new_piece.king = self.king
        return new_piece

    def calc_pos(self):
        self.x = SQUARE_SIZE * self.col + SQUARE_SIZE // 2
        self.y = SQUARE_SIZE * self.row + SQUARE_SIZE // 2

    def make_king(self):
        self.king = True

    def move(self, row, col):
        self.row = row
        self.col = col
        self.calc_pos()

    def draw(self, win, r, c):
        self.x = SQUARE_SIZE * c + SQUARE_SIZE // 2
        self.y = SQUARE_SIZE * r + SQUARE_SIZE // 2
        radius = SQUARE_SIZE // 2 - self.PADDING
        display_color = COLOR_RED if self.color == RED else COLOR_WHITE
        pygame.draw.circle(win, GREY, (self.x, self.y), radius + self.OUTLINE)
        pygame.draw.circle(win, display_color, (self.x, self.y), radius)
        if self.king:
            num_points = 5
            outer_radius = radius - 8
            inner_radius = outer_radius // 2
            angle = math.pi / num_points
            points = []
            for i in range(num_points * 2):
                rad = outer_radius if i % 2 == 0 else inner_radius
                current_angle = i * angle - (math.pi / 2)
                x = self.x + rad * math.cos(current_angle)
                y = self.y + rad * math.sin(current_angle)
                points.append((x, y))
            pygame.draw.polygon(win, DARK_YELLOW, points)
