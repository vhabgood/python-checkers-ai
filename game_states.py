# game_states.py
import pygame
import logging
import time
from engine.constants import (
    COLOR_BG, COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_TEXT,
    RED, WHITE, PLAYER_NAMES
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

class LoadingScreen(BaseState):
    def __init__(self, screen):
        super().__init__(screen)
        self.next_state = "player_selection"
        self.loading_status = ["Loading databases...", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"]
        self.current_status_index = 0
        self.last_update_time = time.time()
        logger.info("LoadingScreen initialized.")

    def handle_events(self, events):
        pass

    def update(self):
        current_time = time.time()
        if current_time - self.last_update_time > 0.5:
            self.current_status_index += 1
            if self.current_status_index >= len(self.loading_status):
                self.done = True
                logger.info("Loading complete. Transitioning to player selection.")
            self.last_update_time = current_time

    def draw(self):
        self.screen.fill(COLOR_BG)
        status_text = self.font.render(self.loading_status[min(self.current_status_index, len(self.loading_status) - 1)], True, COLOR_TEXT)
        status_rect = status_text.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2))
        self.screen.blit(status_text, status_rect)
        
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