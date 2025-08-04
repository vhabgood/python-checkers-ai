# endgame_generator_2K1Mv3K.py
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

def get_moves(position):
    """
    Generates all legal moves for a 2K1M v 3K position.
    Position: (rk1, rk2, rm, wk1, wk2, wk3, turn) - 7 elements
    """
    rk_sqs = set(position[:2])
    rm_sq = position[2]
    wk_sqs = set(position[3:6])
    turn = position[6]
    
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}
    board[ACF_TO_COORD[rm_sq]] = 'r'
    board.update({ACF_TO_COORD[sq]: 'W' for sq in wk_sqs})
    moves = []

    # --- RED'S TURN ---
    if turn == 'r':
        pieces_to_move = list(rk_sqs) + [rm_sq]
        for piece_sq in pieces_to_move:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            is_king = piece_sq in rk_sqs
            move_dirs = [(-1, 1), (1, 1), (-1, -1), (1, -1)] if is_king else [(1, -1), (1, 1)]
            for dr, dc in move_dirs:
                jump_over_coord = (r_start + dr, c_start + dc)
                land_coord = (r_start + 2*dr, c_start + 2*dc)
                if land_coord in COORD_TO_ACF and land_coord not in board and COORD_TO_ACF.get(jump_over_coord) in wk_sqs:
                    return [{'is_win': True}] # 2K1M vs 2K is a winning advantage.

        for piece_sq in pieces_to_move:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            is_king = piece_sq in rk_sqs
            move_dirs = [(-1, 1), (1, 1), (-1, -1), (1, -1)] if is_king else [(1, -1), (1, 1)]
            for dr, dc in move_dirs:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    if is_king:
                        next_rk = list(rk_sqs); next_rk.remove(piece_sq); next_rk.append(new_sq)
                        new_pos = tuple(sorted(next_rk)) + (rm_sq,) + tuple(sorted(wk_sqs)) + ('w',)
                        moves.append({'key': new_pos})
                    else: # Man moved
                        if r_new == 7: # PROMOTION to 3K vs 3K
                            moves.append({'is_draw': True})
                        else:
                            new_pos = tuple(sorted(rk_sqs)) + (new_sq,) + tuple(sorted(wk_sqs)) + ('w',)
                            moves.append({'key': new_pos})
        return moves

    # --- WHITE'S TURN ---
    else: # turn == 'w'
        for piece_sq in wk_sqs:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            for dr, dc in [(-1, 1), (1, 1), (-1, -1), (1, -1)]:
                jump_over_coord = (r_start + dr, c_start + dc)
                land_coord = (r_start + 2*dr, c_start + 2*dc)
                jumped_sq = COORD_TO_ACF.get(jump_over_coord)
                if land_coord in COORD_TO_ACF and land_coord not in board and (jumped_sq in rk_sqs or jumped_sq == rm_sq):
                    # White captures, gaining a decisive advantage. This is a loss for Red.
                    return [{'is_loss_for_red': True}]

        for piece_sq in wk_sqs:
            r_start, c_start = ACF_TO_COORD[piece_sq]
            for dr, dc in [(-1, 1), (1, 1), (-1, -1), (1, -1)]:
                r_new, c_new = r_start + dr, c_start + dc
                if (r_new, c_new) in COORD_TO_ACF and (r_new, c_new) not in board:
                    new_sq = COORD_TO_ACF[(r_new, c_new)]
                    next_wk = list(wk_sqs); next_wk.remove(piece_sq); next_wk.append(new_sq)
                    new_pos = tuple(sorted(rk_sqs)) + (rm_sq,) + tuple(sorted(next_wk)) + ('r',)
                    moves.append({'key': new_pos})
        return moves

def generate_2K1Mv3K_positions():
    positions = set()
    print("Generating all combinations for 2K1M vs 3K...")
    man_invalid_squares = {29, 30, 31, 32}
    
    for squares in combinations(VALID_SQUARES, 6):
        for wk_combo in combinations(squares, 3):
            wk_sqs = tuple(sorted(wk_combo))
            remaining = list(set(squares) - set(wk_sqs))
            for i in range(len(remaining)):
                rm_sq = remaining[i]
                if rm_sq in man_invalid_squares: continue
                rk_sqs = tuple(sorted(remaining[:i] + remaining[i+1:]))
                key = rk_sqs + (rm_sq,) + wk_sqs
                positions.add(key + ('r',))
                positions.add(key + ('w',))

    print(f"Generated {len(positions)} unique positions.")
    return list(positions)

def save_database(db, filename="db_2k1m_vs_3k.pkl"):
    with open(filename, "wb") as f: pickle.dump(db, f)
    print(f"Database with {len(db)} solved positions saved to {filename}")

if __name__ == '__main__':
    start_time = time.time()
    endgame_db = {}
    all_positions = generate_2K1Mv3K_positions()
    ply = 1
    
    print("\nStarting retrograde analysis for 2K1M v 3K...")
    print("This may take a very long time.")
    print("Finding all Win-in-1 positions for Red...")
    newly_solved_positions = []
    for pos in all_positions:
        # CORRECTED INDEX: from pos[7] to pos[6]
        if pos[6] == 'r' and any(m.get('is_win') for m in get_moves(pos)):
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
                # CORRECTED INDEX: from pos[7] to pos[6]
                if pos[6] == 'w':
                    moves = get_moves(pos)
                    # If any move results in a loss or draw for red, white will take it. So not a forced win for red.
                    if not moves or any(m.get('is_loss_for_red') or m.get('is_draw') for m in moves): continue
                    
                    if all(endgame_db.get(m['key']) == target_value for m in moves):
                        endgame_db[pos] = -ply
                        newly_solved_positions.append(pos)
        else: # Odd Ply: Red's turn
            print(f"\nSolving Ply {ply}: Finding positions where Red can force a win...")
            target_value = -(ply - 1)
            for pos in all_positions:
                if pos in endgame_db: continue
                # CORRECTED INDEX: from pos[7] to pos[6]
                if pos[6] == 'r':
                    moves = get_moves(pos)
                    can_force_win = False
                    for move in moves:
                        if move.get('is_win'): can_force_win = True; break
                        # A move to a draw is not a winning move.
                        if move.get('is_draw'): continue
                        if endgame_db.get(move.get('key')) == target_value: can_force_win = True; break
                    if can_force_win:
                        endgame_db[pos] = ply; newly_solved_positions.append(pos)

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
