# engine/checkers_game.py
import pygame
import logging
import threading
import queue
import copy
from .board import Board
from .constants import SQUARE_SIZE, RED, WHITE, BOARD_SIZE, ROWS, COLS, DEFAULT_AI_DEPTH, COORD_TO_ACF
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
        
        self.large_font = pygame.font.SysFont(None, 22) 
        self.font = pygame.font.SysFont(None, 24)
        self.number_font = pygame.font.SysFont(None, 18)
        self.dev_font = pygame.font.SysFont('monospace', 14)
        
        self.ai_move_queue = queue.Queue()
        self.ai_thread = None
        self.positional_score = 0.0
        self.ai_top_moves = []
        self.ai_depth = DEFAULT_AI_DEPTH
        
        self._create_buttons()
        self._update_valid_moves()

    def _create_buttons(self):
        """Creates all the UI buttons for the side panel."""
        self.buttons = []
        panel_x = BOARD_SIZE + 10
        button_width = self.screen.get_width() - BOARD_SIZE - 20
        button_height = 32 
        
        button_defs = [
            ("Reset Board", self.reset_game, 160),
            ("Undo Move", self.undo_move, 200),
            ("Flip Board", self.flip_board, 240),
            ("Board Nums: OFF", self.toggle_board_numbers, 280),
            ("Dev Mode: OFF", self.toggle_dev_mode, 320),
            (f"AI Depth: {self.ai_depth}", self.cycle_ai_depth, 360),
            ("Export to PDN", self.export_to_pdn, 400),
            ("Force AI Move", self.force_ai_move, self.screen.get_height() - 170)
        ]
        
        for text, callback, y_pos in button_defs:
            button = Button(
                text,
                (panel_x, y_pos),
                (button_width, button_height),
                callback
            )
            self.buttons.append(button)
        
        self.board_nums_button = self.buttons[3]
        self.dev_mode_button = self.buttons[4]
        self.ai_depth_button = self.buttons[5]

    def reset_game(self):
        self.board = Board()
        self.turn = self.board.turn
        self.done = False
        self.history = []
        self.ai_top_moves = []
        self._update_valid_moves()

    def undo_move(self):
        if not self.history:
            return
        self.board = self.history.pop()
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
        
    def cycle_ai_depth(self):
        """Cycles the AI search depth between 5 and 9."""
        self.ai_depth += 1
        if self.ai_depth > 9:
            self.ai_depth = 5
        self.ai_depth_button.text = f"AI Depth: {self.ai_depth}"
        logger.info(f"AI depth set to {self.ai_depth}")
        
    def export_to_pdn(self):
        logger.info("Export to PDN button clicked (not implemented).")

    def force_ai_move(self):
        if self.turn == self.ai_color:
            self.start_ai_turn()

    def start_ai_turn(self):
        self.ai_top_moves = []
        if self.ai_thread is None or not self.ai_thread.is_alive():
            logger.info(f"Starting AI calculation with depth {self.ai_depth}...")
            self.ai_thread = threading.Thread(target=self.run_ai_calculation, daemon=True)
            self.ai_thread.start()

    def run_ai_calculation(self):
        try:
            best_move, top_moves = get_ai_move_analysis(self.board, self.ai_depth, self.ai_color, evaluate_board)
            
            if best_move:
                self.positional_score = top_moves[0][0]
                self.ai_top_moves = top_moves
                self.ai_move_queue.put(best_move)
            else:
                self.ai_move_queue.put(None)

        except Exception as e:
            logger.error(f"AI calculation failed: {e}")
            self.ai_move_queue.put(None)
        finally:
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
                self._apply_move(start_pos, (row, col))
                return
            else:
                self.selected_piece = None
        
        if (row, col) in self.valid_moves:
            self.selected_piece = self.board.get_piece(row, col)
        else:
            self.selected_piece = None

    def _apply_move(self, start_pos, end_pos):
        self.history.append(copy.deepcopy(self.board))
        
        piece = self.board.get_piece(start_pos[0], start_pos[1])
        captured_piece = self.board.move(piece, end_pos[0], end_pos[1])

        if captured_piece:
            jumps = self.board._get_jumps_for_piece(end_pos[0], end_pos[1])
            if jumps:
                self.selected_piece = self.board.get_piece(end_pos[0], end_pos[1])
                self.valid_moves = {(end_pos[0], end_pos[1]): list(jumps.keys())}
                return

        self._change_turn()

    def _handle_click(self, pos):
        if self.turn != self.player_color or self.done:
            return
            
        if pos[0] < BOARD_SIZE:
            row, col = pos[1] // SQUARE_SIZE, pos[0] // SQUARE_SIZE
            
            if self.board_flipped:
                row, col = ROWS - 1 - row, COLS - 1 - col
                
            self._select(row, col)

    def draw_info_panel(self):
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - BOARD_SIZE
        
        pygame.draw.rect(self.screen, constants.COLOR_BG, (panel_x, 0, panel_width, self.screen.get_height()))
        
        turn_text = self.large_font.render(f"{constants.PLAYER_NAMES[self.turn]}'s Turn", True, constants.COLOR_TEXT)
        self.screen.blit(turn_text, (panel_x + 10, 20))
        
        red_men = self.board.red_left - self.board.red_kings
        white_men = self.board.white_left - self.board.white_kings
        
        red_text = self.font.render(f"Red: {red_men}+{self.board.red_kings}", True, RED)
        self.screen.blit(red_text, (panel_x + 10, 60))
        
        white_text = self.font.render(f"White: {white_men}+{self.board.white_kings}", True, WHITE)
        self.screen.blit(white_text, (panel_x + 10, 90))
        
        score_text = self.font.render(f"Score: {self.positional_score:.2f}", True, constants.COLOR_TEXT)
        self.screen.blit(score_text, (panel_x + 10, 120))
        
        for button in self.buttons:
            button.draw(self.screen)
            
    def draw_dev_panel(self):
        if not self.dev_mode:
            return
        
        panel_y = BOARD_SIZE
        panel_height = self.screen.get_height() - BOARD_SIZE
        
        pygame.draw.rect(self.screen, (10, 10, 30), (0, panel_y, self.screen.get_width(), panel_height))
        
        title_surf = self.font.render("--- Developer Panel: Top 5 Moves ---", True, WHITE)
        self.screen.blit(title_surf, (10, panel_y + 5))
        
        y_offset = 30
        for i, (score, move) in enumerate(self.ai_top_moves):
            start_pos, end_pos = move
            # Convert coordinates to standard notation (e.g., 11-15)
            start_sq = COORD_TO_ACF.get(start_pos, '?')
            end_sq = COORD_TO_ACF.get(end_pos, '?')
            
            text = f"{i+1}. Move: {start_sq}-{end_sq}    Score: {score:.2f}"
            text_surf = self.dev_font.render(text, True, (200, 200, 200))
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
                    row, col = move
                    draw_row, draw_col = (ROWS - 1 - row, COLS - 1 - col) if self.board_flipped else (row, col)
                    pygame.draw.circle(self.screen, (0, 255, 0),
                                       (draw_col * SQUARE_SIZE + SQUARE_SIZE // 2, draw_row * SQUARE_SIZE + SQUARE_SIZE // 2), 15)

        if self.done:
            winner = RED if self.turn == WHITE else WHITE
            end_text = self.large_font.render(f"{constants.PLAYER_NAMES[winner]} Wins!", True, (0, 255, 0), constants.COLOR_BG)
            text_rect = end_text.get_rect(center=(BOARD_SIZE / 2, self.screen.get_height() / 2))
            self.screen.blit(end_text, text_rect)

    def update(self):
        try:
            # The AI now returns the move tuple (start_pos, end_pos)
            move = self.ai_move_queue.get_nowait()
            if move:
                self._apply_move(move[0], move[1])
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
