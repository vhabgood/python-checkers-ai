# engine/board.py
"""
Defines the Board class, which represents the game board, manages piece
layout, move validation, and drawing.
"""
import pygame
import logging
from .constants import BLACK, RED, WHITE, SQUARE_SIZE, COLS, ROWS
from .piece import Piece

logger = logging.getLogger('board')

class Board:
    """
    Represents the game board, managing piece layout, moves, and drawing.
    """
    def __init__(self):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.create_board()
        self.number_font = pygame.font.SysFont(None, 18)
        logger.debug("Board initialized.")

    def create_board(self):
        """
        Initializes the board with pieces in their starting positions
        and resets all piece counts.
        """
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        for row in range(ROWS):
            self.board.append([])
            for col in range(COLS):
                if col % 2 == ((row + 1) % 2): # This formula finds the dark squares
                    if row < 3:
                        self.board[row].append(Piece(row, col, RED))
                    elif row > 4:
                        self.board[row].append(Piece(row, col, WHITE))
                    else:
                        self.board[row].append(0) # Empty square
                else:
                    self.board[row].append(0) # Empty square

    def draw_squares(self, screen, show_numbers=False, flipped=False):
        """Draws the checkerboard squares."""
        screen.fill(BLACK)
        for row in range(ROWS):
            for col in range(COLS):
                square_num = (row * 4) + (col // 2) + 1
                
                # Remap draw coordinates if the board is flipped
                draw_row, draw_col = (ROWS - 1 - row, COLS - 1 - col) if flipped else (row, col)
                
                if (row + col) % 2 == 1: # Dark squares
                    pygame.draw.rect(screen, (181, 136, 99), (draw_col * SQUARE_SIZE, draw_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
                    if show_numbers:
                        num_surf = self.number_font.render(str(square_num), True, (255, 255, 255))
                        screen.blit(num_surf, (draw_col * SQUARE_SIZE + 2, draw_row * SQUARE_SIZE + 2))
                else: # Light squares
                    pygame.draw.rect(screen, (227, 206, 187), (draw_col * SQUARE_SIZE, draw_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def get_piece(self, row, col):
        """Gets a piece object from a given row and column."""
        return self.board[row][col]
    
    def get_all_pieces(self, color):
        """Gets a list of all piece objects for a given color."""
        pieces = []
        for row in self.board:
            for piece in row:
                if piece != 0 and piece.color == color:
                    pieces.append(piece)
        return pieces

    def move(self, piece, row, col):
        """Moves a piece on the board and handles captures."""
        # Swap the piece with the empty square in the board list
        self.board[piece.row][piece.col], self.board[row][col] = self.board[row][col], self.board[piece.row][piece.col]
        
        captured_piece = None
        # If the move was a jump, remove the captured piece
        if abs(piece.row - row) == 2:
            middle_row = (piece.row + row) // 2
            middle_col = (piece.col + col) // 2
            captured = self.board[middle_row][middle_col]
            if captured != 0:
                captured_piece = captured
                self.board[middle_row][middle_col] = 0
                if captured.color == RED:
                    self.red_left -= 1
                else:
                    self.white_left -= 1

        # Update the piece's internal position
        piece.move(row, col)
        
        # Check for king promotion
        if row == 0 or row == ROWS - 1:
            if not piece.king:
                piece.make_king()
                if piece.color == WHITE:
                    self.white_kings += 1
                else:
                    self.red_kings += 1
        
        return captured_piece

    def draw(self, screen, number_font, show_numbers=False, flipped=False):
        """Draws the entire board, including squares and pieces."""
        self.draw_squares(screen, number_font, show_numbers, flipped)
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    piece.draw(screen, flipped)

    def get_all_valid_moves_for_color(self, color):
        """
        Gets all valid moves for a given color, correctly enforcing the
        forced jump rule.
        """
        moves = {}
        # First, find all possible jumps for every piece of the given color.
        for piece in self.get_all_pieces(color):
            jumps = self._get_jumps_for_piece(piece.row, piece.col)
            if jumps:
                moves[(piece.row, piece.col)] = list(jumps.keys())
        
        # If any jumps were found, they are the only legal moves.
        if moves:
            return moves

        # If no jumps were found, find all simple slide moves.
        for piece in self.get_all_pieces(color):
            slides = self._get_slides_for_piece(piece.row, piece.col)
            if slides:
                moves[(piece.row, piece.col)] = list(slides.keys())

        return moves
        
    def _get_slides_for_piece(self, row, col):
        """Calculates all valid slide moves for a single piece."""
        moves = {}
        piece = self.get_piece(row, col)

        # Check moves towards top of board (for White men and all Kings)
        if piece.color == WHITE or piece.king:
            for r, c in [(row - 1, col - 1), (row - 1, col + 1)]:
                if 0 <= r < ROWS and 0 <= c < COLS and self.board[r][c] == 0:
                    moves[(r, c)] = []

        # Check moves towards bottom of board (for Red men and all Kings)
        if piece.color == RED or piece.king:
            for r, c in [(row + 1, col - 1), (row + 1, col + 1)]:
                if 0 <= r < ROWS and 0 <= c < COLS and self.board[r][c] == 0:
                    moves[(r, c)] = []
        return moves

    def _get_jumps_for_piece(self, row, col):
        """Calculates all valid jump moves for a single piece."""
        moves = {}
        piece = self.get_piece(row, col)

        # Check jumps towards top of board (for White men and all Kings)
        if piece.color == WHITE or piece.king:
            for (r_mid, c_mid), (r_end, c_end) in [((row - 1, col - 1), (row - 2, col - 2)), ((row - 1, col + 1), (row - 2, col + 2))]:
                if 0 <= r_end < ROWS and 0 <= c_end < COLS:
                    mid_piece = self.board[r_mid][c_mid]
                    end_piece = self.board[r_end][c_end]
                    # A jump is valid if the destination is empty and the middle square has an opponent's piece.
                    if end_piece == 0 and mid_piece != 0 and mid_piece.color != piece.color:
                        moves[(r_end, c_end)] = [mid_piece]
        
        # Check jumps towards bottom of board (for Red men and all Kings)
        if piece.color == RED or piece.king:
            for (r_mid, c_mid), (r_end, c_end) in [((row + 1, col - 1), (row + 2, col - 2)), ((row + 1, col + 1), (row + 2, col + 2))]:
                if 0 <= r_end < ROWS and 0 <= c_end < COLS:
                    mid_piece = self.board[r_mid][c_mid]
                    end_piece = self.board[r_end][c_end]
                    if end_piece == 0 and mid_piece != 0 and mid_piece.color != piece.color:
                        moves[(r_end, c_end)] = [mid_piece]
        return moves
