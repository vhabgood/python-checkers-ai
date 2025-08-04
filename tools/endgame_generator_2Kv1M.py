# endgame_generator_2Kv1M.py
import pickle
from itertools import combinations
import time

# --- Mappings (same as before) ---
ACF_TO_COORD, COORD_TO_ACF = {}, {}
num = 1
for r in range(8):
    for c in range(8):
        if (r + c) % 2 == 1:
            ACF_TO_COORD[num], COORD_TO_ACF[(r, c)] = (r, c), num
            num += 1

VALID_SQUARES = list(ACF_TO_COORD.keys())

# --- Helper Functions for Move Logic ---

def get_king_moves_2v1M(position, board_map):
    """Generates Red King moves. Jumps mean an instant win."""
    rk1_sq, rk2_sq, wm_sq, turn = position
    moves = []
    # Any jump of the white man is a win.
    for piece_sq in [rk1_sq, rk2_sq]:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr in [-1, 1]:
            for dc in [-1, 1]:
                if (r_start + 2*dr, c_start + 2*dc) in COORD_TO_ACF: # Landing square is on board
                    if (r_start + dr, c_start + dc) == ACF_TO_COORD[wm_sq]: # Is the man the jumped piece?
                        return [] # JUMP FOUND = WIN
    
    # No jumps, find simple moves
    for piece_sq in [rk1_sq, rk2_sq]:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr in [-1, 1]:
            for dc in [-1, 1]:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board_map:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    if piece_sq == rk1_sq:
                        new_pos = tuple(sorted((new_sq, rk2_sq))) + (wm_sq, 'w')
                    else:
                        new_pos = tuple(sorted((rk1_sq, new_sq))) + (wm_sq, 'w')
                    moves.append(new_pos)
    return moves

def get_man_moves_2v1M(position, board_map):
    """Generates White Man moves. This can result in a promotion."""
    rk1_sq, rk2_sq, wm_sq, turn = position
    moves = []
    r_start, c_start = ACF_TO_COORD[wm_sq]
    
    # Jumps are forced, but it's impossible for a single man to jump a king.
    # We only need to check for simple moves.
    for dr in [-1]: # Man can only move "up" the board
        for dc in [-1, 1]:
            r_new, c_new = r_start + dr, c_start + dc
            if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board_map:
                new_sq = COORD_TO_ACF[(r_new, c_new)]
                # PROMOTION! The resulting state is a 2 Kings vs 1 King endgame.
                if r_new == 0:
                    promoted_pos = tuple(sorted((rk1_sq, rk2_sq))) + (new_sq, 'r')
                    moves.append({'type': 'promotion', 'key': promoted_pos})
                else: # Regular move
                    new_pos = tuple(sorted((rk1_sq, rk2_sq))) + (new_sq, 'r')
                    moves.append({'type': 'move', 'key': new_pos})
    return moves


# --- Database Generation Logic ---

def generate_2Kv1M_positions():
    """Generates all positions for 2 Red Kings vs 1 White Man."""
    positions = set()
    print(f"Generating all combinations of 2 Kings, 1 Man...")
    # A man cannot start on the king row, so we exclude those squares for the man.
    man_possible_squares = [sq for sq in VALID_SQUARES if ACF_TO_COORD[sq][0] != 0]

    for wm_sq in man_possible_squares:
        remaining_squares = list(VALID_SQUARES)
        remaining_squares.remove(wm_sq)
        for rk_squares in combinations(remaining_squares, 2):
            key = tuple(sorted(rk_squares))
            positions.add(key + (wm_sq, 'r'))
            positions.add(key + (wm_sq, 'w'))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_2v1_men.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

def load_database(filename):
    print(f"Loading helper database: {filename}")
    with open(filename, "rb") as f: return pickle.load(f)

# --- Main Execution ---

if __name__ == '__main__':
    start_time = time.time()
    
    # LOAD our previously solved database!
    db_2v1_kings_loaded = load_database("db_2v1_kings.pkl")

    endgame_db_2kv1m = {}
    all_positions = generate_2Kv1M_positions()
    
    ply = 1
    
    print("\nStarting retrograde analysis for 2 Kings vs 1 Man...")
    print("Finding all Win-in-1 positions...")
    newly_solved_positions = []
    for pos in all_positions:
        board_map = {ACF_TO_COORD[pos[0]]:'R', ACF_TO_COORD[pos[1]]:'R', ACF_TO_COORD[pos[2]]:'w'}
        if pos[3] == 'r' and not get_king_moves_2v1M(pos, board_map):
            endgame_db_2kv1m[pos] = 1
            newly_solved_positions.append(pos)

    print(f"Found {len(newly_solved_positions)} Win-in-1 positions.")
    
    while newly_solved_positions:
        ply += 1
        last_solved_positions = newly_solved_positions
        newly_solved_positions = []
        
        if ply % 2 == 0: # Even Ply: White's turn (finding losses)
            print(f"\nSolving Ply {ply}: Finding positions where White must move into a Red win...")
            target_value = ply - 1
            
            for pos in all_positions:
                if pos in endgame_db_2kv1m: continue
                if pos[3] == 'w':
                    board_map = {ACF_TO_COORD[pos[0]]:'R', ACF_TO_COORD[pos[1]]:'R', ACF_TO_COORD[pos[2]]:'w'}
                    moves = get_man_moves_2v1M(pos, board_map)
                    if not moves: continue
                    
                    all_moves_lead_to_loss = True
                    for move in moves:
                        if move['type'] == 'promotion':
                            # This is the key part! Look up the result in the other DB.
                            # We want the resulting position to be a known loss for White (negative value)
                            if db_2v1_kings_loaded.get(move['key'], 1) > 0:
                                all_moves_lead_to_loss = False; break
                        else: # Regular move
                            if endgame_db_2kv1m.get(move['key']) != target_value:
                                all_moves_lead_to_loss = False; break
                    
                    if all_moves_lead_to_loss:
                        endgame_db_2kv1m[pos] = -ply
                        newly_solved_positions.append(pos)

        else: # Odd Ply: Red's turn (finding wins)
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)

            for pos in all_positions:
                if pos in endgame_db_2kv1m: continue
                if pos[3] == 'r':
                    board_map = {ACF_TO_COORD[pos[0]]:'R', ACF_TO_COORD[pos[1]]:'R', ACF_TO_COORD[pos[2]]:'w'}
                    moves = get_king_moves_2v1M(pos, board_map)
                    
                    can_force_win = False
                    for move in moves:
                        if endgame_db_2kv1m.get(move) == target_value:
                            can_force_win = True; break
                    
                    if can_force_win:
                        endgame_db_2kv1m[pos] = ply
                        newly_solved_positions.append(pos)

        if newly_solved_positions:
            print(f"Found {len(newly_solved_positions)} positions solved at ply {ply}.")

    print("\n--------------------")
    print("Retrograde analysis complete!")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    
    save_database(endgame_db_2kv1m, "db_2v1_men.pkl")
