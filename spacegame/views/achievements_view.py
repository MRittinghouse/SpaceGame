"""
Achievements display view.

Shows all achievements with locked/unlocked state and progress bars.
"""

import pygame
import pygame_gui
from typing import Optional

from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.player import Player
from spacegame.achievement_manager import AchievementManager
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground


class AchievementsView(BaseView):
    """Full-screen achievements display with progress tracking."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        achievement_manager: AchievementManager,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.achievement_manager = achievement_manager
        self.next_state: Optional[GameState] = None

        # Scroll offset for scrolling achievement list
        self.scroll_offset = 0

        # Fonts
        self.title_font = pygame.font.Font(None, 40)
        self.name_font = pygame.font.Font(None, 26)
        self.desc_font = pygame.font.Font(None, 20)
        self.progress_font = pygame.font.Font(None, 18)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=77)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Opened achievements view")
        self.scroll_offset = 0
        self._create_ui()

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20, WINDOW_HEIGHT - 60, 150, 40),
            text="BACK",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        if self.back_button:
            self.back_button.kill()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll_offset = max(0, self.scroll_offset - event.y * 30)

    def update(self, dt: float) -> None:
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title = self.title_font.render("ACHIEVEMENTS", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 40))
        screen.blit(title, title_rect)

        # Summary
        all_achievements = self.achievement_manager.get_all_achievements()
        unlocked_ids = set(self.achievement_manager.get_unlocked(self.player))
        unlocked_count = len(unlocked_ids)
        total_count = len(all_achievements)

        summary = self.desc_font.render(
            f"Unlocked: {unlocked_count}/{total_count}",
            True,
            Colors.TEXT_SECONDARY,
        )
        summary_rect = summary.get_rect(center=(WINDOW_WIDTH // 2, 65))
        screen.blit(summary, summary_rect)

        # Achievement cards
        card_width = 550
        card_height = 70
        card_x = (WINDOW_WIDTH - card_width) // 2
        start_y = 90 - self.scroll_offset
        spacing = 8

        for i, achievement in enumerate(all_achievements):
            y = start_y + i * (card_height + spacing)

            # Skip if off-screen
            if y + card_height < 80 or y > WINDOW_HEIGHT - 70:
                continue

            is_unlocked = achievement.id in unlocked_ids
            progress = self.achievement_manager.get_progress(self.player, achievement.id)

            self._render_achievement_card(
                screen,
                achievement,
                is_unlocked,
                progress,
                card_x,
                y,
                card_width,
                card_height,
            )

    def _render_achievement_card(
        self,
        screen: pygame.Surface,
        achievement,
        is_unlocked: bool,
        progress: float,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Render a single achievement card."""
        # Card background
        card_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        if is_unlocked:
            card_surf.fill((25, 35, 20, 200))  # Green tint
        else:
            card_surf.fill((20, 20, 30, 200))  # Gray
        screen.blit(card_surf, (x, y))

        # Border
        border_color = Colors.GREEN if is_unlocked else Colors.UI_BORDER
        pygame.draw.rect(screen, border_color, (x, y, width, height), 1)

        # Name
        if achievement.hidden and not is_unlocked:
            name_text = "???"
            desc_text = "Hidden achievement"
        else:
            name_text = achievement.name
            desc_text = achievement.description

        name_color = Colors.GREEN if is_unlocked else Colors.TEXT_PRIMARY
        name_surf = self.name_font.render(name_text, True, name_color)
        screen.blit(name_surf, (x + 10, y + 8))

        # Description
        desc_surf = self.desc_font.render(desc_text, True, Colors.TEXT_SECONDARY)
        screen.blit(desc_surf, (x + 10, y + 32))

        # Progress bar (for incomplete achievements)
        if not is_unlocked and not (achievement.hidden and progress == 0):
            bar_x = x + 10
            bar_y = y + height - 16
            bar_w = width - 120
            bar_h = 8
            pygame.draw.rect(screen, (30, 30, 45), (bar_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * progress)
            pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, (bar_x, bar_y, fill_w, bar_h))
            pygame.draw.rect(screen, Colors.UI_BORDER, (bar_x, bar_y, bar_w, bar_h), 1)

            # Progress text
            pct_text = f"{int(progress * 100)}%"
            pct_surf = self.progress_font.render(pct_text, True, Colors.TEXT_SECONDARY)
            screen.blit(pct_surf, (bar_x + bar_w + 5, bar_y - 2))

        # Reward info (right side)
        reward_text = self._reward_text(achievement)
        reward_color = Colors.GREEN if is_unlocked else Colors.TEXT_SECONDARY
        reward_surf = self.progress_font.render(reward_text, True, reward_color)
        screen.blit(reward_surf, (x + width - 100, y + 10))

        # Checkmark for unlocked
        if is_unlocked:
            check_surf = self.name_font.render("OK", True, Colors.GREEN)
            screen.blit(check_surf, (x + width - 40, y + 35))

    def _reward_text(self, achievement) -> str:
        """Get display text for an achievement's reward."""
        if achievement.reward_type == "xp":
            return f"+{achievement.reward_value} XP"
        elif achievement.reward_type == "credits":
            return f"+{achievement.reward_value:,} CR"
        elif achievement.reward_type == "skill_point":
            return f"+{achievement.reward_value} SP"
        elif achievement.reward_type == "upgrade":
            return "Upgrade"
        return ""

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
