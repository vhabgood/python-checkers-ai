#main.py
import asyncio
import logging
import argparse
import platform
from engine.checkers_game import main as game_main

# Configure logging
logger = logging.getLogger('main')

def parse_args():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Checkers Game")
    parser.add_argument('--mode', choices=['human', 'ai'], default='human', help="Game mode: human or ai")
    parser.add_argument('--debug-GUI', action='store_true', help="Enable GUI debugging")
    parser.add_argument('--debug-board', action='store_true', help="Enable board debugging")
    return parser.parse_args()

def setup_logging(args):
    # Configure logging to file only
    handlers = [logging.FileHandler('checkers_debug.log', mode='w')]
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

def main():
    args = parse_args()
    setup_logging(args)
    logger.info("Starting Checkers game with mode: %s", args.mode)
    try:
        if platform.system() == "Emscripten":
            asyncio.ensure_future(game_main(args.mode))
        else:
            asyncio.run(game_main(args.mode))
    except Exception as e:
        logger.error("Failed to initialize game: %s", str(e))
        raise

if __name__ == "__main__":
    main()
