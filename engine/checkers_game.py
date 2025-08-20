# engine/checkers_game.py
import copy
import sys
import os
import pickle
import time
import logging
import argparse
from engine.board import Board
from engine.constants import *
from engine.evaluation import evaluate_board_static

class Checkers:
    def __init__(self, use_db=True):
        self.game_board = Board()
        self.winner = None
        self.endgame_db = {}
        if use_db:
            self._load_endgame_db()
        else:
            logging.info("Endgame database loading skipped due to --no-db flag")

    def _load_endgame_db(self):
        resource_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
        possible_dbs = [
            'db_2k1m_vs_2k1m.pkl', 'db_2k1m_vs_2k.pkl', 'db_2k1m_vs_3k.pkl',
            'db_2v1_kings.pkl', 'db_2v1_men.pkl', 'db_3v1k1m.pkl',
            'db_3v1_kings.pkl', 'db_3v2_kings.pkl', 'db_3v3_kings.pkl',
            'db_4v2_kings.pkl', 'db_4v3_kings.pkl'
        ]
        for db_name in possible_dbs:
            db_path = os.path.join(resource_dir, db_name)
            try:
                if os.path.exists(db_path):
                    with open(db_path, 'rb') as f:
                        db = pickle.load(f)
                        self.endgame_db.update(db)
                    logging.info(f"Loaded endgame database: {db_path}")
                else:
                    logging.debug(f"Endgame database not found: {db_path}")
            except Exception as e:
                logging.error(f"Failed to load endgame database {db_path}: {str(e)}")
        if not self.endgame_db:
            logging.info("No endgame databases loaded")
        else:
            logging.debug(f"Endgame database size: {len(self.endgame_db)} entries")

    def _get_board_key(self, board):
        piece_count = sum(row.count(RED) + row.count(RED_KING) + row.count(WHITE) + row.count(WHITE_KING) for row in board)
        if piece_count > 6:
            return None, None
        red_men = sum(row.count(RED) for row in board)
        red_kings = sum(row.count(RED_KING) for row in board)
        white_men = sum(row.count(WHITE) for row in board)
        white_kings = sum(row.count(WHITE_KING) for row in board)
        board_str = ''.join(''.join(row) for row in board) + self.game_board.turn
        acf_positions = []
        for row in range(8):
            for col in range(8):
                if (row, col) in COORD_TO_ACF and board[row][col] != EMPTY:
                    acf_positions.append(f"{COORD_TO_ACF[(row,col)]}:{board[row][col]}")
        acf_key = ','.join(sorted(acf_positions)) + f":{self.game_board.turn}"
        return board_str, acf_key

    def perform_move(self, start, end):
        logging.debug(f"Performing move: {start} -> {end}, ACF: {COORD_TO_ACF.get(start, '??')}-{COORD_TO_ACF.get(end, '??')}")
        captured_piece, captured_pos, promotion, is_jump = self.game_board.move_piece(start, end)
        if not is_jump or not self.game_board.forced_jumps:
            self.game_board.turn = WHITE if self.game_board.turn == RED else RED
        self.winner = self._check_winner()
        logging.debug(f"Move result: captured={captured_piece}, pos={captured_pos}, promotion={promotion}, is_jump={is_jump}, new_turn={self.game_board.turn}")
        return captured_piece, captured_pos, promotion, is_jump

    def _check_winner(self):
        red_moves = self.game_board.get_all_possible_moves(RED)
        white_moves = self.game_board.get_all_possible_moves(WHITE)
        if not red_moves and self.game_board.turn == RED:
            return WHITE
        if not white_moves and self.game_board.turn == WHITE:
            return RED
        return None

    def evaluate_board_static(self, board, turn):
        return evaluate_board_static(board, turn)

    def find_best_move(self, depth, progress_callback):
        logging.debug(f"Finding best move for {self.game_board.turn} at depth {depth}")
        start_time = time.time()
        timeout = 5  # Reduced timeout to prevent freezes
        board_key, acf_key = self._get_board_key(self.game_board.board)
        if self.endgame_db:
            move = self.endgame_db.get(board_key) or self.endgame_db.get(acf_key)
            if move:
                logging.debug(f"Endgame database hit: move={move}, ACF: {COORD_TO_ACF.get(move[0], '??') if isinstance(move[0], tuple) else move}")
                return move
        all_moves = self.game_board.get_all_possible_moves(self.game_board.turn)
        logging.debug(f"All evaluated moves: {[(COORD_TO_ACF.get(s, '??') + '-' + COORD_TO_ACF.get(e, '??')) for s, e in all_moves]}")
        if not all_moves:
            logging.error("No legal moves available")
            return None
        non_jump_moves = [m for m in all_moves if abs(m[0][0] - m[1][0]) == 1 and m[0] in COORD_TO_ACF and m[1] in COORD_TO_ACF]
        best_move = non_jump_moves[0] if non_jump_moves else None
        best_score = float('-inf') if self.game_board.turn == RED else float('inf')
        evaluated_moves = []
        eval_count = 0
        eval_total = len(all_moves) * depth
        for start, end in all_moves:
            if time.time() - start_time > timeout:
                logging.error("Move evaluation timed out")
                break
            if start not in COORD_TO_ACF or end not in COORD_TO_ACF:
                logging.warning(f"Invalid move coordinates: {start} -> {end}")
                continue
            eval_count += 1
            temp_board = copy.deepcopy(self.game_board)
            move_path = [(start, end)]
            captured_piece, captured_pos, promotion, is_jump = temp_board.move_piece(start, end)
            if captured_piece == EMPTY and is_jump:
                logging.debug(f"Skipping invalid jump: {start} -> {end}")
                continue
            while is_jump and temp_board.forced_jumps:
                if time.time() - start_time > timeout:
                    logging.error("Chained jump evaluation timed out")
                    break
                next_start = move_path[-1][1]
                next_end = temp_board.forced_jumps[0][1]
                if next_start not in COORD_TO_ACF or next_end not in COORD_TO_ACF:
                    logging.warning(f"Invalid chained jump coordinates: {next_start} -> {next_end}")
                    break
                move_path.append((next_start, next_end))
                captured_piece, captured_pos, promotion, is_jump = temp_board.move_piece(next_start, next_end)
                if captured_piece == EMPTY and is_jump:
                    logging.debug(f"Skipping invalid chained jump: {next_start} -> {next_end}")
                    break
            score, pv = self._minimax(temp_board, depth - 1, float('-inf'), float('inf'), self.game_board.turn)
            full_pv = move_path + pv
            path_text = ", ".join(f"{COORD_TO_ACF.get((s[0], s[1]), '??')}-{COORD_TO_ACF.get((e[0], e[1]), '??')}" for s, e in full_pv)
            evaluated_moves.append({'pv': full_pv, 'score': score})
            progress_callback(eval_count, eval_total, evaluated_moves)
            logging.debug(f"Evaluated move path: {path_text}, score={score/1500:.2f}")
            if self.game_board.turn == RED and score > best_score:
                best_score = score
                best_move = (start, end)
            elif self.game_board.turn == WHITE and score < best_score:
                best_score = score
                best_move = (start, end)
        if best_move is None:
            logging.error("No valid best move found after evaluation")
            return non_jump_moves[0] if non_jump_moves else None
        logging.debug(f"Best move selected: {best_move}, ACF: {COORD_TO_ACF.get(best_move[0], '??')}-{COORD_TO_ACF.get(best_move[1], '??')}, score={best_score/1500:.2f}")
        return best_move

    def _minimax(self, board, depth, alpha, beta, maximizing_player):
        start_time = time.time()
        timeout = 3  # Reduced timeout
        if depth == 0 or time.time() - start_time > timeout or board.get_all_possible_moves(RED) == [] or board.get_all_possible_moves(WHITE) == []:
            if time.time() - start_time > timeout:
                logging.error("Minimax evaluation timed out")
            score = self.evaluate_board_static(board.board, maximizing_player)
            logging.debug(f"Leaf node evaluated: score={score/1500:.2f}")
            return score, []
        next_turn = WHITE if board.turn == RED else RED
        temp_board = copy.deepcopy(board)
        temp_board.turn = next_turn
        if board.turn == RED:
            max_eval = float('-inf')
            best_pv = []
            for start, end in board.get_all_possible_moves(RED):
                if time.time() - start_time > timeout:
                    logging.error("Minimax move evaluation timed out")
                    break
                if start not in COORD_TO_ACF or end not in COORD_TO_ACF:
                    logging.warning(f"Invalid move coordinates in minimax: {start} -> {end}")
                    continue
                temp_board = copy.deepcopy(board)
                move_path = [(start, end)]
                captured_piece, captured_pos, promotion, is_jump = temp_board.move_piece(start, end)
                if captured_piece == EMPTY and is_jump:
                    logging.debug(f"Skipping invalid jump in minimax: {start} -> {end}")
                    continue
                while is_jump and temp_board.forced_jumps:
                    if time.time() - start_time > timeout:
                        logging.error("Minimax chained jump evaluation timed out")
                        break
                    next_start = move_path[-1][1]
                    next_end = temp_board.forced_jumps[0][1]
                    if next_start not in COORD_TO_ACF or next_end not in COORD_TO_ACF:
                        logging.warning(f"Invalid chained jump coordinates in minimax: {next_start} -> {next_end}")
                        break
                    move_path.append((next_start, next_end))
                    captured_piece, captured_pos, promotion, is_jump = temp_board.move_piece(next_start, next_end)
                    if captured_piece == EMPTY and is_jump:
                        logging.debug(f"Skipping invalid chained jump in minimax: {next_start} -> {next_end}")
                        break
                temp_board.turn = WHITE
                eval_score, pv = self._minimax(temp_board, depth - 1, alpha, beta, maximizing_player)
                path_text = ", ".join(f"{COORD_TO_ACF.get((s[0], s[1]), '??')}-{COORD_TO_ACF.get((e[0], e[1]), '??')}" for s, e in move_path + pv)
                logging.debug(f"Red move: {path_text}, score={eval_score/1500:.2f}")
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_pv = move_path + pv
                alpha = max(alpha, eval_score)
                if beta <= alpha and abs(max_eval) < FUTILITY_MARGIN:
                    break
            return max_eval, best_pv
        else:
            min_eval = float('inf')
            best_pv = []
            for start, end in board.get_all_possible_moves(WHITE):
                if time.time() - start_time > timeout:
                    logging.error("Minimax move evaluation timed out")
                    break
                if start not in COORD_TO_ACF or end not in COORD_TO_ACF:
                    logging.warning(f"Invalid move coordinates in minimax: {start} -> {end}")
                    continue
                temp_board = copy.deepcopy(board)
                move_path = [(start, end)]
                captured_piece, captured_pos, promotion, is_jump = temp_board.move_piece(start, end)
                if captured_piece == EMPTY and is_jump:
                    logging.debug(f"Skipping invalid jump in minimax: {start} -> {end}")
                    continue
                while is_jump and temp_board.forced_jumps:
                    if time.time() - start_time > timeout:
                        logging.error("Minimax chained jump evaluation timed out")
                        break
                    next_start = move_path[-1][1]
                    next_end = temp_board.forced_jumps[0][1]
                    if next_start not in COORD_TO_ACF or next_end not in COORD_TO_ACF:
                        logging.warning(f"Invalid chained jump coordinates in minimax: {next_start} -> {next_end}")
                        break
                    move_path.append((next_start, next_end))
                    captured_piece, captured_pos, promotion, is_jump = temp_board.move_piece(next_start, next_end)
                    if captured_piece == EMPTY and is_jump:
                        logging.debug(f"Skipping invalid chained jump in minimax: {next_start} -> {next_end}")
                        break
                temp_board.turn = RED
                eval_score, pv = self._minimax(temp_board, depth - 1, alpha, beta, maximizing_player)
                path_text = ", ".join(f"{COORD_TO_ACF.get((s[0], s[1]), '??')}-{COORD_TO_ACF.get((e[0], e[1]), '??')}" for s, e in move_path + pv)
                logging.debug(f"White move: {path_text}, score={eval_score/1500:.2f}")
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_pv = move_path + pv
                beta = min(beta, eval_score)
                if beta <= alpha and abs(min_eval) < FUTILITY_MARGIN:
                    break
            return min_eval, best_pv
