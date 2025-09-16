# run_gauntlet.py
import logging
import sqlite3
import time
import os
from datetime import datetime

# --- Import Core Engine Components ---
from engine.board import Board
from engine.constants import RED, WHITE
from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental
from engine.search import get_ai_move_analysis

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class HeadlessGame:
    """
    A class to simulate a single game of checkers between two AI engines
    without any graphical user interface.
    """
    def __init__(self, starting_fen, red_player_config, white_player_config, ai_depth=7):
        """
        Initializes the game from a FEN string.
        """
        self.board = Board()
        self.board.create_board_from_fen(starting_fen)
        
        self.players = {
            RED: red_player_config,
            WHITE: white_player_config
        }
        self.ai_depth = ai_depth
        
        # Draw detection
        self.position_counts = {}
        self._update_position_counts(self.board)

    def _get_board_key(self, board_obj):
        """Creates a hashable key representing the board state for draw detection."""
        return (tuple(map(tuple, board_obj.board)), board_obj.turn)

    def _update_position_counts(self, board_obj):
        """Updates the count for the current board position."""
        key = self._get_board_key(board_obj)
        self.position_counts[key] = self.position_counts.get(key, 0) + 1
        if self.position_counts[key] >= 3:
            return "DRAW_REPETITION"
        return None

    def run(self):
        """
        Executes the game loop until a result is determined.
        Returns: The winner ('V1', 'V2', or 'DRAW')
        """
        db_conn = sqlite3.connect("checkers_endgame.db")

        while True:
            winner = self.board.winner()
            if winner:
                db_conn.close()
                return self.players[winner]['name']
            
            if self._update_position_counts(self.board) or self.board.moves_since_progress >= 80:
                db_conn.close()
                return "DRAW"

            current_player_config = self.players[self.board.turn]
            eval_func = current_player_config['eval_func']
            
            board_for_ai = self.board
            board_for_ai.db_conn = db_conn

            best_move, _ = get_ai_move_analysis(board_for_ai, self.ai_depth, self.board.turn, eval_func)

            if not best_move:
                opponent_color = WHITE if self.board.turn == RED else RED
                db_conn.close()
                return self.players[opponent_color]['name']
            
            self.board = self.board.apply_move(best_move)
        
        db_conn.close()


def run_gauntlet():
    """
    Runs a series of games from a FEN file to test two engine versions.
    """
    logging.info("Starting Engine Gauntlet...")

    # --- Configuration ---
    GAUNTLET_AI_DEPTH = 5 # <-- The "Sweet Spot" Depth for testing
    v1_config = {'name': 'V1', 'eval_func': evaluate_board_v1}
    v2_config = {'name': 'V2', 'eval_func': evaluate_board_v2_experimental}
    fen_file = "test_positions.txt"
    results_file = "gauntlet_results.txt"
    
    try:
        with open(fen_file, "r") as f:
            fens = [line.strip() for line in f if ':' in line and not line.startswith('#')]
        logging.info(f"Loaded {len(fens)} positions from '{fen_file}'.")
    except FileNotFoundError:
        logging.error(f"FATAL: Could not find '{fen_file}'. Aborting.")
        return

    scores = {'V1': 0, 'V2': 0, 'DRAW': 0}
    winning_fens = {'V1': [], 'V2': []}
    total_games = len(fens) * 2

    for i, fen in enumerate(fens):
        game_num = i * 2 + 1
        logging.info(f"--- Running Game {game_num}/{total_games} (V2 as White) ---")
        game1 = HeadlessGame(fen, v1_config, v2_config, GAUNTLET_AI_DEPTH)
        winner1 = game1.run()
        scores[winner1] += 1
        if winner1 != 'DRAW': winning_fens[winner1].append(fen)
        logging.info(f"Result: {winner1} wins.")

        game_num = i * 2 + 2
        logging.info(f"--- Running Game {game_num}/{total_games} (V1 as White) ---")
        game2 = HeadlessGame(fen, v2_config, v1_config, GAUNTLET_AI_DEPTH)
        winner2 = game2.run()
        scores[winner2] += 1
        if winner2 != 'DRAW': winning_fens[winner2].append(fen)
        logging.info(f"Result: {winner2} wins.")

    logging.info("Gauntlet finished. Writing results...")
    with open(results_file, "w") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"Gauntlet Results - {timestamp}\n")
        f.write("="*40 + "\n")
        f.write(f"Final Score: ({scores['V2']} - {scores['V1']} - {scores['DRAW']})\n")
        f.write("="*40 + "\n\n")
        f.write(f"Positions where V2 (Experimental) Won ({len(winning_fens['V2'])}):\n")
        for w_fen in winning_fens['V2'] if winning_fens['V2'] else ["- None"]: f.write(f"- {w_fen}\n")
        f.write("\n")
        f.write(f"Positions where V1 (Stable) Won ({len(winning_fens['V1'])}):\n")
        for w_fen in winning_fens['V1'] if winning_fens['V1'] else ["- None"]: f.write(f"- {w_fen}\n")
    
    logging.info(f"Results saved to '{results_file}'.")

if __name__ == '__main__':
    run_gauntlet()


