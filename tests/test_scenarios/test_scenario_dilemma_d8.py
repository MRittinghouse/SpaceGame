"""End-to-end scenario for D8 Crime vs Community (A2-19).

Mirrors the shape of :mod:`tests.test_scenarios.test_scenario_dilemma_d7`
so each dilemma sprint lands the same shape of coverage.

Drives the loaded dilemma record through the model-layer :func:`resolve`
path and asserts the observable player-facing consequences the sprint
promised:

- Loader parses ``data/narrative/dilemmas/d8_crime_community.json``.
- Integrity guard helpers accept the record.
- Single-pole investment does not collide; two-pole investment does.
- Crime-wins: closes community, routes Wulan to ``wulan_victorious`` and
  Kallio to ``kallio_declined`` (via A2-13's existing state); A2-13's
  ``al_scar_d2_kallio_01`` is reachable at ``havens_rest`` via flag
  convergence (lens_closed_community set by both D2-wealth and D8-crime).
- Community-wins: closes crime, routes Wulan to ``wulan_declined`` and
  Kallio to ``kallio_open_channels`` (via new D8 state added to Kallio);
  ``al_scar_d8_wulan_01`` is reachable at ``stellaris_port``.
- Closed-pole guard: pre-populating ``closed_lenses`` with either D8
  pole suppresses both telegraph and collision even at 100.
- Elena's two ``flag_triggered`` ambient reaction lines load with the
  correct ``required_flags``.
- Two auto-journal entries load with the correct ``trigger_flag``.
- Voice smoke: telegraph lines contain no em-dash, contain Elena anchor,
  no banned phrases; Wulan lines contain authored-anchor and no
  generic-gangster tropes.
- NPC id collision guard: ``wulan_doyle`` and ``thuy_kallio`` each appear
  exactly once; the Kallio extension did not duplicate the record.
- ``KNOWN_CONSUMER_ONLY_ORPHANS`` contains the three D8 flags and still
  contains ``lens_closed_community`` from A2-13.
- D2/D8 community-lens flag-key convergence (AC4).
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

D8_ID = "d8_crime_community"
D2_ID = "d2_wealth_community"


@pytest.fixture(scope="module")
def d8_dilemma():
    """Return the loaded D8 dilemma from the singleton DataLoader."""
    dl = get_data_loader()
    dl.load_all()
    assert D8_ID in dl.dilemmas, (
        f"{D8_ID} not loaded from data/narrative/dilemmas/. Available: {sorted(dl.dilemmas.keys())}"
    )
    return dl.dilemmas[D8_ID]


class TestD8Loads:
    """AC1: DataLoader parses the D8 record with both outcomes populated."""

    def test_dilemma_loads(self, d8_dilemma) -> None:
        assert d8_dilemma.id == D8_ID
        assert set(d8_dilemma.poles) == {"crime", "community"}
        assert d8_dilemma.collision_requires == 2
        assert d8_dilemma.telegraph_threshold == 55
        assert d8_dilemma.collision_threshold == 80
        assert d8_dilemma.telegraph_npc_id == "elena_reeves"
        assert len(d8_dilemma.telegraph_lines) >= 2, (
            "D8 sprint deliverable calls for 3 telegraph lines"
        )
        assert len(d8_dilemma.outcomes) == 2, "One outcome per pole"

    def test_outcomes_named_correctly(self, d8_dilemma) -> None:
        by_lens = {o.winning_lens_id: o for o in d8_dilemma.outcomes}
        assert set(by_lens.keys()) == {"crime", "community"}
        assert by_lens["crime"].closes == ["community"]
        assert by_lens["community"].closes == ["crime"]
        assert by_lens["crime"].outcome_flag == "d8_crime_won"
        assert by_lens["community"].outcome_flag == "d8_community_won"

    def test_both_outcomes_have_narration_summary(self, d8_dilemma) -> None:
        for outcome in d8_dilemma.outcomes:
            assert outcome.narration_summary, (
                f"Outcome {outcome.winning_lens_id!r} must have a non-empty narration_summary."
            )


class TestD8IntegrityGuardPasses:
    """AC2: the integrity-guard helpers accept the D8 record."""

    def test_no_empty_tier_unlocks(self, d8_dilemma) -> None:
        assert _outcomes_with_empty_tier_unlocks({D8_ID: d8_dilemma}) == []

    def test_thresholds_strictly_ordered(self, d8_dilemma) -> None:
        assert _dilemmas_with_bad_thresholds({D8_ID: d8_dilemma}) == []


class TestD8CollisionMath:
    """AC3: single-pole investment does not collide; two-pole does."""

    def test_only_crime_at_90_does_not_collide(self, d8_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("crime", 90, source="test")
        assert check_collision(d8_dilemma, investment) is False

    def test_only_community_at_90_does_not_collide(self, d8_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("community", 90, source="test")
        assert check_collision(d8_dilemma, investment) is False

    def test_both_at_85_collides(self, d8_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("crime", 85, source="test")
        investment.add_investment("community", 85, source="test")
        assert check_collision(d8_dilemma, investment) is True


class TestD8ClosedPoleGuard:
    """AC9: closed-pole guard suppresses D8 when a pole is already closed."""

    def _player_stub_with_closed(self, closed_lens: str):
        class _Stub:
            pass

        stub = _Stub()
        stub.lens_investment = LensInvestment(_values={"crime": 100, "community": 100})
        stub.dilemma_state = DilemmaRuntimeState(closed_lenses={closed_lens})
        return stub

    def test_crime_closed_suppresses_d8(self, d8_dilemma) -> None:
        stub = self._player_stub_with_closed("crime")
        result = check_dilemmas(stub, {D8_ID: d8_dilemma})
        assert result.newly_telegraphed == [], (
            "With crime in closed_lenses, D8 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With crime in closed_lenses, D8 must not collide even at 100/100."
        )

    def test_community_closed_suppresses_d8(self, d8_dilemma) -> None:
        stub = self._player_stub_with_closed("community")
        result = check_dilemmas(stub, {D8_ID: d8_dilemma})
        assert result.newly_telegraphed == [], (
            "With community in closed_lenses, D8 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With community in closed_lenses, D8 must not collide even at 100/100."
        )


class TestD8CrimeWinsClosesCommunity:
    """AC7: resolving in favor of crime closes community and shifts NPC states."""

    def test_lens_closed_community_flag_set(self, d8_dilemma) -> None:
        player = fresh_player()
        resolve(d8_dilemma, "crime", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("community")) is True

    def test_d8_crime_won_flag_set(self, d8_dilemma) -> None:
        player = fresh_player()
        resolve(d8_dilemma, "crime", player)
        assert player.dialogue_flags.get("d8_crime_won") is True

    def test_wulan_routes_to_victorious(self, d8_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        wulan = dl.npcs.get("wulan_doyle")
        assert wulan is not None, "Wulan Doyle NPC record must exist"

        player = fresh_player()
        resolve(d8_dilemma, "crime", player)

        active = wulan.get_active_dialogue_id(player.dialogue_flags)
        assert active == "wulan_victorious", (
            f"Crime-wins must route Wulan to wulan_victorious; got {active!r}"
        )

    def test_kallio_routes_to_declined(self, d8_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None, "Thuy Kallio NPC record must exist"

        player = fresh_player()
        resolve(d8_dilemma, "crime", player)

        active = kallio.get_active_dialogue_id(player.dialogue_flags)
        assert active == "kallio_declined", (
            f"Crime-wins must route Kallio to kallio_declined (via lens_closed_community); "
            f"got {active!r}"
        )

    def test_kallio_scar_reachable_after_crime_wins(self, d8_dilemma) -> None:
        """A2-13's al_scar_d2_kallio_01 fires on lens_closed_community at havens_rest."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        kallio_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d2_kallio_01"),
            None,
        )
        assert kallio_scar is not None, (
            "A2-13 must ship a scar ChatterLine id=al_scar_d2_kallio_01 "
            "at havens_rest gated on lens_closed_community."
        )
        assert kallio_scar.system_id == "havens_rest"
        assert flag_registry.lens_closed("community") in kallio_scar.required_flags

        player = fresh_player()
        resolve(d8_dilemma, "crime", player)

        manager = StationChatterManager([kallio_scar])
        results = manager.get_chatter(
            "havens_rest",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert kallio_scar.text in results, (
            "Kallio scar (al_scar_d2_kallio_01) must be reachable at havens_rest after "
            "D8 crime-wins (lens_closed_community set via flag convergence)."
        )

    def test_tier_unlocks_granted_crime(self, d8_dilemma) -> None:
        player = fresh_player()
        resolve(d8_dilemma, "crime", player)
        assert player.dilemma_state.tier_unlocks_granted.get("crime"), (
            "Crime-wins must record tier_unlocks_granted['crime'] as non-empty."
        )


class TestD8CommunityWinsClosesCrime:
    """AC8: resolving in favor of community closes crime and shifts NPC states."""

    def test_lens_closed_crime_flag_set(self, d8_dilemma) -> None:
        player = fresh_player()
        resolve(d8_dilemma, "community", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("crime")) is True

    def test_d8_community_won_flag_set(self, d8_dilemma) -> None:
        player = fresh_player()
        resolve(d8_dilemma, "community", player)
        assert player.dialogue_flags.get("d8_community_won") is True

    def test_wulan_routes_to_declined(self, d8_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        wulan = dl.npcs.get("wulan_doyle")
        assert wulan is not None, "Wulan Doyle NPC record must exist"

        player = fresh_player()
        resolve(d8_dilemma, "community", player)

        active = wulan.get_active_dialogue_id(player.dialogue_flags)
        assert active == "wulan_declined", (
            f"Community-wins must route Wulan to wulan_declined (via lens_closed_crime); "
            f"got {active!r}"
        )

    def test_kallio_routes_to_open_channels(self, d8_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None, "Thuy Kallio NPC record must exist"

        player = fresh_player()
        resolve(d8_dilemma, "community", player)

        active = kallio.get_active_dialogue_id(player.dialogue_flags)
        assert active == "kallio_open_channels", (
            f"Community-wins must route Kallio to kallio_open_channels "
            f"(via new post_d8_community_won state); got {active!r}"
        )

    def test_wulan_scar_reachable_after_community_wins(self, d8_dilemma) -> None:
        """al_scar_d8_wulan_01 fires on lens_closed_crime at stellaris_port."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        wulan_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d8_wulan_01"),
            None,
        )
        assert wulan_scar is not None, (
            "A2-19 must ship a scar ChatterLine id=al_scar_d8_wulan_01 "
            "at stellaris_port gated on lens_closed_crime."
        )
        assert wulan_scar.category == "scar"
        assert wulan_scar.system_id == "stellaris_port"
        assert wulan_scar.one_shot is False, "Scar convention (A2-11): one_shot must be False."
        assert flag_registry.lens_closed("crime") in wulan_scar.required_flags

        player = fresh_player()
        resolve(d8_dilemma, "community", player)

        manager = StationChatterManager([wulan_scar])
        results = manager.get_chatter(
            "stellaris_port",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert wulan_scar.text in results, (
            "Wulan scar (al_scar_d8_wulan_01) must be reachable at stellaris_port after "
            "D8 community-wins (lens_closed_crime is set)."
        )

    def test_wulan_scar_not_reachable_after_crime_wins(self, d8_dilemma) -> None:
        """al_scar_d8_wulan_01 requires lens_closed_crime, not set when crime wins."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        wulan_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d8_wulan_01"),
            None,
        )
        assert wulan_scar is not None

        player = fresh_player()
        resolve(d8_dilemma, "crime", player)

        manager = StationChatterManager([wulan_scar])
        results = manager.get_chatter(
            "stellaris_port",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert wulan_scar.text not in results, (
            "Wulan scar must NOT be reachable after D8 crime-wins (crime was not closed)."
        )

    def test_tier_unlocks_granted_community(self, d8_dilemma) -> None:
        player = fresh_player()
        resolve(d8_dilemma, "community", player)
        assert player.dilemma_state.tier_unlocks_granted.get("community"), (
            "Community-wins must record tier_unlocks_granted['community'] as non-empty."
        )


class TestD8ElenaReactionsRegistered:
    """AC11: Elena's post-D8 ambient lines load with the right flag gating."""

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

    def test_elena_post_crime_reaction_present(self) -> None:
        line = self._find_elena_flag_line("d8_crime_won")
        assert line is not None, (
            "AC11: Elena flag_triggered ambient line gated on 'd8_crime_won' "
            "must load through DataLoader."
        )
        assert line.crew_id == "elena_reeves"
        assert line.context == "flag_triggered"
        assert "d8_crime_won" in line.required_flags

    def test_elena_post_community_reaction_present(self) -> None:
        line = self._find_elena_flag_line("d8_community_won")
        assert line is not None, (
            "AC11: Elena flag_triggered ambient line gated on 'd8_community_won' "
            "must load through DataLoader."
        )
        assert line.crew_id == "elena_reeves"
        assert line.context == "flag_triggered"
        assert "d8_community_won" in line.required_flags


class TestD8JournalEntriesRegistered:
    """AC10: two auto-journal entries load with correct trigger_flag."""

    def test_crime_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d8_crime_won"),
            None,
        )
        assert entry is not None, "auto_d8_crime_won journal entry must load through DataLoader."
        assert entry.trigger_flag == "d8_crime_won"
        assert entry.system_id == "stellaris_port"

    def test_community_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d8_community_won"),
            None,
        )
        assert entry is not None, (
            "auto_d8_community_won journal entry must load through DataLoader."
        )
        assert entry.trigger_flag == "d8_community_won"
        assert entry.system_id == "havens_rest"


class TestD8NPCUniqueness:
    """AC15: both NPC ids are unique and the Kallio extension did not duplicate the record."""

    def test_wulan_doyle_unique(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        matches = [npc_id for npc_id in dl.npcs if npc_id == "wulan_doyle"]
        assert len(matches) == 1, (
            f"wulan_doyle must appear exactly once in DataLoader.npcs; found {len(matches)}"
        )

    def test_thuy_kallio_unique(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        matches = [npc_id for npc_id in dl.npcs if npc_id == "thuy_kallio"]
        assert len(matches) == 1, (
            f"thuy_kallio must appear exactly once in DataLoader.npcs; found {len(matches)}. "
            "The Kallio extension must not have duplicated her record."
        )


class TestD8WulanNPCLoads:
    """AC5: Wulan Doyle NPC loads with correct fields."""

    def test_wulan_loads(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        wulan = dl.npcs.get("wulan_doyle")
        assert wulan is not None, "Wulan Doyle NPC record must load through DataLoader."
        assert wulan.home_system_id == "stellaris_port"
        assert wulan.dialogue_id == "wulan_default"
        assert wulan.faction_id == ""
        assert wulan.title == "Broker, Kettlebridge Understair"

    def test_wulan_dialogue_states_cover_both_d8_outcomes(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        wulan = dl.npcs.get("wulan_doyle")
        assert wulan is not None
        state_ids = {s.state_id for s in wulan.dialogue_states}
        assert "post_d8_crime_won" in state_ids, (
            "Wulan must have a post_d8_crime_won dialogue_state."
        )
        assert "post_d8_crime_closed" in state_ids, (
            "Wulan must have a post_d8_crime_closed dialogue_state."
        )

    def test_wulan_default_with_no_flags(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        wulan = dl.npcs.get("wulan_doyle")
        assert wulan is not None
        no_flags: dict[str, bool] = {}
        active = wulan.get_active_dialogue_id(no_flags)
        assert active == "wulan_default", (
            f"Wulan default must be 'wulan_default' when no flag is set; got {active!r}"
        )


class TestD8KallioExtensionPreserved:
    """AC6: Kallio now has THREE dialogue_states, with A2-13's two entries byte-identical."""

    def test_kallio_has_three_states(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None
        assert len(kallio.dialogue_states) == 3, (
            f"Kallio must have exactly 3 dialogue_states after D8 extension; "
            f"found {len(kallio.dialogue_states)}: "
            f"{[s.state_id for s in kallio.dialogue_states]}"
        )

    def test_kallio_new_d8_state_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None
        new_state = next(
            (s for s in kallio.dialogue_states if s.state_id == "post_d8_community_won"),
            None,
        )
        assert new_state is not None, (
            "Kallio must have a post_d8_community_won dialogue_state after A2-19 extension."
        )
        assert new_state.dialogue_id == "kallio_open_channels"
        assert "d8_community_won" in new_state.required_flags

    def test_kallio_a213_post_wealth_closed_byte_identical(self) -> None:
        """A2-13's post_wealth_closed state must be untouched by A2-19."""
        dl = get_data_loader()
        dl.load_all()
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None
        state = next(
            (s for s in kallio.dialogue_states if s.state_id == "post_wealth_closed"),
            None,
        )
        assert state is not None, "Kallio's post_wealth_closed state must still exist."
        assert state.dialogue_id == "kallio_open_channels", (
            f"post_wealth_closed dialogue_id must be 'kallio_open_channels'; got {state.dialogue_id!r}"
        )
        assert state.required_flags == ["lens_closed_wealth"], (
            f"post_wealth_closed required_flags must be ['lens_closed_wealth']; "
            f"got {state.required_flags!r}"
        )

    def test_kallio_a213_post_community_closed_byte_identical(self) -> None:
        """A2-13's post_community_closed state must be untouched by A2-19."""
        dl = get_data_loader()
        dl.load_all()
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None
        state = next(
            (s for s in kallio.dialogue_states if s.state_id == "post_community_closed"),
            None,
        )
        assert state is not None, "Kallio's post_community_closed state must still exist."
        assert state.dialogue_id == "kallio_declined", (
            f"post_community_closed dialogue_id must be 'kallio_declined'; "
            f"got {state.dialogue_id!r}"
        )
        assert state.required_flags == ["lens_closed_community"], (
            f"post_community_closed required_flags must be ['lens_closed_community']; "
            f"got {state.required_flags!r}"
        )


class TestD8VoiceSmoke:
    """AC12-13: voice-smoke checks on telegraph, Elena, and Wulan content."""

    def test_telegraph_contains_no_em_dash(self, d8_dilemma) -> None:
        combined = " ".join(d8_dilemma.telegraph_lines)
        for char in ("—", "–", "―"):
            assert char not in combined, (
                f"Em-dash character {char!r} found in D8 telegraph lines. "
                "Writing Bible forbids em-dashes."
            )

    def test_telegraph_contains_no_banned_phrases(self, d8_dilemma) -> None:
        combined = " ".join(d8_dilemma.telegraph_lines).lower()
        banned = ("a testament to", "couldn't help but")
        for phrase in banned:
            assert phrase not in combined, f"Banned phrase {phrase!r} found in D8 telegraph lines."

    def test_telegraph_contains_elena_anchor(self, d8_dilemma) -> None:
        anchors = (
            "captain",
            "with respect",
            "if i'm reading",
            "optimal",
            "heading",
            "dead heading",
            "drifting off course",
        )
        combined = " ".join(d8_dilemma.telegraph_lines).lower()
        assert any(anchor in combined for anchor in anchors), (
            "At least one of Elena's telegraph lines must contain a voice anchor "
            f"(captain/with respect/if i'm reading/optimal/heading/dead heading/"
            f"drifting off course). Got: {d8_dilemma.telegraph_lines!r}"
        )

    def test_wulan_dialogue_contains_authored_anchor(self) -> None:
        """AC13: Wulan's authored content must contain at least one grounding anchor."""
        dl = get_data_loader()
        dl.load_all()
        anchors = (
            "ledger",
            "debt",
            "floor",
            "understair",
            "routes",
            "paperwork",
            "inheritance",
        )
        wulan_ids = {"wulan_default", "wulan_victorious", "wulan_declined"}
        all_text_parts: list[str] = []
        for tree_id, tree in dl.dialogue_trees.items():
            if tree_id not in wulan_ids:
                continue
            for node in tree.nodes.values():
                if node.speaker_id == "wulan_doyle":
                    all_text_parts.append(node.text)

        combined = " ".join(all_text_parts).lower()
        assert combined, "Wulan dialogue corpus must be non-empty for voice-smoke check."
        assert any(anchor in combined for anchor in anchors), (
            "At least one Wulan line must contain a grounding anchor "
            f"(ledger/debt/floor/understair/routes/paperwork/inheritance). "
            f"Got corpus: {combined[:300]!r}"
        )

    def test_wulan_dialogue_no_gangster_tropes(self) -> None:
        """AC13: Wulan must not use generic-gangster tropes."""
        dl = get_data_loader()
        dl.load_all()
        banned_substrings = (
            "the boss",
            "the family",
            "the syndicate",
            "the crew",
            "loyal",
            "traitor",
            "snitch",
        )
        wulan_ids = {"wulan_default", "wulan_victorious", "wulan_declined"}
        all_text_parts: list[str] = []
        for tree_id, tree in dl.dialogue_trees.items():
            if tree_id not in wulan_ids:
                continue
            for node in tree.nodes.values():
                if node.speaker_id == "wulan_doyle":
                    all_text_parts.append(node.text)

        combined = " ".join(all_text_parts).lower()
        assert combined, "Wulan dialogue corpus must be non-empty for trope check."
        for phrase in banned_substrings:
            assert phrase not in combined, (
                f"Generic-gangster trope {phrase!r} found in Wulan dialogue. "
                "Wulan's register is oblique and transactional, not gang-boss."
            )

    def test_no_em_dash_in_wulan_content(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        wulan_ids = {"wulan_default", "wulan_victorious", "wulan_declined"}
        all_text_parts: list[str] = []
        for tree_id, tree in dl.dialogue_trees.items():
            if tree_id not in wulan_ids:
                continue
            for node in tree.nodes.values():
                if node.speaker_id == "wulan_doyle":
                    all_text_parts.append(node.text)
        combined = " ".join(all_text_parts)
        for char in ("—", "–", "―"):
            assert char not in combined, (
                f"Em-dash {char!r} found in Wulan content. Writing Bible forbids em-dashes."
            )

    def test_no_banned_npc_names_in_authored_content(self, d8_dilemma) -> None:
        """AC14: banned NPC names must not appear in authored content."""
        banned_names = ("yara", "elara", "kael", "mara", "lydia", "clive", "magnus", "ambrose")
        dl = get_data_loader()
        dl.load_all()
        wulan_ids = {"wulan_default", "wulan_victorious", "wulan_declined"}
        all_parts: list[str] = []
        # Telegraph lines
        all_parts.extend(d8_dilemma.telegraph_lines)
        # Wulan trees
        for tree_id, tree in dl.dialogue_trees.items():
            if tree_id not in wulan_ids:
                continue
            for node in tree.nodes.values():
                all_parts.append(node.text)

        combined = " ".join(all_parts).lower()
        for name in banned_names:
            assert name not in combined, f"Banned NPC name {name!r} found in D8 authored content."


class TestD8ConsumerAllowlist:
    """AC16: KNOWN_CONSUMER_ONLY_ORPHANS contains the three D8 flags and lens_closed_community."""

    def test_d8_flags_in_consumer_allowlist(self) -> None:
        from tests.test_data.test_dialogue_integrity import KNOWN_CONSUMER_ONLY_ORPHANS

        required_flags = {
            "lens_closed_crime",
            "d8_crime_won",
            "d8_community_won",
            # A2-13 flag that D8 crime-wins sets via convergence; must remain in list
            "lens_closed_community",
        }
        missing = required_flags - KNOWN_CONSUMER_ONLY_ORPHANS
        assert not missing, (
            f"The following flags are missing from KNOWN_CONSUMER_ONLY_ORPHANS: {missing}. "
            "D8 flags added per A2-19 Task 7; lens_closed_community from A2-13 block."
        )


class TestD8CrossDilemmaConvergence:
    """AC4: D2/D8 community-lens flag-key convergence scenarios."""

    def test_d2_wealth_then_d8_crime_both_close_community(self) -> None:
        """D2-first, D8-second: both closing community leaves exactly lens_closed_community."""
        dl = get_data_loader()
        dl.load_all()
        d2 = dl.dilemmas.get(D2_ID)
        assert d2 is not None, f"{D2_ID} must load from DataLoader for convergence test."
        d8 = dl.dilemmas.get(D8_ID)
        assert d8 is not None

        player = fresh_player()
        resolve(d2, "wealth", player)  # D2 wealth-wins closes community
        resolve(d8, "crime", player)  # D8 crime-wins also closes community

        # Only one flag key for community closure, not a second variant
        assert player.dialogue_flags.get(flag_registry.lens_closed("community")) is True
        assert "d8_lens_closed_community" not in player.dialogue_flags
        assert "community_closed_d8" not in player.dialogue_flags

        # Kallio returns kallio_declined in both orderings
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None
        active = kallio.get_active_dialogue_id(player.dialogue_flags)
        assert active == "kallio_declined", (
            f"After D2-wealth then D8-crime, Kallio must route to kallio_declined; got {active!r}"
        )

    def test_d8_crime_then_d2_wealth_both_close_community(self) -> None:
        """D8-first, D2-second: reverse ordering also leaves exactly lens_closed_community."""
        dl = get_data_loader()
        dl.load_all()
        d2 = dl.dilemmas.get(D2_ID)
        assert d2 is not None
        d8 = dl.dilemmas.get(D8_ID)
        assert d8 is not None

        player = fresh_player()
        resolve(d8, "crime", player)  # D8 crime-wins closes community
        resolve(d2, "wealth", player)  # D2 wealth-wins also closes community

        assert player.dialogue_flags.get(flag_registry.lens_closed("community")) is True
        assert "d8_lens_closed_community" not in player.dialogue_flags

        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None
        active = kallio.get_active_dialogue_id(player.dialogue_flags)
        assert active == "kallio_declined", (
            f"After D8-crime then D2-wealth, Kallio must route to kallio_declined; got {active!r}"
        )

    def test_d2_community_then_d8_crime_transitions_kallio(self) -> None:
        """D2 community-wins opens Kallio; D8 crime-wins then closes her again."""
        dl = get_data_loader()
        dl.load_all()
        d2 = dl.dilemmas.get(D2_ID)
        assert d2 is not None
        d8 = dl.dilemmas.get(D8_ID)
        assert d8 is not None
        kallio = dl.npcs.get("thuy_kallio")
        assert kallio is not None

        player = fresh_player()
        resolve(d2, "community", player)  # D2 community-wins: opens Kallio
        active_after_d2 = kallio.get_active_dialogue_id(player.dialogue_flags)
        assert active_after_d2 == "kallio_open_channels", (
            f"After D2-community wins, Kallio must be at kallio_open_channels; "
            f"got {active_after_d2!r}"
        )

        resolve(d8, "crime", player)  # D8 crime-wins: closes community, declines Kallio
        active_after_d8 = kallio.get_active_dialogue_id(player.dialogue_flags)
        assert active_after_d8 == "kallio_declined", (
            f"After D2-community then D8-crime, Kallio must transition to kallio_declined; "
            f"got {active_after_d8!r}"
        )
