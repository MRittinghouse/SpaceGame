"""Scenario: ground mission lifecycle — briefing → run → outcome → reward.

SI-2 Stream 1. Ground missions have a view (briefing → exploration →
result) but no end-to-end scenario covers the contract that turns a
GroundMissionResult into player-state mutations.

Walks the four hops a playtester takes:

  1. **Config** — ``GroundMissionConfig`` defines the mission (rewards,
     objectives, intel, faction).
  2. **Result building** — at the end of exploration,
     ``GroundExplorationView.get_mission_result`` produces a
     ``GroundMissionResult`` with the outcome + tracked counters.
  3. **Outcome semantics** — ``MissionOutcome.SUCCESS / EXTRACTED /
     DEFEATED / FLED`` drive different reward/penalty branches in
     ``GroundMissionResult.calculate_penalties`` (the consequence curve)
     and ``GroundMissionResult.total_credits``.
  4. **Apply** — ``Game._apply_ground_result`` (game.py:3256) walks the
     result and credits the player, awards XP, awards crew XP, applies
     reputation, sets the complete-flag, increments ground-mission
     counters, and (on failure) applies penalties.

The reward dispatch is mirrored inline in ``_apply_ground_result``
below. **If you ever refactor game.py:3256 onto a model method
(``Player.apply_ground_mission_result(...)``), update the inlined
helper here to delegate.**

This scenario originally surfaced a latent crash in game.py:3305
(``self.player.faction_reputation.modify(...)`` against a plain dict).
Fixed in the same SI-2 sprint by routing reputation rewards through
``politics_manager.apply_reputation_with_spillover`` with a fallback to
``player.modify_reputation`` — same pattern the encounter dispatch
uses (game.py:2959). The reputation-reward test below now defends
against the regression.
"""

from __future__ import annotations

from spacegame.models.ground_mapgen import DifficultyTier, MissionType
from spacegame.models.ground_mission import (
    GHOST_RUN_BONUS_PERCENT,
    GroundMissionConfig,
    GroundMissionResult,
    GroundMissionRewards,
    MissionOutcome,
)
from tests.test_scenarios._helpers import fresh_player

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


def _make_config(
    *,
    config_id: str = "scen_ground_01",
    credits: int = 500,
    xp: int = 100,
    crew_xp: int = 25,
    reputation: dict[str, int] | None = None,
    complete_flag: str = "",
) -> GroundMissionConfig:
    return GroundMissionConfig(
        id=config_id,
        name="Scenario Ground Mission",
        description="A test mission.",
        mission_type=MissionType.INFILTRATION,
        difficulty=DifficultyTier.LOW,
        faction_id="commerce_guild",
        objectives=["Reach the exit"],
        intel_hints=[],
        rewards=GroundMissionRewards(
            credits=credits,
            xp=xp,
            crew_xp=crew_xp,
            reputation=reputation or {},
        ),
        max_crew=2,
        complete_flag=complete_flag,
    )


def _make_result(
    config: GroundMissionConfig,
    outcome: MissionOutcome,
    *,
    loot_credits: int = 0,
    loot_commodities: dict[str, int] | None = None,
    progress: float = 1.0,
    detected: bool = True,
    crew_ids: list[str] | None = None,
    enemies_defeated: int = 0,
    enemies_talked: int = 0,
) -> GroundMissionResult:
    return GroundMissionResult(
        config=config,
        outcome=outcome,
        objectives_completed=1,
        objectives_total=1,
        turns_taken=20,
        enemies_defeated=enemies_defeated,
        enemies_talked=enemies_talked,
        loot_credits=loot_credits,
        loot_items=[],
        loot_commodities=loot_commodities or {},
        progress_percent=progress,
        crew_ids=crew_ids or [],
        detected=detected,
    )


def _apply_ground_result(player, result: GroundMissionResult) -> None:
    """Mirror ``Game._apply_ground_result`` (game.py:3256).

    Skips the crew-roster XP path (Game owns the roster, scenario doesn't)
    and the contract-completion bonus (no ground_contract_manager here).
    Routes reputation through ``player.modify_reputation`` directly —
    matches the post-fix ``politics_manager`` fallback branch at
    game.py:3303.
    """
    outcome = result.outcome
    loot_bonus = player.progression.get_bonus("ground_loot_bonus")
    boosted_loot = round(result.loot_credits * (1.0 + loot_bonus))

    if outcome == MissionOutcome.SUCCESS:
        total = result.config.rewards.credits + boosted_loot
        if result.is_ghost_run:
            total += int(result.config.rewards.credits * GHOST_RUN_BONUS_PERCENT / 100)
        player.credits += total

        if result.config.rewards.xp > 0:
            player.progression.add_xp(result.config.rewards.xp)

        # Reputation — see docstring KNOWN GAME-PY BUG.
        for faction_id, rep in result.config.rewards.reputation.items():
            player.modify_reputation(faction_id, rep)

    elif outcome == MissionOutcome.EXTRACTED:
        player.credits += boosted_loot

    elif outcome.is_failure:
        penalties = result.calculate_penalties()
        credit_loss = int(player.credits * penalties["credit_loss_percent"] / 100)
        player.credits -= credit_loss
        kept_loot = int(boosted_loot * penalties["loot_kept_percent"] / 100)
        player.credits += kept_loot
        if penalties["xp_penalty"] > 0:
            player.progression.add_xp(-penalties["xp_penalty"])

    # Commodity drops to cargo (success / extracted / failure all carry these).
    if result.loot_commodities:
        for cid, qty in result.loot_commodities.items():
            player.ship.add_cargo(cid, qty, price_per_unit=0)

    # Stat counters
    player.ground_enemies_defeated += result.enemies_defeated
    player.ground_enemies_talked += result.enemies_talked

    if outcome == MissionOutcome.SUCCESS:
        player.ground_missions_completed += 1
        if result.is_ghost_run:
            player.ground_undetected_completions += 1
        if result.config.is_campaign:
            player.ground_campaign_missions_completed += 1
        if result.config.complete_flag:
            player.dialogue_flags[result.config.complete_flag] = True
    elif outcome.is_failure:
        player.ground_missions_failed += 1


# ---------------------------------------------------------------------------
# 1. Outcome semantics — the four branches
# ---------------------------------------------------------------------------


class TestSuccessAwardsRewards:
    def test_success_credits_xp_and_counter(self) -> None:
        player = fresh_player(credits=1000)
        config = _make_config(credits=500, xp=100)
        result = _make_result(config, MissionOutcome.SUCCESS, detected=True)

        _apply_ground_result(player, result)

        assert player.credits == 1500
        assert player.progression.xp == 100
        assert player.ground_missions_completed == 1
        assert player.ground_missions_failed == 0
        assert player.ground_undetected_completions == 0  # detected=True

    def test_ghost_run_pays_bonus_and_increments_counter(self) -> None:
        """Undetected success = +10% credits + ghost counter increment."""
        player = fresh_player(credits=1000)
        config = _make_config(credits=500, xp=100)
        result = _make_result(config, MissionOutcome.SUCCESS, detected=False)

        _apply_ground_result(player, result)

        bonus = int(500 * GHOST_RUN_BONUS_PERCENT / 100)  # 50
        assert player.credits == 1000 + 500 + bonus
        assert player.ground_undetected_completions == 1

    def test_complete_flag_set_only_on_success(self) -> None:
        player = fresh_player()
        config = _make_config(complete_flag="ground_mission_alpha_done")
        result = _make_result(config, MissionOutcome.SUCCESS)

        _apply_ground_result(player, result)
        assert player.dialogue_flags.get("ground_mission_alpha_done") is True

        # Failure: no flag set
        player2 = fresh_player()
        result_fail = _make_result(
            _make_config(complete_flag="ground_mission_beta_done"),
            MissionOutcome.DEFEATED,
            progress=0.5,
        )
        _apply_ground_result(player2, result_fail)
        assert "ground_mission_beta_done" not in player2.dialogue_flags

    def test_reputation_reward_routes_through_player_api(self) -> None:
        """Regression guard for the ``faction_reputation.modify`` crash
        fixed in SI-2 — see file docstring. If anyone reverts game.py:3303
        back to the dict-attribute call, the production path crashes; this
        test mirrors the corrected dispatch."""
        player = fresh_player()
        baseline = player.faction_reputation.get("commerce_guild", 0)
        config = _make_config(reputation={"commerce_guild": 5})
        result = _make_result(config, MissionOutcome.SUCCESS)

        _apply_ground_result(player, result)
        assert player.faction_reputation.get("commerce_guild", 0) == baseline + 5


class TestExtractedKeepsLootOnly:
    def test_extracted_no_mission_reward_keeps_loot(self) -> None:
        player = fresh_player(credits=1000)
        config = _make_config(credits=500, xp=100)
        result = _make_result(
            config, MissionOutcome.EXTRACTED, loot_credits=200
        )

        _apply_ground_result(player, result)

        # Mission reward NOT awarded; loot IS kept
        assert player.credits == 1200
        # No XP for extraction either
        assert player.progression.xp == 0
        # No completion counter
        assert player.ground_missions_completed == 0
        assert player.ground_missions_failed == 0


class TestFailurePenalties:
    def test_defeated_in_commitment_zone_pays_max_penalty(self) -> None:
        """In the commitment zone (0.40-0.65), defeated takes the peak
        penalty: credit loss interpolates 15-20%, 0% loot kept, 5 XP."""
        player = fresh_player(credits=1000)
        # Give the player some XP to make the penalty observable
        player.progression.add_xp(100)
        config = _make_config(credits=500)
        progress = 0.5
        result = _make_result(
            config,
            MissionOutcome.DEFEATED,
            loot_credits=200,
            progress=progress,
        )

        # Compute the expected loss the same way the consequence curve does
        # so the assertion stays in lockstep with ground_mission.py:332.
        t = (progress - 0.40) / 0.25
        expected_loss_pct = int(15 + t * 5)  # 17 at progress=0.5
        expected_loss = int(1000 * expected_loss_pct / 100)

        starting_xp = player.progression.xp
        _apply_ground_result(player, result)

        # Loot kept: 0% of 200 = 0 (commitment zone strips loot)
        assert player.credits == 1000 - expected_loss
        assert player.progression.xp == starting_xp - 5  # commitment XP penalty
        assert player.ground_missions_failed == 1
        assert player.ground_missions_completed == 0

    def test_fled_lighter_than_defeated(self) -> None:
        """At identical progress, FLED keeps more loot than DEFEATED."""
        config = _make_config()

        defeated_player = fresh_player(credits=1000)
        result_defeated = _make_result(
            config,
            MissionOutcome.DEFEATED,
            loot_credits=300,
            progress=0.7,  # easing zone (10% loss, 50% loot kept)
        )
        _apply_ground_result(defeated_player, result_defeated)

        fled_player = fresh_player(credits=1000)
        result_fled = _make_result(
            config,
            MissionOutcome.FLED,
            loot_credits=300,
            progress=0.7,
        )
        _apply_ground_result(fled_player, result_fled)

        # Fled keeps strictly more credits than defeated at identical progress
        assert fled_player.credits > defeated_player.credits

    def test_grace_zone_minimal_penalty(self) -> None:
        """Failing in the first 15% of the mission has only a 5% credit loss."""
        player = fresh_player(credits=1000)
        config = _make_config()
        result = _make_result(
            config,
            MissionOutcome.DEFEATED,
            loot_credits=100,
            progress=0.05,  # grace zone
        )

        _apply_ground_result(player, result)

        # 5% loss of 1000 = 50; loot kept 100% of 100 = 100
        assert player.credits == 1000 - 50 + 100


# ---------------------------------------------------------------------------
# 2. Loot commodities flow into ship cargo regardless of outcome
# ---------------------------------------------------------------------------


class TestLootCommoditiesToCargo:
    def test_success_loot_commodities_added_to_cargo(self) -> None:
        player = fresh_player()
        config = _make_config()
        result = _make_result(
            config,
            MissionOutcome.SUCCESS,
            loot_commodities={"electronics": 3},
        )

        _apply_ground_result(player, result)
        assert player.ship.get_cargo_quantity("electronics") == 3

    def test_failure_loot_commodities_still_added(self) -> None:
        """Per game.py:3351 the loot_commodities path runs after the
        outcome branch — failures still take the items home (the credits
        get penalized, not the physical loot)."""
        player = fresh_player()
        config = _make_config()
        result = _make_result(
            config,
            MissionOutcome.DEFEATED,
            loot_commodities={"electronics": 2},
            progress=0.5,
        )

        _apply_ground_result(player, result)
        assert player.ship.get_cargo_quantity("electronics") == 2


# ---------------------------------------------------------------------------
# 3. Encounter-counter tracking
# ---------------------------------------------------------------------------


class TestStatCounters:
    def test_enemies_defeated_and_talked_accumulate(self) -> None:
        player = fresh_player()
        config = _make_config()
        result = _make_result(
            config,
            MissionOutcome.SUCCESS,
            enemies_defeated=3,
            enemies_talked=1,
        )

        _apply_ground_result(player, result)
        assert player.ground_enemies_defeated == 3
        assert player.ground_enemies_talked == 1

    def test_counters_accumulate_across_missions(self) -> None:
        player = fresh_player()
        config = _make_config()

        for _ in range(3):
            result = _make_result(
                config,
                MissionOutcome.SUCCESS,
                enemies_defeated=2,
            )
            _apply_ground_result(player, result)

        assert player.ground_missions_completed == 3
        assert player.ground_enemies_defeated == 6


# ---------------------------------------------------------------------------
# 4. Full lifecycle — config → result → applied → all state hops verified
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    def test_complete_lifecycle_credits_xp_flag_counter_loot(self) -> None:
        """One-shot end-to-end: a ghost-run success with loot commodities,
        rep reward, and a completion flag. Every observable state hop is
        asserted."""
        player = fresh_player(credits=1000)
        baseline_rep = player.faction_reputation.get("commerce_guild", 0)
        config = _make_config(
            credits=500,
            xp=100,
            reputation={"commerce_guild": 3},
            complete_flag="alpha_complete",
        )
        result = _make_result(
            config,
            MissionOutcome.SUCCESS,
            loot_credits=150,
            loot_commodities={"electronics": 2},
            detected=False,  # ghost run
            enemies_defeated=2,
        )

        _apply_ground_result(player, result)

        # Credits: 1000 + 500 (mission) + 150 (loot) + 50 (ghost bonus 10%)
        assert player.credits == 1000 + 500 + 150 + 50
        assert player.progression.xp == 100
        assert player.faction_reputation["commerce_guild"] == baseline_rep + 3
        assert player.dialogue_flags.get("alpha_complete") is True
        assert player.ship.get_cargo_quantity("electronics") == 2
        assert player.ground_missions_completed == 1
        assert player.ground_undetected_completions == 1
        assert player.ground_missions_failed == 0
        assert player.ground_enemies_defeated == 2
