# main.py
import pygame
import os
import copy
import pickle
import threading
from datetime import datetime
import random
from engine.evaluation import evaluate_board_static
from engine.constants import *

# --- PART 1: THE CHECKERS GAME ENGINE (DEFINITIVE, CORRECTED VERSION) ---

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

    # All EGTB key functions are unchanged
    
    @staticmethod
    def _get_mvv_lva_score(board, move):
        start, end = move
        aggressor = board[start[0]][start[1]]
        victim_pos = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        victim = board[victim_pos[0]][victim_pos[1]]
        victim_value = PIECE_VALUES.get(victim, 0) * 100
        aggressor_value = PIECE_VALUES.get(aggressor, 0)
        return victim_value - aggressor_value
        
    @staticmethod
    def _record_killer_move(move, depth, killer_moves):
        if move != killer_moves[depth][0]:
            killer_moves[depth][1] = killer_moves[depth][0]
            killer_moves[depth][0] = move

    def _static_quiescence_search(self, board, turn, alpha, beta, maximizing_player, eval_counter):
        eval_counter[0] += 1; game_state = Checkers(board, turn, load_resources=False)
        capture_moves = [m for m in game_state.get_all_possible_moves(turn) if abs(m[0][0] - m[1][0]) == 2]
        if not capture_moves: return evaluate_board_static(board, turn), []
        capture_moves.sort(key=lambda m: self._get_mvv_lva_score(board, m), reverse=True)
        if maximizing_player:
            best_value, best_path = -float('inf'), []
            for start, end in capture_moves:
                temp_game = Checkers([row[:] for row in board], turn, load_resources=False); temp_game.hash = self.hash; further_jumps = temp_game.perform_move_for_search(start, end)
                value, path = temp_game._static_quiescence_search(temp_game.board, temp_game.turn, alpha, beta, bool(further_jumps), eval_counter)
                if value > best_value: best_value, best_path = value, [(start, end)] + path
                alpha = max(alpha, best_value)
                if beta <= alpha: break
            return best_value, best_path
        else:
            best_value, best_path = float('inf'), []
            for start, end in capture_moves:
                temp_game = Checkers([row[:] for row in board], turn, load_resources=False); temp_game.hash = self.hash; further_jumps = temp_game.perform_move_for_search(start, end)
                value, path = temp_game._static_quiescence_search(temp_game.board, temp_game.turn, alpha, beta, not further_jumps, eval_counter)
                if value < best_value: best_value, best_path = value, [(start, end)] + path
                beta = min(beta, best_value)
                if beta <= alpha: break
            return best_value, best_path

    def _static_minimax(self, board, turn, depth, alpha, beta, maximizing_player, eval_counter, progress_callback, killer_moves, path):
        entry = self.transposition_table.get(self.hash)
        if entry and entry['depth'] >= depth:
            if entry['flag'] == 'EXACT': return entry['score'], entry['path']
            elif entry['flag'] == 'LOWERBOUND' and entry['score'] > alpha: alpha = entry['score']
            elif entry['flag'] == 'UPPERBOUND' and entry['score'] < beta: beta = entry['score']
            if alpha >= beta: return entry['score'], entry['path']

        if depth == 0: return self._static_quiescence_search(board, turn, alpha, beta, maximizing_player, eval_counter)
        game_state = Checkers(board, turn, load_resources=False)
        if game_state.check_win_condition() is not None: return evaluate_board_static(board, turn), []
        all_moves = game_state.get_all_possible_moves(turn)
        if not all_moves: return evaluate_board_static(board, turn), []
        
        captures = [m for m in all_moves if abs(m[0][0] - m[1][0]) == 2]
        quiet_moves = [m for m in all_moves if abs(m[0][0] - m[1][0]) != 2]
        captures.sort(key=lambda m: self._get_mvv_lva_score(board, m), reverse=True)
        killers = killer_moves[depth]
        killer_quiet_moves = [m for m in quiet_moves if m in killers]
        other_quiet_moves = [m for m in quiet_moves if m not in killers]
        ordered_moves = captures + killer_quiet_moves + other_quiet_moves

        best_path = []
        original_alpha = alpha
        if maximizing_player:
            max_eval = -float('inf')
            for i, (start, end) in enumerate(ordered_moves):
                temp_game = Checkers([row[:] for row in board], turn, load_resources=False); temp_game.hash = self.hash; further_jumps = temp_game.perform_move_for_search(start, end)
                
                is_capture = abs(start[0] - end[0]) == 2
                if depth <= 2 and not is_capture and not further_jumps and not any(abs(s[0]-e[0])==2 for s,e in temp_game.get_all_possible_moves(temp_game.turn)):
                    static_eval = evaluate_board_static(temp_game.board, temp_game.turn)
                    if static_eval + FUTILITY_MARGIN <= alpha:
                        continue
                
                if progress_callback: progress_callback(None, None, path + [(start, end)])
                eval_score, sub_path = temp_game._static_minimax(temp_game.board, temp_game.turn, depth - 1, alpha, beta, not further_jumps, eval_counter, progress_callback, killer_moves, path + [(start, end)])
                
                if eval_score > max_eval: max_eval, best_path = eval_score, [(start, end)] + sub_path
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    if not is_capture: self._record_killer_move((start, end), depth, killer_moves)
                    break
            flag = 'EXACT' if max_eval > original_alpha and max_eval < beta else 'LOWERBOUND' if max_eval >= beta else 'UPPERBOUND'
            self.transposition_table[self.hash] = {'score': max_eval, 'depth': depth, 'flag': flag, 'path': best_path}
            return max_eval, best_path
        else: # Minimizing Player
            min_eval = float('inf')
            for i, (start, end) in enumerate(ordered_moves):
                temp_game = Checkers([row[:] for row in board], turn, load_resources=False); temp_game.hash = self.hash; further_jumps = temp_game.perform_move_for_search(start, end)
                
                is_capture = abs(start[0] - end[0]) == 2
                if depth <= 2 and not is_capture and not further_jumps and not any(abs(s[0]-e[0])==2 for s,e in temp_game.get_all_possible_moves(temp_game.turn)):
                    static_eval = evaluate_board_static(temp_game.board, temp_game.turn)
                    if static_eval - FUTILITY_MARGIN >= beta:
                        continue

                if progress_callback: progress_callback(None, None, path + [(start, end)])
                eval_score, sub_path = temp_game._static_minimax(temp_game.board, temp_game.turn, depth - 1, alpha, beta, bool(further_jumps), eval_counter, progress_callback, killer_moves, path + [(start, end)])
                if eval_score < min_eval: min_eval, best_path = eval_score, [(start, end)] + sub_path
                beta = min(beta, eval_score)
                if beta <= alpha:
                    if not is_capture: self._record_killer_move((start, end), depth, killer_moves)
                    break
            flag = 'EXACT' if min_eval > alpha and min_eval < beta else 'UPPERBOUND' if min_eval <= alpha else 'LOWERBOUND'
            self.transposition_table[self.hash] = {'score': min_eval, 'depth': depth, 'flag': flag, 'path': best_path}
            return min_eval, best_path

    # ... (The rest of the Checkers class is unchanged for now)
