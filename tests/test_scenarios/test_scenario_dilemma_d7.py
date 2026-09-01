"""End-to-end scenario for D7 Faith vs Transcendence (A2-18).

Mirrors the shape of :mod:`tests.test_scenarios.test_scenario_dilemma_d6`
so each dilemma sprint lands the same shape of coverage.

Drives the loaded dilemma record through the model-layer :func:`resolve`
path and asserts the observable player-facing consequences the sprint
promised:

- Loader parses ``data/narrative/dilemmas/d7_faith_transcendence.json``.
- Integrity guard helpers accept the record.
- Single-pole investment does not collide; two-pole investment does.
- Faith-wins: closes transcendence, routes Solano to
  ``solano_victorious`` and Marchetti to ``marchetti_declined``;
  ``al_scar_d7_marchetti_01`` is reachable at ``axiom_labs``.
- Transcendence-wins: closes faith, routes Solano to
  ``solano_declined`` and Marchetti to ``marchetti_victorious``;
  ``al_scar_d7_solano_01`` is reachable at ``havens_rest``.
- Closed-pole guard: pre-populating ``closed_lenses`` with either D7
  pole suppresses both telegraph and collision even at 100.
- Tomas's two ``flag_triggered`` ambient reaction lines load with the
  correct ``required_flags``.
- Two auto-journal entries load with the correct ``trigger_flag``.
- Voice smoke: telegraph lines contain no em-dash; Tomas register anchor
  present; Solano has no doctrinal phrasing; Marchetti has practical
  grounding anchor.
- NPC id collision guard: both ``imre_solano`` and
  ``rasheeda_marchetti`` each appear exactly once.
- ``KNOWN_CONSUMER_ONLY_ORPHANS`` contains the four D7 flags.
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

D7_ID = "d7_faith_transcendence"


@pytest.fixture(scope="module")
def d7_dilemma():
    """Return the loaded D7 dilemma from the singleton DataLoader."""
    dl = get_data_loader()
    dl.load_all()
    assert D7_ID in dl.dilemmas, (
        f"{D7_ID} not loaded from data/narrative/dilemmas/. Available: {sorted(dl.dilemmas.keys())}"
    )
    return dl.dilemmas[D7_ID]


class TestD7Loads:
    """AC1: DataLoader parses the D7 record with both outcomes populated."""

    def test_dilemma_loads(self, d7_dilemma) -> None:
        assert d7_dilemma.id == D7_ID
        assert set(d7_dilemma.poles) == {"faith", "transcendence"}
        assert d7_dilemma.collision_requires == 2
        assert d7_dilemma.telegraph_threshold == 55
        assert d7_dilemma.collision_threshold == 80
        assert d7_dilemma.telegraph_npc_id == "tomas_drifter"
        assert len(d7_dilemma.telegraph_lines) >= 2, (
            "D7 sprint deliverable calls for 3 telegraph lines"
        )
        assert len(d7_dilemma.outcomes) == 2, "One outcome per pole"

    def test_outcomes_named_correctly(self, d7_dilemma) -> None:
        by_lens = {o.winning_lens_id: o for o in d7_dilemma.outcomes}
        assert set(by_lens.keys()) == {"faith", "transcendence"}
        assert by_lens["faith"].closes == ["transcendence"]
        assert by_lens["transcendence"].closes == ["faith"]
        assert by_lens["faith"].outcome_flag == "d7_faith_won"
        assert by_lens["transcendence"].outcome_flag == "d7_transcendence_won"

    def test_both_outcomes_have_narration_summary(self, d7_dilemma) -> None:
        for outcome in d7_dilemma.outcomes:
            assert outcome.narration_summary, (
                f"Outcome {outcome.winning_lens_id!r} must have a non-empty narration_summary."
            )


class TestD7IntegrityGuardPasses:
    """AC2: the integrity-guard helpers accept the D7 record."""

    def test_no_empty_tier_unlocks(self, d7_dilemma) -> None:
        assert _outcomes_with_empty_tier_unlocks({D7_ID: d7_dilemma}) == []

    def test_thresholds_strictly_ordered(self, d7_dilemma) -> None:
        assert _dilemmas_with_bad_thresholds({D7_ID: d7_dilemma}) == []


class TestD7CollisionMath:
    """AC3: single-pole investment does not collide; two-pole does."""

    def test_only_faith_at_90_does_not_collide(self, d7_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("faith", 90, source="test")
        assert check_collision(d7_dilemma, investment) is False

    def test_only_transcendence_at_90_does_not_collide(self, d7_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("transcendence", 90, source="test")
        assert check_collision(d7_dilemma, investment) is False

    def test_both_at_85_collides(self, d7_dilemma) -> None:
        investment = LensInvestment()
        investment.add_investment("faith", 85, source="test")
        investment.add_investment("transcendence", 85, source="test")
        assert check_collision(d7_dilemma, investment) is True


class TestD7ClosedPoleGuard:
    """AC8: closed-pole guard suppresses D7 when a pole is already closed."""

    def _player_stub_with_closed(self, closed_lens: str):
        class _Stub:
            pass

        stub = _Stub()
        stub.lens_investment = LensInvestment(_values={"faith": 100, "transcendence": 100})
        stub.dilemma_state = DilemmaRuntimeState(closed_lenses={closed_lens})
        return stub

    def test_faith_closed_suppresses_d7(self, d7_dilemma) -> None:
        stub = self._player_stub_with_closed("faith")
        result = check_dilemmas(stub, {D7_ID: d7_dilemma})
        assert result.newly_telegraphed == [], (
            "With faith in closed_lenses, D7 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With faith in closed_lenses, D7 must not collide even at 100/100."
        )

    def test_transcendence_closed_suppresses_d7(self, d7_dilemma) -> None:
        stub = self._player_stub_with_closed("transcendence")
        result = check_dilemmas(stub, {D7_ID: d7_dilemma})
        assert result.newly_telegraphed == [], (
            "With transcendence in closed_lenses, D7 must not telegraph even at 100/100."
        )
        assert result.newly_collided == [], (
            "With transcendence in closed_lenses, D7 must not collide even at 100/100."
        )


class TestD7FaithWinsClosesTranscendence:
    """AC6: resolving in favor of faith closes transcendence and shifts NPC states."""

    def test_lens_closed_transcendence_flag_set(self, d7_dilemma) -> None:
        player = fresh_player()
        resolve(d7_dilemma, "faith", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("transcendence")) is True

    def test_faith_outcome_flag_set(self, d7_dilemma) -> None:
        player = fresh_player()
        resolve(d7_dilemma, "faith", player)
        assert player.dialogue_flags.get("d7_faith_won") is True

    def test_solano_routes_to_victorious(self, d7_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        solano = dl.npcs.get("imre_solano")
        assert solano is not None, "Imre Solano NPC record must exist"

        player = fresh_player()
        resolve(d7_dilemma, "faith", player)

        active = solano.get_active_dialogue_id(player.dialogue_flags)
        assert active == "solano_victorious", (
            f"Faith-wins must route Solano to solano_victorious; got {active!r}"
        )

    def test_marchetti_routes_to_declined(self, d7_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        marchetti = dl.npcs.get("rasheeda_marchetti")
        assert marchetti is not None, "Rasheeda Marchetti NPC record must exist"

        player = fresh_player()
        resolve(d7_dilemma, "faith", player)

        active = marchetti.get_active_dialogue_id(player.dialogue_flags)
        assert active == "marchetti_declined", (
            f"Faith-wins must route Marchetti to marchetti_declined; got {active!r}"
        )

    def test_marchetti_scar_reachable_after_faith_wins(self, d7_dilemma) -> None:
        """Marchetti scar at axiom_labs fires on lens_closed_transcendence."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d7_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d7_marchetti_01"),
            None,
        )
        assert d7_scar is not None, (
            "Sprint A2-18 must ship a scar ChatterLine id=al_scar_d7_marchetti_01 "
            "at axiom_labs gated on lens_closed_transcendence."
        )
        assert d7_scar.category == "scar"
        assert d7_scar.system_id == "axiom_labs"
        assert d7_scar.one_shot is False, "Scar convention (A2-11): one_shot must be False."
        assert flag_registry.lens_closed("transcendence") in d7_scar.required_flags

        player = fresh_player()
        resolve(d7_dilemma, "faith", player)

        manager = StationChatterManager([d7_scar])
        results = manager.get_chatter(
            "axiom_labs",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d7_scar.text in results, (
            "Marchetti scar must be reachable at axiom_labs after faith-wins "
            "(lens_closed_transcendence is set)."
        )

    def test_solano_scar_not_reachable_after_faith_wins(self, d7_dilemma) -> None:
        """Solano scar at havens_rest requires lens_closed_faith, not set here."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d7_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d7_solano_01"),
            None,
        )
        assert d7_scar is not None, (
            "Sprint A2-18 must ship a scar ChatterLine id=al_scar_d7_solano_01 "
            "at havens_rest gated on lens_closed_faith."
        )

        player = fresh_player()
        resolve(d7_dilemma, "faith", player)

        manager = StationChatterManager([d7_scar])
        results = manager.get_chatter(
            "havens_rest",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d7_scar.text not in results, (
            "Solano scar must NOT be reachable after faith-wins (faith was not closed)."
        )

    def test_tier_unlocks_granted_faith(self, d7_dilemma) -> None:
        player = fresh_player()
        resolve(d7_dilemma, "faith", player)
        assert player.dilemma_state.tier_unlocks_granted.get("faith"), (
            "Faith-wins must record tier_unlocks_granted['faith'] as non-empty."
        )


class TestD7TranscendenceWinsClosesFaith:
    """AC7: resolving in favor of transcendence closes faith and shifts NPC states."""

    def test_lens_closed_faith_flag_set(self, d7_dilemma) -> None:
        player = fresh_player()
        resolve(d7_dilemma, "transcendence", player)
        assert player.dialogue_flags.get(flag_registry.lens_closed("faith")) is True

    def test_transcendence_outcome_flag_set(self, d7_dilemma) -> None:
        player = fresh_player()
        resolve(d7_dilemma, "transcendence", player)
        assert player.dialogue_flags.get("d7_transcendence_won") is True

    def test_marchetti_routes_to_victorious(self, d7_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        marchetti = dl.npcs.get("rasheeda_marchetti")
        assert marchetti is not None, "Rasheeda Marchetti NPC record must exist"

        player = fresh_player()
        resolve(d7_dilemma, "transcendence", player)

        active = marchetti.get_active_dialogue_id(player.dialogue_flags)
        assert active == "marchetti_victorious", (
            f"Transcendence-wins must route Marchetti to marchetti_victorious; got {active!r}"
        )

    def test_solano_routes_to_declined(self, d7_dilemma) -> None:
        dl = get_data_loader()
        dl.load_all()
        solano = dl.npcs.get("imre_solano")
        assert solano is not None, "Imre Solano NPC record must exist"

        player = fresh_player()
        resolve(d7_dilemma, "transcendence", player)

        active = solano.get_active_dialogue_id(player.dialogue_flags)
        assert active == "solano_declined", (
            f"Transcendence-wins must route Solano to solano_declined; got {active!r}"
        )

    def test_solano_scar_reachable_after_transcendence_wins(self, d7_dilemma) -> None:
        """Solano scar at havens_rest fires on lens_closed_faith."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d7_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d7_solano_01"),
            None,
        )
        assert d7_scar is not None, (
            "Sprint A2-18 must ship a scar ChatterLine id=al_scar_d7_solano_01 "
            "at havens_rest gated on lens_closed_faith."
        )
        assert d7_scar.category == "scar"
        assert d7_scar.system_id == "havens_rest"
        assert d7_scar.one_shot is False, "Scar convention: one_shot must be False."
        assert flag_registry.lens_closed("faith") in d7_scar.required_flags

        player = fresh_player()
        resolve(d7_dilemma, "transcendence", player)

        manager = StationChatterManager([d7_scar])
        results = manager.get_chatter(
            "havens_rest",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d7_scar.text in results, (
            "Solano scar must be reachable at havens_rest after transcendence-wins "
            "(lens_closed_faith is set)."
        )

    def test_marchetti_scar_not_reachable_after_transcendence_wins(self, d7_dilemma) -> None:
        """Marchetti scar at axiom_labs requires lens_closed_transcendence, not set here."""
        from spacegame.models.station_chatter import StationChatterManager

        dl = get_data_loader()
        dl.load_all()
        d7_scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d7_marchetti_01"),
            None,
        )
        assert d7_scar is not None, (
            "Sprint A2-18 must ship a scar ChatterLine id=al_scar_d7_marchetti_01 "
            "at axiom_labs gated on lens_closed_transcendence."
        )

        player = fresh_player()
        resolve(d7_dilemma, "transcendence", player)

        manager = StationChatterManager([d7_scar])
        results = manager.get_chatter(
            "axiom_labs",
            player_rep=0,
            active_event_types=[],
            count=3,
            player_flags=player.dialogue_flags,
        )
        assert d7_scar.text not in results, (
            "Marchetti scar must NOT be reachable after transcendence-wins "
            "(transcendence was not closed)."
        )

    def test_tier_unlocks_granted_transcendence(self, d7_dilemma) -> None:
        player = fresh_player()
        resolve(d7_dilemma, "transcendence", player)
        assert player.dilemma_state.tier_unlocks_granted.get("transcendence"), (
            "Transcendence-wins must record tier_unlocks_granted['transcendence'] as non-empty."
        )


class TestD7TomasReactionsRegistered:
    """AC10: Tomas's post-D7 ambient lines load with the right flag gating."""

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

    def test_tomas_post_faith_reaction_present(self) -> None:
        line = self._find_tomas_flag_line("d7_faith_won")
        assert line is not None, (
            "AC10: Tomas flag_triggered ambient line gated on 'd7_faith_won' "
            "must load through DataLoader."
        )
        assert line.crew_id == "tomas_drifter"
        assert line.context == "flag_triggered"
        assert "d7_faith_won" in line.required_flags

    def test_tomas_post_transcendence_reaction_present(self) -> None:
        line = self._find_tomas_flag_line("d7_transcendence_won")
        assert line is not None, (
            "AC10: Tomas flag_triggered ambient line gated on 'd7_transcendence_won' "
            "must load through DataLoader."
        )
        assert line.crew_id == "tomas_drifter"
        assert line.context == "flag_triggered"
        assert "d7_transcendence_won" in line.required_flags


class TestD7JournalEntriesRegistered:
    """AC9: two auto-journal entries load with correct trigger_flag."""

    def test_faith_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d7_faith_won"),
            None,
        )
        assert entry is not None, "auto_d7_faith_won journal entry must load through DataLoader."
        assert entry.trigger_flag == "d7_faith_won"
        assert entry.system_id == "havens_rest"

    def test_transcendence_journal_entry_present(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        entry = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_d7_transcendence_won"),
            None,
        )
        assert entry is not None, (
            "auto_d7_transcendence_won journal entry must load through DataLoader."
        )
        assert entry.trigger_flag == "d7_transcendence_won"
        assert entry.system_id == "axiom_labs"


class TestD7NPCCollisionGuard:
    """AC15: both NPC ids are unique in the loader."""

    def test_imre_solano_unique(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        matches = [npc_id for npc_id in dl.npcs if npc_id == "imre_solano"]
        assert len(matches) == 1, (
            f"imre_solano must appear exactly once in DataLoader.npcs; found {len(matches)}"
        )

    def test_rasheeda_marchetti_unique(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        matches = [npc_id for npc_id in dl.npcs if npc_id == "rasheeda_marchetti"]
        assert len(matches) == 1, (
            f"rasheeda_marchetti must appear exactly once in DataLoader.npcs; found {len(matches)}"
        )


class TestD7SolanoNPCLoads:
    """AC4: Chaplain Imre Solano NPC loads with correct fields."""

    def test_solano_loads(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        solano = dl.npcs.get("imre_solano")
        assert solano is not None, "Imre Solano NPC record must load through DataLoader."
        assert solano.home_system_id == "havens_rest"
        assert solano.dialogue_id == "solano_default"

    def test_solano_dialogue_states_cover_both_d7_outcomes(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        solano = dl.npcs.get("imre_solano")
        assert solano is not None
        state_ids = {s.state_id for s in solano.dialogue_states}
        assert "post_d7_faith_won" in state_ids, (
            "Solano must have a post_d7_faith_won dialogue_state."
        )
        assert "post_d7_faith_closed" in state_ids, (
            "Solano must have a post_d7_faith_closed dialogue_state."
        )

    def test_solano_default_with_no_flags(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        solano = dl.npcs.get("imre_solano")
        assert solano is not None
        no_flags: dict[str, bool] = {}
        active = solano.get_active_dialogue_id(no_flags)
        assert active == "solano_default", (
            f"Solano default must be 'solano_default' when no flag is set; got {active!r}"
        )


class TestD7MarchettiNPCLoads:
    """AC5: Dr. Rasheeda Marchetti NPC loads with correct fields."""

    def test_marchetti_loads(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        marchetti = dl.npcs.get("rasheeda_marchetti")
        assert marchetti is not None, "Rasheeda Marchetti NPC record must load through DataLoader."
        assert marchetti.home_system_id == "axiom_labs"
        assert marchetti.dialogue_id == "marchetti_default"

    def test_marchetti_dialogue_states_cover_both_d7_outcomes(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        marchetti = dl.npcs.get("rasheeda_marchetti")
        assert marchetti is not None
        state_ids = {s.state_id for s in marchetti.dialogue_states}
        assert "post_d7_transcendence_won" in state_ids, (
            "Marchetti must have a post_d7_transcendence_won dialogue_state."
        )
        assert "post_d7_transcendence_closed" in state_ids, (
            "Marchetti must have a post_d7_transcendence_closed dialogue_state."
        )

    def test_marchetti_default_with_no_flags(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        marchetti = dl.npcs.get("rasheeda_marchetti")
        assert marchetti is not None
        no_flags: dict[str, bool] = {}
        active = marchetti.get_active_dialogue_id(no_flags)
        assert active == "marchetti_default", (
            f"Marchetti default must be 'marchetti_default' when no flag is set; got {active!r}"
        )


class TestD7VoiceSmoke:
    """AC11-13: voice-smoke checks on telegraph, Solano, and Marchetti content."""

    def test_telegraph_contains_no_em_dash(self, d7_dilemma) -> None:
        combined = " ".join(d7_dilemma.telegraph_lines)
        for char in ("—", "–", "―"):
            assert char not in combined, (
                f"Em-dash character {char!r} found in D7 telegraph lines. "
                "Writing Bible forbids em-dashes."
            )

    def test_telegraph_contains_no_banned_phrases(self, d7_dilemma) -> None:
        combined = " ".join(d7_dilemma.telegraph_lines).lower()
        banned = ("a testament to", "couldn't help but", "no x, no y")
        for phrase in banned:
            assert phrase not in combined, f"Banned phrase {phrase!r} found in D7 telegraph lines."

    def test_telegraph_contains_tomas_anchor(self, d7_dilemma) -> None:
        anchors = (
            "captain",
            "ledger",
            "margin",
            "smart money",
            "way i see it",
            "deal",
            "run",
            "trade",
        )
        combined = " ".join(d7_dilemma.telegraph_lines).lower()
        assert any(anchor in combined for anchor in anchors), (
            "At least one of Tomas's telegraph lines must contain a grounded ledger-register "
            f"anchor (captain/ledger/margin/smart money/way i see it/deal/run/trade). "
            f"Got: {d7_dilemma.telegraph_lines!r}"
        )

    def test_solano_dialogue_contains_no_doctrinal_phrasing(self) -> None:
        """AC12: Solano's authored content must not contain vague-mysticism phrases."""
        dl = get_data_loader()
        dl.load_all()
        banned_phrases = (
            "the universe has a plan",
            "everything happens for a reason",
            "have faith",
            "grand design",
            "meant to be",
            "god's plan",
            "divine will",
        )
        # Gather all Solano dialogue node texts and the Solano scar line
        solano_ids = {"solano_default", "solano_victorious", "solano_declined"}
        all_text_parts: list[str] = []
        for tree_id, tree in dl.dialogue_trees.items():
            if tree_id not in solano_ids:
                continue
            for node in tree.nodes.values():
                if node.speaker_id == "imre_solano":
                    all_text_parts.append(node.text)
        # Also include the scar line
        scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d7_solano_01"),
            None,
        )
        if scar is not None:
            all_text_parts.append(scar.text)

        combined = " ".join(all_text_parts).lower()
        assert combined, "Solano dialogue corpus must be non-empty for voice-smoke check."
        for phrase in banned_phrases:
            assert phrase not in combined, (
                f"Banned doctrinal phrase {phrase!r} found in Solano dialogue/scar content. "
                "Solano must not recite doctrine."
            )

    def test_marchetti_dialogue_contains_practical_grounding(self) -> None:
        """AC13: Marchetti's authored content must reference her practical grounding."""
        dl = get_data_loader()
        dl.load_all()
        anchors = (
            "procedure",
            "institute",
            "mobility",
            "contract",
            "clinical",
            "authorization",
            "ethics",
        )
        marchetti_ids = {"marchetti_default", "marchetti_victorious", "marchetti_declined"}
        all_text_parts: list[str] = []
        for tree_id, tree in dl.dialogue_trees.items():
            if tree_id not in marchetti_ids:
                continue
            for node in tree.nodes.values():
                if node.speaker_id == "rasheeda_marchetti":
                    all_text_parts.append(node.text)

        combined = " ".join(all_text_parts).lower()
        assert combined, "Marchetti dialogue corpus must be non-empty for voice-smoke check."
        assert any(anchor in combined for anchor in anchors), (
            "At least one Marchetti line must contain a practical-grounding anchor "
            f"(procedure/institute/mobility/contract/clinical/authorization/ethics). "
            f"Got corpus: {combined[:300]!r}"
        )

    def test_no_em_dash_in_solano_content(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        solano_ids = {"solano_default", "solano_victorious", "solano_declined"}
        all_text_parts: list[str] = []
        for tree_id, tree in dl.dialogue_trees.items():
            if tree_id not in solano_ids:
                continue
            for node in tree.nodes.values():
                if node.speaker_id == "imre_solano":
                    all_text_parts.append(node.text)
        scar = next(
            (line for line in dl.station_chatter_lines if line.id == "al_scar_d7_solano_01"),
            None,
        )
        if scar is not None:
            all_text_parts.append(scar.text)
        combined = " ".join(all_text_parts)
        for char in ("—", "–", "―"):
            assert char not in combined, (
                f"Em-dash {char!r} found in Solano content. Writing Bible forbids em-dashes."
            )

    def test_no_em_dash_in_marchetti_content(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        marchetti_ids = {"marchetti_default", "marchetti_victorious", "marchetti_declined"}
        all_text_parts: list[str] = []
        for tree_id, tree in dl.dialogue_trees.items():
            if tree_id not in marchetti_ids:
                continue
            for node in tree.nodes.values():
                if node.speaker_id == "rasheeda_marchetti":
                    all_text_parts.append(node.text)
        combined = " ".join(all_text_parts)
        for char in ("—", "–", "―"):
            assert char not in combined, (
                f"Em-dash {char!r} found in Marchetti content. Writing Bible forbids em-dashes."
            )


class TestD7ConsumerAllowlist:
    """AC16: KNOWN_CONSUMER_ONLY_ORPHANS contains all four D7 flags."""

    def test_d7_flags_in_consumer_allowlist(self) -> None:
        from tests.test_data.test_dialogue_integrity import KNOWN_CONSUMER_ONLY_ORPHANS

        required_flags = {
            "lens_closed_faith",
            "lens_closed_transcendence",
            "d7_faith_won",
            "d7_transcendence_won",
        }
        missing = required_flags - KNOWN_CONSUMER_ONLY_ORPHANS
        assert not missing, (
            f"The following D7 flags are missing from KNOWN_CONSUMER_ONLY_ORPHANS: {missing}. "
            "Add them per the DETECTOR MISS convention (A2-18 Task 7)."
        )
