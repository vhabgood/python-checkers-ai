#main.py
import asyncio
import logging
import argparse
import platform
from engine.checkers_game import main as game_main

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('checkers_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('main')

def parse_args():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Checkers Game")
    parser.add_argument('--mode', choices=['human', 'ai'], default='human', help="Game mode: human or ai")
    return parser.parse_args()

def main():
    args = parse_args()
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
