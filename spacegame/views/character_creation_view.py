"""
Character creation view for attribute allocation.

Shown once after name input during new game setup. Player distributes
5 attribute points across the 5 character attributes.
"""

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import (
    FONT_DISPLAY,
    FONT_LG,
    FONT_MD,
    FONT_TITLE,
    FONT_XL,
    FONT_XL2,
    get_font,
)
from spacegame.models.attributes import (
    ATTRIBUTE_DEFINITIONS,
    AttributeId,
    AttributeSheet,
)
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView


class CharacterCreationView(BaseView):
    """Attribute allocation screen for new game character creation."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        attribute_sheet: AttributeSheet,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.attribute_sheet = attribute_sheet
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = get_font("header", FONT_DISPLAY)
        self.subtitle_font = get_font("dialogue", FONT_LG)
        self.attr_font = get_font("header", FONT_XL)
        self.desc_font = get_font("dialogue", FONT_MD)
        self.value_font = get_font("stats", FONT_TITLE)
        self.points_font = get_font("stats", FONT_XL2)

        # UI elements
        self.plus_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self.minus_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self.confirm_button: Optional[pygame_gui.elements.UIButton] = None

        # Visual
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=42)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered character creation view")
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        cx = WINDOW_WIDTH // 2
        start_y = scale_y(230)
        row_height = scale_y(75)

        for i, attr in enumerate(AttributeId):
            y = start_y + i * row_height

            # Minus button
            self.minus_buttons[attr.value] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    cx + scale_x(160), y + scale_y(8), scale_x(36), scale_y(36)
                ),
                text="-",
                manager=self.ui_manager,
            )

            # Plus button
            self.plus_buttons[attr.value] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    cx + scale_x(260), y + scale_y(8), scale_x(36), scale_y(36)
                ),
                text="+",
                manager=self.ui_manager,
            )

        # Confirm button
        btn_width = scale_x(220)
        self.confirm_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                cx - btn_width // 2, start_y + 5 * row_height + scale_y(30), btn_width, scale_y(45)
            ),
            text="CONFIRM & BEGIN",
            manager=self.ui_manager,
        )

        self._update_button_states()

    def _destroy_ui(self) -> None:
        for btn in self.plus_buttons.values():
            btn.kill()
        for btn in self.minus_buttons.values():
            btn.kill()
        if self.confirm_button:
            self.confirm_button.kill()
        self.plus_buttons.clear()
        self.minus_buttons.clear()
        self.confirm_button = None

    def _update_button_states(self) -> None:
        has_points = self.attribute_sheet.unspent_points > 0

        for attr in AttributeId:
            plus_btn = self.plus_buttons.get(attr.value)
            minus_btn = self.minus_buttons.get(attr.value)
            val = self.attribute_sheet.get_value(attr.value)

            if plus_btn:
                if has_points and val < 10:
                    plus_btn.enable()
                else:
                    plus_btn.disable()

            if minus_btn:
                if val > 1:
                    minus_btn.enable()
                else:
                    minus_btn.disable()

        if self.confirm_button:
            if self.attribute_sheet.unspent_points == 0:
                self.confirm_button.enable()
            else:
                self.confirm_button.disable()

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            # Check plus buttons
            for attr_id, btn in self.plus_buttons.items():
                if event.ui_element == btn:
                    self.attribute_sheet.allocate_point(attr_id)
                    self._update_button_states()
                    return

            # Check minus buttons
            for attr_id, btn in self.minus_buttons.items():
                if event.ui_element == btn:
                    self.attribute_sheet.deallocate_point(attr_id)
                    self._update_button_states()
                    return

            # Confirm button
            if event.ui_element == self.confirm_button:
                if self.attribute_sheet.unspent_points == 0:
                    logger.info(
                        f"Character creation confirmed: {self.attribute_sheet.get_all_values()}"
                    )
                    self.next_state = GameState.GALAXY_MAP

    def update(self, dt: float) -> None:
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        cx = WINDOW_WIDTH // 2

        # Title
        title_surf = self.title_font.render("ALLOCATE ATTRIBUTES", True, Colors.ATTR_HIGHLIGHT)
        screen.blit(title_surf, title_surf.get_rect(center=(cx, scale_y(100))))

        # Subtitle
        sub_surf = self.subtitle_font.render(
            "Distribute 5 points across your attributes. Each starts at 1.",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(sub_surf, sub_surf.get_rect(center=(cx, scale_y(145))))

        # Points remaining
        pts = self.attribute_sheet.unspent_points
        pts_color = Colors.YELLOW if pts > 0 else Colors.SUCCESS
        pts_surf = self.points_font.render(f"Points Remaining: {pts}", True, pts_color)
        screen.blit(pts_surf, pts_surf.get_rect(center=(cx, scale_y(185))))

        # Attribute rows
        start_y = scale_y(230)
        row_height = scale_y(75)  # Taller rows for wrapped descriptions

        for i, attr in enumerate(AttributeId):
            y = start_y + i * row_height
            defn = ATTRIBUTE_DEFINITIONS[attr.value]
            val = self.attribute_sheet.get_value(attr.value)

            # Attribute name (left-aligned)
            text_x = cx - scale_x(280)
            name_surf = self.attr_font.render(defn["name"], True, Colors.TEXT_HIGHLIGHT)
            screen.blit(name_surf, (text_x, y))

            # Description — word-wrapped to fit before the buttons
            max_desc_w = scale_x(380)  # Stop before minus button at cx+150
            desc_text = defn["description"]
            desc_y = y + scale_y(22)

            # Simple word wrap
            words = desc_text.split()
            lines: list[str] = []
            current_line = ""
            for word in words:
                test = f"{current_line} {word}".strip()
                if self.desc_font.size(test)[0] <= max_desc_w:
                    current_line = test
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            for line_idx, line in enumerate(lines[:2]):  # Max 2 lines
                line_surf = self.desc_font.render(line, True, Colors.TEXT_SECONDARY)
                screen.blit(line_surf, (text_x, desc_y + line_idx * scale_y(16)))

            # Value (centered between minus and plus buttons)
            val_surf = self.value_font.render(str(val), True, Colors.TEXT)
            val_rect = val_surf.get_rect(center=(cx + scale_x(218), y + scale_y(24)))
            screen.blit(val_surf, val_rect)

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
