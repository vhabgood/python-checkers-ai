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
from engine.search import get_ai_move_analysis
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
        self.board = Board()
        if starting_fen:
            # This is where the FEN is used
            self.board.create_board_from_fen(starting_fen)
        self.players = {RED: red_player_config, WHITE: white_player_config}
        self.ai_depth = ai_depth
        self.position_counts = {}
        self.winner = None
        self.game_ply = 0
        self.max_ply = 150

    def play(self):
        initial_fen = self.board.get_fen(compact=True)
        game_logger.info(f"Starting new game from FEN: {initial_fen}")

        while not self.winner and self.game_ply < self.max_ply:
           # game_logger.info(f"--- Turn {self.game_ply + 1} ({self.board.turn}) ---")
            current_player_config = self.players[self.board.turn]
         #   game_logger.info(f"Engine '{current_player_config['name']}' is thinking.")

            board_for_ai = self.board.copy()
            score, move_path = get_ai_move_analysis(
                board_for_ai,
                self.ai_depth,
                None,
                current_player_config['eval_func']
            )

            if move_path:
                log_move = format_move_path_for_log(move_path)
                game_logger.info(f"Engine '{current_player_config['name']}' plays move: {log_move} (Eval: {score:.4f})")
                self.board = self.board.apply_move(move_path)
                self.game_ply += 1
            else:
                winner_color = WHITE if self.board.turn == RED else RED
                self.winner = self.players[winner_color]['name']
                game_logger.info(f"No moves for {self.board.turn}. Winner: {self.winner}")
                break

            if self.board.winner():
                self.winner = self.players[self.board.winner()]['name']
                game_logger.info(f"Game over. Winner determined by board state: {self.winner}")
            elif self._is_draw_by_repetition():
                self.winner = "DRAW"
                game_logger.info("Game over. Draw by 3-fold repetition.")

        if not self.winner:
            self.winner = "DRAW"
            game_logger.info(f"Game over. Max moves ({self.max_ply}) reached.")

        return self.winner, self.board.get_fen(compact=True)

    def _is_draw_by_repetition(self):
        fen = self.board.get_fen(compact=True)
        self.position_counts[fen] = self.position_counts.get(fen, 0) + 1
        return self.position_counts[fen] >= 3

def run_gauntlet(positions_file, results_file, ai_depth):
    # ==============================================================================
    # --- FINAL FIX: Properly parse FEN strings from the input file ---
    positions = []
    fen_regex = re.compile(r'\[FEN "(.*?)"\]')
    try:
        with open(positions_file, 'r') as f:
            for line in f:
                match = fen_regex.search(line)
                if match:
                    # The engine uses 'R' for Red, but the file uses 'B' for Black.
                    # We need to replace it for the parser to work correctly.
                    fen_string = match.group(1).replace('B:', 'R:').replace(':B', ':R')
                    positions.append(fen_string)
    except FileNotFoundError:
        logger.error(f"Positions file not found: {positions_file}")
        return
    # ==============================================================================

    logger.info(f"Loaded {len(positions)} starting positions for the gauntlet.")

    v1_config = {'name': 'V1', 'eval_func': evaluate_board_v1}
    v2_config = {'name': 'V2', 'eval_func': evaluate_board_v2_experimental}
    
    scores = {'V1': 0, 'V2': 0, 'DRAW': 0}
    winning_fens = {'V1': [], 'V2': []}

    for i, fen in enumerate(positions):
        logger.info(f"--- Starting Match {i+1} of {len(positions)} ---")
        
        # Match 1: V2 (Experimental) as RED, V1 (Stable) as WHITE
        game1 = HeadlessGame(fen, v2_config, v1_config, ai_depth)
        winner1, final_fen1 = game1.play()
        scores[winner1] += 1
        if winner1 != 'DRAW': winning_fens[winner1].append(f"{fen} -> {final_fen1}")
        logger.info(f"Match 1 Result: {winner1} wins. Score: V2 {scores.get('V2',0)} - V1 {scores.get('V1',0)} - D {scores.get('DRAW',0)}")

        # Match 2: V1 (Stable) as RED, V2 (Experimental) as WHITE
        game2 = HeadlessGame(fen, v1_config, v2_config, ai_depth)
        winner2, final_fen2 = game2.play()
        scores[winner2] += 1
        if winner2 != 'DRAW': winning_fens[winner2].append(f"{fen} -> {final_fen2}")
        logger.info(f"Match 2 Result: {winner2} wins. Score: V2 {scores.get('V2',0)} - V1 {scores.get('V1',0)} - D {scores.get('DRAW',0)}")

    logger.info("Gauntlet finished. Writing results...")
    with open(results_file, "w") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"Gauntlet Results - {timestamp}\\n")
        f.write("="*40 + "\\n")
        f.write(f"Final Score: (V2 {scores.get('V2', 0)} - V1 {scores.get('V1', 0)} - D {scores.get('DRAW', 0)})\\n")
        f.write("="*40 + "\\n\\n")
        f.write(f"Positions where V2 (Experimental) Won ({len(winning_fens.get('V2', []))}):\\n")
        for w_fen in winning_fens.get('V2', []) or ["- None"]:
            f.write(f"- {w_fen}\\n")
        f.write("\\n")
        f.write(f"Positions where V1 (Stable) Won ({len(winning_fens.get('V1', []))}):\\n")
        for w_fen in winning_fens.get('V1', []) or ["- None"]:
            f.write(f"- {w_fen}\\n")
    
    logger.info(f"Results written to {results_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a gauntlet of checkers games between two AI engines.")
    parser.add_argument('--file', type=str, help='Path to the text file of starting FEN positions.', default='gauntlet.txt')
    parser.add_argument('--results', type=str, help='Path to write the results file.', default='gauntlet_results.txt')
    parser.add_argument('--depth', type=int, help='AI search depth.', default=5)
    
    for name in LOGGERS:
        parser.add_argument(f'--debug-{name}', action='store_true', help=f'Enable DEBUG logging for the {name} module.')
    
    args = parser.parse_args()
    setup_logging(args)
    
    run_gauntlet(args.file, args.results, args.depth)
