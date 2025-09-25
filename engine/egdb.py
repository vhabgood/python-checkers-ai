# engine/egdb.py
import ctypes, logging, os, platform
from .constants import RED, WHITE, ROWS, COLS

logger = logging.getLogger('egdb')
DB_WIN, DB_LOSS, DB_DRAW, DB_UNKNOWN = 1, 2, 3, 0

class Position(ctypes.Structure):
    _fields_ = [("bm", ctypes.c_uint), ("bk", ctypes.c_uint), ("wm", ctypes.c_uint), ("wk", ctypes.c_uint)]

EGDB_DLL, initlookup, lookup = None, None, None
try:
    lib_name = "egdb64.so" if platform.system() != "Windows" else "egdb64.dll"
    dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', lib_name)
    assert os.path.exists(dll_path), f"{lib_name} not found."
    EGDB_DLL = ctypes.CDLL(dll_path)
    logger.info(f"Successfully loaded {lib_name}")

    initlookup = EGDB_DLL.initlookup
    initlookup.restype, initlookup.argtypes = ctypes.c_int, [ctypes.c_char_p]

    lookup = EGDB_DLL.lookup
    lookup.restype, lookup.argtypes = ctypes.c_int, [ctypes.POINTER(Position), ctypes.c_int]

    # Pass the path to the 'db' directory to the C library
    db_path = os.path.join(os.path.dirname(dll_path), 'db')
    initlookup(db_path.encode('utf-8'))

except Exception as e:
    logger.error(f"Could not load/initialize EGDB library. EGDB disabled. Error: {e}")
    EGDB_DLL = None

BIT_MAP = {(r, c): (r * 4 + (c // 2)) for r, c in [(r,c) for r in range(8) for c in range(8)]}

def board_to_egdb_struct(board):
    # ... (this function is unchanged)
    pos = Position()
    pos.bm, pos.bk, pos.wm, pos.wk = 0, 0, 0, 0
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if piece:
                bit_pos = BIT_MAP.get((r, c))
                if bit_pos is not None:
                    bit = 1 << bit_pos
                    if piece.color == RED:
                        if piece.king: pos.bk |= bit
                        else: pos.bm |= bit
                    else:
                        if piece.king: pos.wk |= bit
                        else: pos.wm |= bit
    return pos

class EGDBDriver:
    def __init__(self):
        self.initialized = bool(EGDB_DLL and lookup)
    def probe(self, board):
        if not self.initialized: return DB_UNKNOWN
        pos_struct = board_to_egdb_struct(board)
        color = 0 if board.turn == RED else 1
        return lookup(ctypes.byref(pos_struct), color)
