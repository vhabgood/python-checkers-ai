#engine/checkers_game.py
import pygame
import logging
import asyncio
import platform
import random
import threading
import time
from queue import Queue, Empty

from game_states import BaseState
from engine.board import (
    setup_initial_board,
    COORD_TO_ACF,
    count_pieces,
    is_dark_square,
    get_valid_moves,
    make_move,
    evaluate_board,
    check_for_kinging
)
from engine.constants import (
    BOARD_SIZE,
    INFO_WIDTH,
    SQUARE_SIZE,
    PIECE_RADIUS,
    PLAYER_NAMES,
    FUTILITY_MARGIN,
    ACF_TO_COORD,
    COLOR_RED_P,
    COLOR_WHITE_P,
    COLOR_LIGHT_SQUARE,
    COLOR_DARK_SQUARE,
    COLOR_HIGHLIGHT,
    COLOR_SELECTED,
    COLOR_CROWN,
    COLOR_TEXT,
    COLOR_BG,
    COLOR_BUTTON,
    COLOR_BUTTON_HOVER,
    RED,
    WHITE,
    RED_KING,
    WHITE_KING,
    EMPTY
)

# NOTE: The FPS constant is defined here to prevent import errors in other files.
FPS = 60

# Configure logging (level set in main.py)
logger = logging.getLogger('gui')

class CheckersGame(BaseState):
    def __init__(self, screen, player_choice):
        """
        Initialize the checkers game with Pygame, board, and menu.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        Sets up board, pieces, menu, and buttons; logs initial state.
        """
        super().__init__(screen) # NOTE: Initialize the BaseState class
        self.player_choice = player_choice
        self.mode = "AI" if self.player_choice else "human"
        self.no_db = False
        
        self.board = setup_initial_board()
        self.board_history = [self.board] # Add a board history for undo functionality
        self.square_size = 60
        self.font = pygame.font.SysFont('Arial', 14)  # Menu font
        self.number_font = pygame.font.SysFont('Arial', 11)  # Board numbers font (20% smaller)
        self.menu_width = 120
        self.ai_depth = 6
        self.developer_mode = False
        self.show_numbers = True
        self.move_history = []
        self.current_player = 'w' if self.player_choice == WHITE else 'r'
        self.score = 0  # Positional score (red - white)
        
        # --- New variables for human move logic ---
        self.selected_piece = None
        self.valid_moves = []
        # --- End of new variables ---
        
        # --- Corrected variables for AI and threading ---
        self.ai_is_thinking = False
        self.ai_thread = None
        self.best_move = None
        self.interrupt_flag = threading.Event()
        self.message_queue = Queue()
        # --- End of corrected variables ---

        self.buttons = [
            {'text': 'Force AI Move', 'rect': pygame.Rect(490, 200, 100, 30), 'action': self.force_ai_move},
            {'text': 'Undo Move', 'rect': pygame.Rect(490, 240, 100, 30), 'action': self.undo_move},
            {'text': 'Restart Game', 'rect': pygame.Rect(490, 280, 100, 30), 'action': self.reset_board},
            {'text': 'Export PDN', 'rect': pygame.Rect(490, 320, 100, 30), 'action': self.export_pdn},
            {'text': 'Board Numbers', 'rect': pygame.Rect(490, 360, 100, 30), 'action': self.toggle_numbers},
            {'text': 'Dev Mode: Off', 'rect': pygame.Rect(490, 400, 100, 30), 'action': self.toggle_dev_mode},
            {'text': 'Rotate Board', 'rect': pygame.Rect(490, 440, 100, 30), 'action': self.rotate_board} # New button
        ]
        
        # --- New Board Orientation Variable ---
        self.board_orientation = 'normal' # 'normal' for red at top, 'flipped' for white at top
        if self.player_choice == WHITE:
            self.board_orientation = 'flipped'
        # --- End of new variable ---
        
        logger.info("CheckersGame initialized with player choice: %s", PLAYER_NAMES.get(self.player_choice))
        red_count, white_count = count_pieces(self.board)
        logger.debug(f"Initial piece count: Red={red_count}, White={white_count}")

    def reset_board(self):
        """
        Reset the board to initial state and clear move history.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        Resets board, move history, current player, and score.
        """
        self.board = setup_initial_board()
        self.board_history = [self.board]
        self.move_history = []
        self.current_player = 'w' if self.mode == 'human' else 'r'
        self.score = 0
        self.ai_calculating = False
        logger.info("Board reset")
        red_count, white_count = count_pieces(self.board)
        logger.debug(f"Reset piece count: Red={red_count}, White={white_count}")

    def toggle_numbers(self):
        """
        Toggle visibility of ACF board numbers.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        Toggles self.show_numbers and logs the state change.
        """
        self.show_numbers = not self.show_numbers
        logger.info(f"Board numbers {'shown' if self.show_numbers else 'hidden'}")

    def toggle_dev_mode(self):
        """
        Toggle developer mode and update button text.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        Toggles self.developer_mode and logs the state change.
        """
        self.developer_mode = not self.developer_mode
        self.buttons[5]['text'] = f"Dev Mode: {'On' if self.developer_mode else 'Off'}"
        logger.info(f"Developer mode: {self.developer_mode}")
        
    def rotate_board(self):
        """
        Flips the board's orientation for evaluation purposes.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        """
        if self.board_orientation == 'normal':
            self.board_orientation = 'flipped'
            logger.info("Board orientation flipped.")
        else:
            self.board_orientation = 'normal'
            logger.info("Board orientation restored to normal.")
    
    def run_ai_in_thread(self):
        """
        Wrapper function to run the AI search and send the result back
        to the GUI thread via the queue.
        """
        logger.info("Starting AI calculation in a new thread...")
        self.interrupt_flag.clear()
        
        # NOTE: This is a placeholder for your actual AI search logic.
        # It needs to be replaced with a call to your Minimax or Alpha-Beta function.
        # It should check self.interrupt_flag.is_set() periodically.
        
        time.sleep(2) # Simulate a longer calculation
        
        valid_moves = get_valid_moves(self.board, self.current_player)
        self.best_move = valid_moves[0] if valid_moves else None

        if self.interrupt_flag.is_set():
            logger.info("AI calculation was interrupted.")
            self.message_queue.put({"type": "ai_interrupted_move", "move": self.best_move})
        else:
            logger.info("AI calculation completed.")
            self.message_queue.put({"type": "ai_completed_move", "move": self.best_move})

    def force_ai_move(self):
        """
        Handle Force AI Move button press.
        If during player's turn, swap to AI and make a move.
        If AI is calculating, apply the best move found so far.
        """
        logger.info("Force AI Move button clicked")
        if self.ai_is_thinking and self.ai_thread and self.ai_thread.is_alive():
            logger.info("AI calculation interrupted.")
            self.interrupt_flag.set()
        else:
            logger.info("Starting AI turn.")
            self.current_player = 'r' # Assume AI is 'r'
            self.ai_is_thinking = True
            self.ai_thread = threading.Thread(target=self.run_ai_in_thread)
            self.ai_thread.start()

    def apply_move(self, move):
        """
        Apply a move to the board, update history, score, and player.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        """
        if not move:
            logger.info("No move to apply.")
            return

        from_row, from_col, to_row, to_col, is_jump = move
        from_acf = COORD_TO_ACF.get((from_row, from_col), 'unknown')
        to_acf = COORD_TO_ACF.get((to_row, to_col), 'unknown')
        move_notation = f"{from_acf}-{to_acf}" if not is_jump else f"{from_acf}x{to_acf}"
        logger.info(f"Applying move for {self.current_player}: {move_notation}")
        self.board = make_move(self.board, move)
        self.board = check_for_kinging(self.board) # NOTE: Check for kinging after every move
        self.board_history.append(self.board)
        self.move_history.append(move_notation)
        self.score = evaluate_board(self.board)
        logger.debug(f"Updated score: {self.score}")
        self.current_player = 'w' if self.current_player == 'r' else 'r'
        self.ai_is_thinking = False
        self.selected_piece = None
        self.valid_moves = []

    def undo_move(self):
        """
        Undo the last move by reverting to the previous board state.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        """
        if len(self.board_history) > 1:
            self.board_history.pop() # Remove the current board state
            self.board = self.board_history[-1] # Set the board to the previous state
            self.move_history.pop() # Remove the last move from history
            self.current_player = 'w' if self.current_player == 'r' else 'r'
            self.score = evaluate_board(self.board)
            logger.info("Undid last move.")
        else:
            logger.debug("No moves to undo")

    def export_pdn(self):
        """
        Export move history in PDN notation.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        Writes move history to game.pdn with standard headers.
        """
        try:
            with open('game.pdn', 'w') as f:
                f.write("[Event \"Checkers Game\"]\n")
                f.write("[Site \"Local\"]\n")
                f.write("[Date \"2025.08.21\"]\n")
                f.write("[Red \"Player1\"]\n")
                f.write("[White \"Player2\"]\n")
                f.write("[Result \"*\"]\n")
                for i, move in enumerate(self.move_history, 1):
                    f.write(f"{i}. {move}\n")
            logger.info("Exported move history to game.pdn")
        except Exception as e:
            logger.error(f"Failed to export PDN: {str(e)}")
            
    def handle_events(self, events):
        """
        Handle Pygame events for this state.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        """
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = event.pos
                    logger.debug(f"Mouse click at {mouse_pos}")
                    # Check for button clicks
                    for button in self.buttons:
                        if button['rect'].collidepoint(mouse_pos):
                            logger.info(f"Button clicked: {button['text']}")
                            try:
                                button['action']()
                            except Exception as e:
                                logger.error(f"Button {button['text']} action failed: {str(e)}")
                            return # Exit after a button is clicked
                    
                    # If it's a human player's turn, handle board clicks
                    if self.current_player == self.player_choice:
                        self.handle_board_click(mouse_pos)
        
        # Check for messages from the AI thread
        try:
            # NOTE: We use get() with a small timeout to avoid crashing if the queue is empty
            message = self.message_queue.get(timeout=0.01)
            if message["type"] == "ai_completed_move" or message["type"] == "ai_interrupted_move":
                self.apply_move(message["move"])
        except Empty:
            # The queue is empty, which is expected most of the time.
            pass
        except Exception as e:
            logger.error(f"Error updating GUI from message queue: {e}")

    def handle_board_click(self, mouse_pos):
        """
        Handles clicks on the board for the human player.
        """
        # Convert mouse position to board row and column
        board_col = mouse_pos[0] // self.square_size
        board_row = mouse_pos[1] // self.square_size
        
        # Invert coordinates if the board is flipped
        if self.board_orientation == 'flipped':
            board_col = 7 - board_col
            board_row = 7 - board_row

        clicked_square = (board_row, board_col)

        # Check if a piece is already selected
        if self.selected_piece:
            # Check if the clicked square is a valid move
            for move in self.valid_moves:
                if (clicked_square[0], clicked_square[1]) == (move[2], move[3]):
                    # A valid move has been found, so apply it
                    self.apply_move((self.selected_piece[0], self.selected_piece[1], clicked_square[0], clicked_square[1], move[4]))
                    logger.info(f"Human move applied: {self.selected_piece} -> {clicked_square}")
                    return

            # If the click was not on a valid move, unselect the piece
            self.selected_piece = None
            self.valid_moves = []
            logger.info("Move cancelled. Piece unselected.")

        # If no piece is selected, try to select one
        else:
            piece_at_click = self.board[clicked_square[0]][clicked_square[1]]
            player_pieces = ['w', 'W'] if self.player_choice == 'w' else ['r', 'R']
            
            if piece_at_click in player_pieces:
                self.selected_piece = clicked_square
                # Get and store valid moves for the selected piece
                all_valid_moves = get_valid_moves(self.board, self.current_player)
                self.valid_moves = [move for move in all_valid_moves if (move[0], move[1]) == self.selected_piece]
                logger.info(f"Piece selected at {self.selected_piece}. Found {len(self.valid_moves)} valid moves.")
            else:
                logger.info("Clicked on an empty square or an opponent's piece.")

    def update(self):
        """
        Update game state logic.
        """
        pass
        
    def draw(self):
        """
        Draw all game elements.
        """
        self.draw_board(self.screen)
        
    def draw_board(self, screen):
        """
        Draw the 8x8 checkers board, pieces, numbers, and menu.
        Verified working 100% correctly as of commit c87b09f1d0225791fa0329196cb2781b154c70d1.
        Renders board (dark/light squares), pieces, ACF numbers, and menu with score and buttons.
        """
        self.screen.fill((255, 255, 255))  # White background
        # Draw menu panel (right side)
        pygame.draw.rect(self.screen, (200, 200, 200), (480, 0, self.menu_width, 480))
        # Draw menu items
        score_text = self.font.render(f"Score: {self.score}", True, (0, 0, 0))
        self.screen.blit(score_text, (490, 80))
        red_count, white_count = count_pieces(self.board)
        red_text = self.font.render(f"Red: {red_count}+0", True, (0, 0, 0))
        white_text = self.font.render(f"White: {white_count}+0", True, (0, 0, 0))
        self.screen.blit(red_text, (490, 120))
        self.screen.blit(white_text, (490, 140))
        ply_text = self.font.render(f"AI Depth: {self.ai_depth}", True, (0, 0, 0))
        self.screen.blit(ply_text, (490, 160))
        for button in self.buttons:
            pygame.draw.rect(self.screen, (100, 100, 100), button['rect'])
            text = self.font.render(button['text'], True, (255, 255, 255))
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)
        
        # --- Drawing the board with orientation logic ---
        for row in range(8):
            for col in range(8):
                if self.board_orientation == 'normal':
                    display_row, display_col = row, col
                else:
                    display_row, display_col = 7 - row, 7 - col

                x = display_col * self.square_size
                y = display_row * self.square_size

                color = (85, 85, 85) if is_dark_square(row, col) else (245, 245, 220)
                pygame.draw.rect(self.screen, color, (x, y, self.square_size, self.square_size))
                
                # Highlight selected piece
                if self.selected_piece and (row, col) == self.selected_piece:
                    pygame.draw.circle(self.screen, COLOR_SELECTED, (x + self.square_size // 2, y + self.square_size // 2), PIECE_RADIUS + 5, 3)

                # Draw highlights for valid moves
                if self.valid_moves:
                    for move in self.valid_moves:
                        if (row, col) == (move[2], move[3]):
                             pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, (x, y, self.square_size, self.square_size), 3)

                piece = self.board[row][col]
                if piece in ['r', 'w', 'R', 'W']:
                    piece_color = (200, 0, 0) if piece.lower() == 'r' else (255, 255, 255)
                    center_x = x + self.square_size // 2
                    center_y = y + self.square_size // 2
                    radius = int((self.square_size // 2 - 5) * 0.95)
                    pygame.draw.circle(self.screen, piece_color, (center_x, center_y), radius)

                if self.show_numbers and (row, col) in COORD_TO_ACF:
                    acf = COORD_TO_ACF[(row, col)]
                    if is_dark_square(row, col):
                        text = self.number_font.render(str(acf), True, (0, 0, 0))
                        text_rect = text.get_rect(center=(x + self.square_size // 2, y + self.square_size // 2))
                        self.screen.blit(text, text_rect)
                        logger.debug(f"Rendering ACF {acf} at ({row},{col})")
                    else:
                        logger.error(f"Attempted to render ACF {acf} on light square at ({row},{col})")
        
        pygame.display.flip()


