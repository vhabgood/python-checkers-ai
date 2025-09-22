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
        board_logger.debug(f"Board state validated by {calling_function}.")

    def get_hash(self):
        return self.hash

    def _calculate_initial_hash(self):
        h = 0
        if not ZOBRIST_KEYS: return h
        for r, row in enumerate(self.board):
            for c, piece in enumerate(row):
                if piece != 0:
                    piece_char = ('R' if piece.king else 'r') if piece.color == RED else ('W' if piece.king else 'w')
                    h ^= ZOBRIST_KEYS.get((piece_char, COORD_TO_ACF.get((r, c))), 0)
        if self.turn == WHITE:
            h ^= ZOBRIST_KEYS.get('turn', 0)
        return h

    def _update_hash(self, move_path, captured_pieces, promotion_details):
        if not ZOBRIST_KEYS: return
        start_pos, end_pos = move_path[0], move_path[-1]
        piece = self.get_piece(end_pos[0], end_pos[1])
        promoted, original_king_status = promotion_details
        start_char = 'R' if original_king_status else ('r' if piece.color == RED else 'w')
        end_char = 'R' if piece.king else ('r' if piece.color == RED else 'w')
        self.hash ^= ZOBRIST_KEYS.get((start_char, COORD_TO_ACF.get(start_pos)), 0)
        self.hash ^= ZOBRIST_KEYS.get((end_char, COORD_TO_ACF.get(end_pos)), 0)
        for p, pos in captured_pieces:
            captured_char = 'R' if p.king else ('r' if p.color == RED else 'w')
            self.hash ^= ZOBRIST_KEYS.get((captured_char, COORD_TO_ACF.get(pos)), 0)
        self.hash ^= ZOBRIST_KEYS.get('turn', 0)

    def create_board(self):
        self.board = [[0] * COLS for _ in range(ROWS)]
        for row in range(ROWS):
            for col in range(COLS):
                if (row + col) % 2 == 1:
                    if row < 3: self.board[row][col] = Piece(row, col, WHITE)
                    elif row > 4: self.board[row][col] = Piece(row, col, RED)

    def create_board_from_fen(self, fen_string):
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.red_left, self.white_left, self.red_kings, self.white_kings = 0, 0, 0, 0
        match = re.search(r'\"(.*?)\"', fen_string)
        if not match: return
        core_fen = match.group(1).upper()
        parts = core_fen.split(':')
        self.turn = RED if parts[0] in ['B', 'R'] else WHITE
        for part in parts[1:]:
            color = RED if part.startswith('B') or part.startswith('R') else WHITE
            for pos_str in part[1:].split(','):
                if not pos_str: continue
                is_king = pos_str.startswith('K')
                digits = re.search(r'\d+', pos_str)
                if not digits: continue
                acf_num = int(digits.group(0))
                if acf_num not in ACF_TO_COORD: continue
                row, col = ACF_TO_COORD[acf_num]
                piece = Piece(row, col, color)
                if is_king:
                    piece.make_king()
                    if color == RED: self.red_kings += 1
                    else: self.white_kings += 1
                self.board[row][col] = piece
                if color == RED: self.red_left += 1
                else: self.white_left += 1
        self.hash = self._calculate_initial_hash()

    def get_fen(self, compact=False):
        turn = 'W' if self.turn == WHITE else 'R'
        r_m, r_k, w_m, w_k = [], [], [], []
        for r, row in enumerate(self.board):
            for c, p in enumerate(row):
                if p:
                    pos = COORD_TO_ACF.get((r, c))
                    if p.color == RED: (r_k if p.king else r_m).append(f"K{pos}" if p.king else str(pos))
                    else: (w_k if p.king else w_m).append(f"K{pos}" if p.king else str(pos))
        r_m.sort(key=int); w_m.sort(key=int)
        r_k.sort(key=lambda x: int(x[1:])); w_k.sort(key=lambda x: int(x[1:]))
        w_str = "W" + ",".join(w_m) + ("," if w_m and w_k else "") + ",".join(w_k)
        r_str = "R" + ",".join(r_m) + ("," if r_m and r_k else "") + ",".join(r_k)
        return f"{turn}:{w_str}:{r_str}"

    def get_piece(self, row, col):
        if 0 <= row < ROWS and 0 <= col < COLS: return self.board[row][col]
        return None

    def winner(self):
        if self.red_left <= 0: return WHITE
        if self.white_left <= 0: return RED
        return None

    def apply_move(self, path):
        # --- CRITICAL FIX: Use deepcopy to prevent object mutation ---
        new_board = copy.deepcopy(self)
        start_pos, end_pos = path[0], path[-1]
        
        piece = new_board.get_piece(start_pos[0], start_pos[1])

        # --- DEBUGGING TRAP ---
        assert isinstance(piece, Piece), f"Attempted to move a non-piece at {start_pos}"

        original_king_status = piece.king
        new_board.board[start_pos[0]][start_pos[1]] = 0
        new_board.board[end_pos[0]][end_pos[1]] = piece
        piece.move(end_pos[0], end_pos[1])
        
        captured_pieces = []
        if abs(start_pos[0] - end_pos[0]) >= 2:
            for i in range(len(path) - 1):
                r1, c1, r2, c2 = *path[i], *path[i+1]
                mid_r, mid_c = (r1 + r2) // 2, (c1 + c2) // 2
                captured = new_board.get_piece(mid_r, mid_c)
                if captured:
                    captured_pieces.append((captured, (mid_r, mid_c)))
                    new_board.board[mid_r][mid_c] = 0
                    if captured.color == RED: new_board.red_left -= 1
                    else: new_board.white_left -= 1
        
        promoted = False
        if (end_pos[0] == 0 and piece.color == RED and not original_king_status) or \
           (end_pos[0] == ROWS - 1 and piece.color == WHITE and not original_king_status):
            promoted = True
            piece.make_king()
            if piece.color == RED: new_board.red_kings += 1
            else: new_board.white_kings += 1
            
        new_board.turn = WHITE if new_board.turn == RED else RED
        new_board._update_hash(path, captured_pieces, (promoted, original_king_status))
        
        # --- DEBUGGING TRAP ---
        new_board._validate_board_state("apply_move")
        return new_board
        
    def get_valid_moves(self, piece):
        assert isinstance(piece, Piece), f"get_valid_moves called on a non-piece: {piece}"
        board_logger.debug(f"Getting valid moves for {piece.color} piece at ({piece.row}, {piece.col})")
        jumps = self._find_jumps(piece.row, piece.col, piece.king, piece.color, [])
        return jumps if jumps else self._find_simple_moves(piece.row, piece.col, piece.king, piece.color)

    def _find_simple_moves(self, r, c, is_king, color):
        moves, dirs = [], [(-1,-1),(-1,1),(1,-1),(1,1)]
        for dr, dc in dirs:
            if not is_king and ((color == RED and dr == 1) or (color == WHITE and dr == -1)): continue
            nr, nc = r+dr, c+dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and not self.get_piece(nr, nc): moves.append([(r,c),(nr,nc)])
        return moves

    def _find_jumps(self, r, c, is_king, color, path):
        paths, curr = [], path + [(r,c)]
        dirs = [(-2,-2),(-2,2),(2,-2),(2,2)]
        for dr, dc in dirs:
            if not is_king and ((color == RED and dr > 0) or (color == WHITE and dr < 0)): continue
            nr, nc = r+dr, c+dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and (nr,nc) not in path:
                mr, mc = (r+nr)//2, (c+nc)//2
                cap, land = self.get_piece(mr, mc), self.get_piece(nr, nc)
                if not land and cap and cap.color != color:
                    temp_b = copy.deepcopy(self) 
                    temp_b.board[mr][mc] = 0
                    further = temp_b._find_jumps(nr, nc, is_king, color, curr)
                    if further: paths.extend(further)
                    else: paths.append(curr + [(nr,nc)])
        return paths
