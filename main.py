# main.py
import pygame
import os
import copy
import pickle
import threading
from datetime import datetime
import random

# --- PART 1: THE CHECKERS GAME ENGINE (DEFINITIVE, CORRECTED VERSION) ---

# Constants and Mappings
EMPTY, RED, WHITE, RED_KING, WHITE_KING = ' ', 'r', 'w', 'R', 'W'
PLAYER_NAMES = {RED: "Red", WHITE: "White"}
ACF_TO_COORD, COORD_TO_ACF = {}, {}
num = 1
for r in range(8):
    for c in range(8):
        if (r + c) % 2 == 1:
            ACF_TO_COORD[num], COORD_TO_ACF[(r, c)] = (r, c), num
            num += 1
def coord_to_acf_notation(coord): return str(COORD_TO_ACF.get(coord, "??"))

class Checkers:
    FUTILITY_MARGIN = 300.0
    
    # --- Resource Integration ---
    ZOBRIST_KEYS, OPENING_BOOK = {}, {}
    EGTB_2v1_KINGS, EGTB_2v1_MEN, EGTB_3v1_KINGS, EGTB_3v2_KINGS = None, None, None, None
    EGTB_3v1K1M, EGTB_2K1Mv2K, EGTB_4v2_KINGS, EGTB_2K1Mv3K = None, None, None, None
    EGTB_3v3_KINGS, EGTB_2K1Mv2K1M, EGTB_4v3_KINGS = None, None, None
    RESOURCES_FILENAME = "game_resources.pkl"
    
    MATERIAL_MULTIPLIER = 1500.0
    PIECE_VALUES = {RED: 1.0, WHITE: 1.0, RED_KING: 1.5, WHITE_KING: 1.5, EMPTY: 0}

    def __init__(self, board=None, turn=None, load_resources=True):
        if load_resources:
            self.load_all_resources()
        
        self.board = self._setup_board() if board is None else board
        self.turn = RED if turn is None else turn
        self.forced_jumps, self.move_history, self.current_move_path, self.winner = [], [], [], None
        
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
        for r, row in enumerate(self.board):
            for c, piece in enumerate(row):
                if piece != EMPTY:
                    h ^= self.ZOBRIST_KEYS.get((piece, COORD_TO_ACF.get((r, c))), 0)
        if self.turn == WHITE:
            h ^= self.ZOBRIST_KEYS.get('turn', 0)
        return h

    def _update_hash(self, move, captured_piece=None, captured_pos=None, promotion=False):
        start, end = move; piece = self.board[end[0]][end[1]]
        start_acf, end_acf = COORD_TO_ACF[start], COORD_TO_ACF[end]
        original_piece = piece.lower() if promotion else piece
        self.hash ^= self.ZOBRIST_KEYS.get((original_piece, start_acf), 0)
        self.hash ^= self.ZOBRIST_KEYS.get((piece, end_acf), 0)
        if captured_piece: self.hash ^= self.ZOBRIST_KEYS.get((captured_piece, COORD_TO_ACF[captured_pos]), 0)
        self.hash ^= self.ZOBRIST_KEYS.get('turn', 0)
    
    def _get_board_tuple(self):
        return tuple(map(tuple, self.board))

    def _get_egtb_key_2K1Mv2K1M(self, piece_counts):
        if piece_counts == (1, 2, 1, 2):
            red_kings, red_men, white_kings, white_men = [], [], [], []
            for r, row in enumerate(self.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == RED: red_men.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE: white_men.append(COORD_TO_ACF.get((r, c)))
            return tuple(sorted(red_kings)) + (red_men[0],) + tuple(sorted(white_kings)) + (white_men[0],) + (self.turn,)
        return None

    def _get_egtb_key_3Kv3K(self, piece_counts):
        if piece_counts == (0, 3, 0, 3):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + tuple(sorted(white_kings)) + (self.turn,)
        return None

    def _get_egtb_key_4Kv3K(self, piece_counts):
        if piece_counts == (0, 4, 0, 3):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r, c)))
            return (tuple(sorted(red_kings)), tuple(sorted(white_kings)), self.turn)
        return None

    @staticmethod
    def evaluate_board_static(board, turn_to_move):
        gs = Checkers(board, turn_to_move, load_resources=False)
        red_moves, white_moves = gs.get_all_possible_moves(RED), gs.get_all_possible_moves(WHITE)
        red_jumps, white_jumps = any(abs(s[0]-e[0])==2 for s,e in red_moves), any(abs(s[0]-e[0])==2 for s,e in white_moves)
        is_tactical = red_jumps or white_jumps

        mat_score, pos_score = 0, 0
        BACK_ROW_CORNER_BONUS = 0.05
        
        for r, row in enumerate(board):
            for c, piece in enumerate(row):
                if piece == EMPTY: continue
                
                is_red = piece.lower() == RED
                mat_score += Checkers.PIECE_VALUES[piece] if is_red else -Checkers.PIECE_VALUES[piece]
                
                if not is_tactical:
                    if not piece.isupper():
                        acf_pos = COORD_TO_ACF.get((r, c))
                        if piece == RED and acf_pos in {1, 3}: pos_score += BACK_ROW_CORNER_BONUS
                        elif piece == WHITE and acf_pos in {30, 32}: pos_score -= BACK_ROW_CORNER_BONUS
                            
        if not is_tactical:
            red_kings = sum(row.count(RED_KING) for row in board)
            white_kings = sum(row.count(WHITE_KING) for row in board)
            if red_kings > 0 and white_kings == 0: pos_score += 0.5 * red_kings
            elif white_kings > 0 and red_kings == 0: pos_score -= 0.5 * white_kings
                
        return (mat_score * Checkers.MATERIAL_MULTIPLIER) + pos_score

    # ... (The rest of the Checkers class methods, like search and move logic, follow here)
