# engine/evaluation.py
import logging
import math
#from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS

logger = logging.getLogger('board')


def evaluate_board(board):
    """
    Calculates the static score of the board.
    Includes state-dependent logic for winning, tied, and losing positions.
    """
    # --- 1. Check Endgame Tables (Highest Priority) ---
    if board.db_conn:
        try:
            # The _get_endgame_key function now returns the tuple directly
            table_name, key_tuple = board._get_endgame_key()

            # We check if the key_tuple is valid, and REMOVE the old eval() line
            if table_name and key_tuple:
                num_pieces = len(key_tuple) - 1
                where_clause = ' AND '.join([f'p{i + 1}_pos = ?' for i in range(num_pieces)])
                sql = f"SELECT result FROM {table_name} WHERE {where_clause} AND turn = ?"
                
                # The key_tuple is already in the correct format for the SQL parameters
                params = key_tuple

                human_readable_turn = "White" if key_tuple[-1] == 'w' else "Red"
                human_readable_key = f"Positions: {key_tuple[:-1]}, Turn: {human_readable_turn}"
                logger.debug(f"DATABASE: Querying table '{table_name}' for position: {human_readable_key}")

                cursor = board.db_conn.cursor()
                cursor.execute(sql, params)
                result = cursor.fetchone()

                if result:
                    logger.info(
                        f"DATABASE: SUCCESS! Result for key '{key_tuple}' is '{result[0]}'. Overriding standard eval.")
                    db_score = int(result[0])
                    if db_score > 0: return 1000 - db_score
                    if db_score < 0: return -1000 - db_score
                    return 0  # Draw
                else:
                    logger.debug(f"DATABASE: No entry found for key '{key_tuple}' in table '{table_name}'.")

        except Exception as e:
            logger.error(f"DATABASE: Error during query: {e}", exc_info=True)

    # --- 2. Standard Static Evaluation ---
    material_score = (board.white_left - board.red_left) + (board.white_kings - board.red_kings) * 1.5

    white_pos_score = 0
    red_pos_score = 0
    PROMOTION_PROGRESS_BONUS = 0.1
    CENTER_CONTROL_BONUS = 0.1
    KING_ADVANTAGE_BONUS = 1.0
    MOBILITY_WEIGHT = 0.1

    white_moves_count = len(list(board.get_all_move_sequences(WHITE)))
    red_moves_count = len(list(board.get_all_move_sequences(RED)))
    mobility_score = (white_moves_count - red_moves_count) * MOBILITY_WEIGHT

    for piece in board.get_all_pieces(WHITE):
        white_pos_score += (ROWS - 1 - piece.row) * PROMOTION_PROGRESS_BONUS
        if piece.col in {2, 3, 4, 5}:
            white_pos_score += CENTER_CONTROL_BONUS

    for piece in board.get_all_pieces(RED):
        red_pos_score += piece.row * PROMOTION_PROGRESS_BONUS
        if piece.col in {2, 3, 4, 5}:
            red_pos_score += CENTER_CONTROL_BONUS

    positional_score = white_pos_score - red_pos_score

    king_advantage = 0
    if board.white_kings > 0 and board.red_kings == 0:
        king_advantage = KING_ADVANTAGE_BONUS
    elif board.red_kings > 0 and board.white_kings == 0:
        king_advantage = -KING_ADVANTAGE_BONUS

    base_score = (material_score * 10) + positional_score + king_advantage + mobility_score

    # --- 3. State-Dependent Strategic Adjustments ---
    SIMPLIFICATION_BONUS_WEIGHT = 0.2
    COMPLICATION_PENALTY_WEIGHT = 0.2

    # If winning, prioritize simplifying. If losing, prioritize complicating.
    if base_score > 1.5:  # Clearly winning
        return base_score + ((12 - board.red_left) * SIMPLIFICATION_BONUS_WEIGHT)
    elif base_score < -1.5:  # Clearly losing
        return base_score - ((12 - board.white_left) * COMPLICATION_PENALTY_WEIGHT)

    return base_score
