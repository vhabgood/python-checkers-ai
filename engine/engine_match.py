# engine/engine_match.py
import pygame
import logging
import threading
import queue
import copy
from .board import Board
from .constants import RED, WHITE, BOARD_SIZE
from game_states import Button
from engine.search import get_ai_move_analysis
# Import both evaluation functions for the match
from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental

logger = logging.getLogger('engine_match')

class EngineMatchGame:
    """
    A game state that runs a match between two AI engines, each with its own
    evaluation function, to test improvements.
    """
    def __init__(self, screen, status_queue, args):
        self.screen = screen
        self.args = args
        self.db_conn = None # Note: Reuses the db_conn logic from CheckersGame
        
        # This class is very similar to CheckersGame. In the future, they could
        # inherit from a common BaseGame class to reduce code duplication.
        
        # --- Engine Configuration ---
        self.engine_red = {'name': 'Engine V1 (Stable)', 'eval_func': evaluate_board_v1}
        self.engine_white = {'name': 'Engine V2 (Experimental)', 'eval_func': evaluate_board_v2_experimental}
        
        # --- Standard Game Setup ---
        self.board = Board(db_conn=None) # Simplified for now
        self.turn = self.board.turn
        self.done = False
        self.next_state = None
        self.large_font = pygame.font.SysFont(None, 24)
        self.font = pygame.font.SysFont(None, 20)
        self.winner_font = pygame.font.SysFont(None, 50)
        self.history_font = pygame.font.SysFont(None, 16)
        self.ai_depth = 5 # A good depth for automated testing
        self.winner = None
        self.last_move_path = None
        self.game_is_active = True
        self.full_move_history = []
        self.board_history = [copy.deepcopy(self.board)]
        self.history_index = 0
        self.ai_is_thinking = False
        self.ai_move_queue = queue.Queue()
        self.ai_best_move_for_execution = None

    def start_ai_turn(self):
        if self.ai_is_thinking or self.winner: return

        self.ai_is_thinking = True
        current_engine = self.engine_red if self.turn == RED else self.engine_white
        eval_function_to_use = current_engine['eval_func']
        
        board_copy = self.board_history[self.history_index]
        
        thread = threading.Thread(
            target=self.run_ai_calculation,
            args=(board_copy, self.turn, eval_function_to_use),
            daemon=True
        )
        thread.start()

    def run_ai_calculation(self, board_instance, color_to_move, evaluate_func):
        try:
            logger.info(f"AI_THREAD: Starting calculation for {'White' if color_to_move == WHITE else 'Red'} at depth {self.ai_depth}.")
            best_move, _ = get_ai_move_analysis(board_instance, self.ai_depth, color_to_move, evaluate_func)
            self.ai_move_queue.put({'best': best_move})
        except Exception as e:
            logger.error(f"AI_THREAD: CRITICAL ERROR: {e}", exc_info=True)
            self.ai_move_queue.put({'best': None})

    def _apply_move_sequence(self, path):
        if not path:
            # If one engine fails to find a move, the other wins.
            self.winner = RED if self.turn == WHITE else WHITE
            return

        current_board = self.board_history[self.history_index]
        new_board = current_board.apply_move(path)
        
        self.board_history.append(new_board)
        # Simplified history for now for automated games
        self.full_move_history.append(f"{len(self.full_move_history) + 1}.")
        self.history_index += 1
        
        self.board = new_board
        self.turn = self.board.turn
        self.winner = self.board.winner()
        self.last_move_path = path

    def update(self):
        if self.winner: return

        try:
            ai_results = self.ai_move_queue.get_nowait()
            self.ai_is_thinking = False
            self.ai_best_move_for_execution = ai_results['best']
        except queue.Empty:
            pass

        if not self.ai_is_thinking and self.ai_best_move_for_execution:
            self._apply_move_sequence(self.ai_best_move_for_execution)
            self.ai_best_move_for_execution = None
        elif not self.ai_is_thinking:
            self.start_ai_turn()

    def draw(self):
        self.screen.fill((40, 40, 40))
        self.board.draw(self.screen, self.font, False, False, set(), self.last_move_path)
        
        # Simple side panel for match status
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - panel_x
        pygame.draw.rect(self.screen, (20, 20, 20), (panel_x, 0, panel_width, self.screen.get_height()))
        
        red_text = self.large_font.render(f"Red: {self.engine_red['name']}", True, (255, 150, 150))
        white_text = self.large_font.render(f"White: {self.engine_white['name']}", True, (200, 200, 255))
        self.screen.blit(red_text, (panel_x + 10, 20))
        self.screen.blit(white_text, (panel_x + 10, 50))
        
        if self.winner:
            winner_color_name = "Red" if self.winner == RED else "White"
            winner_engine_name = self.engine_red['name'] if self.winner == RED else self.engine_white['name']
            text = f"{winner_color_name} Wins! ({winner_engine_name})"
            color = (255, 100, 100) if self.winner == RED else (150, 150, 255)
            winner_surface = self.winner_font.render(text, True, color)
            self.screen.blit(winner_surface, (BOARD_SIZE // 2 - winner_surface.get_width() // 2, BOARD_SIZE // 2))
        elif self.ai_is_thinking:
            turn_color = "Red" if self.turn == RED else "White"
            thinking_text = self.large_font.render(f"{turn_color} is thinking...", True, (255, 255, 0))
            self.screen.blit(thinking_text, (panel_x + 10, 100))

    def handle_event(self, event):
        # This mode is non-interactive
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.done = True
            self.next_state = "player_selection" # Go back to main menu

