# engine/evaluation.py
import logging
import math
from .piece import Piece
from .constants import RED, WHITE, ROWS, COLS
# This import is no longer needed and was causing crashes.
# from engine.search import get_all_move_sequences

logger = logging.getLogger('board')

def evaluate_board(board):
    """
    Calculates the static score of the board.
    Includes state-dependent logic for winning, tied, and losing positions.
    """
    # --- 1. Check Endgame Tables (Highest Priority) ---
    if board.db_conn:
        try:
            table_name, key_string = board._get_endgame_key()
        
            if table_name and key_string:
                # --- THIS IS THE CORRECTED LOGIC ---
            
                # 1. Convert the key string back into a tuple
                key_tuple = eval(key_string)
            
                # 2. Dynamically build the query based on the key's length
                num_pieces = len(key_tuple) - 1
                pos_cols = ', '.join([f'p{i+1}_pos' for i in range(num_pieces)])
            
                # Create the WHERE clause with the correct number of placeholders
                where_clause = ' AND '.join([f'p{i+1}_pos = ?' for i in range(num_pieces)])
            
                sql = f"SELECT result FROM {table_name} WHERE {where_clause} AND turn = ?"
            
                # 3. Execute with the correctly unpacked tuple
                cursor = board.db_conn.cursor()
                params = key_tuple[:-1] + (key_tuple[-1],) # Unpack all piece positions and the turn
            
                logger.debug(f"DATABASE: Querying with SQL: {sql} and PARAMS: {params}")
                cursor.execute(sql, params)
                result = cursor.fetchone()
            
                if result:
                    logger.info(f"DATABASE: SUCCESS! Result for key '{key_string}' is '{result[0]}'. Overriding standard eval.")
                    db_score = int(result[0])
                    # This scoring is perfect, don't change it.
                    if db_score > 0: return 1000 - db_score 
                    if db_score < 0: return -1000 - db_score
                    return 0 # Draw
                else:
                    logger.debug(f"DATABASE: No entry found for key '{key_string}' in table '{table_name}'.")

        except Exception as e:
            logger.error(f"DATABASE: Error during query: {e}", exc_info=True)

    # --- 2. Standard Evaluation ---
    white_men = board.white_left - board.white_kings
    red_men = board.red_left - board.red_kings
    material_score = (white_men - red_men) + (board.white_kings - board.red_kings) * 1.5

    white_pos_score, red_pos_score = 0, 0
    PROMOTION_PROGRESS_BONUS = 0.1
    CENTER_CONTROL_BONUS = 0.1
    KING_ADVANTAGE_BONUS = 1.0
    
    MOBILITY_WEIGHT = 0.1
    # --- FIX: Call get_all_move_sequences as a method of the board object ---
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
    
    total_pieces = board.red_left + board.white_left
    
    if base_score > 20: # A clear advantage for White
        base_score += (24 - total_pieces) * SIMPLIFICATION_BONUS_WEIGHT
        
    elif base_score < -20: # A clear advantage for Red
        base_score -= (24 - total_pieces) * COMPLICATION_PENALTY_WEIGHT

    return base_score
