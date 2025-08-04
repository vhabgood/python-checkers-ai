# endgame_generator_4Kv3K.py
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
    Generates all legal moves for a 4K v 3K position.
    Position: (rk_sqs_tuple, wk_sqs_tuple, turn)
    """
    rk_sqs = set(position[0])
    wk_sqs = set(position[1])
    turn = position[2]
    
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})
    moves = []

    if turn == 'r':
        pieces_to_move, opponent_pieces = rk_sqs, wk_sqs
        next_turn = 'w'
    else: # turn == 'w'
        pieces_to_move, opponent_pieces = wk_sqs, rk_sqs
        next_turn = 'r'

    # Check for Jumps First (Terminal states)
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            jump_over_coord = (r_start + dr, c_start + dc)
            land_coord = (r_start + 2*dr, c_start + 2*dc)
            if land_coord in COORD_TO_ACF and land_coord not in board:
                jumped_piece_sq = COORD_TO_ACF.get(jump_over_coord)
                if jumped_piece_sq in opponent_pieces:
                    # A capture always simplifies to a smaller, known endgame.
                    if turn == 'r': # Red captures, -> 4v2, a known win for Red.
                        return [{'is_win': True}]
                    else: # White captures, -> 3v3, a known draw.
                        return [{'is_draw': True}]

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
                new_pos = (tuple(sorted(next_rk_sqs)), tuple(sorted(next_wk_sqs)), next_turn)
                moves.append({'key': new_pos})
    return moves


def generate_4Kv3K_positions():
    """Generates all positions for 4 Red Kings vs 3 White Kings."""
    positions = set()
    print(f"Generating all combinations of 7 pieces on {len(VALID_SQUARES)} squares...")
    for squares in combinations(VALID_SQUARES, 7):
        # Iterate through all ways to choose 4 squares for Red's kings
        for rk_squares in combinations(squares, 4):
            wk_squares = tuple(sorted(list(set(squares) - set(rk_squares))))
            rk_squares = tuple(sorted(rk_squares))
            
            # Use tuples for keys to make them hashable
            key = (rk_squares, wk_squares)
            positions.add(key + ('r',))
            positions.add(key + ('w',))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_4v3_kings.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")


if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_4Kv3K_positions()
    ply = 1
    
    print("\nStarting retrograde analysis for 4 Kings vs 3 Kings...")
    print("This will take a very, very long time.")
    print("Finding all Win-in-1 positions for Red...")
    newly_solved_positions = []
    for pos in all_positions:
        # pos[2] is the turn indicator
        if pos[2] == 'r' and any(m.get('is_win') for m in get_king_moves(pos)):
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
                if pos[2] == 'w':
                    moves = get_king_moves(pos)
                    # If White can force a draw or it's a stalemate, it's not a loss for them.
                    if not moves or any(m.get('is_draw') for m in moves): continue
                    # Check if all resulting positions lead to a known red win
                    if all(endgame_db.get(m['key']) == target_value for m in moves if 'key' in m):
                        endgame_db[pos] = -ply
                        newly_solved_positions.append(pos)
        else: # Odd Ply: Red's turn
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[2] == 'r':
                    moves = get_king_moves(pos)
                    # Check if any move leads to a known white loss
                    if any(endgame_db.get(m.get('key')) == target_value for m in moves if 'key' in m):
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
