# engine/board.py
import pygame
import logging
import random
import copy
from .constants import ROWS, COLS, SQUARE_SIZE, RED, WHITE, COORD_TO_ACF
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

    def __deepcopy__(self, memo):
        new_board = Board(db_conn=self.db_conn)
        memo[id(self)] = new_board
        for k, v in self.__dict__.items():
            if k != 'db_conn':
                setattr(new_board, k, copy.deepcopy(v, memo))
        return new_board

    def get_all_move_sequences(self, color):
        all_paths = []
        forced_jumps_found = False
        for piece in self.get_all_pieces(color):
            jumps = self._get_moves_for_piece(piece, find_jumps=True)
            if jumps:
                forced_jumps_found = True
                all_paths.extend(jumps)
        
        if forced_jumps_found:
            return all_paths

        for piece in self.get_all_pieces(color):
            moves = self._get_moves_for_piece(piece, find_jumps=False)
            all_paths.extend(moves)
        return all_paths

    def _get_moves_for_piece(self, piece, find_jumps):
        paths = []
        if find_jumps:
            self._find_jump_sequences(piece.row, piece.col, piece, [], paths)
        else:
            simple_moves = self._find_simple_moves(piece)
            for move in simple_moves:
                paths.append([(piece.row, piece.col), move])
        return paths

    def _find_simple_moves(self, piece):
        moves = set()
        move_dirs = [(1, -1), (1, 1)] if piece.color == RED else [(-1, -1), (-1, 1)]
        if piece.king:
            move_dirs.extend([(-d[0], -d[1]) for d in move_dirs])

        for dr, dc in move_dirs:
            new_row, new_col = piece.row + dr, piece.col + dc
            if 0 <= new_row < ROWS and 0 <= new_col < COLS and self.get_piece(new_row, new_col) == 0:
                moves.add((new_row, new_col))
        return moves

    def _find_jump_sequences(self, row, col, piece, current_path, all_paths):
        start_pos = (row, col)
        if not current_path:
            current_path = [start_pos]

        jump_dirs = [(2, -2), (2, 2)] if piece.color == RED else [(-2, -2), (-2, 2)]
        if piece.king:
            jump_dirs.extend([(-d[0], -d[1]) for d in jump_dirs])

        found_next_jump = False
        for dr, dc in jump_dirs:
            new_row, new_col = row + dr, col + dc
            
            temp_board_state = [row[:] for row in self.board]
            for i in range(1, len(current_path)):
                p_start = current_path[i-1]
                p_end = current_path[i]
                jumped_r, jumped_c = (p_start[0] + p_end[0]) // 2, (p_start[1] + p_end[1]) // 2
                temp_board_state[jumped_r][jumped_c] = 0

            if 0 <= new_row < ROWS and 0 <= new_col < COLS and temp_board_state[new_row][new_col] == 0:
                jumped_row, jumped_col = row + dr // 2, col + dc // 2
                jumped_piece = temp_board_state[jumped_row][jumped_col]
                if jumped_piece != 0 and jumped_piece.color != piece.color:
                    found_next_jump = True
                    new_path = current_path + [(new_row, new_col)]
                    self._find_jump_sequences(new_row, new_col, piece, new_path, all_paths)

        if not found_next_jump and len(current_path) > 1:
            all_paths.append(current_path)

    def apply_move(self, path):
        new_board = copy.deepcopy(self)
        start_pos = path[0]
        end_pos = path[-1]
        piece = new_board.get_piece(start_pos[0], start_pos[1])

        if not piece: return new_board

        new_board.board[start_pos[0]][start_pos[1]] = 0
        new_board.board[end_pos[0]][end_pos[1]] = piece
        piece.move(end_pos[0], end_pos[1])

        if abs(start_pos[0] - path[1][0]) == 2: # It's a jump
            for i in range(len(path) - 1):
                jumped_pos = ((path[i][0] + path[i+1][0]) // 2, (path[i][1] + path[i+1][1]) // 2)
                jumped_piece = new_board.get_piece(jumped_pos[0], jumped_pos[1])
                if jumped_piece:
                    if jumped_piece.color == RED: new_board.red_left -= 1
                    else: new_board.white_left -= 1
                    new_board.board[jumped_pos[0]][jumped_pos[1]] = 0

        if end_pos[0] == ROWS - 1 and piece.color == RED and not piece.king:
            piece.make_king(); new_board.red_kings += 1
        elif end_pos[0] == 0 and piece.color == WHITE and not piece.king:
            piece.make_king(); new_board.white_kings += 1
            
        new_board.turn = WHITE if self.turn == RED else RED
        return new_board

    def get_piece(self, row, col):
        if 0 <= row < ROWS and 0 <= col < COLS:
            return self.board[row][col]
        return None

    def create_board(self):
        for row in range(ROWS):
            self.board.append([])
            for col in range(COLS):
                if col % 2 == ((row + 1) % 2):
                    if row < 3: self.board[row].append(Piece(row, col, RED))
                    elif row > 4: self.board[row].append(Piece(row, col, WHITE))
                    else: self.board[row].append(0)
                else: self.board[row].append(0)

    def draw(self, screen, font, show_numbers, flipped, valid_moves, last_move_path):
        self.draw_squares(screen)
    
        if last_move_path:
        	# last_move_path is a list of tuples, e.g., [(start_r, start_c), (end_r, end_c)]
        	for r_pos, c_pos in last_move_path:
            	    r, c = (ROWS - 1 - r_pos, COLS - 1 - c_pos) if flipped else (r_pos, c_pos)
            	    pygame.draw.rect(screen, (50, 50, 0), (c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    
        for r_idx, row in enumerate(self.board):
            for c_idx, piece in enumerate(row):
                if piece != 0:
                    piece.draw(screen)
    
        # --- THIS IS THE CORRECTED LOGIC ---
        if valid_moves:
            # The 'valid_moves' variable is now already a set of the (row, col) tuples
            # we want to highlight. We can iterate over it directly.
            for move in valid_moves:
                r, c = (ROWS - 1 - move[0], COLS - 1 - move[1]) if flipped else move
                pygame.draw.circle(screen, (0, 150, 0), (c * SQUARE_SIZE + SQUARE_SIZE // 2, r * SQUARE_SIZE + SQUARE_SIZE // 2), 15)

        if show_numbers:
            for r in range(ROWS):
                for c in range(COLS):
                    if (r + c) % 2 == 1:
                        num = COORD_TO_ACF.get((r, c))
                        if num:
                            disp_r, disp_c = (ROWS - 1 - r, COLS - 1 - c) if flipped else (r, c)
                            text = font.render(str(num), True, (200, 200, 200))
                            screen.blit(text, (disp_c * SQUARE_SIZE + 5, disp_r * SQUARE_SIZE + 5))

    def draw_squares(self, win):
        win.fill((10, 10, 10))
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(win, (60, 60, 60), (row * SQUARE_SIZE, col * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def get_all_pieces(self, color):
        pieces = []
        for row in self.board:
            for piece in row:
                if piece != 0 and piece.color == color:
                    pieces.append(piece)
        return pieces

    def winner(self):
        if self.red_left <= 0: return WHITE
        elif self.white_left <= 0: return RED
        if not self.get_all_move_sequences(self.turn):
            return WHITE if self.turn == RED else RED
        return None
        
    def _get_endgame_key(self):
        """
        Generates a canonical, stringified FLAT tuple key for the current board state
        to query the endgame database.
        """
        total_pieces = self.red_left + self.white_left
        if total_pieces > 8:
            return None, None

        white_king_pos, red_king_pos, white_men_pos, red_men_pos = [], [], [], []
        for r in range(ROWS):
            for c in range(COLS):
                piece = self.get_piece(r, c)
                if piece != 0:
                    pos_acf = COORD_TO_ACF.get((r, c))
                    if piece.color == WHITE:
                        if piece.king: white_king_pos.append(pos_acf)
                        else: white_men_pos.append(pos_acf)
                    else:
                        if piece.king: red_king_pos.append(pos_acf)
                        else: red_men_pos.append(pos_acf)

        w_kings, r_kings = len(white_king_pos), len(red_king_pos)
        w_men, r_men = len(white_men_pos), len(red_men_pos)
        turn_char = 'w' if self.turn == WHITE else 'r'
        
        logger.debug(f"DB_KEY_GEN: Checking board state. R:{r_kings}K,{r_men}M W:{w_kings}K,{w_men}M")

        table_name, key_tuple = None, None
        
        if r_men == 0 and w_men == 0:
            kings_config = frozenset([r_kings, w_kings])
            if kings_config == frozenset([2, 1]): table_name = "db_2v1_kings"
            elif kings_config == frozenset([3, 1]): table_name = "db_3v1_kings"
            elif kings_config == frozenset([3, 2]): table_name = "db_3v2_kings"
            elif kings_config == frozenset([4, 2]): table_name = "db_4v2_kings"
            elif kings_config == frozenset([4, 3]): table_name = "db_4v3_kings"
            elif r_kings == 3 and w_kings == 3: table_name = "db_3v3_kings"
            if table_name:
                 key_tuple = tuple(sorted(red_king_pos)) + tuple(sorted(white_king_pos)) + (turn_char,)
        elif r_kings == 0 and w_kings == 0 and {r_men, w_men} == {2, 1}:
            table_name = "db_2v1_men"
            key_tuple = tuple(sorted(red_men_pos)) + tuple(white_men_pos) + (turn_char,)
        else:
            if r_kings == 3 and r_men == 0 and w_kings == 1 and w_men == 1:
                table_name = "db_3kv1k1m"
                key_tuple = tuple(sorted(red_king_pos)) + (white_king_pos[0], white_men_pos[0]) + (turn_char,)
            elif r_kings == 2 and r_men == 1 and w_kings == 2 and w_men == 0:
                table_name = "db_2k1m_vs_2k"
                key_tuple = tuple(sorted(red_king_pos)) + (red_men_pos[0],) + tuple(sorted(white_king_pos)) + (turn_char,)
            elif r_kings == 2 and r_men == 1 and w_kings == 3 and w_men == 0:
                table_name = "db_2k1m_vs_3k"
                key_tuple = tuple(sorted(red_king_pos)) + (red_men_pos[0],) + tuple(sorted(white_king_pos)) + (turn_char,)
            elif r_kings == 3 and r_men == 1 and w_kings == 3 and w_men == 0:
                table_name = "db_3k1m_vs_3k"
                key_tuple = tuple(sorted(red_king_pos)) + (red_men_pos[0],) + tuple(sorted(white_king_pos)) + (turn_char,)
            elif r_kings == 2 and r_men == 1 and w_kings == 2 and w_men == 1:
                table_name = "db_2k1m_vs_2k1m"
                key_tuple = tuple(sorted(red_king_pos)) + (red_men_pos[0],) + tuple(sorted(white_king_pos)) + (white_men_pos[0],) + (turn_char,)

        if table_name is None:
            return None, None

        key_string = str(key_tuple)
        
        logger.debug(f"DB_KEY_GEN: Match found! Table='{table_name}', Key='{key_string}'")
        return table_name, key_string
