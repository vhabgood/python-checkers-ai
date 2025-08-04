# custom_book_generator.py
import pickle
import random
from Quiescence30 import Checkers # Import our game engine

# --- CONFIGURATION ---
# The maximum depth of the opening book (number of half-moves). 8-10 is a good start.
MAX_BOOK_DEPTH = 10
# The search depth the AI uses to evaluate which move is "best" at each step.
SEARCH_DEPTH_PER_MOVE = 8
# The probability to explore non-optimal moves.
# (Best move, 2nd best, 3rd best, etc.)
DROPOUT_CHANCES = [1.0, 0.5, 0.25] 
# The filename for the new book.
OUTPUT_FILENAME = "custom_book2.pkl"

# --- Global variables to hold our book and track progress ---
opening_book = {}
processed_boards = set()

def analyze_position(game_state):
    """
    Analyzes all legal moves from a position and returns them sorted by score.
    This is different from find_best_move, which only returns the single best move.
    """
    all_possible_moves = game_state.get_all_possible_moves(game_state.turn)
    if not all_possible_moves:
        return []

    evaluated_moves = []
    is_maximizing = game_state.turn == 'r'
    
    for start, end in all_possible_moves:
        # Create a temporary game state to evaluate the move
        temp_game = Checkers([row[:] for row in game_state.board], game_state.turn)
        further_jumps = temp_game.perform_move_for_search(start, end)
        
        # We need to run a minimax search for EACH move to get an accurate score
        score, _ = Checkers._static_minimax(
            temp_game.board, 
            temp_game.turn, 
            SEARCH_DEPTH_PER_MOVE - 1, 
            -float('inf'), 
            float('inf'), 
            not further_jumps, 
            [0], None, [(start, end)]
        )
        evaluated_moves.append({'move': (start, end), 'score': score})

    # Sort moves from best to worst
    evaluated_moves.sort(key=lambda x: x['score'], reverse=is_maximizing)
    return evaluated_moves

def expand_node(game_state, current_depth):
    """
    Recursively explores moves from the current board state (node).
    """
    if current_depth >= MAX_BOOK_DEPTH:
        return

    board_key = game_state._get_board_tuple()
    if board_key in processed_boards:
        return
        
    processed_boards.add(board_key)

    print(f"Expanding Node at Depth {current_depth}... Total Positions: {len(opening_book)}")

    # Find the best moves from this position
    top_moves = analyze_position(game_state)
    if not top_moves:
        return

    # --- Dropout Expansion Logic ---
    for i, move_data in enumerate(top_moves):
        # Apply dropout probability
        if i < len(DROPOUT_CHANCES):
            if random.random() <= DROPOUT_CHANCES[i]:
                # This move is selected for expansion
                
                # 1. Add the parent state and this move to the book
                current_board_key = game_state._get_board_tuple()
                if current_board_key not in opening_book:
                    opening_book[current_board_key] = move_data['move']

                # 2. Create the child state
                next_game_state = Checkers([row[:] for row in game_state.board], game_state.turn)
                next_game_state.perform_move_for_search(move_data['move'][0], move_data['move'][1])
                
                # 3. Recurse
                expand_node(next_game_state, current_depth + 1)
        else:
            break # Stop considering moves beyond the dropout chances array

def save_book(filename):
    with open(filename, "wb") as f:
        pickle.dump(opening_book, f)
    print(f"\n--- Generation Complete ---")
    print(f"Saved {len(opening_book)} positions to {filename}")


if __name__ == '__main__':
    print("--- Starting Custom Opening Book Generation ---")
    print(f"Max Depth: {MAX_BOOK_DEPTH}, Search Depth per Move: {SEARCH_DEPTH_PER_MOVE}")
    
    initial_game = Checkers()
    expand_node(initial_game, 0)
    save_book(OUTPUT_FILENAME)

