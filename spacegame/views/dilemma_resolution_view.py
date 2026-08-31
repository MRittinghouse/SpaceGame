"""Modal overlay pushed when a dilemma collides (A2-8).

The player picks a pole; the engine pops the modal and records the
outcome. The view is deliberately spartan — this sprint ships plumbing,
not authored narration. A2-10 extends the resolve callback with the
close-lens walk plus ``tier_unlocks`` flag setting; A2-11 (Scars) will
skin refusing-NPC surfaces on top.

Constructor takes ``current_investment: dict[str, int]`` (a snapshot the
engine builds via :func:`spacegame.models.dilemma.build_investment_snapshot`
so the view file never reads the investment store directly. The
compliance guard under ``tests/test_compliance/`` forbids the store
token here (see the guard file for the exact rule).

Button eligibility:
  - Any pole at or above ``dilemma.collision_threshold`` (per the
    snapshot) always gets a button.
  - Any pole below threshold ALSO gets a button when the dilemma is
    genuinely "pick one of three" — i.e. ``len(poles) >
    collision_requires``. That is the D3 (three-pole triangle) case: two
    poles fire hot together, the third stays cold, but the player still
    has the option to reconcile the choice by falling back to the cold
    pole. Pair dilemmas (``collision_requires == len(poles)``) only
    surface buttons for poles that actually crossed collision.

The modal has no cancel button and no Esc handler. Once the collision
fires, the player must pick — that is the design commitment behind
"the world forces the trade."
"""

from __future__ import annotations

import math
from typing import Callable, Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, scale_x, scale_y
from spacegame.engine.fonts import FONT_LG, FONT_SECTION, FONT_SUBTITLE, get_font
from spacegame.models.dilemma import Dilemma
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView


class DilemmaResolutionView(BaseView):
    """Full-screen dim + centered panel with one button per eligible pole."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        dilemma: Dilemma,
        on_resolve: Callable[[str], None],
        current_investment: dict[str, int],
    ) -> None:
        """Initialize the resolution view.

        Args:
            ui_manager: The pygame_gui UIManager to attach buttons to.
            dilemma: The dilemma being resolved.
            on_resolve: Callback invoked with the winning ``lens_id``
                when the player presses a pole button. The engine
                installs a callback that writes
                ``player.dilemma_state.resolved[dilemma.id] = lens_id``
                and sets the ``flags.dilemma_resolved(id)`` flag.
            current_investment: Snapshot of ``{pole_id: investment}``
                built by :func:`spacegame.models.dilemma.build_investment_snapshot`.
                The view never reads investment through any other path.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.dilemma = dilemma
        self.on_resolve = on_resolve
        self.current_investment = dict(current_investment)
        self.dismissed = False

        self.title_font = get_font("header", FONT_SECTION)
        self.body_font = get_font("dialogue", FONT_SUBTITLE)
        self.detail_font = get_font("narration", FONT_LG)

        self.pole_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._pulse_time = 0.0

    def on_enter(self) -> None:
        super().on_enter()
        logger.info(
            f"Dilemma resolution modal: dilemma_id={self.dilemma.id!r} poles={self.dilemma.poles!r}"
        )
        self._create_ui()

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()

    def _eligible_poles(self) -> list[str]:
        """Return the poles that should get a button.

        See module docstring for the D3 rule.
        """
        collision_threshold = self.dilemma.collision_threshold
        allow_below_threshold = len(self.dilemma.poles) > self.dilemma.collision_requires
        eligible: list[str] = []
        for pole in self.dilemma.poles:
            at_threshold = self.current_investment.get(pole, 0) >= collision_threshold
            if at_threshold or allow_below_threshold:
                eligible.append(pole)
        return eligible

    def _create_ui(self) -> None:
        eligible = self._eligible_poles()
        if not eligible:
            return

        panel_bottom = (WINDOW_HEIGHT + scale_y(320)) // 2

        button_width = scale_x(200)
        button_height = scale_y(46)
        spacing = scale_x(20)
        total_width = len(eligible) * button_width + (len(eligible) - 1) * spacing
        start_x = (WINDOW_WIDTH - total_width) // 2
        button_y = panel_bottom - button_height - scale_y(24)

        for i, pole_id in enumerate(eligible):
            button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    start_x + i * (button_width + spacing),
                    button_y,
                    button_width,
                    button_height,
                ),
                text=pole_id.replace("_", " ").upper(),
                manager=self.ui_manager,
            )
            self.pole_buttons[pole_id] = button

    def _destroy_ui(self) -> None:
        for btn in self.pole_buttons.values():
            btn.kill()
        self.pole_buttons.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return
        for pole_id, button in self.pole_buttons.items():
            if event.ui_element is button:
                logger.info(
                    f"Dilemma resolved: dilemma_id={self.dilemma.id!r} chosen_lens={pole_id!r}"
                )
                self.dismissed = True
                self.on_resolve(pole_id)
                return

    def update(self, dt: float) -> None:
        self._pulse_time += dt

    def render(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(210)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        panel_width = scale_x(560)
        panel_height = scale_y(320)
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        panel_y = (WINDOW_HEIGHT - panel_height) // 2

        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((*Colors.PANEL, 240))
        screen.blit(panel_surface, (panel_x, panel_y))

        pulse_alpha = int(140 + 80 * math.sin(self._pulse_time * 3))
        pulse_color = (*Colors.TEXT_HIGHLIGHT, max(0, min(255, pulse_alpha)))
        pulse_surf = pygame.Surface((panel_width + 4, panel_height + 4), pygame.SRCALPHA)
        pygame.draw.rect(pulse_surf, pulse_color, pulse_surf.get_rect(), 3)
        screen.blit(pulse_surf, (panel_x - 2, panel_y - 2))
        pygame.draw.rect(
            screen,
            Colors.TEXT_HIGHLIGHT,
            pygame.Rect(panel_x, panel_y, panel_width, panel_height),
            2,
        )

        title = self.title_font.render("A CHOICE ARRIVES", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + scale_y(40)))
        screen.blit(title, title_rect)

        prompt = self.body_font.render(
            "Two paths crossed thresholds. Pick one.",
            True,
            Colors.TEXT_PRIMARY,
        )
        prompt_rect = prompt.get_rect(center=(WINDOW_WIDTH // 2, panel_y + scale_y(90)))
        screen.blit(prompt, prompt_rect)

        detail = self.detail_font.render(
            "The path you set aside stays set aside.",
            True,
            Colors.TEXT_SECONDARY,
        )
        detail_rect = detail.get_rect(center=(WINDOW_WIDTH // 2, panel_y + scale_y(140)))
        screen.blit(detail, detail_rect)

    def is_dismissed(self) -> bool:
        return self.dismissed

    def get_next_state(self) -> Optional[str]:
        """Modal state — the engine drives transitions, not the view."""
        return None
