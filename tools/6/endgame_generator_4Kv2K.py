# endgame_generator_4Kv2K_V3.py
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

def get_king_moves(position):
    rk_sqs, wk_sqs, turn = set(position[:4]), set(position[4:6]), position[6]
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})
    moves = []

    pieces_to_move, opponent_pieces, next_turn = (rk_sqs, wk_sqs, 'w') if turn == 'r' else (wk_sqs, rk_sqs, 'r')

    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            jump_over = (r_start + dr, c_start + dc)
            land = (r_start + 2 * dr, c_start + 2 * dc)
            if land in COORD_TO_ACF and land not in board and COORD_TO_ACF.get(jump_over) in opponent_pieces:
                return [] # Capture is a terminal win

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

def generate_4Kv2K_positions():
    positions = set()
    print("Generating 4v2 King positions...")
    for squares in combinations(VALID_SQUARES, 6):
        for rk_squares in combinations(squares, 4):
            wk_squares = tuple(sorted(list(set(squares) - set(rk_squares))))
            key = tuple(sorted(rk_squares)) + wk_squares
            positions.add(key + ('r',)); positions.add(key + ('w',))
    print(f"Generated {len(positions)} positions.")
    return list(positions)

def save_database(db, filename="db_4v2_kings.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_4Kv2K_positions()

    print("Finding all Win-in-1 positions...")
    newly_solved = []
    for pos in all_positions:
        if not get_king_moves(pos):
            endgame_db[pos] = 1 if pos[6] == 'r' else -1
            newly_solved.append(pos)
    print(f"Found {len(newly_solved)} Win-in-1 positions.")

    ply = 1
    while newly_solved:
        ply += 1
        last_solved = newly_solved; newly_solved = []
        
        print(f"\nSolving Ply {ply}...")
        for pos in all_positions:
            if pos in endgame_db: continue
            moves = get_king_moves(pos)
            if not moves: continue
            
            turn = pos[6]
            if turn == 'r': # Red's turn, finding win
                target_value = -(ply - 1)
                if any(endgame_db.get(move) == target_value for move in moves):
                    endgame_db[pos] = ply; newly_solved.append(pos)
            else: # White's turn, finding loss
                target_value = ply - 1
                if all(endgame_db.get(move) == target_value for move in moves):
                    endgame_db[pos] = -ply; newly_solved.append(pos)

        if newly_solved: print(f"Found {len(newly_solved)} positions solved at ply {ply}.")

    print("\n--------------------")
    print("Retrograde analysis complete! All 4v2 positions are decisive.")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    save_database(endgame_db)
