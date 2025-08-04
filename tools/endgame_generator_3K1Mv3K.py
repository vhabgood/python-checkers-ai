# endgame_generator_3K1Mv3K.py
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

def get_moves(position, db_4v2_kings):
    """
    Generates all legal moves for a 3K1M v 3K position.
    Position: (sorted_rk_sqs, rm_sq, sorted_wk_sqs, turn)
    """
    rk_sqs = set(position[:3])
    rm_sq = position[3]
    wk_sqs = set(position[4:7])
    turn = position[7]
    
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board[ACF_TO_COORD[rm_sq]] = 'r'
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})
    moves = []

    # --- RED'S TURN ---
    if turn == 'r':
        pieces_to_move = list(rk_sqs) + [rm_sq]
        for piece_sq in pieces_to_move:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            is_king = piece_sq in rk_sqs
            move_dirs = [(-1, 1), (1, 1), (-1, -1), (1, -1)] if is_king else [(1, -1), (1, 1)]
            for dr, dc in move_dirs:
                if 0 <= r_start + 2*dr < 8 and 0 <= c_start + 2*dc < 8:
                    jump_over_coord = (r_start + dr, c_start + dc)
                    land_coord = (r_start + 2*dr, c_start + 2*dc)
                    if land_coord not in board and COORD_TO_ACF.get(jump_over_coord) in wk_sqs:
                        return [{'is_win': True}] # Capture leads to 3K1M v 2K, a win.
        
        for piece_sq in pieces_to_move:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            is_king = piece_sq in rk_sqs
            move_dirs = [(-1, 1), (1, 1), (-1, -1), (1, -1)] if is_king else [(1, -1), (1, 1)]
            for dr, dc in move_dirs:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    if is_king:
                        next_rk = list(rk_sqs); next_rk.remove(piece_sq); next_rk.append(new_sq)
                        new_pos = tuple(sorted(next_rk)) + (rm_sq,) + tuple(sorted(wk_sqs)) + ('w',)
                        moves.append({'key': new_pos})
                    else: # Man moved
                        if r_new == 7: # PROMOTION
                            promoted_key = tuple(sorted(list(rk_sqs) + [new_sq])) + tuple(sorted(wk_sqs)) + ('w',)
                            outcome = db_4v2_kings.get(promoted_key)
                            moves.append({'is_terminal': True, 'key': promoted_key, 'outcome': outcome})
                        else:
                            new_pos = tuple(sorted(rk_sqs)) + (new_sq,) + tuple(sorted(wk_sqs)) + ('w',)
                            moves.append({'key': new_pos})
        return moves

    # --- WHITE'S TURN ---
    else:
        for piece_sq in wk_sqs:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            for dr, dc in [(-1, 1), (1, 1), (-1, -1), (1, -1)]:
                 if 0 <= r_start + 2*dr < 8 and 0 <= c_start + 2*dc < 8:
                    jump_over_coord = (r_start + dr, c_start + dc)
                    land_coord = (r_start + 2*dr, c_start + 2*dc)
                    jumped_sq = COORD_TO_ACF.get(jump_over_coord)
                    if land_coord not in board and (jumped_sq in rk_sqs or jumped_sq == rm_sq):
                        # White captures. This is a terminal state good for White (not a Red win).
                        # 3K vs 2K1M (if king captured) or 3K vs 2K (if man captured) are draws/wins for white.
                        return [{'is_loss_for_red': True}]

        for piece_sq in wk_sqs:
            r_start, c_start = ACF_TO_ACF[piece_sq]
            for dr, dc in [(-1, 1), (1, 1), (-1, -1), (1, -1)]:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    next_wk = list(wk_sqs); next_wk.remove(piece_sq); next_wk.append(new_sq)
                    new_pos = tuple(sorted(rk_sqs)) + (rm_sq,) + tuple(sorted(next_wk)) + ('r',)
                    moves.append({'key': new_pos})
        return moves

def generate_3K1Mv3K_positions():
    positions = set()
    print("Generating all combinations of 7 pieces... This may take a moment.")
    # This is too large to generate all at once. Let's do it strategically.
    # It's actually a 6 piece database, my apologies.
    print("Correction: Generating all combinations of 6 pieces...")
    man_invalid_squares = {29, 30, 31, 32}
    
    for squares in combinations(VALID_SQUARES, 6):
        # Choose 3 squares for white kings
        for wk_combo in combinations(squares, 3):
            wk_sqs = tuple(sorted(wk_combo))
            remaining = list(set(squares) - set(wk_sqs))
            # Choose 1 square for the red man from the remainder
            for i in range(len(remaining)):
                rm_sq = remaining[i]
                if rm_sq in man_invalid_squares: continue
                rk_sqs = tuple(sorted(remaining[:i] + remaining[i+1:]))
                
                key = rk_sqs + (rm_sq,) + wk_sqs
                positions.add(key + ('r',))
                positions.add(key + ('w',))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_3k1m_vs_3k.pkl"):
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
    db_4v2_kings_loaded = load_database("db_4v2_kings.pkl")
    endgame_db = {}
    all_positions = generate_3K1Mv3K_positions()
    ply = 1
    
    print("\nStarting retrograde analysis for 3K1M v 3K...")
    print("This will take a very long time.")
    print("Finding all Win-in-1 positions for Red...")
    newly_solved_positions = []
    for pos in all_positions:
        if pos[7] == 'r':
            moves = get_moves(pos, db_4v2_kings_loaded)
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
                if pos[7] == 'w':
                    moves = get_moves(pos, db_4v2_kings_loaded)
                    if not moves or any(m.get('is_loss_for_red') for m in moves): continue
                    
                    if all(endgame_db.get(m['key']) == target_value for m in moves):
                        endgame_db[pos] = -ply
                        newly_solved_positions.append(pos)
        else: # Odd Ply: Red's turn
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[7] == 'r':
                    moves = get_moves(pos, db_4v2_kings_loaded)
                    can_force_win = False
                    for move in moves:
                        if move.get('is_win'): can_force_win = True; break
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
