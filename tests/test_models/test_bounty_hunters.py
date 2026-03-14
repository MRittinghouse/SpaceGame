"""Tests for bounty hunter encounter system (Phase D).

Covers bounty hunter spawning based on criminal heat, encounter building
with player choices (surrender/fight/negotiate/bribe), tier selection,
and heat-based encounter frequency.
"""

import pytest

from spacegame.models.smuggling import (
    BountyHunterTier,
    get_bounty_hunter_tier,
    should_trigger_bounty_hunter,
    calculate_bounty_hunter_chance,
    build_bounty_hunter_encounter,
    get_bounty_hunter_enemies,
    calculate_surrender_cost,
)


# ============================================================================
# Bounty Hunter Tier Selection
# ============================================================================


class TestBountyHunterTier:
    """Bounty hunter tier depends on criminal heat level."""

    def test_no_bounty_below_26(self) -> None:
        """Heat below 26 doesn't attract bounty hunters."""
        assert get_bounty_hunter_tier(0) is None
        assert get_bounty_hunter_tier(10) is None
        assert get_bounty_hunter_tier(25) is None

    def test_tier_1_at_26_to_50(self) -> None:
        """Heat 26-50 attracts freelance trackers (tier 1)."""
        assert get_bounty_hunter_tier(26) == BountyHunterTier.FREELANCE
        assert get_bounty_hunter_tier(40) == BountyHunterTier.FREELANCE
        assert get_bounty_hunter_tier(50) == BountyHunterTier.FREELANCE

    def test_tier_2_at_51_to_75(self) -> None:
        """Heat 51-75 attracts licensed hunters (tier 2)."""
        assert get_bounty_hunter_tier(51) == BountyHunterTier.LICENSED
        assert get_bounty_hunter_tier(65) == BountyHunterTier.LICENSED
        assert get_bounty_hunter_tier(75) == BountyHunterTier.LICENSED

    def test_tier_3_at_76_plus(self) -> None:
        """Heat 76-100 attracts elite/faction enforcers (tier 3)."""
        assert get_bounty_hunter_tier(76) == BountyHunterTier.ELITE
        assert get_bounty_hunter_tier(90) == BountyHunterTier.ELITE
        assert get_bounty_hunter_tier(100) == BountyHunterTier.ELITE


# ============================================================================
# Bounty Hunter Encounter Chance
# ============================================================================


class TestBountyHunterChance:
    """Bounty hunter encounter probability scales with heat."""

    def test_zero_chance_below_threshold(self) -> None:
        """No bounty hunters below heat 26."""
        chance = calculate_bounty_hunter_chance(criminal_heat=20)
        assert chance == 0.0

    def test_tier_1_base_chance(self) -> None:
        """Tier 1 has 5% base encounter chance per jump."""
        chance = calculate_bounty_hunter_chance(criminal_heat=30)
        assert chance == pytest.approx(0.05, abs=0.01)

    def test_tier_2_base_chance(self) -> None:
        """Tier 2 has 10% base encounter chance per jump."""
        chance = calculate_bounty_hunter_chance(criminal_heat=60)
        assert chance == pytest.approx(0.10, abs=0.01)

    def test_tier_3_base_chance(self) -> None:
        """Tier 3 has 15% base encounter chance per jump."""
        chance = calculate_bounty_hunter_chance(criminal_heat=80)
        assert chance == pytest.approx(0.15, abs=0.01)

    def test_signal_jammer_reduces_chance(self) -> None:
        """Signal jammer reduces bounty hunter chance by 3%."""
        base = calculate_bounty_hunter_chance(criminal_heat=60)
        jammed = calculate_bounty_hunter_chance(criminal_heat=60, has_signal_jammer=True)
        assert jammed == pytest.approx(base - 0.03, abs=0.01)

    def test_false_transponder_reduces_chance(self) -> None:
        """False transponder reduces bounty hunter chance by 5%."""
        base = calculate_bounty_hunter_chance(criminal_heat=60)
        masked = calculate_bounty_hunter_chance(criminal_heat=60, has_false_transponder=True)
        assert masked == pytest.approx(base - 0.05, abs=0.01)

    def test_chance_has_floor_of_1_percent(self) -> None:
        """Even with all modifiers, minimum 1% if tier is active."""
        chance = calculate_bounty_hunter_chance(
            criminal_heat=30,
            has_signal_jammer=True,
            has_false_transponder=True,
        )
        assert chance >= 0.01

    def test_crimson_reach_no_bounty_hunters(self) -> None:
        """Crimson Reach is a safe haven — no bounty hunters spawn there."""
        chance = calculate_bounty_hunter_chance(
            criminal_heat=90, system_id="crimson_reach"
        )
        assert chance == 0.0


# ============================================================================
# Bounty Hunter Trigger (Deterministic)
# ============================================================================


class TestBountyHunterTrigger:
    """Deterministic bounty hunter spawn check."""

    def test_deterministic_same_inputs(self) -> None:
        """Same inputs produce same result."""
        r1 = should_trigger_bounty_hunter(
            criminal_heat=60, game_day=10, system_id="nexus_prime"
        )
        r2 = should_trigger_bounty_hunter(
            criminal_heat=60, game_day=10, system_id="nexus_prime"
        )
        assert r1 == r2

    def test_different_day_may_differ(self) -> None:
        """Different days can produce different results."""
        results = set()
        for day in range(1, 100):
            r = should_trigger_bounty_hunter(
                criminal_heat=80, game_day=day, system_id="nexus_prime"
            )
            results.add(r)
        # With 15% chance over 99 days, we should see both True and False
        assert True in results
        assert False in results

    def test_no_trigger_at_low_heat(self) -> None:
        """Never triggers below heat 26."""
        for day in range(1, 100):
            assert should_trigger_bounty_hunter(
                criminal_heat=10, game_day=day, system_id="nexus_prime"
            ) is False


# ============================================================================
# Bounty Hunter Enemy Selection
# ============================================================================


class TestBountyHunterEnemies:
    """Enemy template selection by bounty hunter tier."""

    def test_tier_1_returns_1_enemy(self) -> None:
        """Freelance trackers come alone."""
        enemies = get_bounty_hunter_enemies(BountyHunterTier.FREELANCE, seed=42)
        assert len(enemies) == 1

    def test_tier_2_returns_1_or_2(self) -> None:
        """Licensed hunters bring 1-2 ships."""
        counts = set()
        for seed in range(100):
            enemies = get_bounty_hunter_enemies(BountyHunterTier.LICENSED, seed=seed)
            counts.add(len(enemies))
        assert counts.issubset({1, 2})
        assert 2 in counts  # Should sometimes bring a wingman

    def test_tier_3_returns_2_or_3(self) -> None:
        """Elite hunters bring 2-3 ships."""
        counts = set()
        for seed in range(100):
            enemies = get_bounty_hunter_enemies(BountyHunterTier.ELITE, seed=seed)
            counts.add(len(enemies))
        assert counts.issubset({2, 3})

    def test_tier_1_uses_tracker_templates(self) -> None:
        """Tier 1 pulls from tracker/enforcer pool."""
        enemies = get_bounty_hunter_enemies(BountyHunterTier.FREELANCE, seed=42)
        valid_ids = {"bounty_tracker", "bounty_enforcer"}
        for eid in enemies:
            assert eid in valid_ids

    def test_tier_3_uses_elite_templates(self) -> None:
        """Tier 3 can include elite enemies."""
        all_ids: set[str] = set()
        for seed in range(200):
            enemies = get_bounty_hunter_enemies(BountyHunterTier.ELITE, seed=seed)
            all_ids.update(enemies)
        # Elite pool should include at least vanguard or ace or faction_enforcer
        elite_ids = {"bounty_vanguard", "bounty_ace", "faction_enforcer"}
        assert len(all_ids & elite_ids) > 0


# ============================================================================
# Surrender Cost
# ============================================================================


class TestSurrenderCost:
    """Surrender cost scales with criminal heat."""

    def test_cost_scales_with_heat(self) -> None:
        """Surrender costs heat × 15 CR."""
        assert calculate_surrender_cost(30) == 450
        assert calculate_surrender_cost(60) == 900
        assert calculate_surrender_cost(100) == 1500

    def test_minimum_cost(self) -> None:
        """Minimum surrender cost is 200 CR."""
        assert calculate_surrender_cost(5) == 200


# ============================================================================
# Bounty Hunter Encounter Building
# ============================================================================


class TestBountyHunterEncounter:
    """build_bounty_hunter_encounter creates a pre-combat encounter."""

    def _build_tier1(self, player_credits: int = 5000) -> object:
        return build_bounty_hunter_encounter(
            tier=BountyHunterTier.FREELANCE,
            criminal_heat=35,
            player_credits=player_credits,
            persuasion_level=2,
            seed=42,
        )

    def _build_tier2(self, player_credits: int = 5000) -> object:
        return build_bounty_hunter_encounter(
            tier=BountyHunterTier.LICENSED,
            criminal_heat=60,
            player_credits=player_credits,
            persuasion_level=3,
            seed=42,
        )

    def _build_tier3(self) -> object:
        return build_bounty_hunter_encounter(
            tier=BountyHunterTier.ELITE,
            criminal_heat=85,
            player_credits=10000,
            persuasion_level=2,
            seed=42,
        )

    def test_encounter_has_fight_choice(self) -> None:
        """All bounty encounters have a Fight option."""
        enc = self._build_tier1()
        choice_ids = [c.id for c in enc.choices]
        assert "fight" in choice_ids

    def test_encounter_has_surrender_choice(self) -> None:
        """All bounty encounters have a Surrender option."""
        enc = self._build_tier1()
        choice_ids = [c.id for c in enc.choices]
        assert "surrender" in choice_ids

    def test_surrender_costs_credits(self) -> None:
        """Surrender choice deducts credits."""
        enc = self._build_tier1()
        surrender = next(c for c in enc.choices if c.id == "surrender")
        has_deduction = any(
            r.reward_type == "deduct_credits" for r in surrender.outcome.rewards
        )
        assert has_deduction is True

    def test_surrender_reduces_heat(self) -> None:
        """Surrender reduces criminal heat."""
        enc = self._build_tier1()
        surrender = next(c for c in enc.choices if c.id == "surrender")
        has_heat_reduction = any(
            r.reward_type == "reduce_criminal_heat" for r in surrender.outcome.rewards
        )
        assert has_heat_reduction is True

    def test_tier_1_has_bribe_option(self) -> None:
        """Freelance trackers can be bribed."""
        enc = self._build_tier1()
        choice_ids = [c.id for c in enc.choices]
        assert "bribe" in choice_ids

    def test_tier_2_no_bribe(self) -> None:
        """Licensed hunters cannot be bribed."""
        enc = self._build_tier2()
        choice_ids = [c.id for c in enc.choices]
        assert "bribe" not in choice_ids

    def test_tier_3_no_bribe(self) -> None:
        """Elite enforcers cannot be bribed."""
        enc = self._build_tier3()
        choice_ids = [c.id for c in enc.choices]
        assert "bribe" not in choice_ids

    def test_negotiate_available(self) -> None:
        """Negotiate option available at all tiers."""
        enc = self._build_tier1()
        choice_ids = [c.id for c in enc.choices]
        assert "negotiate" in choice_ids

    def test_negotiate_shows_skill_vs_difficulty(self) -> None:
        """Negotiate choice shows persuasion level vs difficulty."""
        enc = self._build_tier1()
        negotiate = next(c for c in enc.choices if c.id == "negotiate")
        # Description should mention level and difficulty
        assert "Lv" in negotiate.label or "vs" in negotiate.label

    def test_negotiate_difficulty_scales_with_tier(self) -> None:
        """Higher tiers have harder negotiate checks."""
        enc1 = self._build_tier1()
        enc3 = self._build_tier3()
        neg1 = next(c for c in enc1.choices if c.id == "negotiate")
        neg3 = next(c for c in enc3.choices if c.id == "negotiate")
        # Tier 3 description should mention higher difficulty
        assert neg1.description != neg3.description

    def test_fight_leads_to_combat_flag(self) -> None:
        """Fight choice outcome has start_combat flag."""
        enc = self._build_tier1()
        fight = next(c for c in enc.choices if c.id == "fight")
        has_combat = any(
            r.reward_type == "start_bounty_combat" for r in fight.outcome.rewards
        )
        assert has_combat is True

    def test_encounter_type_is_bounty_hunter(self) -> None:
        """Encounter type identifies it as a bounty hunter encounter."""
        enc = self._build_tier1()
        assert enc.encounter_type == "bounty_hunter"

    def test_insufficient_credits_no_surrender(self) -> None:
        """Surrender not available if player can't afford it."""
        enc = build_bounty_hunter_encounter(
            tier=BountyHunterTier.FREELANCE,
            criminal_heat=35,
            player_credits=10,  # Can't afford surrender cost
            persuasion_level=2,
            seed=42,
        )
        choice_ids = [c.id for c in enc.choices]
        assert "surrender" not in choice_ids

    def test_bribe_costs_less_than_surrender(self) -> None:
        """Bribe is cheaper than surrender but doesn't reduce heat."""
        enc = self._build_tier1(player_credits=5000)
        surrender = next(c for c in enc.choices if c.id == "surrender")
        bribe = next(c for c in enc.choices if c.id == "bribe")
        surrender_cost = next(
            r.amount for r in surrender.outcome.rewards if r.reward_type == "deduct_credits"
        )
        bribe_cost = next(
            r.amount for r in bribe.outcome.rewards if r.reward_type == "deduct_credits"
        )
        assert bribe_cost < surrender_cost

    def test_bribe_does_not_reduce_heat(self) -> None:
        """Bribing a tracker doesn't reduce criminal heat."""
        enc = self._build_tier1()
        bribe = next(c for c in enc.choices if c.id == "bribe")
        has_heat_reduction = any(
            r.reward_type == "reduce_criminal_heat" for r in bribe.outcome.rewards
        )
        assert has_heat_reduction is False

    def test_tier_descriptions_vary(self) -> None:
        """Different tiers have different encounter descriptions."""
        enc1 = self._build_tier1()
        enc2 = self._build_tier2()
        enc3 = self._build_tier3()
        # Names should differ
        assert enc1.name != enc3.name

    def test_negotiate_success_grants_immunity(self) -> None:
        """Successful negotiate grants temporary bounty immunity."""
        enc = build_bounty_hunter_encounter(
            tier=BountyHunterTier.FREELANCE,
            criminal_heat=35,
            player_credits=5000,
            persuasion_level=5,  # High enough to succeed
            seed=42,
        )
        negotiate = next(c for c in enc.choices if c.id == "negotiate")
        has_immunity = any(
            r.reward_type == "bounty_immunity" for r in negotiate.outcome.rewards
        )
        assert has_immunity is True
