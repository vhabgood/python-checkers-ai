# engine/board.py
import pygame
import logging
import random
import copy
import os
import pickle
from .constants import BLACK, ROWS, COLS, SQUARE_SIZE, RED, WHITE, COORD_TO_ACF
from .piece import Piece

logger = logging.getLogger('board')

class Board:
    """
    Manages the board state, including piece positions, move generation,
    and applying moves. This class is the ultimate authority on the rules of the game.
    """
    # --- THIS IS THE FIX ---
    # The __init__ method is now updated to accept keyword arguments (kwargs)
    # for the endgame and opening book databases.
    def __init__(self):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.turn = RED
        self.create_board()
        self.zobrist_table = self._init_zobrist()
        self.hash = self._compute_hash()
        self.history = [copy.deepcopy(self.board)]
        
    @staticmethod
    def load_databases(status_queue):
        """Loads all endgame database files."""
        db_path = "resources/"
        databases = {}
        
        db_files = {
            "db_2v1_kings.pkl": "EGTB_2v1_KINGS",
            "db_2v1_men.pkl": "EGTB_2v1_MEN",
            "db_3v1_kings.pkl": "EGTB_3v1_KINGS",
            "db_3v2_kings.pkl": "EGTB_3v2_KINGS",
            "db_3v1k1m.pkl": "EGTB_3v1K1M",
            "db_2k1m_vs_2k.pkl": "EGTB_2K1Mv2K",
            "db_4v2_kings.pkl": "EGTB_4v2_KINGS",
            "db_2k1m_vs_3k.pkl": "EGTB_2K1Mv3K",
            "db_3v3_kings.pkl": "EGTB_3v3_KINGS",
            "db_2k1m_vs_2k1m.pkl": "EGTB_2K1Mv2K1M",
            "db_4v3_kings.pkl": "EGTB_4v3_KINGS",
            "custom_book.pkl": "OPENING_BOOK"
        }

        for filename, attr_name in db_files.items():
            filepath = os.path.join(db_path, filename)
            status_queue.put(f"Loading {filename}")
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    databases[attr_name] = pickle.load(f)
                status_queue.put(f"Loaded {filename}")
            else:
                logger.warning(f"Database file not found: {filepath}")
                databases[attr_name] = {}

        return databases

    def _init_zobrist(self):
        """Initializes the Zobrist table with random numbers."""
        table = {}
        for r in range(ROWS):
            for c in range(COLS):
                for color in [RED, WHITE]:
                    for is_king in [True, False]:
                        key = (r, c, color, is_king)
                        table[key] = random.getrandbits(64)
        table['turn'] = random.getrandbits(64)
        return table

    def _compute_hash(self):
        """Calculates the initial Zobrist hash for the board."""
        h = 0
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r, c)
                if piece != 0:
                    key = (r, c, piece.color, piece.king)
                    h ^= self.zobrist_table[key]
        if self.turn == WHITE:
            h ^= self.zobrist_table['turn']
        return h

    def create_board(self):
        """Initializes the board with pieces in their starting positions."""
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

    def draw_squares(self, win):
        """Draws the checkerboard pattern."""
        win.fill(BLACK)
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(win, (60,60,60), (row * SQUARE_SIZE, col * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def move(self, piece, row, col):
        """
        Moves a piece on the board and updates its state. This modifies the
        current board object.
        """
        old_key = (piece.row, piece.col, piece.color, piece.king)
        self.hash ^= self.zobrist_table[old_key]
        
        self.board[piece.row][piece.col] = 0
        self.board[row][col] = piece
        
        was_king = piece.king
        piece.move(row, col)

        if (row == ROWS - 1 or row == 0) and not was_king:
            piece.make_king()
            if piece.color == WHITE: self.white_kings += 1
            else: self.red_kings += 1
        
        new_key = (row, col, piece.color, piece.king)
        self.hash ^= self.zobrist_table[new_key]
        
        self.history.append(copy.deepcopy(self.board))

    def _remove(self, pieces):
        """Removes pieces from the board (after a capture)."""
        for piece in pieces:
            if piece is not None and piece != 0:
                key = (piece.row, piece.col, piece.color, piece.king)
                self.hash ^= self.zobrist_table[key]
                self.board[piece.row][piece.col] = 0
                if piece.color == RED: self.red_left -= 1
                else: self.white_left -= 1
    
    def get_piece(self, row, col):
        """Returns the piece object at a given location."""
        return self.board[row][col]

    def get_all_pieces(self, color):
        """Returns a list of all pieces of a given color."""
        pieces = []
        for row in self.board:
            for piece in row:
                if piece != 0 and piece.color == color:
                    pieces.append(piece)
        return pieces

    def winner(self):
        """Determines if there is a winner."""
        if self.red_left <= 0: return WHITE
        if self.white_left <= 0: return RED
        if not self.get_all_valid_moves(self.turn):
            return WHITE if self.turn == RED else RED
        return None

    def draw(self, win, font, show_nums, flipped, valid_moves):
        """Draws the entire board and all pieces."""
        self.draw_squares(win)

        if valid_moves:
            for move in valid_moves:
                row, col = move
                highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                highlight_surface.fill((60, 120, 200, 100))
                win.blit(highlight_surface, (col * SQUARE_SIZE, row * SQUARE_SIZE))

        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    piece.draw(win)
        
        if show_nums:
            self._draw_board_numbers(win, font, flipped)

    def _draw_board_numbers(self, win, font, flipped):
        """Draws the algebraic notation numbers on the board."""
        for r in range(ROWS):
            for c in range(COLS):
                if c % 2 == ((r + 1) % 2):
                    num = r * 4 + c // 2 + 1
                    text = font.render(str(num), True, (200,200,200))
                    draw_r, draw_c = (ROWS - 1 - r, COLS - 1 - c) if flipped else (r, c)
                    win.blit(text, (draw_c * SQUARE_SIZE + 5, draw_r * SQUARE_SIZE + 5))

    def get_all_valid_moves(self, color):
        """
        The single authoritative function to get all valid moves for a color,
        correctly enforcing the mandatory jump rule.
        """
        moves = {}
        has_jumps = False
        
        for piece in self.get_all_pieces(color):
            jumps = self._get_moves_for_piece(piece, find_jumps=True)
            if jumps:
                has_jumps = True
                moves[(piece.row, piece.col)] = jumps
        
        if has_jumps:
            return moves

        for piece in self.get_all_pieces(color):
            slides = self._get_moves_for_piece(piece, find_jumps=False)
            if slides:
                moves[(piece.row, piece.col)] = slides
        
        return moves

    def _get_moves_for_piece(self, piece, find_jumps):
        """
        Helper function to find all moves (jumps or slides) for a single piece.
        """
        moves = {}
        step = 2 if find_jumps else 1
        
        directions = []
        if piece.color == RED or piece.king:
            directions.extend([(1, -1), (1, 1)])
        if piece.color == WHITE or piece.king:
            directions.extend([(-1, -1), (-1, 1)])
            
        for dr, dc in directions:
            end_row, end_col = piece.row + dr * step, piece.col + dc * step
            
            if not (0 <= end_row < ROWS and 0 <= end_col < COLS):
                continue

            dest_square = self.get_piece(end_row, end_col)

            if find_jumps:
                mid_row, mid_col = piece.row + dr, piece.col + dc
                mid_square = self.get_piece(mid_row, mid_col)
                if dest_square == 0 and isinstance(mid_square, Piece) and mid_square.color != piece.color:
                    moves[(end_row, end_col)] = [mid_square]
            else:
                if dest_square == 0:
                    moves[(end_row, end_col)] = []
        
        return moves
        
    def recalculate_pieces(self):
        """Recalculates piece and king counts directly from the board state."""
        self.red_left = self.white_left = 0
        self.red_kings = self.white_kings = 0
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r,c)
                if piece != 0:
                    if piece.color == RED:
                        self.red_left += 1
                        if piece.king: self.red_kings += 1
                    else:
                        self.white_left += 1
                        if piece.king: self.white_kings += 1
