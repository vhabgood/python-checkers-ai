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
    """
    The main game state manager. It handles the game loop, player input,
    AI turn management via threading, and drawing everything to the screen.
    """
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
        # Font setup
        self.large_font = pygame.font.SysFont(None, 22) 
        self.font = pygame.font.SysFont(None, 20) #was 24
        self.small_font = pygame.font.SysFont(None, 18)
        self.dev_font = pygame.font.SysFont('monospace', 12) #was 16
        self.number_font = pygame.font.SysFont(None, 18)
        
        # AI threading and communication setup
        self.ai_move_queue = queue.Queue()
        self.ai_analysis_queue = queue.Queue()
        self.ai_thread = None
        self.ai_is_thinking = False
        self.positional_score = 0.0
        self.ai_top_moves = []
        self.ai_depth = DEFAULT_AI_DEPTH
        # Initialize UI elements
        self._create_buttons()
        # Calculate the first set of valid moves
        self._update_valid_moves()
    
    # --- Button Callbacks and UI Toggles ---

    def _create_buttons(self):
        self.buttons = []
        panel_x = BOARD_SIZE + 10
        button_width = self.screen.get_width() - BOARD_SIZE - 22
        
        # --- LAYOUT FIX ---
        button_height = 30 # Was 32
        # Start the buttons much higher to make room for the dev panel
        y_start = self.screen.get_height() - 150 # Was - 50

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
        for btn in self.buttons:
            if "Board Nums" in btn.text: self.board_nums_button = btn
            elif "Dev Mode" in btn.text: self.dev_mode_button = btn

    def toggle_board_numbers(self):
        """Toggles the visibility of the board square numbers."""
        self.show_board_numbers = not self.show_board_numbers
        self.board_nums_button.text = f"Board Nums: {'ON' if self.show_board_numbers else 'OFF'}"
        
    def toggle_dev_mode(self):
        """Toggles the visibility of the developer/AI analysis panel."""
        self.dev_mode = not self.dev_mode
        self.dev_mode_button.text = f"Dev Mode: {'ON' if self.dev_mode else 'OFF'}"
        
    def increase_ai_depth(self):
        """Increases the AI search depth."""
        if self.ai_depth < 9: self.ai_depth += 1
        logger.info(f"AI depth set to {self.ai_depth}")
        
    def decrease_ai_depth(self):
        """Decreases the AI search depth."""
        if self.ai_depth > 5: self.ai_depth -= 1
        logger.info(f"AI depth set to {self.ai_depth}")
    
    # --- Core Game State Management ---

    def reset_game(self):
        """Resets the board and game state to the beginning."""
        self.board = Board()
        self.turn = self.board.turn
        self.done = False
        self.history = []
        self.move_history = []
        self.ai_top_moves = []
        self._update_valid_moves()

    def undo_move(self):
        """Reverts the game state to the previous turn using the history."""
        if not self.history: return
        self.board = self.history.pop()
        if self.move_history: self.move_history.pop()
        self.turn = self.board.turn
        self.ai_top_moves = []
        self._update_valid_moves()

    def flip_board(self):
        """Flips the board's orientation."""
        self.board_flipped = not self.board_flipped
        
    def export_to_pdn(self):
        """Placeholder for exporting the game to Portable Draughts Notation."""
        logger.info("Export to PDN button clicked (not implemented).")

    def force_ai_move(self):
        """
        Allows the player to have the AI make a move for them on their turn.
        Does nothing if it's already the AI's turn or the AI is thinking.
        """
        if self.turn == self.player_color and not self.ai_is_thinking:
            logger.info(f"Player forcing AI to calculate move for {constants.PLAYER_NAMES[self.player_color]}")
            self.start_ai_turn(force_color=self.player_color)
    
    # --- AI Turn Management ---

    def start_ai_turn(self, force_color=None):
        """
        Initiates the AI's turn by starting a new thread for the calculation.
        This keeps the GUI from freezing while the AI is thinking.
        """
        if self.ai_thread and self.ai_thread.is_alive(): return
        
        self.ai_is_thinking = True
        self.ai_top_moves = []
        color_to_move = force_color if force_color else self.ai_color
        
        logger.info(f"Starting AI calculation with depth {self.ai_depth}...")
        # Run the calculation in a separate thread
        self.ai_thread = threading.Thread(target=self.run_ai_calculation, args=(color_to_move,), daemon=True)
        self.ai_thread.start()

    def run_ai_calculation(self, color_to_move):
        """
        This function is executed in a separate thread. It calls the search
        algorithm and puts the result (the best move path) onto a queue
        for the main game loop to retrieve.
        """
        try:
            best_move_path, top_moves = get_ai_move_analysis(self.board, self.ai_depth, color_to_move, evaluate_board)
            
            if best_move_path:
                self.positional_score = top_moves[0][0]
                self.ai_top_moves = top_moves
                self.ai_move_queue.put(best_move_path)
            else:
                self.ai_move_queue.put([]) # Put an empty list if no moves are found
        except Exception as e:
            logger.error(f"AI calculation failed: {e}")
            self.ai_move_queue.put(None) # Put None to signal an error
        finally:
            self.ai_is_thinking = False
            if self.ai_top_moves:
                logger.info(f"AI calculation completed. Best score: {self.positional_score:.2f}")

    # --- Player Turn and Move Logic ---
    
    def _update_valid_moves(self):
        """
        Calculates all valid moves for the current turn using the new authoritative method.
        """
        # FIX: Changed to call the new, correct function name
        self.valid_moves = self.board.get_all_valid_moves(self.turn)
        
        if not self.valid_moves and not self.done:
            self.done = True
            winner = RED if self.turn == WHITE else WHITE
            logger.info(f"Game over! {constants.PLAYER_NAMES[winner]} wins as opponent has no moves.")

    def _change_turn(self):
        """Swaps the turn to the other player."""
        self.selected_piece = None
        self.turn = RED if self.turn == WHITE else WHITE
        self.board.turn = self.turn
        self._update_valid_moves()

    def _select(self, row, col):
        """
        Handles piece selection and move execution, now preventing deselection
        during a mandatory multi-jump.
        """
        if self.selected_piece:
            start_pos = (self.selected_piece.row, self.selected_piece.col)
            if start_pos in self.valid_moves and (row, col) in self.valid_moves[start_pos]:
                self._apply_move_sequence([start_pos, (row, col)])
            else:
                # CRITICAL FIX: Check if the player is in a forced jump sequence.
                # If they are, do not allow them to deselect the piece.
                is_forced_jump = False
                if self.valid_moves and start_pos in self.valid_moves:
                    # Check if the current valid moves are jumps (i.e., have captured pieces)
                    if any(val for val in self.valid_moves[start_pos].values()):
                        is_forced_jump = True
                
                if not is_forced_jump:
                    self.selected_piece = None
                    self._select(row, col) # Attempt to select a new piece

        elif (row, col) in self.valid_moves:
            self.selected_piece = self.board.get_piece(row, col)
        else:
            self.selected_piece = None

    def _apply_move_sequence(self, path):
        """
        Executes a move sequence and now correctly handles multi-jumps for the player.
        """
        if not path or len(path) < 2:
            logger.warning("Attempted to apply an invalid move sequence.")
            return

        self.history.append(copy.deepcopy(self.board))
        self.move_history.append(path)

        start_pos = path[0]
        end_pos = path[-1]
        piece = self.board.get_piece(start_pos[0], start_pos[1])
        
        if piece == 0:
            logger.error(f"Attempted to move a piece from an empty square at {start_pos}.")
            return

        # Determine if the move was a jump and get captured pieces
        jumped_pieces = []
        is_jump = abs(start_pos[0] - end_pos[0]) == 2

        if is_jump:
            mid_row = (start_pos[0] + end_pos[0]) // 2
            mid_col = (start_pos[1] + end_pos[1]) // 2
            jumped_piece = self.board.get_piece(mid_row, mid_col)
            if jumped_piece != 0:
                jumped_pieces.append(jumped_piece)
        
        # Move the piece and remove any captured pieces
        self.board.move(piece, end_pos[0], end_pos[1])
        if jumped_pieces:
            self.board._remove(jumped_pieces)

        # CRITICAL FIX: After a jump, check if more jumps are possible.
        if is_jump:
            # The piece object itself has been moved, so we use its new coordinates.
            more_jumps = self.board._get_moves_for_piece(piece, find_jumps=True)
            if more_jumps:
                # If more jumps exist, do NOT change the turn.
                # Instead, lock the selection to this piece and update valid moves.
                self.selected_piece = piece
                self.valid_moves = {(piece.row, piece.col): more_jumps}
                return  # End the function here, skipping _change_turn()

        # If it wasn't a jump or no more jumps are available, change the turn.
        self._change_turn()

    def _handle_click(self, pos):
        """Handles a mouse click on the game board."""
        # Ignore clicks if it's not the player's turn or the game is over
        if self.turn != self.player_color or self.done: return
        # Check if the click was within the board area
        if pos[0] < BOARD_SIZE:
            # Convert pixel coordinates to board row/col
            row, col = pos[1] // SQUARE_SIZE, pos[0] // SQUARE_SIZE
            if self.board_flipped: row, col = ROWS - 1 - row, COLS - 1 - col
            self._select(row, col)
    
    # --- Drawing and Main Loop ---
    def _format_move_path(self, path):
        """
        Formats a move path into a readable string. It can now handle both
        simple single-turn paths and long multi-turn analytical paths.
        """
        if not path:
            return ""

        # This will hold the formatted moves, like "11-15", "22x15", etc.
        formatted_moves = []
        
        # We process the path two coordinates at a time to form each move
        i = 0
        while i < len(path) - 1:
            start_pos = path[i]
            end_pos = path[i+1]
            
            # Convert coordinates to algebraic notation (e.g., 11, 15)
            start_acf = constants.COORD_TO_ACF.get(start_pos, '?')
            end_acf = constants.COORD_TO_ACF.get(end_pos, '?')
            
            # Determine if it's a jump or a slide
            separator = 'x' if abs(start_pos[0] - end_pos[0]) == 2 else '-'
            
            formatted_moves.append(f"{start_acf}{separator}{end_acf}")
            
            # Check for multi-jumps within a single turn
            # If the next "start" is the same as our "end", it's a continuation
            if i + 2 < len(path) and path[i+1] == path[i+2]:
                i += 1 # Skip the duplicate coordinate
            else:
                i += 2 # Move to the next pair

        return " ".join(formatted_moves)

    def draw_move_history(self, start_y):
        """Draws the formatted move history panel."""
        panel_x = BOARD_SIZE + 10
        y_offset = start_y
        history_font = pygame.font.SysFont('monospace', 14)
        title_surf = self.large_font.render("Move History", True, WHITE)
        self.screen.blit(title_surf, (panel_x, y_offset))
        y_offset += 30
        header = history_font.render("Red     White", True, WHITE)
        self.screen.blit(header, (panel_x, y_offset))
        y_offset += 20
        # Only show the last 10 moves
        start_index = max(0, len(self.move_history) - 10)
        if start_index % 2 != 0: start_index -=1
        for i in range(start_index, len(self.move_history), 2):
            move_num = (i // 2) + 1
            red_path = self.move_history[i]
            red_move_str = self._format_move_path(red_path)
            
            white_move_str = ""
            if i + 1 < len(self.move_history):
                white_path = self.move_history[i+1]
                white_move_str = self._format_move_path(white_path)
            
            line = f"{move_num}. {red_move_str:<8} {white_move_str}"
            line_surf = history_font.render(line, True, WHITE)
            self.screen.blit(line_surf, (panel_x, y_offset))
            y_offset += 15

    def draw_info_panel(self):
        """Draws the main side panel with turn info and buttons."""
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - BOARD_SIZE
        pygame.draw.rect(self.screen, constants.COLOR_BG, (panel_x, 0, panel_width, self.screen.get_height()))
        turn_text = self.large_font.render(f"{constants.PLAYER_NAMES[self.turn]}'s Turn", True, constants.COLOR_TEXT)
        self.screen.blit(turn_text, (panel_x + 10, 20))
        if self.ai_is_thinking:
            thinking_text = self.font.render("AI is Thinking...", True, (255, 255, 0))
            self.screen.blit(thinking_text, (panel_x + 10, 45))
        self.draw_move_history(start_y=40)
        depth_label_text = self.small_font.render(f"AI Depth: {self.ai_depth}", True, WHITE)
        text_rect = depth_label_text.get_rect(center=(panel_x + panel_width / 2, self.screen.get_height() - 380))
        self.screen.blit(depth_label_text, text_rect)
        for button in self.buttons:
            button.draw(self.screen)
            
    def draw_dev_panel(self):
        if not self.dev_mode: return
        panel_y = BOARD_SIZE
        panel_height = self.screen.get_height() - BOARD_SIZE
        pygame.draw.rect(self.screen, (10, 10, 30), (0, panel_y, BOARD_SIZE+220, panel_height))
        title_surf = self.font.render("--- AI Analysis ---", True, WHITE)
        self.screen.blit(title_surf, (10, panel_y + 5))
        y_offset = 30
        for i, (score, path) in enumerate(self.ai_top_moves):
            move_str = self._format_move_path(path)
            line = f"{i+1}. {move_str:<25} Score: {score:.2f}"
            text_surf = self.dev_font.render(line, True, (200, 200, 200))
            self.screen.blit(text_surf, (20, panel_y + y_offset))
            # --- LAYOUT FIX ---
            y_offset += 13 # Was 15

    def draw(self):
        """The main draw call for the entire game screen."""
        self.board.draw(self.screen, self.number_font, self.show_board_numbers, self.board_flipped)
        self.draw_info_panel()
        self.draw_dev_panel()
        # Highlight valid moves for the selected piece
        if self.selected_piece:
            start_pos = (self.selected_piece.row, self.selected_piece.col)
            if start_pos in self.valid_moves:
                for move in self.valid_moves[start_pos]:
                    draw_row, draw_col = (ROWS - 1 - move[0], COLS - 1 - move[1]) if self.board_flipped else (move[0], move[1])
                    pygame.draw.circle(self.screen, (0, 255, 0), (draw_col * SQUARE_SIZE + SQUARE_SIZE // 2, draw_row * SQUARE_SIZE + SQUARE_SIZE // 2), 15)
        # Display the winner text when the game is over
        if self.done:
            winner = WHITE if self.turn == RED else RED
            end_text = self.large_font.render(f"{constants.PLAYER_NAMES[winner]} Wins!", True, (0, 255, 0), constants.COLOR_BG)
            text_rect = end_text.get_rect(center=(BOARD_SIZE / 2, self.screen.get_height() / 2))
            self.screen.blit(end_text, text_rect)

    def update(self):
        """
        The main logic loop for the game state. It handles retrieving AI moves
        from the queue and automatically starting the AI's turn.
        """
        try:
            best_move_path = self.ai_move_queue.get_nowait()
            # Case 1: AI returned a valid move
            # --- DEBUGGING TEXT ---
            # This confirms what move was retrieved from the AI's thread.
            logger.debug(f"GAME UPDATE: Move received from queue: {best_move_path}")
            # --- END DEBUGGING TEXT ---
            if best_move_path and isinstance(best_move_path, list):
                self._apply_move_sequence(best_move_path)
            # Case 2: AI returned an empty list, meaning it has no moves and loses
            elif isinstance(best_move_path, list) and not best_move_path:
                logger.info(f"AI ({constants.PLAYER_NAMES[self.ai_color]}) has no valid moves. Player wins!")
                self.done = True
            # Case 3: AI returned None, indicating an error
            elif best_move_path is None:
                logger.warning("AI calculation failed and returned None. Turn will be skipped.")
        except queue.Empty:
            # This is normal, means AI is thinking or it's the player's turn
            pass

        # Automatically start the AI's turn if it's their turn and they are not already thinking
        if not self.done and self.turn == self.ai_color and not self.ai_is_thinking:
            self.start_ai_turn()

    def handle_events(self, events):
        """Handles all user input events, like clicks and key presses."""
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Check if a button was clicked first
                for button in self.buttons:
                    if button.is_clicked(event.pos):
                        button.callback()
                        break 
                else: # If no button was clicked, handle it as a board click
                    self._handle_click(event.pos)
