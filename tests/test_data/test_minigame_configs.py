"""Tests for mini-game config expansion (R8 gap-filling)."""

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
VALID_SYSTEM_IDS = {
    "nexus_prime",
    "verdant",
    "forgeworks",
    "breakstone",
    "axiom_labs",
    "havens_rest",
    "crimson_reach",
    "stellaris_port",
    "iron_depths",
    "nova_research",
    "the_fulcrum",
}


def _load_mining() -> list[dict]:
    with open(DATA_DIR / "economy" / "mining_configs.json", "r", encoding="utf-8") as f:
        return json.load(f)["mining_configs"]


def _load_salvage() -> list[dict]:
    with open(DATA_DIR / "economy" / "salvage_configs.json", "r", encoding="utf-8") as f:
        return json.load(f)["salvage_configs"]


def _load_recipes() -> list[dict]:
    with open(DATA_DIR / "economy" / "recipes.json", "r", encoding="utf-8") as f:
        return json.load(f)["recipes"]


class TestMiningConfigs:
    """Test mining config data integrity."""

    def test_mining_config_count(self) -> None:
        configs = _load_mining()
        assert len(configs) >= 5, f"Expected >= 5 mining configs, got {len(configs)}"

    def test_expected_mining_systems(self) -> None:
        configs = _load_mining()
        sys_ids = {c["system_id"] for c in configs}
        expected = {"breakstone", "iron_depths", "forgeworks", "verdant", "the_fulcrum"}
        assert expected.issubset(sys_ids), f"Missing mining systems: {expected - sys_ids}"

    def test_mining_system_ids_valid(self) -> None:
        configs = _load_mining()
        for cfg in configs:
            assert cfg["system_id"] in VALID_SYSTEM_IDS, f"Invalid system_id: {cfg['system_id']}"

    def test_mining_distribution_sums_to_one(self) -> None:
        configs = _load_mining()
        for cfg in configs:
            total = sum(cfg["rock_distribution"].values())
            assert abs(total - 1.0) < 0.01, f"{cfg['system_id']} distribution sums to {total}"

    def test_mining_grid_dimensions_reasonable(self) -> None:
        configs = _load_mining()
        for cfg in configs:
            assert 3 <= cfg["grid_width"] <= 10, f"{cfg['system_id']} grid_width out of range"
            assert 3 <= cfg["grid_height"] <= 8, f"{cfg['system_id']} grid_height out of range"

    def test_dangerous_systems_better_yields(self) -> None:
        """Dangerous systems (the_fulcrum, iron_depths) should have better rare yields."""
        configs = _load_mining()
        by_sys = {c["system_id"]: c for c in configs}
        fulcrum_rare = by_sys["the_fulcrum"]["rock_distribution"]["rare"]
        iron_rare = by_sys["iron_depths"]["rock_distribution"]["rare"]
        forge_rare = by_sys["forgeworks"]["rock_distribution"]["rare"]
        assert fulcrum_rare >= forge_rare, "The Fulcrum should have >= rare yield vs Forgeworks"
        assert iron_rare >= forge_rare, "Iron Depths should have >= rare yield vs Forgeworks"


class TestSalvageConfigs:
    """Test salvage config data integrity."""

    def test_salvage_config_count(self) -> None:
        configs = _load_salvage()
        assert len(configs) >= 5, f"Expected >= 5 salvage configs, got {len(configs)}"

    def test_expected_salvage_systems(self) -> None:
        configs = _load_salvage()
        sys_ids = {c["system_id"] for c in configs}
        expected = {"forgeworks", "crimson_reach", "breakstone", "the_fulcrum", "iron_depths"}
        assert expected.issubset(sys_ids), f"Missing salvage systems: {expected - sys_ids}"

    def test_salvage_system_ids_valid(self) -> None:
        configs = _load_salvage()
        for cfg in configs:
            assert cfg["system_id"] in VALID_SYSTEM_IDS, f"Invalid system_id: {cfg['system_id']}"

    def test_salvage_distribution_sums_to_one(self) -> None:
        configs = _load_salvage()
        for cfg in configs:
            total = sum(cfg["item_distribution"].values())
            assert abs(total - 1.0) < 0.01, f"{cfg['system_id']} distribution sums to {total}"

    def test_salvage_grid_size_reasonable(self) -> None:
        configs = _load_salvage()
        for cfg in configs:
            assert 3 <= cfg["grid_size"] <= 10, f"{cfg['system_id']} grid_size out of range"

    def test_fulcrum_best_salvage_yields(self) -> None:
        """The Fulcrum (battlefield) should have the best rare_parts ratio."""
        configs = _load_salvage()
        by_sys = {c["system_id"]: c for c in configs}
        fulcrum_rare = by_sys["the_fulcrum"]["item_distribution"]["rare_parts"]
        for sys_id, cfg in by_sys.items():
            if sys_id != "the_fulcrum":
                assert fulcrum_rare >= cfg["item_distribution"]["rare_parts"], (
                    f"The Fulcrum should have >= rare_parts vs {sys_id}"
                )


class TestRefiningRecipes:
    """Test refining recipe updates."""

    def test_nexus_prime_in_basic_recipes(self) -> None:
        """Nexus Prime should appear in at least one basic refining recipe."""
        recipes = _load_recipes()
        nexus_recipes = [r for r in recipes if "nexus_prime" in r.get("location_ids", [])]
        assert len(nexus_recipes) >= 1, "nexus_prime should appear in at least 1 recipe"

    def test_smelt_iron_includes_nexus(self) -> None:
        recipes = _load_recipes()
        smelt = next(r for r in recipes if r["id"] == "smelt_iron")
        assert "nexus_prime" in smelt["location_ids"]

    def test_salvage_to_metals_includes_nexus(self) -> None:
        recipes = _load_recipes()
        salvage = next(r for r in recipes if r["id"] == "salvage_to_metals")
        assert "nexus_prime" in salvage["location_ids"]
