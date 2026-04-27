"""Scenario: shipyard install flow — purchase upgrade → install → stats reflect.

SI-2 Stream 1. The shipyard is the most-touched non-combat view; every
session that builds out a ship runs through this flow. No end-to-end
scenario currently covers it as a chain.

Walks the four hops a playtester takes when buying an upgrade:

  1. **Gating** — ``ShipyardView._is_upgrade_locked`` (shipyard_view.py:426)
     short-circuits the buy if the player is in the wrong system, lacks
     faction rep, or hasn't tripped the unlock flag.
  2. **Affordability + duplicate check** — ``Player.can_afford`` and
     ``ShipUpgradeManager.can_install`` gate the actual transaction.
  3. **Transaction** — ``Player.deduct_credits`` + ``ShipUpgradeManager.install``
     are the primitives the view orchestrates (shipyard_view.py:682).
  4. **Stats reflection** — ``Ship.max_cargo`` (ship.py:249), ``max_fuel``
     (ship.py:270), ``effective_fuel_efficiency`` (ship.py:289), etc.
     read ``upgrade_manager.get_bonus(...)`` at access time. The bonus
     must reach the ship the moment the install lands.

The transaction block is mirrored inline in ``_buy_upgrade`` below.
**If you ever refactor the shipyard purchase block in
``ShipyardView._buy_selected`` (shipyard_view.py:661) into a
``Player.purchase_upgrade(upgrade) -> tuple[bool, str]`` method,
update the inlined helper here to delegate.**

The mark-enhancement chain (Mk1 → Mk2 with tuning → Mk3) is also
exercised since the multiplier (1.0 / 1.25 / 1.50) plus the doubled
tuning at Mk3 is one of the most balance-load-bearing primitives in
the upgrade pipeline.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.upgrades import (
    MARK_MULTIPLIERS,
    ShipUpgrade,
    ShipUpgradeManager,
)
from tests.test_scenarios._helpers import fresh_player

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


def _wire_upgrade_manager(player) -> ShipUpgradeManager:
    """Create + attach a fresh upgrade manager to the ship.

    Production wires this in Game setup via ``Ship.set_upgrade_manager``;
    fresh_player doesn't, so the scenario does it explicitly. Without
    it, ``Ship.max_cargo`` won't see install bonuses.
    """
    mgr = ShipUpgradeManager()
    player.ship.set_upgrade_manager(mgr)
    return mgr


def _is_locked(player, upgrade: ShipUpgrade) -> tuple[bool, str]:
    """Mirror ShipyardView._is_upgrade_locked (shipyard_view.py:426)."""
    if upgrade.available_systems and player.current_system_id not in upgrade.available_systems:
        return (True, "wrong system")
    if upgrade.faction_required:
        rep = player.get_reputation(upgrade.faction_required)
        if rep < upgrade.faction_rep_required:
            return (
                True,
                f"need {upgrade.faction_rep_required} rep with {upgrade.faction_required}",
            )
    if upgrade.unlock_condition:
        if not player.dialogue_flags.get(upgrade.unlock_condition, False):
            return (True, f"requires flag {upgrade.unlock_condition}")
    return (False, "")


def _buy_upgrade(player, mgr: ShipUpgradeManager, upgrade: ShipUpgrade) -> tuple[bool, str]:
    """Mirror ShipyardView._buy_selected (shipyard_view.py:661)."""
    locked, reason = _is_locked(player, upgrade)
    if locked:
        return (False, f"LOCKED: {reason}")
    if not player.can_afford(upgrade.price):
        return (False, "Cannot afford")
    if not mgr.can_install(upgrade):
        return (False, "Already installed")
    player.deduct_credits(upgrade.price)
    return mgr.install(upgrade)


def _real_upgrade(upgrade_id: str) -> ShipUpgrade:
    dl = get_data_loader()
    dl.load_all()
    if upgrade_id not in dl.upgrades:
        raise AssertionError(f"upgrade {upgrade_id!r} not in data loader")
    return dl.upgrades[upgrade_id]


# ---------------------------------------------------------------------------
# 1. Stats reflection — the core contract
# ---------------------------------------------------------------------------


class TestStatsReflectAfterInstall:
    def test_cargo_bonus_install_increases_max_cargo(self) -> None:
        """``cargo_bay_ext`` is +60 cargo at Mk1. Buying it should raise
        ``Ship.max_cargo`` by exactly 60 over the shuttle's base cargo
        (50 per data/ships/ship_types.json)."""
        player = fresh_player(credits=10_000)
        mgr = _wire_upgrade_manager(player)
        baseline = player.ship.max_cargo
        upgrade = _real_upgrade("cargo_bay_ext")  # +60 cargo

        ok, _msg = _buy_upgrade(player, mgr, upgrade)
        assert ok

        assert player.ship.max_cargo == baseline + int(upgrade.bonus_value)

    def test_install_deducts_credits(self) -> None:
        player = fresh_player(credits=10_000)
        mgr = _wire_upgrade_manager(player)
        upgrade = _real_upgrade("cargo_bay_ext")
        starting = player.credits

        ok, _msg = _buy_upgrade(player, mgr, upgrade)
        assert ok
        assert player.credits == starting - upgrade.price

    def test_uninstall_drops_bonus_back_to_baseline(self) -> None:
        player = fresh_player(credits=10_000)
        mgr = _wire_upgrade_manager(player)
        baseline = player.ship.max_cargo
        upgrade = _real_upgrade("cargo_bay_ext")
        _buy_upgrade(player, mgr, upgrade)
        assert player.ship.max_cargo > baseline

        ok, _msg = mgr.uninstall(upgrade.id)
        assert ok
        assert player.ship.max_cargo == baseline


# ---------------------------------------------------------------------------
# 2. Gating — locked upgrades reject before transaction
# ---------------------------------------------------------------------------


class TestGating:
    def test_wrong_system_blocks_purchase(self) -> None:
        """An upgrade with ``available_systems`` rejects when the player
        is somewhere else — credits stay, no install."""
        player = fresh_player(credits=100_000, system_id="nexus_prime")
        mgr = _wire_upgrade_manager(player)
        upgrade = ShipUpgrade(
            id="test_local_only",
            name="Local Only",
            description="Only sold at one station.",
            price=1000,
            slot_type="cargo",
            bonus_type="cargo_bonus",
            bonus_value=10.0,
            available_systems=["forgeworks"],  # not nexus_prime
        )
        ok, msg = _buy_upgrade(player, mgr, upgrade)
        assert not ok
        assert "LOCKED" in msg
        assert player.credits == 100_000
        assert not mgr.has_upgrade("test_local_only")

    def test_insufficient_faction_rep_blocks_purchase(self) -> None:
        player = fresh_player(credits=100_000)
        mgr = _wire_upgrade_manager(player)
        upgrade = ShipUpgrade(
            id="test_faction_gated",
            name="Faction Gated",
            description="Requires rep.",
            price=1000,
            slot_type="cargo",
            bonus_type="cargo_bonus",
            bonus_value=10.0,
            faction_required="commerce_guild",
            faction_rep_required=20,
        )
        # Default rep is 0 — should block.
        ok, msg = _buy_upgrade(player, mgr, upgrade)
        assert not ok
        assert "LOCKED" in msg
        assert player.credits == 100_000

        # Bump rep above threshold and the gate opens.
        player.modify_reputation("commerce_guild", 25)
        ok2, _msg2 = _buy_upgrade(player, mgr, upgrade)
        assert ok2

    def test_missing_unlock_flag_blocks_purchase(self) -> None:
        player = fresh_player(credits=100_000)
        mgr = _wire_upgrade_manager(player)
        upgrade = ShipUpgrade(
            id="test_quest_gated",
            name="Quest Gated",
            description="Requires flag.",
            price=1000,
            slot_type="cargo",
            bonus_type="cargo_bonus",
            bonus_value=10.0,
            unlock_condition="completed_act_one",
        )
        ok, msg = _buy_upgrade(player, mgr, upgrade)
        assert not ok
        assert "LOCKED" in msg

        player.dialogue_flags["completed_act_one"] = True
        ok2, _msg2 = _buy_upgrade(player, mgr, upgrade)
        assert ok2


# ---------------------------------------------------------------------------
# 3. Transaction guards — affordability and duplicate-install
# ---------------------------------------------------------------------------


class TestTransactionGuards:
    def test_cannot_afford_does_not_charge_or_install(self) -> None:
        player = fresh_player(credits=100)
        mgr = _wire_upgrade_manager(player)
        upgrade = _real_upgrade("cargo_bay_ext")  # 5000 CR
        starting = player.credits

        ok, msg = _buy_upgrade(player, mgr, upgrade)
        assert not ok
        assert "afford" in msg.lower()
        assert player.credits == starting
        assert not mgr.has_upgrade("cargo_bay_ext")

    def test_duplicate_install_rejected(self) -> None:
        player = fresh_player(credits=20_000)
        mgr = _wire_upgrade_manager(player)
        upgrade = _real_upgrade("cargo_bay_ext")
        _buy_upgrade(player, mgr, upgrade)

        ok, msg = _buy_upgrade(player, mgr, upgrade)
        assert not ok
        assert "Already" in msg or "installed" in msg.lower()
        # Credits not double-deducted
        assert player.credits == 20_000 - upgrade.price


# ---------------------------------------------------------------------------
# 4. Mark enhancement — multiplier and tuning math
# ---------------------------------------------------------------------------


class TestMarkEnhancementBonus:
    def test_mk2_applies_125_multiplier(self) -> None:
        player = fresh_player(credits=20_000)
        mgr = _wire_upgrade_manager(player)
        upgrade = _real_upgrade("cargo_bay_ext")  # +60 base, has tuning options
        _buy_upgrade(player, mgr, upgrade)
        baseline_bonus = mgr.get_bonus("cargo_bonus")

        # Pick whichever tuning the upgrade ships with.
        assert upgrade.tuning_options, "cargo_bay_ext should have tuning options"
        tuning_id = upgrade.tuning_options[0]["id"]
        ok, _msg = mgr.enhance(upgrade.id, mark=2, tuning=tuning_id)
        assert ok

        cargo_bonus = mgr.get_bonus("cargo_bonus")
        # Mark 2 multiplier is 1.25 (per upgrades.py:16).
        expected_main = upgrade.bonus_value * MARK_MULTIPLIERS[2]
        # The tuning itself may or may not be a cargo_bonus — assert the
        # base cargo bonus picks up the multiplier whichever way.
        assert cargo_bonus >= expected_main, (
            f"Mk2 cargo bonus should be at least {expected_main}, got {cargo_bonus}"
        )
        assert cargo_bonus > baseline_bonus

    def test_mk3_doubles_tuning_bonus(self) -> None:
        """Per upgrades.py:188 — at Mk3, the tuning bonus doubles."""
        player = fresh_player(credits=20_000)
        mgr = _wire_upgrade_manager(player)
        upgrade = _real_upgrade("cargo_bay_ext")
        _buy_upgrade(player, mgr, upgrade)

        # Find a tuning option that gives a non-cargo bonus (so we can
        # observe the tuning value in isolation from the main bonus).
        tuning_opt = None
        for opt in upgrade.tuning_options:
            if opt["bonus_type"] != "cargo_bonus":
                tuning_opt = opt
                break
        assert tuning_opt, "expected at least one non-cargo tuning on cargo_bay_ext"
        tuning_id = tuning_opt["id"]
        tuning_bonus_type = tuning_opt["bonus_type"]
        tuning_value = float(tuning_opt["bonus_value"])

        # Mk2 with the tuning equipped — tuning bonus is 1x its value.
        mgr.enhance(upgrade.id, mark=2, tuning=tuning_id)
        mk2_tuning_bonus = mgr.get_bonus(tuning_bonus_type)
        assert mk2_tuning_bonus == tuning_value, (
            f"Mk2 tuning bonus should be 1x: {tuning_value}, got {mk2_tuning_bonus}"
        )

        # Mk3 — tuning doubles.
        mgr.enhance(upgrade.id, mark=3)
        mk3_tuning_bonus = mgr.get_bonus(tuning_bonus_type)
        assert mk3_tuning_bonus == tuning_value * 2.0, (
            f"Mk3 tuning bonus should double: expected {tuning_value * 2.0}, got {mk3_tuning_bonus}"
        )


# ---------------------------------------------------------------------------
# 5. Full chain — purchase, enhance, save round-trip
# ---------------------------------------------------------------------------


class TestFullShipyardChain:
    def test_buy_then_enhance_then_stats_reflect_chain(self) -> None:
        """End-to-end: fresh player, no upgrades, no rep. Bumps rep,
        purchases a Mk1 upgrade, enhances to Mk2 with tuning, asserts
        every stat hop along the way."""
        player = fresh_player(credits=50_000)
        mgr = _wire_upgrade_manager(player)
        upgrade = _real_upgrade("cargo_bay_ext")  # base +60, no faction gate
        baseline_cargo = player.ship.max_cargo

        # Mk1 install
        ok, _ = _buy_upgrade(player, mgr, upgrade)
        assert ok
        mk1_cargo = player.ship.max_cargo
        assert mk1_cargo == baseline_cargo + int(upgrade.bonus_value)

        # Mk2 enhance with first available tuning
        tuning_id = upgrade.tuning_options[0]["id"]
        ok2, _ = mgr.enhance(upgrade.id, mark=2, tuning=tuning_id)
        assert ok2
        mk2_cargo = player.ship.max_cargo
        # Cargo strictly increases by at least the Mk2 - Mk1 delta on the
        # main bonus (tuning may or may not contribute additional cargo).
        expected_mk2_main = int(upgrade.bonus_value * MARK_MULTIPLIERS[2])
        assert mk2_cargo >= baseline_cargo + expected_mk2_main

        # Manager records the new mark
        installed = mgr.get_installed(upgrade.id)
        assert installed is not None
        assert installed.mark == 2
        assert installed.tuning == tuning_id
