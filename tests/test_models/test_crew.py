"""Tests for crew system models."""

from pathlib import Path

import pytest

from spacegame.data_loader import DataLoader
from spacegame.models.crew import (
    CrewAbility,
    CrewRoster,
    CrewTemplate,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.upgrades import ShipUpgrade, ShipUpgradeManager

# ============================================================================
# Helpers
# ============================================================================


def _make_ship_type(crew_slots: int = 3) -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=10,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=crew_slots,
        special_abilities=[],
        availability="all",
    )


def _make_player(crew_slots: int = 3, **overrides) -> Player:
    defaults = {
        "name": "TestCaptain",
        "credits": 2000,
        "current_system_id": "nexus_prime",
        "ship": Ship(ship_type=_make_ship_type(crew_slots), current_fuel=50),
    }
    defaults.update(overrides)
    return Player(**defaults)


def _make_ability(
    bonus_type: str = "fuel_efficiency_bonus",
    bonus_value: float = 2.0,
    description: str = "Test ability",
    unlock_level: int = 1,
) -> CrewAbility:
    return CrewAbility(
        bonus_type=bonus_type,
        bonus_value=bonus_value,
        description=description,
        unlock_level=unlock_level,
    )


def _make_template(
    template_id: str = "elena_reeves",
    name: str = "Elena Reeves",
    role: str = "navigator",
    abilities: list[CrewAbility] | None = None,
    max_level: int = 5,
    home_system_id: str = "nexus_prime",
) -> CrewTemplate:
    if abilities is None:
        abilities = [
            _make_ability("fuel_efficiency_bonus", 2.0, "Efficient Routing", 1),
            _make_ability("fuel_efficiency_bonus", 3.0, "Advanced Navigation", 3),
            _make_ability("fuel_bonus", 20.0, "Fleet Support", 5),
        ]
    return CrewTemplate(
        id=template_id,
        name=name,
        role=role,
        description=f"A test crew member: {name}",
        portrait_color=[100, 180, 255],
        abilities=abilities,
        max_level=max_level,
        xp_thresholds=[0, 50, 150, 350, 700],
        is_companion=True,
        home_system_id=home_system_id,
    )


def _make_roster(
    templates: dict[str, CrewTemplate] | None = None,
) -> CrewRoster:
    if templates is None:
        templates = {
            "elena_reeves": _make_template(),
            "marcus_jin": _make_template(
                "marcus_jin",
                "Marcus Jin",
                "engineer",
                [
                    _make_ability("cargo_bonus", 15.0, "Cargo Optimization", 1),
                    _make_ability("fuel_bonus", 15.0, "Fuel Tank Mods", 3),
                    _make_ability("cargo_bonus", 20.0, "Master Engineer", 5),
                ],
                home_system_id="breakstone",
            ),
        }
    return CrewRoster(templates)


# ============================================================================
# CrewAbility Tests
# ============================================================================


class TestCrewAbility:
    """Tests for CrewAbility dataclass."""

    def test_creation(self) -> None:
        ability = _make_ability()
        assert ability.bonus_type == "fuel_efficiency_bonus"
        assert ability.bonus_value == 2.0
        assert ability.description == "Test ability"
        assert ability.unlock_level == 1

    def test_to_dict_from_dict_roundtrip(self) -> None:
        ability = _make_ability("cargo_bonus", 15.0, "Cargo Opt", 3)
        data = ability.to_dict()
        restored = CrewAbility.from_dict(data)
        assert restored.bonus_type == ability.bonus_type
        assert restored.bonus_value == ability.bonus_value
        assert restored.description == ability.description
        assert restored.unlock_level == ability.unlock_level


# ============================================================================
# CrewTemplate Tests
# ============================================================================


class TestCrewTemplate:
    """Tests for CrewTemplate dataclass."""

    def test_creation(self) -> None:
        template = _make_template()
        assert template.id == "elena_reeves"
        assert template.name == "Elena Reeves"
        assert template.role == "navigator"
        assert len(template.abilities) == 3
        assert template.max_level == 5
        assert len(template.xp_thresholds) == 5

    def test_get_abilities_at_level(self) -> None:
        template = _make_template()
        # Level 1: only first ability (unlock_level=1)
        lv1 = template.get_abilities_at_level(1)
        assert len(lv1) == 1
        assert lv1[0].unlock_level == 1

        # Level 3: first two abilities
        lv3 = template.get_abilities_at_level(3)
        assert len(lv3) == 2

        # Level 5: all three
        lv5 = template.get_abilities_at_level(5)
        assert len(lv5) == 3

    def test_get_bonus_at_level(self) -> None:
        template = _make_template()
        # Level 1: only 2.0 fuel_efficiency_bonus
        assert template.get_bonus_at_level("fuel_efficiency_bonus", 1) == 2.0
        # Level 3: 2.0 + 3.0 = 5.0
        assert template.get_bonus_at_level("fuel_efficiency_bonus", 3) == 5.0
        # fuel_bonus only at level 5
        assert template.get_bonus_at_level("fuel_bonus", 3) == 0.0
        assert template.get_bonus_at_level("fuel_bonus", 5) == 20.0


# ============================================================================
# CrewRoster — Recruitment Tests
# ============================================================================


class TestCrewRosterRecruitment:
    """Tests for crew recruitment and dismissal."""

    def test_recruit_succeeds_with_slot(self) -> None:
        roster = _make_roster()
        success, msg = roster.recruit("elena_reeves", crew_slots=3)
        assert success, f"Recruit should succeed: {msg}"
        assert len(roster.get_recruited_members()) == 1

    def test_recruit_fails_when_full(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=1)
        success, msg = roster.recruit("marcus_jin", crew_slots=1)
        assert not success, "Recruit should fail when slots full"
        assert "slot" in msg.lower() or "full" in msg.lower()

    def test_recruit_fails_duplicate(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        success, msg = roster.recruit("elena_reeves", crew_slots=3)
        assert not success, "Duplicate recruit should fail"
        assert "already" in msg.lower()

    def test_recruit_fails_unknown_template(self) -> None:
        roster = _make_roster()
        success, msg = roster.recruit("nonexistent", crew_slots=3)
        assert not success, "Unknown template should fail"
        assert "not found" in msg.lower() or "unknown" in msg.lower()

    def test_dismiss_succeeds(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        success, msg = roster.dismiss("elena_reeves")
        assert success, f"Dismiss should succeed: {msg}"
        assert len(roster.get_recruited_members()) == 0


# ============================================================================
# CrewRoster — Bonus Tests
# ============================================================================


class TestCrewRosterBonuses:
    """Tests for crew bonus calculations."""

    def test_get_bonus_no_crew(self) -> None:
        roster = _make_roster()
        assert roster.get_bonus("fuel_efficiency_bonus") == 0.0

    def test_get_bonus_sums_active_crew(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        # Elena at level 1: fuel_efficiency_bonus = 2.0
        assert roster.get_bonus("fuel_efficiency_bonus") == 2.0

    def test_higher_level_unlocks_abilities(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        # Manually set level to 3
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["level"] = 3
        # Now both lv1 and lv3 abilities active: 2.0 + 3.0 = 5.0
        assert roster.get_bonus("fuel_efficiency_bonus") == 5.0

    def test_multiple_crew_bonuses_stack(self) -> None:
        # Both Elena and Marcus have fuel_bonus at different levels
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        roster.recruit("marcus_jin", crew_slots=3)
        # Elena lv1: fuel_efficiency_bonus=2, no fuel_bonus
        # Marcus lv1: cargo_bonus=15, no fuel_bonus
        # Neither contributes fuel_bonus at level 1
        assert roster.get_bonus("fuel_bonus") == 0.0
        assert roster.get_bonus("cargo_bonus") == 15.0
        assert roster.get_bonus("fuel_efficiency_bonus") == 2.0


# ============================================================================
# CrewRoster — XP & Leveling Tests
# ============================================================================


class TestCrewRosterXP:
    """Tests for crew XP and leveling."""

    def test_add_xp_to_all(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        roster.recruit("marcus_jin", crew_slots=3)
        roster.add_xp_to_all(30)
        elena_state = roster.get_member_state("elena_reeves")
        marcus_state = roster.get_member_state("marcus_jin")
        assert elena_state is not None and elena_state["xp"] == 30
        assert marcus_state is not None and marcus_state["xp"] == 30

    def test_level_up_on_threshold(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        # Thresholds: [0, 50, 150, 350, 700]
        # At 50 XP, should level up to 2
        messages = roster.add_xp_to_all(50)
        state = roster.get_member_state("elena_reeves")
        assert state is not None and state["level"] == 2
        assert any("Elena" in m or "level" in m.lower() for m in messages)

    def test_level_capped_at_max(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        # Give massive XP to exceed all thresholds
        roster.add_xp_to_all(2000)
        state = roster.get_member_state("elena_reeves")
        assert state is not None and state["level"] == 5  # max_level
        assert state["xp"] == 2000  # XP still accumulates

    def test_add_xp_returns_levelup_messages(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        # No level up at 30 XP
        messages = roster.add_xp_to_all(30)
        assert len(messages) == 0
        # Level up at 50
        messages = roster.add_xp_to_all(20)  # total 50
        assert len(messages) == 1


# ============================================================================
# CrewRoster — Loyalty Tests
# ============================================================================


class TestCrewRosterLoyalty:
    """Tests for crew loyalty system."""

    def test_loyalty_starts_at_30(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        state = roster.get_member_state("elena_reeves")
        assert state is not None and state["loyalty"] == 30

    def test_adjust_loyalty_increase_capped_at_100(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        roster.adjust_loyalty("elena_reeves", 80)  # 30 + 80 = 110 -> capped at 100
        state = roster.get_member_state("elena_reeves")
        assert state is not None and state["loyalty"] == 100

    def test_adjust_loyalty_decrease_floored_at_0(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        roster.adjust_loyalty("elena_reeves", -80)  # 30 - 80 = -50 -> floored at 0
        state = roster.get_member_state("elena_reeves")
        assert state is not None and state["loyalty"] == 0


# ============================================================================
# CrewRoster — Serialization Tests
# ============================================================================


class TestCrewRosterSerialization:
    """Tests for crew state serialization."""

    def test_get_state_load_state_roundtrip(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        roster.recruit("marcus_jin", crew_slots=3)
        roster.add_xp_to_all(60)  # Elena levels to 2 (at 50 threshold)
        roster.adjust_loyalty("elena_reeves", 10)

        saved = roster.get_state()

        # Create fresh roster and restore
        roster2 = _make_roster()
        roster2.load_state(saved)

        assert len(roster2.get_recruited_members()) == 2
        elena = roster2.get_member_state("elena_reeves")
        assert elena is not None
        assert elena["level"] == 2
        assert elena["xp"] == 60
        assert elena["loyalty"] == 40  # 30 + 10

        marcus = roster2.get_member_state("marcus_jin")
        assert marcus is not None
        assert marcus["level"] == 2  # Also levels to 2 at 50
        assert marcus["xp"] == 60

    def test_load_state_skips_unknown_template(self) -> None:
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        saved = roster.get_state()

        # Inject unknown template ID into saved state
        saved["recruited"].append("unknown_crew")
        saved["members"]["unknown_crew"] = {"level": 1, "xp": 0, "loyalty": 30}

        roster2 = _make_roster()
        roster2.load_state(saved)
        # Only elena should be restored (unknown_crew skipped)
        assert len(roster2.get_recruited_members()) == 1


# ============================================================================
# CrewRoster — Integration Tests
# ============================================================================


class TestCrewRosterIntegration:
    """Tests for crew bonuses integrating with other systems."""

    def test_crew_bonus_stacks_with_upgrade_bonus(self) -> None:
        """Verify crew cargo_bonus stacks additively with upgrade cargo_bonus."""
        roster = _make_roster()
        roster.recruit("marcus_jin", crew_slots=3)
        crew_cargo = roster.get_bonus("cargo_bonus")  # 15.0

        upgrade_mgr = ShipUpgradeManager()
        cargo_upgrade = ShipUpgrade(
            id="cargo_exp",
            name="Cargo Expansion",
            description="More cargo",
            price=500,
            slot_type="cargo",
            bonus_type="cargo_bonus",
            bonus_value=20.0,
        )
        upgrade_mgr.install(cargo_upgrade)
        upgrade_cargo = upgrade_mgr.get_bonus("cargo_bonus")  # 20.0

        total = crew_cargo + upgrade_cargo
        assert total == 35.0, f"Expected 35.0, got {total}"

    def test_crew_bonus_stacks_with_progression_bonus(self) -> None:
        """Verify crew buy_price_reduction stacks with skill buy_price_reduction."""
        trader_template = _make_template(
            "tomas_drifter",
            "Tomas Drifter",
            "trader",
            [_make_ability("buy_price_reduction", 0.03, "Trade Contacts", 1)],
        )
        roster = CrewRoster({"tomas_drifter": trader_template})
        roster.recruit("tomas_drifter", crew_slots=3)
        crew_discount = roster.get_bonus("buy_price_reduction")  # 0.03

        # Progression bonuses are tested separately — just verify additive stacking
        skill_discount = 0.05  # Simulated skill bonus
        total = crew_discount + skill_discount
        assert abs(total - 0.08) < 0.001, f"Expected ~0.08, got {total}"


# ============================================================================
# CrewRoster — Pending Companions Tests
# ============================================================================


def _make_non_companion_template(
    template_id: str = "hired_gunner",
    name: str = "Hired Gunner",
) -> CrewTemplate:
    """Create a non-companion crew template."""
    return CrewTemplate(
        id=template_id,
        name=name,
        role="gunner",
        description=f"A hired crew member: {name}",
        portrait_color=[180, 80, 80],
        abilities=[_make_ability("combat_bonus", 5.0, "Trained Fighter", 1)],
        max_level=3,
        xp_thresholds=[0, 100, 300],
        is_companion=False,
        home_system_id="nexus_prime",
    )


class TestPendingCompanions:
    """Tests for pending companion recruitment (crew full fallback)."""

    def test_add_pending_companion(self) -> None:
        """Adding a companion to pending tracking works."""
        roster = _make_roster()
        result = roster.add_pending_companion("elena_reeves")
        assert result, "Should succeed for a companion template"
        assert "elena_reeves" in roster.pending_companion_ids

    def test_add_pending_non_companion_fails(self) -> None:
        """Non-companion crew cannot be added to pending."""
        templates = {
            "hired_gunner": _make_non_companion_template(),
        }
        roster = CrewRoster(templates)
        result = roster.add_pending_companion("hired_gunner")
        assert not result, "Should fail for non-companion"
        assert "hired_gunner" not in roster.pending_companion_ids

    def test_add_pending_unknown_template_fails(self) -> None:
        """Unknown template ID returns False."""
        roster = _make_roster()
        result = roster.add_pending_companion("nonexistent")
        assert not result

    def test_pending_companion_shows_in_available_at_system(self) -> None:
        """A pending companion at their home system shows in available crew."""
        roster = _make_roster()
        roster.add_pending_companion("elena_reeves")
        available = roster.get_available_crew_at_system("nexus_prime")
        ids = [t.id for t in available]
        assert "elena_reeves" in ids, f"Pending companion should appear at home system, got {ids}"

    def test_pending_companion_not_at_wrong_system(self) -> None:
        """Pending companion doesn't show at a different system."""
        roster = _make_roster()
        roster.add_pending_companion("elena_reeves")
        available = roster.get_available_crew_at_system("breakstone")
        ids = [t.id for t in available]
        assert "elena_reeves" not in ids

    def test_recruit_clears_pending(self) -> None:
        """Successful recruit removes companion from pending set."""
        roster = _make_roster()
        roster.add_pending_companion("elena_reeves")
        assert "elena_reeves" in roster.pending_companion_ids

        roster.recruit("elena_reeves", crew_slots=3)
        assert "elena_reeves" not in roster.pending_companion_ids

    def test_pending_serialization_roundtrip(self) -> None:
        """get_state/load_state preserves pending companions."""
        roster = _make_roster()
        roster.add_pending_companion("elena_reeves")
        saved = roster.get_state()

        roster2 = _make_roster()
        roster2.load_state(saved)
        assert "elena_reeves" in roster2.pending_companion_ids

    def test_pending_backward_compat(self) -> None:
        """load_state without pending_companions key works (old saves)."""
        roster = _make_roster()
        roster.recruit("elena_reeves", crew_slots=3)
        saved = roster.get_state()
        # Remove the pending_companions key to simulate old save format
        saved.pop("pending_companions", None)

        roster2 = _make_roster()
        roster2.load_state(saved)
        assert len(roster2.pending_companion_ids) == 0
        assert len(roster2.get_recruited_members()) == 1

    def test_non_pending_companion_still_excluded(self) -> None:
        """Regular companions without pending status don't appear in cantina."""
        roster = _make_roster()
        # Don't add to pending — just check they don't show up
        available = roster.get_available_crew_at_system("nexus_prime")
        ids = [t.id for t in available]
        assert "elena_reeves" not in ids, (
            "Non-pending companions should not appear in available crew"
        )


# ============================================================================
# SA Arc Specialist Tests (SA-A2)
# ============================================================================

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_sa_loader_cache: DataLoader | None = None


def _get_sa_loader() -> DataLoader:
    """Load crew templates from live JSON once and cache for the SA-A2 test class."""
    global _sa_loader_cache
    if _sa_loader_cache is None:
        loader = DataLoader(data_dir=_PROJECT_ROOT / "data")
        loader.load_all()
        _sa_loader_cache = loader
    return _sa_loader_cache


def _make_sa_roster() -> CrewRoster:
    """Return a CrewRoster seeded with all live crew templates."""
    loader = _get_sa_loader()
    return CrewRoster(loader.crew_templates)


class TestSAArcSpecialists:
    """Integration tests for the five SA arc specialist crew members.

    All tests use the live DataLoader against the real JSON files so that
    JSON authoring — not test fixtures — is what's being verified.
    """

    # ------------------------------------------------------------------
    # AC 2: DataLoader loads all five templates without warning
    # ------------------------------------------------------------------

    def test_sable_trent_template_loads(self) -> None:
        loader = _get_sa_loader()
        template = loader.get_crew_template("sable_trent")
        assert template is not None, "sable_trent template should load from JSON"
        assert template.name == "Sable Trent"
        assert template.role == "auction reader"
        assert template.max_level == 1
        assert template.xp_thresholds == [0]
        assert template.is_companion is False

    def test_desta_coll_template_loads(self) -> None:
        loader = _get_sa_loader()
        template = loader.get_crew_template("desta_coll")
        assert template is not None, "desta_coll template should load from JSON"
        assert template.name == "Desta Coll"
        assert template.role == "coalition builder"
        assert template.max_level == 1
        assert template.is_companion is False

    def test_cass_weller_template_loads(self) -> None:
        loader = _get_sa_loader()
        template = loader.get_crew_template("cass_weller")
        assert template is not None, "cass_weller template should load from JSON"
        assert template.name == "Cass Weller"
        assert template.role == "arbiter"
        assert template.max_level == 1
        assert template.is_companion is False

    def test_brix_tano_template_loads(self) -> None:
        loader = _get_sa_loader()
        template = loader.get_crew_template("brix_tano")
        assert template is not None, "brix_tano template should load from JSON"
        assert template.name == "Brix Tano"
        assert template.role == "speculator"
        assert template.max_level == 1
        assert template.is_companion is False

    def test_nuri_solberg_template_loads(self) -> None:
        loader = _get_sa_loader()
        template = loader.get_crew_template("nuri_solberg")
        assert template is not None, "nuri_solberg template should load from JSON"
        assert template.name == "Nuri Solberg"
        assert template.role == "research patron"
        assert template.max_level == 1
        assert template.is_companion is False

    # ------------------------------------------------------------------
    # AC 1: no combat_moves or combat_move field on any of the five
    # ------------------------------------------------------------------

    def test_no_specialist_has_combat_fields(self) -> None:
        loader = _get_sa_loader()
        for sid in ("sable_trent", "desta_coll", "cass_weller", "brix_tano", "nuri_solberg"):
            tmpl = loader.get_crew_template(sid)
            assert tmpl is not None
            assert not tmpl.combat_moves, f"{sid} should have no combat_moves"

    # ------------------------------------------------------------------
    # AC 3: bonuses resolve to correct magnitudes after recruitment
    # ------------------------------------------------------------------

    def test_sable_trent_bonuses_resolve(self) -> None:
        roster = _make_sa_roster()
        success, msg = roster.recruit("sable_trent", crew_slots=10)
        assert success, f"sable_trent recruit should succeed: {msg}"
        assert roster.get_bonus("auction_bid_visibility") == pytest.approx(1.0)
        assert roster.get_bonus("auction_lot_appraisal_bonus") == pytest.approx(0.10)

    def test_desta_coll_bonuses_resolve(self) -> None:
        roster = _make_sa_roster()
        success, msg = roster.recruit("desta_coll", crew_slots=10)
        assert success, f"desta_coll recruit should succeed: {msg}"
        assert roster.get_bonus("coalition_sway_bonus") == pytest.approx(0.15)
        assert roster.get_bonus("coalition_size_bonus") == pytest.approx(1.0)

    def test_cass_weller_bonuses_resolve(self) -> None:
        roster = _make_sa_roster()
        success, msg = roster.recruit("cass_weller", crew_slots=10)
        assert success, f"cass_weller recruit should succeed: {msg}"
        assert roster.get_bonus("arbitration_neutrality_bonus") == pytest.approx(0.15)
        assert roster.get_bonus("arbitration_dispute_intel") == pytest.approx(1.0)

    def test_brix_tano_bonuses_resolve(self) -> None:
        roster = _make_sa_roster()
        success, msg = roster.recruit("brix_tano", crew_slots=10)
        assert success, f"brix_tano recruit should succeed: {msg}"
        assert roster.get_bonus("futures_intel") == pytest.approx(1.0)
        assert roster.get_bonus("speculator_premium_reduction") == pytest.approx(0.10)

    def test_nuri_solberg_bonuses_resolve(self) -> None:
        roster = _make_sa_roster()
        success, msg = roster.recruit("nuri_solberg", crew_slots=10)
        assert success, f"nuri_solberg recruit should succeed: {msg}"
        assert roster.get_bonus("research_yield_bonus") == pytest.approx(0.10)
        assert roster.get_bonus("research_risk_reduction") == pytest.approx(0.10)

    # ------------------------------------------------------------------
    # AC 4: bonuses return 0.0 when specialist not recruited
    # ------------------------------------------------------------------

    def test_specialist_bonuses_zero_when_not_recruited(self) -> None:
        roster = _make_sa_roster()
        for bonus_type in (
            "auction_bid_visibility",
            "auction_lot_appraisal_bonus",
            "coalition_sway_bonus",
            "coalition_size_bonus",
            "arbitration_neutrality_bonus",
            "arbitration_dispute_intel",
            "futures_intel",
            "speculator_premium_reduction",
            "research_yield_bonus",
            "research_risk_reduction",
        ):
            assert roster.get_bonus(bonus_type) == 0.0, (
                f"{bonus_type} should be 0.0 when no specialist recruited"
            )

    # ------------------------------------------------------------------
    # AC 5: each specialist appears at their locked home system
    # ------------------------------------------------------------------

    def test_specialists_appear_at_home_systems(self) -> None:
        roster = _make_sa_roster()

        stellaris = [t.id for t in roster.get_available_crew_at_system("stellaris_port")]
        assert "sable_trent" in stellaris, (
            f"sable_trent should be at stellaris_port, got {stellaris}"
        )
        assert "rina_vasquez" in stellaris, "rina_vasquez should also be at stellaris_port"
        assert "leah_chen" in stellaris, "leah_chen should also be at stellaris_port"

        havens = [t.id for t in roster.get_available_crew_at_system("havens_rest")]
        assert "desta_coll" in havens, f"desta_coll should be at havens_rest, got {havens}"
        assert "adisa_nyongo" in havens, "adisa_nyongo should also be at havens_rest"

        crimson = [t.id for t in roster.get_available_crew_at_system("crimson_reach")]
        assert "cass_weller" in crimson, f"cass_weller should be at crimson_reach, got {crimson}"
        assert "sgt_harkov" in crimson, "sgt_harkov should also be at crimson_reach"

        nexus = [t.id for t in roster.get_available_crew_at_system("nexus_prime")]
        assert "brix_tano" in nexus, f"brix_tano should be at nexus_prime, got {nexus}"
        assert "kai_torren" in nexus, "kai_torren should also be at nexus_prime"

        axiom = [t.id for t in roster.get_available_crew_at_system("axiom_labs")]
        assert "nuri_solberg" in axiom, f"nuri_solberg should be at axiom_labs, got {axiom}"

    def test_specialist_not_at_wrong_system(self) -> None:
        roster = _make_sa_roster()
        for specialist in ("sable_trent", "desta_coll", "cass_weller", "brix_tano", "nuri_solberg"):
            # Check they don't appear at a system that is not their home
            wrong_systems = [
                s
                for s in ("breakstone", "verdant", "forgeworks", "herons_mark")
                if s
                not in (
                    "stellaris_port",
                    "havens_rest",
                    "crimson_reach",
                    "nexus_prime",
                    "axiom_labs",
                )
            ]
            for sys_id in wrong_systems:
                available_ids = [t.id for t in roster.get_available_crew_at_system(sys_id)]
                assert specialist not in available_ids, (
                    f"{specialist} should not appear at {sys_id}"
                )

    # ------------------------------------------------------------------
    # AC 6: save/load round-trip preserves sable_trent
    # ------------------------------------------------------------------

    def test_sable_trent_save_load_roundtrip(self) -> None:
        roster = _make_sa_roster()
        roster.recruit("sable_trent", crew_slots=10)
        assert roster.get_bonus("auction_bid_visibility") == pytest.approx(1.0)

        saved = roster.get_state()

        roster2 = _make_sa_roster()
        roster2.load_state(saved)

        assert roster2.is_recruited("sable_trent"), "sable_trent should survive round-trip"
        assert roster2.get_bonus("auction_bid_visibility") == pytest.approx(1.0)
        assert roster2.get_bonus("auction_lot_appraisal_bonus") == pytest.approx(0.10)

    # ------------------------------------------------------------------
    # AC 7: add_xp_to_all is a no-op for specialists (max_level=1)
    # ------------------------------------------------------------------

    def test_specialists_no_xp_gain(self) -> None:
        roster = _make_sa_roster()
        roster.recruit("sable_trent", crew_slots=10)
        messages = roster.add_xp_to_all(10000)
        specialist_messages = [m for m in messages if "Sable" in m or "sable_trent" in m]
        assert len(specialist_messages) == 0, (
            f"No level-up message should fire for a max_level=1 specialist; got: {specialist_messages}"
        )

    # ------------------------------------------------------------------
    # AC 12: bonus-string collision regression
    # ------------------------------------------------------------------

    def test_no_duplicate_bonus_type_descriptions(self) -> None:
        """No two crew templates share (bonus_type, description) across the roster.

        Catches accidental copy-paste of an ability block between templates.
        Internal duplicate within a single template is also prohibited.
        """
        loader = _get_sa_loader()
        seen_pairs: dict[tuple[str, str], str] = {}
        errors = []

        for tid, template in loader.crew_templates.items():
            internal: set[tuple[str, str]] = set()
            for ability in template.abilities:
                pair = (ability.bonus_type, ability.description)
                # Internal duplicate within one template
                if pair in internal:
                    errors.append(
                        f"Template '{tid}' has duplicate (bonus_type, description) pair: {pair}"
                    )
                internal.add(pair)
                # Cross-template duplicate
                if pair in seen_pairs and seen_pairs[pair] != tid:
                    errors.append(
                        f"Templates '{seen_pairs[pair]}' and '{tid}' share "
                        f"(bonus_type, description) pair: {pair}"
                    )
                else:
                    seen_pairs[pair] = tid

        assert not errors, "\n".join(errors)
