# engine/zobrist.py
import random

def generate_zobrist_keys():
    """
    Generates a full set of Zobrist keys for hashing checkers positions
    using a more robust random number generator to prevent collisions.
    """
    # --- FIX: Use SystemRandom for higher quality random numbers ---
    rng = random.SystemRandom()
    # -----------------------------------------------------------
    
    keys = {}
    # Generate a key for whose turn it is
    keys['turn'] = rng.getrandbits(64)
    
    # Generate a key for each piece type on each square
    pieces = ['r', 'w', 'R', 'W'] # red man, white man, red king, white king
    for i in range(1, 33): # For each of the 32 legal squares
        for piece in pieces:
            keys[(piece, i)] = rng.getrandbits(64)
            
    return keys
