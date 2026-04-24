"""CE-5a: CrewInterjection model + CrewInterjectionResolver tests.

Resolver is exercised against a stubbed CombatState shape (MagicMock)
since the engine doesn't need to know about interjections.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from spacegame.models.crew_interjection import (
    VALID_INTERJECTION_TRIGGERS,
    CrewInterjection,
    CrewInterjectionResolver,
)


def _state(
    round_number: int = 1,
    player_hull: int = 100,
    player_max: int = 100,
    enemies: list[tuple[int, int, str]] | None = None,
):
    """Build a minimal CombatState-like object for resolver tests.

    Each enemy is (current_hull, max_hull, template_id). All enemies
    are treated as alive + not_fled by surviving_enemies.
    """
    if enemies is None:
        enemies = [(80, 80, "pirate_scout")]

    enemy_objs = []
    for hp, max_hp, tid in enemies:
        e = MagicMock()
        e.current_hull = hp
        e.max_hull = max_hp
        e.template = MagicMock()
        e.template.id = tid
        e.is_alive = hp > 0
        e.is_fled = False
        enemy_objs.append(e)

    state = MagicMock()
    state.round_number = round_number
    state.player.hull = player_hull
    state.player.max_hull = player_max
    state.enemies = enemy_objs
    state.surviving_enemies = [e for e in enemy_objs if e.is_alive and not e.is_fled]
    return state


def _crew_aboard() -> list[tuple[str, str]]:
    return [
        ("elena_reeves", "Elena"),
        ("marcus_jin", "Marcus"),
    ]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class TestCrewInterjectionModel:
    def test_round_trip(self) -> None:
        original = CrewInterjection(
            crew_id="elena_reeves",
            trigger="first_turn",
            lines=["Engagement window opens.", "Hold this heading."],
            conditions={"threshold": 0.3},
        )
        round_tripped = CrewInterjection.from_dict(original.to_dict())
        assert round_tripped == original

    def test_valid_triggers_constant(self) -> None:
        assert "first_turn" in VALID_INTERJECTION_TRIGGERS
        assert "player_low_hp" in VALID_INTERJECTION_TRIGGERS
        assert "enemy_low_hp" in VALID_INTERJECTION_TRIGGERS
        assert "enemy_type_match" in VALID_INTERJECTION_TRIGGERS
        assert "combat_outcome" in VALID_INTERJECTION_TRIGGERS


# ---------------------------------------------------------------------------
# first_turn
# ---------------------------------------------------------------------------


class TestFirstTurnTrigger:
    def test_fires_on_round_one(self) -> None:
        entry = CrewInterjection(
            crew_id="elena_reeves",
            trigger="first_turn",
            lines=["Engagement window opens."],
        )
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(_state(round_number=1))
        assert len(events) == 1
        assert events[0].crew_id == "elena_reeves"
        assert events[0].crew_name == "Elena"

    def test_does_not_fire_round_two(self) -> None:
        entry = CrewInterjection("elena_reeves", "first_turn", ["x"])
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(_state(round_number=2))
        assert events == []

    def test_does_not_fire_for_crew_not_aboard(self) -> None:
        entry = CrewInterjection("dr_priya_osei", "first_turn", ["x"])
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(_state())
        assert events == []


# ---------------------------------------------------------------------------
# player_low_hp / enemy_low_hp
# ---------------------------------------------------------------------------


class TestPlayerLowHpTrigger:
    def test_fires_at_threshold(self) -> None:
        entry = CrewInterjection("marcus_jin", "player_low_hp", ["Hold on."])
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(_state(player_hull=25))
        assert len(events) == 1

    def test_does_not_fire_above_threshold(self) -> None:
        entry = CrewInterjection("marcus_jin", "player_low_hp", ["Hold on."])
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(_state(player_hull=50))
        assert events == []

    def test_custom_threshold(self) -> None:
        entry = CrewInterjection(
            "marcus_jin",
            "player_low_hp",
            ["Hold on."],
            conditions={"threshold": 0.5},
        )
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(_state(player_hull=49))
        assert len(events) == 1


class TestEnemyLowHpTrigger:
    def test_fires_when_any_enemy_below_threshold(self) -> None:
        entry = CrewInterjection("elena_reeves", "enemy_low_hp", ["He's done."])
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(
            _state(enemies=[(15, 80, "pirate_scout")])
        )
        assert len(events) == 1

    def test_does_not_fire_when_all_enemies_healthy(self) -> None:
        entry = CrewInterjection("elena_reeves", "enemy_low_hp", ["He's done."])
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(
            _state(enemies=[(80, 80, "pirate_scout")])
        )
        assert events == []


# ---------------------------------------------------------------------------
# enemy_type_match
# ---------------------------------------------------------------------------


class TestEnemyTypeMatchTrigger:
    def test_fires_when_template_id_present(self) -> None:
        entry = CrewInterjection(
            "marcus_jin",
            "enemy_type_match",
            ["I know that hull."],
            conditions={"enemy_template_id": "union_brawler"},
        )
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(
            _state(enemies=[(80, 80, "union_brawler")])
        )
        assert len(events) == 1

    def test_does_not_fire_when_template_absent(self) -> None:
        entry = CrewInterjection(
            "marcus_jin",
            "enemy_type_match",
            ["I know that hull."],
            conditions={"enemy_template_id": "union_brawler"},
        )
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(
            _state(enemies=[(80, 80, "pirate_scout")])
        )
        assert events == []

    def test_no_template_id_means_no_fire(self) -> None:
        entry = CrewInterjection(
            "marcus_jin", "enemy_type_match", ["x"], conditions={}
        )
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(_state())
        assert events == []


# ---------------------------------------------------------------------------
# combat_outcome
# ---------------------------------------------------------------------------


class TestCombatOutcomeTrigger:
    def test_victory_outcome_fires(self) -> None:
        entry = CrewInterjection(
            "elena_reeves",
            "combat_outcome",
            ["Engagement closed."],
            conditions={"outcome": "victory"},
        )
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_outcome(_state(), "victory")
        assert len(events) == 1

    def test_defeat_outcome_skipped_on_victory_call(self) -> None:
        entry = CrewInterjection(
            "elena_reeves",
            "combat_outcome",
            ["Sorry, Captain."],
            conditions={"outcome": "defeat"},
        )
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_outcome(_state(), "victory")
        assert events == []

    def test_outcome_unspecified_fires_for_either(self) -> None:
        entry = CrewInterjection(
            "elena_reeves", "combat_outcome", ["Done."]
        )
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        # Fires on victory
        events = resolver.evaluate_outcome(_state(), "victory")
        assert len(events) == 1


# ---------------------------------------------------------------------------
# Once-only firing
# ---------------------------------------------------------------------------


class TestCommitGatesFutureFiring:
    """Resolver returns candidates; only committed ones are gated next call.

    The view layer picks one candidate per round (priority + throttle),
    commits it, and the rest stay live for future evaluations.
    """

    def test_uncommitted_candidates_stay_eligible(self) -> None:
        entries = [
            CrewInterjection("elena_reeves", "first_turn", ["a"]),
            CrewInterjection("marcus_jin", "first_turn", ["b"]),
        ]
        resolver = CrewInterjectionResolver(entries, _crew_aboard())
        first = resolver.evaluate_round(_state(round_number=1))
        # Re-evaluate without committing: same candidates returned
        second = resolver.evaluate_round(_state(round_number=1))
        assert len(first) == 2
        assert len(second) == 2

    def test_committed_event_does_not_refire(self) -> None:
        entry = CrewInterjection("elena_reeves", "first_turn", ["x"])
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        events = resolver.evaluate_round(_state(round_number=1))
        assert len(events) == 1
        resolver.commit(events[0])
        # After commit, this entry no longer surfaces
        assert resolver.evaluate_round(_state(round_number=1)) == []

    def test_outcome_event_only_gated_after_commit(self) -> None:
        entry = CrewInterjection(
            "elena_reeves", "combat_outcome", ["Engagement closed."]
        )
        resolver = CrewInterjectionResolver([entry], _crew_aboard())
        a = resolver.evaluate_outcome(_state(), "victory")
        # Without commit, second evaluate still returns the candidate
        b = resolver.evaluate_outcome(_state(), "victory")
        assert len(a) == 1
        assert len(b) == 1
        resolver.commit(a[0])
        assert resolver.evaluate_outcome(_state(), "victory") == []


# ---------------------------------------------------------------------------
# Multiple eligible per evaluate
# ---------------------------------------------------------------------------


class TestMultipleEligible:
    def test_multiple_crew_first_turn_in_same_round(self) -> None:
        entries = [
            CrewInterjection("elena_reeves", "first_turn", ["a"]),
            CrewInterjection("marcus_jin", "first_turn", ["b"]),
        ]
        resolver = CrewInterjectionResolver(entries, _crew_aboard())
        events = resolver.evaluate_round(_state(round_number=1))
        assert len(events) == 2
        # Caller (the view) decides which to display this tick

    def test_line_picked_from_bank_deterministically(self) -> None:
        entry = CrewInterjection(
            "elena_reeves", "first_turn", ["alpha", "beta", "gamma"]
        )
        resolver_a = CrewInterjectionResolver([entry], _crew_aboard(), seed=42)
        resolver_b = CrewInterjectionResolver([entry], _crew_aboard(), seed=42)
        a = resolver_a.evaluate_round(_state(round_number=1))
        b = resolver_b.evaluate_round(_state(round_number=1))
        assert a[0].line == b[0].line
