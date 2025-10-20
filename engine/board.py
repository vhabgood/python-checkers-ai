# engine/board.py
import pygame
import logging
import re
import copy
from .constants import (ROWS, COLS, SQUARE_SIZE, RED, WHITE,
                      COORD_TO_ACF, ACF_TO_COORD, COLOR_SQUARE_DARK, COLOR_SQUARE_LIGHT)
from .piece import Piece
from .zobrist import generate_zobrist_keys

ZOBRIST_KEYS = generate_zobrist_keys()
board_logger = logging.getLogger('board')

class Board:
    def __init__(self, db_conn=None):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.turn = RED
        self.db_conn = db_conn
        self.create_board()
        self.hash = self._calculate_initial_hash()

    def get_piece(self, row, col):
        if 0 <= row < ROWS and 0 <= col < COLS:
            return self.board[row][col]
        return None

    def get_all_pieces(self, color):
        pieces = []
        for row in self.board:
            for piece in row:
                if piece != 0 and piece.color == color:
                    pieces.append(piece)
        return pieces

    def create_board(self):
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        for row in range(ROWS):
            for col in range(COLS):
                if (row + col) % 2 == 1:
                    # FIX: White starts at the top (rows 0-2)
                    if row < 3: self.board[row][col] = Piece(row, col, WHITE)
                    # FIX: Red starts at the bottom (rows 5-7)
                    elif row > 4: self.board[row][col] = Piece(row, col, RED)
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0

    def create_board_from_fen(self, fen_string):
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        try:
            if fen_string.startswith('[FEN "'):
                fen_string = fen_string.split('"')[1]
            turn_char, white_pieces_str, red_pieces_str = fen_string.split(':')
            self.turn = WHITE if turn_char == 'W' else RED

            if len(white_pieces_str) > 1:
                for piece_str in white_pieces_str[1:].split(','):
                    if not piece_str: continue
                    is_king = 'K' in piece_str
                    pos = int(''.join(filter(str.isdigit, piece_str)))
                    r, c = ACF_TO_COORD[pos]
                    self.board[r][c] = Piece(r, c, WHITE)
                    if is_king: self.board[r][c].make_king()

            if len(red_pieces_str) > 1:
                for piece_str in red_pieces_str[1:].split(','):
                    if not piece_str: continue
                    is_king = 'K' in piece_str
                    pos = int(''.join(filter(str.isdigit, piece_str)))
                    r, c = ACF_TO_COORD[pos]
                    self.board[r][c] = Piece(r, c, RED)
                    if is_king: self.board[r][c].make_king()
        except Exception as e:
            board_logger.error(f"Invalid FEN string: {fen_string}. Error: {e}")
            self.create_board()
            self.hash = self._calculate_initial_hash()
            return

        self.red_left, self.white_left, self.red_kings, self.white_kings = 0, 0, 0, 0
        for row in self.board:
            for piece in row:
                if piece != 0:
                    if piece.color == RED:
                        self.red_left += 1
                        if piece.king: self.red_kings += 1
                    else:
                        self.white_left += 1
                        if piece.king: self.white_kings += 1
        self.hash = self._calculate_initial_hash()

    def get_fen(self):
        turn_char = 'W' if self.turn == WHITE else 'B'
        red_pieces, white_pieces = [], []
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r, c)
                if piece:
                    pos = COORD_TO_ACF.get((r, c))
                    if pos:
                        piece_str = f"K{pos}" if piece.king else str(pos)
                        if piece.color == RED: red_pieces.append(piece_str)
                        else: white_pieces.append(piece_str)
        red_pieces.sort(key=lambda x: int(x.lstrip('K')))
        white_pieces.sort(key=lambda x: int(x.lstrip('K')))
        return f"{turn_char}:W{','.join(white_pieces)}:R{','.join(red_pieces)}"

    def get_hash(self):
        return self.hash

    def _calculate_initial_hash(self):
        h = 0
        if self.turn == WHITE:
            h ^= ZOBRIST_KEYS['turn']
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r, c)
                if piece:
                    acf_pos = COORD_TO_ACF.get((r,c))
                    key = ('R' if piece.king else 'r') if piece.color == RED else ('W' if piece.king else 'w')
                    h ^= ZOBRIST_KEYS.get((key, acf_pos), 0)
        return h

    def copy(self):
        new_board = Board()
        new_board.board = copy.deepcopy(self.board)
        new_board.red_left, new_board.white_left = self.red_left, self.white_left
        new_board.red_kings, new_board.white_kings = self.red_kings, self.white_kings
        new_board.turn, new_board.hash = self.turn, self.hash
        return new_board

    def get_valid_moves(self, piece):
        """
        Returns a list of valid moves for a single piece.
        This now correctly delegates to the board-level function to enforce the
        "forced capture" rule across the entire board.
        """
        # Defer to the board-level move check.
        # This is crucial for correctly enforcing the "forced capture" rule.
        all_moves_for_turn = self.get_all_valid_moves(self.turn)
        
        # Filter the moves to only include those for the requested piece.
        return [move for move in all_moves_for_turn if move[0] == (piece.row, piece.col)]

    def _find_simple_moves(self, r, c, is_king, color):
        moves = []
        if is_king:
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        elif color == RED:
            # FIX: Red moves UP (row index decreases)
            directions = [(-1, -1), (-1, 1)]
        else: # WHITE
            # FIX: White moves DOWN (row index increases)
            directions = [(1, -1), (1, 1)]
            
        for dr, dc in directions:
            new_r, new_c = r + dr, c + dc
            if 0 <= new_r < 8 and 0 <= new_c < 8 and self.get_piece(new_r, new_c) == 0: # <-- THE FIX
                moves.append([(r, c), (new_r, new_c)])
        return moves

    def _find_jumps(self, r, c, is_king, color, path):
        paths = []
        current_path = path + [(r, c)]
        
        if is_king:
            directions = [(-2, -2), (-2, 2), (2, -2), (2, 2)]
        elif color == RED:
            # FIX: Red jumps UP (row index decreases)
            directions = [(-2, -2), (-2, 2)]
        else: # WHITE
            # FIX: White jumps DOWN (row index increases)
            directions = [(2, -2), (2, 2)]

        for dr, dc in directions:
            new_r, new_c = r + dr, c + dc
            
            if 0 <= new_r < 8 and 0 <= new_c < 8 and (new_r, new_c) not in path:
                mid_r, mid_c = (r + new_r) // 2, (c + new_c) // 2
                
                captured_piece = self.get_piece(mid_r, mid_c)
                landing_spot = self.get_piece(new_r, new_c)

                if captured_piece and captured_piece.color != color and landing_spot == 0: # <-- THE FIX
                    further_jumps = self._find_jumps(new_r, new_c, is_king, color, current_path)
                    if further_jumps:
                        paths.extend(further_jumps)
                    else:
                        paths.append(current_path + [(new_r, new_c)])
        return paths

    def apply_move(self, path):
        new_board = self.copy()
        new_board._execute_move(path)
        return new_board

    def _execute_move(self, path):
        piece = self.get_piece(path[0][0], path[0][1])
        self.board[path[0][0]][path[0][1]] = 0
        self.board[path[-1][0]][path[-1][1]] = piece
        piece.move(path[-1][0], path[-1][1])
        if abs(path[0][0] - path[1][0]) == 2:
            for i in range(len(path) - 1):
                mid_r, mid_c = (path[i][0] + path[i+1][0]) // 2, (path[i][1] + path[i+1][1]) // 2
                captured = self.get_piece(mid_r, mid_c)
                if captured: self.board[mid_r][mid_c] = 0
                if captured.color == RED: self.red_left -= 1
                else: self.white_left -= 1
        # FIX: Update the kinging rows to match the new setup
        if (path[-1][0] == 0 and piece.color == RED) or (path[-1][0] == ROWS - 1 and piece.color == WHITE):
            if not piece.king:
                piece.make_king()
                if piece.color == RED: self.red_kings += 1
                else: self.white_kings += 1
        self.change_turn()
        self.hash = self._calculate_initial_hash()

    def change_turn(self):
        self.turn = WHITE if self.turn == RED else RED

    def winner(self):
        if self.red_left <= 0: return WHITE
        if self.white_left <= 0: return RED
        if not self.get_all_valid_moves(self.turn): return WHITE if self.turn == RED else RED
        return None
    
    def get_all_valid_moves(self, color):
        """
        Returns a list of all valid moves for all pieces of a given color,
        with added debugging prints to trace the logic.
        """
        board_logger.debug(f"\n--- DEBUG: GETTING ALL MOVES FOR {color.upper()} ---")
        if color != self.turn:
            board_logger.error("DEBUG: Not this color's turn to move. Returning [].")
            return []

        all_moves = []
        pieces = self.get_all_pieces(color)
        board_logger.debug(f"DEBUG: Found {len(pieces)} pieces for {color.upper()}.")

        # Check for any possible jumps first
        board_logger.debug("DEBUG: Checking for jumps...")
        for piece in pieces:
            jumps = self._find_jumps(piece.row, piece.col, piece.king, piece.color, [])
            if jumps:
                board_logger.debug(f"DEBUG: Found {len(jumps)} jump(s) for piece at ({piece.row}, {piece.col}).")
                all_moves.extend(jumps)

        # If jumps were found, only they are legal moves
        if all_moves:
            board_logger.debug(f"DEBUG: Total jumps found: {len(all_moves)}. Returning ONLY jumps.")
            return all_moves

        # If no jumps were found, get all simple moves
        board_logger.debug("DEBUG: No jumps found. Checking for simple moves...")
        for piece in pieces:
            simple_moves = self._find_simple_moves(piece.row, piece.col, piece.king, piece.color)
            if simple_moves:
                board_logger.debug(f"DEBUG: Found {len(simple_moves)} simple move(s) for piece at ({piece.row}, {piece.col}).")
                all_moves.extend(simple_moves)
        
        board_logger.debug(f"DEBUG: Total simple moves found: {len(all_moves)}. Returning.")
        return all_moves
