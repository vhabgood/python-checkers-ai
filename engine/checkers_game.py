# engine/checkers_game.py
import pygame
import logging
import threading
import queue
import copy
import time
import pickle
import os
from .board import Board
from .constants import SQUARE_SIZE, RED, WHITE, BOARD_SIZE, ROWS, COLS, DEFAULT_AI_DEPTH
import engine.constants as constants
from game_states import Button # Assuming Button is in game_states
from engine.search import get_ai_move_analysis
from engine.evaluation import evaluate_board

logger = logging.getLogger('gui')

class CheckersGame:
    """
    The main game state manager. It handles the game loop, player input,
    AI turn management via threading, and drawing everything to the screen.
    """
    # The __init__ method now accepts a queue to send loading status updates
    def __init__(self, screen, player_color_str, status_queue):
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
        self.font = pygame.font.SysFont(None, 20)
        self.small_font = pygame.font.SysFont(None, 18)
        self.dev_font = pygame.font.SysFont('monospace', 12)
        self.number_font = pygame.font.SysFont(None, 18)
        self.ai_move_queue = queue.Queue()
        self.ai_thread = None
        self.ai_is_thinking = False
        self.positional_score = 0.0
        self.ai_top_moves = []
        self.ai_depth = DEFAULT_AI_DEPTH

        # --- THREADED LOADING ---
        # Send status messages to the loading screen via the provided queue
        status_queue.put("Loading Opening Book...")
        self.opening_book = self._load_database('resources/custom_book.pkl')
        
        status_queue.put("Loading Endgame Tablebases...")
        # Example of loading multiple databases
        self.endgame_db_3v2 = self._load_database('resources/db_3v2_kings.pkl')
        self.endgame_db_4v3 = self._load_database('resources/db_4v3_kings.pkl')
        # ... you would continue this for all your database files
        
        status_queue.put("Finalizing...")
        time.sleep(0.5) # A small delay for visual effect
        # --- END THREADED LOADING ---
        
        self._create_buttons()
        self._update_valid_moves()

    def _load_database(self, file_path):
        """Loads a pickled database file from the resources directory."""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    logger.info(f"Loading database: {file_path}")
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Failed to load database {file_path}: {e}")
        else:
            logger.warning(f"Database file not found: {file_path}")
        return {} # Return an empty dictionary if loading fails

    # --- Button Callbacks and UI Toggles ---

    def _create_buttons(self):
        self.buttons = []
        panel_x = BOARD_SIZE + 10
        button_width = self.screen.get_width() - BOARD_SIZE - 22
        button_height = 30
        # Adjust y_start to make room for all buttons
        y_start = self.screen.get_height() - 50

        button_defs = [
            ("Export to PDN", self.export_to_pdn, y_start),
            ("Dev Mode: OFF", self.toggle_dev_mode, y_start - 35),
            ("Board Nums: OFF", self.toggle_board_numbers, y_start - 70),
            ("Flip Board", self.flip_board, y_start - 105),
            ("Undo Move", self.undo_move, y_start - 140),
            ("Reset Board", self.reset_game, y_start - 175),
            ("Force AI Move", self.force_ai_move, y_start - 210)
        ]
        for text, callback, y_pos in button_defs:
            button = Button(text, (panel_x, y_pos), (button_width, button_height), callback)
            self.buttons.append(button)
        
        depth_btn_y = y_start - 245
        self.buttons.append(Button("-", (panel_x, depth_btn_y), (30, 30), self.decrease_ai_depth))
        self.buttons.append(Button("+", (panel_x + button_width - 30, depth_btn_y), (30, 30), self.increase_ai_depth))
        
        # Store references to buttons that need their text updated
        for btn in self.buttons:
            if "Board Nums" in btn.text: self.board_nums_button = btn
            elif "Dev Mode" in btn.text: self.dev_mode_button = btn

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
    
    # --- Core Game State Management ---

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
        
    def export_to_pdn(self):
        logger.info("Export to PDN button clicked (not implemented).")

    def force_ai_move(self):
        if self.turn == self.player_color and not self.ai_is_thinking:
            logger.info(f"Player forcing AI to calculate move for {constants.PLAYER_NAMES[self.player_color]}")
            self.start_ai_turn(force_color=self.player_color)
    
    # --- AI Turn Management ---

    def start_ai_turn(self, force_color=None):
        if self.ai_thread and self.ai_thread.is_alive(): return
        
        self.ai_is_thinking = True
        self.ai_top_moves = []
        color_to_move = force_color if force_color else self.ai_color
        
        logger.info(f"Starting AI calculation with depth {self.ai_depth}...")
        self.ai_thread = threading.Thread(target=self.run_ai_calculation, args=(color_to_move,), daemon=True)
        self.ai_thread.start()

    def run_ai_calculation(self, color_to_move):
        try:
            # Database lookups would go here before the main search
            # For brevity, this example proceeds directly to the search
            best_move_path, top_moves = get_ai_move_analysis(self.board, self.ai_depth, color_to_move, evaluate_board)
            
            if best_move_path:
                self.positional_score = top_moves[0][0]
                self.ai_top_moves = top_moves
                self.ai_move_queue.put(best_move_path)
            else:
                self.ai_move_queue.put([]) # AI has no moves
        except Exception as e:
            logger.error(f"AI calculation failed: {e}", exc_info=True)
            self.ai_move_queue.put(None) # Signal an error
        finally:
            self.ai_is_thinking = False
            if self.ai_top_moves:
                logger.info(f"AI calculation completed. Best score: {self.positional_score:.2f}")

    # --- Player Turn and Move Logic ---
    
    def _update_valid_moves(self):
        self.valid_moves = self.board.get_all_valid_moves(self.turn)
        if not self.valid_moves and not self.done:
            self.done = True
            winner = RED if self.turn == WHITE else WHITE
            logger.info(f"Game over! {constants.PLAYER_NAMES[winner]} wins as opponent has no moves.")

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
                is_forced_jump = any(val for val in self.valid_moves.get(start_pos, {}).values())
                if not is_forced_jump:
                    self.selected_piece = None
                    self._select(row, col)
        elif (row, col) in self.valid_moves:
            self.selected_piece = self.board.get_piece(row, col)
        else:
            self.selected_piece = None

    def _apply_move_sequence(self, path):
        if not path or len(path) < 2: return

        self.history.append(copy.deepcopy(self.board))
        self.move_history.append(path)

        start_pos, end_pos = path[0], path[-1]
        piece = self.board.get_piece(start_pos[0], start_pos[1])
        
        if piece == 0: return

        is_jump = abs(start_pos[0] - end_pos[0]) == 2
        
        self.board.move(piece, end_pos[0], end_pos[1])

        if is_jump:
            mid_row, mid_col = (start_pos[0] + end_pos[0]) // 2, (start_pos[1] + end_pos[1]) // 2
            jumped_piece = self.board.get_piece(mid_row, mid_col)
            if jumped_piece != 0: self.board._remove([jumped_piece])
            
            more_jumps = self.board._get_moves_for_piece(piece, find_jumps=True)
            if more_jumps:
                self.selected_piece = piece
                self.valid_moves = {(piece.row, piece.col): more_jumps}
                return

        self._change_turn()

    def _handle_click(self, pos):
        if self.turn != self.player_color or self.done: return
        if pos[0] < BOARD_SIZE:
            row, col = pos[1] // SQUARE_SIZE, pos[0] // SQUARE_SIZE
            if self.board_flipped: row, col = ROWS - 1 - row, COLS - 1 - col
            self._select(row, col)
    
    # --- Drawing and Main Loop ---
    def _format_move_path(self, path):
        if not path: return ""
        formatted_moves = []
        for i in range(len(path) - 1):
            start_pos, end_pos = path[i], path[i+1]
            start_acf = constants.COORD_TO_ACF.get(start_pos, '?')
            end_acf = constants.COORD_TO_ACF.get(end_pos, '?')
            separator = 'x' if abs(start_pos[0] - end_pos[0]) == 2 else '-'
            formatted_moves.append(f"{start_acf}{separator}{end_acf}")
        return " ".join(formatted_moves)

    def draw_move_history(self, start_y):
        panel_x = BOARD_SIZE + 10
        y_offset = start_y
        history_font = pygame.font.SysFont('monospace', 14)
        title_surf = self.large_font.render("Move History", True, WHITE)
        self.screen.blit(title_surf, (panel_x, y_offset))
        y_offset += 30
        
        # Draw limited history
        max_moves_to_show = 10
        start_index = max(0, len(self.move_history) - max_moves_to_show * 2)
        if start_index % 2 != 0: start_index -= 1 # Ensure we start on a Red move

        for i in range(start_index, len(self.move_history), 2):
            move_num = (i // 2) + 1
            red_move_str = self._format_move_path(self.move_history[i])
            white_move_str = self._format_move_path(self.move_history[i+1]) if i + 1 < len(self.move_history) else ""
            line = f"{move_num}. {red_move_str:<8} {white_move_str}"
            line_surf = history_font.render(line, True, WHITE)
            self.screen.blit(line_surf, (panel_x, y_offset))
            y_offset += 15

    def draw_info_panel(self):
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - BOARD_SIZE
        pygame.draw.rect(self.screen, constants.COLOR_BG, (panel_x, 0, panel_width, self.screen.get_height()))
        turn_text = self.large_font.render(f"{constants.PLAYER_NAMES[self.turn]}'s Turn", True, constants.COLOR_TEXT)
        self.screen.blit(turn_text, (panel_x + 10, 10))
        if self.ai_is_thinking:
            thinking_text = self.font.render("AI is Thinking...", True, (255, 255, 0))
            self.screen.blit(thinking_text, (panel_x + 10, 35))
        
        self.draw_move_history(start_y=60)
        
        depth_label_text = self.small_font.render(f"AI Depth: {self.ai_depth}", True, WHITE)
        text_rect = depth_label_text.get_rect(center=(panel_x + panel_width / 2, self.screen.get_height() - 280))
        self.screen.blit(depth_label_text, text_rect)
        
        for button in self.buttons:
            button.draw(self.screen)
            
    def draw_dev_panel(self):
        if not self.dev_mode: return
        panel_y = BOARD_SIZE
        panel_height = self.screen.get_height() - BOARD_SIZE
        pygame.draw.rect(self.screen, (10, 10, 30), (0, panel_y, self.screen.get_width(), panel_height))
        title_surf = self.font.render("--- AI Analysis ---", True, WHITE)
        self.screen.blit(title_surf, (10, panel_y + 5))
        y_offset = 30
        for i, (score, path) in enumerate(self.ai_top_moves[:10]): # Limit to top 10 moves
            move_str = self._format_move_path(path)
            line = f"{i+1}. {move_str:<25} Score: {score:.2f}"
            text_surf = self.dev_font.render(line, True, (200, 200, 200))
            self.screen.blit(text_surf, (20, panel_y + y_offset))
            y_offset += 13

    def draw(self):
        self.screen.fill(constants.COLOR_BG) # Fill background first
        self.board.draw(self.screen, self.number_font, self.show_board_numbers, self.board_flipped)
        self.draw_info_panel()
        self.draw_dev_panel()
        
        if self.selected_piece:
            start_pos = (self.selected_piece.row, self.selected_piece.col)
            if start_pos in self.valid_moves:
                for move in self.valid_moves[start_pos]:
                    draw_row, draw_col = (ROWS - 1 - move[0], COLS - 1 - move[1]) if self.board_flipped else move
                    center_pos = (draw_col * SQUARE_SIZE + SQUARE_SIZE // 2, draw_row * SQUARE_SIZE + SQUARE_SIZE // 2)
                    pygame.draw.circle(self.screen, (0, 255, 0), center_pos, 15)
        
        if self.done:
            winner = WHITE if self.turn == RED else RED
            end_text = self.font.render(f"{constants.PLAYER_NAMES[winner]} Wins!", True, (0, 255, 0), constants.COLOR_BG)
            text_rect = end_text.get_rect(center=(BOARD_SIZE / 2, BOARD_SIZE / 2))
            self.screen.blit(end_text, text_rect)

    def update(self):
        try:
            best_move_path = self.ai_move_queue.get_nowait()
            logger.debug(f"GAME UPDATE: Move received from queue: {best_move_path}")
            if isinstance(best_move_path, list) and best_move_path:
                self._apply_move_sequence(best_move_path)
            elif isinstance(best_move_path, list) and not best_move_path:
                logger.info(f"AI ({constants.PLAYER_NAMES[self.ai_color]}) has no valid moves. Player wins!")
                self.done = True
            elif best_move_path is None:
                logger.warning("AI calculation failed and returned None. Turn will be skipped.")
        except queue.Empty:
            pass

        if not self.done and self.turn == self.ai_color and not self.ai_is_thinking:
            self.start_ai_turn()

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                clicked_button = False
                for button in self.buttons:
                    if button.is_clicked(event.pos):
                        button.callback()
                        clicked_button = True
                        break 
                if not clicked_button:
                    self._handle_click(event.pos)

