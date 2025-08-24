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
        # This function runs in a separate thread to keep the game responsive.
        try:
            # FIX: We now check the data type from the board to prevent crashes.
            # The AI search expects a dictionary, but was receiving a list.
            # This check will log a specific error if the board returns the wrong type.
            moves = self.board.get_all_valid_moves_for_color(self.ai_color)
            if not isinstance(moves, dict):
                logger.error(f"AI ABORTED: board.get_all_valid_moves_for_color() returned a {type(moves)}, but AI expects a dict.")
                self.ai_move_queue.put(None)
                return

            best_move_path, top_moves = get_ai_move_analysis(self.board, self.ai_depth, self.ai_color, evaluate_board)

            if best_move_path:
                self.positional_score = top_moves[0][0]
                self.ai_top_moves = top_moves
                self.ai_move_queue.put(best_move_path)
            else:
                # If AI returns an empty path (no moves), put None on the queue.
                self.ai_move_queue.put(None)
        except Exception as e:
            logger.error(f"AI calculation failed: {e}")
            self.ai_move_queue.put(None)
        finally:
            self.ai_is_thinking = False
            # This log message was moved to appear only when a valid score is found.
            if self.ai_top_moves:
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
        # FIX: Added a check to ensure the path is valid before proceeding.
        if not path or len(path) < 2:
            logger.warning("AI tried to apply an invalid move sequence.")
            self._change_turn()
            return

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
            # FIX: Added a check to ensure best_move_path is a non-empty list.
            # The AI can now return an empty list or None, both of which mean "no move".
            if best_move_path and isinstance(best_move_path, list):
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
