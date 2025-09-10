# engine/evaluation.py
import logging
import math
from .constants import RED, WHITE, ROWS, COLS, COORD_TO_ACF

logger = logging.getLogger('board')

# ======================================================================================
# --- 1. Piece-Square Tables (PSTs) ---
# ======================================================================================
# These tables assign a strategic value to each square for each piece type.
# The values are higher for squares that are positionally stronger.
# We use a dummy value at index 0 to align with 1-based ACF square numbering.

# For Men: Value increases as they approach the promotion row.
MAN_PST = [
    0.0,  # Dummy
     5,  5,  5,  5,  # Row 1 (Red's Start)
     4,  4,  4,  4,  # Row 2
     3,  3,  3,  3,  # Row 3
     2,  2,  2,  2,  # Row 4
     1,  1,  1,  1,  # Row 5
     0,  0,  0,  0,  # Row 6
    -1, -1, -1, -1,  # Row 7 (Vulnerable)
    -2, -2, -2, -2,  # Row 8 (Vulnerable)
]

# For Kings: Value is highest in the center, providing control and mobility.
KING_PST = [
    0.0,  # Dummy
    1.0, 1.0, 1.0, 1.0,
    1.5, 1.5, 1.5, 1.5,
    2.0, 2.5, 2.5, 2.0,
    2.5, 3.0, 3.0, 2.5,
    2.5, 3.0, 3.0, 2.5,
    2.0, 2.5, 2.5, 2.0,
    1.5, 1.5, 1.5, 1.5,
    1.0, 1.0, 1.0, 1.0,
]

# A small bonus for pieces on the edge, which can be part of a strong defense.
EDGE_BONUS = 0.3
EDGE_SQUARES = {1, 5, 8, 9, 13, 17, 21, 24, 25, 29, 32}

# ======================================================================================
# --- 2. The Evaluation Function ---
# ======================================================================================

def evaluate_board(board):
    """
    Calculates the static score of the board using advanced positional evaluation.
    A positive score favors White, a negative score favors Red.
    """
    # --- Phase 1: Check Endgame Tables (Highest Priority) ---
    if board.db_conn:
        try:
            table_name, key_tuple = board._get_endgame_key()
            if table_name and key_tuple:
                num_pieces = len(key_tuple) - 1
                where_clause = ' AND '.join([f'p{i + 1}_pos = ?' for i in range(num_pieces)])
                sql = f"SELECT result FROM {table_name} WHERE {where_clause} AND turn = ?"
                params = key_tuple

                cursor = board.db_conn.cursor()
                cursor.execute(sql, params)
                result = cursor.fetchone()

                if result:
                    logger.info(f"DATABASE: SUCCESS! Result for key '{key_tuple}' is '{result[0]}'. Overriding standard eval.")
                    db_score = int(result[0])
                    # Convert distance-to-win into a large score for the search
                    if db_score > 0: return 1000 - db_score  # Shorter wins are better
                    if db_score < 0: return -1000 - db_score # Longer losses are better
                    return 0  # Draw

        except Exception as e:
            logger.error(f"DATABASE: Error during query: {e}", exc_info=True)

    # --- Phase 2: Standard Static Evaluation ---
    
    # Base material score
    material_score = (board.white_left - board.red_left) + (board.white_kings - board.red_kings) * 1.5
    
    # Positional score from PSTs
    positional_score = 0
    for r in range(ROWS):
        for c in range(COLS):
            piece = board.get_piece(r, c)
            if piece == 0:
                continue

            acf_pos = COORD_TO_ACF.get((r, c))
            if not acf_pos: continue

            if piece.king:
                score = KING_PST[acf_pos]
                if acf_pos in EDGE_SQUARES:
                    score += EDGE_BONUS
                positional_score += score if piece.color == WHITE else -score
            else: # It's a man
                # The PST is written from Red's perspective.
                # For White, we flip the board by reading the PST backwards.
                score = MAN_PST[acf_pos] if piece.color == RED else MAN_PST[33 - acf_pos]
                if acf_pos in EDGE_SQUARES:
                    score += EDGE_BONUS
                positional_score += -score if piece.color == RED else score


    # Mobility score
    white_moves_count = len(list(board.get_all_move_sequences(WHITE)))
    red_moves_count = len(list(board.get_all_move_sequences(RED)))
    mobility_score = (white_moves_count - red_moves_count) * 0.1

    # --- Phase 3: Combine Scores ---
    
    # Weights for each component of the evaluation
    MATERIAL_WEIGHT = 10.0
    POSITIONAL_WEIGHT = 0.1
    
    final_score = (material_score * MATERIAL_WEIGHT) + \
                  (positional_score * POSITIONAL_WEIGHT) + \
                  mobility_score

    # --- Phase 4: State-Dependent Adjustments (same as before) ---
    if final_score > 1.5:  # Clearly winning
        return final_score + ((12 - board.red_left) * 0.2)
    elif final_score < -1.5:  # Clearly losing
        return final_score - ((12 - board.white_left) * 0.2)

    return final_score


