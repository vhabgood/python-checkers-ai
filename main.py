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
        self.play_red_rect = pygame.Rect(WIDTH//2 - 140, HEIGHT//2 - 25, 120, 50)
        self.play_white_rect = pygame.Rect(WIDTH//2 + 20, HEIGHT//2 - 25, 120, 50)
        
    def _load_resources_worker(self):
        def update_status(msg):
            with self.loading_lock:
                self.loading_status_message = msg
        
        # Call Checkers.load_all_resources directly
        Checkers.load_all_resources(update_status)
        self.reset_game_state(first_load=True)
        self.loading_state = 'side_selection'

    def reset_game_state(self, first_load=False):
        self.game = Checkers(load_resources=False)
        self.game_state_history = []
        self.selected_piece = None
        self.valid_moves = {}
        self.board_is_flipped = False
        self.last_move = None
        self.ai_depth = 5
        self.is_ai_thinking = False
        self.ai_move_result = None
        self.ai_analysis_complete_paused = False
        self.ai_all_evaluated_moves = []
        self.ai_analysis_lock = threading.Lock()
        self.ai_eval_count = 0
        self.developer_mode = False
        self.ai_current_path = []
        self.eval_scroll_offset = 0
        self.game_mode = None
        self.human_player_color = None
        self.ai_is_paused = False
        

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
        if self.is_ai_thinking or self.ai_analysis_complete_paused or self.game.winner or self.ai_is_paused: return
        self.is_ai_thinking, self.ai_move_result, self.eval_scroll_offset = True, "THINKING", 0
        with self.ai_analysis_lock: self.ai_all_evaluated_moves, self.ai_eval_count, self.ai_current_path = [], 0, []
        thread = threading.Thread(target=self._ai_worker, daemon=True).start()
    def _get_display_coords(self, r, c): return (7-r, 7-c) if self.board_is_flipped else (r, c)
    def _get_logical_coords_from_mouse(self, pos):
        x, y = pos
        if x > BOARD_SIZE or y > BOARD_SIZE: return None, None
        disp_r, disp_c = y // SQUARE_SIZE, x // SQUARE_SIZE
        return (7-disp_r, 7-disp_c) if self.board_is_flipped else (disp_r, disp_c)
    def _handle_move(self, start, end):
        self.ai_is_paused = False
        if not self.game.forced_jumps: self.game_state_history.append(copy.deepcopy(self.game))
        self.game.perform_move(start, end)
        self.last_move = (start, end)
        self.selected_piece = self.game.game_board.forced_jumps[0][0] if self.game.game_board.forced_jumps else None
        self._update_valid_moves()
    def _sync_gui_to_game_state(self):
        self.game.winner = self.game.check_win_condition()
        self.selected_piece, self.last_move, self.is_ai_thinking, self.ai_analysis_complete_paused = None, None, False, False
        with self.ai_analysis_lock: self.ai_all_evaluated_moves, self.ai_eval_count = [], 0
        self._update_valid_moves()
    def _update_valid_moves(self):
        self.valid_moves = {}
        if not self.game: return
        possible = self.game.game_board.forced_jumps or (self.game.get_all_possible_moves(self.game.game_board.turn) if self.selected_piece else [])
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
                    if self.buttons["Force Move"].collidepoint(mouse_pos):
                        if self.is_ai_thinking:
                            with self.ai_analysis_lock:
                                if self.ai_all_evaluated_moves: self.ai_move_result = self.ai_all_evaluated_moves[0]['move']
                        else: self._start_ai_move()
                        continue

                    if self.is_ai_thinking or self.ai_analysis_complete_paused:
                        if self.eval_scroll_up_rect.collidepoint(mouse_pos): self.eval_scroll_offset=max(0,self.eval_scroll_offset-1)
                        elif self.eval_scroll_down_rect.collidepoint(mouse_pos): self.eval_scroll_offset+=1
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
                        row, col = self._get_logical_coords_from_mouse(mouse_pos)
                        if self.game.game_board.turn == self.human_player_color and row is not None:
                            if (row, col) in self.valid_moves: self._handle_move(self.valid_moves[(row, col)], (row, col))
                            elif not self.game.game_board.forced_jumps and self.game.game_board.board[row][col].lower() == self.game.game_board.turn:
                                self.selected_piece = (row, col); self._update_valid_moves()
                            else: self.selected_piece = None; self._update_valid_moves()
            
            if self.loading_state == 'loading': self.draw_loading_screen()
            elif self.loading_state == 'side_selection': self.draw_side_selection_screen(mouse_pos)
            elif self.game_mode:
                if not self.game.winner: self.game.winner = self.game.check_win_condition()
                if self.is_ai_thinking and self.ai_move_result != "THINKING":
                    self.is_ai_thinking = False
                    if self.developer_mode or self.game.game_board.turn != self.human_player_color: self.ai_analysis_complete_paused = True
                    else:
                        if self.ai_move_result: self._handle_move(self.ai_move_result[0], self.ai_move_result[1])
                        self.ai_move_result = None
                
                all_moves = self.game.get_all_possible_moves(self.game.game_board.turn) if self.game else []
                is_ai_turn = self.game and self.game.game_board.turn != self.human_player_color and not self.ai_is_paused
                if is_ai_turn and all_moves and not (self.is_ai_thinking or self.ai_analysis_complete_paused or self.game.winner):
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

    def _wrap_text(self, text, font, max_text_width):
        lines = []
        words = text.split(' ')
        if not words:
            return []
        current_line = words[0]
        for word in words[1:]:
            if self.font_small.size(current_line + ' ' + word)[0] <= max_text_width:
                current_line += ' ' + word
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines

    def _draw_game_screen(self, mouse_pos):
        self.screen.fill(COLOR_BG); self._draw_board(); self._draw_last_move_highlight()
        if self.developer_mode and (self.is_ai_thinking or self.ai_analysis_complete_paused): self._draw_dev_mode_highlights()
        self._draw_pieces(mouse_pos); self._draw_valid_moves(); self._draw_info_panel(mouse_pos); self._draw_menu_bar(mouse_pos)

    def _draw_board(self):
        for r_logic in range(ROWS):
            for c_logic in range(COLS):
                r_disp, c_disp = self._get_display_coords(r_logic, c_logic)
                color = COLOR_LIGHT if (r_disp + c_disp) % 2 == 0 else COLOR_DARK
                pygame.draw.rect(self.screen, color, (c_disp*SQUARE_SIZE, r_disp*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
                if (r_logic + c_logic) % 2 == 1:
                    num_text = self.font_small.render(str(COORD_TO_ACF.get((r_logic, c_logic), '')), True, COLOR_LIGHT)
                    self.screen.blit(num_text, (c_disp * SQUARE_SIZE + 5, r_disp * SQUARE_SIZE + 5))

    def _draw_last_move_highlight(self):
        if not self.last_move: return
        s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA); s.fill(COLOR_LAST_MOVE)
        for r_logic, c_logic in self.last_move:
            r_disp, c_disp = self._get_display_coords(r_logic, c_logic)
            self.screen.blit(s, (c_disp * SQUARE_SIZE, r_disp * SQUARE_SIZE))

    def _draw_dev_mode_highlights(self):
        with self.ai_analysis_lock: path = self.ai_current_path
        if not path: return
        for i, (start, end) in enumerate(path[:self.MAX_DEV_HIGHLIGHTS]):
            color = COLOR_DEV_PRIMARY if i == 0 else COLOR_DEV_SECONDARY
            s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA); s.fill(color)
            for r_logic, c_logic in [start, end]:
                r_disp, c_disp = self._get_display_coords(r_logic, c_logic)
                self.screen.blit(s, (c_disp * SQUARE_SIZE, r_disp * SQUARE_SIZE))

    def _draw_pieces(self, mouse_pos):
        radius = SQUARE_SIZE//2 - 8; self.piece_counts = [0, 0, 0, 0]
        for r_logic in range(ROWS):
            for c_logic in range(COLS):
                piece = self.game.game_board.board[r_logic][c_logic]
                if piece != EMPTY:
                    r_disp, c_disp = self._get_display_coords(r_logic, c_logic)
                    cx, cy = c_disp * SQUARE_SIZE + SQUARE_SIZE // 2, r_disp * SQUARE_SIZE + SQUARE_SIZE // 2
                    if (r_logic, c_logic) == self.selected_piece: pygame.draw.circle(self.screen, COLOR_SELECTED, (cx, cy), radius + 4)
                    piece_color = COLOR_RED_P if piece.lower() == RED else COLOR_WHITE_P
                    pygame.draw.circle(self.screen, piece_color, (cx, cy), radius)
                    if piece.isupper(): pygame.draw.circle(self.screen, COLOR_CROWN, (cx, cy), radius // 2)
                    if piece == RED: self.piece_counts[0]+=1
                    elif piece == RED_KING: self.piece_counts[1]+=1
                    elif piece == WHITE: self.piece_counts[2]+=1
                    elif piece == WHITE_KING: self.piece_counts[3]+=1

    def _draw_valid_moves(self):
        if not self.valid_moves: return
        s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA); pygame.draw.circle(s, COLOR_VALID, (SQUARE_SIZE // 2, SQUARE_SIZE // 2), 15)
        for r_logic, c_logic in self.valid_moves.keys():
            r_disp, c_disp = self._get_display_coords(r_logic, c_logic)
            self.screen.blit(s, (c_disp * SQUARE_SIZE, r_disp * SQUARE_SIZE))

    def _draw_info_panel(self, mouse_pos):
        panel_x, y_pos = BOARD_SIZE + 20, 20
        panel_right_edge = BOARD_SIZE + INFO_WIDTH - 20
        self.screen.blit(self.font_medium.render("CHECKERS", True, COLOR_LIGHT), (panel_x, y_pos)); y_pos += 40
        if self.game.winner: text = f"Winner: {PLAYER_NAMES[self.game.winner]}!"; surf = self.font_large.render(text, True, COLOR_CROWN)
        else: text = f"Turn: {PLAYER_NAMES[self.game.game_board.turn]}"; surf = self.font_medium.render(text, True, COLOR_WHITE_P if self.game.game_board.turn == WHITE else COLOR_RED_P)
        self.screen.blit(surf, (panel_x, y_pos)); y_pos += 40
        score = Checkers.evaluate_board_static(self.game.game_board.board, self.game.game_board.turn)/Checkers.MATERIAL_MULTIPLIER
        adv = f"+{score:.2f} (Red Adv.)" if score > 0.05 else f"{score:.2f} (White Adv.)" if score < -0.05 else "Even"
        self.screen.blit(self.font_small.render(f"Positional Score: {adv}", True, COLOR_LIGHT), (panel_x, y_pos)); y_pos += 25
        rm, rk, wm, wk = self.piece_counts
        self.screen.blit(self.font_small.render(f"Red: {rm} men, {rk} kings", True, COLOR_RED_P), (panel_x, y_pos)); y_pos += 20
        self.screen.blit(self.font_small.render(f"White: {wm} men, {wk} kings", True, COLOR_WHITE_P), (panel_x, y_pos)); y_pos += 25
        self.screen.blit(self.font_small.render(f"AI Depth: {self.ai_depth}", True, COLOR_LIGHT), (panel_x, y_pos)); y_pos += 30
        is_dis = self.is_ai_thinking or self.ai_analysis_complete_paused
        for r, t in [(self.depth_minus_rect, "-"), (self.depth_plus_rect, "+")]:
            color = COLOR_BUTTON_HOVER if r.collidepoint(mouse_pos) and not is_dis else COLOR_BUTTON_DISABLED if is_dis else COLOR_BUTTON
            pygame.draw.rect(self.screen, color, r); self.screen.blit(self.font_medium.render(t,True,COLOR_TEXT), r.move(10 if t=='-' else 7, 1))
        y_pos+=10
        
        is_ai_active = self.is_ai_thinking or self.ai_analysis_complete_paused
        if is_ai_active:
            if self.ai_analysis_complete_paused:
                self.screen.blit(self.font_small.render("Analysis Complete!", True, COLOR_CROWN), (panel_x, y_pos)); y_pos += 20
                self.screen.blit(self.font_small.render("Press SPACE to make move.", True, COLOR_LIGHT), (panel_x, y_pos)); y_pos += 25
            else:
                self.screen.blit(self.font_small.render("Thinking...", True, COLOR_LIGHT), (panel_x, y_pos)); y_pos += 45

            if self.developer_mode:
                with self.ai_analysis_lock: moves, count = self.ai_all_evaluated_moves, self.ai_eval_count
                self.screen.blit(self.font_small.render(f"Positions: {count:,}", True, COLOR_LIGHT), (panel_x, y_pos)); y_pos += 25
                self.screen.blit(self.font_small.render("Principal Variations:", True, COLOR_LIGHT), (panel_x, y_pos)); y_pos += 25
                list_y_start, line_h = y_pos, 22
                clip_area = pygame.Rect(panel_x, list_y_start, INFO_WIDTH - 30, BOARD_SIZE - list_y_start - 50)
                self.screen.set_clip(clipping_area); current_y = list_y_start
                for i, move_data in enumerate(moves):
                    if i < self.eval_scroll_offset or current_y > clip_area.bottom: continue
                    path = move_data['path']; path_str_parts = []
                    j=0
                    while j < len(path):
                        start, end = path[j]
                        if abs(start[0] - end[0]) != 2: # Simple move
                            path_str_parts.append(f"{coord_to_acf_notation(start)}-{coord_to_acf_notation(end)}"); j+=1
                        else: # Jump sequence
                            jump_seq = [coord_to_acf_notation(start), coord_to_acf_notation(end)]
                            while (j + 1 < len(path)) and (path[j+1][0] == path[j][1]) and (abs(path[j+1][0][0]-path[j+1][1][0])==2):
                                j+=1; jump_seq.append(coord_to_acf_notation(path[j][1]))
                            path_str_parts.append("x".join(jump_seq)); j+=1
                    path_str = " -> ".join(path_str_parts)

                    score_str = f"({move_data['score']/Checkers.MATERIAL_MULTIPLIER:+.2f})"; color = COLOR_CROWN if i==0 else COLOR_LIGHT
                    score_surf = self.font_small.render(score_str, True, color)
                    score_rect = score_surf.get_rect(topright=(panel_right_edge, current_y))
                    max_text_width = clipping_area.width - score_rect.width - 15
                    lines = self._wrap_text(f"{i+1}. {path_str}", self.font_small, max_text_width)
                    for k, line in enumerate(lines):
                        if current_y > clip_area.bottom: break
                        self.screen.blit(self.font_small.render(line, True, color), (panel_x, current_y))
                        if k==0: self.screen.blit(score_surf, score_rect)
                        current_y += line_h
                self.screen.set_clip(None)

    def _draw_menu_bar(self, mouse_pos):
        pygame.draw.rect(self.screen, COLOR_BG, (0, BOARD_SIZE, WIDTH, MENU_BAR_HEIGHT))
        for text, rect in self.buttons.items():
            is_clickable = True
            if text not in ["Force Move", "Dev Mode", "Reset"] and (self.is_ai_thinking or self.ai_analysis_complete_paused):
                is_clickable = False
            
            color = COLOR_BUTTON_HOVER if rect.collidepoint(mouse_pos) and is_clickable else (COLOR_BUTTON if is_clickable else COLOR_BUTTON_DISABLED)
            pygame.draw.rect(self.screen, color, rect)
            disp_text = "Dev: ON" if text == 'Dev Mode' and self.developer_mode else text
            text_surf = self.font_small.render(disp_text, True, COLOR_TEXT)
            self.screen.blit(text_surf, text_surf.get_rect(center=rect.center))

if __name__ == '__main__':
    gui = CheckersGUI()
    gui.main_loop()

