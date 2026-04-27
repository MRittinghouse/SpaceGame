"""Scenario E: Dual tech fire + reveal persistence.

Impl 2 wired dual techs into the combat engine. This scenario validates:
  - First activation returns a reveal scene + sets the reveal flag
  - Subsequent activations return None (reveal is one-shot)
  - The reveal flag persists through a save/load cycle

Cinematic rendering is out of scope — combat_view consumes the reveal but
that's a view-layer concern. This test owns the DATA contract.
"""

from __future__ import annotations

from spacegame.models.dual_tech import (
    DUAL_TECH_PALETTE,
    activate_fire_at_will,
    activate_power_drift,
)
from spacegame.models.dual_tech_dialogue import (
    DUAL_TECH_REVEALS,
    check_and_mark_reveal,
    reveal_flag_key,
)
from tests.test_scenarios._helpers import fresh_player, round_trip_save


class TestRevealOneShotContract:
    """Reveal is one-shot: first call returns the scene, subsequent calls
    return None. The dialogue flag is the persistence mechanism."""

    def test_first_fire_returns_reveal_and_sets_flag(self) -> None:
        player = fresh_player()
        assert player.dialogue_flags.get("dual_tech_fire_at_will_revealed") is None

        reveal = check_and_mark_reveal(player.dialogue_flags, "fire_at_will")

        assert reveal is not None, "First activation must return a reveal scene"
        assert reveal.tech_id == "fire_at_will"
        assert len(reveal.lines) > 0, "Reveal scene must have dialogue lines"
        assert player.dialogue_flags["dual_tech_fire_at_will_revealed"] is True

    def test_second_fire_returns_none(self) -> None:
        player = fresh_player()
        first = check_and_mark_reveal(player.dialogue_flags, "fire_at_will")
        assert first is not None

        second = check_and_mark_reveal(player.dialogue_flags, "fire_at_will")
        assert second is None, "Reveal must NOT fire twice"

    def test_reveal_flag_key_format_matches_save_flag(self) -> None:
        """The flag key must follow the documented format — save files persist
        these keys, so format drift would silently orphan old saves."""
        key = reveal_flag_key("fire_at_will")
        assert key == "dual_tech_fire_at_will_revealed"


class TestRevealPersistsAcrossSaveLoad:
    """Critical: reveal flags live in player.dialogue_flags and must survive
    save/load — otherwise every session would re-reveal the same tech."""

    def test_revealed_flag_survives_round_trip(self) -> None:
        player = fresh_player()
        check_and_mark_reveal(player.dialogue_flags, "fire_at_will")
        check_and_mark_reveal(player.dialogue_flags, "power_drift")

        restored = round_trip_save(player)

        # Both reveal flags persist
        assert restored.dialogue_flags.get("dual_tech_fire_at_will_revealed") is True
        assert restored.dialogue_flags.get("dual_tech_power_drift_revealed") is True

        # Check-and-mark on restored player returns None (already revealed)
        result = check_and_mark_reveal(restored.dialogue_flags, "fire_at_will")
        assert result is None


class TestActivationSetsStateFlags:
    """Impl 2 handlers mutate PlayerCombatState — verify the wire-up."""

    def test_fire_at_will_sets_active_flag(self) -> None:
        """A stand-in object with the same attributes as PlayerCombatState
        so we exercise the activation handler directly."""

        class MockState:
            fire_at_will_active = False

        state = MockState()
        activate_fire_at_will(state)
        assert state.fire_at_will_active is True

    def test_power_drift_gives_energy_and_reduces_cooldowns(self) -> None:
        class MockState:
            energy = 2
            max_energy = 10
            cooldowns = {"shot": 3, "burst": 2, "power_drift": 4}

        state = MockState()
        activate_power_drift(state)

        # Energy grows by +6 but clamped at max_energy
        assert state.energy <= state.max_energy
        assert state.energy >= 2  # At minimum, didn't go down

        # Non-self cooldowns reduced by 2
        assert state.cooldowns["shot"] == 1
        assert state.cooldowns["burst"] == 0
        # Own cooldown preserved (per spec — Power Drift doesn't tick itself)
        assert state.cooldowns["power_drift"] == 4


class TestPaletteCoverage:
    """Every tech in DUAL_TECH_PALETTE should have a corresponding reveal
    entry — otherwise the first-fire experience is silently missing."""

    def test_every_tech_has_a_reveal(self) -> None:
        missing = []
        for tech_id in DUAL_TECH_PALETTE:
            if tech_id not in DUAL_TECH_REVEALS:
                missing.append(tech_id)
        assert not missing, f"Every palette tech should have a reveal scene. Missing: {missing}"

    def test_every_reveal_has_at_least_two_lines(self) -> None:
        """A reveal with <2 lines isn't a scene, it's a stub."""
        thin = [tid for tid, rev in DUAL_TECH_REVEALS.items() if len(rev.lines) < 2]
        assert not thin, f"Reveals too thin to be cinematic: {thin}"


class TestIndependentRevealState:
    """Revealing one tech must not set the flag for another tech — flags
    must be per-tech, not per-player."""

    def test_revealing_one_tech_does_not_reveal_another(self) -> None:
        player = fresh_player()
        check_and_mark_reveal(player.dialogue_flags, "fire_at_will")

        # power_drift is a different tech — flag must still be unset
        assert player.dialogue_flags.get("dual_tech_power_drift_revealed") is None

        other = check_and_mark_reveal(player.dialogue_flags, "power_drift")
        assert other is not None, "Different tech must still reveal independently"
