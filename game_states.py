# game_states.py
import pygame
import logging
from engine.constants import (COLOR_BG, COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_TEXT, WIDTH)

logger = logging.getLogger('gui')

class Button:
    """A simple, clickable button class."""
    def __init__(self, text, pos, size, callback):
        self.text = text; self.pos = pos; self.size = size; self.callback = callback
        self.rect = pygame.Rect(pos, size); self.font = pygame.font.SysFont(None, 24); self.hovered = False

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos)
        button_color = COLOR_BUTTON_HOVER if self.hovered else COLOR_BUTTON
        pygame.draw.rect(screen, button_color, self.rect)
        text_surf = self.font.render(self.text, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, pos): return self.rect.collidepoint(pos)

class BaseState:
    """A base class for all game states."""
    def __init__(self): self.done = False
    def handle_event(self, event): pass
    def update(self): pass
    def draw(self, screen): pass
    def reset(self): self.done = False

class PlayerSelectionScreen(BaseState):
    """
    A simplified main menu screen. Its only purpose is to launch the main
    game/analysis board.
    """
    def __init__(self, screen):
        super().__init__()
        self.screen = screen
        self.font = pygame.font.SysFont('Arial', 36)
        self.next_state = "game"
        self.button = Button('Start Analysis', (WIDTH/2 - 125, 250), (250, 50), self.start_game)
        self.player_configs = None # Must be initialized for main loop

    def start_game(self):
        """Sets the done flag to trigger the state transition."""
        self.player_configs = {} # Signal to main loop that a choice was made
        self.done = True

    def handle_event(self, event):
        """Handles clicks on the start button."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button.is_clicked(event.pos):
                self.button.callback()

    def draw(self, screen):
        """Draws the main menu."""
        screen.fill(COLOR_BG)
        title_text = self.font.render("Checkers Engine", True, COLOR_TEXT)
        screen.blit(title_text, (screen.get_width() / 2 - title_text.get_width() / 2, 150))
        self.button.draw(screen)

    def reset(self):
        """Resets the state to be ready for the next time it's shown."""
        self.done = False
        self.player_configs = None


