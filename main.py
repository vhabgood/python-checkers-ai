# main.py
"""
The main entry point for the checkers game application.
Initializes Pygame, manages game states, and handles the main game loop.
"""
import pygame
import logging
import datetime
import argparse
import sys
import os

from engine.checkers_game import CheckersGame
from game_states import LoadingScreen, PlayerSelectionScreen
from engine.constants import FPS

def configure_logging(args):
    """
    Configures logging to output to both a file and the console.
    Sets the logging level based on command-line arguments.
    """
    log_level = logging.INFO
    if args.debug_gui or args.debug_board:
        log_level = logging.DEBUG

    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = os.path.join(log_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_checkers_debug.log")
    
    class CustomFormatter(logging.Formatter):
        """Custom formatter to show relative paths in log messages."""
        def format(self, record):
            pathname = record.pathname
            if pathname.startswith(os.getcwd()):
                record.pathname = os.path.relpath(pathname, os.getcwd())
            return super().format(record)

    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(CustomFormatter('%(asctime)s - %(pathname)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s'))
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomFormatter('%(name)s - %(levelname)s - %(message)s'))

    logging.basicConfig(level=log_level, handlers=[file_handler, console_handler])

    logging.getLogger('gui').setLevel(logging.INFO if not args.debug_gui else logging.DEBUG)
    logging.getLogger('board').setLevel(logging.INFO if not args.debug_board else logging.DEBUG)

class StateManager:
    """
    Manages the different states of the game (e.g., loading, menu, gameplay).
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

    def run(self):
        """
        The main game loop. Handles event processing, state updates,
        drawing, and state transitions.
        """
        clock = pygame.time.Clock()
        while self.running:
            events = pygame.event.get()
            
            # Handle state transitions when a state signals it is 'done'.
            if self.current_state.done:
                next_state_name = self.current_state.next_state
                
                if next_state_name is None:
                    # If the game is over, show the final screen for a moment then exit.
                    self.current_state.draw()
                    pygame.display.flip()
                    pygame.time.wait(3000)
                    self.running = False
                    continue

                if next_state_name == "game":
                    # Special case: Initialize the main game state with the player's choice.
                    player_choice = self.current_state.player_choice
                    self.states["game"] = CheckersGame(self.screen, player_choice)
                
                self.current_state = self.states[next_state_name]
            
            # Delegate event handling, updates, and drawing to the current state.
            if self.current_state is not None:
                self.current_state.handle_events(events)
                self.current_state.update()
                self.current_state.draw()
            
            # Global quit event.
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
            
            pygame.display.flip()
            clock.tick(FPS)
            
        pygame.quit()
        
# --- Main execution block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A checkers game with an AI engine.")
    parser.add_argument("--debug-gui", action="store_true", help="Enable debug logging for GUI.")
    parser.add_argument("--debug-board", action="store_true", help="Enable debug logging for board.")
    args = parser.parse_args()

    configure_logging(args)
    
    pygame.init()
    window_size = (600, 480)
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Checkers")
    
    game_manager = StateManager(screen)
    game_manager.run()
