# engine/board.py
from .constants import *

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
        piece_to_move = self.board[start[0]][start[1]]
        self.board[end[0]][end[1]] = piece_to_move; self.board[start[0]][start[1]] = EMPTY
        promotion = self._promote_to_king(end[0], end[1])
        captured_piece, captured_pos = None, None
        if abs(start[0] - end[0]) == 2:
            captured_pos = ((start[0]+end[0])//2, (start[1]+end[1])//2)
            captured_piece = self.board[captured_pos[0]][captured_pos[1]]
            self.board[captured_pos[0]][captured_pos[1]] = EMPTY
        
        further_jumps = []
        if captured_piece:
            _, further_jumps_list = self._get_piece_moves(end[0], end[1])
            if further_jumps_list:
                further_jumps = [(end, j_end) for _, j_end in further_jumps_list]
        
        return further_jumps, captured_piece, captured_pos, promotion
