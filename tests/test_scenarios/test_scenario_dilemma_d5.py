"""End-to-end scenario for D5 Legacy vs Connection (A2-16).

Mirrors the shape of :mod:`tests.test_scenarios.test_scenario_dilemma_d1`
and :mod:`tests.test_scenarios.test_scenario_dilemma_d4` so each dilemma
sprint lands the same shape of coverage.

Drives the loaded dilemma record through the model-layer :func:`resolve`
path and asserts the observable player-facing consequences the sprint
promised:

- Loader parses ``data/narrative/dilemmas/d5_legacy_connection.json``.
- Integrity guard helpers accept the record.
- Single-pole investment does not collide; two-pole investment does.
- Legacy-wins: closes connection, routes Solheim to ``solheim_victorious``,
  Elena to ``elena_connection_declined``; ``al_scar_d5_elena_01`` is
  reachable at ``nexus_prime``.
- Connection-wins: closes legacy, routes Elena to ``elena_connection_deepened``,
  Solheim to ``solheim_declined``; ``al_scar_d5_solheim_01`` is reachable
  at ``axiom_labs``.
- Closed-pole guard: pre-populating ``closed_lenses`` with either D5 pole
  suppresses both telegraph and collision even with investment at 100.
- Marcus's two ``flag_triggered`` ambient reaction lines load with the correct
  ``required_flags``.
- Two auto-journal entries load with the correct ``trigger_flag``.
- Voice smoke: telegraph lines contain no em-dash character; contain at
  least one Marcus anchor (short declarative, direct).
- NPC id collision guard: ``amrit_solheim`` is unique in the loader.
- Elena record extension safety: both new ``dialogue_states`` parse; default
  ``elena_cantina`` is still returned when no post-collision flag is set.
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

D5_ID = "d5_legacy_connection"


@pytest.fixture(scope="module")
def d5_dilemma():
    """Return the loaded D5 dilemma from the singleton DataLoader."""
    dl = get_data_loader()
    dl.load_all()
    assert D5_ID in dl.dilemmas, (
        f"{D5_ID} not loaded from data/narrative/dilemmas/. Available: {sorted(dl.dilemmas.keys())}"
    )
    return dl.dilemmas[D5_ID]


class TestD5Loads:
    """AC1: DataLoader parses the D5 record with both outcomes populated."""

    def test_dilemma_loads(self, d5_dilemma) -> None:
        assert d5_dilemma.id == D5_ID
        assert set(d5_dilemma.poles) == {"legacy", "connection"}
        assert d5_dilemma.collision_requires == 2
        assert d5_dilemma.telegraph_threshold == 55
        assert d5_dilemma.collision_threshold == 80
        assert d5_dilemma.telegraph_npc_id == "marcus_jin"
        assert len(d5_dilemma.telegraph_lines) >= 2, (
            "D5 sprint deliverable calls for 2-3 telegraph lines"
        )
        assert len(d5_dilemma.outcomes) == 2, "One outcome per pole"

    def test_outcomes_named_correctly(self, d5_dilemma) -> None:
        by_lens = {o.winning_lens_id: o for o in d5_dilemma.outcomes}
        assert set(by_lens.keys()) == {"legacy", "connection"}
        assert by_lens["legacy"].closes == ["connection"]
        assert by_lens["connection"].closes == ["legacy"]
        assert by_lens["legacy"].outcome_flag == "d5_legacy_won"
        assert by_lens["connection"].outcome_flag == "d5_connection_won"


class TestD5IntegrityGuardPasses:
    """AC2: the integrity-guard helpers accept the D5 record."""

    def test_no_empty_tier_unlocks(self, d5_dilemma) -> None:
        assert _outcomes_with_empty_tier_unlocks({D5_ID: d5_dilemma}) == []

    def test_thresholds_strictly_ordered(self, d5_dilemma) -> None:
        assert _dilemmas_with_bad_thresholds({D5_ID: d5_dilemma}) == []


class TestD5CollisionMath:
    """AC3: single-pole investment does not collide; two-pole does."""

    def test_only_legacy_at_90_does_not_collide(self, d5_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("legacy", 90, source="test")
        assert check_collision(d5_dilemma, investment) is False

    def test_only_connection_at_90_does_not_collide(self, d5_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("connection", 90, source="test")
        assert check_collision(d5_dilemma, investment) is False

    def test_both_at_85_collides(self, d5_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("legacy", 85, source="test")
        investment.add_investment("connection", 85, source="test")
        assert check_collision(d5_dilemma, investment) is True


class TestD5ClosedPoleGuard:
    """AC5: closed-pole guard suppresses D5 when a pole is already closed.

    Simulates a sibling dilemma having closed legacy or connection first,
    then confirms D5 is permanently ineligible.
    """

    def _player_stub_with_closed(self, closed_lens: str):
        """Minimal duck-typed player with one lens in closed_lenses."""

        class _Stub:
            pass

        stub = _Stub()
        stub.lens_investment = LensInvestment(_values={"legacy": 100, "connection": 100})
        stub.dilemma_state = DilemmaRuntimeState(closed_lenses={closed_lens})
        return stub

    def test_legacy_closed_suppresses_d5(self, d5_dilemma) -> None:
        stub = self._player_stub_with_closed("legacy")
        result = check_dilemmas(stub, {D5_ID: d5_dilemma})
        assert result.newly_telegraphed == [], (
            "With legacy in closed_lenses, D5 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With legacy in closed_lenses, D5 must not collide even at 100/100."
        )

    def test_connection_closed_suppresses_d5(self, d5_dilemma) -> None:
        stub = self._player_stub_with_closed("connection")
        result = check_dilemmas(stub, {D5_ID: d5_dilemma})
        assert result.newly_telegraphed == [], (
            "With connection in closed_lenses, D5 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With connection in closed_lenses, D5 must not collide even at 100/100."
        )


class TestD5LegacyWinsClosesConnection:
    """AC6: resolving in favor of legacy closes connection and shifts NPC states."""

    def test_lens_closed_connection_flag_set(self, d5_dilemma) -> None:
        player = fresh_player()
        resolve(d5_dilemma, "legacy", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("connection")) is True

    def test_legacy_outcome_flag_set(self, d5_dilemma) -> None:
        player = fresh_player()
        resolve(d5_dilemma, "legacy", player)
        assert player.dialogue_flags.get("d5_legacy_won") is True

    def test_solheim_dialogue_routes_to_victorious(self, d5_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        solheim = dl.npcs.get("amrit_solheim")
        assert solheim is not None, "Director Amrit Solheim NPC record must exist for D5"

        player = fresh_player()
        resolve(d5_dilemma, "legacy", player)

        active = solheim.get_active_dialogue_id(player.dialogue_flags)
        assert active == "solheim_victorious", (
            f"Legacy-wins must route Solheim to victorious tree; got {active!r}"
        )

    def test_elena_dialogue_routes_to_connection_declined(self, d5_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        elena = dl.npcs.get("elena_reeves")
        assert elena is not None, "Elena Reeves NPC record must exist"

        player = fresh_player()
        resolve(d5_dilemma, "legacy", player)

        active = elena.get_active_dialogue_id(player.dialogue_flags)
        assert active == "elena_connection_declined", (
            f"Legacy-wins must route Elena to elena_connection_declined; got {active!r}"
        )

    def test_solheim_scar_not_reachable_after_legacy_wins(self, d5_dilemma) -> None:
        """Solheim scar at axiom_labs fires on lens_closed_legacy, not lens_closed_connection."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d5_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d5_solheim_01"),
            None,
        )
        assert d5_scar is not None, (
            "Sprint A2-16 must ship a scar ChatterLine id=al_scar_d5_solheim_01 "
            "at axiom_labs gated on lens_closed_legacy."
        )

        player = fresh_player()
        resolve(d5_dilemma, "legacy", player)

        manager = StationChatterManager([d5_scar])
        results = manager.get_chatter(
            "axiom_labs",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d5_scar.text not in results, (
            "Solheim scar must NOT be reachable after legacy-wins (connection was closed, "
            "not legacy)."
        )

    def test_elena_scar_reachable_after_legacy_wins(self, d5_dilemma) -> None:
        """Elena scar at nexus_prime fires on lens_closed_connection, set when legacy wins."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d5_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d5_elena_01"),
            None,
        )
        assert d5_scar is not None, (
            "Sprint A2-16 must ship a scar ChatterLine id=al_scar_d5_elena_01 "
            "at nexus_prime gated on lens_closed_connection."
        )
        assert d5_scar.category == "scar"
        assert d5_scar.system_id == "nexus_prime"
        assert d5_scar.one_shot is False, "Scar convention (A2-11): one_shot must be False."
        assert flag_registry.lens_closed("connection") in d5_scar.required_flags

        player = fresh_player()
        resolve(d5_dilemma, "legacy", player)

        manager = StationChatterManager([d5_scar])
        results = manager.get_chatter(
            "nexus_prime",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d5_scar.text in results, (
            "Elena scar line must be reachable at nexus_prime after legacy-wins "
            "(lens_closed_connection is set)."
        )

    def test_tier_unlocks_granted_legacy(self, d5_dilemma) -> None:
        player = fresh_player()
        resolve(d5_dilemma, "legacy", player)
        assert player.dilemma_state.tier_unlocks_granted.get("legacy"), (
            "Legacy-wins must record tier_unlocks_granted['legacy'] as non-empty."
        )


class TestD5ConnectionWinsClosesLegacy:
    """AC4 + AC6: resolving in favor of connection closes legacy, shifts NPC states."""

    def test_lens_closed_legacy_flag_set(self, d5_dilemma) -> None:
        player = fresh_player()
        resolve(d5_dilemma, "connection", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("legacy")) is True

    def test_connection_outcome_flag_set(self, d5_dilemma) -> None:
        player = fresh_player()
        resolve(d5_dilemma, "connection", player)
        assert player.dialogue_flags.get("d5_connection_won") is True

    def test_elena_dialogue_routes_to_connection_deepened(self, d5_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        elena = dl.npcs.get("elena_reeves")
        assert elena is not None, "Elena Reeves NPC record must exist"

        player = fresh_player()
        resolve(d5_dilemma, "connection", player)

        active = elena.get_active_dialogue_id(player.dialogue_flags)
        assert active == "elena_connection_deepened", (
            f"Connection-wins must route Elena to elena_connection_deepened; got {active!r}"
        )

    def test_solheim_dialogue_routes_to_declined(self, d5_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        solheim = dl.npcs.get("amrit_solheim")
        assert solheim is not None, "Director Amrit Solheim NPC record must exist for D5"

        player = fresh_player()
        resolve(d5_dilemma, "connection", player)

        active = solheim.get_active_dialogue_id(player.dialogue_flags)
        assert active == "solheim_declined", (
            f"Connection-wins must route Solheim to solheim_declined; got {active!r}"
        )

    def test_solheim_scar_reachable_after_connection_wins(self, d5_dilemma) -> None:
        """Solheim scar at axiom_labs fires on lens_closed_legacy, set when connection wins."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d5_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d5_solheim_01"),
            None,
        )
        assert d5_scar is not None, (
            "Sprint A2-16 must ship a scar ChatterLine id=al_scar_d5_solheim_01 "
            "at axiom_labs gated on lens_closed_legacy."
        )
        assert d5_scar.category == "scar"
        assert d5_scar.system_id == "axiom_labs"
        assert d5_scar.one_shot is False, "Scar convention: one_shot must be False."
        assert flag_registry.lens_closed("legacy") in d5_scar.required_flags

        player = fresh_player()
        resolve(d5_dilemma, "connection", player)

        manager = StationChatterManager([d5_scar])
        results = manager.get_chatter(
            "axiom_labs",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d5_scar.text in results, (
            "Solheim scar line must be reachable at axiom_labs after connection-wins "
            "(lens_closed_legacy is set)."
        )

    def test_elena_scar_not_reachable_after_connection_wins(self, d5_dilemma) -> None:
        """Elena scar at nexus_prime requires lens_closed_connection, not set when connection wins."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d5_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d5_elena_01"),
            None,
        )
        assert d5_scar is not None, (
            "Sprint A2-16 must ship a scar ChatterLine id=al_scar_d5_elena_01 "
            "at nexus_prime gated on lens_closed_connection."
        )

        player = fresh_player()
        resolve(d5_dilemma, "connection", player)

        manager = StationChatterManager([d5_scar])
        results = manager.get_chatter(
            "nexus_prime",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d5_scar.text not in results, (
            "Elena scar must NOT be reachable after connection-wins (connection was not closed)."
        )

    def test_tier_unlocks_granted_connection(self, d5_dilemma) -> None:
        """AC4 alt-path: tier_unlocks_granted['connection'] is populated after resolve.

        The mechanical loyalty-ceiling hook (raising crew loyalty caps above 100) is
        deferred to the proposed follow-up sprint A2-16A. That sprint will add a
        loyalty_ceiling attribute on CrewRoster and wire it to this tier-unlock.
        This test satisfies AC4 via the documented alt-path: asserting the unlock
        is recorded in dilemma_state rather than verifying crew.py stat changes.
        """
        player = fresh_player()
        resolve(d5_dilemma, "connection", player)
        assert player.dilemma_state.tier_unlocks_granted.get("connection"), (
            "AC4 alt-path: Connection-wins must record tier_unlocks_granted['connection'] "
            "as a non-empty list. Mechanical loyalty-ceiling hook deferred to A2-16A."
        )


class TestD5MarcusReactionsRegistered:
    """AC7: Marcus's post-D5 ambient lines load with the right flag gating."""

    def _find_marcus_flag_line(self, outcome_flag: str):
        dl = get_data_loader()
        dl.load_all()
        for line in dl.ambient_lines:
            if line.crew_id != "marcus_jin":
                continue
            if line.context != "flag_triggered":
                continue
            if outcome_flag in line.required_flags:
                return line
        return None

    def test_marcus_post_legacy_reaction_present(self) -> None:
        line = self._find_marcus_flag_line("d5_legacy_won")
        assert line is not None, (
            "AC7: Marcus flag_triggered ambient line gated on 'd5_legacy_won' "
            "must load through DataLoader.load_ambient_dialogue()."
        )
        assert line.crew_id == "marcus_jin"
        assert line.context == "flag_triggered"
        assert "d5_legacy_won" in line.required_flags

    def test_marcus_post_connection_reaction_present(self) -> None:
        line = self._find_marcus_flag_line("d5_connection_won")
        assert line is not None, (
            "AC7: Marcus flag_triggered ambient line gated on 'd5_connection_won' "
            "must load through DataLoader.load_ambient_dialogue()."
        )
        assert line.crew_id == "marcus_jin"
        assert line.context == "flag_triggered"
        assert "d5_connection_won" in line.required_flags


class TestD5JournalEntriesRegistered:
    """AC8: two auto-journal entries load with correct trigger_flag."""

    def test_legacy_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d5_legacy_won"),
            None,
        )
        assert entry is not None, "auto_d5_legacy_won journal entry must load through DataLoader."
        assert entry.trigger_flag == "d5_legacy_won"

    def test_connection_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d5_connection_won"),
            None,
        )
        assert entry is not None, (
            "auto_d5_connection_won journal entry must load through DataLoader."
        )
        assert entry.trigger_flag == "d5_connection_won"


class TestD5NPCCollisionGuard:
    """AC9: amrit_solheim NPC id is unique in the loader."""

    def test_amrit_solheim_unique(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        matches = [npc_id for npc_id in dl.npcs if npc_id == "amrit_solheim"]
        assert len(matches) == 1, (
            f"amrit_solheim must appear exactly once in DataLoader.npcs; found {len(matches)}"
        )

    def test_elena_record_extension_safe(self) -> None:
        """Elena's dialogue_states array parses and default still works pre-collision."""
        dl = get_data_loader()
        dl.load_all()
        elena = dl.npcs.get("elena_reeves")
        assert elena is not None
        assert hasattr(elena, "dialogue_states"), (
            "Elena's NPC record must have a dialogue_states attribute after A2-16 extension."
        )
        assert len(elena.dialogue_states) >= 2, (
            "Elena must have at least 2 dialogue_states (the two D5 post-collision entries)."
        )

        # No flags set — must route to the default elena_cantina
        no_flags: dict[str, bool] = {}
        active = elena.get_active_dialogue_id(no_flags)
        assert active == "elena_cantina", (
            f"Elena's default dialogue_id must still be 'elena_cantina' when no "
            f"post-collision flag is set; got {active!r}"
        )


class TestD5VoiceSmoke:
    """AC10 voice smoke: telegraph lines follow Marcus's voice and Writing Bible rules."""

    def test_telegraph_contains_no_em_dash(self, d5_dilemma) -> None:
        combined = " ".join(d5_dilemma.telegraph_lines)
        for char in ("—", "–", "―"):
            assert char not in combined, (
                f"Em-dash character {char!r} found in D5 telegraph lines. "
                "Writing Bible forbids em-dashes."
            )

    def test_telegraph_contains_marcus_anchor(self, d5_dilemma) -> None:
        # Marcus: short declaratives, Union foreman directness, "we", direct verbs
        anchors = (
            "we ",
            "the ship",
            "the crew",
            "manifest",
            "bridge",
            "roster",
            "somewhere else",
            "present",
            "farrow",
            "institute",
        )
        combined = " ".join(d5_dilemma.telegraph_lines).lower()
        assert any(anchor in combined for anchor in anchors), (
            "At least one of Marcus's telegraph lines must contain a foreman-voice anchor "
            f"(crew/ship/manifest/bridge/Farrow/institute). Got: {d5_dilemma.telegraph_lines!r}"
        )
