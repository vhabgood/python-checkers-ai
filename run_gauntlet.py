# run_gauntlet.py
import logging
import sqlite3
import time
import os
import argparse
from datetime import datetime

# --- FIX: All engine imports moved to the top level for proper initialization ---
from engine.board import Board
from engine.constants import RED, WHITE
from engine.search import get_ai_move_analysis
from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental

# --- REFINED: Logging Configuration ---
def setup_logging(eval_log_enabled):
    # ... (rest of the function is unchanged) ...
    # Configure the root logger for clean console output
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                        handlers=[logging.StreamHandler()]) # Explicitly use console
    
    # --- Setup dedicated file for search details (aspiration fails) ---
    search_logger = logging.getLogger('search_detail')
    search_logger.setLevel(logging.WARNING) # We only care about the warnings
    search_log_handler = logging.FileHandler('search_log.log', mode='w')
    search_logger.addHandler(search_log_handler)
    search_logger.propagate = False # This is the key to stopping console spam
        
    # --- Setup dedicated file for evaluation CSV data ---
    if eval_log_enabled:
        eval_logger = logging.getLogger('eval_detail')
        eval_logger.setLevel(logging.INFO)
        eval_log_handler = logging.FileHandler('evaluation_log.csv', mode='w')
        eval_logger.addHandler(eval_log_handler)
        eval_logger.propagate = False
        eval_logger.info("Engine,FEN,FinalScore,Material,Positional,Blockade,FirstKing,Mobility,Advancement,Simplification")


class HeadlessGame:
    """
    A class to simulate a single game of checkers between two AI engines
    without any graphical user interface.
    """
    def __init__(self, starting_fen, red_player_config, white_player_config, ai_depth=5):
        # The import is no longer needed here
        self.board = Board()
        self.board.create_board_from_fen(starting_fen)
        
        self.players = {
            'RED': red_player_config,
            'WHITE': white_player_config
        }
        self.ai_depth = ai_depth
        self.position_counts = {}
        self._update_position_counts(self.board)

    def _get_board_key(self, board_obj):
        return (tuple(map(tuple, board_obj.board)), board_obj.turn)

    def _update_position_counts(self, board_obj):
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
        # Imports are no longer needed here
        db_conn = sqlite3.connect("checkers_endgame.db")

        while True:
            winner_color = self.board.winner()
            if winner_color:
                winner_name = self.players['RED']['name'] if winner_color == RED else self.players['WHITE']['name']
                db_conn.close()
                return winner_name
            
            if self._update_position_counts(self.board) or self.board.moves_since_progress >= 80:
                db_conn.close()
                return "DRAW"

            current_turn_color = self.board.turn
            current_player_config = self.players['RED'] if current_turn_color == RED else self.players['WHITE']
            eval_func = current_player_config['eval_func']
            
            board_for_ai = self.board
            board_for_ai.db_conn = db_conn

            analysis_result = get_ai_move_analysis(board_for_ai, self.ai_depth, current_turn_color, eval_func)
            
            # This logic now correctly handles a true game-over scenario
            if analysis_result is None:
                best_move = None
            else:
                best_move, _ = analysis_result

            if not best_move:
                opponent_color_name = self.players['WHITE']['name'] if current_turn_color == RED else self.players['RED']['name']
                db_conn.close()
                return opponent_color_name
            
            self.board = self.board.apply_move(best_move)
        
        db_conn.close()


def run_gauntlet(args):
    """
    Runs a series of games from a FEN file to test two engine versions.
    """
    # Imports are no longer needed here
    setup_logging(args.eval_log)
    
    # ... (rest of the function is unchanged) ...
    logging.info("Starting Engine Gauntlet...")

    GAUNTLET_AI_DEPTH = 7
    v1_config = {'name': 'V1', 'eval_func': evaluate_board_v1}
    v2_config = {'name': 'V2', 'eval_func': evaluate_board_v2_experimental}
    fen_file = "test_positions.txt"
    results_file = "gauntlet_results.txt"
    
    try:
        with open(fen_file, "r") as f:
            fens = [line.strip() for line in f if ':' in line and not line.startswith('#')]
        logging.info(f"Loaded {len(fens)} positions from '{fen_file}'.")
    except FileNotFoundError:
        logging.error(f"FATAL: Could not find '{fen_file}'. Aborting."); return

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
        logging.info(f"Game {game_num} complete. Winner: {winner1}. | Current Score: (V2 {scores['V2']} - V1 {scores['V1']} - D {scores['DRAW']})")

        # --- Game 2: V1 as White ---
        game_num = i * 2 + 2
        logging.info(f"--- Running Game {game_num}/{total_games} (V1 as White) ---")
        game2 = HeadlessGame(fen, v2_config, v1_config, GAUNTLET_AI_DEPTH)
        winner2 = game2.run()
        scores[winner2] += 1
        if winner2 != 'DRAW': winning_fens[winner2].append(fen)
        logging.info(f"Game {game_num} complete. Winner: {winner2}. | Current Score: (V2 {scores['V2']} - V1 {scores['V1']} - D {scores['DRAW']})")

    logging.info("Gauntlet finished. Writing results...")
    with open(results_file, "w") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"Gauntlet Results - {timestamp}\n")
        f.write("="*40 + "\n")
        f.write(f"Final Score: ({scores.get('V2', 0)} - {scores.get('V1', 0)} - {scores.get('DRAW', 0)})\n")
        f.write("="*40 + "\n\n")
        f.write(f"Positions where V2 (Experimental) Won ({len(winning_fens.get('V2',[]))}):\n")
        for w_fen in winning_fens.get('V2',[]) if winning_fens.get('V2',[]) else ["- None"]: f.write(f"- {w_fen}\n")
        f.write("\n")
        f.write(f"Positions where V1 (Stable) Won ({len(winning_fens.get('V1',[]))}):\n")
        for w_fen in winning_fens.get('V1',[]) if winning_fens.get('V1',[]) else ["- None"]: f.write(f"- {w_fen}\n")
    
    logging.info(f"Results saved to '{results_file}'.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a gauntlet of checkers games between two engine versions.")
    parser.add_argument('--eval-log', action='store_true', help='Enable detailed evaluation logging to evaluation_log.csv')
    args = parser.parse_args()
    
    run_gauntlet(args)
