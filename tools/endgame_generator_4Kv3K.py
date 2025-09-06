# endgame_generator_4Kv3K_V2.py
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
    Generates legal moves for 4K v 3K. Returns a list of next-state tuples.
    An empty list signifies a capture is available (a terminal win for the current player).
    """
    rk_sqs = set(position[0:4])
    wk_sqs = set(position[4:7])
    turn = position[7]
    
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})
    moves = []

    pieces_to_move, opponent_pieces, next_turn = (rk_sqs, wk_sqs, 'w') if turn == 'r' else (wk_sqs, rk_sqs, 'r')

    # Check for Jumps First
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            jump_over_coord = (r_start + dr, c_start + dc)
            land_coord = (r_start + 2 * dr, c_start + 2 * dc)
            if land_coord in COORD_TO_ACF and land_coord not in board:
                jumped_piece_sq = COORD_TO_ACF.get(jump_over_coord)
                if jumped_piece_sq in opponent_pieces:
                    # A capture is available. This is a terminal state.
                    # For 4v3, ANY capture by Red is a win.
                    if turn == 'r':
                        return [] # Returning an empty list signifies a win.

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

def generate_4Kv3K_positions():
    positions = set()
    print("Generating 4v3 King positions...")
    for squares in combinations(VALID_SQUARES, 7):
        for rk_squares in combinations(squares, 4):
            wk_squares = tuple(sorted(list(set(squares) - set(rk_squares))))
            key = tuple(sorted(rk_squares)) + wk_squares
            positions.add(key + ('r',)); positions.add(key + ('w',))
    print(f"Generated {len(positions)} positions.")
    return list(positions)

def save_database(db, filename="db_4v3_kings.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_4Kv3K_positions()
    
    # --- Step 1: Initialize Known Outcomes ---
    # In 4v3, if White (3 kings) captures, it becomes 3v3, a draw.
    # Mark all positions where White can capture as draws immediately.
    print("Initializing known draws (White to move and capture)...")
    for pos in all_positions:
        if pos[7] == 'w' and not get_king_moves(pos):
             # A capture by white leads to 3v3 (a draw)
             # but it is a losing move if Red has a forced win.
             # We will let the main loop handle this.
             pass

    # Find immediate wins for Red (Red to move and capture)
    print("Finding all Win-in-1 positions for Red...")
    newly_solved_positions = []
    for pos in all_positions:
        if pos[7] == 'r' and not get_king_moves(pos):
            endgame_db[pos] = 1
            newly_solved_positions.append(pos)
    print(f"Found {len(newly_solved_positions)} Win-in-1 positions.")
    
    # --- Step 2: Main Retrograde Analysis Loop ---
    ply = 1
    while newly_solved_positions:
        ply += 1
        last_solved = newly_solved_positions
        newly_solved_positions = []
        
        # Even Ply: White's turn (Finding Losses)
        if ply % 2 == 0:
            print(f"\nSolving Ply {ply}: Finding positions where White must move into a Red win...")
            target_value = ply - 1
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[7] == 'w':
                    moves = get_king_moves(pos)
                    if not moves: continue # This is a capture for white (3v3 draw), not a loss.
                    if all(endgame_db.get(move) == target_value for move in moves):
                        endgame_db[pos] = -ply
                        newly_solved_positions.append(pos)
        # Odd Ply: Red's turn (Finding Wins)
        else:
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[7] == 'r':
                    moves = get_king_moves(pos)
                    if any(endgame_db.get(move) == target_value for move in moves):
                        endgame_db[pos] = ply
                        newly_solved_positions.append(pos)

        if newly_solved_positions:
            print(f"Found {len(newly_solved_positions)} positions solved at ply {ply}.")

    print("\nMarking all remaining unsolved positions as draws...")
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
