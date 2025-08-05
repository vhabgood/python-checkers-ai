# engine/checkers_game.py
import os
import pickle
from datetime import datetime
from .constants import *
from .search import static_minimax

class Checkers:
    ZOBRIST_KEYS, OPENING_BOOK = {}, {}
    EGTB_2v1_KINGS, EGTB_2v1_MEN, EGTB_3v1_KINGS, EGTB_3v2_KINGS = None, None, None, None
    EGTB_3v1K1M, EGTB_2K1Mv2K, EGTB_4v2_KINGS, EGTB_2K1Mv3K = None, None, None, None
    EGTB_3v3_KINGS, EGTB_2K1Mv2K1M, EGTB_4v3_KINGS = None, None, None
    RESOURCES_FILENAME = "game_resources.pkl"
    
    def __init__(self, board=None, turn=None, load_resources=True):
        if load_resources: self.load_all_resources()
        self.board = self._setup_board() if board is None else board
        self.turn = RED if turn is None else turn
        self.forced_jumps, self.move_history, self.current_move_path, self.winner = [], [], [], None
        self.transposition_table = {}
        if Checkers.ZOBRIST_KEYS: self.hash = self._calculate_initial_hash()

    @staticmethod
    def load_all_resources(status_callback=None):
        def update(msg):
            if status_callback: status_callback(msg)
        update("Loading bundled resources...")
        if os.path.exists(Checkers.RESOURCES_FILENAME):
            with open(Checkers.RESOURCES_FILENAME, "rb") as f: all_resources = pickle.load(f)
            for key, value in all_resources.items(): setattr(Checkers, key, value)
            update("All resources loaded successfully.")
        else:
            update(f"Error: {Checkers.RESOURCES_FILENAME} not found.")
            Checkers.ZOBRIST_KEYS, Checkers.OPENING_BOOK = {}, {}

    def _calculate_initial_hash(self):
        h = 0
        for r, row in enumerate(self.board):
            for c, piece in enumerate(row):
                if piece != EMPTY: h ^= self.ZOBRIST_KEYS.get((piece, COORD_TO_ACF.get((r, c))), 0)
        if self.turn == WHITE: h ^= self.ZOBRIST_KEYS.get('turn', 0)
        return h

    def _update_hash(self, move, captured_piece=None, captured_pos=None, promotion=False):
        start, end = move; piece = self.board[end[0]][end[1]]
        start_acf, end_acf = COORD_TO_ACF[start], COORD_TO_ACF[end]
        original_piece = piece.lower() if promotion else piece
        self.hash ^= self.ZOBRIST_KEYS.get((original_piece, start_acf), 0)
        self.hash ^= self.ZOBRIST_KEYS.get((piece, end_acf), 0)
        if captured_piece: self.hash ^= self.ZOBRIST_KEYS.get((captured_piece, COORD_TO_ACF[captured_pos]), 0)
        self.hash ^= self.ZOBRIST_KEYS.get('turn', 0)
    
    def _get_board_tuple(self): return tuple(map(tuple, self.board))

    def _get_piece_counts(self):
        return (sum(row.count(RED) for row in self.board), sum(row.count(RED_KING) for row in self.board),
                sum(row.count(WHITE) for row in self.board), sum(row.count(WHITE_KING) for row in self.board))

    def find_best_move(self, depth, progress_callback=None):
        # ... EGTB Logic Here ...
        
        if self._get_board_tuple() in self.OPENING_BOOK: return self.OPENING_BOOK[self._get_board_tuple()]
        all_possible_moves = self.get_all_possible_moves(self.turn)
        if not all_possible_moves: return None
        self.transposition_table.clear()
        killer_moves = [[None, None] for _ in range(depth + 1)]
        is_maximizing = self.turn == RED
        best_move_path, evaluated_moves, eval_counter, alpha, beta = [], [], [0], -float('inf'), float('inf')
        best_score = -float('inf') if is_maximizing else float('inf')
        for start, end in all_possible_moves:
            temp_game = Checkers([row[:] for row in self.board], self.turn, False); temp_game.hash = self.hash; temp_game.perform_move_for_search(start, end)
            score, path = static_minimax(temp_game, temp_game.board, temp_game.turn, depth - 1, alpha, beta, not temp_game.turn == self.turn, eval_counter, progress_callback, killer_moves, [(start, end)])
            full_path = [(start, end)] + path
            evaluated_moves.append({'move': (start, end), 'score': score, 'path': full_path})
            if progress_callback: progress_callback(sorted(evaluated_moves, key=lambda x:x['score'], reverse=is_maximizing), eval_counter[0], None)
            if (is_maximizing and score > best_score) or (not is_maximizing and score < best_score):
                best_score, best_move_path = score, full_path
            if is_maximizing: alpha = max(alpha, score)
            else: beta = min(beta, score)
            if alpha >= beta: break
        return best_move_path[0] if best_move_path else None

    def _setup_board(self):
        board = [[EMPTY for _ in range(8)] for _ in range(8)]
        for r in range(8):
            for c in range(8):
                if (r + c) % 2 == 1:
                    if r < 3: board[r][c] = RED
                    elif r > 4: board[r][c] = WHITE
        return board

    def get_all_possible_moves(self, player):
        all_simple, all_jumps = [], []
        for r, row in enumerate(self.board):
            for c, piece in enumerate(row):
                if piece.lower() == player:
                    simple, jumps = self._get_piece_moves(r, c)
                    all_simple.extend(simple); all_jumps.extend(jumps)
        return all_jumps if all_jumps else all_simple

    def _get_piece_moves(self, row, col):
        simple, jumps, piece = [], [], self.board[row][col]
        if piece == EMPTY: return [], []
        dirs = [(-1,-1),(-1,1),(1,-1),(1,1)] if piece.isupper() else [(-1,-1),(-1,1)] if piece==WHITE else [(1,-1),(1,1)]
        for dr, dc in dirs:
            r, c = row+dr, col+dc
            if 0<=r<8 and 0<=c<8 and self.board[r][c]==EMPTY: simple.append(((row, col),(r,c)))
            r_j, c_j = row+2*dr, col+2*dc
            if 0<=r_j<8 and 0<=c_j<8 and self.board[r_j][c_j]==EMPTY:
                if 0<=row+dr<8 and 0<=col+dc<8 and self.board[row+dr][col+dc].lower() not in [piece.lower(), EMPTY]:
                    jumps.append(((row,col),(r_j,c_j)))
        return simple, jumps

    def _promote_to_king(self, row, col):
        piece = self.board[row][col]
        if piece == RED and row == 7: self.board[row][col] = RED_KING; return True
        elif piece == WHITE and row == 0: self.board[row][col] = WHITE_KING; return True
        return False
        
    def perform_move(self, start, end):
        if not self.forced_jumps: self.current_move_path = [coord_to_acf_notation(start)]
        further_jumps = self.perform_move_for_search(start, end)
        self.current_move_path.append(coord_to_acf_notation(end))
        if not further_jumps:
            is_jump = any(abs(ACF_TO_COORD[int(self.current_move_path[i])][0] - ACF_TO_COORD[int(self.current_move_path[i+1])][0])==2 for i in range(len(self.current_move_path)-1))
            self._finalize_turn(is_jump)
        else: self.forced_jumps = further_jumps

    def perform_move_for_search(self, start, end):
        piece_to_move = self.board[start[0]][start[1]]
        self.board[end[0]][end[1]] = piece_to_move; self.board[start[0]][start[1]] = EMPTY
        promotion = self._promote_to_king(end[0], end[1])
        captured_piece, captured_pos = None, None
        if abs(start[0] - end[0]) == 2:
            captured_pos = ((start[0]+end[0])//2, (start[1]+end[1])//2)
            captured_piece = self.board[captured_pos[0]][captured_pos[1]]
            self.board[captured_pos[0]][captured_pos[1]] = EMPTY
        self._update_hash((start, end), captured_piece, captured_pos, promotion)
        if captured_piece:
            _, further_jumps = self._get_piece_moves(end[0], end[1])
            if further_jumps:
                self.forced_jumps = [(end, j_end) for _, j_end in further_jumps]
                return self.forced_jumps
        self.turn = WHITE if self.turn == RED else RED; self.forced_jumps = []
        return None
        
    def _finalize_turn(self, was_jump):
        path = [item for i, item in enumerate(self.current_move_path) if i == 0 or item != self.current_move_path[i-1]]
        move_str = f"{path[0]}x{path[-1]}" if was_jump else f"{path[0]}-{path[-1]}"
        self.move_history.append(f"{PLAYER_NAMES[WHITE if self.turn == RED else RED]}: {move_str}")
        self.current_move_path, self.forced_jumps, self.winner = [], [], self.check_win_condition()

    def check_win_condition(self):
        if not self.get_all_possible_moves(self.turn): return WHITE if self.turn == RED else RED
        if not any(p.lower() == RED for r in self.board for p in r): return WHITE
        if not any(p.lower() == WHITE for r in self.board for p in r): return RED
        return None
