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
    A refactored, universal game controller that handles all game modes
    with a full UI and analysis features.
    """
    # ======================================================================================
    # --- Initialization and Setup ---
    # ======================================================================================
    def __init__(self, screen, status_queue, args, red_player_config, white_player_config):
        """
        Initializes the entire game state.
        """
        self.screen = screen
        self.args = args
        self.status_queue = status_queue

        self.players = { RED: red_player_config, WHITE: white_player_config }
        self.is_human_game = self.players[RED]['type'] == 'human' or self.players[WHITE]['type'] == 'human'

        self.board = Board()
        self.turn = self.board.turn
        self.selected_piece = None
        self.valid_moves = {}
        self.done = False
        self.next_state = "player_selection"
        self.winner = None
        self.game_is_active = True
        self.last_move_time = 0
        self.last_move_path = None

        self.full_move_history = []
        self.board_history = [copy.deepcopy(self.board)]
        self.history_index = 0
        self.position_counts = {}
        self._update_position_counts(self.board)

        self.show_board_numbers = True
        self.dev_mode = True
        self.board_flipped = False
        self.large_font = pygame.font.SysFont(None, 24)
        self.font = pygame.font.SysFont(None, 20)
        self.dev_font = pygame.font.SysFont(None, 18)
        self.winner_font = pygame.font.SysFont(None, 50)
        self.history_font = pygame.font.SysFont(None, 16)
        self.feedback_message = ""
        self.feedback_timer = 0
        
        self.ai_depth = DEFAULT_AI_DEPTH
        self.ai_is_thinking = False
        self.ai_move_queue = queue.Queue()
        self.ai_top_moves = []
        self.ai_best_move_for_execution = None
        self.force_ai_flag = False

        self.wants_to_load_fen = False
        self.wants_to_load_pdn = False

        self._initialize_buttons()

    def _initialize_buttons(self):
        """
        Creates the UI buttons with a simple, robust layout logic.
        """
        self.buttons = []
        button_width, button_height = 171, 28
        side_panel_width = self.screen.get_width() - BOARD_SIZE
        button_x = BOARD_SIZE + (side_panel_width - button_width) // 2
        
        button_y = self.screen.get_height() - button_height - 10
        y_step = button_height + 10

        base_buttons = [
            ("Dev Mode", self.toggle_dev_mode),
            ("Reset Match", self.reset_game),
            ("Main Menu", self.go_to_main_menu),
        ]
        human_buttons = [
            ("Load Position (FEN)", self.request_fen_load),
            ("Force AI Move", self.force_ai_move),
            ("Load PDN", self.request_pdn_load),
            ("Export to PDN", self.export_to_pdn),
        ]
        ai_buttons = [
            ("Load Position (FEN)", self.request_fen_load),
            ("Pause/Resume", self.toggle_pause),
        ]
        
        layout = base_buttons
        if self.is_human_game:
            layout += human_buttons
        else:
            layout += ai_buttons

        for text, callback in layout:
            self.buttons.append(Button(text, (button_x, button_y), (button_width, button_height), callback))
            button_y -= y_step

        nav_y = button_y - 10
        self.buttons.append(Button("<", (button_x, nav_y), (40, 28), self.step_back))
        self.buttons.append(Button(">", (button_x + 45, nav_y), (40, 28), self.step_forward))
        depth_btn_y = nav_y - 35
        self.buttons.append(Button("-", (button_x + (button_width - 70), depth_btn_y), (30, 28), self.decrease_ai_depth))
        self.buttons.append(Button("+", (button_x + (button_width - 35), depth_btn_y), (30, 28), self.increase_ai_depth))

    # ======================================================================================
    # --- Core Game Loop Methods ---
    # ======================================================================================
    def update(self):
        if self.winner: self.game_is_active = False
        if self.board.moves_since_progress >= 80:
            self.winner = "DRAW"; logger.info("DRAW by 40-move rule.")

        try:
            res = self.ai_move_queue.get_nowait()
            self.ai_is_thinking = False
            self.ai_top_moves = res.get('top', [])
            self.ai_best_move_for_execution = res.get('best')
            if not self.ai_best_move_for_execution and not self.is_human_turn(): 
                self.winner = RED if self.turn == WHITE else WHITE
        except queue.Empty: pass
        
        is_ai_turn_to_play = (not self.is_human_turn()) or self.force_ai_flag

        if self.game_is_active and is_ai_turn_to_play and not self.ai_is_thinking:
            move_delay = 0.5 if not self.is_human_game else 0
            if time.time() - self.last_move_time > move_delay:
                if self.ai_best_move_for_execution:
                    self._apply_move_sequence(self.ai_best_move_for_execution)
                    self.ai_best_move_for_execution = None
                    self.force_ai_flag = False
                else:
                    self.start_ai_turn()

    def draw(self, screen):
        self.screen.fill((40, 40, 40))
        current_board = self.board_history[self.history_index]
        all_paths = current_board.get_all_move_sequences(current_board.turn)
        self.valid_moves = {}
        for path in all_paths:
            start_pos, end_pos = path[0], path[-1]
            if start_pos not in self.valid_moves: self.valid_moves[start_pos] = set()
            self.valid_moves[start_pos].add(end_pos)
        moves_to_highlight = set()
        if self.selected_piece and self.is_human_turn():
            moves_to_highlight = self.valid_moves.get((self.selected_piece.row, self.selected_piece.col), set())
        current_board.draw(self.screen, self.font, self.show_board_numbers, self.board_flipped, moves_to_highlight, self.last_move_path)
        self.draw_side_panel()
        if self.dev_mode: self.draw_dev_panel()
        if self.winner: self._draw_winner_message()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.is_clicked(event.pos):
                    button.callback()
                    return
            if self.game_is_active and not self.winner and self.is_human_turn():
                row, col = event.pos[1] // SQUARE_SIZE, event.pos[0] // SQUARE_SIZE
                self._handle_board_click(row, col)

    # ======================================================================================
    # --- FEN, PDN, and Test Position Loading ---
    # ======================================================================================
    def request_fen_load(self):
        """Sets a flag for the main loop to open a FEN file dialog."""
        self.wants_to_load_fen = True
        logger.info("FEN load requested.")
    
    def load_fen_from_file(self, filepath):
        """
        REWRITTEN: Loads the first valid FEN position from a text file,
        intelligently ignoring comments and blank lines.
        """
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    fen_string = line.strip()
                    # A valid FEN must have 2 colons. Ignore comments and blank lines.
                    if fen_string and not fen_string.startswith('#') and fen_string.count(':') == 2:
                        # Found the first valid FEN, now load it.
                        new_board = Board()
                        new_board.create_board_from_fen(fen_string)
                        self._reset_game_state_with_new_board(new_board)
                        logger.info(f"Loaded position from FEN: {fen_string}")
                        
                        # Immediately trigger an analysis of the new position
                        self.force_ai_move()
                        return # Stop after loading the first valid position
            
            # If we get here, no valid FEN was found in the file.
            logger.error(f"No valid FEN string found in file: {filepath}")

        except Exception as e:
            logger.error(f"Failed to load FEN file '{filepath}': {e}")
            
    def request_pdn_load(self):
        self.wants_to_load_pdn = True
        logger.info("PDN load requested.")

    def load_pdn_from_file(self, filepath):
        logger.info(f"PDN loading from {filepath} is not yet fully implemented.")
    
    def export_to_pdn(self):
        # Placeholder for PDN export logic
        logger.info("Export to PDN clicked.")

    # ======================================================================================
    # --- The rest of the class methods, verified and complete ---
    # ======================================================================================
    def _get_board_key(self, board_obj):
        return (tuple(map(tuple, board_obj.board)), board_obj.turn)

    def _update_position_counts(self, board_obj):
        key = self._get_board_key(board_obj)
        self.position_counts[key] = self.position_counts.get(key, 0) + 1
        if self.position_counts[key] >= 3:
            self.winner = "DRAW"
            self.game_is_active = False
            logger.info("DRAW by three-fold repetition.")

    def start_ai_turn(self):
        """
        Starts the AI calculation in a separate thread.
        FIXED: Now correctly determines which evaluation function to use
        when forcing a move for a human player.
        """
        if self.ai_is_thinking or self.winner: return
        self.ai_is_thinking = True
        self.ai_top_moves = []
        self.ai_best_move_for_execution = None

        # --- FIX: Determine the correct evaluation function ---
        if self.force_ai_flag and self.is_human_turn():
            # If a human forces a move, use the AI opponent's "brain"
            ai_opponent_color = WHITE if self.turn == RED else RED
            eval_func = self.players[ai_opponent_color]['eval_func']
        else:
            # Normal case: it's the AI's turn
            eval_func = self.players[self.turn]['eval_func']
        
        board_copy = copy.deepcopy(self.board_history[self.history_index])
        threading.Thread(target=self.run_ai_calculation, args=(board_copy, self.turn, eval_func), daemon=True).start()

    def run_ai_calculation(self, board_instance, color_to_move, evaluate_func):
        db_conn = None
        try:
            db_conn = sqlite3.connect("checkers_endgame.db")
            board_instance.db_conn = db_conn
            best_move, top_moves = get_ai_move_analysis(board_instance, self.ai_depth, color_to_move, evaluate_func)
            self.ai_move_queue.put({'best': best_move, 'top': top_moves})
        except Exception as e:
            logger.error(f"AI_THREAD: CRITICAL ERROR: {e}", exc_info=True)
            self.ai_move_queue.put({'best': None, 'top': []})
        finally:
            if db_conn: db_conn.close()
            board_instance.db_conn = None

    def draw_side_panel(self):
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - panel_x
        pygame.draw.rect(self.screen, (20, 20, 20), (panel_x, 0, panel_width, self.screen.get_height()))
        
        red_text = self.large_font.render(f"Red: {self.players[RED]['name']}", True, (255, 150, 150))
        white_text = self.large_font.render(f"White: {self.players[WHITE]['name']}", True, (200, 200, 255))
        self.screen.blit(red_text, (panel_x + 10, 20))
        self.screen.blit(white_text, (panel_x + 10, 50))

        turn_color = "Red's" if self.turn == RED else "White's"
        status_text = f"Analysis: Mv {self.history_index}" if not self.game_is_active and not self.winner else f"{turn_color} Turn"
        if self.ai_is_thinking: status_text = f"{turn_color} Thinking..."
        if self.winner: status_text = "Match Over"
        
        status_surface = self.large_font.render(status_text, True, (255, 255, 0) if self.ai_is_thinking else (220, 220, 220))
        self.screen.blit(status_surface, (panel_x + 10, 90))

        history_y_start, line_height, moves_per_col = 130, 18, 12
        move_pairs = []
        for i in range(0, len(self.full_move_history), 2):
            move_num = i // 2 + 1
            red_move = self.full_move_history[i]
            white_move = self.full_move_history[i + 1] if i + 1 < len(self.full_move_history) else ""
            move_pairs.append(f"{move_num}. {red_move} {white_move}")

        for i, line in enumerate(move_pairs):
            col = i // moves_per_col
            if col > 1: break
            row = i % moves_per_col
            x_pos = panel_x + 15 + (col * 100)
            y_pos = history_y_start + row * line_height
            is_current = (i * 2 == self.history_index - 1) or (i * 2 + 1 == self.history_index - 1)
            color = (255, 255, 0) if is_current else (200, 200, 200)
            move_surface = self.history_font.render(line, True, color)
            self.screen.blit(move_surface, (x_pos, y_pos))

        depth_btn_y = self.buttons[-1].rect.y
        depth_text = self.large_font.render(f"AI Depth: {self.ai_depth}", True, (200, 200, 200))
        self.screen.blit(depth_text, (panel_x + 10, depth_btn_y - 30))

        for button in self.buttons: button.draw(self.screen)

    def draw_dev_panel(self):
        panel_y = BOARD_SIZE
        panel_height = self.screen.get_height() - panel_y
        if panel_height <= 0: return
        pygame.draw.rect(self.screen, (30, 30, 30), (0, panel_y, BOARD_SIZE, panel_height))
        y_offset = panel_y + 5
        title_text = self.large_font.render("AI Analysis (Principal Variation):", True, (200, 200, 200))
        self.screen.blit(title_text, (10, y_offset))
        y_offset += 25
        for i, (score, sequence) in enumerate(self.ai_top_moves):
            if not sequence: continue
            x_offset = 15
            score_text = f"{i+1}. (Score: {score:.2f}) "
            score_surface = self.dev_font.render(score_text, True, (220, 220, 220))
            self.screen.blit(score_surface, (x_offset, y_offset + i * 20))
            x_offset += score_surface.get_width()
            first_move_path = sequence[0]
            start_pos = first_move_path[0]
            first_piece = self.board.get_piece(start_pos[0], start_pos[1])
            current_move_color = self.turn if not first_piece else first_piece.color
            for move_path in sequence:
                move_text = self._format_move_path(move_path)
                text_color = (255, 150, 150) if current_move_color == RED else (200, 200, 255)
                move_surface = self.dev_font.render(move_text, True, text_color)
                self.screen.blit(move_surface, (x_offset, y_offset + i * 20))
                x_offset += move_surface.get_width() + 10
                current_move_color = WHITE if current_move_color == RED else RED

    def _draw_winner_message(self):
        if self.winner == "DRAW":
            text, color = "Draw!", (200, 200, 200)
            winner_surface = self.winner_font.render(text, True, color)
            self.screen.blit(winner_surface, (BOARD_SIZE // 2 - winner_surface.get_width() // 2, BOARD_SIZE // 2 - 20))
        else:
            winner_color = "Red" if self.winner == RED else "White"
            winner_name = self.players[self.winner]['name']
            text = f"{winner_color} Wins!"
            sub_text = self.font.render(f"({winner_name})", True, (200, 200, 200))
            color = (255, 100, 100) if self.winner == RED else (150, 150, 255)
            winner_surface = self.winner_font.render(text, True, color)
            self.screen.blit(winner_surface, (BOARD_SIZE // 2 - winner_surface.get_width() // 2, BOARD_SIZE // 2 - 20))
            self.screen.blit(sub_text, (BOARD_SIZE // 2 - sub_text.get_width() // 2, BOARD_SIZE // 2 + 20))

    def go_to_main_menu(self): self.done = True
    def is_human_turn(self): return self.players[self.turn].get('type') == 'human'
    def toggle_pause(self): self.game_is_active = not self.game_is_active
    def step_back(self):
        if self.history_index > 0: self.game_is_active = False; self.history_index -= 1; self._update_game_state_from_history()
    def step_forward(self):
        if self.history_index < len(self.board_history) - 1: self.history_index += 1; self._update_game_state_from_history()
    def reset_game(self):
        new_board = Board()
        self._reset_game_state_with_new_board(new_board)
        self.game_is_active = not self.is_human_game

    def _reset_game_state_with_new_board(self, new_board):
        self.board = new_board; self.turn = new_board.turn; self.winner = None; self.last_move_path = None
        self.ai_top_moves = []; self.full_move_history = []
        self.board_history = [copy.deepcopy(self.board)]; self.history_index = 0
        self.position_counts = {}; self._update_position_counts(self.board)

    def increase_ai_depth(self): self.ai_depth = min(9, self.ai_depth + 1)
    def decrease_ai_depth(self): self.ai_depth = max(3, self.ai_depth - 1)
    def toggle_dev_mode(self): self.dev_mode = not self.dev_mode
    def force_ai_move(self):
        if self.ai_is_thinking or self.winner: return
        self.force_ai_flag = True
        logger.info(f"Force AI move requested for {self.turn}.")
        # The main update loop will now pick this up and start the AI turn.

    def _format_move_path(self, path):
        if not path or len(path) < 2: return "??"
        start, end = path[0], path[-1]
        sep = 'x' if abs(start[0]-end[0]) >= 2 else '-'
        return f"{self._coord_to_acf(start)}{sep}{self._coord_to_acf(end)}"
    
    def _coord_to_acf(self, coord): return str(constants.COORD_TO_ACF.get(coord, "??"))
    
    def _apply_move_sequence(self, path):
        if not path: return
        self.last_move_time = time.time()
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
    
    def _update_game_state_from_history(self):
        self.board = self.board_history[self.history_index]
        self.turn = self.board.turn
        self.winner = self.board.winner()
        if self.history_index > 0:
            last_move_str = self.full_move_history[self.history_index-1]
            parts = re.findall(r'(\d+)', last_move_str)
            if len(parts) >= 2: self.last_move_path = [ACF_TO_COORD.get(int(p)) for p in parts if p and int(p) in ACF_TO_COORD]
        else: self.last_move_path = None
    
    def _handle_board_click(self, r, c):
        if self.selected_piece and self._attempt_move((r,c)): return
        self._select_piece(r,c)
    
    def _select_piece(self, r, c):
        piece = self.board.get_piece(r,c)
        self.selected_piece = piece if piece and piece.color == self.turn else None
    
    def _attempt_move(self, end_pos):
        start_pos = (self.selected_piece.row, self.selected_piece.col)
        path = next((p for p in self.board.get_all_move_sequences(self.turn) if p[0]==start_pos and p[-1]==end_pos), None)
        if path: self._apply_move_sequence(path); self.selected_piece = None; return True
        return False


