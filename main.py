# main.py
import pygame
import logging
import sys
import threading
import queue
import argparse
from engine.checkers_game import CheckersGame
from engine.constants import WIDTH, HEIGHT, COLOR_BG
from game_states import PlayerSelectionScreen, LoadingScreen

# --- Logging Setup ---
# Using a more robust logging configuration
log_format = '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_format)
logger = logging.getLogger('gui')

# --- Argument Parsing ---
def parse_arguments():
    parser = argparse.ArgumentParser(description="Checkers AI")
    parser.add_argument('--debug-board', action='store_true', help='Show board debug numbers.')
    parser.add_argument('--no-db', action='store_true', help='Do not load the endgame databases.')
    return parser.parse_args()

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
        This method runs in a separate thread to load all game resources
        without freezing the UI.
        """
        thread_id = threading.get_ident()
        logger.info(f"DATABASE: Loading thread {thread_id} started.")
        try:
            self.game = CheckersGame(self.screen, player_color_str, self.status_queue, self.args)
            self.states["game"] = self.game
            self.status_queue.put("DONE")
            logger.info(f"DATABASE: Loading thread {thread_id} finished successfully.")
        except Exception as e:
            logger.error(f"DATABASE: Loading thread {thread_id} failed: {e}", exc_info=True)
            self.status_queue.put("Error loading game!")


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
            for event in events:
                if event.type == pygame.QUIT:
                    self.done = True
            
            self.state.handle_events(events, self)
            self.state.update()
            self.transition_state()
            
            self.screen.fill(COLOR_BG)
            self.state.draw()
            pygame.display.update()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    args = parse_arguments()
    app = App(args)
    app.main_loop()

