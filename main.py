# main.py
import pygame
import os
import logging
import sys
import argparse
from datetime import datetime
import multiprocessing as mp

from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT
SCREEN_SIZE=(SCREEN_WIDTH,SCREEN_HEIGHT)

# --- Logging (unchanged) ---
if not os.path.exists('logs'): os.makedirs('logs')
log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_checkers_debug.log'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)-10s - %(levelname)-8s - %(message)s', filename=os.path.join('logs', log_filename), filemode='w', force=True)
logger = logging.getLogger(__name__)

# --- Imports ---
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

        # The status_queue is needed for the LoadingScreen
        self.status_queue = mp.Queue() 

        self.states = {
            "player_selection": PlayerSelectionScreen(self.screen),
            "loading": LoadingScreen(self.screen, self.status_queue),
            "game": None
        }
        self.state = self.states["player_selection"]

    def transition_to_game(self):
        """Creates and transitions to the main game state."""
        configs = self.states["player_selection"].player_configs
        if configs:
            self.states["game"] = CheckersGame(self.screen, self.status_queue, self.args, configs["red"], configs["white"])
            self.state = self.states["game"]
        else:
            logger.error("Attempted to transition to game, but no player configuration was set.")

    def main_loop(self):
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.done = True
                
                if hasattr(self.state, 'handle_event'):
                    self.state.handle_event(event)

            if hasattr(self.state, 'update'):
                self.state.update()

            if self.state.done:
                if isinstance(self.state, PlayerSelectionScreen):
                    self.transition_to_game()
                elif isinstance(self.state, CheckersGame):
                    self.state = self.states["player_selection"]
                    self.state.reset()

            if hasattr(self.state, 'draw'):
                # --- CRITICAL FIX HERE ---
                # Pass the self.screen object to the state's draw method.
                self.state.draw(self.screen)

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


