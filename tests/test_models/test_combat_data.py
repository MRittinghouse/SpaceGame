"""Tests for combat data loading via DataLoader."""

import pytest
from pathlib import Path
from spacegame.data_loader import DataLoader
from spacegame.models.combat import EnemyBehavior, EffectType


# ============================================================================
# Helpers
# ============================================================================


def _make_loader() -> DataLoader:
    """Create a DataLoader pointing at the project data/ directory."""
    project_root = Path(__file__).parent.parent.parent
    loader = DataLoader(data_dir=project_root / "data")
    return loader


# ============================================================================
# Enemy Templates
# ============================================================================


class TestEnemyTemplateLoading:
    """Tests for loading enemy templates from JSON."""

    def test_load_all_enemies(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        assert len(loader.enemy_templates) == 28

    def test_pirate_scout_template(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        scout = loader.enemy_templates["pirate_scout"]
        assert scout.name == "Pirate Scout"
        assert scout.behavior == EnemyBehavior.COWARDLY
        assert scout.hull == 50
        assert scout.shields == 15
        assert scout.negotiate_difficulty == 2
        assert len(scout.moves) == 1
        assert scout.moves[0].id == "scout_blaster"

    def test_pirate_raider_has_two_moves(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        raider = loader.enemy_templates["pirate_raider"]
        assert len(raider.moves) == 2
        assert raider.moves[1].cooldown == 2

    def test_pirate_heavy_defensive_move(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        heavy = loader.enemy_templates["pirate_heavy"]
        assert heavy.behavior == EnemyBehavior.DEFENSIVE
        shield_move = heavy.moves[1]
        assert any(e.type == EffectType.SHIELD_RESTORE for e in shield_move.effects)

    def test_enemy_loot_table(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        raider = loader.enemy_templates["pirate_raider"]
        assert len(raider.loot_table) > 0
        assert "commodity_id" in raider.loot_table[0]

    def test_all_enemies_have_faction_id(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        for template in loader.enemy_templates.values():
            assert hasattr(template, "faction_id"), f"{template.id} missing faction_id"
            assert isinstance(template.faction_id, str)

    def test_all_enemies_have_danger_tier(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        valid_tiers = {"low", "moderate", "dangerous"}
        for template in loader.enemy_templates.values():
            assert hasattr(template, "danger_tier"), f"{template.id} missing danger_tier"
            assert template.danger_tier in valid_tiers, (
                f"{template.id} has invalid danger_tier: {template.danger_tier}"
            )

    def test_all_enemies_have_bribe_cost(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        for template in loader.enemy_templates.values():
            assert hasattr(template, "bribe_cost"), f"{template.id} missing bribe_cost"
            assert isinstance(template.bribe_cost, int)
            assert template.bribe_cost >= 0

    def test_pirate_scout_faction_fields(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        scout = loader.enemy_templates["pirate_scout"]
        assert scout.faction_id == ""
        assert scout.danger_tier == "low"
        assert scout.bribe_cost == 50

    def test_pirate_heavy_faction_fields(self) -> None:
        loader = _make_loader()
        loader.load_enemy_templates()
        heavy = loader.enemy_templates["pirate_heavy"]
        assert heavy.faction_id == ""
        assert heavy.danger_tier == "dangerous"
        assert heavy.bribe_cost == 400

    def test_default_faction_fields(self) -> None:
        """Templates without explicit faction fields should get defaults."""
        from spacegame.models.combat import EnemyShipTemplate, EnemyBehavior
        template = EnemyShipTemplate(
            id="test", name="Test", description="Test",
            behavior=EnemyBehavior.AGGRESSIVE,
            hull=50, shields=10, energy=8, energy_regen=3,
            speed=8, evasion=10, accuracy=60,
            moves=[], loot_table=[],
        )
        assert template.faction_id == ""
        assert template.danger_tier == "moderate"
        assert template.bribe_cost == 0

    def test_total_enemy_count_with_factions(self) -> None:
        """Should have 25 total enemies: 13 generic + 12 faction."""
        loader = _make_loader()
        loader.load_enemy_templates()
        assert len(loader.enemy_templates) == 28

    def test_faction_enemies_have_correct_faction_ids(self) -> None:
        """Faction enemies should reference valid faction IDs."""
        loader = _make_loader()
        loader.load_enemy_templates()
        valid_factions = {"commerce_guild", "miners_union", "science_collective", "frontier_alliance"}
        faction_enemies = [
            t for t in loader.enemy_templates.values() if t.faction_id != ""
        ]
        assert len(faction_enemies) == 12
        for t in faction_enemies:
            assert t.faction_id in valid_factions, f"{t.id} has invalid faction: {t.faction_id}"

    def test_all_danger_tiers_valid(self) -> None:
        """All enemies should have valid danger tiers."""
        loader = _make_loader()
        loader.load_enemy_templates()
        valid_tiers = {"low", "moderate", "dangerous"}
        for t in loader.enemy_templates.values():
            assert t.danger_tier in valid_tiers, f"{t.id}: {t.danger_tier}"

    def test_dangerous_enemies_stronger_than_moderate(self) -> None:
        """Dangerous tier enemies should generally be stronger than moderate."""
        loader = _make_loader()
        loader.load_enemy_templates()
        for faction in ["commerce_guild", "miners_union", "science_collective", "frontier_alliance"]:
            faction_enemies = [
                t for t in loader.enemy_templates.values() if t.faction_id == faction
            ]
            moderate = [t for t in faction_enemies if t.danger_tier == "moderate"]
            dangerous = [t for t in faction_enemies if t.danger_tier == "dangerous"]
            if moderate and dangerous:
                mod_hp = moderate[0].hull + moderate[0].shields
                dng_hp = dangerous[0].hull + dangerous[0].shields
                assert dng_hp > mod_hp, (
                    f"{faction}: dangerous ({dng_hp}) should exceed moderate ({mod_hp})"
                )

    def test_all_faction_enemies_have_moves(self) -> None:
        """Every faction enemy should have at least one combat move."""
        loader = _make_loader()
        loader.load_enemy_templates()
        for t in loader.enemy_templates.values():
            if t.faction_id != "":
                assert len(t.moves) >= 1, f"{t.id} has no moves"


# ============================================================================
# Ship Type Combat Stats
# ============================================================================


class TestShipTypeCombatLoading:
    """Tests for combat stat fields on loaded ShipTypes."""

    def test_all_ships_have_combat_stats(self) -> None:
        loader = _make_loader()
        loader.load_ship_types()
        for st in loader.ship_types.values():
            assert st.combat_hull > 0, f"{st.id} should have combat_hull"
            assert st.combat_shields >= 0, f"{st.id} should have combat_shields"

    def test_light_freighter_combat_stats(self) -> None:
        loader = _make_loader()
        loader.load_ship_types()
        lf = loader.ship_types["light_freighter"]
        assert lf.combat_hull == 100
        assert lf.combat_shields == 40
        assert lf.combat_energy == 10
        assert lf.combat_speed == 8
        assert lf.weapon_slots == 1
        assert lf.defense_slots == 1
        assert lf.utility_slots == 3

    def test_slot_distribution_varies(self) -> None:
        loader = _make_loader()
        loader.load_ship_types()
        shuttle = loader.ship_types["shuttle"]
        hauler = loader.ship_types["bulk_hauler"]
        assert shuttle.weapon_slots < hauler.weapon_slots


# ============================================================================
# Weapon/Defense Upgrades
# ============================================================================


class TestCombatUpgradeLoading:
    """Tests for weapon and defense upgrade loading."""

    def test_weapon_upgrades_loaded(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        weapons = [u for u in loader.upgrades.values() if u.slot_type == "weapon"]
        assert len(weapons) == 10

    def test_defense_upgrades_loaded(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        defenses = [u for u in loader.upgrades.values() if u.slot_type == "defense"]
        assert len(defenses) == 9

    def test_weapon_has_combat_move(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        laser = loader.upgrades["laser_cannon"]
        assert laser.combat_move is not None
        assert laser.combat_move["id"] == "laser_cannon"

    def test_utility_has_no_combat_move(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        cargo = loader.upgrades["cargo_bay_ext"]
        assert cargo.combat_move is None

    def test_existing_utility_upgrades_unchanged(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        assert "cargo_bay_ext" in loader.upgrades
        assert "fuel_tank_upgrade" in loader.upgrades
        assert "efficient_engines" in loader.upgrades
        assert "mining_drill_mk2" in loader.upgrades
        assert "advanced_scanner" in loader.upgrades


# ============================================================================
# Crew Combat Moves
# ============================================================================


class TestCrewCombatMoveLoading:
    """Tests for crew combat move loading."""

    def test_all_crew_have_combat_moves(self) -> None:
        loader = _make_loader()
        loader.load_crew_templates()
        for ct in loader.crew_templates.values():
            assert ct.combat_move is not None, f"{ct.id} should have combat_move"

    def test_elena_evasive_maneuvers(self) -> None:
        loader = _make_loader()
        loader.load_crew_templates()
        elena = loader.crew_templates["elena_reeves"]
        assert elena.combat_move["id"] == "evasive_maneuvers"
        assert elena.combat_move["effects"][0]["type"] == "evasion_mod"

    def test_marcus_emergency_repairs(self) -> None:
        loader = _make_loader()
        loader.load_crew_templates()
        marcus = loader.crew_templates["marcus_jin"]
        assert marcus.combat_move["id"] == "emergency_repairs"
        assert marcus.combat_move["effects"][0]["type"] == "hull_restore"
