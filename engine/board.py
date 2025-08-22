# engine/board.py
import pygame
from .constants import BLACK, RED, WHITE, SQUARE_SIZE, ROWS, COLS
from .piece import Piece

class Board:
    def __init__(self):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.create_board()

    def create_board(self):
        for row in range(ROWS):
            self.board.append([])
            for col in range(COLS):
                if col % 2 == ((row + 1) % 2):
                    if row < 3:
                        self.board[row].append(Piece(row, col, RED))
                    elif row > 4:
                        self.board[row].append(Piece(row, col, WHITE))
                    else:
                        self.board[row].append(0)
                else:
                    self.board[row].append(0)

    def draw_squares(self, screen):
        screen.fill(BLACK)
        for row in range(ROWS):
            for col in range(row % 2, COLS, 2):
                pygame.draw.rect(screen, (200, 200, 200), (row * SQUARE_SIZE, col * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)) # Lighter squares

    def get_piece(self, row, col):
        return self.board[row][col]
    
    def get_all_pieces(self, color):
        pieces = []
        for row in self.board:
            for piece in row:
                if piece != 0 and piece.color == color:
                    pieces.append(piece)
        return pieces

    def move(self, piece, row, col):
        self.board[piece.row][piece.col], self.board[row][col] = self.board[row][col], self.board[piece.row][piece.col]
        piece.move(row, col)
        
        captured_piece = None

        if row == ROWS - 1 or row == 0:
            piece.make_king()
            if piece.color == WHITE:
                self.white_kings += 1
            else:
                self.red_kings += 1

        # Check if it was a jump move to remove the captured piece
        if abs(piece.row - row) == 2 or abs(piece.col - col) == 2:
            middle_row = (piece.row + row) // 2
            middle_col = (piece.col + col) // 2
            captured = self.board[middle_row][middle_col]
            if captured != 0:
                captured_piece = captured
                self.board[middle_row][middle_col] = 0
                if captured.color == RED:
                    self.red_left -= 1
                else:
                    self.white_left -= 1
        
        return captured_piece


    def draw(self, screen):
        self.draw_squares(screen)
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    piece.draw(screen)

    def get_all_valid_moves_for_color(self, color):
        """
        Gets all valid moves for a given color, respecting the global forced jump rule.
        Returns a dictionary: { (start_row, start_col): [ (end_row, end_col), ... ], ... }
        """
        all_possible_moves = {}
        
        # First, find all possible jumps for ALL pieces of the given color
        jumps = {}
        for piece in self.get_all_pieces(color):
            # The keys of the returned dict are the destinations
            piece_jumps = self._get_jumps_for_piece(piece.row, piece.col)
            if piece_jumps:
                jumps[(piece.row, piece.col)] = list(piece_jumps.keys())
                
        # If any jump moves exist, they are the only valid moves
        if jumps:
            return jumps

        # If no jumps were found, find all possible slides
        slides = {}
        for piece in self.get_all_pieces(color):
            piece_slides = self._get_slides_for_piece(piece.row, piece.col)
            if piece_slides:
                slides[(piece.row, piece.col)] = list(piece_slides.keys())

        return slides

    def _get_slides_for_piece(self, row, col):
        """Calculates all valid slide moves for a single piece."""
        slides = {}
        piece = self.get_piece(row, col)
        
        # Directions: up for WHITE, down for RED
        up = -1
        down = 1

        if piece.color == WHITE or piece.king:
            slides.update(self._traverse_left(row + up, max(row - 2, -1), up, piece.color, col - 1, is_slide=True))
            slides.update(self._traverse_right(row + up, max(row - 2, -1), up, piece.color, col + 1, is_slide=True))
        if piece.color == RED or piece.king:
            slides.update(self._traverse_left(row + down, min(row + 2, ROWS), down, piece.color, col - 1, is_slide=True))
            slides.update(self._traverse_right(row + down, min(row + 2, ROWS), down, piece.color, col + 1, is_slide=True))

        return slides

    def _get_jumps_for_piece(self, row, col):
        """Calculates all valid jump moves for a single piece."""
        jumps = {}
        piece = self.get_piece(row, col)

        # Directions: up for WHITE, down for RED
        up = -1
        down = 1

        if piece.color == WHITE or piece.king:
            jumps.update(self._traverse_left(row + up, max(row-3, -1), up, piece.color, col-1))
            jumps.update(self._traverse_right(row + up, max(row-3, -1), up, piece.color, col+1))
        if piece.color == RED or piece.king:
            jumps.update(self._traverse_left(row + down, min(row+3, ROWS), down, piece.color, col-1))
            jumps.update(self._traverse_right(row + down, min(row+3, ROWS), down, piece.color, col+1))
        
        return jumps

    def _traverse_left(self, start, stop, step, color, left, skipped=[], is_slide=False):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if left < 0:
                break
            
            current = self.board[r][left]
            if current == 0:
                if is_slide: # If it's a slide, we can only move one empty space
                    moves[(r, left)] = []
                    break
                
                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, left)] = last + skipped
                else:
                    moves[(r, left)] = last
                
                if last:
                    if step == -1:
                        row = max(r-3, -1)
                    else:
                        row = min(r+3, ROWS)
                    moves.update(self._traverse_left(r+step, row, step, color, left-1,skipped=moves[(r,left)]))
                    moves.update(self._traverse_right(r+step, row, step, color, left+1,skipped=moves[(r,left)]))
                break
            elif current.color == color:
                break
            else:
                last = [current]

            left -= 1
        
        return moves

    def _traverse_right(self, start, stop, step, color, right, skipped=[], is_slide=False):
        moves = {}
        last = []
        for r in range(start, stop, step):
            if right >= COLS:
                break
            
            current = self.board[r][right]
            if current == 0:
                if is_slide: # If it's a slide, we can only move one empty space
                    moves[(r, right)] = []
                    break

                if skipped and not last:
                    break
                elif skipped:
                    moves[(r, right)] = last + skipped
                else:
                    moves[(r, right)] = last
                
                if last:
                    if step == -1:
                        row = max(r-3, -1)
                    else:
                        row = min(r+3, ROWS)
                    moves.update(self._traverse_left(r+step, row, step, color, right-1,skipped=moves[(r,right)]))
                    moves.update(self._traverse_right(r+step, row, step, color, right+1,skipped=moves[(r,right)]))
                break
            elif current.color == color:
                break
            else:
                last = [current]

            right += 1
        
        return moves
