# main.py
import pygame
import os
import copy
import pickle
import threading
from datetime import datetime
import random
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

    def _get_egtb_key(self, piece_counts):
        if piece_counts == (0, 2, 0, 1):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + (white_kings[0], self.turn)
        return None

    def _get_egtb_key_2Kv1M(self, piece_counts):
        if piece_counts == (0, 2, 1, 0):
            red_kings, white_men = [], []
            for r, row in enumerate(self.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE: white_men.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + (white_men[0], self.turn)
        return None

    def _get_egtb_key_3Kv1K(self, piece_counts):
        if piece_counts == (0, 3, 0, 1):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + (white_kings[0], self.turn)
        return None

    def _get_egtb_key_3Kv2K(self, piece_counts):
        if piece_counts == (0, 3, 0, 2):
            red_kings, white_kings = [], []
            for r, row in enumerate(self.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + tuple(sorted(white_kings)) + (self.turn,)
        return None

    def _get_egtb_key_3Kv1K1M(self, piece_counts):
        if piece_counts == (0, 3, 1, 1):
            red_kings, white_kings, white_men = [], [], []
            for r, row in enumerate(self.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r,c)))
                    elif piece == WHITE: white_men.append(COORD_TO_ACF.get((r,c)))
            return tuple(sorted(red_kings)) + (white_kings[0], white_men[0], self.turn)
        return None
        
    def _get_egtb_key_2K1Mv2K(self, piece_counts):
        if piece_counts == (1, 2, 0, 2):
            red_kings, red_men, white_kings = [], [], []
            for r, row in enumerate(self.board):
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
                for c in range(8):
                    piece = self.board[r][c]
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r, c)))
            return tuple(sorted(red_kings)) + tuple(sorted(white_kings)) + (self.turn,)
        return None
    
    def _get_egtb_key_2K1Mv3K(self, piece_counts):
        if piece_counts == (1, 2, 0, 3):
            red_kings, red_men, white_kings = [], [], []
            for r, row in enumerate(self.board):
                for c, piece in enumerate(row):
                    if piece == RED_KING: red_kings.append(COORD_TO_ACF.get((r, c)))
                    elif piece == RED: red_men.append(COORD_TO_ACF.get((r, c)))
                    elif piece == WHITE_KING: white_kings.append(COORD_TO_ACF.get((r, c)))
            return tuple(sorted(red_kings)) + (red_men[0],) + tuple(sorted(white_kings)) + (self.turn,)
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
        mat_score, pos_score = 0, 0
        
        for r, row in enumerate(board):
            for c, piece in enumerate(row):
                if piece == EMPTY: continue
                
                is_red = piece.lower() == RED
                mat_score += Checkers.PIECE_VALUES[piece] if is_red else -Checkers.PIECE_VALUES[piece]
                
                if not piece.isupper():
                    acf_pos = COORD_TO_ACF.get((r, c))
                    if piece == RED and acf_pos in {1, 3}: pos_score += BACK_ROW_CORNER_BONUS
                    elif piece == WHITE and acf_pos in {30, 32}: pos_score -= BACK_ROW_CORNER_BONUS
                        
        red_kings = sum(row.count(RED_KING) for row in board)
        white_kings = sum(row.count(WHITE_KING) for row in board)
        if red_kings > 0 and white_kings == 0: pos_score += 0.5 * red_kings
        elif white_kings > 0 and red_kings == 0: pos_score -= 0.5 * white_kings
            
        return (mat_score * MATERIAL_MULTIPLIER) + pos_score

    @staticmethod
    def _get_mvv_lva_score(board, move):
        start, end = move
        aggressor = board[start[0]][start[1]]
        victim_pos = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        victim = board[victim_pos[0]][victim_pos[1]]
        victim_value = Checkers.PIECE_VALUES.get(victim, 0) * 100
        aggressor_value = Checkers.PIECE_VALUES.get(aggressor, 0)
        return victim_value - aggressor_value
        
    @staticmethod
    def _record_killer_move(move, depth, killer_moves):
        if move != killer_moves[depth][0]:
            killer_moves[depth][1] = killer_moves[depth][0]
            killer_moves[depth][0] = move

    def _static_quiescence_search(self, board, turn, alpha, beta, maximizing_player, eval_counter):
        eval_counter[0] += 1; game_state = Checkers(board, turn, load_resources=False)
        capture_moves = [m for m in game_state.get_all_possible_moves(turn) if abs(m[0][0] - m[1][0]) == 2]
        if not capture_moves: return self.evaluate_board_static(board, turn), []
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
        if game_state.check_win_condition() is not None: return self.evaluate_board_static(board, turn), []
        all_moves = game_state.get_all_possible_moves(turn)
        if not all_moves: return self.evaluate_board_static(board, turn), []
        
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
                    static_eval = self.evaluate_board_static(temp_game.board, temp_game.turn)
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
                    static_eval = self.evaluate_board_static(temp_game.board, temp_game.turn)
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

    def find_best_move(self, depth, progress_callback=None):
        piece_counts = (
            sum(row.count(RED) for row in self.board), sum(row.count(RED_KING) for row in self.board),
            sum(row.count(WHITE) for row in self.board), sum(row.count(WHITE_KING) for row in self.board)
        )
        total_pieces = sum(piece_counts)

        if total_pieces <= 7:
            db_checks = [
                (self.EGTB_4v3_KINGS, self._get_egtb_key_4Kv3K, "4K v 3K"),
                (self.EGTB_2K1Mv2K1M, self._get_egtb_key_2K1Mv2K1M, "2K1M v 2K1M"),
                (self.EGTB_3v3_KINGS, self._get_egtb_key_3Kv3K, "3K v 3K"),
                (self.EGTB_2K1Mv3K, self._get_egtb_key_2K1Mv3K, "2K1M v 3K"),
                (self.EGTB_4v2_KINGS, self._get_egtb_key_4Kv2K, "4K v 2K"),
                (self.EGTB_2K1Mv2K, self._get_egtb_key_2K1Mv2K, "2K1M v 2K"),
                (self.EGTB_3v2_KINGS, self._get_egtb_key_3Kv2K, "3K v 2K"),
                (self.EGTB_3v1K1M, self._get_egtb_key_3Kv1K1M, "3K v 1K1M"),
                (self.EGTB_3v1_KINGS, self._get_egtb_key_3Kv1K, "3K v 1K"),
                (self.EGTB_2v1_KINGS, self._get_egtb_key, "2K v 1K"),
                (self.EGTB_2v1_MEN, self._get_egtb_key_2Kv1M, "2K v 1M")
            ]
            for db, key_func, name in db_checks:
                if db:
                    egtb_key = key_func(piece_counts)
                    if egtb_key and egtb_key in db:
                        print(f"EGTB Hit ({name})! Finding perfect move.")
                        current_value = db[egtb_key]; all_moves = self.get_all_possible_moves(self.turn)
                        best_move = all_moves[0] if all_moves else None
                        target = (-(current_value - 1) if current_value > 0 else 0) if self.turn == RED else (-(current_value + 1) if current_value < 0 else 0)
                        for s, e in all_moves:
                            temp_game = Checkers([r[:] for r in self.board], self.turn, False); temp_game.perform_move_for_search(s, e)
                            temp_counts = (sum(r.count(RED) for r in temp_game.board), sum(r.count(RED_KING) for r in temp_game.board), sum(r.count(WHITE) for r in temp_game.board), sum(r.count(WHITE_KING) for r in temp_game.board))
                            next_key = key_func.__get__(temp_game, Checkers)(temp_counts)
                            if db.get(next_key) == target: best_move = (s, e); break
                        if progress_callback: progress_callback([{'move': best_move, 'score': current_value * 1000, 'path': [best_move]}], 1, [best_move])
                        return best_move

        if self._get_board_tuple() in self.OPENING_BOOK: return self.OPENING_BOOK[self._get_board_tuple()]
        
        all_possible_moves = self.get_all_possible_moves(self.turn)
        if not all_possible_moves: return None
        
        self.transposition_table.clear()
        killer_moves = [[None, None] for _ in range(depth + 1)]
        is_maximizing = self.turn == RED
        best_move_path, evaluated_moves, eval_counter, alpha, beta = [], [], [0], -float('inf'), float('inf')
        best_score = -float('inf') if is_maximizing else float('inf')
        
        for start, end in all_possible_moves:
            temp_game = Checkers([row[:] for row in self.board], self.turn, False); temp_game.hash = self.hash; further_jumps = temp_game.perform_move_for_search(start, end)
            score, path = temp_game._static_minimax(temp_game.board, temp_game.turn, depth - 1, alpha, beta, not further_jumps, eval_counter, progress_callback, killer_moves, [(start, end)])
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
        all_simple, all_jumps = [], [];
        for r in range(8):
            for c in range(8):
                if self.board[r][c].lower() == player:
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
                if 0<=row+dr<8 and 0<=col+dc<8 and self.board[row+dr][col+dc].lower() not in [piece.lower(), EMPTY]: jumps.append(((row,col),(r_j,c_j)))
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

# --- PART 2: The Pygame GUI (Final Polished Version) ---
SQUARE_SIZE, BOARD_SIZE, INFO_WIDTH, MENU_BAR_HEIGHT = 80, 8*80, 400, 50
WIDTH, HEIGHT, ROWS, COLS = BOARD_SIZE+INFO_WIDTH, BOARD_SIZE+MENU_BAR_HEIGHT, 8, 8
COLOR_LIGHT, COLOR_DARK, COLOR_RED_P, COLOR_WHITE_P = (240,217,181), (181,136,99), (192,57,43), (248,248,248)
COLOR_SELECTED, COLOR_VALID, COLOR_CROWN = (255,255,0), (68,108,179,150), (252,191,73)
COLOR_TEXT, COLOR_BG, COLOR_BUTTON, COLOR_BUTTON_DISABLED = (44,62,80), (44,62,80), (149,165,166), (93,109,126)
COLOR_BUTTON_HOVER, COLOR_LAST_MOVE, COLOR_DEV_PRIMARY, COLOR_DEV_SECONDARY = (189,195,199), (46,204,113,150), (0,0,255,200), (0,100,255,100)

class CheckersGUI:
    MAX_DEV_HIGHLIGHTS = 3
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT)); pygame.display.set_caption('American Checkers')
        self.font_small, self.font_medium, self.font_large = pygame.font.SysFont('Arial', 18), pygame.font.SysFont('Arial', 24, bold=True), pygame.font.SysFont('Arial', 40, bold=True)
        self.game = None
        self.loading_state = 'loading'
        self.loading_status_message = "Initializing..."
        self.loading_lock = threading.Lock()
        threading.Thread(target=self._load_resources_worker, daemon=True).start()
        
    def _load_resources_worker(self):
        def update_status(msg):
            with self.loading_lock:
                self.loading_status_message = msg
        
        Checkers.load_all_resources(update_status)
        self.reset_game_state(first_load=True)
        self.loading_state = 'side_selection'

    def reset_game_state(self, first_load=False):
        self.game = Checkers(load_resources=False)
        self.game_state_history = []
        self.selected_piece, self.valid_moves, self.board_is_flipped, self.last_move = None, {}, False, None
        self.ai_depth, self.is_ai_thinking, self.ai_move_result, self.ai_analysis_complete_paused = 5, False, None, False
        self.ai_all_evaluated_moves, self.ai_analysis_lock, self.ai_eval_count, self.developer_mode, self.ai_current_path, self.eval_scroll_offset = [], threading.Lock(), 0, False, [], 0
        self.game_mode = None
        self.human_player_color = None
        self.ai_is_paused = False
        self.play_red_rect = pygame.Rect(WIDTH//2 - 140, HEIGHT//2 - 25, 120, 50)
        self.play_white_rect = pygame.Rect(WIDTH//2 + 20, HEIGHT//2 - 25, 120, 50)

        if first_load:
            btn_h, start_x, y_pos, num_btns, btn_w = 40, 10, BOARD_SIZE + 5, 7, (WIDTH - 20) // 7
            self.buttons = { "Force Move": pygame.Rect(start_x, y_pos, btn_w, btn_h), "Dev Mode": pygame.Rect(start_x+btn_w, y_pos, btn_w, btn_h), "Reset": pygame.Rect(start_x+2*btn_w, y_pos, btn_w, btn_h), "Undo": pygame.Rect(start_x+3*btn_w, y_pos, btn_w, btn_h), "Save": pygame.Rect(start_x+4*btn_w, y_pos, btn_w, btn_h), "Load": pygame.Rect(start_x+5*btn_w, y_pos, btn_w, btn_h), "Export": pygame.Rect(start_x+6*btn_w, y_pos, btn_w, btn_h) }
            self.depth_minus_rect, self.depth_plus_rect = pygame.Rect(BOARD_SIZE+270, 195, 30, 30), pygame.Rect(BOARD_SIZE+320, 195, 30, 30)
            self.eval_scroll_up_rect, self.eval_scroll_down_rect = pygame.Rect(BOARD_SIZE+INFO_WIDTH-40, 315, 30, 25), pygame.Rect(BOARD_SIZE+INFO_WIDTH-40, BOARD_SIZE-75, 30, 25)

    def _update_ai_progress(self, all_moves, eval_count, current_path):
        with self.ai_analysis_lock:
            if all_moves: self.ai_all_evaluated_moves = all_moves
            if eval_count: self.ai_eval_count = eval_count
            if current_path: self.ai_current_path = current_path
    def _ai_worker(self): self.ai_move_result = self.game.find_best_move(self.ai_depth, self._update_ai_progress)
    def _start_ai_move(self):
        if self.is_ai_thinking or self.ai_analysis_complete_paused or self.game.winner: return
        self.is_ai_thinking, self.ai_move_result, self.eval_scroll_offset = True, "THINKING", 0
        with self.ai_analysis_lock: self.ai_all_evaluated_moves, self.ai_eval_count, self.ai_current_path = [], 0, []
        threading.Thread(target=self._ai_worker, daemon=True).start()
    def _get_display_coords(self, r, c): return (7-r, 7-c) if self.board_is_flipped else (r, c)
    def _get_logical_coords_from_mouse(self, pos):
        x, y = pos
        if x > BOARD_SIZE or y > BOARD_SIZE: return None, None
        r, c = y // SQUARE_SIZE, x // SQUARE_SIZE
        return (7-r, 7-c) if self.board_is_flipped else (r, c)
    def _handle_move(self, start, end):
        self.ai_is_paused = False
        if not self.game.forced_jumps: self.game_state_history.append(copy.deepcopy(self.game))
        self.game.perform_move(start, end)
        self.last_move = (start, end)
        self.selected_piece = self.game.forced_jumps[0][0] if self.game.forced_jumps else None
        self._update_valid_moves()
    def _sync_gui_to_game_state(self):
        self.game.winner = self.game.check_win_condition()
        self.selected_piece, self.last_move, self.is_ai_thinking, self.ai_analysis_complete_paused = None, None, False, False
        with self.ai_analysis_lock: self.ai_all_evaluated_moves, self.ai_eval_count = [], 0
        self._update_valid_moves()
    def _update_valid_moves(self):
        self.valid_moves = {}
        if not self.game: return
        possible = self.game.forced_jumps or (self.game.get_all_possible_moves(self.game.turn) if self.selected_piece else [])
        if self.selected_piece: possible = [m for m in possible if m[0] == self.selected_piece]
        for start, end in possible: self.valid_moves[end] = start
    def main_loop(self):
        running, clock = True, pygame.time.Clock()
        while running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False; continue
                
                if self.loading_state != 'done':
                    if self.loading_state == 'side_selection' and event.type == pygame.MOUSEBUTTONDOWN:
                        if self.play_red_rect.collidepoint(event.pos): self.human_player_color, self.game_mode, self.loading_state = RED, "P_VS_C", "done"
                        elif self.play_white_rect.collidepoint(event.pos): self.human_player_color, self.game_mode, self.loading_state = WHITE, "P_VS_C", "done"
                    continue

                if event.type == pygame.MOUSEWHEEL and self.developer_mode and (self.is_ai_thinking or self.ai_analysis_complete_paused) and mouse_pos[0] > BOARD_SIZE:
                    self.eval_scroll_offset = max(0, self.eval_scroll_offset - event.y)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and self.ai_analysis_complete_paused:
                    if self.ai_move_result: self._handle_move(self.ai_move_result[0], self.ai_move_result[1])
                    self.ai_analysis_complete_paused, self.ai_move_result = False, None
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.buttons["Force Move"].collidepoint(event.pos):
                        if self.is_ai_thinking:
                            with self.ai_analysis_lock:
                                if self.ai_all_evaluated_moves: self.ai_move_result = self.ai_all_evaluated_moves[0]['move']
                        else: self._start_ai_move()
                        continue

                    if self.is_ai_thinking or self.ai_analysis_complete_paused:
                        if self.eval_scroll_up_rect.collidepoint(event.pos): self.eval_scroll_offset=max(0,self.eval_scroll_offset-1)
                        elif self.eval_scroll_down_rect.collidepoint(event.pos): self.eval_scroll_offset+=1
                        continue
                    
                    if self.buttons["Dev Mode"].collidepoint(event.pos): self.developer_mode = not self.developer_mode
                    elif self.buttons["Reset"].collidepoint(event.pos): self.loading_state = 'side_selection'; self.reset_game_state()
                    elif self.buttons["Undo"].collidepoint(event.pos) and self.game_state_history:
                        self.game = self.game_state_history.pop()
                        self._sync_gui_to_game_state()
                        self.ai_is_paused = True
                    elif self.buttons["Save"].collidepoint(event.pos):
                        with open("savegame.dat", "wb") as f: pickle.dump(self.game, f)
                    elif self.buttons["Load"].collidepoint(event.pos) and os.path.exists("savegame.dat"):
                        with open("savegame.dat", "rb") as f: self.game = pickle.load(f)
                        self.game_state_history = []; self._sync_gui_to_game_state()
                    elif self.buttons["Export"].collidepoint(event.pos): self.game.export_to_pdn()
                    elif self.depth_minus_rect.collidepoint(event.pos): self.ai_depth = max(1, self.ai_depth - 1)
                    elif self.depth_plus_rect.collidepoint(event.pos): self.ai_depth = min(12, self.ai_depth + 1)
                    elif not self.game.winner:
                        row, col = self._get_logical_coords_from_mouse(event.pos)
                        if self.game.turn == self.human_player_color and row is not None:
                            if (row, col) in self.valid_moves: self._handle_move(self.valid_moves[(row, col)], (row, col))
                            elif not self.game.forced_jumps and self.game.board[row][col].lower() == self.game.turn:
                                self.selected_piece = (row, col); self._update_valid_moves()
                            else: self.selected_piece = None; self._update_valid_moves()
            
            if self.loading_state == 'loading': self.draw_loading_screen()
            elif self.loading_state == 'side_selection': self.draw_side_selection_screen(mouse_pos)
            elif self.game_mode:
                if not self.game.winner: self.game.winner = self.game.check_win_condition()
                if self.is_ai_thinking and self.ai_move_result != "THINKING":
                    self.is_ai_thinking = False
                    if self.developer_mode or self.game.turn != self.human_player_color: self.ai_analysis_complete_paused = True
                    else:
                        if self.ai_move_result: self._handle_move(self.ai_move_result[0], self.ai_move_result[1])
                        self.ai_move_result = None
                
                all_moves = self.game.get_all_possible_moves(self.game.turn) if self.game else []
                is_ai_turn = self.game and self.game.turn != self.human_player_color
                if is_ai_turn and all_moves and not (self.is_ai_thinking or self.ai_analysis_complete_paused or self.game.winner or self.ai_is_paused):
                    if len(all_moves) == 1:
                        self._handle_move(all_moves[0][0], all_moves[0][1])
                    else: self._start_ai_move()
                self._draw_game_screen(mouse_pos)
            
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()

    def draw_loading_screen(self):
        self.screen.fill(COLOR_BG)
        title_surf = self.font_large.render("Loading Resources...", True, COLOR_LIGHT)
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
        with self.loading_lock:
            status_surf = self.font_small.render(self.loading_status_message, True, COLOR_LIGHT)
            self.screen.blit(status_surf, status_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

    def draw_side_selection_screen(self, mouse_pos):
        self.screen.fill(COLOR_BG)
        title_surf = self.font_large.render("Choose Your Opening Side", True, COLOR_LIGHT)
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3)))
        
        for text, rect in {"Red": self.play_red_rect, "White": self.play_white_rect}.items():
            color = COLOR_BUTTON_HOVER if rect.collidepoint(mouse_pos) else COLOR_BUTTON
            pygame.draw.rect(self.screen, color, rect)
            text_surf = self.font_medium.render(text, True, COLOR_TEXT)
            self.screen.blit(text_surf, text_surf.get_rect(center=rect.center))

    def _wrap_text(self, text, font, max_width):
        lines, words = [], text.split(' ');
        if not words: return []
        current_line = words[0]
        for word in words[1:]:
            if font.size(current_line + ' ' + word)[0] <= max_width: current_line += ' ' + word
            else: lines.append(current_line); current_line = word
        lines.append(current_line)
        return lines

    def _draw_game_screen(self, mouse_pos):
        self.screen.fill(COLOR_BG); self._draw_board(); self._draw_last_move_highlight()
        if self.developer_mode and (self.is_ai_thinking or self.ai_analysis_complete_paused): self._draw_dev_mode_highlights()
        self._draw_pieces(); self._draw_valid_moves(); self._draw_info_panel(mouse_pos); self._draw_menu_bar(mouse_pos)

    def _draw_board(self):
        for r_l in range(ROWS):
            for c_l in range(COLS):
                r_d, c_d = self._get_display_coords(r_l, c_l)
                color = COLOR_LIGHT if (r_d + c_d) % 2 == 0 else COLOR_DARK
                pygame.draw.rect(self.screen, color, (c_d*SQUARE_SIZE, r_d*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
                if (r_l + c_l) % 2 == 1:
                    num_text = self.font_small.render(str(COORD_TO_ACF.get((r_l, c_l), '')), True, COLOR_LIGHT)
                    self.screen.blit(num_text, (c_d*SQUARE_SIZE+5, r_d*SQUARE_SIZE+5))

    def _draw_last_move_highlight(self):
        if not self.last_move: return
        s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA); s.fill(COLOR_LAST_MOVE)
        for r_l, c_l in self.last_move:
            r_d, c_d = self._get_display_coords(r_l, c_l)
            self.screen.blit(s, (c_d*SQUARE_SIZE, r_d*SQUARE_SIZE))

    def _draw_dev_mode_highlights(self):
        with self.ai_analysis_lock: path = self.ai_current_path
        if not path: return
        for i, (start, end) in enumerate(path[:self.MAX_DEV_HIGHLIGHTS]):
            color = COLOR_DEV_PRIMARY if i == 0 else COLOR_DEV_SECONDARY
            s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA); s.fill(color)
            for r_l, c_l in [start, end]:
                r_d, c_d = self._get_display_coords(r_l, c_l)
                self.screen.blit(s, (c_d*SQUARE_SIZE, r_d*SQUARE_SIZE))

    def _draw_pieces(self):
        radius = SQUARE_SIZE//2 - 8; self.piece_counts = [0,0,0,0]
        for r_l in range(ROWS):
            for c_l in range(COLS):
                piece = self.game.board[r_l][c_l]
                if piece != EMPTY:
                    r_d, c_d = self._get_display_coords(r_l, c_l)
                    cx, cy = c_d*SQUARE_SIZE + SQUARE_SIZE//2, r_d*SQUARE_SIZE + SQUARE_SIZE//2
                    if (r_l, c_l) == self.selected_piece: pygame.draw.circle(self.screen, COLOR_SELECTED, (cx, cy), radius + 4)
                    pygame.draw.circle(self.screen, COLOR_RED_P if piece.lower() == RED else COLOR_WHITE_P, (cx, cy), radius)
                    if piece.isupper(): pygame.draw.circle(self.screen, COLOR_CROWN, (cx, cy), radius // 2)
                    idx = {'r':0, 'R':1, 'w':2, 'W':3}[piece]
                    self.piece_counts[idx] += 1

    def _draw_valid_moves(self):
        if not self.valid_moves: return
        s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA); pygame.draw.circle(s, COLOR_VALID, (SQUARE_SIZE//2, SQUARE_SIZE//2), 15)
        for r_l, c_l in self.valid_moves.keys():
            r_d, c_d = self._get_display_coords(r_l, c_l)
            self.screen.blit(s, (c_d*SQUARE_SIZE, r_d*SQUARE_SIZE))

    def _draw_info_panel(self, mouse_pos):
        panel_x, y = BOARD_SIZE+20, 20; panel_re = BOARD_SIZE+INFO_WIDTH-20
        self.screen.blit(self.font_medium.render("CHECKERS", True, COLOR_LIGHT), (panel_x, y)); y+=40
        if self.game.winner: txt = f"Winner: {PLAYER_NAMES[self.game.winner]}!"; surf = self.font_large.render(txt,True,COLOR_CROWN)
        else: txt = f"Turn: {PLAYER_NAMES[self.game.turn]}"; surf = self.font_medium.render(txt,True,COLOR_WHITE_P if self.game.turn==WHITE else COLOR_RED_P)
        self.screen.blit(surf, (panel_x, y)); y+=40
        score = Checkers.evaluate_board_static(self.game.board,self.game.turn)/Checkers.MATERIAL_MULTIPLIER
        adv = f"+{score:.2f} (Red Adv.)" if score>0.05 else f"{score:.2f} (White Adv.)" if score<-0.05 else "Even"
        self.screen.blit(self.font_small.render(f"Positional Score: {adv}",True,COLOR_LIGHT), (panel_x, y)); y+=25
        rm, rk, wm, wk = self.piece_counts
        self.screen.blit(self.font_small.render(f"Red: {rm} men, {rk} kings",True,COLOR_RED_P), (panel_x,y)); y+=20
        self.screen.blit(self.font_small.render(f"White: {wm} men, {wk} kings",True,COLOR_WHITE_P), (panel_x,y)); y+=25
        self.screen.blit(self.font_small.render(f"AI Depth: {self.ai_depth}",True,COLOR_LIGHT), (panel_x, y)); y+=30
        is_dis = self.is_ai_thinking or self.ai_analysis_complete_paused
        for r, t in [(self.depth_minus_rect, "-"), (self.depth_plus_rect, "+")]:
            color = COLOR_BUTTON_HOVER if r.collidepoint(mouse_pos) and not is_dis else COLOR_BUTTON_DISABLED if is_dis else COLOR_BUTTON
            pygame.draw.rect(self.screen, color, r); self.screen.blit(self.font_medium.render(t,True,COLOR_TEXT), r.move(10 if t=='-' else 7, 1))
        y+=10
        
        is_ai_active = self.is_ai_thinking or self.ai_analysis_complete_paused
        if is_ai_active:
            if self.ai_analysis_complete_paused:
                self.screen.blit(self.font_small.render("Analysis Complete!", True, COLOR_CROWN), (panel_x, y)); y+=20
                self.screen.blit(self.font_small.render("Press SPACE to make move.", True, COLOR_LIGHT), (panel_x, y)); y+=25
            else: # is_ai_thinking
                self.screen.blit(self.font_small.render("Thinking...", True, COLOR_LIGHT), (panel_x, y)); y+=45

            if self.developer_mode:
                with self.ai_analysis_lock: moves, count = self.ai_all_evaluated_moves, self.ai_eval_count
                self.screen.blit(self.font_small.render(f"Positions: {count:,}", True, COLOR_LIGHT), (panel_x, y)); y+=25
                self.screen.blit(self.font_small.render("Principal Variations:", True, COLOR_LIGHT), (panel_x, y)); y+=25
                list_y_start, line_h = y, 22
                clip_area = pygame.Rect(panel_x, list_y_start, INFO_WIDTH - 30, BOARD_SIZE - list_y_start - 50)
                for r_scroll, t in [(self.eval_scroll_up_rect, "^"), (self.eval_scroll_down_rect, "v")]:
                    pygame.draw.rect(self.screen, COLOR_BUTTON_HOVER if r_scroll.collidepoint(mouse_pos) else COLOR_BUTTON, r_scroll)
                    self.screen.blit(self.font_small.render(t,True,COLOR_TEXT), r_scroll.move(12, 4))
                self.screen.set_clip(clip_area); current_y = list_y_start
                for i, move_data in enumerate(moves):
                    if i < self.eval_scroll_offset or current_y > clip_area.bottom: continue
                    path = move_data['path']; path_str_parts = []
                    j=0
                    while j < len(path):
                        start, end = path[j]
                        if abs(start[0] - end[0]) != 2: # Simple move
                            path_str_parts.append(f"{coord_to_acf_notation(start)}-{coord_to_acf_notation(end)}"); j+=1
                        else: # Jump sequence
                            jump_seq = [coord_to_acf_notation(start), coord_to_acf_notation(end)]
                            while (j + 1 < len(path)) and (path[j+1][0] == path[j][1]) and (abs(path[j+1][0][0]-path[j+1][1][0])==2):
                                j+=1; jump_seq.append(coord_to_acf_notation(path[j][1]))
                            path_str_parts.append("x".join(jump_seq)); j+=1
                    path_str = " -> ".join(path_str_parts)

                    score_str = f"({move_data['score']/Checkers.MATERIAL_MULTIPLIER:+.2f})"; color = COLOR_CROWN if i==0 else COLOR_LIGHT
                    score_surf = self.font_small.render(score_str, True, color); score_rect = score_surf.get_rect(topright=(panel_re, current_y))
                    for k, line in enumerate(self._wrap_text(f"{i+1}. {path_str}", self.font_small, clip_area.width - score_rect.width - 15)):
                        if current_y > clip_area.bottom: break
                        self.screen.blit(self.font_small.render(line, True, color), (panel_x, current_y))
                        if k==0: self.screen.blit(score_surf, score_rect)
                        current_y += line_h
                self.screen.set_clip(None)

    def _draw_menu_bar(self, mouse_pos):
        pygame.draw.rect(self.screen, COLOR_BG, (0, BOARD_SIZE, WIDTH, MENU_BAR_HEIGHT))
        for text, rect in self.buttons.items():
            is_clickable = True
            if text not in ["Force Move", "Dev Mode", "Reset"] and (self.is_ai_thinking or self.ai_analysis_complete_paused):
                is_clickable = False
            
            color = COLOR_BUTTON_HOVER if rect.collidepoint(mouse_pos) and is_clickable else (COLOR_BUTTON if is_clickable else COLOR_BUTTON_DISABLED)
            pygame.draw.rect(self.screen, color, rect)
            disp_text = "Dev: ON" if text == 'Dev Mode' and self.developer_mode else text
            text_surf = self.font_small.render(disp_text, True, COLOR_TEXT)
            self.screen.blit(text_surf, text_surf.get_rect(center=rect.center))

if __name__ == '__main__':
    gui = CheckersGUI()
    gui.main_loop()
