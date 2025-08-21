#engine/checkers_game.py
import pygame
import logging
import asyncio
import platform
import random
from engine.board import setup_initial_board, COORD_TO_ACF, count_pieces, is_dark_square, get_valid_moves, make_move, evaluate_board

# Configure logging (level set in main.py)
logger = logging.getLogger('gui')

FPS = 60

class CheckersGame:
    def __init__(self, mode='human', no_db=False):
        """
        Initialize the checkers game with Pygame, board, and menu.
        Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
        Sets up board, pieces, menu, and buttons; logs initial state.
        """
        pygame.init()
        self.mode = mode
        self.no_db = no_db
        self.screen = pygame.display.set_mode((600, 480))  # Extra width for menu
        pygame.display.set_caption("Checkers Game")
        self.board = setup_initial_board()
        self.square_size = 60
        self.font = pygame.font.SysFont('Arial', 14)  # Menu font
        self.number_font = pygame.font.SysFont('Arial', 11)  # Board numbers font (20% smaller)
        self.menu_width = 120
        self.ai_depth = 6
        self.developer_mode = False
        self.show_numbers = True
        self.move_history = []
        self.current_player = 'w' if mode == 'human' else 'r'  # White starts in human mode
        self.score = 0  # Positional score (red - white)
        self.ai_calculating = False
        self.best_move = None
        self.buttons = [
            {'text': 'Force AI Move', 'rect': pygame.Rect(490, 200, 100, 30), 'action': self.force_ai_move},
            {'text': 'Undo Move', 'rect': pygame.Rect(490, 240, 100, 30), 'action': self.undo_move},
            {'text': 'Restart Game', 'rect': pygame.Rect(490, 280, 100, 30), 'action': self.reset_board},
            {'text': 'Export PDN', 'rect': pygame.Rect(490, 320, 100, 30), 'action': self.export_pdn},
            {'text': 'Board Numbers', 'rect': pygame.Rect(490, 360, 100, 30), 'action': self.toggle_numbers},
            {'text': 'Dev Mode: Off', 'rect': pygame.Rect(490, 400, 100, 30), 'action': self.toggle_dev_mode}
        ]
        logger.info("CheckersGame initialized with mode: %s, no-db: %s", mode, no_db)
        red_count, white_count = count_pieces(self.board)
        logger.debug(f"Initial piece count: Red={red_count}, White={white_count}")
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece in ['r', 'w', 'R', 'W']:
                    logger.debug(f"Board state: {piece} at ({row},{col})")

    def reset_board(self):
        """
        Reset the board to initial state and clear move history.
        Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
        Resets board, move history, current player, and score.
        """
        self.board = setup_initial_board()
        self.move_history = []
        self.current_player = 'w' if self.mode == 'human' else 'r'
        self.score = 0
        self.ai_calculating = False
        logger.info("Board reset")
        red_count, white_count = count_pieces(self.board)
        logger.debug(f"Reset piece count: Red={red_count}, White={white_count}")

    def toggle_numbers(self):
        """
        Toggle visibility of ACF board numbers.
        Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
        Toggles self.show_numbers and logs the state change.
        """
        self.show_numbers = not self.show_numbers
        logger.info(f"Board numbers {'shown' if self.show_numbers else 'hidden'}")

    def toggle_dev_mode(self):
        """
        Toggle developer mode and update button text.
        Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
        Toggles self.developer_mode and logs the state change.
        """
        self.developer_mode = not self.developer_mode
        self.buttons[5]['text'] = f"Dev Mode: {'On' if self.developer_mode else 'Off'}"
        logger.info(f"Developer mode: {self.developer_mode}")

    def force_ai_move(self):
        """
        Handle Force AI Move button press.
        If during player's turn, swap to AI and make a move.
        If AI is calculating, apply the best move found so far.
        Updates board, move history, score, and player.
        """
        logger.info("Force AI Move button clicked")
        if self.ai_calculating:
            logger.info("AI calculation interrupted")
            if self.best_move:
                self.apply_move(self.best_move)
            self.ai_calculating = False
        else:
            if self.current_player == 'w' and self.mode == 'human':
                self.current_player = 'r'  # Swap to AI
                logger.info("Swapped sides to AI (red)")
            self.ai_calculating = True
            moves = get_valid_moves(self.board, self.current_player)
            if not moves:
                logger.info("No valid moves for %s", self.current_player)
                self.ai_calculating = False
                return
            # Simulate iterative deepening (replace with search.py later)
            self.best_move = None
            for depth in range(1, self.ai_depth + 1):
                best_score = float('-inf') if self.current_player == 'r' else float('inf')
                for move in moves:
                    score = evaluate_board(make_move(self.board, move))
                    if self.current_player == 'r' and score > best_score:
                        best_score = score
                        self.best_move = move
                    elif self.current_player == 'w' and score < best_score:
                        best_score = score
                        self.best_move = move
                logger.debug(f"Best move at depth {depth}: {self.best_move}")
            if self.best_move:
                self.apply_move(self.best_move)
            self.ai_calculating = False

    def apply_move(self, move):
        """Apply a move to the board, update history, score, and player."""
        from_row, from_col, to_row, to_col, is_jump = move
        from_acf = COORD_TO_ACF.get((from_row, from_col), 'unknown')
        to_acf = COORD_TO_ACF.get((to_row, to_col), 'unknown')
        move_notation = f"{from_acf}-{to_acf}" if not is_jump else f"{from_acf}x{to_acf}"
        logger.info(f"Applying AI move for {self.current_player}: {move_notation}")
        self.board = make_move(self.board, move)
        self.move_history.append(move_notation)
        self.score = evaluate_board(self.board)
        logger.debug(f"Updated score: {self.score}")
        self.current_player = 'w' if self.current_player == 'r' else 'r'

    def undo_move(self):
        # Placeholder for undo move
        if self.move_history:
            logger.info("Undo move triggered (not implemented)")
        else:
            logger.debug("No moves to undo")

    def export_pdn(self):
        """
        Export move history in PDN notation.
        Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
        Writes move history to game.pdn with standard headers.
        """
        try:
            with open('game.pdn', 'w') as f:
                f.write("[Event \"Checkers Game\"]\n")
                f.write("[Site \"Local\"]\n")
                f.write("[Date \"2025.08.21\"]\n")
                f.write("[Red \"Player1\"]\n")
                f.write("[White \"Player2\"]\n")
                f.write("[Result \"*\"]\n")
                for i, move in enumerate(self.move_history, 1):
                    f.write(f"{i}. {move}\n")
            logger.info("Exported move history to game.pdn")
        except Exception as e:
            logger.error(f"Failed to export PDN: {str(e)}")

    def draw_board(self):
        """
        Draw the 8x8 checkers board, pieces, numbers, and menu.
        Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
        Renders board (dark/light squares), pieces, ACF numbers, and menu with score and buttons.
        """
        self.screen.fill((255, 255, 255))  # White background
        # Draw menu panel (right side)
        pygame.draw.rect(self.screen, (200, 200, 200), (480, 0, self.menu_width, 480))
        # Draw menu items
        score_text = self.font.render(f"Score: {self.score}", True, (0, 0, 0))
        self.screen.blit(score_text, (490, 80))
        red_count, white_count = count_pieces(self.board)
        red_text = self.font.render(f"Red: {red_count}+0", True, (0, 0, 0))
        white_text = self.font.render(f"White: {white_count}+0", True, (0, 0, 0))
        self.screen.blit(red_text, (490, 120))
        self.screen.blit(white_text, (490, 140))
        ply_text = self.font.render(f"AI Depth: {self.ai_depth}", True, (0, 0, 0))
        self.screen.blit(ply_text, (490, 160))
        for button in self.buttons:
            pygame.draw.rect(self.screen, (100, 100, 100), button['rect'])
            text = self.font.render(button['text'], True, (255, 255, 255))
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)
        # Draw board
        for row in range(8):
            for col in range(8):
                x = col * self.square_size
                y = row * self.square_size
                # Dark squares (lightened ~20% from original 70,70,70), light squares (beige)
                color = (85, 85, 85) if is_dark_square(row, col) else (245, 245, 220)
                pygame.draw.rect(self.screen, color, (x, y, self.square_size, self.square_size))
                # Draw pieces if present
                piece = self.board[row][col]
                if piece in ['r', 'w', 'R', 'W']:
                    piece_color = (200, 0, 0) if piece.lower() == 'r' else (255, 255, 255)
                    center_x = x + self.square_size // 2
                    center_y = y + self.square_size // 2
                    radius = int((self.square_size // 2 - 5) * 0.95)  # 5% smaller
                    pygame.draw.circle(self.screen, piece_color, (center_x, center_y), radius)
                    logger.debug(f"Drawing piece {piece} at ({row},{col}), pos ({center_x},{center_y})")
                # Draw ACF numbers on dark squares if enabled
                if self.show_numbers and (row, col) in COORD_TO_ACF:
                    acf = COORD_TO_ACF[(row, col)]
                    if is_dark_square(row, col):
                        text = self.number_font.render(str(acf), True, (0, 0, 0))  # Black text
                        text_rect = text.get_rect(center=(x + self.square_size // 2, y + self.square_size // 2))
                        self.screen.blit(text, text_rect)
                        logger.debug(f"Rendering ACF {acf} at ({row},{col})")
                    else:
                        logger.error(f"Attempted to render ACF {acf} on light square at ({row},{col})")
        pygame.display.flip()

    def update_loop(self):
        """
        Handle Pygame events and update game state.
        Verified working 100% correctly for rendering and working buttons as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
        Processes quit events, mouse clicks, and calls draw_board.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                logger.info("Pygame window closed")
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = event.pos
                    logger.debug(f"Mouse click at {mouse_pos}")
                    for button in self.buttons:
                        if button['rect'].collidepoint(mouse_pos):
                            logger.info(f"Button clicked: {button['text']}")
                            try:
                                button['action']()
                            except Exception as e:
                                logger.error(f"Button {button['text']} action failed: {str(e)}")
                            break
                        else:
                            logger.debug(f"Click at {mouse_pos} missed button {button['text']} at {button['rect']}")
        self.draw_board()
        return True

async def main(mode='human', no_db=False):
    """
    Initialize and run the game loop.
    Verified working 100% correctly as of commit d2f58b72a719f621afa165a3ecbae26d00e07499.
    Creates CheckersGame instance and runs async loop, handling Pyodide compatibility.
    """
    game = CheckersGame(mode, no_db)
    while True:
        if not game.update_loop():
            break
        await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
