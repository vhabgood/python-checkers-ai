# engine/board.py
import pygame
import logging
import re
import copy
from .constants import ROWS, COLS, SQUARE_SIZE, RED, WHITE, COORD_TO_ACF, ACF_TO_COORD, ZOBRIST_KEYS
from .piece import Piece

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

    def copy(self):
        """
        Creates a deep, independent copy of the entire board state.
        """
        new_board = Board(db_conn=self.db_conn)
        new_board.board = copy.deepcopy(self.board)
        new_board.red_left = self.red_left
        new_board.white_left = self.white_left
        new_board.red_kings = self.red_kings
        new_board.white_kings = self.white_kings
        new_board.turn = self.turn
        new_board.hash = self.hash
        return new_board

    def _validate_board_state(self, calling_function=""):
        """
        A debugging trap that checks for inconsistencies in the board state.
        """
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r, c)
                if isinstance(piece, Piece):
                    error_msg = (
                        f"STATE CORRUPTION DETECTED in {calling_function}: "
                        f"Piece internal state ({piece.row},{piece.col}) does not match "
                        f"its grid position ({r},{c})."
                    )
                    assert (piece.row, piece.col) == (r, c), error_msg
      #  board_logger.debug(f"Board state validated by {calling_function}.")

    def get_hash(self):
        return self.hash

    def _calculate_initial_hash(self):
        h = 0
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r,c)
                if piece:
                    piece_char = ('R' if piece.king else 'r') if piece.color == RED else ('W' if piece.king else 'w')
                    acf_pos = COORD_TO_ACF.get((r, c))
                    if acf_pos:
                        h ^= ZOBRIST_KEYS.get((piece_char, acf_pos), 0)
        if self.turn == WHITE:
            h ^= ZOBRIST_KEYS.get('turn', 0)
        return h

    def _update_hash(self, move_path, captured_pieces):
        start_pos, end_pos = move_path[0], move_path[-1]
        piece = self.get_piece(end_pos[0], end_pos[1]) # Piece is already at the new position
        
        original_piece_char = ('R' if piece.king and not (piece.color == RED and end_pos[0] == 7) and not (piece.color == WHITE and end_pos[0] == 0) else 'r') if piece.color == RED else ('W' if piece.king and not (piece.color == WHITE and end_pos[0] == 0) and not (piece.color == RED and end_pos[0] == 7) else 'w')
        final_piece_char = ('R' if piece.king else 'r') if piece.color == RED else ('W' if piece.king else 'w')

        self.hash ^= ZOBRIST_KEYS.get((original_piece_char, COORD_TO_ACF.get(start_pos)), 0)
        self.hash ^= ZOBRIST_KEYS.get((final_piece_char, COORD_TO_ACF.get(end_pos)), 0)
        
        for (r,c), captured_char in captured_pieces:
             self.hash ^= ZOBRIST_KEYS.get((captured_char, COORD_TO_ACF.get((r,c))), 0)

        self.hash ^= ZOBRIST_KEYS.get('turn', 0)

    def draw(self, win):
        self.draw_squares(win)
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    piece.draw(win, row, col)

    def _move_piece(self, piece, row, col):
        self.board[piece.row][piece.col], self.board[row][col] = 0, self.board[piece.row][piece.col]
        piece.move(row, col)
        if (row == 7 and piece.color == RED) or (row == 0 and piece.color == WHITE):
            if not piece.king:
                piece.make_king()
                if piece.color == RED: self.red_kings += 1
                else: self.white_kings += 1

    def get_piece(self, row, col):
        if 0 <= row < ROWS and 0 <= col < COLS: return self.board[row][col]
        return None

    def create_board(self):
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        for row in range(ROWS):
            for col in range(COLS):
                if (row + col) % 2 == 1:
                    if row < 3: self.board[row][col] = Piece(row, col, RED)
                    elif row > 4: self.board[row][col] = Piece(row, col, WHITE)
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0

    def create_board_from_fen(self, fen_string):
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.red_left, self.white_left, self.red_kings, self.white_kings = 0, 0, 0, 0
        
        parts = re.match(r"([RW]):(W(?:[K]?\d+,?)+):(R(?:[K]?\d+,?)+)", fen_string)
        if not parts:
            board_logger.error(f"Invalid FEN string format: {fen_string}")
            self.create_board()
            return
        
        turn_char, white_pieces_str, red_pieces_str = parts.groups()
        self.turn = RED if turn_char == 'R' else WHITE
        
        for piece_str in white_pieces_str.strip('W').split(','):
            if not piece_str: continue
            is_king = 'K' in piece_str
            pos = int(piece_str.replace('K', ''))
            r, c = ACF_TO_COORD[pos]
            self.board[r][c] = Piece(r, c, WHITE)
            if is_king: self.board[r][c].make_king(); self.white_kings += 1
            self.white_left += 1

        for piece_str in red_pieces_str.strip('R').split(','):
            if not piece_str: continue
            is_king = 'K' in piece_str
            pos = int(piece_str.replace('K', ''))
            r, c = ACF_TO_COORD[pos]
            self.board[r][c] = Piece(r, c, RED)
            if is_king: self.board[r][c].make_king(); self.red_kings += 1
            self.red_left += 1

        self.hash = self._calculate_initial_hash()

    def get_fen(self, compact=False):
        red_men, red_kings, white_men, white_kings = [], [], [], []
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r, c)
                if piece:
                    acf_pos = COORD_TO_ACF.get((r, c))
                    if piece.color == RED:
                        if piece.king: red_kings.append(f"K{acf_pos}")
                        else: red_men.append(str(acf_pos))
                    else:
                        if piece.king: white_kings.append(f"K{acf_pos}")
                        else: white_men.append(str(acf_pos))
        
        turn_char = 'R' if self.turn == RED else 'W'
        white_str = "W" + ",".join(white_kings + white_men)
        red_str = "R" + ",".join(red_kings + red_men)
        
        return f"{turn_char}:{white_str}:{red_str}"

    def draw_squares(self, win):
        win.fill((40, 40, 40))
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(win, (120, 120, 120), (row*SQUARE_SIZE, col*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def remove(self, piece):
        piece_char = ('R' if piece.king else 'r') if piece.color == RED else ('W' if piece.king else 'w')
        self.board[piece.row][piece.col] = 0
        if piece.color == RED: self.red_left -= 1
        else: self.white_left -= 1
        return (piece.row, piece.col), piece_char

    def winner(self):
        if self.red_left <= 0: return WHITE
        if self.white_left <= 0: return RED
        return None

    def change_turn(self):
        self.turn = WHITE if self.turn == RED else RED

    def apply_move(self, path):
        new_board = self.copy()
        new_board.move(path)
        new_board._validate_board_state("apply_move")
        return new_board

    def move(self, path):
        piece = self.get_piece(path[0][0], path[0][1])
        if not piece:
            board_logger.error(f"Attempted to move a non-existent piece from {path[0]}.")
            return

        self._move_piece(piece, path[-1][0], path[-1][1])
        captured_pieces = []
        if len(path) > 1 and abs(path[0][0] - path[1][0]) == 2:
            for i in range(len(path) - 1):
                start_pos, end_pos = path[i], path[i+1]
                mid_row, mid_col = (start_pos[0] + end_pos[0]) // 2, (start_pos[1] + end_pos[1]) // 2
                captured_piece = self.get_piece(mid_row, mid_col)
                if captured_piece:
                    captured_data = self.remove(captured_piece)
                    captured_pieces.append(captured_data)
        
        self.change_turn()
        self._update_hash(path, captured_pieces)

    def get_valid_moves(self, piece):
      #  board_logger.debug(f"Getting valid moves for {piece.color} piece at ({piece.row}, {piece.col})")
        jumps = self._find_jumps(piece.row, piece.col, piece.king, piece.color, [])
        return jumps if jumps else self._find_simple_moves(piece.row, piece.col, piece.king, piece.color)

    def _find_simple_moves(self, r, c, is_king, color):
        moves, dirs = [], [(-1,-1),(-1,1),(1,-1),(1,1)]
        for dr, dc in dirs:
            if not is_king and ((color == RED and dr < 0) or (color == WHITE and dr > 0)):
                continue
            nr, nc = r+dr, c+dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and not self.get_piece(nr, nc):
                moves.append([(r,c),(nr,nc)])
        return moves

    def _find_jumps(self, r, c, is_king, color, path):
        paths, curr = [], path + [(r,c)]
        dirs = [(-2,-2),(-2,2),(2,-2),(2,2)]
        for dr, dc in dirs:
            if not is_king and ((color == RED and dr < 0) or (color == WHITE and dr > 0)):
                continue
            nr, nc = r+dr, c+dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and (nr,nc) not in path:
                mr, mc = (r+nr)//2, (c+nc)//2
                cap, land = self.get_piece(mr, mc), self.get_piece(nr, nc)
                if cap and cap.color != color and not land:
                    # This jump is valid, check for more from this new position
                    extended_paths = self._find_jumps(nr, nc, is_king, color, curr)
                    if extended_paths: paths.extend(extended_paths)
                    else: paths.append(curr + [(nr,nc)])
        return paths
