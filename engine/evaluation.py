# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS

logger = logging.getLogger('board')

def evaluate_board(board):
       """
    Calculates the static score of the board. Now checks opening book AND endgame databases
    and includes detailed logging for database queries.
    """
    # --- 1. Check Endgame Tables ---
    if board.db_conn:
        try:
            table_name, key = board._get_endgame_key()
            if table_name and key:
                # --- DEBUG LOG 1: What is being sent to the database ---
                logger.info(f"DATABASE_QUERY: Sending query to table '{table_name}' with key: {key}")
                
                cursor = board.db_conn.cursor()
                cursor.execute("SELECT result FROM endgame_tables WHERE table_name = ? AND board_config = ?", (table_name, key))
                result = cursor.fetchone()
                
                # --- DEBUG LOG 2: What is coming back from the database ---
                if result:
                    logger.info(f"DATABASE_RESULT: Received result: '{result[0]}'")
                    if result[0] == 'WIN': return 1000
                    if result[0] == 'LOSS': return -1000
                    return 0 # Draw
                else:
                    logger.info("DATABASE_RESULT: No entry found for this configuration.")

        except Exception as e:
            logger.error(f"DATABASE: Error querying endgame_tables: {e}")
            
    # --- 1. Material Score: Kings are worth 1.5x a regular piece ---
    white_men = board.white_left - board.white_kings
    red_men = board.red_left - board.red_kings
    material_score = (white_men - red_men) + (board.white_kings - board.red_kings) * 1.5

    # --- 2. Positional Scores ---
    white_pos_score = 0
    red_pos_score = 0
    
    PROMOTION_PROGRESS_BONUS = 0.1  # Reward for pieces nearing the king row.
    CENTER_CONTROL_BONUS = 0.1    # Reward for pieces in the center.
    KING_ADVANTAGE_BONUS = 1.0      # Bonus for having the only kings.

    for piece in board.get_all_pieces(WHITE):
        # Add bonus for advancing towards the king row
        white_pos_score += (ROWS - 1 - piece.row) * PROMOTION_PROGRESS_BONUS
        # Add bonus for controlling the center
        if piece.col in {2, 3, 4, 5}:
            white_pos_score += CENTER_CONTROL_BONUS

    for piece in board.get_all_pieces(RED):
        red_pos_score += piece.row * PROMOTION_PROGRESS_BONUS
        if piece.col in {2, 3, 4, 5}:
            red_pos_score += CENTER_CONTROL_BONUS

    positional_score = white_pos_score - red_pos_score

    # --- 3. King Advantage Score ---
    king_advantage = 0
    if board.white_kings > 0 and board.red_kings == 0:
        king_advantage = KING_ADVANTAGE_BONUS
    elif board.red_kings > 0 and board.white_kings == 0:
        king_advantage = -KING_ADVANTAGE_BONUS
        
    final_score = (material_score * 10) + positional_score + king_advantage
    return final_score
