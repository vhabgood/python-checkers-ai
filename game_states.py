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
    def __init__(self, screen):
        self.screen = screen
        self.done = False
        self.next_state = None
        self.font = pygame.font.SysFont('Arial', 36)
        self.small_font = pygame.font.SysFont('Arial', 24)


    def handle_events(self, events, app=None): # Add app parameter for compatibility
        raise NotImplementedError
    def update(self):
        raise NotImplementedError
    def draw(self):
        raise NotImplementedError

class LoadingScreen:
    """A screen that shows a simple loading message."""
    def __init__(self, screen, status_queue):
        self.screen = screen
        self.status_queue = status_queue
        self.done = False
        self.next_state = None
        self.font = pygame.font.SysFont(None, 36)
        self.error_message = ""

    def reset(self):
        self.done = False
        self.next_state = None
        self.error_message = ""

    def update(self):
        try:
            msg = self.status_queue.get_nowait()
            if "DONE" in msg:
                self.done = True
                self.next_state = "game"
            elif "ERROR" in msg:
                self.error_message = msg.replace("ERROR:", "").strip()
        except queue.Empty:
            pass

    def draw(self):
        self.screen.fill((20, 20, 20))
        if self.error_message:
            text = self.font.render("Error Loading Game!", True, (255, 100, 100))
            self.screen.blit(text, (self.screen.get_width() // 2 - text.get_width() // 2, 100))
        else:
            text = self.font.render("Loading...", True, (255, 255, 255))
            self.screen.blit(text, (self.screen.get_width() // 2 - text.get_width() // 2, 100))

    def handle_events(self, events, app_instance):
        pass

class PlayerSelectionScreen(BaseState):
    def __init__(self, screen):
        super().__init__(screen)
        self.next_state = "loading" 
        self.player_choice = None
        self.selection_made = False # Flag to prevent double-clicks
        self.buttons = [
            Button('Play as Red', (WIDTH/2 - 100, 200), (200, 50), lambda: self.select_player(RED)),
            Button('Play as White', (WIDTH/2 - 100, 270), (200, 50), lambda: self.select_player(WHITE))
        ]
        logger.info("PlayerSelectionScreen initialized.")

    def select_player(self, color):
        """Callback function for the buttons."""
        player_color_name = PLAYER_NAMES.get(color)
        self.player_choice = player_color_name.lower()
        self.done = True
        logger.info(f"Player selected {player_color_name}. Selection is now locked.")

    def handle_events(self, events, app=None):
        for event in events:
            # Only handle clicks if a selection has NOT been made yet
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.selection_made:
                for button in self.buttons:
                    if button.is_clicked(event.pos):
                        self.selection_made = True # Set the flag to true, preventing more clicks
                        logger.debug("Player selection button clicked.")
                        button.callback()
                        break # Stop processing other buttons after a click

    def update(self):
        # This state doesn't have any continuous logic to update
        pass

    def draw(self):
        self.screen.fill(COLOR_BG)
        title_text = self.font.render("Choose Your Side", True, COLOR_TEXT)
        title_rect = title_text.get_rect(center=(self.screen.get_width() / 2, 100))
        self.screen.blit(title_text, title_rect)
        for button in self.buttons:
            button.draw(self.screen)
            
            # game_states.py -> in PlayerSelectionScreen class

    def reset(self):
        """Resets the screen to its initial state."""
        self.done = False
        self.next_state = None
        self.player_choice = None
        self.selection_made = False # <-- Reset the flag here

