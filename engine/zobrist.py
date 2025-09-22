# engine/zobrist.py
import random

def generate_zobrist_keys():
    """
    Generates a full set of Zobrist keys for hashing checkers positions.
    """
    random.seed() # <-- ADD THIS LINE
    keys = {}
    # Generate a key for whose turn it is
    keys['turn'] = random.getrandbits(64)
    
    # Generate a key for each piece type on each square
    pieces = ['r', 'w', 'R', 'W'] # red man, white man, red king, white king
    for i in range(1, 33): # For each of the 32 legal squares
        for piece in pieces:
            keys[(piece, i)] = random.getrandbits(64)
            
    return keys
