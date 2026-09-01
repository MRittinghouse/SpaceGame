"""Modal overlay pushed when a capstone fires (A2-20).

The player reads the moment and acknowledges. The engine pops the modal
and records the capstone as reached. Play continues — the session does not
end. This view is deliberately spartan; it ships plumbing and a placeholder
narration, not authored cutscene content.

Placeholder narration note: the ``_TEMPLATE`` constant below is generated
text proving that the format works before any authored cutscenes exist. When
a future authored-content sprint (A2-21 or a dedicated cutscene sprint)
ships bespoke narration, replace ``_TEMPLATE`` with per-lens authored copy
and the ``_render_narration`` call with the authored lookup. The placeholder
is intentional and documented — do not add authored content here.

Config imports: this file uses ``import spacegame.config as config`` and
reads ``config.WINDOW_WIDTH`` / ``config.WINDOW_HEIGHT`` at call time inside
methods. It does NOT ``from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT``
because the module-level dim-capture compliance guard
(``tests/test_ui_layout/test_module_level_dim_capture.py``) fails when the
count of offending views exceeds the 27-baseline (A2-20 Locked decision 12).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

import pygame
import pygame_gui

import spacegame.config as config
from spacegame.config import Colors, scale_x, scale_y
from spacegame.engine.fonts import FONT_LG, FONT_SECTION, FONT_SUBTITLE, get_font
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

if TYPE_CHECKING:
    from spacegame.models.capstone import Capstone
    from spacegame.models.lens import Lens

# Placeholder narration template. Substituted at display time with the
# loaded Lens.name and Lens.core_fantasy. This is not authored content —
# it proves the plumbing works before A2-21 or a future cutscene sprint
# ships bespoke narration per lens.
_TEMPLATE = (
    "You have reached the {lens_name} capstone. This is who you have chosen"
    " to be: {core_fantasy}. Play continues."
)


class CapstoneView(BaseView):
    """Full-screen dim + centered panel with a single Continue button."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        capstone: "Capstone",
        lens: "Lens",
        on_acknowledge: Callable[[], None],
    ) -> None:
        """Initialize the capstone modal.

        Args:
            ui_manager: The pygame_gui UIManager to attach buttons to.
            capstone: The capstone record being shown.
            lens: The loaded Lens record for ``capstone.lens_id``; the engine
                passes it in so the view never reads DataLoader directly.
            on_acknowledge: Callback invoked when the player presses Continue.
                The engine records the capstone in ``player.capstones_reached``
                and pops the state.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.capstone = capstone
        self.lens = lens
        self.on_acknowledge = on_acknowledge
        self.dismissed = False

        self.title_font = get_font("header", FONT_SECTION)
        self.body_font = get_font("dialogue", FONT_SUBTITLE)
        self.detail_font = get_font("narration", FONT_LG)

        self._continue_button: Optional[pygame_gui.elements.UIButton] = None

    def on_enter(self) -> None:
        super().on_enter()
        logger.info(
            f"Capstone modal: capstone_id={self.capstone.capstone_id!r} "
            f"lens_id={self.capstone.lens_id!r}"
        )
        self._create_ui()

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        w = config.WINDOW_WIDTH
        h = config.WINDOW_HEIGHT
        panel_height = scale_y(260)
        button_height = scale_y(46)
        button_width = scale_x(200)

        panel_bottom = (h + panel_height) // 2
        button_y = panel_bottom - button_height - scale_y(24)
        button_x = (w - button_width) // 2

        self._continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(button_x, button_y, button_width, button_height),
            text="CONTINUE",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        if self._continue_button is not None:
            self._continue_button.kill()
            self._continue_button = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return
        if event.ui_element is self._continue_button:
            logger.info(f"Capstone acknowledged: capstone_id={self.capstone.capstone_id!r}")
            self.dismissed = True
            self.on_acknowledge()

    def update(self, dt: float) -> None:
        pass

    def render(self, screen: pygame.Surface) -> None:
        w = config.WINDOW_WIDTH
        h = config.WINDOW_HEIGHT

        overlay = pygame.Surface((w, h))
        overlay.set_alpha(210)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        panel_width = scale_x(560)
        panel_height = scale_y(260)
        panel_x = (w - panel_width) // 2
        panel_y = (h - panel_height) // 2

        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((*Colors.PANEL, 240))
        screen.blit(panel_surface, (panel_x, panel_y))

        pygame.draw.rect(
            screen,
            Colors.TEXT_HIGHLIGHT,
            pygame.Rect(panel_x, panel_y, panel_width, panel_height),
            2,
        )

        title = self.title_font.render("A MOMENT ARRIVES", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(w // 2, panel_y + scale_y(40)))
        screen.blit(title, title_rect)

        core = self.lens.core_fantasy.rstrip(".")
        narration_text = _TEMPLATE.format(
            lens_name=self.lens.name,
            core_fantasy=core.lower(),
        )
        body = self.body_font.render(narration_text, True, Colors.TEXT_PRIMARY)
        body_rect = body.get_rect(center=(w // 2, panel_y + scale_y(110)))
        screen.blit(body, body_rect)

    def is_dismissed(self) -> bool:
        """Return True if the player has acknowledged this capstone."""
        return self.dismissed

    def get_next_state(self) -> Optional[str]:
        """Modal state — the engine drives transitions, not the view."""
        return None
