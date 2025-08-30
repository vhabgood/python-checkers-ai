# engine/board.py
import pygame
import logging
import random
import copy
from .constants import BLACK, ROWS, COLS, SQUARE_SIZE, RED, WHITE, COORD_TO_ACF
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
        self.turn = RED
        self.create_board()
        self.zobrist_table = self._init_zobrist()
        self.hash = self._compute_hash()
        
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

    def draw(self, win, font, show_nums, flipped):
        """Draws the entire board and all pieces."""
        self.draw_squares(win)
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
        correctly enforcing the mandatory jump rule. Now with added logging.
        """
        moves = {}
        has_jumps = False
        
        logger.debug(f"GET_MOVES: Finding all possible jumps for {'White' if color == WHITE else 'Red'}.")
        for piece in self.get_all_pieces(color):
            jumps = self._get_moves_for_piece(piece, find_jumps=True)
            if jumps:
                has_jumps = True
                moves[(piece.row, piece.col)] = jumps
        
        if has_jumps:
            logger.debug(f"GET_MOVES: Jumps found. Returning only jump moves: {moves}")
            return moves

        logger.debug(f"GET_MOVES: No jumps found. Finding all slide moves for {'White' if color == WHITE else 'Red'}.")
        for piece in self.get_all_pieces(color):
            slides = self._get_moves_for_piece(piece, find_jumps=False)
            if slides:
                moves[(piece.row, piece.col)] = slides
        
        logger.debug(f"GET_MOVES: Slide moves found: {moves}")
        return moves

    def _get_moves_for_piece(self, piece, find_jumps):
        """
        Helper function to find all moves (jumps or slides) for a single piece.
        Now with added logging.
        """
        moves = {}
        step = 2 if find_jumps else 1
        
        move_type = "jumps" if find_jumps else "slides"
        piece_pos = COORD_TO_ACF.get((piece.row, piece.col), '?')
        logger.debug(f"GET_PIECE_MOVES: Finding {move_type} for piece at {piece_pos} ({piece.row}, {piece.col})")

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
                if dest_square == 0 and mid_square != 0 and mid_square.color != piece.color:
                    moves[(end_row, end_col)] = [mid_square]
            else:
                if dest_square == 0:
                    moves[(end_row, end_col)] = []
        
        if moves:
            logger.debug(f"GET_PIECE_MOVES: Found {len(moves)} {move_type} for piece at {piece_pos}: {moves.keys()}")
        return moves

    def apply_move(self, path):
        """
        Applies a full move sequence to a DEEP COPY of the board, flips the turn,
        and returns the new board state. This is used exclusively by the minimax
        search for simulating future turns.
        """
        # Create a completely independent copy of the board for simulation.
        temp_board = copy.deepcopy(self)
        
        # Get the piece from the starting position on the new board
        start_pos = path[0]
        piece_to_move = temp_board.get_piece(start_pos[0], start_pos[1])

        # It's possible for a path to be invalid during deep simulation; handle safely.
        if piece_to_move == 0:
            logger.error(f"APPLY_MOVE: Attempted to move from an empty square at {start_pos} for path {path}.")
            # Return the unchanged board to prevent a crash.
            return temp_board

        # Handle captures for the entire path
        captured_pieces = []
        for i in range(len(path) - 1):
            p_start, p_end = path[i], path[i+1]
            # A jump is a move of 2 rows
            if abs(p_start[0] - p_end[0]) == 2:
                mid_row = (p_start[0] + p_end[0]) // 2
                mid_col = (p_start[1] + p_end[1]) // 2
                captured = temp_board.get_piece(mid_row, mid_col)
                if captured:
                    captured_pieces.append(captured)
        
        if captured_pieces:
            temp_board._remove(captured_pieces)

        # Move the piece to its final destination
        final_pos = path[-1]
        temp_board.move(piece_to_move, final_pos[0], final_pos[1])
        
        # CRITICAL: After the move is complete, always flip the turn for the simulation.
        temp_board.turn = WHITE if temp_board.turn == RED else RED
        temp_board.hash ^= temp_board.zobrist_table['turn'] # Update the hash for the new turn

        return temp_board
    
    # Add this new method inside the Board class in engine/board.py

    def _simulate_path(self, path):
        """
        Simulates applying a path to a deep copy of the board WITHOUT changing the turn.
        This is used for internal checks, like finding multi-jumps.
        """
        temp_board = copy.deepcopy(self)
        for i in range(len(path) - 1):
            start_pos = path[i]
            end_pos = path[i+1]
            piece = temp_board.get_piece(start_pos[0], start_pos[1])
            if piece == 0: continue

            is_jump = abs(start_pos[0] - end_pos[0]) == 2
            if is_jump:
                captured_row = (start_pos[0] + end_pos[0]) // 2
                captured_col = (start_pos[1] + end_pos[1]) // 2
                captured_piece = temp_board.get_piece(captured_row, captured_col)
                if captured_piece != 0:
                    temp_board._remove([captured_piece])
            
            temp_board.move(piece, end_pos[0], end_pos[1])
        return temp_board
