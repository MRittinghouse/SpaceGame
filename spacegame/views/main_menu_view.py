"""
Main menu view.

Starting point for the game with options to start new game, load, settings, etc.
"""

import pygame
import pygame_gui
import math
import random
from typing import Optional, Union
from spacegame.views.base_view import BaseView
from spacegame.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState, IMAGES_DIR, scale_x, scale_y,
)
from spacegame.save_manager import SaveManager
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FONT_HERO, FONT_TITLE, FontCache
from spacegame.engine.particles import ParticlePool, STAR_TWINKLE
from spacegame.engine.sprites import AnimatedSprite, get_sprite_manager, res_scale


class MainMenuView(BaseView):
    """
    Main menu screen with game options.

    Features animated deep-space background, title glow, and particle ambiance.
    """

    def __init__(self, ui_manager: pygame_gui.UIManager, save_manager: SaveManager) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.save_manager = save_manager
        self.next_state: Optional[Union[GameState, str]] = None

        # Fonts
        self.title_font = FontCache.get(FONT_HERO)
        self.subtitle_font = FontCache.get(FONT_TITLE)

        # UI Elements (created in on_enter)
        self.new_game_button: Optional[pygame_gui.elements.UIButton] = None
        self.continue_button: Optional[pygame_gui.elements.UIButton] = None
        self.load_game_button: Optional[pygame_gui.elements.UIButton] = None
        self.exit_button: Optional[pygame_gui.elements.UIButton] = None

        # Animated background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=7)

        # Particle system for ambient title sparkles
        self.particles = ParticlePool(200)
        self._particle_timer = 0.0

        # Drifting ship sprite (slowly crosses the lower portion of the screen)
        self._sprite_mgr = get_sprite_manager()
        self._ship_anim: Optional[AnimatedSprite] = None
        self._ship_x = -100.0  # starts off-screen left
        self._ship_y = WINDOW_HEIGHT * 0.65
        self._ship_speed = 18.0  # pixels per second — slow, ambient drift
        self._ship_bob_phase = 0.0

        # Fade-in animation
        self._fade_alpha = 255  # starts fully black
        self._fade_speed = 510.0  # alpha units per second (0.5s fade)

        # Title glow animation
        self._glow_time = 0.0

        # New game confirmation state
        self._confirm_new_game: bool = False
        self._confirm_font = FontCache.get(FONT_TITLE)

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered Main Menu")
        self._fade_alpha = 255

        # Load an animated ship sprite for the drifting ambient ship
        if self._ship_anim is None:
            ship_ids = [
                "light_freighter", "scout_vessel", "fast_courier",
                "clipper", "shuttle",
            ]
            ship_id = random.choice(ship_ids)
            self._ship_anim = self._sprite_mgr.get_ship_animated(
                ship_id, category="player", scale=res_scale(2),
            )
        # Reset ship position to off-screen left
        self._ship_x = -100.0

        button_width = scale_x(300)
        button_height = scale_y(60)
        button_x = (WINDOW_WIDTH - button_width) // 2
        start_y = WINDOW_HEIGHT // 2
        spacing = scale_y(70)

        self.new_game_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y, button_width, button_height),
            text="New Game",
            manager=self.ui_manager,
        )

        self.continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing, button_width, button_height),
            text="Continue",
            manager=self.ui_manager,
        )
        # Enable Continue only if saves exist
        most_recent = self.save_manager.get_most_recent_save_slot()
        if most_recent is None:
            self.continue_button.disable()

        self.load_game_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 2, button_width, button_height),
            text="Load Game",
            manager=self.ui_manager,
        )

        self.exit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, start_y + spacing * 3, button_width, button_height),
            text="Exit",
            manager=self.ui_manager,
        )

    def on_exit(self) -> None:
        super().on_exit()
        for btn in [
            self.new_game_button,
            self.continue_button,
            self.load_game_button,
            self.exit_button,
        ]:
            if btn:
                btn.kill()

    def handle_event(self, event: pygame.event.Event) -> None:
        # New game confirmation dialog
        if self._confirm_new_game:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_y, pygame.K_RETURN):
                    self._confirm_new_game = False
                    self._set_menu_buttons_visible(True)
                    logger.info("New Game confirmed")
                    self.next_state = GameState.GALAXY_MAP
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    self._confirm_new_game = False
                    self._set_menu_buttons_visible(True)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check Yes/No button rects (must match render positions exactly)
                cx = WINDOW_WIDTH // 2
                cy = WINDOW_HEIGHT // 2
                pw, ph = scale_x(480), scale_y(200)
                panel_top = cy - ph // 2
                btn_w, btn_h = scale_x(140), scale_y(44)
                btn_y = panel_top + scale_y(100)
                yes_rect = pygame.Rect(cx - btn_w - scale_x(15), btn_y, btn_w, btn_h)
                no_rect = pygame.Rect(cx + scale_x(15), btn_y, btn_w, btn_h)
                if yes_rect.collidepoint(event.pos):
                    self._confirm_new_game = False
                    self._set_menu_buttons_visible(True)
                    self.next_state = GameState.GALAXY_MAP
                elif no_rect.collidepoint(event.pos):
                    self._confirm_new_game = False
                    self._set_menu_buttons_visible(True)
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.new_game_button:
                # Check if saves exist before starting new game
                has_saves = any(
                    self.save_manager.get_save_metadata(i) is not None
                    for i in range(self.save_manager.DEFAULT_NUM_SLOTS)
                )
                if has_saves:
                    self._confirm_new_game = True
                    self._set_menu_buttons_visible(False)
                    logger.info("New Game: showing confirmation (saves exist)")
                else:
                    logger.info("New Game: no saves, starting directly")
                    self.next_state = GameState.GALAXY_MAP
            elif event.ui_element == self.continue_button:
                logger.info("Continue button pressed")
                self.next_state = "continue"
            elif event.ui_element == self.load_game_button:
                logger.info("Load Game button pressed")
                self.next_state = "load_game"
            elif event.ui_element == self.exit_button:
                logger.info("Exit button pressed")
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _set_menu_buttons_visible(self, visible: bool) -> None:
        """Show or hide the main menu buttons (for confirmation dialog)."""
        for btn in [self.new_game_button, self.continue_button,
                    self.load_game_button, self.exit_button]:
            if btn:
                if visible:
                    btn.show()
                else:
                    btn.hide()

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt

        # Fade in
        if self._fade_alpha > 0:
            self._fade_alpha = max(0, self._fade_alpha - self._fade_speed * dt)

        # Drift ship across screen and update its animation
        self._ship_x += self._ship_speed * dt
        self._ship_bob_phase += dt * 0.8
        if self._ship_x > WINDOW_WIDTH + 100:
            self._ship_x = -100.0  # wrap around
        if self._ship_anim is not None:
            self._ship_anim.update(dt)

        # Emit ambient particles — title sparkles + scattered across screen
        self._particle_timer += dt
        if self._particle_timer > 0.08:
            self._particle_timer = 0.0
            # Title area sparkles
            x = WINDOW_WIDTH // 2 + random.randint(-250, 250)
            y = WINDOW_HEIGHT // 4 + random.randint(-40, 40)
            self.particles.emit(x, y, STAR_TWINKLE)
            # Scattered ambient sparkles across the background
            if random.random() < 0.3:
                x2 = random.randint(0, WINDOW_WIDTH)
                y2 = random.randint(0, WINDOW_HEIGHT)
                self.particles.emit(x2, y2, STAR_TWINKLE)

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)

        # Drifting ship (behind particles and title, on top of starfield)
        ship_surf = self._ship_anim.get_surface() if self._ship_anim else None
        if ship_surf is not None:
            bob_y = self._ship_y + math.sin(self._ship_bob_phase) * 4
            # Rotate so nose points forward (into the drift direction)
            rotated = pygame.transform.rotate(ship_surf, 135)
            # Dim the ship so it feels ambient, not focal
            rotated.set_alpha(100)
            rect = rotated.get_rect(center=(int(self._ship_x), int(bob_y)))
            screen.blit(rotated, rect)

        # Particles behind title
        self.particles.render(screen)

        # Title glow (blurred duplicate behind)
        title_y = WINDOW_HEIGHT // 4
        glow_alpha = int(80 + 40 * math.sin(self._glow_time * 2))
        glow_surf = self.title_font.render("AURELIA", True, Colors.GLOW_BLUE)
        glow_surf.set_alpha(glow_alpha)
        glow_rect = glow_surf.get_rect(center=(WINDOW_WIDTH // 2, title_y))
        screen.blit(glow_surf, (glow_rect.x - 2, glow_rect.y + 2))

        # Crisp title on top
        title_text = self.title_font.render("AURELIA", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, title_y))
        screen.blit(title_text, title_rect)

        # Subtitle: "A Ledger of Stars"
        subtitle_text = self.subtitle_font.render(
            "A Ledger of Stars", True, Colors.TEXT
        )
        subtitle_rect = subtitle_text.get_rect(center=(WINDOW_WIDTH // 2, title_y + scale_y(55)))
        screen.blit(subtitle_text, subtitle_rect)

        # New game confirmation dialog
        if self._confirm_new_game:
            dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 200))
            screen.blit(dim, (0, 0))

            cx = WINDOW_WIDTH // 2
            cy = WINDOW_HEIGHT // 2

            # Panel — larger, properly centered
            pw, ph = scale_x(480), scale_y(200)
            panel = pygame.Rect(cx - pw // 2, cy - ph // 2, pw, ph)
            panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
            panel_surf.fill((12, 16, 32, 245))
            screen.blit(panel_surf, panel.topleft)
            pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, panel, 2, border_radius=8)

            # Title
            from spacegame.engine.fonts import FONT_BODY, FONT_SM
            warn_font = FontCache.get(FONT_BODY)
            small_font = FontCache.get(FONT_SM)

            line1 = warn_font.render("Start a new game?", True, Colors.TEXT_HIGHLIGHT)
            screen.blit(line1, line1.get_rect(centerx=cx, top=panel.top + scale_y(20)))

            line2 = small_font.render(
                "Your autosave will be overwritten. Manual saves are kept.",
                True, Colors.TEXT_SECONDARY,
            )
            screen.blit(line2, line2.get_rect(centerx=cx, top=panel.top + scale_y(55)))

            # Yes / No buttons — larger, filled backgrounds, clearly clickable
            btn_w, btn_h = scale_x(140), scale_y(44)
            btn_y = panel.top + scale_y(100)
            yes_rect = pygame.Rect(cx - btn_w - scale_x(15), btn_y, btn_w, btn_h)
            no_rect = pygame.Rect(cx + scale_x(15), btn_y, btn_w, btn_h)

            # Yes button — filled green background
            yes_bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            yes_bg.fill((20, 60, 30, 220))
            screen.blit(yes_bg, yes_rect.topleft)
            pygame.draw.rect(screen, Colors.GREEN, yes_rect, 2, border_radius=6)
            yes_text = warn_font.render("Yes (Y)", True, Colors.GREEN)
            screen.blit(yes_text, yes_text.get_rect(center=yes_rect.center))

            # No button — filled red background
            no_bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            no_bg.fill((60, 20, 20, 220))
            screen.blit(no_bg, no_rect.topleft)
            pygame.draw.rect(screen, Colors.RED, no_rect, 2, border_radius=6)
            no_text = warn_font.render("No (N)", True, Colors.RED)
            screen.blit(no_text, no_text.get_rect(center=no_rect.center))

            # Keyboard hint
            hint = small_font.render("Press Y or N  |  Enter to confirm, Escape to cancel", True, Colors.TEXT_SECONDARY)
            screen.blit(hint, hint.get_rect(centerx=cx, top=panel.top + scale_y(155)))

        # Fade-in overlay
        if self._fade_alpha > 0:
            fade_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(int(self._fade_alpha))
            screen.blit(fade_surf, (0, 0))

    def get_next_state(self) -> Optional[Union[GameState, str]]:
        """Return the requested next state."""
        return self.next_state
