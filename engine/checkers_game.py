# engine/checkers_game.py
import os
import pickle
from datetime import datetime
import copy # <<< ADD THIS LINE
from .constants import *
from .board import Board
from .search import static_minimax

class Checkers:
    # --- Resource Integration ---
    ZOBRIST_KEYS, OPENING_BOOK = {}, {}
    EGTB_2v1_KINGS, EGTB_2v1_MEN, EGTB_3v1_KINGS, EGTB_3v2_KINGS = None, None, None, None
    EGTB_3v1K1M, EGTB_2K1Mv2K, EGTB_4v2_KINGS, EGTB_2K1Mv3K = None, None, None, None
    EGTB_3v3_KINGS, EGTB_2K1Mv2K1M, EGTB_4v3_KINGS = None, None, None
    RESOURCES_FILENAME = "game_resources.pkl"

    def __init__(self, board=None, turn=None, load_resources=True):
        if load_resources:
            self.load_all_resources()
        
        self.game_board = Board(board, turn)
        self.move_history = []
        self.current_move_path = []
        self.winner = None
        
        self.transposition_table = {}
        if Checkers.ZOBRIST_KEYS:
            self.hash = self._calculate_initial_hash()

    @staticmethod
    def load_all_resources(status_callback=None):
        def update(msg):
            if status_callback: status_callback(msg)
        
        update("Loading bundled resources...")
        if os.path.exists(Checkers.RESOURCES_FILENAME):
            with open(Checkers.RESOURCES_FILENAME, "rb") as f:
                all_resources = pickle.load(f)
            
            for key, value in all_resources.items():
                setattr(Checkers, key, value)
            update("All resources loaded successfully.")
        else:
            update(f"Error: {Checkers.RESOURCES_FILENAME} not found.")
            Checkers.ZOBRIST_KEYS, Checkers.OPENING_BOOK = {}, {}

    def _calculate_initial_hash(self):
        h = 0
        for r, row in enumerate(self.game_board.board):
            for c, piece in enumerate(row):
                if piece != EMPTY:
                    h ^= self.ZOBRIST_KEYS.get((piece, COORD_TO_ACF.get((r, c))), 0)
        if self.game_board.turn == WHITE:
            h ^= self.ZOBRIST_KEYS.get('turn', 0)
        return h

    def _update_hash(self, move, captured_piece=None, captured_pos=None, promotion=False):
        start, end = move
        piece = self.game_board.board[end[0]][end[1]]
        start_acf, end_acf = COORD_TO_ACF[start], COORD_TO_ACF[end]
        original_piece = piece.lower() if promotion else piece
        
        self.hash ^= self.ZOBRIST_KEYS.get((original_piece, start_acf), 0)
        self.hash ^= self.ZOBRIST_KEYS.get((piece, end_acf), 0)
        if captured_piece: self.hash ^= self.ZOBRIST_KEYS.get((captured_piece, COORD_TO_ACF[captured_pos]), 0)
        self.hash ^= self.ZOBRIST_KEYS.get('turn', 0)
    
    def _get_board_tuple(self):
        return tuple(map(tuple, self.game_board.board))

    def _get_piece_counts(self):
        return (
            sum(row.count(RED) for row in self.game_board.board), sum(row.count(RED_KING) for row in self.game_board.board),
            sum(row.count(WHITE) for row in self.game_board.board), sum(row.count(WHITE_KING) for row in self.game_board.board)
        )

    # All EGTB key functions remain here
    # ...

    def find_best_move(self, depth, progress_callback=None):
        # ... (find_best_move logic is unchanged)
        all_possible_moves = self.game_board.get_all_possible_moves(self.game_board.turn)
        if not all_possible_moves: return None
        
        self.transposition_table.clear()
        killer_moves = [[None, None] for _ in range(depth + 1)]
        is_maximizing = self.game_board.turn == RED
        best_move_path, evaluated_moves, eval_counter, alpha, beta = [], [], [0], -float('inf'), float('inf')
        best_score = -float('inf') if is_maximizing else float('inf')
        
        for start, end in all_possible_moves:
            temp_game = self.clone()
            further_jumps = temp_game.perform_move_for_search(start, end)
            
            score, path = static_minimax(temp_game, depth - 1, alpha, beta, not further_jumps, eval_counter, progress_callback, killer_moves, [(start, end)])
            
            full_path = [(start, end)] + path
            evaluated_moves.append({'move': (start, end), 'score': score, 'path': full_path})
            
            if progress_callback:
                progress_callback(sorted(evaluated_moves, key=lambda x:x['score'], reverse=is_maximizing), eval_counter[0], None)
            
            if (is_maximizing and score > best_score) or (not is_maximizing and score < best_score):
                best_score, best_move_path = score, full_path
            
            if is_maximizing: alpha = max(alpha, score)
            else: beta = min(beta, score)
            if alpha >= beta:
                break
        
        return best_move_path[0] if best_move_path else None

    def perform_move_for_search(self, start, end):
        further_jumps, captured_piece, captured_pos, promotion = self.game_board.perform_move(start, end)
        self._update_hash((start, end), captured_piece, captured_pos, promotion)
        self.game_board.turn = WHITE if self.game_board.turn == RED else RED
        self.game_board.forced_jumps = further_jumps
        return bool(further_jumps)

    def clone(self):
        new_game = Checkers(load_resources=False)
        new_game.game_board = copy.deepcopy(self.game_board)
        new_game.hash = self.hash
        new_game.transposition_table = self.transposition_table
        return new_game
        
    def perform_move(self, start, end):
        if not self.game_board.forced_jumps:
            self.current_move_path = [coord_to_acf_notation(start)]
        
        further_jumps, _, _, _ = self.game_board.perform_move(start, end)
        self.current_move_path.append(coord_to_acf_notation(end))
        
        if not further_jumps:
            is_jump = any(abs(ACF_TO_COORD[int(self.current_move_path[i])][0] - ACF_TO_COORD[int(self.current_move_path[i+1])][0])==2 for i in range(len(self.current_move_path)-1))
            self._finalize_turn(is_jump)
        else:
            self.game_board.forced_jumps = further_jumps

    def _finalize_turn(self, was_jump):
        path = [item for i, item in enumerate(self.current_move_path) if i == 0 or item != self.current_move_path[i-1]]
        move_str = f"{path[0]}x{path[-1]}" if was_jump else f"{path[0]}-{path[-1]}"
        self.move_history.append(f"{PLAYER_NAMES[WHITE if self.game_board.turn == RED else RED]}: {move_str}")
        self.current_move_path = []
        self.game_board.turn = WHITE if self.game_board.turn == RED else RED
        self.game_board.forced_jumps = []
        self.winner = self.check_win_condition()

    def check_win_condition(self):
        if not self.game_board.get_all_possible_moves(self.game_board.turn):
            return WHITE if self.game_board.turn == RED else RED
        
        red_pieces = any(p.lower() == RED for r in self.game_board.board for p in r)
        white_pieces = any(p.lower() == WHITE for r in self.game_board.board for p in r)
        
        if not red_pieces: return WHITE
        if not white_pieces: return RED
        return None

    def _setup_board(self):
        return Board().board
