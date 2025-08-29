# engine/checkers_game.py
import pygame
import logging
import threading
import queue
import copy
import time
import pickle
import os
import glob
from .board import Board
from .constants import SQUARE_SIZE, RED, WHITE, BOARD_SIZE, ROWS, COLS, DEFAULT_AI_DEPTH
import engine.constants as constants
from game_states import Button
from engine.search import get_ai_move_analysis
from engine.evaluation import evaluate_board

logger = logging.getLogger('gui')

class CheckersGame:
    """
    The main game state manager. It handles the game loop, player input,
    AI turn management via threading, and drawing everything to the screen.
    """
    def __init__(self, screen, player_color_str, status_queue, args): # Add args here
        logger.critical("--- NEW CHECKERS GAME INSTANCE CREATED ---")
        self.screen = screen
        self.args = args # Store args
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
        self.game_started = False  # <-- ADD THIS LINE
        # --- DATABASE LOADING ---
        status_queue.put("Loading Opening Book...")
        self.opening_book = self._load_database('resources/custom_book.pkl')
        
        # --- CONDITIONAL LOADING ---
        self.endgame_db = {} # Default to empty
        if not self.args.no_db:
            status_queue.put("Loading Endgame Tablebases...")
            self.endgame_db = self._load_and_merge_databases(status_queue)
        else:
            logger.warning("Skipping endgame database load due to --no-db flag.")
        
        status_queue.put("Finalizing...")
        time.sleep(0.5)
        
        self._create_buttons()
        self._update_valid_moves()

    def _load_database(self, file_path):
        """Loads a single pickled database file."""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    logger.info(f"Loading database: {file_path}")
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Failed to load database {file_path}: {e}")
        else:
            logger.warning(f"Database file not found: {file_path}")
        return {}

    def _load_and_merge_databases(self, status_queue):
        """
        Finds all 'db_*.pkl' files, loads them, and merges them into a
        single master endgame database dictionary.
        """
        master_db = {}
        db_path = 'resources'
        db_files = glob.glob(os.path.join(db_path, 'db_*.pkl'))
        
        for i, file_path in enumerate(db_files):
            filename = os.path.basename(file_path)
            status_queue.put(f"Loading DB ({i+1}/{len(db_files)}): {filename}")
            db_content = self._load_database(file_path)
            if db_content:
                master_db.update(db_content)
        
        logger.info(f"Successfully merged {len(db_files)} endgame databases into a single table with {len(master_db)} positions.")
        return master_db

    def _create_buttons(self):
        self.buttons = []
        panel_x = BOARD_SIZE + 10
        button_width = self.screen.get_width() - BOARD_SIZE - 22
        button_height = 30
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
            self.buttons.append(Button(text, (panel_x, y_pos), (button_width, button_height), callback))
        
        depth_btn_y = y_start - 245
        self.buttons.append(Button("-", (panel_x, depth_btn_y), (30, 30), self.decrease_ai_depth))
        self.buttons.append(Button("+", (panel_x + button_width - 30, depth_btn_y), (30, 30), self.increase_ai_depth))
        
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
    
    def reset_game(self):
        self.board = Board()
        self.turn = self.board.turn
        self.done = False
        self.history = []
        self.move_history = []
        self.ai_top_moves = []
        self.ai_is_thinking = False
        self._update_valid_moves()

    def undo_move(self):
        if self.ai_is_thinking or self.done or not self.history:
            return
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
        if self.turn == self.player_color and not self.ai_is_thinking and not self.done:
            logger.info(f"Player forcing AI to calculate move for {constants.PLAYER_NAMES[self.player_color]}")
            self.start_ai_turn(force_color=self.turn)
    
    def start_ai_turn(self, force_color=None):
        if self.ai_is_thinking: 
            logger.warning("AI is already thinking, start_ai_turn call ignored.")
            return
        
        self.ai_is_thinking = True
        self.ai_top_moves = []
        color_to_move = force_color if force_color else self.ai_color
        
        logger.info(f"Starting AI calculation with depth {self.ai_depth} for {constants.PLAYER_NAMES[color_to_move]}...")
        self.ai_thread = threading.Thread(target=self.run_ai_calculation, args=(color_to_move,), daemon=True)
        self.ai_thread.start()

    def run_ai_calculation(self, color_to_move): # Remove is_display_only
        try:
            best_move_path, top_moves = get_ai_move_analysis(self.board, self.ai_depth, color_to_move, evaluate_board)
            
            if best_move_path:
                self.positional_score = top_moves[0][0]
                self.ai_top_moves = top_moves
                self.ai_move_queue.put(best_move_path)
            else:
                self.ai_move_queue.put([])
        except Exception as e:
            logger.error(f"AI calculation failed: {e}", exc_info=True)
            self.ai_move_queue.put(None)
        finally:
            if self.ai_top_moves:
                logger.info(f"AI calculation completed. Best score: {self.positional_score:.2f}")

    def _update_valid_moves(self):
        winner = self.board.winner()
        if winner:
            self.done = True
            logger.info(f"Game over! {constants.PLAYER_NAMES[winner]} wins.")
            self.valid_moves = {}
        else:
            self.valid_moves = self.board.get_all_valid_moves(self.turn)
    
    def _change_turn(self):
        logger.debug(f"Changing turn from {constants.PLAYER_NAMES[self.turn]}...")
        self.selected_piece = None
        self.turn = RED if self.turn == WHITE else WHITE
        self.board.turn = self.turn
        self.ai_is_thinking = False
        self._update_valid_moves()   
        logger.debug(f"...turn is now {constants.PLAYER_NAMES[self.turn]}.")

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
        logger.debug(f"Applying move sequence: {self._format_move_path(path)}")
        if not path or len(path) < 2:
            return

        self.history.append(copy.deepcopy(self.board))
        self.move_history.append(path)

        piece = self.board.get_piece(path[0][0], path[0][1])
        if piece == 0:
            logger.warning(f"Attempted to move a piece from an empty square: {path[0]}")
            return

        # --- START: THE DEFINITIVE FIX ---

        # First, determine if the move being made is a jump.
        # A turn can only continue if the move itself was a jump.
        is_a_jump_move = abs(path[0][0] - path[1][0]) == 2

        # Apply all steps in the path (this handles both slides and multi-jumps correctly)
        for i in range(len(path) - 1):
            start_pos = path[i]
            end_pos = path[i+1]
            
            self.board.move(piece, end_pos[0], end_pos[1])
            
            # If it was a jump, remove the captured piece
            if abs(start_pos[0] - end_pos[0]) == 2:
                mid_row = (start_pos[0] + end_pos[0]) // 2
                mid_col = (start_pos[1] + end_pos[1]) // 2
                jumped_piece = self.board.get_piece(mid_row, mid_col)
                if jumped_piece != 0:
                    self.board._remove([jumped_piece])

        # After the move, ONLY check for more jumps IF the move just made was a jump.
        if is_a_jump_move:
            final_pos_piece = self.board.get_piece(path[-1][0], path[-1][1])
            if final_pos_piece != 0:
                more_jumps = self.board._get_moves_for_piece(final_pos_piece, find_jumps=True)
                if more_jumps:
                    logger.debug("Multi-jump detected. Turn will not change yet.")
                    self.selected_piece = final_pos_piece
                    self.valid_moves = {(final_pos_piece.row, final_pos_piece.col): more_jumps}
                    return # Exit without changing turn to allow the user/AI to continue the jump.
        
        # If it wasn't a jump move, or if no more jumps are available, the turn MUST end.
        logger.debug("Move sequence complete. Changing turn.")
        self._change_turn()

        # --- END: THE DEFINITIVE FIX ---
    def _handle_click(self, pos):
        if self.done or self.turn != self.player_color: return
        
        if pos[0] < BOARD_SIZE:
            row, col = pos[1] // SQUARE_SIZE, pos[0] // SQUARE_SIZE
            if self.board_flipped: row, col = ROWS - 1 - row, COLS - 1 - col
            self._select(row, col)
    
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
        
        max_moves_to_show = 10
        start_index = max(0, len(self.move_history) - max_moves_to_show * 2)
        if start_index % 2 != 0: start_index -= 1

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
        
        if self.done:
            winner_color = WHITE if self.turn == RED else RED
            turn_text_str = f"{constants.PLAYER_NAMES[winner_color]} Wins!"
        else:
            turn_text_str = f"{constants.PLAYER_NAMES[self.turn]}'s Turn"

        turn_text = self.large_font.render(turn_text_str, True, constants.COLOR_TEXT)
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
        # --- DEBUG TRAP: FUNCTION ENTRY ---
        # This log will appear every frame, confirming the function is being called.
        logger.debug("DRAW_DEV: --- DEV PANEL DRAW START ---")

        # Step 1: Check if Dev Mode is active. If not, the function does nothing.
        if not self.dev_mode:
            logger.debug("DRAW_DEV: Dev mode is OFF. Aborting draw.")
            return

        # Step 2: Define the panel's area and draw its dark background.
        panel_y = BOARD_SIZE
        panel_height = self.screen.get_height() - BOARD_SIZE
        pygame.draw.rect(self.screen, (10, 10, 30), (0, panel_y, self.screen.get_width(), panel_height))
        
        # Step 3: Draw the title text "--- AI Analysis ---".
        title_surf = self.font.render("--- AI Analysis ---", True, WHITE)
        self.screen.blit(title_surf, (10, panel_y + 5))
        
        # --- DEBUG TRAP: DATA CHECK ---
        # The critical check. Does the self.ai_top_moves list have any data?
        # This list is populated by the AI's search function *only* during the AI's turn.
        if not self.ai_top_moves:
            # If the list is empty, the panel should be blank. This is expected on the player's turn.
            logger.debug("DRAW_DEV: self.ai_top_moves is EMPTY. Panel will be blank.")
            return

        # --- DEBUG TRAP: DATA CONTENT ---
        # If we have data, log the turn state and how many lines we are about to draw.
        current_turn_color = "White" if self.turn == WHITE else "Red"
        logger.debug(f"DRAW_DEV: Turn is currently {current_turn_color}. Found {len(self.ai_top_moves)} analysis lines to render.")
        
        y_offset = 30
        for i, (score, path) in enumerate(self.ai_top_moves[:10]):
            # Step 5a: Format the move path to ACF notation (e.g., "9-14").
            move_str = self._format_move_path(path)
            
            # Step 5b: Create the full text line.
            line = f"{i+1}. {move_str:<25} Score: {score:.2f}"
            
            # --- DEBUG TRAP: LINE-BY-LINE CONTENT ---
            # Log each line of text exactly as it's about to be drawn.
            logger.debug(f"DRAW_DEV: Rendering line {i+1}: '{line}'")
            
            # Step 5c: Render and draw the text onto the screen.
            text_surf = self.dev_font.render(line, True, (200, 200, 200))
            self.screen.blit(text_surf, (20, panel_y + y_offset))
            
            y_offset += 13
        
        logger.debug("DRAW_DEV: --- DEV PANEL DRAW END ---")

    def draw(self):
        self.screen.fill(constants.COLOR_BG)
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
        
    def handle_events(self, events, app=None):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked_button = False
                for button in self.buttons:
                    if button.is_clicked(event.pos):
                        button.callback()
                        clicked_button = True
                        break 
                if not clicked_button:
                    self._handle_click(event.pos)
                    
    def update(self):
        if self.done:
            return

        # If it's the AI's turn and it's not already thinking, start the calculation.
        if self.turn == self.ai_color and not self.ai_is_thinking:
            self.start_ai_turn()

        # Check if the AI has finished thinking and placed a move in the queue.
        try:
            best_move_path = self.ai_move_queue.get_nowait()
            
            if best_move_path:
                logger.info(f"UPDATE: Move received from AI queue: {self._format_move_path(best_move_path)}. Applying.")
                self._apply_move_sequence(best_move_path)
            elif best_move_path is None:
                logger.warning("AI calculation returned None. Forfeiting turn.")
                self._change_turn()
            else: # An empty list means the AI has no moves
                logger.warning("AI returned an empty list, meaning it is blocked. Forfeiting turn.")
                self._change_turn()

        except queue.Empty:
            # This is the normal state; do nothing and wait for the AI or player.
            pass

