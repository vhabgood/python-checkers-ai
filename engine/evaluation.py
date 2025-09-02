# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS

logger = logging.getLogger('board')

def evaluate_board(board):
    """
    Calculates the static score of the board. This version now checks the opening book database.
    """
    # --- NEW: Check the Opening Book database ---
    if board.db_conn and board.hash:
        try:
            cursor = board.db_conn.cursor()
            # Query the database for the current board position's hash
            cursor.execute("SELECT score FROM opening_book WHERE board_hash = ?", (board.hash,))
            result = cursor.fetchone()
            if result:
                logger.info("EVALUATION: Found position in opening book database.")
                # If found, return the pre-calculated score
                return result[0] + random.uniform(-0.01, 0.01)
        except Exception as e:
            logger.error(f"DATABASE: Error querying opening_book: {e}")

    # --- Standard Evaluation (if not in a database) ---
    white_men = board.white_left - board.white_kings
    red_men = board.red_left - board.red_kings
    material_score = (white_men - red_men) + (board.white_kings - board.red_kings) * 1.5

    white_pos_score, red_pos_score = 0, 0
    PROMOTION_PROGRESS_BONUS = 0.1
    CENTER_CONTROL_BONUS = 0.1
    KING_ADVANTAGE_BONUS = 1.0

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
        
    final_score = (material_score * 10) + positional_score + king_advantage
    return final_score
