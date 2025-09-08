# endgame_generator_3Kv1K1M_V3.py
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
    # Position: (rk1, rk2, rk3, wk, wm, turn)
    rk_sqs, wk_sq, wm_sq, turn = set(position[:3]), position[3], position[4], position[5]
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board[ACF_TO_COORD[wk_sq]] = 'W'
    board[ACF_TO_COORD[wm_sq]] = 'w'
    moves = []

    pieces_to_move, opponent_pieces, next_turn, is_red_turn = (list(rk_sqs), {wk_sq, wm_sq}, 'w', True) if turn == 'r' else (list({wk_sq, wm_sq}), rk_sqs, 'r', False)

    for piece_sq in pieces_to_move:
        is_king = (is_red_turn and piece_sq in rk_sqs) or (not is_red_turn and piece_sq == wk_sq)
        r_start, c_start = ACF_TO_COORD[piece_sq]
        
        for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            jump_over = (r_start + dr, c_start + dc)
            land = (r_start + 2*dr, c_start + 2*dc)
            if land in COORD_TO_ACF and land not in board and COORD_TO_ACF.get(jump_over) in opponent_pieces:
                return [] # Capture is a terminal win

        move_dirs = [(-1,-1),(-1,1),(1,-1),(1,1)] if is_king else ([( -1,-1),(-1,1)]) # White man moves
        for dr, dc in move_dirs:
            r_new, c_new = r_start + dr, c_start + dc
            if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                new_sq = COORD_TO_ACF[(r_new, c_new)]
                next_rk, next_wk, next_wm = list(rk_sqs), wk_sq, wm_sq
                if is_red_turn:
                    next_rk.remove(piece_sq); next_rk.append(new_sq)
                else:
                    if is_king: next_wk = new_sq
                    else: next_wm = new_sq
                moves.append(tuple(sorted(next_rk)) + (next_wk, next_wm) + (next_turn,))
    return moves

def generate_3Kv1K1M_positions():
    positions = set()
    print("Generating 3K vs 1K1M positions...")
    for squares in combinations(VALID_SQUARES, 5):
        for i in range(5):
            wm_sq = squares[i]
            kings_and_man = list(squares[:i]) + list(squares[i+1:])
            for j in range(4):
                wk_sq = kings_and_man[j]
                rk_sqs = tuple(sorted(list(set(kings_and_man) - {wk_sq})))
                positions.add(rk_sqs + (wk_sq, wm_sq, 'r',))
                positions.add(rk_sqs + (wk_sq, wm_sq, 'w',))
    print(f"Generated {len(positions)} positions.")
    return list(positions)

def save_database(db, filename="db_3kv1k1m.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_3Kv1K1M_positions()

    print("Finding all Win-in-1 positions...")
    newly_solved = []
    for pos in all_positions:
        if not get_moves(pos):
            endgame_db[pos] = 1 if pos[5] == 'r' else -1
            newly_solved.append(pos)
    print(f"Found {len(newly_solved)} Win-in-1 positions.")

    ply = 1
    while newly_solved:
        ply += 1
        last_solved = newly_solved; newly_solved = []
        
        print(f"\nSolving Ply {ply}...")
        for pos in all_positions:
            if pos in endgame_db: continue
            moves = get_moves(pos)
            if not moves: continue
            
            turn = pos[5]
            if turn == 'r': # Red's turn (stronger side)
                target = -(ply-1)
                if any(endgame_db.get(move) == target for move in moves):
                    endgame_db[pos] = ply; newly_solved.append(pos)
            else: # White's turn (weaker side)
                target = ply-1
                if all(endgame_db.get(move) == target for move in moves):
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
