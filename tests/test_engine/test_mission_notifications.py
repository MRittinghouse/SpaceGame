"""Tests for consolidated mission availability notifications."""

from unittest.mock import MagicMock, patch

from spacegame.models.journal import Journal
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
)


def _make_mission(
    mission_id: str,
    name: str = "Test Mission",
    prerequisites: list[str] | None = None,
    auto_accept: bool = False,
    discovery_text: str = "",
) -> Mission:
    return Mission(
        id=mission_id,
        name=name,
        description=f"Description for {name}.",
        objectives=[
            MissionObjective(type="reach_system", target_id="breakstone", target_quantity=1)
        ],
        rewards=[MissionReward(reward_type="credits", amount=100)],
        prerequisites=prerequisites or [],
        auto_accept=auto_accept,
        discovery_text=discovery_text,
    )


def _make_game_with_prereq_completed(
    prereq_id: str,
    unlocked_missions: list[Mission],
) -> "Game":
    """Create a Game where prereq is COMPLETED and unlocked missions are UNAVAILABLE.

    This simulates the moment check_missions() runs after a prerequisite
    mission was just completed, triggering update_availability().
    """
    from spacegame.engine.game import Game

    with patch.object(Game, "__init__", lambda self: None):
        game = Game()

    game.player = MagicMock()
    game.player.game_day = 1
    game.player.current_system_id = "nexus_prime"
    game.player.dialogue_flags = {}
    game.player.side_missions_completed = 0
    game.player.crew_quests_completed = 0
    game.player.ship = MagicMock()

    # Build manager with prereq already completed
    prereq = _make_mission(prereq_id, "Prereq")
    all_missions = [prereq, *unlocked_missions]
    manager = MissionManager(all_missions)
    # Force prereq to COMPLETED state so update_availability fires for dependents
    manager._status[prereq_id] = MissionStatus.COMPLETED

    game.mission_manager = manager
    game.journal = Journal()
    game.crew_roster = None
    game.dialogue_manager = MagicMock()
    game.politics_manager = None
    game.galaxy_map_view = None
    game.ambient_dialogue = None
    game._mission_notifications = []

    return game


def _trigger_availability(game: "Game") -> None:
    """Simulate the update_availability portion of check_missions.

    We call update_availability directly and then run the same notification
    logic that check_missions uses, since we can't easily make check_objectives
    return a completed ID without a fully wired player.
    """
    newly_available = game.mission_manager.update_availability(game.player.dialogue_flags)
    discoverable_count = 0
    for mid in newly_available:
        mission = game.mission_manager.get_mission(mid)
        if mission:
            if mission.auto_accept and mission.on_accept_cargo:
                for cargo in mission.on_accept_cargo:
                    game.player.ship.add_cargo(cargo.commodity_id, cargo.quantity, 0)
                    game._mission_notifications.append(
                        f"Cargo Loaded: {cargo.quantity} {cargo.commodity_id}"
                    )
            if mission.auto_accept:
                game._mission_notifications.append(f"Mission Accepted: {mission.name}")
            else:
                discoverable_count += 1
                if game.journal:
                    discovery = mission.discovery_text or f"Heard word of new work: {mission.name}."
                    game.journal.add_auto_entry(
                        entry_id=f"mission_discover_{mid}",
                        text=discovery,
                        game_day=game.player.game_day,
                        system_id=game.player.current_system_id,
                        tag="goals",
                        mission_id=mid,
                    )
    if discoverable_count == 1:
        game._mission_notifications.append("New Mission Available \u2014 check your journal")
    elif discoverable_count > 1:
        game._mission_notifications.append("New Missions Available \u2014 check your journal")


class TestConsolidatedMissionNotifications:
    """Newly available missions produce a single notification + journal entries."""

    def test_single_mission_singular_notification(self) -> None:
        """One new mission produces singular 'New Mission Available' text."""
        unlocked = _make_mission("unlocked", "Unlocked Mission", prerequisites=["prereq"])
        game = _make_game_with_prereq_completed("prereq", [unlocked])
        _trigger_availability(game)

        notifications = game._mission_notifications
        available_msgs = [n for n in notifications if "New Mission" in n]
        assert len(available_msgs) == 1, f"Expected 1 notification, got: {available_msgs}"
        assert "check your journal" in available_msgs[0]
        assert "New Mission Available" in available_msgs[0]

    def test_multiple_missions_plural_notification(self) -> None:
        """Multiple new missions produce plural 'New Missions Available' text."""
        m1 = _make_mission("m1", "Mission One", prerequisites=["prereq"])
        m2 = _make_mission("m2", "Mission Two", prerequisites=["prereq"])
        game = _make_game_with_prereq_completed("prereq", [m1, m2])
        _trigger_availability(game)

        notifications = game._mission_notifications
        available_msgs = [n for n in notifications if "New Mission" in n]
        assert len(available_msgs) == 1, f"Expected 1 notification, got: {available_msgs}"
        assert "New Missions Available" in available_msgs[0]

    def test_no_individual_mission_name_in_notifications(self) -> None:
        """Individual mission names should not appear in notification cards."""
        unlocked = _make_mission("unlocked", "Secret Mission", prerequisites=["prereq"])
        game = _make_game_with_prereq_completed("prereq", [unlocked])
        _trigger_availability(game)

        assert not any("Secret Mission" in n for n in game._mission_notifications), (
            "Individual mission name should not appear in notification cards"
        )

    def test_journal_entry_with_custom_discovery_text(self) -> None:
        """Custom discovery_text is used for the journal entry."""
        unlocked = _make_mission(
            "unlocked",
            "Ore Hauling",
            prerequisites=["prereq"],
            discovery_text="Overheard a broker looking for haulers.",
        )
        game = _make_game_with_prereq_completed("prereq", [unlocked])
        _trigger_availability(game)

        entries = game.journal.get_entries(tag_filter="goals")
        assert len(entries) == 1
        assert entries[0].text == "Overheard a broker looking for haulers."
        assert entries[0].mission_id == "unlocked"
        assert entries[0].tag == "goals"
        assert entries[0].system_id == "nexus_prime"

    def test_journal_entry_fallback_without_discovery_text(self) -> None:
        """Without discovery_text, journal entry uses generic fallback."""
        unlocked = _make_mission("unlocked", "Ore Hauling", prerequisites=["prereq"])
        game = _make_game_with_prereq_completed("prereq", [unlocked])
        _trigger_availability(game)

        entries = game.journal.get_entries(tag_filter="goals")
        assert len(entries) == 1
        assert "Ore Hauling" in entries[0].text

    def test_auto_accept_missions_skip_journal_discovery(self) -> None:
        """Auto-accepted missions get 'Mission Accepted', not journal discovery."""
        auto = _make_mission("auto_m", "Auto Mission", prerequisites=["prereq"], auto_accept=True)
        game = _make_game_with_prereq_completed("prereq", [auto])
        _trigger_availability(game)

        assert any("Mission Accepted: Auto Mission" in n for n in game._mission_notifications)
        goal_entries = game.journal.get_entries(tag_filter="goals")
        assert len(goal_entries) == 0

    def test_no_notification_when_nothing_unlocks(self) -> None:
        """No consolidated notification when nothing new unlocks."""
        # Mission with unmet prereq
        locked = _make_mission("locked", "Locked", prerequisites=["other_prereq"])
        game = _make_game_with_prereq_completed("prereq", [locked])
        _trigger_availability(game)

        available_msgs = [n for n in game._mission_notifications if "New Mission" in n]
        assert len(available_msgs) == 0

    def test_mixed_auto_and_discoverable(self) -> None:
        """Auto-accept and discoverable missions produce correct notifications."""
        auto = _make_mission("auto_m", "Auto Mission", prerequisites=["prereq"], auto_accept=True)
        disc = _make_mission(
            "disc_m",
            "Discoverable",
            prerequisites=["prereq"],
            discovery_text="Spotted a notice on the board.",
        )
        game = _make_game_with_prereq_completed("prereq", [auto, disc])
        _trigger_availability(game)

        # Auto gets individual "Mission Accepted"
        assert any("Mission Accepted: Auto Mission" in n for n in game._mission_notifications)
        # Discoverable gets single consolidated notification
        available_msgs = [n for n in game._mission_notifications if "New Mission" in n]
        assert len(available_msgs) == 1
        assert "New Mission Available" in available_msgs[0]
        # Journal has only the discoverable mission
        entries = game.journal.get_entries(tag_filter="goals")
        assert len(entries) == 1
        assert entries[0].text == "Spotted a notice on the board."


# ============================================================================
# CB-2 engine integration: combat marker + warp-arrival banter wiring
# ============================================================================


class TestCB2CombatMarkerWiring:
    """CB-2 criterion 8: _apply_combat_result calls ambient_dialogue.mark_combat."""

    def test_apply_combat_result_marks_combat_day(self) -> None:
        """combat marker is set to player.game_day after combat resolves."""
        from spacegame.engine.game import Game
        from spacegame.models.ambient_dialogue import AmbientDialogueManager
        from spacegame.models.combat import CombatResult

        with patch.object(Game, "__init__", lambda self: None):
            game = Game()

        game.ambient_dialogue = AmbientDialogueManager([])
        game.player = MagicMock()
        game.player.game_day = 3
        game.player.current_system_id = "nexus_prime"

        mock_state = MagicMock()
        mock_state.result = CombatResult.DEFEAT  # Simple branch — no loot/XP logic
        mock_state.player.hull = 80
        mock_state.player.shields = 20
        game.combat_view = MagicMock()
        game.combat_view.engine.get_state.return_value = mock_state

        game._apply_combat_result()

        assert game.ambient_dialogue.last_combat_day == 3, (
            "_apply_combat_result must call mark_combat(player.game_day)"
        )


class TestCB2WarpArrivalBanterWiring:
    """CB-2 criterion 9: warp arrival queues combat_after banter in _mission_notifications."""

    # All view attributes that _handle_state_transitions reads with `if self.X` guards.
    # Setting them to None causes those blocks to be skipped entirely.
    _ALL_VIEWS = (
        "main_menu_view",
        "name_input_view",
        "character_creation_view",
        "journal_view",
        "crew_roster_view",
        "character_view",
        "trading_view",
        "combat_view",
        "encounter_view",
        "mining_view",
        "salvage_view",
        "refining_view",
        "station_hub_view",
        "ship_builder_view",
        "shipyard_view",
        "repair_bay_view",
        "skill_tree_view",
        "cantina_view",
        "deep_shafts_view",
        "dispute_view",
        "auction_view",
        "sell_lot_view",
        "wreckers_guild_view",
        "investment_view",
        "mission_log_view",
        "statistics_view",
        "achievements_view",
        "ground_briefing_view",
        "ground_exploration_view",
        "ground_result_view",
        "dialogue_view",
    )

    def test_warp_arrival_queues_combat_after_notification(self) -> None:
        """After combat + warp, a combat_after line appears in _mission_notifications."""
        from spacegame.engine.game import Game
        from spacegame.models.ambient_dialogue import AmbientDialogueManager, AmbientLine

        with patch.object(Game, "__init__", lambda self: None):
            game = Game()

        # Null all views so _handle_state_transitions skips their blocks
        for view_attr in self._ALL_VIEWS:
            setattr(game, view_attr, None)

        # Real AmbientDialogueManager with one combat_after line
        ca_line = AmbientLine(
            crew_id="marcus_jin",
            text="Drive seals took a hit. Check them before the next jump.",
            context="combat_after",
        )
        game.ambient_dialogue = AmbientDialogueManager([ca_line])
        game.ambient_dialogue.mark_combat(0)  # Combat happened on day 0

        game.player = MagicMock()
        game.player.game_day = 1  # Within 3-day window of day-0 combat
        game.player.current_system_id = "breakstone"
        game.player.dialogue_flags = {}
        game.player.systems_visited = []

        mock_template = MagicMock()
        mock_template.id = "marcus_jin"
        mock_template.name = "Marcus Jin"
        mock_template.home_system_id = "other_system"
        mock_template.faction_id = ""
        game.crew_roster = MagicMock()
        game.crew_roster.get_recruited_members.return_value = [(mock_template, None)]
        game.crew_roster.get_member_state.return_value = {"loyalty": 50}
        game.crew_roster.get_template.return_value = mock_template

        game.data_loader = MagicMock()
        game.data_loader.get_system.return_value = MagicMock(faction="")

        # Galaxy map view with an arrival message — simulates warp-arrival trigger
        game.galaxy_map_view = MagicMock()
        game.galaxy_map_view.active = True
        game.galaxy_map_view.save_requested = False
        game.galaxy_map_view.arrival_message = "Arrived at Breakstone."

        game.transition_manager = MagicMock()
        game.transition_manager.active = False
        game.travel_log = None
        game.journal = None
        game._last_visited_count = 0
        game._mission_notifications = []
        game._check_auto_triggers = MagicMock()

        game._handle_state_transitions()

        ca_msgs = [n for n in game._mission_notifications if "Drive seals" in n]
        assert len(ca_msgs) == 1, (
            "Warp arrival must queue combat_after banter within the recency window"
        )
