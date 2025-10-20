# run_gauntlet.py
# This script runs a headless "gauntlet" match between two AI versions
# to test their performance from a given set of starting positions (FENs).

import argparse
import logging
import os
from engine.board import Board
from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental
from engine.debug import setup_logging, LOGGERS
from engine.search import initialize_search, get_ai_move_analysis
from engine.egdb import EGDBDriver

# --- Setup ---
logger = logging.getLogger('gameflow')

# --- Main Test Class ---
class HeadlessGame:
    """Simulates a checkers game between two AI engines without a GUI."""
    def __init__(self, fen, player_red_eval, player_white_eval):
        self.board = Board()
        self.board.create_board_from_fen(fen)
        self.players = {'red': {'eval': player_red_eval}, 'white': {'eval': player_white_eval}}
        self.history = [self.board.get_hash()]

    def play_game(self):
        """Plays a full game, returning the winner ('red', 'white', or 'draw')."""
        move_count = 0
        # FIX: Increase the move limit to allow for long endgames
        while move_count < 500:
            if self.board.winner() is not None:
                logger.info(f"Game over. Winner: {self.board.winner().upper()}")
                return self.board.winner()
            
            if self.is_draw():
                logger.info("Game over. Draw by 3-fold repetition.")
                return 'draw'

            current_player_color = self.board.turn
            player = self.players[current_player_color]
            
            _, move_path = get_ai_move_analysis(self.board.copy(), 5, None, player['eval'], self.history)
            
            if not move_path or not move_path[0]:
                winner = 'white' if current_player_color == 'red' else 'red'
                logger.info(f"Game over. No legal moves for {current_player_color}. Winner: {winner.upper()}")
                return winner

            self.board = self.board.apply_move(move_path[0])
            self.history.append(self.board.get_hash())
            move_count += 1
        
        logger.info("Game over. 150 move limit reached. Declaring a draw.")
        return 'draw'


    def is_draw(self):
        """Checks for a draw by 3-fold repetition."""
        for h in set(self.history):
            if self.history.count(h) >= 3:
                return True
        return False

# --- Main Gauntlet Function ---
def run_gauntlet(args):
    """Sets up engines, loads positions, and manages the matches."""
    setup_logging(args)
    db_directory = os.path.abspath("./db")
    egdb_driver = EGDBDriver(db_directory)
    initialize_search(egdb_driver)

    try:
        with open(args.file, 'r') as f:
            positions = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(positions)} starting positions for the gauntlet.")
    except FileNotFoundError:
        logger.error(f"Error: The file '{args.file}' was not found.")
        return

    scores = {'v1': 0, 'v2': 0, 'draws': 0}
    total_games = len(positions) * 2

    for i, fen in enumerate(positions):
        # Game 1: V1 (Red) vs V2 (White)
        logger.info(f"--- Starting Game {i*2 + 1} / {total_games} ---")
        game1 = HeadlessGame(fen, evaluate_board_v1, evaluate_board_v2_experimental)
        winner1 = game1.play_game()
        if winner1 == 'red': scores['v1'] += 1; logger.info("RED (V1) WINS.")
        elif winner1 == 'white': scores['v2'] += 1; logger.info("WHITE (V2) WINS.")
        else: scores['draws'] += 1; logger.info("DRAW.")
        logger.info(f"Score= V1: {scores['v1']} - V2: {scores['v2']} - Draws: {scores['draws']}")

        # Game 2: V2 (Red) vs V1 (White)
        logger.info(f"--- Starting Game {i*2 + 2} / {total_games} ---")
        game2 = HeadlessGame(fen, evaluate_board_v2_experimental, evaluate_board_v1)
        winner2 = game2.play_game()
        if winner2 == 'red': scores['v2'] += 1; logger.info("RED (V2) WINS.")
        elif winner2 == 'white': scores['v1'] += 1; logger.info("WHITE (V1) WINS.")
        else: scores['draws'] += 1; logger.info("DRAW.")
        logger.info(f"Score= V1: {scores['v1']} - V2: {scores['v2']} - Draws: {scores['draws']}")
    
    logger.info("Gauntlet finished.")
    logger.info(f"Final Score: V1 {scores['v1']} - V2 {scores['v2']} - Draws {scores['draws']}")

# --- Script Entry Point ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a gauntlet of checkers games.")
    parser.add_argument('--file', type=str, required=True, help='Path to the file with FEN starting positions.')
    parser.add_argument('--egdb-files-path', type=str, default='db', help='Path to the directory containing EGDB files.')
    
    for name in LOGGERS:
        parser.add_argument(f'--debug-{name}', action='store_true', help=f'Enable DEBUG logging for {name}.')
        
    args = parser.parse_args()
    run_gauntlet(args)


