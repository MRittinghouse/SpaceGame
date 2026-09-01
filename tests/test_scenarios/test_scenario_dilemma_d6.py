"""End-to-end scenario for D6 Preservation vs Empire (A2-17).

Mirrors the shape of :mod:`tests.test_scenarios.test_scenario_dilemma_d5`
so each dilemma sprint lands the same shape of coverage.

Drives the loaded dilemma record through the model-layer :func:`resolve`
path and asserts the observable player-facing consequences the sprint
promised:

- Loader parses ``data/narrative/dilemmas/d6_preservation_empire.json``.
- Integrity guard helpers accept the record.
- Single-pole investment does not collide; two-pole investment does.
- Preservation-wins: closes empire, routes Halvorsen to
  ``halvorsen_d6_administering``, Virtanen to ``virtanen_victorious``;
  ``al_scar_d6_halvorsen_01`` is reachable at ``crimson_reach``.
- Empire-wins: closes preservation, routes Halvorsen to
  ``halvorsen_d6_victorious``, Virtanen to ``virtanen_declined``;
  ``al_scar_d6_virtanen_01`` is reachable at ``herons_mark``.
- Closed-pole guard: pre-populating ``closed_lenses`` with either D6 pole
  suppresses both telegraph and collision even with investment at 100.
- Priya's two ``flag_triggered`` ambient reaction lines load with the
  correct ``required_flags``.
- Two auto-journal entries load with the correct ``trigger_flag``.
- Voice smoke: telegraph lines contain no em-dash; contain at least one
  Priya voice anchor (data, suggest, analysis, catalogue, record, institute).
- NPC id collision guard: both ``junho_virtanen`` and ``idris_halvorsen``
  each appear exactly once.
- Halvorsen extension safety: ``dialogue_states`` length == 4, D6 states
  come first, default returns ``halvorsen_default`` when no flag set.
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

D6_ID = "d6_preservation_empire"


@pytest.fixture(scope="module")
def d6_dilemma():
    """Return the loaded D6 dilemma from the singleton DataLoader."""
    dl = get_data_loader()
    dl.load_all()
    assert D6_ID in dl.dilemmas, (
        f"{D6_ID} not loaded from data/narrative/dilemmas/. Available: {sorted(dl.dilemmas.keys())}"
    )
    return dl.dilemmas[D6_ID]


class TestD6Loads:
    """AC1: DataLoader parses the D6 record with both outcomes populated."""

    def test_dilemma_loads(self, d6_dilemma) -> None:
        assert d6_dilemma.id == D6_ID
        assert set(d6_dilemma.poles) == {"preservation", "empire"}
        assert d6_dilemma.collision_requires == 2
        assert d6_dilemma.telegraph_threshold == 55
        assert d6_dilemma.collision_threshold == 80
        assert d6_dilemma.telegraph_npc_id == "dr_priya_osei"
        assert len(d6_dilemma.telegraph_lines) >= 2, (
            "D6 sprint deliverable calls for 3 telegraph lines"
        )
        assert len(d6_dilemma.outcomes) == 2, "One outcome per pole"

    def test_outcomes_named_correctly(self, d6_dilemma) -> None:
        by_lens = {o.winning_lens_id: o for o in d6_dilemma.outcomes}
        assert set(by_lens.keys()) == {"preservation", "empire"}
        assert by_lens["preservation"].closes == ["empire"]
        assert by_lens["empire"].closes == ["preservation"]
        assert by_lens["preservation"].outcome_flag == "d6_preservation_won"
        assert by_lens["empire"].outcome_flag == "d6_empire_won"


class TestD6IntegrityGuardPasses:
    """AC2: the integrity-guard helpers accept the D6 record."""

    def test_no_empty_tier_unlocks(self, d6_dilemma) -> None:
        assert _outcomes_with_empty_tier_unlocks({D6_ID: d6_dilemma}) == []

    def test_thresholds_strictly_ordered(self, d6_dilemma) -> None:
        assert _dilemmas_with_bad_thresholds({D6_ID: d6_dilemma}) == []


class TestD6CollisionMath:
    """AC3: single-pole investment does not collide; two-pole does."""

    def test_only_preservation_at_90_does_not_collide(self, d6_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("preservation", 90, source="test")
        assert check_collision(d6_dilemma, investment) is False

    def test_only_empire_at_90_does_not_collide(self, d6_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("empire", 90, source="test")
        assert check_collision(d6_dilemma, investment) is False

    def test_both_at_85_collides(self, d6_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("preservation", 85, source="test")
        investment.add_investment("empire", 85, source="test")
        assert check_collision(d6_dilemma, investment) is True


class TestD6ClosedPoleGuard:
    """AC8: closed-pole guard suppresses D6 when a pole is already closed."""

    def _player_stub_with_closed(self, closed_lens: str):
        class _Stub:
            pass

        stub = _Stub()
        stub.lens_investment = LensInvestment(_values={"preservation": 100, "empire": 100})
        stub.dilemma_state = DilemmaRuntimeState(closed_lenses={closed_lens})
        return stub

    def test_empire_closed_suppresses_d6(self, d6_dilemma) -> None:
        stub = self._player_stub_with_closed("empire")
        result = check_dilemmas(stub, {D6_ID: d6_dilemma})
        assert result.newly_telegraphed == [], (
            "With empire in closed_lenses, D6 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With empire in closed_lenses, D6 must not collide even at 100/100."
        )

    def test_preservation_closed_suppresses_d6(self, d6_dilemma) -> None:
        stub = self._player_stub_with_closed("preservation")
        result = check_dilemmas(stub, {D6_ID: d6_dilemma})
        assert result.newly_telegraphed == [], (
            "With preservation in closed_lenses, D6 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With preservation in closed_lenses, D6 must not collide even at 100/100."
        )


class TestD6PreservationWinsClosesEmpire:
    """AC6: resolving in favor of preservation closes empire and shifts NPC states."""

    def test_lens_closed_empire_flag_set(self, d6_dilemma) -> None:
        player = fresh_player()
        resolve(d6_dilemma, "preservation", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("empire")) is True

    def test_preservation_outcome_flag_set(self, d6_dilemma) -> None:
        player = fresh_player()
        resolve(d6_dilemma, "preservation", player)
        assert player.dialogue_flags.get("d6_preservation_won") is True

    def test_halvorsen_routes_to_d6_administering(self, d6_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        halvorsen = dl.npcs.get("idris_halvorsen")
        assert halvorsen is not None, "Halvorsen NPC record must exist"

        player = fresh_player()
        resolve(d6_dilemma, "preservation", player)

        active = halvorsen.get_active_dialogue_id(player.dialogue_flags)
        assert active == "halvorsen_d6_administering", (
            f"Preservation-wins must route Halvorsen to halvorsen_d6_administering; got {active!r}"
        )

    def test_virtanen_routes_to_victorious(self, d6_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        virtanen = dl.npcs.get("junho_virtanen")
        assert virtanen is not None, "Junho Virtanen NPC record must exist"

        player = fresh_player()
        resolve(d6_dilemma, "preservation", player)

        active = virtanen.get_active_dialogue_id(player.dialogue_flags)
        assert active == "virtanen_victorious", (
            f"Preservation-wins must route Virtanen to virtanen_victorious; got {active!r}"
        )

    def test_halvorsen_scar_reachable_after_preservation_wins(self, d6_dilemma) -> None:
        """Halvorsen scar at crimson_reach fires on lens_closed_empire."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d6_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d6_halvorsen_01"),
            None,
        )
        assert d6_scar is not None, (
            "Sprint A2-17 must ship a scar ChatterLine id=al_scar_d6_halvorsen_01 "
            "at crimson_reach gated on lens_closed_empire."
        )
        assert d6_scar.category == "scar"
        assert d6_scar.system_id == "crimson_reach"
        assert d6_scar.one_shot is False, "Scar convention (A2-11): one_shot must be False."
        assert flag_registry.lens_closed("empire") in d6_scar.required_flags

        player = fresh_player()
        resolve(d6_dilemma, "preservation", player)

        manager = StationChatterManager([d6_scar])
        results = manager.get_chatter(
            "crimson_reach",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d6_scar.text in results, (
            "Halvorsen scar must be reachable at crimson_reach after preservation-wins "
            "(lens_closed_empire is set)."
        )

    def test_virtanen_scar_not_reachable_after_preservation_wins(self, d6_dilemma) -> None:
        """Virtanen scar at herons_mark requires lens_closed_preservation, not set here."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d6_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d6_virtanen_01"),
            None,
        )
        assert d6_scar is not None, (
            "Sprint A2-17 must ship a scar ChatterLine id=al_scar_d6_virtanen_01 "
            "at herons_mark gated on lens_closed_preservation."
        )

        player = fresh_player()
        resolve(d6_dilemma, "preservation", player)

        manager = StationChatterManager([d6_scar])
        results = manager.get_chatter(
            "herons_mark",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d6_scar.text not in results, (
            "Virtanen scar must NOT be reachable after preservation-wins "
            "(preservation was not closed)."
        )

    def test_tier_unlocks_granted_preservation(self, d6_dilemma) -> None:
        player = fresh_player()
        resolve(d6_dilemma, "preservation", player)
        assert player.dilemma_state.tier_unlocks_granted.get("preservation"), (
            "Preservation-wins must record tier_unlocks_granted['preservation'] as non-empty."
        )


class TestD6EmpireWinsClosesPreservation:
    """AC7: resolving in favor of empire closes preservation and shifts NPC states."""

    def test_lens_closed_preservation_flag_set(self, d6_dilemma) -> None:
        player = fresh_player()
        resolve(d6_dilemma, "empire", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("preservation")) is True

    def test_empire_outcome_flag_set(self, d6_dilemma) -> None:
        player = fresh_player()
        resolve(d6_dilemma, "empire", player)
        assert player.dialogue_flags.get("d6_empire_won") is True

    def test_halvorsen_routes_to_d6_victorious(self, d6_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        halvorsen = dl.npcs.get("idris_halvorsen")
        assert halvorsen is not None, "Halvorsen NPC record must exist"

        player = fresh_player()
        resolve(d6_dilemma, "empire", player)

        active = halvorsen.get_active_dialogue_id(player.dialogue_flags)
        assert active == "halvorsen_d6_victorious", (
            f"Empire-wins must route Halvorsen to halvorsen_d6_victorious; got {active!r}"
        )

    def test_virtanen_routes_to_declined(self, d6_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        virtanen = dl.npcs.get("junho_virtanen")
        assert virtanen is not None, "Junho Virtanen NPC record must exist"

        player = fresh_player()
        resolve(d6_dilemma, "empire", player)

        active = virtanen.get_active_dialogue_id(player.dialogue_flags)
        assert active == "virtanen_declined", (
            f"Empire-wins must route Virtanen to virtanen_declined; got {active!r}"
        )

    def test_virtanen_scar_reachable_after_empire_wins(self, d6_dilemma) -> None:
        """Virtanen scar at herons_mark fires on lens_closed_preservation."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d6_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d6_virtanen_01"),
            None,
        )
        assert d6_scar is not None, (
            "Sprint A2-17 must ship a scar ChatterLine id=al_scar_d6_virtanen_01 "
            "at herons_mark gated on lens_closed_preservation."
        )
        assert d6_scar.category == "scar"
        assert d6_scar.system_id == "herons_mark"
        assert d6_scar.one_shot is False, "Scar convention: one_shot must be False."
        assert flag_registry.lens_closed("preservation") in d6_scar.required_flags

        player = fresh_player()
        resolve(d6_dilemma, "empire", player)

        manager = StationChatterManager([d6_scar])
        results = manager.get_chatter(
            "herons_mark",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d6_scar.text in results, (
            "Virtanen scar must be reachable at herons_mark after empire-wins "
            "(lens_closed_preservation is set)."
        )

    def test_halvorsen_scar_not_reachable_after_empire_wins(self, d6_dilemma) -> None:
        """Halvorsen scar at crimson_reach requires lens_closed_empire, not set here."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d6_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d6_halvorsen_01"),
            None,
        )
        assert d6_scar is not None, (
            "Sprint A2-17 must ship a scar ChatterLine id=al_scar_d6_halvorsen_01 "
            "at crimson_reach gated on lens_closed_empire."
        )

        player = fresh_player()
        resolve(d6_dilemma, "empire", player)

        manager = StationChatterManager([d6_scar])
        results = manager.get_chatter(
            "crimson_reach",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d6_scar.text not in results, (
            "Halvorsen scar must NOT be reachable after empire-wins (empire was not closed)."
        )

    def test_tier_unlocks_granted_empire(self, d6_dilemma) -> None:
        player = fresh_player()
        resolve(d6_dilemma, "empire", player)
        assert player.dilemma_state.tier_unlocks_granted.get("empire"), (
            "Empire-wins must record tier_unlocks_granted['empire'] as non-empty."
        )


class TestD6PriyaReactionsRegistered:
    """AC10: Priya's post-D6 ambient lines load with the right flag gating."""

    def _find_priya_flag_line(self, outcome_flag: str):
        dl = get_data_loader()
        dl.load_all()
        for line in dl.ambient_lines:
            if line.crew_id != "dr_priya_osei":
                continue
            if line.context != "flag_triggered":
                continue
            if outcome_flag in line.required_flags:
                return line
        return None

    def test_priya_post_preservation_reaction_present(self) -> None:
        line = self._find_priya_flag_line("d6_preservation_won")
        assert line is not None, (
            "AC10: Priya flag_triggered ambient line gated on 'd6_preservation_won' "
            "must load through DataLoader."
        )
        assert line.crew_id == "dr_priya_osei"
        assert line.context == "flag_triggered"
        assert "d6_preservation_won" in line.required_flags

    def test_priya_post_empire_reaction_present(self) -> None:
        line = self._find_priya_flag_line("d6_empire_won")
        assert line is not None, (
            "AC10: Priya flag_triggered ambient line gated on 'd6_empire_won' "
            "must load through DataLoader."
        )
        assert line.crew_id == "dr_priya_osei"
        assert line.context == "flag_triggered"
        assert "d6_empire_won" in line.required_flags


class TestD6JournalEntriesRegistered:
    """AC9: two auto-journal entries load with correct trigger_flag."""

    def test_preservation_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d6_preservation_won"),
            None,
        )
        assert entry is not None, (
            "auto_d6_preservation_won journal entry must load through DataLoader."
        )
        assert entry.trigger_flag == "d6_preservation_won"

    def test_empire_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d6_empire_won"),
            None,
        )
        assert entry is not None, "auto_d6_empire_won journal entry must load through DataLoader."
        assert entry.trigger_flag == "d6_empire_won"


class TestD6NPCCollisionGuard:
    """AC12: both NPC ids are unique in the loader."""

    def test_junho_virtanen_unique(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        matches = [npc_id for npc_id in dl.npcs if npc_id == "junho_virtanen"]
        assert len(matches) == 1, (
            f"junho_virtanen must appear exactly once in DataLoader.npcs; found {len(matches)}"
        )

    def test_idris_halvorsen_unique(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        matches = [npc_id for npc_id in dl.npcs if npc_id == "idris_halvorsen"]
        assert len(matches) == 1, (
            f"idris_halvorsen must appear exactly once in DataLoader.npcs; found {len(matches)}"
        )


class TestD6HalvorsenExtensionSafe:
    """AC4: Halvorsen extension preserves priority ordering and default routing."""

    def test_dialogue_states_length_is_four(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        halvorsen = dl.npcs.get("idris_halvorsen")
        assert halvorsen is not None
        assert len(halvorsen.dialogue_states) == 4, (
            f"Halvorsen must have exactly 4 dialogue_states after A2-17 extension; "
            f"got {len(halvorsen.dialogue_states)}"
        )

    def test_d6_states_come_first(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        halvorsen = dl.npcs.get("idris_halvorsen")
        assert halvorsen is not None
        first_two = [s.state_id for s in halvorsen.dialogue_states[:2]]
        assert "post_d6_empire_won" in first_two, (
            "D6 state post_d6_empire_won must be in the first two dialogue_states."
        )
        assert "post_d6_preservation_won" in first_two, (
            "D6 state post_d6_preservation_won must be in the first two dialogue_states."
        )

    def test_default_returns_halvorsen_default_with_no_flags(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        halvorsen = dl.npcs.get("idris_halvorsen")
        assert halvorsen is not None
        no_flags: dict[str, bool] = {}
        active = halvorsen.get_active_dialogue_id(no_flags)
        assert active == "halvorsen_default", (
            f"Halvorsen default dialogue_id must be 'halvorsen_default' when no "
            f"post-collision flag is set; got {active!r}"
        )


class TestD6VirtanenNPCLoads:
    """AC5: Junho Virtanen NPC loads with correct fields."""

    def test_virtanen_loads(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        virtanen = dl.npcs.get("junho_virtanen")
        assert virtanen is not None, "Junho Virtanen NPC record must load through DataLoader."
        assert virtanen.home_system_id == "herons_mark"
        assert virtanen.dialogue_id == "virtanen_default"

    def test_virtanen_dialogue_states_cover_both_d6_outcomes(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        virtanen = dl.npcs.get("junho_virtanen")
        assert virtanen is not None
        state_ids = {s.state_id for s in virtanen.dialogue_states}
        assert "post_d6_preservation_won" in state_ids, (
            "Virtanen must have a post_d6_preservation_won dialogue_state."
        )
        assert "post_d6_empire_closed" in state_ids, (
            "Virtanen must have a post_d6_empire_closed dialogue_state."
        )

    def test_virtanen_default_with_no_flags(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        virtanen = dl.npcs.get("junho_virtanen")
        assert virtanen is not None
        no_flags: dict[str, bool] = {}
        active = virtanen.get_active_dialogue_id(no_flags)
        assert active == "virtanen_default", (
            f"Virtanen default must be 'virtanen_default' when no flag is set; got {active!r}"
        )


class TestD6VoiceSmoke:
    """AC11: telegraph lines follow Priya's voice and Writing Bible rules."""

    def test_telegraph_contains_no_em_dash(self, d6_dilemma) -> None:
        combined = " ".join(d6_dilemma.telegraph_lines)
        for char in ("—", "–", "―"):
            assert char not in combined, (
                f"Em-dash character {char!r} found in D6 telegraph lines. "
                "Writing Bible forbids em-dashes."
            )

    def test_telegraph_contains_no_banned_phrases(self, d6_dilemma) -> None:
        combined = " ".join(d6_dilemma.telegraph_lines).lower()
        banned = ("a testament to", "couldn't help but", "no x, no y")
        for phrase in banned:
            assert phrase not in combined, f"Banned phrase {phrase!r} found in D6 telegraph lines."

    def test_telegraph_contains_priya_anchor(self, d6_dilemma) -> None:
        anchors = (
            "data",
            "suggest",
            "analysis",
            "catalogue",
            "the record",
            "institute",
            "the sites",
            "border",
        )
        combined = " ".join(d6_dilemma.telegraph_lines).lower()
        assert any(anchor in combined for anchor in anchors), (
            "At least one of Priya's telegraph lines must contain a precision-register anchor "
            f"(data/suggest/analysis/catalogue/record/institute/sites/border). "
            f"Got: {d6_dilemma.telegraph_lines!r}"
        )
