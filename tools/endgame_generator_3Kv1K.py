# endgame_generator_3Kv1K.py
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

def get_king_moves(position):
    """
    Generates all legal moves for the current player from a given 3K v 1K position.
    A position tuple is now (rk1, rk2, rk3, wk, turn).
    """
    # *** CHANGED: Unpacking 5 elements now ***
    rk1_sq, rk2_sq, rk3_sq, wk_sq, turn = position
    moves = []
    
    board = {
        ACF_TO_COORD[rk1_sq]: 'R',
        ACF_TO_COORD[rk2_sq]: 'R',
        ACF_TO_COORD[rk3_sq]: 'R',
        ACF_TO_COORD[wk_sq]: 'W'
    }

    pieces_to_move = []
    if turn == 'r':
        pieces_to_move = [(rk1_sq, 'R'), (rk2_sq, 'R'), (rk3_sq, 'R')]
        opponent_color = 'W'
    else: # turn == 'w'
        pieces_to_move = [(wk_sq, 'W')]
        opponent_color = 'R'

    # Check for Jumps First (Forced)
    for piece_sq, piece_color in pieces_to_move:
        if piece_color == 'R': # Only red kings can possibly jump the white king
            r_start, c_start = ACF_TO_COORD[piece_sq]
            for dr in [-1, 1]:
                for dc in [-1, 1]:
                    # Check if the square being jumped contains the white king
                    if (r_start + dr, c_start + dc) == ACF_TO_COORD[wk_sq]:
                        # Check if the landing square is on the board and empty
                        r_land, c_land = r_start + 2*dr, c_start + 2*dc
                        if (r_land, c_land) in COORD_TO_ACF and (r_land, c_land) not in board:
                            # A jump is possible, this is an immediate win.
                            return [] # Signifies a capture is available.

    # If no jumps, find simple moves
    for piece_sq, piece_color in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr in [-1, 1]:
            for dc in [-1, 1]:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    if turn == 'r':
                        # *** CHANGED: Rebuilding the position tuple for 3 kings ***
                        red_kings = [rk1_sq, rk2_sq, rk3_sq]
                        red_kings.remove(piece_sq)
                        red_kings.append(new_sq)
                        new_pos = tuple(sorted(red_kings)) + (wk_sq, 'w')
                        moves.append(new_pos)
                    else: # turn == 'w'
                        new_pos = tuple(sorted((rk1_sq, rk2_sq, rk3_sq))) + (new_sq, 'r')
                        moves.append(new_pos)
    return moves

# --- Database Generation Logic ---

def generate_3Kv1K_positions():
    """Generates all positions for 3 Red Kings vs 1 White King."""
    positions = set()
    print(f"Generating all combinations of 4 pieces on {len(VALID_SQUARES)} squares...")
    # *** CHANGED: combinations of 4 pieces now ***
    for squares in combinations(VALID_SQUARES, 4):
        # For each combination, assign the white king to each spot
        for i in range(4):
            wk_sq = squares[i]
            red_squares = list(squares)
            red_squares.pop(i)
            # Standardize order of red kings
            key = tuple(sorted(red_squares))
            positions.add(key + (wk_sq, 'r'))
            positions.add(key + (wk_sq, 'w'))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_3v1_kings.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

# --- Main Execution ---

if __name__ == '__main__':
    start_time = time.time()
    
    endgame_db = {}
    all_positions = generate_3Kv1K_positions()
    
    ply = 1
    
    print("\nStarting retrograde analysis for 3 Kings vs 1 King...")
    print("Finding all Win-in-1 positions...")
    newly_solved_positions = []
    for pos in all_positions:
        if pos[4] == 'r' and not get_king_moves(pos):
            endgame_db[pos] = 1
            newly_solved_positions.append(pos)
    print(f"Found {len(newly_solved_positions)} Win-in-1 positions.")
    
    # The main analysis loop is logically identical to the 2v1 generator
    while newly_solved_positions:
        ply += 1
        newly_solved_positions_this_ply = []
        
        if ply % 2 == 0: # Even Ply: White's turn
            print(f"\nSolving Ply {ply}: Finding positions where White must move into a Red win...")
            target_value = ply - 1
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[4] == 'w':
                    moves = get_king_moves(pos)
                    if not moves: continue
                    if all(endgame_db.get(move) == target_value for move in moves):
                        endgame_db[pos] = -ply
                        newly_solved_positions_this_ply.append(pos)
        else: # Odd Ply: Red's turn
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[4] == 'r':
                    moves = get_king_moves(pos)
                    if any(endgame_db.get(move) == target_value for move in moves):
                        endgame_db[pos] = ply
                        newly_solved_positions_this_ply.append(pos)

        newly_solved_positions = newly_solved_positions_this_ply
        if newly_solved_positions:
            print(f"Found {len(newly_solved_positions)} positions solved at ply {ply}.")

    print("\n--------------------")
    print("Retrograde analysis complete!")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    
    save_database(endgame_db)

