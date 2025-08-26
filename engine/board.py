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
        
            # --- ZOBRIST HASHING ---
    def _init_zobrist(self):
        """
        Initializes the Zobrist table with random 64-bit numbers for each
        possible piece at each possible square.
        """
        table = {}
        # For each square, for each piece type (red/white, man/king)
        for r in range(ROWS):
            for c in range(COLS):
                for color in [RED, WHITE]:
                    for is_king in [True, False]:
                        table[(r, c, color, is_king)] = random.getrandbits(64)
        # Add a value for whose turn it is
        table['turn'] = random.getrandbits(64)
        return table

    def _compute_hash(self):
        """
        Calculates the initial Zobrist hash for the starting board position.
        This is only done once; the hash is updated incrementally afterwards.
        """
        h = 0
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r, c)
                if piece != 0:
                    h ^= self.zobrist_table[(r, c, piece.color, piece.king)]
        if self.turn == WHITE:
            h ^= self.zobrist_table['turn']
        return h
    # --- END ZOBRIST HASHING ---

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
        The master move function, now with incremental hash updates.
        """
        # --- HASH UPDATE ---
        # 1. XOR out the piece from its old position
        self.hash ^= self.zobrist_table[(piece.row, piece.col, piece.color, piece.king)]
        # ---
        
        self.board[piece.row][piece.col] = 0
        self.board[row][col] = piece
        
        was_king = piece.king
        piece.move(row, col)

        if row == ROWS - 1 or row == 0:
            if not piece.king:
                piece.make_king()
                if piece.color == WHITE: self.white_kings += 1
                else: self.red_kings += 1
        
        # --- HASH UPDATE ---
        # 2. XOR in the piece at its new position, considering if it became a king
        if not was_king and piece.king:
            self.hash ^= self.zobrist_table[(row, col, piece.color, True)]
        else:
            self.hash ^= self.zobrist_table[(row, col, piece.color, piece.king)]
        # ---

    def _remove(self, pieces):
        """
        Removes captured pieces, now with incremental hash updates.
        """
        for piece in pieces:
            if piece is not None and piece != 0:
                # --- HASH UPDATE ---
                # XOR out the captured piece from its position
                self.hash ^= self.zobrist_table[(piece.row, piece.col, piece.color, piece.king)]
                # ---
                self.board[piece.row][piece.col] = 0
                if piece.color == RED: self.red_left -= 1
                else: self.white_left -= 1
    
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
        
        if not self.get_all_valid_moves(self.turn):
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
                    
                    # ADD THIS ENTIRE BLOCK OF NEW FUNCTIONS TO board.py

    def _find_moves(self, row, col, color, is_king, step):
        """
        A helper function that explores possible moves (slides or jumps) for a piece.
        'step' determines the move type: 1 for a slide, 2 for a jump.
        """
        moves = {}
        directions = []
        
        if color == RED or is_king:
            directions.extend([(1, -1), (1, 1)]) # Down-left, Down-right
        if color == WHITE or is_king:
            directions.extend([(-1, -1), (-1, 1)]) # Up-left, Up-right
            
        for dr, dc in directions:
            end_row, end_col = row + dr * step, col + dc * step
            
            if not (0 <= end_row < ROWS and 0 <= end_col < COLS):
                continue # Skip moves that go off the board

            dest_square = self.get_piece(end_row, end_col)
            
            # --- Slide Logic (step=1) ---
            if step == 1:
                if dest_square == 0:
                    moves[(end_row, end_col)] = [] # Empty list for no capture
            
            # --- Jump Logic (step=2) ---
            elif step == 2:
                mid_row, mid_col = row + dr, col + dc
                mid_square = self.get_piece(mid_row, mid_col)
                
                # A jump is valid if the destination is empty and the middle has an opponent piece
                if dest_square == 0 and mid_square != 0 and mid_square.color != color:
                    moves[(end_row, end_col)] = [mid_square] # List contains the captured piece
                    
        return moves
   
# --- New, Final Move Generation Logic ---

    def get_all_valid_moves(self, color):
        """
        The single authoritative function to get all valid moves for a color.
        It correctly enforces the mandatory jump rule for the entire team.
        """
        moves = {}
        has_jumps = False

        # First, check if any piece has a jump available.
        for piece in self.get_all_pieces(color):
            jumps = self._get_moves_for_piece(piece, find_jumps=True)
            if jumps:
                has_jumps = True
                moves[(piece.row, piece.col)] = jumps
        
        # If any jump was found, only jumps are legal moves.
        if has_jumps:
            return moves

        # If no jumps were found for any piece, then find all slides.
        for piece in self.get_all_pieces(color):
            slides = self._get_moves_for_piece(piece, find_jumps=False)
            if slides:
                moves[(piece.row, piece.col)] = slides
                
        return moves

    def _get_moves_for_piece(self, piece, find_jumps):
        """
        The core helper function to find all moves (jumps or slides) for one piece.
        """
        moves = {}
        step = 2 if find_jumps else 1
        
        directions = []
        if piece.color == RED or piece.king:
            directions.extend([(1, -1), (1, 1)])  # Down-left, Down-right
        if piece.color == WHITE or piece.king:
            directions.extend([(-1, -1), (-1, 1)])  # Up-left, Up-right
            
        for dr, dc in directions:
            end_row, end_col = piece.row + dr * step, piece.col + dc * step
            
            if not (0 <= end_row < ROWS and 0 <= end_col < COLS):
                continue

            dest_square = self.get_piece(end_row, end_col)

            if find_jumps:
                mid_row, mid_col = piece.row + dr, piece.col + dc
                mid_square = self.get_piece(mid_row, mid_col)
                if dest_square == 0 and mid_square != 0 and mid_square.color != piece.color:
                    moves[(end_row, end_col)] = [mid_square]
            else: # Find slides
                if dest_square == 0:
                    moves[(end_row, end_col)] = [] # Empty list for no capture
                    
        return moves

    



        
 
