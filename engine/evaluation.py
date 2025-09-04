# engine/evaluation.py
import logging
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS

logger = logging.getLogger('board')

def evaluate_board(board):
    """
    Calculates the static score of the board.
    """
    # --- Check Endgame Tables ---
    if board.db_conn:
        try:
            endgame_result = board._get_endgame_key()
            if endgame_result and endgame_result[0] is not None:
                table_name, key = endgame_result
                
                logger.debug(f"DATABASE: Querying table '{table_name}' with key: {key}")
                cursor = board.db_conn.cursor()
                cursor.execute("SELECT result FROM endgame_tables WHERE table_name = ? AND board_config = ?", (table_name, key))
                result = cursor.fetchone()
                
                if result:
                    logger.info(f"DATABASE: SUCCESS! Result for key '{key}' is '{result[0]}'. Overriding standard eval.")
                    # --- FIX: Handle integer scores from database ---
                    db_score = int(result[0])
                    # Return a very high or low score to represent a forced win/loss.
                    # The score also encodes the number of moves to the win/loss.
                    if db_score > 0: return 1000 - db_score # A faster win (lower ply) is better
                    if db_score < 0: return -1000 - db_score # A slower loss (higher ply) is better
                    return 0 # Draw
                else:
                    logger.debug(f"DATABASE: No entry found for key '{key}' in table '{table_name}'.")

        except Exception as e:
            logger.error(f"DATABASE: Error during query: {e}", exc_info=True)

    # --- Standard Evaluation (only runs if not in a database scenario) ---
    white_men = board.white_left - board.white_kings
    red_men = board.red_left - board.red_kings
    material_score = (white_men - red_men) + (board.white_kings - board.red_kings) * 1.5

    white_pos_score, red_pos_score = 0, 0
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
        
    final_score = (material_score * 10) + positional_score + king_advantage + mobility_score
    return final_score
