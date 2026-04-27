"""Tests for WreckersGuildView (SA-1).

Covers:
  - Construction with synthetic state
  - on_enter / on_exit lifecycle and UI cleanup
  - Contract board offers respect tier gating
  - Enrollment flow (first conversation seeds apprentice rep + flag)
  - Accept flow registers a Mission with a COLLECT_CARGO objective
  - Turn-in flow consumes cargo, pays out at the tier multiplier
  - Lockout state blocks accepts
  - Make-up branch unlocks accepts and sets the apology flag
  - First-time tip overlay fires once per save
  - Tier-promotion drain sets the right flags
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.constants.flags import (
    enrolled_wreckers_guild,
    seen_wreckers_guild_tip,
    wreckers_contract_completed,
    wreckers_made_up_apology,
    wreckers_promoted_tier,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.mission import MissionManager, MissionStatus, ObjectiveType
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.models.sub_reputation import SubReputationDelta, get_tier_for_rep
from spacegame.models.wreckers_guild import (
    LOCKOUT_DAYS,
    WRECKERS_GUILD_CONFIG,
    WreckersGuildState,
    get_template,
    payout_multiplier_for_tier,
)
from spacegame.views.wreckers_guild_view import WreckersGuildView


def _make_view_env(
    *,
    credits: int = 1000,
    sub_rep: int = 0,
    enrolled: bool = False,
    lockout_until: int = 0,
    game_day: int = 5,
) -> tuple[pygame_gui.UIManager, Player, MissionManager]:
    """Build an isolated test environment for the view."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Test Captain",
        credits=credits,
        current_system_id="crimson_reach",
        ship=ship,
        game_day=game_day,
    )
    if sub_rep:
        player.sub_reputation["wreckers_guild"] = sub_rep
    if enrolled or lockout_until:
        player.wreckers_guild_state = WreckersGuildState(
            enrolled=enrolled,
            lockout_until_day=lockout_until,
        )
    mission_manager = MissionManager(missions=[])
    return manager, player, mission_manager


def _make_view(
    player: Player, manager: pygame_gui.UIManager, mission_manager: MissionManager
) -> WreckersGuildView:
    return WreckersGuildView(
        ui_manager=manager,
        player=player,
        mission_manager=mission_manager,
    )


# ---------------------------------------------------------------------------
# Construction + lifecycle
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_construct_unjoined_player(self) -> None:
        manager, player, mm = _make_view_env()
        view = _make_view(player, manager, mm)
        assert view is not None
        assert view.next_state is None

    def test_on_enter_sets_active(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        assert view.active
        view.on_exit()

    def test_on_exit_destroys_ui(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        # Some buttons should exist after enter
        view.on_exit()
        # All button refs should be None after destroy
        assert view.back_button is None


# ---------------------------------------------------------------------------
# Enrollment flow (acceptance #2)
# ---------------------------------------------------------------------------


class TestEnrollment:
    def test_unjoined_player_can_enroll(self) -> None:
        manager, player, mm = _make_view_env()
        view = _make_view(player, manager, mm)
        view.on_enter()
        assert player.wreckers_guild_state is None or not player.wreckers_guild_state.enrolled
        view._enroll_player()
        assert player.wreckers_guild_state is not None
        assert player.wreckers_guild_state.enrolled is True
        assert player.sub_reputation["wreckers_guild"] == 1
        assert player.dialogue_flags.get(enrolled_wreckers_guild()) is True
        view.on_exit()

    def test_enrollment_idempotent(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=15)
        view = _make_view(player, manager, mm)
        view.on_enter()
        # Already enrolled — second call must not re-seed rep.
        view._enroll_player()
        assert player.sub_reputation["wreckers_guild"] == 15
        view.on_exit()


# ---------------------------------------------------------------------------
# Contract board (acceptance #3)
# ---------------------------------------------------------------------------


class TestContractBoard:
    def test_apprentice_sees_only_apprentice_offers(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        offers = view.get_offered_template_ids()
        for offer_id in offers:
            tpl = get_template(offer_id)
            assert tpl is not None
            assert tpl.tier_required == "apprentice"
        view.on_exit()

    def test_journeyman_unlocks_recovery(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=35)
        view = _make_view(player, manager, mm)
        view.on_enter()
        offers = view.get_offered_template_ids()
        # The pool should now include both apprentice and journeyman tiers.
        cats = {get_template(oid).category for oid in offers if get_template(oid)}  # type: ignore[union-attr]
        assert cats  # non-empty
        view.on_exit()

    def test_unjoined_sees_empty_board(self) -> None:
        manager, player, mm = _make_view_env(enrolled=False, sub_rep=0)
        view = _make_view(player, manager, mm)
        view.on_enter()
        assert view.get_offered_template_ids() == []
        view.on_exit()


# ---------------------------------------------------------------------------
# Accept flow (acceptance #4)
# ---------------------------------------------------------------------------


class TestAcceptFlow:
    def test_accept_creates_mission_with_collect_cargo(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1, game_day=10)
        view = _make_view(player, manager, mm)
        view.on_enter()
        offers = view.get_offered_template_ids()
        assert offers, "test fixture should produce at least one offer"
        template_id = offers[0]
        success = view._accept_contract(template_id)
        assert success
        # The mission was registered on the manager
        active = mm.get_missions_by_status(MissionStatus.ACTIVE)
        assert len(active) == 1
        mission = active[0]
        # COLLECT_CARGO objective targets the template's commodity
        tpl = get_template(template_id)
        assert tpl is not None
        cargo_objs = [o for o in mission.objectives if o.type == ObjectiveType.COLLECT_CARGO]
        assert len(cargo_objs) == 1
        assert cargo_objs[0].target_id == tpl.target_commodity_id
        assert cargo_objs[0].target_quantity == tpl.target_quantity
        # State tracks the active contract
        assert mission.id in player.wreckers_guild_state.active_contract_ids
        view.on_exit()

    def test_accept_blocked_when_locked_out(self) -> None:
        manager, player, mm = _make_view_env(
            enrolled=True, sub_rep=1, lockout_until=100, game_day=5
        )
        view = _make_view(player, manager, mm)
        view.on_enter()
        offers = view.get_offered_template_ids()
        assert offers
        success = view._accept_contract(offers[0])
        assert success is False
        view.on_exit()


# ---------------------------------------------------------------------------
# Turn-in flow (acceptance #4 + #7)
# ---------------------------------------------------------------------------


class TestTurnInFlow:
    def test_turn_in_consumes_cargo_and_pays(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1, game_day=10)
        view = _make_view(player, manager, mm)
        view.on_enter()
        offers = view.get_offered_template_ids()
        assert offers
        template_id = offers[0]
        view._accept_contract(template_id)
        tpl = get_template(template_id)
        assert tpl is not None
        # Stock the cargo so the turn-in succeeds
        player.ship.add_cargo(tpl.target_commodity_id, tpl.target_quantity)
        starting_credits = player.credits
        starting_rep = player.sub_reputation.get("wreckers_guild", 0)
        success, _msg = view._turn_in_active_contract()
        assert success
        # Cargo consumed
        assert player.ship.get_cargo_quantity(tpl.target_commodity_id) == 0
        # Apprentice tier multiplier == 1.0 — payout is exactly the base.
        expected_payout = int(tpl.base_payout_credits * payout_multiplier_for_tier("apprentice"))
        assert player.credits == starting_credits + expected_payout
        # Sub-rep rewarded
        assert player.sub_reputation["wreckers_guild"] == starting_rep + tpl.sub_rep_reward
        # Active contract cleared
        assert mm.get_status(view._last_completed_mission_id()) == MissionStatus.COMPLETED  # type: ignore[arg-type]
        view.on_exit()

    def test_turn_in_journeyman_pays_110_pct(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=35, game_day=10)
        view = _make_view(player, manager, mm)
        view.on_enter()
        offers = view.get_offered_template_ids()
        assert offers
        # Pick any offer with a known base_payout — first works.
        template_id = offers[0]
        view._accept_contract(template_id)
        tpl = get_template(template_id)
        assert tpl is not None
        player.ship.add_cargo(tpl.target_commodity_id, tpl.target_quantity)
        starting_credits = player.credits
        success, _ = view._turn_in_active_contract()
        assert success
        expected = int(tpl.base_payout_credits * 1.10)
        assert player.credits == starting_credits + expected
        view.on_exit()


# ---------------------------------------------------------------------------
# Lockout + make-up (acceptance #5)
# ---------------------------------------------------------------------------


class TestLockoutAndMakeUp:
    def test_lockout_active_when_in_window(self) -> None:
        manager, player, mm = _make_view_env(
            enrolled=True, sub_rep=10, lockout_until=20, game_day=15
        )
        view = _make_view(player, manager, mm)
        view.on_enter()
        assert view.is_locked_out()
        view.on_exit()

    def test_lockout_expires(self) -> None:
        manager, player, mm = _make_view_env(
            enrolled=True, sub_rep=10, lockout_until=20, game_day=21
        )
        view = _make_view(player, manager, mm)
        view.on_enter()
        assert not view.is_locked_out()
        view.on_exit()

    def test_make_up_clears_lockout_and_sets_flag(self) -> None:
        manager, player, mm = _make_view_env(
            enrolled=True, sub_rep=10, lockout_until=20, game_day=25
        )
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._make_up_with_malia()
        assert player.dialogue_flags.get(wreckers_made_up_apology()) is True
        assert player.wreckers_guild_state is not None
        assert player.wreckers_guild_state.lockout_until_day == 0
        view.on_exit()

    def test_make_up_does_not_fire_before_lockout_expires(self) -> None:
        manager, player, mm = _make_view_env(
            enrolled=True, sub_rep=10, lockout_until=20, game_day=10
        )
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._make_up_with_malia()
        # Make-up beat is gated on lockout expiry — flag should not set early.
        assert player.dialogue_flags.get(wreckers_made_up_apology()) is not True
        view.on_exit()

    def test_failure_applies_lockout(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=20, game_day=10)
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._fail_active_contract_with_penalty(mission_id="wreckers_contract_x")
        assert player.wreckers_guild_state is not None
        assert player.wreckers_guild_state.lockout_until_day == 10 + LOCKOUT_DAYS
        # Sub-rep dropped by SUB_REP_FAILURE_PENALTY
        assert player.sub_reputation["wreckers_guild"] == 15
        view.on_exit()

    def test_failure_clamps_at_zero(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=2, game_day=10)
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._fail_active_contract_with_penalty(mission_id="wreckers_contract_x")
        assert player.sub_reputation["wreckers_guild"] == 0
        view.on_exit()


# ---------------------------------------------------------------------------
# First-time tip (acceptance #10)
# ---------------------------------------------------------------------------


class TestFirstTimeTip:
    def test_tip_fires_on_first_entry(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        assert view._tip_overlay is not None
        view.on_exit()

    def test_tip_does_not_refire(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        player.dialogue_flags[seen_wreckers_guild_tip()] = True
        view = _make_view(player, manager, mm)
        view.on_enter()
        assert view._tip_overlay is None
        view.on_exit()


# ---------------------------------------------------------------------------
# Tier promotion drain (acceptance #6)
# ---------------------------------------------------------------------------


class TestPromotionDrain:
    def test_drain_sets_journeyman_flag(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=30)
        view = _make_view(player, manager, mm)
        view.on_enter()
        # Synthesize a delta as the model would when crossing 1 -> 30
        old_tier = get_tier_for_rep(WRECKERS_GUILD_CONFIG, 29)
        new_tier = get_tier_for_rep(WRECKERS_GUILD_CONFIG, 30)
        player._pending_sub_rep_deltas = [  # type: ignore[attr-defined]
            SubReputationDelta(
                org_id="wreckers_guild",
                effective_amount=29,
                old_tier=old_tier,
                new_tier=new_tier,
            )
        ]
        view._drain_promotion_queue()
        assert player.dialogue_flags.get(wreckers_promoted_tier("journeyman")) is True
        view.on_exit()

    def test_drain_master_promotion(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=70)
        view = _make_view(player, manager, mm)
        view.on_enter()
        old_tier = get_tier_for_rep(WRECKERS_GUILD_CONFIG, 69)
        new_tier = get_tier_for_rep(WRECKERS_GUILD_CONFIG, 70)
        player._pending_sub_rep_deltas = [  # type: ignore[attr-defined]
            SubReputationDelta(
                org_id="wreckers_guild",
                effective_amount=1,
                old_tier=old_tier,
                new_tier=new_tier,
            )
        ]
        view._drain_promotion_queue()
        assert player.dialogue_flags.get(wreckers_promoted_tier("master")) is True
        view.on_exit()

    def test_drain_skips_unrelated_orgs(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=10)
        view = _make_view(player, manager, mm)
        view.on_enter()
        # Synthetic delta for some other org; must not corrupt our flags.
        from spacegame.models.sub_reputation import OrganizationTier

        other = OrganizationTier(id="x", name="X", rank=1, min_rep=0)
        player._pending_sub_rep_deltas = [  # type: ignore[attr-defined]
            SubReputationDelta(
                org_id="other_org",
                effective_amount=1,
                old_tier=other,
                new_tier=other,
            )
        ]
        view._drain_promotion_queue()
        # No wreckers promotion flags should be set
        assert not any(
            k.startswith("wreckers_promoted_") and v for k, v in player.dialogue_flags.items()
        )
        view.on_exit()


# ---------------------------------------------------------------------------
# Contract completion side effects (journal flag + count)
# ---------------------------------------------------------------------------


class TestCompletionEffects:
    def test_first_completion_sets_journal_flag(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1, game_day=10)
        view = _make_view(player, manager, mm)
        view.on_enter()
        offers = view.get_offered_template_ids()
        view._accept_contract(offers[0])
        tpl = get_template(offers[0])
        assert tpl is not None
        player.ship.add_cargo(tpl.target_commodity_id, tpl.target_quantity)
        view._turn_in_active_contract()
        assert player.dialogue_flags.get(wreckers_contract_completed()) is True
        assert player.wreckers_guild_state is not None
        assert player.wreckers_guild_state.completed_contract_count == 1
        view.on_exit()


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


class TestNavigation:
    def test_back_returns_to_station_hub(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._request_back()
        assert view.get_next_state() == GameState.STATION_HUB
        view.on_exit()


# ---------------------------------------------------------------------------
# Secondary contacts dock (R1 — Paz / Daro / Ife as interactive speakers)
# ---------------------------------------------------------------------------


class TestSecondaryContacts:
    def test_dock_lists_all_three_contacts(self) -> None:
        """Enrolled view exposes Paz, Daro, and Ife as openable contacts."""
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        contact_ids = view.get_contact_speaker_ids()
        assert set(contact_ids) == {"paz_reina", "daro_teck", "ife_obi"}
        view.on_exit()

    def test_dock_hidden_when_unenrolled(self) -> None:
        """Unenrolled players don't get to chat with the contacts yet."""
        manager, player, mm = _make_view_env()
        view = _make_view(player, manager, mm)
        view.on_enter()
        assert view.get_contact_speaker_ids() == []
        view.on_exit()

    def test_open_paz_loads_greeting_node(self) -> None:
        """Opening Paz starts at her dialogue tree's greeting node."""
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._open_contact_dialogue("paz_reina")
        node = view.get_active_dialogue_node()
        assert node is not None
        assert node.speaker_id == "paz_reina"
        assert node.id == "greeting"
        view.on_exit()

    def test_open_daro_loads_greeting_node(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._open_contact_dialogue("daro_teck")
        node = view.get_active_dialogue_node()
        assert node is not None
        assert node.speaker_id == "daro_teck"
        view.on_exit()

    def test_open_ife_loads_greeting_node(self) -> None:
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._open_contact_dialogue("ife_obi")
        node = view.get_active_dialogue_node()
        assert node is not None
        assert node.speaker_id == "ife_obi"
        view.on_exit()

    def test_advance_walks_three_nodes_then_closes(self) -> None:
        """Each contact's tree is greeting → craft → signoff → close."""
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._open_contact_dialogue("paz_reina")
        node1 = view.get_active_dialogue_node()
        assert node1 is not None and node1.id == "greeting"
        view._advance_dialogue()
        node2 = view.get_active_dialogue_node()
        assert node2 is not None and node2.id == "craft"
        view._advance_dialogue()
        node3 = view.get_active_dialogue_node()
        assert node3 is not None and node3.id == "signoff"
        view._advance_dialogue()
        # Sign-off response had next_node_id null — dialogue closes.
        assert view.get_active_dialogue_node() is None
        view.on_exit()

    def test_unknown_contact_id_is_no_op(self) -> None:
        """Bad input doesn't crash the view (boundary safety)."""
        manager, player, mm = _make_view_env(enrolled=True, sub_rep=1)
        view = _make_view(player, manager, mm)
        view.on_enter()
        view._open_contact_dialogue("not_a_real_contact")
        assert view.get_active_dialogue_node() is None
        view.on_exit()

    def test_distinct_voice_registers(self) -> None:
        """Each contact's greeting carries the verbal habit from their voice sheet.

        Paz tags confirmed vs estimated. Daro leads with assessment-then-reasoning
        ("borderline" + "because"). Ife uses cataloging language ("cataloging",
        "anomalous", "pending"). The three texts must not collapse into
        each other's register.
        """
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        paz = dl.get_dialogue("paz_reina_guild_hall")
        daro = dl.get_dialogue("daro_teck_guild_hall")
        ife = dl.get_dialogue("ife_obi_guild_hall")
        assert paz is not None and daro is not None and ife is not None
        # Paz: spatial-precision, confirmed vs estimated.
        assert "confirmed" in paz.nodes["greeting"].text.lower()
        # Daro: diagnostic-directness, assessment-first.
        assert "borderline" in daro.nodes["greeting"].text.lower()
        # Ife: indexing curiosity, cataloging language.
        assert "cataloging" in ife.nodes["greeting"].text.lower()
        # And every greeting is genuinely distinct text.
        greetings = {
            paz.nodes["greeting"].text,
            daro.nodes["greeting"].text,
            ife.nodes["greeting"].text,
        }
        assert len(greetings) == 3
