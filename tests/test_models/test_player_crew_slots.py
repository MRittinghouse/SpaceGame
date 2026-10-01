"""Player queries the bug bash added."""

from __future__ import annotations

from pathlib import Path

from spacegame.data_loader import get_data_loader
from spacegame.models.player import Player
from spacegame.models.ship import Ship

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _player() -> Player:
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    return Player("TestPilot", 5000, "nexus_prime", Ship(ship_type=ship_type, current_fuel=40))


class TestCrewSlots:
    def test_the_shuttle_has_one_berth(self) -> None:
        assert _player().get_crew_slots() == 1

    def test_crew_manager_one_plus_legend_gives_four(self) -> None:
        player = _player()
        player.progression.skills["crew_manager"].current_level = 1
        player.progression.skills["legend_of_the_expanse"].current_level = 1
        assert player.get_crew_slots() == 4

    def test_crew_manager_alone_gives_two(self) -> None:
        player = _player()
        player.progression.skills["crew_manager"].current_level = 1
        assert player.get_crew_slots() == 2

    def test_only_the_player_reads_the_slot_bonus(self) -> None:
        readers = sorted(
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in (PROJECT_ROOT / "spacegame").rglob("*.py")
            if '"crew_slot_bonus"' in path.read_text(encoding="utf-8")
        )
        assert readers == ["spacegame/models/player.py"]


class TestEffectiveReputation:
    """BB-82: Frontier Reputation counts toward the Frontier's mission gate."""

    def test_the_skill_bonus_opens_the_lost_registry(self) -> None:
        from spacegame.models.mission import MissionManager, MissionStatus

        dl = get_data_loader()
        dl.load_all()
        player = _player()
        player.faction_reputation["frontier_alliance"] = 5
        player.progression.skills["frontier_reputation"].current_level = 2
        flags = {"registry_search_started": True}
        stored = MissionManager(dl.missions)
        stored.load_state({"status": {"whispers_at_the_bar": "completed"}})
        stored.update_availability(flags, player_reputation=dict(player.faction_reputation))
        assert stored.get_status("the_lost_registry") == MissionStatus.UNAVAILABLE
        effective = MissionManager(dl.missions)
        effective.load_state({"status": {"whispers_at_the_bar": "completed"}})
        effective.update_availability(
            flags, player_reputation=player.get_effective_reputations(dl.factions)
        )
        assert effective.get_status("the_lost_registry") == MissionStatus.ACTIVE
