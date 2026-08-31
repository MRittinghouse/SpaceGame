"""Full-screen modal that resolves an Act II dilemma collision (A2-8).

Rendered when the dilemma engine detects a fresh collision. The view
paints a dim backdrop over whatever was underneath, drops a centered
panel titled with the telegraph NPC's cue line and per-outcome
narration summaries, and offers one button per eligible pole. There is
no cancel button and no Esc-to-dismiss handler — the collision must be
resolved before play resumes (Spec F: "the world stops signalling and
starts asking").

Compliance: the current pole values arrive as an immutable
``dict[str, int]`` snapshot that ``engine/game.py`` builds via the
model-layer coordinator, so the view never imports or reads the
Act-II investment substrate directly. The compliance scanner for the
substrate module keeps this file clean of that store's tokens.

A2-10 will extend the engine-side resolve callback with the actual
close-lens walk plus ``tier_unlocks`` flag setting. A2-8 ships the
plumbing only: the callback receives the winning pole's lens id.
"""

from __future__ import annotations

from typing import Callable, Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, scale_x, scale_y
from spacegame.engine.fonts import FONT_LG, FONT_SECTION, FONT_SUBTITLE, get_font
from spacegame.models.dilemma import Dilemma, DilemmaOutcome
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView


class DilemmaResolutionView(BaseView):
    """Modal overlay that closes out a dilemma collision.

    Args:
        ui_manager: pygame_gui manager shared with the rest of the game.
        dilemma: The collided dilemma. Its ``outcomes`` list drives the
            button layout — one button per pole (with the D3
            below-threshold pole included when
            ``len(poles) > collision_requires``).
        on_resolve: Callback invoked with the winning pole's lens id
            when the player presses a button. The callback must NOT
            call ``state_manager.pop_state()`` itself; that belongs to
            the engine's frame handler observing ``self.dismissed``,
            matching :class:`spacegame.views.event_notification_view.EventNotificationView`.
        current_investment: Immutable per-pole snapshot the engine
            captures at collision time. The view uses it only to decide
            which buttons to enable — it never renders raw values (Spec
            F: no meters, no counters, never a number).
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        dilemma: Dilemma,
        on_resolve: Callable[[str], None],
        current_investment: dict[str, int],
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.dilemma = dilemma
        self.on_resolve = on_resolve
        # Copy so a caller can safely mutate their snapshot after
        # construction without disturbing the view's eligibility logic.
        self._current_investment: dict[str, int] = dict(current_investment)
        self.dismissed = False

        # Fonts (created once, reused per frame).
        self.title_font = get_font("header", FONT_SECTION)
        self.body_font = get_font("dialogue", FONT_SUBTITLE)
        self.detail_font = get_font("narration", FONT_LG)

        # Per-pole button map. Populated in ``_create_ui``; used by the
        # event handler to identify which pole the player pressed.
        self.pole_buttons: dict[str, pygame_gui.elements.UIButton] = {}

    def on_enter(self) -> None:
        """Activate + build UI. Follows the BaseView contract."""
        super().on_enter()
        logger.info(
            f"DilemmaResolutionView opened for dilemma '{self.dilemma.id}' "
            f"(poles={self.dilemma.poles})"
        )
        self._create_ui()

    def on_exit(self) -> None:
        """Tear down UI and deactivate."""
        self._destroy_ui()
        super().on_exit()

    def _eligible_poles(self) -> list[str]:
        """Return the list of pole ids that should get a button.

        A pole is eligible when either:
        - its investment is at or above ``collision_threshold``, OR
        - ``len(poles) > collision_requires`` (D3 rule: the extra pole
          is offered as an escape valve even when its own investment
          is still below threshold).
        """
        d = self.dilemma
        d3_third_option = len(d.poles) > d.collision_requires
        eligible: list[str] = []
        for pole in d.poles:
            at_threshold = self._current_investment.get(pole, 0) >= d.collision_threshold
            if at_threshold or d3_third_option:
                eligible.append(pole)
        return eligible

    def _outcome_for_pole(self, lens_id: str) -> Optional[DilemmaOutcome]:
        """Return the ``DilemmaOutcome`` whose ``winning_lens_id`` matches."""
        for outcome in self.dilemma.outcomes:
            if outcome.winning_lens_id == lens_id:
                return outcome
        return None

    def _create_ui(self) -> None:
        """Instantiate one button per eligible pole."""
        eligible = self._eligible_poles()

        panel_width = scale_x(700)
        panel_height = scale_y(440)
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        panel_y = (WINDOW_HEIGHT - panel_height) // 2

        button_width = scale_x(200)
        button_height = scale_y(50)
        # Space buttons evenly along a horizontal row near the panel bottom.
        total_button_span = button_width * len(eligible) + scale_x(30) * (len(eligible) - 1)
        start_x = panel_x + (panel_width - total_button_span) // 2
        button_y = panel_y + panel_height - scale_y(70)

        for i, pole in enumerate(eligible):
            outcome = self._outcome_for_pole(pole)
            label = (
                pole.replace("_", " ").title()
                if outcome is None
                else outcome.winning_lens_id.replace("_", " ").title()
            )
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    start_x + i * (button_width + scale_x(30)),
                    button_y,
                    button_width,
                    button_height,
                ),
                text=label.upper(),
                manager=self.ui_manager,
            )
            self.pole_buttons[pole] = btn

    def _destroy_ui(self) -> None:
        """Kill every button and clear the map (per views/CLAUDE.md)."""
        for btn in self.pole_buttons.values():
            btn.kill()
        self.pole_buttons = {}

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route a button press to ``on_resolve`` and mark dismissed."""
        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return
        for pole, btn in self.pole_buttons.items():
            if event.ui_element is btn:
                logger.info(
                    f"DilemmaResolutionView: player resolved '{self.dilemma.id}' "
                    f"in favor of '{pole}'"
                )
                self.on_resolve(pole)
                self.dismissed = True
                return

    def update(self, dt: float) -> None:
        """No animation state to advance; interface method for BaseView."""
        del dt

    def render(self, screen: pygame.Surface) -> None:
        """Draw the dim backdrop, panel, title, and per-outcome text."""
        # Full-screen dim backdrop -- the underlying view is not drawn by
        # StateManager while this modal is on top, so we own the background.
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(210)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Panel.
        panel_width = scale_x(700)
        panel_height = scale_y(440)
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        panel_y = (WINDOW_HEIGHT - panel_height) // 2

        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((*Colors.PANEL, 240))
        screen.blit(panel_surface, (panel_x, panel_y))
        pygame.draw.rect(
            screen,
            Colors.TEXT_PRIMARY,
            pygame.Rect(panel_x, panel_y, panel_width, panel_height),
            2,
        )

        # Title.
        title_surf = self.title_font.render("A CHOICE STANDS", True, Colors.TEXT_PRIMARY)
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, panel_y + scale_y(40)))
        screen.blit(title_surf, title_rect)

        # Per-outcome narration summaries, stacked vertically above the buttons.
        eligible = self._eligible_poles()
        summary_top = panel_y + scale_y(90)
        line_gap = scale_y(60)
        for i, pole in enumerate(eligible):
            outcome = self._outcome_for_pole(pole)
            if outcome is None:
                continue
            label_surf = self.body_font.render(
                outcome.winning_lens_id.replace("_", " ").title(),
                True,
                Colors.TEXT_PRIMARY,
            )
            label_rect = label_surf.get_rect(
                topleft=(panel_x + scale_x(40), summary_top + i * line_gap)
            )
            screen.blit(label_surf, label_rect)
            summary_surf = self.detail_font.render(
                outcome.narration_summary, True, Colors.TEXT_SECONDARY
            )
            summary_rect = summary_surf.get_rect(
                topleft=(panel_x + scale_x(40), summary_top + i * line_gap + scale_y(24))
            )
            screen.blit(summary_surf, summary_rect)

    def is_dismissed(self) -> bool:
        """Match EventNotificationView polling API for the engine frame handler."""
        return self.dismissed
