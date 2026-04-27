"""SA-1: Wreckers' Guild Hall view (contract board + recurring contacts).

Renders the contract board for the player's current Wreckers' Guild tier,
exposes accept / turn-in / make-up actions, and surfaces a first-visit
PT-M tip overlay. Pure presentation + thin orchestration; the
business logic lives in :mod:`spacegame.models.wreckers_guild`.
"""

from __future__ import annotations

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_x,
    scale_y,
)
from spacegame.constants.flags import (
    enrolled_wreckers_guild,
    met_npc,
    seen_wreckers_guild_tip,
    wreckers_contract_completed,
    wreckers_made_up_apology,
    wreckers_made_up_journal,
    wreckers_promoted_tier,
)
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_LG,
    FONT_MD,
    FONT_SUBTITLE,
    FONT_TITLE,
    get_font,
)
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.player import Player
from spacegame.models.soft_deadline import SoftDeadline
from spacegame.models.sub_reputation import get_tier_for_rep
from spacegame.models.wreckers_guild import (
    APPRENTICE_LATE_MULTIPLIER,
    APPRENTICE_PARTIAL_MULTIPLIER,
    SUB_REP_FAILURE_PENALTY,
    WRECKERS_GUILD_CONFIG,
    WreckersContractTemplate,
    WreckersGuildState,
    current_tier_id,
    enroll_player_state,
    get_template,
    payout_multiplier_for_tier,
    roll_offers,
    seed_for_window,
)
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.first_time_tip import FirstTimeTipOverlay

# Layout
PANEL_X = scale_x(60)
PANEL_W = WINDOW_WIDTH - scale_x(120)
PANEL_TOP_Y = scale_y(20)
HEADER_H = scale_y(110)
BOARD_TOP_Y = PANEL_TOP_Y + HEADER_H + scale_y(20)
BOARD_H = scale_y(420)
CARD_H = scale_y(80)
CARD_PAD = scale_y(8)
ACCENT_COLOR = (200, 160, 255)  # Same purple Reach unique cards use


class WreckersGuildView(BaseView):
    """Contract board + Malia dock for the Wreckers' Guild Hall."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        mission_manager: MissionManager,
    ) -> None:
        """Initialize the Wreckers' Guild Hall view.

        Args:
            ui_manager: pygame_gui UI manager.
            player: Current player. Mutated in place during enrollment,
                accept / turn-in flows, and tier promotions.
            mission_manager: Active MissionManager — Wreckers' contracts
                spawn through ``add_mission`` so existing mission systems
                (HUD hints, journal, save) pick them up uniformly.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.mission_manager = mission_manager
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = get_font("header", FONT_TITLE)
        self.subtitle_font = get_font("dialogue", FONT_MD)
        self.body_font = get_font("dialogue", FONT_BODY)
        self.label_font = get_font("label", FONT_SUBTITLE)
        self.value_font = get_font("stats", FONT_LG)

        # UI element refs
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.enroll_button: Optional[pygame_gui.elements.UIButton] = None
        self.turn_in_button: Optional[pygame_gui.elements.UIButton] = None
        self.make_up_button: Optional[pygame_gui.elements.UIButton] = None
        self._accept_buttons: dict[str, pygame_gui.elements.UIButton] = {}

        # Status / feedback message
        self.message: Optional[str] = None
        self.message_timer: float = 0.0

        # Promotion banner (drained from player._pending_sub_rep_deltas)
        self._promotion_banner: Optional[str] = None
        self._promotion_banner_timer: float = 0.0

        # First-time tip overlay (PT-M pattern)
        self._tip_overlay: Optional[FirstTimeTipOverlay] = None

        # Cached offer list for the current visit (for tests + hover)
        self._offer_template_ids: list[str] = []

        # Last completed mission id — exposed for tests/UX confirmation flow.
        self._last_completed_id: Optional[str] = None

        # Background — neutral station theme; the Hall is dim, industrial.
        self.background = AnimatedBackground("station", WINDOW_WIDTH, WINDOW_HEIGHT, seed=4321)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(150)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        """Activate the view, refresh the board, and fire the first-time tip."""
        super().on_enter()
        logger.info("Entered Wreckers' Guild Hall")
        # Auto-fail any outstanding contract whose soft deadline elapsed
        # while the player was elsewhere (acceptance #5).
        self._auto_fail_overdue_contracts()
        self._refresh_offers()
        self._create_ui()
        self._maybe_show_tip()
        self._drain_promotion_queue()

    def on_exit(self) -> None:
        """Deactivate the view and tear down UI."""
        self._destroy_ui()
        self._tip_overlay = None
        super().on_exit()

    # ------------------------------------------------------------------
    # Board state
    # ------------------------------------------------------------------

    def _refresh_offers(self) -> None:
        """Populate the offer list using the deterministic roll.

        Acceptance #8: same-window visits return the same offers; window
        rollover produces a fresh roll. Already-accepted contracts are
        filtered out so the same template doesn't double-show.
        """
        state = self._ensure_state()
        if not state.enrolled:
            self._offer_template_ids = []
            return
        window = seed_for_window(self.player.game_day)
        if state.slot_seed_window != window or not state.slot_offers:
            offers = roll_offers(
                self.player.name,
                self.player.game_day,
                current_tier_id(self.player.sub_reputation),
            )
            state.slot_seed_window = window
            state.slot_offers = offers
        # Filter offers whose mission is currently active so the board
        # doesn't double-show what the player already accepted.
        active_template_ids = self._active_template_ids()
        self._offer_template_ids = [
            tid for tid in state.slot_offers if tid not in active_template_ids
        ]

    def _ensure_state(self) -> WreckersGuildState:
        """Return the player's WreckersGuildState, creating it if absent."""
        if self.player.wreckers_guild_state is None:
            self.player.wreckers_guild_state = WreckersGuildState()
        return self.player.wreckers_guild_state

    def _active_template_ids(self) -> set[str]:
        """Resolve the template ids of the player's active wreckers contracts."""
        state = self._ensure_state()
        active: set[str] = set()
        for mission_id in state.active_contract_ids:
            tpl_id = self._template_id_from_mission_id(mission_id)
            if tpl_id:
                active.add(tpl_id)
        return active

    @staticmethod
    def _template_id_from_mission_id(mission_id: str) -> Optional[str]:
        """Inverse of :meth:`_mission_id_for_template`."""
        prefix = "wreckers_contract_"
        if not mission_id.startswith(prefix):
            return None
        # Mission id format: wreckers_contract_<template_id>_<window>_<slot>
        rest = mission_id[len(prefix) :]
        parts = rest.rsplit("_", 2)
        if len(parts) != 3:
            return None
        return parts[0]

    @staticmethod
    def _mission_id_for_template(template_id: str, window: int, slot: int) -> str:
        return f"wreckers_contract_{template_id}_{window}_{slot}"

    def get_offered_template_ids(self) -> list[str]:
        """Return cached offer template ids for tests + the renderer."""
        return list(self._offer_template_ids)

    # ------------------------------------------------------------------
    # UI lifecycle
    # ------------------------------------------------------------------

    def _create_ui(self) -> None:
        """Create all pygame_gui elements for the current state."""
        self._destroy_ui()

        state = self._ensure_state()

        # Back button — always present.
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_X + PANEL_W - scale_x(140),
                PANEL_TOP_Y + scale_y(20),
                scale_x(120),
                scale_y(36),
            ),
            text="Back to Station",
            manager=self.ui_manager,
        )

        if not state.enrolled:
            # Single enroll button replaces the contract list.
            self.enroll_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + PANEL_W // 2 - scale_x(120),
                    BOARD_TOP_Y + scale_y(80),
                    scale_x(240),
                    scale_y(48),
                ),
                text="Sign On with the Guild",
                manager=self.ui_manager,
            )
            return

        # Make-up button (post-lockout) takes precedence over the board.
        if self._make_up_available():
            self.make_up_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + PANEL_W // 2 - scale_x(120),
                    BOARD_TOP_Y + scale_y(120),
                    scale_x(240),
                    scale_y(40),
                ),
                text="Square It With Malia",
                manager=self.ui_manager,
            )

        # Turn-in button when there's an eligible active contract.
        if self._has_turn_in_eligible_contract():
            self.turn_in_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + PANEL_W // 2 - scale_x(120),
                    BOARD_TOP_Y + scale_y(60),
                    scale_x(240),
                    scale_y(40),
                ),
                text="Turn In Contract",
                manager=self.ui_manager,
            )

        # Accept buttons — one per offer.
        for idx, template_id in enumerate(self._offer_template_ids):
            tpl = get_template(template_id)
            if tpl is None:
                continue
            button_y = (
                BOARD_TOP_Y + scale_y(180) + idx * (CARD_H + CARD_PAD) + (CARD_H - scale_y(34)) // 2
            )
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    PANEL_X + PANEL_W - scale_x(140),
                    button_y,
                    scale_x(120),
                    scale_y(34),
                ),
                text="Take Contract",
                manager=self.ui_manager,
            )
            if self.is_locked_out():
                btn.disable()
                btn.tool_tip_text = "Square it with Malia first."
            self._accept_buttons[template_id] = btn

    def _destroy_ui(self) -> None:
        """Kill all pygame_gui elements (CLAUDE.md lifecycle invariant)."""
        for elem in (
            self.back_button,
            self.enroll_button,
            self.turn_in_button,
            self.make_up_button,
        ):
            if elem:
                elem.kill()
        self.back_button = None
        self.enroll_button = None
        self.turn_in_button = None
        self.make_up_button = None
        for btn in self._accept_buttons.values():
            btn.kill()
        self._accept_buttons.clear()

    # ------------------------------------------------------------------
    # First-time tip
    # ------------------------------------------------------------------

    def _maybe_show_tip(self) -> None:
        """Fire the PT-M overlay on first entry per save (acceptance #10)."""
        if self.player.dialogue_flags.get(seen_wreckers_guild_tip()):
            return

        def _on_dismiss() -> None:
            self.player.dialogue_flags[seen_wreckers_guild_tip()] = True

        self._tip_overlay = FirstTimeTipOverlay(
            title="Guild Work",
            body=(
                "Take a contract from the board. Haul the listed cargo back "
                "here to turn it in. Standing builds with completed work."
            ),
            on_dismiss=_on_dismiss,
        )

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------

    def _enroll_player(self) -> None:
        """First conversation with Malia — apprentice tier seeded."""
        state = self._ensure_state()
        new_state, granted = enroll_player_state(state, self.player.sub_reputation)
        self.player.wreckers_guild_state = new_state
        if granted:
            self.player.dialogue_flags[enrolled_wreckers_guild()] = True
            # Mark Malia as met if some other path hasn't already done so.
            self.player.dialogue_flags.setdefault(met_npc("malia_torres"), True)
            self._show_message("Apprentice. Welcome to the work.")
            self._refresh_offers()
            self._create_ui()

    # ------------------------------------------------------------------
    # Lockout / make-up
    # ------------------------------------------------------------------

    def is_locked_out(self) -> bool:
        """True if accepts are blocked by an active lockout."""
        state = self._ensure_state()
        return state.is_locked_out(self.player.game_day)

    def _make_up_available(self) -> bool:
        """Make-up beat fires only after lockout expires and once per save."""
        state = self._ensure_state()
        if not state.enrolled:
            return False
        if state.lockout_until_day == 0:
            return False
        if self.player.game_day <= state.lockout_until_day:
            return False
        if self.player.dialogue_flags.get(wreckers_made_up_apology()):
            return False
        return True

    def _make_up_with_malia(self) -> None:
        """Resolve the post-lockout make-up beat (acceptance #5)."""
        if not self._make_up_available():
            return
        state = self._ensure_state()
        state.clear_lockout()
        self.player.dialogue_flags[wreckers_made_up_apology()] = True
        self.player.dialogue_flags[wreckers_made_up_journal()] = True
        self._show_message("Done. Pick up where we left off.")
        self._create_ui()

    # ------------------------------------------------------------------
    # Auto-fail
    # ------------------------------------------------------------------

    def _auto_fail_overdue_contracts(self) -> None:
        """Acceptance #5: auto-fail any wreckers contract past its deadline.

        Iterates active wreckers contracts and fails any whose soft
        deadline has elapsed by the current game day. The first such
        failure also applies the lockout + sub-rep penalty; subsequent
        failures clean up the active list without re-locking (rare in
        practice, but safe).
        """
        state = self._ensure_state()
        if not state.enrolled or not state.active_contract_ids:
            return
        for mission_id in list(state.active_contract_ids):
            mission = self.mission_manager.get_mission(mission_id)
            if mission is None:
                # Lost mission — clean up state.
                state.clear_active_contract(mission_id)
                continue
            status = self.mission_manager.get_status(mission_id)
            if status != MissionStatus.ACTIVE:
                continue
            if not self._mission_overdue(mission_id):
                continue
            # Soft deadline elapsed — fail with consequence.
            self._fail_active_contract_with_penalty(mission_id)

    def _mission_overdue(self, mission_id: str) -> bool:
        mission = self.mission_manager.get_mission(mission_id)
        if mission is None or mission.soft_deadline is None:
            return False
        accepted = self.mission_manager.get_accepted_day(mission_id)
        if accepted is None:
            return False
        days_elapsed = self.player.game_day - accepted
        return days_elapsed > mission.soft_deadline.partial_reward_day_count

    def _fail_active_contract_with_penalty(self, mission_id: str) -> None:
        """Fail a contract: drop sub-rep, set lockout, clear from state."""
        state = self._ensure_state()
        # Drop sub-rep and clamp at 0 (acceptance #5).
        success, _msg = self.player.modify_sub_reputation(
            "wreckers_guild", -SUB_REP_FAILURE_PENALTY, WRECKERS_GUILD_CONFIG
        )
        if not success:
            logger.warning("modify_sub_reputation refused for wreckers_guild on failure")
        state.apply_lockout(self.player.game_day)
        state.clear_active_contract(mission_id)
        # Mark mission failed if it's still tracked.
        if self.mission_manager.get_mission(mission_id) is not None:
            self.mission_manager.fail_mission(mission_id)
        self._show_message("Missed it. Malia will say so.")

    # ------------------------------------------------------------------
    # Accept / turn-in
    # ------------------------------------------------------------------

    def _accept_contract(self, template_id: str) -> bool:
        """Spawn a Mission for ``template_id`` and register it in state."""
        if self.is_locked_out():
            self._show_message("Guild won't take new work from you yet.")
            return False
        tpl = get_template(template_id)
        if tpl is None:
            return False
        state = self._ensure_state()
        # Don't double-accept the same template within the active set.
        if template_id in self._active_template_ids():
            return False
        slot = state.slot_offers.index(template_id) if template_id in state.slot_offers else 0
        mission_id = self._mission_id_for_template(template_id, state.slot_seed_window, slot)
        mission = self._build_mission(tpl, mission_id)
        success, _msg = self.mission_manager.add_mission(
            mission, initial_status=MissionStatus.AVAILABLE
        )
        if not success:
            logger.warning("MissionManager rejected contract %s", mission_id)
            return False
        accept_ok, accept_msg = self.mission_manager.accept_mission(
            mission_id, game_day=self.player.game_day, player=self.player
        )
        if not accept_ok:
            logger.warning("Accept failed for %s: %s", mission_id, accept_msg)
            return False
        state.register_active_contract(mission_id)
        self._refresh_offers()
        self._create_ui()
        self._show_message(f"Contract taken: {tpl.name}.")
        return True

    def _build_mission(self, tpl: WreckersContractTemplate, mission_id: str) -> Mission:
        """Construct a Mission instance from a template."""
        # Soft deadline: full window is 60% of the soft cap; partial is the
        # cap itself; past the cap the contract auto-fails.
        full_days = max(1, int(tpl.soft_deadline_days * 0.6))
        deadline = SoftDeadline(
            full_reward_day_count=full_days,
            partial_reward_day_count=tpl.soft_deadline_days,
            partial_reward_multiplier=APPRENTICE_PARTIAL_MULTIPLIER,
            late_multiplier=APPRENTICE_LATE_MULTIPLIER,
        )
        objectives = [
            MissionObjective(
                type=ObjectiveType.COLLECT_CARGO,
                target_id=tpl.target_commodity_id,
                target_quantity=tpl.target_quantity,
                description=f"Recover {tpl.target_quantity} {tpl.target_commodity_id}",
            ),
        ]
        # Forced encounter wired through if the template asks for it
        # (escort_salvage). Reuses the generic ForcedEncounter — Mission's
        # existing travel hook fires the encounter once.
        forced_encounter = None
        if tpl.forced_encounter_id:
            from spacegame.models.mission import ForcedEncounter

            forced_encounter = ForcedEncounter(
                encounter_type="hostile",
                trigger_flag=f"{mission_id}_encounter_fired",
                encounter_def_id=tpl.forced_encounter_id,
            )
        return Mission(
            id=mission_id,
            name=tpl.name,
            description=tpl.briefing,
            objectives=objectives,
            rewards=[
                MissionReward(reward_type="credits", amount=tpl.base_payout_credits),
            ],
            mission_type="side",
            available_at=["crimson_reach"],
            soft_deadline=deadline,
            forced_encounter=forced_encounter,
            hint=f"Bring {tpl.target_quantity} {tpl.target_commodity_id} to Crimson Reach.",
        )

    def _has_turn_in_eligible_contract(self) -> bool:
        """True if the player has an active wreckers contract whose cargo is on-ship."""
        state = self._ensure_state()
        for mission_id in state.active_contract_ids:
            if self._cargo_satisfies_mission(mission_id):
                return True
        return False

    def _cargo_satisfies_mission(self, mission_id: str) -> bool:
        mission = self.mission_manager.get_mission(mission_id)
        if mission is None:
            return False
        for obj in mission.objectives:
            if obj.type == ObjectiveType.COLLECT_CARGO:
                if self.player.ship.get_cargo_quantity(obj.target_id) < obj.target_quantity:
                    return False
        return True

    def _turn_in_active_contract(self) -> tuple[bool, str]:
        """Resolve the first eligible active contract: pay, consume cargo."""
        state = self._ensure_state()
        for mission_id in list(state.active_contract_ids):
            if not self._cargo_satisfies_mission(mission_id):
                continue
            mission = self.mission_manager.get_mission(mission_id)
            if mission is None:
                continue
            template_id = self._template_id_from_mission_id(mission_id)
            tpl = get_template(template_id) if template_id else None
            if tpl is None:
                continue
            # Consume the listed cargo before applying credits so we don't
            # double-credit a partial fill from a stale objective slot.
            self.player.ship.remove_cargo(tpl.target_commodity_id, tpl.target_quantity)
            multiplier = payout_multiplier_for_tier(current_tier_id(self.player.sub_reputation))
            payout = int(tpl.base_payout_credits * multiplier)
            self.player.add_credits(payout)
            # Sub-rep reward; queues a SubReputationDelta on tier crossings.
            self.player.modify_sub_reputation(
                "wreckers_guild", tpl.sub_rep_reward, WRECKERS_GUILD_CONFIG
            )
            # Mark the mission completed for the rest of the system.
            mission_status = self.mission_manager.get_status(mission_id)
            if mission_status == MissionStatus.ACTIVE:
                # Trip COLLECT_CARGO progress + COMPLETED via the shared path.
                # The cargo is gone now, so re-check would fail — set the
                # progress flags and status manually rather than rerunning.
                self.mission_manager._status[mission_id] = MissionStatus.COMPLETED
                progress = self.mission_manager._progress.get(mission_id)
                if progress is not None:
                    for i in range(len(progress)):
                        progress[i] = True
            state.clear_active_contract(mission_id)
            state.completed_contract_count += 1
            self._last_completed_id = mission_id
            self.player.dialogue_flags[wreckers_contract_completed()] = True
            self._refresh_offers()
            self._drain_promotion_queue()
            self._create_ui()
            self._show_message(f"+{payout:,} CR. {tpl.turn_in_line}")
            return True, tpl.turn_in_line
        return False, "Nothing to turn in yet."

    def _last_completed_mission_id(self) -> Optional[str]:
        return self._last_completed_id

    # ------------------------------------------------------------------
    # Promotion drain (acceptance #6)
    # ------------------------------------------------------------------

    def _drain_promotion_queue(self) -> None:
        """Walk ``player._pending_sub_rep_deltas`` for wreckers transitions."""
        deltas = getattr(self.player, "_pending_sub_rep_deltas", None)
        if not deltas:
            return
        remaining = []
        state = self._ensure_state()
        for delta in deltas:
            if delta.org_id != "wreckers_guild":
                remaining.append(delta)
                continue
            tier_id = delta.new_tier.id
            if state.record_promotion(tier_id):
                self.player.dialogue_flags[wreckers_promoted_tier(tier_id)] = True
                self._promotion_banner = self._promotion_message(tier_id)
                self._promotion_banner_timer = 4.5
        # Replace the queue with non-wreckers deltas so other consumers
        # still see them.
        self.player._pending_sub_rep_deltas = remaining  # type: ignore[attr-defined]

    @staticmethod
    def _promotion_message(tier_id: str) -> str:
        """Return Malia's voiced promotion line for a tier id.

        Per the SA Arc Note (character_voices.md:408), the master-tier
        message must NOT include the "kid" address. The journeyman line
        keeps it.
        """
        if tier_id == "journeyman":
            return "Journeyman now, kid. Earned every rivet."
        if tier_id == "master":
            return "You walk in here as a master. The Guild knows your name."
        if tier_id == "apprentice":
            return "Apprentice. Welcome to the work."
        return ""

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process pygame_gui button presses + first-time tip overlay."""
        # Tip overlay is modal — consume events before view buttons.
        if self._tip_overlay is not None and not self._tip_overlay.dismissed:
            if self._tip_overlay.handle_event(event):
                return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self._request_back()
                return
            if event.ui_element == self.enroll_button:
                self._enroll_player()
                return
            if event.ui_element == self.make_up_button:
                self._make_up_with_malia()
                return
            if event.ui_element == self.turn_in_button:
                self._turn_in_active_contract()
                return
            for template_id, btn in list(self._accept_buttons.items()):
                if event.ui_element == btn:
                    self._accept_contract(template_id)
                    return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._request_back()

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance background animation, message + banner timers, tip overlay."""
        self.background.update(dt)
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = None
        if self._promotion_banner_timer > 0:
            self._promotion_banner_timer -= dt
            if self._promotion_banner_timer <= 0:
                self._promotion_banner = None
        if self._tip_overlay is not None:
            self._tip_overlay.update(dt)
            if self._tip_overlay.dismissed:
                self._tip_overlay = None

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface) -> None:
        """Render the Hall: header card, board, status messages."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Header card
        self._render_header(screen)

        # Body — varies by enrolled state.
        state = self._ensure_state()
        if not state.enrolled:
            self._render_enrollment_pitch(screen)
        else:
            self._render_board(screen)

        # Status / promotion banner
        if self._promotion_banner:
            self._render_banner(screen, self._promotion_banner, ACCENT_COLOR)
        elif self.message:
            self._render_banner(screen, self.message, Colors.TEXT_SECONDARY)

    def render_top(self, screen: pygame.Surface) -> None:
        """Render the first-time tip overlay above pygame_gui chrome."""
        if self._tip_overlay is not None and not self._tip_overlay.dismissed:
            self._tip_overlay.render(screen)

    def _render_header(self, screen: pygame.Surface) -> None:
        draw_panel(
            screen,
            (PANEL_X, PANEL_TOP_Y, PANEL_W, HEADER_H),
            alpha=220,
            border_color=ACCENT_COLOR,
        )
        pygame.draw.rect(screen, ACCENT_COLOR, (PANEL_X, PANEL_TOP_Y, PANEL_W, 3))
        title = self.title_font.render("WRECKERS' GUILD HALL", True, ACCENT_COLOR)
        screen.blit(title, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(14)))

        tier_id = current_tier_id(self.player.sub_reputation)
        tier = get_tier_for_rep(
            WRECKERS_GUILD_CONFIG, self.player.sub_reputation.get("wreckers_guild", 0)
        )
        sub_rep = self.player.sub_reputation.get("wreckers_guild", 0)
        state_label = "Unjoined" if not self._ensure_state().enrolled else tier.name
        label = self.subtitle_font.render(
            f"Standing: {state_label} ({sub_rep})  |  Malia Torres",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(label, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(56)))

        if self.is_locked_out():
            lockout = self.body_font.render(
                "Guild's not taking new work from you. Settle the last one first.",
                True,
                Colors.YELLOW,
            )
            screen.blit(lockout, (PANEL_X + scale_x(20), PANEL_TOP_Y + scale_y(82)))

        # Bind tier_id to suppress unused-variable warnings under mypy strict.
        _ = tier_id

    def _render_enrollment_pitch(self, screen: pygame.Surface) -> None:
        """Render the unenrolled-state body: Malia's pitch + a Sign On button."""
        body_y = BOARD_TOP_Y
        draw_panel(screen, (PANEL_X, body_y, PANEL_W, BOARD_H), alpha=210)
        lines = [
            "Malia Torres, Wrench, looks up from a stripped reactor housing.",
            '"Heard you do real work. Guild takes a cut, you take the rest. ',
            'Standing builds with completed contracts. Say the word."',
        ]
        ty = body_y + scale_y(20)
        for line in lines:
            surf = self.body_font.render(line, True, Colors.TEXT_PRIMARY)
            screen.blit(surf, (PANEL_X + scale_x(20), ty))
            ty += scale_y(24)

    def _render_board(self, screen: pygame.Surface) -> None:
        """Render the active contract board for enrolled players."""
        body_y = BOARD_TOP_Y
        draw_panel(screen, (PANEL_X, body_y, PANEL_W, BOARD_H), alpha=210)

        # Active contract summary at the top.
        state = self._ensure_state()
        info_y = body_y + scale_y(14)
        if state.active_contract_ids:
            for mission_id in state.active_contract_ids:
                mission = self.mission_manager.get_mission(mission_id)
                if mission is None:
                    continue
                tpl_id = self._template_id_from_mission_id(mission_id)
                tpl = get_template(tpl_id) if tpl_id else None
                if tpl is None:
                    continue
                have = self.player.ship.get_cargo_quantity(tpl.target_commodity_id)
                line = f"Active: {tpl.name}. {have}/{tpl.target_quantity} {tpl.target_commodity_id}"
                surf = self.subtitle_font.render(line, True, Colors.TEXT_HIGHLIGHT)
                screen.blit(surf, (PANEL_X + scale_x(20), info_y))
                info_y += scale_y(22)

        # If no offers, show empty state copy.
        if not self._offer_template_ids:
            ts = self.body_font.render(
                "No new contracts on the board. Come back after the next cycle.",
                True,
                Colors.TEXT_SECONDARY,
            )
            screen.blit(ts, (PANEL_X + scale_x(20), body_y + scale_y(180)))
            return

        # Card list — deterministic order from the slot roll.
        card_y = body_y + scale_y(180)
        for template_id in self._offer_template_ids:
            tpl = get_template(template_id)
            if tpl is None:
                continue
            self._render_offer_card(screen, tpl, card_y)
            card_y += CARD_H + CARD_PAD

    def _render_offer_card(
        self,
        screen: pygame.Surface,
        tpl: WreckersContractTemplate,
        y: int,
    ) -> None:
        """Render a single contract card."""
        card_x = PANEL_X + scale_x(20)
        card_w = PANEL_W - scale_x(40)
        draw_panel(screen, (card_x, y, card_w, CARD_H), alpha=180)
        # Tier-required strip on the left.
        tier_color = (
            (180, 220, 180)
            if tpl.tier_required == "apprentice"
            else (220, 200, 80)
            if tpl.tier_required == "journeyman"
            else ACCENT_COLOR
        )
        pygame.draw.rect(screen, tier_color, (card_x, y, scale_x(4), CARD_H))
        name = self.subtitle_font.render(tpl.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name, (card_x + scale_x(16), y + scale_y(8)))
        target_label = (
            f"Bring {tpl.target_quantity} {tpl.target_commodity_id}"
            f"  |  {tpl.base_payout_credits:,} CR base"
            f"  |  {tpl.soft_deadline_days} days"
        )
        target = self.body_font.render(target_label, True, Colors.TEXT_PRIMARY)
        screen.blit(target, (card_x + scale_x(16), y + scale_y(34)))

    def _render_banner(
        self, screen: pygame.Surface, text: str, color: tuple[int, int, int]
    ) -> None:
        surf = self.subtitle_font.render(text, True, color)
        bg = pygame.Surface((surf.get_width() + scale_x(40), surf.get_height() + scale_y(16)))
        bg.fill((10, 14, 24))
        bg.set_alpha(220)
        x = WINDOW_WIDTH // 2 - bg.get_width() // 2
        y = WINDOW_HEIGHT - scale_y(70)
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + scale_x(20), y + scale_y(8)))

    # ------------------------------------------------------------------
    # Helpers used by tests / Game wiring
    # ------------------------------------------------------------------

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 4.0

    def _request_back(self) -> None:
        """Navigate back to the station hub."""
        self.next_state = GameState.STATION_HUB

    def get_next_state(self) -> Optional[GameState]:
        """Return pending state transition (for the engine router)."""
        return self.next_state
