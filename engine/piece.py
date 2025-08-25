# engine/piece.py
import pygame
import math
from .constants import SQUARE_SIZE, CROWN, GREY, YELLOW

class Piece:
    """
    Represents a single checker piece on the board.
    Manages its own position, color, king status, and drawing.
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
        """Calculates the screen x, y coordinates based on the piece's row and col."""
        self.x = SQUARE_SIZE * self.col + SQUARE_SIZE // 2
        self.y = SQUARE_SIZE * self.row + SQUARE_SIZE // 2

    def make_king(self):
        """Promotes the piece to a king."""
        self.king = True

    def move(self, row, col):
        """
        Updates the piece's internal row and column. This is critical for keeping
        the piece's state consistent with its position on the main board array.
        """
        self.row = row
        self.col = col
        self.calc_pos()

    def draw(self, win):
        """Draws the piece on the screen, adding a star if it's a king."""
        radius = SQUARE_SIZE // 2 - self.PADDING
        # Draw the outline circle
        pygame.draw.circle(win, GREY, (self.x, self.y), radius + self.OUTLINE)
        # Draw the main piece circle
        pygame.draw.circle(win, self.color, (self.x, self.y), radius)
        
        # If the piece is a king, draw a star on top of it.
        if self.king:
            # --- Star Drawing Logic ---
            num_points = 5
            outer_radius = radius - 8
            inner_radius = outer_radius // 2
            angle = math.pi / num_points
            
            points = []
            for i in range(num_points * 2):
                # Alternate between outer and inner radius
                r = outer_radius if i % 2 == 0 else inner_radius
                # Calculate the x, y coordinate for the point
                current_angle = i * angle - (math.pi / 2) # Start at the top
                x = self.x + r * math.cos(current_angle)
                y = self.y + r * math.sin(current_angle)
                points.append((x, y))

            # Draw the star polygon
            pygame.draw.polygon(win, YELLOW, points)

    def __repr__(self):
        """Provides a simple string representation for the piece object, useful for debugging."""
        return str(self.color)
