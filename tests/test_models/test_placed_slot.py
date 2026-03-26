"""Tests for PlacedSlot dataclass and ShipBuild placed_slots integration."""

from spacegame.models.ship_build import FRAME_SLOT_LIMITS, PlacedSlot, ShipBuild


class TestPlacedSlot:
    def test_basic_creation(self) -> None:
        ps = PlacedSlot(slot_def_id="weapon_small", x=5, y=3)
        assert ps.slot_def_id == "weapon_small"
        assert ps.x == 5
        assert ps.y == 3
        assert ps.rotation == 0
        assert ps.equipped_part_id is None

    def test_with_equipment(self) -> None:
        ps = PlacedSlot(
            slot_def_id="defense_medium",
            x=10,
            y=8,
            rotation=90,
            equipped_part_id="shield_gen_mk2",
        )
        assert ps.equipped_part_id == "shield_gen_mk2"
        assert ps.rotation == 90

    def test_to_dict_minimal(self) -> None:
        ps = PlacedSlot(slot_def_id="engine_small", x=2, y=14)
        d = ps.to_dict()
        assert d["slot_def_id"] == "engine_small"
        assert d["x"] == 2
        assert d["y"] == 14
        # Defaults should be omitted for compact serialization
        assert "rotation" not in d
        assert "equipped_part_id" not in d

    def test_to_dict_full(self) -> None:
        ps = PlacedSlot(
            slot_def_id="weapon_large",
            x=8,
            y=4,
            rotation=180,
            equipped_part_id="heavy_railgun",
        )
        d = ps.to_dict()
        assert d["rotation"] == 180
        assert d["equipped_part_id"] == "heavy_railgun"

    def test_from_dict_minimal(self) -> None:
        d = {"slot_def_id": "cargo_large", "x": 0, "y": 0}
        ps = PlacedSlot.from_dict(d)
        assert ps.slot_def_id == "cargo_large"
        assert ps.rotation == 0
        assert ps.equipped_part_id is None

    def test_round_trip(self) -> None:
        original = PlacedSlot(
            slot_def_id="reactor_medium",
            x=12,
            y=6,
            rotation=270,
            equipped_part_id="fusion_core",
        )
        restored = PlacedSlot.from_dict(original.to_dict())
        assert restored.slot_def_id == original.slot_def_id
        assert restored.x == original.x
        assert restored.y == original.y
        assert restored.rotation == original.rotation
        assert restored.equipped_part_id == original.equipped_part_id


class TestShipBuildWithPlacedSlots:
    def test_build_with_placed_slots(self) -> None:
        build = ShipBuild(
            weight_class="small",
            placed_slots=[
                PlacedSlot(slot_def_id="weapon_small", x=5, y=2),
                PlacedSlot(
                    slot_def_id="engine_small",
                    x=10,
                    y=14,
                    equipped_part_id="ion_thruster",
                ),
            ],
        )
        assert len(build.placed_slots) == 2
        assert build.placed_slots[1].equipped_part_id == "ion_thruster"

    def test_build_round_trip_with_placed_slots(self) -> None:
        build = ShipBuild(
            weight_class="medium",
            placed_slots=[
                PlacedSlot(slot_def_id="weapon_medium", x=3, y=5),
                PlacedSlot(
                    slot_def_id="defense_small",
                    x=8,
                    y=8,
                    equipped_part_id="light_shield",
                ),
                PlacedSlot(slot_def_id="cargo_large", x=2, y=10),
            ],
        )
        d = build.to_dict()
        assert "placed_slots" in d
        assert len(d["placed_slots"]) == 3

        restored = ShipBuild.from_dict(d)
        assert len(restored.placed_slots) == 3
        assert restored.placed_slots[0].slot_def_id == "weapon_medium"
        assert restored.placed_slots[1].equipped_part_id == "light_shield"
        assert restored.placed_slots[2].slot_def_id == "cargo_large"

    def test_backward_compat_no_placed_slots(self) -> None:
        """Old saves without placed_slots should load with empty list."""
        d = {"weight_class": "small", "pixels": [], "slots": []}
        build = ShipBuild.from_dict(d)
        assert build.placed_slots == []
        assert build.modules == []

    def test_build_can_have_both_modules_and_slots(self) -> None:
        """During migration, builds might have both legacy modules and new slots."""
        build = ShipBuild(
            weight_class="small",
            placed_slots=[PlacedSlot(slot_def_id="weapon_small", x=5, y=2)],
        )
        # Both fields coexist
        assert len(build.placed_slots) == 1
        assert len(build.modules) == 0


class TestFrameSlotLimits:
    def test_all_weight_classes_have_limits(self) -> None:
        for wc in ["tiny", "small", "medium", "large", "xlarge"]:
            assert wc in FRAME_SLOT_LIMITS, f"Missing limits for {wc}"

    def test_limits_include_all_slot_types(self) -> None:
        expected_types = {
            "cockpit",
            "weapon",
            "defense",
            "engine",
            "utility",
            "cargo",
            "crew_quarters",
            "reactor",
        }
        for wc, limits in FRAME_SLOT_LIMITS.items():
            for st in expected_types:
                assert st in limits, f"Missing {st} in {wc} limits"

    def test_limits_scale_with_weight_class(self) -> None:
        """Larger frames should generally allow more slots."""
        small = FRAME_SLOT_LIMITS["small"]
        large = FRAME_SLOT_LIMITS["large"]
        assert large["weapon"] > small["weapon"]
        assert large["cargo"] > small["cargo"]

    def test_all_limits_positive(self) -> None:
        for wc, limits in FRAME_SLOT_LIMITS.items():
            for st, count in limits.items():
                assert count >= 1, f"{wc}.{st} has non-positive limit: {count}"
