# engine/piece.py
import pygame
import math
from .constants import RED, WHITE, SQUARE_SIZE, GREY, COLOR_CROWN

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
        """Calculates the screen x, y coordinates based on board row, col."""
        self.x = SQUARE_SIZE * self.col + SQUARE_SIZE // 2
        self.y = SQUARE_SIZE * self.row + SQUARE_SIZE // 2

    def make_king(self):
        """Makes this piece a king."""
        self.king = True

    def draw(self, screen):
        """Draws the piece on the screen."""
        radius = SQUARE_SIZE // 2 - self.PADDING
        pygame.draw.circle(screen, GREY, (self.x, self.y), radius + self.OUTLINE)
        pygame.draw.circle(screen, self.color, (self.x, self.y), radius)
        if self.king:
            self._draw_star(screen)

    def _draw_star(self, screen):
        """Draws a star in the center of the piece to indicate a king."""
        star_radius = self.PADDING
        num_points = 5
        points = []
        for i in range(num_points * 2):
            r = star_radius if i % 2 == 0 else star_radius / 2.5
            angle = math.pi / num_points * i - math.pi / 2
            x = self.x + r * math.cos(angle)
            y = self.y + r * math.sin(angle)
            points.append((x, y))
        pygame.draw.polygon(screen, COLOR_CROWN, points)

    def move(self, row, col):
        """Updates the piece's position."""
        self.row = row
        self.col = col
        self.calc_pos()

    def __repr__(self):
        """String representation of the piece."""
        return str(self.color)
