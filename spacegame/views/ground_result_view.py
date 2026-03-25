"""Ground mission result view.

Post-mission screen displaying outcome (success/extracted/defeated/fled),
mission stats, rewards or penalties, and a continue button. Mirrors the
combat outcome overlay pattern as a standalone view.
"""

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FONT_LG, FONT_MD, FONT_SECTION2, FONT_XL, get_font
from spacegame.models.ground_mission import (
    GHOST_RUN_BONUS_PERCENT,
    GroundMissionResult,
    MissionOutcome,
)
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

# Outcome display mapping
_OUTCOME_TITLES: dict[MissionOutcome, str] = {
    MissionOutcome.SUCCESS: "MISSION COMPLETE",
    MissionOutcome.EXTRACTED: "EXTRACTED",
    MissionOutcome.DEFEATED: "MISSION FAILED",
    MissionOutcome.FLED: "FLED",
}

_OUTCOME_COLORS: dict[MissionOutcome, tuple[int, int, int]] = {
    MissionOutcome.SUCCESS: Colors.GREEN,
    MissionOutcome.EXTRACTED: Colors.YELLOW,
    MissionOutcome.DEFEATED: Colors.RED,
    MissionOutcome.FLED: (255, 140, 40),  # Orange
}


class GroundResultView(BaseView):
    """Post-mission result screen for ground exploration.

    Displays a centered panel with outcome title, mission stats,
    rewards (on success) or penalties (on failure), and a continue
    button to return to the previous game state.
    """

    # Layout constants
    PANEL_W = scale_x(480)
    PANEL_H = scale_y(500)
    PANEL_X = WINDOW_WIDTH // 2 - PANEL_W // 2
    PANEL_Y = WINDOW_HEIGHT // 2 - PANEL_H // 2
    BUTTON_W = scale_x(200)
    BUTTON_H = scale_y(44)

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        result: GroundMissionResult,
        return_state: GameState = GameState.GALAXY_MAP,
    ) -> None:
        """Initialize the result view.

        Args:
            ui_manager: pygame_gui UI manager.
            result: The ground mission result to display.
            return_state: GameState to transition to on continue.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.result = result
        self.return_state = return_state
        self.next_state: Optional[GameState] = None

        # UI element refs
        self.continue_button: Optional[pygame_gui.elements.UIButton] = None

        # Fonts
        self.title_font = get_font("header", FONT_SECTION2)
        self.subtitle_font = get_font("header", FONT_XL)
        self.stat_font = get_font("stats", FONT_LG)
        self.hint_font = get_font("dialogue", FONT_MD)

        # Visual
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=88)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(160)

    def on_enter(self) -> None:
        """Initialize view state and UI elements."""
        super().on_enter()
        logger.info(
            "Entered ground result: %s — %s",
            self.result.config.name,
            self.result.outcome.value,
        )
        self.next_state = None
        self._create_ui()

    def on_exit(self) -> None:
        """Clean up UI elements."""
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create the continue button."""
        btn_x = WINDOW_WIDTH // 2 - self.BUTTON_W // 2
        btn_y = self.PANEL_Y + self.PANEL_H - self.BUTTON_H - 20
        self.continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, btn_y, self.BUTTON_W, self.BUTTON_H),
            text="CONTINUE",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        """Kill all pygame_gui elements."""
        if self.continue_button:
            self.continue_button.kill()
        self.continue_button = None

    def get_next_state(self) -> Optional[GameState]:
        """Return pending state transition."""
        return self.next_state

    def get_outcome_summary(self) -> dict[str, object]:
        """Build outcome summary with title and color.

        Returns:
            Dict with 'title' (str) and 'color' (RGB tuple).
        """
        outcome = self.result.outcome
        return {
            "title": _OUTCOME_TITLES.get(outcome, outcome.value.upper()),
            "color": _OUTCOME_COLORS.get(outcome, Colors.TEXT_PRIMARY),
        }

    def build_stat_lines(self) -> list[tuple[str, tuple[int, int, int]]]:
        """Build the list of stat lines for display.

        Each entry is (text, color). Lines are conditionally included
        based on the outcome and result data.

        Returns:
            List of (text, color) tuples for rendering.
        """
        result = self.result
        config = result.config
        outcome = result.outcome
        lines: list[tuple[str, tuple[int, int, int]]] = []

        # Mission name
        lines.append((f"Mission: {config.name}", Colors.TEXT_PRIMARY))

        # Objectives
        lines.append(
            (
                f"Objectives: {result.objectives_completed}/{result.objectives_total}",
                Colors.TEXT_PRIMARY,
            )
        )

        # Turns taken
        lines.append((f"Turns taken: {result.turns_taken}", Colors.TEXT_PRIMARY))

        # Detection status
        if result.is_ghost_run:
            lines.append(("Detection: Undetected", Colors.TEXT_HIGHLIGHT))
        elif not result.detected:
            lines.append(("Detection: Undetected", Colors.TEXT_SECONDARY))

        # Enemies
        if result.enemies_defeated > 0:
            lines.append((f"Enemies defeated: {result.enemies_defeated}", Colors.TEXT_PRIMARY))
        if result.enemies_talked > 0:
            lines.append((f"Enemies talked past: {result.enemies_talked}", Colors.TEXT_PRIMARY))

        # --- Separator ---
        lines.append(("", Colors.TEXT_PRIMARY))

        # --- Rewards (success) ---
        if outcome == MissionOutcome.SUCCESS:
            if config.rewards.credits > 0:
                lines.append((f"Mission reward: +{config.rewards.credits} CR", Colors.GREEN))
            if result.loot_credits > 0:
                lines.append((f"Credits looted: +{result.loot_credits} CR", Colors.GREEN))
            if config.rewards.xp > 0:
                lines.append((f"XP earned: +{config.rewards.xp}", Colors.TEXT_HIGHLIGHT))
            if result.crew_ids and config.rewards.crew_xp > 0:
                lines.append((f"Crew XP: +{config.rewards.crew_xp}", Colors.TEXT_HIGHLIGHT))
            if result.is_ghost_run:
                bonus = int(config.rewards.credits * GHOST_RUN_BONUS_PERCENT / 100)
                lines.append((f"Ghost run bonus: +{bonus} CR", Colors.TEXT_HIGHLIGHT))

        # --- Extraction (loot kept, no mission reward) ---
        elif outcome == MissionOutcome.EXTRACTED:
            if result.loot_credits > 0:
                lines.append((f"Credits looted: +{result.loot_credits} CR", Colors.GREEN))
            lines.append(("Objectives incomplete — no mission reward", Colors.YELLOW))

        # --- Failure penalties ---
        elif outcome.is_failure:
            penalties = result.calculate_penalties()
            credit_loss = penalties["credit_loss_percent"]
            loot_kept = penalties["loot_kept_percent"]

            lines.append((f"Credits lost: {credit_loss}%", Colors.RED))

            if loot_kept == 0:
                lines.append(("Loot: All lost", Colors.RED))
            elif loot_kept < 100:
                lines.append((f"Loot: {loot_kept}% kept", Colors.YELLOW))
            else:
                lines.append(("Loot: Kept", Colors.GREEN))

            if penalties["xp_penalty"] > 0:
                lines.append((f"XP penalty: -{penalties['xp_penalty']}", Colors.RED))

        return lines

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle button presses and keyboard input."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.next_state = self.return_state
                return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.continue_button:
                self.next_state = self.return_state
                return

    def update(self, dt: float) -> None:
        """Update background animation."""
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """Render the result screen."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Panel background
        panel_rect = pygame.Rect(self.PANEL_X, self.PANEL_Y, self.PANEL_W, self.PANEL_H)
        summary = self.get_outcome_summary()
        panel_bg = pygame.Surface((self.PANEL_W, self.PANEL_H), pygame.SRCALPHA)
        panel_bg.fill((12, 16, 32, 240))
        screen.blit(panel_bg, (self.PANEL_X, self.PANEL_Y))
        pygame.draw.rect(screen, summary["color"], panel_rect, 2, border_radius=6)

        # Title
        title_surf = self.title_font.render(str(summary["title"]), True, summary["color"])
        title_rect = title_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=self.PANEL_Y + 20)
        screen.blit(title_surf, title_rect)

        # Separator
        sep_y = self.PANEL_Y + 70
        pygame.draw.line(
            screen,
            Colors.UI_BORDER,
            (self.PANEL_X + 20, sep_y),
            (self.PANEL_X + self.PANEL_W - 20, sep_y),
        )

        # Stat lines
        stat_x = self.PANEL_X + scale_x(30)
        stat_y = sep_y + scale_y(16)
        line_height = scale_y(26)

        for text, color in self.build_stat_lines():
            if text:  # Skip empty separator lines (add spacing)
                surf = self.stat_font.render(text, True, color)
                screen.blit(surf, (stat_x, stat_y))
            stat_y += line_height

        # Continue hint
        hint_y = self.PANEL_Y + self.PANEL_H - 64
        hint_surf = self.hint_font.render(
            "Press ENTER or click Continue", True, Colors.TEXT_SECONDARY
        )
        hint_rect = hint_surf.get_rect(centerx=WINDOW_WIDTH // 2, top=hint_y)
        screen.blit(hint_surf, hint_rect)
