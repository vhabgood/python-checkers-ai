# engine/piece.py
"""
Defines the Piece class, which represents a single checker on the board.
"""
import pygame
import math
from .constants import RED, WHITE, SQUARE_SIZE, GREY, COLOR_CROWN, BOARD_SIZE, ROWS, COLS

class Piece:
    """
    Represents a single checker piece, handling its own position and drawing.
    """
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
        """Calculates the screen x, y coordinates from the board row, col."""
        self.x = SQUARE_SIZE * self.col + SQUARE_SIZE // 2
        self.y = SQUARE_SIZE * self.row + SQUARE_SIZE // 2

    def make_king(self):
        """Promotes the piece to a king."""
        self.king = True

    def draw(self, screen, flipped=False):
        """Draws the piece on the screen, handling board orientation."""
        radius = SQUARE_SIZE // 2 - self.PADDING
        
        # Adjust draw coordinates if the board is flipped
        draw_x, draw_y = self.x, self.y
        if flipped:
            draw_x = BOARD_SIZE - self.x
            draw_y = BOARD_SIZE - self.y

        # Draw the piece as two concentric circles
        pygame.draw.circle(screen, GREY, (draw_x, draw_y), radius + self.OUTLINE)
        pygame.draw.circle(screen, self.color, (draw_x, draw_y), radius)
        
        # Draw a star if the piece is a king
        if self.king:
            self._draw_star(screen, draw_x, draw_y)

    def _draw_star(self, screen, x, y):
        """Draws a star in the center of the piece to indicate a king."""
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
        """Updates the piece's logical position and recalculates draw coordinates."""
        self.row = row
        self.col = col
        self.calc_pos()

    def __repr__(self):
        """String representation for debugging."""
        return str(self.color)
