# engine/board.py
from .constants import *
import logging

class Board:
    def __init__(self, board_state=None, turn=None):
        self.board = self._setup_board() if board_state is None else [row[:] for row in board_state]
        self.turn = RED if turn is None else turn
        self.forced_jumps = []

    def _setup_board(self):
        board = [[EMPTY for _ in range(8)] for _ in range(8)]
        for r in range(8):
            for c in range(8):
                if (r + c) % 2 == 1:
                    if r < 3: board[r][c] = RED
                    elif r > 4: board[r][c] = WHITE
        return board
    
    def get_all_possible_moves(self, player):
        if self.forced_jumps:
            if self.forced_jumps and self.board[self.forced_jumps[0][0][0]][self.forced_jumps[0][0][1]].lower() == player:
                return self.forced_jumps
            else:
                self.forced_jumps = []
        all_simple, all_jumps = [], []
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
                if 0<=row+dr<8 and 0<=col+dc<8 and self.board[row+dr][col+dc].lower() not in [piece.lower(), EMPTY]:
                    jumps.append(((row,col),(r_j,c_j)))
        return simple, jumps

    def _promote_to_king(self, row, col):
        piece = self.board[row][col]
        if piece == RED and row == 7: self.board[row][col] = RED_KING; return True
        elif piece == WHITE and row == 0: self.board[row][col] = WHITE_KING; return True
        return False
        
    def perform_move(self, start, end):
        logging.debug(f"Performing move: {start} -> {end}")
        piece_to_move = self.board[start[0]][start[1]]
        self.board[end[0]][end[1]] = piece_to_move; self.board[start[0]][start[1]] = EMPTY
        promotion = self._promote_to_king(end[0], end[1])
        captured_piece, captured_pos = [], None
        is_jump = abs(start[0] - end[0]) == 2
        if is_jump:
            captured_pos = ((start[0]+end[0])//2, (start[1]+end[1])//2)
            captured_piece = [self.board[captured_pos[0]][captured_pos[1]]]
            self.board[captured_pos[0]][captured_pos[1]] = EMPTY
        further_jumps = []
        if is_jump:
            _, further_jumps_list = self._get_piece_moves(end[0], end[1])
            if further_jumps_list:
                further_jumps = [(end, j_end) for _, j_end in further_jumps_list]
        self.forced_jumps = further_jumps
        logging.debug(f"Move result: captured={captured_piece}, pos={captured_pos}, promotion={promotion}, is_jump={is_jump}")
        return captured_piece, captured_pos, promotion, is_jump

    def is_game_over(self, board=None):
        logging.debug("Checking if game is over")
        board = board if board is not None else self.board
        red_pieces = sum(row.count(RED) + row.count(RED_KING) for row in board)
        white_pieces = sum(row.count(WHITE) + row.count(WHITE_KING) for row in board)
        if red_pieces == 0:
            logging.debug("Game over: White wins, no Red pieces remain")
            return True, WHITE
        if white_pieces == 0:
            logging.debug("Game over: Red wins, no White pieces remain")
            return True, RED
        # Check if the current player has no legal moves
        moves = self.get_all_possible_moves(self.turn)
        if not moves:
            winner = WHITE if self.turn == RED else RED
            logging.debug(f"Game over: {PLAYER_NAMES[winner]} wins, {PLAYER_NAMES[self.turn]} has no moves")
            return True, winner
        logging.debug("Game not over")
        return False, None
