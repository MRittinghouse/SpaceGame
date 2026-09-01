"""End-to-end scenario for D1 Vengeance vs Justice (A2-14).

Mirrors the shape of :mod:`tests.test_scenarios.test_scenario_dilemma_d2`
and :mod:`tests.test_scenarios.test_scenario_dilemma_d4` so each dilemma
sprint lands the same shape of coverage.

Drives the loaded dilemma record through the model-layer :func:`resolve`
path and asserts the observable player-facing consequences the sprint
promised:

- Loader parses ``data/narrative/dilemmas/d1_vengeance_justice.json``.
- Integrity guard helpers accept the record.
- Single-pole investment does not collide; two-pole investment does.
- Vengeance-wins closes ``justice`` and routes Magistrate Odusanya's NPC
  record to ``odusanya_declined``; ``al_scar_d1_odusanya_01`` becomes
  reachable via :class:`StationChatterManager` at ``havens_rest``.
- Justice-wins closes ``vengeance`` and makes
  ``al_scar_d1_names_still_out_there_01`` reachable at ``crimson_reach``.
- Closed-pole guard (AC3): pre-populating ``closed_lenses`` with either
  D1 pole suppresses both telegraph and collision even with investment
  driven above threshold.
- Elena's two ``flag_triggered`` ambient reaction lines load with the
  correct ``required_flags``.
- Voice smoke: telegraph lines contain no em-dash character; at least
  one line contains "With respect" or a navigation metaphor.
"""

from __future__ import annotations

import pytest

from spacegame.constants import flags as flag_registry
from spacegame.data_loader import get_data_loader
from spacegame.models.dilemma import (
    DilemmaRuntimeState,
    check_collision,
    check_dilemmas,
    resolve,
)
from spacegame.models.lens_investment import LensInvestment
from tests.test_compliance.test_dilemma_integrity import (
    _dilemmas_with_bad_thresholds,
    _outcomes_with_empty_tier_unlocks,
)
from tests.test_scenarios._helpers import fresh_player

D1_ID = "d1_vengeance_justice"


@pytest.fixture(scope="module")
def d1_dilemma():
    """Return the loaded D1 dilemma from the singleton DataLoader."""
    dl = get_data_loader()
    dl.load_all()
    assert D1_ID in dl.dilemmas, (
        f"{D1_ID} not loaded from data/narrative/dilemmas/. Available: {sorted(dl.dilemmas.keys())}"
    )
    return dl.dilemmas[D1_ID]


class TestD1Loads:
    """AC1: DataLoader parses the D1 record with both outcomes populated."""

    def test_dilemma_loads(self, d1_dilemma) -> None:
        assert d1_dilemma.id == D1_ID
        assert set(d1_dilemma.poles) == {"vengeance", "justice"}
        assert d1_dilemma.collision_requires == 2
        assert d1_dilemma.telegraph_threshold == 55
        assert d1_dilemma.collision_threshold == 80
        assert d1_dilemma.telegraph_npc_id == "elena_reeves"
        assert len(d1_dilemma.telegraph_lines) >= 2, (
            "D1 sprint deliverable calls for 2-3 telegraph lines"
        )
        assert len(d1_dilemma.outcomes) == 2, "One outcome per pole"

    def test_outcomes_named_correctly(self, d1_dilemma) -> None:
        by_lens = {o.winning_lens_id: o for o in d1_dilemma.outcomes}
        assert set(by_lens.keys()) == {"vengeance", "justice"}
        assert by_lens["vengeance"].closes == ["justice"]
        assert by_lens["justice"].closes == ["vengeance"]
        assert by_lens["vengeance"].outcome_flag == "d1_vengeance_won"
        assert by_lens["justice"].outcome_flag == "d1_justice_won"


class TestD1IntegrityGuardPasses:
    """AC2: the integrity-guard helpers accept the D1 record."""

    def test_no_empty_tier_unlocks(self, d1_dilemma) -> None:
        assert _outcomes_with_empty_tier_unlocks({D1_ID: d1_dilemma}) == []

    def test_thresholds_strictly_ordered(self, d1_dilemma) -> None:
        assert _dilemmas_with_bad_thresholds({D1_ID: d1_dilemma}) == []


class TestD1CollisionMath:
    """AC4: single-pole investment does not collide; two-pole does."""

    def test_only_vengeance_at_90_does_not_collide(self, d1_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("vengeance", 90, source="test")
        assert check_collision(d1_dilemma, investment) is False

    def test_only_justice_at_90_does_not_collide(self, d1_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("justice", 90, source="test")
        assert check_collision(d1_dilemma, investment) is False

    def test_both_at_85_collides(self, d1_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("vengeance", 85, source="test")
        investment.add_investment("justice", 85, source="test")
        assert check_collision(d1_dilemma, investment) is True


class TestD1ClosedPoleGuard:
    """AC3: closed-pole guard suppresses D1 when a pole is already closed.

    Simulates D4 having resolved vengeance first, or justice being closed
    via another path, then confirms D1 is permanently ineligible.
    """

    def _player_stub_with_closed(self, closed_lens: str):
        """Minimal duck-typed player with one lens in closed_lenses."""

        class _Stub:
            pass

        stub = _Stub()
        stub.lens_investment = LensInvestment(_values={"vengeance": 100, "justice": 100})
        stub.dilemma_state = DilemmaRuntimeState(closed_lenses={closed_lens})
        return stub

    def test_vengeance_closed_suppresses_d1(self, d1_dilemma) -> None:
        stub = self._player_stub_with_closed("vengeance")
        result = check_dilemmas(stub, {D1_ID: d1_dilemma})
        assert result.newly_telegraphed == [], (
            "With vengeance in closed_lenses, D1 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With vengeance in closed_lenses, D1 must not collide even at 100/100."
        )

    def test_justice_closed_suppresses_d1(self, d1_dilemma) -> None:
        stub = self._player_stub_with_closed("justice")
        result = check_dilemmas(stub, {D1_ID: d1_dilemma})
        assert result.newly_telegraphed == [], (
            "With justice in closed_lenses, D1 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With justice in closed_lenses, D1 must not collide even at 100/100."
        )


class TestD1VengeanceWinsClosesJustice:
    """AC5: resolving in favor of vengeance closes justice and shifts NPC states."""

    def test_lens_closed_justice_flag_set(self, d1_dilemma) -> None:
        player = fresh_player()
        resolve(d1_dilemma, "vengeance", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("justice")) is True

    def test_vengeance_outcome_flag_set(self, d1_dilemma) -> None:
        player = fresh_player()
        resolve(d1_dilemma, "vengeance", player)
        assert player.dialogue_flags.get("d1_vengeance_won") is True

    def test_odusanya_dialogue_routes_to_declined(self, d1_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        odusanya = dl.npcs.get("magistrate_odusanya")
        assert odusanya is not None, "Magistrate Odusanya NPC record must exist for D1"

        player = fresh_player()
        resolve(d1_dilemma, "vengeance", player)

        active = odusanya.get_active_dialogue_id(player.dialogue_flags)
        assert active == "odusanya_declined", (
            f"Vengeance-wins must route Odusanya to declined tree; got {active!r}"
        )

    def test_odusanya_scar_reachable_via_chatter_manager(self, d1_dilemma) -> None:
        """Scar chatter at havens_rest becomes eligible once justice closes."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d1_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d1_odusanya_01"),
            None,
        )
        assert d1_scar is not None, (
            "Sprint A2-14 must ship a scar ChatterLine id=al_scar_d1_odusanya_01 "
            "at havens_rest gated on lens_closed_justice."
        )
        assert d1_scar.category == "scar"
        assert d1_scar.system_id == "havens_rest"
        assert d1_scar.one_shot is False, (
            "Scar convention (A2-11): one_shot must be False so the line recurs on each dock visit."
        )
        assert flag_registry.lens_closed("justice") in d1_scar.required_flags

        player = fresh_player()
        resolve(d1_dilemma, "vengeance", player)

        manager = StationChatterManager([d1_scar])
        results = manager.get_chatter(
            "havens_rest",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d1_scar.text in results, (
            "Odusanya scar line must be reachable through StationChatterManager "
            "filtering once lens_closed_justice is set."
        )


class TestD1JusticeWinsClosesVengeance:
    """AC5: resolving in favor of justice closes vengeance and shifts NPC states."""

    def test_lens_closed_vengeance_flag_set(self, d1_dilemma) -> None:
        player = fresh_player()
        resolve(d1_dilemma, "justice", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("vengeance")) is True

    def test_justice_outcome_flag_set(self, d1_dilemma) -> None:
        player = fresh_player()
        resolve(d1_dilemma, "justice", player)
        assert player.dialogue_flags.get("d1_justice_won") is True

    def test_odusanya_dialogue_routes_to_warrant_sponsor(self, d1_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        odusanya = dl.npcs.get("magistrate_odusanya")
        assert odusanya is not None, "Magistrate Odusanya NPC record must exist for D1"

        player = fresh_player()
        resolve(d1_dilemma, "justice", player)

        active = odusanya.get_active_dialogue_id(player.dialogue_flags)
        assert active == "odusanya_warrant_sponsor", (
            f"Justice-wins must route Odusanya to warrant-sponsor tree; got {active!r}"
        )

    def test_names_scar_reachable_via_chatter_manager(self, d1_dilemma) -> None:
        """Scar chatter at crimson_reach becomes eligible once vengeance closes."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d1_scar = next(
            (
                line
                for line in dl.station_chatter_lines
                if line.id == "al_scar_d1_names_still_out_there_01"
            ),
            None,
        )
        assert d1_scar is not None, (
            "Sprint A2-14 must ship a scar ChatterLine id=al_scar_d1_names_still_out_there_01 "
            "at crimson_reach gated on lens_closed_vengeance."
        )
        assert d1_scar.category == "scar"
        assert d1_scar.system_id == "crimson_reach"
        assert d1_scar.one_shot is False, (
            "Scar convention (A2-11): one_shot must be False so the line recurs on each dock visit."
        )
        assert flag_registry.lens_closed("vengeance") in d1_scar.required_flags

        player = fresh_player()
        resolve(d1_dilemma, "justice", player)

        manager = StationChatterManager([d1_scar])
        results = manager.get_chatter(
            "crimson_reach",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d1_scar.text in results, (
            "Names scar line must be reachable through StationChatterManager "
            "filtering once lens_closed_vengeance is set."
        )


class TestD1ElenaReactionsRegistered:
    """AC6: Elena's post-D1 ambient lines load with the right flag gating."""

    def _find_elena_flag_line(self, outcome_flag: str):
        dl = get_data_loader()
        dl.load_all()
        for line in dl.ambient_lines:
            if line.crew_id != "elena_reeves":
                continue
            if line.context != "flag_triggered":
                continue
            if outcome_flag in line.required_flags:
                return line
        return None

    def test_elena_post_vengeance_reaction_present(self) -> None:
        line = self._find_elena_flag_line("d1_vengeance_won")
        assert line is not None, (
            "AC6: Elena flag_triggered ambient line gated on 'd1_vengeance_won' "
            "must load through DataLoader.load_ambient_dialogue()."
        )
        assert line.crew_id == "elena_reeves"
        assert line.context == "flag_triggered"
        assert "d1_vengeance_won" in line.required_flags

    def test_elena_post_justice_reaction_present(self) -> None:
        line = self._find_elena_flag_line("d1_justice_won")
        assert line is not None, (
            "AC6: Elena flag_triggered ambient line gated on 'd1_justice_won' "
            "must load through DataLoader.load_ambient_dialogue()."
        )
        assert line.crew_id == "elena_reeves"
        assert line.context == "flag_triggered"
        assert "d1_justice_won" in line.required_flags


class TestD1JournalEntriesRegistered:
    """AC7: two auto-journal entries load with correct trigger_flag."""

    def test_vengeance_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d1_vengeance_won"),
            None,
        )
        assert entry is not None, (
            "auto_d1_vengeance_won journal entry must load through DataLoader."
        )
        assert entry.trigger_flag == "d1_vengeance_won"

    def test_justice_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d1_justice_won"),
            None,
        )
        assert entry is not None, "auto_d1_justice_won journal entry must load through DataLoader."
        assert entry.trigger_flag == "d1_justice_won"


class TestD1VoiceSmoke:
    """AC8 voice smoke: telegraph lines follow Elena's voice and Writing Bible rules."""

    def test_telegraph_contains_no_em_dash(self, d1_dilemma) -> None:
        combined = " ".join(d1_dilemma.telegraph_lines)
        assert "—" not in combined, (
            "Em-dash character found in D1 telegraph lines. Writing Bible forbids em-dashes."
        )

    def test_telegraph_contains_elena_anchor(self, d1_dilemma) -> None:
        anchors = ("with respect", "heading", "route", "course", "manifest", "ledger")
        combined = " ".join(d1_dilemma.telegraph_lines).lower()
        assert any(anchor in combined for anchor in anchors), (
            "At least one of Elena's telegraph lines must contain a navigation metaphor "
            f"or 'With respect' (soft anchor from her voice sheet). Got: {d1_dilemma.telegraph_lines!r}"
        )
