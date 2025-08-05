# engine/search.py
from .constants import *
from .evaluation import evaluate_board_static
from .checkers_game import Checkers

def _get_mvv_lva_score(board, move):
    start, end = move
    aggressor = board[start[0]][start[1]]
    victim_pos = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
    victim = board[victim_pos[0]][victim_pos[1]]
    victim_value = PIECE_VALUES.get(victim, 0) * 100
    aggressor_value = PIECE_VALUES.get(aggressor, 0)
    return victim_value - aggressor_value

def _record_killer_move(move, depth, killer_moves):
    if move != killer_moves[depth][0]:
        killer_moves[depth][1] = killer_moves[depth][0]
        killer_moves[depth][0] = move

def _static_quiescence_search(game, board, turn, alpha, beta, maximizing_player, eval_counter):
    eval_counter[0] += 1
    entry = game.transposition_table.get(game.hash)
    if entry: return entry['score'], []
    game_state = Checkers(board, turn, load_resources=False)
    capture_moves = [m for m in game_state.get_all_possible_moves(turn) if abs(m[0][0] - m[1][0]) == 2]
    if not capture_moves: return evaluate_board_static(board, turn), []
    capture_moves.sort(key=lambda m: _get_mvv_lva_score(board, m), reverse=True)
    if maximizing_player:
        best_value = -float('inf')
        for start, end in capture_moves:
            temp_game = Checkers([row[:] for row in board], turn, load_resources=False); temp_game.hash = game.hash; temp_game.perform_move_for_search(start, end)
            value, _ = _static_quiescence_search(temp_game, temp_game.board, temp_game.turn, alpha, beta, bool(temp_game.turn != turn), eval_counter)
            best_value = max(best_value, value)
            alpha = max(alpha, best_value)
            if beta <= alpha: break
        return best_value, []
    else:
        best_value = float('inf')
        for start, end in capture_moves:
            temp_game = Checkers([row[:] for row in board], turn, load_resources=False); temp_game.hash = game.hash; temp_game.perform_move_for_search(start, end)
            value, _ = _static_quiescence_search(temp_game, temp_game.board, temp_game.turn, alpha, beta, not (temp_game.turn != turn), eval_counter)
            best_value = min(best_value, value)
            beta = min(beta, best_value)
            if beta <= alpha: break
        return best_value, []

def static_minimax(game, board, turn, depth, alpha, beta, maximizing_player, eval_counter, progress_callback, killer_moves, path):
    entry = game.transposition_table.get(game.hash)
    if entry and entry['depth'] >= depth:
        if entry['flag'] == 'EXACT': return entry['score'], entry['path']
        elif entry['flag'] == 'LOWERBOUND' and entry['score'] > alpha: alpha = entry['score']
        elif entry['flag'] == 'UPPERBOUND' and entry['score'] < beta: beta = entry['score']
        if alpha >= beta: return entry['score'], entry['path']

    if depth == 0: return _static_quiescence_search(game, board, turn, alpha, beta, maximizing_player, eval_counter)
    
    game_state = Checkers(board, turn, load_resources=False)
    if game_state.check_win_condition() is not None: return evaluate_board_static(board, turn), []
    all_moves = game_state.get_all_possible_moves(turn)
    if not all_moves: return evaluate_board_static(board, turn), []
    
    captures = [m for m in all_moves if abs(m[0][0] - m[1][0]) == 2]
    quiet_moves = [m for m in all_moves if abs(m[0][0] - m[1][0]) != 2]
    captures.sort(key=lambda m: _get_mvv_lva_score(board, m), reverse=True)
    killers = killer_moves[depth]
    killer_quiet_moves = [m for m in quiet_moves if m in killers]
    other_quiet_moves = [m for m in quiet_moves if m not in killers]
    ordered_moves = captures + killer_quiet_moves + other_quiet_moves

    best_path = []
    original_alpha = alpha
    if maximizing_player:
        max_eval = -float('inf')
        for i, (start, end) in enumerate(ordered_moves):
            temp_game = Checkers([row[:] for row in board], turn, load_resources=False); temp_game.hash = game.hash; further_jumps = temp_game.perform_move_for_search(start, end)
            is_capture = abs(start[0] - end[0]) == 2
            if depth <= 2 and not is_capture and not further_jumps and not any(abs(s[0]-e[0])==2 for s,e in temp_game.get_all_possible_moves(temp_game.turn)):
                static_eval = evaluate_board_static(temp_game.board, temp_game.turn)
                if static_eval + FUTILITY_MARGIN <= alpha: continue
            
            if progress_callback: progress_callback(None, None, path + [(start, end)])
            eval_score, sub_path = static_minimax(temp_game, temp_game.board, temp_game.turn, depth - 1, alpha, beta, not further_jumps, eval_counter, progress_callback, killer_moves, path + [(start, end)])
            
            if eval_score > max_eval: max_eval, best_path = eval_score, [(start, end)] + sub_path
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                if not is_capture: _record_killer_move((start, end), depth, killer_moves)
                break
        flag = 'EXACT' if max_eval > original_alpha and max_eval < beta else 'LOWERBOUND' if max_eval >= beta else 'UPPERBOUND'
        game.transposition_table[game.hash] = {'score': max_eval, 'depth': depth, 'flag': flag, 'path': best_path}
        return max_eval, best_path
    else: # Minimizing Player
        min_eval = float('inf')
        for i, (start, end) in enumerate(ordered_moves):
            temp_game = Checkers([row[:] for row in board], turn, load_resources=False); temp_game.hash = game.hash; further_jumps = temp_game.perform_move_for_search(start, end)
            is_capture = abs(start[0] - end[0]) == 2
            if depth <= 2 and not is_capture and not further_jumps and not any(abs(s[0]-e[0])==2 for s,e in temp_game.get_all_possible_moves(temp_game.turn)):
                static_eval = evaluate_board_static(temp_game.board, temp_game.turn)
                if static_eval - FUTILITY_MARGIN >= beta: continue

            if progress_callback: progress_callback(None, None, path + [(start, end)])
            eval_score, sub_path = static_minimax(temp_game, temp_game.board, temp_game.turn, depth - 1, alpha, beta, bool(further_jumps), eval_counter, progress_callback, killer_moves, path + [(start, end)])
            if eval_score < min_eval: min_eval, best_path = eval_score, [(start, end)] + sub_path
            beta = min(beta, eval_score)
            if beta <= alpha:
                if not is_capture: _record_killer_move((start, end), depth, killer_moves)
                break
        flag = 'EXACT' if min_eval > alpha and min_eval < beta else 'UPPERBOUND' if min_eval <= alpha else 'LOWERBOUND'
        game.transposition_table[game.hash] = {'score': min_eval, 'depth': depth, 'flag': flag, 'path': best_path}
        return min_eval, best_path
