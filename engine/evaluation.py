# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS
# The incorrect 'from .board import ...' line has been removed.

logger = logging.getLogger('board')

def evaluate_board(board):
    """
    Calculates the static score of the board. Now correctly interprets database results.
    """
    # --- Check Endgame Tables ---
    if board.db_conn:
        try:
            endgame_result = board._get_endgame_key()
            # If the key function returns a table, we are in a known endgame scenario
            if endgame_result and endgame_result[0] is not None:
                table_name, key = endgame_result
                
                logger.debug(f"DATABASE: Querying table '{table_name}' with key: {key}")
                cursor = board.db_conn.cursor()
                cursor.execute("SELECT result FROM endgame_tables WHERE table_name = ? AND board_config = ?", (table_name, key))
                result = cursor.fetchone()
                
                if result:
                    logger.info(f"DATABASE: SUCCESS! Result for key '{key}' is '{result[0]}'. Overriding standard eval.")
                    db_score = int(result[0])
                    if db_score > 0: return 1000 - db_score
                    if db_score < 0: return -1000 - db_score
                    return 0 # Explicit Draw from DB
                else:
                    # --- FIX: If a key is valid but not found in the table, it IS a draw ---
                    # We must not fall back to the heuristic in this case.
                    logger.debug(f"DATABASE: No entry found for key '{key}'. Position is a known DRAW.")
                    return 0 # Return a neutral score for the draw

        except Exception as e:
            logger.error(f"DATABASE: Error during query: {e}", exc_info=True)

    # --- Standard Evaluation (only runs if NOT in a database scenario) ---
    white_men = board.white_left - board.white_kings
    red_men = board.red_left - board.red_kings
    material_score = (white_men - red_men) + (board.white_kings - board.red_kings) * 1.5

    white_pos_score, red_pos_score = 0, 0
    PROMOTION_PROGRESS_BONUS = 0.1
    CENTER_CONTROL_BONUS = 0.1
    KING_ADVANTAGE_BONUS = 1.0
    
    MOBILITY_WEIGHT = 0.1
    white_moves_count = len(list(board.get_all_move_sequences(board, WHITE)))
    red_moves_count = len(list(board.get_all_move_sequences(board, RED)))
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
        
    final_score = (material_score * 10) + positional_score + king_advantage + mobility_score
    return final_score
