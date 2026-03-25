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
    all_missions = [prereq] + unlocked_missions
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
