# engine/checkers_game.py
import pygame
import logging
import threading
import queue
from .board import Board
from .constants import SQUARE_SIZE, RED, WHITE, BOARD_SIZE
import engine.constants as constants
from game_states import Button

# Set up logging
logger = logging.getLogger('gui')

class CheckersGame:
    def __init__(self, screen, player_color_str):
        self.screen = screen
        self.board = Board()
        
        self.player_color = WHITE if player_color_str == 'white' else RED
        self.ai_color = RED if self.player_color == WHITE else WHITE
        
        self.turn = RED # Red always starts
        self.selected_piece = None
        self.valid_moves = {}
        
        self.done = False
        self.next_state = None
        
        # --- Visual Toggles ---
        self.show_board_numbers = False
        self.dev_mode = False
        
        self.large_font = pygame.font.SysFont(None, 22) 
        self.font = pygame.font.SysFont(None, 24)
        
        self._create_buttons()
        self._update_valid_moves()

        # AI threading
        self.ai_move_queue = queue.Queue()
        self.ai_thread = None

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
            ("Export to PDN", self.export_to_pdn, 360),
            ("Force AI Move", self.force_ai_move, self.screen.get_height() - 50)
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

    # --- Button Callback Methods ---
    def reset_game(self):
        logger.info("Reset Game button clicked.")
        self.board.create_board()
        self.turn = RED # Red always starts
        self.done = False
        self._update_valid_moves()

    def undo_move(self):
        logger.info("Undo Move button clicked (not implemented).")

    def flip_board(self):
        logger.info("Flip Board button clicked (not implemented).")
        
    def toggle_board_numbers(self):
        self.show_board_numbers = not self.show_board_numbers
        self.board_nums_button.text = f"Board Nums: {'ON' if self.show_board_numbers else 'OFF'}"
        logger.info(f"Board numbers toggled {'ON' if self.show_board_numbers else 'OFF'}.")
        
    def toggle_dev_mode(self):
        self.dev_mode = not self.dev_mode
        self.dev_mode_button.text = f"Dev Mode: {'ON' if self.dev_mode else 'OFF'}"
        logger.info(f"Developer mode toggled {'ON' if self.dev_mode else 'OFF'}.")
        
    def export_to_pdn(self):
        logger.info("Export to PDN button clicked (not implemented).")

    def force_ai_move(self):
        logger.info("Force AI Move button clicked")
        if self.turn == self.ai_color:
            self.start_ai_turn()

    # --- AI Methods ---
    def start_ai_turn(self):
        logger.info("Starting AI turn.")
        if self.ai_thread is None or not self.ai_thread.is_alive():
            logger.info("Starting AI calculation in a new thread...")
            self.ai_thread = threading.Thread(target=self.run_ai_calculation, daemon=True)
            self.ai_thread.start()

    def run_ai_calculation(self):
        try:
            if self.valid_moves:
                all_moves = list(self.valid_moves.items())
                start_pos, end_positions = all_moves[0]
                end_pos = end_positions[0]
                move = (start_pos, end_pos)
                self.ai_move_queue.put(move)
            else:
                self.ai_move_queue.put(None)
        except Exception as e:
            logger.error(f"AI calculation failed: {e}")
            self.ai_move_queue.put(None)
        finally:
            logger.info("AI calculation completed.")

    # --- Core Game Logic Methods ---
    def _update_valid_moves(self):
        self.valid_moves = self.board.get_all_valid_moves_for_color(self.turn)
        if not self.valid_moves:
            self.done = True
            winner = RED if self.turn == WHITE else WHITE
            logger.info(f"Game over! {constants.PLAYER_NAMES[winner]} wins.")

    def _change_turn(self):
        self.selected_piece = None
        self.turn = RED if self.turn == WHITE else WHITE
        logger.info(f"Turn changed to {constants.PLAYER_NAMES[self.turn]}")
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
            logger.info(f"Piece selected at {(row, col)}. Found {len(self.valid_moves[(row, col)])} valid moves.")
        else:
            self.selected_piece = None

    def _apply_move(self, start_pos, end_pos):
        piece = self.board.get_piece(start_pos[0], start_pos[1])
        captured_piece = self.board.move(piece, end_pos[0], end_pos[1])

        if captured_piece:
            jumps = self.board._get_jumps_for_piece(end_pos[0], end_pos[1])
            if jumps:
                self.selected_piece = self.board.get_piece(end_pos[0], end_pos[1])
                self.valid_moves = {(end_pos[0], end_pos[1]): list(jumps.keys())}
                logger.info(f"Multi-jump available for piece at {end_pos}")
                return

        self._change_turn()

    # --- Event and Drawing Methods ---
    def _handle_click(self, pos):
        if self.turn != self.player_color or self.done:
            return
            
        if pos[0] < BOARD_SIZE:
            row, col = pos[1] // SQUARE_SIZE, pos[0] // SQUARE_SIZE
            self._select(row, col)

    def draw_info_panel(self):
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - BOARD_SIZE
        
        pygame.draw.rect(self.screen, constants.COLOR_BG, (panel_x, 0, panel_width, self.screen.get_height()))
        
        turn_text = self.large_font.render(f"{constants.PLAYER_NAMES[self.turn]}'s Turn", True, constants.COLOR_TEXT)
        self.screen.blit(turn_text, (panel_x + 10, 20))
        
        red_captured = 12 - self.board.white_left
        white_captured = 12 - self.board.red_left
        
        red_text = self.font.render(f"Red Captured: {red_captured}", True, RED)
        self.screen.blit(red_text, (panel_x + 10, 80))
        
        white_text = self.font.render(f"White Captured: {white_captured}", True, WHITE)
        self.screen.blit(white_text, (panel_x + 10, 120))
        
        for button in self.buttons:
            button.draw(self.screen)

    def draw(self):
        self.board.draw(self.screen, self.show_board_numbers)
        self.draw_info_panel()

        if self.selected_piece:
            start_pos = (self.selected_piece.row, self.selected_piece.col)
            if start_pos in self.valid_moves:
                for move in self.valid_moves[start_pos]:
                    row, col = move
                    pygame.draw.circle(self.screen, (0, 255, 0),
                                       (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2), 15)

        if self.done:
            winner = RED if self.turn == WHITE else WHITE
            end_text = self.large_font.render(f"{constants.PLAYER_NAMES[winner]} Wins!", True, (0, 255, 0), constants.COLOR_BG)
            text_rect = end_text.get_rect(center=(BOARD_SIZE / 2, self.screen.get_height() / 2))
            self.screen.blit(end_text, text_rect)

    def update(self):
        try:
            start_pos, end_pos = self.ai_move_queue.get_nowait()
            if start_pos and end_pos:
                self._apply_move(start_pos, end_pos)
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
                    self.current_state.handle_events(events)
