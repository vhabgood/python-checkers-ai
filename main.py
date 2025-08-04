# main.py
import pygame
import os
import copy
import pickle
import threading
from datetime import datetime
import random
from engine.constants import *
from engine.checkers_game import Checkers

# --- PART 2: THE PYGAME GUI (DEFINITIVE, CORRECTED VERSION) ---

class CheckersGUI:
    MAX_DEV_HIGHLIGHTS = 3
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT)); pygame.display.set_caption('American Checkers')
        self.font_small, self.font_medium, self.font_large = pygame.font.SysFont('Arial', 18), pygame.font.SysFont('Arial', 24, bold=True), pygame.font.SysFont('Arial', 40, bold=True)
        self.game = None
        self.loading_state = 'loading'
        self.loading_status_message = "Initializing..."
        self.loading_lock = threading.Lock()
        threading.Thread(target=self._load_resources_worker, daemon=True).start()
        
    def _load_resources_worker(self):
        def update_status(msg):
            with self.loading_lock:
                self.loading_status_message = msg
        
        Checkers.load_all_resources(update_status)
        self.reset_game_state(first_load=True)
        self.loading_state = 'side_selection'

    def reset_game_state(self, first_load=False):
        self.game = Checkers(load_resources=False)
        self.game_state_history = []
        self.selected_piece, self.valid_moves, self.board_is_flipped, self.last_move = None, {}, False, None
        self.ai_depth, self.is_ai_thinking, self.ai_move_result, self.ai_analysis_complete_paused = 5, False, None, False
        self.ai_all_evaluated_moves, self.ai_analysis_lock, self.ai_eval_count, self.developer_mode, self.ai_current_path, self.eval_scroll_offset = [], threading.Lock(), 0, False, [], 0
        self.game_mode = None
        self.human_player_color = None
        self.ai_is_paused = False
        self.play_red_rect = pygame.Rect(WIDTH//2 - 140, HEIGHT//2 - 25, 120, 50)
        self.play_white_rect = pygame.Rect(WIDTH//2 + 20, HEIGHT//2 - 25, 120, 50)

        if first_load:
            btn_h, start_x, y_pos, num_btns, btn_w = 40, 10, BOARD_SIZE + 5, 7, (WIDTH - 20) // 7
            self.buttons = { "Force Move": pygame.Rect(start_x, y_pos, btn_w, btn_h), "Dev Mode": pygame.Rect(start_x+btn_w, y_pos, btn_w, btn_h), "Reset": pygame.Rect(start_x+2*btn_w, y_pos, btn_w, btn_h), "Undo": pygame.Rect(start_x+3*btn_w, y_pos, btn_w, btn_h), "Save": pygame.Rect(start_x+4*btn_w, y_pos, btn_w, btn_h), "Load": pygame.Rect(start_x+5*btn_w, y_pos, btn_w, btn_h), "Export": pygame.Rect(start_x+6*btn_w, y_pos, btn_w, btn_h) }
            self.depth_minus_rect, self.depth_plus_rect = pygame.Rect(BOARD_SIZE+270, 195, 30, 30), pygame.Rect(BOARD_SIZE+320, 195, 30, 30)
            self.eval_scroll_up_rect, self.eval_scroll_down_rect = pygame.Rect(BOARD_SIZE+INFO_WIDTH-40, 315, 30, 25), pygame.Rect(BOARD_SIZE+INFO_WIDTH-40, BOARD_SIZE-75, 30, 25)

    def _update_ai_progress(self, all_moves, eval_count, current_path):
        with self.ai_analysis_lock:
            if all_moves: self.ai_all_evaluated_moves = all_moves
            if eval_count: self.ai_eval_count = eval_count
            if current_path: self.ai_current_path = current_path
    def _ai_worker(self): self.ai_move_result = self.game.find_best_move(self.ai_depth, self._update_ai_progress)
    def _start_ai_move(self):
        if self.is_ai_thinking or self.ai_analysis_complete_paused or self.game.winner: return
        self.is_ai_thinking, self.ai_move_result, self.eval_scroll_offset = True, "THINKING", 0
        with self.ai_analysis_lock: self.ai_all_evaluated_moves, self.ai_eval_count, self.ai_current_path = [], 0, []
        threading.Thread(target=self._ai_worker, daemon=True).start()
    def _get_display_coords(self, r, c): return (7-r, 7-c) if self.board_is_flipped else (r, c)
    def _get_logical_coords_from_mouse(self, pos):
        x, y = pos
        if x > BOARD_SIZE or y > BOARD_SIZE: return None, None
        r, c = y // SQUARE_SIZE, x // SQUARE_SIZE
        return (7-r, 7-c) if self.board_is_flipped else (r, c)
    def _handle_move(self, start, end):
        self.ai_is_paused = False
        if not self.game.forced_jumps: self.game_state_history.append(copy.deepcopy(self.game))
        self.game.perform_move(start, end)
        self.last_move = (start, end)
        self.selected_piece = self.game.forced_jumps[0][0] if self.game.forced_jumps else None
        self._update_valid_moves()
    def _sync_gui_to_game_state(self):
        self.game.winner = self.game.check_win_condition()
        self.selected_piece, self.last_move, self.is_ai_thinking, self.ai_analysis_complete_paused = None, None, False, False
        with self.ai_analysis_lock: self.ai_all_evaluated_moves, self.ai_eval_count = [], 0
        self._update_valid_moves()
    def _update_valid_moves(self):
        self.valid_moves = {}
        if not self.game: return
        possible = self.game.forced_jumps or (self.game.get_all_possible_moves(self.game.turn) if self.selected_piece else [])
        if self.selected_piece: possible = [m for m in possible if m[0] == self.selected_piece]
        for start, end in possible: self.valid_moves[end] = start
    def main_loop(self):
        running, clock = True, pygame.time.Clock()
        while running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False; continue
                
                if self.loading_state != 'done':
                    if self.loading_state == 'side_selection' and event.type == pygame.MOUSEBUTTONDOWN:
                        if self.play_red_rect.collidepoint(event.pos): self.human_player_color, self.game_mode, self.loading_state = RED, "P_VS_C", "done"
                        elif self.play_white_rect.collidepoint(event.pos): self.human_player_color, self.game_mode, self.loading_state = WHITE, "P_VS_C", "done"
                    continue

                if event.type == pygame.MOUSEWHEEL and self.developer_mode and (self.is_ai_thinking or self.ai_analysis_complete_paused) and mouse_pos[0] > BOARD_SIZE:
                    self.eval_scroll_offset = max(0, self.eval_scroll_offset - event.y)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and self.ai_analysis_complete_paused:
                    if self.ai_move_result: self._handle_move(self.ai_move_result[0], self.ai_move_result[1])
                    self.ai_analysis_complete_paused, self.ai_move_result = False, None
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.buttons["Force Move"].collidepoint(event.pos):
                        if self.is_ai_thinking:
                            with self.ai_analysis_lock:
                                if self.ai_all_evaluated_moves: self.ai_move_result = self.ai_all_evaluated_moves[0]['move']
                        else: self._start_ai_move()
                        continue

                    if self.is_ai_thinking or self.ai_analysis_complete_paused:
                        if self.eval_scroll_up_rect.collidepoint(event.pos): self.eval_scroll_offset=max(0,self.eval_scroll_offset-1)
                        elif self.eval_scroll_down_rect.collidepoint(event.pos): self.eval_scroll_offset+=1
                        continue
                    
                    if self.buttons["Dev Mode"].collidepoint(event.pos): self.developer_mode = not self.developer_mode
                    elif self.buttons["Reset"].collidepoint(event.pos): self.reset_game_state(); self.loading_state = 'side_selection'
                    elif self.buttons["Undo"].collidepoint(event.pos) and self.game_state_history:
                        self.game = self.game_state_history.pop()
                        self._sync_gui_to_game_state()
                        self.ai_is_paused = True
                    elif self.buttons["Save"].collidepoint(event.pos):
                        with open("savegame.dat", "wb") as f: pickle.dump(self.game, f)
                    elif self.buttons["Load"].collidepoint(event.pos) and os.path.exists("savegame.dat"):
                        with open("savegame.dat", "rb") as f: self.game = pickle.load(f)
                        self.game_state_history = []; self._sync_gui_to_game_state()
                    elif self.buttons["Export"].collidepoint(event.pos): self.game.export_to_pdn()
                    elif self.depth_minus_rect.collidepoint(event.pos): self.ai_depth = max(1, self.ai_depth - 1)
                    elif self.depth_plus_rect.collidepoint(event.pos): self.ai_depth = min(12, self.ai_depth + 1)
                    elif not self.game.winner:
                        row, col = self._get_logical_coords_from_mouse(event.pos)
                        if self.game.turn == self.human_player_color and row is not None:
                            if (row, col) in self.valid_moves: self._handle_move(self.valid_moves[(row, col)], (row, col))
                            elif not self.game.forced_jumps and self.game.board[row][col].lower() == self.game.turn:
                                self.selected_piece = (row, col); self._update_valid_moves()
                            else: self.selected_piece = None; self._update_valid_moves()
            
            if self.loading_state == 'loading': self.draw_loading_screen()
            elif self.loading_state == 'side_selection': self.draw_side_selection_screen(mouse_pos)
            elif self.game_mode:
                if not self.game.winner: self.game.winner = self.game.check_win_condition()
                if self.is_ai_thinking and self.ai_move_result != "THINKING":
                    self.is_ai_thinking = False
                    if self.developer_mode or self.game.turn != self.human_player_color: self.ai_analysis_complete_paused = True
                    else:
                        if self.ai_move_result: self._handle_move(self.ai_move_result[0], self.ai_move_result[1])
                        self.ai_move_result = None
                
                all_moves = self.game.get_all_possible_moves(self.game.turn) if self.game else []
                is_ai_turn = self.game and self.game.turn != self.human_player_color
                if is_ai_turn and all_moves and not (self.is_ai_thinking or self.ai_analysis_complete_paused or self.game.winner or self.ai_is_paused):
                    if len(all_moves) == 1:
                        self._handle_move(all_moves[0][0], all_moves[0][1])
                    else: self._start_ai_move()
                self._draw_game_screen(mouse_pos)
            
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()

    def draw_loading_screen(self):
        self.screen.fill(COLOR_BG)
        title_surf = self.font_large.render("Loading Resources...", True, COLOR_LIGHT)
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
        with self.loading_lock:
            status_surf = self.font_small.render(self.loading_status_message, True, COLOR_LIGHT)
            self.screen.blit(status_surf, status_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

    def draw_side_selection_screen(self, mouse_pos):
        self.screen.fill(COLOR_BG)
        title_surf = self.font_large.render("Choose Your Opening Side", True, COLOR_LIGHT)
        self.screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3)))
        
        for text, rect in {"Red": self.play_red_rect, "White": self.play_white_rect}.items():
            color = COLOR_BUTTON_HOVER if rect.collidepoint(mouse_pos) else COLOR_BUTTON
            pygame.draw.rect(self.screen, color, rect)
            text_surf = self.font_medium.render(text, True, COLOR_TEXT)
            self.screen.blit(text_surf, text_surf.get_rect(center=rect.center))

    # ... (The rest of the CheckersGUI class is unchanged) ...

if __name__ == '__main__':
    gui = CheckersGUI()
    gui.main_loop()
