# engine/egdb.py
# This file provides the Python interface to the C++ endgame database library.

import ctypes
import os
import logging
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF
from .constants import ACF_TO_COORD, RED
from .constants import DB_UNKNOWN, DB_WIN, DB_LOSS, DB_DRAW, DB_UNAVAILABLE, RESULT_MAP

# --- C-level Data Structures ---
# This must match the 'position' struct in the C++ code.
class CPosition(ctypes.Structure):
    _fields_ = [
        ("bm", ctypes.c_uint32),
        ("bk", ctypes.c_uint32),
        ("wm", ctypes.c_uint32),
        ("wk", ctypes.c_uint32),
    ]

# --- Main Driver Class ---
class EGDBDriver:
    """Manages loading and interacting with the checkers_db.so shared library."""
    
    def __init__(self, db_path=None):
        """Initializes the driver, loads the library, and sets up function signatures."""
        self.lib = None
        self.egdb_lookup = None
        self.initialized = False
        self.logger = logging.getLogger('search')
        
        # Determine the library path relative to this file
        lib_name = 'checkers_db.so'
        engine_dir = os.path.dirname(os.path.abspath(__file__))
        lib_path = os.path.join(engine_dir, lib_name)

        if not os.path.exists(lib_path):
            self.logger.warning(f"EGDB: Library file not found at {lib_path}. EGDB will be disabled.")
            return

        try:
            self.lib = ctypes.CDLL(lib_path)
            self._setup_c_functions(db_path)
            self.initialized = True
            self.logger.info(f"EGDB driver loaded successfully from {lib_path}")
        except Exception as e:
            self.logger.error(f"EGDB: Failed to load or initialize library: {e}", exc_info=True)
            self.initialized = False

    def board_to_pos(self, board):
        """Converts a board object to a C-compatible CPosition struct."""
        bm, bk, wm, wk = 0, 0, 0, 0  # Initialize all to zero
        for r in range(ROWS):
            for c in range(COLS):
                piece = board.get_piece(r, c)
                if piece is not None:
                    acf_pos = COORD_TO_ACF.get((r, c))
                    if acf_pos:
                        bit_idx = acf_pos - 1
                        mask = 1 << bit_idx
                        if piece.color == RED:
                            if piece.king:
                                bk |= mask
                            else:
                                bm |= mask
                        else:  # WHITE
                            if piece.king:
                                wk |= mask
                            else:
                                wm |= mask
        return CPosition(bm, bk, wm, wk)
        
    def _setup_c_functions(self, db_path):
        """Defines the argument and return types for the C++ functions."""
        init_func = self.lib.db_init
        init_func.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        init_func.restype = ctypes.c_int
        
        # Setup for the MODIFIED EGDB_lookup
        self.egdb_lookup = self.lib.EGDB_lookup
        # --- THIS IS THE FIX ---
        # Explicitly use c_uint32 to guarantee a 32-bit unsigned integer,
        # matching the C++ uint32_t and removing any ambiguity that could
        # cause memory corruption on the stack.
        self.egdb_lookup.argtypes = [
        ctypes.POINTER(ctypes.c_int), # R (result)
        ctypes.c_uint32,             # bm
        ctypes.c_uint32,             # bk
        ctypes.c_uint32,             # wm
        ctypes.c_uint32,             # wk
        ctypes.c_int,                # color
        ctypes.POINTER(ctypes.c_int) # mtc
        ]
        self.egdb_lookup.restype = ctypes.c_int
        
        if db_path:
            abs_db_path = os.path.abspath(db_path)
            self.logger.info(f"EGDB: Initializing database with path: {abs_db_path}")
            init_func(db_path.encode('utf-8'), 0, 0)

    def _board_to_c_position(self, board):
        """Converts the Python Board object to the C-level bitboard struct."""
        bm, bk, wm, wk = 0, 0, 0, 0
        for r in range(ROWS):
            for c in range(COLS):
                if (r + c) % 2 == 1:
                    piece = board.get_piece(r, c)
                    if piece:
                        acf_pos = COORD_TO_ACF.get((r, c))
                        if acf_pos is not None:
                            bit_idx = acf_pos - 1
                            mask = 1 << bit_idx
                            if piece.color == RED:
                                if piece.king: bk |= mask
                                else: bm |= mask
                            else: # WHITE
                                if piece.king: wk |= mask
                                else: wm |= mask
        return CPosition(bm, bk, wm, wk)

    def probe(self, board):
        """Probes the database for the given board state."""
        if not self.initialized:
            return DB_UNAVAILABLE, 0

        # This part is correct
        c_pos = self.board_to_pos(board)
        color_code = 2 if board.turn == RED else 1
        
        result = ctypes.c_int()
        mtc = ctypes.c_int()

        # --- THIS IS THE FINAL, CRITICAL FIX ---
        # Unpack the struct and pass its fields as individual arguments
        # to match the C++ function signature.
        self.egdb_lookup(
            ctypes.byref(result),
            c_pos.bm, c_pos.bk, c_pos.wm, c_pos.wk,
            color_code,
            ctypes.byref(mtc)
        )
        # ------------------------------------

        result_value = result.value
        mtc_value = mtc.value

        # Logging block (no changes needed here)
        self.logger.debug("<--- EGDB Response ---")
        self.logger.debug(f"  Result: {result_value} ({RESULT_MAP.get(result_value, 'ERR')}), MTC: {mtc_value}")

        return result_value, mtc_value


