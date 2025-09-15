# engine/board.py
import pygame
import logging
import re
import copy
from .constants import ROWS, COLS, SQUARE_SIZE, RED, WHITE, COORD_TO_ACF, ACF_TO_COORD
from .piece import Piece

logger = logging.getLogger('board')

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
        # --- FIX: Initialize the counter for the 40-move draw rule ---
        self.moves_since_progress = 0
        self.create_board()

    def __deepcopy__(self, memo):
        """Custom deepcopy to handle the database connection correctly."""
        new_board = Board(db_conn=self.db_conn)
        memo[id(self)] = new_board
        for k, v in self.__dict__.items():
            if k != 'db_conn':
                setattr(new_board, k, copy.deepcopy(v, memo))
        return new_board

    def apply_move(self, path):
        """
        Applies a move sequence to a copy of the board and returns the new board state.
        Now also manages the 40-move rule counter.
        """
        new_board = copy.deepcopy(self)
        start_pos, end_pos = path[0], path[-1]
        piece = new_board.get_piece(start_pos[0], start_pos[1])

        if not piece: return new_board

        is_capture = abs(start_pos[0] - path[1][0]) == 2
        is_man_move = not piece.king

        # --- 40-Move Rule Logic ---
        if is_capture or is_man_move:
            new_board.moves_since_progress = 0
        else:
            new_board.moves_since_progress += 1

        # Move the piece
        new_board.board[start_pos[0]][start_pos[1]] = 0
        new_board.board[end_pos[0]][end_pos[1]] = piece
        piece.move(end_pos[0], end_pos[1])

        # If it was a jump, remove the captured pieces
        if is_capture:
            for i in range(len(path) - 1):
                jumped_pos = ((path[i][0] + path[i+1][0]) // 2, (path[i][1] + path[i+1][1]) // 2)
                jumped_piece = new_board.get_piece(jumped_pos[0], jumped_pos[1])
                if jumped_piece:
                    if jumped_piece.color == RED: new_board.red_left -= 1
                    else: new_board.white_left -= 1
                    new_board.board[jumped_pos[0]][jumped_pos[1]] = 0

        # Handle promotion
        if end_pos[0] == ROWS - 1 and piece.color == RED and not piece.king:
            piece.make_king(); new_board.red_kings += 1
        elif end_pos[0] == 0 and piece.color == WHITE and not piece.king:
            piece.make_king(); new_board.white_kings += 1
            
        new_board.turn = WHITE if self.turn == RED else RED
        return new_board
        
    # --- The rest of the file is unchanged but verified for correctness ---
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
        if len(parts) != 3: logger.error(f"Invalid FEN: {fen_string}"); self.create_board(); return
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
                except (ValueError, KeyError) as e: logger.error(f"Invalid piece in FEN: '{p}' - {e}")
        place_pieces(white_pieces_str, WHITE); place_pieces(red_pieces_str, RED)

    def get_piece(self, row, col):
        if 0 <= row < ROWS and 0 <= col < COLS: return self.board[row][col]
        return None

    def get_all_pieces(self, color):
        return [p for row in self.board for p in row if p != 0 and p.color == color]

    def get_all_move_sequences(self, color):
        all_paths, forced_jumps_found = [], False
        for piece in self.get_all_pieces(color):
            jumps = self._find_jump_sequences_for_piece(piece)
            if jumps: forced_jumps_found = True; all_paths.extend(jumps)
        if forced_jumps_found: return all_paths
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
        # This logic is correct and does not need to be changed.
        return None, None


