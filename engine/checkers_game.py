# engine/checkers_game.py
import os
import pickle
import copy
from datetime import datetime
from .constants import *
from .board import Board
from .evaluation import evaluate_board_static
from .search import static_minimax

class Checkers:
    # --- Resource Integration ---
    ZOBRIST_KEYS, OPENING_BOOK = {}, {}
    EGTB_2v1_KINGS, EGTB_FILENAME_2V1K = None, "db_2v1_kings.pkl"
    EGTB_2v1_MEN, EGTB_FILENAME_2V1M = None, "db_2v1_men.pkl"
    EGTB_3v1_KINGS, EGTB_FILENAME_3V1K = None, "db_3v1_kings.pkl"
    EGTB_3v2_KINGS, EGTB_FILENAME_3V2K = None, "db_3v2_kings.pkl"
    EGTB_3v1K1M, EGTB_FILENAME_3V1K1M = None, "db_3v1k1m.pkl"
    EGTB_2K1Mv2K, EGTB_FILENAME_2K1Mv2K = None, "db_2k1m_vs_2k.pkl"
    EGTB_4v2_KINGS, EGTB_FILENAME_4V2K = None, "db_4v2_kings.pkl"
    EGTB_2K1Mv3K, EGTB_FILENAME_2K1Mv3K = None, "db_2k1m_vs_3k.pkl"
    EGTB_3v3_KINGS, EGTB_FILENAME_3V3K = None, "db_3v3_kings.pkl"
    EGTB_2K1Mv2K1M, EGTB_FILENAME_2K1Mv2K1M = None, "db_2k1m_vs_2k1m.pkl"
    EGTB_4v3_KINGS, EGTB_FILENAME_4V3K = None, "db_4v3_kings.pkl"
    
    OPENING_BOOK = {}
    BOOK_FILENAME = "custom_book.pkl"
    RESOURCES_FILENAME = "game_resources.pkl"
    MATERIAL_MULTIPLIER = 1500.0
    PIECE_VALUES = {RED: 1.0, WHITE: 1.0, RED_KING: 1.5, WHITE_KING: 1.5, EMPTY: 0}

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
        else:
            self.hash = 0

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

    def _get_egtb_key(self, piece_counts):
        if piece_counts == (0, 2, 0, 1):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + (white_kings[0], self.turn)
        return None

    def _get_egtb_key_2Kv1M(self, piece_counts):
        if piece_counts == (0, 2, 1, 0):
            red_kings, white_men = [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE: white_men.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + (white_men[0], self.turn)
        return None

    def _get_egtb_key_3Kv1K(self, piece_counts):
        if piece_counts == (0, 3, 0, 1):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + (white_kings[0], self.turn)
        return None

    def _get_egtb_key_3Kv2K(self, piece_counts):
        if piece_counts == (0, 3, 0, 2):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + tuple(sorted(white_kings)) + (self.turn,)
        return None

    def _get_egtb_key_3Kv1K1M(self, piece_counts):
        if piece_counts == (0, 3, 1, 1):
            red_kings, white_kings, white_men = [], [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE: white_men.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + (white_kings[0], white_men[0], self.turn)
        return None
        
    def _get_egtb_key_2K1Mv2K(self, piece_counts):
        if piece_counts == (1, 2, 0, 2):
            red_kings, red_men, white_kings = [], [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == RED: red_men.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r, c)))
            return tuple(sorted(red_kings)) + (red_men[0],) + tuple(sorted(white_kings)) + (self.turn,)
        return None

    def _get_egtb_key_4Kv2K(self, piece_counts):
        if piece_counts == (0, 4, 0, 2):
            red_kings, white_kings = [], []
            for r in range(8):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r, c)))
            return tuple(sorted(red_kings)) + tuple(sorted(white_kings)) + (self.turn,)
        return None
    
    def _get_egtb_key_2K1Mv3K(self, piece_counts):
        if piece_counts == (1, 2, 0, 3):
            red_kings, red_men, white_kings = [], [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == RED: red_men.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r, c)))
            return tuple(sorted(red_kings)) + (red_men[0],) + tuple(sorted(white_kings)) + (self.turn,)
        return None

    def _get_egtb_key_3Kv3K(self, piece_counts):
        if piece_counts == (0, 3, 0, 3):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + tuple(sorted(white_kings)) + (self.turn,)
        return None

    def _get_egtb_key_2K1Mv2K1M(self, piece_counts):
        if piece_counts == (1, 2, 1, 2):
            red_kings, red_men, white_kings, white_men = [], [], [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == RED: red_men.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE: white_men.append(COORD_TO_ACF.get((r, c)))
            return tuple(sorted(red_kings)) + (red_men[0],) + tuple(sorted(white_kings)) + (white_men[0],) + (self.turn,)
        return None
    
    def _get_egtb_key_4Kv3K(self, piece_counts):
        if piece_counts == (0, 4, 0, 3):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.game_board.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r, c)))
            return (tuple(sorted(red_kings)), tuple(sorted(white_kings)), self.turn)
        return None

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

    def perform_move_for_search(self, start, end):
        further_jumps, captured_piece, captured_pos, promotion = self.game_board.perform_move(start, end)
        self._update_hash((start, end), captured_piece, captured_pos, promotion)
        self.game_board.turn = WHITE if self.game_board.turn == RED else RED
        self.game_board.forced_jumps = further_jumps
        return bool(further_jumps)
        
    def _finalize_turn(self, was_jump):
        path = [item for i, item in enumerate(self.current_move_path) if i == 0 or item != self.current_move_path[i-1]]
        move_str = f"{path[0]}x{path[-1]}" if was_jump else f"{path[0]}-{path[-1]}"
        self.move_history.append(f"{PLAYER_NAMES[WHITE if self.game_board.turn == RED else RED]}: {move_str}")
        self.current_move_path = []
        self.game_board.turn = WHITE if self.game_board.turn == RED else RED
        self.game_board.forced_jumps = []
        self.winner = self.check_win_condition()

    def check_win_condition(self):
        if not self.game_board.get_all_possible_moves(self.game_board.turn): return WHITE if self.game_board.turn == RED else RED
        if not any(p.lower() == RED for r in self.game_board.board for p in r): return WHITE
        if not any(p.lower() == WHITE for r in self.game_board.board for p in r): return RED
        return None

    def _setup_board(self):
        return Board().board

    def get_all_possible_moves(self, player):
        return self.game_board.get_all_possible_moves(player)

    def clone(self):
        new_game = Checkers(load_resources=False)
        new_game.game_board = copy.deepcopy(self.game_board)
        new_game.hash = self.hash
        new_game.transposition_table = self.transposition_table
        return new_game
