# engine/checkers_game.py
import pygame
import logging
import threading
import queue
import copy
from .board import Board
from .constants import (SQUARE_SIZE, RED, WHITE, BOARD_RECT, SIDE_MENU_RECT, DEV_PANEL_RECT,
                      DEFAULT_AI_DEPTH, COORD_TO_ACF)
import engine.constants as constants
from game_states import Button
from engine.search import get_ai_move_analysis, _get_all_moves_for_color
from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental

logger = logging.getLogger('gui')

class CheckersGame:
    def __init__(self, screen, status_queue, args):
        self.screen = screen
        self.args = args
        self.status_queue = status_queue
        # Player and AI setup
        self.player_options = [
            {'type': 'human', 'name': 'Human', 'eval_func': None},
            {'type': 'ai', 'name': 'Engine V1', 'eval_func': evaluate_board_v1},
            {'type': 'ai', 'name': 'Engine V2', 'eval_func': evaluate_board_v2_experimental}
        ]
        self.player_red_idx, self.player_white_idx = 0, 1
        self.player_red = self.player_options[self.player_red_idx]
        self.player_white = self.player_options[self.player_white_idx]
        # AI Threading
        self.ai_thread, self.ai_move_queue = None, queue.Queue()
        self.ai_is_thinking = False
        self.ai_depth = self.args.depth if hasattr(self.args, 'depth') else DEFAULT_AI_DEPTH
        self.last_top_moves = []
        # Game State & History
        self.board_history, self.full_move_history = [Board()], []
        self.history_index = 0
        self.board = self.board_history[0]
        self.turn = self.board.turn
        self.selected_piece, self.current_move_path, self.valid_moves = None, [], []
        self.winner = None
        self.board_flipped = False
        # UI
        self.font = pygame.font.SysFont("Consolas", 18)
        self.large_font = pygame.font.SysFont("Consolas", 24)
        self.done, self.next_state = False, None
        self._create_buttons()
        self._update_game_state_from_history()

    def _create_buttons(self):
        x = SIDE_MENU_RECT.left + 15
        y_bottom = SIDE_MENU_RECT.bottom - 260
        button_width = SIDE_MENU_RECT.width - 30
        button_height = 40
        spacing = 50

        self.buttons = {
            "red_prev": Button("<", (x, 20), (20, 32), self._cycle_player_red, -1),
            "red_next": Button(">", (x + button_width - 20, 20), (20, 32), self._cycle_player_red, 1),
            "white_prev": Button("<", (x, 70), (20, 32), self._cycle_player_white, -1),
            "white_next": Button(">", (x + button_width - 20, 70), (20, 32), self._cycle_player_white, 1),
            "load_pdn": Button("Load PDN", (x, y_bottom), (button_width, button_height), self.load_pdn),
            "save_pdn": Button("Save PDN", (x, y_bottom + spacing), (button_width, button_height), self.save_pdn),
            "reset": Button("Reset", (x, y_bottom + spacing * 2), (button_width, button_height), self.reset),
            "flip_board": Button("Flip Board", (x, y_bottom + spacing * 3), (button_width, button_height), self.flip_board),
            "undo": Button("Undo", (x, y_bottom + spacing * 4), (button_width, button_height), self._navigate_history, -1),
        }

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            if SIDE_MENU_RECT.collidepoint(pos):
                for btn in self.buttons.values():
                    if btn.is_clicked(pos): btn.callback(btn.callback_args) if btn.callback_args is not None else btn.callback()
            elif BOARD_RECT.collidepoint(pos):
                current_player = self.player_red if self.turn == RED else self.player_white
                if current_player['type'] == 'human': self._handle_board_click(pos)

    def update(self):
        self._check_for_ai_move()
        current_player = self.player_red if self.turn == RED else self.player_white
        is_latest_pos = self.history_index == len(self.board_history) - 1
        if current_player['type'] == 'ai' and not self.ai_is_thinking and not self.winner and is_latest_pos:
            self._start_ai_move()

    def draw(self, screen):
        screen.fill(constants.COLOR_BG)
        self.board.draw(screen, self.board_flipped)
        self._draw_side_panel()
        self._draw_bottom_panel()
        self._draw_valid_moves()

    def reset(self): self.__init__(self.screen, self.status_queue, self.args)
    def load_pdn(self): logger.info("Load PDN button clicked.")
    def save_pdn(self): logger.info("Save PDN button clicked.")
    def flip_board(self): self.board_flipped = not self.board_flipped
    def _cycle_player_red(self, d): self.player_red_idx=(self.player_red_idx+d)%len(self.player_options); self.player_red=self.player_options[self.player_red_idx]
    def _cycle_player_white(self, d): self.player_white_idx=(self.player_white_idx+d)%len(self.player_options); self.player_white=self.player_options[self.player_white_idx]

    def _draw_side_panel(self):
        pygame.draw.rect(self.screen, constants.COLOR_PANEL_BG, SIDE_MENU_RECT)
        pygame.draw.line(self.screen, (20, 20, 20), SIDE_MENU_RECT.topleft, SIDE_MENU_RECT.bottomleft, 2)
        red_label = self.large_font.render(f"Red: {self.player_red['name']}", True, constants.COLOR_RED)
        white_label = self.large_font.render(f"White: {self.player_white['name']}", True, constants.COLOR_WHITE)
        self.screen.blit(red_label, (SIDE_MENU_RECT.centerx - red_label.get_width() / 2, 25))
        self.screen.blit(white_label, (SIDE_MENU_RECT.centerx - white_label.get_width() / 2, 75))
        history_x = SIDE_MENU_RECT.left + 15
        history_y = 120
        history_title = self.large_font.render("Move History", True, constants.COLOR_TEXT)
        self.screen.blit(history_title, (history_x, history_y))
        for i in range(0, len(self.full_move_history), 2):
            if i // 2 >= 24: break
            turn_num = i // 2 + 1
            red_move_str = self.full_move_history[i]
            text = f"{turn_num}. {red_move_str}"
            is_current = (i == self.history_index - 1)
            color = constants.DARK_YELLOW if is_current else constants.COLOR_TEXT
            move_surf = self.font.render(text, True, color)
            self.screen.blit(move_surf, (history_x, history_y + 30 + (i//2) * 20))
            if i + 1 < len(self.full_move_history):
                white_move_str = self.full_move_history[i+1]
                is_current = (i + 1 == self.history_index - 1)
                color = constants.DARK_YELLOW if is_current else constants.COLOR_TEXT
                move_surf = self.font.render(white_move_str, True, color)
                self.screen.blit(move_surf, (history_x + 150, history_y + 30 + (i//2) * 20))
        for btn in self.buttons.values():
            btn.draw(self.screen)

    def _draw_bottom_panel(self):
        pygame.draw.rect(self.screen, constants.COLOR_DEV_PANEL_BG, DEV_PANEL_RECT)
        title_surf = self.large_font.render("AI Analysis", True, constants.COLOR_TEXT)
        self.screen.blit(title_surf, (DEV_PANEL_RECT.left + 10, DEV_PANEL_RECT.top + 5))
        if self.ai_is_thinking:
            think_surf = self.large_font.render("AI is thinking...", True, constants.DARK_YELLOW)
            self.screen.blit(think_surf, (DEV_PANEL_RECT.left + 20, DEV_PANEL_RECT.top + 40))
        elif self.last_top_moves:
            for i, (move, score) in enumerate(self.last_top_moves):
                move_str = self._format_move_path(move)
                text = f"Var {i+1}: {move_str:<18} (Eval: {score:.4f})"
                surf = self.font.render(text, True, constants.DARK_YELLOW if i==0 else constants.COLOR_TEXT)
                self.screen.blit(surf, (DEV_PANEL_RECT.left + 20, DEV_PANEL_RECT.top + 40 + i * 20))

    def _handle_board_click(self, pos):
        is_latest_pos = self.history_index == len(self.board_history) - 1
        if self.ai_is_thinking or self.winner or not is_latest_pos: return
        row, col = pos[1] // SQUARE_SIZE, pos[0] // SQUARE_SIZE
        if self.board_flipped: row, col = 7 - row, 7 - col
        if self.selected_piece:
            if not self._select_move(row, col): self.selected_piece, self.current_move_path = None, []
        else:
            piece = self.board.get_piece(row, col)
            if piece and piece.color == self.turn: self.selected_piece, self.current_move_path = piece, [(row, col)]
    
    def _select_move(self, row, col):
        target = (row, col)
        for move in self.valid_moves:
            if self.current_move_path == move[:len(self.current_move_path)] and target in move:
                idx = move.index(target)
                is_jump = abs(move[idx-1][0] - target[0]) == 2
                if is_jump and idx < len(move)-1: self.current_move_path.append(target); return True
                self._apply_move_to_history(move[:idx+1]); return True
        return False

    def _draw_valid_moves(self):
        if not self.selected_piece: return
        for move in self.valid_moves:
            if move[0] == (self.selected_piece.row, self.selected_piece.col):
                for r, c in move[1:]:
                    draw_r, draw_c = (7 - r, 7 - c) if self.board_flipped else (r, c)
                    pygame.draw.circle(self.screen, constants.DARK_YELLOW, (draw_c*SQUARE_SIZE+SQUARE_SIZE//2, draw_r*SQUARE_SIZE+SQUARE_SIZE//2), 15)

    def _update_game_state_from_history(self):
        if 0 <= self.history_index < len(self.board_history):
            self.board = self.board_history[self.history_index]
            self.turn = self.board.turn
            # --- FIX: Provide the missing arguments with default None/empty values ---
            self.valid_moves = _get_all_moves_for_color(self.board, None, [])
            # --------------------------------------------------------------------
            self.selected_piece, self.current_move_path = None, []
            self.winner = self.board.winner()
            if not self.winner and not self.valid_moves and self.history_index == len(self.board_history)-1:
                self.winner = WHITE if self.turn == RED else RED
    
    def _format_move_path(self, path):
        if not path: return ""
        sep = 'x' if abs(path[0][0]-path[1][0])==2 else '-'
        return sep.join(str(COORD_TO_ACF.get(pos, "??")) for pos in path)

    def _navigate_history(self, direction):
        if self.ai_is_thinking: return
        new_index = self.history_index + direction
        if 0 <= new_index < len(self.board_history): self.history_index = new_index; self._update_game_state_from_history()
            
    def _apply_move_to_history(self, path):
        if self.history_index < len(self.board_history) - 1:
            self.board_history = self.board_history[:self.history_index + 1]
            self.full_move_history = self.full_move_history[:self.history_index]
        new_board = self.board.apply_move(path)
        self.board_history.append(new_board)
        self.full_move_history.append(self._format_move_path(path))
        self.history_index += 1
        self._update_game_state_from_history()

    def _start_ai_move(self):
        self.ai_is_thinking = True
        self.last_top_moves = []
        current_player = self.player_red if self.turn == RED else self.player_white
        self.ai_thread = threading.Thread(target=get_ai_move_analysis, args=(self.board.copy(), self.ai_depth, self.ai_move_queue, current_player['eval_func']))
        self.ai_thread.start()

    def _check_for_ai_move(self):
        if self.ai_is_thinking and not self.ai_move_queue.empty():
            self.last_top_moves = self.ai_move_queue.get()
            if self.last_top_moves:
                best_move_path = self.last_top_moves[0][0]
                self._apply_move_to_history(best_move_path)
            else: self._update_game_state_from_history()
            self.ai_is_thinking = False
