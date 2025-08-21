# Assuming your main file imports your engine components like this:
# from engine.checkers_game import CheckersGame
# from engine.search import CheckersAI
# and your GUI library (e.g., Pygame, Tkinter)

import threading
import time
from queue import Queue

# --- Assumed Classes from your project ---
# These are simplified for this example.
# Please replace these with your actual classes from your project structure.
# You will also need to import your actual GUI library (e.g., Pygame, Tkinter, etc.).

class Board:
    """Represents the game board state."""
    def __init__(self):
        self.state = "initial"

class CheckersGame:
    """Manages the game state, including player turns and board."""
    def __init__(self):
        self.board = Board()
        self.current_player = "red"  # Could be "red" or "black"
        self.ai_player = "black"

    def make_move(self, move):
        """Simulates making a move on the board."""
        print(f"Game: Making move {move}")
        if self.current_player == "red":
            self.current_player = "black"
        else:
            self.current_player = "red"

    def get_valid_moves(self):
        """Returns a list of dummy valid moves for demonstration."""
        return [("A1", "B2"), ("C3", "D4")]

# --- Assuming the CheckersAI class is imported from engine/search.py ---
# from engine.search import CheckersAI
class CheckersAI:
    """
    A class to handle AI move calculation, designed to be run in a thread.
    (This is a placeholder. You'll use the one from engine/search.py)
    """
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

# --- GUI Controller Class (likely in main.py) ---
class CheckersGUIController:
    """
    Manages the game state and interacts with the GUI.
    This class would have methods called by your GUI buttons.
    """
    def __init__(self):
        self.game = CheckersGame()
        self.ai = CheckersAI(self.game) # Make sure to instantiate your actual AI class
        
        self.ai_is_thinking = False
        self.ai_thread = None
        # Use a Queue for thread-safe communication back to the GUI.
        self.message_queue = Queue()

    def update_gui(self):
        """
        This method would be called periodically by the GUI's main loop
        to check for new messages from the AI thread.
        
        For example, in a Tkinter app you would call this with root.after(100, self.update_gui).
        In Pygame, you would call this in your main game loop.
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
                    # self.gui_buttons["Force AI"].config(state="normal")
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
        This is the method you would link to your button's 'command' attribute.
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
            self.game.current_player = self.ai.ai_player
            self.ai_is_thinking = True
            # Start the AI calculation in a new, non-blocking thread.
            self.ai_thread = threading.Thread(target=self.run_ai_in_thread)
            self.ai_thread.start()
            # Disable the button to prevent multiple presses while the AI is busy.
            # self.gui_buttons["Force AI"].config(state="disabled")

# --- Main execution example (for testing) ---
if __name__ == "__main__":
    controller = CheckersGUIController()
    
    print("Simulating game start...")
    print("\nUser presses 'Force AI' button for the first time.")
    controller.force_ai_move()
    
    time.sleep(2.5)
    
    print("\nUser presses 'Force AI' button again while AI is busy.")
    controller.force_ai_move()
    
    controller.ai_thread.join()
    controller.update_gui()

