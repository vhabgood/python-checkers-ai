# build_database.py (Refactored for Speed and Modularity)
import sqlite3
from itertools import combinations
import time
import os

# --- Mappings (consistent with your project) ---
ACF_TO_COORD, COORD_TO_ACF = {}, {}
num = 1
for r in range(8):
    for c in range(8):
        if (r + c) % 2 == 1:
            ACF_TO_COORD[num], COORD_TO_ACF[(r, c)] = (r, c), num
            num += 1
VALID_SQUARES = list(ACF_TO_COORD.keys())

# --- Database Setup ---
DB_FILENAME = "checkers_endgame.db"

# ======================================================================================
# --- 1. CORE GENERATOR LOGIC (REUSABLE) ---
# ======================================================================================

def run_generator(conn, table_name, num_pieces, position_generator, move_generator, terminal_evaluator):
    """A generic function to build any endgame database."""
    print(f"--- Generating {table_name} ({num_pieces}-piece) ---")
    start_time = time.time()
    
    # 1. Setup Table
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    pos_cols = ', '.join([f'p{i+1}_pos INTEGER' for i in range(num_pieces)])
    pk_cols = ', '.join([f'p{i+1}_pos' for i in range(num_pieces)])
    cursor.execute(f"CREATE TABLE {table_name} ({pos_cols}, turn TEXT, result INTEGER, PRIMARY KEY ({pk_cols}, turn))")
    print(f"Table '{table_name}' created.")

    # 2. Generate Positions
    all_positions = position_generator()
    print(f"Generated {len(all_positions)} unique positions.")
    
    # 3. Retrograde Analysis
    endgame_db = {}
    newly_solved = []
    # Find terminal positions (immediate wins, losses, or draws)
    for pos in all_positions:
        result = terminal_evaluator(pos, move_generator)
        if result is not None:
            endgame_db[pos] = result
            newly_solved.append(pos)
    print(f"Found {len(newly_solved)} terminal positions.")

    ply = 1
    while newly_solved:
        ply += 1
        last_solved, newly_solved = newly_solved, []
        
        for pos in all_positions:
            if pos in endgame_db: continue
            
            moves = [m for m in move_generator(pos) if isinstance(m, tuple)]
            if not moves: continue

            turn = pos[-1]
            if turn == 'w': # White to move: looking for losses (all moves lead to a Red win)
                target_value = ply - 1
                if all(endgame_db.get(move) == target_value for move in moves):
                    endgame_db[pos] = -ply
                    newly_solved.append(pos)
            else: # Red to move: looking for wins (at least one move leads to a White loss)
                target_value = -(ply - 1)
                if any(endgame_db.get(move) == target_value for move in moves):
                    endgame_db[pos] = ply
                    newly_solved.append(pos)
        
        if newly_solved: print(f"Found {len(newly_solved)} positions solved at ply {ply}.")

    # 4. Mark remaining as draws and insert
    to_insert = [pos + (res,) for pos, res in endgame_db.items()]
    unsolved_draws = [pos + (0,) for pos in all_positions if pos not in endgame_db]
    to_insert.extend(unsolved_draws)
    
    q_marks = ','.join(['?'] * (num_pieces + 2))
    cursor.executemany(f"INSERT INTO {table_name} VALUES ({q_marks})", to_insert)
    conn.commit()
    
    end_time = time.time()
    print(f"Inserted {len(to_insert)} records into '{table_name}'.")
    print(f"Finished in {end_time - start_time:.2f} seconds.\n")

# ======================================================================================
# --- 2. DATABASE-SPECIFIC LOGIC ---
# ======================================================================================

# --- 3-PIECE DATABASES ---

def db_2v1_kings():
    """Logic for 2 Red Kings vs 1 White King."""
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 3):
            for i in range(3):
                wk_sq = squares[i]
                rk_sqs = tuple(sorted(list(set(squares) - {wk_sq})))
                positions.add(rk_sqs + (wk_sq, 'r'))
                positions.add(rk_sqs + (wk_sq, 'w'))
        return list(positions)
    
    return "db_2v1_kings", 3, position_generator, get_king_moves_2v1, lambda p, m: 1 if p[-1] == 'r' and not m(p) else None

def db_2K_vs_1M():
    """Logic for 2 Red Kings vs 1 White Man."""
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 3):
            for i in range(3):
                wm_sq = squares[i]
                if ACF_TO_COORD[wm_sq][0] == 0: continue
                rk_sqs = tuple(sorted(list(set(squares) - {wm_sq})))
                positions.add(rk_sqs + (wm_sq, 'r'))
                positions.add(rk_sqs + (wm_sq, 'w'))
        return list(positions)

    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if pos[-1] == 'r' and not moves: return 1
        if pos[-1] == 'w' and any(isinstance(m, dict) for m in moves): return 0
        return None

    return "db_2v1_men", 3, position_generator, get_moves_2Kv1M, terminal_evaluator

# --- 4-PIECE DATABASES ---

def db_3v1_kings():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 4):
            for i in range(4):
                wk_sq = squares[i]
                rk_sqs = tuple(sorted(list(set(squares) - {wk_sq})))
                positions.add(rk_sqs + (wk_sq, 'r'))
                positions.add(rk_sqs + (wk_sq, 'w'))
        return list(positions)
    return "db_3v1_kings", 4, position_generator, get_king_moves_3v1, lambda p, m: 1 if p[-1] == 'r' and not m(p) else None

def db_2v2_kings():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 4):
            for rk_sqs in combinations(squares, 2):
                wk_sqs = tuple(sorted(list(set(squares) - set(rk_sqs))))
                rk_sqs = tuple(sorted(rk_sqs))
                positions.add(rk_sqs + wk_sqs + ('r',))
                positions.add(rk_sqs + wk_sqs + ('w',))
        return list(positions)
    return "db_2v2_kings", 4, position_generator, get_king_moves_2v2, lambda p, m: 1 if not m(p) else None

def db_3v1_men():
    """Logic for 3 Red Men vs 1 White Man."""
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 4):
            for i in range(4):
                wm_sq = squares[i]
                if ACF_TO_COORD[wm_sq][0] == 0: continue
                
                rm_sqs = tuple(sorted(list(set(squares) - {wm_sq})))
                if any(ACF_TO_COORD[s][0] == 7 for s in rm_sqs): continue
                
                positions.add(rm_sqs + (wm_sq, 'r'))
                positions.add(rm_sqs + (wm_sq, 'w'))
        return list(positions)

    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if any(isinstance(m, dict) for m in moves):
            return 1 if pos[-1] == 'r' else 0
        return None
        
    return "db_3v1_men", 4, position_generator, get_moves_3v1_men, terminal_evaluator


# --- 5-PIECE DATABASES ---

def db_3v2_kings():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 5):
            for wk_sqs in combinations(squares, 2):
                rk_sqs = tuple(sorted(list(set(squares) - set(wk_sqs))))
                wk_sqs = tuple(sorted(wk_sqs))
                positions.add(rk_sqs + wk_sqs + ('r',))
                positions.add(rk_sqs + wk_sqs + ('w',))
        return list(positions)
    return "db_3v2_kings", 5, position_generator, get_king_moves_3v2, lambda p, m: 1 if not m(p) else None

def db_3K_vs_1K1M():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 5):
            for i in range(5):
                wk_sq = squares[i]
                remaining = list(set(squares) - {wk_sq})
                for j in range(4):
                    wm_sq = remaining[j]
                    if ACF_TO_COORD[wm_sq][0] == 0: continue
                    rk_sqs = tuple(sorted(list(set(remaining) - {wm_sq})))
                    positions.add(rk_sqs + (wk_sq, wm_sq, 'r'))
                    positions.add(rk_sqs + (wk_sq, wm_sq, 'w'))
        return list(positions)

    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if pos[-1] == 'w' and any(isinstance(m, dict) for m in moves): return 0
        return None
    return "db_3kv1k1m", 5, position_generator, get_moves_3Kv1K1M, terminal_evaluator

def db_2K1M_vs_2K():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 5):
            for i in range(5):
                rm_sq = squares[i]
                if ACF_TO_COORD[rm_sq][0] == 7: continue
                remaining = list(set(squares) - {rm_sq})
                for rk_sqs in combinations(remaining, 2):
                    wk_sqs = tuple(sorted(list(set(remaining) - set(rk_sqs))))
                    rk_sqs = tuple(sorted(rk_sqs))
                    positions.add(rk_sqs + (rm_sq,) + wk_sqs + ('r',))
                    positions.add(rk_sqs + (rm_sq,) + wk_sqs + ('w',))
        return list(positions)
        
    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if pos[-1] == 'r' and any(isinstance(m, dict) for m in moves): return 0
        return None
    return "db_2k1m_vs_2k", 5, position_generator, get_moves_2K1Mv2K, terminal_evaluator

# ======================================================================================
# --- 3. MOVE GENERATION HELPERS ---
# ======================================================================================
def _generic_king_move_generator(r_king_sqs, w_king_sqs, turn):
    board = {ACF_TO_COORD[p]: 'R' for p in r_king_sqs}
    board.update({ACF_TO_COORD[p]: 'W' for p in w_king_sqs})
    moves = []
    
    my_kings = r_king_sqs if turn == 'r' else w_king_sqs
    
    for k_sq in my_kings:
        r_start, c_start = ACF_TO_COORD[k_sq]
        for dr, dc in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            jump_over_coord = (r_start + dr, c_start + dc)
            land_coord = (r_start + 2*dr, c_start + 2*dc)
            if land_coord in COORD_TO_ACF and land_coord not in board and jump_over_coord in board and board[jump_over_coord] != ('R' if turn == 'r' else 'W'):
                return [] # Forced capture

    for k_sq in my_kings:
        r_start, c_start = ACF_TO_COORD[k_sq]
        for dr, dc in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            new_coord = (r_start + dr, c_start + dc)
            if new_coord in COORD_TO_ACF and new_coord not in board:
                new_sq = COORD_TO_ACF[new_coord]
                if turn == 'r':
                    new_r_kings = tuple(sorted(list(set(r_king_sqs) - {k_sq}) + [new_sq]))
                    moves.append(new_r_kings + w_king_sqs + ('w',))
                else:
                    new_w_kings = tuple(sorted(list(set(w_king_sqs) - {k_sq}) + [new_sq]))
                    moves.append(r_king_sqs + new_w_kings + ('r',))
    return moves

def get_king_moves_2v1(pos): return _generic_king_move_generator(pos[:2], pos[2:3], pos[3])
def get_king_moves_3v1(pos): return _generic_king_move_generator(pos[:3], pos[3:4], pos[4])
def get_king_moves_2v2(pos): return _generic_king_move_generator(pos[:2], pos[2:4], pos[4])
def get_king_moves_3v2(pos): return _generic_king_move_generator(pos[:3], pos[3:5], pos[5])

def get_moves_2Kv1M(pos):
    rk_sqs, wm_sq, turn = set(pos[:2]), pos[2], pos[3]
    board = {ACF_TO_COORD[sq]: 'R' for sq in rk_sqs}; board[ACF_TO_COORD[wm_sq]] = 'w'
    moves = []
    if turn == 'r':
        if any(ACF_TO_COORD.get(wm_sq) == (ACF_TO_COORD[rk][0]+dr, ACF_TO_COORD[rk][1]+dc) and (r_land := (ACF_TO_COORD[rk][0]+2*dr, ACF_TO_COORD[rk][1]+2*dc)) in COORD_TO_ACF and r_land not in board for rk in rk_sqs for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]): return []
        for rk_sq in rk_sqs:
            r,c = ACF_TO_COORD[rk_sq]
            for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                new_coord = (r+dr, c+dc)
                if new_coord in COORD_TO_ACF and new_coord not in board:
                    moves.append(tuple(sorted(list(rk_sqs - {rk_sq}) + [COORD_TO_ACF[new_coord]])) + (wm_sq,'w'))
    else:
        r,c = ACF_TO_COORD[wm_sq]
        if any(jsq in rk_sqs for dr,dc in [(-1,-1),(-1,1)] if (jsq := COORD_TO_ACF.get((r+dr,c+dc))) and (r+2*dr, c+2*dc) in COORD_TO_ACF and (r+2*dr,c+2*dc) not in board): return []
        for dr,dc in [(-1,-1),(-1,1)]:
            new_coord = (r+dr, c+dc)
            if new_coord in COORD_TO_ACF and new_coord not in board:
                if new_coord[0] == 0: return [{'is_draw': True}]
                moves.append(tuple(sorted(rk_sqs)) + (COORD_TO_ACF[new_coord], 'r'))
    return moves

def get_moves_3v1_men(pos):
    """Generates legal moves for 3 Red Men vs 1 White Man."""
    rm_sqs, wm_sq, turn = set(pos[:3]), pos[3], pos[4]
    board = {ACF_TO_COORD[p]:'r' for p in rm_sqs}; board[ACF_TO_COORD[wm_sq]]='w'
    moves = []
    
    my_pieces, opp_pieces = (rm_sqs, {wm_sq}) if turn == 'r' else ({wm_sq}, rm_sqs)
    my_dirs = [(1,-1), (1,1)] if turn == 'r' else [(-1,-1), (-1,1)]
    
    for p_sq in my_pieces:
        r,c = ACF_TO_COORD[p_sq]
        for dr,dc in my_dirs:
            jump_over_coord = (r+dr, c+dc)
            land_coord = (r+2*dr, c+2*dc)
            if land_coord in COORD_TO_ACF and land_coord not in board:
                jumped_piece_sq = COORD_TO_ACF.get(jump_over_coord)
                if jumped_piece_sq in opp_pieces:
                    return [] # Capture is terminal

    for p_sq in my_pieces:
        r,c = ACF_TO_COORD[p_sq]
        for dr,dc in my_dirs:
            new_coord = (r+dr, c+dc)
            if new_coord in COORD_TO_ACF and new_coord not in board:
                new_sq = COORD_TO_ACF[new_coord]
                promo_row = 7 if turn == 'r' else 0
                if new_coord[0] == promo_row: return [{'is_promotion': True}]

                if turn == 'r':
                    new_rm_sqs = tuple(sorted(list(rm_sqs - {p_sq}) + [new_sq]))
                    moves.append(new_rm_sqs + (wm_sq, 'w'))
                else:
                    moves.append(tuple(sorted(rm_sqs)) + (new_sq, 'r'))
    return moves

def get_moves_3Kv1K1M(pos):
    rk_sqs, wk_sq, wm_sq, turn = set(pos[:3]), pos[3], pos[4], pos[5]
    board = {ACF_TO_COORD[p]:'R' for p in rk_sqs}; board[ACF_TO_COORD[wk_sq]]='W'; board[ACF_TO_COORD[wm_sq]]='w'
    moves = []
    
    my_pieces = rk_sqs if turn == 'r' else {wk_sq, wm_sq}
    
    for p_sq in my_pieces:
        r_start, c_start = ACF_TO_COORD[p_sq]
        is_king = p_sq != wm_sq
        dirs = [(-1,-1),(-1,1),(1,-1),(1,1)] if is_king else ([(-1,-1),(-1,1)])
        
        for dr, dc in dirs:
             jump_over_coord = (r_start+dr, c_start+dc)
             land_coord = (r_start+2*dr, c_start+2*dc)
             if land_coord in COORD_TO_ACF and land_coord not in board and jump_over_coord in board and board[jump_over_coord] != ('R' if turn == 'r' else 'W'):
                 return []

    if turn == 'r':
        for rk_sq in rk_sqs:
            r,c = ACF_TO_COORD[rk_sq]
            for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                new_coord = (r+dr,c+dc)
                if new_coord in COORD_TO_ACF and new_coord not in board: moves.append(tuple(sorted(list(rk_sqs-{rk_sq})+[COORD_TO_ACF[new_coord]]))+(wk_sq,wm_sq,'w'))
    else:
        r,c = ACF_TO_COORD[wk_sq]
        for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            new_coord = (r+dr,c+dc)
            if new_coord in COORD_TO_ACF and new_coord not in board: moves.append(tuple(sorted(rk_sqs))+(COORD_TO_ACF[new_coord],wm_sq,'r'))
        r,c = ACF_TO_COORD[wm_sq]
        for dr,dc in [(-1,-1),(-1,1)]:
            new_coord = (r+dr,c+dc)
            if new_coord in COORD_TO_ACF and new_coord not in board:
                if new_coord[0] == 0: return [{'is_draw': True}]
                moves.append(tuple(sorted(rk_sqs))+(wk_sq, COORD_TO_ACF[new_coord], 'r'))
    return moves

def get_moves_2K1Mv2K(pos):
    rk_sqs, rm_sq, wk_sqs, turn = set(pos[:2]), pos[2], set(pos[3:5]), pos[5]
    board = {ACF_TO_COORD[p]:'R' for p in rk_sqs}; board[ACF_TO_COORD[rm_sq]]='r'; board.update({ACF_TO_COORD[p]:'W' for p in wk_sqs})
    moves = []

    my_pieces = list(rk_sqs)+[rm_sq] if turn == 'r' else list(wk_sqs)

    for p_sq in my_pieces:
        r_start, c_start = ACF_TO_COORD[p_sq]
        is_king = p_sq != rm_sq
        dirs = [(-1,-1),(-1,1),(1,-1),(1,1)] if is_king else ([(1,-1),(1,1)])
        
        for dr, dc in dirs:
             jump_over_coord = (r_start+dr, c_start+dc)
             land_coord = (r_start+2*dr, c_start+2*dc)
             if land_coord in COORD_TO_ACF and land_coord not in board and jump_over_coord in board and board[jump_over_coord] != ('R' if turn == 'r' else 'W'):
                 return []
    
    if turn == 'r':
        for rk_sq in rk_sqs:
            r,c = ACF_TO_COORD[rk_sq]
            for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                new_coord = (r+dr,c+dc)
                if new_coord in COORD_TO_ACF and new_coord not in board: moves.append(tuple(sorted(list(rk_sqs-{rk_sq})+[COORD_TO_ACF[new_coord]]))+(rm_sq,)+tuple(sorted(wk_sqs))+('w',))
        r,c = ACF_TO_COORD[rm_sq]
        for dr,dc in [(1,-1),(1,1)]:
            new_coord = (r+dr,c+dc)
            if new_coord in COORD_TO_ACF and new_coord not in board:
                if new_coord[0] == 7: return [{'is_draw': True}]
                moves.append(tuple(sorted(rk_sqs))+(COORD_TO_ACF[new_coord],)+tuple(sorted(wk_sqs))+('w',))
    else:
        for wk_sq in wk_sqs:
            r,c = ACF_TO_COORD[wk_sq]
            for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                new_coord = (r+dr,c+dc)
                if new_coord in COORD_TO_ACF and new_coord not in board: moves.append(tuple(sorted(rk_sqs))+(rm_sq,)+tuple(sorted(list(wk_sqs-{wk_sq})+[COORD_TO_ACF[new_coord]]))+('r',))
    return moves

# ======================================================================================
# --- 4. MAIN EXECUTION ---
# ======================================================================================

if __name__ == '__main__':
    if os.path.exists(DB_FILENAME):
        os.remove(DB_FILENAME)
        print(f"Removed old database file: {DB_FILENAME}")
        
    conn = sqlite3.connect(DB_FILENAME)
    
    all_databases = [
        db_2v1_kings, db_2K_vs_1M,
        db_3v1_kings, db_2v2_kings, db_3v1_men,
        db_3v2_kings, db_3K_vs_1K1M, db_2K1M_vs_2K,
    ]
    
    total_start_time = time.time()
    for db_func in all_databases:
        table_name, num_pieces, pos_gen, move_gen, term_eval = db_func()
        run_generator(conn, table_name, num_pieces, pos_gen, move_gen, term_eval)
        
    total_end_time = time.time()
    print(f"===\nALL DATABASES GENERATED. Total time: {total_end_time - total_start_time:.2f} seconds.\n===")
    conn.close()



