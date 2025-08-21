#engine/checkers_game.py
import pygame
import logging
import asyncio
import platform
from .board import setup_initial_board, COORD_TO_ACF, count_pieces

# Configure logging (level set in main.py)
logger = logging.getLogger('gui')

FPS = 60

class CheckersGame:
    def __init__(self, mode='human'):
        # Initialize Pygame
        pygame.init()
        self.mode = mode
        self.screen = pygame.display.set_mode((480, 560))  # Extra height for menu
        pygame.display.set_caption("Checkers Game")
        self.board = setup_initial_board()
        self.square_size = 60
        self.font = pygame.font.SysFont('Arial', 20)
        self.menu_height = 80
        self.buttons = [
            {'text': 'New Game', 'rect': pygame.Rect(10, 10, 100, 30), 'action': self.reset_board},
            {'text': f'Mode: {self.mode}', 'rect': pygame.Rect(120, 10, 100, 30), 'action': self.toggle_mode}
        ]
        logger.info("CheckersGame initialized with mode: %s", mode)
        red_count, white_count = count_pieces(self.board)
        logger.debug(f"Initial piece count: Red={red_count}, White={white_count}")

    def reset_board(self):
        # Reset the board to initial state
        self.board = setup_initial_board()
        logger.info("Board reset")
        red_count, white_count = count_pieces(self.board)
        logger.debug(f"Reset piece count: Red={red_count}, White={white_count}")

    def toggle_mode(self):
        # Toggle between human and AI mode
        self.mode = 'ai' if self.mode == 'human' else 'human'
        self.buttons[1]['text'] = f'Mode: {self.mode}'
        logger.info("Switched to mode: %s", self.mode)

    def draw_board(self):
        # Draw the 8x8 checkers board, pieces, and menu
        self.screen.fill((255, 255, 255))  # White background
        # Draw menu bar
        pygame.draw.rect(self.screen, (200, 200, 200), (0, 0, 480, self.menu_height))
        for button in self.buttons:
            pygame.draw.rect(self.screen, (100, 100, 100), button['rect'])
            text = self.font.render(button['text'], True, (255, 255, 255))
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)
        # Draw board
        for row in range(8):
            for col in range(8):
                x, y = col * self.square_size, row * self.square_size + self.menu_height
                # Dark squares (dark gray) for playable, light squares (beige) for non-playable
                color = (50, 50, 50) if (row + col) % 2 == 0 else (245, 245, 220)
                pygame.draw.rect(self.screen, color, (x, y, self.square_size, self.square_size))
                # Draw pieces if present
                piece = self.board[row][col]
                if piece in ['r', 'w', 'R', 'W']:
                    piece_color = (200, 0, 0) if piece.lower() == 'r' else (255, 255, 255)
                    pygame.draw.circle(self.screen, piece_color, 
                                     (x + self.square_size // 2, y + self.square_size // 2), 
                                     self.square_size // 2 - 5)
                    logger.debug(f"Drawing piece {piece} at ({row},{col})")
                # Draw ACF numbers on dark squares
                if (row, col) in COORD_TO_ACF:
                    acf = COORD_TO_ACF[(row, col)]
                    if (row + col) % 2 == 0:  # Match board.py's dark square logic
                        text = self.font.render(str(acf), True, (255, 255, 0))
                        self.screen.blit(text, (x + 25, y + 25))
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
