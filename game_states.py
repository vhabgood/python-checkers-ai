# game_states.py
import pygame
import logging
import queue
from engine.constants import (
    COLOR_BG, COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_TEXT,
    RED, WHITE, PLAYER_NAMES, WIDTH, HEIGHT
)

logger = logging.getLogger('gui')

class Button:
    def __init__(self, text, pos, size, callback):
        self.text = text
        self.pos = pos
        self.size = size
        self.callback = callback
        self.rect = pygame.Rect(pos, size)
        self.font = pygame.font.SysFont(None, 24) 
        self.hovered = False

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos)
        button_color = COLOR_BUTTON_HOVER if self.hovered else COLOR_BUTTON
        pygame.draw.rect(screen, button_color, self.rect)
        text_surf = self.font.render(self.text, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class BaseState:
    def __init__(self):
        self.done = False

    def handle_event(self, event):
        raise NotImplementedError
    def update(self):
        raise NotImplementedError
    def draw(self, screen):
        raise NotImplementedError


class PlayerSelectionScreen(BaseState):
    def __init__(self, screen):
        super().__init__()
        self.screen = screen
        self.font = pygame.font.SysFont('Arial', 36)
        self.player_configs = None
        self.buttons = [
            Button('Play as Red (vs V1)', (WIDTH/2 - 125, 200), (250, 50), lambda: self.select_player_vs_ai(RED)),
            Button('Play as White (vs V1)', (WIDTH/2 - 125, 270), (250, 50), lambda: self.select_player_vs_ai(WHITE)),
            Button('Engine V1 vs V2 (Test)', (WIDTH/2 - 125, 340), (250, 50), self.start_engine_match)
        ]

    def select_player_vs_ai(self, player_color):
        """Sets up a Human vs AI match."""
        from engine.evaluation import evaluate_board_v1
        self.done = True
        if player_color == RED:
            self.player_configs = {
                "red": {'type': 'human', 'name': 'Human'},
                "white": {'type': 'engine', 'name': 'Engine V1', 'eval_func': evaluate_board_v1}
            }
        else:
            self.player_configs = {
                "red": {'type': 'engine', 'name': 'Engine V1', 'eval_func': evaluate_board_v1},
                "white": {'type': 'human', 'name': 'Human'}
            }

    def start_engine_match(self):
        """Sets up an AI vs AI match for testing."""
        from engine.evaluation import evaluate_board_v1, evaluate_board_v2_experimental
        self.done = True
        self.player_configs = {
            "red": {'type': 'engine', 'name': 'Engine V1 (Stable)', 'eval_func': evaluate_board_v1},
            "white": {'type': 'engine', 'name': 'Engine V2 (Experimental)', 'eval_func': evaluate_board_v2_experimental}
        }

    def handle_event(self, event):
        """
        Handles a single event. Corrected to process one event at a time without a loop.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.is_clicked(event.pos):
                    button.callback()
                    return # Process one click at a time

    def update(self):
        # This state has no logic that needs to run every frame.
        pass

    def draw(self, screen):
        screen.fill(COLOR_BG)
        title_text = self.font.render("Checkers Engine", True, COLOR_TEXT)
        screen.blit(title_text, (screen.get_width() / 2 - title_text.get_width() / 2, 100))
        for button in self.buttons:
            button.draw(screen)
            
    def reset(self):
        """Resets the screen for the next game."""
        self.done = False
        self.player_configs = None

class LoadingScreen(BaseState):
    """
    A simple state to display a loading message. This is added back in
    to resolve the ImportError from main.py.
    """
    def __init__(self, screen, status_queue):
        super().__init__()
        self.screen = screen
        self.status_queue = status_queue
        self.font = pygame.font.SysFont('Arial', 36)
        self.next_state = "game"

    def update(self):
        try:
            if "DONE" in self.status_queue.get_nowait():
                self.done = True
        except queue.Empty:
            pass

    def draw(self, screen):
        screen.fill(COLOR_BG)
        text = self.font.render("Loading...", True, COLOR_TEXT)
        screen.blit(text, (screen.get_width() // 2 - text.get_width() // 2, 150))
    
    def handle_event(self, event):
        # This screen is not interactive
        pass

