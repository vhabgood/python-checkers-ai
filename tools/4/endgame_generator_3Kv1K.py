# endgame_generator_3Kv1K_V3.py
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
    rk_sqs, wk_sq, turn = set(position[:3]), position[3], position[4]
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board[ACF_TO_COORD[wk_sq]] = 'W'
    moves = []

    pieces_to_move, opponent_pieces, next_turn = (rk_sqs, {wk_sq}, 'w') if turn == 'r' else ({wk_sq}, rk_sqs, 'r')

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
                next_rk_sqs, next_wk_sq = list(rk_sqs), wk_sq
                if turn == 'r':
                    next_rk_sqs.remove(piece_sq); next_rk_sqs.append(new_sq)
                else:
                    next_wk_sq = new_sq
                moves.append(tuple(sorted(next_rk_sqs)) + (next_wk_sq,) + (next_turn,))
    return moves

def generate_3Kv1K_positions():
    positions = set()
    print("Generating 3 Kings vs 1 King positions...")
    for squares in combinations(VALID_SQUARES, 4):
        for i in range(4):
            wk_sq = squares[i]
            rk_sqs = tuple(sorted(list(set(squares) - {wk_sq})))
            positions.add(rk_sqs + (wk_sq, 'r',))
            positions.add(rk_sqs + (wk_sq, 'w',))
    print(f"Generated {len(positions)} positions.")
    return list(positions)

def save_database(db, filename="db_3v1_kings.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_3Kv1K_positions()
    
    print("Finding all Win-in-1 positions...")
    newly_solved = []
    for pos in all_positions:
        if not get_king_moves(pos):
            # 3v1 is a win for the side with 3 kings
            endgame_db[pos] = 1 if pos[4] == 'r' else -1
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
            
            turn = pos[4]
            # Red's turn (finding win)
            if turn == 'r':
                target_value = -(ply - 1)
                if any(endgame_db.get(move) == target_value for move in moves):
                    endgame_db[pos] = ply; newly_solved.append(pos)
            # White's turn (finding loss)
            else:
                target_value = ply - 1
                if all(endgame_db.get(move) == target_value for move in moves):
                    endgame_db[pos] = -ply; newly_solved.append(pos)

        if newly_solved: print(f"Found {len(newly_solved)} positions solved at ply {ply}.")

    print("\n--------------------")
    print("Retrograde analysis complete! All 3v1 positions are decisive.")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    save_database(endgame_db)
