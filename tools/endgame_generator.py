# endgame_generator.py
import pickle
from itertools import combinations
import time

# --- Mappings for move generation ---
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
    Generates all legal moves for the current player from a given position.
    Returns a list of new position tuples.
    """
    rk1_sq, rk2_sq, wk_sq, turn = position
    moves = []
    
    board = {
        ACF_TO_COORD[rk1_sq]: 'R',
        ACF_TO_COORD[rk2_sq]: 'R',
        ACF_TO_COORD[wk_sq]: 'W'
    }

    pieces_to_move = []
    if turn == 'r':
        pieces_to_move = [(rk1_sq, 'R'), (rk2_sq, 'R')]
        opponent_color = 'W'
    else: # turn == 'w'
        pieces_to_move = [(wk_sq, 'W')]
        opponent_color = 'R'

    # --- Check for Jumps First (Forced) ---
    jump_moves = []
    for piece_sq, piece_color in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr in [-1, 1]:
            for dc in [-1, 1]:
                r_jump_over, c_jump_over = r_start + dr, c_start + dc
                r_land, c_land = r_start + 2*dr, c_start + 2*dc

                # Check if landing square is on the board and empty
                if (r_land, c_land) in COORD_TO_ACF and (r_land, c_land) not in board:
                    # Check if the piece being jumped is an opponent
                    if board.get((r_jump_over, c_jump_over)) == opponent_color:
                        # This is a valid jump. Since it's 2v1, any jump is a win.
                        # We represent a win by returning an empty list, a terminal state.
                        return [] # Returning an empty list signifies a capture is possible.

    # --- If no jumps, find simple moves ---
    for piece_sq, piece_color in pieces_to_move:
        r_start, c_start = ACF_TO_COORD[piece_sq]
        for dr in [-1, 1]:
            for dc in [-1, 1]:
                r_new, c_new = r_start + dr, c_start + dc
                # Check if the new square is valid and unoccupied
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    if turn == 'r':
                        # Figure out which red king moved
                        if piece_sq == rk1_sq:
                            new_pos = tuple(sorted((new_sq, rk2_sq))) + (wk_sq, 'w')
                        else: # piece_sq == rk2_sq
                            new_pos = tuple(sorted((rk1_sq, new_sq))) + (wk_sq, 'w')
                        moves.append(new_pos)
                    else: # turn == 'w'
                        new_pos = tuple(sorted((rk1_sq, rk2_sq))) + (new_sq, 'r')
                        moves.append(new_pos)

    return moves

# --- Database Generation Logic ---

def generate_2v1_king_positions():
    """Generates all possible legal board states for 2 Red Kings vs 1 White King."""
    positions = set()
    print(f"Generating all combinations of 3 pieces on {len(VALID_SQUARES)} squares...")
    for squares in combinations(VALID_SQUARES, 3):
        # Assign the single white king to each possible position in the trio
        for i in range(3):
            wk_sq = squares[i]
            red_squares = list(squares)
            red_squares.pop(i)
            # Standardize order of red kings to avoid duplicates
            key = tuple(sorted(red_squares))
            positions.add(key + (wk_sq, 'r'))
            positions.add(key + (wk_sq, 'w'))
    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_2v1_kings.pkl"):
    """Saves the database to a file using pickle."""
    with open(filename, "wb") as f:
        pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

# --- Main Execution ---

if __name__ == '__main__':
    start_time = time.time()
    
    endgame_db = {} # Key: position, Value: distance to win/loss in plies
    all_positions = generate_2v1_king_positions()
    
    ply = 1
    
    # --- Step 1: Find all immediate wins for Red (Win-in-1) ---
    print("\nStarting retrograde analysis...")
    print("Finding all Win-in-1 positions (Red to move and capture)...")
    newly_solved_positions = []
    for pos in all_positions:
        if pos[3] == 'r': # It's Red's turn
            # If get_king_moves returns an empty list, it means a capture is available.
            if not get_king_moves(pos):
                endgame_db[pos] = 1 # Win in 1 ply
                newly_solved_positions.append(pos)

    print(f"Found {len(newly_solved_positions)} Win-in-1 positions.")
    
    # --- Step 2: Main analysis loop ---
    while newly_solved_positions:
        ply += 1
        last_solved_positions = newly_solved_positions
        newly_solved_positions = []
        
        if ply % 2 == 0: # Even Ply: White's turn (finding losses)
            print(f"\nSolving Ply {ply}: Finding positions where White must move into a Red win...")
            # These are positions where it's White's turn, and ALL moves lead to a known Red win.
            
            # We are looking for positions that can move TO a state we just found.
            # The states we just found are Red-wins-in-(ply-1). So their value is (ply-1)
            target_value = ply - 1
            
            for pos in all_positions:
                if pos in endgame_db: continue # Already solved
                if pos[3] == 'w': # White's turn
                    
                    moves = get_king_moves(pos)
                    if not moves: continue # No moves, can't be a loss, it's a draw/stalemate
                    
                    # Check if ALL moves lead to a previously solved position for Red
                    all_moves_lead_to_loss = True
                    for move in moves:
                        if endgame_db.get(move) != target_value:
                            all_moves_lead_to_loss = False
                            break
                    
                    if all_moves_lead_to_loss:
                        endgame_db[pos] = -ply # Loss in 'ply' for White (negative value)
                        newly_solved_positions.append(pos)

        else: # Odd Ply: Red's turn (finding wins)
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            # These are positions where it's Red's turn, and AT LEAST ONE move leads to a known White loss.
            
            # The states we just found are White-losses-in-(ply-1). So their value is -(ply-1)
            target_value = -(ply - 1)

            for pos in all_positions:
                if pos in endgame_db: continue # Already solved
                if pos[3] == 'r': # Red's turn
                    
                    moves = get_king_moves(pos)
                    
                    # Check if ANY move leads to a previously solved position for White's loss
                    can_force_win = False
                    for move in moves:
                        if endgame_db.get(move) == target_value:
                            can_force_win = True
                            break
                    
                    if can_force_win:
                        endgame_db[pos] = ply # Win in 'ply' for Red
                        newly_solved_positions.append(pos)

        if newly_solved_positions:
            print(f"Found {len(newly_solved_positions)} positions solved at ply {ply}.")

    print("\n--------------------")
    print("Retrograde analysis complete!")
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
    
    # --- Step 3: Save the completed database ---
    save_database(endgame_db)
