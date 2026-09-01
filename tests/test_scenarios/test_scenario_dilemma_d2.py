"""End-to-end scenario for D2 Wealth vs Community (A2-13).

Mirrors the shape of :mod:`tests.test_scenarios.test_scenario_dilemma_d4` so
each dilemma sprint (A2-12 through A2-19) lands the same shape of coverage.

Drives the loaded dilemma record through the model-layer :func:`resolve`
path and asserts the observable player-facing consequences the sprint
promised:

- Loader parses ``data/narrative/dilemmas/d2_wealth_community.json``.
- Integrity guard helpers accept the record.
- Single-pole investment does not collide; two-pole investment does.
- Wealth-wins closes ``community`` and routes Thuy Kallio's NPC record
  to ``kallio_declined`` (the door is closed); Noor Castellano's record
  routes to ``noor_buyers_open``; the ``al_scar_d2_kallio_01`` chatter
  line becomes reachable at ``havens_rest``.
- Community-wins closes ``wealth`` and routes Kallio to
  ``kallio_open_channels``, Castellano to ``noor_declined_credit``, and
  the ``al_scar_d2_noor_01`` chatter line becomes reachable at
  ``nexus_prime``.
- Marcus Jin's telegraph anchors on the M05 wound (buried / report /
  recyclers substring, case-insensitive) — AC6.
- Two Marcus reactive ambient lines carry the correct outcome flags in
  ``required_flags`` — AC7.
"""

from __future__ import annotations

import pytest

from spacegame.constants import flags as flag_registry
from spacegame.data_loader import get_data_loader
from spacegame.models.dilemma import check_collision, resolve
from spacegame.models.lens_investment import LensInvestment
from tests.test_compliance.test_dilemma_integrity import (
    _dilemmas_with_bad_thresholds,
    _outcomes_with_empty_tier_unlocks,
)
from tests.test_scenarios._helpers import fresh_player

D2_ID = "d2_wealth_community"


@pytest.fixture(scope="module")
def d2_dilemma():
    """Return the loaded D2 dilemma from the singleton DataLoader."""
    dl = get_data_loader()
    dl.load_all()
    assert D2_ID in dl.dilemmas, (
        f"{D2_ID} not loaded from data/narrative/dilemmas/. Available: {sorted(dl.dilemmas.keys())}"
    )
    return dl.dilemmas[D2_ID]


class TestD2Loads:
    """AC1: DataLoader parses the D2 record with both outcomes populated."""

    def test_dilemma_loads(self, d2_dilemma) -> None:
        assert d2_dilemma.id == D2_ID
        assert set(d2_dilemma.poles) == {"wealth", "community"}
        assert d2_dilemma.collision_requires == 2
        assert d2_dilemma.telegraph_threshold == 55
        assert d2_dilemma.collision_threshold == 80
        assert d2_dilemma.telegraph_npc_id == "marcus_jin"
        assert len(d2_dilemma.telegraph_lines) >= 2, (
            "D2 sprint deliverable calls for 2-3 telegraph lines"
        )
        assert len(d2_dilemma.outcomes) == 2, "One outcome per pole"

    def test_outcomes_named_correctly(self, d2_dilemma) -> None:
        by_lens = {o.winning_lens_id: o for o in d2_dilemma.outcomes}
        assert set(by_lens.keys()) == {"wealth", "community"}
        assert by_lens["wealth"].closes == ["community"]
        assert by_lens["community"].closes == ["wealth"]
        assert by_lens["wealth"].outcome_flag == "d2_wealth_won"
        assert by_lens["community"].outcome_flag == "d2_community_won"


class TestD2IntegrityGuardPasses:
    """AC2: the integrity-guard helpers accept the D2 record."""

    def test_no_empty_tier_unlocks(self, d2_dilemma) -> None:
        assert _outcomes_with_empty_tier_unlocks({D2_ID: d2_dilemma}) == []

    def test_thresholds_strictly_ordered(self, d2_dilemma) -> None:
        assert _dilemmas_with_bad_thresholds({D2_ID: d2_dilemma}) == []


class TestD2CollisionMath:
    """AC3: single-pole investment does not collide; two-pole does."""

    def test_only_wealth_at_90_does_not_collide(self, d2_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("wealth", 90, source="test")
        assert check_collision(d2_dilemma, investment) is False

    def test_only_community_at_90_does_not_collide(self, d2_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("community", 90, source="test")
        assert check_collision(d2_dilemma, investment) is False

    def test_both_at_85_collides(self, d2_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("wealth", 85, source="test")
        investment.add_investment("community", 85, source="test")
        assert check_collision(d2_dilemma, investment) is True


class TestD2WealthWinClosesCommunity:
    """AC4: resolving in favor of wealth closes community and shifts NPC states."""

    def test_lens_closed_community_flag_set(self, d2_dilemma) -> None:
        player = fresh_player()
        resolve(d2_dilemma, "wealth", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("community")) is True

    def test_wealth_outcome_flag_set(self, d2_dilemma) -> None:
        player = fresh_player()
        resolve(d2_dilemma, "wealth", player)
        assert player.dialogue_flags.get("d2_wealth_won") is True

    def test_kallio_dialogue_routes_to_declined(self, d2_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None, "Thuy Kallio NPC record must exist for D2"

        player = fresh_player()
        resolve(d2_dilemma, "wealth", player)

        active = kallio.get_active_dialogue_id(player.dialogue_flags)
        assert active == "kallio_declined", (
            f"Wealth-wins must route Kallio to the declined tree; got {active!r}"
        )

    def test_noor_dialogue_routes_to_buyers_open(self, d2_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        noor = dl.npcs.get("noor_castellano")
        assert noor is not None, "Noor Castellano NPC record must exist for D2"

        player = fresh_player()
        resolve(d2_dilemma, "wealth", player)

        active = noor.get_active_dialogue_id(player.dialogue_flags)
        assert active == "noor_buyers_open", (
            f"Wealth-wins must route Noor to the buyers-open tree; got {active!r}"
        )

    def test_kallio_scar_reachable_via_chatter_manager(self, d2_dilemma) -> None:
        """Scar chatter at havens_rest becomes eligible once community closes."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d2_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d2_kallio_01"),
            None,
        )
        assert d2_scar is not None, (
            "Sprint A2-13 must ship a scar ChatterLine id=al_scar_d2_kallio_01 "
            "at havens_rest gated on lens_closed_community."
        )
        assert d2_scar.category == "scar"
        assert d2_scar.system_id == "havens_rest"
        assert d2_scar.one_shot is False, (
            "Scar convention (A2-11): one_shot must be False so the line recurs on each dock visit."
        )
        assert flag_registry.lens_closed("community") in d2_scar.required_flags

        player = fresh_player()
        resolve(d2_dilemma, "wealth", player)

        manager = StationChatterManager([d2_scar])
        results = manager.get_chatter(
            "havens_rest",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d2_scar.text in results, (
            "Kallio scar line must be reachable through StationChatterManager "
            "filtering once lens_closed_community is set."
        )


class TestD2CommunityWinClosesWealth:
    """AC5: resolving in favor of community closes wealth and shifts NPC states."""

    def test_lens_closed_wealth_flag_set(self, d2_dilemma) -> None:
        player = fresh_player()
        resolve(d2_dilemma, "community", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("wealth")) is True

    def test_community_outcome_flag_set(self, d2_dilemma) -> None:
        player = fresh_player()
        resolve(d2_dilemma, "community", player)
        assert player.dialogue_flags.get("d2_community_won") is True

    def test_kallio_dialogue_routes_to_open_channels(self, d2_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None, "Thuy Kallio NPC record must exist for D2"

        player = fresh_player()
        resolve(d2_dilemma, "community", player)

        active = kallio.get_active_dialogue_id(player.dialogue_flags)
        assert active == "kallio_open_channels", (
            f"Community-wins must route Kallio to the open-channels tree; got {active!r}"
        )

    def test_noor_dialogue_routes_to_declined_credit(self, d2_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        noor = dl.npcs.get("noor_castellano")
        assert noor is not None, "Noor Castellano NPC record must exist for D2"

        player = fresh_player()
        resolve(d2_dilemma, "community", player)

        active = noor.get_active_dialogue_id(player.dialogue_flags)
        assert active == "noor_declined_credit", (
            f"Community-wins must route Noor to the declined-credit tree; got {active!r}"
        )

    def test_noor_scar_reachable_via_chatter_manager(self, d2_dilemma) -> None:
        """Scar chatter at nexus_prime becomes eligible once wealth closes."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d2_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d2_noor_01"),
            None,
        )
        assert d2_scar is not None, (
            "Sprint A2-13 must ship a scar ChatterLine id=al_scar_d2_noor_01 "
            "at nexus_prime gated on lens_closed_wealth."
        )
        assert d2_scar.category == "scar"
        assert d2_scar.system_id == "nexus_prime"
        assert d2_scar.one_shot is False, (
            "Scar convention (A2-11): one_shot must be False so the line recurs on each dock visit."
        )
        assert flag_registry.lens_closed("wealth") in d2_scar.required_flags

        player = fresh_player()
        resolve(d2_dilemma, "community", player)

        manager = StationChatterManager([d2_scar])
        results = manager.get_chatter(
            "nexus_prime",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d2_scar.text in results, (
            "Noor scar line must be reachable through StationChatterManager "
            "filtering once lens_closed_wealth is set."
        )


class TestD2TelegraphAnchor:
    """AC6: Marcus's telegraph text ties to the M05 buried-report wound."""

    def test_telegraph_contains_wound_anchor_word(self, d2_dilemma) -> None:
        anchors = ("buried", "report", "recyclers")
        combined = " ".join(d2_dilemma.telegraph_lines).lower()
        assert any(anchor in combined for anchor in anchors), (
            "At least one of Marcus's telegraph lines must contain one of "
            f"{anchors!r} to anchor the collision on the M05 wound "
            "(requirements/act_one_reference.md:254). "
            f"Got telegraph_lines: {d2_dilemma.telegraph_lines!r}"
        )


class TestD2MarcusReactionsRegistered:
    """AC7: Marcus's post-D2 ambient lines load with the right flag gating."""

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

    def test_marcus_post_wealth_reaction_present(self) -> None:
        line = self._find_marcus_flag_line("d2_wealth_won")
        assert line is not None, (
            "AC7: Marcus flag_triggered ambient line gated on 'd2_wealth_won' "
            "must load through DataLoader.load_ambient_dialogue()."
        )
        assert line.crew_id == "marcus_jin"
        assert line.context == "flag_triggered"
        assert "d2_wealth_won" in line.required_flags

    def test_marcus_post_community_reaction_present(self) -> None:
        line = self._find_marcus_flag_line("d2_community_won")
        assert line is not None, (
            "AC7: Marcus flag_triggered ambient line gated on 'd2_community_won' "
            "must load through DataLoader.load_ambient_dialogue()."
        )
        assert line.crew_id == "marcus_jin"
        assert line.context == "flag_triggered"
        assert "d2_community_won" in line.required_flags
