"""Tests for upgrade tier system and system-locking (R2 gap-filling)."""

import json
from pathlib import Path

from spacegame.data_loader import get_data_loader
from spacegame.models.upgrades import ShipUpgrade


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


def _load_upgrades_json() -> list[dict]:
    with open(DATA_DIR / "ships" / "upgrades.json", "r", encoding="utf-8") as f:
        return json.load(f)["upgrades"]


class TestUpgradeTierField:
    """Test that tier field exists and is valid on all upgrades."""

    def test_all_upgrades_have_tier(self) -> None:
        raw = _load_upgrades_json()
        for entry in raw:
            assert "tier" in entry, f"{entry['id']} missing tier field"

    def test_tier_values_are_valid(self) -> None:
        raw = _load_upgrades_json()
        for entry in raw:
            assert entry["tier"] in (1, 2, 3), f"{entry['id']} has invalid tier: {entry['tier']}"

    def test_tier_distribution_not_empty(self) -> None:
        raw = _load_upgrades_json()
        tiers = {1: 0, 2: 0, 3: 0}
        for entry in raw:
            tiers[entry["tier"]] += 1
        for tier, count in tiers.items():
            assert count > 0, f"Tier {tier} has no upgrades"

    def test_tier_defaults_to_1_in_model(self) -> None:
        upgrade = ShipUpgrade(
            id="test",
            name="Test",
            description="Test",
            price=1000,
            slot_type="cargo",
            bonus_type="",
            bonus_value=0.0,
        )
        assert upgrade.tier == 1

    def test_tier_aligns_with_price(self) -> None:
        """Tier 1 upgrades should generally be cheaper than Tier 3."""
        raw = _load_upgrades_json()
        tier1_prices = [e["price"] for e in raw if e["tier"] == 1]
        tier3_prices = [e["price"] for e in raw if e["tier"] == 3]
        avg_t1 = sum(tier1_prices) / len(tier1_prices)
        avg_t3 = sum(tier3_prices) / len(tier3_prices)
        assert avg_t1 < avg_t3, f"Tier 1 avg ({avg_t1}) should be less than Tier 3 avg ({avg_t3})"


class TestAvailableSystems:
    """Test available_systems field for system-locking."""

    def test_all_upgrades_have_available_systems(self) -> None:
        raw = _load_upgrades_json()
        for entry in raw:
            assert "available_systems" in entry, f"{entry['id']} missing available_systems field"

    def test_available_systems_defaults_to_empty(self) -> None:
        upgrade = ShipUpgrade(
            id="test",
            name="Test",
            description="Test",
            price=1000,
            slot_type="cargo",
            bonus_type="",
            bonus_value=0.0,
        )
        assert upgrade.available_systems == []

    def test_tier_1_upgrades_available_everywhere(self) -> None:
        raw = _load_upgrades_json()
        for entry in raw:
            if entry["tier"] == 1:
                assert entry["available_systems"] == [], (
                    f"Tier 1 upgrade {entry['id']} should be available everywhere"
                )

    def test_system_locked_upgrades_reference_valid_systems(self) -> None:
        raw = _load_upgrades_json()
        for entry in raw:
            for sys_id in entry.get("available_systems", []):
                assert sys_id in VALID_SYSTEM_IDS, (
                    f"{entry['id']} references invalid system: {sys_id}"
                )

    def test_some_tier_3_upgrades_are_system_locked(self) -> None:
        raw = _load_upgrades_json()
        locked_t3 = [e for e in raw if e["tier"] == 3 and e.get("available_systems")]
        assert len(locked_t3) >= 3, "Expected at least 3 system-locked Tier 3 upgrades"


class TestNewUpgrades:
    """Test that the 3 new upgrades exist and are well-formed."""

    def test_diplomatic_transponder_exists(self) -> None:
        raw = _load_upgrades_json()
        ids = {e["id"] for e in raw}
        assert "diplomatic_transponder" in ids

    def test_trade_manifest_scanner_exists(self) -> None:
        raw = _load_upgrades_json()
        ids = {e["id"] for e in raw}
        assert "trade_manifest_scanner" in ids

    def test_overclocked_engines_exists(self) -> None:
        raw = _load_upgrades_json()
        ids = {e["id"] for e in raw}
        assert "overclocked_engines" in ids

    def test_total_upgrade_count(self) -> None:
        raw = _load_upgrades_json()
        assert len(raw) >= 43, f"Expected >= 43 upgrades, got {len(raw)}"

    def test_diplomatic_transponder_is_tier_1(self) -> None:
        raw = _load_upgrades_json()
        dt = next(e for e in raw if e["id"] == "diplomatic_transponder")
        assert dt["tier"] == 1
        assert dt["available_systems"] == []

    def test_trade_manifest_scanner_is_tier_2(self) -> None:
        raw = _load_upgrades_json()
        tms = next(e for e in raw if e["id"] == "trade_manifest_scanner")
        assert tms["tier"] == 2
        assert len(tms["available_systems"]) > 0

    def test_overclocked_engines_is_tier_3(self) -> None:
        raw = _load_upgrades_json()
        oe = next(e for e in raw if e["id"] == "overclocked_engines")
        assert oe["tier"] == 3
        assert len(oe["available_systems"]) > 0


class TestDataLoaderParsesTiers:
    """Test that DataLoader correctly parses tier and available_systems."""

    def test_loaded_upgrade_has_tier(self) -> None:
        dl = get_data_loader()
        dl.load_upgrades()
        for uid, upgrade in dl.upgrades.items():
            assert upgrade.tier in (1, 2, 3), f"{uid} tier not loaded correctly"

    def test_loaded_upgrade_has_available_systems(self) -> None:
        dl = get_data_loader()
        dl.load_upgrades()
        # At least one upgrade should have non-empty available_systems
        has_locked = any(len(u.available_systems) > 0 for u in dl.upgrades.values())
        assert has_locked, "No upgrades have available_systems set"

    def test_no_duplicate_upgrade_ids(self) -> None:
        raw = _load_upgrades_json()
        ids = [e["id"] for e in raw]
        assert len(ids) == len(set(ids)), "Duplicate upgrade IDs found"
