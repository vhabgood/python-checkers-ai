# engine/piece.py
import pygame
import math
from .constants import SQUARE_SIZE, GREY, COLOR_CROWN, BOARD_SIZE

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

    def calc_pos(self):
        self.x = SQUARE_SIZE * self.col + SQUARE_SIZE // 2
        self.y = SQUARE_SIZE * self.row + SQUARE_SIZE // 2

    def make_king(self):
        self.king = True

    def draw(self, screen, flipped=False):
        radius = SQUARE_SIZE // 2 - self.PADDING
        draw_x, draw_y = self.x, self.y
        if flipped:
            draw_x = BOARD_SIZE - self.x
            draw_y = BOARD_SIZE - self.y
        pygame.draw.circle(screen, GREY, (draw_x, draw_y), radius + self.OUTLINE)
        pygame.draw.circle(screen, self.color, (draw_x, draw_y), radius)
        if self.king:
            self._draw_star(screen, draw_x, draw_y)

    def _draw_star(self, screen, x, y):
        star_radius = self.PADDING
        num_points = 5
        points = []
        for i in range(num_points * 2):
            r = star_radius if i % 2 == 0 else star_radius / 2.5
            angle = math.pi / num_points * i - math.pi / 2
            point_x = x + r * math.cos(angle)
            point_y = y + r * math.sin(angle)
            points.append((point_x, point_y))
        pygame.draw.polygon(screen, COLOR_CROWN, points)

    def move(self, row, col):
        self.row = row
        self.col = col
        self.calc_pos()

    def __repr__(self):
        return str(self.color)