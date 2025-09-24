# main.py
import pygame
import os
import logging
import sys
import argparse
import copy
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import multiprocessing as mp

# Your engine and game state imports
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from game_states import PlayerSelectionScreen
from engine.checkers_game import CheckersGame
from engine.debug import setup_logging, LOGGERS # Assuming you have this from other files

SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

# (Your existing setup_logging function is fine and can remain here)
# ...

class App:
    """
    The main application class that manages the game states and the main loop.
    """
    def __init__(self, args):
        self.args = args
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Checkers Engine")
        self.clock = pygame.time.Clock()
        self.running = True
        self.states = {
            "player_selection": PlayerSelectionScreen(self.screen),
            "game": CheckersGame(self.screen, None, self.args)
        }
        self.state = self.states["player_selection"]

    def run(self):
        """The main game loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60) # Limit frame rate to 60 FPS

    def handle_events(self):
        """Processes all Pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            self.state.handle_event(event)

    def update(self):
        """Updates the current game state."""
        self.state.update()
        if self.state.done:
            self._handle_state_transition()

    def draw(self):
        """Draws the current game state to the screen."""
        self.state.draw(self.screen)
        pygame.display.flip()

    def _handle_state_transition(self):
        """Switches between game states."""
        if isinstance(self.state, PlayerSelectionScreen):
            # Transition from menu to game
            self.state.reset()
            self.state = self.states["game"]
        elif isinstance(self.state, CheckersGame):
            # Transition from game back to menu (you can customize this)
            self.state.reset()
            self.state = self.states["player_selection"]


if __name__ == '__main__':
    mp.freeze_support()
    parser = argparse.ArgumentParser(description="A checkers engine with analysis tools.")

    # Add your existing parser arguments for logging
    for name in LOGGERS:
        parser.add_argument(f'--debug-{name}', action='store_true', help=f'Enable DEBUG logging for the {name} module.')

    # --- THIS IS THE FIX ---
    # Add the missing --depth argument that the game engine expects
    parser.add_argument('--depth', type=int, default=5, help='Set the AI search depth for the game.')
    # -----------------------

    args = parser.parse_args()
    setup_logging(args)

    main_app = App(args)
    main_app.run()

    pygame.quit()
    sys.exit()
