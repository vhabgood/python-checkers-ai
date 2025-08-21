# Assuming this code is being added to a GUI Controller or a main game file.
# You will need to import your existing classes (CheckersGame, etc.)
# and your GUI framework (e.g., Tkinter, Pygame).

import pygame
import threading
import time
from queue import Queue

# NOTE: The corrected imports for your project structure.
from engine.checkers_game import CheckersGame
from engine.board import (
    setup_initial_board,
    make_move,
    get_valid_moves,
    count_pieces
)
from engine.search import CheckersAI
from engine.constants import (
    BOARD_SIZE,
    INFO_WIDTH,
    SQUARE_SIZE,
    PIECE_RADIUS,
    PLAYER_NAMES,
    FUTILITY_MARGIN,
    COORD_TO_ACF,
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

# --- Main Class (from your repository) ---
class Checkers:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        # NOTE: Your constants file doesn't have FPS. Let's use a standard value.
        self.FPS = pygame.time.Clock()
        self.fps_value = 60 # You can adjust this value as needed.
        
        # --- This is the key change to fix the AttributeError ---
        initial_board_state = setup_initial_board()
        self.game = CheckersGame(self.screen)
        self.game.board = initial_board_state
        # --- End of key change ---

        self.ai = CheckersAI(self.game)

        # --- New variables for AI and threading ---
        self.ai_is_thinking = False
        self.ai_thread = None
        self.message_queue = Queue()

    def _draw(self, board):
        # This function likely needs to be updated to handle the board as a data structure
        # instead of a class object.
        # For now, we will assume your game.draw() method handles this.
        # board.draw(self.screen)
        pygame.display.update()

    # --- New methods for AI and button logic ---
    def update_gui(self):
        """
        This method checks the message queue for new messages from the AI thread.
        It should be called periodically in your main game loop.
        """
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                print(f"GUI received message: {message}")
                if message["type"] == "ai_move":
                    # Call the move function with the game's current board and the new move.
                    self.game.board = make_move(self.game.board, message["move"])
                    # Now you would need to tell your game to update the visual board
                    # to reflect the new state. This would likely involve a draw call.
                    self.ai_is_thinking = False
                    
                    # Update a GUI button's state, e.g., enable it again.
                    # You will need to have a reference to your button object here.
        except Exception as e:
            print(f"Error updating GUI: {e}")

    def run_ai_in_thread(self):
        """
        Wrapper function to run the AI search and send the result back
        to the GUI thread via the queue.
        """
        print("Starting AI calculation in a new thread...")
        best_move = self.ai.find_best_move()
        self.message_queue.put({"type": "ai_move", "move": best_move})

    def force_ai_move(self):
        """
        This function handles both scenarios for the Force AI button.
        """
        # Scenario 1: AI is currently thinking (search thread is active)
        if self.ai_is_thinking and self.ai_thread and self.ai_thread.is_alive():
            print("Force AI button pressed: Interrupting AI search.")
            # Set the interrupt flag to tell the AI to stop.
            self.ai.interrupt_flag.set()
        # Scenario 2: AI is not thinking, start a new turn for it
        else:
            print("Force AI button pressed: Starting AI turn.")
            # Change the current player to the AI.
            self.game.current_player = self.game.ai_player
            self.ai_is_thinking = True
            # Start the AI calculation in a new, non-blocking thread.
            self.ai_thread = threading.Thread(target=self.run_ai_in_thread)
            self.ai_thread.start()
            # Disable the button to prevent multiple presses while the AI is busy.
            # You would need a reference to the button object to do this.

    def main(self, window_width, window_height):
        # Your original main game loop.
        
        while self.running:
            self.FPS.tick(self.fps_value)
            self.game.draw()
            
            # --- This is where you would call the new update_gui method ---
            self.update_gui()
            
            # This is where your original event loop would be.
            # You would need to add a line to call self.force_ai_move()
            # when the button is clicked.
            # For example:
            # if event.type == pygame.MOUSEBUTTONDOWN and force_ai_button.rect.collidepoint(event.pos):
            #    self.force_ai_move()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.game.handle_click(pygame.mouse.get_pos())

            self._draw(self.game.board)

# --- Your main execution block ---
if __name__ == "__main__":
    window_size = (640, 640)
    pygame.init()
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Checkers")

    checkers = Checkers(screen)
    checkers.main(window_size[0], window_size[1])

    pygame.quit()

