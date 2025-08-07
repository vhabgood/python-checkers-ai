# engine/search.py
from .constants import *
from .evaluation import evaluate_board_static
from .board import Board

def _get_mvv_lva_score(board, move):
    """
    Calculates a score for a capture move based on Most Valuable Victim - Least Valuable Aggressor.
    """
    start, end = move
    aggressor = board[start[0]][start[1]]
    victim_pos = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
    victim = board[victim_pos[0]][victim_pos[1]]
    victim_value = PIECE_VALUES.get(victim, 0) * 100
    aggressor_value = PIECE_VALUES.get(aggressor, 0)
    return victim_value - aggressor_value

def _record_killer_move(move, depth, killer_moves):
    """Updates the killer moves table for a given depth."""
    if move != killer_moves[depth][0]:
        killer_moves[depth][1] = killer_moves[depth][0]
        killer_moves[depth][0] = move

def _static_quiescence_search(main_game, temp_board_obj, alpha, beta, maximizing_player, eval_counter):
    """
    Performs a search extension for capture moves to stabilize the evaluation.
    Uses the main_game for its shared transposition table.
    """
    eval_counter[0] += 1
    
    current_hash = temp_board_obj.hash
    entry = main_game.transposition_table.get(current_hash)
    if entry:
        return entry['score'], []

    stand_pat = evaluate_board_static(temp_board_obj.board, temp_board_obj.turn)
    
    if maximizing_player:
        alpha = max(alpha, stand_pat)
    else:
        beta = min(beta, stand_pat)
    
    if beta <= alpha:
        return stand_pat, []

    capture_moves = temp_board_obj.get_all_possible_moves(temp_board_obj.turn)
    if not capture_moves or abs(capture_moves[0][0][0] - capture_moves[0][1][0]) != 2:
        return stand_pat, []

    capture_moves.sort(key=lambda m: _get_mvv_lva_score(temp_board_obj.board, m), reverse=True)
    
    best_path = []
    for start, end in capture_moves:
        child_game = temp_board_obj.clone()
        further_jumps = child_game.perform_move_for_search(start, end)
        
        score, path = _static_quiescence_search(main_game, child_game, alpha, beta, not maximizing_player if not further_jumps else maximizing_player, eval_counter)

        if maximizing_player:
            if score > stand_pat:
                stand_pat = score
                best_path = [(start, end)] + path
            alpha = max(alpha, stand_pat)
        else:
            if score < stand_pat:
                stand_pat = score
                best_path = [(start, end)] + path
            beta = min(beta, stand_pat)
        
        if beta <= alpha:
            break
            
    return stand_pat, best_path

def static_minimax(main_game, temp_board_obj, depth, alpha, beta, maximizing_player, eval_counter, progress_callback, killer_moves, path):
    """
    The main search function using minimax with alpha-beta pruning and advanced heuristics.
    """
    current_hash = temp_board_obj.hash
    entry = main_game.transposition_table.get(current_hash)
    if entry and entry['depth'] >= depth:
        if entry['flag'] == 'EXACT': return entry['score'], entry['path']
        elif entry['flag'] == 'LOWERBOUND' and entry['score'] >= beta: return entry['score'], entry['path']
        elif entry['flag'] == 'UPPERBOUND' and entry['score'] <= alpha: return entry['score'], entry['path']

    if depth <= 0:
        return _static_quiescence_search(main_game, temp_board_obj, alpha, beta, maximizing_player, eval_counter)
    
    all_moves = temp_board_obj.game_board.get_all_possible_moves(temp_board_obj.game_board.turn)
    if not all_moves:
        return evaluate_board_static(temp_board_obj.game_board.board, temp_board_obj.game_board.turn), []
    
    captures = [m for m in all_moves if abs(m[0][0] - m[1][0]) == 2]
    quiet_moves = [m for m in all_moves if abs(m[0][0] - m[1][0]) != 2]
    captures.sort(key=lambda m: _get_mvv_lva_score(temp_board_obj.game_board.board, m), reverse=True)
    
    killers = killer_moves[depth]
    killer_quiet_moves = [m for m in quiet_moves if m in killers]
    other_quiet_moves = [m for m in quiet_moves if m not in killers]
    ordered_moves = captures + killer_quiet_moves + other_quiet_moves

    best_path = []; original_alpha = alpha
    best_score = -float('inf') if maximizing_player else float('inf')
    
    for i, (start, end) in enumerate(ordered_moves):
        child_game = temp_board_obj.clone()
        further_jumps = child_game.perform_move_for_search(start, end)
        
        is_capture = abs(start[0] - end[0]) == 2
        
        if depth <= 2 and not is_capture and not further_jumps:
            static_eval = evaluate_board_static(child_game.game_board.board, child_game.game_board.turn)
            if maximizing_player and static_eval + FUTILITY_MARGIN <= alpha: continue
            elif not maximizing_player and static_eval - FUTILITY_MARGIN >= beta: continue
        
        if progress_callback: progress_callback(None, None, path + [(start, end)])
        
        search_depth = depth - 1
        if depth >= 3 and i > 2 and not is_capture: search_depth -= 1
        
        score, sub_path = static_minimax(main_game, child_game, search_depth, alpha, beta, not further_jumps, eval_counter, progress_callback, killer_moves, path + [(start, end)])

        if search_depth < depth - 1 and ((maximizing_player and score > alpha) or (not maximizing_player and score < beta)):
             score, sub_path = static_minimax(main_game, child_game, depth - 1, alpha, beta, not further_jumps, eval_counter, progress_callback, killer_moves, path + [(start, end)])

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
    main_game.transposition_table[current_hash] = {'score': best_score, 'depth': depth, 'flag': flag, 'path': best_path}
    
    return best_score, best_path
