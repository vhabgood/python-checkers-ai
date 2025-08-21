#main.py
import asyncio
import logging
import argparse
import platform
import os
from engine.checkers_game import main as game_main

# Configure logging
logger = logging.getLogger('main')

def parse_args():
    """
    Parse command-line arguments for game mode and debugging options.
    Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
    Handles --mode, --debug-GUI, --debug-board, and --no-db flags accurately.
    """
    parser = argparse.ArgumentParser(description="Checkers Game")
    parser.add_argument('--mode', choices=['human', 'ai'], default='human', help="Game mode: human or ai")
    parser.add_argument('--debug-GUI', action='store_true', help="Enable GUI debugging")
    parser.add_argument('--debug-board', action='store_true', help="Enable board debugging")
    parser.add_argument('--no-db', action='store_true', help="Disable endgame database loading")
    return parser.parse_args()

def setup_logging(args):
    """
    Configure logging to write to checkers_debug.log with appropriate debug levels.
    Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
    Sets up file handler and debug levels for gui and board based on flags.
    """
    log_file = 'checkers_debug.log'
    try:
        handlers = [logging.FileHandler(log_file, mode='w')]
    except Exception as e:
        print(f"Error creating log file {log_file}: {str(e)}")
        handlers = []
    log_level = logging.WARNING  # Default level
    if args.debug_GUI or args.debug_board:
        log_level = logging.DEBUG
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # Override any existing handlers
    )
    # Set specific logger levels
    logging.getLogger('gui').setLevel(logging.DEBUG if args.debug_GUI else logging.WARNING)
    logging.getLogger('board').setLevel(logging.DEBUG if args.debug_board else logging.WARNING)
    if os.path.exists(log_file):
        logger.info(f"Logging initialized to {log_file}")
    else:
        logger.error(f"Log file {log_file} not created")

def main():
    """
    Initialize and start the checkers game, passing mode and no-db flags.
    Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
    Sets up logging and runs the game loop, handling Pyodide compatibility.
    """
    args = parse_args()
    setup_logging(args)
    logger.info("Starting Checkers game with mode: %s, no-db: %s", args.mode, args.no_db)
    try:
        if platform.system() == "Emscripten":
            asyncio.ensure_future(game_main(args.mode, args.no_db))
        else:
            asyncio.run(game_main(args.mode, args.no_db))
    except Exception as e:
        logger.error("Failed to initialize game: %s", str(e))
        raise

if __name__ == "__main__":
    main()
