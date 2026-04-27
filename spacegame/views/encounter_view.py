"""Encounter view for non-hostile random encounters.

Presents a narrative description with player choices, shows outcome text
and rewards, then transitions back to the galaxy map or into combat.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UITextBox

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState, scale_x, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import FONT_BODY, FONT_LG, FONT_TITLE, get_font
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterDefinition,
    EncounterOutcome,
    EncounterRef,
)
from spacegame.models.mission import MissionReward
from spacegame.models.player import Player
from spacegame.models.social import SocialManager
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.first_time_tip import FirstTimeTipOverlay


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
        player: Optional[Player] = None,
        social_manager: Optional[SocialManager] = None,
        journal: Optional[object] = None,
    ) -> None:
        super().__init__(ui_manager)
        self.encounter_def = encounter_def
        self.encounter_ref = encounter_ref
        self.player = player
        # CE-4: SocialManager is consulted for skill_check resolution on
        # encounter choices. When None, skill-check choices fall back to
        # their failure_outcome (or outcome if no failure_outcome) and
        # display "[skill ?]" so the missing wiring is visible.
        self.social_manager = social_manager
        # RC-6: optional Journal reference for first-meeting captain entries.
        self.journal = journal
        self.next_state: Optional[GameState] = None
        self._first_time_tip: Optional[FirstTimeTipOverlay] = None

        # Phase state
        self.phase = EncounterPhase.CHOOSING
        self.chosen_outcome: Optional[EncounterOutcome] = None
        self.pending_combat: bool = False

        # Fonts
        self.title_font = get_font("header", FONT_TITLE)
        self.body_font = get_font("narration", FONT_BODY)
        self.reward_font = get_font("stats", FONT_LG)

        # Background
        self.background = AnimatedBackground(
            "deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=encounter_ref.encounter_seed
        )
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

        # CE-1: captain attribution — when the encounter has a captain_id,
        # use the captain's pre_combat_hail + display_name instead of the
        # definition's static description + name. Falls back cleanly when
        # no captain is attached or the id doesn't resolve.
        # RC-3: when the player has met this captain before, an authored
        # ``CaptainVariant`` overlays the base hail with a return-meeting
        # version. self._effective_dialogue holds the resolved overlay.
        self._captain = self._resolve_captain()
        self._effective_dialogue = self._resolve_effective_dialogue()

        # Template substitution for shakedown encounters — applied to the
        # effective description (captain hail or static description).
        subs = {"shakedown_demand": str(encounter_ref.shakedown_demand)}
        base_description = (
            self._effective_dialogue.pre_combat_hail
            if self._effective_dialogue is not None
            else encounter_def.description
        )
        self.display_description = base_description.format_map(_SafeFormatMap(subs))
        self.display_name = (
            self._effective_dialogue.display_name
            if self._effective_dialogue is not None
            else encounter_def.name
        )
        self.display_choices = _substitute_choices(encounter_def.choices, subs)

        # UI element refs (created in _create_ui)
        self.choice_buttons: list[UIButton] = []
        self.continue_button: Optional[UIButton] = None
        self.description_box: Optional[UITextBox] = None
        self.outcome_box: Optional[UITextBox] = None

    def _resolve_captain(self):
        """Look up the ``EnemyCaptain`` attached to this encounter, if any.

        Returns ``None`` when the encounter has no ``captain_id`` or when
        the id doesn't resolve (treated as a content-data warning, not a
        hard failure — the encounter falls back to its static fields).
        """
        captain_id = getattr(self.encounter_def, "captain_id", "")
        if not captain_id:
            return None
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        captain = dl.captains.get(captain_id) if hasattr(dl, "captains") else None
        if captain is None:
            logger.warning(
                f"Encounter '{self.encounter_def.id}' references unknown "
                f"captain_id='{captain_id}' — falling back to static description"
            )
        return captain

    def _resolve_effective_dialogue(self):
        """RC-3: overlay any authored CaptainVariant onto the base captain.

        Reads the player's ``CaptainMemory`` to pick the meeting state,
        then consults ``DataLoader.captain_variants`` for an override.
        Returns ``None`` when no captain is attached.
        """
        if self._captain is None:
            return None
        from spacegame.data_loader import get_data_loader
        from spacegame.models.captain_variant import get_effective_captain_dialogue

        dl = get_data_loader()
        memory = None
        if self.player is not None and hasattr(self.player, "captain_memory"):
            memory = self.player.captain_memory.get(self._captain.id)
        return get_effective_captain_dialogue(self._captain, memory, dl.captain_variants)

    def on_enter(self) -> None:
        """Initialize encounter UI."""
        super().on_enter()
        logger.info(f"Entering encounter: {self.display_name}")
        self._create_ui()
        self._maybe_show_tip()

    def _maybe_show_tip(self) -> None:
        """First-time teaching tip keyed on encounter_type.

        Customs inspection is the only teachable case today. Others can
        be added later by extending the type→flag check.
        """
        if self.player is None:
            return
        etype = self.encounter_def.encounter_type
        if etype != "customs_inspection":
            return
        if self.player.dialogue_flags.get("seen_tip_customs_inspection", False):
            return

        self._first_time_tip = FirstTimeTipOverlay(
            title="Customs",
            body=(
                "Four options: comply, persuade, bribe, intimidate. Each "
                "costs something different. Hidden Compartments hide cargo "
                "from routine scans, but deep scans still find it and "
                "double the penalty."
            ),
            on_dismiss=self._mark_customs_tip_seen,
        )

    def _mark_customs_tip_seen(self) -> None:
        if self.player is not None:
            self.player.dialogue_flags["seen_tip_customs_inspection"] = True

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
            label, tooltip, disabled = self._format_choice_button(i, choice)
            btn = UIButton(
                relative_rect=btn_rect,
                text=label,
                manager=self.ui_manager,
                tool_tip_text=tooltip,
            )
            if disabled:
                btn.disable()
            self.choice_buttons.append(btn)

    def _format_choice_button(self, index: int, choice: EncounterChoice) -> tuple[str, str, bool]:
        """Compose the button label + tooltip + disabled-flag for a choice.

        - When ``skill_check`` is set, append "[Skill N PASS|FAIL]" so the
          player sees the deterministic outcome before clicking.
        - When ``requires_credits`` is unmet, prefix with "Need Xc" and
          disable the button.
        """
        label = f"{index + 1}. {choice.label}"
        tooltip_lines = [choice.description] if choice.description else []
        disabled = False

        if choice.requires_credits and self.player is not None:
            if self.player.credits < choice.requires_credits:
                disabled = True
                label = f"{label} ({choice.requires_credits}c)"
                tooltip_lines.append(
                    f"Need {choice.requires_credits} credits — short by "
                    f"{choice.requires_credits - self.player.credits}."
                )
            else:
                label = f"{label} ({choice.requires_credits}c)"

        if choice.skill_check is not None:
            sc = choice.skill_check
            if self.social_manager is not None:
                will_pass = self.social_manager.can_pass_check(sc.skill, sc.difficulty, "")
                marker = "PASS" if will_pass else "FAIL"
                label = f"{label}  [{sc.skill.title()} {sc.difficulty} {marker}]"
                effective = self.social_manager.get_effective_level(sc.skill, "")
                tooltip_lines.append(
                    f"{sc.skill.title()} check: your {effective} vs {sc.difficulty}."
                )
            else:
                label = f"{label}  [{sc.skill.title()} {sc.difficulty}]"

        return label, "\n".join(tooltip_lines), disabled

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
        if self._first_time_tip is not None:
            self._first_time_tip.update(dt)
            if self._first_time_tip.dismissed:
                self._first_time_tip = None
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """Render encounter panel."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Panel background
        panel_rect = pygame.Rect(_PANEL_X, _PANEL_Y, _PANEL_W, _PANEL_H)
        color = self.encounter_def.icon_color
        draw_panel(
            screen,
            panel_rect,
            alpha=255,
            bg_color=(20, 20, 30),
            border_color=color,
            border_radius=8,
        )

        # Title — truncate if it overflows the panel (QA-G-4 fix).
        # Several captain display_names exceed 700px at the title font;
        # without truncation they render past the panel edges.
        from spacegame.engine.draw_utils import truncate_text

        max_title_w = _PANEL_W - _INNER_PAD * 2
        title_text = truncate_text(self.display_name, self.title_font, max_title_w)
        title_surf = self.title_font.render(title_text, True, color)
        title_x = _PANEL_X + (_PANEL_W - title_surf.get_width()) // 2
        screen.blit(title_surf, (title_x, _PANEL_Y + 16))

        # RC-6: "Met before" badge for captain-attached encounters when
        # the player has prior history with this captain. Subtle line
        # under the title.
        badge_text = self._met_before_badge_text()
        if badge_text:
            badge_surf = self.body_font.render(badge_text, True, (160, 160, 180))
            badge_x = _PANEL_X + (_PANEL_W - badge_surf.get_width()) // 2
            screen.blit(badge_surf, (badge_x, _PANEL_Y + 36))

        # Horizontal rule
        rule_y = _PANEL_Y + 50
        pygame.draw.line(
            screen,
            (60, 60, 80),
            (_PANEL_X + _INNER_PAD, rule_y),
            (_PANEL_X + _PANEL_W - _INNER_PAD, rule_y),
        )

        # Phase-specific rendering
        if self.phase == EncounterPhase.OUTCOME and self.chosen_outcome:
            self._render_rewards(screen)

    def _met_before_badge_text(self) -> str:
        """RC-6: subtle 'Met before' tag for captains the player has history with.

        Returns empty string when no captain attached, no player, or never
        met. Plural-aware so "1 time" and "3 times" both read clean.
        """
        if self._captain is None or self.player is None:
            return ""
        if not hasattr(self.player, "captain_memory"):
            return ""
        memory = self.player.captain_memory.get(self._captain.id)
        if memory is None or memory.encounter_count == 0:
            return ""
        n = memory.encounter_count
        suffix = "time" if n == 1 else "times"
        return f"Met before. {n} {suffix}."

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
        if self._first_time_tip is not None and not self._first_time_tip.dismissed:
            if self._first_time_tip.handle_event(event):
                return
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            self._handle_button(event)

    def render_top(self, screen: pygame.Surface) -> None:
        """Draw the first-time tip above pygame_gui elements."""
        if self._first_time_tip is not None:
            self._first_time_tip.render(screen)

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
        """Process a player choice selection.

        CE-4: when ``choice.skill_check`` is set, resolve via SocialManager
        and pick ``outcome`` on success or ``failure_outcome`` on failure
        (falling back to ``outcome`` if no failure path is authored).
        Skill check flags (set_flag_on_success/failure) write into
        ``player.dialogue_flags`` so other systems can react.
        """
        choice = self.display_choices[index]

        # CE-4: resolve skill_check first; outcome selection follows.
        outcome = choice.outcome
        skill_check_succeeded = False
        if choice.skill_check is not None:
            skill_check_succeeded = self._resolve_choice_skill_check(choice)
            if not skill_check_succeeded and choice.failure_outcome is not None:
                outcome = choice.failure_outcome

        # Resolve shakedown sentinel: deduct_credits with amount=-1
        resolved_rewards = []
        for reward in outcome.rewards:
            if reward.reward_type == "deduct_credits" and reward.amount == -1:
                resolved_rewards.append(
                    MissionReward("deduct_credits", self.encounter_ref.shakedown_demand)
                )
            else:
                resolved_rewards.append(reward)

        # CE-4: convert requires_credits into an automatic deduct_credits
        # reward so the existing reward pipeline handles the spend.
        if choice.requires_credits and not any(
            r.reward_type == "deduct_credits" for r in resolved_rewards
        ):
            resolved_rewards.insert(0, MissionReward("deduct_credits", choice.requires_credits))

        self.chosen_outcome = EncounterOutcome(
            description=outcome.description,
            rewards=resolved_rewards,
            leads_to_combat=outcome.leads_to_combat,
        )
        self.pending_combat = outcome.leads_to_combat

        # Boss / encounter-spawn enemies: outcome may name the templates.
        if (
            outcome.leads_to_combat
            and hasattr(outcome, "enemy_template_ids")
            and outcome.enemy_template_ids
        ):
            self.encounter_ref.enemy_template_ids = list(outcome.enemy_template_ids)

        # RC-6: record the captain encounter for non-combat resolutions.
        # Combat-bound outcomes are recorded by CombatView at COMBAT_OVER
        # so we skip them here to avoid double-counting.
        if not self.pending_combat:
            self._maybe_record_captain_encounter(choice, skill_check_succeeded)

        self.phase = EncounterPhase.OUTCOME
        self._create_ui()
        logger.info(f"Encounter choice: {choice.id} (combat={self.pending_combat})")

    def _maybe_record_captain_encounter(
        self, choice: EncounterChoice, skill_check_succeeded: bool
    ) -> None:
        """RC-6: record a non-combat captain meeting on player memory.

        Maps the choice path to a captain_memory outcome:
        - ``requires_credits`` (Pay)        -> ``OUTCOME_BRIBED``
        - successful skill check            -> ``OUTCOME_NEGOTIATED``
        - other peaceful resolutions        -> not recorded (no engagement)

        Skips silently when the encounter has no captain or no player.
        """
        captain_id = getattr(self.encounter_def, "captain_id", "")
        if not captain_id or self.player is None:
            return

        from spacegame.models.captain_memory import (
            OUTCOME_BRIBED,
            OUTCOME_NEGOTIATED,
        )

        if choice.requires_credits and choice.requires_credits > 0:
            outcome = OUTCOME_BRIBED
        elif choice.skill_check is not None and skill_check_succeeded:
            outcome = OUTCOME_NEGOTIATED
        else:
            return  # Walk-away / pass — not a meaningful captain meeting

        # RC-6: journal entry for first meeting (BEFORE recording so
        # is_first_meeting still reads true).
        memory = self.player.get_captain_memory(captain_id)
        if memory.is_first_meeting:
            self._add_first_meeting_journal_entry(captain_id)
        was_wanderer = memory.status == "wanderer"

        self.player.record_captain_encounter(captain_id, outcome)

        # QA-F-2: wanderer auto-retire journal entry.
        if not was_wanderer and memory.status == "wanderer":
            self._add_wanderer_journal_entry(captain_id)

    def _add_wanderer_journal_entry(self, captain_id: str) -> None:
        """QA-F-2: silent wanderer retirement fix. Fires when a captain
        auto-retires after N unresolved encounters, so the player sees
        the rivalry end instead of the captain just disappearing."""
        if self.journal is None:
            return
        from spacegame.data_loader import get_data_loader

        try:
            captain = get_data_loader().captains.get(captain_id)
        except Exception:
            captain = None
        if captain is None:
            return
        text = (
            f"Word came back through the docks. {captain.name} moved on. "
            "Whatever they were chasing, they're chasing it somewhere you "
            "aren't."
        )
        self.journal.add_auto_entry(
            entry_id=f"captain_wanderer_{captain_id}",
            text=text,
            game_day=getattr(self.player, "game_day", 1),
            system_id=getattr(self.player, "current_system_id", ""),
            tag="people",
        )

    def _add_first_meeting_journal_entry(self, captain_id: str) -> None:
        """RC-6: drop a journal entry the first time the player meets a captain.

        No-op when no journal is wired or the captain doesn't resolve.
        """
        if self.journal is None:
            return
        from spacegame.data_loader import get_data_loader

        try:
            captain = get_data_loader().captains.get(captain_id)
        except Exception:
            captain = None
        if captain is None:
            return
        # Use captain.name + captain.nickname directly. display_name uses
        # an em-dash separator that's fine for headers but a Writing Bible
        # violation in narrative text.
        nickname_phrase = f", the {captain.nickname}," if captain.nickname else ","
        text = (
            f"Met {captain.name}{nickname_phrase} for the first time. "
            f"Their ship runs the {captain.signature_ship_template} hull. "
            f"They keep a base out of {captain.home_sector or 'parts unknown'}."
        )
        self.journal.add_auto_entry(
            entry_id=f"captain_met_{captain_id}",
            text=text,
            game_day=getattr(self.player, "game_day", 1),
            system_id=getattr(self.player, "current_system_id", ""),
            tag="people",
        )

    def _resolve_choice_skill_check(self, choice: EncounterChoice) -> bool:
        """Resolve a CE-4 encounter skill check and apply its flags.

        Returns ``True`` on pass. When ``social_manager`` is missing the
        check is treated as failed so authored failure_outcomes still
        play — the flag side-effects are skipped because there's no XP /
        disposition system to update in that path.
        """
        sc = choice.skill_check
        assert sc is not None
        if self.social_manager is None:
            return False
        success, _msg = self.social_manager.resolve_check(sc.skill, sc.difficulty, "")
        if self.player is not None:
            flag = sc.set_flag_on_success if success else sc.set_flag_on_failure
            if flag:
                self.player.dialogue_flags[flag] = True
        return success

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
    """Create copies of choices with template strings substituted.

    CE-4: passes ``skill_check``, ``failure_outcome``, and
    ``requires_credits`` through unchanged.
    """
    fmt = _SafeFormatMap(subs)

    def _sub_outcome(o: EncounterOutcome) -> EncounterOutcome:
        return EncounterOutcome(
            description=o.description.format_map(fmt),
            rewards=list(o.rewards),
            leads_to_combat=o.leads_to_combat,
            enemy_template_ids=list(o.enemy_template_ids),
        )

    result = []
    for c in choices:
        result.append(
            EncounterChoice(
                id=c.id,
                label=c.label.format_map(fmt),
                description=c.description.format_map(fmt),
                outcome=_sub_outcome(c.outcome),
                skill_check=c.skill_check,
                failure_outcome=(
                    _sub_outcome(c.failure_outcome) if c.failure_outcome is not None else None
                ),
                requires_credits=c.requires_credits,
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
