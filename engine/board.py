# engine/board.py
import pygame
import logging
import re
import copy
# --- MODIFIED: Add ZOBRIST_KEYS to the import ---
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
        self.moves_since_progress = 0
        self.create_board()
        # --- NEW: Initialize the Zobrist hash ---
        self.hash = self._calculate_initial_hash()

    # --- NEW: Add get_hash method ---
    def get_hash(self):
        """Returns the current Zobrist hash for the board state."""
        return self.hash

    # --- NEW: Add Zobrist hash calculation methods (from main.py) ---
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
        start_acf, end_acf = COORD_TO_ACF[start_pos], COORD_TO_ACF[end_pos]
        
        # Determine piece characters
        original_piece_char = ('R' if piece.king and not (end_pos[0] in [0, 7]) else 'r') if piece.color == RED else ('W' if piece.king and not (end_pos[0] in [0, 7]) else 'w')
        final_piece_char = ('R' if piece.king else 'r') if piece.color == RED else ('W' if piece.king else 'w')

        # XOR out the piece from its original position
        self.hash ^= ZOBRIST_KEYS.get((original_piece_char, start_acf), 0)
        # XOR in the piece at its new position
        self.hash ^= ZOBRIST_KEYS.get((final_piece_char, end_acf), 0)

        # XOR out any captured pieces
        for captured_piece, pos in captured_pieces:
            captured_char = ('R' if captured_piece.king else 'r') if captured_piece.color == RED else ('W' if captured_piece.king else 'w')
            captured_acf = COORD_TO_ACF.get(pos)
            if captured_acf:
                self.hash ^= ZOBRIST_KEYS.get((captured_char, captured_acf), 0)

        # XOR the turn
        self.hash ^= ZOBRIST_KEYS.get('turn', 0)

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
                    captured_pieces_for_hash.append((jumped_piece, jumped_pos)) # Store for hashing
                    if jumped_piece.color == RED: new_board.red_left -= 1
                    else: new_board.white_left -= 1
                    new_board.board[jumped_pos[0]][jumped_pos[1]] = 0

        # Store king status before the move for accurate hash update
        was_king = piece.king
        piece.move(end_pos[0], end_pos[1])

        # Handle promotion
        if end_pos[0] == ROWS - 1 and piece.color == RED and not was_king:
            piece.make_king(); new_board.red_kings += 1
        elif end_pos[0] == 0 and piece.color == WHITE and not was_king:
            piece.make_king(); new_board.white_kings += 1
        
        # --- MODIFIED: Update the hash value on the new board ---
        new_board._update_hash(path, piece, captured_pieces_for_hash)
        
        new_board.turn = WHITE if self.turn == RED else RED
        return new_board

    # ... (the rest of the Board class methods are unchanged)
    # ... (get_fen, __deepcopy__, create_board, create_board_from_fen, etc.)
    # ... Make sure to keep your _format_move_path and _get_endgame_key methods
