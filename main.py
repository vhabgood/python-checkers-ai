#main.py
import pygame
import logging
import datetime
import argparse
import sys
import os

# NOTE: The corrected imports for your project structure.
from engine.checkers_game import CheckersGame
from game_states import LoadingScreen, PlayerSelectionScreen
from engine.constants import (
    FPS,
    BOARD_SIZE,
    INFO_WIDTH,
    SQUARE_SIZE,
    PIECE_RADIUS,
    PLAYER_NAMES,
    FUTILITY_MARGIN,
    COORD_TO_ACF,
    ACF_TO_COORD,
    COLOR_RED_P,
    COLOR_WHITE_P,
    COLOR_LIGHT_SQUARE,
    COLOR_DARK_SQUARE,
    COLOR_HIGHLIGHT,
    COLOR_SELECTED,
    COLOR_CROWN,
    COLOR_TEXT,
    COLOR_BG,
    COLOR_BUTTON,
    COLOR_BUTTON_HOVER,
    RED,
    WHITE,
    RED_KING,
    WHITE_KING,
    EMPTY
)

# --- Logging Configuration ---
# NOTE: Restored logging configuration to the main file.
def configure_logging(args):
    """
    Configures logging based on command-line arguments.
    """
    log_level = logging.INFO
    if args.debug_gui or args.debug_board:
        log_level = logging.DEBUG

    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = os.path.join(log_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_checkers_debug.log")
    
    # Define a custom formatter to include the relative path of the caller
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            pathname = record.pathname
            if pathname.startswith(os.getcwd()):
                record.pathname = os.path.relpath(pathname, os.getcwd())
            return super().format(record)

    # File handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(CustomFormatter('%(asctime)s - %(pathname)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s'))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomFormatter('%(name)s - %(levelname)s - %(message)s'))

    # Add handlers to the root logger
    logging.basicConfig(level=log_level, handlers=[file_handler, console_handler])

    # Set logger levels for specific modules
    logging.getLogger('gui').setLevel(logging.INFO if not args.debug_gui else logging.DEBUG)
    logging.getLogger('board').setLevel(logging.INFO if not args.debug_board else logging.DEBUG)


# --- Game States Manager ---
class StateManager:
    def __init__(self, screen):
        self.screen = screen
        self.states = {
            "loading": LoadingScreen(self.screen),
            "player_selection": PlayerSelectionScreen(self.screen),
            "game": None  # This will be initialized after player selection
        }
        self.current_state = self.states["loading"]
        self.running = True

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            events = pygame.event.get()
            
            # Handle state transitions
            if self.current_state.done:
                next_state_name = self.current_state.next_state
                
                # If there is no next state, the game is over.
                if next_state_name is None:
                    # Allow the final 'Game Over' screen to show for a few seconds
                    self.current_state.draw()
                    pygame.display.flip()
                    pygame.time.wait(3000) # Wait 3 seconds
                    self.running = False
                    continue # Skip to next loop iteration to exit cleanly

                if next_state_name == "game":
                    player_choice = self.current_state.player_choice
                    self.states["game"] = CheckersGame(self.screen, player_choice)
                    self.current_state = self.states[next_state_name]
                else:
                    self.current_state = self.states[next_state_name]
            
            if self.current_state is not None:
                self.current_state.handle_events(events)
                self.current_state.update()
                self.current_state.draw()
            
            # Global quit event
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
            
            pygame.display.flip()
            clock.tick(FPS)
            
        pygame.quit()
        
    def quit(self):
        self.running = False

# --- Main execution block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A checkers game with an AI engine.")
    parser.add_argument("--debug-gui", action="store_true", help="Enable debug logging for GUI.")
    parser.add_argument("--debug-board", action="store_true", help="Enable debug logging for board.")
    args = parser.parse_args()

    configure_logging(args)
    
    # Initialize Pygame and the game
    pygame.init()
    window_size = (600, 480)
    screen = pygame.display.set_mode(window_size)
    pygame.display.set_caption("Checkers")
    
    game_manager = StateManager(screen)
    game_manager.run()
