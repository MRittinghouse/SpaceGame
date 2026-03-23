"""Encounter view for non-hostile random encounters.

Presents a narrative description with player choices, shows outcome text
and rewards, then transitions back to the galaxy map or into combat.
"""

from __future__ import annotations

import copy
from enum import Enum
from typing import Optional

import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UITextBox

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState, scale_x, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterDefinition,
    EncounterOutcome,
    EncounterRef,
)
from spacegame.models.mission import MissionReward
from spacegame.engine.draw_utils import draw_panel
from spacegame.utils.logger import logger
from spacegame.engine.fonts import FONT_BODY, FONT_LG, FONT_TITLE, FontCache
from spacegame.views.base_view import BaseView


class EncounterPhase(str, Enum):
    """State machine phases for the encounter view."""

    CHOOSING = "choosing"
    OUTCOME = "outcome"
    DONE = "done"


# Layout constants — proportional to resolution
_PANEL_W = scale_x(700)
_PANEL_H = scale_y(500)
_PANEL_X = (WINDOW_WIDTH - _PANEL_W) // 2
_PANEL_Y = (WINDOW_HEIGHT - _PANEL_H) // 2
_INNER_PAD = scale_x(24)
_BUTTON_H = scale_y(40)
_BUTTON_GAP = scale_y(12)


class EncounterView(BaseView):
    """View for non-hostile encounter interactions.

    Presents encounter description, player choices, and outcome text
    using a phase-based state machine.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        encounter_def: EncounterDefinition,
        encounter_ref: EncounterRef,
    ) -> None:
        super().__init__(ui_manager)
        self.encounter_def = encounter_def
        self.encounter_ref = encounter_ref
        self.next_state: Optional[GameState] = None

        # Phase state
        self.phase = EncounterPhase.CHOOSING
        self.chosen_outcome: Optional[EncounterOutcome] = None
        self.pending_combat: bool = False

        # Fonts
        self.title_font = FontCache.get(FONT_TITLE)
        self.body_font = FontCache.get(FONT_BODY)
        self.reward_font = FontCache.get(FONT_LG)

        # Background
        self.background = AnimatedBackground(
            "deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=encounter_ref.encounter_seed
        )
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

        # Template substitution for shakedown encounters
        subs = {"shakedown_demand": str(encounter_ref.shakedown_demand)}
        self.display_description = encounter_def.description.format_map(
            _SafeFormatMap(subs)
        )
        self.display_choices = _substitute_choices(encounter_def.choices, subs)

        # UI element refs (created in _create_ui)
        self.choice_buttons: list[UIButton] = []
        self.continue_button: Optional[UIButton] = None
        self.description_box: Optional[UITextBox] = None
        self.outcome_box: Optional[UITextBox] = None

    def on_enter(self) -> None:
        """Initialize encounter UI."""
        super().on_enter()
        logger.info(f"Entering encounter: {self.encounter_def.name}")
        self._create_ui()

    def on_exit(self) -> None:
        """Clean up UI."""
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create UI elements for the current phase."""
        self._destroy_ui()

        if self.phase == EncounterPhase.CHOOSING:
            self._create_choosing_ui()
        elif self.phase == EncounterPhase.OUTCOME:
            self._create_outcome_ui()

    def _create_choosing_ui(self) -> None:
        """Create choice buttons for the CHOOSING phase."""
        # Description text box
        desc_rect = pygame.Rect(
            _PANEL_X + _INNER_PAD,
            _PANEL_Y + 60,
            _PANEL_W - _INNER_PAD * 2,
            140,
        )
        self.description_box = UITextBox(
            html_text=self.display_description,
            relative_rect=desc_rect,
            manager=self.ui_manager,
        )

        # Choice buttons
        button_y = _PANEL_Y + 220
        button_w = _PANEL_W - _INNER_PAD * 2
        self.choice_buttons = []
        for i, choice in enumerate(self.display_choices):
            btn_rect = pygame.Rect(
                _PANEL_X + _INNER_PAD,
                button_y + i * (_BUTTON_H + _BUTTON_GAP),
                button_w,
                _BUTTON_H,
            )
            btn = UIButton(
                relative_rect=btn_rect,
                text=f"{i + 1}. {choice.label}",
                manager=self.ui_manager,
                tool_tip_text=choice.description,
            )
            self.choice_buttons.append(btn)

    def _create_outcome_ui(self) -> None:
        """Create outcome display for the OUTCOME phase."""
        if not self.chosen_outcome:
            return

        # Outcome text box
        desc_rect = pygame.Rect(
            _PANEL_X + _INNER_PAD,
            _PANEL_Y + 60,
            _PANEL_W - _INNER_PAD * 2,
            200,
        )
        self.outcome_box = UITextBox(
            html_text=self.chosen_outcome.description,
            relative_rect=desc_rect,
            manager=self.ui_manager,
        )

        # Continue button
        btn_rect = pygame.Rect(
            _PANEL_X + _PANEL_W // 2 - 100,
            _PANEL_Y + _PANEL_H - 70,
            200,
            _BUTTON_H,
        )
        self.continue_button = UIButton(
            relative_rect=btn_rect,
            text="Continue (Enter)",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        """Kill all UI elements."""
        for btn in self.choice_buttons:
            btn.kill()
        self.choice_buttons = []
        if self.continue_button:
            self.continue_button.kill()
            self.continue_button = None
        if self.description_box:
            self.description_box.kill()
            self.description_box = None
        if self.outcome_box:
            self.outcome_box.kill()
            self.outcome_box = None

    def update(self, dt: float) -> None:
        """Update background animation."""
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """Render encounter panel."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Panel background
        panel_rect = pygame.Rect(_PANEL_X, _PANEL_Y, _PANEL_W, _PANEL_H)
        color = self.encounter_def.icon_color
        draw_panel(
            screen, panel_rect, alpha=255, bg_color=(20, 20, 30),
            border_color=color, border_radius=8,
        )

        # Title
        title_surf = self.title_font.render(
            self.encounter_def.name, True, color
        )
        title_x = _PANEL_X + (_PANEL_W - title_surf.get_width()) // 2
        screen.blit(title_surf, (title_x, _PANEL_Y + 16))

        # Horizontal rule
        rule_y = _PANEL_Y + 50
        pygame.draw.line(
            screen, (60, 60, 80),
            (_PANEL_X + _INNER_PAD, rule_y),
            (_PANEL_X + _PANEL_W - _INNER_PAD, rule_y),
        )

        # Phase-specific rendering
        if self.phase == EncounterPhase.OUTCOME and self.chosen_outcome:
            self._render_rewards(screen)

    def _render_rewards(self, screen: pygame.Surface) -> None:
        """Render reward summary lines in OUTCOME phase."""
        if not self.chosen_outcome:
            return

        y = _PANEL_Y + 280
        for reward in self.chosen_outcome.rewards:
            text = _reward_display_text(reward)
            if text:
                surf = self.reward_font.render(text, True, (180, 220, 180))
                screen.blit(surf, (_PANEL_X + _INNER_PAD, y))
                y += 28

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle keyboard and button events."""
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            self._handle_button(event)

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """Handle keyboard input."""
        if self.phase == EncounterPhase.CHOOSING:
            # Number keys 1-3 select choices
            key_map = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
            idx = key_map.get(event.key)
            if idx is not None and idx < len(self.display_choices):
                self._select_choice(idx)

        elif self.phase == EncounterPhase.OUTCOME:
            if event.key == pygame.K_RETURN:
                self._finish()

    def _handle_button(self, event: pygame.event.Event) -> None:
        """Handle pygame_gui button presses."""
        if self.phase == EncounterPhase.CHOOSING:
            for i, btn in enumerate(self.choice_buttons):
                if event.ui_element == btn:
                    self._select_choice(i)
                    return

        elif self.phase == EncounterPhase.OUTCOME:
            if event.ui_element == self.continue_button:
                self._finish()

    def _select_choice(self, index: int) -> None:
        """Process a player choice selection."""
        choice = self.display_choices[index]
        outcome = choice.outcome

        # Resolve shakedown sentinel: deduct_credits with amount=-1
        resolved_rewards = []
        for reward in outcome.rewards:
            if reward.reward_type == "deduct_credits" and reward.amount == -1:
                resolved_rewards.append(
                    MissionReward("deduct_credits", self.encounter_ref.shakedown_demand)
                )
            else:
                resolved_rewards.append(reward)

        self.chosen_outcome = EncounterOutcome(
            description=outcome.description,
            rewards=resolved_rewards,
            leads_to_combat=outcome.leads_to_combat,
        )
        self.pending_combat = outcome.leads_to_combat

        # Boss encounters: override enemy_template_ids from outcome
        if outcome.leads_to_combat and hasattr(outcome, "enemy_template_ids") and outcome.enemy_template_ids:
            self.encounter_ref.enemy_template_ids = list(outcome.enemy_template_ids)

        self.phase = EncounterPhase.OUTCOME
        self._create_ui()
        logger.info(
            f"Encounter choice: {choice.id} (combat={self.pending_combat})"
        )

    def _finish(self) -> None:
        """Transition from OUTCOME to DONE."""
        self.phase = EncounterPhase.DONE
        if self.pending_combat:
            self.next_state = GameState.COMBAT
        else:
            self.next_state = GameState.TRADING

    def get_next_state(self) -> Optional[GameState]:
        """Return the requested next state, if any."""
        return self.next_state


# ============================================================================
# Helpers
# ============================================================================


class _SafeFormatMap(dict):
    """Dict subclass that returns the key template for missing keys."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _substitute_choices(
    choices: list[EncounterChoice], subs: dict[str, str]
) -> list[EncounterChoice]:
    """Create copies of choices with template strings substituted."""
    fmt = _SafeFormatMap(subs)
    result = []
    for c in choices:
        result.append(
            EncounterChoice(
                id=c.id,
                label=c.label.format_map(fmt),
                description=c.description.format_map(fmt),
                outcome=EncounterOutcome(
                    description=c.outcome.description.format_map(fmt),
                    rewards=list(c.outcome.rewards),
                    leads_to_combat=c.outcome.leads_to_combat,
                ),
            )
        )
    return result


def _reward_display_text(reward: MissionReward) -> str:
    """Convert a reward to display text."""
    if reward.reward_type == "credits":
        return f"+{reward.amount} Credits"
    elif reward.reward_type == "deduct_credits":
        return f"-{reward.amount} Credits"
    elif reward.reward_type == "xp":
        return f"+{reward.amount} XP"
    elif reward.reward_type == "set_flag":
        return ""  # Flags are silent
    return ""
