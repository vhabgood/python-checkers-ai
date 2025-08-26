# main.py
import pygame
import logging
import datetime
import argparse
import sys
import threading
import os

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
            if pathname.startswith(os.getcwd()):
                record.pathname = os.path.relpath(pathname, os.getcwd())
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
    Manages the different screens (states) of the application. It now uses a
    separate thread to load game assets to prevent the UI from freezing.
    """
    def __init__(self, screen):
        self.screen = screen
        self.states = {
            "loading": LoadingScreen(self.screen),
            "player_selection": PlayerSelectionScreen(self.screen),
            "game": None
        }
        self.current_state = self.states["loading"]
        self.running = True
        
        # --- THREADING FIX ---
        self.loading_thread = None
        self.game_instance = None # This will hold the loaded CheckersGame object
        # --- END FIX ---

    def load_game_thread(self, player_choice):
        """
        This function runs in a separate thread. It creates the CheckersGame
        instance, which performs the heavy lifting of loading databases.
        """
        loading_screen = self.states["loading"]
        try:
            # This is the long-running operation that was freezing the game
            self.game_instance = CheckersGame(self.screen, player_choice, loading_screen)
        except Exception as e:
            logger.error(f"Failed to load game assets in thread: {e}")
            self.game_instance = None # Signal that loading failed

    def run(self):
        """The main application loop, now with simplified and correct thread handling."""
        clock = pygame.time.Clock()
        while self.running:
            events = pygame.event.get()

            # --- State Transition Logic ---
            if self.current_state.done:
                next_state_name = self.current_state.next_state
                if next_state_name is None:
                    self.running = False
                    continue
                
                if next_state_name == "game":
                    # If the game instance has been loaded by the thread, switch to it.
                    if self.game_instance:
                        self.states["game"] = self.game_instance
                        self.current_state = self.states["game"]
                        self.loading_thread = None # Clear the completed thread
                        if self.game_instance is None:
                            logger.critical("Game instance failed to load. Exiting.")
                            self.running = False
                    # If the loading thread hasn't started yet, start it.
                    elif self.loading_thread is None:
                        player_choice = self.states["player_selection"].player_choice
                        self.states["loading"].done = False
                        self.current_state = self.states["loading"]
                        self.loading_thread = threading.Thread(target=self.load_game_thread, args=(player_choice,), daemon=True)
                        self.loading_thread.start()
                else:
                    self.current_state = self.states[next_state_name]
            # --- Main Update and Draw Logic ---
            # This simplified logic works for all states now.
            # The loading screen will update its message from its queue.
            self.current_state.handle_events(events)
            self.current_state.update()
            self.current_state.draw()

            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
            
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()

# This is the main entry point when the script is run.
if __name__ == "__main__":
    # Set up command-line argument parsing for debugging
    parser = argparse.ArgumentParser(description="A checkers game with an AI engine.")
    parser.add_argument("--debug-gui", action="store_true", help="Enable debug logging for GUI.")
    parser.add_argument("--debug-board", action="store_true", help="Enable debug logging for board.")
    args = parser.parse_args()
    
    # Configure logging and initialize Pygame
    configure_logging(args)
    pygame.init()
    window_size = (WIDTH, HEIGHT)
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Checkers")
    
    # Create the state manager and run the game
    game_manager = StateManager(screen)
    game_manager.run()
