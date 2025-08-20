# main.py
import pygame
import logging
import time
import threading
import argparse
from engine.checkers_game import Checkers
from engine.constants import *

logging.basicConfig(
    filename=f"/home/victor/Desktop/checkers/Programs/checkers_project/{time.strftime('%Y-%m-%d_%H-%M-%S')}_checkers_debug.log",
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CheckersGUI:
    def __init__(self, use_db=True):
        try:
            pygame.init()
            self.screen = pygame.display.set_mode((768, 676))
            pygame.display.set_caption("Checkers")
            self.clock = pygame.time.Clock()
            self.checkers = Checkers(use_db=use_db)
            self.player_side = None
            self.selected_piece = None
            self.legal_moves = []
            self.developer_mode = False
            self.eval_scroll_offset = 0
            self.ai_move = None
            self.ai_move_lock = threading.Lock()
            self.ai_computing = False
            self.show_acf_numbers = True  # Debug: Show ACF numbers by default
            logging.info("CheckersGUI initialized")
            # Uncomment to test endgame database
            # self.checkers.game_board.setup_test_board()
        except Exception as e:
            logging.error(f"Initialization failed: {str(e)}")
            raise

    def draw_board(self):
        try:
            self.screen.fill(COLOR_BG)
            if self.ai_computing:
                font = pygame.font.Font(None, 36)
                text = font.render("Computing AI move...", True, COLOR_TEXT)
                self.screen.blit(text, (250, 300))
                pygame.display.flip()
                return
            # Draw board with correct light/dark squares (bottom-left light: (row + col) % 2 == 1 = light)
            for row in range(8):
                for col in range(8):
                    color = COLOR_LIGHT_SQUARE if (row + col) % 2 == 1 else COLOR_DARK_SQUARE
                    pygame.draw.rect(self.screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
                    piece = self.checkers.game_board.board[row][col]
                    if piece != EMPTY:
                        piece_color = COLOR_RED_P if piece.lower() == RED else COLOR_WHITE_P
                        pygame.draw.circle(self.screen, piece_color, 
                            (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2), PIECE_RADIUS)
                        if piece.isupper():
                            pygame.draw.circle(self.screen, COLOR_CROWN, 
                                (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2), PIECE_RADIUS // 2)
                    # Debug: Draw ACF numbers on dark squares
                    if self.show_acf_numbers and (row, col) in COORD_TO_ACF:
                        font = pygame.font.Font(None, 14)
                        acf_text = COORD_TO_ACF[(row, col)]
                        text_surface = font.render(acf_text, True, COLOR_TEXT)
                        self.screen.blit(text_surface, (col * SQUARE_SIZE + 5, row * SQUARE_SIZE + 5))
                        logging.debug(f"Rendering ACF {acf_text} at ({row},{col})")
            # Draw info panel
            font = pygame.font.Font(None, 16)
            info_x = 590
            pygame.draw.rect(self.screen, COLOR_BG, (BOARD_SIZE, 0, INFO_WIDTH, BOARD_SIZE))
            texts = [
                f"Turn: {PLAYER_NAMES[self.checkers.game_board.turn]}",
                f"Winner: {PLAYER_NAMES[self.checkers.winner] if self.checkers.winner else 'None'}",
                f"Score: {self.checkers.evaluate_board_static(self.checkers.game_board.board, self.checkers.game_board.turn)/1500:.2f} (Red Adv.)",
                f"Pieces: Red {sum(row.count(RED) + row.count(RED_KING) for row in self.checkers.game_board.board)}/{sum(row.count(RED_KING) for row in self.checkers.game_board.board)}, White {sum(row.count(WHITE) + row.count(WHITE_KING) for row in self.checkers.game_board.board)}/{sum(row.count(WHITE_KING) for row in self.checkers.game_board.board)}",
                f"AI Depth: 6"
            ]
            for i, text in enumerate(texts):
                surface = font.render(text, True, COLOR_TEXT)
                self.screen.blit(surface, (info_x, 10 + i * 20))
            # Draw eval panel (developer mode)
            if self.developer_mode:
                font = pygame.font.Font(None, 12)
                pygame.draw.rect(self.screen, COLOR_BG, (0, BOARD_SIZE, 768, 100))
                eval_text = f"Evals: {len(self.checkers.find_best_move(6, lambda x, y, z: None)[1]) if self.checkers.game_board.turn != self.player_side else 0}"
                self.screen.blit(font.render(eval_text, True, COLOR_TEXT), (10, BOARD_SIZE + 10))
                # Placeholder for move trees
            # Draw side selection
            if self.player_side is None:
                font = pygame.font.Font(None, 24)
                button_width, button_height = 76, 48
                red_button = pygame.Rect(346, 300, button_width, button_height)
                white_button = pygame.Rect(346, 360, button_width, button_height)
                pygame.draw.rect(self.screen, COLOR_BUTTON, red_button)
                pygame.draw.rect(self.screen, COLOR_BUTTON, white_button)
                self.screen.blit(font.render("Red", True, COLOR_TEXT), (360, 310))
                self.screen.blit(font.render("White", True, COLOR_TEXT), (350, 370))
            pygame.display.flip()
        except Exception as e:
            logging.error(f"Error drawing board: {str(e)}")
            self.screen.fill(COLOR_BG)
            font = pygame.font.Font(None, 36)
            text = font.render("Error rendering board. Check log.", True, COLOR_TEXT)
            self.screen.blit(text, (50, 300))
            pygame.display.flip()

    def compute_ai_move(self):
        with self.ai_move_lock:
            self.ai_computing = True
        try:
            best_move = self.checkers.find_best_move(6, lambda x, y, z: None)
            with self.ai_move_lock:
                self.ai_move = best_move
                self.ai_computing = False
            if best_move:
                self.checkers.perform_move(*best_move)
                logging.debug(f"AI moved: {COORD_TO_ACF.get(best_move[0], '??')}-{COORD_TO_ACF.get(best_move[1], '??')}")
        except Exception as e:
            logging.error(f"AI move computation failed: {str(e)}")
            with self.ai_move_lock:
                self.ai_computing = False

    def main_loop(self):
        running = True
        while running:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN and self.player_side is None:
                        pos = pygame.mouse.get_pos()
                        red_button = pygame.Rect(346, 300, 76, 48)
                        white_button = pygame.Rect(346, 360, 76, 48)
                        if red_button.collidepoint(pos):
                            self.player_side = RED
                            logging.info("Player selected Red")
                        elif white_button.collidepoint(pos):
                            self.player_side = WHITE
                            logging.info("Player selected White")
                            if self.checkers.game_board.turn == RED:
                                threading.Thread(target=self.compute_ai_move, daemon=True).start()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE and self.checkers.game_board.turn != self.player_side and not self.ai_computing:
                            threading.Thread(target=self.compute_ai_move, daemon=True).start()
                        elif event.key == pygame.K_d:
                            self.developer_mode = not self.developer_mode
                            logging.info(f"Developer mode: {self.developer_mode}")
                        elif event.key == pygame.K_n:
                            self.show_acf_numbers = not self.show_acf_numbers
                            logging.info(f"ACF numbers display: {self.show_acf_numbers}")
                self.draw_board()
                self.clock.tick(60)
            except Exception as e:
                logging.error(f"Main loop error: {str(e)}")
                self.screen.fill(COLOR_BG)
                font = pygame.font.Font(None, 36)
                text = font.render("Error in game loop. Check log.", True, COLOR_TEXT)
                self.screen.blit(text, (50, 300))
                pygame.display.flip()
                running = False
        pygame.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Checkers game")
    parser.add_argument('--no-db', action='store_true', help="Disable endgame database loading")
    args = parser.parse_args()
    try:
        logging.info("Starting Checkers game")
        gui = CheckersGUI(use_db=not args.no_db)
        gui.main_loop()
    except Exception as e:
        logging.error(f"Program crashed: {str(e)}")
        raise
