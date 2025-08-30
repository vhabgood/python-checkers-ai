# engine/checkers_game.py
import pygame
import logging
import threading
import queue
import copy
from .board import Board
from .constants import SQUARE_SIZE, RED, WHITE, BOARD_SIZE, ROWS, COLS, DEFAULT_AI_DEPTH
import engine.constants as constants
from game_states import Button
# --- THIS LINE IS THE FIX ---
from engine.search import get_ai_move_analysis, get_all_move_sequences
from engine.evaluation import evaluate_board

logger = logging.getLogger('gui')

class CheckersGame:
    def __init__(self, screen, player_color_str, status_queue, args):
        logger.critical("--- NEW CHECKERS GAME INSTANCE CREATED ---")
        self.screen = screen
        self.args = args
        self.board = Board()
        self.player_color = WHITE if player_color_str == 'white' else RED
        self.ai_color = RED if self.player_color == WHITE else WHITE
        self.turn = self.board.turn
        self.selected_piece = None
        self.valid_moves = {}
        self.done = False
        self.next_state = None
        self.show_board_numbers = False
        self.dev_mode = False
        self.board_flipped = False
        self.history = []
        self.move_history = []
        self.large_font = pygame.font.SysFont(None, 22)
        self.font = pygame.font.SysFont(None, 18)
        self.buttons = [
            Button("Toggle Dev Mode", (BOARD_SIZE + 10, self.screen.get_height() - 40), (180, 30), self.toggle_dev_mode),
            Button("Flip Board", (BOARD_SIZE + 10, self.screen.get_height() - 80), (180, 30), self.toggle_board_flip),
            Button("Toggle Numbers", (BOARD_SIZE + 10, self.screen.get_height() - 120), (180, 30), self.toggle_board_numbers)
        ]
        self.ai_is_thinking = False
        self.ai_move_queue = queue.Queue()
        self.ai_top_moves = []

    def _coord_to_acf(self, coord):
        return str(constants.COORD_TO_ACF.get(coord, "??"))

    def _format_move_path(self, path):
        if not path:
            return ""
        return "-".join(self._coord_to_acf(pos) for pos in path)

    def start_ai_turn(self, force_color=None):
        self.ai_is_thinking = True
        self.ai_top_moves = []
        color_to_move = force_color if force_color else self.turn
        threading.Thread(target=self.run_ai_calculation, args=(color_to_move,)).start()

    def run_ai_calculation(self, color_to_move):
        logger.info(f"AI_THREAD: Starting calculation for {'White' if color_to_move == WHITE else 'Red'} at depth {DEFAULT_AI_DEPTH}.")
        board_copy = copy.deepcopy(self.board)
        best_move_path, top_moves = get_ai_move_analysis(board_copy, DEFAULT_AI_DEPTH, color_to_move, evaluate_board)
        self.ai_top_moves = top_moves
        self.ai_move_queue.put(best_move_path)
        self.ai_is_thinking = False
        logger.info("AI_THREAD: Calculation finished. Move placed in queue.")

    def _change_turn(self):
        self.valid_moves = {}
        self.selected_piece = None
        if self.turn == RED:
            self.turn = WHITE
        else:
            self.turn = RED
        self.board.turn = self.turn
        self.board.hash ^= self.board.zobrist_table['turn']

    def _apply_move_sequence(self, path):
        if not path:
            logger.error("APPLY_MOVE: Received an empty or invalid path.")
            return

        start_pos = path[0]
        piece = self.board.get_piece(start_pos[0], start_pos[1])
        
        if piece == 0:
            logger.error(
                f"CRITICAL ERROR: AI or player tried to move from an empty square at {start_pos}. "
                f"Move path: {self._format_move_path(path)}. Aborting move."
            )
            return
        
        end_pos = path[-1]
        is_jump = any(abs(path[i][0] - path[i+1][0]) == 2 for i in range(len(path)-1))
        
        if is_jump:
            captured_pieces = []
            for i in range(len(path)-1):
                p_start, p_end = path[i], path[i+1]
                mid_row = (p_start[0] + p_end[0]) // 2
                mid_col = (p_start[1] + p_end[1]) // 2
                captured = self.board.get_piece(mid_row, mid_col)
                if captured:
                    captured_pieces.append(captured)
            self.board._remove(captured_pieces)
        
        self.board.move(piece, end_pos[0], end_pos[1])
        self.move_history.append(self._format_move_path(path))
        self._change_turn()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked_button = False
            for button in self.buttons:
                if button.is_clicked(event.pos):
                    button.callback()
                    clicked_button = True
                    break
            if not clicked_button:
                self._handle_click(event.pos)

    def update(self):
        if self.done:
            return
        if self.turn == self.ai_color and not self.ai_is_thinking:
            self.start_ai_turn()
        try:
            best_move_path = self.ai_move_queue.get_nowait()
            if best_move_path:
                logger.info(f"UPDATE: Move received from AI queue: {self._format_move_path(best_move_path)}. Applying.")
                self._apply_move_sequence(best_move_path)
            elif best_move_path is None:
                logger.warning("AI calculation returned None. Forfeiting turn.")
                self._change_turn()
            else:
                logger.warning("AI returned an empty list, meaning it is blocked. Forfeiting turn.")
                self._change_turn()
        except queue.Empty:
            pass

    def draw(self):
        self.screen.fill((40, 40, 40))
        self.board.draw(self.screen, self.font, self.show_board_numbers, self.board_flipped)
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - BOARD_SIZE
        panel_height = self.screen.get_height()
        panel_rect = pygame.Rect(panel_x, 0, panel_width, panel_height)
        pygame.draw.rect(self.screen, (20, 20, 20), panel_rect)
        pygame.draw.line(self.screen, (100, 100, 100), (panel_x, 0), (panel_x, panel_height), 2)
        for button in self.buttons:
            button.draw(self.screen)
        turn_text_str = "White's Turn" if self.turn == WHITE else "Red's Turn"
        turn_surface = self.large_font.render(turn_text_str, True, (255, 255, 255))
        self.screen.blit(turn_surface, (BOARD_SIZE + 10, 15))
        if self.dev_mode:
            self.draw_dev_panel()

    def draw_dev_panel(self):
        if not self.ai_top_moves:
            return
        panel_x = BOARD_SIZE
        y_offset = 50
        title_text = self.large_font.render("AI Analysis:", True, (200, 200, 200))
        self.screen.blit(title_text, (panel_x + 10, y_offset))
        y_offset += 30
        ai_turn_color = (180, 220, 180)
        opponent_turn_color = (220, 180, 180)
        for i, (score, sequence) in enumerate(self.ai_top_moves):
            if not sequence: continue
            move_text = f"{i+1}. "
            for move_segment in sequence:
                segment_str = ""
                for j in range(len(move_segment) - 1):
                    start_acf = self._coord_to_acf(move_segment[j])
                    end_acf = self._coord_to_acf(move_segment[j+1])
                    separator = 'x' if abs(move_segment[j][0] - move_segment[j+1][0]) == 2 else '-'
                    segment_str += f"{start_acf}{separator}{end_acf} "
                move_text += f"({segment_str.strip()}) "
            score_text = f"Score: {score:.2f}"
            full_text = f"{move_text} {score_text}"
            text_surface = self.font.render(full_text, True, (220, 220, 220))
            self.screen.blit(text_surface, (panel_x + 15, y_offset))
            y_offset += 25
            if i == 0:
                is_ai_turn = True
                for move_segment in sequence:
                    line_color = ai_turn_color if is_ai_turn else opponent_turn_color
                    for j in range(len(move_segment) - 1):
                        start_coord, end_coord = move_segment[j], move_segment[j+1]
                        start_pixel = (start_coord[1] * SQUARE_SIZE + SQUARE_SIZE // 2, start_coord[0] * SQUARE_SIZE + SQUARE_SIZE // 2)
                        end_pixel = (end_coord[1] * SQUARE_SIZE + SQUARE_SIZE // 2, end_coord[0] * SQUARE_SIZE + SQUARE_SIZE // 2)
                        pygame.draw.line(self.screen, line_color, start_pixel, end_pixel, 3)
                    is_ai_turn = not is_ai_turn
    
    def _handle_click(self, pos):
        if self.turn != self.player_color:
            return
        col = pos[0] // SQUARE_SIZE
        row = pos[1] // SQUARE_SIZE
        if self.board_flipped:
            row = ROWS - 1 - row
            col = COLS - 1 - col
        if self.selected_piece:
            if self._attempt_move((row, col)):
                return
        self._select_piece(row, col)

    def _select_piece(self, row, col):
        piece = self.board.get_piece(row, col)
        if piece != 0 and piece.color == self.turn:
            self.selected_piece = piece
            self.valid_moves = self.board.get_all_valid_moves(self.turn)
            return True
        self.selected_piece = None
        self.valid_moves = {}
        return False

    def _attempt_move(self, move_end_pos):
        start_pos = (self.selected_piece.row, self.selected_piece.col)
        all_possible_moves = list(get_all_move_sequences(self.board, self.turn))
        found_path = None
        for path in all_possible_moves:
            if path[0] == start_pos and path[-1] == move_end_pos:
                found_path = path
                break
        if found_path:
            self._apply_move_sequence(found_path)
            return True
        self.selected_piece = None
        self.valid_moves = {}
        return False

    def toggle_dev_mode(self):
        self.dev_mode = not self.dev_mode
        logger.info(f"Developer mode toggled {'ON' if self.dev_mode else 'OFF'}.")

    def toggle_board_flip(self):
        self.board_flipped = not self.board_flipped
        logger.info(f"Board flip toggled {'ON' if self.board_flipped else 'OFF'}.")

    def toggle_board_numbers(self):
        self.show_board_numbers = not self.show_board_numbers
        logger.info(f"Board numbers toggled {'ON' if self.show_board_numbers else 'OFF'}.")
