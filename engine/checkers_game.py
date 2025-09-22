# engine/checkers_game.py
import pygame
import logging
import threading
import queue
import copy
import re
import sqlite3
import os
import time
from .board import Board
from .piece import Piece
from .constants import SQUARE_SIZE, RED, WHITE, BOARD_SIZE, DEFAULT_AI_DEPTH, ACF_TO_COORD
import engine.constants as constants
from game_states import Button
from engine.search import get_ai_move_analysis
from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental

logger = logging.getLogger('gui')

class CheckersGame:
    """
    A refactored, universal analysis board controller where player types
    (Human, AI) can be changed dynamically during the game.
    """
    # ======================================================================================
    # --- Initialization and Setup ---
    # ======================================================================================
    def __init__(self, screen, status_queue, args):
        """
        Initializes the entire game state, UI, and player configurations.
        """
        self.screen = screen
        self.args = args
        self.status_queue = status_queue

        # --- Flexible Player Configuration ---
        self.player_options = [
            {'type': 'human', 'name': 'Human', 'eval_func': None},
            {'type': 'ai', 'name': 'Engine V1 (Stable)', 'eval_func': evaluate_board_v1},
            {'type': 'ai', 'name': 'Engine V2 (Exp)', 'eval_func': evaluate_board_v2_experimental}
        ]
        self.player_configs = {'RED': self.player_options[0], 'WHITE': self.player_options[1]}
        self.ai_depth = self.args.depth or DEFAULT_AI_DEPTH

        # --- Game State ---
        self.board_history = [Board()]
        self.full_move_history = []
        self.history_index = 0
        self.position_counts = {}
        self.selected_piece = None
        self.last_move_path = None
        self.valid_moves = {}
        self._update_game_state_from_history()
        self._update_position_counts(self.board)

        # --- AI Threading ---
        self.ai_thread = None
        self.ai_move_queue = queue.Queue()
        self.ai_is_thinking = False

        # --- UI Elements ---
        self.font = pygame.font.SysFont(None, 22)
        self.large_font = pygame.font.SysFont(None, 28)
        self.winner_font = pygame.font.SysFont(None, 48)
        self.back_button = Button(BOARD_SIZE + 10, 560, 180, 40, "Back to Menu")
        
        # --- NEW: Flip Board Button and State ---
        self.flip_board_button = Button(BOARD_SIZE + 10, 510, 180, 40, "Flip Board")
        self.board_is_flipped = False

        self.done = False
        self.next_state = None

    # ======================================================================================
    # --- Main Loop Functions ---
    # ======================================================================================
    def run(self):
        self.handle_ai_turn()
        self._check_for_ai_move()
        self._draw_game()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.done = True
            self.next_state = "QUIT"
        elif event.type == pygame.MOUSEBUTTONDOWN and not self.ai_is_thinking:
            if self.back_button.is_over(pygame.mouse.get_pos()):
                self.done = True
                return

            # --- NEW: Handle Flip Board Button Click ---
            if self.flip_board_button.is_over(pygame.mouse.get_pos()):
                self.board_is_flipped = not self.board_is_flipped
                return

            if self.player_configs[self.turn]['type'] == 'human':
                pos = pygame.mouse.get_pos()
                if pos[0] < BOARD_SIZE:
                    r, c = self._get_row_col_from_mouse(pos)
                    self._handle_board_click(r, c)

        elif event.type == pygame.KEYDOWN and not self.ai_is_thinking:
            if event.key == pygame.K_LEFT:
                self._navigate_history(-1)
            elif event.key == pygame.K_RIGHT:
                self._navigate_history(1)

    # ======================================================================================
    # --- Drawing ---
    # ======================================================================================
    def _draw_game(self):
        self.screen.fill((40, 40, 40))
        self._draw_board_and_pieces()
        self._draw_panel()
        pygame.display.update()

    def _draw_board_and_pieces(self):
        self.board.draw_squares(self.screen)
        
        # --- MODIFIED: Draw valid moves, pieces, and labels based on flipped state ---
        if self.selected_piece:
            self._draw_valid_moves(self.valid_moves.get(self.selected_piece, []))
            
        for r in range(constants.ROWS):
            for c in range(constants.COLS):
                piece = self.board.get_piece(r, c)
                
                # Determine draw coordinates based on flip state
                draw_r, draw_c = (constants.ROWS - 1 - r, constants.COLS - 1 - c) if self.board_is_flipped else (r, c)
                
                if piece:
                    piece.draw(self.screen, draw_r, draw_c)
        
        self._draw_labels()

    def _draw_labels(self):
        # --- MODIFIED: Draw board labels (1-32) based on flipped state ---
        for r in range(constants.ROWS):
            for c in range(constants.COLS):
                if (r + c) % 2 == 1:
                    draw_r, draw_c = (constants.ROWS - 1 - r, constants.COLS - 1 - c) if self.board_is_flipped else (r, c)
                    
                    square_num = constants.COORD_TO_ACF.get((r,c))
                    if square_num:
                        text = self.font.render(str(square_num), True, (200, 200, 200))
                        self.screen.blit(text, (draw_c * SQUARE_SIZE + 2, draw_r * SQUARE_SIZE + 2))

    def _draw_valid_moves(self, moves):
        # --- MODIFIED: Highlight valid moves based on flipped state ---
        for r, c in moves:
            draw_r, draw_c = (constants.ROWS - 1 - r, constants.COLS - 1 - c) if self.board_is_flipped else (r, c)
            pygame.draw.circle(self.screen, (0, 150, 0), (draw_c * SQUARE_SIZE + SQUARE_SIZE // 2, draw_r * SQUARE_SIZE + SQUARE_SIZE // 2), 15)

    def _draw_panel(self):
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - BOARD_SIZE
        pygame.draw.rect(self.screen, (20, 20, 20), (panel_x, 0, panel_width, self.screen.get_height()))

        # Draw Turn indicator
        turn_text = self.large_font.render(f"Turn: {self.turn}", True, (255, 255, 255))
        self.screen.blit(turn_text, (panel_x + 10, 20))

        # --- NEW: Draw Flip Board Button ---
        self.flip_board_button.draw(self.screen)
        
        self.back_button.draw(self.screen)
        
        if self.winner:
            text = f"{self.winner} Wins!"
            color = (255, 100, 100) if self.winner == RED else (150, 150, 255)
            winner_surface = self.winner_font.render(text, True, color)
            self.screen.blit(winner_surface, (BOARD_SIZE // 2 - winner_surface.get_width() // 2, BOARD_SIZE // 2))

    # ======================================================================================
    # --- Game Logic and Player Interaction ---
    # ======================================================================================
    def _get_row_col_from_mouse(self, pos):
        # --- MODIFIED: Calculate board coordinates from mouse click based on flipped state ---
        x, y = pos
        row = y // SQUARE_SIZE
        col = x // SQUARE_SIZE
        
        if self.board_is_flipped:
            return constants.ROWS - 1 - row, constants.COLS - 1 - col
        else:
            return row, col

    def _update_game_state_from_history(self):
        self.board = self.board_history[self.history_index]
        self.turn = self.board.turn
        self.winner = self.board.winner()
        if self.history_index > 0:
            last_move_str = self.full_move_history[self.history_index - 1]
            parts = re.findall(r'(\d+)', last_move_str)
            if len(parts) >= 2:
                self.last_move_path = [ACF_TO_COORD.get(int(p)) for p in parts if p and int(p) in ACF_TO_COORD]
        else:
            self.last_move_path = None
        
        self.selected_piece = None
        self.valid_moves = self.board.get_all_possible_moves(self.turn)

    def _handle_board_click(self, r, c):
        if self.selected_piece and self._attempt_move((r, c)): return
        self._select_piece(r, c)

    def _select_piece(self, r, c):
        piece = self.board.get_piece(r, c)
        if piece and piece.color == self.turn:
            # Check if this piece belongs to a set of forced jumps
            forced_jumps = [path for path in self.valid_moves if abs(path[0][0] - path[1][0]) == 2]
            if forced_jumps and not any(path[0] == (r, c) for path in forced_jumps):
                self.selected_piece = None # This piece cannot move
            else:
                self.selected_piece = piece
        else:
            self.selected_piece = None

    def _attempt_move(self, target_pos):
        move_paths = self.valid_moves.get(self.selected_piece, [])
        target_path = next((path for path in move_paths if path[-1] == target_pos), None)
        
        if target_path:
            self._apply_move_to_history(target_path)
            return True
        return False
    
    # --- The rest of the methods (handle_ai_turn, _check_for_ai_move, etc.) remain the same ---
    # (You don't need to change the functions below this line)
    
    def handle_ai_turn(self):
        if not self.winner and self.player_configs[self.turn]['type'] == 'ai' and not self.ai_is_thinking:
            self.ai_is_thinking = True
            eval_func = self.player_configs[self.turn]['eval_func']
            
            # Use a deepcopy to prevent the AI thread from modifying the main game board state
            board_copy = copy.deepcopy(self.board)
            
            self.ai_thread = threading.Thread(
                target=get_ai_move_analysis,
                args=(board_copy, self.ai_depth, self.turn, eval_func, self.ai_move_queue)
            )
            self.ai_thread.start()

    def _check_for_ai_move(self):
        if not self.ai_move_queue.empty():
            _, best_move = self.ai_move_queue.get()
            if best_move:
                self._apply_move_to_history(best_move)
            self.ai_is_thinking = False

    def _update_position_counts(self, board):
        fen = board.get_fen(compact=True)
        self.position_counts[fen] = self.position_counts.get(fen, 0) + 1

    def _navigate_history(self, direction):
        new_index = self.history_index + direction
        if 0 <= new_index < len(self.board_history):
            self.history_index = new_index
            self._update_game_state_from_history()
            
    def _apply_move_to_history(self, path):
        # Trim future history if we are branching from a past state
        if self.history_index < len(self.board_history) - 1:
            self.board_history = self.board_history[:self.history_index + 1]
            self.full_move_history = self.full_move_history[:self.history_index]

        current_board = self.board_history[self.history_index]
        new_board = current_board.apply_move(path)
        self.board_history.append(new_board)
        self.full_move_history.append(self._format_move_path(path))
        self.history_index += 1
        self._update_game_state_from_history()
        self._update_position_counts(self.board)

    def _format_move_path(self, path):
        separator = 'x' if abs(path[0][0] - path[1][0]) == 2 else '-'
        return separator.join(str(constants.COORD_TO_ACF.get(pos, "??")) for pos in path)
