# endgame_generator_3Kv3K_V2.py
import pickle
from itertools import combinations
import time

# --- Mappings ---
ACF_TO_coord, COORD_TO_ACF = {}, {}
num = 1
for r in range(8):
    for c in range(8):
        if (r + c) % 2 == 1:
            ACF_TO_coord[num], COORD_TO_ACF[(r, c)] = (r, c), num
            num += 1
VALID_SQUARES = list(ACF_TO_coord.keys())

def get_king_moves(position):
    """
    Generates legal moves. An empty list signifies a capture is available,
    which is a terminal win for the current player in a 3v3 scenario.
    """
    rk_sqs = set(position[0:3])
    wk_sqs = set(position[3:6])
    turn = position[6]
    
    board = {ACF_TO_coord[sq]: 'R' for sq in rk_sqs}
    board.update({ACF_TO_coord[sq]: 'W' for sq in wk_sqs})
    moves = []

    pieces_to_move, opponent_pieces, next_turn = (rk_sqs, wk_sqs, 'w') if turn == 'r' else (wk_sqs, rk_sqs, 'r')

    # Jumps are terminal wins in 3v3 as they lead to a won 3v2
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_coord[piece_sq]
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            jump_over = (r_start + dr, c_start + dc)
            land = (r_start + 2 * dr, c_start + 2 * dc)
            if land in COORD_TO_ACF and land not in board and COORD_TO_ACF.get(jump_over) in opponent_pieces:
                return [] # A capture is possible, return an empty list to signify a win.

    # No jumps, find simple moves
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_coord[piece_sq]
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            r_new, c_new = r_start + dr, c_start + dc
            if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                new_sq = COORD_TO_ACF[(r_new, c_new)]
                next_rk, next_wk = list(rk_sqs), list(wk_sqs)
                if turn == 'r':
                    next_rk.remove(piece_sq); next_rk.append(new_sq)
                else:
                    next_wk.remove(piece_sq); next_wk.append(new_sq)
                moves.append(tuple(sorted(next_rk)) + tuple(sorted(next_wk)) + (next_turn,))
    return moves

def generate_3Kv3K_positions():
    positions = set()
    print("Generating 3v3 King positions...")
    for squares in combinations(VALID_SQUARES, 6):
        for rk_squares in combinations(squares, 3):
            wk_squares = tuple(sorted(list(set(squares) - set(rk_squares))))
            key = tuple(sorted(rk_squares)) + wk_squares
            positions.add(key + ('r',)); positions.add(key + ('w',))
    print(f"Generated {len(positions)} positions.")
    return list(positions)

def save_database(db, filename="db_3v3_kings.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_3Kv3K_positions()
    
    # --- Step 1: Find all immediate wins (Win-in-1) ---
    print("Finding all Win-in-1 positions...")
    newly_solved = []
    for pos in all_positions:
        if not get_king_moves(pos): # Empty list means a capture is available
            endgame_db[pos] = 1 if pos[6] == 'r' else -1 # Win for Red or White
            newly_solved.append(pos)
    print(f"Found {len(newly_solved)} Win-in-1 positions.")
    
    # --- Step 2: Main Retrograde Analysis Loop ---
    ply = 1
    while newly_solved:
        ply += 1
        last_solved = newly_solved; newly_solved = []
        
        # Even Ply: Finding losses
        if ply % 2 == 0:
            print(f"\nSolving Ply {ply}: Finding positions that must move into a win...")
            for pos in all_positions:
                if pos in endgame_db: continue
                moves = get_king_moves(pos)
                if not moves: continue
                
                # If ALL moves lead to a known win for the other player
                if all(endgame_db.get(move) == (ply - 1) * (-1 if pos[6] == 'r' else 1) for move in moves):
                    endgame_db[pos] = ply * (1 if pos[6] == 'r' else -1)
                    newly_solved.append(pos)
        # Odd Ply: Finding wins
        else:
            print(f"\nSolving Ply {ply}: Finding positions that can force a loss...")
            for pos in all_positions:
                if pos in endgame_db: continue
                moves = get_king_moves(pos)
                
                # If ANY move leads to a known loss for the other player
                if any(endgame_db.get(move) == -(ply - 1) * (-1 if pos[6] == 'r' else 1) for move in moves):
                    endgame_db[pos] = ply * (1 if pos[6] == 'r' else -1)
                    newly_solved.append(pos)

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
