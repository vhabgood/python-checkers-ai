# endgame_generator_2K1Mv2K.py
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

def get_moves(position, db_3v2_kings):
    """
    Generates all legal moves for the current player from a 2K1M v 2K position.
    Position: (sorted_rk_sqs, rm_sq, sorted_wk_sqs, turn)
    """
    rk_sqs = set(position[:2])
    rm_sq = position[2]
    wk_sqs = set(position[3:5])
    turn = position[5]
    
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board[ACF_TO_COORD[rm_sq]] = 'r'
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})
    moves = []

    # --- RED'S TURN ---
    if turn == 'r':
        pieces_to_move = list(rk_sqs) + [rm_sq]
        # Check for Jumps
        for piece_sq in pieces_to_move:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            is_king = piece_sq in rk_sqs
            move_dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)] if is_king else [(1, -1), (1, 1)]
            for dr, dc in move_dirs:
                jump_over_coord = (r_start + dr, c_start + dc)
                land_coord = (r_start + 2*dr, c_start + 2*dc)
                if land_coord in COORD_TO_ACF and land_coord not in board and jump_over_coord in board and board[jump_over_coord] == 'W':
                    return [{'is_win': True}] # Any capture results in 2K1M vs 1K, a certain win.

        # No Jumps, find Simple Moves
        for piece_sq in pieces_to_move:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            is_king = piece_sq in rk_sqs
            move_dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)] if is_king else [(1, -1), (1, 1)] # Red man moves "down" the board rows
            for dr, dc in move_dirs:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    if is_king:
                        next_rk_sqs = list(rk_sqs); next_rk_sqs.remove(piece_sq); next_rk_sqs.append(new_sq)
                        new_pos = tuple(sorted(next_rk_sqs)) + (rm_sq,) + tuple(sorted(wk_sqs)) + ('w',)
                        moves.append({'key': new_pos})
                    else: # Man moved
                        if r_new == 7: # PROMOTION
                            promoted_key = tuple(sorted(list(rk_sqs) + [new_sq])) + tuple(sorted(wk_sqs)) + ('w',)
                            outcome = db_3v2_kings.get(promoted_key)
                            moves.append({'is_terminal': True, 'key': promoted_key, 'outcome': outcome})
                        else:
                            new_pos = tuple(sorted(rk_sqs)) + (new_sq,) + tuple(sorted(wk_sqs)) + ('w',)
                            moves.append({'key': new_pos})
        return moves

    # --- WHITE'S TURN ---
    else: # turn == 'w'
        # Check for Jumps
        for piece_sq in wk_sqs:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                jump_over_coord = (r_start + dr, c_start + dc)
                land_coord = (r_start + 2*dr, c_start + 2*dc)
                if land_coord in COORD_TO_ACF and land_coord not in board and jump_over_coord in board and board[jump_over_coord] != 'W':
                    if board[jump_over_coord] == 'R': return [{'is_loss': True}] # 1K1M vs 2K is a loss for Red
                    else: return [{'is_draw': True}] # 2K vs 2K is a draw
        
        # No Jumps, find Simple Moves
        for piece_sq in wk_sqs:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    next_wk_sqs = list(wk_sqs); next_wk_sqs.remove(piece_sq); next_wk_sqs.append(new_sq)
                    new_pos = tuple(sorted(rk_sqs)) + (rm_sq,) + tuple(sorted(next_wk_sqs)) + ('r',)
                    moves.append({'key': new_pos})
        return moves

def generate_2K1Mv2K_positions():
    positions = set()
    print("Generating all combinations of 5 pieces...")
    # Red man cannot start on his own king row
    man_invalid_squares = {29, 30, 31, 32}
    
    for squares in combinations(VALID_SQUARES, 5):
        for wk_combo in combinations(squares, 2):
            wk_sqs = tuple(sorted(wk_combo))
            remaining = list(set(squares) - set(wk_sqs))
            for rm_sq in remaining:
                if rm_sq in man_invalid_squares: continue
                rk_sqs = tuple(sorted(list(set(remaining) - {rm_sq})))
                key = rk_sqs + (rm_sq,) + wk_sqs
                positions.add(key + ('r',))
                positions.add(key + ('w',))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_2k1m_vs_2k.pkl"):
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
    db_3v2_kings_loaded = load_database("db_3v2_kings.pkl")
    endgame_db = {}
    all_positions = generate_2K1Mv2K_positions()
    ply = 1
    
    print("\nStarting retrograde analysis for 2K1M v 2K...")
    print("Finding all Win-in-1 positions for Red...")
    newly_solved_positions = []
    for pos in all_positions:
        if pos[5] == 'r' and any(m.get('is_win') for m in get_moves(pos, db_3v2_kings_loaded)):
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
                if pos[5] == 'w':
                    moves = get_moves(pos, db_3v2_kings_loaded)
                    if not moves or any(m.get('is_loss') or m.get('is_draw') for m in moves): continue
                    
                    if all(endgame_db.get(m['key']) == target_value for m in moves):
                        endgame_db[pos] = -ply
                        newly_solved_positions.append(pos)
        else: # Odd Ply: Red's turn
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[5] == 'r':
                    moves = get_moves(pos, db_3v2_kings_loaded)
                    can_force_win = False
                    for move in moves:
                        if move.get('is_terminal'): # Promotion
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
