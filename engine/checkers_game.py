# engine/checkers_game.py
import pygame
import logging
import threading
import queue
import copy
import time
import sqlite3
import os
import re
from .board import Board
from .constants import SQUARE_SIZE, RED, WHITE, BOARD_SIZE, ROWS, COLS, DEFAULT_AI_DEPTH
import engine.constants as constants
from game_states import Button
from engine.search import get_ai_move_analysis
from engine.evaluation import evaluate_board_v1

logger = logging.getLogger('gui')

class CheckersGame:
    def __init__(self, screen, player_color_str, status_queue, args):
        self.screen = screen
        self.args = args
        self.db_conn = None
        try:
            self.db_conn = sqlite3.connect("checkers_endgame.db")
        except Exception as e:
            logger.error(f"DATABASE: Failed to connect: {e}")
            self.db_conn = None

        self.board = Board(db_conn=self.db_conn)
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
        
        self.large_font = pygame.font.SysFont(None, 24)
        self.font = pygame.font.SysFont(None, 20)
        self.dev_font = pygame.font.SysFont(None, 18)
        self.winner_font = pygame.font.SysFont(None, 50)
        self.history_font = pygame.font.SysFont(None, 16)
        
        self.ai_depth = DEFAULT_AI_DEPTH
        self.winner = None
        self.last_move_path = None
        self.wants_to_load_pdn = False
        self.pending_pdn_load = False
        self.game_is_active = True

        self.full_move_history = []
        self.board_history = [copy.deepcopy(self.board)]
        self.history_index = 0

        button_width = 171
        button_height = 28
        side_panel_width = self.screen.get_width() - BOARD_SIZE
        button_x = BOARD_SIZE + (side_panel_width - button_width) // 2
        button_y_start = self.screen.get_height() - 38
        nav_button_y = button_y_start - 228
        self.buttons = [
            Button("Dev Mode", (button_x, button_y_start), (button_width, button_height), self.toggle_dev_mode),
            Button("Board Numbers", (button_x, button_y_start - 38), (button_width, button_height), self.toggle_board_numbers),
            Button("Load PDN", (button_x, button_y_start - 76), (button_width, button_height), self.request_pdn_load),
            Button("Export to PDN", (button_x, button_y_start - 114), (button_width, button_height), self.export_to_pdn),
            Button("Force AI Move", (button_x, button_y_start - 152), (button_width, button_height), self.force_ai_move),
            Button("Reset", (button_x, button_y_start - 190), (button_width, button_height), self.reset_game),
            Button("<", (button_x, nav_button_y), (40, 28), self.step_back),
            Button(">", (button_x + 45, nav_button_y), (40, 28), self.step_forward),
            Button("-", (button_x + (button_width - 70), button_y_start - 263), (30, 28), self.decrease_ai_depth),
            Button("+", (button_x + (button_width - 35), button_y_start - 263), (30, 28), self.increase_ai_depth)
        ]

        self.ai_is_thinking = False
        self.ai_move_queue = queue.Queue()
        self.ai_top_moves = []
        self.ai_best_move_for_execution = None
        self.force_ai_flag = False
        self.feedback_message = ""
        self.feedback_timer = 0
        self.feedback_color = (180, 220, 180)

    def _coord_to_acf(self, coord):
        return str(constants.COORD_TO_ACF.get(coord, "??"))

    def _format_move_path(self, path):
        if not path or len(path) < 2: return ""
        
        start_pos = path[0]
        end_pos = path[-1]
        is_jump = abs(start_pos[0] - end_pos[0]) >= 2

        # --- NEW: Formatting for long jumps as requested ---
        if is_jump:
            # For multi-jumps, show only the start and end
            if len(path) > 2:
                return f"{self._coord_to_acf(start_pos)}x{self._coord_to_acf(end_pos)}"
            # For single jumps, show start x end
            return f"{self._coord_to_acf(start_pos)}x{self._coord_to_acf(path[1])}"
        
        # Standard move formatting
        return f"{self._coord_to_acf(start_pos)}-{self._coord_to_acf(end_pos)}"

    def step_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.game_is_active = False
            self.selected_piece = None
            self.ai_top_moves = [] # Clear analysis when stepping
            self._update_game_state_from_history()
            logger.debug(f"HISTORY: Stepped back to index {self.history_index}")

    def step_forward(self):
        if self.history_index < len(self.board_history) - 1:
            self.history_index += 1
            self._update_game_state_from_history()
            if self.history_index == len(self.board_history) - 1:
                self.game_is_active = True
            logger.debug(f"HISTORY: Stepped forward to index {self.history_index}")

    def _update_game_state_from_history(self):
        self.board = self.board_history[self.history_index]
        self.turn = self.board.turn
        self.winner = self.board.winner()
        # Update last move for highlighting
        if self.history_index > 0:
            last_move_str = self.full_move_history[self.history_index - 1]
            separator = 'x' if 'x' in last_move_str else '-'
            parts = [int(p) for p in last_move_str.split(separator)]
            self.last_move_path = [constants.ACF_TO_COORD.get(p) for p in parts]
        else:
            self.last_move_path = None

    def start_ai_turn(self, force_color=None):
        self.ai_is_thinking = True
        self.ai_top_moves = [] # Clear previous analysis
        self.ai_best_move_for_execution = None
        color_to_move = force_color if force_color else self.turn
        board_copy = self.board_history[self.history_index]
        threading.Thread(target=self.run_ai_calculation, args=(board_copy, color_to_move,)).start()

    def run_ai_calculation(self, board_instance, color_to_move):
        try:
            logger.info(f"AI_THREAD: Starting calculation for {'White' if color_to_move == WHITE else 'Red'} at depth {self.ai_depth}.")
            # --- FIX: Pass the specific, stable evaluation function to the search ---
            best_move, top_moves = get_ai_move_analysis(board_instance, self.ai_depth, color_to_move, evaluate_board_v1)
            self.ai_move_queue.put({'best': best_move, 'top': top_moves})
            logger.info("AI_THREAD: Calculation finished. Move placed in queue.")
        except Exception as e:
            logger.error(f"AI_THREAD: CRITICAL ERROR during calculation: {e}", exc_info=True)
            self.ai_move_queue.put({'best': None, 'top': []})

    def _apply_move_sequence(self, path):
        if not path: return

        if self.history_index < len(self.board_history) - 1:
            self.board_history = self.board_history[:self.history_index + 1]
            self.full_move_history = self.full_move_history[:self.history_index]
            logger.info("HISTORY: New move from past state. Future history truncated.")

        current_board = self.board_history[self.history_index]
        new_board = current_board.apply_move(path)
        
        self.board_history.append(new_board)
        self.full_move_history.append(self._format_move_path(path))
        self.history_index += 1
        self._update_game_state_from_history()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Always check for button clicks first, regardless of winner
            clicked_button = False
            for button in self.buttons:
                if button.is_clicked(event.pos):
                    button.callback()
                    clicked_button = True
                    break
            
            # Only handle clicks on the board itself if the game is not over
            if not clicked_button and not self.winner:
                row, col = event.pos[1] // SQUARE_SIZE, event.pos[0] // SQUARE_SIZE
                if self.turn == self.player_color or not self.game_is_active:
                    current_board = self.board_history[self.history_index]
                    piece = current_board.get_piece(row, col)
                    if self.selected_piece and (row, col) in self.valid_moves.get((self.selected_piece.row, self.selected_piece.col), set()):
                        self._attempt_move((row, col))
                    elif piece != 0 and piece.color == self.turn:
                        self._select_piece(row, col)
                    else:
                        self.selected_piece = None
                        self.valid_moves = {}

    def update(self):
        if self.winner: return
        
        if self.feedback_timer > 0: self.feedback_timer -= 1
        else: self.feedback_message = ""

        try:
            ai_results = self.ai_move_queue.get_nowait()
            self.ai_is_thinking = False
            self.ai_top_moves = ai_results['top'] # Get the new analysis
            self.ai_best_move_for_execution = ai_results['best']
            
            if self.pending_pdn_load:
                self.wants_to_load_pdn = True
                self.pending_pdn_load = False
                logger.debug("AI finished. Executing deferred PDN load request.")
            if not self.ai_best_move_for_execution: self.winner = self.player_color
        except queue.Empty:
            pass

        if self.game_is_active and (self.turn == self.ai_color or self.force_ai_flag) and not self.ai_is_thinking and self.ai_best_move_for_execution:
            self._apply_move_sequence(self.ai_best_move_for_execution)
            self.ai_best_move_for_execution = None
            self.force_ai_flag = False
        elif self.game_is_active and self.turn == self.ai_color and not self.ai_is_thinking and not self.ai_best_move_for_execution:
            self.start_ai_turn()

    def draw(self):
        self.screen.fill((40, 40, 40))
        current_board = self.board_history[self.history_index]
        turn_for_moves = current_board.turn
        all_paths = current_board.get_all_move_sequences(turn_for_moves)
        valid_moves_dict = {}
        for path in all_paths:
    	    start_pos = path[0]
    	    end_pos = path[-1]
    	    if start_pos not in valid_moves_dict:
    	        valid_moves_dict[start_pos] = set()
    	    valid_moves_dict[start_pos].add(end_pos)
        self.valid_moves = valid_moves_dict
        
        moves_to_highlight = set()
        if self.selected_piece:
            moves_to_highlight = self.valid_moves.get((self.selected_piece.row, self.selected_piece.col), set())
      #  print(f"DEBUG: Highlighting moves: {moves_to_highlight}") 
        current_board.draw(self.screen, self.font, self.show_board_numbers, self.board_flipped, moves_to_highlight, self.last_move_path)
        
        self.draw_side_panel()
        if self.dev_mode: self.draw_dev_panel()
        if self.winner is not None:
            text = "You Win!" if self.winner == self.player_color else "AI Wins!"
            color = (100, 255, 100) if self.winner == self.player_color else (255, 100, 100)
            winner_surface = self.winner_font.render(text, True, color)
            self.screen.blit(winner_surface, (BOARD_SIZE // 2 - winner_surface.get_width() // 2, BOARD_SIZE // 2 - winner_surface.get_height() // 2))

    def draw_side_panel(self):
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - panel_x
        panel_rect = pygame.Rect(panel_x, 0, panel_width, self.screen.get_height())
        pygame.draw.rect(self.screen, (20, 20, 20), panel_rect)
        pygame.draw.line(self.screen, (100, 100, 100), (panel_x, 0), (panel_x, self.screen.get_height()), 2)
        for button in self.buttons: button.draw(self.screen)
        
        turn_text_str = "White's Turn" if self.turn == WHITE else "Red's Turn"
        if not self.game_is_active: turn_text_str = f"Analysis: Mv {self.history_index}"
        
        turn_surface = self.large_font.render(turn_text_str, True, (255, 255, 255))
        self.screen.blit(turn_surface, (panel_x + 10, 15))

        y_pos_after_turn = 50
        if self.feedback_timer > 0 and self.feedback_message:
            feedback_surface = self.font.render(self.feedback_message, True, self.feedback_color)
            self.screen.blit(feedback_surface, (panel_x + 10, y_pos_after_turn))
        elif self.ai_is_thinking:
            thinking_text = self.large_font.render("AI is thinking...", True, (255, 255, 0))
            self.screen.blit(thinking_text, (panel_x + 10, y_pos_after_turn))
        
        history_y_start = 80
        history_title = self.large_font.render("Move History:", True, (200, 200, 200))
        self.screen.blit(history_title, (panel_x + 10, history_y_start))
        y_offset = history_y_start + 30
        line_height = 18

        # --- NEW: Rewritten Move History Display Logic ---
        moves_per_column = 12 
        col1_x = panel_x + 15
        col2_x = panel_x + (panel_width // 2)

        for i in range(moves_per_column):
            # First Column
            move_idx = i * 2
            if move_idx < len(self.full_move_history):
                move_num = i + 1
                red_move = self.full_move_history[move_idx]
                white_move = self.full_move_history[move_idx + 1] if move_idx + 1 < len(self.full_move_history) else ""
                line = f"{move_num}. {red_move} {white_move}"
                
                # Highlight based on history index
                is_current_red = move_idx == self.history_index - 1
                is_current_white = move_idx + 1 == self.history_index - 1
                color = (255, 255, 0) if (is_current_red or is_current_white) else (220, 220, 220)

                move_surface = self.history_font.render(line, True, color)
                self.screen.blit(move_surface, (col1_x, y_offset + i * line_height))

            # Second Column
            move_idx = (i + moves_per_column) * 2
            if move_idx < len(self.full_move_history):
                move_num = i + moves_per_column + 1
                red_move = self.full_move_history[move_idx]
                white_move = self.full_move_history[move_idx + 1] if move_idx + 1 < len(self.full_move_history) else ""
                line = f"{move_num}. {red_move} {white_move}"
                
                is_current_red = move_idx == self.history_index - 1
                is_current_white = move_idx + 1 == self.history_index - 1
                color = (255, 255, 0) if (is_current_red or is_current_white) else (220, 220, 220)

                move_surface = self.history_font.render(line, True, color)
                self.screen.blit(move_surface, (col2_x, y_offset + i * line_height))

        depth_button = self.buttons[-2]
        depth_text_surface = self.large_font.render(f"AI Depth: {self.ai_depth}", True, (200, 200, 200))
        text_y = depth_button.rect.centery - (depth_text_surface.get_height() // 2)
        self.screen.blit(depth_text_surface, (panel_x + 10, text_y))

    def draw_dev_panel(self):
        panel_height = self.screen.get_height() - BOARD_SIZE
        if panel_height <= 0: return
        panel_y, panel_rect = BOARD_SIZE, pygame.Rect(0, BOARD_SIZE, BOARD_SIZE, panel_height)
        pygame.draw.rect(self.screen, (30, 30, 30), panel_rect)
        pygame.draw.line(self.screen, (100, 100, 100), (0, panel_y), (BOARD_SIZE, panel_y), 2)
        if not self.ai_top_moves: return
        y_offset = panel_y + 5
        title_text = self.large_font.render("AI Analysis:", True, (200, 200, 200))
        self.screen.blit(title_text, (10, y_offset))
        y_offset += 25
        line_height = 18
        for i, (score, sequence) in enumerate(self.ai_top_moves):
            if not sequence: continue
            move_text = f"{i+1}. " + " ".join(f"({self._format_move_path(seg)})" for seg in sequence)
            score_text = f"Score: {score:.2f}"
            full_text = f"{move_text} {score_text}"
            text_surface = self.dev_font.render(full_text, True, (220, 220, 220))
            self.screen.blit(text_surface, (15, y_offset))
            y_offset += line_height
            if y_offset > self.screen.get_height() - (line_height / 2): break

    def increase_ai_depth(self): self.ai_depth = min(9, self.ai_depth + 1)
    def decrease_ai_depth(self): self.ai_depth = max(5, self.ai_depth - 1)
    def toggle_dev_mode(self): self.dev_mode = not self.dev_mode
    def toggle_board_numbers(self): self.show_board_numbers = not self.show_board_numbers
    def toggle_board_flip(self): self.board_flipped = not self.board_flipped
    
    def force_ai_move(self):
        if not self.ai_is_thinking:
            self.game_is_active = True
            self.force_ai_flag = True
            self.start_ai_turn(self.turn)

    def reset_game(self):
        self.board = Board(db_conn=self.db_conn)
        self.turn = self.board.turn
        self.selected_piece = None
        self.winner = None
        self.last_move_path = None
        self.ai_top_moves = []
        self.game_is_active = True
        self.full_move_history = []
        self.board_history = [copy.deepcopy(self.board)]
        self.history_index = 0

    def export_to_pdn(self):
        try:
            filename = f"game_{time.strftime('%Y%m%d_%H%M%S')}.pdn"
            with open(filename, "w") as f:
                f.write('[Event "Checkers Game"]\n[Site "Local"]\n')
                f.write(f'[Date "{time.strftime("%Y.%m.%d")}"]\n[Round "-"]\n')
                f.write(f'[White "{"Player" if self.player_color == WHITE else "AI"}"]\n')
                f.write(f'[Black "{"Player" if self.player_color == RED else "AI"}"]\n')
                f.write('[Result "*"]\n\n')
                move_str = ""
                for i in range(0, len(self.full_move_history), 2):
                    move_num = i // 2 + 1
                    red_move = self.full_move_history[i]
                    white_move = self.full_move_history[i+1] if i + 1 < len(self.full_move_history) else ""
                    move_str += f"{move_num}. {red_move} {white_move} "
                f.write(move_str.strip() + " *\n")
            self.feedback_message = f"Saved to {filename}"
            self.feedback_timer, self.feedback_color = 180, (180, 220, 180)
        except Exception as e:
            self.feedback_message = "Error saving PDN!"
            self.feedback_timer, self.feedback_color = 180, (220, 180, 180)
    
    def load_pdn_from_file(self, filepath):
        logger.info(f"PDN_LOAD: Received filepath: {filepath}")
        try:
            with open(filepath, 'r') as f: pdn_text = f.read()
            movetext_match = re.search(r'1\..*?(?=\[|$)', pdn_text, re.DOTALL)
            if not movetext_match: raise ValueError("No valid movetext found in PDN file.")
            
            movetext = movetext_match.group(0)
            moves_only = re.sub(r'\{.*?\}|\d+\.|\*', '', movetext).split()
            
            temp_board = Board(db_conn=self.db_conn)
            new_board_history = [copy.deepcopy(temp_board)]
            new_move_history = []
            
            for i, move_str in enumerate(moves_only):
                separator = 'x' if 'x' in move_str else '-'
                parts = [int(p) for p in move_str.split(separator)]
                path_to_apply = [constants.ACF_TO_COORD.get(p) for p in parts]
                if None in path_to_apply:
                    logger.warning(f"PDN_LOAD: Could not parse move '{move_str}'. Skipping.")
                    continue
                
                temp_board = temp_board.apply_move(path_to_apply)
                new_board_history.append(temp_board)
                new_move_history.append(move_str)
            
            self.board_history = new_board_history
            self.full_move_history = new_move_history
            self.history_index = len(self.board_history) - 1
            self._update_game_state_from_history()
            
            self.game_is_active, self.ai_top_moves = False, []
            self.feedback_message = f"Loaded {os.path.basename(filepath)}"
            self.feedback_timer, self.feedback_color = 180, (180, 220, 180)
            logger.info(f"Successfully loaded game from {filepath}. Game is now in analysis mode.")
        except Exception as e:
            self.feedback_message = "Error loading PDN!"
            self.feedback_timer, self.feedback_color = 180, (220, 180, 180)
            logger.error(f"Failed to load PDN file '{filepath}': {e}", exc_info=True)

    def _select_piece(self, row, col):
        current_board = self.board_history[self.history_index]
        piece = current_board.get_piece(row, col)
        if piece != 0 and piece.color == self.turn:
            self.selected_piece = piece
            log_moves = {self._coord_to_acf(m) for m in self.valid_moves.get((row, col), set())}
            logger.debug(f"Piece selected at {self._coord_to_acf((row, col))}. Valid destinations: {log_moves}")
            return True
        self.selected_piece, self.valid_moves = None, {}
        return False

    def _attempt_move(self, move_end_pos):
        if not self.selected_piece: return False
        
        current_board = self.board_history[self.history_index]
        start_pos = (self.selected_piece.row, self.selected_piece.col)
        
        all_possible_sequences = list(current_board.get_all_move_sequences(self.turn))
        found_path = next((path for path in all_possible_sequences if path[0] == start_pos and path[-1] == move_end_pos), None)
        
        if found_path:
            #logger.info(f"Player move validated. Applying sequence: {self._format_move_path(found_path)}")
            self.game_is_active = True
            self._apply_move_sequence(found_path)
            return True

        logger.warning(f"Invalid move attempted from {self._coord_to_acf(start_pos)} to {self._coord_to_acf(move_end_pos)}. Clearing selection.")
        self.selected_piece, self.valid_moves = None, {}
        return False
        
    def request_pdn_load(self):
        logger.debug("PDN_LOAD: Button clicked.")
        if self.ai_is_thinking:
            self.pending_pdn_load = True
            self.feedback_message, self.feedback_timer, self.feedback_color = "Will load after AI moves...", 120, (255, 255, 0)
            logger.debug("PDN_LOAD: AI is thinking. Deferring request.")
        else:
            logger.debug("PDN_LOAD: Requesting file dialog from main loop.")
            self.wants_to_load_pdn = True
