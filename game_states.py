# game_states.py
import pygame
import logging
import time
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
        self.font = pygame.font.SysFont(None, 18) 
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
    def __init__(self, screen):
        self.screen = screen
        self.done = False
        self.next_state = None
        self.font = pygame.font.SysFont('Arial', 24)

    def handle_events(self, events):
        raise NotImplementedError
    def update(self):
        raise NotImplementedError
    def draw(self):
        raise NotImplementedError

class LoadingScreen:
    """A screen that shows a loading message and progress, now with a thread-safe queue."""
    def __init__(self, screen):
        self.screen = screen
        self.done = False
        self.next_state = "player_selection"
        self.font = pygame.font.SysFont(None, 48)
        self.small_font = pygame.font.SysFont(None, 24)
        self.status_message = "Initializing..."
        
        # --- THREADING FIX ---
        # A queue to safely receive status updates from the loading thread.
        self.status_queue = queue.Queue()
        # --- END FIX ---

#
# --- CHANGE START ---
#
    def reset(self):
        """Resets the loading screen to its initial state for a new loading sequence."""
        self.done = False
        self.status_message = "Loading Databases..."
        # Use hasattr to safely initialize start_time
        if not hasattr(self, 'start_time'):
            self.start_time = pygame.time.get_ticks()
        else:
            self.start_time = pygame.time.get_ticks()
#
# --- CHANGE END ---
#

#
# --- CHANGE START ---
#
    def update(self):
        """Checks the queue for new status messages from the loading thread."""
        try:
            # Check for a new message without blocking
            self.status_message = self.status_queue.get_nowait()
            # If we receive the final message, mark the screen as done
            if self.status_message == "Load Complete!":
                self.done = True
                self.next_state = "game" # Set the next state to transition to
        except queue.Empty:
            pass
#
# --- CHANGE END ---
#

    def handle_events(self, events):
        pass

    def update(self):
        """Checks the queue for new status messages from the loading thread."""
        try:
            # Check for a new message without blocking
            self.status_message = self.status_queue.get_nowait()
        except queue.Empty:
            pass # It's normal for the queue to be empty most of the time

    def draw(self):
        """Draws the loading text and the current status message."""
        self.screen.fill(COLOR_BG)
        title_surf = self.font.render("Checkers AI", True, COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50))
        
        status_surf = self.small_font.render(self.status_message, True, COLOR_TEXT)
        status_rect = status_surf.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 20))
        
        self.screen.blit(title_surf, title_rect)
        self.screen.blit(status_surf, status_rect)

    def reset(self):
        """Resets the loading screen to its initial state."""
        self.done = False
        self.status_message = "Loading Databases..."
        if not hasattr(self, 'start_time'):
            self.start_time = pygame.time.get_ticks()
        
class PlayerSelectionScreen(BaseState):
    def __init__(self, screen):
        super().__init__(screen)
        self.next_state = "game"
        self.player_choice = None
        self.buttons = [
            {'text': 'Red', 'rect': pygame.Rect(100, 200, 100, 50), 'player': RED},
            {'text': 'White', 'rect': pygame.Rect(400, 200, 100, 50), 'player': WHITE}
        ]
        logger.info("PlayerSelectionScreen initialized.")

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                for button in self.buttons:
                    if button['rect'].collidepoint(mouse_pos):
                        player_color_name = PLAYER_NAMES.get(button['player'])
                        self.player_choice = player_color_name.lower()
                        self.done = True
                        logger.info(f"Player selected {player_color_name}.")

    def update(self):
        pass

    def draw(self):
        self.screen.fill(COLOR_BG)
        title_text = self.font.render("Choose Your Side", True, COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.screen.get_width() / 2, 100))
        self.screen.blit(title_text, title_rect)
        for button in self.buttons:
            pygame.draw.rect(self.screen, COLOR_BUTTON, button['rect'])
            text_surf = self.font.render(button['text'], True, COLOR_TEXT)
            text_rect = text_surf.get_rect(center=button['rect'].center)
            self.screen.blit(text_surf, text_rect)
