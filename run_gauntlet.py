# run_gauntlet.py
import logging
import sqlite3
import re
import argparse
from datetime import datetime
import copy

# --- Imports from your engine ---
from engine.debug import setup_logging, LOGGERS
from engine.board import Board
from engine.constants import RED, WHITE, COORD_TO_ACF
# --- FIX: Removed 'clear_history_table' which no longer exists ---
from engine.search import get_ai_move_analysis, _get_all_moves_for_color
from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental

# --- Get the loggers ---
logger = logging.getLogger()
game_logger = logging.getLogger('gameflow')

def format_move_path_for_log(path):
    if not path or len(path) < 2: return "Invalid Path"
    separator = 'x' if abs(path[0][0] - path[1][0]) == 2 else '-'
    return separator.join(str(COORD_TO_ACF.get(pos, "??")) for pos in path)

class HeadlessGame:
    def __init__(self, starting_fen, red_player_config, white_player_config, ai_depth):
        # --- FIX: Removed call to 'clear_history_table()' ---
        self.board = Board()
        if starting_fen:
            self.board.create_board_from_fen(starting_fen)
        self.players = {RED: red_player_config, WHITE: white_player_config}
        self.ai_depth = ai_depth
        self.position_counts = {}
        self._update_position_counts()
        self.move_history = []

    def run(self):
        move_limit = 200 # 100 moves per player
        for i in range(move_limit):
            if self.board.winner() is not None:
                return self.board.winner()
            
            if any(count >= 3 for count in self.position_counts.values()):
                return "DRAW"

            current_turn_color = self.board.turn
            current_player = self.players[current_turn_color]
            
            game_logger.info(f"--- Turn {len(self.move_history) // 2 + 1} ({current_turn_color}) ---")
            game_logger.info(f"Engine '{current_player['name']}' is thinking.")
            
            available_moves = _get_all_moves_for_color(self.board)
            
            if not available_moves:
                game_logger.error(f"FATAL: No legal moves found for {current_turn_color}. Opponent wins.")
                return WHITE if current_turn_color == RED else RED
            
            game_logger.info(f"Found {len(available_moves)} legal move(s): {[format_move_path_for_log(m) for m in available_moves]}")
            
            board_for_ai = copy.deepcopy(self.board)
            score, best_move = get_ai_move_analysis(board_for_ai, self.ai_depth, current_turn_color, current_player['eval_func'])
            
            if best_move is None:
                game_logger.error(f"AI returned no best move for {current_turn_color}. Opponent wins.")
                return WHITE if current_turn_color == RED else RED

            self.board = self.board.apply_move(best_move)
            self.move_history.append(format_move_path_for_log(best_move))
            self._update_position_counts()
        
        return "DRAW"

    def _update_position_counts(self):
        fen = self.board.get_fen(compact=True).split(':', 1)[1]
        self.position_counts[fen] = self.position_counts.get(fen, 0) + 1

def run_gauntlet(args):
    setup_logging(args)
    
    positions_file = args.file if args.file else 'test_positions.txt'
    results_file = args.results if args.results else 'gauntlet_results.txt'
    GAUNTLET_AI_DEPTH = args.depth if args.depth else 4

    try:
        with open(positions_file, 'r') as f:
            fens = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(fens)} starting positions from {positions_file}")
    except FileNotFoundError:
        logger.error(f"Error: Starting positions file not found at '{positions_file}'")
        return

    v1_config = {'name': 'V1', 'eval_func': evaluate_board_v1}
    v2_config = {'name': 'V2', 'eval_func': evaluate_board_v2_experimental}
    scores = {'V1': 0, 'V2': 0, 'DRAW': 0}
    winning_fens = {'V1': [], 'V2': []}

    for i, fen in enumerate(fens):
        logger.info(f"""
--------------------------------------------------
Running Match {i+1}/{len(fens)} | FEN: {fen}
--------------------------------------------------""")
        
        logger.info("--- Game 1: V1 (Red) vs V2 (White) ---")
        game1 = HeadlessGame(fen, v1_config, v2_config, GAUNTLET_AI_DEPTH)
        winner1 = game1.run()
        winner1_name = v1_config['name'] if winner1 == RED else (v2_config['name'] if winner1 == WHITE else 'DRAW')
        scores[winner1_name] += 1
        if winner1 != 'DRAW': winning_fens[winner1_name].append(fen)
        logger.info(f"Game complete. Winner: {winner1_name}. | Score: V2 {scores['V2']} - V1 {scores['V1']} - D {scores['DRAW']}")

        logger.info("--- Game 2: V2 (Red) vs V1 (White) ---")
        game2 = HeadlessGame(fen, v2_config, v1_config, GAUNTLET_AI_DEPTH)
        winner2 = game2.run()
        winner2_name = v2_config['name'] if winner2 == RED else (v1_config['name'] if winner2 == WHITE else 'DRAW')
        scores[winner2_name] += 1
        if winner2 != 'DRAW': winning_fens[winner2_name].append(fen)
        logger.info(f"Game complete. Winner: {winner2_name}. | Score: V2 {scores['V2']} - V1 {scores['V1']} - D {scores['DRAW']}")

    logger.info("Gauntlet finished. Writing results...")
    with open(results_file, "w") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"Gauntlet Results - {timestamp}\n")
        f.write("="*40 + "\n")
        f.write(f"Final Score: (V2 {scores.get('V2', 0)} - V1 {scores.get('V1', 0)} - D {scores.get('DRAW', 0)})\n")
        f.write("="*40 + "\n\n")
        f.write(f"Positions where V2 (Experimental) Won ({len(winning_fens.get('V2', []))}):\n")
        for w_fen in winning_fens.get('V2', []) or ["- None"]:
            f.write(f"- {w_fen}\n")
        f.write("\n")
        f.write(f"Positions where V1 (Stable) Won ({len(winning_fens.get('V1', []))}):\n")
        for w_fen in winning_fens.get('V1', []) or ["- None"]:
            f.write(f"- {w_fen}\n")
    
    logger.info(f"Results written to {results_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a gauntlet of checkers games between two AI engines.")
    parser.add_argument('--file', type=str, help='Path to the text file of starting FEN positions.')
    parser.add_argument('--results', type=str, help='Path to the output file for gauntlet results.')
    parser.add_argument('--depth', type=int, help='AI search depth for the gauntlet.')
    for name in LOGGERS:
        parser.add_argument(f'--debug-{name}', action='store_true', help=f'Enable DEBUG logging for the {name} logger.')
    
    args = parser.parse_args()
    run_gauntlet(args)
