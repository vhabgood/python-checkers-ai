

import threading
import time
from queue import Queue


class Board:
    """Represents the game board state."""
    def __init__(self):
        self.state = "initial"

class CheckersGame:
    """Manages the game state, including player turns and board."""
    def __init__(self):
        self.board = Board()
        self.current_player = "red"  # Could be "red" or "black"
        self.ai_player = "black"

    def make_move(self, move):
        """Simulates making a move on the board."""
        print(f"Game: Making move {move}")
        if self.current_player == "red":
            self.current_player = "black"
        else:
            self.current_player = "red"

    def get_valid_moves(self):
        """Returns a list of dummy valid moves for demonstration."""
        return [("A1", "B2"), ("C3", "D4")]

# --- Assuming the CheckersAI class is imported from engine/search.py ---
# from engine.search import CheckersAI
class CheckersAI:
    """
    A class to handle AI move calculation, designed to be run in a thread.
    (This is a placeholder. You'll use the one from engine/search.py)
    """
    def __init__(self, game_state):
        self.game_state = game_state
        self.interrupt_flag = threading.Event()
        self.best_move_found = None
        
    def find_best_move(self, depth_limit=10):
        self.interrupt_flag.clear()
        self.best_move_found = None
        for current_depth in range(1, depth_limit + 1):
            if self.interrupt_flag.is_set():
                return self.best_move_found
            time.sleep(1) 
            valid_moves = self.game_state.get_valid_moves()
            if valid_moves:
                self.best_move_found = valid_moves[0]
        return self.best_move_found

# --- GUI Controller Class (likely in main.py) ---
class CheckersGUIController:
    """
    Manages the game state and interacts with the GUI.
    This class would have methods called by your GUI buttons.
    """
    def __init__(self):
        self.game = CheckersGame()
        self.ai = CheckersAI(self.game) # Make sure to instantiate your actual AI class
        
        self.ai_is_thinking = False
        self.ai_thread = None
        # Use a Queue for thread-safe communication back to the GUI.
        self.message_queue = Queue()

    def update_gui(self):
        """
        This method would be called periodically by the GUI's main loop
        to check for new messages from the AI thread.
        
        For example, in a Tkinter app you would call this with root.after(100, self.update_gui).
        In Pygame, you would call this in your main game loop.
        """
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                print(f"GUI received message: {message}")
                if message["type"] == "ai_move":
                    self.game.make_move(message["move"])
                    # You would also update the GUI board here to reflect the move.
                    self.ai_is_thinking = False
                    
                    # Update a GUI button's state, e.g., enable it again.
                    # self.gui_buttons["Force AI"].config(state="normal")
        except Exception as e:
            print(f"Error updating GUI: {e}")

    def run_ai_in_thread(self):
        """
        Wrapper function to run the AI search and send the result back
        to the GUI thread via the queue.
        """
        print("Starting AI calculation in a new thread...")
        best_move = self.ai.find_best_move()
        self.message_queue.put({"type": "ai_move", "move": best_move})
        
    def force_ai_move(self):
        """
        This function handles both scenarios for the Force AI button.
        This is the method you would link to your button's 'command' attribute.
        """
        # Scenario 1: AI is currently thinking (search thread is active)
        if self.ai_is_thinking and self.ai_thread and self.ai_thread.is_alive():
            print("Force AI button pressed: Interrupting AI search.")
            # Set the interrupt flag to tell the AI to stop.
            self.ai.interrupt_flag.set()
        # Scenario 2: AI is not thinking, start a new turn for it
        else:
            print("Force AI button pressed: Starting AI turn.")
            # Change the current player to the AI.
            self.game.current_player = self.ai.ai_player
            self.ai_is_thinking = True
            # Start the AI calculation in a new, non-blocking thread.
            self.ai_thread = threading.Thread(target=self.run_ai_in_thread)
            self.ai_thread.start()
            # Disable the button to prevent multiple presses while the AI is busy.
            # self.gui_buttons["Force AI"].config(state="disabled")

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
            # Draw board
            for row in range(8):
                for col in range(8):
                    color = COLOR_LIGHT_SQUARE if (row + col) % 2 == 0 else COLOR_DARK_SQUARE
                    pygame.draw.rect(self.screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
                    piece = self.checkers.game_board.board[row][col]
                    if piece != EMPTY:
                        piece_color = COLOR_RED_P if piece.lower() == RED else COLOR_WHITE_P
                        pygame.draw.circle(self.screen, piece_color, 
                            (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2), PIECE_RADIUS)
                        if piece.isupper():
                            pygame.draw.circle(self.screen, COLOR_CROWN, 
                                (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2), PIECE_RADIUS // 2)
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


# --- Main execution example (for testing) ---
if __name__ == "__main__":

    controller = CheckersGUIController()
    
    print("Simulating game start...")
    print("\nUser presses 'Force AI' button for the first time.")
    controller.force_ai_move()
    
    time.sleep(2.5)
    
    print("\nUser presses 'Force AI' button again while AI is busy.")
    controller.force_ai_move()
    
    controller.ai_thread.join()
    controller.update_gui()


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

