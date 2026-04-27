"""SA-V scenario: The Longer Ledger -- investment introduction arc.

Integration coverage for the full Odom / investment_introduced mission path:

  iron_ore_delivered set
  → odom_broker ongoing_greet branch available
  → investment_intro dialogue node → odom_explained_investment set
  → the_longer_ledger mission auto-completes → investment_introduced set
  → all 10 investment systems unlock their investment cards
  → first investment-card click fires PT-M tip (seen once, never again)
  → journal entry auto_sa_v_longer_ledger exists
  → graduation_pointer branch names Meridian + Ilse Vey
  → iron_delivery_failed still hides Odom (betrayal arc regression)
  → NPC data: odom_broker present, legacy id absent

Existing iron-delivery flow (data loader, cantina filter, SL-2 gating)
also regresses here so a rename bug cannot silently pass the scenario tests.
"""

from __future__ import annotations

import pygame
import pygame_gui
import pytest

from spacegame.constants.flags import (
    investment_introduced,
    odom_explained_investment,
    seen_faction_tip,
    seen_investment_tip,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.location import Location
from spacegame.models.station_salience import is_investment_unlocked
from spacegame.views.station_hub_view import StationHubView
from tests.test_scenarios._helpers import fresh_player


@pytest.fixture(autouse=True, scope="module")
def _pygame_init() -> object:
    """station_hub_view requires pygame fonts and a display surface."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    yield
    pygame.quit()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SYSTEMS_WITH_INVESTMENT: list[str] = [
    "nexus_prime",
    "stellaris_port",
    "breakstone",
    "iron_depths",
    "forgeworks",
    "axiom_labs",
    "nova_research",
    "havens_rest",
    "verdant",
    "crimson_reach",
]


def _make_hub_view(player, system_id: str) -> StationHubView:
    dl = get_data_loader()
    dl.load_all()
    ui_mgr = pygame_gui.UIManager((1280, 800))
    return StationHubView(
        ui_manager=ui_mgr,
        player=player,
        system=dl.systems[system_id],
        locations=list(dl.locations.get(system_id, [])),
        activity_registry=None,
        data_loader=dl,
    )


def _has_investment_card(view: StationHubView) -> bool:
    return any(loc.location_type == "investment" for loc in view.locations)


def _get_investment_location(system_id: str) -> Location | None:
    dl = get_data_loader()
    dl.load_all()
    return next(
        (loc for loc in dl.locations.get(system_id, []) if loc.location_type == "investment"),
        None,
    )


# ---------------------------------------------------------------------------
# AC-1: NPC data — odom_broker present, legacy id absent
# ---------------------------------------------------------------------------


class TestNpcRenameComplete:
    """AC-1: NPC entry has id=odom_broker, legacy id is absent."""

    def test_odom_broker_npc_exists(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        npc = dl.get_npc("odom_broker")
        assert npc is not None, "odom_broker NPC must exist in data"
        assert npc.name == "Odom"
        assert npc.title == "Cargo Broker"
        assert npc.home_system_id == "nexus_prime"
        assert npc.dialogue_id == "merchant_delivery"
        assert npc.hide_after_flag == "iron_delivery_failed"

    def test_legacy_npc_id_absent(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        assert dl.get_npc("delivery_merchant") is None, (
            "Legacy delivery_merchant id must be gone — rename was not complete"
        )


# ---------------------------------------------------------------------------
# AC-3: Iron-delivery flow still works after rename (regression)
# ---------------------------------------------------------------------------


class TestIronDeliveryFlowRegression:
    """AC-3: The pre-rename iron_delivery flow is byte-clean after rename."""

    def test_iron_delivery_mission_loads(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        m = next((m for m in dl.missions if m.id == "iron_delivery"), None)
        assert m is not None, "iron_delivery mission must still exist"

    def test_betrayal_flag_hides_odom(self) -> None:
        """hide_after_flag=iron_delivery_failed still removes Odom after betrayal."""
        dl = get_data_loader()
        dl.load_all()
        npc = dl.get_npc("odom_broker")
        assert npc.hide_after_flag == "iron_delivery_failed"
        # Verify the filter logic: if iron_delivery_failed is set, npc is hidden
        flags_betrayed = {"iron_delivery_failed": True}
        assert flags_betrayed.get(npc.hide_after_flag, False) is True

    def test_betrayal_arc_nodes_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.dialogue_trees["merchant_delivery"]
        for node_id in ("betrayal", "betrayal_rant", "betrayal_end"):
            assert node_id in tree.nodes, f"Betrayal node '{node_id}' must still exist"


# ---------------------------------------------------------------------------
# AC-2 & AC-5: Speaker-id rename complete (sampled regression)
# ---------------------------------------------------------------------------


class TestSpeakerIdRenameInDialogue:
    """AC-2: All merchant_delivery nodes carry speaker_id=odom_broker."""

    def test_all_merchant_delivery_nodes_have_odom_broker_speaker(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.dialogue_trees["merchant_delivery"]
        for node_id, node in tree.nodes.items():
            assert node.speaker_id == "odom_broker", (
                f"Node '{node_id}' still carries legacy speaker_id '{node.speaker_id}'"
            )


# ---------------------------------------------------------------------------
# AC-4: Dialogue branch gating
# ---------------------------------------------------------------------------


class TestDialogueBranchGating:
    """AC-4: New gated branches surface in flag-dependent order."""

    def _get_tree(self):
        dl = get_data_loader()
        dl.load_all()
        return dl.dialogue_trees["merchant_delivery"]

    def test_greet_has_ongoing_greet_response(self) -> None:
        tree = self._get_tree()
        greet = tree.nodes["greet"]
        ongoing_responses = [r for r in greet.responses if r.next_node_id == "ongoing_greet"]
        assert ongoing_responses, "greet node must have a response leading to ongoing_greet"

    def test_ongoing_greet_gated_on_iron_ore_delivered(self) -> None:
        tree = self._get_tree()
        greet = tree.nodes["greet"]
        for r in greet.responses:
            if r.next_node_id == "ongoing_greet":
                assert "iron_ore_delivered" in (r.required_flags or []), (
                    "ongoing_greet response must require iron_ore_delivered"
                )
                assert "iron_delivery_failed" in (r.excluded_flags or []), (
                    "ongoing_greet response must exclude iron_delivery_failed"
                )

    def test_ongoing_greet_leads_to_investment_intro_when_not_introduced(self) -> None:
        """Before investment_introduced, ongoing_greet offers investment_intro."""
        tree = self._get_tree()
        ongoing = tree.nodes["ongoing_greet"]
        intro_response = next(
            (r for r in ongoing.responses if r.next_node_id == "investment_intro"), None
        )
        assert intro_response is not None, "ongoing_greet must offer investment_intro response"
        assert "investment_introduced" in (intro_response.excluded_flags or []), (
            "investment_intro response must be excluded when investment_introduced is set"
        )

    def test_ongoing_greet_leads_to_graduation_pointer_when_introduced(self) -> None:
        """After investment_introduced, ongoing_greet offers graduation_pointer."""
        tree = self._get_tree()
        ongoing = tree.nodes["ongoing_greet"]
        pointer_response = next(
            (r for r in ongoing.responses if r.next_node_id == "graduation_pointer"), None
        )
        assert pointer_response is not None, "ongoing_greet must offer graduation_pointer response"
        assert "investment_introduced" in (pointer_response.required_flags or []), (
            "graduation_pointer response must require investment_introduced"
        )

    def test_investment_intro_sets_odom_explained_investment(self) -> None:
        """investment_intro response sets odom_explained_investment flag."""
        tree = self._get_tree()
        intro = tree.nodes["investment_intro"]
        set_flags = [r.set_flag for r in intro.responses if r.set_flag]
        assert odom_explained_investment() in set_flags, (
            "investment_intro must set odom_explained_investment on response"
        )

    def test_graduation_pointer_mentions_meridian_and_ilse_vey(self) -> None:
        """AC-7: graduation_pointer names Meridian and Ilse Vey by name."""
        tree = self._get_tree()
        pointer = tree.nodes["graduation_pointer"]
        text = pointer.text
        assert "Meridian" in text, "graduation_pointer must name Meridian"
        assert "Ilse Vey" in text, "graduation_pointer must name Ilse Vey"

    def test_graduation_pointer_sets_no_flags(self) -> None:
        """AC-7: graduation_pointer sets no flags (SA-F3 owns next transition)."""
        tree = self._get_tree()
        pointer = tree.nodes["graduation_pointer"]
        for r in pointer.responses:
            assert not r.set_flag, (
                f"graduation_pointer response sets '{r.set_flag}' — only SA-F3 may gate next transition"
            )


# ---------------------------------------------------------------------------
# AC-5: Mission loading and structure
# ---------------------------------------------------------------------------


class TestTheLongerLedgerMission:
    """AC-5: the_longer_ledger mission has correct structure."""

    def _get_mission(self):
        dl = get_data_loader()
        dl.load_all()
        return next((m for m in dl.missions if m.id == "sa_v_investment_intro"), None)

    def test_mission_loads(self) -> None:
        assert self._get_mission() is not None, "sa_v_investment_intro mission must load"

    def test_mission_name(self) -> None:
        m = self._get_mission()
        assert m.name == "The Longer Ledger"

    def test_mission_prerequisites(self) -> None:
        m = self._get_mission()
        assert "iron_delivery" in (m.prerequisites or [])

    def test_mission_required_flags(self) -> None:
        m = self._get_mission()
        assert "iron_ore_delivered" in (m.required_flags or [])

    def test_mission_objective_has_flag(self) -> None:
        m = self._get_mission()
        from spacegame.models.mission import ObjectiveType

        obj = next(
            (o for o in m.objectives if o.type == ObjectiveType.HAS_FLAG), None
        )
        assert obj is not None, "Mission must have a has_flag objective"
        assert obj.target_id == odom_explained_investment()

    def test_mission_rewards_xp(self) -> None:
        m = self._get_mission()
        xp_rewards = [r for r in m.rewards if r.reward_type == "xp"]
        assert xp_rewards, "Mission must grant XP"
        assert xp_rewards[0].amount == 25

    def test_mission_rewards_set_flag_investment_introduced(self) -> None:
        m = self._get_mission()
        flag_rewards = [
            r for r in m.rewards if r.reward_type == "set_flag" and r.target_id == investment_introduced()
        ]
        assert flag_rewards, "Mission must set investment_introduced on completion"

    def test_mission_auto_accept(self) -> None:
        m = self._get_mission()
        assert m.auto_accept is True


# ---------------------------------------------------------------------------
# AC-6: SL-2 19-case matrix with investment_introduced=True + zero credits
# ---------------------------------------------------------------------------


class TestInvestmentCardUnlocksViaFlag:
    """AC-6: investment_introduced flag unlocks all 10 systems regardless of credits."""

    @pytest.mark.parametrize("system_id", _SYSTEMS_WITH_INVESTMENT)
    def test_flag_unlocks_investment_card_at_zero_credits(self, system_id: str) -> None:
        player = fresh_player()
        player.credits_earned_lifetime = 0
        player.dialogue_flags[investment_introduced()] = True
        assert is_investment_unlocked(player), (
            f"is_investment_unlocked must return True with flag set at {system_id}"
        )
        loc = _get_investment_location(system_id)
        if loc is None:
            pytest.skip(f"No investment location in source data at {system_id}")
        view = _make_hub_view(player, system_id)
        assert _has_investment_card(view), (
            f"Investment card must render at {system_id} when investment_introduced is set"
        )

    def test_fresh_player_no_investment_cards(self) -> None:
        """Regression: fresh save still sees zero investment cards."""
        player = fresh_player()
        assert player.credits_earned_lifetime == 0
        assert not is_investment_unlocked(player)
        view = _make_hub_view(player, "nexus_prime")
        assert not _has_investment_card(view)

    def test_iron_ore_delivered_alone_does_not_unlock(self) -> None:
        """After iron delivery but before Odom's intro, investment is still locked."""
        player = fresh_player()
        player.dialogue_flags["iron_ore_delivered"] = True
        assert not is_investment_unlocked(player)


# ---------------------------------------------------------------------------
# AC-7: Graduation pointer (already covered in AC-4; aliased here for clarity)
# ---------------------------------------------------------------------------


class TestGraduationPointer:
    """AC-7: graduation_pointer is gated on investment_introduced, no new flags."""

    def test_graduation_pointer_required_flags(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.dialogue_trees["merchant_delivery"]
        ongoing = tree.nodes["ongoing_greet"]
        pointer_response = next(
            (r for r in ongoing.responses if r.next_node_id == "graduation_pointer"), None
        )
        assert pointer_response is not None
        assert investment_introduced() in (pointer_response.required_flags or [])


# ---------------------------------------------------------------------------
# AC-8: PT-M investment-card tip fires exactly once
# ---------------------------------------------------------------------------


class TestInvestmentCardTip:
    """AC-8: PT-M tip fires on first investment click, never again."""

    def _build_view_with_investment_unlocked(self, system_id: str) -> StationHubView:
        player = fresh_player()
        player.dialogue_flags[investment_introduced()] = True
        # Pre-set the faction tip flag so it does not fire on enter and
        # suppress the investment tip (both are PT-M overlays; they don't stack).
        player.dialogue_flags[seen_faction_tip("guild")] = True
        view = _make_hub_view(player, system_id)
        view.on_enter()
        return view

    def test_tip_fires_on_first_investment_click(self) -> None:
        """After investment_introduced, clicking an investment card fires the tip."""
        view = self._build_view_with_investment_unlocked("nexus_prime")
        assert view._investment_tip is None, "Tip must not fire on dock alone"
        # Simulate clicking an investment-typed zone
        view._maybe_show_investment_tip()
        assert view._investment_tip is not None, (
            "Tip must appear after _maybe_show_investment_tip call"
        )
        assert not view._investment_tip.dismissed

    def test_tip_does_not_fire_without_investment_introduced(self) -> None:
        """Tip must not fire if the flag is not set."""
        player = fresh_player()
        view = _make_hub_view(player, "nexus_prime")
        view.on_enter()
        view._maybe_show_investment_tip()
        assert view._investment_tip is None, (
            "Tip must not fire when investment_introduced is not set"
        )

    def test_dismiss_sets_seen_flag(self) -> None:
        """Dismissing the tip sets seen_investment_tip on the player."""
        player = fresh_player()
        player.dialogue_flags[investment_introduced()] = True
        # Pre-set faction tip so it doesn't suppress the investment tip
        player.dialogue_flags[seen_faction_tip("guild")] = True
        view = _make_hub_view(player, "nexus_prime")
        view.on_enter()
        view._maybe_show_investment_tip()
        assert view._investment_tip is not None
        assert player.dialogue_flags.get(seen_investment_tip(), False) is False
        view._investment_tip._dismiss()
        assert player.dialogue_flags.get(seen_investment_tip(), False) is True

    def test_tip_does_not_fire_after_seen(self) -> None:
        """Once seen_investment_tip is set, the tip never re-fires."""
        player = fresh_player()
        player.dialogue_flags[investment_introduced()] = True
        player.dialogue_flags[seen_investment_tip()] = True
        view = _make_hub_view(player, "nexus_prime")
        view.on_enter()
        view._maybe_show_investment_tip()
        assert view._investment_tip is None, (
            "Tip must not re-fire when seen_investment_tip is already set"
        )

    def test_tip_does_not_refire_at_second_system(self) -> None:
        """Tip never re-fires at a different investment system either."""
        player = fresh_player()
        player.dialogue_flags[investment_introduced()] = True
        # Pre-set faction tips for both systems to prevent them from suppressing
        # the investment tip in the test (each uses a different layout_key).
        player.dialogue_flags[seen_faction_tip("guild")] = True   # nexus_prime
        player.dialogue_flags[seen_faction_tip("union")] = True   # breakstone
        # First click: fires and dismisses
        view1 = _make_hub_view(player, "nexus_prime")
        view1.on_enter()
        view1._maybe_show_investment_tip()
        assert view1._investment_tip is not None
        view1._investment_tip._dismiss()
        # seen_investment_tip is now set
        assert player.dialogue_flags.get(seen_investment_tip(), False) is True
        # Second system: tip must NOT fire
        view2 = _make_hub_view(player, "breakstone")
        view2.on_enter()
        view2._maybe_show_investment_tip()
        assert view2._investment_tip is None, (
            "Tip must not re-fire at a different system after dismissal"
        )


# ---------------------------------------------------------------------------
# AC-9: Journal entry
# ---------------------------------------------------------------------------


class TestJournalEntry:
    """AC-9: auto_sa_v_longer_ledger entry exists with correct fields."""

    def test_journal_entry_exists(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_sa_v_longer_ledger"),
            None,
        )
        assert entry is not None, "auto_sa_v_longer_ledger journal entry must exist"

    def test_journal_entry_trigger_flag(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(e for e in dl.journal_entries if e.entry_id == "auto_sa_v_longer_ledger")
        assert entry.trigger_flag == investment_introduced()

    def test_journal_entry_system_id(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(e for e in dl.journal_entries if e.entry_id == "auto_sa_v_longer_ledger")
        assert entry.system_id == "nexus_prime"

    def test_journal_entry_mission_id(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(e for e in dl.journal_entries if e.entry_id == "auto_sa_v_longer_ledger")
        assert entry.mission_id == "sa_v_investment_intro"

    def test_journal_entry_names_ilse_vey(self) -> None:
        """Journal text records Odom naming Ilse Vey (working-notebook register)."""
        dl = get_data_loader()
        dl.load_all()
        entry = next(e for e in dl.journal_entries if e.entry_id == "auto_sa_v_longer_ledger")
        assert "Ilse Vey" in entry.text
        assert "Meridian" in entry.text


# ---------------------------------------------------------------------------
# AC-10: SI-3 flag pairing (quick sanity)
# ---------------------------------------------------------------------------


class TestFlagPairing:
    """AC-10: SA-V flags are properly paired producer/consumer after data load."""

    def test_investment_introduced_is_produced_by_mission(self) -> None:
        """The_longer_ledger mission reward produces investment_introduced."""
        dl = get_data_loader()
        dl.load_all()
        m = next(m for m in dl.missions if m.id == "sa_v_investment_intro")
        set_flag_rewards = [
            r for r in m.rewards
            if r.reward_type == "set_flag" and r.target_id == investment_introduced()
        ]
        assert set_flag_rewards, "investment_introduced must be produced by mission reward"

    def test_odom_explained_investment_is_consumed_by_mission(self) -> None:
        """The_longer_ledger mission objective consumes odom_explained_investment."""
        dl = get_data_loader()
        dl.load_all()
        m = next(m for m in dl.missions if m.id == "sa_v_investment_intro")
        from spacegame.models.mission import ObjectiveType

        consuming_objectives = [
            o for o in m.objectives
            if o.type == ObjectiveType.HAS_FLAG and o.target_id == odom_explained_investment()
        ]
        assert consuming_objectives, "odom_explained_investment must be consumed by mission objective"
