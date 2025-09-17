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

# --- REFINED: Logging Configuration ---
def setup_logging(eval_log_enabled):
    """Configures the main debug logger and the special evaluation logger."""
    if not os.path.exists('logs'): os.makedirs('logs')
    
    # Main debug log
    log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_checkers_debug.log'
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)-10s - %(levelname)-8s - %(message)s', filename=os.path.join('logs', log_filename), filemode='w', force=True)
    
    # --- NEW: Dedicated logger for evaluation details ---
    if eval_log_enabled:
        eval_logger = logging.getLogger('eval_detail')
        eval_logger.setLevel(logging.INFO)
        # Use a different handler to avoid conflicting with the basic config
        eval_log_handler = logging.FileHandler('evaluation_log.csv', mode='w')
        eval_logger.addHandler(eval_log_handler)
        # Write the header for the CSV file
        eval_logger.info("Engine,FEN,FinalScore,Material,Positional,Blockade,FirstKing,Mobility,Advancement,Simplification")

logger = logging.getLogger(__name__)

# --- The rest of the file is based on your latest provided version ---
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
        self.dialog_load_type = None

    def main_loop(self):
        while not self.done:
            self._handle_dialog_requests()
            self._check_for_dialog_results()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.done = True
                if not self.is_waiting_for_dialog and hasattr(self.state, 'handle_event'):
                    self.state.handle_event(event)
            
            if self.state:
                if hasattr(self.state, 'update'): self.state.update()
                if hasattr(self.state, 'draw'): self.state.draw(self.screen)

            if self.state.done:
                self._handle_state_transition()

            pygame.display.update()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()

    def _handle_dialog_requests(self):
        if self.is_waiting_for_dialog: return
        
        if hasattr(self.state, 'wants_to_load_pdn') and self.state.wants_to_load_pdn:
            self.state.wants_to_load_pdn = False; self.dialog_load_type = 'pdn'
            self._launch_file_dialog("Select a PDN file", (("PDN files", "*.pdn"),))
        elif hasattr(self.state, 'wants_to_load_fen') and self.state.wants_to_load_fen:
            self.state.wants_to_load_fen = False; self.dialog_load_type = 'fen'
            self._launch_file_dialog("Select a FEN text file", (("Text files", "*.txt"),))

    def _check_for_dialog_results(self):
        if self.is_waiting_for_dialog and self.dialog_pipe_parent_conn.poll():
            filepath = self.dialog_pipe_parent_conn.recv()
            if filepath:
                if self.dialog_load_type == 'fen' and hasattr(self.state, 'load_fen_from_file'):
                    self.state.load_fen_from_file(filepath)
            
            self.dialog_process.join(); self.dialog_pipe_parent_conn.close()
            self.is_waiting_for_dialog = False; self.dialog_load_type = None

    def _handle_state_transition(self):
        if isinstance(self.state, PlayerSelectionScreen):
            self.state = CheckersGame(self.screen, None, self.args)
        elif isinstance(self.state, CheckersGame):
            self.state = self.states["player_selection"]
            self.state.reset()

    def _launch_file_dialog(self, title, types):
        self.dialog_pipe_parent_conn, child_conn = mp.Pipe()
        self.dialog_process = mp.Process(target=open_file_dialog_process, args=(child_conn, title, types))
        self.dialog_process.start()
        self.is_waiting_for_dialog = True

def open_file_dialog_process(conn, title, filetypes):
    try:
        root = tk.Tk(); root.withdraw()
        filepath = filedialog.askopenfilename(title=title, filetypes=filetypes)
        conn.send(filepath if filepath else "")
    except Exception: conn.send("")
    finally: conn.close()

if __name__ == '__main__':
    mp.freeze_support()
    parser = argparse.ArgumentParser(description="A checkers engine with analysis tools.")
    parser.add_argument('--eval-log', action='store_true', help='Enable detailed evaluation logging to evaluation_log.csv')
    args = parser.parse_args()
    
    setup_logging(args.eval_log)
    
    app = App(args)
    app.main_loop()


