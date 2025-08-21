#engine/checkers_game.py
import pygame
import logging
import asyncio
import platform
from engine.board import setup_initial_board, COORD_TO_ACF, count_pieces, is_dark_square

# Configure logging (level set in main.py)
logger = logging.getLogger('gui')

FPS = 60

class CheckersGame:
    def __init__(self, mode='human'):
        # Initialize Pygame
        pygame.init()
        self.mode = mode
        self.screen = pygame.display.set_mode((600, 480))  # Extra width for menu
        pygame.display.set_caption("Checkers Game")
        self.board = setup_initial_board()
        self.square_size = 60
        self.font = pygame.font.SysFont('Arial', 20)
        self.menu_width = 120
        self.ai_ply = 6
        self.developer_mode = False
        self.show_numbers = True
        self.move_history = []
        self.buttons = [
            {'text': 'Force AI Move', 'rect': pygame.Rect(490, 200, 100, 30), 'action': self.force_ai_move},
            {'text': 'Undo Move', 'rect': pygame.Rect(490, 240, 100, 30), 'action': self.undo_move},
            {'text': 'Restart Game', 'rect': pygame.Rect(490, 280, 100, 30), 'action': self.reset_board},
            {'text': 'Export PDN', 'rect': pygame.Rect(490, 320, 100, 30), 'action': self.export_pdn},
            {'text': 'Toggle Numbers', 'rect': pygame.Rect(490, 360, 100, 30), 'action': self.toggle_numbers},
            {'text': 'Dev Mode: Off', 'rect': pygame.Rect(490, 400, 100, 30), 'action': self.toggle_dev_mode}
        ]
        logger.info("CheckersGame initialized with mode: %s", mode)
        red_count, white_count = count_pieces(self.board)
        logger.debug(f"Initial piece count: Red={red_count}, White={white_count}")
        for row in range(8):
            for col in range(8):
                if self.board[row][col] in ['r', 'w', 'R', 'W']:
                    logger.debug(f"Board state: {self.board[row][col]} at ({row},{col})")

    def reset_board(self):
        # Reset the board to initial state
        self.board = setup_initial_board()
        self.move_history = []
        logger.info("Board reset")
        red_count, white_count = count_pieces(self.board)
        logger.debug(f"Reset piece count: Red={red_count}, White={white_count}")

    def toggle_mode(self):
        # Toggle between human and AI mode
        self.mode = 'ai' if self.mode == 'human' else 'human'
        logger.info("Switched to mode: %s", self.mode)

    def force_ai_move(self):
        # Placeholder for AI move
        logger.info("Force AI move triggered (not implemented)")
        # To be implemented in gameplay fix

    def undo_move(self):
        # Placeholder for undo move
        if self.move_history:
            logger.info("Undo move triggered (not implemented)")
            # To be implemented in gameplay fix
        else:
            logger.debug("No moves to undo")

    def export_pdn(self):
        # Export move history in PDN notation
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

    def toggle_numbers(self):
        # Toggle ACF number visibility
        self.show_numbers = not self.show_numbers
        logger.info(f"ACF numbers {'shown' if self.show_numbers else 'hidden'}")

    def toggle_dev_mode(self):
        # Toggle developer mode
        self.developer_mode = not self.developer_mode
        self.buttons[5]['text'] = f"Dev Mode: {'On' if self.developer_mode else 'Off'}"
        logger.info(f"Developer mode: {self.developer_mode}")

    def draw_board(self):
        # Draw the 8x8 checkers board, pieces, and menu
        self.screen.fill((255, 255, 255))  # White background
        # Draw menu panel (right side)
        pygame.draw.rect(self.screen, (200, 200, 200), (480, 0, self.menu_width, 480))
        # Draw menu items
        score_text = self.font.render("Score: 0-0", True, (0, 0, 0))
        self.screen.blit(score_text, (490, 80))
        red_count, white_count = count_pieces(self.board)
        piece_text = self.font.render(f"Piece Count: {red_count}+0 red, {white_count}+0 white", True, (0, 0, 0))
        self.screen.blit(piece_text, (490, 120))
        ply_text = self.font.render(f"AI Ply: {self.ai_ply}", True, (0, 0, 0))
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
                # Dark squares (dark gray) for playable, light squares (beige) for non-playable
                color = (70, 70, 70) if is_dark_square(row, col) else (245, 245, 220)
                pygame.draw.rect(self.screen, color, (x, y, self.square_size, self.square_size))
                # Draw pieces if present
                piece = self.board[row][col]
                if piece in ['r', 'w', 'R', 'W']:
                    piece_color = (200, 0, 0) if piece.lower() == 'r' else (255, 255, 255)
                    pygame.draw.circle(self.screen, piece_color, 
                                     (x + self.square_size // 2, y + self.square_size // 2), 
                                     self.square_size // 2 - 5)
                    logger.debug(f"Drawing piece {piece} at ({row},{col})")
                # Draw ACF numbers on dark squares if enabled
                if self.show_numbers and (row, col) in COORD_TO_ACF:
                    acf = COORD_TO_ACF[(row, col)]
                    if is_dark_square(row, col):
                        text = self.font.render(str(acf), True, (255, 255, 0))
                        text_rect = text.get_rect(center=(x + self.square_size // 2, y + self.square_size // 2))
                        self.screen.blit(text, text_rect)
                        logger.debug(f"Rendering ACF {acf} at ({row},{col})")
                    else:
                        logger.error(f"Attempted to render ACF {acf} on light square at ({row},{col})")
        pygame.display.flip()

    def update_loop(self):
        # Handle events and update game state
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                logger.info("Pygame window closed")
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    for button in self.buttons:
                        if button['rect'].collidepoint(event.pos):
                            button['action']()
                            break
        self.draw_board()
        return True

async def main(mode='human'):
    # Initialize and run the game loop
    game = CheckersGame(mode)
    while True:
        if not game.update_loop():
            break
        await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
