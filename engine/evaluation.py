# engine/evaluation.py
from engine.constants import *
from engine.board import Board
import logging

def evaluate_board_static(board, turn):
    logging.debug("Evaluating board state")
    mat_score = 0
    pos_score = 0
    center_score = 0
    jump_score = 0
    edge_penalty = 0
    mobility_score = 0
    king_threat = 0
    jump_distance_penalty = 0
    temp_board = Board()
    temp_board.board = [row[:] for row in board]
    for i in range(8):
        for j in range(8):
            piece = board[i][j]
            if piece != EMPTY:
                row_score = i if piece.lower() == WHITE else 7 - i
                row_score = (row_score + 1) / 4
                is_center = j in [3, 4]
                is_edge = j in [0, 7]
                is_near_promotion = (i <= 1 and piece == RED) or (i >= 6 and piece == WHITE)
                if piece == RED:
                    mat_score += 2500
                    pos_score += row_score
                    center_score += 500 if is_center else 0
                    edge_penalty -= 200 if is_edge else 0
                    king_threat += 1000 if is_near_promotion else 0
                elif piece == WHITE:
                    mat_score -= 2500
                    pos_score -= row_score
                    center_score -= 500 if is_center else 0
                    edge_penalty += 200 if is_edge else 0
                    king_threat -= 1000 if is_near_promotion else 0
                elif piece == RED_KING:
                    mat_score += 4000
                    pos_score += row_score * 0.5
                    center_score += 750 if is_center else 0
                    edge_penalty -= 300 if is_edge else 0
                elif piece == WHITE_KING:
                    mat_score -= 4000
                    pos_score -= row_score * 0.5
                    center_score -= 750 if is_center else 0
                    edge_penalty += 300 if is_edge else 0
    red_jumps = sum(len(temp_board.get_jumps_for_piece((i, j), board[i][j])) for i in range(8) for j in range(8) if board[i][j] in [RED, RED_KING])
    white_jumps = sum(len(temp_board.get_jumps_for_piece((i, j), board[i][j])) for i in range(8) for j in range(8) if board[i][j] in [WHITE, WHITE_KING])
    jump_score = 700 * (red_jumps - white_jumps)
    temp_board.turn = RED
    red_moves = len(temp_board.get_all_possible_moves(RED))
    temp_board.turn = WHITE
    white_moves = len(temp_board.get_all_possible_moves(WHITE))
    mobility_score = 200 * (red_moves - white_moves)
    # Penalize long jumps
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece != EMPTY:
                jumps = temp_board.get_jumps_for_piece((row, col), piece)
                for start, end in jumps:
                    row_diff = abs(start[0] - end[0])
                    if row_diff > 2:  # Penalize jumps > 2 rows
                        jump_distance_penalty -= 500 if piece.lower() == RED else -500
    logging.debug(f"Red jumps: {red_jumps}, White jumps: {white_jumps}, Jump score: {jump_score}")
    logging.debug(f"Red moves: {red_moves}, White moves: {white_moves}, Mobility score: {mobility_score}")
    logging.debug(f"King threat score: {king_threat}")
    logging.debug(f"Jump distance penalty: {jump_distance_penalty}")
    final_score = mat_score + pos_score * 1000 + center_score + jump_score + edge_penalty + mobility_score + king_threat + jump_distance_penalty
    logging.debug(f"evaluate_board_static components: mat={mat_score}, pos={pos_score*1000}, center={center_score}, jumps={jump_score}, edge={edge_penalty}, mobility={mobility_score}, king_threat={king_threat}, jump_distance_penalty={jump_distance_penalty}, final={final_score}")
    return final_score if turn == RED else -final_score
