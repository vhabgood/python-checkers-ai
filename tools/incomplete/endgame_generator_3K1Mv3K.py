# endgame_generator_3K1Mv3K_V3.py
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

def get_moves(position):
    # This endgame has Red with the man: (rk1, rk2, rk3, rm, wk1, wk2, wk3, turn)
    rk_sqs, rm_sq, wk_sqs, turn = set(position[:3]), position[3], set(position[4:7]), position[7]
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}; board[ACF_TO_COORD[rm_sq]] = 'r'
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})
    moves = []

    pieces_to_move, opponent_pieces, next_turn, is_red_turn = (list(rk_sqs)+[rm_sq], wk_sqs, 'w', True) if turn == 'r' else (list(wk_sqs), list(rk_sqs)+[rm_sq], 'r', False)

    for piece_sq in pieces_to_move:
        # A man is not a king
        is_king = (is_red_turn and piece_sq != rm_sq) or (not is_red_turn)
        r_start, c_start = ACF_TO_COORD[piece_sq]
        
        # Check for jumps (terminal wins)
        for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            jump_over = (r_start + dr, c_start + dc)
            land = (r_start + 2*dr, c_start + 2*dc)
            if land in COORD_TO_ACF and land not in board and COORD_TO_ACF.get(jump_over) in opponent_pieces:
                return [] # A capture simplifies to a won endgame

        # Check for simple moves
        move_dirs = [(-1,-1),(-1,1),(1,-1),(1,1)] if is_king else ([(1,-1),(1,1)]) # Red man moves
        for dr, dc in move_dirs:
            r_new, c_new = r_start + dr, c_start + dc
            if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                new_sq = COORD_TO_ACF[(r_new, c_new)]
                next_rk, next_rm, next_wk = list(rk_sqs), rm_sq, list(wk_sqs)
                if is_red_turn:
                    if is_king: next_rk.remove(piece_sq); next_rk.append(new_sq)
                    else: next_rm = new_sq # Man moves
                else: # White's turn (all kings)
                    next_wk.remove(piece_sq); next_wk.append(new_sq)
                moves.append(tuple(sorted(next_rk)) + (next_rm,) + tuple(sorted(next_wk)) + (next_turn,))
    return moves

def generate_3K1Mv3K_positions():
    positions = set()
    print("Generating 3K1M vs 3K positions...")
    print("WARNING: This will generate a very large number of positions and may require a large amount of RAM.")
    for squares in combinations(VALID_SQUARES, 7):
        for i in range(7):
            man_sq = squares[i]
            kings_sqs = list(squares[:i]) + list(squares[i+1:])
            for rk_combo in combinations(kings_sqs, 3):
                rk_sqs = tuple(sorted(rk_combo))
                wk_sqs = tuple(sorted(list(set(kings_sqs) - set(rk_sqs))))
                positions.add(rk_sqs + (man_sq,) + wk_sqs + ('r',))
                positions.add(rk_sqs + (man_sq,) + wk_sqs + ('w',))
    print(f"Generated {len(positions)} positions.")
    return list(positions)

def save_database(db, filename="db_3k1m_v_3k.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_3K1Mv3K_positions()

    print("Finding all Win-in-1 positions...")
    newly_solved = []
    for pos in all_positions:
        if not get_moves(pos):
            # The side with the man (Red) has the advantage
            endgame_db[pos] = 1 if pos[7] == 'r' else -1
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
            
            turn = pos[7]
            # Red's turn (stronger side)
            if turn == 'r': 
                target = -(ply-1)
                if any(endgame_db.get(move) == target for move in moves):
                    endgame_db[pos] = ply; newly_solved.append(pos)
            # White's turn (weaker side)
            else:
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
