"""
Statistics display view.

Shows all tracked player stats organized by category.
"""

import pygame
import pygame_gui
from typing import Optional

from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.player import Player
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FontCache


class StatisticsView(BaseView):
    """Full-screen statistics display with categorized player stats."""

    def __init__(self, ui_manager: pygame_gui.UIManager, player: Player):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = FontCache.get(40)
        self.category_font = FontCache.get(28)
        self.stat_font = FontCache.get(22)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=55)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Opened statistics view")
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

    def update(self, dt: float) -> None:
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title = self.title_font.render("STATISTICS", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 40))
        screen.blit(title, title_rect)

        stats = self.player.get_statistics()
        col_width = 380
        col1_x = 80
        col2_x = 80 + col_width + 60
        col3_x = 80 + (col_width + 60) * 2

        y = 80
        line_h = 24

        # Column 1: Economic
        y = self._render_category(
            screen,
            "ECONOMIC",
            col1_x,
            y,
            line_h,
            [
                ("Credits", f"{stats['credits']:,} CR"),
                ("Net Worth", f"{stats['net_worth']:,} CR"),
                ("Lifetime Earned", f"{stats['credits_earned_lifetime']:,} CR"),
                ("Lifetime Spent", f"{stats['credits_spent_lifetime']:,} CR"),
                ("Best Single Sale", f"{stats['largest_single_profit']:,} CR"),
                ("Trades Completed", str(stats["trades"])),
            ],
        )

        # Column 1: Exploration (below Economic)
        y += 15
        self._render_category(
            screen,
            "EXPLORATION",
            col1_x,
            y,
            line_h,
            [
                ("Systems Visited", f"{stats['systems_visited']}"),
                ("Jumps Traveled", f"{stats['jumps_traveled']}"),
                ("Fuel Consumed", f"{stats['fuel_consumed']}"),
                ("Current Day", f"Day {stats['day']}"),
            ],
        )

        # Column 2: Activities
        y2 = 80
        y2 = self._render_category(
            screen,
            "ACTIVITIES",
            col2_x,
            y2,
            line_h,
            [
                ("Ore Mined", f"{stats['ore_mined']}"),
                ("Items Salvaged", f"{stats['items_salvaged']}"),
                ("Items Refined", f"{stats['items_refined']}"),
            ],
        )

        # Column 2: Progression
        y2 += 15
        self._render_category(
            screen,
            "PROGRESSION",
            col2_x,
            y2,
            line_h,
            [
                ("Level", f"{stats['level']}"),
                ("XP", f"{stats['xp']}"),
                ("Skill Points Spent", f"{stats['skill_points_spent']}"),
                ("Ship", stats["ship"]),
                ("Location", stats["location"]),
            ],
        )

        # Column 3: Personal Records
        y3 = 80
        records = []
        if stats.get("best_trade_profit", 0) > 0:
            records.append(("Best Trade Profit", f"{stats['best_trade_profit']:,} CR"))
        if stats.get("max_credits_held", 0) > 0:
            records.append(("Peak Credits Held", f"{stats['max_credits_held']:,} CR"))
        if stats.get("best_mining_session_ore", 0) > 0:
            records.append(("Best Mining Haul", f"{stats['best_mining_session_ore']} ore"))
        if stats.get("best_mining_depth", 0) > 0:
            records.append(("Deepest Mine", f"Depth {stats['best_mining_depth']}"))
        if stats.get("best_salvage_haul", 0) > 0:
            records.append(("Best Salvage Haul", f"{stats['best_salvage_haul']} items"))
        if stats.get("best_refining_output", 0) > 0:
            records.append(("Best Forge Session", f"{stats['best_refining_output']} output"))
        records.append(("S-Rank Sessions", str(self.player.s_ranks_earned)))

        if records:
            self._render_category(
                screen,
                "PERSONAL RECORDS",
                col3_x,
                y3,
                line_h,
                records,
            )

    def _render_category(
        self,
        screen: pygame.Surface,
        title: str,
        x: int,
        y: int,
        line_h: int,
        items: list[tuple[str, str]],
    ) -> int:
        """Render a stat category with title and items. Returns next Y position."""
        cat_surf = self.category_font.render(title, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(cat_surf, (x, y))
        y += line_h + 8

        # Underline
        pygame.draw.line(screen, Colors.UI_BORDER, (x, y - 4), (x + 300, y - 4), 1)

        for label, value in items:
            label_surf = self.stat_font.render(f"{label}:", True, Colors.TEXT_SECONDARY)
            value_surf = self.stat_font.render(value, True, Colors.TEXT_PRIMARY)
            screen.blit(label_surf, (x + 10, y))
            screen.blit(value_surf, (x + 200, y))
            y += line_h

        return y

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
