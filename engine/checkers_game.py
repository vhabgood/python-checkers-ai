#checkers_game.py
import copy
import random
from engine.constants import *
from engine.board import Board
import logging

class Checkers:
    MATERIAL_MULTIPLIER = 100
    ZOBRIST_KEYS = {}
    for piece in [RED, WHITE, RED_KING, WHITE_KING]:
        for i in range(32):
            ZOBRIST_KEYS[(piece, i+1)] = random.getrandbits(64)
    ZOBRIST_KEYS['turn'] = random.getrandbits(64)

    def __init__(self):
        self.game_board = Board()
        self.hash = self._compute_initial_hash()

    @property
    def winner(self):
        is_over, winner = self.game_board.is_game_over()
        return winner if is_over else None

    def _compute_initial_hash(self):
        h = 0
        for row in range(8):
            for col in range(8):
                piece = self.game_board.board[row][col]
                if piece != EMPTY:
                    acf = COORD_TO_ACF[(row, col)]
                    h ^= self.ZOBRIST_KEYS.get((piece, acf), 0)
        if self.game_board.turn == WHITE:
            h ^= self.ZOBRIST_KEYS.get('turn', 0)
        return h

    def static_minimax(self, board, hash_val, turn, depth, alpha, beta, eval_counter, progress_callback, killer_moves, path):
        eval_counter[0] += 1
        is_over, _ = self.game_board.is_game_over(board)
        if depth == 0 or is_over:
            score = self.evaluate_board_static(board, turn)
            if progress_callback:
                progress_callback(eval_counter[0], 0, [{'score': score, 'path': path}])
            return score, path
        temp_game = Checkers()
        temp_game.game_board.board = [row[:] for row in board]
        temp_game.game_board.turn = turn
        temp_game.hash = hash_val
        best_score = -float('inf') if turn == RED else float('inf')
        best_path = []
        moves = temp_game.game_board.get_all_possible_moves(turn)
        ordered_moves = []
        for killer in killer_moves.get(depth, []):
            if killer in moves:
                ordered_moves.append(killer)
        ordered_moves.extend([m for m in moves if m not in ordered_moves])
        evaluated_moves = []
        for start, end in ordered_moves:
            further_jumps = temp_game.perform_move_for_search(start, end)
            new_path = path + [(start, end)]
            if further_jumps:
                for jump_end in further_jumps:
                    score, sub_path = self.static_minimax(temp_game.game_board.board, temp_game.hash, turn, depth, alpha, beta, eval_counter, progress_callback, killer_moves, new_path + [(end, jump_end)])
                    if turn == RED:
                        if score > best_score:
                            best_score = score
                            best_path = sub_path
                            alpha = max(alpha, best_score)
                    else:
                        if score < best_score:
                            best_score = score
                            best_path = sub_path
                            beta = min(beta, best_score)
                    evaluated_moves.append({'score': score, 'path': sub_path})
                    if beta <= alpha:
                        break
            else:
                score, sub_path = self.static_minimax(temp_game.game_board.board, temp_game.hash, RED if turn == WHITE else WHITE, depth - 1, alpha, beta, eval_counter, progress_callback, killer_moves, new_path)
                if turn == RED:
                    if score > best_score:
                        best_score = score
                        best_path = sub_path
                        alpha = max(alpha, best_score)
                    evaluated_moves.append({'score': score, 'path': sub_path})
                else:
                    if score < best_score:
                        best_score = score
                        best_path = sub_path
                        beta = min(beta, best_score)
                    evaluated_moves.append({'score': score, 'path': sub_path})
                if beta <= alpha:
                    break
            temp_game.game_board.board = [row[:] for row in board]
            temp_game.game_board.turn = turn
            temp_game.hash = hash_val
        if progress_callback:
            progress_callback(eval_counter[0], 0, evaluated_moves)
        return best_score, best_path

    def find_best_move(self, depth, progress_callback=None):
        eval_counter = [0]
        killer_moves = {i: [] for i in range(depth + 1)}
        best_score, best_path = self.static_minimax(self.game_board.board, self.hash, self.game_board.turn, depth, -float('inf'), float('inf'), eval_counter, progress_callback, killer_moves, [])
        return best_path

    def perform_move(self, start, end):
        captured_piece, captured_pos, promotion, is_jump = self.game_board.perform_move(start, end)
        self._update_hash((start, end), captured_piece, captured_pos, promotion)
        return self.game_board.forced_jumps

    def perform_move_for_search(self, start, end):
        logging.debug(f"Performing move for search: {start} -> {end}")
        result = self.game_board.perform_move(start, end)
        logging.debug(f"Board.perform_move returned: {result}")
        captured_piece, captured_pos, promotion, is_jump = result
        logging.debug(f"Captured: {captured_piece}, Pos: {captured_pos}, Promotion: {promotion}, Is Jump: {is_jump}")
        self._update_hash((start, end), captured_piece, captured_pos, promotion)
        return self.game_board.forced_jumps

    def _update_hash(self, move, captured_piece=None, captured_pos=None, promotion=False):
        logging.debug(f"Updating hash for move: {move}, captured_piece: {captured_piece}, captured_pos: {captured_pos}, promotion: {promotion}")
        start, end = move
        piece = self.game_board.board[end[0]][end[1]]
        start_acf, end_acf = COORD_TO_ACF[start], COORD_TO_ACF[end]
        original_piece = piece.lower() if promotion else piece
        self.hash ^= self.ZOBRIST_KEYS.get((original_piece, start_acf), 0)
        self.hash ^= self.ZOBRIST_KEYS.get((piece, end_acf), 0)
        if captured_piece and captured_pos:
            for cap_piece in captured_piece:
                if cap_piece:
                    logging.debug(f"Hashing capture: piece={cap_piece}, pos={captured_pos}")
                    self.hash ^= self.ZOBRIST_KEYS.get((cap_piece, COORD_TO_ACF[captured_pos]), 0)
        if not self.game_board.forced_jumps:
            self.hash ^= self.ZOBRIST_KEYS.get('turn', 0)

    def evaluate_board_static(self, board, turn):
        logging.debug(f"Calling evaluate_board_static with board={board}, turn={turn}")
        logging.debug("Attempting to import evaluate_board_static")
        from engine.evaluation import evaluate_board_static
        return evaluate_board_static(board, turn, piece_values)
