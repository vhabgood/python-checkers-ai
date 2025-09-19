# engine/board.py
import pygame
import logging
import re
import copy
from .constants import ROWS, COLS, SQUARE_SIZE, RED, WHITE, COORD_TO_ACF, ACF_TO_COORD, ZOBRIST_KEYS
from .piece import Piece

board_logger = logging.getLogger('board')

class Board:
    """
    Represents the checkers board and manages all pieces and game logic,
    including move generation, piece placement, and database key creation.
    """
    def __init__(self, db_conn=None):
        """Initializes the board to the standard starting position."""
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.turn = RED
        self.db_conn = db_conn
        self.moves_since_progress = 0
        self.create_board()
        self.hash = self._calculate_initial_hash()

    def get_hash(self):
        """Returns the current Zobrist hash for the board state."""
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

    def _update_hash(self, move_path, piece, captured_pieces):
        """Updates the hash based on a move."""
        if not ZOBRIST_KEYS: return
        
        start_pos, end_pos = move_path[0], move_path[-1]
        start_acf, end_acf = COORD_TO_ACF.get(start_pos), COORD_TO_ACF.get(end_pos)
        
        # Determine piece characters, accounting for promotion
        is_promotion = (not piece.king) and (end_pos[0] == 0 or end_pos[0] == ROWS - 1)
        original_piece_char = ('r' if piece.color == RED else 'w') if is_promotion else \
                              (('R' if piece.king else 'r') if piece.color == RED else ('W' if piece.king else 'w'))
        final_piece_char = ('R' if piece.king else 'r') if piece.color == RED else ('W' if piece.king else 'w')
        
        self.hash ^= ZOBRIST_KEYS.get((original_piece_char, start_acf), 0)
        self.hash ^= ZOBRIST_KEYS.get((final_piece_char, end_acf), 0)

        for captured_piece, pos in captured_pieces:
            captured_char = ('R' if captured_piece.king else 'r') if captured_piece.color == RED else ('W' if captured_piece.king else 'w')
            captured_acf = COORD_TO_ACF.get(pos)
            if captured_acf:
                self.hash ^= ZOBRIST_KEYS.get((captured_char, captured_acf), 0)

        self.hash ^= ZOBRIST_KEYS.get('turn', 0)

    def get_fen(self):
        turn_char = 'W' if self.turn == WHITE else 'R'
        white_pieces, red_pieces = [], []
        for i in range(1, 33):
            r, c = ACF_TO_COORD[i]
            piece = self.get_piece(r,c)
            if piece != 0:
                pos = i
                fen_char = f"K{pos}" if piece.king else str(pos)
                if piece.color == WHITE:
                    white_pieces.append(fen_char)
                else:
                    red_pieces.append(fen_char)
        white_str = "W" + ",".join(white_pieces)
        red_str = "R" + ",".join(red_pieces)
        return f"{turn_char}:{white_str}:{red_str}"

    def __deepcopy__(self, memo):
        new_board = Board(db_conn=self.db_conn)
        memo[id(self)] = new_board
        for k, v in self.__dict__.items():
            if k != 'db_conn':
                setattr(new_board, k, copy.deepcopy(v, memo))
        return new_board

    def apply_move(self, path):
        new_board = copy.deepcopy(self)
        start_pos, end_pos = path[0], path[-1]
        piece = new_board.get_piece(start_pos[0], start_pos[1])

        if not piece: return new_board

        is_capture = abs(start_pos[0] - path[1][0]) == 2
        is_man_move = not piece.king
        captured_pieces_for_hash = []

        if is_capture or is_man_move:
            new_board.moves_since_progress = 0
        else:
            new_board.moves_since_progress += 1

        new_board.board[start_pos[0]][start_pos[1]] = 0
        new_board.board[end_pos[0]][end_pos[1]] = piece
        
        if is_capture:
            for i in range(len(path) - 1):
                jumped_pos = ((path[i][0] + path[i+1][0]) // 2, (path[i][1] + path[i+1][1]) // 2)
                jumped_piece = new_board.get_piece(jumped_pos[0], jumped_pos[1])
                if jumped_piece:
                    captured_pieces_for_hash.append((jumped_piece, jumped_pos))
                    if jumped_piece.color == RED: new_board.red_left -= 1
                    else: new_board.white_left -= 1
                    new_board.board[jumped_pos[0]][jumped_pos[1]] = 0
        
        # --- THE FIX: Update the hash BEFORE promotion ---
        # 1. Move the piece's internal coordinates
        piece.move(end_pos[0], end_pos[1])
        
        # 2. Update the hash based on this move
        new_board._update_hash(path, piece, captured_pieces_for_hash)
        
        # 3. NOW, handle promotion after the hash is correct
        was_king = piece.king
        if not was_king:
            if end_pos[0] == ROWS - 1 and piece.color == RED:
                piece.make_king(); new_board.red_kings += 1
            elif end_pos[0] == 0 and piece.color == WHITE:
                piece.make_king(); new_board.white_kings += 1
        
        new_board.turn = WHITE if self.turn == RED else RED
        return new_board

    def create_board(self):
        self.board = []
        for row in range(ROWS):
            self.board.append([0] * COLS)
            for col in range(COLS):
                if col % 2 == ((row + 1) % 2):
                    if row < 3: self.board[row][col] = Piece(row, col, RED)
                    elif row > 4: self.board[row][col] = Piece(row, col, WHITE)

    def create_board_from_fen(self, fen_string):
        self.board = []; self.red_left = self.white_left = 0; self.red_kings = self.white_kings = 0
        for _ in range(ROWS): self.board.append([0] * COLS)
        parts = fen_string.split(':')
        if len(parts) != 3: board_logger.error(f"Invalid FEN: {fen_string}"); self.create_board(); return
        turn_char, white_pieces_str, red_pieces_str = parts
        self.turn = WHITE if turn_char.upper() == 'W' else RED
        def place_pieces(piece_str, color):
            if not piece_str or len(piece_str) <= 1: return
            for p in piece_str[1:].split(','):
                p = p.strip();
                if not p: continue
                is_king = p.upper().startswith('K')
                try:
                    square_num = int(re.sub(r'\D', '', p))
                    if square_num not in ACF_TO_COORD: continue
                    row, col = ACF_TO_COORD[square_num]
                    piece = Piece(row, col, color)
                    if is_king:
                        piece.make_king()
                        if color == WHITE: self.white_kings += 1
                        else: self.red_kings += 1
                    self.board[row][col] = piece
                    if color == WHITE: self.white_left += 1
                    else: self.red_left += 1
                except (ValueError, KeyError) as e: board_logger.error(f"Invalid piece in FEN: '{p}' - {e}")
        place_pieces(white_pieces_str, WHITE); place_pieces(red_pieces_str, RED)
        self.hash = self._calculate_initial_hash()

    def get_piece(self, row, col):
        if 0 <= row < ROWS and 0 <= col < COLS: return self.board[row][col]
        return None

    def get_all_pieces(self, color):
        return [p for row in self.board for p in row if p != 0 and p.color == color]

    def _format_move_path(self, path):
        if not path: return ""
        separator = '-'
        if len(path) > 1 and abs(path[0][0] - path[1][0]) == 2:
            separator = 'x'
        return separator.join([str(COORD_TO_ACF.get(pos, "??")) for pos in path])

    def get_all_move_sequences(self, color, override_turn_check=False):
        if not override_turn_check and color != self.turn:
            board_logger.critical(f"FATAL: Move generation called for '{color}' but it is '{self.turn}'s turn!")
            return []
        all_paths, forced_jumps_found = [], False
        for piece in self.get_all_pieces(color):
            jumps = self._find_jump_sequences_for_piece(piece)
            if jumps: forced_jumps_found = True; all_paths.extend(jumps)
        
        if forced_jumps_found:
            formatted_jumps = [self._format_move_path(p) for p in all_paths]
            board_logger.debug(f"Forced jumps found: {formatted_jumps}")
            return all_paths
            
        for piece in self.get_all_pieces(color):
            for move in self._find_simple_moves(piece):
                all_paths.append([(piece.row, piece.col), move])
        return all_paths

    def _find_simple_moves(self, piece):
        moves = set()
        move_dirs = [(1, -1), (1, 1)] if piece.color == RED else [(-1, -1), (-1, 1)]
        if piece.king: move_dirs.extend([(-d[0], d[1]) for d in move_dirs] + [(d[0], -d[1]) for d in move_dirs])
        for dr, dc in set(move_dirs):
            nr, nc = piece.row + dr, piece.col + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and self.get_piece(nr, nc) == 0: moves.add((nr, nc))
        return list(moves)

    def _find_jump_sequences_for_piece(self, piece):
        all_jump_paths = []
        self._find_jumps_recursive(piece.row, piece.col, piece, [(piece.row, piece.col)], [], all_jump_paths)
        return all_jump_paths

    def _find_jumps_recursive(self, r, c, piece, current_path, captured, all_paths):
        found_next = False
        jump_dirs = [(-2,-2),(-2,2),(2,-2),(2,2)] if piece.king else ([(-2,-2),(-2,2)] if piece.color==WHITE else [(2,-2),(2,2)])
        for dr, dc in jump_dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and self.get_piece(nr, nc) == 0:
                jr, jc = r + dr // 2, c + dc // 2
                jumped = self.get_piece(jr, jc)
                if jumped != 0 and jumped.color != piece.color and (jr, jc) not in captured:
                    found_next = True
                    self._find_jumps_recursive(nr, nc, piece, current_path + [(nr, nc)], captured + [(jr, jc)], all_paths)
        if not found_next and len(current_path) > 1: all_paths.append(current_path)
            
    def winner(self):
        if self.red_left <= 0: return WHITE
        elif self.white_left <= 0: return RED
        if not self.get_all_move_sequences(self.turn): return WHITE if self.turn == RED else RED
        return None

    def draw(self, screen, font, show_numbers, flipped, valid_moves, last_move_path):
        self.draw_squares(screen)
        if last_move_path:
            for r_pos, c_pos in last_move_path:
                if r_pos is None or c_pos is None: continue
                r, c = (ROWS - 1 - r_pos, COLS - 1 - c_pos) if flipped else (r_pos, c_pos)
                pygame.draw.rect(screen, (50, 50, 0), (c*SQUARE_SIZE, r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        for row in self.board:
            for piece in row:
                if piece != 0: piece.draw(screen)
        if valid_moves:
            for move in valid_moves:
                r, c = (ROWS - 1 - move[0], COLS - 1 - move[1]) if flipped else move
                pygame.draw.circle(screen, (0, 150, 0), (c*SQUARE_SIZE + SQUARE_SIZE//2, r*SQUARE_SIZE + SQUARE_SIZE//2), 15)
        if show_numbers:
            for r, c in ACF_TO_COORD.values():
                num = COORD_TO_ACF.get((r,c))
                disp_r, disp_c = (ROWS - 1 - r, COLS - 1 - c) if flipped else (r, c)
                text = font.render(str(num), True, (200,200,200))
                screen.blit(text, (disp_c * SQUARE_SIZE + 5, disp_r * SQUARE_SIZE + 5))

    def draw_squares(self, win):
        win.fill((10, 10, 10))
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(win, (60, 60, 60), (row*SQUARE_SIZE, col*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        
    def _get_endgame_key(self):
        """
        Generates a key for querying the endgame database.
        Returns a tuple: (table_name, key_tuple) or (None, None).
        """
        piece_count = self.red_left + self.white_left
        if piece_count > 7: # Databases are for 7 pieces or fewer
            return None, None

        table_name = None
        # --- FIX: Corrected the table name to match the database schema ---
        if (self.white_left == 2 and self.white_kings == 2 and self.red_left == 1 and self.red_kings == 1) or \
           (self.red_left == 2 and self.red_kings == 2 and self.white_left == 1 and self.white_kings == 1):
            table_name = "db_2v1_kings" # <-- Corrected from "db_2Kv1K"
        
        # (You can add more 'elif' blocks here for your other database tables)
        
        if not table_name:
            return None, None

        # --- Generate the key tuple ---
        red_king_pos = []
        white_king_pos = []
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r, c)
                if piece and piece.king:
                    pos = COORD_TO_ACF.get((r, c))
                    if piece.color == RED:
                        red_king_pos.append(pos)
                    elif piece.color == WHITE:
                        white_king_pos.append(pos)
        
        red_king_pos.sort()
        white_king_pos.sort()
        
        key_tuple = tuple(white_king_pos + red_king_pos) + (self.turn,)
        
        board_logger.debug(f"Generated EGTB key: {key_tuple} for table {table_name}")
        return table_name, key_tuple
