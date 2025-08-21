import threading
import time

# --- This file would likely contain your primary AI classes and functions.
# --- The CheckersAI class is modified here to be interruptible.

class CheckersAI:
    """
    A class to handle AI move calculation, designed to be run in a thread.
    The search function is now aware of an interrupt flag.
    """
    def __init__(self, game_state):
        self.game_state = game_state
        # This is a thread-safe flag that can be set to stop the search.
        self.interrupt_flag = threading.Event()
        self.best_move_found = None
        
    def find_best_move(self, depth_limit=10):
        """
        The main AI search function (e.g., Minimax/Alpha-Beta).
        It is designed to be interruptible.
        """
        # --- The following are additions for the interruptible feature ---
        self.interrupt_flag.clear()  # Reset the flag for a new search
        self.best_move_found = None
        # --- End of additions ---
        
        # This is a simplified search loop. In your actual code,
        # you would need to add a check for self.interrupt_flag.is_set()
        # at the start of your recursive function (e.g., at the top of minimax()).
        for current_depth in range(1, depth_limit + 1):
            # --- This is the key check for the interrupt feature ---
            if self.interrupt_flag.is_set():
                print(f"AI search interrupted at depth {current_depth-1}.")
                # Return the best move found *so far*.
                return self.best_move_found
            # --- End of key check ---
            
            print(f"AI is calculating at depth {current_depth}...")
            # Simulate heavy computation. Replace this with your actual
            # search logic.
            time.sleep(1) 
            
            # Simplified logic to find a "best move" at this depth
            valid_moves = self.game_state.get_valid_moves()
            if valid_moves:
                # In your real code, this would be the result of a full
                # minimax search at the current depth.
                self.best_move_found = valid_moves[0]
                
        print("AI search completed normally.")
        return self.best_move_found

# --- Other AI-related functions would be below here ---
# (e.g., minimax, evaluation, etc.)

