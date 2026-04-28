"""Tests for new achievements (R11 gap-filling)."""

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Stat keys that map to direct Player fields or computed stats
VALID_STAT_KEYS = {
    "trades_completed",
    "credits_earned_lifetime",
    "credits_spent_lifetime",
    "largest_single_profit",
    "jumps_traveled",
    "fuel_consumed",
    "ore_mined",
    "items_salvaged",
    "items_refined",
    "level",
    "systems_discovered",
    "max_mining_depth",
    "total_chains_triggered",
    "rare_ores_mined",
    "salvage_sessions_completed",
    "corrupted_items_extracted",
    "refining_jobs_completed",
    "batch_jobs_queued",
    "unique_recipes_crafted",
    "investments_owned",
    "s_ranks_earned",
    "ground_missions_completed",
    "ground_undetected_completions",
    "ground_enemies_defeated",
    "ground_enemies_talked",
    "ground_tiles_explored",
    "ground_campaign_missions_completed",
    "goods_smuggled",
    "max_criminal_heat_reached",
    "inspections_passed_with_contraband",
    # New stat keys from Batch 1
    "combats_won",
    "combats_fled",
    "combats_negotiated",
    "combats_bribed",
    "side_missions_completed",
    "crew_quests_completed",
    "encounters_survived",
    # SA-B2: auction stub stat_keys (resolved via Player @property)
    "auction_lots_won_total",
    "auction_lots_won_stellaris",
    "auction_rivals_retired",
    "auction_perfect_reads",
}

VALID_REWARD_TYPES = {"xp", "credits", "skill_point"}


def _load_achievements() -> list[dict]:
    with open(DATA_DIR / "progression" / "achievements.json", "r", encoding="utf-8") as f:
        return json.load(f)["achievements"]


class TestAchievementCount:
    """Test overall achievement data."""

    def test_total_achievement_count(self) -> None:
        achievements = _load_achievements()
        assert len(achievements) >= 62, f"Expected >= 62 achievements, got {len(achievements)}"

    def test_no_duplicate_ids(self) -> None:
        achievements = _load_achievements()
        ids = [a["id"] for a in achievements]
        assert len(ids) == len(set(ids)), "Duplicate achievement IDs found"


class TestAchievementCategories:
    """Test that expected categories exist."""

    def test_combat_category_exists(self) -> None:
        achievements = _load_achievements()
        combat = [a for a in achievements if a["category"] == "combat"]
        assert len(combat) >= 5, f"Expected >= 5 combat achievements, got {len(combat)}"

    def test_side_quest_category_exists(self) -> None:
        achievements = _load_achievements()
        side = [a for a in achievements if a["category"] == "side_quest"]
        assert len(side) >= 3, f"Expected >= 3 side_quest achievements, got {len(side)}"

    def test_smuggling_expanded(self) -> None:
        achievements = _load_achievements()
        smuggling = [a for a in achievements if a["category"] == "smuggling"]
        assert len(smuggling) >= 5, f"Expected >= 5 smuggling achievements, got {len(smuggling)}"


class TestAchievementValidity:
    """Test achievement data integrity."""

    def test_stat_keys_are_valid(self) -> None:
        achievements = _load_achievements()
        for a in achievements:
            assert a["stat_key"] in VALID_STAT_KEYS, (
                f"Achievement {a['id']} has invalid stat_key: {a['stat_key']}"
            )

    def test_reward_types_are_valid(self) -> None:
        achievements = _load_achievements()
        for a in achievements:
            assert a["reward_type"] in VALID_REWARD_TYPES, (
                f"Achievement {a['id']} has invalid reward_type: {a['reward_type']}"
            )

    def test_thresholds_are_positive(self) -> None:
        achievements = _load_achievements()
        for a in achievements:
            assert a["threshold"] > 0, (
                f"Achievement {a['id']} has non-positive threshold: {a['threshold']}"
            )

    def test_hidden_achievements_exist(self) -> None:
        achievements = _load_achievements()
        hidden = [a for a in achievements if a.get("hidden", False)]
        assert len(hidden) >= 3, f"Expected >= 3 hidden achievements, got {len(hidden)}"


class TestNewAchievements:
    """Test specific new achievements."""

    def test_first_combat_win_exists(self) -> None:
        achievements = _load_achievements()
        ids = {a["id"] for a in achievements}
        assert "first_combat_win" in ids

    def test_first_side_quest_exists(self) -> None:
        achievements = _load_achievements()
        ids = {a["id"] for a in achievements}
        assert "first_side_quest" in ids

    def test_encounter_survivor_exists(self) -> None:
        achievements = _load_achievements()
        ids = {a["id"] for a in achievements}
        assert "encounter_survivor" in ids

    def test_level_15_and_20_exist(self) -> None:
        achievements = _load_achievements()
        ids = {a["id"] for a in achievements}
        assert "level_15" in ids
        assert "level_20" in ids
