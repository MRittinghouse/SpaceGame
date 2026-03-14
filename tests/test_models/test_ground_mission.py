"""Tests for ground mission configuration, results, and consequence curve.

Tests the data models that bridge campaign/contract systems to ground
exploration: mission configs, intel hints, rewards, results, and the
bell-curve failure penalty system (Phase F.1).
"""

from spacegame.models.ground_mission import (
    GroundMissionConfig,
    GroundMissionResult,
    GroundMissionRewards,
    IntelHint,
    MissionOutcome,
)
from spacegame.models.ground_mapgen import DifficultyTier, MissionType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rewards(**overrides: object) -> GroundMissionRewards:
    """Create test rewards with sensible defaults."""
    defaults: dict = {
        "credits": 500,
        "xp": 25,
        "reputation": {},
        "items": [],
        "crew_xp": 15,
    }
    defaults.update(overrides)
    return GroundMissionRewards(**defaults)


def _make_config(**overrides: object) -> GroundMissionConfig:
    """Create a minimal test mission config."""
    defaults: dict = {
        "id": "test_ground_001",
        "name": "Test Mission",
        "description": "A test ground mission for unit testing.",
        "mission_type": MissionType.INFILTRATION,
        "difficulty": DifficultyTier.LOW,
        "faction_id": "frontier_alliance",
        "objectives": ["Reach the target room"],
        "intel_hints": [],
        "rewards": _make_rewards(),
        "campaign_mission_id": None,
        "campaign_map_data": None,
        "seed": 42,
    }
    defaults.update(overrides)
    return GroundMissionConfig(**defaults)


def _make_result(**overrides: object) -> GroundMissionResult:
    """Create a test mission result with sensible defaults."""
    defaults: dict = {
        "config": _make_config(),
        "outcome": MissionOutcome.SUCCESS,
        "objectives_completed": 1,
        "objectives_total": 1,
        "turns_taken": 30,
        "enemies_defeated": 2,
        "enemies_talked": 1,
        "loot_credits": 180,
        "loot_items": [],
        "progress_percent": 1.0,
        "crew_ids": [],
        "detected": False,
    }
    defaults.update(overrides)
    return GroundMissionResult(**defaults)


# ===========================================================================
# IntelHint
# ===========================================================================


class TestIntelHint:
    """Tests for IntelHint dataclass."""

    def test_construction(self) -> None:
        hint = IntelHint(
            text="Guards rotate on a 6-turn cycle.",
            required_skill="observation",
            required_level=2,
        )
        assert hint.text == "Guards rotate on a 6-turn cycle."
        assert hint.required_skill == "observation"
        assert hint.required_level == 2

    def test_to_dict(self) -> None:
        hint = IntelHint(text="East wing has a shaft.", required_skill="acuity", required_level=3)
        data = hint.to_dict()
        assert data["text"] == "East wing has a shaft."
        assert data["required_skill"] == "acuity"
        assert data["required_level"] == 3

    def test_from_dict(self) -> None:
        data = {
            "text": "Automated defenses detected.",
            "required_skill": "observation",
            "required_level": 1,
        }
        hint = IntelHint.from_dict(data)
        assert hint.text == "Automated defenses detected."
        assert hint.required_skill == "observation"
        assert hint.required_level == 1

    def test_round_trip(self) -> None:
        original = IntelHint(text="Hidden passage east.", required_skill="acuity", required_level=4)
        restored = IntelHint.from_dict(original.to_dict())
        assert restored.text == original.text
        assert restored.required_skill == original.required_skill
        assert restored.required_level == original.required_level

    def test_is_revealed_at_sufficient_level(self) -> None:
        hint = IntelHint(text="Guard pattern.", required_skill="observation", required_level=2)
        assert hint.is_revealed(skill_levels={"observation": 2})

    def test_is_revealed_above_threshold(self) -> None:
        hint = IntelHint(text="Guard pattern.", required_skill="observation", required_level=2)
        assert hint.is_revealed(skill_levels={"observation": 5})

    def test_not_revealed_below_threshold(self) -> None:
        hint = IntelHint(text="Guard pattern.", required_skill="observation", required_level=3)
        assert not hint.is_revealed(skill_levels={"observation": 2})

    def test_not_revealed_missing_skill(self) -> None:
        hint = IntelHint(text="Guard pattern.", required_skill="observation", required_level=1)
        assert not hint.is_revealed(skill_levels={})

    def test_not_revealed_wrong_skill(self) -> None:
        hint = IntelHint(text="Guard pattern.", required_skill="observation", required_level=1)
        assert not hint.is_revealed(skill_levels={"persuasion": 5})


# ===========================================================================
# GroundMissionRewards
# ===========================================================================


class TestGroundMissionRewards:
    """Tests for GroundMissionRewards dataclass."""

    def test_default_values(self) -> None:
        rewards = GroundMissionRewards()
        assert rewards.credits == 0
        assert rewards.xp == 0
        assert rewards.reputation == {}
        assert rewards.items == []
        assert rewards.crew_xp == 0

    def test_custom_values(self) -> None:
        rewards = _make_rewards(
            credits=800,
            xp=50,
            reputation={"frontier_alliance": 10},
            items=["noise_dampener"],
            crew_xp=20,
        )
        assert rewards.credits == 800
        assert rewards.xp == 50
        assert rewards.reputation == {"frontier_alliance": 10}
        assert rewards.items == ["noise_dampener"]
        assert rewards.crew_xp == 20

    def test_to_dict(self) -> None:
        rewards = _make_rewards(credits=500, reputation={"merchants_guild": 5})
        data = rewards.to_dict()
        assert data["credits"] == 500
        assert data["reputation"] == {"merchants_guild": 5}

    def test_from_dict(self) -> None:
        data = {"credits": 300, "xp": 15, "reputation": {}, "items": [], "crew_xp": 10}
        rewards = GroundMissionRewards.from_dict(data)
        assert rewards.credits == 300
        assert rewards.crew_xp == 10

    def test_from_dict_with_defaults(self) -> None:
        """Partial data should use defaults for missing fields."""
        data = {"credits": 100}
        rewards = GroundMissionRewards.from_dict(data)
        assert rewards.credits == 100
        assert rewards.xp == 0
        assert rewards.reputation == {}
        assert rewards.items == []
        assert rewards.crew_xp == 0

    def test_round_trip(self) -> None:
        original = _make_rewards(
            credits=750,
            xp=40,
            reputation={"miners_union": 8, "frontier_alliance": -3},
            items=["personal_shield", "lockpick_set"],
            crew_xp=25,
        )
        restored = GroundMissionRewards.from_dict(original.to_dict())
        assert restored.credits == original.credits
        assert restored.xp == original.xp
        assert restored.reputation == original.reputation
        assert restored.items == original.items
        assert restored.crew_xp == original.crew_xp


# ===========================================================================
# GroundMissionConfig
# ===========================================================================


class TestGroundMissionConfig:
    """Tests for GroundMissionConfig dataclass."""

    def test_basic_construction(self) -> None:
        config = _make_config()
        assert config.id == "test_ground_001"
        assert config.name == "Test Mission"
        assert config.mission_type == MissionType.INFILTRATION
        assert config.difficulty == DifficultyTier.LOW
        assert config.faction_id == "frontier_alliance"

    def test_default_max_crew(self) -> None:
        config = _make_config()
        assert config.max_crew == 2

    def test_custom_max_crew(self) -> None:
        config = _make_config(max_crew=1)
        assert config.max_crew == 1

    def test_campaign_mission_link(self) -> None:
        config = _make_config(campaign_mission_id="mission_10")
        assert config.campaign_mission_id == "mission_10"

    def test_is_campaign_true_when_linked(self) -> None:
        config = _make_config(campaign_mission_id="mission_10")
        assert config.is_campaign

    def test_is_campaign_false_for_contracts(self) -> None:
        config = _make_config(campaign_mission_id=None)
        assert not config.is_campaign

    def test_campaign_map_data_present(self) -> None:
        map_data = {"width": 25, "height": 20, "tiles": []}
        config = _make_config(campaign_map_data=map_data)
        assert config.campaign_map_data is not None
        assert config.campaign_map_data["width"] == 25

    def test_procedural_map_when_no_campaign_data(self) -> None:
        config = _make_config(campaign_map_data=None, seed=99)
        assert config.campaign_map_data is None
        assert config.seed == 99

    def test_intel_hints_stored(self) -> None:
        hints = [
            IntelHint(text="Patrol every 6 turns.", required_skill="observation", required_level=2),
            IntelHint(text="Maintenance shaft.", required_skill="acuity", required_level=3),
        ]
        config = _make_config(intel_hints=hints)
        assert len(config.intel_hints) == 2

    def test_get_revealed_hints_filters_by_level(self) -> None:
        hints = [
            IntelHint(text="Easy hint.", required_skill="observation", required_level=1),
            IntelHint(text="Hard hint.", required_skill="observation", required_level=4),
        ]
        config = _make_config(intel_hints=hints)
        revealed = config.get_revealed_hints({"observation": 2})
        assert len(revealed) == 1
        assert revealed[0].text == "Easy hint."

    def test_get_revealed_hints_empty_when_no_skills(self) -> None:
        hints = [
            IntelHint(text="Hint.", required_skill="observation", required_level=1),
        ]
        config = _make_config(intel_hints=hints)
        revealed = config.get_revealed_hints({})
        assert len(revealed) == 0

    def test_get_revealed_hints_all_revealed(self) -> None:
        hints = [
            IntelHint(text="Hint A.", required_skill="observation", required_level=1),
            IntelHint(text="Hint B.", required_skill="acuity", required_level=2),
        ]
        config = _make_config(intel_hints=hints)
        revealed = config.get_revealed_hints({"observation": 5, "acuity": 5})
        assert len(revealed) == 2

    def test_to_dict(self) -> None:
        config = _make_config(
            intel_hints=[
                IntelHint(text="Guard cycle.", required_skill="observation", required_level=2),
            ],
        )
        data = config.to_dict()
        assert data["id"] == "test_ground_001"
        assert data["mission_type"] == "infiltration"
        assert data["difficulty"] == "low"
        assert data["faction_id"] == "frontier_alliance"
        assert len(data["intel_hints"]) == 1
        assert data["intel_hints"][0]["text"] == "Guard cycle."
        assert data["max_crew"] == 2

    def test_from_dict(self) -> None:
        data = {
            "id": "contract_nexus_001",
            "name": "Data Retrieval",
            "description": "Retrieve sensitive data from a Guild warehouse.",
            "mission_type": "retrieval",
            "difficulty": "moderate",
            "faction_id": "merchants_guild",
            "objectives": ["Find the data core", "Extract safely"],
            "intel_hints": [],
            "rewards": {"credits": 800, "xp": 30},
            "campaign_mission_id": None,
            "campaign_map_data": None,
            "seed": 77,
        }
        config = GroundMissionConfig.from_dict(data)
        assert config.id == "contract_nexus_001"
        assert config.mission_type == MissionType.RETRIEVAL
        assert config.difficulty == DifficultyTier.MODERATE
        assert config.faction_id == "merchants_guild"
        assert len(config.objectives) == 2
        assert config.rewards.credits == 800
        assert config.seed == 77

    def test_from_dict_defaults_max_crew(self) -> None:
        data = {
            "id": "test",
            "name": "Test",
            "description": "Test.",
            "mission_type": "infiltration",
            "difficulty": "low",
            "faction_id": "frontier_alliance",
            "objectives": [],
            "intel_hints": [],
            "rewards": {},
        }
        config = GroundMissionConfig.from_dict(data)
        assert config.max_crew == 2

    def test_round_trip(self) -> None:
        hints = [
            IntelHint(text="Patrol hint.", required_skill="observation", required_level=2),
            IntelHint(text="Hidden path.", required_skill="acuity", required_level=4),
        ]
        original = _make_config(
            id="mission_10_crimson_reach",
            name="The Crimson Run",
            description="Intelligence suggests Malia Torres operates from Wrecker's Outpost.",
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.LOW,
            faction_id="frontier_alliance",
            objectives=["Reach Malia Torres's workshop", "Avoid detection"],
            intel_hints=hints,
            rewards=_make_rewards(credits=500, xp=25, reputation={"frontier_alliance": 10}),
            campaign_mission_id="mission_10",
            seed=1010,
            max_crew=2,
        )
        restored = GroundMissionConfig.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.mission_type == original.mission_type
        assert restored.difficulty == original.difficulty
        assert restored.faction_id == original.faction_id
        assert restored.objectives == original.objectives
        assert len(restored.intel_hints) == len(original.intel_hints)
        assert restored.intel_hints[0].text == original.intel_hints[0].text
        assert restored.rewards.credits == original.rewards.credits
        assert restored.campaign_mission_id == original.campaign_mission_id
        assert restored.seed == original.seed
        assert restored.max_crew == original.max_crew


# ===========================================================================
# MissionOutcome
# ===========================================================================


class TestMissionOutcome:
    """Tests for MissionOutcome enum."""

    def test_all_outcomes_have_string_values(self) -> None:
        expected = {"success", "extracted", "defeated", "fled"}
        actual = {o.value for o in MissionOutcome}
        assert actual == expected

    def test_is_success_true_for_success(self) -> None:
        assert MissionOutcome.SUCCESS.is_success

    def test_is_success_false_for_others(self) -> None:
        assert not MissionOutcome.EXTRACTED.is_success
        assert not MissionOutcome.DEFEATED.is_success
        assert not MissionOutcome.FLED.is_success

    def test_is_failure_for_defeated(self) -> None:
        assert MissionOutcome.DEFEATED.is_failure

    def test_is_failure_for_fled(self) -> None:
        assert MissionOutcome.FLED.is_failure

    def test_is_failure_false_for_success(self) -> None:
        assert not MissionOutcome.SUCCESS.is_failure

    def test_extracted_is_partial_success(self) -> None:
        """Extraction is neither full success nor failure — loot kept, objectives incomplete."""
        assert not MissionOutcome.EXTRACTED.is_success
        assert not MissionOutcome.EXTRACTED.is_failure


# ===========================================================================
# GroundMissionResult
# ===========================================================================


class TestGroundMissionResult:
    """Tests for GroundMissionResult dataclass."""

    def test_basic_construction(self) -> None:
        result = _make_result()
        assert result.outcome == MissionOutcome.SUCCESS
        assert result.objectives_completed == 1
        assert result.objectives_total == 1
        assert result.turns_taken == 30
        assert result.enemies_defeated == 2
        assert result.enemies_talked == 1
        assert result.loot_credits == 180

    def test_is_ghost_run_undetected_success(self) -> None:
        result = _make_result(detected=False, outcome=MissionOutcome.SUCCESS)
        assert result.is_ghost_run

    def test_is_ghost_run_false_when_detected(self) -> None:
        result = _make_result(detected=True, outcome=MissionOutcome.SUCCESS)
        assert not result.is_ghost_run

    def test_is_ghost_run_false_on_failure(self) -> None:
        result = _make_result(detected=False, outcome=MissionOutcome.DEFEATED)
        assert not result.is_ghost_run

    def test_all_objectives_completed(self) -> None:
        result = _make_result(objectives_completed=3, objectives_total=3)
        assert result.all_objectives_completed

    def test_not_all_objectives_completed(self) -> None:
        result = _make_result(objectives_completed=1, objectives_total=3)
        assert not result.all_objectives_completed

    def test_to_dict(self) -> None:
        result = _make_result(crew_ids=["elena_reeves", "tomas_drifter"])
        data = result.to_dict()
        assert data["outcome"] == "success"
        assert data["objectives_completed"] == 1
        assert data["turns_taken"] == 30
        assert data["loot_credits"] == 180
        assert data["crew_ids"] == ["elena_reeves", "tomas_drifter"]
        assert data["detected"] is False

    def test_from_dict(self) -> None:
        data = {
            "config": _make_config().to_dict(),
            "outcome": "defeated",
            "objectives_completed": 0,
            "objectives_total": 2,
            "turns_taken": 15,
            "enemies_defeated": 0,
            "enemies_talked": 0,
            "loot_credits": 50,
            "loot_items": [],
            "progress_percent": 0.35,
            "crew_ids": ["marcus_jin"],
            "detected": True,
        }
        result = GroundMissionResult.from_dict(data)
        assert result.outcome == MissionOutcome.DEFEATED
        assert result.objectives_completed == 0
        assert result.turns_taken == 15
        assert result.detected is True

    def test_round_trip(self) -> None:
        original = _make_result(
            outcome=MissionOutcome.EXTRACTED,
            objectives_completed=1,
            objectives_total=2,
            turns_taken=45,
            enemies_defeated=3,
            enemies_talked=2,
            loot_credits=300,
            loot_items=["noise_dampener"],
            progress_percent=0.78,
            crew_ids=["elena_reeves"],
            detected=True,
        )
        restored = GroundMissionResult.from_dict(original.to_dict())
        assert restored.outcome == original.outcome
        assert restored.objectives_completed == original.objectives_completed
        assert restored.objectives_total == original.objectives_total
        assert restored.turns_taken == original.turns_taken
        assert restored.enemies_defeated == original.enemies_defeated
        assert restored.enemies_talked == original.enemies_talked
        assert restored.loot_credits == original.loot_credits
        assert restored.loot_items == original.loot_items
        assert restored.progress_percent == original.progress_percent
        assert restored.crew_ids == original.crew_ids
        assert restored.detected == original.detected


# ===========================================================================
# Consequence Curve
# ===========================================================================


class TestConsequenceCurve:
    """Tests for the bell-curve failure penalty system.

    The consequence curve determines penalties based on how far into
    the mission the player progressed before failing. Penalties peak
    in the middle (commitment zone) and ease off at both ends.
    """

    # --- Grace zone (0-15%) ---

    def test_grace_zone_zero_progress(self) -> None:
        """Barely entered — minimal penalty."""
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.0)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] == 5
        assert penalties["loot_kept_percent"] == 100
        assert penalties["xp_penalty"] == 0

    def test_grace_zone_at_boundary(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.14)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] == 5
        assert penalties["loot_kept_percent"] == 100
        assert penalties["xp_penalty"] == 0

    # --- Escalating zone (15-40%) ---

    def test_escalating_zone_early(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.15)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] == 10
        assert penalties["loot_kept_percent"] == 10
        assert penalties["xp_penalty"] == 0

    def test_escalating_zone_late(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.39)
        penalties = result.calculate_penalties()
        assert (
            10 <= penalties["credit_loss_percent"] <= 15
        ), f"Escalating zone credit loss should be 10-15%, got {penalties['credit_loss_percent']}%"
        assert penalties["loot_kept_percent"] == 10
        assert penalties["xp_penalty"] == 0

    # --- Commitment zone (40-65%) — peak penalty ---

    def test_commitment_zone_early(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.40)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] == 15
        assert penalties["loot_kept_percent"] == 0
        assert penalties["xp_penalty"] > 0

    def test_commitment_zone_middle(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.50)
        penalties = result.calculate_penalties()
        assert (
            15 <= penalties["credit_loss_percent"] <= 20
        ), f"Commitment zone credit loss should be 15-20%, got {penalties['credit_loss_percent']}%"
        assert penalties["loot_kept_percent"] == 0
        assert penalties["xp_penalty"] > 0

    def test_commitment_zone_late(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.64)
        penalties = result.calculate_penalties()
        assert (
            15 <= penalties["credit_loss_percent"] <= 20
        ), f"Commitment zone credit loss should be 15-20%, got {penalties['credit_loss_percent']}%"
        assert penalties["loot_kept_percent"] == 0
        assert penalties["xp_penalty"] > 0

    # --- Easing zone (65-85%) ---

    def test_easing_zone(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.75)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] == 10
        assert penalties["loot_kept_percent"] == 50
        assert penalties["xp_penalty"] == 0

    # --- So close zone (85-100%) ---

    def test_so_close_zone(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.90)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] == 5
        assert penalties["loot_kept_percent"] == 80
        assert penalties["xp_penalty"] == 0

    def test_so_close_zone_at_99_percent(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.99)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] == 5
        assert penalties["loot_kept_percent"] == 80
        assert penalties["xp_penalty"] == 0

    # --- Success should have no penalties ---

    def test_success_no_penalties(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, progress_percent=1.0)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] == 0
        assert penalties["loot_kept_percent"] == 100
        assert penalties["xp_penalty"] == 0

    # --- Extracted (voluntary extraction) — loot kept, no penalties ---

    def test_extracted_no_penalties(self) -> None:
        """Voluntary extraction keeps all loot but objectives may be incomplete."""
        result = _make_result(outcome=MissionOutcome.EXTRACTED, progress_percent=0.50)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] == 0
        assert penalties["loot_kept_percent"] == 100
        assert penalties["xp_penalty"] == 0

    # --- Fled has lighter penalties than defeated ---

    def test_fled_lighter_than_defeated_at_same_progress(self) -> None:
        """Fleeing successfully should be less punishing than outright defeat."""
        defeated = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.50)
        fled = _make_result(outcome=MissionOutcome.FLED, progress_percent=0.50)
        d_penalties = defeated.calculate_penalties()
        f_penalties = fled.calculate_penalties()
        assert f_penalties["credit_loss_percent"] <= d_penalties["credit_loss_percent"]
        assert f_penalties["loot_kept_percent"] >= d_penalties["loot_kept_percent"]

    # --- Boundary precision ---

    def test_exactly_15_percent_is_escalating(self) -> None:
        """15% boundary belongs to escalating zone, not grace."""
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.15)
        penalties = result.calculate_penalties()
        assert penalties["credit_loss_percent"] >= 10, "Should be in escalating zone"

    def test_exactly_40_percent_is_commitment(self) -> None:
        """40% boundary belongs to commitment zone."""
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.40)
        penalties = result.calculate_penalties()
        assert penalties["loot_kept_percent"] == 0, "Should be in commitment zone"

    def test_exactly_65_percent_is_easing(self) -> None:
        """65% boundary belongs to easing zone."""
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.65)
        penalties = result.calculate_penalties()
        assert penalties["loot_kept_percent"] == 50, "Should be in easing zone"

    def test_exactly_85_percent_is_so_close(self) -> None:
        """85% boundary belongs to so-close zone."""
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.85)
        penalties = result.calculate_penalties()
        assert penalties["loot_kept_percent"] == 80, "Should be in so-close zone"


# ===========================================================================
# Reward Calculation
# ===========================================================================


class TestRewardCalculation:
    """Tests for total reward computation on successful missions."""

    def test_total_credits_includes_loot_and_reward(self) -> None:
        result = _make_result(
            outcome=MissionOutcome.SUCCESS,
            loot_credits=180,
            detected=True,  # No ghost bonus
        )
        assert result.total_credits == result.config.rewards.credits + 180

    def test_total_credits_on_failure_applies_penalty(self) -> None:
        """Defeated at 50% progress — commitment zone penalties apply."""
        result = _make_result(
            outcome=MissionOutcome.DEFEATED,
            progress_percent=0.50,
            loot_credits=200,
        )
        # Should NOT get mission reward credits, and loot is reduced/lost
        total = result.total_credits
        assert total < 200, "Should lose loot in commitment zone"

    def test_total_credits_on_extraction_keeps_loot(self) -> None:
        """Voluntary extraction keeps loot but no mission reward."""
        result = _make_result(
            outcome=MissionOutcome.EXTRACTED,
            loot_credits=300,
        )
        total = result.total_credits
        assert total == 300, "Extraction keeps loot but no mission reward"

    def test_ghost_bonus_on_undetected_success(self) -> None:
        """Ghost runs should earn a bonus — stealth-first philosophy."""
        normal = _make_result(
            outcome=MissionOutcome.SUCCESS,
            detected=True,
            loot_credits=100,
        )
        ghost = _make_result(
            outcome=MissionOutcome.SUCCESS,
            detected=False,
            loot_credits=100,
        )
        assert (
            ghost.total_credits >= normal.total_credits
        ), "Ghost run should not earn less than a detected run"


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_zero_objectives(self) -> None:
        """Exploration missions may have no discrete objectives."""
        result = _make_result(objectives_completed=0, objectives_total=0)
        assert result.all_objectives_completed

    def test_negative_progress_clamped(self) -> None:
        """Progress should never be negative, but handle gracefully."""
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=-0.1)
        penalties = result.calculate_penalties()
        # Should behave like grace zone
        assert penalties["credit_loss_percent"] == 5

    def test_progress_above_one_clamped(self) -> None:
        """Progress above 1.0 should be treated as 1.0."""
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=1.5)
        penalties = result.calculate_penalties()
        # At 100% progress, so-close zone
        assert penalties["credit_loss_percent"] == 5
        assert penalties["loot_kept_percent"] == 80

    def test_empty_crew(self) -> None:
        result = _make_result(crew_ids=[])
        assert result.crew_ids == []

    def test_multiple_crew(self) -> None:
        result = _make_result(crew_ids=["elena_reeves", "tomas_drifter"])
        assert len(result.crew_ids) == 2

    def test_no_loot(self) -> None:
        result = _make_result(loot_credits=0, loot_items=[])
        assert result.loot_credits == 0
        assert result.loot_items == []

    def test_config_with_empty_description(self) -> None:
        """Contract configs may have minimal descriptions."""
        config = _make_config(description="")
        assert config.description == ""

    def test_config_with_no_seed_uses_none(self) -> None:
        config = _make_config(seed=None)
        assert config.seed is None
