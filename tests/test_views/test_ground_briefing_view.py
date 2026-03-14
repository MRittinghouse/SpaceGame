"""Tests for the GroundBriefingView — mission briefing, crew selection, intel display.

Tests the pre-mission briefing screen that shows mission details,
filtered intel hints, crew selection with ability summaries, and
launch/cancel state transitions (Phase F.1).
"""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState  # noqa: E402
from spacegame.models.crew import CrewAbility, CrewRoster, CrewTemplate  # noqa: E402
from spacegame.models.ground_crew import GroundCrewBonuses  # noqa: E402
from spacegame.models.ground_mapgen import DifficultyTier, MissionType  # noqa: E402
from spacegame.models.ground_mission import (  # noqa: E402
    GroundMissionConfig,
    GroundMissionRewards,
    IntelHint,
)
from spacegame.views.ground_briefing_view import GroundBriefingView  # noqa: E402

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


# --- Ground crew ability descriptions for briefing display ---
_GROUND_ABILITY_DESCRIPTIONS: dict[str, list[str]] = {
    "elena_reeves": ["Vision +1", "Reveal patrols", "Retreat +2"],
    "marcus_jin": ["Silent doors"],
    "dr_priya_osei": ["Analyze weakness"],
    "tomas_drifter": ["Noise -1", "Talk +2"],
}


def _make_crew_template(
    tid: str = "elena_reeves",
    name: str = "Elena Reeves",
    role: str = "navigator",
) -> CrewTemplate:
    """Create a minimal crew template for testing."""
    return CrewTemplate(
        id=tid,
        name=name,
        role=role,
        description=f"Test crew member {name}.",
        portrait_color=[100, 150, 200],
        abilities=[
            CrewAbility(
                bonus_type="fuel_efficiency_bonus",
                bonus_value=0.05,
                description="Efficient Routing",
                unlock_level=1,
            ),
        ],
    )


def _make_crew_roster(
    recruit_ids: list[str] | None = None,
) -> CrewRoster:
    """Create a crew roster with specified members recruited."""
    templates = {
        "elena_reeves": _make_crew_template("elena_reeves", "Elena Reeves", "navigator"),
        "marcus_jin": _make_crew_template("marcus_jin", "Marcus Jin", "engineer"),
        "dr_priya_osei": _make_crew_template("dr_priya_osei", "Dr. Priya Osei", "scientist"),
        "tomas_drifter": _make_crew_template("tomas_drifter", "Tomas Drifter", "trader"),
    }
    roster = CrewRoster(templates)
    for tid in recruit_ids or []:
        roster.recruit(tid, crew_slots=4)
    return roster


def _make_config(**overrides: object) -> GroundMissionConfig:
    """Create a test mission config with sensible defaults."""
    defaults: dict = {
        "id": "test_ground_001",
        "name": "Test Infiltration",
        "description": "Slip into the outpost and reach the target room.",
        "mission_type": MissionType.INFILTRATION,
        "difficulty": DifficultyTier.LOW,
        "faction_id": "frontier_alliance",
        "objectives": ["Reach the target room", "Avoid detection"],
        "intel_hints": [],
        "rewards": GroundMissionRewards(credits=500, xp=25),
        "campaign_mission_id": None,
        "campaign_map_data": None,
        "seed": 42,
        "max_crew": 2,
    }
    defaults.update(overrides)
    return GroundMissionConfig(**defaults)


def _make_view(
    config: GroundMissionConfig | None = None,
    crew_roster: CrewRoster | None = None,
    skill_levels: dict[str, int] | None = None,
) -> GroundBriefingView:
    """Create a briefing view with test data, fully initialized."""
    ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    cfg = config or _make_config()
    roster = crew_roster or _make_crew_roster()
    view = GroundBriefingView(
        ui_manager=ui,
        mission_config=cfg,
        crew_roster=roster,
        skill_levels=skill_levels or {},
    )
    view.on_enter()
    return view


def _press_button(view: GroundBriefingView, button: object) -> None:
    """Simulate a pygame_gui button press event."""
    event = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=button)
    view.handle_event(event)


# ============================================================================
# Construction
# ============================================================================


class TestConstruction:
    """Tests for view initialization."""

    def test_stores_mission_config(self) -> None:
        view = _make_view()
        assert view.mission_config.id == "test_ground_001"
        view.on_exit()

    def test_stores_crew_roster(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves"])
        view = _make_view(crew_roster=roster)
        assert view.crew_roster is roster
        view.on_exit()

    def test_next_state_initially_none(self) -> None:
        view = _make_view()
        assert view.get_next_state() is None
        view.on_exit()

    def test_selected_crew_initially_empty(self) -> None:
        view = _make_view()
        assert view.selected_crew == []
        view.on_exit()

    def test_active_after_on_enter(self) -> None:
        view = _make_view()
        assert view.active
        view.on_exit()

    def test_inactive_after_on_exit(self) -> None:
        view = _make_view()
        view.on_exit()
        assert not view.active


# ============================================================================
# Mission Info Display
# ============================================================================


class TestMissionInfoDisplay:
    """Tests for mission information content."""

    def test_mission_name_accessible(self) -> None:
        config = _make_config(name="The Crimson Run")
        view = _make_view(config=config)
        assert view.mission_config.name == "The Crimson Run"
        view.on_exit()

    def test_objectives_accessible(self) -> None:
        config = _make_config(objectives=["Find the data core", "Extract safely"])
        view = _make_view(config=config)
        assert len(view.mission_config.objectives) == 2
        view.on_exit()

    def test_difficulty_displayed(self) -> None:
        config = _make_config(difficulty=DifficultyTier.HIGH)
        view = _make_view(config=config)
        assert view.mission_config.difficulty == DifficultyTier.HIGH
        view.on_exit()


# ============================================================================
# Intel Hints
# ============================================================================


class TestIntelHints:
    """Tests for intel hint filtering and display."""

    def test_no_hints_when_no_skills(self) -> None:
        hints = [
            IntelHint(
                text="Guards rotate every 6 turns.", required_skill="observation", required_level=2
            ),
        ]
        config = _make_config(intel_hints=hints)
        view = _make_view(config=config, skill_levels={})
        assert len(view.revealed_hints) == 0
        view.on_exit()

    def test_hints_revealed_at_sufficient_level(self) -> None:
        hints = [
            IntelHint(text="Guard cycle hint.", required_skill="observation", required_level=2),
        ]
        config = _make_config(intel_hints=hints)
        view = _make_view(config=config, skill_levels={"observation": 3})
        assert len(view.revealed_hints) == 1
        assert view.revealed_hints[0].text == "Guard cycle hint."
        view.on_exit()

    def test_partial_hints_revealed(self) -> None:
        """Only hints the player qualifies for are shown."""
        hints = [
            IntelHint(text="Easy hint.", required_skill="observation", required_level=1),
            IntelHint(text="Hard hint.", required_skill="observation", required_level=5),
        ]
        config = _make_config(intel_hints=hints)
        view = _make_view(config=config, skill_levels={"observation": 2})
        assert len(view.revealed_hints) == 1
        assert view.revealed_hints[0].text == "Easy hint."
        view.on_exit()

    def test_multiple_skill_types(self) -> None:
        hints = [
            IntelHint(text="Observation hint.", required_skill="observation", required_level=1),
            IntelHint(text="Acuity hint.", required_skill="acuity", required_level=2),
        ]
        config = _make_config(intel_hints=hints)
        view = _make_view(config=config, skill_levels={"observation": 3, "acuity": 2})
        assert len(view.revealed_hints) == 2
        view.on_exit()


# ============================================================================
# Crew Selection
# ============================================================================


class TestCrewSelection:
    """Tests for crew member selection and deselection."""

    def test_select_one_crew_member(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves"])
        view = _make_view(crew_roster=roster)
        view.toggle_crew_selection("elena_reeves")
        assert "elena_reeves" in view.selected_crew
        view.on_exit()

    def test_deselect_crew_member(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves"])
        view = _make_view(crew_roster=roster)
        view.toggle_crew_selection("elena_reeves")
        view.toggle_crew_selection("elena_reeves")  # Toggle off
        assert "elena_reeves" not in view.selected_crew
        view.on_exit()

    def test_select_up_to_max_crew(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves", "marcus_jin", "tomas_drifter"])
        config = _make_config(max_crew=2)
        view = _make_view(config=config, crew_roster=roster)
        view.toggle_crew_selection("elena_reeves")
        view.toggle_crew_selection("marcus_jin")
        assert len(view.selected_crew) == 2
        view.on_exit()

    def test_cannot_exceed_max_crew(self) -> None:
        """Selecting beyond max_crew should not add the member."""
        roster = _make_crew_roster(recruit_ids=["elena_reeves", "marcus_jin", "tomas_drifter"])
        config = _make_config(max_crew=2)
        view = _make_view(config=config, crew_roster=roster)
        view.toggle_crew_selection("elena_reeves")
        view.toggle_crew_selection("marcus_jin")
        view.toggle_crew_selection("tomas_drifter")  # Should be rejected
        assert len(view.selected_crew) == 2
        assert "tomas_drifter" not in view.selected_crew
        view.on_exit()

    def test_deselect_then_select_different(self) -> None:
        """Can swap crew by deselecting one and selecting another."""
        roster = _make_crew_roster(recruit_ids=["elena_reeves", "marcus_jin", "tomas_drifter"])
        config = _make_config(max_crew=2)
        view = _make_view(config=config, crew_roster=roster)
        view.toggle_crew_selection("elena_reeves")
        view.toggle_crew_selection("marcus_jin")
        view.toggle_crew_selection("elena_reeves")  # Deselect
        view.toggle_crew_selection("tomas_drifter")  # Now fits
        assert "tomas_drifter" in view.selected_crew
        assert "marcus_jin" in view.selected_crew
        assert "elena_reeves" not in view.selected_crew
        view.on_exit()

    def test_cannot_select_unrecruited_crew(self) -> None:
        """Only recruited crew members can be selected."""
        roster = _make_crew_roster(recruit_ids=["elena_reeves"])
        view = _make_view(crew_roster=roster)
        view.toggle_crew_selection("tomas_drifter")  # Not recruited
        assert "tomas_drifter" not in view.selected_crew
        view.on_exit()

    def test_no_crew_available(self) -> None:
        """View works fine with no recruited crew."""
        roster = _make_crew_roster(recruit_ids=[])
        view = _make_view(crew_roster=roster)
        assert view.selected_crew == []
        assert view.available_crew == []
        view.on_exit()

    def test_available_crew_lists_recruited_only(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves", "marcus_jin"])
        view = _make_view(crew_roster=roster)
        available_ids = [t.id for t, _ in view.available_crew]
        assert "elena_reeves" in available_ids
        assert "marcus_jin" in available_ids
        assert "tomas_drifter" not in available_ids
        view.on_exit()

    def test_solo_mission_allowed(self) -> None:
        """Player can launch with zero crew selected."""
        roster = _make_crew_roster(recruit_ids=["elena_reeves"])
        view = _make_view(crew_roster=roster)
        # Don't select anyone — launch should still be possible
        assert view.selected_crew == []
        view.on_exit()


# ============================================================================
# Crew Ground Abilities Display
# ============================================================================


class TestCrewGroundAbilities:
    """Tests for crew ground ability descriptions in briefing."""

    def test_get_ground_abilities_elena(self) -> None:
        view = _make_view()
        abilities = view.get_crew_ground_abilities("elena_reeves")
        assert "Vision +1" in abilities
        assert "Reveal patrols" in abilities
        assert "Retreat +2" in abilities
        view.on_exit()

    def test_get_ground_abilities_marcus(self) -> None:
        view = _make_view()
        abilities = view.get_crew_ground_abilities("marcus_jin")
        assert "Silent doors" in abilities
        view.on_exit()

    def test_get_ground_abilities_priya(self) -> None:
        view = _make_view()
        abilities = view.get_crew_ground_abilities("dr_priya_osei")
        assert "Analyze weakness" in abilities
        view.on_exit()

    def test_get_ground_abilities_tomas(self) -> None:
        view = _make_view()
        abilities = view.get_crew_ground_abilities("tomas_drifter")
        assert "Noise -1" in abilities
        assert "Talk +2" in abilities
        view.on_exit()

    def test_unknown_crew_returns_empty(self) -> None:
        view = _make_view()
        abilities = view.get_crew_ground_abilities("unknown_crew_id")
        assert abilities == []
        view.on_exit()


# ============================================================================
# State Transitions
# ============================================================================


class TestStateTransitions:
    """Tests for launch and cancel transitions."""

    def test_launch_sets_ground_exploration_state(self) -> None:
        view = _make_view()
        _press_button(view, view.launch_button)
        assert view.get_next_state() == GameState.GROUND_EXPLORATION
        view.on_exit()

    def test_cancel_sets_return_state(self) -> None:
        view = _make_view()
        _press_button(view, view.cancel_button)
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()

    def test_custom_return_state(self) -> None:
        """Cancel returns to a custom state if set."""
        view = _make_view()
        view.return_state = GameState.TRADING
        _press_button(view, view.cancel_button)
        assert view.get_next_state() == GameState.TRADING
        view.on_exit()

    def test_escape_key_cancels(self) -> None:
        view = _make_view()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0)
        view.handle_event(event)
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()


# ============================================================================
# Render Smoke Tests
# ============================================================================


class TestRenderSmoke:
    """Smoke tests — view renders without crashing."""

    def test_render_does_not_crash(self) -> None:
        view = _make_view()
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_with_intel_hints(self) -> None:
        hints = [
            IntelHint(text="Patrol hint.", required_skill="observation", required_level=1),
        ]
        config = _make_config(intel_hints=hints)
        view = _make_view(config=config, skill_levels={"observation": 5})
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_with_crew_selected(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves", "tomas_drifter"])
        view = _make_view(crew_roster=roster)
        view.toggle_crew_selection("elena_reeves")
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_render_with_no_crew(self) -> None:
        roster = _make_crew_roster(recruit_ids=[])
        view = _make_view(crew_roster=roster)
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()

    def test_update_does_not_crash(self) -> None:
        view = _make_view()
        view.update(0.016)  # 60 FPS frame
        view.on_exit()


# ============================================================================
# UI Element Lifecycle
# ============================================================================


class TestUILifecycle:
    """Tests for _create_ui / _destroy_ui pairing."""

    def test_launch_button_created(self) -> None:
        view = _make_view()
        assert view.launch_button is not None
        view.on_exit()

    def test_cancel_button_created(self) -> None:
        view = _make_view()
        assert view.cancel_button is not None
        view.on_exit()

    def test_crew_buttons_created_for_recruited(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves", "marcus_jin"])
        view = _make_view(crew_roster=roster)
        assert len(view.crew_buttons) == 2
        view.on_exit()

    def test_no_crew_buttons_when_no_crew(self) -> None:
        roster = _make_crew_roster(recruit_ids=[])
        view = _make_view(crew_roster=roster)
        assert len(view.crew_buttons) == 0
        view.on_exit()

    def test_buttons_cleaned_up_on_exit(self) -> None:
        view = _make_view()
        view.on_exit()
        assert view.launch_button is None
        assert view.cancel_button is None

    def test_on_enter_on_exit_cycle(self) -> None:
        """View can be entered and exited cleanly."""
        ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        config = _make_config()
        roster = _make_crew_roster()
        view = GroundBriefingView(
            ui_manager=ui, mission_config=config, crew_roster=roster, skill_levels={}
        )
        view.on_enter()
        assert view.active
        view.on_exit()
        assert not view.active


# ============================================================================
# Crew Button Interaction
# ============================================================================


class TestCrewButtonInteraction:
    """Tests for crew selection via button presses."""

    def test_crew_button_toggles_selection(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves"])
        view = _make_view(crew_roster=roster)
        # Press the crew button for Elena
        elena_btn = view.crew_buttons.get("elena_reeves")
        assert elena_btn is not None
        _press_button(view, elena_btn)
        assert "elena_reeves" in view.selected_crew
        view.on_exit()

    def test_crew_button_deselects_on_second_press(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves"])
        view = _make_view(crew_roster=roster)
        elena_btn = view.crew_buttons["elena_reeves"]
        _press_button(view, elena_btn)
        _press_button(view, elena_btn)
        assert "elena_reeves" not in view.selected_crew
        view.on_exit()

    def test_crew_button_respects_max_crew(self) -> None:
        roster = _make_crew_roster(recruit_ids=["elena_reeves", "marcus_jin", "tomas_drifter"])
        config = _make_config(max_crew=1)
        view = _make_view(config=config, crew_roster=roster)
        elena_btn = view.crew_buttons["elena_reeves"]
        marcus_btn = view.crew_buttons["marcus_jin"]
        _press_button(view, elena_btn)
        _press_button(view, marcus_btn)  # Should be rejected (max_crew=1)
        assert len(view.selected_crew) == 1
        assert "elena_reeves" in view.selected_crew
        view.on_exit()
