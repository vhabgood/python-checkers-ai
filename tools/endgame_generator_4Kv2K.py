# endgame_generator_4Kv2K.py
import pickle
from itertools import combinations
import time
import os

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

def get_king_moves(position):
    """
    Generates all legal moves for the current player from a given 4K v 2K position.
    Position: (rk1, rk2, rk3, rk4, wk1, wk2, turn)
    """
    rk_sqs = set(position[:4])
    wk_sqs = set(position[4:6])
    turn = position[6]
    
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})

    moves = []
    
    if turn == 'r':
        pieces_to_move, opponent_pieces = rk_sqs, wk_sqs
        next_turn = 'w'
    else: # turn == 'w'
        pieces_to_move, opponent_pieces = wk_sqs, rk_sqs
        next_turn = 'r'

    # Check for Jumps First
    jump_found = False
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            jump_over_coord = (r_start + dr, c_start + dc)
            land_coord = (r_start + 2*dr, c_start + 2*dc)

            if land_coord in COORD_TO_ACF and land_coord not in board:
                jumped_piece_sq = COORD_TO_ACF.get(jump_over_coord)
                if jumped_piece_sq in opponent_pieces:
                    # Any jump simplifies to a smaller endgame which is a known win/loss.
                    # Red capturing -> 4v1 (Win). White capturing -> 3v2 (can be a win for White).
                    # For simplicity, we treat any capture as a terminal win/loss for the side making it.
                    moves.append({'is_win': True})
                    jump_found = True

    if jump_found: return [m for m in moves if m.get('is_win')]

    # No jumps, find simple moves
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            r_new, c_new = r_start + dr, c_start + dc
            if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                new_sq = COORD_TO_ACF[(r_new, c_new)]
                next_rk_sqs, next_wk_sqs = list(rk_sqs), list(wk_sqs)
                if turn == 'r':
                    next_rk_sqs.remove(piece_sq); next_rk_sqs.append(new_sq)
                else:
                    next_wk_sqs.remove(piece_sq); next_wk_sqs.append(new_sq)
                new_pos = tuple(sorted(next_rk_sqs)) + tuple(sorted(next_wk_sqs)) + (next_turn,)
                moves.append({'key': new_pos})
    return moves


def generate_4Kv2K_positions():
    """Generates all positions for 4 Red Kings vs 2 White Kings."""
    positions = set()
    print(f"Generating all combinations of 6 pieces on {len(VALID_SQUARES)} squares...")
    # This will be a very large number!
    for squares in combinations(VALID_SQUARES, 6):
        for rk_squares in combinations(squares, 4):
            wk_squares = tuple(sorted(list(set(squares) - set(rk_squares))))
            rk_squares = tuple(sorted(rk_squares))
            key = rk_squares + wk_squares
            positions.add(key + ('r',))
            positions.add(key + ('w',))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_4v2_kings.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")


if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_4Kv2K_positions()
    ply = 1
    
    print("\nStarting retrograde analysis for 4 Kings vs 2 Kings...")
    print("This will take a very long time.")
    print("Finding all Win-in-1 positions for Red...")
    newly_solved_positions = []
    for pos in all_positions:
        if pos[6] == 'r' and any(m.get('is_win') for m in get_king_moves(pos)):
            endgame_db[pos] = 1
            newly_solved_positions.append(pos)
    print(f"Found {len(newly_solved_positions)} Win-in-1 positions.")
    
    while newly_solved_positions:
        ply += 1
        last_solved = newly_solved_positions; newly_solved_positions = []
        
        if ply % 2 == 0: # Even Ply: White's turn
            print(f"\nSolving Ply {ply}: Finding positions where White must move into a Red win...")
            target_value = ply - 1
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[6] == 'w':
                    moves = get_king_moves(pos)
                    if not moves or any(m.get('is_win') for m in moves): continue
                    if all(endgame_db.get(m['key']) == target_value for m in moves):
                        endgame_db[pos] = -ply
                        newly_solved_positions.append(pos)
        else: # Odd Ply: Red's turn
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[6] == 'r':
                    moves = get_king_moves(pos)
                    if any(endgame_db.get(m.get('key')) == target_value for m in moves):
                        endgame_db[pos] = ply
                        newly_solved_positions.append(pos)

        if newly_solved_positions: print(f"Found {len(newly_solved_positions)} positions solved at ply {ply}.")

    print("\nWin/Loss analysis complete. Marking remaining positions as draws...")
    draw_count = 0
    for pos in all_positions:
        if pos not in endgame_db: endgame_db[pos] = 0; draw_count += 1
    print(f"Marked {draw_count} positions as draws.")
    
    print("\n--------------------")
    print("Retrograde analysis complete!")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    
    save_database(endgame_db)
