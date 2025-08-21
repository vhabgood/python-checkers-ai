#engine/checkers_game.py
import pygame
import logging
import asyncio
import platform
from .board import setup_initial_board, COORD_TO_ACF, count_pieces

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('gui')

FPS = 60

class CheckersGame:
    def __init__(self, mode='human'):
        # Initialize Pygame
        pygame.init()
        self.mode = mode
        self.screen = pygame.display.set_mode((480, 480))
        pygame.display.set_caption("Checkers Game")
        self.board = setup_initial_board()
        self.square_size = 60
        self.font = pygame.font.SysFont('Arial', 20)
        logger.info("CheckersGame initialized with mode: %s", mode)
        red_count, white_count = count_pieces(self.board)
        logger.debug(f"Initial piece count: Red={red_count}, White={white_count}")

    def draw_board(self):
        # Draw the 8x8 checkers board and pieces
        self.screen.fill((255, 255, 255))  # White background
        for row in range(8):
            for col in range(8):
                x, y = col * self.square_size, row * self.square_size
                color = (255, 0, 0) if (row + col) % 2 == 0 else (0, 0, 0)
                pygame.draw.rect(self.screen, color, (x, y, self.square_size, self.square_size))
                if self.board[row][col] in ['r', 'w', 'R', 'W']:
                    piece_color = (200, 0, 0) if self.board[row][col].lower() == 'r' else (255, 255, 255)
                    pygame.draw.circle(self.screen, piece_color, (x + self.square_size // 2, y + self.square_size // 2), self.square_size // 2 - 5)
                if (row, col) in COORD_TO_ACF:
                    acf = COORD_TO_ACF[(row, col)]
                    logger.debug(f"Rendering ACF {acf} at ({row},{col})")
                    text = self.font.render(str(acf), True, (255, 255, 0))
                    self.screen.blit(text, (x + 25, y + 25))
        pygame.display.flip()

    def update_loop(self):
        # Handle events and update game state
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                logger.info("Pygame window closed")
                return False
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
