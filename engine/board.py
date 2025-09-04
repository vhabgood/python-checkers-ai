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
    def __init__(self, db_conn=None):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.turn = RED
        self.db_conn = db_conn
        self.create_board()
        self.zobrist_table = self._init_zobrist()
        self.hash = self._compute_hash()

    def __deepcopy__(self, memo):
        new_board = Board(db_conn=None)
        memo[id(self)] = new_board
        for k, v in self.__dict__.items():
            if k not in ['db_conn', 'zobrist_table']:
                setattr(new_board, k, copy.deepcopy(v, memo))
        new_board.db_conn = self.db_conn
        new_board.zobrist_table = self.zobrist_table
        return new_board

    def get_all_move_sequences(self, color):
        all_paths = []
        forced_jumps_found = False
        for piece in self.get_all_pieces(color):
            jumps = self._get_moves_for_piece(piece, find_jumps=True)
            if jumps:
                forced_jumps_found = True
                start_pos = (piece.row, piece.col)
                for end_pos in jumps:
                    initial_path = [start_pos, end_pos]
                    all_paths.extend(self._find_all_paths_from(initial_path))
        
        if forced_jumps_found:
            for path in all_paths: yield path
            return

        for piece in self.get_all_pieces(color):
            slides = self._get_moves_for_piece(piece, find_jumps=False)
            if slides:
                start_pos = (piece.row, piece.col)
                for end_pos in slides: yield [start_pos, end_pos]

    def _find_all_paths_from(self, current_path):
        """
        A recursive helper to find all possible multi-jump extensions from a given path.
        This corrected version properly simulates the board state at each jump segment.
        """
        paths = []
        last_pos = current_path[-1]

        # Create a temporary board reflecting the state *before* this next jump
        temp_board = copy.deepcopy(self)
        
        # Manually apply the move segments in the current path to the temp_board
        if len(current_path) > 1:
            start_piece = temp_board.get_piece(current_path[0][0], current_path[0][1])
            if start_piece == 0: return [current_path] # Should not happen
            
            captured_pieces = []
            for i in range(len(current_path) - 1):
                p_start, p_end = current_path[i], current_path[i+1]
                mid_row, mid_col = (p_start[0] + p_end[0]) // 2, (p_start[1] + p_end[1]) // 2
                captured = temp_board.get_piece(mid_row, mid_col)
                if captured: captured_pieces.append(captured)

            if captured_pieces: temp_board._remove(captured_pieces)
            temp_board.move(start_piece, last_pos[0], last_pos[1])
        
        # Now, from this new board state, find the next possible jumps
        moved_piece_on_temp_board = temp_board.get_piece(last_pos[0], last_pos[1])
        if moved_piece_on_temp_board == 0: return [current_path]

        more_jumps = temp_board._get_moves_for_piece(moved_piece_on_temp_board, find_jumps=True)

        if not more_jumps:
            paths.append(current_path) # This is the end of a jump sequence
        else:
            for next_pos in more_jumps:
                new_path = current_path + [next_pos]
                # The recursive call must be on the original board `self`
                paths.extend(self._find_all_paths_from(new_path))
        return paths

    def apply_move(self, path):
        temp_board = copy.deepcopy(self)
        start_pos = path[0]
        piece_to_move = temp_board.get_piece(start_pos[0], start_pos[1])
        if piece_to_move == 0: return temp_board
        
        captured_pieces = []
        for i in range(len(path) - 1):
            p_start, p_end = path[i], path[i+1]
            if abs(p_start[0] - p_end[0]) == 2:
                mid_row, mid_col = (p_start[0] + p_end[0]) // 2, (p_start[1] + p_end[1]) // 2
                captured = temp_board.get_piece(mid_row, mid_col)
                if captured: captured_pieces.append(captured)
        
        if captured_pieces: temp_board._remove(captured_pieces)
        
        final_pos = path[-1]
        temp_board.move(piece_to_move, final_pos[0], final_pos[1])
        temp_board.turn = WHITE if self.turn == RED else RED
        temp_board.hash ^= self.zobrist_table['turn']
        return temp_board

    def _init_zobrist(self):
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
        self.board = []
        for row in range(ROWS):
            self.board.append([])
            for col in range(COLS):
                if col % 2 == ((row + 1) % 2):
                    if row < 3: self.board[row].append(Piece(row, col, RED))
                    elif row > 4: self.board[row].append(Piece(row, col, WHITE))
                    else: self.board[row].append(0)
                else: self.board[row].append(0)

    def draw_squares(self, win):
        win.fill(BLACK)
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(win, (60,60,60), (row * SQUARE_SIZE, col * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def move(self, piece, row, col):
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
        for piece in pieces:
            if piece is not None and piece != 0:
                key = (piece.row, piece.col, piece.color, piece.king)
                self.hash ^= self.zobrist_table[key]
                self.board[piece.row][piece.col] = 0
                if piece.color == RED: self.red_left -= 1
                else: self.white_left -= 1
    
    def get_piece(self, row, col):
        return self.board[row][col]

    def get_all_pieces(self, color):
        pieces = []
        for row in self.board:
            for piece in row:
                if piece != 0 and piece.color == color:
                    pieces.append(piece)
        return pieces

    def winner(self):
        if self.red_left <= 0: return WHITE
        if self.white_left <= 0: return RED
        if not list(self.get_all_move_sequences(self.turn)):
            return WHITE if self.turn == RED else RED
        return None

    def draw(self, win, font, show_nums, flipped, valid_moves, last_move_path=None):
        self.draw_squares(win)
        if last_move_path:
            start_coord, end_coord = last_move_path[0], last_move_path[-1]
            if start_coord and end_coord:
                start_highlight = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                start_highlight.fill((200, 200, 60, 70))
                win.blit(start_highlight, (start_coord[1] * SQUARE_SIZE, start_coord[0] * SQUARE_SIZE))
                end_highlight = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                end_highlight.fill((200, 200, 60, 120))
                win.blit(end_highlight, (end_coord[1] * SQUARE_SIZE, end_coord[0] * SQUARE_SIZE))
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
        for r in range(ROWS):
            for c in range(COLS):
                if c % 2 == ((r + 1) % 2):
                    num = COORD_TO_ACF.get((r,c), "")
                    text = font.render(str(num), True, (200,200,200))
                    draw_r, draw_c = (ROWS - 1 - r, COLS - 1 - c) if flipped else (r, c)
                    win.blit(text, (draw_c * SQUARE_SIZE + 5, draw_r * SQUARE_SIZE + 5))

    def get_all_valid_moves(self, color):
        moves = {}
        all_move_sequences = list(self.get_all_move_sequences(color))
        if not all_move_sequences: return {}
        
        for path in all_move_sequences:
            start_pos, end_pos = path[0], path[-1]
            if start_pos not in moves:
                moves[start_pos] = set()
            moves[start_pos].add(end_pos)
            
        return moves

    def _get_moves_for_piece(self, piece, find_jumps):
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

    def _get_endgame_key(self):
        total_pieces = self.red_left + self.white_left
        if total_pieces > 8:
            return None, None

        w_men, w_kings, r_men, r_kings = 0, 0, 0, 0
        white_king_pos, red_king_pos, white_men_pos, red_men_pos = [], [], [], []
        
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r,c)
                if piece != 0:
                    pos_acf = COORD_TO_ACF.get((r,c))
                    if piece.color == WHITE:
                        if piece.king: w_kings += 1; white_king_pos.append(pos_acf)
                        else: w_men += 1; white_men_pos.append(pos_acf)
                    else: # RED
                        if piece.king: r_kings += 1; red_king_pos.append(pos_acf)
                        else: r_men += 1; red_men_pos.append(pos_acf)
        
        logger.debug(f"DB_KEY_GEN: Checking board state. R:{r_kings}K,{r_men}M W:{w_kings}K,{w_men}M")

        table_name = None
        key_tuple = None
        turn_char = 'w' if self.turn == WHITE else 'r'
        
        # --- FINAL, CORRECTED KEY LOGIC - Based on all Generator Scripts ---
        kings = {r_kings, w_kings}
        men = {r_men, w_men}
        
        # Case 1: Pure Kings vs Kings -> ( (r_kings_tuple), (w_kings_tuple), turn )
        if men == {0} and kings in [{4,3}, {4,2}, {3,3}, {3,2}, {3,1}, {2,1}, {2,2}]:
            key_tuple = (tuple(sorted(red_king_pos)), tuple(sorted(white_king_pos)), turn_char)
            if kings == {4,3}: table_name = "db_4v3_kings"
            elif kings == {4,2}: table_name = "db_4v2_kings"
            elif kings == {3,3}: table_name = "db_3v3_kings"
            elif kings == {3,2}: table_name = "db_3v2_kings"
            elif kings == {3,1}: table_name = "db_3v1_kings"
            elif kings == {2,1}: table_name = "db_2v1_kings"
            elif kings == {2,2}: table_name = "db_2v2_kings"

        # Case 2: Pure Men vs Men -> (stronger_men_tuple, weaker_man_tuple, turn)
        elif kings == {0} and men == {2,1}:
            table_name = "db_2v1_men"
            if r_men > w_men: key_tuple = tuple(sorted(red_men_pos)) + tuple(white_men_pos) + (turn_char,)
            else: key_tuple = tuple(sorted(white_men_pos)) + tuple(red_men_pos) + (turn_char,)
        
        # Case 3: Mixed pieces (each has a unique flat tuple structure)
        elif r_kings == 2 and r_men == 1 and w_kings == 2 and w_men == 1: 
            table_name = "db_2k1m_vs_2k1m"
            key_tuple = tuple(sorted(red_king_pos)) + tuple(red_men_pos) + tuple(sorted(white_king_pos)) + tuple(white_men_pos) + (turn_char,)
        elif r_kings == 2 and r_men == 1 and w_kings == 3 and w_men == 0:
            table_name = "db_2k1m_vs_3k"
            key_tuple = tuple(sorted(red_king_pos)) + tuple(red_men_pos) + tuple(sorted(white_king_pos)) + (turn_char,)
        elif r_kings == 3 and r_men == 0 and w_kings == 2 and w_men == 1:
            table_name = "db_2k1m_vs_3k"
            key_tuple = tuple(sorted(white_king_pos)) + tuple(white_men_pos) + tuple(sorted(red_king_pos)) + (turn_char,)
        elif r_kings == 2 and r_men == 1 and w_kings == 2 and w_men == 0:
            table_name = "db_2k1m_vs_2k"
            key_tuple = tuple(sorted(red_king_pos)) + tuple(red_men_pos) + tuple(sorted(white_king_pos)) + (turn_char,)
        elif r_kings == 2 and r_men == 0 and w_kings == 2 and w_men == 1:
            table_name = "db_2k1m_vs_2k"
            key_tuple = tuple(sorted(white_king_pos)) + tuple(white_men_pos) + tuple(sorted(red_king_pos)) + (turn_char,)
        elif r_kings == 3 and r_men == 1 and w_kings == 3 and w_men == 0:
            table_name = "db_3k1m_vs_3k"
            key_tuple = tuple(sorted(red_king_pos)) + tuple(red_men_pos) + tuple(sorted(white_king_pos)) + (turn_char,)
        elif r_kings == 3 and r_men == 0 and w_kings == 3 and w_men == 1:
            table_name = "db_3k1m_vs_3k"
            key_tuple = tuple(sorted(white_king_pos)) + tuple(white_men_pos) + tuple(sorted(red_king_pos)) + (turn_char,)
        elif r_kings == 3 and r_men == 0 and w_kings == 1 and w_men == 1:
            table_name = "db_3kv1k1m"
            key_tuple = tuple(sorted(red_king_pos)) + tuple(sorted(white_king_pos)) + tuple(white_men_pos) + (turn_char,)
        elif r_kings == 1 and r_men == 1 and w_kings == 3 and w_men == 0:
            table_name = "db_3kv1k1m"
            key_tuple = tuple(sorted(white_king_pos)) + tuple(sorted(red_king_pos)) + tuple(red_men_pos) + (turn_char,)

        if table_name is None:
            logger.debug("DB_KEY_GEN: Board state does not match any known endgame database.")
            return None, None

        # --- FIX: Convert the tuple to a string exactly as the create_db script does, preserving spaces ---
        key_string = str(key_tuple)
        
        logger.debug(f"DB_KEY_GEN: Match found! Table='{table_name}', Key='{key_string}'")
        return table_name, key_string
