"""Crew XP and loyalty triggered by trades and jumps (SP3 spec 6.1)."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.crew import CrewRoster


def _roster() -> CrewRoster:
    dl = get_data_loader()
    dl.load_all()
    roster = CrewRoster(dl.crew_templates)
    roster.recruit("elena_reeves", 4)
    return roster


class TestTriggers:
    def test_trades_pay_xp_and_loyalty(self) -> None:
        roster = _roster()
        roster.on_trades(new_trades=3, xp_bonus=2, loyalty_bonus=1)
        member = roster.get_state()["members"]["elena_reeves"]
        assert member["xp"] == (5 + 2) * 3
        assert member["loyalty"] == 30 + (1 + 1) * 3

    def test_jumps_pay_xp_only(self) -> None:
        roster = _roster()
        roster.on_jumps(new_jumps=4, xp_bonus=1)
        member = roster.get_state()["members"]["elena_reeves"]
        assert member["xp"] == (3 + 1) * 4
        assert member["loyalty"] == 30

    def test_leadership(self) -> None:
        roster = _roster()
        roster.apply_leadership(loyalty_floor=20, legendary=True)
        assert roster.loyalty_floor == 20
        assert roster.loyalty_flag_offset == 10
        roster.apply_leadership(loyalty_floor=0, legendary=False)
        assert roster.loyalty_floor == 0
        assert roster.loyalty_flag_offset == 0

    def test_trades_return_levelups_then_flags(self) -> None:
        roster = _roster()
        result = roster.on_trades(new_trades=10, xp_bonus=0, loyalty_bonus=1)
        assert result == (["Elena Reeves reached level 2!"], ["crew_loyalty_elena_reeves_50"])

    def test_jumps_return_levelups(self) -> None:
        roster = _roster()
        assert roster.on_jumps(new_jumps=10, xp_bonus=2) == ["Elena Reeves reached level 2!"]
        member = roster.get_state()["members"]["elena_reeves"]
        assert member["loyalty"] == 30
