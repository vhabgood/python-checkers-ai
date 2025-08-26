# main.py
import pygame
import logging
import datetime
import argparse
import sys
import threading
import os
import queue

from engine.checkers_game import CheckersGame
from game_states import LoadingScreen, PlayerSelectionScreen
from engine.constants import FPS, WIDTH, HEIGHT

def configure_logging(args):
    """Sets up file and console logging based on command-line arguments."""
    log_level = logging.INFO
    if args.debug_gui or args.debug_board:
        log_level = logging.DEBUG
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_filename = os.path.join(log_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_checkers_debug.log")
    
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            pathname = record.pathname
            # This logic makes the path relative for cleaner logs
            if os.getcwd() in pathname:
                record.pathname = os.path.relpath(pathname)
            return super().format(record)

    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(CustomFormatter('%(asctime)s - %(pathname)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s'))
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(CustomFormatter('%(name)s - %(levelname)s - %(message)s'))
    logging.basicConfig(level=log_level, handlers=[file_handler, console_handler])
    logging.getLogger('gui').setLevel(logging.INFO if not args.debug_gui else logging.DEBUG)
    logging.getLogger('board').setLevel(logging.INFO if not args.debug_board else logging.DEBUG)

class StateManager:
    """
    Manages game states with a non-blocking, threaded asset loader.
    This version contains the final, correct logic for the main game loop.
    """
    def __init__(self, screen):
        self.screen = screen
        self.status_queue = queue.Queue() # A queue for thread communication
        self.states = {
            "loading": LoadingScreen(self.screen, self.status_queue),
            "player_selection": PlayerSelectionScreen(self.screen),
            "game": None # The game state is initialized later
        }
        self.current_state_name = "player_selection" # Start at player selection
        self.current_state = self.states[self.current_state_name]
        self.running = True
        self.loading_thread = None
        self.game_instance = None
        self.logger = logging.getLogger('gui')

    def load_game_thread(self, player_choice):
        """This function runs in a separate thread to load game assets."""
        self.logger.info("DATABASE: Loading thread started.")
        try:
            # The CheckersGame class will put status messages on the queue
            self.game_instance = CheckersGame(self.screen, player_choice, self.status_queue)
            # When loading is done, put the final 'done' signal on the queue.
            self.status_queue.put("DONE")
        except Exception as e:
            self.logger.error(f"DATABASE: Failed to load game assets in thread: {e}", exc_info=True)
            self.game_instance = None
            self.status_queue.put("DONE") # Also signal done on failure
        self.logger.info("DATABASE: Loading thread finished.")

    def run(self):
        """The main application loop with corrected thread management."""
        clock = pygame.time.Clock()
        while self.running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            # Let the current state handle its own events and logic
            self.current_state.handle_events(events)
            self.current_state.update()
            self.current_state.draw()

            # Check for state transitions
            if self.current_state.done:
                # --- This is the core logic for switching states ---
                
                # 1. From Player Selection to Loading
                if self.current_state_name == "player_selection":
                    player_choice = self.current_state.player_choice
                    self.logger.info(f"Player selected {player_choice}, transitioning to LoadingScreen.")
                    
                    # Switch to the loading screen
                    self.current_state_name = "loading"
                    self.current_state = self.states["loading"]
                    self.current_state.reset() # Reset loading screen for a new session
                    
                    # Start the background thread to load the game
                    self.loading_thread = threading.Thread(
                        target=self.load_game_thread, 
                        args=(player_choice,), 
                        daemon=True
                    )
                    self.loading_thread.start()
                    self.logger.debug("MAIN: Database loading thread initiated.")

                # 2. From Loading to Game
                elif self.current_state_name == "loading":
                    self.logger.debug("MAIN: Loading complete. Transitioning to game state.")
                    if self.game_instance:
                        self.states["game"] = self.game_instance
                        self.current_state_name = "game"
                        self.current_state = self.states["game"]
                    else:
                        self.logger.critical("Game instance failed to load. Exiting.")
                        self.running = False
                
                # 3. Handle exiting the application
                elif self.current_state.next_state is None:
                    self.running = False
            
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()

# This is the main entry point when the script is run.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A checkers game with an AI engine.")
    parser.add_argument("--debug-gui", action="store_true", help="Enable debug logging for GUI.")
    parser.add_argument("--debug-board", action="store_true", help="Enable debug logging for board.")
    args = parser.parse_args()
    
    configure_logging(args)
    pygame.init()
    window_size = (WIDTH, HEIGHT)
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Checkers")
    
    game_manager = StateManager(screen)
    game_manager.run()

