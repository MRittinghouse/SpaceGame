"""Tests for the GroundResultView — post-mission outcome screen.

Tests the result display for ground missions: outcome title/color,
stats (objectives, turns, enemies), rewards on success, penalty
application on failure, ghost run indicator, and state transitions
(Phase F.2).
"""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState  # noqa: E402
from spacegame.models.ground_mapgen import DifficultyTier, MissionType  # noqa: E402
from spacegame.models.ground_mission import (  # noqa: E402
    GroundMissionConfig,
    GroundMissionResult,
    GroundMissionRewards,
    IntelHint,
    MissionOutcome,
)
from spacegame.views.ground_result_view import GroundResultView  # noqa: E402

# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for all view tests in this module."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_config(**overrides: object) -> GroundMissionConfig:
    """Create a test mission config."""
    defaults: dict = {
        "id": "test_ground_001",
        "name": "Test Infiltration",
        "description": "A test ground mission.",
        "mission_type": MissionType.INFILTRATION,
        "difficulty": DifficultyTier.LOW,
        "faction_id": "frontier_alliance",
        "objectives": ["Reach the target"],
        "intel_hints": [],
        "rewards": GroundMissionRewards(credits=500, xp=25, crew_xp=15),
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
        "detected": True,
    }
    defaults.update(overrides)
    return GroundMissionResult(**defaults)


def _make_view(
    result: GroundMissionResult | None = None,
    return_state: GameState = GameState.GALAXY_MAP,
) -> GroundResultView:
    """Create a result view with test data, fully initialized."""
    ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    res = result or _make_result()
    view = GroundResultView(
        ui_manager=ui,
        result=res,
        return_state=return_state,
    )
    view.on_enter()
    return view


def _press_button(view: GroundResultView, button: object) -> None:
    """Simulate a pygame_gui button press event."""
    event = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=button)
    view.handle_event(event)


def _send_key(view: GroundResultView, key: int) -> None:
    """Simulate a KEYDOWN event."""
    event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0)
    view.handle_event(event)


# ============================================================================
# Construction
# ============================================================================


class TestConstruction:
    """Tests for view initialization."""

    def test_stores_result(self) -> None:
        result = _make_result()
        view = _make_view(result=result)
        assert view.result is result
        view.on_exit()

    def test_next_state_initially_none(self) -> None:
        view = _make_view()
        assert view.get_next_state() is None
        view.on_exit()

    def test_active_after_on_enter(self) -> None:
        view = _make_view()
        assert view.active
        view.on_exit()

    def test_inactive_after_on_exit(self) -> None:
        view = _make_view()
        view.on_exit()
        assert not view.active

    def test_stores_return_state(self) -> None:
        view = _make_view(return_state=GameState.TRADING)
        assert view.return_state == GameState.TRADING
        view.on_exit()


# ============================================================================
# Outcome Display Data
# ============================================================================


class TestOutcomeDisplay:
    """Tests for outcome title, color, and summary generation."""

    def test_success_title(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS)
        view = _make_view(result=result)
        summary = view.get_outcome_summary()
        assert summary["title"] == "MISSION COMPLETE"
        view.on_exit()

    def test_success_color_is_green(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS)
        view = _make_view(result=result)
        summary = view.get_outcome_summary()
        assert summary["color"] == Colors.GREEN
        view.on_exit()

    def test_extracted_title(self) -> None:
        result = _make_result(outcome=MissionOutcome.EXTRACTED)
        view = _make_view(result=result)
        summary = view.get_outcome_summary()
        assert summary["title"] == "EXTRACTED"
        view.on_exit()

    def test_extracted_color_is_yellow(self) -> None:
        result = _make_result(outcome=MissionOutcome.EXTRACTED)
        view = _make_view(result=result)
        summary = view.get_outcome_summary()
        assert summary["color"] == Colors.YELLOW
        view.on_exit()

    def test_defeated_title(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.5)
        view = _make_view(result=result)
        summary = view.get_outcome_summary()
        assert summary["title"] == "MISSION FAILED"
        view.on_exit()

    def test_defeated_color_is_red(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.5)
        view = _make_view(result=result)
        summary = view.get_outcome_summary()
        assert summary["color"] == Colors.RED
        view.on_exit()

    def test_fled_title(self) -> None:
        result = _make_result(outcome=MissionOutcome.FLED, progress_percent=0.3)
        view = _make_view(result=result)
        summary = view.get_outcome_summary()
        assert summary["title"] == "FLED"
        view.on_exit()

    def test_fled_color_is_orange(self) -> None:
        result = _make_result(outcome=MissionOutcome.FLED, progress_percent=0.3)
        view = _make_view(result=result)
        summary = view.get_outcome_summary()
        # Orange for fled
        assert summary["color"] == (255, 140, 40)
        view.on_exit()


# ============================================================================
# Stats Lines
# ============================================================================


class TestStatsLines:
    """Tests for the stat lines displayed on the result screen."""

    def test_success_stats_include_objectives(self) -> None:
        result = _make_result(objectives_completed=2, objectives_total=2)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        obj_line = _find_stat_containing(stats, "Objectives")
        assert obj_line is not None
        assert "2/2" in obj_line[0]
        view.on_exit()

    def test_stats_include_turns(self) -> None:
        result = _make_result(turns_taken=42)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        turns_line = _find_stat_containing(stats, "Turns")
        assert turns_line is not None
        assert "42" in turns_line[0]
        view.on_exit()

    def test_stats_include_enemies_defeated(self) -> None:
        result = _make_result(enemies_defeated=3)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        enemy_line = _find_stat_containing(stats, "defeated")
        assert enemy_line is not None
        assert "3" in enemy_line[0]
        view.on_exit()

    def test_stats_include_enemies_talked(self) -> None:
        result = _make_result(enemies_talked=2)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        talk_line = _find_stat_containing(stats, "talked")
        assert talk_line is not None
        assert "2" in talk_line[0]
        view.on_exit()

    def test_enemies_talked_hidden_when_zero(self) -> None:
        result = _make_result(enemies_talked=0)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        assert _find_stat_containing(stats, "talked") is None
        view.on_exit()

    def test_ghost_indicator_on_undetected_success(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, detected=False)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        ghost_line = _find_stat_containing(stats, "Ghost")
        assert ghost_line is not None, "Ghost run should be indicated"
        view.on_exit()

    def test_no_ghost_indicator_when_detected(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, detected=True)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        ghost_line = _find_stat_containing(stats, "Ghost")
        assert ghost_line is None
        view.on_exit()

    def test_detection_shown_as_undetected_on_ghost(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, detected=False)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        det_line = _find_stat_containing(stats, "Undetected")
        assert det_line is not None
        view.on_exit()


# ============================================================================
# Rewards Section (Success)
# ============================================================================


class TestRewardsSection:
    """Tests for reward display on successful missions."""

    def test_success_shows_mission_credits(self) -> None:
        config = _make_config(rewards=GroundMissionRewards(credits=800))
        result = _make_result(config=config, outcome=MissionOutcome.SUCCESS)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        credits_line = _find_stat_containing(stats, "Mission reward")
        assert credits_line is not None
        assert "800" in credits_line[0]
        view.on_exit()

    def test_success_shows_loot_credits(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, loot_credits=250)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        loot_line = _find_stat_containing(stats, "looted")
        assert loot_line is not None
        assert "250" in loot_line[0]
        view.on_exit()

    def test_loot_credits_hidden_when_zero(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, loot_credits=0)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        loot_line = _find_stat_containing(stats, "looted")
        assert loot_line is None
        view.on_exit()

    def test_success_shows_xp(self) -> None:
        config = _make_config(rewards=GroundMissionRewards(xp=30))
        result = _make_result(config=config, outcome=MissionOutcome.SUCCESS)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        xp_line = _find_stat_containing(stats, "XP")
        assert xp_line is not None
        assert "30" in xp_line[0]
        view.on_exit()

    def test_success_shows_crew_xp(self) -> None:
        config = _make_config(rewards=GroundMissionRewards(crew_xp=15))
        result = _make_result(
            config=config,
            outcome=MissionOutcome.SUCCESS,
            crew_ids=["elena_reeves", "tomas_drifter"],
        )
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        crew_line = _find_stat_containing(stats, "Crew XP")
        assert crew_line is not None
        assert "15" in crew_line[0]
        view.on_exit()

    def test_no_crew_xp_line_when_no_crew(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, crew_ids=[])
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        crew_line = _find_stat_containing(stats, "Crew XP")
        assert crew_line is None
        view.on_exit()

    def test_ghost_bonus_shown(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, detected=False)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        ghost_line = _find_stat_containing(stats, "Ghost")
        assert ghost_line is not None
        view.on_exit()


# ============================================================================
# Penalties Section (Failure)
# ============================================================================


class TestPenaltiesSection:
    """Tests for penalty display on failed missions."""

    def test_defeated_shows_credit_loss(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.50)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        loss_line = _find_stat_containing(stats, "Credits lost")
        assert loss_line is not None
        view.on_exit()

    def test_defeated_shows_loot_status(self) -> None:
        """In commitment zone (50%), all loot is lost."""
        result = _make_result(
            outcome=MissionOutcome.DEFEATED,
            progress_percent=0.50,
            loot_credits=200,
        )
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        loot_line = _find_stat_containing(stats, "Loot")
        assert loot_line is not None
        view.on_exit()

    def test_defeated_no_mission_reward(self) -> None:
        """Failed missions don't show mission reward credits."""
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.50)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        reward_line = _find_stat_containing(stats, "Mission reward")
        assert reward_line is None
        view.on_exit()

    def test_extracted_shows_loot_kept(self) -> None:
        """Extraction keeps loot."""
        result = _make_result(outcome=MissionOutcome.EXTRACTED, loot_credits=300)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        loot_line = _find_stat_containing(stats, "looted")
        assert loot_line is not None
        assert "300" in loot_line[0]
        view.on_exit()

    def test_extracted_no_mission_reward(self) -> None:
        """Extraction doesn't award mission reward credits (the +X CR line)."""
        result = _make_result(outcome=MissionOutcome.EXTRACTED)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        # Should not have the green "+X CR" reward line, only the yellow notice
        reward_line = _find_stat_containing(stats, "Mission reward: +")
        assert reward_line is None
        view.on_exit()

    def test_penalty_lines_use_red_color(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.50)
        view = _make_view(result=result)
        stats = view.build_stat_lines()
        loss_line = _find_stat_containing(stats, "Credits lost")
        assert loss_line is not None
        assert loss_line[1] == Colors.RED, "Penalty lines should be red"
        view.on_exit()


# ============================================================================
# State Transitions
# ============================================================================


class TestStateTransitions:
    """Tests for continue/return transitions."""

    def test_continue_button_sets_return_state(self) -> None:
        view = _make_view(return_state=GameState.GALAXY_MAP)
        _press_button(view, view.continue_button)
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()

    def test_enter_key_continues(self) -> None:
        view = _make_view(return_state=GameState.GALAXY_MAP)
        _send_key(view, pygame.K_RETURN)
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()

    def test_space_key_continues(self) -> None:
        view = _make_view(return_state=GameState.GALAXY_MAP)
        _send_key(view, pygame.K_SPACE)
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()

    def test_custom_return_state(self) -> None:
        view = _make_view(return_state=GameState.TRADING)
        _press_button(view, view.continue_button)
        assert view.get_next_state() == GameState.TRADING
        view.on_exit()


# ============================================================================
# Render Smoke Tests
# ============================================================================


class TestRenderSmoke:
    """Smoke tests — view renders without crashing for all outcome types."""

    def test_render_success(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS)
        view = _make_view(result=result)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_defeated(self) -> None:
        result = _make_result(outcome=MissionOutcome.DEFEATED, progress_percent=0.5)
        view = _make_view(result=result)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_extracted(self) -> None:
        result = _make_result(outcome=MissionOutcome.EXTRACTED)
        view = _make_view(result=result)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_fled(self) -> None:
        result = _make_result(outcome=MissionOutcome.FLED, progress_percent=0.3)
        view = _make_view(result=result)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_with_crew(self) -> None:
        result = _make_result(
            outcome=MissionOutcome.SUCCESS,
            crew_ids=["elena_reeves", "tomas_drifter"],
        )
        view = _make_view(result=result)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_ghost_run(self) -> None:
        result = _make_result(outcome=MissionOutcome.SUCCESS, detected=False)
        view = _make_view(result=result)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_update_does_not_crash(self) -> None:
        view = _make_view()
        view.update(0.016)
        view.on_exit()


# ============================================================================
# UI Element Lifecycle
# ============================================================================


class TestUILifecycle:
    """Tests for _create_ui / _destroy_ui pairing."""

    def test_continue_button_created(self) -> None:
        view = _make_view()
        assert view.continue_button is not None
        view.on_exit()

    def test_button_cleaned_up_on_exit(self) -> None:
        view = _make_view()
        view.on_exit()
        assert view.continue_button is None

    def test_on_enter_on_exit_cycle(self) -> None:
        ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        result = _make_result()
        view = GroundResultView(ui_manager=ui, result=result, return_state=GameState.GALAXY_MAP)
        view.on_enter()
        assert view.active
        view.on_exit()
        assert not view.active


# ============================================================================
# Stat Line Helpers
# ============================================================================


def _find_stat_containing(
    stats: list[tuple[str, tuple[int, int, int]]],
    substring: str,
) -> tuple[str, tuple[int, int, int]] | None:
    """Find the first stat line containing the given substring."""
    for text, color in stats:
        if substring.lower() in text.lower():
            return (text, color)
    return None
