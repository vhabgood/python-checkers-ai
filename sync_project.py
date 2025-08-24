import os

# This script will overwrite your project files with the latest correct versions.

# --- File Contents ---

MAIN_PY_CONTENT = """
# main.py
import pygame
import logging
import datetime
import argparse
import sys
import os

from engine.checkers_game import CheckersGame
from game_states import LoadingScreen, PlayerSelectionScreen
from engine.constants import FPS, WIDTH, HEIGHT

def configure_logging(args):
    log_level = logging.INFO
    if args.debug_gui or args.debug_board:
        log_level = logging.DEBUG
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_filename = os.path.join(log_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_checkers_debug.log")
    
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            pathname = record.pathname
            if pathname.startswith(os.getcwd()):
                record.pathname = os.path.relpath(pathname, os.getcwd())
            return super().format(record)

    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(CustomFormatter('%(asctime)s - %(pathname)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s'))
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(CustomFormatter('%(name)s - %(levelname)s - %(message)s'))
    logging.basicConfig(level=log_level, handlers=[file_handler, console_handler])
    logging.getLogger('gui').setLevel(logging.INFO if not args.debug_gui else logging.DEBUG)
    logging.getLogger('board').setLevel(logging.INFO if not args.debug_board else logging.DEBUG)

class StateManager:
    def __init__(self, screen):
        self.screen = screen
        self.states = {
            "loading": LoadingScreen(self.screen),
            "player_selection": PlayerSelectionScreen(self.screen),
            "game": None
        }
        self.current_state = self.states["loading"]
        self.running = True

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            events = pygame.event.get()
            if self.current_state.done:
                next_state_name = self.current_state.next_state
                if next_state_name is None:
                    self.current_state.draw()
                    pygame.display.flip()
                    pygame.time.wait(3000)
                    self.running = False
                    continue
                if next_state_name == "game":
                    player_choice = self.current_state.player_choice
                    self.states["game"] = CheckersGame(self.screen, player_choice)
                self.current_state = self.states[next_state_name]
            
            if self.current_state is not None:
                self.current_state.handle_events(events)
                self.current_state.update()
                self.current_state.draw()
            
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
            
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A checkers game with an AI engine.")
    parser.add_argument("--debug-gui", action="store_true", help="Enable debug logging for GUI.")
    parser.add_argument("--debug-board", action="store_true", help="Enable debug logging for board.")
    args = parser.parse_args()
    configure_logging(args)
    pygame.init()
    window_size = (WIDTH, HEIGHT)
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Checkers")
    game_manager = StateManager(screen)
    game_manager.run()
"""

GAME_STATES_PY_CONTENT = """
# game_states.py
import pygame
import logging
import time
from engine.constants import (
    COLOR_BG, COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_TEXT,
    RED, WHITE, PLAYER_NAMES
)

logger = logging.getLogger('gui')

class Button:
    def __init__(self, text, pos, size, callback):
        self.text = text
        self.pos = pos
        self.size = size
        self.callback = callback
        self.rect = pygame.Rect(pos, size)
        self.font = pygame.font.SysFont(None, 18) 
        self.hovered = False

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos)
        button_color = COLOR_BUTTON_HOVER if self.hovered else COLOR_BUTTON
        pygame.draw.rect(screen, button_color, self.rect)
        text_surf = self.font.render(self.text, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class BaseState:
    def __init__(self, screen):
        self.screen = screen
        self.done = False
        self.next_state = None
        self.font = pygame.font.SysFont('Arial', 24)

    def handle_events(self, events):
        raise NotImplementedError
    def update(self):
        raise NotImplementedError
    def draw(self):
        raise NotImplementedError

class LoadingScreen(BaseState):
    def __init__(self, screen):
        super().__init__(screen)
        self.next_state = "player_selection"
        self.loading_status = ["Loading databases...", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"]
        self.current_status_index = 0
        self.last_update_time = time.time()
        logger.info("LoadingScreen initialized.")

    def handle_events(self, events):
        pass

    def update(self):
        current_time = time.time()
        if current_time - self.last_update_time > 0.5:
            self.current_status_index += 1
            if self.current_status_index >= len(self.loading_status):
                self.done = True
                logger.info("Loading complete. Transitioning to player selection.")
            self.last_update_time = current_time

    def draw(self):
        self.screen.fill(COLOR_BG)
        status_text = self.font.render(self.loading_status[min(self.current_status_index, len(self.loading_status) - 1)], True, COLOR_TEXT)
        status_rect = status_text.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2))
        self.screen.blit(status_text, status_rect)
        
class PlayerSelectionScreen(BaseState):
    def __init__(self, screen):
        super().__init__(screen)
        self.next_state = "game"
        self.player_choice = None
        self.buttons = [
            {'text': 'Red', 'rect': pygame.Rect(100, 200, 100, 50), 'player': RED},
            {'text': 'White', 'rect': pygame.Rect(400, 200, 100, 50), 'player': WHITE}
        ]
        logger.info("PlayerSelectionScreen initialized.")

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                for button in self.buttons:
                    if button['rect'].collidepoint(mouse_pos):
                        player_color_name = PLAYER_NAMES.get(button['player'])
                        self.player_choice = player_color_name.lower()
                        self.done = True
                        logger.info(f"Player selected {player_color_name}.")

    def update(self):
        pass

    def draw(self):
        self.screen.fill(COLOR_BG)
        title_text = self.font.render("Choose Your Side", True, COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.screen.get_width() / 2, 100))
        self.screen.blit(title_text, title_rect)
        for button in self.buttons:
            pygame.draw.rect(self.screen, COLOR_BUTTON, button['rect'])
            text_surf = self.font.render(button['text'], True, COLOR_TEXT)
            text_rect = text_surf.get_rect(center=button['rect'].center)
            self.screen.blit(text_surf, text_rect)
"""

CONSTANTS_PY_CONTENT = """
# engine/constants.py
import pygame

FPS = 60
DEFAULT_AI_DEPTH = 5
BOARD_SIZE = 480
INFO_WIDTH = 220
WIDTH, HEIGHT = BOARD_SIZE + INFO_WIDTH, BOARD_SIZE + 120
ROWS, COLS = 8, 8
SQUARE_SIZE = BOARD_SIZE // COLS
RED = (255, 0, 0)
WHITE = (255, 255, 255)
PLAYER_NAMES = {RED: 'Red', WHITE: 'White'}
COLOR_CROWN = (255, 215, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_BG = (20, 20, 20)
COLOR_BUTTON = (100, 100, 100)
COLOR_BUTTON_HOVER = (150, 150, 150)
BLACK = (0, 0, 0)
GREY = (128, 128, 128)
COORD_TO_ACF = {}
ACF_TO_COORD = {}
square_num = 1
for r in range(ROWS):
    for c in range(COLS):
        if (r + c) % 2 == 1:
            COORD_TO_ACF[(r, c)] = square_num
            ACF_TO_COORD[square_num] = (r, c)
            square_num += 1
"""

PIECE_PY_CONTENT = """
# engine/piece.py
import pygame
import math
from .constants import SQUARE_SIZE, GREY, COLOR_CROWN, BOARD_SIZE

class Piece:
    PADDING = 15
    OUTLINE = 2
    def __init__(self, row, col, color):
        self.row = row
        self.col = col
        self.color = color
        self.king = False
        self.x = 0
        self.y = 0
        self.calc_pos()

    def calc_pos(self):
        self.x = SQUARE_SIZE * self.col + SQUARE_SIZE // 2
        self.y = SQUARE_SIZE * self.row + SQUARE_SIZE // 2

    def make_king(self):
        self.king = True

    def draw(self, screen, flipped=False):
        radius = SQUARE_SIZE // 2 - self.PADDING
        draw_x, draw_y = self.x, self.y
        if flipped:
            draw_x = BOARD_SIZE - self.x
            draw_y = BOARD_SIZE - self.y
        pygame.draw.circle(screen, GREY, (draw_x, draw_y), radius + self.OUTLINE)
        pygame.draw.circle(screen, self.color, (draw_x, draw_y), radius)
        if self.king:
            self._draw_star(screen, draw_x, draw_y)

    def _draw_star(self, screen, x, y):
        star_radius = self.PADDING
        num_points = 5
        points = []
        for i in range(num_points * 2):
            r = star_radius if i % 2 == 0 else star_radius / 2.5
            angle = math.pi / num_points * i - math.pi / 2
            point_x = x + r * math.cos(angle)
            point_y = y + r * math.sin(angle)
            points.append((point_x, point_y))
        pygame.draw.polygon(screen, COLOR_CROWN, points)

    def move(self, row, col):
        self.row = row
        self.col = col
        self.calc_pos()

    def __repr__(self):
        return str(self.color)
"""

BOARD_PY_CONTENT = """
# engine/board.py
import pygame
import logging
from .constants import BLACK, RED, WHITE, SQUARE_SIZE, COLS, ROWS
from .piece import Piece

logger = logging.getLogger('board')

class Board:
    def __init__(self):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
        self.turn = RED
        self.create_board()
        logger.debug("Board initialized.")

    def create_board(self):
        self.board = []
        self.red_left = self.white_left = 12
        self.red_kings = self.white_kings = 0
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
        captured_piece = None
        if abs(piece.row - row) == 2:
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
        piece.move(row, col)
        if row == 0 or row == ROWS - 1:
            if not piece.king:
                piece.make_king()
                if piece.color == WHITE:
                    self.white_kings += 1
                else:
                    self.red_kings += 1
        return captured_piece

    def draw(self, screen, number_font, show_numbers=False, flipped=False):
        self.draw_squares(screen, number_font, show_numbers, flipped)
        for row in range(ROWS):
            for col in range(COLS):
                piece = self.board[row][col]
                if piece != 0:
                    piece.draw(screen, flipped)

    def draw_squares(self, screen, number_font, show_numbers=False, flipped=False):
        screen.fill(BLACK)
        for row in range(ROWS):
            for col in range(COLS):
                square_num = (row * 4) + (col // 2) + 1
                draw_row, draw_col = (ROWS - 1 - row, COLS - 1 - col) if flipped else (row, col)
                if (row + col) % 2 == 1:
                    pygame.draw.rect(screen, (181, 136, 99), (draw_col * SQUARE_SIZE, draw_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
                    if show_numbers:
                        num_surf = number_font.render(str(square_num), True, (255, 255, 255))
                        screen.blit(num_surf, (draw_col * SQUARE_SIZE + 2, draw_row * SQUARE_SIZE + 2))
                else:
                    pygame.draw.rect(screen, (227, 206, 187), (draw_col * SQUARE_SIZE, draw_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

    def get_all_valid_moves_for_color(self, color):
        moves = {}
        for piece in self.get_all_pieces(color):
            jumps = self._get_jumps_for_piece(piece.row, piece.col)
            if jumps:
                moves[(piece.row, piece.col)] = list(jumps.keys())
        if moves:
            return moves
        for piece in self.get_all_pieces(color):
            slides = self._get_slides_for_piece(piece.row, piece.col)
            if slides:
                moves[(piece.row, piece.col)] = list(slides.keys())
        return moves
        
    def _get_slides_for_piece(self, row, col):
        moves = {}
        piece = self.get_piece(row, col)
        if piece.color == WHITE or piece.king:
            for r, c in [(row - 1, col - 1), (row - 1, col + 1)]:
                if 0 <= r < ROWS and 0 <= c < COLS and self.board[r][c] == 0:
                    moves[(r, c)] = []
        if piece.color == RED or piece.king:
            for r, c in [(row + 1, col - 1), (row + 1, col + 1)]:
                if 0 <= r < ROWS and 0 <= c < COLS and self.board[r][c] == 0:
                    moves[(r, c)] = []
        return moves

    def _get_jumps_for_piece(self, row, col):
        moves = {}
        piece = self.get_piece(row, col)
        if piece.color == WHITE or piece.king:
            for (r_mid, c_mid), (r_end, c_end) in [((row - 1, col - 1), (row - 2, col - 2)), ((row - 1, col + 1), (row - 2, col + 2))]:
                if 0 <= r_end < ROWS and 0 <= c_end < COLS:
                    mid_piece = self.board[r_mid][c_mid]
                    end_piece = self.board[r_end][c_end]
                    if end_piece == 0 and mid_piece != 0 and mid_piece.color != piece.color:
                        moves[(r_end, c_end)] = [mid_piece]
        if piece.color == RED or piece.king:
            for (r_mid, c_mid), (r_end, c_end) in [((row + 1, col - 1), (row + 2, col - 2)), ((row + 1, col + 1), (row + 2, col + 2))]:
                if 0 <= r_end < ROWS and 0 <= c_end < COLS:
                    mid_piece = self.board[r_mid][c_mid]
                    end_piece = self.board[r_end][c_end]
                    if end_piece == 0 and mid_piece != 0 and mid_piece.color != piece.color:
                        moves[(r_end, c_end)] = [mid_piece]
        return moves
"""

SEARCH_PY_CONTENT = """
# engine/search.py
from .constants import RED, WHITE
import copy

def get_ai_move_analysis(board, depth, ai_color, evaluate_func):
    is_maximizing = ai_color == WHITE
    all_scored_moves = []
    for move_path, move_board in get_all_moves(board, ai_color):
        score, subsequent_path = minimax(move_board, depth - 1, float('-inf'), float('inf'), not is_maximizing, evaluate_func)
        full_path = move_path + subsequent_path
        all_scored_moves.append((score, full_path))
    if not all_scored_moves:
        return None, []
    all_scored_moves.sort(key=lambda x: x[0], reverse=is_maximizing)
    best_path = all_scored_moves[0][1]
    top_5_paths = all_scored_moves[:5]
    return best_path, top_5_paths

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_func):
    if depth == 0 or not board.get_all_valid_moves_for_color(board.turn):
        return evaluate_func(board), []
    best_path = []
    if maximizing_player:
        max_eval = float('-inf')
        for path, move_board in get_all_moves(board, WHITE):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, False, evaluate_func)
            if evaluation > max_eval:
                max_eval = evaluation
                best_path = path + subsequent_path
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval, best_path
    else:
        min_eval = float('inf')
        for path, move_board in get_all_moves(board, RED):
            evaluation, subsequent_path = minimax(move_board, depth - 1, alpha, beta, True, evaluate_func)
            if evaluation < min_eval:
                min_eval = evaluation
                best_path = path + subsequent_path
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_path

def get_all_moves(board, color):
    for start_pos, end_positions in board.get_all_valid_moves_for_color(color).items():
        for end_pos in end_positions:
            temp_board = copy.deepcopy(board)
            piece = temp_board.get_piece(start_pos[0], start_pos[1])
            temp_board.move(piece, end_pos[0], end_pos[1])
            is_jump = abs(start_pos[0] - end_pos[0]) > 1
            if is_jump:
                yield from _get_jump_sequences(temp_board, [start_pos, end_pos])
            else:
                temp_board.turn = RED if color == WHITE else WHITE
                yield [start_pos, end_pos], temp_board

def _get_jump_sequences(board, path):
    current_pos = path[-1]
    more_jumps = board._get_jumps_for_piece(current_pos[0], current_pos[1])
    if not more_jumps:
        yield path, board
        return
    for next_pos in more_jumps:
        temp_board = copy.deepcopy(board)
        temp_piece = temp_board.get_piece(current_pos[0], current_pos[1])
        temp_board.move(temp_piece, next_pos[0], next_pos[1])
        new_path = path + [next_pos]
        yield from _get_jump_sequences(temp_board, new_path)
"""

EVALUATION_PY_CONTENT = """
# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS, ACF_TO_COORD

logger = logging.getLogger('board')

def evaluate_board(board):
    white_material = (board.white_left - board.white_kings) * 1.0 + board.white_kings * 1.5
    red_material = (board.red_left - board.red_kings) * 1.0 + board.red_kings * 1.5
    material_score = white_material - red_material
    
    white_moves = board.get_all_valid_moves_for_color(WHITE)
    red_moves = board.get_all_valid_moves_for_color(RED)
    mobility_score = 0.1 * (len(white_moves) - len(red_moves))
    
    white_jumps = sum(1 for moves in white_moves.values() if abs(list(moves.keys())[0][0] - list(white_moves.keys())[0][0]) > 1)
    red_jumps = sum(1 for moves in red_moves.values() if abs(list(moves.keys())[0][0] - list(red_moves.keys())[0][0]) > 1)
    jump_score = 0.5 * (white_jumps - red_jumps)

    final_score = (material_score * 100) + mobility_score + jump_score
    
    return final_score
"""

CHECKERS_GAME_PY_CONTENT = """
# engine/checkers_game.py
import pygame
import logging
import threading
import queue
import copy
import time
from .board import Board
from .constants import SQUARE_SIZE, RED, WHITE, BOARD_SIZE, ROWS, COLS, DEFAULT_AI_DEPTH, COORD_TO_ACF, GREY
import engine.constants as constants
from game_states import Button
from engine.search import get_ai_move_analysis
from engine.evaluation import evaluate_board

logger = logging.getLogger('gui')

class CheckersGame:
    def __init__(self, screen, player_color_str):
        self.screen = screen
        self.board = Board()
        self.player_color = WHITE if player_color_str == 'white' else RED
        self.ai_color = RED if self.player_color == WHITE else WHITE
        self.turn = self.board.turn
        self.selected_piece = None
        self.valid_moves = {}
        self.done = False
        self.next_state = None
        self.show_board_numbers = False
        self.dev_mode = False
        self.board_flipped = False
        self.history = []
        self.move_history = []
        self.large_font = pygame.font.SysFont(None, 22) 
        self.font = pygame.font.SysFont(None, 24)
        self.small_font = pygame.font.SysFont(None, 18)
        self.dev_font = pygame.font.SysFont('monospace', 16)
        self.number_font = pygame.font.SysFont(None, 18)
        self.ai_move_queue = queue.Queue()
        self.ai_analysis_queue = queue.Queue()
        self.ai_thread = None
        self.ai_is_thinking = False
        self.positional_score = 0.0
        self.ai_top_moves = []
        self.ai_depth = DEFAULT_AI_DEPTH
        self._create_buttons()
        self._update_valid_moves()

    def _create_buttons(self):
        self.buttons = []
        panel_x = BOARD_SIZE + 10
        button_width = self.screen.get_width() - BOARD_SIZE - 20
        button_height = 32 
        y_start = self.screen.get_height() - 50
        button_defs = [
            ("Export to PDN", self.export_to_pdn, y_start),
            ("Dev Mode: OFF", self.toggle_dev_mode, y_start - 40),
            ("Board Nums: OFF", self.toggle_board_numbers, y_start - 80),
            ("Flip Board", self.flip_board, y_start - 120),
            ("Undo Move", self.undo_move, y_start - 160),
            ("Reset Board", self.reset_game, y_start - 200),
            ("Force AI Move", self.force_ai_move, y_start - 240)
        ]
        for text, callback, y_pos in button_defs:
            button = Button(text, (panel_x, y_pos), (button_width, button_height), callback)
            self.buttons.append(button)
        depth_btn_y = y_start - 280
        self.buttons.append(Button("-", (panel_x, depth_btn_y), (30, 30), self.decrease_ai_depth))
        self.buttons.append(Button("+", (panel_x + button_width - 30, depth_btn_y), (30, 30), self.increase_ai_depth))
        for btn in self.buttons:
            if "Board Nums" in btn.text: self.board_nums_button = btn
            elif "Dev Mode" in btn.text: self.dev_mode_button = btn

    def reset_game(self):
        self.board = Board()
        self.turn = self.board.turn
        self.done = False
        self.history = []
        self.move_history = []
        self.ai_top_moves = []
        self._update_valid_moves()

    def undo_move(self):
        if not self.history: return
        self.board = self.history.pop()
        if self.move_history: self.move_history.pop()
        self.turn = self.board.turn
        self.ai_top_moves = []
        self._update_valid_moves()

    def flip_board(self):
        self.board_flipped = not self.board_flipped
        
    def toggle_board_numbers(self):
        self.show_board_numbers = not self.show_board_numbers
        self.board_nums_button.text = f"Board Nums: {'ON' if self.show_board_numbers else 'OFF'}"
        
    def toggle_dev_mode(self):
        self.dev_mode = not self.dev_mode
        self.dev_mode_button.text = f"Dev Mode: {'ON' if self.dev_mode else 'OFF'}"
        
    def increase_ai_depth(self):
        if self.ai_depth < 9: self.ai_depth += 1
        logger.info(f"AI depth set to {self.ai_depth}")
        
    def decrease_ai_depth(self):
        if self.ai_depth > 5: self.ai_depth -= 1
        logger.info(f"AI depth set to {self.ai_depth}")
        
    def export_to_pdn(self):
        logger.info("Export to PDN button clicked (not implemented).")

    def force_ai_move(self):
        if self.turn == self.ai_color:
            self.start_ai_turn()

    def start_ai_turn(self):
        if self.ai_thread and self.ai_thread.is_alive(): return
        self.ai_is_thinking = True
        self.ai_top_moves = []
        logger.info(f"Starting AI calculation with depth {self.ai_depth}...")
        self.ai_thread = threading.Thread(target=self.run_ai_calculation, daemon=True)
        self.ai_thread.start()

    def run_ai_calculation(self):
        try:
            best_move_path, top_moves = get_ai_move_analysis(self.board, self.ai_depth, self.ai_color, evaluate_board)
            if best_move_path:
                self.positional_score = top_moves[0][0]
                self.ai_top_moves = top_moves
                self.ai_move_queue.put(best_move_path)
            else:
                self.ai_move_queue.put(None)
        except Exception as e:
            logger.error(f"AI calculation failed: {e}")
            self.ai_move_queue.put(None)
        finally:
            self.ai_is_thinking = False
            logger.info(f"AI calculation completed. Best score: {self.positional_score:.2f}")

    def _update_valid_moves(self):
        self.valid_moves = self.board.get_all_valid_moves_for_color(self.turn)
        if not self.valid_moves:
            self.done = True
            winner = RED if self.turn == WHITE else WHITE
            logger.info(f"Game over! {constants.PLAYER_NAMES[winner]} wins.")

    def _change_turn(self):
        self.selected_piece = None
        self.turn = RED if self.turn == WHITE else WHITE
        self.board.turn = self.turn
        self._update_valid_moves()

    def _select(self, row, col):
        if self.selected_piece:
            start_pos = (self.selected_piece.row, self.selected_piece.col)
            if start_pos in self.valid_moves and (row, col) in self.valid_moves[start_pos]:
                self._apply_move_sequence([start_pos, (row, col)])
            else:
                self.selected_piece = None
        elif (row, col) in self.valid_moves:
            self.selected_piece = self.board.get_piece(row, col)
        else:
            self.selected_piece = None

    def _apply_move_sequence(self, path):
        self.history.append(copy.deepcopy(self.board))
        self.move_history.append(path)
        for i in range(len(path) - 1):
            start_pos, end_pos = path[i], path[i+1]
            piece = self.board.get_piece(start_pos[0], start_pos[1])
            if piece != 0:
                self.board.move(piece, end_pos[0], end_pos[1])
                self.draw()
                pygame.display.flip()
                time.sleep(0.2)
        self._change_turn()

    def _handle_click(self, pos):
        if self.turn != self.player_color or self.done: return
        if pos[0] < BOARD_SIZE:
            row, col = pos[1] // SQUARE_SIZE, pos[0] // SQUARE_SIZE
            if self.board_flipped: row, col = ROWS - 1 - row, COLS - 1 - col
            self._select(row, col)

    def draw_move_history(self, start_y):
        panel_x = BOARD_SIZE + 10
        y_offset = start_y
        history_font = pygame.font.SysFont('monospace', 14)
        title_surf = self.large_font.render("Move History", True, WHITE)
        self.screen.blit(title_surf, (panel_x, y_offset))
        y_offset += 30
        header = history_font.render("Red     White", True, WHITE)
        self.screen.blit(header, (panel_x, y_offset))
        y_offset += 20
        start_index = max(0, len(self.move_history) - 10)
        if start_index % 2 != 0: start_index -=1
        for i in range(start_index, len(self.move_history), 2):
            move_num = (i // 2) + 1
            red_path = self.move_history[i]
            red_move_str = "x".join(str(COORD_TO_ACF.get(pos, '?')) for pos in red_path)
            white_move_str = ""
            if i + 1 < len(self.move_history):
                white_path = self.move_history[i+1]
                white_move_str = "x".join(str(COORD_TO_ACF.get(pos, '?')) for pos in white_path)
            line = f"{move_num}. {red_move_str:<8} {white_move_str}"
            line_surf = history_font.render(line, True, WHITE)
            self.screen.blit(line_surf, (panel_x, y_offset))
            y_offset += 15

    def draw_info_panel(self):
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - BOARD_SIZE
        pygame.draw.rect(self.screen, constants.COLOR_BG, (panel_x, 0, panel_width, self.screen.get_height()))
        turn_text = self.large_font.render(f"{constants.PLAYER_NAMES[self.turn]}'s Turn", True, constants.COLOR_TEXT)
        self.screen.blit(turn_text, (panel_x + 10, 20))
        if self.ai_is_thinking:
            thinking_text = self.font.render("AI is Thinking...", True, (255, 255, 0))
            self.screen.blit(thinking_text, (panel_x + 10, 45))
        self.draw_move_history(start_y=80)
        depth_label_text = self.small_font.render(f"AI Depth: {self.ai_depth}", True, WHITE)
        text_rect = depth_label_text.get_rect(center=(panel_x + panel_width / 2, self.screen.get_height() - 315))
        self.screen.blit(depth_label_text, text_rect)
        for button in self.buttons:
            button.draw(self.screen)
            
    def draw_dev_panel(self):
        if not self.dev_mode: return
        panel_y = BOARD_SIZE
        panel_height = self.screen.get_height() - BOARD_SIZE
        pygame.draw.rect(self.screen, (10, 10, 30), (0, panel_y, BOARD_SIZE, panel_height))
        title_surf = self.font.render("--- AI Analysis ---", True, WHITE)
        self.screen.blit(title_surf, (10, panel_y + 5))
        y_offset = 30
        for i, (score, path) in enumerate(self.ai_top_moves):
            move_str = "x".join(str(COORD_TO_ACF.get(pos, '?')) for pos in path)
            line = f"{i+1}. {move_str:<25} Score: {score:.2f}"
            text_surf = self.dev_font.render(line, True, (200, 200, 200))
            self.screen.blit(text_surf, (20, panel_y + y_offset))
            y_offset += 15

    def draw(self):
        self.board.draw(self.screen, self.number_font, self.show_board_numbers, self.board_flipped)
        self.draw_info_panel()
        self.draw_dev_panel()
        if self.selected_piece:
            start_pos = (self.selected_piece.row, self.selected_piece.col)
            if start_pos in self.valid_moves:
                for move in self.valid_moves[start_pos]:
                    draw_row, draw_col = (ROWS - 1 - move[0], COLS - 1 - move[1]) if self.board_flipped else (move[0], move[1])
                    pygame.draw.circle(self.screen, (0, 255, 0), (draw_col * SQUARE_SIZE + SQUARE_SIZE // 2, draw_row * SQUARE_SIZE + SQUARE_SIZE // 2), 15)
        if self.done:
            winner = RED if self.turn == WHITE else WHITE
            end_text = self.large_font.render(f"{constants.PLAYER_NAMES[winner]} Wins!", True, (0, 255, 0), constants.COLOR_BG)
            text_rect = end_text.get_rect(center=(BOARD_SIZE / 2, self.screen.get_height() / 2))
            self.screen.blit(end_text, text_rect)

    def update(self):
        try:
            best_move_path = self.ai_move_queue.get_nowait()
            if best_move_path:
                self._apply_move_sequence(best_move_path)
        except queue.Empty:
            pass

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                for button in self.buttons:
                    if button.is_clicked(event.pos):
                        button.callback()
                        break 
                else: 
                    self._handle_click(event.pos)
"""

# --- Script Logic ---

FILES_TO_WRITE = {
    "main.py": MAIN_PY_CONTENT,
    "game_states.py": GAME_STATES_PY_CONTENT,
    os.path.join('engine', 'constants.py'): CONSTANTS_PY_CONTENT,
    os.path.join('engine', 'piece.py'): PIECE_PY_CONTENT,
    os.path.join('engine', 'board.py'): BOARD_PY_CONTENT,
    os.path.join('engine', 'search.py'): SEARCH_PY_CONTENT,
    os.path.join('engine', 'evaluation.py'): EVALUATION_PY_CONTENT,
    os.path.join('engine', 'checkers_game.py'): CHECKERS_GAME_PY_CONTENT
}

def sync_files():
    """Overwrites local files with the correct, synchronized versions."""
    try:
        for file_path, content in FILES_TO_WRITE.items():
            print(f"Writing {file_path}...")
            dir_name = os.path.dirname(file_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name)
            
            with open(file_path, 'w') as f:
                f.write(content.strip())
        
        print("\nAll files have been synchronized successfully.")
        print("You can now run the game with 'python3 -m main'.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check your file permissions.")

if __name__ == "__main__":
    sync_files()
