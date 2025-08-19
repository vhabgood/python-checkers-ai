#main.py
import pygame
import threading
import time
import sys
import os
from datetime import datetime
# Add project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from engine.board import Board
from engine.checkers_game import Checkers
from engine.constants import *  # Updated import
import logging

class CheckersGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((BOARD_SIZE + INFO_WIDTH, BOARD_SIZE))
        pygame.display.set_caption("Checkers")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("arial", 24, bold=True)
        self.font_medium = pygame.font.SysFont("arial", 20)
        self.font_small = pygame.font.SysFont("arial", 16)
        self.game = Checkers()
        self.ai_depth = 4
        self.game_mode = 'side_selection'
        self.human_player_color = None
        self.is_ai_thinking = False
        self.ai_analysis_complete_paused = False
        self.ai_move_result = None
        self.ai_eval_count = 0
        self.ai_all_evaluated_moves = []
        self.ai_analysis_lock = threading.Lock()
        self.selected_piece = None
        self.valid_moves = {}
        self.piece_counts = (12, 0, 12, 0)
        self.play_red_rect = pygame.Rect(BOARD_SIZE//2 - 80, BOARD_SIZE//2 - 40, 60, 40)
        self.play_white_rect = pygame.Rect(BOARD_SIZE//2 + 20, BOARD_SIZE//2 - 40, 60, 40)
        self.depth_minus_rect = pygame.Rect(BOARD_SIZE + 10, 150, 30, 30)
        self.depth_plus_rect = pygame.Rect(BOARD_SIZE + 40, 150, 30, 30)
        self.developer_mode = False
        self.eval_scroll_offset = 0
        self.board_is_flipped = False
        self.loading_state = 'side_selection'
        # Initialize logging
        log_dir = os.path.dirname(os.path.abspath(__file__))
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, f"{timestamp}_checkers_debug.log")),
                logging.StreamHandler()
            ]
        )
        logging.info("CheckersGUI initialized")

    def _update_valid_moves(self):
        logging.debug(f"Turn: {self.game.game_board.turn}, Human: {self.human_player_color}, Selected: {self.selected_piece}")
        all_moves = self.game.game_board.get_all_possible_moves(self.game.game_board.turn)
        logging.debug(f"All possible moves: {all_moves}")
        self.valid_moves = {}
        if self.game.game_board.forced_jumps:
            for start, end in self.game.game_board.forced_jumps:
                self.valid_moves[end] = start
        else:
            for start, end in all_moves:
                self.valid_moves[end] = start
        logging.debug(f"Valid moves: {self.valid_moves}")

    def _handle_click(self, pos):
        if self.game_mode != 'playing' or self.is_ai_thinking or self.ai_analysis_complete_paused:
            return
        x, y = pos
        row, col = y // SQUARE_SIZE, x // SQUARE_SIZE
        if self.board_is_flipped:
            row, col = 7 - row, 7 - col
        clicked_coord = (row, col)
        logging.debug(f"Clicked: {clicked_coord}")
        if self.selected_piece:
            if clicked_coord in self.valid_moves and self.valid_moves[clicked_coord] == self.selected_piece:
                logging.debug(f"Making move: {self.selected_piece} -> {clicked_coord}")
                self.game.perform_move(self.selected_piece, clicked_coord)
                logging.debug(f"Forced jumps: {self.game.game_board.forced_jumps}")
                if not self.game.game_board.forced_jumps:
                    self.selected_piece = None
                    self._update_valid_moves()
                    if self.human_player_color != self.game.game_board.turn:
                        self._start_ai_move()
                else:
                    self._update_valid_moves()
            else:
                self.selected_piece = None
                self._update_valid_moves()
                self._handle_click(pos)
        else:
            if (row, col) in [(s[0], s[1]) for s, e in self.game.game_board.get_all_possible_moves(self.game.game_board.turn)]:
                self.selected_piece = (row, col)
                logging.debug(f"Selected piece: {self.selected_piece}")
                filtered_moves = [(s, e) for s, e in self.game.game_board.get_all_possible_moves(self.game.game_board.turn) if s == self.selected_piece]
                logging.debug(f"Filtered moves for {self.selected_piece}: {filtered_moves}")
                self.valid_moves = {e: s for s, e in filtered_moves}
                logging.debug(f"Valid moves: {self.valid_moves}")
                logging.debug(f"Drawing valid moves: {self.valid_moves}")

    def _draw_board(self, mouse_pos):
        for row in range(8):
            for col in range(8):
                square_color = COLOR_LIGHT_SQUARE if (row + col) % 2 == 0 else COLOR_DARK_SQUARE
                pygame.draw.rect(self.screen, square_color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        if self.board_is_flipped:
            board = [row[:] for row in self.game.game_board.board][::-1]
            board = [row[::-1] for row in board]
        else:
            board = [row[:] for row in self.game.game_board.board]
        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece != EMPTY:
                    piece_color = COLOR_RED_P if piece in [RED, RED_KING] else COLOR_WHITE_P
                    pygame.draw.circle(self.screen, piece_color, (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2), PIECE_RADIUS)
                    if piece in [RED_KING, WHITE_KING]:
                        pygame.draw.circle(self.screen, COLOR_CROWN, (col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2), PIECE_RADIUS // 2)
        if self.valid_moves:
            for end in self.valid_moves:
                end_row, end_col = end
                if self.board_is_flipped:
                    end_row, end_col = 7 - end_row, 7 - end_col
                pygame.draw.circle(self.screen, COLOR_HIGHLIGHT, (end_col * SQUARE_SIZE + SQUARE_SIZE // 2, end_row * SQUARE_SIZE + SQUARE_SIZE // 2), PIECE_RADIUS // 2)
        if self.selected_piece:
            sel_row, sel_col = self.selected_piece
            if self.board_is_flipped:
                sel_row, sel_col = 7 - sel_row, 7 - sel_col
            pygame.draw.circle(self.screen, COLOR_SELECTED, (sel_col * SQUARE_SIZE + SQUARE_SIZE // 2, sel_row * SQUARE_SIZE + SQUARE_SIZE // 2), PIECE_RADIUS, 3)

    def _draw_info_panel(self, mouse_pos):
        logging.debug("Drawing info panel")
        panel_x, panel_right_edge = BOARD_SIZE + 10, BOARD_SIZE + INFO_WIDTH - 10
        y_pos = 10
        self.piece_counts = (
            sum(row.count(RED) for row in self.game.game_board.board),
            sum(row.count(RED_KING) for row in self.game.game_board.board),
            sum(row.count(WHITE) for row in self.game.game_board.board),
            sum(row.count(WHITE_KING) for row in self.game.game_board.board)
        )
        if self.game.winner:
            text = f"Winner: {PLAYER_NAMES[self.game.winner]}!"
            surf = self.font_large.render(text, True, COLOR_CROWN)
        else:
            text = f"Turn: {PLAYER_NAMES[self.game.game_board.turn]}"
            surf = self.font_medium.render(text, True, COLOR_WHITE_P if self.game.game_board.turn == WHITE else COLOR_RED_P)
        self.screen.blit(surf, (panel_x, y_pos))
        y_pos += 40
        score = self.game.evaluate_board_static(self.game.game_board.board, self.game.game_board.turn)/Checkers.MATERIAL_MULTIPLIER
        adv = f"+{score:.2f} (Red Adv.)" if score > 0.05 else f"{score:.2f} (White Adv.)" if score < -0.05 else "Even"
        self.screen.blit(self.font_small.render(f"Positional Score: {adv}", True, COLOR_TEXT), (panel_x, y_pos))
        y_pos += 25
        rm, rk, wm, wk = self.piece_counts
        self.screen.blit(self.font_small.render(f"Red: {rm} men, {rk} kings", True, COLOR_RED_P), (panel_x, y_pos))
        y_pos += 20
        self.screen.blit(self.font_small.render(f"White: {wm} men, {wk} kings", True, COLOR_WHITE_P), (panel_x, y_pos))
        y_pos += 25
        self.screen.blit(self.font_small.render(f"AI Depth: {self.ai_depth}", True, COLOR_TEXT), (panel_x, y_pos))
        y_pos += 30
        is_dis = self.is_ai_thinking or self.ai_analysis_complete_paused
        for r, t in [(self.depth_minus_rect, "-"), (self.depth_plus_rect, "+")]:
            color = COLOR_BUTTON_HOVER if r.collidepoint(mouse_pos) and not is_dis else COLOR_BUTTON_DISABLED if is_dis else COLOR_BUTTON
            pygame.draw.rect(self.screen, color, r)
            self.screen.blit(self.font_medium.render(t, True, COLOR_TEXT), r.move(10 if t=='-' else 7, 1))
        y_pos += 10
        
        is_ai_active = self.is_ai_thinking or self.ai_analysis_complete_paused
        if is_ai_active:
            if self.ai_analysis_complete_paused:
                self.screen.blit(self.font_small.render("Analysis Complete!", True, COLOR_CROWN), (panel_x, y_pos))
                y_pos += 20
                self.screen.blit(self.font_small.render("Press SPACE to make move.", True, COLOR_TEXT), (panel_x, y_pos))
                y_pos += 25
            else:
                self.screen.blit(self.font_small.render("Thinking...", True, COLOR_TEXT), (panel_x, y_pos))
                y_pos += 45

            if self.developer_mode:
                with self.ai_analysis_lock:
                    moves, count = self.ai_all_evaluated_moves, self.ai_eval_count
                self.screen.blit(self.font_small.render(f"Positions: {count:,}", True, COLOR_TEXT), (panel_x, y_pos))
                y_pos += 25
                self.screen.blit(self.font_small.render("Principal Variations:", True, COLOR_TEXT), (panel_x, y_pos))
                y_pos += 25
                list_y_start = y_pos
                line_height = 22
                clipping_area = pygame.Rect(panel_x, list_y_start, INFO_WIDTH - 30, BOARD_SIZE - list_y_start - 50)
                self.screen.set_clip(clipping_area)
                current_y = list_y_start
                for i, move_data in enumerate(moves):
                    if i < self.eval_scroll_offset or current_y > clipping_area.bottom:
                        continue
                    path = move_data['path']
                    path_str_parts = []
                    j = 0
                    while j < len(path):
                        start, end = path[j]
                        if abs(start[0] - end[0]) != 2:
                            path_str_parts.append(f"{coord_to_acf_notation(start)}-{coord_to_acf_notation(end)}")
                            j += 1
                        else:  # Jump sequence
                            jump_seq = [coord_to_acf_notation(start), coord_to_acf_notation(end)]
                            while (j + 1 < len(path)) and (path[j+1][0] == path[j][1]) and (abs(path[j+1][0][0]-path[j+1][1][0])==2):
                                j += 1
                                jump_seq.append(coord_to_acf_notation(path[j][1]))
                            path_str_parts.append("x".join(jump_seq))
                            j += 1
                    path_str = " -> ".join(path_str_parts)
                    score_str = f"({move_data['score']/Checkers.MATERIAL_MULTIPLIER:+.2f})"
                    color = COLOR_CROWN if i == 0 else COLOR_TEXT
                    score_surf = self.font_small.render(score_str, True, color)
                    score_rect = score_surf.get_rect(topright=(panel_right_edge, current_y))
                    max_text_width = clipping_area.width - score_rect.width - 15
                    lines = self._wrap_text(f"{i+1}. {path_str}", self.font_small, max_text_width)
                    for k, line in enumerate(lines):
                        if current_y > clipping_area.bottom:
                            break
                        self.screen.blit(self.font_small.render(line, True, color), (panel_x, current_y))
                        if k == 0:
                            self.screen.blit(score_surf, score_rect)
                        current_y += line_height
                self.screen.set_clip(None)

    def _wrap_text(self, text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = []
        current_width = 0
        for word in words:
            word_surface = font.render(word, True, COLOR_TEXT)
            word_width = word_surface.get_width()
            if current_width + word_width <= max_width:
                current_line.append(word)
                current_width += word_width + font.render(' ', True, COLOR_TEXT).get_width()
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width + font.render(' ', True, COLOR_TEXT).get_width()
        if current_line:
            lines.append(' '.join(current_line))
        return lines

    def _draw_game_screen(self, mouse_pos):
        self._draw_board(mouse_pos)
        self._draw_info_panel(mouse_pos)

    def _start_ai_move(self):
        self.is_ai_thinking = True
        self.ai_eval_count = 0
        self.ai_all_evaluated_moves = []
        threading.Thread(target=self._ai_worker, daemon=True).start()

    def _ai_worker(self):
        self.ai_move_result = self.game.find_best_move(self.ai_depth, self._update_ai_progress)
        self.is_ai_thinking = False
        self.ai_analysis_complete_paused = True

    def _update_ai_progress(self, evaluated, total, moves):
        with self.ai_analysis_lock:
            self.ai_eval_count = evaluated
            self.ai_all_evaluated_moves = moves

    def main_loop(self):
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.game_mode == 'side_selection':
                        if self.play_red_rect.collidepoint(mouse_pos):
                            self.human_player_color = RED
                            self.game_mode = 'playing'
                            self.loading_state = 'playing'
                            self._update_valid_moves()
                            if self.game.game_board.turn == WHITE:
                                self._start_ai_move()
                        elif self.play_white_rect.collidepoint(mouse_pos):
                            self.human_player_color = WHITE
                            self.game_mode = 'playing'
                            self.loading_state = 'playing'
                            self.board_is_flipped = True
                            self._update_valid_moves()
                            if self.game.game_board.turn == RED:
                                self._start_ai_move()
                        continue
                    if self.depth_minus_rect.collidepoint(mouse_pos) and not (self.is_ai_thinking or self.ai_analysis_complete_paused):
                        self.ai_depth = max(1, self.ai_depth - 1)
                    elif self.depth_plus_rect.collidepoint(mouse_pos) and not (self.is_ai_thinking or self.ai_analysis_complete_paused):
                        self.ai_depth += 1
                    elif self.human_player_color == self.game.game_board.turn:
                        self._handle_click(mouse_pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_d:
                        self.developer_mode = not self.developer_mode
                    elif event.key == pygame.K_SPACE and self.ai_analysis_complete_paused:
                        for start, end in self.ai_move_result:
                            self.game.perform_move(start, end)
                        self.ai_analysis_complete_paused = False
                        self.ai_move_result = None
                        self._update_valid_moves()
                        if self.human_player_color != self.game.game_board.turn:
                            self._start_ai_move()
                    elif event.key == pygame.K_UP and self.developer_mode:
                        self.eval_scroll_offset = max(0, self.eval_scroll_offset - 1)
                    elif event.key == pygame.K_DOWN and self.developer_mode:
                        self.eval_scroll_offset += 1
            self.screen.fill(COLOR_BG)
            if self.game_mode == 'side_selection':
                self.screen.blit(self.font_large.render("Select Your Side", True, COLOR_TEXT), (BOARD_SIZE//2 - 80, BOARD_SIZE//2 - 80))
                pygame.draw.rect(self.screen, COLOR_BUTTON_HOVER if self.play_red_rect.collidepoint(mouse_pos) else COLOR_BUTTON, self.play_red_rect)
                pygame.draw.rect(self.screen, COLOR_BUTTON_HOVER if self.play_white_rect.collidepoint(mouse_pos) else COLOR_BUTTON, self.play_white_rect)
                self.screen.blit(self.font_medium.render("Red", True, COLOR_RED_P), self.play_red_rect.move(10, 7))
                self.screen.blit(self.font_medium.render("White", True, COLOR_WHITE_P), self.play_white_rect.move(10, 7))
            elif self.game_mode == 'playing':
                self._draw_game_screen(mouse_pos)
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    gui = CheckersGUI()
    gui.main_loop()
