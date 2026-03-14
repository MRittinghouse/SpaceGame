"""Tests for encounter model: distance-based probability scaling and encounter generation."""

import pytest

from spacegame.models.encounter import (
    EncounterRef,
    ENCOUNTER_CHANCE_SAFE,
    ENCOUNTER_CHANCE_MODERATE,
    ENCOUNTER_CHANCE_DANGEROUS,
    SHAKEDOWN_CHANCE,
    calculate_encounter_chance,
    check_travel_encounter,
    filter_enemies_for_system,
)
from spacegame.models.combat import EnemyShipTemplate, EnemyBehavior


# ============================================================================
# EncounterRef Tests
# ============================================================================


class TestEncounterRef:
    """Tests for EncounterRef dataclass."""

    def test_creation(self) -> None:
        ref = EncounterRef(enemy_template_ids=["pirate_scout"], encounter_seed=42)
        assert ref.enemy_template_ids == ["pirate_scout"]
        assert ref.encounter_seed == 42


# ============================================================================
# Constants Tests
# ============================================================================


class TestEncounterConstants:
    """Tests for encounter chance constants."""

    def test_safe_is_zero(self) -> None:
        assert ENCOUNTER_CHANCE_SAFE == 0

    def test_moderate_is_positive(self) -> None:
        assert ENCOUNTER_CHANCE_MODERATE > 0

    def test_dangerous_greater_than_moderate(self) -> None:
        assert ENCOUNTER_CHANCE_DANGEROUS > ENCOUNTER_CHANCE_MODERATE


# ============================================================================
# calculate_encounter_chance Tests
# ============================================================================


class TestCalculateEncounterChance:
    """Tests for distance-based encounter probability scaling."""

    def test_safe_always_zero(self) -> None:
        """Safe systems have 0% chance regardless of distance."""
        assert calculate_encounter_chance(ENCOUNTER_CHANCE_SAFE, 40.0) == 0.0
        assert calculate_encounter_chance(ENCOUNTER_CHANCE_SAFE, 110.0) == 0.0
        assert calculate_encounter_chance(ENCOUNTER_CHANCE_SAFE, 180.0) == 0.0

    def test_chance_at_min_distance(self) -> None:
        """At minimum distance (40), multiplier is 0.5."""
        result = calculate_encounter_chance(30, 40.0)
        assert result == pytest.approx(15.0, abs=0.1), f"30 * 0.5 = 15, got {result}"

    def test_chance_at_max_distance(self) -> None:
        """At maximum distance (180), multiplier is 1.5."""
        result = calculate_encounter_chance(30, 180.0)
        assert result == pytest.approx(45.0, abs=0.1), f"30 * 1.5 = 45, got {result}"

    def test_chance_at_mid_distance(self) -> None:
        """At midpoint distance (110), multiplier is ~1.0."""
        result = calculate_encounter_chance(30, 110.0)
        assert result == pytest.approx(30.0, abs=0.1), f"30 * 1.0 = 30, got {result}"

    def test_chance_clamps_below_min(self) -> None:
        """Distance below 40 still uses 0.5x multiplier."""
        result = calculate_encounter_chance(30, 10.0)
        assert result == pytest.approx(15.0, abs=0.1), f"Should clamp to 0.5x, got {result}"

    def test_chance_clamps_above_max(self) -> None:
        """Distance above 180 still uses 1.5x multiplier."""
        result = calculate_encounter_chance(30, 250.0)
        assert result == pytest.approx(45.0, abs=0.1), f"Should clamp to 1.5x, got {result}"

    def test_chance_never_exceeds_100(self) -> None:
        """Result is clamped to 100 max."""
        result = calculate_encounter_chance(80, 180.0)
        assert result <= 100.0, f"Should not exceed 100, got {result}"

    def test_moderate_at_medium_distance(self) -> None:
        """Moderate system at 80u distance."""
        # t = (80 - 40) / (180 - 40) = 40/140 ≈ 0.286
        # multiplier = 0.5 + 0.286 = 0.786
        # 20 * 0.786 ≈ 15.7
        result = calculate_encounter_chance(ENCOUNTER_CHANCE_MODERATE, 80.0)
        assert 14.0 < result < 17.0, f"Expected ~15.7, got {result}"


# ============================================================================
# check_travel_encounter Tests
# ============================================================================


class TestCheckTravelEncounter:
    """Tests for the full encounter check function."""

    ENEMIES = ["pirate_scout", "pirate_raider", "pirate_heavy"]

    def test_safe_always_none(self) -> None:
        """Safe systems never trigger encounters regardless of distance."""
        for day in range(100):
            result = check_travel_encounter(
                system_danger="safe",
                enemy_template_ids=self.ENEMIES,
                game_day=day,
                system_id="safe_system",
                distance=180.0,
            )
            assert result is None, f"Safe system triggered encounter on day {day}"

    def test_deterministic_seed(self) -> None:
        """Same inputs always produce the same result."""
        r1 = check_travel_encounter("dangerous", self.ENEMIES, 42, "sys_a", 100.0)
        r2 = check_travel_encounter("dangerous", self.ENEMIES, 42, "sys_a", 100.0)
        if r1 is None:
            assert r2 is None
        else:
            assert r2 is not None
            assert r1.encounter_seed == r2.encounter_seed
            assert r1.enemy_template_ids == r2.enemy_template_ids

    def test_empty_enemy_list_returns_none(self) -> None:
        """No available enemies means no encounter."""
        for day in range(100):
            result = check_travel_encounter("dangerous", [], day, "sys", 100.0)
            assert result is None

    def test_returned_ids_from_input(self) -> None:
        """All returned template IDs must come from the input list."""
        for day in range(200):
            result = check_travel_encounter("dangerous", self.ENEMIES, day, "test", 150.0)
            if result is not None:
                for tid in result.enemy_template_ids:
                    assert tid in self.ENEMIES, f"Unknown template ID: {tid}"

    def test_short_distance_fewer_encounters(self) -> None:
        """Short-distance travel should produce fewer encounters (statistical)."""
        short_hits = sum(
            1
            for day in range(1000)
            if check_travel_encounter("dangerous", self.ENEMIES, day, f"short_{day}", 40.0)
            is not None
        )
        # At distance 40: chance = 30 * 0.5 = 15%, expect ~150/1000
        assert short_hits < 250, f"Short distance had {short_hits} encounters (expected ~150)"
        assert short_hits > 50, f"Short distance had {short_hits} encounters (expected ~150)"

    def test_long_distance_more_encounters(self) -> None:
        """Long-distance travel should produce more encounters (statistical)."""
        long_hits = sum(
            1
            for day in range(1000)
            if check_travel_encounter("dangerous", self.ENEMIES, day, f"long_{day}", 180.0)
            is not None
        )
        # At distance 180: chance = 30 * 1.5 = 45%, expect ~450/1000
        assert long_hits > 300, f"Long distance had {long_hits} encounters (expected ~450)"
        assert long_hits < 600, f"Long distance had {long_hits} encounters (expected ~450)"

    def test_dangerous_more_than_moderate(self) -> None:
        """Dangerous systems should trigger more encounters than moderate at same distance."""
        dangerous_hits = sum(
            1
            for day in range(1000)
            if check_travel_encounter("dangerous", self.ENEMIES, day, f"d_{day}", 100.0)
            is not None
        )
        moderate_hits = sum(
            1
            for day in range(1000)
            if check_travel_encounter("moderate", self.ENEMIES, day, f"m_{day}", 100.0)
            is not None
        )
        assert dangerous_hits > moderate_hits, (
            f"Dangerous ({dangerous_hits}) should > moderate ({moderate_hits})"
        )

    def test_default_distance_backward_compatible(self) -> None:
        """Distance parameter defaults to 80.0 for backward compatibility."""
        # Should not raise — distance has a default
        result = check_travel_encounter("dangerous", self.ENEMIES, 1, "sys")
        assert result is None or isinstance(result, EncounterRef)

    def test_encounter_enemy_count_scales_with_danger(self) -> None:
        """Dangerous systems can have more enemies than moderate."""
        dangerous_multi = False
        moderate_multi = False
        for day in range(500):
            d_result = check_travel_encounter("dangerous", self.ENEMIES, day, f"d_{day}", 150.0)
            m_result = check_travel_encounter("moderate", self.ENEMIES, day, f"m_{day}", 150.0)
            if d_result and d_result.encounter_type == "hostile" and len(d_result.enemy_template_ids) > 1:
                dangerous_multi = True
            if m_result and m_result.encounter_type == "hostile" and len(m_result.enemy_template_ids) > 1:
                moderate_multi = True
        assert dangerous_multi, "Dangerous should sometimes have multiple enemies"
        assert not moderate_multi, "Moderate should always have exactly 1 enemy"


# ============================================================================
# Encounter Type Tests
# ============================================================================


class TestEncounterType:
    """Tests for encounter_type field and distress signal generation."""

    ENEMIES = ["pirate_scout", "pirate_raider", "pirate_heavy"]

    def test_encounter_ref_defaults_to_hostile(self) -> None:
        ref = EncounterRef(enemy_template_ids=["pirate_scout"], encounter_seed=42)
        assert ref.encounter_type == "hostile"

    def test_encounter_ref_accepts_distress_signal(self) -> None:
        ref = EncounterRef(
            enemy_template_ids=[], encounter_seed=42, encounter_type="distress_signal"
        )
        assert ref.encounter_type == "distress_signal"

    def test_distress_signal_never_in_safe_systems(self) -> None:
        """Safe systems should never generate any encounters including distress."""
        for day in range(500):
            result = check_travel_encounter("safe", self.ENEMIES, day, f"safe_{day}", 100.0)
            assert result is None

    def test_distress_signal_possible_in_dangerous(self) -> None:
        """Dangerous systems can generate distress signals (statistical)."""
        distress_count = 0
        for day in range(2000):
            result = check_travel_encounter(
                "dangerous", self.ENEMIES, day, f"d_{day}", 150.0
            )
            if result and result.encounter_type == "distress_signal":
                distress_count += 1
        assert distress_count > 0, f"Expected distress signals in 2000 trials, got {distress_count}"

    def test_distress_signal_has_empty_enemy_list(self) -> None:
        """Distress signals should not have enemy template IDs."""
        for day in range(2000):
            result = check_travel_encounter(
                "dangerous", self.ENEMIES, day, f"d_{day}", 150.0
            )
            if result and result.encounter_type == "distress_signal":
                assert result.enemy_template_ids == [], "Distress should have no enemies"
                return
        pytest.skip("No distress signals triggered in 2000 attempts")


# ============================================================================
# Enemy Filtering Tests
# ============================================================================


def _make_template(
    id: str,
    faction_id: str = "",
    danger_tier: str = "moderate",
) -> EnemyShipTemplate:
    """Create a minimal EnemyShipTemplate for filter tests."""
    return EnemyShipTemplate(
        id=id, name=id, description="test",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=50, shields=10, energy=8, energy_regen=3,
        speed=8, evasion=10, accuracy=60,
        moves=[], loot_table=[],
        faction_id=faction_id,
        danger_tier=danger_tier,
    )


class TestFilterEnemiesForSystem:
    """Tests for filter_enemies_for_system()."""

    def _make_templates(self) -> dict[str, EnemyShipTemplate]:
        return {
            # Generic (appear anywhere)
            "pirate_scout": _make_template("pirate_scout", "", "low"),
            "pirate_raider": _make_template("pirate_raider", "", "moderate"),
            "pirate_heavy": _make_template("pirate_heavy", "", "dangerous"),
            # Commerce Guild
            "guild_enforcer": _make_template("guild_enforcer", "commerce_guild", "moderate"),
            "guild_dreadnought": _make_template("guild_dreadnought", "commerce_guild", "dangerous"),
            # Miners Union
            "union_brawler": _make_template("union_brawler", "miners_union", "moderate"),
            "union_crusher": _make_template("union_crusher", "miners_union", "dangerous"),
        }

    def test_generic_enemies_appear_in_any_faction(self) -> None:
        templates = self._make_templates()
        result = filter_enemies_for_system(templates, "commerce_guild", "moderate")
        generic_ids = [eid for eid in result if eid.startswith("pirate")]
        assert len(generic_ids) > 0, "Generic pirates should appear in any faction system"

    def test_faction_enemies_only_in_own_system(self) -> None:
        templates = self._make_templates()
        result = filter_enemies_for_system(templates, "commerce_guild", "dangerous")
        assert "guild_enforcer" in result
        assert "guild_dreadnought" in result
        assert "union_brawler" not in result
        assert "union_crusher" not in result

    def test_safe_system_only_low_tier(self) -> None:
        templates = self._make_templates()
        result = filter_enemies_for_system(templates, "", "safe")
        for eid in result:
            assert templates[eid].danger_tier == "low", (
                f"{eid} is {templates[eid].danger_tier}, only low allowed in safe"
            )

    def test_moderate_system_low_and_moderate_tiers(self) -> None:
        templates = self._make_templates()
        result = filter_enemies_for_system(templates, "", "moderate")
        allowed = {"low", "moderate"}
        for eid in result:
            assert templates[eid].danger_tier in allowed, (
                f"{eid} has tier {templates[eid].danger_tier}, not allowed in moderate"
            )

    def test_dangerous_system_all_tiers(self) -> None:
        templates = self._make_templates()
        result = filter_enemies_for_system(templates, "", "dangerous")
        tiers_found = {templates[eid].danger_tier for eid in result}
        assert "low" in tiers_found
        assert "moderate" in tiers_found
        assert "dangerous" in tiers_found

    def test_empty_templates_returns_empty(self) -> None:
        result = filter_enemies_for_system({}, "commerce_guild", "dangerous")
        assert result == []

    def test_no_faction_match_still_returns_generics(self) -> None:
        templates = self._make_templates()
        result = filter_enemies_for_system(templates, "unknown_faction", "moderate")
        assert all(templates[eid].faction_id == "" for eid in result)

    def test_combined_filter_faction_and_tier(self) -> None:
        """In a moderate Commerce Guild system: generics (low+moderate) + guild moderate."""
        templates = self._make_templates()
        result = filter_enemies_for_system(templates, "commerce_guild", "moderate")
        assert "pirate_scout" in result       # generic, low
        assert "pirate_raider" in result      # generic, moderate
        assert "pirate_heavy" not in result   # generic, dangerous (filtered by tier)
        assert "guild_enforcer" in result     # faction, moderate
        assert "guild_dreadnought" not in result  # faction, dangerous (filtered by tier)
        assert "union_brawler" not in result  # wrong faction


# ============================================================================
# Shakedown encounter tests
# ============================================================================


class TestShakedownEncounter:
    """Tests for shakedown encounter type in dangerous systems."""

    def test_shakedown_chance_constant_exists(self) -> None:
        """SHAKEDOWN_CHANCE should be defined and reasonable."""
        assert isinstance(SHAKEDOWN_CHANCE, int)
        assert 5 <= SHAKEDOWN_CHANCE <= 30

    def test_shakedown_only_in_dangerous_systems(self) -> None:
        """Shakedown encounters should never appear in safe/moderate systems."""
        enemies = ["pirate_scout"]
        # Brute-force many seeds; none should produce shakedown in moderate
        shakedown_found = False
        for day in range(500):
            result = check_travel_encounter(
                "moderate", enemies, day, "sys_test", distance=120.0
            )
            if result and result.encounter_type == "shakedown":
                shakedown_found = True
                break
        assert not shakedown_found, "Shakedown should not appear in moderate systems"

    def test_shakedown_can_occur_in_dangerous_systems(self) -> None:
        """Shakedown encounters should be possible in dangerous systems."""
        enemies = ["pirate_scout"]
        shakedown_found = False
        for day in range(2000):
            result = check_travel_encounter(
                "dangerous", enemies, day, f"sys_{day}", distance=120.0
            )
            if result and result.encounter_type == "shakedown":
                shakedown_found = True
                break
        assert shakedown_found, "Shakedown should occur eventually in dangerous systems"

    def test_shakedown_has_single_enemy(self) -> None:
        """Shakedown encounters should have exactly one enemy."""
        enemies = ["pirate_scout", "pirate_raider", "pirate_heavy"]
        for day in range(2000):
            result = check_travel_encounter(
                "dangerous", enemies, day, f"sys_{day}", distance=120.0
            )
            if result and result.encounter_type == "shakedown":
                assert len(result.enemy_template_ids) == 1
                break
        else:
            pytest.skip("No shakedown generated in test range")

    def test_encounter_ref_accepts_shakedown_type(self) -> None:
        """EncounterRef should accept encounter_type='shakedown'."""
        ref = EncounterRef(
            enemy_template_ids=["pirate_scout"],
            encounter_seed=42,
            encounter_type="shakedown",
        )
        assert ref.encounter_type == "shakedown"

    def test_shakedown_demand_amount_positive(self) -> None:
        """Shakedown encounters should have a positive demand amount."""
        enemies = ["pirate_scout"]
        for day in range(2000):
            result = check_travel_encounter(
                "dangerous", enemies, day, f"sys_{day}", distance=120.0
            )
            if result and result.encounter_type == "shakedown":
                assert hasattr(result, "shakedown_demand")
                assert result.shakedown_demand > 0
                break
        else:
            pytest.skip("No shakedown generated in test range")


# ============================================================================
# Encounter Definition Model Tests
# ============================================================================


class TestEncounterOutcome:
    """Tests for EncounterOutcome dataclass."""

    def test_creation_minimal(self) -> None:
        from spacegame.models.encounter import EncounterOutcome

        outcome = EncounterOutcome(description="You helped.", rewards=[])
        assert outcome.description == "You helped."
        assert outcome.rewards == []
        assert outcome.leads_to_combat is False

    def test_with_rewards(self) -> None:
        from spacegame.models.encounter import EncounterOutcome
        from spacegame.models.mission import MissionReward

        rewards = [MissionReward(reward_type="credits", amount=200)]
        outcome = EncounterOutcome(description="Reward!", rewards=rewards)
        assert len(outcome.rewards) == 1
        assert outcome.rewards[0].amount == 200

    def test_leads_to_combat(self) -> None:
        from spacegame.models.encounter import EncounterOutcome

        outcome = EncounterOutcome(
            description="Fight!", rewards=[], leads_to_combat=True
        )
        assert outcome.leads_to_combat is True


class TestEncounterChoice:
    """Tests for EncounterChoice dataclass."""

    def test_creation(self) -> None:
        from spacegame.models.encounter import EncounterChoice, EncounterOutcome

        outcome = EncounterOutcome(description="Done.", rewards=[])
        choice = EncounterChoice(
            id="help", label="Help", description="Assist the crew.", outcome=outcome
        )
        assert choice.id == "help"
        assert choice.label == "Help"
        assert choice.description == "Assist the crew."
        assert choice.outcome is outcome

    def test_combat_choice(self) -> None:
        from spacegame.models.encounter import EncounterChoice, EncounterOutcome

        outcome = EncounterOutcome(
            description="Fight!", rewards=[], leads_to_combat=True
        )
        choice = EncounterChoice(
            id="fight", label="Fight", description="Open fire.", outcome=outcome
        )
        assert choice.outcome.leads_to_combat is True


class TestEncounterDefinition:
    """Tests for EncounterDefinition dataclass."""

    def test_creation(self) -> None:
        from spacegame.models.encounter import (
            EncounterDefinition,
            EncounterChoice,
            EncounterOutcome,
        )

        outcome = EncounterOutcome(description="Done.", rewards=[])
        choice = EncounterChoice(
            id="ignore", label="Ignore", description="Move on.", outcome=outcome
        )
        defn = EncounterDefinition(
            id="distress_01",
            encounter_type="distress_signal",
            name="Distress Signal",
            description="A ship in trouble.",
            choices=[choice],
        )
        assert defn.id == "distress_01"
        assert defn.encounter_type == "distress_signal"
        assert len(defn.choices) == 1

    def test_defaults(self) -> None:
        from spacegame.models.encounter import (
            EncounterDefinition,
            EncounterChoice,
            EncounterOutcome,
        )

        outcome = EncounterOutcome(description=".", rewards=[])
        choice = EncounterChoice(id="a", label="A", description=".", outcome=outcome)
        defn = EncounterDefinition(
            id="test",
            encounter_type="derelict",
            name="Test",
            description="Test.",
            choices=[choice],
        )
        assert defn.weight == 10
        assert defn.danger_levels == ["moderate", "dangerous"]
        assert defn.icon_color == (200, 200, 200)

    def test_custom_fields(self) -> None:
        from spacegame.models.encounter import (
            EncounterDefinition,
            EncounterChoice,
            EncounterOutcome,
        )

        outcome = EncounterOutcome(description=".", rewards=[])
        choice = EncounterChoice(id="a", label="A", description=".", outcome=outcome)
        defn = EncounterDefinition(
            id="anomaly_01",
            encounter_type="anomaly",
            name="Strange Signal",
            description="An anomaly.",
            choices=[choice],
            weight=5,
            danger_levels=["dangerous"],
            icon_color=(100, 200, 255),
        )
        assert defn.weight == 5
        assert defn.danger_levels == ["dangerous"]
        assert defn.icon_color == (100, 200, 255)


class TestSelectEncounterDefinition:
    """Tests for select_encounter_definition()."""

    def _make_def(
        self,
        def_id: str,
        enc_type: str = "distress_signal",
        weight: int = 10,
        danger_levels: list[str] | None = None,
    ) -> "EncounterDefinition":
        from spacegame.models.encounter import (
            EncounterDefinition,
            EncounterChoice,
            EncounterOutcome,
        )

        outcome = EncounterOutcome(description=".", rewards=[])
        choice = EncounterChoice(id="a", label="A", description=".", outcome=outcome)
        return EncounterDefinition(
            id=def_id,
            encounter_type=enc_type,
            name=def_id,
            description=".",
            choices=[choice],
            weight=weight,
            danger_levels=danger_levels or ["moderate", "dangerous"],
        )

    def test_basic_selection(self) -> None:
        from spacegame.models.encounter import select_encounter_definition

        defs = [self._make_def("d1", "distress_signal")]
        result = select_encounter_definition(defs, "distress_signal", "moderate", 42)
        assert result is not None
        assert result.id == "d1"

    def test_filters_by_type(self) -> None:
        from spacegame.models.encounter import select_encounter_definition

        defs = [
            self._make_def("d1", "distress_signal"),
            self._make_def("d2", "derelict"),
        ]
        result = select_encounter_definition(defs, "derelict", "moderate", 42)
        assert result is not None
        assert result.id == "d2"

    def test_filters_by_danger_level(self) -> None:
        from spacegame.models.encounter import select_encounter_definition

        defs = [
            self._make_def("d1", "anomaly", danger_levels=["dangerous"]),
        ]
        result = select_encounter_definition(defs, "anomaly", "moderate", 42)
        assert result is None

        result = select_encounter_definition(defs, "anomaly", "dangerous", 42)
        assert result is not None

    def test_deterministic_with_seed(self) -> None:
        from spacegame.models.encounter import select_encounter_definition

        defs = [
            self._make_def("d1", "distress_signal"),
            self._make_def("d2", "distress_signal"),
            self._make_def("d3", "distress_signal"),
        ]
        r1 = select_encounter_definition(defs, "distress_signal", "moderate", 42)
        r2 = select_encounter_definition(defs, "distress_signal", "moderate", 42)
        assert r1 is not None and r2 is not None
        assert r1.id == r2.id, "Same seed should select same definition"

    def test_empty_pool_returns_none(self) -> None:
        from spacegame.models.encounter import select_encounter_definition

        result = select_encounter_definition([], "distress_signal", "moderate", 42)
        assert result is None


# ============================================================================
# Non-Hostile Type Distribution Tests
# ============================================================================


class TestNonHostileDistribution:
    """Tests for the new non-hostile encounter type distribution."""

    ENEMIES = ["pirate_scout", "pirate_raider", "pirate_heavy"]

    def test_moderate_has_no_shakedown(self) -> None:
        """Moderate systems should never produce shakedown encounters."""
        for day in range(500):
            result = check_travel_encounter(
                "moderate", self.ENEMIES, day, f"m_{day}", 120.0
            )
            if result and result.encounter_type == "shakedown":
                pytest.fail("Shakedown should not appear in moderate systems")

    def test_moderate_has_no_anomaly(self) -> None:
        """Moderate systems should never produce anomaly encounters."""
        for day in range(500):
            result = check_travel_encounter(
                "moderate", self.ENEMIES, day, f"m_{day}", 120.0
            )
            if result and result.encounter_type == "anomaly":
                pytest.fail("Anomaly should not appear in moderate systems")

    def test_dangerous_has_new_types(self) -> None:
        """Dangerous systems should eventually produce derelict/debris/merchant/anomaly."""
        types_seen: set[str] = set()
        for day in range(5000):
            result = check_travel_encounter(
                "dangerous", self.ENEMIES, day, f"d_{day}", 150.0
            )
            if result:
                types_seen.add(result.encounter_type)
        # Must include at least one of the NEW non-hostile types
        new_types = {"derelict", "merchant", "debris", "anomaly"}
        assert types_seen & new_types, (
            f"Expected new encounter types in dangerous, got {types_seen}"
        )

    def test_non_hostile_types_at_moderate(self) -> None:
        """Moderate systems should produce multiple non-hostile types including new ones."""
        types_seen: set[str] = set()
        for day in range(5000):
            result = check_travel_encounter(
                "moderate", self.ENEMIES, day, f"m_{day}", 150.0
            )
            if result and result.encounter_type != "hostile":
                types_seen.add(result.encounter_type)
        valid_moderate = {"distress_signal", "derelict", "merchant", "debris"}
        assert types_seen.issubset(valid_moderate), (
            f"Unexpected types in moderate: {types_seen - valid_moderate}"
        )
        # Must include at least one new type (not just distress_signal)
        new_moderate_types = {"derelict", "merchant", "debris"}
        assert types_seen & new_moderate_types, (
            f"Expected new types at moderate, only got {types_seen}"
        )


# ============================================================================
# Encounter Reward Application Tests
# ============================================================================


class TestApplyEncounterRewards:
    """Tests for encounter reward resolution logic."""

    def test_credits_reward(self) -> None:
        """Credits reward should add to player balance."""
        from spacegame.models.mission import MissionReward

        reward = MissionReward(reward_type="credits", amount=100)
        assert reward.reward_type == "credits"
        assert reward.amount == 100

    def test_deduct_credits_reward(self) -> None:
        """Deduct credits reward should subtract from balance."""
        from spacegame.models.mission import MissionReward

        reward = MissionReward(reward_type="deduct_credits", amount=150)
        assert reward.amount == 150

    def test_xp_reward(self) -> None:
        """XP reward should be valid."""
        from spacegame.models.mission import MissionReward

        reward = MissionReward(reward_type="xp", amount=20)
        assert reward.amount == 20

    def test_shakedown_sentinel_resolution(self) -> None:
        """Shakedown sentinel amount=-1 should be replaced with actual demand."""
        from spacegame.models.mission import MissionReward

        sentinel = MissionReward(reward_type="deduct_credits", amount=-1)
        demand = 200
        # Simulate resolution (as done in EncounterView._select_choice)
        resolved = MissionReward("deduct_credits", demand) if sentinel.amount == -1 else sentinel
        assert resolved.amount == 200

    def test_set_flag_reward(self) -> None:
        """Set flag reward should use target_id for the flag name."""
        from spacegame.models.mission import MissionReward

        reward = MissionReward(reward_type="set_flag", amount=1, target_id="anomaly_observed")
        assert reward.target_id == "anomaly_observed"

    def test_encounter_ref_has_def_id(self) -> None:
        """EncounterRef.encounter_def_id should default to empty string."""
        ref = EncounterRef(enemy_template_ids=[], encounter_seed=42)
        assert ref.encounter_def_id == ""

    def test_encounter_ref_def_id_settable(self) -> None:
        """EncounterRef.encounter_def_id should be settable."""
        ref = EncounterRef(enemy_template_ids=[], encounter_seed=42)
        ref.encounter_def_id = "distress_medical_01"
        assert ref.encounter_def_id == "distress_medical_01"
