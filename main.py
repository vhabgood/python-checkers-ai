# main.py
import pygame
import os
import logging
import sys
import threading
import queue
import argparse
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT
SCREEN_SIZE=(SCREEN_WIDTH,SCREEN_HEIGHT)
# --- Logging Configuration ---
if not os.path.exists('logs'):
    os.makedirs('logs')
log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_checkers_debug.log'
log_filepath = os.path.join('logs', log_filename)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s',
    filename=log_filepath,
    filemode='w',
    force=True
)
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. All output will be sent to: {log_filepath}")

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="A checkers AI program.")
    parser.add_argument('--debug-board', action='store_true', help='Enable detailed board and AI logging.')
    return parser.parse_args()

# Import game states and game logic
from game_states import PlayerSelectionScreen, LoadingScreen
from engine.checkers_game import CheckersGame

class App:
    def __init__(self, args):
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Checkers AI")
        self.clock = pygame.time.Clock()
        self.args = args
        self.done = False

        self.status_queue = queue.Queue()
        self.states = {
            "player_selection": PlayerSelectionScreen(self.screen),
            "loading": LoadingScreen(self.screen, self.status_queue),
            "game": None
        }
        self.state = self.states["player_selection"]
        self.loading_thread = None

    def load_game(self, player_color_str):
        """Initializes the game state and connects to the SQLite database."""
        try:
            self.states["game"] = CheckersGame(self.screen, player_color_str, self.status_queue, self.args)
            self.status_queue.put("DONE")
        except Exception as e:
            logger.error(f"GAME_LOADING: Loading thread failed: {e}", exc_info=True)
            self.status_queue.put(f"ERROR: {e}")

    def transition_state(self):
        if self.state.done:
            next_state_name = self.state.next_state
            if next_state_name == "loading":
                # Correctly get the player_choice string from the selection screen
                player_color = self.states["player_selection"].player_choice
                self.state = self.states["loading"]
                self.state.reset()
                self.loading_thread = threading.Thread(target=self.load_game, args=(player_color,), daemon=True)
                self.loading_thread.start()
            elif next_state_name == "game":
                if self.states["game"]:
                    self.state = self.states["game"]
                else:
                    logger.error("Attempted to transition to game state, but game object is not ready.")
            elif next_state_name is None:
                self.done = True

    def main_loop(self):
        """The main loop of the application."""
        while not self.done:
            events = pygame.event.get()

            # Handle PDN loading request from the main thread
            if hasattr(self.state, 'wants_to_load_pdn') and self.state.wants_to_load_pdn:
                # --- DEBUG LOG 1 ---
                logger.debug("MAIN_LOOP: PDN load requested. Creating temporary Tkinter root.")
                root = tk.Tk()
                root.withdraw() # Hide the main Tkinter window

                # --- DEBUG LOG 2 ---
                logger.debug("MAIN_LOOP: Tkinter root created. Opening file dialog now.")
                filepath = filedialog.askopenfilename(
                    title="Select a PDN file",
                    filetypes=(("PDN files", "*.pdn"), ("All files", "*.*"))
                )
                # --- DEBUG LOG 3 ---
                logger.debug(f"MAIN_LOOP: File dialog closed. Filepath selected: '{filepath}'")

                root.destroy()
                # --- DEBUG LOG 4 ---
                logger.debug("MAIN_LOOP: Tkinter root destroyed.")

                if filepath:
                    logger.info(f"MAIN_LOOP: Valid filepath received. Passing to game state for loading.")
                    self.state.load_pdn_from_file(filepath)

                self.state.wants_to_load_pdn = False


            for event in events:
                if event.type == pygame.QUIT:
                    self.done = True

            # Unified event handling
            if hasattr(self.state, 'handle_events'):
                self.state.handle_events(events, self)
            elif hasattr(self.state, 'handle_event'):
                for event in events:
                    self.state.handle_event(event)

            # Update and draw current state
            if self.state:
                self.state.update()
                self.state.draw()

            self.transition_state()

            pygame.display.update()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    args = parse_arguments()
    app = App(args)
    app.main_loop()
