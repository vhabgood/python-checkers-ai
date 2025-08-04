# zobrist_generator.py
import random
import pickle

# --- Constants (subset from main file) ---
EMPTY, RED, WHITE, RED_KING, WHITE_KING = ' ', 'r', 'w', 'R', 'W'
PIECES = [RED, WHITE, RED_KING, WHITE_KING]

def generate_zobrist_keys():
    """
    Generates a dictionary of unique 64-bit random numbers for every
    possible piece on every possible square, plus a turn indicator.
    """
    keys = {}
    # 32 playable squares (1-32)
    for i in range(1, 33):
        for piece in PIECES:
            # The key is a tuple: (piece_char, acf_square_number)
            keys[(piece, i)] = random.getrandbits(64)
    
    # Add a key for the turn
    keys['turn'] = random.getrandbits(64)
    
    print(f"Generated {len(keys)} Zobrist keys.")
    return keys

def save_keys(keys, filename="zobrist_keys.pkl"):
    with open(filename, "wb") as f:
        pickle.dump(keys, f)
    print(f"Zobrist keys saved to {filename}")

if __name__ == '__main__':
    zobrist_keys = generate_zobrist_keys()
    save_keys(zobrist_keys)
