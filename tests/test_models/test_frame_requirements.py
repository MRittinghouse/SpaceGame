"""Tests for FrameRequirements — per-frame slot min/max/min_size system.

Covers FrameRequirements parsing, validation, flight-readiness checks,
size constraints, fallback generation, and data integrity across all ships.
"""

import json
from pathlib import Path

import pytest

from spacegame.models.ship_build import (
    FRAME_SLOT_LIMITS,
    FrameRequirements,
    PlacedSlot,
    ShipBuild,
)

# ============================================================================
# Constants
# ============================================================================

SLOT_TYPES = [
    "cockpit",
    "engine",
    "fuel",
    "reactor",
    "weapon",
    "defense",
    "utility",
    "cargo",
    "crew_quarters",
]

SIZE_ORDER = {"small": 0, "medium": 1, "large": 2}

# ============================================================================
# Helpers
# ============================================================================


def _sample_requirements() -> dict[str, dict[str, int | str]]:
    """War Frigate-style requirements for testing."""
    return {
        "cockpit": {"min": 1, "max": 1, "min_size": "medium"},
        "engine": {"min": 2, "max": 2, "min_size": "medium"},
        "fuel": {"min": 1, "max": 2, "min_size": "medium"},
        "reactor": {"min": 1, "max": 2, "min_size": "small"},
        "weapon": {"min": 0, "max": 5, "min_size": "small"},
        "defense": {"min": 0, "max": 4, "min_size": "small"},
        "utility": {"min": 0, "max": 3, "min_size": "small"},
        "cargo": {"min": 0, "max": 3, "min_size": "small"},
        "crew_quarters": {"min": 1, "max": 3, "min_size": "small"},
    }


def _load_ship_types_json() -> list[dict]:
    """Load raw ship types from JSON for data integrity tests."""
    path = Path(__file__).resolve().parents[2] / "data" / "ships" / "ship_types.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["ship_types"]


# ============================================================================
# FrameRequirements — Construction and Accessors
# ============================================================================


class TestFrameRequirementsConstruction:
    def test_from_dict(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.get_min("weapon") == 0
        assert reqs.get_max("weapon") == 5
        assert reqs.get_min_size("weapon") == "small"

    def test_get_min_returns_correct_value(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.get_min("engine") == 2
        assert reqs.get_min("cockpit") == 1
        assert reqs.get_min("cargo") == 0

    def test_get_max_returns_correct_value(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.get_max("engine") == 2
        assert reqs.get_max("weapon") == 5
        assert reqs.get_max("crew_quarters") == 3

    def test_get_min_size_returns_correct_value(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.get_min_size("engine") == "medium"
        assert reqs.get_min_size("cockpit") == "medium"
        assert reqs.get_min_size("weapon") == "small"

    def test_unknown_slot_type_returns_defaults(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.get_min("nonexistent") == 0
        assert reqs.get_max("nonexistent") == 0
        assert reqs.get_min_size("nonexistent") == "small"

    def test_empty_requirements_returns_defaults(self) -> None:
        reqs = FrameRequirements({})
        assert reqs.get_min("weapon") == 0
        assert reqs.get_max("weapon") == 0
        assert reqs.get_min_size("weapon") == "small"


# ============================================================================
# Size Validation
# ============================================================================


class TestSizeValidation:
    def test_small_slot_valid_when_min_size_small(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.is_slot_size_valid("weapon", "small") is True

    def test_medium_slot_valid_when_min_size_small(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.is_slot_size_valid("weapon", "medium") is True

    def test_large_slot_valid_when_min_size_small(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.is_slot_size_valid("weapon", "large") is True

    def test_small_slot_invalid_when_min_size_medium(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.is_slot_size_valid("engine", "small") is False

    def test_medium_slot_valid_when_min_size_medium(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.is_slot_size_valid("engine", "medium") is True

    def test_large_slot_valid_when_min_size_medium(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.is_slot_size_valid("engine", "large") is True

    def test_unknown_slot_type_accepts_any_size(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        assert reqs.is_slot_size_valid("nonexistent", "small") is True


# ============================================================================
# Flight Readiness
# ============================================================================


class TestFlightReadiness:
    def test_all_mins_met_is_flight_ready(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        slot_counts = {
            "cockpit": 1,
            "engine": 2,
            "fuel": 1,
            "reactor": 1,
            "crew_quarters": 1,
        }
        slot_sizes: dict[str, list[str]] = {
            "cockpit": ["medium"],
            "engine": ["medium", "medium"],
            "fuel": ["medium"],
            "reactor": ["small"],
            "crew_quarters": ["small"],
        }
        ready, reasons = reqs.check_flight_ready(slot_counts, slot_sizes)
        assert ready is True, f"Should be flight ready, got reasons: {reasons}"
        assert reasons == []

    def test_missing_engine_not_flight_ready(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        slot_counts = {
            "cockpit": 1,
            "engine": 1,  # Need 2
            "fuel": 1,
            "reactor": 1,
            "crew_quarters": 1,
        }
        slot_sizes: dict[str, list[str]] = {
            "cockpit": ["medium"],
            "engine": ["medium"],
            "fuel": ["medium"],
            "reactor": ["small"],
            "crew_quarters": ["small"],
        }
        ready, reasons = reqs.check_flight_ready(slot_counts, slot_sizes)
        assert ready is False
        assert any("engine" in r.lower() for r in reasons)

    def test_undersized_slot_not_flight_ready(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        slot_counts = {
            "cockpit": 1,
            "engine": 2,
            "fuel": 1,
            "reactor": 1,
            "crew_quarters": 1,
        }
        slot_sizes: dict[str, list[str]] = {
            "cockpit": ["medium"],
            "engine": ["small", "medium"],  # One engine is too small
            "fuel": ["medium"],
            "reactor": ["small"],
            "crew_quarters": ["small"],
        }
        ready, reasons = reqs.check_flight_ready(slot_counts, slot_sizes)
        assert ready is False
        assert any("size" in r.lower() or "engine" in r.lower() for r in reasons)

    def test_zero_min_slots_not_required(self) -> None:
        """Weapon/defense/utility with min=0 don't block flight readiness."""
        reqs = FrameRequirements(_sample_requirements())
        slot_counts = {
            "cockpit": 1,
            "engine": 2,
            "fuel": 1,
            "reactor": 1,
            "crew_quarters": 1,
            # No weapons, defense, utility, or cargo
        }
        slot_sizes: dict[str, list[str]] = {
            "cockpit": ["medium"],
            "engine": ["medium", "large"],
            "fuel": ["medium"],
            "reactor": ["small"],
            "crew_quarters": ["small"],
        }
        ready, reasons = reqs.check_flight_ready(slot_counts, slot_sizes)
        assert ready is True, f"Should be ready with 0 optional slots: {reasons}"

    def test_empty_build_not_flight_ready(self) -> None:
        reqs = FrameRequirements(_sample_requirements())
        ready, reasons = reqs.check_flight_ready({}, {})
        assert ready is False
        assert len(reasons) > 0


# ============================================================================
# Fallback from Weight Class
# ============================================================================


class TestFallbackFromWeightClass:
    def test_fallback_large_has_correct_maxes(self) -> None:
        reqs = FrameRequirements.fallback_from_weight_class("large")
        assert reqs.get_max("weapon") == FRAME_SLOT_LIMITS["large"]["weapon"]
        assert reqs.get_max("defense") == FRAME_SLOT_LIMITS["large"]["defense"]
        assert reqs.get_max("engine") == FRAME_SLOT_LIMITS["large"]["engine"]

    def test_fallback_tiny_has_correct_maxes(self) -> None:
        reqs = FrameRequirements.fallback_from_weight_class("tiny")
        assert reqs.get_max("weapon") == FRAME_SLOT_LIMITS["tiny"]["weapon"]
        assert reqs.get_max("cargo") == FRAME_SLOT_LIMITS["tiny"]["cargo"]

    def test_fallback_unknown_weight_class_returns_empty(self) -> None:
        reqs = FrameRequirements.fallback_from_weight_class("nonexistent")
        assert reqs.get_max("weapon") == 0

    def test_fallback_sets_min_to_infrastructure_defaults(self) -> None:
        """Fallback should set reasonable minimums for infrastructure."""
        reqs = FrameRequirements.fallback_from_weight_class("large")
        assert reqs.get_min("cockpit") >= 1
        assert reqs.get_min("engine") >= 1
        assert reqs.get_min("fuel") >= 1
        assert reqs.get_min("reactor") >= 1

    def test_fallback_all_weight_classes_valid(self) -> None:
        for wc in ("tiny", "small", "medium", "large", "xlarge"):
            reqs = FrameRequirements.fallback_from_weight_class(wc)
            for slot_type in SLOT_TYPES:
                assert reqs.get_min(slot_type) <= reqs.get_max(slot_type), (
                    f"{wc}/{slot_type}: min {reqs.get_min(slot_type)} > "
                    f"max {reqs.get_max(slot_type)}"
                )


# ============================================================================
# from_ship_type factory
# ============================================================================


class TestFromShipType:
    def test_from_ship_type_reads_frame_requirements(self) -> None:
        """ShipType with frame_requirements produces correct FrameRequirements."""

        class FakeShipType:
            frame_requirements = _sample_requirements()
            ship_class = "late_game"

        reqs = FrameRequirements.from_ship_type(FakeShipType())
        assert reqs.get_max("weapon") == 5
        assert reqs.get_min("engine") == 2

    def test_from_ship_type_empty_falls_back(self) -> None:
        """ShipType without frame_requirements falls back to weight class."""

        class FakeShipType:
            frame_requirements: dict = {}
            ship_class = "late_game"

        reqs = FrameRequirements.from_ship_type(FakeShipType())
        # Should get large fallback maxes
        assert reqs.get_max("weapon") == FRAME_SLOT_LIMITS["large"]["weapon"]


# ============================================================================
# ShipBuild — ship_type_id serialization
# ============================================================================


class TestShipBuildShipTypeId:
    def test_to_dict_includes_ship_type_id(self) -> None:
        build = ShipBuild(weight_class="large", ship_type_id="war_frigate")
        d = build.to_dict()
        assert d["ship_type_id"] == "war_frigate"

    def test_from_dict_restores_ship_type_id(self) -> None:
        build = ShipBuild(weight_class="large", ship_type_id="clipper")
        d = build.to_dict()
        restored = ShipBuild.from_dict(d)
        assert restored.ship_type_id == "clipper"

    def test_from_dict_backward_compat_no_ship_type_id(self) -> None:
        d = {"weight_class": "large", "pixels": [], "slots": []}
        build = ShipBuild.from_dict(d)
        assert build.ship_type_id is None

    def test_to_dict_omits_none_ship_type_id(self) -> None:
        build = ShipBuild(weight_class="large")
        d = build.to_dict()
        assert "ship_type_id" not in d or d.get("ship_type_id") is None


# ============================================================================
# Data Integrity — all ships in ship_types.json
# ============================================================================


class TestDataIntegrity:
    """Validate frame_requirements data across all ships in ship_types.json."""

    @pytest.fixture(scope="class")
    def ship_types(self) -> list[dict]:
        return _load_ship_types_json()

    def test_all_ships_have_frame_requirements(self, ship_types: list[dict]) -> None:
        for ship in ship_types:
            assert "frame_requirements" in ship, (
                f"{ship['id']} missing frame_requirements"
            )
            assert isinstance(ship["frame_requirements"], dict)

    def test_all_ships_min_lte_max(self, ship_types: list[dict]) -> None:
        for ship in ship_types:
            reqs = FrameRequirements(ship.get("frame_requirements", {}))
            for slot_type in SLOT_TYPES:
                min_val = reqs.get_min(slot_type)
                max_val = reqs.get_max(slot_type)
                assert min_val <= max_val, (
                    f"{ship['id']}/{slot_type}: min {min_val} > max {max_val}"
                )

    def test_all_ships_valid_min_size(self, ship_types: list[dict]) -> None:
        valid_sizes = {"small", "medium", "large"}
        for ship in ship_types:
            reqs = ship.get("frame_requirements", {})
            for slot_type, spec in reqs.items():
                min_size = spec.get("min_size", "small")
                assert min_size in valid_sizes, (
                    f"{ship['id']}/{slot_type}: invalid min_size '{min_size}'"
                )

    def test_all_ships_have_cockpit_min_1(self, ship_types: list[dict]) -> None:
        for ship in ship_types:
            reqs = FrameRequirements(ship.get("frame_requirements", {}))
            assert reqs.get_min("cockpit") >= 1, (
                f"{ship['id']} has cockpit min < 1"
            )

    def test_all_ships_have_engine_min_gte_1(self, ship_types: list[dict]) -> None:
        for ship in ship_types:
            reqs = FrameRequirements(ship.get("frame_requirements", {}))
            assert reqs.get_min("engine") >= 1, (
                f"{ship['id']} has engine min < 1"
            )

    def test_weapon_max_gte_weapon_slots(self, ship_types: list[dict]) -> None:
        """frame_requirements weapon max must be >= legacy weapon_slots field."""
        for ship in ship_types:
            reqs = FrameRequirements(ship.get("frame_requirements", {}))
            weapon_slots = ship.get("weapon_slots", 0)
            assert reqs.get_max("weapon") >= weapon_slots, (
                f"{ship['id']}: weapon max {reqs.get_max('weapon')} < "
                f"weapon_slots {weapon_slots}"
            )

    def test_defense_max_gte_defense_slots(self, ship_types: list[dict]) -> None:
        for ship in ship_types:
            reqs = FrameRequirements(ship.get("frame_requirements", {}))
            defense_slots = ship.get("defense_slots", 0)
            assert reqs.get_max("defense") >= defense_slots, (
                f"{ship['id']}: defense max {reqs.get_max('defense')} < "
                f"defense_slots {defense_slots}"
            )

    def test_utility_max_gte_utility_slots(self, ship_types: list[dict]) -> None:
        for ship in ship_types:
            reqs = FrameRequirements(ship.get("frame_requirements", {}))
            utility_slots = ship.get("utility_slots", 3)
            assert reqs.get_max("utility") >= utility_slots, (
                f"{ship['id']}: utility max {reqs.get_max('utility')} < "
                f"utility_slots {utility_slots}"
            )

    def test_all_ships_have_unique_frame_requirements(
        self, ship_types: list[dict]
    ) -> None:
        """Each ship should have distinct frame_requirements for identity."""
        import json

        seen: dict[str, str] = {}
        for ship in ship_types:
            sig = json.dumps(ship.get("frame_requirements", {}), sort_keys=True)
            if sig in seen:
                assert False, (
                    f"{ship['id']} has identical frame_requirements to "
                    f"{seen[sig]}"
                )
            seen[sig] = ship["id"]


# ============================================================================
# Preset Generation — respects frame_requirements
# ============================================================================


class TestPresetGeneration:
    """Verify presets use appropriately sized slots from frame_requirements."""

    def test_large_ship_uses_medium_engines(self) -> None:
        """War Frigate preset should use medium+ engine slots, not small."""
        from spacegame.data_loader import DataLoader

        dl = DataLoader()
        dl.load_all()
        ship_type = dl.ship_types.get("war_frigate")
        assert ship_type is not None

        from spacegame.models.ship_presets import generate_preset_from_ship_type

        build = generate_preset_from_ship_type(ship_type)
        engine_defs = [
            ps.slot_def_id for ps in build.placed_slots if "engine" in ps.slot_def_id
        ]
        assert len(engine_defs) >= 2, "War Frigate should have >= 2 engines"
        for def_id in engine_defs:
            assert "small" not in def_id, (
                f"War Frigate engine should be medium+, got {def_id}"
            )

    def test_tiny_ship_uses_small_slots(self) -> None:
        """Shuttle preset should use small slots."""
        from spacegame.data_loader import DataLoader

        dl = DataLoader()
        dl.load_all()
        ship_type = dl.ship_types.get("shuttle")
        assert ship_type is not None

        from spacegame.models.ship_presets import generate_preset_from_ship_type

        build = generate_preset_from_ship_type(ship_type)
        assert len(build.placed_slots) > 0, "Shuttle should have placed slots"

    def test_preset_sets_ship_type_id(self) -> None:
        """Preset builds should carry the ship_type_id."""
        from spacegame.data_loader import DataLoader

        dl = DataLoader()
        dl.load_all()
        ship_type = dl.ship_types.get("clipper")
        assert ship_type is not None

        from spacegame.models.ship_presets import generate_preset_from_ship_type

        build = generate_preset_from_ship_type(ship_type)
        assert build.ship_type_id == "clipper"
