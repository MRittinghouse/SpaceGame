"""Tests for ground mission contract system.

Tests GroundContract model, GroundContractManager generation/expiry/
completion, contract template loading, and save/load round-trips.
"""

import pytest

from spacegame.models.ground_contracts import (
    GroundContract,
    GroundContractManager,
)
from spacegame.models.ground_mission import (
    GroundMissionConfig,
    GroundMissionRewards,
)
from spacegame.models.ground_mapgen import DifficultyTier, MissionType


# ===========================================================================
# Helpers
# ===========================================================================


def _make_config(**overrides) -> GroundMissionConfig:
    """Create a test GroundMissionConfig."""
    defaults = {
        "id": "contract_test_01",
        "name": "Test Contract Mission",
        "description": "Infiltrate the test facility.",
        "mission_type": MissionType.INFILTRATION,
        "difficulty": DifficultyTier.LOW,
        "faction_id": "commerce_guild",
        "objectives": ["Reach the target"],
        "intel_hints": [],
        "rewards": GroundMissionRewards(credits=300, xp=15),
        "seed": 42,
    }
    defaults.update(overrides)
    return GroundMissionConfig(**defaults)


def _make_contract(**overrides) -> GroundContract:
    """Create a test GroundContract."""
    defaults = {
        "id": "test_contract_001",
        "config": _make_config(),
        "system_id": "nexus_prime",
        "target_system_id": "nexus_prime",
        "expiry_day": 20,
        "bonus_credits": 100,
    }
    defaults.update(overrides)
    return GroundContract(**defaults)


# ===========================================================================
# GroundContract
# ===========================================================================


class TestGroundContract:
    """GroundContract dataclass behavior."""

    def test_construction(self):
        """Contract stores all fields."""
        contract = _make_contract(
            id="gc_001",
            system_id="forgeworks",
            target_system_id="breakstone",
            expiry_day=30,
            bonus_credits=200,
        )
        assert contract.id == "gc_001"
        assert contract.system_id == "forgeworks"
        assert contract.target_system_id == "breakstone"
        assert contract.expiry_day == 30
        assert contract.bonus_credits == 200
        assert contract.completed is False

    def test_is_expired_before_day(self):
        """Contract is not expired before expiry day."""
        contract = _make_contract(expiry_day=10)
        assert not contract.is_expired(current_day=9)

    def test_is_expired_on_day(self):
        """Contract is not expired on its expiry day."""
        contract = _make_contract(expiry_day=10)
        assert not contract.is_expired(current_day=10)

    def test_is_expired_after_day(self):
        """Contract is expired after expiry day."""
        contract = _make_contract(expiry_day=10)
        assert contract.is_expired(current_day=11)

    def test_days_remaining(self):
        """days_remaining returns correct count."""
        contract = _make_contract(expiry_day=15)
        assert contract.days_remaining(current_day=10) == 5
        assert contract.days_remaining(current_day=15) == 0
        assert contract.days_remaining(current_day=20) == 0

    def test_serialization_round_trip(self):
        """to_dict/from_dict preserves all fields."""
        original = _make_contract(
            id="gc_rt_001",
            bonus_credits=250,
            completed=False,
        )
        data = original.to_dict()
        restored = GroundContract.from_dict(data)
        assert restored.id == original.id
        assert restored.config.name == original.config.name
        assert restored.system_id == original.system_id
        assert restored.target_system_id == original.target_system_id
        assert restored.expiry_day == original.expiry_day
        assert restored.bonus_credits == original.bonus_credits
        assert restored.completed == original.completed

    def test_completed_round_trip(self):
        """Completed flag survives serialization."""
        contract = _make_contract(completed=True)
        data = contract.to_dict()
        restored = GroundContract.from_dict(data)
        assert restored.completed is True


# ===========================================================================
# GroundContractManager — Generation
# ===========================================================================


class TestContractGeneration:
    """GroundContractManager.generate_contracts deterministic seeding."""

    def test_generates_contracts(self):
        """Generates 1-3 contracts for a system."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts(
            system_id="nexus_prime",
            faction_id="commerce_guild",
            game_day=5,
            player_level=3,
        )
        assert 1 <= len(contracts) <= 3

    def test_deterministic_same_inputs(self):
        """Same inputs produce identical contracts."""
        mgr1 = GroundContractManager()
        result1 = mgr1.generate_contracts("nexus_prime", "commerce_guild", 5, 3)

        mgr2 = GroundContractManager()
        result2 = mgr2.generate_contracts("nexus_prime", "commerce_guild", 5, 3)

        assert len(result1) == len(result2)
        for c1, c2 in zip(result1, result2):
            assert c1.id == c2.id
            assert c1.config.name == c2.config.name
            assert c1.config.difficulty == c2.config.difficulty
            assert c1.config.mission_type == c2.config.mission_type

    def test_different_systems_different_contracts(self):
        """Different systems produce different contracts."""
        mgr = GroundContractManager()
        r1 = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        r2 = mgr.generate_contracts("forgeworks", "miners_union", 5, 3)
        # At least IDs should differ
        ids1 = {c.id for c in r1}
        ids2 = {c.id for c in r2}
        assert ids1.isdisjoint(ids2)

    def test_different_days_different_contracts(self):
        """Different days produce different contracts."""
        mgr = GroundContractManager()
        r1 = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        r2 = mgr.generate_contracts("nexus_prime", "commerce_guild", 12, 3)
        ids1 = {c.id for c in r1}
        ids2 = {c.id for c in r2}
        assert ids1.isdisjoint(ids2)

    def test_contracts_have_expiry(self):
        """Generated contracts expire after 5-14 days."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("nexus_prime", "commerce_guild", 10, 3)
        for c in contracts:
            duration = c.expiry_day - 10
            assert 5 <= duration <= 14, f"Duration {duration} out of range"

    def test_contracts_have_rewards(self):
        """Generated contracts have positive rewards."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        for c in contracts:
            assert c.config.rewards.credits > 0
            assert c.bonus_credits > 0

    def test_difficulty_scales_with_level(self):
        """Higher player level unlocks harder contracts."""
        mgr_low = GroundContractManager()
        contracts_low = mgr_low.generate_contracts("nexus_prime", "commerce_guild", 5, 1)
        difficulties_low = {c.config.difficulty for c in contracts_low}

        mgr_high = GroundContractManager()
        contracts_high = mgr_high.generate_contracts("nexus_prime", "commerce_guild", 5, 8)
        difficulties_high = {c.config.difficulty for c in contracts_high}

        # Low level should not get EXTREME; high level CAN get harder ones
        assert DifficultyTier.EXTREME not in difficulties_low

    def test_system_id_stored(self):
        """Contract system_id matches where it was posted."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("forgeworks", "miners_union", 5, 3)
        for c in contracts:
            assert c.system_id == "forgeworks"

    def test_faction_id_on_config(self):
        """Contract config has the correct faction_id."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        for c in contracts:
            assert c.config.faction_id == "commerce_guild"

    def test_contracts_added_to_manager(self):
        """Generated contracts are tracked internally."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        assert len(mgr.active_contracts) == len(contracts)


# ===========================================================================
# GroundContractManager — Availability
# ===========================================================================


class TestContractAvailability:
    """GroundContractManager.get_available filtering."""

    def test_available_by_system(self):
        """Only returns contracts for the requested system."""
        mgr = GroundContractManager()
        mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        mgr.generate_contracts("forgeworks", "miners_union", 5, 3)
        available = mgr.get_available("nexus_prime", game_day=5)
        for c in available:
            assert c.system_id == "nexus_prime"

    def test_excludes_expired(self):
        """Expired contracts are not returned."""
        mgr = GroundContractManager()
        mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        # Advance past all expiry days
        available = mgr.get_available("nexus_prime", game_day=100)
        assert len(available) == 0

    def test_excludes_completed(self):
        """Completed contracts are not returned."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        mgr.complete_contract(contracts[0].id)
        available = mgr.get_available("nexus_prime", game_day=5)
        assert contracts[0].id not in {c.id for c in available}


# ===========================================================================
# GroundContractManager — Completion
# ===========================================================================


class TestContractCompletion:
    """GroundContractManager.complete_contract behavior."""

    def test_marks_completed(self):
        """Completing a contract marks it as completed."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        cid = contracts[0].id
        success, msg = mgr.complete_contract(cid)
        assert success
        assert contracts[0].completed is True

    def test_increments_completed_count(self):
        """Completion counter tracks total completions."""
        mgr = GroundContractManager()
        c1 = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        c2 = mgr.generate_contracts("forgeworks", "miners_union", 5, 3)
        mgr.complete_contract(c1[0].id)
        assert mgr.completed_count == 1
        mgr.complete_contract(c2[0].id)
        assert mgr.completed_count == 2

    def test_cannot_complete_unknown(self):
        """Completing unknown contract ID fails."""
        mgr = GroundContractManager()
        success, msg = mgr.complete_contract("nonexistent_id")
        assert not success

    def test_cannot_double_complete(self):
        """Completing same contract twice fails."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        mgr.complete_contract(contracts[0].id)
        success, msg = mgr.complete_contract(contracts[0].id)
        assert not success

    def test_returns_bonus_in_message(self):
        """Completion message mentions bonus credits."""
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        success, msg = mgr.complete_contract(contracts[0].id)
        assert "bonus" in msg.lower() or "CR" in msg


# ===========================================================================
# GroundContractManager — Expiry
# ===========================================================================


class TestContractExpiry:
    """GroundContractManager.advance_day cleanup."""

    def test_removes_expired(self):
        """advance_day removes expired contracts."""
        mgr = GroundContractManager()
        mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        initial_count = len(mgr.active_contracts)
        assert initial_count > 0
        mgr.advance_day(game_day=200)
        assert len(mgr.active_contracts) == 0

    def test_keeps_active(self):
        """advance_day keeps contracts within expiry window."""
        mgr = GroundContractManager()
        mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        mgr.advance_day(game_day=6)  # Still within window
        assert len(mgr.active_contracts) > 0


# ===========================================================================
# GroundContractManager — Serialization
# ===========================================================================


class TestContractManagerSerialization:
    """GroundContractManager to_dict/from_dict."""

    def test_round_trip(self):
        """Serialization preserves all state."""
        mgr = GroundContractManager()
        mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        mgr.generate_contracts("forgeworks", "miners_union", 8, 5)
        mgr.complete_contract(mgr.active_contracts[0].id)

        data = mgr.to_dict()
        restored = GroundContractManager.from_dict(data)

        assert len(restored.active_contracts) == len(mgr.active_contracts)
        assert restored.completed_count == mgr.completed_count

    def test_empty_manager_round_trip(self):
        """Empty manager serializes/deserializes cleanly."""
        mgr = GroundContractManager()
        data = mgr.to_dict()
        restored = GroundContractManager.from_dict(data)
        assert len(restored.active_contracts) == 0
        assert restored.completed_count == 0


# ===========================================================================
# Contract Template Loading
# ===========================================================================


class TestContractTemplates:
    """Contract template data loading."""

    def test_templates_loaded(self):
        """DataLoader has contract templates populated."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        assert hasattr(dl, "contract_templates")
        assert len(dl.contract_templates) > 0

    def test_templates_have_descriptions(self):
        """Each mission type template has at least one description."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        for mt_key, template in dl.contract_templates.items():
            assert len(template["descriptions"]) > 0, (
                f"Template {mt_key} has no descriptions"
            )

    def test_templates_have_objectives(self):
        """Each mission type template has at least one objective."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        for mt_key, template in dl.contract_templates.items():
            assert len(template["objectives"]) > 0, (
                f"Template {mt_key} has no objectives"
            )

    def test_generated_contracts_use_templates(self):
        """Generated contract descriptions come from templates."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        mgr = GroundContractManager()
        contracts = mgr.generate_contracts("nexus_prime", "commerce_guild", 5, 3)
        for c in contracts:
            # Description should be non-empty and not a placeholder
            assert len(c.config.description) > 10
            assert len(c.config.objectives) >= 1
