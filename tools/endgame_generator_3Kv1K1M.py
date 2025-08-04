# endgame_generator_3Kv1K1M.py
import pickle
from itertools import combinations
import time

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
    Generates all legal moves for the current player from a given 3K v 1K1M position.
    Position: (rk1, rk2, rk3, wk, wm, turn)
    """
    rk_sqs = set(position[:3])
    wk_sq = position[3]
    wm_sq = position[4]
    turn = position[5]
    
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board[ACF_TO_COORD[wk_sq]] = 'W'
    board[ACF_TO_COORD[wm_sq]] = 'w'

    moves = []
    
    # --- RED'S TURN ---
    if turn == 'r':
        # Check for jumps first (always winning)
        for rk_sq in rk_sqs:
            r_start, c_start = ACF_TO_COORD[rk_sq]
            for dr in [-1, 1]:
                for dc in [-1, 1]:
                    jump_over_coord = (r_start + dr, c_start + dc)
                    land_coord = (r_start + 2*dr, c_start + 2*dc)
                    if land_coord in COORD_TO_ACF and land_coord not in board:
                        if jump_over_coord == ACF_TO_COORD[wk_sq] or jump_over_coord == ACF_TO_COORD[wm_sq]:
                            return [{'is_win': True}] # Any capture is a win

        # No jumps, find simple moves
        for rk_sq in rk_sqs:
            r_start, c_start = ACF_TO_COORD[rk_sq]
            for dr in [-1, 1]:
                for dc in [-1, 1]:
                    r_new, c_new = r_start + dr, c_start + dc
                    if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                        new_sq = COORD_TO_ACF[(r_new, c_new)]
                        next_rk_sqs = list(rk_sqs); next_rk_sqs.remove(rk_sq); next_rk_sqs.append(new_sq)
                        new_pos = tuple(sorted(next_rk_sqs)) + (wk_sq, wm_sq, 'w')
                        moves.append({'key': new_pos})
        return moves

    # --- WHITE'S TURN ---
    else: # turn == 'w'
        # White King moves
        r_start, c_start = ACF_TO_COORD[wk_sq]
        for dr in [-1, 1]:
            for dc in [-1, 1]:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    new_pos = tuple(sorted(rk_sqs)) + (new_sq, wm_sq, 'r')
                    moves.append({'key': new_pos})
        
        # White Man moves
        r_start, c_start = ACF_TO_COORD[wm_sq]
        for dc in [-1, 1]:
            r_new, c_new = r_start - 1, c_start + dc # Men only move forward
            if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                new_sq = COORD_TO_ACF[(r_new, c_new)]
                # PROMOTION!
                if r_new == 0:
                    promoted_key = tuple(sorted(rk_sqs)) + tuple(sorted((wk_sq, new_sq))) + ('r',)
                    # Look up the result in the 3v2 database
                    outcome = db_3v2_kings.get(promoted_key)
                    moves.append({'key': promoted_key, 'is_terminal': True, 'outcome': outcome})
                else: # Regular move
                    new_pos = tuple(sorted(rk_sqs)) + (wk_sq, new_sq, 'r')
                    moves.append({'key': new_pos})
        return moves

def generate_3Kv1K1M_positions():
    """Generates all positions for 3 Red Kings vs 1 White King & 1 White Man."""
    positions = set()
    print(f"Generating all combinations of 5 pieces...")
    man_possible_squares = [sq for sq in VALID_SQUARES if ACF_TO_COORD[sq][0] != 0]

    for squares in combinations(VALID_SQUARES, 5):
        for wk_sq in squares:
            remaining_after_wk = list(set(squares) - {wk_sq})
            for wm_sq in remaining_after_wk:
                # Constraint: man cannot be on king row
                if ACF_TO_COORD[wm_sq][0] == 0:
                    continue
                
                rk_sqs = tuple(sorted(list(set(remaining_after_wk) - {wm_sq})))
                key = rk_sqs + (wk_sq, wm_sq)
                positions.add(key + ('r',))
                positions.add(key + ('w',))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_3v1k1m.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

def load_database(filename):
    print(f"Loading helper database: {filename}")
    with open(filename, "rb") as f: return pickle.load(f)

# --- Main Execution ---
if __name__ == '__main__':
    start_time = time.time()
    
    # Load the crucial 3v2 Kings database
    db_3v2_kings_loaded = load_database("db_3v2_kings.pkl")

    endgame_db = {}
    all_positions = generate_3Kv1K1M_positions()
    ply = 1
    
    print("\nStarting retrograde analysis for 3K v 1K1M...")
    print("Finding all Win-in-1 positions for Red...")
    newly_solved_positions = []
    for pos in all_positions:
        if pos[5] == 'r' and any(m.get('is_win') for m in get_moves(pos, db_3v2_kings_loaded)):
            endgame_db[pos] = 1
            newly_solved_positions.append(pos)
    print(f"Found {len(newly_solved_positions)} Win-in-1 positions.")
    
    while newly_solved_positions:
        ply += 1
        last_solved_positions = newly_solved_positions
        newly_solved_positions = []
        
        if ply % 2 == 0: # Even Ply: White's turn
            print(f"\nSolving Ply {ply}: Finding positions where White must move into a Red win...")
            target_value = ply - 1
            
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[5] == 'w':
                    moves = get_moves(pos, db_3v2_kings_loaded)
                    if not moves: continue

                    all_outcomes_are_loss = True
                    for move in moves:
                        if move.get('is_terminal'): # Promotion happened
                            # If outcome is positive (Red win) or 0 (draw), it's a loss/draw for White.
                            # We consider forcing a draw from a losing position a "good" move for White.
                            if move['outcome'] is None or move['outcome'] > 0:
                                all_outcomes_are_loss = False; break
                        else: # Regular move
                            if endgame_db.get(move['key']) != target_value:
                                all_outcomes_are_loss = False; break
                    
                    if all_outcomes_are_loss:
                        endgame_db[pos] = -ply
                        newly_solved_positions.append(pos)
        
        else: # Odd Ply: Red's turn
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[5] == 'r':
                    moves = get_moves(pos, db_3v2_kings_loaded)
                    if any(endgame_db.get(m.get('key')) == target_value for m in moves):
                        endgame_db[pos] = ply
                        newly_solved_positions.append(pos)

        if newly_solved_positions:
            print(f"Found {len(newly_solved_positions)} positions solved at ply {ply}.")

    print("\nWin/Loss analysis complete. Marking remaining positions as draws...")
    draw_count = 0
    for pos in all_positions:
        if pos not in endgame_db:
            endgame_db[pos] = 0
            draw_count += 1
    print(f"Marked {draw_count} positions as draws.")
    
    print("\n--------------------")
    print("Retrograde analysis complete!")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    
    save_database(endgame_db)

