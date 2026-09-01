"""End-to-end scenario for D4 Truth vs Vengeance (A2-12).

Drives the loaded dilemma record through the coordinator and the model-
layer :func:`resolve` path, then asserts the observable player-facing
consequences the sprint promised:

- Loader parses ``data/narrative/dilemmas/d4_truth_vengeance.json``.
- Integrity guard helpers accept the record.
- Single-pole investment does not collide; two-pole investment does.
- Truth-wins closes ``vengeance`` and routes Aldric Senn's NPC record
  to the ``senn_truth_confrontation`` dialogue state.
- Vengeance-wins closes ``truth`` and makes the Priya scar chatter
  line reachable via :class:`StationChatterManager` filtering.
- The Act I ``the_ledger`` mission seed
  (``told_senn_orchestrated_operation``) is present in the flag
  registry and settable through ``player.dialogue_flags``.

Consumer path for AC5: this sprint chose scar ``ChatterLine`` only per
the locked decision in the sprint plan. The test filters chatter via
``StationChatterManager.get_chatter`` and asserts the D4-authored line
appears when ``lens_closed_truth`` is set. Priya's own dialogue tree is
NOT gated on this flag by design.
"""

from __future__ import annotations

import pytest

from spacegame.constants import flags as flag_registry
from spacegame.data_loader import get_data_loader
from spacegame.models.dilemma import (
    check_collision,
    resolve,
)
from spacegame.models.lens_investment import LensInvestment
from tests.test_compliance.test_dilemma_integrity import (
    _dilemmas_with_bad_thresholds,
    _outcomes_with_empty_tier_unlocks,
)
from tests.test_scenarios._helpers import fresh_player

D4_ID = "d4_truth_vengeance"


@pytest.fixture(scope="module")
def d4_dilemma():
    """Return the loaded D4 dilemma from the singleton DataLoader."""
    dl = get_data_loader()
    dl.load_all()
    assert D4_ID in dl.dilemmas, (
        f"{D4_ID} not loaded from data/narrative/dilemmas/. Available: {sorted(dl.dilemmas.keys())}"
    )
    return dl.dilemmas[D4_ID]


class TestD4Loads:
    """AC1: DataLoader parses the D4 record with both outcomes populated."""

    def test_dilemma_loads(self, d4_dilemma) -> None:
        assert d4_dilemma.id == D4_ID
        assert set(d4_dilemma.poles) == {"truth", "vengeance"}
        assert d4_dilemma.collision_requires == 2
        assert d4_dilemma.telegraph_threshold == 55
        assert d4_dilemma.collision_threshold == 80
        assert d4_dilemma.telegraph_npc_id == "dr_priya_osei"
        assert len(d4_dilemma.telegraph_lines) >= 2, (
            "D4 sprint deliverable calls for 2-3 telegraph lines"
        )
        assert len(d4_dilemma.outcomes) == 2, "One outcome per pole"

    def test_outcomes_named_correctly(self, d4_dilemma) -> None:
        by_lens = {o.winning_lens_id: o for o in d4_dilemma.outcomes}
        assert set(by_lens.keys()) == {"truth", "vengeance"}
        assert by_lens["truth"].closes == ["vengeance"]
        assert by_lens["vengeance"].closes == ["truth"]
        assert by_lens["truth"].outcome_flag == "d4_truth_won"
        assert by_lens["vengeance"].outcome_flag == "d4_vengeance_won"


class TestD4IntegrityGuardPasses:
    """AC2: the integrity-guard helpers accept the D4 record."""

    def test_no_empty_tier_unlocks(self, d4_dilemma) -> None:
        assert _outcomes_with_empty_tier_unlocks({D4_ID: d4_dilemma}) == []

    def test_thresholds_strictly_ordered(self, d4_dilemma) -> None:
        assert _dilemmas_with_bad_thresholds({D4_ID: d4_dilemma}) == []


class TestD4CollisionMath:
    """AC3: single-pole investment does not collide; two-pole does."""

    def test_only_truth_at_90_does_not_collide(self, d4_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("truth", 90, source="test")
        # vengeance stays at 0
        assert check_collision(d4_dilemma, investment) is False

    def test_only_vengeance_at_90_does_not_collide(self, d4_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("vengeance", 90, source="test")
        # truth stays at 0
        assert check_collision(d4_dilemma, investment) is False

    def test_both_at_85_collides(self, d4_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("truth", 85, source="test")
        investment.add_investment("vengeance", 85, source="test")
        assert check_collision(d4_dilemma, investment) is True


class TestD4TruthWinClosesVengeance:
    """AC4: resolving in favor of truth closes vengeance and opens Senn."""

    def test_lens_closed_vengeance_flag_set(self, d4_dilemma) -> None:
        player = fresh_player()
        resolve(d4_dilemma, "truth", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("vengeance")) is True

    def test_truth_outcome_flag_set(self, d4_dilemma) -> None:
        player = fresh_player()
        resolve(d4_dilemma, "truth", player)
        assert player.dialogue_flags.get("d4_truth_won") is True

    def test_senn_dialogue_routes_to_truth_confrontation(self, d4_dilemma) -> None:
        """Post-resolution Senn NPC record surfaces the confrontation tree."""
        dl = get_data_loader()
        dl.load_all()
        senn = dl.npcs.get("aldric_senn")
        assert senn is not None, "Aldric Senn NPC record must exist for D4"

        player = fresh_player()
        resolve(d4_dilemma, "truth", player)

        active = senn.get_active_dialogue_id(player.dialogue_flags)
        assert active == "senn_truth_confrontation", (
            f"Truth-wins must route Senn to the confrontation tree; got {active!r}"
        )


class TestD4VengeanceWinClosesTruth:
    """AC5: resolving in favor of vengeance closes truth and surfaces Priya's scar."""

    def test_lens_closed_truth_flag_set(self, d4_dilemma) -> None:
        player = fresh_player()
        resolve(d4_dilemma, "vengeance", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("truth")) is True

    def test_vengeance_outcome_flag_set(self, d4_dilemma) -> None:
        player = fresh_player()
        resolve(d4_dilemma, "vengeance", player)
        assert player.dialogue_flags.get("d4_vengeance_won") is True

    def test_priya_scar_reachable_via_chatter_manager(self, d4_dilemma) -> None:
        """Scar chatter at axiom_labs becomes eligible once truth is closed.

        Per the sprint's locked decision (Risks / open questions, Vengeance-
        wins Priya-declines-intel), the visible cost is a scar
        ``ChatterLine`` only. Priya's own dialogue tree is intentionally
        NOT gated on ``lens_closed_truth``. See A2-11 for the scar
        convention.
        """
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d4_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d4_priya_01"),
            None,
        )
        assert d4_scar is not None, (
            "Sprint A2-12 must ship a scar ChatterLine id=al_scar_d4_priya_01 "
            "at axiom_labs gated on lens_closed_truth."
        )
        assert d4_scar.category == "scar"
        assert d4_scar.system_id == "axiom_labs"
        assert d4_scar.one_shot is False, (
            "Scar convention (A2-11): one_shot must be False so the line recurs on each dock visit."
        )
        assert flag_registry.lens_closed("truth") in d4_scar.required_flags

        player = fresh_player()
        resolve(d4_dilemma, "vengeance", player)

        manager = StationChatterManager([d4_scar])
        results = manager.get_chatter(
            "axiom_labs",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d4_scar.text in results, (
            "Priya scar line must be reachable through StationChatterManager "
            "filtering once lens_closed_truth is set."
        )


class TestD4MissionSeedingFlag:
    """AC6-supporting: the ``the_ledger`` mission seed is registered and settable."""

    def test_flag_helper_present_in_registry(self) -> None:
        assert flag_registry.told_senn_orchestrated_operation() == (
            "told_senn_orchestrated_operation"
        )

    def test_flag_settable_and_readable_on_player(self) -> None:
        player = fresh_player()
        seed_flag = flag_registry.told_senn_orchestrated_operation()
        assert player.dialogue_flags.get(seed_flag) is None
        player.dialogue_flags[seed_flag] = True
        assert player.dialogue_flags.get(seed_flag) is True

    def test_the_ledger_mission_seeds_flag_via_reward(self) -> None:
        """The Act I ``the_ledger`` mission must set the flag as a reward."""
        dl = get_data_loader()
        dl.load_all()
        the_ledger = next((m for m in dl.missions if m.id == "the_ledger"), None)
        assert the_ledger is not None, "the_ledger mission must exist in Act I"

        seed_flag = flag_registry.told_senn_orchestrated_operation()
        seeding = [
            r
            for r in the_ledger.rewards
            if r.reward_type == "set_flag" and r.target_id == seed_flag
        ]
        assert seeding, (
            f"the_ledger mission must carry a set_flag reward for {seed_flag!r} "
            f"so D4's narration references land on a real precondition."
        )
