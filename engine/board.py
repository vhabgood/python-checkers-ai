# engine/board.py
import pygame
import logging
from .constants import BLACK, RED, WHITE, SQUARE_SIZE, COLS, ROWS, BOARD_SIZE
from .piece import Piece

logger = logging.getLogger('board')

class Board:
    def __init__(self):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.create_board()
        # Font for drawing board numbers
        self.number_font = pygame.font.SysFont(None, 18)
        logger.debug("Board initialized.")

    def create_board(self):
        self.board = []
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

    def draw_squares(self, screen, show_numbers=False):
        screen.fill(BLACK)
        for row in range(ROWS):
            for col in range(COLS):
                square_num = (row * 4) + (col // 2) + 1
                
                if (row + col) % 2 == 1:
                    pygame.draw.rect(screen, (181, 136, 99), (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
                    if show_numbers:
                        num_surf = self.number_font.render(str(square_num), True, (255, 255, 255))
                        screen.blit(num_surf, (col * SQUARE_SIZE + 2, row * SQUARE_SIZE + 2))
                else:
                    pygame.draw.rect(screen, (227, 206, 187), (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def get_piece(self, row, col):
        return self.board[row][col]
    
    def get_all_pieces(self, color):
        pieces = []
        for r_idx, row in enumerate(self.board):
            for c_idx, piece in enumerate(row):
                if piece != 0 and piece.color == color:
                    pieces.append(piece)
        return pieces

    def move(self, piece, row, col):
        self.board[piece.row][piece.col], self.board[row][col] = self.board[row][col], self.board[piece.row][piece.col]
        
        captured_piece = None
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

        piece.move(row, col)
        
        if row == 0 or row == ROWS - 1:
            if not piece.king:
                piece.make_king()
                if piece.color == WHITE:
                    self.white_kings += 1
                else:
                    self.red_kings += 1
        
        return captured_piece

    def draw(self, screen, show_numbers=False):
        self.draw_squares(screen, show_numbers)
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    piece.draw(screen)

    def get_all_valid_moves_for_color(self, color):
        """Gets all valid moves for a given color, respecting the forced jump rule."""
        moves = {}
        for piece in self.get_all_pieces(color):
            jumps = self._get_jumps_for_piece(piece.row, piece.col)
            if jumps:
                moves[(piece.row, piece.col)] = list(jumps.keys())
        
        if moves:
            return moves

        for piece in self.get_all_pieces(color):
            slides = self._get_slides_for_piece(piece.row, piece.col)
            if slides:
                moves[(piece.row, piece.col)] = list(slides.keys())

        return moves
        
    def _get_slides_for_piece(self, row, col):
        """Calculates all valid slide moves for a single piece."""
        moves = {}
        piece = self.get_piece(row, col)

        if piece.color == WHITE or piece.king:
            for r, c in [(row - 1, col - 1), (row - 1, col + 1)]:
                if 0 <= r < ROWS and 0 <= c < COLS and self.board[r][c] == 0:
                    moves[(r, c)] = []

        if piece.color == RED or piece.king:
            for r, c in [(row + 1, col - 1), (row + 1, col + 1)]:
                if 0 <= r < ROWS and 0 <= c < COLS and self.board[r][c] == 0:
                    moves[(r, c)] = []
        return moves

    def _get_jumps_for_piece(self, row, col):
        """Calculates all valid jump moves for a single piece."""
        moves = {}
        piece = self.get_piece(row, col)

        if piece.color == WHITE or piece.king:
            for (r_mid, c_mid), (r_end, c_end) in [((row - 1, col - 1), (row - 2, col - 2)), ((row - 1, col + 1), (row - 2, col + 2))]:
                if 0 <= r_end < ROWS and 0 <= c_end < COLS:
                    mid_piece = self.board[r_mid][c_mid]
                    end_piece = self.board[r_end][c_end]
                    if end_piece == 0 and mid_piece != 0 and mid_piece.color != piece.color:
                        moves[(r_end, c_end)] = [mid_piece]
        
        if piece.color == RED or piece.king:
            for (r_mid, c_mid), (r_end, c_end) in [((row + 1, col - 1), (row + 2, col - 2)), ((row + 1, col + 1), (row + 2, col + 2))]:
                if 0 <= r_end < ROWS and 0 <= c_end < COLS:
                    mid_piece = self.board[r_mid][c_mid]
                    end_piece = self.board[r_end][c_end]
                    if end_piece == 0 and mid_piece != 0 and mid_piece.color != piece.color:
                        moves[(r_end, c_end)] = [mid_piece]
        return moves
