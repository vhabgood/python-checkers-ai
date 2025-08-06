# engine/search.py
from .constants import *
from .evaluation import evaluate_board_static
from .board import Board

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

def _static_quiescence_search(game, alpha, beta, maximizing_player, eval_counter):
    eval_counter[0] += 1
    
    entry = game.transposition_table.get(game.hash)
    if entry: return entry['score'], []

    current_board_state = game.game_board.board
    current_turn = game.game_board.turn
    
    stand_pat = evaluate_board_static(current_board_state, current_turn)
    if maximizing_player:
        alpha = max(alpha, stand_pat)
    else:
        beta = min(beta, stand_pat)
    
    if beta <= alpha: return stand_pat, []

    capture_moves = [m for m in game.game_board.get_all_possible_moves(current_turn) if abs(m[0][0] - m[1][0]) == 2]
    if not capture_moves: return stand_pat, []

    capture_moves.sort(key=lambda m: _get_mvv_lva_score(current_board_state, m), reverse=True)
    
    best_path = []
    for start, end in capture_moves:
        temp_game = game.clone()
        further_jumps = temp_game.perform_move_for_search(start, end)
        score, path = _static_quiescence_search(temp_game, alpha, beta, not maximizing_player if not further_jumps else maximizing_player, eval_counter)
        if maximizing_player:
            if score > stand_pat: stand_pat = score; best_path = [(start, end)] + path
            alpha = max(alpha, stand_pat)
        else:
            if score < stand_pat: stand_pat = score; best_path = [(start, end)] + path
            beta = min(beta, stand_pat)
        if beta <= alpha: break
    return stand_pat, best_path

def static_minimax(game, depth, alpha, beta, maximizing_player, eval_counter, progress_callback, killer_moves, path):
    entry = game.transposition_table.get(game.hash)
    if entry and entry['depth'] >= depth:
        if entry['flag'] == 'EXACT': return entry['score'], entry['path']
        elif entry['flag'] == 'LOWERBOUND' and entry['score'] >= beta: return entry['score'], entry['path']
        elif entry['flag'] == 'UPPERBOUND' and entry['score'] <= alpha: return entry['score'], entry['path']

    if depth == 0: return _static_quiescence_search(game, alpha, beta, maximizing_player, eval_counter)
    
    all_moves = game.game_board.get_all_possible_moves(game.game_board.turn)
    if not all_moves:
        return evaluate_board_static(game.game_board.board, game.game_board.turn), []
    
    captures = [m for m in all_moves if abs(m[0][0] - m[1][0]) == 2]
    quiet_moves = [m for m in all_moves if abs(m[0][0] - m[1][0]) != 2]
    captures.sort(key=lambda m: _get_mvv_lva_score(game.game_board.board, m), reverse=True)
    killers = killer_moves[depth]
    killer_quiet_moves = [m for m in quiet_moves if m in killers]
    other_quiet_moves = [m for m in quiet_moves if m not in killers]
    ordered_moves = captures + killer_quiet_moves + other_quiet_moves

    best_path = []; original_alpha = alpha
    best_score = -float('inf') if maximizing_player else float('inf')
    
    for i, (start, end) in enumerate(ordered_moves):
        temp_game = game.clone()
        further_jumps = temp_game.perform_move_for_search(start, end)
        
        is_capture = abs(start[0] - end[0]) == 2
        if depth <= 2 and not is_capture and not further_jumps and not any(abs(s[0]-e[0])==2 for s,e in temp_game.game_board.get_all_possible_moves(temp_game.game_board.turn)):
            static_eval = evaluate_board_static(temp_game.game_board.board, temp_game.game_board.turn)
            if maximizing_player and static_eval + FUTILITY_MARGIN <= alpha: continue
            elif not maximizing_player and static_eval - FUTILITY_MARGIN >= beta: continue
        
        if progress_callback: progress_callback(None, None, path + [(start, end)])
        search_depth = depth - 1
        if depth >= 3 and i > 2 and not is_capture: search_depth -= 1
        
        score, sub_path = static_minimax(temp_game, search_depth, alpha, beta, not further_jumps, eval_counter, progress_callback, killer_moves, path + [(start, end)])

        if search_depth < depth - 1 and ((maximizing_player and score > alpha) or (not maximizing_player and score < beta)):
             score, sub_path = static_minimax(temp_game, depth - 1, alpha, beta, not further_jumps, eval_counter, progress_callback, killer_moves, path + [(start, end)])

        if maximizing_player:
            if score > best_score: best_score, best_path = score, [(start, end)] + sub_path
            alpha = max(alpha, best_score)
        else:
            if score < best_score: best_score, best_path = score, [(start, end)] + sub_path
            beta = min(beta, best_score)
            
        if alpha >= beta:
            if not is_capture: _record_killer_move((start, end), depth, killer_moves)
            break
            
    if best_score <= original_alpha: flag = 'UPPERBOUND'
    elif best_score >= beta: flag = 'LOWERBOUND'
    else: flag = 'EXACT'
    game.transposition_table[game.hash] = {'score': best_score, 'depth': depth, 'flag': flag, 'path': best_path}
    
    return best_score, best_path
