# endgame_generator_2Kv1M_V3.py
import pickle
from itertools import combinations
import time

ACF_TO_COORD, COORD_TO_ACF = {}, {}
num = 1
for r in range(8):
    for c in range(8):
        if (r + c) % 2 == 1:
            ACF_TO_COORD[num], COORD_TO_ACF[(r, c)] = (r, c), num
            num += 1
VALID_SQUARES = list(ACF_TO_COORD.keys())

def get_moves(position):
    rk_sqs, wm_sq, turn = set(position[:2]), position[2], position[3]
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board[ACF_TO_COORD[wm_sq]] = 'w'
    moves = []

    if turn == 'r': # Red's Turn (2 Kings)
        for rk_sq in rk_sqs:
            r_start, c_start = ACF_TO_COORD[rk_sq]
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                jump_over_coord = (r_start + dr, c_start + dc)
                land_coord = (r_start + 2 * dr, c_start + 2 * dc)
                if land_coord in COORD_TO_ACF and land_coord not in board and jump_over_coord == ACF_TO_COORD[wm_sq]:
                    return [] # Capture is a terminal win for Red

        for rk_sq in rk_sqs:
            r_start, c_start = ACF_TO_COORD[rk_sq]
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    next_rks = list(rk_sqs - {rk_sq}) + [new_sq]
                    moves.append(tuple(sorted(next_rks)) + (wm_sq, 'w'))
    else: # White's Turn (1 Man)
        r_start, c_start = ACF_TO_COORD[wm_sq]
        # Jumps are forced, but 2k vs 0 is a red win.
        for dr, dc in [(-1, -1), (-1, 1)]:
             jump_over_coord = (r_start + dr, c_start + dc)
             jumped_sq = COORD_TO_ACF.get(jump_over_coord)
             land_coord = (r_start + 2*dr, c_start + 2*dc)
             if land_coord in COORD_TO_ACF and land_coord not in board and jumped_sq in rk_sqs:
                 # White must jump, leading to a known loss.
                 # The analysis will discover this is a losing path.
                 remaining_king = list(rk_sqs - {jumped_sq})[0]
                 # This is a different endgame, but we must return the move.
                 # This path will eventually be marked as a Red win.
                 return [] # Treat as terminal for this DB.

        # Simple moves
        for dr, dc in [(-1, -1), (-1, 1)]:
            r_new, c_new = r_start + dr, c_start + dc
            if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                if r_new == 0: # Promotion
                    return [{'is_draw': True}] # 2K vs 1K is a known draw
                new_sq = COORD_TO_ACF[(r_new, c_new)]
                moves.append(tuple(sorted(rk_sqs)) + (new_sq, 'r'))
    return moves

def generate_2Kv1M_positions():
    positions = set()
    print("Generating 2 Kings vs 1 Man positions...")
    for squares in combinations(VALID_SQUARES, 3):
        for i in range(3):
            wm_sq = squares[i]
            rk_sqs = tuple(sorted(list(set(squares) - {wm_sq})))
            # Rule out illegal starting positions for the white man
            if ACF_TO_COORD[wm_sq][0] == 0: continue
            positions.add(rk_sqs + (wm_sq, 'r',))
            positions.add(rk_sqs + (wm_sq, 'w',))
    print(f"Generated {len(positions)} positions.")
    return list(positions)

def save_database(db, filename="db_2v1_men.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_2Kv1M_positions()

    # --- Step 1: Initialize terminal positions ---
    print("Finding all Win-in-1 and terminal draw positions...")
    newly_solved = []
    for pos in all_positions:
        moves = get_moves(pos)
        if not moves: # Red captures the man
            endgame_db[pos] = 1 # Red wins
            newly_solved.append(pos)
        elif any(isinstance(m, dict) and m.get('is_draw') for m in moves): # White promotes
            endgame_db[pos] = 0 # Draw
            newly_solved.append(pos)
    print(f"Found {len(newly_solved)} terminal positions (wins/draws).")

    # --- Step 2: Main Retrograde Analysis Loop ---
    ply = 1
    while newly_solved:
        ply += 1
        last_solved = newly_solved; newly_solved = []
        
        print(f"\nSolving Ply {ply}...")
        for pos in all_positions:
            if pos in endgame_db: continue
            
            moves = get_moves(pos)
            # Filter out special dict moves for the main loop
            key_moves = [m for m in moves if isinstance(m, tuple)]
            if not key_moves: continue
            
            turn = pos[3]
            # Red's turn (finding wins)
            if turn == 'r':
                target_value = -(ply - 1) # Look for a move to a White loss
                if any(endgame_db.get(move) == target_value for move in key_moves):
                    endgame_db[pos] = ply; newly_solved.append(pos)
            # White's turn (finding losses)
            else: # turn == 'w'
                target_value = ply - 1 # Look for moves to a Red win
                # Check if ALL moves lead to a known Red win
                if all(endgame_db.get(move) == target_value for move in key_moves):
                    endgame_db[pos] = -ply; newly_solved.append(pos)

        if newly_solved: print(f"Found {len(newly_solved)} positions solved at ply {ply}.")

    print("\nMarking all remaining unsolved positions as draws...")
    draw_count = 0
    for pos in all_positions:
        if pos not in endgame_db: endgame_db[pos] = 0; draw_count += 1
    print(f"Marked {draw_count} positions as draws.")
    
    print("\n--------------------")
    print("Retrograde analysis complete!")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    save_database(endgame_db)
