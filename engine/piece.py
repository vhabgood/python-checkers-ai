# engine/piece.py
import pygame
from .constants import RED, WHITE, SQUARE_SIZE, GREY, CROWN

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
            screen.blit(CROWN, (self.x - CROWN.get_width() // 2, self.y - CROWN.get_height() // 2))

    def move(self, row, col):
        """Updates the piece's position."""
        self.row = row
        self.col = col
        self.calc_pos()

    def __repr__(self):
        """String representation of the piece."""
        return str(self.color)
