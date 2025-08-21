# Assuming this code is being added to a GUI Controller or a main game file.
# You will need to import your existing classes (Board, CheckersGame, etc.)
# and your GUI framework (e.g., Tkinter, Pygame).

import pygame
import threading
import time
from queue import Queue

# NOTE: The correct import is CheckersGame, not Checkers.
from engine.checkers_game import CheckersGame
from engine.board import Board
from engine.search import CheckersAI
from engine.constants import Constants

# This is a simplified AI for demonstration purposes.
# The real one is the one you would be importing.
class CheckersAI:
    def __init__(self, game_state):
        self.game_state = game_state
        self.interrupt_flag = threading.Event()
        self.best_move_found = None
        
    def find_best_move(self, depth_limit=10):
        self.interrupt_flag.clear()
        self.best_move_found = None
        for current_depth in range(1, depth_limit + 1):
            if self.interrupt_flag.is_set():
                return self.best_move_found
            time.sleep(1) 
            valid_moves = self.game_state.get_valid_moves()
            if valid_moves:
                self.best_move_found = valid_moves[0]
        return self.best_move_found

# --- Main Class (from your repository) ---
class Checkers:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.FPS = pygame.time.Clock()
        
        # You will need to import your actual CheckersGame and CheckersAI classes
        self.game = CheckersGame(self.screen)
        self.ai = CheckersAI(self.game)

        # --- New variables for AI and threading ---
        self.ai_is_thinking = False
        self.ai_thread = None
        self.message_queue = Queue()

    def _draw(self, board):
        board.draw(self.screen)
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
                    self.game.make_move(message["move"])
                    # You would also update the GUI board here to reflect the move.
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
        self.game.setup()
        
        while self.running:
            self.FPS.tick(Constants.FPS)
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

