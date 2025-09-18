# run_gauntlet.py
import logging
import sqlite3
import time
import os
import argparse
import re
from datetime import datetime

# --- MODIFIED: Import our logging setup and constants ---
from engine.debug import setup_logging
from engine.board import Board
# --- MODIFIED: Added COORD_TO_ACF for the new helper function ---
from engine.constants import RED, WHITE, COORD_TO_ACF
from engine.search import get_ai_move_analysis
from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental

# --- Get the specific logger ---
game_logger = logging.getLogger('gameflow')
logger = logging.getLogger()
# --- NEW: Helper function to format moves for the log ---
def format_move_path_for_log(path):
    """Converts a move path like [(4, 5), (5, 4)] to ACF notation like '17-21'."""
    if not path or len(path) < 2:
        return "Invalid Path"
    
    start_pos, end_pos = path[0], path[-1]
    start_acf = COORD_TO_ACF.get(start_pos, "??")
    end_acf = COORD_TO_ACF.get(end_pos, "??")
    
    # Determine if it's a jump or a simple move
    separator = 'x' if abs(start_pos[0] - path[1][0]) == 2 else '-'
    
    return f"{start_acf}{separator}{end_acf}"

class HeadlessGame:
    """
    A class to simulate a single game of checkers between two AI engines
    without any graphical user interface.
    """
    def __init__(self, starting_fen, red_player_config, white_player_config, ai_depth=5):
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

            game_logger.debug(f"Starting turn for {current_turn_color}. FEN: {self.board.get_fen()}")
            analysis_result = get_ai_move_analysis(board_for_ai, self.ai_depth, current_turn_color, eval_func)
            
            if analysis_result is None or not analysis_result[0]:
                best_move = None
                game_logger.debug("AI analysis returned: None")
            else:
                best_move, _ = analysis_result
                # --- MODIFIED: Use the new helper function for logging ---
                formatted_move = format_move_path_for_log(best_move)
                game_logger.debug(f"AI analysis returned: {formatted_move}")

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
    setup_logging(args)
    
    logging.info("Starting Engine Gauntlet...")

    GAUNTLET_AI_DEPTH = 5
    v1_config = {'name': 'V1', 'eval_func': evaluate_board_v1}
    v2_config = {'name': 'V2', 'eval_func': evaluate_board_v2_experimental}
    fen_file = "test_positions.txt"
    results_file = "gauntlet_results.txt"
    
    try:
        with open(fen_file, "r") as f:
            content = f.read()
            fens = re.findall(r'\[FEN "([^"]+)"\]', content)
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
    parser.add_argument('--debug-gameflow', action='store_true', help='Enable game flow logging.')
    parser.add_argument('--debug-search', action='store_true', help='Enable search algorithm logging.')
    parser.add_argument('--debug-eval', action='store_true', help='Enable evaluation function logging.')
    parser.add_argument('--debug-board', action='store_true', help='Enable board state and move gen logging.')
    args = parser.parse_args()
    
    run_gauntlet(args)
