import logging
import sqlite3
import re
import argparse
from datetime import datetime

# --- Imports from your engine ---
from engine.debug import setup_logging
from engine.board import Board
from engine.constants import RED, WHITE, COORD_TO_ACF
from engine.search import get_ai_move_analysis, clear_history_table
from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental

# --- Get the loggers ---
logger = logging.getLogger()
game_logger = logging.getLogger('gameflow')

def format_move_path_for_log(path):
    if not path or len(path) < 2: return "Invalid Path"
    start_pos, end_pos = path[0], path[-1]
    start_acf = COORD_TO_ACF.get(start_pos, "??")
    end_acf = COORD_TO_ACF.get(end_pos, "??")
    separator = 'x' if abs(start_pos[0] - path[1][0]) == 2 else '-'
    return f"{start_acf}{separator}{end_acf}"

class HeadlessGame:
    def __init__(self, starting_fen, red_player_config, white_player_config, ai_depth):
        clear_history_table()
        self.board = Board()
        self.board.create_board_from_fen(starting_fen)
        self.players = {'RED': red_player_config, 'WHITE': white_player_config}
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
        db_conn = sqlite3.connect("checkers_endgame.db")
        while True:
            if self.board.winner() is not None or self._update_position_counts(self.board) or self.board.moves_since_progress >= 80:
                break
            
            current_turn_color = self.board.turn
            player_key = 'RED' if current_turn_color == RED else 'WHITE'
            current_player = self.players[player_key]
            
            board_for_ai = self.board
            board_for_ai.db_conn = db_conn
            
            best_move, _ = get_ai_move_analysis(board_for_ai, self.ai_depth, current_turn_color, current_player['eval_func'])
            
            if not best_move:
                break
            
            self.board = self.board.apply_move(best_move)
        
        db_conn.close()
        winner_color = self.board.winner()
        if winner_color:
            winner_key = 'RED' if winner_color == RED else 'WHITE'
            return self.players[winner_key]['name']
        return "DRAW"

def run_gauntlet(args):
    setup_logging(args)
    logger.info("Starting Engine Gauntlet...")

    GAUNTLET_AI_DEPTH = 7
    v1_config = {'name': 'V1', 'eval_func': evaluate_board_v1}
    v2_config = {'name': 'V2', 'eval_func': evaluate_board_v2_experimental}
    fen_file = "test_positions.txt"
    results_file = "gauntlet_results.txt"
    
    try:
        with open(fen_file, "r") as f:
            content = f.read()
            fens = re.findall(r'\[FEN "([^"]+)"\]', content)
        logger.info(f"Loaded {len(fens)} positions from '{fen_file}'.")
    except FileNotFoundError:
        logger.error(f"FATAL: Could not find '{fen_file}'. Aborting."); return

    scores = {'V1': 0, 'V2': 0, 'DRAW': 0}
    winning_fens = {'V1': [], 'V2': []}
    
    for i, fen in enumerate(fens):
        # Game 1: V1 (Red) vs V2 (White)
        logger.info(f"--- Running Game {i*2+1}/{len(fens)*2} (V1 as Red) ---")
        game1 = HeadlessGame(fen, v1_config, v2_config, GAUNTLET_AI_DEPTH)
        winner1 = game1.run()
        if winner1 in scores:
            scores[winner1] += 1
            if winner1 != 'DRAW':
                winning_fens[winner1].append(fen)
        logger.info(f"Game complete. Winner: {winner1}. | Score: V2 {scores['V2']} - V1 {scores['V1']} - D {scores['DRAW']}")

        # Game 2: V2 (Red) vs V1 (White)
        logger.info(f"--- Running Game {i*2+2}/{len(fens)*2} (V2 as Red) ---")
        game2 = HeadlessGame(fen, v2_config, v1_config, GAUNTLET_AI_DEPTH)
        winner2 = game2.run()
        if winner2 in scores:
            scores[winner2] += 1
            if winner2 != 'DRAW':
                winning_fens[winner2].append(fen)
        logger.info(f"Game complete. Winner: {winner2}. | Score: V2 {scores['V2']} - V1 {scores['V1']} - D {scores['DRAW']}")

    logger.info("Gauntlet finished. Writing results...")
    with open(results_file, "w") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"Gauntlet Results - {timestamp}\n")
        f.write("="*40 + "\n")
        f.write(f"Final Score: ({scores.get('V2', 0)} - {scores.get('V1', 0)} - {scores.get('DRAW', 0)})\n")
        f.write("="*40 + "\n\n")
        f.write(f"Positions where V2 (Experimental) Won ({len(winning_fens.get('V2', []))}):\n")
        for w_fen in winning_fens.get('V2', []) or ["- None"]:
            f.write(f"- {w_fen}\n")
        f.write("\n")
        f.write(f"Positions where V1 (Stable) Won ({len(winning_fens.get('V1', []))}):\n")
        for w_fen in winning_fens.get('V1', []) or ["- None"]:
            f.write(f"- {w_fen}\n")
    
    logger.info(f"Results saved to '{results_file}'.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a gauntlet of checkers games.")
    parser.add_argument('--debug-gameflow', action='store_true')
    parser.add_argument('--debug-search', action='store_true')
    parser.add_argument('--debug-eval', action='store_true')
    parser.add_argument('--debug-board', action='store_true')
    args = parser.parse_args()
    run_gauntlet(args)
