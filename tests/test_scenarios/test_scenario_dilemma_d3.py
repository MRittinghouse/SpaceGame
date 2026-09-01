"""End-to-end scenario for D3 Political Power vs Revolution vs Empire (A2-15).

Mirrors the shape of the other dilemma scenarios (D1/D2/D4) so each dilemma
sprint lands the same shape of coverage. Where this scenario differs from
the pair-dilemma tests is the triangle: three poles, ``collision_requires=2``,
and outcomes whose ``closes`` list carries two entries.

The triangle-specific coverage here is the concrete proof of two model
features that no pair dilemma exercises:

- A2-8's ``collision_requires < len(poles)`` support: two-of-three-poles
  crossing threshold must collide, and any single one alone must not.
- A2-10's multi-lens ``closes`` support: a single ``resolve()`` call must
  set BOTH ``lens_closed_<other>`` flags, add both pole ids to
  ``runtime.closed_lenses``, and record tier unlocks for the winner.
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
    _dilemmas_with_bad_collision_requires,
    _dilemmas_with_bad_thresholds,
    _outcomes_with_empty_tier_unlocks,
)
from tests.test_scenarios._helpers import fresh_player

D3_ID = "d3_power_revolution_empire"
POLES = ("political_power", "revolution", "empire")
NPC_ID_BY_POLE = {
    "political_power": "emiko_owusu",
    "revolution": "sorcha_deng",
    "empire": "idris_halvorsen",
}
# Dialogue tree ids use the shortname suffix rather than the full NPC id
# (matches D1/D2/D4 convention: ``odusanya_default`` for ``magistrate_odusanya``).
DIALOGUE_SHORTNAME_BY_POLE = {
    "political_power": "owusu",
    "revolution": "deng",
    "empire": "halvorsen",
}
SCAR_ID_BY_POLE = {
    "political_power": "al_scar_d3_owusu_01",
    "revolution": "al_scar_d3_deng_01",
    "empire": "al_scar_d3_halvorsen_01",
}
SCAR_SYSTEM_BY_POLE = {
    "political_power": "havens_rest",
    "revolution": "havens_rest",
    "empire": "crimson_reach",
}
OUTCOME_FLAG_BY_POLE = {
    "political_power": "d3_political_power_won",
    "revolution": "d3_revolution_won",
    "empire": "d3_empire_won",
}


@pytest.fixture(scope="module")
def d3_dilemma():
    """Return the loaded D3 dilemma from the singleton DataLoader."""
    dl = get_data_loader()
    dl.load_all()
    assert D3_ID in dl.dilemmas, (
        f"{D3_ID} not loaded from data/narrative/dilemmas/. Available: {sorted(dl.dilemmas.keys())}"
    )
    return dl.dilemmas[D3_ID]


class TestD3Loads:
    """AC1: DataLoader parses the D3 record with three outcomes populated."""

    def test_dilemma_loads(self, d3_dilemma) -> None:
        assert d3_dilemma.id == D3_ID
        assert set(d3_dilemma.poles) == set(POLES)
        assert d3_dilemma.collision_requires == 2
        assert d3_dilemma.telegraph_threshold == 55
        assert d3_dilemma.collision_threshold == 80
        assert d3_dilemma.telegraph_npc_id == "tomas_drifter"
        assert len(d3_dilemma.telegraph_lines) >= 2, (
            "D3 sprint deliverable calls for 2-3 telegraph lines"
        )
        assert len(d3_dilemma.outcomes) == 3, "One outcome per pole"

    def test_outcomes_close_the_other_two(self, d3_dilemma) -> None:
        by_lens = {o.winning_lens_id: o for o in d3_dilemma.outcomes}
        assert set(by_lens.keys()) == set(POLES)
        for pole in POLES:
            others = set(POLES) - {pole}
            assert set(by_lens[pole].closes) == others, (
                f"Outcome '{pole}' must close exactly the other two poles; "
                f"got closes={by_lens[pole].closes!r}"
            )
            assert by_lens[pole].outcome_flag == OUTCOME_FLAG_BY_POLE[pole]


class TestD3IntegrityGuardPasses:
    """AC2: the integrity-guard helpers accept the D3 record."""

    def test_no_empty_tier_unlocks(self, d3_dilemma) -> None:
        assert _outcomes_with_empty_tier_unlocks({D3_ID: d3_dilemma}) == []

    def test_thresholds_strictly_ordered(self, d3_dilemma) -> None:
        assert _dilemmas_with_bad_thresholds({D3_ID: d3_dilemma}) == []

    def test_collision_requires_within_pole_count(self, d3_dilemma) -> None:
        assert _dilemmas_with_bad_collision_requires({D3_ID: d3_dilemma}) == []


class TestD3CollisionMath:
    """AC3: two-of-three poles at threshold collides; single pole does not.

    This is the concrete proof of A2-8's ``collision_requires < len(poles)``
    support — no pair dilemma exercises the case where one pole below
    threshold does not block a collision the other two together satisfy.
    """

    @pytest.mark.parametrize("high_pole", POLES)
    def test_single_pole_at_90_does_not_collide(self, d3_dilemma, high_pole: str) -> None:
        investment = LensInvestment()
        investment.add_investment(high_pole, 90, source="test")
        assert check_collision(d3_dilemma, investment) is False, (
            f"Only {high_pole} at 90 with the other two at 0 must not collide "
            "(collision_requires=2)."
        )

    @pytest.mark.parametrize(
        "pole_a,pole_b",
        [
            ("political_power", "revolution"),
            ("political_power", "empire"),
            ("revolution", "empire"),
        ],
    )
    def test_two_poles_at_85_collides(self, d3_dilemma, pole_a: str, pole_b: str) -> None:
        investment = LensInvestment()
        investment.add_investment(pole_a, 85, source="test")
        investment.add_investment(pole_b, 85, source="test")
        assert check_collision(d3_dilemma, investment) is True, (
            f"{pole_a}=85 and {pole_b}=85 must collide (collision_requires=2)."
        )

    def test_all_three_at_85_collides(self, d3_dilemma) -> None:
        investment = LensInvestment()
        for pole in POLES:
            investment.add_investment(pole, 85, source="test")
        assert check_collision(d3_dilemma, investment) is True


class TestD3ClosedPoleGuard:
    """A2-14 closed-pole guard: a pre-closed pole suppresses D3 entirely."""

    def _player_stub_with_closed(self, closed_lens: str):
        class _Stub:
            pass

        stub = _Stub()
        stub.lens_investment = LensInvestment(_values=dict.fromkeys(POLES, 100))
        stub.dilemma_state = DilemmaRuntimeState(closed_lenses={closed_lens})
        return stub

    def test_political_power_closed_suppresses_d3(self, d3_dilemma) -> None:
        stub = self._player_stub_with_closed("political_power")
        result = check_dilemmas(stub, {D3_ID: d3_dilemma})
        assert result.newly_telegraphed == [], (
            "With political_power in closed_lenses, D3 must not telegraph "
            "even at 100 on all three poles."
        )
        assert result.newly_collided == [], (
            "With political_power in closed_lenses, D3 must not collide "
            "even at 100 on all three poles."
        )


class TestD3TriangleResolution:
    """AC4: resolving one pole closes the other two in a single ``resolve()``.

    This is the concrete proof that ``DilemmaOutcome.closes`` supports more
    than one entry — the seven pair-dilemmas cannot exercise it.
    """

    @pytest.mark.parametrize("winning_pole", POLES)
    def test_resolve_closes_both_other_poles(self, d3_dilemma, winning_pole: str) -> None:
        player = fresh_player()
        others = tuple(p for p in POLES if p != winning_pole)

        resolve(d3_dilemma, winning_pole, player)

        assert player.dialogue_flags.get(OUTCOME_FLAG_BY_POLE[winning_pole]) is True, (
            f"Outcome flag {OUTCOME_FLAG_BY_POLE[winning_pole]!r} must be set."
        )
        for other in others:
            assert player.dialogue_flags.get(flag_registry.lens_closed(other)) is True, (
                f"After resolving to {winning_pole!r}, "
                f"{flag_registry.lens_closed(other)!r} must be set."
            )
            assert other in player.dilemma_state.closed_lenses, (
                f"After resolving to {winning_pole!r}, "
                f"runtime.closed_lenses must contain {other!r}."
            )
        assert player.dilemma_state.tier_unlocks_granted.get(winning_pole), (
            f"tier_unlocks_granted[{winning_pole!r}] must be non-empty after resolve."
        )
        # And the WINNING pole must not have been auto-closed.
        assert flag_registry.lens_closed(winning_pole) not in player.dialogue_flags or (
            player.dialogue_flags.get(flag_registry.lens_closed(winning_pole)) is not True
        ), f"Winning pole {winning_pole!r} must not be marked closed."


class TestD3NPCRouting:
    """AC6: each outcome routes the losing NPCs to declined, the winner to victorious."""

    @pytest.mark.parametrize("winning_pole", POLES)
    def test_dialogue_states_route_correctly(self, d3_dilemma, winning_pole: str) -> None:
        dl = get_data_loader()
        dl.load_all()

        player = fresh_player()
        resolve(d3_dilemma, winning_pole, player)

        for pole, npc_id in NPC_ID_BY_POLE.items():
            npc = dl.npcs.get(npc_id)
            assert npc is not None, f"D3 NPC {npc_id!r} must exist in DataLoader.npcs"
            active = npc.get_active_dialogue_id(player.dialogue_flags)
            shortname = DIALOGUE_SHORTNAME_BY_POLE[pole]
            expected = (
                f"{shortname}_victorious" if pole == winning_pole else f"{shortname}_declined"
            )
            assert active == expected, (
                f"After resolving to {winning_pole!r}, NPC {npc_id!r} must route "
                f"to {expected!r} (got {active!r})."
            )


class TestD3ScarReachability:
    """AC7: for each outcome, the two closed-pole scars are reachable via chatter."""

    @pytest.mark.parametrize("winning_pole", POLES)
    def test_two_scars_reachable(self, d3_dilemma, winning_pole: str) -> None:
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()

        # Build a lookup of D3 scars.
        d3_scars_by_id = {}
        for pole in POLES:
            scar_id = SCAR_ID_BY_POLE[pole]
            scar = next(
                (line for line in dl.station_chatter_lines if line.id == scar_id),
                None,
            )
            assert scar is not None, (
                f"Sprint A2-15 must ship scar ChatterLine id={scar_id!r} "
                f"at {SCAR_SYSTEM_BY_POLE[pole]!r} gated on "
                f"lens_closed_{pole}."
            )
            assert scar.category == "scar"
            assert scar.system_id == SCAR_SYSTEM_BY_POLE[pole]
            assert scar.one_shot is False, (
                "Scar convention (A2-11): one_shot must be False so the line "
                "recurs on each dock visit."
            )
            assert flag_registry.lens_closed(pole) in scar.required_flags, (
                f"Scar {scar_id!r} must gate on lens_closed_{pole}"
            )
            d3_scars_by_id[pole] = scar

        player = fresh_player()
        resolve(d3_dilemma, winning_pole, player)

        # The two poles that just closed have their scars reachable.
        losing = [p for p in POLES if p != winning_pole]
        for lost_pole in losing:
            scar = d3_scars_by_id[lost_pole]
            manager = StationChatterManager([scar])
            results = manager.get_chatter(
                scar.system_id,
                player_rep=0,
                active_event_types=[],
                count=3,
                player_flags=player.dialogue_flags,
            )
            assert scar.text in results, (
                f"After resolving to {winning_pole!r}, scar {scar.id!r} at "
                f"{scar.system_id!r} must be reachable through "
                f"StationChatterManager filtering."
            )


class TestD3TomasReactiveLines:
    """AC8: Tomas's three flag_triggered ambient lines load with the right gating."""

    def _find_tomas_flag_line(self, outcome_flag: str):
        dl = get_data_loader()
        dl.load_all()
        for line in dl.ambient_lines:
            if line.crew_id != "tomas_drifter":
                continue
            if line.context != "flag_triggered":
                continue
            if outcome_flag in line.required_flags:
                return line
        return None

    @pytest.mark.parametrize("winning_pole", POLES)
    def test_tomas_reaction_present(self, winning_pole: str) -> None:
        outcome_flag = OUTCOME_FLAG_BY_POLE[winning_pole]
        line = self._find_tomas_flag_line(outcome_flag)
        assert line is not None, (
            f"AC8: Tomas flag_triggered ambient line gated on {outcome_flag!r} "
            "must load through DataLoader.load_ambient_dialogue()."
        )
        assert line.crew_id == "tomas_drifter"
        assert line.context == "flag_triggered"
        assert outcome_flag in line.required_flags


class TestD3JournalEntries:
    """AC9: three auto-journal entries load with the correct trigger_flag."""

    @pytest.mark.parametrize("winning_pole", POLES)
    def test_journal_entry_present(self, winning_pole: str) -> None:
        dl = get_data_loader()
        dl.load_all()
        expected_id = f"auto_{OUTCOME_FLAG_BY_POLE[winning_pole]}"
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == expected_id),
            None,
        )
        assert entry is not None, f"{expected_id!r} journal entry must load through DataLoader."
        assert entry.trigger_flag == OUTCOME_FLAG_BY_POLE[winning_pole]


class TestD3NpcIdSafety:
    """AC5: authored NPC ids do not collide with any pre-existing NPC id."""

    def test_ids_present_exactly_once(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        for npc_id in NPC_ID_BY_POLE.values():
            assert npc_id in dl.npcs, (
                f"NPC {npc_id!r} must be registered in DataLoader.npcs (A2-15 authors it)."
            )
        # dl.npcs is keyed by id, so uniqueness is guaranteed at load time.
        # Guard the raw source anyway in case that ever changes.
        import json
        from pathlib import Path

        raw = json.loads(Path("data/characters/npcs.json").read_text(encoding="utf-8"))
        ids = [n["id"] for n in raw.get("npcs", [])]
        for npc_id in NPC_ID_BY_POLE.values():
            assert ids.count(npc_id) == 1, (
                f"NPC id {npc_id!r} must appear exactly once in "
                f"data/characters/npcs.json (got {ids.count(npc_id)})."
            )


class TestD3VoiceSmoke:
    """AC10 voice smoke: telegraph lines follow Tomas's voice and Writing Bible."""

    def test_telegraph_contains_no_em_dash(self, d3_dilemma) -> None:
        combined = " ".join(d3_dilemma.telegraph_lines)
        assert "—" not in combined, (
            "Em-dash character found in D3 telegraph lines. Writing Bible forbids em-dashes."
        )

    def test_telegraph_contains_tomas_anchor(self, d3_dilemma) -> None:
        anchors = (
            "way i see it",
            "margin",
            "bad deal",
            "smart money",
            "call me",
            "trade",
            "ledger",
        )
        combined = " ".join(d3_dilemma.telegraph_lines).lower()
        assert any(anchor in combined for anchor in anchors), (
            "At least one of Tomas's telegraph lines must contain a trade metaphor "
            f"or a 'Way I see it' anchor from his voice sheet. Got: "
            f"{d3_dilemma.telegraph_lines!r}"
        )
