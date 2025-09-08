# endgame_generator_3Kv2K_V2.py
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

def get_king_moves(position):
    """
    Generates legal moves. An empty list signifies a capture, which is a terminal win.
    """
    rk_sqs, wk_sqs, turn = set(position[:3]), set(position[3:5]), position[5]
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})
    moves = []

    pieces_to_move, opponent_pieces, next_turn = (rk_sqs, wk_sqs, 'w') if turn == 'r' else (wk_sqs, rk_sqs, 'r')

    # Check for Jumps (Terminal Wins)
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            jump_over = (r_start + dr, c_start + dc)
            land = (r_start + 2 * dr, c_start + 2 * dc)
            if land in COORD_TO_ACF and land not in board and COORD_TO_ACF.get(jump_over) in opponent_pieces:
                return [] # Capture is a terminal win

    # No jumps, find simple moves
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
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

def generate_3Kv2K_positions():
    positions = set()
    print("Generating 3v2 King positions...")
    for squares in combinations(VALID_SQUARES, 5):
        for rk_squares in combinations(squares, 3):
            wk_squares = tuple(sorted(list(set(squares) - set(rk_squares))))
            key = tuple(sorted(rk_squares)) + wk_squares
            positions.add(key + ('r',)); positions.add(key + ('w',))
    print(f"Generated {len(positions)} positions.")
    return list(positions)

def save_database(db, filename="db_3v2_kings.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_3Kv2K_positions()

    # --- Standard Retrograde Analysis Loop ---
    print("Finding all Win-in-1 positions...")
    newly_solved = []
    for pos in all_positions:
        if not get_king_moves(pos): # Empty list means a capture is available
            # 3v2 is a win for the side with 3 kings, regardless of whose turn
            endgame_db[pos] = 1 if len(set(pos[:3])) > len(set(pos[3:5])) else -1
            newly_solved.append(pos)
    print(f"Found {len(newly_solved)} Win-in-1 positions.")

    ply = 1
    while newly_solved:
        ply += 1
        last_solved = newly_solved; newly_solved = []
        
        # Determine winning and losing players based on who has 3 kings
        # This logic is simplified because 3v2 is always a win for the 3 kings.
        # We just need to find the distance.
        
        print(f"\nSolving Ply {ply}...")
        for pos in all_positions:
            if pos in endgame_db: continue
            
            moves = get_king_moves(pos)
            if not moves: continue
            
            # Check for forced wins/losses
            # Red has 3 kings
            if len(set(pos[:3])) > len(set(pos[3:5])):
                if pos[5] == 'r': # Red's turn, can it force a win?
                    if any(endgame_db.get(move) == -(ply - 1) for move in moves):
                        endgame_db[pos] = ply; newly_solved.append(pos)
                else: # White's turn, must it lose?
                    if all(endgame_db.get(move) == (ply - 1) for move in moves):
                        endgame_db[pos] = -ply; newly_solved.append(pos)
            # White has 3 kings
            else:
                if pos[5] == 'w': # White's turn, can it force a win?
                     if any(endgame_db.get(move) == (ply-1) for move in moves):
                         endgame_db[pos] = -ply; newly_solved.append(pos)
                else: # Red's turn, must it lose?
                    if all(endgame_db.get(move) == -(ply-1) for move in moves):
                        endgame_db[pos] = ply; newly_solved.append(pos)
                        
        if newly_solved: print(f"Found {len(newly_solved)} positions solved at ply {ply}.")
    
    print("\n--------------------")
    print("Retrograde analysis complete!")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    save_database(endgame_db)
