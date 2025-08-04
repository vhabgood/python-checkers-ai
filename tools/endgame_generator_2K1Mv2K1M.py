# endgame_generator_2K1Mv2K1M.py
import pickle
from itertools import combinations
import time
import os

# --- Mappings ---
ACF_TO_COORD, COORD_TO_ACF = {}, {}
num = 1
for r in range(8):
    for c in range(8):
        if (r + c) % 2 == 1:
            ACF_TO_COORD[num], COORD_TO_ACF[(r, c)] = (r, c), num
            num += 1
VALID_SQUARES = list(ACF_TO_COORD.keys())

# --- Helper Functions for Move Logic ---

def get_moves(position, db_2k1m_v_2k):
    """
    Generates all legal moves for a 2K1M v 2K1M position.
    Position: (rk_sqs, rm_sq, wk_sqs, wm_sq, turn)
    """
    rk_sqs = set(position[:2])
    rm_sq = position[2]
    wk_sqs = set(position[3:5])
    wm_sq = position[5]
    turn = position[6]
    
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    # --- FIX: Corrected variable name from ACF_TO_ACF to ACF_TO_COORD ---
    board[ACF_TO_COORD[rm_sq]] = 'r'
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})
    board[ACF_TO_COORD[wm_sq]] = 'w'
    moves = []

    pieces_to_move, opponent_color = (list(rk_sqs) + [rm_sq], 'W') if turn == 'r' else (list(wk_sqs) + [wm_sq], 'R')
    
    # Check for Jumps First (Terminal)
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        is_king = piece_sq in rk_sqs or piece_sq in wk_sqs
        move_dirs = [(-1,1),(1,1),(-1,-1),(1,-1)] if is_king else [(1,-1),(1,1)] if turn=='r' else [(-1,-1),(-1,1)]
        
        for dr, dc in move_dirs:
            jump_over_coord = (r_start + dr, c_start + dc)
            land_coord = (r_start + 2*dr, c_start + 2*dc)
            
            if land_coord in COORD_TO_ACF and land_coord not in board and jump_over_coord in board and board[jump_over_coord].lower() != turn:
                jumped_piece = board[jump_over_coord]
                jumped_sq = COORD_TO_ACF[jump_over_coord]
                
                if turn == 'r': # Red captures
                    if jumped_piece == 'W': # Red captures a king
                        return [{'is_win': True}]
                    else: # Red captures a man
                        next_key = tuple(sorted(rk_sqs)) + (rm_sq,) + tuple(sorted(wk_sqs)) + ('w',)
                        outcome = db_2k1m_v_2k.get(next_key)
                        return [{'is_terminal': True, 'outcome': outcome}]
                else: # White captures
                    if jumped_piece == 'R': # White captures a king
                        return [{'is_loss_for_red': True}]
                    else: # White captures a man
                        return [{'is_draw': True}]

    # No Jumps, find Simple Moves
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        is_king = piece_sq in rk_sqs or piece_sq in wk_sqs
        move_dirs = [(-1,1),(1,1),(-1,-1),(1,-1)] if is_king else [(1,-1),(1,1)] if turn=='r' else [(-1,-1),(-1,1)]
        for dr, dc in move_dirs:
            r_new, c_new = r_start + dr, c_start + dc
            if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                new_sq = COORD_TO_ACF[(r_new, c_new)]
                next_rk, next_rm, next_wk, next_wm = list(rk_sqs), rm_sq, list(wk_sqs), wm_sq
                next_turn = 'w' if turn == 'r' else 'r'
                
                if turn == 'r':
                    if is_king: next_rk.remove(piece_sq); next_rk.append(new_sq)
                    else: next_rm = new_sq
                else: # White's turn
                    if is_king: next_wk.remove(piece_sq); next_wk.append(new_sq)
                    else: next_wm = new_sq

                if (turn == 'r' and not is_king and r_new == 7) or \
                   (turn == 'w' and not is_king and r_new == 0):
                    moves.append({'is_draw': True})
                    continue

                new_pos = tuple(sorted(next_rk)) + (next_rm,) + tuple(sorted(next_wk)) + (next_wm,) + (next_turn,)
                moves.append({'key': new_pos})
    return moves


def generate_2K1Mv2K1M_positions():
    positions = set()
    print("Generating all combinations of 6 pieces...")
    red_man_invalid = {29, 30, 31, 32}
    white_man_invalid = {1, 2, 3, 4}
    
    for squares in combinations(VALID_SQUARES, 6):
        for red_squares_combo in combinations(squares, 3):
            red_squares = set(red_squares_combo)
            white_squares = set(squares) - red_squares
            for rm_sq in red_squares:
                if rm_sq in red_man_invalid: continue
                rk_sqs = tuple(sorted(list(red_squares - {rm_sq})))
                for wm_sq in white_squares:
                    if wm_sq in white_man_invalid: continue
                    wk_sqs = tuple(sorted(list(white_squares - {wm_sq})))
                    key = rk_sqs + (rm_sq,) + wk_sqs + (wm_sq,)
                    positions.add(key + ('r',))
                    positions.add(key + ('w',))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_2k1m_vs_2k1m.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

def load_database(filename):
    if not os.path.exists(filename):
        print(f"FATAL ERROR: Helper database '{filename}' not found. Cannot proceed.")
        exit()
    print(f"Loading helper database: {filename}")
    with open(filename, "rb") as f: return pickle.load(f)

if __name__ == '__main__':
    start_time = time.time()
    db_2k1m_v_2k_loaded = load_database("db_2k1m_vs_2k.pkl")
    endgame_db = {}
    all_positions = generate_2K1Mv2K1M_positions()
    ply = 1
    
    print("\nStarting retrograde analysis for 2K1M v 2K1M...")
    print("This will take many hours.")
    print("Finding all Win-in-1 positions for Red...")
    newly_solved_positions = []
    for pos in all_positions:
        if pos[6] == 'r':
            moves = get_moves(pos, db_2k1m_v_2k_loaded)
            if any(m.get('is_win') or (m.get('is_terminal') and m.get('outcome', 0) > 0) for m in moves):
                endgame_db[pos] = 1
                newly_solved_positions.append(pos)
    print(f"Found {len(newly_solved_positions)} Win-in-1 positions.")
    
    while newly_solved_positions:
        ply += 1
        last_solved = newly_solved_positions; newly_solved_positions = []
        
        if ply % 2 == 0: # Even Ply: White's turn
            print(f"\nSolving Ply {ply}: Finding positions where White must move into a Red win...")
            target_value = ply - 1
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[6] == 'w':
                    moves = get_moves(pos, db_2k1m_v_2k_loaded)
                    if not moves or any(m.get('is_loss_for_red') or m.get('is_draw') for m in moves): continue
                    
                    all_moves_are_losses = True
                    for move in moves:
                        if move.get('is_terminal'):
                            if move['outcome'] is None or move['outcome'] > 0: all_moves_are_losses=False; break
                        elif endgame_db.get(move['key']) != target_value: all_moves_are_losses=False; break
                    if all_moves_are_losses:
                        endgame_db[pos] = -ply
                        newly_solved_positions.append(pos)
        else: # Odd Ply: Red's turn
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[6] == 'r':
                    moves = get_moves(pos, db_2k1m_v_2k_loaded)
                    can_force_win = False
                    for move in moves:
                        if move.get('is_win'): can_force_win = True; break
                        if move.get('is_draw'): continue
                        if move.get('is_terminal'):
                            if move['outcome'] is not None and move['outcome'] > 0: can_force_win = True; break
                        elif endgame_db.get(move.get('key')) == target_value: can_force_win = True; break
                    if can_force_win:
                        endgame_db[pos] = ply; newly_solved_positions.append(pos)

        if newly_solved_positions: print(f"Found {len(newly_solved_positions)} positions solved at ply {ply}.")

    print("\nWin/Loss analysis complete. Marking remaining positions as draws...")
    draw_count = 0
    for pos in all_positions:
        if pos not in endgame_db: endgame_db[pos] = 0; draw_count += 1
    print(f"Marked {draw_count} positions as draws.")
    
    print("\n--------------------")
    print("Retrograde analysis complete!")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    
    save_database(endgame_db)
