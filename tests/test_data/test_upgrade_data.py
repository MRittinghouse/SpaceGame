"""
Tests for the complete upgrade roster (~40 upgrades with tuning options).
"""

import pytest
from spacegame.data_loader import get_data_loader


@pytest.fixture()
def upgrades() -> dict:
    dl = get_data_loader()
    dl.load_upgrades()
    return dl.upgrades


class TestUpgradeCount:
    def test_total_upgrade_count(self, upgrades: dict) -> None:
        assert len(upgrades) == 85

    def test_utility_upgrades(self, upgrades: dict) -> None:
        utility_types = {"cargo", "fuel", "engine", "mining", "scanner"}
        count = sum(1 for u in upgrades.values() if u.slot_type in utility_types)
        assert count >= 13

    def test_weapon_upgrades(self, upgrades: dict) -> None:
        count = sum(1 for u in upgrades.values() if u.slot_type == "weapon")
        assert count == 32

    def test_defense_upgrades(self, upgrades: dict) -> None:
        count = sum(1 for u in upgrades.values() if u.slot_type == "defense")
        assert count == 14

    def test_smuggling_upgrades(self, upgrades: dict) -> None:
        count = sum(1 for u in upgrades.values() if u.slot_type == "smuggling")
        assert count == 4


class TestNewUpgradeIdentities:
    NEW_IDS = [
        "nav_computer", "tractor_beam", "refining_module", "crew_quarters",
        "sensor_array", "cargo_compressor", "hull_reinforcement",
        "autocannon", "rail_gun", "flak_battery",
        "reactive_armor", "ecm_suite",
        "nexus_trade_beacon", "forge_plating", "frontier_salvage_array", "axiom_scanner",
        "prototype_shields", "ancient_drive", "black_sun_jammer",
        "reinforced_plating", "overclocked_scanner", "plasma_conduit",
        "titan_plating", "command_array", "nova_core",
        "phantom_module",
        "shield_capacitor", "arc_emitter",
    ]

    def test_all_new_upgrades_exist(self, upgrades: dict) -> None:
        for uid in self.NEW_IDS:
            assert uid in upgrades, f"Missing upgrade: {uid}"


class TestTuningOptions:
    def test_most_upgrades_have_tuning(self, upgrades: dict) -> None:
        """Most upgrades should have tuning options."""
        with_tuning = sum(1 for u in upgrades.values() if len(u.tuning_options) > 0)
        assert with_tuning >= 35, f"Only {with_tuning} upgrades have tuning"

    def test_tuning_has_two_options(self, upgrades: dict) -> None:
        """Each upgrade with tuning should have exactly 2 options."""
        for uid, u in upgrades.items():
            if u.tuning_options:
                assert len(u.tuning_options) == 2, f"{uid} should have 2 tuning options"

    def test_tuning_options_have_required_fields(self, upgrades: dict) -> None:
        for uid, u in upgrades.items():
            for opt in u.tuning_options:
                assert "id" in opt, f"{uid} tuning missing id"
                assert "name" in opt, f"{uid} tuning missing name"
                assert "bonus_type" in opt, f"{uid} tuning missing bonus_type"
                assert "bonus_value" in opt, f"{uid} tuning missing bonus_value"

    def test_salvaged_pulse_emitter_no_tuning(self, upgrades: dict) -> None:
        """Salvaged junk weapon should be max Mk1 (no enhancement)."""
        u = upgrades["salvaged_pulse_emitter"]
        assert u.max_mark == 1
        assert len(u.tuning_options) == 0


class TestFactionUpgrades:
    FACTION_UPGRADES = {
        "nexus_trade_beacon": ("nexus_trade", 20),
        "forge_plating": ("forgeworks_industrial", 20),
        "frontier_salvage_array": ("free_salvagers", 20),
        "axiom_scanner": ("axiom_research", 20),
    }

    def test_faction_gates(self, upgrades: dict) -> None:
        for uid, (faction, rep) in self.FACTION_UPGRADES.items():
            u = upgrades[uid]
            assert u.faction_required == faction, f"{uid} wrong faction"
            assert u.faction_rep_required == rep, f"{uid} wrong rep"

    def test_non_faction_upgrades_no_gate(self, upgrades: dict) -> None:
        faction_ids = set(self.FACTION_UPGRADES.keys())
        for uid, u in upgrades.items():
            if uid not in faction_ids:
                assert u.faction_required is None or u.faction_required == "", (
                    f"{uid} shouldn't have faction gate"
                )


class TestQuestUpgrades:
    QUEST_UPGRADES = {
        "prototype_shields": "quest_axiom_defense",
        "ancient_drive": "quest_deep_ruins",
        "black_sun_jammer": "quest_fulcrum_chain",
        "reinforced_plating": "crafted_reinforced_plating",
        "overclocked_scanner": "crafted_overclocked_scanner",
        "plasma_conduit": "crafted_plasma_conduit",
        "titan_plating": "crafted_titan_plating",
        "command_array": "crafted_command_array",
        "nova_core": "crafted_nova_core",
        "phantom_module": "crafted_phantom_module",
        "shield_capacitor": "crafted_shield_capacitor",
        "arc_emitter": "crafted_arc_emitter",
    }

    def test_quest_gates(self, upgrades: dict) -> None:
        for uid, condition in self.QUEST_UPGRADES.items():
            u = upgrades[uid]
            assert u.unlock_condition == condition, f"{uid} wrong unlock_condition"


class TestUpgradeStats:
    def test_all_have_valid_price(self, upgrades: dict) -> None:
        craft_gated = {uid for uid, u in upgrades.items() if u.unlock_condition and u.unlock_condition.startswith("crafted_")}
        for uid, u in upgrades.items():
            if uid in craft_gated:
                assert u.price == 0, f"Craft-gated {uid} should be free to install"
            else:
                assert u.price > 0, f"{uid} should have positive price"

    def test_weapons_have_combat_moves(self, upgrades: dict) -> None:
        for uid, u in upgrades.items():
            if u.slot_type == "weapon":
                assert u.combat_move is not None, f"Weapon {uid} missing combat_move"

    def test_max_mark_valid_range(self, upgrades: dict) -> None:
        for uid, u in upgrades.items():
            assert 1 <= u.max_mark <= 3, f"{uid} max_mark out of range"
