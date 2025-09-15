# main.py
import pygame
import os
import logging
import sys
import argparse
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import multiprocessing as mp

from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT
SCREEN_SIZE=(SCREEN_WIDTH,SCREEN_HEIGHT)

# --- Logging (unchanged) ---
if not os.path.exists('logs'): os.makedirs('logs')
log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_checkers_debug.log'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)-10s - %(levelname)-8s - %(message)s', filename=os.path.join('logs', log_filename), filemode='w', force=True)
logger = logging.getLogger(__name__)


# ======================================================================================
# --- File Dialog Process (Correct and Unchanged) ---
# ======================================================================================
def open_file_dialog_process(conn, title, filetypes):
    """
    A generic function to run a file dialog in a separate process.
    """
    try:
        root = tk.Tk()
        root.withdraw()
        filepath = filedialog.askopenfilename(title=title, filetypes=filetypes)
        conn.send(filepath if filepath else "")
    except Exception as e:
        conn.send("")
    finally:
        conn.close()

# --- Imports ---
from game_states import PlayerSelectionScreen
from engine.checkers_game import CheckersGame

class App:
    def __init__(self, args):
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Checkers AI")
        self.clock = pygame.time.Clock()
        self.args = args
        self.done = False

        self.states = { "player_selection": PlayerSelectionScreen(self.screen), "game": None }
        self.state = self.states["player_selection"]
        self.dialog_process = None
        self.dialog_pipe_parent_conn = None
        self.is_waiting_for_dialog = False
        self.dialog_load_type = None # NEW: To track which load was requested

    def main_loop(self):
        while not self.done:
            # --- Handle File Dialog Requests ---
            if not self.is_waiting_for_dialog:
                if hasattr(self.state, 'wants_to_load_pdn') and self.state.wants_to_load_pdn:
                    self.state.wants_to_load_pdn = False
                    self.dialog_load_type = 'pdn' # Track request type
                    title, types = "Select a PDN file", (("PDN files", "*.pdn"), ("All files", "*.*"))
                    self.dialog_pipe_parent_conn, child_conn = mp.Pipe()
                    self.dialog_process = mp.Process(target=open_file_dialog_process, args=(child_conn, title, types))
                    self.dialog_process.start()
                    self.is_waiting_for_dialog = True

                elif hasattr(self.state, 'wants_to_load_fen') and self.state.wants_to_load_fen:
                    self.state.wants_to_load_fen = False
                    self.dialog_load_type = 'fen' # Track request type
                    title, types = "Select a FEN text file", (("Text files", "*.txt"), ("All files", "*.*"))
                    self.dialog_pipe_parent_conn, child_conn = mp.Pipe()
                    self.dialog_process = mp.Process(target=open_file_dialog_process, args=(child_conn, title, types))
                    self.dialog_process.start()
                    self.is_waiting_for_dialog = True
            
            # --- Check for Dialog Results ---
            if self.is_waiting_for_dialog and self.dialog_pipe_parent_conn.poll():
                filepath = self.dialog_pipe_parent_conn.recv()
                if filepath:
                    # --- REWRITTEN: Use the tracked type to call the correct function ---
                    if self.dialog_load_type == 'pdn' and hasattr(self.state, 'load_pdn_from_file'):
                        self.state.load_pdn_from_file(filepath)
                    elif self.dialog_load_type == 'fen' and hasattr(self.state, 'load_fen_from_file'):
                        self.state.load_fen_from_file(filepath)
                
                # Cleanup
                self.dialog_process.join()
                self.dialog_pipe_parent_conn.close()
                self.is_waiting_for_dialog = False
                self.dialog_load_type = None

            # --- Event Loop ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.done = True
                if not self.is_waiting_for_dialog and hasattr(self.state, 'handle_event'):
                    self.state.handle_event(event)
            
            # --- State Updates and Drawing ---
            if self.state:
                if hasattr(self.state, 'update'): self.state.update()
                if hasattr(self.state, 'draw'): self.state.draw(self.screen)

            # --- State Transitions ---
            if self.state.done:
                if isinstance(self.state, PlayerSelectionScreen):
                    configs = self.state.player_configs
                    if configs:
                        self.state = CheckersGame(self.screen, None, self.args, configs["red"], configs["white"])
                        self.states["player_selection"].reset()
                elif isinstance(self.state, CheckersGame):
                    self.state = self.states["player_selection"]
                    self.state.reset()

            pygame.display.update()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    mp.freeze_support()
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    app = App(args)
    app.main_loop()


