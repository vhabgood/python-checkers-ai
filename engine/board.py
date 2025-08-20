# engine/board.py
from engine.constants import *
import logging

class Board:
    def __init__(self):
        self.board = [[EMPTY for _ in range(8)] for _ in range(8)]
        self.turn = RED
        self.forced_jumps = []
        try:
            self.setup_board()
        except Exception as e:
            logging.error(f"Board initialization failed: {str(e)}")
            raise

    def setup_board(self):
        logging.debug("Setting up initial board")
        self.board = [[EMPTY for _ in range(8)] for _ in range(8)]
        red_squares = [(r, c) for (r, c), acf in COORD_TO_ACF.items() if int(acf) <= 12]
        white_squares = [(r, c) for (r, c), acf in COORD_TO_ACF.items() if int(acf) >= 21]
        for row, col in red_squares:
            if (row + col) % 2 != 0:
                logging.error(f"Light square in COORD_TO_ACF for Red: ({row},{col})={COORD_TO_ACF[(row,col)]}")
                continue
            if self.board[row][col] != EMPTY:
                logging.warning(f"Overwriting existing piece at ({row},{col})={COORD_TO_ACF[(row,col)]}: {self.board[row][col]}")
            self.board[row][col] = RED
            logging.debug(f"Placed Red at ({row},{col})={COORD_TO_ACF[(row,col)]}")
        for row, col in white_squares:
            if (row + col) % 2 != 0:
                logging.error(f"Light square in COORD_TO_ACF for White: ({row},{col})={COORD_TO_ACF[(row,col)]}")
                continue
            if self.board[row][col] != EMPTY:
                logging.warning(f"Overwriting existing piece at ({row},{col})={COORD_TO_ACF[(row,col)]}: {self.board[row][col]}")
            self.board[row][col] = WHITE
            logging.debug(f"Placed White at ({row},{col})={COORD_TO_ACF[(row,col)]}")
        red_count = sum(row.count(RED) for row in self.board)
        white_count = sum(row.count(WHITE) for row in self.board)
        if red_count != 12 or white_count != 12:
            logging.error(f"Piece count mismatch: Red={red_count}, White={white_count}")
            # Log all occupied squares to diagnose missing pieces
            occupied = [(r, c, self.board[r][c], COORD_TO_ACF.get((r, c), '??')) for r in range(8) for c in range(8) if self.board[r][c] != EMPTY]
            logging.debug(f"Occupied squares: {occupied}")
        else:
            logging.info(f"Board setup complete: Red={red_count}, White={white_count}")
        logging.debug(f"Initial board: {self.board}")

    def setup_test_board(self):
        logging.debug("Setting up test board for endgame")
        self.board = [[EMPTY for _ in range(8)] for _ in range(8)]
        self.board[5][5] = RED  # Square 1
        self.board[5][7] = RED  # Square 2
        self.board[2][4] = WHITE  # Square 23
        self.board[2][6] = WHITE  # Square 24
        self.turn = RED
        logging.debug(f"Test board: {self.board}")
        logging.debug(f"Test board piece counts: Red={sum(row.count(RED) for row in self.board)}, White={sum(row.count(WHITE) for row in self.board)}")

    def move_piece(self, start, end):
        logging.debug(f"Moving piece from {start} to {end}, ACF: {COORD_TO_ACF.get(start, '??')}-{COORD_TO_ACF.get(end, '??')}")
        if start not in COORD_TO_ACF or end not in COORD_TO_ACF:
            logging.error(f"Invalid move coordinates: {start} -> {end}")
            return EMPTY, None, False, False
        start_row, start_col = start
        end_row, end_col = end
        piece = self.board[start_row][start_col]
        captured_piece = EMPTY
        captured_pos = None
        promotion = False
        is_jump = abs(start_row - end_row) == 2
        if is_jump:
            mid_row = (start_row + end_row) // 2
            mid_col = (start_col + end_col) // 2
            captured_piece = self.board[mid_row][mid_col]
            captured_pos = (mid_row, mid_col)
            if captured_piece == EMPTY or (piece.lower() == RED and captured_piece.lower() == RED) or (piece.lower() == WHITE and captured_piece.lower() == WHITE):
                logging.error(f"Invalid jump: no opponent piece at {captured_pos}")
                return EMPTY, None, False, False
            self.board[mid_row][mid_col] = EMPTY
        self.board[end_row][end_col] = piece
        self.board[start_row][start_col] = EMPTY
        if (piece == RED and end_row == 0) or (piece == WHITE and end_row == 7):
            self.board[end_row][end_col] = RED_KING if piece == RED else WHITE_KING
            promotion = True
        self.forced_jumps = []
        if is_jump:
            self.forced_jumps = self.get_jumps_for_piece(end, self.board[end_row][end_col])
        logging.debug(f"Move result: captured={captured_piece}, pos={captured_pos}, promotion={promotion}, is_jump={is_jump}, forced_jumps={self.forced_jumps}")
        return captured_piece, captured_pos, promotion, is_jump

    def get_jumps_for_piece(self, pos, piece):
        if pos not in COORD_TO_ACF:
            logging.warning(f"Invalid start position for jumps: {pos}")
            return []
        if (pos[0] + pos[1]) % 2 != 0:
            logging.error(f"Light square used for jumps: {pos}")
            return []
        jumps = []
        row, col = pos
        directions = [(-1,-1), (-1,1), (1,-1), (1,1)] if piece.isupper() else [(-1,-1), (-1,1)] if piece == RED else [(1,-1), (1,1)]
        opponent = [WHITE, WHITE_KING] if piece.lower() == RED else [RED, RED_KING]
        for dr, dc in directions:
            mid_row, mid_col = row + dr, col + dc
            end_row, end_col = row + 2*dr, col + 2*dc
            end_pos = (end_row, end_col)
            if 0 <= mid_row < 8 and 0 <= mid_col < 8 and 0 <= end_row < 8 and 0 <= end_col < 8:
                if end_pos in COORD_TO_ACF and self.board[mid_row][mid_col] in opponent and self.board[end_row][end_col] == EMPTY:
                    jumps.append((pos, end_pos))
                else:
                    logging.debug(f"Jump rejected: {pos} -> {end_pos}, mid={self.board[mid_row][mid_col] if 0 <= mid_row < 8 and 0 <= mid_col < 8 else 'out of bounds'}, end={self.board[end_row][end_col] if 0 <= end_row < 8 and 0 <= end_col < 8 else 'out of bounds'}")
        logging.debug(f"Jumps for {piece} at {pos}: {[(COORD_TO_ACF.get(s, '??') + '-' + COORD_TO_ACF.get(e, '??')) for s, e in jumps]}")
        return jumps

    def get_all_possible_moves(self, turn):
        moves = []
        jumps_exist = False
        valid_squares = [pos for pos in COORD_TO_ACF if self.board[pos[0]][pos[1]].lower() == turn]
        logging.debug(f"Valid squares for {turn}: {[(pos, COORD_TO_ACF.get(pos, '??')) for pos in valid_squares]}")
        for pos in valid_squares:
            row, col = pos
            if (row + col) % 2 != 0:
                logging.error(f"Light square detected in valid squares: {pos}, ACF={COORD_TO_ACF.get(pos, '??')}")
                continue
            piece = self.board[row][col]
            jumps = self.get_jumps_for_piece(pos, piece)
            if jumps:
                jumps_exist = True
                moves.extend(jumps)
            elif not self.forced_jumps:
                directions = [(-1,-1), (-1,1), (1,-1), (1,1)] if piece.isupper() else [(-1,-1), (-1,1)] if piece == RED else [(1,-1), (1,1)]
                for dr, dc in directions:
                    new_row, new_col = row + dr, col + dc
                    new_pos = (new_row, new_col)
                    if new_pos in COORD_TO_ACF and self.board[new_row][new_col] == EMPTY:
                        moves.append((pos, new_pos))
                    else:
                        logging.debug(f"Move rejected: {pos} -> {new_pos}, not in COORD_TO_ACF or not empty")
        moves = moves if not jumps_exist else [m for m in moves if abs(m[0][0] - m[1][0]) == 2]
        logging.debug(f"All possible moves for {turn}: {[(COORD_TO_ACF.get(s, '??') + '-' + COORD_TO_ACF.get(e, '??')) for s, e in moves]}")
        return moves
