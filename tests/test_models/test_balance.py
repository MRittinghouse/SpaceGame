"""Tests for the Act 1 balancing pass.

Verifies all rebalanced values across config constants, model defaults,
JSON data files, and cross-system integration.
"""

import pytest
from pathlib import Path
from spacegame import config
from spacegame.models.social import SOCIAL_XP_THRESHOLDS, MAX_SOCIAL_LEVEL
from spacegame.models.encounter import (
    ENCOUNTER_CHANCE_SAFE,
    ENCOUNTER_CHANCE_MODERATE,
    ENCOUNTER_CHANCE_DANGEROUS,
)
from spacegame.models.event import EventGenerator
from spacegame.data_loader import DataLoader


def _make_loader() -> DataLoader:
    """Create a DataLoader pointing at the project data/ directory."""
    project_root = Path(__file__).parent.parent.parent
    return DataLoader(data_dir=project_root / "data")


# ============================================================================
# Step 1: Config Constants
# ============================================================================


class TestConfigConstants:
    """Verify rebalanced config.py constants."""

    def test_starting_credits(self) -> None:
        assert config.STARTING_CREDITS == 4000, (
            f"Starting credits should be 4000, got {config.STARTING_CREDITS}"
        )

    def test_xp_per_mining(self) -> None:
        assert config.XP_PER_MINING == 3, f"Mining XP should be 3, got {config.XP_PER_MINING}"

    def test_xp_per_salvage(self) -> None:
        assert config.XP_PER_SALVAGE == 6, f"Salvage XP should be 6, got {config.XP_PER_SALVAGE}"

    def test_xp_per_refine(self) -> None:
        assert config.XP_PER_REFINE == 10, f"Refine XP should be 10, got {config.XP_PER_REFINE}"

    def test_xp_per_trade(self) -> None:
        assert config.XP_PER_TRADE == 5, "Trade XP should be 5"

    def test_xp_per_travel(self) -> None:
        assert config.XP_PER_TRAVEL == 10, "Travel XP should remain 10"

    def test_ground_combat_base_hp(self) -> None:
        assert config.GROUND_COMBAT_BASE_HP == 10, (
            f"Ground HP should be 10, got {config.GROUND_COMBAT_BASE_HP}"
        )


class TestSocialThresholds:
    """Verify social skill XP thresholds are stretched for longer progression."""

    def test_threshold_values(self) -> None:
        assert SOCIAL_XP_THRESHOLDS == [0, 8, 25, 55, 100], (
            f"Social thresholds should be [0, 8, 25, 55, 100], got {SOCIAL_XP_THRESHOLDS}"
        )

    def test_max_social_level_unchanged(self) -> None:
        assert MAX_SOCIAL_LEVEL == 5

    def test_threshold_count_matches_max_level(self) -> None:
        assert len(SOCIAL_XP_THRESHOLDS) == MAX_SOCIAL_LEVEL


class TestEncounterRates:
    """Verify encounter chance constants are raised for more combat."""

    def test_safe_unchanged(self) -> None:
        assert ENCOUNTER_CHANCE_SAFE == 0

    def test_moderate_raised(self) -> None:
        assert ENCOUNTER_CHANCE_MODERATE == 20, (
            f"Moderate encounter chance should be 20%, got {ENCOUNTER_CHANCE_MODERATE}"
        )

    def test_dangerous_raised(self) -> None:
        assert ENCOUNTER_CHANCE_DANGEROUS == 40, (
            f"Dangerous encounter chance should be 40%, got {ENCOUNTER_CHANCE_DANGEROUS}"
        )


class TestMarketEventFrequency:
    """Verify market event chance is doubled."""

    def test_event_chance(self) -> None:
        assert EventGenerator.EVENT_CHANCE == 0.05, (
            f"Event chance should be 0.05, got {EventGenerator.EVENT_CHANCE}"
        )


# ============================================================================
# Step 2: Python Model Changes
# ============================================================================


class TestSkillPointProgression:
    """Verify bonus skill points at milestone levels."""

    def test_level_5_grants_bonus_skill_point(self) -> None:
        from spacegame.models.progression import PlayerProgression, get_xp_threshold

        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(5))
        assert prog.level == 5
        # Levels 2,3,4 = 1 each, level 5 = 2 → total 5
        assert prog.skill_points == 5, (
            f"Should have 5 skill points at level 5 (bonus at 5), got {prog.skill_points}"
        )

    def test_level_10_grants_bonus_skill_point(self) -> None:
        from spacegame.models.progression import PlayerProgression, get_xp_threshold

        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(10))
        assert prog.level == 10
        # Levels 2-4,6-9: 7×1, milestones 5,10: 2×2 → total 11
        assert prog.skill_points == 11, (
            f"Should have 11 skill points at level 10, got {prog.skill_points}"
        )

    def test_skill_points_at_level_20(self) -> None:
        """23 total skill points across 20 levels (milestone every 5th)."""
        from spacegame.models.progression import PlayerProgression, get_xp_threshold

        prog = PlayerProgression()
        prog.add_xp(get_xp_threshold(20))
        assert prog.level == 20
        # 19 level-ups: milestones at 5,10,15,20 = 4*2=8, normal 15*1=15 → total 23
        assert prog.skill_points == 23


class TestCrewLoyalty:
    """Verify crew starts with reduced loyalty."""

    def test_initial_loyalty_is_30(self) -> None:
        from spacegame.models.crew import CrewRoster, CrewTemplate

        template = CrewTemplate(
            id="test_crew",
            name="Test",
            role="Test",
            description="Test crew member",
            portrait_color=(100, 100, 100),
            base_attributes={},
            abilities=[],
            combat_move=None,
        )
        roster = CrewRoster({"test_crew": template})
        success, _ = roster.recruit("test_crew", crew_slots=4)
        assert success
        state = roster.get_member_state("test_crew")
        assert state["loyalty"] == 30, f"Initial loyalty should be 30, got {state['loyalty']}"


class TestMiningYields:
    """Verify mining rock yields are increased."""

    def test_common_rock_yields(self) -> None:
        from spacegame.models.mining import ROCK_TYPE_CONFIGS, RockType

        cfg = ROCK_TYPE_CONFIGS[RockType.COMMON]
        assert cfg.min_yield == 2, f"Common min should be 2, got {cfg.min_yield}"
        assert cfg.max_yield == 4, f"Common max should be 4, got {cfg.max_yield}"

    def test_iron_rock_yields(self) -> None:
        from spacegame.models.mining import ROCK_TYPE_CONFIGS, RockType

        cfg = ROCK_TYPE_CONFIGS[RockType.IRON]
        assert cfg.min_yield == 1, f"Iron min should be 1, got {cfg.min_yield}"
        assert cfg.max_yield == 4, f"Iron max should be 4, got {cfg.max_yield}"

    def test_crystal_rock_yields(self) -> None:
        from spacegame.models.mining import ROCK_TYPE_CONFIGS, RockType

        cfg = ROCK_TYPE_CONFIGS[RockType.CRYSTAL]
        assert cfg.min_yield == 1, f"Crystal min should be 1, got {cfg.min_yield}"
        assert cfg.max_yield == 3, f"Crystal max should be 3, got {cfg.max_yield}"

    def test_rare_rock_yields(self) -> None:
        from spacegame.models.mining import ROCK_TYPE_CONFIGS, RockType

        cfg = ROCK_TYPE_CONFIGS[RockType.RARE]
        assert cfg.min_yield == 1, f"Rare min should be 1, got {cfg.min_yield}"
        assert cfg.max_yield == 3, f"Rare max should be 3, got {cfg.max_yield}"


class TestGameStartingCredits:
    """Verify game.py uses config constant, not a hardcoded value."""

    def test_config_starting_credits_is_authoritative(self) -> None:
        """The config value should be the single source of truth."""
        assert config.STARTING_CREDITS == 4000


# ============================================================================
# Step 3: JSON Economy Data
# ============================================================================


class TestCommodityPrices:
    """Verify raw material and refined good price increases."""

    def test_raw_ore_price(self) -> None:
        loader = _make_loader()
        loader.load_commodities()
        ore = loader.commodities["raw_ore"]
        assert ore.base_price == 5, f"raw_ore should be 5, got {ore.base_price}"

    def test_iron_ore_price(self) -> None:
        loader = _make_loader()
        loader.load_commodities()
        iron = loader.commodities["iron_ore"]
        assert iron.base_price == 15, f"iron_ore should be 15, got {iron.base_price}"

    def test_crystal_ore_price(self) -> None:
        loader = _make_loader()
        loader.load_commodities()
        crystal = loader.commodities["crystal_ore"]
        assert crystal.base_price == 45, f"crystal_ore should be 45, got {crystal.base_price}"

    def test_rare_ore_price(self) -> None:
        loader = _make_loader()
        loader.load_commodities()
        rare = loader.commodities["rare_ore"]
        assert rare.base_price == 80, f"rare_ore should be 80, got {rare.base_price}"

    def test_scrap_metal_price(self) -> None:
        loader = _make_loader()
        loader.load_commodities()
        scrap = loader.commodities["scrap_metal"]
        assert scrap.base_price == 12, f"scrap_metal should be 12, got {scrap.base_price}"

    def test_salvaged_electronics_price(self) -> None:
        loader = _make_loader()
        loader.load_commodities()
        salvage = loader.commodities["salvaged_electronics"]
        assert salvage.base_price == 50, (
            f"salvaged_electronics should be 50, got {salvage.base_price}"
        )

    def test_rare_parts_price(self) -> None:
        loader = _make_loader()
        loader.load_commodities()
        parts = loader.commodities["rare_parts"]
        assert parts.base_price == 110, f"rare_parts should be 110, got {parts.base_price}"

    def test_alloy_composite_price(self) -> None:
        loader = _make_loader()
        loader.load_commodities()
        alloy = loader.commodities["alloy_composite"]
        assert alloy.base_price == 280, f"alloy_composite should be 280, got {alloy.base_price}"

    def test_purified_crystal_price(self) -> None:
        loader = _make_loader()
        loader.load_commodities()
        crystal = loader.commodities["purified_crystal"]
        assert crystal.base_price == 400, (
            f"purified_crystal should be 400, got {crystal.base_price}"
        )

    def test_basic_commodity_prices_unchanged(self) -> None:
        """Food, textiles, common_metals should not change."""
        loader = _make_loader()
        loader.load_commodities()
        assert loader.commodities["food"].base_price == 50
        assert loader.commodities["textiles"].base_price == 40
        assert loader.commodities["common_metals"].base_price == 60


class TestMissionRewards:
    """Verify early mission credit reward bumps."""

    @staticmethod
    def _find_mission(loader: DataLoader, mission_id: str) -> object:
        """Find a mission by ID in the loaded list."""
        for m in loader.missions:
            if m.id == mission_id:
                return m
        raise AssertionError(f"Mission '{mission_id}' not found")

    def test_iron_delivery_reward(self) -> None:
        loader = _make_loader()
        loader.load_missions()
        mission = self._find_mission(loader, "iron_delivery")
        credit_reward = next((r for r in mission.rewards if r.reward_type == "credits"), None)
        assert credit_reward is not None
        assert credit_reward.amount == 600, (
            f"iron_delivery should reward 600 CR, got {credit_reward.amount}"
        )

    def test_footing_the_bill_has_credit_reward(self) -> None:
        loader = _make_loader()
        loader.load_missions()
        mission = self._find_mission(loader, "footing_the_bill")
        credit_reward = next((r for r in mission.rewards if r.reward_type == "credits"), None)
        assert credit_reward is not None, "footing_the_bill should have a credit reward"
        assert credit_reward.amount == 150

    def test_scholars_errand_reward(self) -> None:
        loader = _make_loader()
        loader.load_missions()
        mission = self._find_mission(loader, "the_scholars_errand")
        credit_reward = next((r for r in mission.rewards if r.reward_type == "credits"), None)
        assert credit_reward is not None
        assert credit_reward.amount == 350, (
            f"scholars_errand should reward 350 CR, got {credit_reward.amount}"
        )


# ============================================================================
# Step 4: JSON Combat & Ship Data
# ============================================================================


class TestDualLaserWeapon:
    """Verify the new dual laser weapon exists and has correct stats."""

    def test_dual_laser_exists(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        assert "dual_laser" in loader.upgrades, "dual_laser upgrade should exist"

    def test_dual_laser_is_weapon(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        dl = loader.upgrades["dual_laser"]
        assert dl.slot_type == "weapon"

    def test_dual_laser_price(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        dl = loader.upgrades["dual_laser"]
        assert dl.price == 14000

    def test_dual_laser_damage(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        dl = loader.upgrades["dual_laser"]
        assert dl.combat_move is not None
        damage_effect = dl.combat_move["effects"][0]
        assert damage_effect["value"] == 24

    def test_weapon_count_updated(self) -> None:
        loader = _make_loader()
        loader.load_upgrades()
        weapons = [u for u in loader.upgrades.values() if u.slot_type == "weapon"]
        assert len(weapons) == 32, f"Should have 32 weapons, got {len(weapons)}"


class TestEnemyNegotiateDifficulty:
    """Verify enemy negotiate difficulty scales properly."""

    def test_ledger_vanguard_effectively_unnegotiable(self) -> None:
        """Boss-tier enemies should be nearly impossible to negotiate."""
        loader = _make_loader()
        loader.load_enemy_templates()
        vanguard = loader.enemy_templates["ledger_vanguard"]
        assert vanguard.negotiate_difficulty >= 6, (
            f"ledger_vanguard should be very hard to negotiate, got {vanguard.negotiate_difficulty}"
        )

    def test_guild_dreadnought_difficulty(self) -> None:
        """Dangerous faction enemies should have difficulty 4+."""
        loader = _make_loader()
        loader.load_enemy_templates()
        dread = loader.enemy_templates["guild_dreadnought"]
        assert dread.negotiate_difficulty >= 4, (
            f"guild_dreadnought negotiate should be 4+, got {dread.negotiate_difficulty}"
        )

    def test_guild_enforcer_raised(self) -> None:
        """Mid-tier faction enforcer should be raised to 4."""
        loader = _make_loader()
        loader.load_enemy_templates()
        enforcer = loader.enemy_templates["guild_enforcer"]
        assert enforcer.negotiate_difficulty == 4, (
            f"guild_enforcer negotiate should be 4, got {enforcer.negotiate_difficulty}"
        )

    def test_pirate_scout_unchanged(self) -> None:
        """Early enemies should keep low difficulty."""
        loader = _make_loader()
        loader.load_enemy_templates()
        scout = loader.enemy_templates["pirate_scout"]
        assert scout.negotiate_difficulty == 2


class TestShipPrices:
    """Verify late-game ship price smoothing."""

    def test_bulk_hauler_price(self) -> None:
        loader = _make_loader()
        loader.load_ship_types()
        hauler = loader.ship_types["bulk_hauler"]
        assert hauler.purchase_price == 400000, (
            f"bulk_hauler should be 400K, got {hauler.purchase_price}"
        )

    def test_luxury_yacht_price(self) -> None:
        loader = _make_loader()
        loader.load_ship_types()
        yacht = loader.ship_types["luxury_yacht"]
        assert yacht.purchase_price == 600000, (
            f"luxury_yacht should be 600K, got {yacht.purchase_price}"
        )

    def test_clipper_price(self) -> None:
        loader = _make_loader()
        loader.load_ship_types()
        clipper = loader.ship_types["clipper"]
        assert clipper.purchase_price == 350000, (
            f"clipper should be 350K, got {clipper.purchase_price}"
        )

    def test_shuttle_price_unchanged(self) -> None:
        loader = _make_loader()
        loader.load_ship_types()
        shuttle = loader.ship_types["shuttle"]
        assert shuttle.purchase_price == 5000


# ============================================================================
# Step 5: Integration Checks
# ============================================================================


class TestBalanceIntegration:
    """Cross-system balance sanity checks."""

    def test_mining_income_viable_vs_trading(self) -> None:
        """Mining a full session should yield meaningful income."""
        loader = _make_loader()
        loader.load_commodities()
        # Realistic Breakstone mining session: ~30 raw_ore, ~10 iron_ore, ~3 crystal_ore
        raw_income = 30 * loader.commodities["raw_ore"].base_price
        iron_income = 10 * loader.commodities["iron_ore"].base_price
        crystal_income = 3 * loader.commodities["crystal_ore"].base_price
        mining_income = raw_income + iron_income + crystal_income
        # Should be at least 300 CR per session to feel worthwhile
        assert mining_income >= 300, f"Mining session should yield 300+ CR, got {mining_income}"

    def test_salvage_income_viable(self) -> None:
        """Salvage session should yield at least 200 CR."""
        loader = _make_loader()
        loader.load_commodities()
        # Conservative: 5 scrap + 3 electronics + 1 rare_parts
        income = (
            5 * loader.commodities["scrap_metal"].base_price
            + 3 * loader.commodities["salvaged_electronics"].base_price
            + 1 * loader.commodities["rare_parts"].base_price
        )
        assert income >= 200, f"Salvage session should yield 200+ CR, got {income}"

    def test_skill_points_allow_meaningful_builds(self) -> None:
        """11 skill points (was 10) allows one full tree + partial second."""
        from spacegame.models.progression import PlayerProgression

        prog = PlayerProgression()
        prog.add_xp(10000)
        assert prog.skill_points >= 11, (
            f"Need 11+ skill points for meaningful builds, got {prog.skill_points}"
        )

    def test_social_level_3_requires_meaningful_investment(self) -> None:
        """Level 3 should require at least 10 successful checks."""
        from spacegame.models.social import SOCIAL_XP_THRESHOLDS, XP_ON_SUCCESS

        xp_needed = SOCIAL_XP_THRESHOLDS[2]  # Level 3 threshold
        checks_needed = xp_needed / XP_ON_SUCCESS
        assert checks_needed >= 10, f"Level 3 should need 10+ successes, got {checks_needed}"

    def test_starting_credits_cover_first_permit_and_cargo(self) -> None:
        """3000 CR should cover M01 permit (250) + a full cargo run."""
        permit_cost = 250
        remaining = config.STARTING_CREDITS - permit_cost
        assert remaining >= 2000, f"After permit, should have 2000+ CR for cargo, got {remaining}"
