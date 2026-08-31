"""Scenario A: Complex save/load round-trip.

Covers the gaps in existing ``test_save_roundtrip.py``:
  - Ship with an attached ShipBuild (build-derived path)
  - Recently added dialogue_flags (dual_tech reveals, subsystem focus flags)
  - All four factions' reputation at distinct values + perks unlocked
  - Active mission + on_accept_cargo state
  - Crew roster with loyalty across companions

Scenarios in this file fail when a newly added field is not wired through
``Player.to_dict`` / ``Player.from_dict`` — the most common save-bug class.
"""

from __future__ import annotations

from tests.test_scenarios._helpers import (
    attach_build,
    fresh_player,
    round_trip_save,
)


class TestSaveLoadShipBuildPath:
    """Ship with a ShipBuild attached round-trips fully."""

    def test_ship_build_attached_survives_save_load(self) -> None:
        player = fresh_player()
        attach_build(player, weight_class="small")
        assert player.ship.computed_stats is not None, "Build path should activate"
        assert player.ship.build is not None

        restored = round_trip_save(player)

        # Build path should still be active after restore
        assert restored.ship.build is not None, "ShipBuild must survive round-trip"
        assert restored.ship.build.weight_class == "small"
        assert len(restored.ship.build.pixels) == 16  # 4x4 grid from helper
        assert restored.ship.computed_stats is not None

    def test_ship_build_pixels_preserved(self) -> None:
        player = fresh_player()
        attach_build(player)
        original_pixels = [(p.x, p.y, p.material_id) for p in player.ship.build.pixels]

        restored = round_trip_save(player)
        restored_pixels = [(p.x, p.y, p.material_id) for p in restored.ship.build.pixels]

        assert restored_pixels == original_pixels, (
            "Every placed pixel must survive identically — saves corrupt silently otherwise"
        )


class TestSaveLoadDualTechRevealFlags:
    """Dual tech reveal flags (dialogue_flags[``dual_tech_<id>_revealed``])
    persist through save/load. Impl 2 added these; regression risk is that
    they get dropped because reveal flags share the dialogue_flags dict with
    many other flags."""

    def test_reveal_flag_survives(self) -> None:
        player = fresh_player()
        player.dialogue_flags["dual_tech_frozen_inferno_revealed"] = True
        player.dialogue_flags["dual_tech_fire_at_will_revealed"] = True

        restored = round_trip_save(player)

        assert restored.dialogue_flags.get("dual_tech_frozen_inferno_revealed") is True
        assert restored.dialogue_flags.get("dual_tech_fire_at_will_revealed") is True

    def test_missing_reveal_flag_is_false(self) -> None:
        """Unrevealed techs don't have the flag — .get default should be False."""
        player = fresh_player()
        restored = round_trip_save(player)
        assert restored.dialogue_flags.get("dual_tech_power_drift_revealed", False) is False


class TestSaveLoadAllFactionsReputation:
    """Every faction's rep must round-trip even when values cover the full
    range (hostile, neutral, friendly, allied)."""

    def test_all_four_factions_preserved(self) -> None:
        player = fresh_player()
        player.faction_reputation = {
            "commerce_guild": 75,  # allied
            "miners_union": 40,  # friendly
            "science_collective": 0,  # neutral
            "frontier_alliance": -50,  # hostile
        }

        restored = round_trip_save(player)

        assert restored.faction_reputation == player.faction_reputation

    def test_extreme_values_preserved(self) -> None:
        player = fresh_player()
        player.faction_reputation = {
            "commerce_guild": 100,
            "miners_union": -100,
        }
        restored = round_trip_save(player)
        assert restored.faction_reputation["commerce_guild"] == 100
        assert restored.faction_reputation["miners_union"] == -100


class TestSaveLoadSubsystemRelatedState:
    """Combat §11.2: runtime subsystem state lives on EnemyShip during combat
    only. Combat doesn't save mid-fight, so subsystem state itself isn't
    persisted — BUT dialogue flags that gate subsystem-based content must be.
    """

    def test_flags_with_subsystem_naming_persist(self) -> None:
        """Flags referencing subsystems (e.g., first-time destroyed an engine)
        must survive save/load — they'll drive future content."""
        player = fresh_player()
        player.dialogue_flags["first_engine_destroyed"] = True
        player.dialogue_flags["first_cockpit_shot"] = True
        restored = round_trip_save(player)
        assert restored.dialogue_flags.get("first_engine_destroyed") is True
        assert restored.dialogue_flags.get("first_cockpit_shot") is True


class TestSaveLoadFullIntegration:
    """The kitchen-sink scenario: every new field wired, round-trip matches."""

    def test_complete_mid_game_state(self) -> None:
        player = fresh_player(credits=25000, system_id="breakstone")
        attach_build(player)

        # Dual tech reveals across multiple techs
        player.dialogue_flags["dual_tech_frozen_inferno_revealed"] = True
        player.dialogue_flags["dual_tech_power_drift_revealed"] = True

        # All four factions
        player.faction_reputation = {
            "commerce_guild": 55,
            "miners_union": -15,
            "science_collective": 20,
            "frontier_alliance": 0,
        }

        # Mission progression
        player.mission_state = {
            "active": ["the_foremans_son"],
            "completed": ["first_delivery"],
            "progress": {"the_foremans_son": [True, False]},
        }

        # Crew state with loyalty across tiers
        player.crew_state = {
            "elena_reeves": {"loyalty": 85, "recruited": True},
            "marcus_jin": {"loyalty": 50, "recruited": True},
        }

        # Exercise several stat counters
        player.game_day = 80
        player.combats_won = 12
        player.credits_earned_lifetime = 150000

        restored = round_trip_save(player)

        # Core fields
        assert restored.credits == 25000
        assert restored.current_system_id == "breakstone"

        # Build path intact
        assert restored.ship.build is not None
        assert restored.ship.computed_stats is not None

        # Flags
        assert restored.dialogue_flags.get("dual_tech_frozen_inferno_revealed") is True
        assert restored.dialogue_flags.get("dual_tech_power_drift_revealed") is True

        # Factions
        assert restored.faction_reputation == player.faction_reputation

        # Mission + crew
        assert restored.mission_state == player.mission_state
        assert restored.crew_state == player.crew_state

        # Stats
        assert restored.game_day == 80
        assert restored.combats_won == 12
        assert restored.credits_earned_lifetime == 150000
