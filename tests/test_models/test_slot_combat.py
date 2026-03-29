"""Tests for slot-based combat integration.

Verifies that PlacedSlot+ShipPart builds produce correct combat states,
equipment moves, and module combat states for the combat engine.
"""

from spacegame.models.module_combat import (
    HP_PER_SLOT_CELL,
    get_slot_equipment_moves,
    init_slot_combat_states,
)
from spacegame.models.ship_build import PlacedSlot, ShipBuild
from spacegame.models.ship_part import ShipPart
from spacegame.models.slot_definition import SlotDefinition


def _make_slot_def(
    slot_id: str = "weapon_small",
    slot_type: str = "weapon",
    size: str = "small",
    fw: int = 2,
    fh: int = 2,
) -> SlotDefinition:
    return SlotDefinition(
        id=slot_id,
        slot_type=slot_type,
        size=size,
        footprint_w=fw,
        footprint_h=fh,
        weight=3.0,
        placement_cost=500,
        color=(200, 60, 60),
    )


def _make_part(
    part_id: str = "light_laser",
    slot_type: str = "weapon",
    min_size: str = "small",
    combat_move: dict | None = None,
) -> ShipPart:
    if combat_move is None:
        combat_move = {
            "id": part_id,
            "name": "Light Laser",
            "description": "Pew pew",
            "effects": [{"type": "damage", "value": 10.0}],
            "energy_cost": 2,
            "accuracy_modifier": 0,
        }
    return ShipPart(
        id=part_id,
        name="Light Laser",
        description="A basic weapon",
        slot_type=slot_type,
        min_size=min_size,
        manufacturer="test",
        provides={"damage": 10},
        base_cost=1000,
        combat_move=combat_move,
    )


class TestInitSlotCombatStates:
    def test_basic_states(self) -> None:
        build = ShipBuild(
            weight_class="small",
            placed_slots=[
                PlacedSlot(slot_def_id="weapon_small", x=5, y=5),
                PlacedSlot(slot_def_id="engine_small", x=10, y=10),
            ],
        )
        slot_defs = {
            "weapon_small": _make_slot_def("weapon_small", "weapon", "small", 2, 2),
            "engine_small": _make_slot_def("engine_small", "engine", "small", 2, 3),
        }
        states = init_slot_combat_states(build, slot_defs)
        assert len(states) == 2

        # Weapon slot: 2x2 = 4 cells * HP_PER_SLOT_CELL
        assert states[0].max_hp == 4 * HP_PER_SLOT_CELL
        assert states[0].category == "weapon"
        assert states[0].placed_index == 0

        # Engine slot: 2x3 = 6 cells
        assert states[1].max_hp == 6 * HP_PER_SLOT_CELL
        assert states[1].category == "engine"
        assert states[1].placed_index == 1

    def test_defense_maps_to_shield_category(self) -> None:
        build = ShipBuild(
            weight_class="small",
            placed_slots=[PlacedSlot(slot_def_id="defense_small", x=3, y=3)],
        )
        slot_defs = {
            "defense_small": _make_slot_def("defense_small", "defense", "small", 2, 2),
        }
        states = init_slot_combat_states(build, slot_defs)
        assert states[0].category == "shield"

    def test_empty_build(self) -> None:
        build = ShipBuild(weight_class="small")
        states = init_slot_combat_states(build, {})
        assert states == []

    def test_unknown_slot_def_skipped(self) -> None:
        build = ShipBuild(
            weight_class="small",
            placed_slots=[PlacedSlot(slot_def_id="nonexistent", x=0, y=0)],
        )
        states = init_slot_combat_states(build, {})
        assert states == []


class TestGetSlotEquipmentMoves:
    def test_equipped_weapon_produces_move(self) -> None:
        build = ShipBuild(
            weight_class="small",
            placed_slots=[
                PlacedSlot(
                    slot_def_id="weapon_small",
                    x=5,
                    y=5,
                    equipped_part_id="light_laser",
                ),
            ],
        )
        slot_defs = {
            "weapon_small": _make_slot_def("weapon_small", "weapon", "small"),
        }
        parts = {"light_laser": _make_part("light_laser")}

        moves = get_slot_equipment_moves(build, slot_defs, parts)
        assert len(moves) == 1
        assert moves[0]["equipped_part_id"] == "light_laser"
        assert moves[0]["combat_move"]["name"] == "Light Laser"
        assert moves[0]["slot_type"] == "weapon"

    def test_empty_slot_no_move(self) -> None:
        build = ShipBuild(
            weight_class="small",
            placed_slots=[PlacedSlot(slot_def_id="weapon_small", x=5, y=5)],
        )
        slot_defs = {
            "weapon_small": _make_slot_def("weapon_small", "weapon", "small"),
        }
        moves = get_slot_equipment_moves(build, slot_defs, {})
        assert moves == []

    def test_non_combat_part_excluded(self) -> None:
        """Parts without combat_move (cargo, crew, etc) don't produce moves."""
        cargo_part = ShipPart(
            id="cargo_bay",
            name="Cargo Bay",
            description="",
            slot_type="cargo",
            min_size="small",
            manufacturer="",
            provides={"cargo_capacity": 50},
            base_cost=500,
            combat_move=None,
        )
        build = ShipBuild(
            weight_class="small",
            placed_slots=[
                PlacedSlot(
                    slot_def_id="cargo_small",
                    x=0,
                    y=0,
                    equipped_part_id="cargo_bay",
                ),
            ],
        )
        slot_defs = {
            "cargo_small": _make_slot_def("cargo_small", "cargo", "small"),
        }
        parts = {"cargo_bay": cargo_part}
        moves = get_slot_equipment_moves(build, slot_defs, parts)
        assert moves == []

    def test_multiple_weapons(self) -> None:
        build = ShipBuild(
            weight_class="small",
            placed_slots=[
                PlacedSlot(slot_def_id="weapon_small", x=2, y=2, equipped_part_id="laser_a"),
                PlacedSlot(slot_def_id="weapon_small", x=8, y=2, equipped_part_id="laser_b"),
            ],
        )
        slot_defs = {
            "weapon_small": _make_slot_def("weapon_small", "weapon", "small"),
        }
        parts = {
            "laser_a": _make_part("laser_a"),
            "laser_b": _make_part("laser_b"),
        }
        moves = get_slot_equipment_moves(build, slot_defs, parts)
        assert len(moves) == 2


class TestEmptyBuildProducesNoStates:
    """Verify that builds without placed_slots produce no combat states."""

    def test_empty_build_no_states(self) -> None:
        build = ShipBuild(weight_class="small")
        states = init_slot_combat_states(build, {})
        assert states == []
