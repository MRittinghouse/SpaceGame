"""Tests for Phase 12 — Station module shops and blueprint purchases.

Covers blueprint purchase logic, station catalog filtering, price
modifiers, faction gating, and drydock catalog data integrity.
"""

from spacegame.models.build_sharing import (
    purchase_module_blueprint,
    get_station_modules,
)
from spacegame.models.ship_module import ShipModule


# ============================================================================
# Helpers
# ============================================================================


def _catalog() -> dict[str, ShipModule]:
    return {
        "purchasable": ShipModule(
            id="purchasable",
            name="Buyable Part",
            description="",
            category="weapon",
            manufacturer="reyes_kowalski",
            pixel_grid=[["H"]],
            material_map={"H": "m"},
            provides={},
            weight=1.0,
            base_cost=0,
            unlock_method="purchase",
            unlock_cost=5000,
        ),
        "quest_only": ShipModule(
            id="quest_only",
            name="Quest Part",
            description="",
            category="weapon",
            manufacturer="talon",
            pixel_grid=[["H"]],
            material_map={"H": "m"},
            provides={},
            weight=1.0,
            base_cost=0,
            unlock_method="quest",
            unlock_source="quest_example",
        ),
        "free_starter": ShipModule(
            id="free_starter",
            name="Free Part",
            description="",
            category="structural",
            manufacturer="reyes_kowalski",
            pixel_grid=[["H"]],
            material_map={"H": "m"},
            provides={},
            weight=0.5,
            base_cost=0,
            unlock_method="free",
        ),
    }


class _MockPlayer:
    def __init__(self, credits: int = 10000):
        self.credits = credits
        self.unlocked_modules: set[str] = set()


# ============================================================================
# Blueprint Purchase
# ============================================================================


class TestBlueprintPurchase:
    """Test module blueprint purchase logic."""

    def test_successful_purchase(self) -> None:
        player = _MockPlayer(credits=10000)
        catalog = _catalog()
        ok, msg = purchase_module_blueprint(player, "purchasable", catalog)
        assert ok, f"Purchase should succeed: {msg}"
        assert "purchasable" in player.unlocked_modules
        assert player.credits == 5000  # 10000 - 5000

    def test_already_owned(self) -> None:
        player = _MockPlayer()
        player.unlocked_modules.add("purchasable")
        catalog = _catalog()
        ok, msg = purchase_module_blueprint(player, "purchasable", catalog)
        assert not ok
        assert "already" in msg.lower()

    def test_insufficient_credits(self) -> None:
        player = _MockPlayer(credits=100)
        catalog = _catalog()
        ok, msg = purchase_module_blueprint(player, "purchasable", catalog)
        assert not ok
        assert "afford" in msg.lower()

    def test_quest_only_not_purchasable(self) -> None:
        player = _MockPlayer()
        catalog = _catalog()
        ok, msg = purchase_module_blueprint(player, "quest_only", catalog)
        assert not ok
        assert "not for sale" in msg.lower()

    def test_free_module_no_charge(self) -> None:
        player = _MockPlayer(credits=100)
        catalog = _catalog()
        ok, msg = purchase_module_blueprint(player, "free_starter", catalog)
        assert ok
        assert player.credits == 100  # No charge
        assert "free_starter" in player.unlocked_modules

    def test_price_modifier(self) -> None:
        player = _MockPlayer(credits=10000)
        catalog = _catalog()
        ok, msg = purchase_module_blueprint(player, "purchasable", catalog, price_modifier=1.5)
        assert ok
        assert player.credits == 2500  # 10000 - 7500 (5000 * 1.5)

    def test_unknown_module(self) -> None:
        player = _MockPlayer()
        ok, msg = purchase_module_blueprint(player, "nonexistent", {})
        assert not ok
        assert "unknown" in msg.lower()


# ============================================================================
# Station Module Catalog
# ============================================================================


class TestStationModuleCatalog:
    """Test station-specific module availability."""

    def test_station_returns_modules(self) -> None:
        catalog = _catalog()
        drydock = {"station_a": {"modules_sold": ["purchasable", "free_starter"]}}
        result = get_station_modules("station_a", drydock, catalog)
        assert len(result) == 2
        ids = {m.id for m in result}
        assert "purchasable" in ids
        assert "free_starter" in ids

    def test_unknown_station_returns_empty(self) -> None:
        catalog = _catalog()
        drydock = {"station_a": {"modules_sold": ["purchasable"]}}
        result = get_station_modules("nonexistent", drydock, catalog)
        assert result == []

    def test_unknown_module_id_skipped(self) -> None:
        catalog = _catalog()
        drydock = {"station_a": {"modules_sold": ["purchasable", "HACKED_ID"]}}
        result = get_station_modules("station_a", drydock, catalog)
        assert len(result) == 1
        assert result[0].id == "purchasable"

    def test_sorted_by_category_then_name(self) -> None:
        catalog = _catalog()
        drydock = {"station_a": {"modules_sold": ["purchasable", "free_starter", "quest_only"]}}
        result = get_station_modules("station_a", drydock, catalog)
        categories = [m.category for m in result]
        # structural < weapon (alphabetical)
        assert categories == sorted(categories)

    def test_drydock_catalogs_have_modules_sold(self) -> None:
        """All stations in drydock_catalogs.json should have modules_sold."""
        import json
        from pathlib import Path

        path = Path("data/ships/drydock_catalogs.json")
        with open(path) as f:
            data = json.load(f)
        for station_id, entry in data["drydock_catalogs"].items():
            assert "modules_sold" in entry, f"Station {station_id} missing modules_sold"
            assert len(entry["modules_sold"]) >= 5, (
                f"Station {station_id} has too few modules ({len(entry['modules_sold'])})"
            )

    def test_all_sold_modules_exist_in_catalog(self) -> None:
        """Every module_id in drydock_catalogs should exist in modules.json."""
        import json
        from pathlib import Path

        catalogs_path = Path("data/ships/drydock_catalogs.json")
        modules_path = Path("data/ships/modules.json")
        with open(catalogs_path) as f:
            catalogs = json.load(f)
        with open(modules_path) as f:
            modules = json.load(f)
        valid_ids = {m["id"] for m in modules["modules"]}
        for station_id, entry in catalogs["drydock_catalogs"].items():
            for mid in entry.get("modules_sold", []):
                assert mid in valid_ids, f"Station {station_id} sells unknown module '{mid}'"
