# engine/checkers_game.py
import pygame
import logging
import threading
import queue
import copy
import time
from .board import Board
from .constants import SQUARE_SIZE, RED, WHITE, BOARD_SIZE, ROWS, COLS, DEFAULT_AI_DEPTH
import engine.constants as constants
from game_states import Button
from engine.search import get_ai_move_analysis, get_all_move_sequences
from engine.evaluation import evaluate_board

logger = logging.getLogger('gui')

class CheckersGame:
    def __init__(self, screen, player_color_str, status_queue, args):
        self.screen = screen
        self.args = args
        
        # --- NEW: Load databases if not disabled by the --no-db flag ---
        if not self.args.no_db:
            databases = Board.load_databases(status_queue)
        else:
            databases = {}
            status_queue.put("Skipping database loading.")

        self.board = Board(**databases) # Pass loaded databases to the Board
        
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
        self.move_history = []
        self.large_font = pygame.font.SysFont(None, 24)
        self.font = pygame.font.SysFont(None, 20)
        self.dev_font = pygame.font.SysFont(None, 18)
        
        self.ai_depth = DEFAULT_AI_DEPTH

        button_width = 180
        panel_x = BOARD_SIZE + 10
        button_y_start = self.screen.get_height() - 40
        self.buttons = [
            Button("Dev Mode", (panel_x, button_y_start), (button_width, 30), self.toggle_dev_mode),
            Button("Board Numbers", (panel_x, button_y_start - 40), (button_width, 30), self.toggle_board_numbers),
            Button("Export to PDN", (panel_x, button_y_start - 80), (button_width, 30), self.export_to_pdn),
            Button("Force AI Move", (panel_x, button_y_start - 120), (button_width, 30), self.force_ai_move),
            Button("Reset", (panel_x, button_y_start - 160), (button_width, 30), self.reset_game),
            Button("Undo", (panel_x, button_y_start - 200), (button_width, 30), self.undo_move),
            Button("-", (panel_x + 100, button_y_start - 235), (30, 30), self.decrease_ai_depth),
            Button("+", (panel_x + 140, button_y_start - 235), (30, 30), self.increase_ai_depth)
        ]

        self.ai_is_thinking = False
        self.ai_move_queue = queue.Queue()
        self.ai_top_moves = []
        self.ai_best_move_for_execution = None
        self.force_ai_flag = False
        self.feedback_message = ""
        self.feedback_timer = 0
        self.feedback_color = (180, 220, 180)

    def _coord_to_acf(self, coord):
        return str(constants.COORD_TO_ACF.get(coord, "??"))

    def _format_move_path(self, path):
        if not path or len(path) < 2: return ""
        separator = 'x' if abs(path[0][0] - path[1][0]) == 2 else '-'
        if separator == 'x':
            return 'x'.join(self._coord_to_acf(pos) for pos in path)
        return separator.join(self._coord_to_acf(pos) for pos in path)

    def start_ai_turn(self, force_color=None):
        self.ai_is_thinking = True
        self.ai_top_moves = []
        self.ai_best_move_for_execution = None
        color_to_move = force_color if force_color else self.turn
        threading.Thread(target=self.run_ai_calculation, args=(color_to_move,)).start()

    def run_ai_calculation(self, color_to_move):
        try:
            logger.info(f"AI_THREAD: Starting calculation for {'White' if color_to_move == WHITE else 'Red'} at depth {self.ai_depth}.")
            board_copy = copy.deepcopy(self.board)
            best_move, top_moves = get_ai_move_analysis(board_copy, self.ai_depth, color_to_move, evaluate_board)
            self.ai_move_queue.put({'best': best_move, 'top': top_moves})
            logger.info("AI_THREAD: Calculation finished normally. Move placed in queue.")
        except Exception as e:
            logger.error(f"AI_THREAD: CRITICAL ERROR during calculation: {e}", exc_info=True)
            self.ai_move_queue.put({'best': None, 'top': []})

    def _change_turn(self):
        self.valid_moves = {}
        self.selected_piece = None
        self.turn = WHITE if self.turn == RED else RED
        self.board.turn = self.turn

    def _apply_move_sequence(self, path):
        if not path: return
        self.move_history.append(self._format_move_path(path))
        start_pos, end_pos = path[0], path[-1]
        piece = self.board.get_piece(start_pos[0], start_pos[1])
        if piece == 0: return

        is_jump = any(abs(path[i][0] - path[i+1][0]) == 2 for i in range(len(path)-1))
        if is_jump:
            captured_pieces = []
            for i in range(len(path)-1):
                p_start, p_end = path[i], path[i+1]
                mid_row, mid_col = (p_start[0] + p_end[0]) // 2, (p_start[1] + p_end[1]) // 2
                captured = self.board.get_piece(mid_row, mid_col)
                if captured: captured_pieces.append(captured)
            self.board._remove(captured_pieces)
        
        self.board.move(piece, end_pos[0], end_pos[1])
        self._change_turn()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked_button = False
            for button in self.buttons:
                if button.is_clicked(event.pos):
                    button.callback()
                    clicked_button = True
                    break
            if not clicked_button: self._handle_click(event.pos)

    def update(self):
        if self.done: return
        
        if self.feedback_timer > 0:
            self.feedback_timer -= 1
        else:
            self.feedback_message = ""

        try:
            ai_results = self.ai_move_queue.get_nowait()
            self.ai_top_moves = ai_results['top']
            self.ai_best_move_for_execution = ai_results['best']
            self.ai_is_thinking = False
        except queue.Empty:
            pass

        if (self.turn == self.ai_color or self.force_ai_flag) and not self.ai_is_thinking and self.ai_best_move_for_execution:
            self._apply_move_sequence(self.ai_best_move_for_execution)
            self.ai_best_move_for_execution = None
            self.force_ai_flag = False

        elif self.turn == self.ai_color and not self.ai_is_thinking and not self.ai_best_move_for_execution:
            self.start_ai_turn()

    def draw(self):
        self.screen.fill((40, 40, 40))
        moves_to_highlight = self.valid_moves.get((self.selected_piece.row, self.selected_piece.col)) if self.selected_piece else {}
        self.board.draw(self.screen, self.font, self.show_board_numbers, self.board_flipped, moves_to_highlight)
        self.draw_side_panel()
        if self.dev_mode:
            self.draw_dev_panel()

    def draw_side_panel(self):
        panel_x = BOARD_SIZE
        panel_width = self.screen.get_width() - panel_x
        panel_height = self.screen.get_height()
        panel_rect = pygame.Rect(panel_x, 0, panel_width, panel_height)
        pygame.draw.rect(self.screen, (20, 20, 20), panel_rect)
        pygame.draw.line(self.screen, (100, 100, 100), (panel_x, 0), (panel_x, panel_height), 2)
        
        for button in self.buttons:
            button.draw(self.screen)
            
        turn_text_str = "White's Turn" if self.turn == WHITE else "Red's Turn"
        turn_surface = self.large_font.render(turn_text_str, True, (255, 255, 255))
        self.screen.blit(turn_surface, (panel_x + 10, 15))

        y_pos_after_turn = 50
        if self.feedback_timer > 0 and self.feedback_message:
            feedback_surface = self.font.render(self.feedback_message, True, self.feedback_color)
            self.screen.blit(feedback_surface, (panel_x + 10, y_pos_after_turn))
        elif self.ai_is_thinking:
            thinking_text = self.large_font.render("AI is thinking...", True, (255, 255, 0))
            self.screen.blit(thinking_text, (panel_x + 10, y_pos_after_turn))
        
        history_y_start = 80
        history_title = self.large_font.render("Move History:", True, (200, 200, 200))
        self.screen.blit(history_title, (panel_x + 10, history_y_start))
        y_offset = history_y_start + 30
        
        button_boundary = self.buttons[-3].rect.top 

        for i in range(0, len(self.move_history), 2):
            move_num = i // 2 + 1
            white_move = self.move_history[i]
            red_move = self.move_history[i+1] if (i+1) < len(self.move_history) else ""
            line = f"{move_num}. {white_move:<10} {red_move:<10}"
            move_surface = self.font.render(line, True, (220, 220, 220))
            self.screen.blit(move_surface, (panel_x + 15, y_offset))
            y_offset += 20
            if y_offset > button_boundary - 20: break
            
        depth_button = self.buttons[-2]
        depth_text_surface = self.large_font.render(f"AI Depth: {self.ai_depth}", True, (200, 200, 200))
        text_y = depth_button.rect.centery - (depth_text_surface.get_height() // 2)
        self.screen.blit(depth_text_surface, (panel_x + 10, text_y))

    def draw_dev_panel(self):
        panel_height = self.screen.get_height() - BOARD_SIZE
        if panel_height <= 0: return
        panel_y = BOARD_SIZE
        panel_rect = pygame.Rect(0, panel_y, BOARD_SIZE, panel_height)
        pygame.draw.rect(self.screen, (30, 30, 30), panel_rect)
        pygame.draw.line(self.screen, (100, 100, 100), (0, panel_y), (BOARD_SIZE, panel_y), 2)

        if not self.ai_top_moves: return

        y_offset = panel_y + 5
        title_text = self.large_font.render("AI Analysis:", True, (200, 200, 200))
        self.screen.blit(title_text, (10, y_offset))
        y_offset += 25

        line_height = 18
        for i, (score, sequence) in enumerate(self.ai_top_moves):
            if not sequence: continue
            move_text = f"{i+1}. "
            for move_segment in sequence:
                segment_str = self._format_move_path(move_segment)
                move_text += f"({segment_str}) "
            score_text = f"Score: {score:.2f}"
            full_text = f"{move_text} {score_text}"
            text_surface = self.dev_font.render(full_text, True, (220, 220, 220))
            self.screen.blit(text_surface, (15, y_offset))
            y_offset += line_height
            if y_offset > self.screen.get_height() - (line_height / 2): break

            if i == 0:
                max_alpha, current_alpha = 100, 100
                alpha_step = max(max_alpha // (len(sequence) * 2), 1)
                for move_segment in sequence:
                    highlight_color = (255, 255, 0, current_alpha)
                    dest_square_coord = move_segment[-1]
                    highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    highlight_surface.fill(highlight_color)
                    self.screen.blit(highlight_surface, (dest_square_coord[1] * SQUARE_SIZE, dest_square_coord[0] * SQUARE_SIZE))
                    current_alpha = max(0, current_alpha - alpha_step * 4)

    def increase_ai_depth(self):
        self.ai_depth = min(9, self.ai_depth + 1)
        logger.info(f"AI depth increased to {self.ai_depth}")

    def decrease_ai_depth(self):
        self.ai_depth = max(5, self.ai_depth - 1)
        logger.info(f"AI depth decreased to {self.ai_depth}")

    def toggle_dev_mode(self): self.dev_mode = not self.dev_mode
    def toggle_board_numbers(self): self.show_board_numbers = not self.show_board_numbers
    def toggle_board_flip(self): self.board_flipped = not self.board_flipped
    
    def force_ai_move(self):
        if not self.ai_is_thinking:
            self.force_ai_flag = True
            self.start_ai_turn(self.turn)

    def reset_game(self):
        self.board = Board()
        self.turn = self.board.turn
        self.move_history = []
        self.ai_top_moves = []
        self.selected_piece = None

    def undo_move(self):
        if len(self.board.history) > 1:
            self.board.history.pop()
            last_board_state = self.board.history[-1]
            self.board.board = copy.deepcopy(last_board_state)
            self.board.recalculate_pieces()
            if self.move_history: self.move_history.pop()
            self._change_turn()
            self.ai_is_thinking = False
            self.ai_top_moves = []
            self.ai_best_move_for_execution = None

    def export_to_pdn(self):
        try:
            filename = f"game_{time.strftime('%Y%m%d_%H%M%S')}.pdn"
            with open(filename, "w") as f:
                f.write('[Event "Checkers Game"]\n[Site "Local"]\n')
                f.write(f'[Date "{time.strftime("%Y.%m.%d")}"]\n[Round "-"]\n')
                f.write(f'[White "{"Player" if self.player_color == WHITE else "AI"}"]\n')
                f.write(f'[Black "{"Player" if self.player_color == RED else "AI"}"]\n')
                f.write('[Result "*"]\n\n')
                move_str = ""
                for i, move in enumerate(self.move_history):
                    if i % 2 == 0: move_str += f"{i//2 + 1}. {move} "
                    else: move_str += f"{move} "
                f.write(move_str.strip() + " *\n")
            self.feedback_message = f"Saved to {filename}"
            self.feedback_timer = 180
            self.feedback_color = (180, 220, 180)
        except Exception as e:
            self.feedback_message = f"Error saving PDN!"
            self.feedback_timer = 180
            self.feedback_color = (220, 180, 180)

    def _handle_click(self, pos):
        # --- FIX: Boundary check to prevent crash on side-panel clicks ---
        if pos[0] >= BOARD_SIZE or pos[1] >= BOARD_SIZE:
            return

        if self.turn != self.player_color or self.ai_is_thinking: return
        
        col = pos[0] // SQUARE_SIZE
        row = pos[1] // SQUARE_SIZE

        if self.board_flipped:
            row, col = ROWS - 1 - row, COLS - 1 - col
        
        if self.selected_piece:
            if self._attempt_move((row, col)): return
        
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
