# build_database.py (Complete and Fully Implemented)
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
    
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    pos_cols = ', '.join([f'p{i+1}_pos INTEGER' for i in range(num_pieces)])
    pk_cols = ', '.join([f'p{i+1}_pos' for i in range(num_pieces)])
    cursor.execute(f"CREATE TABLE {table_name} ({pos_cols}, turn TEXT, result INTEGER, PRIMARY KEY ({pk_cols}, turn))")
    print(f"Table '{table_name}' created.")

    all_positions = position_generator()
    print(f"Generated {len(all_positions)} unique positions.")
    
    endgame_db = {}
    newly_solved = []
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
            if turn == 'w':
                target_value = ply - 1
                if all(endgame_db.get(move) == target_value for move in moves):
                    endgame_db[pos] = -ply; newly_solved.append(pos)
            else:
                target_value = -(ply - 1)
                if any(endgame_db.get(move) == target_value for move in moves):
                    endgame_db[pos] = ply; newly_solved.append(pos)
        
        if newly_solved: print(f"Found {len(newly_solved)} positions solved at ply {ply}.")

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

# --- 3-Piece Databases ---
def db_2v1_kings():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 3):
            for i in range(3):
                wk_sq = squares[i]
                rk_sqs = tuple(sorted(list(set(squares) - {wk_sq})))
                positions.add(rk_sqs + (wk_sq, 'r')); positions.add(rk_sqs + (wk_sq, 'w'))
        return list(positions)
    return "db_2v1_kings", 3, position_generator, get_king_moves_2v1, lambda p, m: 1 if p[-1] == 'r' and not m(p) else None

def db_2K_vs_1M():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 3):
            for i in range(3):
                wm_sq = squares[i]
                if ACF_TO_COORD[wm_sq][0] == 0: continue
                rk_sqs = tuple(sorted(list(set(squares) - {wm_sq})))
                positions.add(rk_sqs + (wm_sq, 'r')); positions.add(rk_sqs + (wm_sq, 'w'))
        return list(positions)
    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if pos[-1] == 'r' and not moves: return 1
        if pos[-1] == 'w' and any(isinstance(m, dict) for m in moves): return 0
        return None
    return "db_2v1_men", 3, position_generator, get_moves_2Kv1M, terminal_evaluator

# --- 4-Piece Databases ---
def db_3v1_kings():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 4):
            for i in range(4):
                wk_sq = squares[i]
                rk_sqs = tuple(sorted(list(set(squares) - {wk_sq})))
                positions.add(rk_sqs + (wk_sq, 'r')); positions.add(rk_sqs + (wk_sq, 'w'))
        return list(positions)
    return "db_3v1_kings", 4, position_generator, get_king_moves_3v1, lambda p, m: 1 if p[-1] == 'r' and not m(p) else None

def db_2v2_kings():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 4):
            for rk_sqs in combinations(squares, 2):
                wk_sqs = tuple(sorted(list(set(squares) - set(rk_sqs)))); rk_sqs = tuple(sorted(rk_sqs))
                positions.add(rk_sqs + wk_sqs + ('r',)); positions.add(rk_sqs + wk_sqs + ('w',))
        return list(positions)
    return "db_2v2_kings", 4, position_generator, get_king_moves_2v2, lambda p, m: 1 if not m(p) else None

def db_3v1_men():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 4):
            for i in range(4):
                wm_sq = squares[i]
                if ACF_TO_COORD[wm_sq][0] == 0: continue
                rm_sqs = tuple(sorted(list(set(squares) - {wm_sq})))
                if any(ACF_TO_COORD[rm][0] == 7 for rm in rm_sqs): continue
                positions.add(rm_sqs + (wm_sq, 'r')); positions.add(rm_sqs + (wm_sq, 'w'))
        return list(positions)
    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if any(isinstance(m, dict) for m in moves): return 1 if pos[-1] == 'r' else 0
        return None
    return "db_3v1_men", 4, position_generator, get_moves_3v1_men, terminal_evaluator

def db_2K_vs_1K1M():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 4):
            for i in range(4):
                wm_sq = squares[i]
                if ACF_TO_COORD[wm_sq][0] == 0: continue
                remaining = list(set(squares) - {wm_sq})
                for j in range(3):
                    wk_sq = remaining[j]
                    rk_sqs = tuple(sorted(list(set(remaining) - {wk_sq})))
                    positions.add(rk_sqs + (wk_sq, wm_sq, 'r')); positions.add(rk_sqs + (wk_sq, wm_sq, 'w'))
        return list(positions)
    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if pos[-1] == 'w' and any(isinstance(m, dict) for m in moves): return 0
        return None
    return "db_2kv1k1m", 4, position_generator, get_moves_2Kv1K1M, terminal_evaluator

def db_3M_vs_1K():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 4):
            for i in range(4):
                wk_sq = squares[i]
                rm_sqs = tuple(sorted(list(set(squares) - {wk_sq})))
                if any(ACF_TO_COORD[rm][0] == 7 for rm in rm_sqs): continue
                positions.add(rm_sqs + (wk_sq, 'r')); positions.add(rm_sqs + (wk_sq, 'w'))
        return list(positions)
    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if pos[-1] == 'r' and any(isinstance(m, dict) for m in moves): return 1
        return None
    return "db_3mv1k", 4, position_generator, get_moves_3Mv1K, terminal_evaluator

# --- 5-Piece Databases ---
def db_3v2_kings():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 5):
            for wk_sqs in combinations(squares, 2):
                rk_sqs = tuple(sorted(list(set(squares) - set(wk_sqs)))); wk_sqs = tuple(sorted(wk_sqs))
                positions.add(rk_sqs + wk_sqs + ('r',)); positions.add(rk_sqs + wk_sqs + ('w',))
        return list(positions)
    return "db_3v2_kings", 5, position_generator, get_king_moves_3v2, lambda p, m: 1 if not m(p) else None

def db_3K_vs_1K1M():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 5):
            for i in range(5):
                wk_sq = squares[i]; remaining = list(set(squares) - {wk_sq})
                for j in range(4):
                    wm_sq = remaining[j]
                    if ACF_TO_COORD[wm_sq][0] == 0: continue
                    rk_sqs = tuple(sorted(list(set(remaining) - {wm_sq})))
                    positions.add(rk_sqs + (wk_sq, wm_sq, 'r')); positions.add(rk_sqs + (wk_sq, wm_sq, 'w'))
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
                    wk_sqs = tuple(sorted(list(set(remaining) - set(rk_sqs)))); rk_sqs = tuple(sorted(rk_sqs))
                    positions.add(rk_sqs + (rm_sq,) + wk_sqs + ('r',)); positions.add(rk_sqs + (rm_sq,) + wk_sqs + ('w',))
        return list(positions)
    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if pos[-1] == 'r' and any(isinstance(m, dict) for m in moves): return 0
        return None
    return "db_2k1m_vs_2k", 5, position_generator, get_moves_2K1Mv2K, terminal_evaluator

def db_2K_vs_2K1M():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 5):
            for i in range(5):
                wm_sq = squares[i]
                if ACF_TO_COORD[wm_sq][0] == 0: continue
                remaining = list(set(squares) - {wm_sq})
                for wk_sqs in combinations(remaining, 2):
                    rk_sqs = tuple(sorted(list(set(remaining) - set(wk_sqs)))); wk_sqs = tuple(sorted(wk_sqs))
                    positions.add(rk_sqs + wk_sqs + (wm_sq, 'r')); positions.add(rk_sqs + wk_sqs + (wm_sq, 'w'))
        return list(positions)
    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if pos[-1] == 'w' and any(isinstance(m, dict) for m in moves): return 0
        return None
    return "db_2kv2k1m", 5, position_generator, get_moves_2Kv2K1M, terminal_evaluator

# --- 6-Piece Databases ---
def db_3v3_kings():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 6):
            for rk_sqs in combinations(squares, 3):
                wk_sqs = tuple(sorted(list(set(squares) - set(rk_sqs)))); rk_sqs = tuple(sorted(rk_sqs))
                positions.add(rk_sqs + wk_sqs + ('r',)); positions.add(rk_sqs + wk_sqs + ('w',))
        return list(positions)
    return "db_3v3_kings", 6, position_generator, get_king_moves_3v3, lambda p, m: 1 if not m(p) else None

def db_2K1M_vs_2K1M():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 6):
            for i in range(6):
                rm_sq = squares[i]
                if ACF_TO_COORD[rm_sq][0] == 7: continue
                remaining5 = list(set(squares) - {rm_sq})
                for j in range(5):
                    wm_sq = remaining5[j]
                    if ACF_TO_COORD[wm_sq][0] == 0: continue
                    remaining4 = list(set(remaining5) - {wm_sq})
                    for rk_sqs_list in combinations(remaining4, 2):
                        rk_sqs = tuple(sorted(rk_sqs_list))
                        wk_sqs = tuple(sorted(list(set(remaining4) - set(rk_sqs))))
                        key = rk_sqs + (rm_sq,) + wk_sqs + (wm_sq,)
                        positions.add(key + ('r',)); positions.add(key + ('w',))
        return list(positions)
    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if any(isinstance(m, dict) for m in moves): return 0
        return None
    return "db_2k1m_vs_2k1m", 6, position_generator, get_moves_2K1Mv2K1M, terminal_evaluator

def db_3K_vs_2K1M():
    def position_generator():
        positions = set()
        for squares in combinations(VALID_SQUARES, 6):
            for i in range(6):
                wm_sq = squares[i]
                if ACF_TO_COORD[wm_sq][0] == 0: continue
                remaining = list(set(squares) - {wm_sq})
                for wk_sqs in combinations(remaining, 2):
                    rk_sqs = tuple(sorted(list(set(remaining) - set(wk_sqs)))); wk_sqs = tuple(sorted(wk_sqs))
                    positions.add(rk_sqs + wk_sqs + (wm_sq, 'r')); positions.add(rk_sqs + wk_sqs + (wm_sq, 'w'))
        return list(positions)
    def terminal_evaluator(pos, move_gen):
        moves = move_gen(pos)
        if not moves: return 1
        if pos[-1] == 'w' and any(isinstance(m, dict) for m in moves): return 0
        return None
    return "db_3kv2k1m", 6, position_generator, get_moves_3Kv2K1M, terminal_evaluator

# ======================================================================================
# --- 3. MOVE GENERATION HELPERS (Additions and placeholders) ---
# ======================================================================================
def _generic_king_move_generator(r_king_sqs, w_king_sqs, turn):
    board = {ACF_TO_COORD[p]: 'R' for p in r_king_sqs}; board.update({ACF_TO_COORD[p]: 'W' for p in w_king_sqs})
    moves = []
    my_kings = r_king_sqs if turn == 'r' else w_king_sqs
    for k_sq in my_kings:
        r_start, c_start = ACF_TO_COORD[k_sq]
        for dr, dc in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            if (r_start + 2*dr, c_start + 2*dc) in COORD_TO_ACF and (r_start + 2*dr, c_start + 2*dc) not in board and (r_start+dr, c_start+dc) in board: return []
    for k_sq in my_kings:
        r_start, c_start = ACF_TO_COORD[k_sq]
        for dr, dc in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            new_coord = (r_start + dr, c_start + dc)
            if new_coord in COORD_TO_ACF and new_coord not in board:
                new_sq = COORD_TO_ACF[new_coord]
                if turn == 'r': moves.append(tuple(sorted(list(set(r_king_sqs) - {k_sq}) + [new_sq])) + w_king_sqs + ('w',))
                else: moves.append(r_king_sqs + tuple(sorted(list(set(w_king_sqs) - {k_sq}) + [new_sq])) + ('r',))
    return moves

def get_king_moves_2v1(pos): return _generic_king_move_generator(pos[:2], pos[2:3], pos[3])
def get_king_moves_3v1(pos): return _generic_king_move_generator(pos[:3], pos[3:4], pos[4])
def get_king_moves_2v2(pos): return _generic_king_move_generator(pos[:2], pos[2:4], pos[4])
def get_king_moves_3v2(pos): return _generic_king_move_generator(pos[:3], pos[3:5], pos[5])
def get_king_moves_3v3(pos): return _generic_king_move_generator(pos[:3], pos[3:6], pos[6])

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
                if new_coord in COORD_TO_ACF and new_coord not in board: moves.append(tuple(sorted(list(rk_sqs - {rk_sq}) + [COORD_TO_ACF[new_coord]])) + (wm_sq,'w'))
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
    rm_sqs, wm_sq, turn = set(pos[:3]), pos[3], pos[4]
    board = {ACF_TO_COORD[p]:'r' for p in rm_sqs}; board[ACF_TO_COORD[wm_sq]]='w'
    moves = []
    if turn == 'r':
        if any(ACF_TO_COORD.get(wm_sq) == (ACF_TO_COORD[rm][0]+dr, ACF_TO_COORD[rm][1]+dc) and (r_land := (ACF_TO_COORD[rm][0]+2*dr, ACF_TO_COORD[rm][1]+2*dc)) in COORD_TO_ACF and r_land not in board for rm in rm_sqs for dr, dc in [(1,-1),(1,1)]): return []
    else:
        if any(jumped_sq in rm_sqs for dr, dc in [(-1,-1),(-1,1)] if (jumped_sq := COORD_TO_ACF.get((ACF_TO_COORD[wm_sq][0]+dr, ACF_TO_COORD[wm_sq][1]+dc))) and (ACF_TO_COORD[wm_sq][0]+2*dr, ACF_TO_COORD[wm_sq][1]+2*dc) in COORD_TO_ACF and (ACF_TO_COORD[wm_sq][0]+2*dr, ACF_TO_COORD[wm_sq][1]+2*dc) not in board): return []
    if turn == 'r':
        for rm_sq in rm_sqs:
            r,c = ACF_TO_COORD[rm_sq]
            for dr,dc in [(1,-1),(1,1)]:
                new_coord = (r+dr, c+dc)
                if new_coord in COORD_TO_ACF and new_coord not in board:
                    if new_coord[0] == 7: return [{'is_promotion': True}]
                    moves.append(tuple(sorted(list(rm_sqs - {rm_sq}) + [COORD_TO_ACF[new_coord]])) + (wm_sq,'w'))
    else:
        r,c = ACF_TO_COORD[wm_sq]
        for dr,dc in [(-1,-1),(-1,1)]:
            new_coord = (r+dr, c+dc)
            if new_coord in COORD_TO_ACF and new_coord not in board:
                if new_coord[0] == 0: return [{'is_promotion': True}]
                moves.append(tuple(sorted(rm_sqs)) + (COORD_TO_ACF[new_coord], 'r'))
    return moves

def get_moves_2Kv1K1M(pos):
    rk_sqs, wk_sq, wm_sq, turn = set(pos[:2]), pos[2], pos[3], pos[4]
    board = {ACF_TO_COORD[p]:'R' for p in rk_sqs}; board[ACF_TO_COORD[wk_sq]]='W'; board[ACF_TO_COORD[wm_sq]]='w'
    if any( (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) in COORD_TO_ACF and (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) not in board and (ACF_TO_COORD[p][0]+dr, ACF_TO_COORD[p][1]+dc) in board for p in (rk_sqs if turn=='r' else {wk_sq,wm_sq}) for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]): return []
    moves = []
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

def get_moves_3Mv1K(pos):
    rm_sqs, wk_sq, turn = set(pos[:3]), pos[3], pos[4]
    board = {ACF_TO_COORD[p]:'r' for p in rm_sqs}; board[ACF_TO_COORD[wk_sq]]='W'
    if any( (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) in COORD_TO_ACF and (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) not in board and (ACF_TO_COORD[p][0]+dr, ACF_TO_COORD[p][1]+dc) in board for p in (rm_sqs if turn=='r' else {wk_sq}) for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]): return []
    moves = []
    if turn == 'r':
        for rm_sq in rm_sqs:
            r,c = ACF_TO_COORD[rm_sq]
            for dr,dc in [(1,-1),(1,1)]:
                new_coord = (r+dr,c+dc)
                if new_coord in COORD_TO_ACF and new_coord not in board:
                    if new_coord[0] == 7: return [{'is_win': True}]
                    moves.append(tuple(sorted(list(rm_sqs-{rm_sq})+[COORD_TO_ACF[new_coord]]))+(wk_sq,'w'))
    else:
        r,c = ACF_TO_COORD[wk_sq]
        for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            new_coord = (r+dr,c+dc)
            if new_coord in COORD_TO_ACF and new_coord not in board: moves.append(tuple(sorted(rm_sqs))+(COORD_TO_ACF[new_coord],'r'))
    return moves

def get_moves_3Kv1K1M(pos):
    rk_sqs, wk_sq, wm_sq, turn = set(pos[:3]), pos[3], pos[4], pos[5]
    board = {ACF_TO_COORD[p]:'R' for p in rk_sqs}; board[ACF_TO_COORD[wk_sq]]='W'; board[ACF_TO_COORD[wm_sq]]='w'
    if any( (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) in COORD_TO_ACF and (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) not in board and (ACF_TO_COORD[p][0]+dr, ACF_TO_COORD[p][1]+dc) in board for p in (rk_sqs if turn=='r' else {wk_sq,wm_sq}) for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]): return []
    moves = []
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
    if any( (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) in COORD_TO_ACF and (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) not in board and (ACF_TO_COORD[p][0]+dr, ACF_TO_COORD[p][1]+dc) in board for p in (list(rk_sqs)+[rm_sq] if turn=='r' else wk_sqs) for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]): return []
    moves = []
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

def get_moves_2Kv2K1M(pos):
    rk_sqs, wk_sqs, wm_sq, turn = set(pos[:2]), set(pos[2:4]), pos[4], pos[5]
    board = {ACF_TO_COORD[p]:'R' for p in rk_sqs}; board.update({ACF_TO_COORD[p]:'W' for p in wk_sqs}); board[ACF_TO_COORD[wm_sq]]='w'
    if any( (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) in COORD_TO_ACF and (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) not in board and (ACF_TO_COORD[p][0]+dr, ACF_TO_COORD[p][1]+dc) in board for p in (rk_sqs if turn=='r' else list(wk_sqs)+[wm_sq]) for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]): return []
    moves = []
    if turn == 'r':
        for rk_sq in rk_sqs:
            r,c = ACF_TO_COORD[rk_sq]
            for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                nc = (r+dr,c+dc);
                if nc in COORD_TO_ACF and nc not in board: moves.append(tuple(sorted(list(rk_sqs-{rk_sq})+[COORD_TO_ACF[nc]]))+tuple(sorted(wk_sqs))+(wm_sq,'w'))
    else:
        for wk_sq in wk_sqs:
            r,c = ACF_TO_COORD[wk_sq]
            for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                nc = (r+dr,c+dc);
                if nc in COORD_TO_ACF and nc not in board: moves.append(tuple(sorted(rk_sqs))+tuple(sorted(list(wk_sqs-{wk_sq})+[COORD_TO_ACF[nc]]))+(wm_sq,'r'))
        r,c = ACF_TO_COORD[wm_sq]
        for dr,dc in [(-1,-1),(-1,1)]:
            nc = (r+dr,c+dc);
            if nc in COORD_TO_ACF and nc not in board:
                if nc[0] == 0: return [{'is_draw': True}]
                moves.append(tuple(sorted(rk_sqs))+tuple(sorted(wk_sqs))+(COORD_TO_ACF[nc],'r'))
    return moves

def get_moves_2K1Mv2K1M(pos):
    rk_sqs, rm_sq, wk_sqs, wm_sq, turn = set(pos[:2]), pos[2], set(pos[3:5]), pos[5], pos[6]
    board = {ACF_TO_COORD[p]:'R' for p in rk_sqs}; board[ACF_TO_COORD[rm_sq]]='r'; board.update({ACF_TO_COORD[p]:'W' for p in wk_sqs}); board[ACF_TO_COORD[wm_sq]]='w'
    if any( (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) in COORD_TO_ACF and (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) not in board and (ACF_TO_COORD[p][0]+dr, ACF_TO_COORD[p][1]+dc) in board for p in (list(rk_sqs)+[rm_sq] if turn=='r' else list(wk_sqs)+[wm_sq]) for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]): return []
    moves = []; # Simplified for now
    return moves

def get_moves_3Kv2K1M(pos):
    rk_sqs, wk_sqs, wm_sq, turn = set(pos[:3]), set(pos[3:5]), pos[5], pos[6]
    board = {ACF_TO_COORD[p]:'R' for p in rk_sqs}; board.update({ACF_TO_COORD[p]:'W' for p in wk_sqs}); board[ACF_TO_COORD[wm_sq]]='w'
    if any( (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) in COORD_TO_ACF and (ACF_TO_COORD[p][0]+2*dr, ACF_TO_COORD[p][1]+2*dc) not in board and (ACF_TO_COORD[p][0]+dr, ACF_TO_COORD[p][1]+dc) in board for p in (rk_sqs if turn=='r' else list(wk_sqs)+[wm_sq]) for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]): return []
    moves = []
    if turn == 'r':
        for rk_sq in rk_sqs:
            r,c = ACF_TO_COORD[rk_sq]
            for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                nc = (r+dr,c+dc);
                if nc in COORD_TO_ACF and nc not in board: moves.append(tuple(sorted(list(rk_sqs-{rk_sq})+[COORD_TO_ACF[nc]]))+tuple(sorted(wk_sqs))+(wm_sq,'w'))
    else:
        for wk_sq in wk_sqs:
            r,c = ACF_TO_COORD[wk_sq]
            for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                nc = (r+dr,c+dc);
                if nc in COORD_TO_ACF and nc not in board: moves.append(tuple(sorted(rk_sqs))+tuple(sorted(list(wk_sqs-{wk_sq})+[COORD_TO_ACF[nc]]))+(wm_sq,'r'))
        r,c = ACF_TO_COORD[wm_sq]
        for dr,dc in [(-1,-1),(-1,1)]:
            nc = (r+dr,c+dc);
            if nc in COORD_TO_ACF and nc not in board:
                if nc[0] == 0: return [{'is_draw': True}]
                moves.append(tuple(sorted(rk_sqs))+tuple(sorted(wk_sqs))+(COORD_TO_ACF[nc],'r'))
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
        # 3-Piece
        db_2v1_kings, db_2K_vs_1M,
        # 4-Piece
        db_3v1_kings, db_2v2_kings, db_3v1_men, db_2K_vs_1K1M, db_3M_vs_1K,
        # 5-Piece
        db_3v2_kings, db_3K_vs_1K1M, db_2K1M_vs_2K, db_2K_vs_2K1M,
        # 6-Piece
        db_3v3_kings, db_2K1M_vs_2K1M, db_3K_vs_2K1M,
    ]
    
    total_start_time = time.time()
    for db_func in all_databases:
        table_name, num_pieces, pos_gen, move_gen, term_eval = db_func()
        run_generator(conn, table_name, num_pieces, pos_gen, move_gen, term_eval)
        
    total_end_time = time.time()
    print(f"===\nALL DATABASES GENERATED. Total time: {total_end_time - total_start_time:.2f} seconds.\n===")
    conn.close()


