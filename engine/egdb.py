# engine/egdb.py
import ctypes
import logging
import os
from .constants import RED, WHITE

logger = logging.getLogger('egdb')

# --- Define constants from egdb.h for clarity ---
EGDB_WIN = 1
EGDB_LOSS = 2
EGDB_DRAW = 3
EGDB_UNKNOWN = 0
EGDB_NORMAL = 0 # Bitboard type

# --- Load the EGDB Driver Library ---
try:
    # This assumes egdb64.dll is in the project's root directory
    dll_path = "egdb64.dll"
    if not os.path.exists(dll_path):
        # Fallback for running from within the engine directory
        dll_path = os.path.join(os.path.dirname(__file__), '..', 'egdb64.dll')

    EGDB_DLL = ctypes.CDLL(dll_path)
    logger.info("Successfully loaded egdb64.dll")

except OSError as e:
    logger.error(f"Could not load egdb64.dll. Make sure it's in your project's root directory. Error: {e}")
    EGDB_DLL = None

# ======================================================================================
# --- STEP 2: Define C Structures and Function Prototypes ---
# ======================================================================================

# --- C Structures, replicated as Python classes ---
# This mirrors the EGDB_NORMAL_BITBOARD struct from egdb.h
class EGDB_NORMAL_BITBOARD(ctypes.Structure):
    _fields_ = [
        ("black_man", ctypes.c_uint),
        ("white_man", ctypes.c_uint),
        ("black_king", ctypes.c_uint),
        ("white_king", ctypes.c_uint),
    ]

# This mirrors the EGDB_BITBOARD union from egdb.h
class EGDB_BITBOARD(ctypes.Union):
    _fields_ = [
        ("normal", EGDB_NORMAL_BITBOARD),
        # The C union has another member, 'row_reversed', but we only need 'normal'
    ]

# The EGDB_DRIVER struct is opaque to us (we just use a pointer to it),
# so we don't need to define its fields.
class EGDB_DRIVER(ctypes.Structure):
    pass

# --- C Function Prototypes ---
# This tells ctypes what the arguments and return types are for each C function we will use.
if EGDB_DLL:
    # EGDB_API EGDB_DRIVER *__cdecl egdb_open(...)
    egdb_open = EGDB_DLL.egdb_open
    egdb_open.restype = ctypes.POINTER(EGDB_DRIVER)
    egdb_open.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p]

    # int (__cdecl *lookup)(struct egdb_driver *handle, EGDB_BITBOARD *position, int color, int cl);
    # This function is called through a function pointer inside the EGDB_DRIVER struct.
    # We will define this part later when we wrap the driver object.

    # int (__cdecl *close)(struct egdb_driver *handle);
    # Also a function pointer in the struct.
