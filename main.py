# main.py
import pygame
import os
import logging
import sys
import threading
import queue
import argparse
from datetime import datetime

# --- START: LOGGING CONFIGURATION ---
# Create the logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Generate a filename with the current timestamp
log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_checkers_debug.log'
log_filepath = os.path.join('logs', log_filename)

# Set up the basic configuration to log to a file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s',
    filename=log_filepath,
    filemode='w',
    # CRITICAL CHANGE: Force all loggers to use this configuration
    force=True 
)

# Get the root logger and remove any other handlers to ensure no console output
root_logger = logging.getLogger('')
for handler in root_logger.handlers[1:]:
    root_logger.removeHandler(handler) # This removes the default console handler

logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. All output will be sent to: {log_filepath}")

logging.info(f"Logging initialized. Log file at: {log_filepath}")
# You can now get logger instances in other files, and they will inherit this config
logger = logging.getLogger(__name__)
logger.info("Logging configured. Application starting.")
# --- END: LOGGING CONFIGURATION ---
# --- Argument Parsing ---
def parse_arguments():
    parser = argparse.ArgumentParser(description="Checkers AI")
    parser.add_argument('--debug-board', action='store_true', help='Show board debug numbers.')
    parser.add_argument('--no-db', action='store_true', help='Do not load the endgame databases.')
    return parser.parse_args()

# --- 2. NOW IMPORT YOUR GAME MODULES ---
from engine.constants import WIDTH, HEIGHT, FPS, COLOR_BG, WHITE, RED, COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_TEXT
from engine.checkers_game import CheckersGame
from game_states import PlayerSelectionScreen, LoadingScreen

class App:
    """
    The main application class that manages the game window, states, and the main loop.
    """
    def __init__(self, args):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Checkers AI')
        self.clock = pygame.time.Clock()
        self.done = False
        self.args = args
        self.status_queue = queue.Queue()
        self.loading_thread = None
        self.game = None
        
        self.states = {
            "selection": PlayerSelectionScreen(self.screen),
            "loading": LoadingScreen(self.screen, self.status_queue),
            "game": None # Game is initialized via the loading thread
        }
        self.state = self.states["selection"]

    def load_game(self, player_color_str):
        """
        Loads all game resources in a separate thread to avoid freezing the UI.
        This now passes the --no-db flag to the game instance.
        """
        try:
            # --- FIX: Pass the status queue and args to the CheckersGame instance ---
            self.states["game"] = CheckersGame(self.screen, player_color_str, self.status_queue, self.args)
            self.next_state = "game"
            self.status_queue.put("DONE")
        except Exception as e:
            logger.error(f"DATABASE: Loading thread failed: {e}", exc_info=True)
            self.status_queue.put(f"ERROR: {e}")

    def transition_state(self):
        """Handles changing from one game state to another."""
        if self.state.done:
            next_state_name = self.state.next_state
            
            if next_state_name == "loading":
                if self.loading_thread and self.loading_thread.is_alive():
                    logger.warning("Transition to loading requested, but a loading thread is already active. Ignoring.")
                    return

                player_color = self.states["selection"].player_choice
                logger.info(f"Player selected {player_color}, transitioning to LoadingScreen.")
                self.state = self.states["loading"]
                self.state.reset()
                
                # Start the loading process in a separate thread
                self.loading_thread = threading.Thread(target=self.load_game, args=(player_color,), daemon=True)
                self.loading_thread.start()

            elif next_state_name == "game":
                if self.states["game"]:
                    self.state = self.states["game"]
                    logger.info("Transitioned to Game state.")
                else:
                    logger.error("Attempted to transition to game state, but game object is not ready.")
            
            elif next_state_name is None:
                self.done = True # If next state is None, quit the app

    def main_loop(self):
        """The main loop of the application."""
        while not self.done:
            events = pygame.event.get()
            
            # --- FIX: Handle events based on which method the current state has ---
            if self.state:
                if hasattr(self.state, 'handle_events'):
                    # For states like PlayerSelectionScreen that handle the whole list
                    self.state.handle_events(events, self)
                else:
                    # For states like CheckersGame that handle one event at a time
                    for event in events:
                        if event.type == pygame.QUIT:
                            self.done = True
                        if hasattr(self.state, 'handle_event'):
                            self.state.handle_event(event)

            # Check for quit event separately in case a state doesn't handle events
            for event in events:
                if event.type == pygame.QUIT:
                    self.done = True

            if self.state:
                self.state.update()

            self.transition_state()
            
            self.screen.fill(COLOR_BG)
            if self.state:
                self.state.draw()
            pygame.display.update()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    args = parse_arguments()
    app = App(args)
    app.main_loop()

