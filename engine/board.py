# engine/board.py
import pygame
import logging
from .constants import BLACK, ROWS, COLS, SQUARE_SIZE, RED, WHITE
from .piece import Piece

logger = logging.getLogger('board')

class Board:
    """
    Manages the board state, including piece positions, move generation,
    and applying moves. This class is the ultimate authority on the rules of the game.
    """
    def __init__(self):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.turn = RED # Red always starts in checkers
        self.create_board()
        logger.debug("Board initialized.")

    def create_board(self):
        """
        Initializes the 2D list representing the board and places
        the pieces in their starting positions.
        """
        for row in range(ROWS):
            self.board.append([])
            for col in range(COLS):
                if col % 2 == ((row + 1) % 2):
                    if row < 3:
                        self.board[row].append(Piece(row, col, RED))
                    elif row > 4:
                        self.board[row].append(Piece(row, col, WHITE))
                    else:
                        self.board[row].append(0)
                else:
                    self.board[row].append(0)

    def draw_squares(self, win):
        """Draws the checkerboard pattern of squares."""
        win.fill(BLACK)
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(win, (60,60,60), (row * SQUARE_SIZE, col * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def move(self, piece, row, col):
        """
        The master function for moving a piece. It updates both the board grid
        and the piece's internal state, and handles king promotion. This ensures
        the game state remains consistent.
        """
        # Swap the piece's location on the board grid
        self.board[piece.row][piece.col], self.board[row][col] = self.board[row][col], self.board[piece.row][piece.col]
        # Update the piece's internal row and column attributes
        piece.move(row, col)
        # Check for and apply kinging
        if row == ROWS - 1 or row == 0:
            if not piece.king:
                piece.make_king()
                if piece.color == WHITE:
                    self.white_kings += 1
                else:
                    self.red_kings += 1

    def _remove(self, pieces):
        """
        Removes a list of captured pieces from the board and updates
        the count of remaining pieces.
        """
        for piece in pieces:
            # Set the square on the board grid to be empty (0)
            self.board[piece.row][piece.col] = 0
            # Decrement the count of remaining pieces
            if piece is not None and piece != 0:
                if piece.color == RED:
                    self.red_left -= 1
                else:
                    self.white_left -= 1
    
    def get_piece(self, row, col):
        """Returns the piece object at a given row and col."""
        return self.board[row][col]

    def get_all_pieces(self, color):
        """Returns a list of all piece objects of a given color."""
        pieces = []
        for row in self.board:
            for piece in row:
                if piece != 0 and piece.color == color:
                    pieces.append(piece)
        return pieces

    def _get_slides_for_piece(self, row, col):
        """
        Calculates all possible non-capture (slide) moves for a piece.
        Returns a list of destination coordinates.
        """
        piece = self.get_piece(row, col)
        if piece == 0:
            return []
        
        moves = []
        directions = []
        if piece.color == WHITE or piece.king:
            directions.extend([(-1, -1), (-1, 1)])
        if piece.color == RED or piece.king:
            directions.extend([(1, -1), (1, 1)])

        for dr, dc in directions:
            end_row, end_col = row + dr, col + dc
            if 0 <= end_row < ROWS and 0 <= end_col < COLS and self.board[end_row][end_col] == 0:
                moves.append((end_row, end_col))
        return moves

    def _get_jumps_for_piece(self, row, col):
        """
        Calculates all possible capture (jump) moves for a piece.
        Returns a dictionary mapping destination coordinates to the piece(s) that would be captured.
        """
        piece = self.get_piece(row, col)
        if piece == 0:
            return {}
        
        jumps = {}
        directions = []
        if piece.color == WHITE or piece.king:
            directions.extend([-1])
        if piece.color == RED or piece.king:
            directions.extend([1])

        for direction in directions:
            for d_col in [-1, 1]:
                jumped_row, jumped_col = row + direction, col + d_col
                end_row, end_col = row + 2 * direction, col + 2 * d_col
                
                if 0 <= end_row < ROWS and 0 <= end_col < COLS:
                    jumped_piece = self.get_piece(jumped_row, jumped_col)
                    end_square = self.get_piece(end_row, end_col)

                    if jumped_piece != 0 and jumped_piece.color != piece.color and end_square == 0:
                        jumps[(end_row, end_col)] = [jumped_piece]
        return jumps

    def _get_valid_moves_for_piece(self, piece):
        """
        Returns all valid moves for a single piece, enforcing the mandatory jump rule.
        If a jump is available, only jumps are returned. Otherwise, slides are returned.
        """
        jumps = self._get_jumps_for_piece(piece.row, piece.col)
        if jumps:
            return jumps
        
        slides = self._get_slides_for_piece(piece.row, piece.col)
        # Slides need to be returned in the same dictionary format as jumps for consistency
        return {move: [] for move in slides}

    def get_all_valid_moves_for_color(self, color):
        """
        Aggregates all valid moves for all pieces of a given color.
        Returns the data in a dictionary format that the AI and game engine need:
        { (start_pos): { (end_pos): [captured_pieces] }, ... }
        """
        moves = {}
        pieces = self.get_all_pieces(color)
        for piece in pieces:
            valid_moves_for_piece = self._get_valid_moves_for_piece(piece)
            if valid_moves_for_piece:
                moves[(piece.row, piece.col)] = valid_moves_for_piece
        return moves

    def evaluate(self):
        """
        The board's evaluation function. Provides a score for the current
        board state, used by the AI to determine the best move.
        A positive score favors White, a negative score favors Red.
        """
        return (self.white_left - self.red_left) + (self.white_kings * 0.5 - self.red_kings * 0.5)

    def winner(self):
        """
        Determines if there is a winner by checking the number of pieces left
        or if a player has no more valid moves.
        """
        if self.red_left <= 0:
            return WHITE
        elif self.white_left <= 0:
            return RED
        
        if not self.get_all_valid_moves_for_color(self.turn):
            return WHITE if self.turn == RED else RED
        
        return None

    def draw(self, win, font, show_nums, flipped):
        """The main drawing function for the board and all pieces."""
        self.draw_squares(win)
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    draw_row, draw_col = (ROWS - 1 - row, COLS - 1 - col) if flipped else (row, col)
                    piece.draw(win) # Pieces draw themselves based on their internal x, y
        if show_nums:
            self._draw_board_numbers(win, font, flipped)

    def _draw_board_numbers(self, win, font, flipped):
        """Draws the algebraic notation numbers on the board squares."""
        for r in range(ROWS):
            for c in range(COLS):
                if c % 2 == ((r + 1) % 2):
                    num = r * 4 + c // 2 + 1
                    text = font.render(str(num), True, (200,200,200))
                    draw_r, draw_c = (ROWS - 1 - r, COLS - 1 - c) if flipped else (r, c)
                    win.blit(text, (draw_c * SQUARE_SIZE + 5, draw_r * SQUARE_SIZE + 5))
