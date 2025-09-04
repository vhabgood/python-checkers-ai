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
import multiprocessing as mp

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

# --- NEW: Function to run the dialog in a separate process ---
def open_file_dialog_process(conn):
    """
    This function runs in a separate process. It opens the file dialog
    and sends the selected path back to the main process via a pipe.
    """
    try:
        root = tk.Tk()
        root.withdraw()
        filepath = filedialog.askopenfilename(
            title="Select a PDN file",
            filetypes=(("PDN files", "*.pdn"), ("All files", "*.*"))
        )
        conn.send(filepath)
    except Exception as e:
        # Send back an error or None if something goes wrong
        conn.send(None)
    finally:
        conn.close()

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

        # --- NEW: State for managing the dialog process ---
        self.dialog_process = None
        self.dialog_pipe_parent_conn = None
        self.is_waiting_for_dialog = False

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
                player_color = self.states["player_selection"].player_choice
                self.state = self.states["loading"]
                self.state.reset()
                self.loading_thread = threading.Thread(target=self.load_game, args=(player_color,), daemon=True)
                self.loading_thread.start()
            elif next_state_name == "game":
                if self.states["game"]: self.state = self.states["game"]
                else: logger.error("Attempted to transition to game state, but game object is not ready.")
            elif next_state_name is None: self.done = True

    def main_loop(self):
        """The main loop of the application."""
        while not self.done:
            # --- MODIFIED: Handle PDN loading with a separate process ---
            if hasattr(self.state, 'wants_to_load_pdn') and self.state.wants_to_load_pdn and not self.is_waiting_for_dialog:
                self.state.wants_to_load_pdn = False
                logger.info("MAIN_LOOP: Starting file dialog process.")
                self.dialog_pipe_parent_conn, child_conn = mp.Pipe()
                self.dialog_process = mp.Process(target=open_file_dialog_process, args=(child_conn,))
                self.dialog_process.start()
                self.is_waiting_for_dialog = True

            # --- NEW: Non-blocking check for the dialog result ---
            if self.is_waiting_for_dialog:
                if self.dialog_pipe_parent_conn.poll():
                    filepath = self.dialog_pipe_parent_conn.recv()
                    logger.info(f"MAIN_LOOP: Received '{filepath}' from dialog process.")
                    if filepath:
                        self.state.load_pdn_from_file(filepath)
                    
                    # Clean up the process
                    self.dialog_process.join()
                    self.dialog_pipe_parent_conn.close()
                    self.is_waiting_for_dialog = False
                    self.dialog_process = None
                    self.dialog_pipe_parent_conn = None

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT: self.done = True
            
            # Prevent handling game events while dialog is (supposedly) open
            if not self.is_waiting_for_dialog:
                if hasattr(self.state, 'handle_events'): self.state.handle_events(events, self)
                elif hasattr(self.state, 'handle_event'):
                    for event in events: self.state.handle_event(event)

            if self.state:
                self.state.update()
                self.state.draw()

            self.transition_state()
            
            pygame.display.update()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    # Required for multiprocessing on some platforms
    mp.freeze_support()
    # It's safer to use 'fork' on Linux if available
    try:
        mp.set_start_method('fork')
    except RuntimeError:
        pass
    
    args = parse_arguments()
    app = App(args)
    app.main_loop()
