# engine/search.py
# This file contains the core AI logic, including the Principal Variation Search
# (PVS) algorithm and the integration with the endgame database (EGDB).

import random
import logging
from .constants import (RED, WHITE, ROWS, COLS, COORD_TO_ACF, 
                      DB_WIN, DB_LOSS, DB_DRAW, DB_UNAVAILABLE, DB_UNKNOWN, RESULT_MAP)
from .board import Board

# --- Globals & Initialization ---
search_logger = logging.getLogger('search')
transposition_table = {}
killer_moves = [[(None, None)] * 2 for _ in range(15)]
history_heuristic = {}
egdb_driver = None

def initialize_search(driver):
    """Initializes the search module with the EGDB driver."""
    global egdb_driver
    egdb_driver = driver

# --- Helper Functions ---
def _format_move_for_log(path):
    """Formats a move path for logging."""
    if not path: return "None"
    sep = 'x' if abs(path[0][0] - path[1][0]) == 2 else '-'
    return sep.join(str(COORD_TO_ACF.get(pos, "??")) for pos in path)

# --- Endgame Database (EGDB) Logic ---
def _handle_egdb_hit(result, mtc, board, history_hashes):
    """Determines the best move based on a definitive EGDB result."""
    outcomes = []
    legal_moves = board.get_all_valid_moves(board.turn)
    if not legal_moves:
        return None

    for move in legal_moves:
        next_board = board.apply_move(move)
        res, next_mtc = egdb_driver.probe(next_board)
        outcomes.append({'move': move, 'res': res, 'mtc': next_mtc, 'hash': next_board.get_hash()})

    best_move = None

    # Case 1: The current position is a WIN. Find the fastest winning move.
    if result == DB_WIN:
        # A winning move is one that leads to a LOSS for the opponent. Sort by MTC to find the fastest win.
        winning_moves = sorted([o for o in outcomes if o['res'] == DB_LOSS], key=lambda x: x['mtc'])
        if winning_moves:
            best_mtc = winning_moves[0]['mtc']
            # In case of ties, randomly pick one of the best moves.
            best_options = [o['move'] for o in winning_moves if o['mtc'] == best_mtc]
            best_move = random.choice(best_options)
            search_logger.info(f"EGDB (in WIN): Found move forcing a loss (MTC {best_mtc}): {_format_move_for_log(best_move)}")
        else:
            # If no move forces a loss, maintain the win by finding a non-repeating draw.
            drawing_moves = [o['move'] for o in outcomes if o['res'] == DB_DRAW and o['hash'] not in history_hashes]
            if drawing_moves:
                best_move = random.choice(drawing_moves)
                search_logger.info(f"EGDB (in WIN): Found move maintaining win via draw: {_format_move_for_log(best_move)}")

    # Case 2: The current position is a DRAW.
    elif result == DB_DRAW:
        # First, see if the opponent blundered and offered a win.
        winning_moves = sorted([o for o in outcomes if o['res'] == DB_LOSS], key=lambda x: x['mtc'])
        if winning_moves:
            best_mtc = winning_moves[0]['mtc']
            best_options = [o['move'] for o in winning_moves if o['mtc'] == best_mtc]
            best_move = random.choice(best_options)
            search_logger.info(f"EGDB (in DRAW): Opponent blundered. Taking win (MTC {best_mtc}): {_format_move_for_log(best_move)}")
        else:
            # Otherwise, find a non-repeating move that maintains the draw.
            drawing_moves = [o for o in outcomes if o['res'] == DB_DRAW]
            non_repeating_draws = [o['move'] for o in drawing_moves if o['hash'] not in history_hashes]
            if non_repeating_draws:
                best_move = random.choice(non_repeating_draws)
                search_logger.info(f"EGDB (in DRAW): Found non-repeating draw: {_format_move_for_log(best_move)}")
            elif drawing_moves: # If all drawing moves are repetitions, we must pick one.
                best_move = random.choice([o['move'] for o in drawing_moves])
                search_logger.info(f"EGDB (in DRAW): Found drawing move (accepting repetition): {_format_move_for_log(best_move)}")

    # Case 3: The current position is a LOSS. Find the slowest losing move.
    elif result == DB_LOSS:
        # Sort all available moves by the opponent's MTC in descending order (longest loss is best).
        if outcomes:
            best_moves_by_mtc = sorted(outcomes, key=lambda x: x['mtc'], reverse=True)
            best_mtc = best_moves_by_mtc[0]['mtc']
            best_options = [o['move'] for o in best_moves_by_mtc if o['mtc'] == best_mtc]
            best_move = random.choice(best_options)
            search_logger.info(f"EGDB (in LOSS): Choosing longest loss (MTC {best_mtc}): {_format_move_for_log(best_move)}")

    # If no best move was found by the logic above, fall back.
    if not best_move and legal_moves:
        search_logger.warning("EGDB FALLBACK: Could not determine a best move, choosing first legal move.")
        best_move = legal_moves[0]
        
    return best_move

# --- Core AI Search Function ---
def get_ai_move_analysis(board, depth, result_queue, evaluate_func, history_hashes=None):
    """Top-level AI interface. Probes EGDB first, then falls back to PVS search."""
    history_hashes = history_hashes or []
    
    if egdb_driver and egdb_driver.initialized:
        result, mtc = egdb_driver.probe(board)
        
        if result in (DB_WIN, DB_LOSS, DB_DRAW):
            # FIX: Converted print to logger.debug
            search_logger.debug(f"[TRACE 1] EGDB HIT. Result is {RESULT_MAP.get(result)}. Calling _handle_egdb_hit...")
            best_move = _handle_egdb_hit(result, mtc, board, history_hashes)
            # FIX: Converted print to logger.debug
            search_logger.debug(f"[TRACE 2] _handle_egdb_hit returned: {best_move}")

            score = 9999 if result == DB_WIN else -9999 if result == DB_LOSS else 0
            move_path = [best_move] if best_move else []
            
            if result_queue:
                result_queue.put([(move_path, score)])
            
            # FIX: Converted print to logger.debug
            search_logger.debug(f"[TRACE 3] Returning from EGDB HIT block with move_path: {move_path}")
            return score, move_path

    # FIX: Converted print to logger.debug
    search_logger.debug(f"[TRACE 4] Proceeding to EGDB Fallback...")
    search_logger.debug(f"EGDB Fallback. Starting PVS search to depth {depth}...")
    best_move_sequence, best_score = _pvs_search_top(board, depth, evaluate_func) 
    
    if result_queue:
        result_queue.put([(best_move_sequence, best_score)])
        
    return best_score, best_move_sequence
# --- PVS Search Implementation ---

def _pvs_search_top(board, depth, evaluate_func):
    """
    The top-level PVS search function.
    Initializes the search and handles the first level of moves.
    """
    global killer_moves, history_heuristic
    
    moves = board.get_all_valid_moves(board.turn)
    search_logger.debug(f"DEBUG: Found {len(moves)} legal moves at root for {board.turn}.")
    if not moves:
        search_logger.debug(f"DEBUG: No moves found for {board.turn}. Returning evaluation.")
        return [], evaluate_func(board) # Return current score if no moves

    best_score = -float('inf')
    best_move = None
    
    # Sort moves using heuristics
    moves.sort(key=lambda move: history_heuristic.get((board.get_hash(), _format_move_for_log(move)), 0), reverse=True)
    
    # Principal Variation Search
    for i, move in enumerate(moves):
        new_board = board.apply_move(move)
        
        if i == 0:
            # Full window search for the first move
            score = -_pvs_search(new_board, depth - 1, -float('inf'), float('inf'), evaluate_func)
        else:
            # Null window search for subsequent moves
            score = -_pvs_search(new_board, depth - 1, -best_score - 1, -best_score, evaluate_func)
            
            # Re-search with full window if a better move is found
            if score > best_score:
                score = -_pvs_search(new_board, depth - 1, -float('inf'), -score, evaluate_func)
                
        if score > best_score:
            best_score = score
            best_move= move
            
    # FIX: Initialize best_move_sequence with the best_move found after the loop finishes.
    best_move_sequence = [best_move] if best_move else []  
    
    # FIX: The original code returned a single move, but the caller expects a sequence.
    # Now we return a sequence and a score.   
    search_logger.debug(f"Search complete. Best move: {_format_move_for_log(best_move)}")
    return best_move_sequence, best_score

def _pvs_search(board, depth, alpha, beta, evaluate_func):
    """
    The core recursive PVS search with alpha-beta pruning.
    """
    search_logger.debug(f"DEBUG: PVS search called for {board.turn} at depth {depth}.")
    if board.winner() or depth == 0:
        return quiescence_search(board, alpha, beta, evaluate_func)

    moves = board.get_all_valid_moves(board.turn)
    if not moves:
        search_logger.debug(f"DEBUG: Leaf node reached for {board.turn} at depth {depth}. No moves.")
        return evaluate_func(board)

    # Sort moves using heuristics
    moves.sort(key=lambda move: history_heuristic.get((board.get_hash(), _format_move_for_log(move)), 0), reverse=True)

    for i, move in enumerate(moves):
        new_board = board.apply_move(move)
        
        if i == 0:
            score = -_pvs_search(new_board, depth - 1, -beta, -alpha, evaluate_func)
        else:
            score = -_pvs_search(new_board, depth - 1, -alpha - 1, -alpha, evaluate_func)
            if score > alpha and score < beta:
                score = -_pvs_search(new_board, depth - 1, -beta, -alpha, evaluate_func)
        
        alpha = max(alpha, score)
        if alpha >= beta:
            # Alpha-beta cutoff. Store this killer move.
            # FIX: Properly store killer moves
            if move not in killer_moves[depth]:
                killer_moves[depth].insert(0, move)
                killer_moves[depth].pop()
            break
    
    return alpha

def quiescence_search(board, alpha, beta, evaluate_func):
    """
    A specialized search to evaluate non-quiescent positions.
    It only considers captures to avoid the horizon effect.
    NOW WITH CORRECT EGDB INTEGRATION.
    """
    total_pieces = board.red_left + board.white_left
    if egdb_driver and egdb_driver.initialized and total_pieces <= 10:
        result, mtc = egdb_driver.probe(board) # <-- GET MTC
        if result in (DB_WIN, DB_LOSS, DB_DRAW):
            # If the DB has a definitive result, use it to create a precise score.
            # The score is from the perspective of the current player to move.
            if result == DB_WIN:
                # A faster win (lower mtc) is better. Score is higher.
                return 10000 - mtc
            elif result == DB_LOSS:
                # A longer loss (higher mtc) is better. Score is less negative.
                return -10000 + mtc
            else: # DB_DRAW
                return 0

    # If EGDB has no result, proceed with the original evaluation logic.
    stand_pat = evaluate_func(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat
        
    moves = board.get_all_valid_moves(board.turn)
    
    # Filter for jumps only (captures)
    jumps = [move for move in moves if abs(move[0][0] - move[1][0]) == 2]

    for move in jumps:
        new_board = board.apply_move(move)
        score = -quiescence_search(new_board, -beta, -alpha, evaluate_func)
        
        alpha = max(alpha, score)
        if alpha >= beta:
            return beta

    return alpha
