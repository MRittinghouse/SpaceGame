"""CE-3: ComplicationResolver + content integrity tests.

Resolver is evaluated without running a full combat — we mock or stub
the ``CombatState`` contract and verify trigger evaluation, effect
dispatch, and modifier accumulation in isolation.

Content integrity tests load the real ``complications.json`` and check
every complication has valid structure + resolvable template ids.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from spacegame.models.combat_complication import (
    VALID_EFFECT_TYPES,
    VALID_TRIGGER_TYPES,
    CombatComplication,
)
from spacegame.models.complication_resolver import (
    ComplicationEvent,
    ComplicationResolver,
)


def _state(
    round_number: int = 1,
    player_hull: int = 100,
    player_max: int = 100,
    enemy_hull: int = 100,
    enemy_max: int = 100,
):
    """Build a minimal CombatState-like object sufficient for the resolver.

    The resolver only reads a narrow slice of CombatState: round_number,
    player.hull / player.max_hull, surviving_enemies (with hull /
    max_hull), and mutates fired_complication_ids + the three env
    modifier fields + complication_flags. We fake that shape rather
    than constructing a full CombatState.
    """
    enemy = MagicMock()
    enemy.current_hull = enemy_hull
    enemy.max_hull = enemy_max

    state = MagicMock()
    state.round_number = round_number
    state.player.hull = player_hull
    state.player.max_hull = player_max
    state.surviving_enemies = [enemy]
    state.fired_complication_ids = set()
    state.shield_regen_multiplier = 1.0
    state.player_evasion_modifier = 0
    state.enemy_accuracy_multiplier = 1.0
    state.complication_flags = set()
    return state


# ---------------------------------------------------------------------------
# Trigger evaluation
# ---------------------------------------------------------------------------


class TestTurnCounterTrigger:
    def test_fires_on_target_turn(self) -> None:
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 3},
            effect_type="narration",
            effect_params={"flag_name": "f"},
        )
        resolver = ComplicationResolver([comp])
        events = resolver.evaluate(_state(round_number=3))
        assert len(events) == 1

    def test_does_not_fire_before_target_turn(self) -> None:
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 3},
            effect_type="narration",
        )
        resolver = ComplicationResolver([comp])
        events = resolver.evaluate(_state(round_number=2))
        assert events == []

    def test_fires_on_later_turn_if_missed(self) -> None:
        """Turn-counter triggers fire at or after target — if the resolver
        wasn't called on turn 3, it should still fire on turn 4."""
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 3},
            effect_type="narration",
        )
        resolver = ComplicationResolver([comp])
        events = resolver.evaluate(_state(round_number=4))
        assert len(events) == 1


class TestHpThresholdTrigger:
    def test_player_threshold_fires(self) -> None:
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="hp_threshold",
            trigger_params={"target": "player", "hp_pct": 0.3},
            effect_type="narration",
            effect_params={"flag_name": "f"},
        )
        resolver = ComplicationResolver([comp])
        # 25 / 100 = 25% ≤ 30% threshold
        events = resolver.evaluate(_state(player_hull=25, player_max=100))
        assert len(events) == 1

    def test_player_threshold_not_met(self) -> None:
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="hp_threshold",
            trigger_params={"target": "player", "hp_pct": 0.3},
            effect_type="narration",
        )
        resolver = ComplicationResolver([comp])
        events = resolver.evaluate(_state(player_hull=50, player_max=100))
        assert events == []

    def test_enemy_threshold_fires(self) -> None:
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="hp_threshold",
            trigger_params={"target": "enemy", "hp_pct": 0.5},
            effect_type="environmental",
            effect_params={"enemy_accuracy_multiplier": 0.9},
        )
        resolver = ComplicationResolver([comp])
        events = resolver.evaluate(_state(enemy_hull=40, enemy_max=100))
        assert len(events) == 1


# ---------------------------------------------------------------------------
# Once-only firing
# ---------------------------------------------------------------------------


class TestOnceOnlyFiring:
    def test_complication_does_not_re_fire(self) -> None:
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 1},
            effect_type="narration",
        )
        resolver = ComplicationResolver([comp])
        state = _state(round_number=1)
        events1 = resolver.evaluate(state)
        events2 = resolver.evaluate(state)
        assert len(events1) == 1
        assert events2 == [], "fired id must be tracked in state.fired_complication_ids"


# ---------------------------------------------------------------------------
# Effect handlers
# ---------------------------------------------------------------------------


class TestSpawnReinforcementEffect:
    def test_returns_template_ids_without_spawning_directly(self) -> None:
        """Resolver does not touch state.enemies — that's the engine's job.
        It returns spawn intent in the event."""
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 1},
            effect_type="spawn_reinforcement",
            effect_params={"template_ids": ["pirate_scout", "pirate_raider"]},
        )
        resolver = ComplicationResolver([comp])
        state = _state(round_number=1)
        events = resolver.evaluate(state)
        assert events[0].spawned_template_ids == ["pirate_scout", "pirate_raider"]


class TestEnvironmentalEffect:
    def test_shield_regen_multiplier_applies(self) -> None:
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 1},
            effect_type="environmental",
            effect_params={"shield_regen_multiplier": 0.5},
        )
        resolver = ComplicationResolver([comp])
        state = _state(round_number=1)
        resolver.evaluate(state)
        assert state.shield_regen_multiplier == 0.5

    def test_evasion_modifier_adds(self) -> None:
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 1},
            effect_type="environmental",
            effect_params={"player_evasion_modifier": -3},
        )
        resolver = ComplicationResolver([comp])
        state = _state(round_number=1)
        resolver.evaluate(state)
        assert state.player_evasion_modifier == -3

    def test_enemy_accuracy_multiplier(self) -> None:
        comp = CombatComplication(
            id="t",
            name="t",
            description="",
            trigger_type="hp_threshold",
            trigger_params={"target": "enemy", "hp_pct": 0.5},
            effect_type="environmental",
            effect_params={"enemy_accuracy_multiplier": 0.9},
        )
        resolver = ComplicationResolver([comp])
        state = _state(enemy_hull=40, enemy_max=100)
        resolver.evaluate(state)
        assert state.enemy_accuracy_multiplier == pytest.approx(0.9)


class TestNarrationEffect:
    def test_sets_flag_on_state(self) -> None:
        comp = CombatComplication(
            id="morale_shift",
            name="Morale Shift",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 1},
            effect_type="narration",
            effect_params={"flag_name": "player_low_hp_moment"},
        )
        resolver = ComplicationResolver([comp])
        state = _state(round_number=1)
        resolver.evaluate(state)
        assert "player_low_hp_moment" in state.complication_flags

    def test_flag_defaults_to_complication_id(self) -> None:
        comp = CombatComplication(
            id="my_beat",
            name="m",
            description="",
            trigger_type="turn_counter",
            trigger_params={"turn": 1},
            effect_type="narration",
        )
        resolver = ComplicationResolver([comp])
        state = _state(round_number=1)
        resolver.evaluate(state)
        assert "my_beat" in state.complication_flags


# ---------------------------------------------------------------------------
# Content integrity
# ---------------------------------------------------------------------------


class TestComplicationsJsonContent:
    """Load the real complications.json and validate content shape."""

    def test_loader_parses_roster(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        assert len(dl.complications) >= 6, "CE-3 ships at least 6 complications"

    def test_all_trigger_types_valid(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for comp in dl.complications.values():
            assert comp.trigger_type in VALID_TRIGGER_TYPES, (
                f"{comp.id} trigger_type='{comp.trigger_type}' not in registry"
            )

    def test_all_effect_types_valid(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for comp in dl.complications.values():
            assert comp.effect_type in VALID_EFFECT_TYPES, (
                f"{comp.id} effect_type='{comp.effect_type}' not in registry"
            )

    def test_spawn_reinforcement_templates_resolve(self) -> None:
        """spawn_reinforcement effect_params.template_ids must resolve."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for comp in dl.complications.values():
            if comp.effect_type != "spawn_reinforcement":
                continue
            tids = comp.effect_params.get("template_ids", [])
            for tid in tids:
                assert tid in dl.enemy_templates, (
                    f"{comp.id} references unknown enemy template '{tid}'"
                )

    def test_narration_present_on_every_complication(self) -> None:
        """Every shipping complication has player-facing narration."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for comp in dl.complications.values():
            assert comp.narration.strip(), f"{comp.id} has empty narration"

    def test_no_em_dashes_in_complication_narration(self) -> None:
        """Writing Bible discipline on complication content."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        offenders = []
        for comp in dl.complications.values():
            if "\u2014" in comp.narration or "\u2013" in comp.narration:
                offenders.append(f"{comp.id}: {comp.narration[:80]!r}")
        assert not offenders, "Em/en dashes in complication narration:\n  " + "\n  ".join(offenders)


class TestEncounterComplicationIdsField:
    def test_default_empty_list(self) -> None:
        from spacegame.models.encounter import (
            EncounterChoice,
            EncounterDefinition,
            EncounterOutcome,
        )

        defn = EncounterDefinition(
            id="x",
            encounter_type="t",
            name="n",
            description="d",
            choices=[
                EncounterChoice(
                    id="c",
                    label="l",
                    description="",
                    outcome=EncounterOutcome(description="", rewards=[]),
                )
            ],
        )
        assert defn.complication_ids == []

    def test_parser_threads_complication_ids(self) -> None:
        from spacegame.data_loader import DataLoader

        dl = DataLoader()
        raw = {
            "id": "test_ce3",
            "encounter_type": "hostile",
            "name": "T",
            "description": "d",
            "choices": [],
            "complication_ids": ["reinforcement_arrival", "shield_harmonic"],
        }
        defn = dl._parse_encounter_definition(raw)
        assert defn.complication_ids == ["reinforcement_arrival", "shield_harmonic"]
