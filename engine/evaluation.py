# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS
from engine.search import get_all_move_sequences

logger = logging.getLogger('board')

def evaluate_board(board):
    """
    Calculates the static score of the board. Now includes a mobility component
    and checks endgame databases with detailed logging.
    """
    # --- Check Endgame Tables ---
    if board.db_conn:
        try:
            table_name, key = board._get_endgame_key()
            if table_name and key:
                logger.info(f"DATABASE_QUERY: Sending query to table '{table_name}' with key: {key}")
                cursor = board.db_conn.cursor()
                cursor.execute("SELECT result FROM endgame_tables WHERE table_name = ? AND board_config = ?", (table_name, key))
                result = cursor.fetchone()
                
                if result:
                    logger.info(f"DATABASE_RESULT: Success! Received result: '{result[0]}'")
                    if result[0] == 'WIN': return 1000
                    if result[0] == 'LOSS': return -1000
                    return 0 # Draw
                else:
                    logger.info("DATABASE_RESULT: No entry found for this configuration.")

        except Exception as e:
            logger.error(f"DATABASE: Error querying endgame_tables: {e}")

    # --- Standard Evaluation (if not in a database) ---
    white_men = board.white_left - board.white_kings
    red_men = board.red_left - board.red_kings
    material_score = (white_men - red_men) + (board.white_kings - board.red_kings) * 1.5

    white_pos_score, red_pos_score = 0, 0
    PROMOTION_PROGRESS_BONUS = 0.1
    CENTER_CONTROL_BONUS = 0.1
    KING_ADVANTAGE_BONUS = 1.0
    
    # --- Mobility Score ---
    MOBILITY_WEIGHT = 0.1
    # Now calls the board's own method
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

    final_score = (material_score * 10) + positional_score + king_advantage + mobility_score
    return final_score
