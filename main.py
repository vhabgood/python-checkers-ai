# main.py
import pygame
import os
import logging
import sys
import argparse
import multiprocessing as mp

from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from game_states import PlayerSelectionScreen
from engine.checkers_game import CheckersGame
from engine.debug import setup_logging, LOGGERS
from engine.egdb import EGDBDriver
from engine import search # Import the whole module

SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

class App:
    def __init__(self, args):
        self.args = args
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Checkers Engine")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # --- FINALIZED INTEGRATION ---
        # 1. Create the driver instance.
        egdb_driver = EGDBDriver(lib_path=args.egdb_lib_path)
        search.initialize_search(egdb_driver)
        # --------------------
        
        # 2. Initialize the C-level database with the path to the .cpr files.
        egdb_driver = EGDBDriver(db_path=args.egdb_files_path)
        search.initialize_search(egdb_driver)
            
        # 3. Pass the configured driver to the search module.
        search.initialize_search(egdb_driver)
        # -----------------------------

        self.states = {
            "player_selection": PlayerSelectionScreen(self.screen),
            "game": CheckersGame(self.screen, None, self.args) # CheckersGame will use the initialized search module
        }
        self.state = self.states["player_selection"]

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            self.state.handle_event(event)

    def update(self):
        self.state.update()
        if self.state.done:
            self._handle_state_transition()

    def draw(self):
        self.state.draw(self.screen)
        pygame.display.flip()

    def _handle_state_transition(self):
        if isinstance(self.state, PlayerSelectionScreen):
            self.state.reset()
            self.state = self.states["game"]
        elif isinstance(self.state, CheckersGame):
            self.state.reset()
            self.state = self.states["player_selection"]


if __name__ == '__main__':
    mp.freeze_support()
    parser = argparse.ArgumentParser(description="A checkers engine with analysis tools.")

    # Logging arguments
    for name in LOGGERS:
        parser.add_argument(f'--debug-{name}', action='store_true', help=f'Enable DEBUG logging for the {name} module.')

    # Engine performance arguments
    parser.add_argument('--depth', type=int, default=5, help='Set the AI search depth for the game.')
    
    # --- NEW ARGUMENT ---
    # This allows you to specify the path to the EGDB file, making your program portable.
    parser.add_argument('--egdb-path', type=str, default=None, help='Path to the checkers_db.so shared library file.')
    # --------------------

    args = parser.parse_args()
    setup_logging(args)

    main_app = App(args)
    main_app.run()

    pygame.quit()
    sys.exit()

