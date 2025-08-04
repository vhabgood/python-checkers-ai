# endgame_generator_3Kv2K.py
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

# --- Helper Functions for Move Logic ---
def get_king_moves(position):
    """
    Generates all legal moves for the current player from a given 3K v 2K position.
    Position: (rk1, rk2, rk3, wk1, wk2, turn)
    """
    rk_sqs = set(position[:3])
    wk_sqs = set(position[3:5])
    turn = position[5]
    
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})

    moves = []
    
    if turn == 'r':
        pieces_to_move = rk_sqs
        opponent_pieces = wk_sqs
        next_turn = 'w'
    else: # turn == 'w'
        pieces_to_move = wk_sqs
        opponent_pieces = rk_sqs
        next_turn = 'r'

    # Check for Jumps First
    jump_found = False
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr in [-1, 1]:
            for dc in [-1, 1]:
                jump_over_coord = (r_start + dr, c_start + dc)
                land_coord = (r_start + 2*dr, c_start + 2*dc)

                if land_coord in COORD_TO_ACF and land_coord not in board:
                    if jump_over_coord in board and board[jump_over_coord] != turn.upper():
                        # A jump is possible. This is a terminal state for this sub-problem.
                        # For simplicity in this generator, any jump leads to a simpler endgame
                        # which we treat as a win. So, return an empty list.
                        jump_found = True
                        
                        # --- Create the resulting position after the jump ---
                        jumped_piece_sq = COORD_TO_ACF[jump_over_coord]
                        new_piece_sq = COORD_TO_ACF[land_coord]
                        
                        temp_pieces = list(pieces_to_move)
                        temp_pieces.remove(piece_sq)
                        temp_pieces.append(new_piece_sq)
                        
                        temp_opp_pieces = list(opponent_pieces)
                        temp_opp_pieces.remove(jumped_piece_sq)
                        
                        if turn == 'r':
                            # This results in a 3v1 endgame, a known win
                            moves.append({'is_win': True})
                        else: # White jumped a red king
                            # This results in a 2v2 endgame. We'll also treat this as a terminal win for white
                            # to simplify, as the goal is to solve the 3v2 itself.
                            moves.append({'is_win': True})

    if jump_found:
        return [m for m in moves if 'is_win' in m] # Return only jump moves if any exist

    # If no jumps, find simple moves
    for piece_sq in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr in [-1, 1]:
            for dc in [-1, 1]:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    
                    next_rk_sqs, next_wk_sqs = list(rk_sqs), list(wk_sqs)
                    if turn == 'r':
                        next_rk_sqs.remove(piece_sq)
                        next_rk_sqs.append(new_sq)
                    else:
                        next_wk_sqs.remove(piece_sq)
                        next_wk_sqs.append(new_sq)

                    new_pos = tuple(sorted(next_rk_sqs)) + tuple(sorted(next_wk_sqs)) + (next_turn,)
                    moves.append({'key': new_pos})
    return moves


def generate_3Kv2K_positions():
    """Generates all positions for 3 Red Kings vs 2 White Kings."""
    positions = set()
    print(f"Generating all combinations of 5 pieces on {len(VALID_SQUARES)} squares...")
    for squares in combinations(VALID_SQUARES, 5):
        # Iterate through all ways to choose 3 squares for Red's kings
        for rk_squares in combinations(squares, 3):
            wk_squares = tuple(sorted(list(set(squares) - set(rk_squares))))
            rk_squares = tuple(sorted(rk_squares))
            
            key = rk_squares + wk_squares
            positions.add(key + ('r',))
            positions.add(key + ('w',))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_3v2_kings.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

# --- Main Execution ---
if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_3Kv2K_positions()
    ply = 1
    
    print("\nStarting retrograde analysis for 3 Kings vs 2 Kings...")
    print("Finding all Win-in-1 positions (Red captures a White King)...")
    newly_solved_positions = []
    for pos in all_positions:
        if pos[5] == 'r': # Red's turn
            moves = get_king_moves(pos)
            if any(m.get('is_win') for m in moves):
                endgame_db[pos] = 1
                newly_solved_positions.append(pos)
    print(f"Found {len(newly_solved_positions)} Win-in-1 positions.")
    
    while newly_solved_positions:
        ply += 1
        last_solved_positions = newly_solved_positions
        newly_solved_positions = []
        
        # Even Ply: White's turn (finding losses for White/wins for Red)
        if ply % 2 == 0:
            print(f"\nSolving Ply {ply}: Finding positions where White must move into a Red win...")
            target_value = ply - 1 # Red wins in ply-1
            
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[5] == 'w':
                    moves = get_king_moves(pos)
                    # If White can jump, it's a win for them, not a loss. Skip.
                    if any(m.get('is_win') for m in moves): continue
                    if not moves: continue # No moves, stalemate = draw

                    # All of white's moves must lead to a known red win
                    if all(endgame_db.get(m['key']) == target_value for m in moves):
                        endgame_db[pos] = -ply # White loses in 'ply'
                        newly_solved_positions.append(pos)
        
        # Odd Ply: Red's turn (finding wins for Red)
        else:
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1) # White loses in ply-1
            for pos in all_positions:
                if pos in endgame_db: continue
                if pos[5] == 'r':
                    moves = get_king_moves(pos)
                    # Red needs just one move that leads to a known white loss
                    if any(endgame_db.get(m.get('key')) == target_value for m in moves):
                        endgame_db[pos] = ply
                        newly_solved_positions.append(pos)

        if newly_solved_positions:
            print(f"Found {len(newly_solved_positions)} positions solved at ply {ply}.")

    # --- Step 3: Mark all remaining unsolved positions as draws ---
    print("\nWin/Loss analysis complete. Marking remaining positions as draws...")
    draw_count = 0
    for pos in all_positions:
        if pos not in endgame_db:
            endgame_db[pos] = 0 # 0 signifies a draw
            draw_count += 1
    print(f"Marked {draw_count} positions as draws.")
    
    print("\n--------------------")
    print("Retrograde analysis complete!")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    
    save_database(endgame_db)
