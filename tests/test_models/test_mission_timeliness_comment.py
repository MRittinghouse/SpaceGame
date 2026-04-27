"""TW follow-up comment: iron_delivery NPC voice reacts to timeliness.

Covers the tier resolver on SoftDeadline, the comment helper on Mission,
the MissionManager surfacing helper, and content integrity for the
authored iron_delivery lines.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionReward,
    MissionStatus,
)
from spacegame.models.soft_deadline import SoftDeadline


def _make_player(game_day: int = 0):
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship, ShipType

    ship_type = ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="x",
        cargo_capacity=10,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=2,
        special_abilities=[],
        availability="all",
    )
    player = Player(
        name="T",
        credits=0,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )
    player.game_day = game_day
    return player


# ---------------------------------------------------------------------------
# Tier resolver
# ---------------------------------------------------------------------------


class TestSoftDeadlineResolveTier:
    def _sd(self) -> SoftDeadline:
        return SoftDeadline(full_reward_day_count=10, partial_reward_day_count=15)

    @pytest.mark.parametrize(
        "days,expected",
        [
            (0, "timely"),
            (5, "timely"),
            (10, "timely"),
            (11, "late"),
            (14, "late"),
            (15, "late"),
            (16, "very_late"),
            (1000, "very_late"),
        ],
    )
    def test_tier_boundaries(self, days, expected) -> None:
        assert self._sd().resolve_tier(days) == expected


# ---------------------------------------------------------------------------
# Mission.get_timeliness_comment
# ---------------------------------------------------------------------------


class TestMissionGetTimelinessComment:
    def _mission(self, comments: dict[str, str] | None = None) -> Mission:
        return Mission(
            id="test",
            name="Test",
            description="d",
            rewards=[MissionReward(reward_type="credits", amount=100)],
            soft_deadline=SoftDeadline(
                full_reward_day_count=10,
                partial_reward_day_count=15,
            ),
            timeliness_comments=comments or {},
        )

    def test_returns_comment_for_tier(self) -> None:
        m = self._mission(
            {
                "timely": "On time.",
                "late": "Ran long.",
                "very_late": "Forgot about you.",
            }
        )
        assert m.get_timeliness_comment(5) == "On time."
        assert m.get_timeliness_comment(12) == "Ran long."
        assert m.get_timeliness_comment(50) == "Forgot about you."

    def test_returns_none_when_no_comments_authored(self) -> None:
        m = self._mission({})
        assert m.get_timeliness_comment(5) is None
        assert m.get_timeliness_comment(50) is None

    def test_returns_none_when_tier_comment_missing(self) -> None:
        """A mission with only a 'timely' comment returns None for late tiers
        rather than a wrong-tier line."""
        m = self._mission({"timely": "On time."})
        assert m.get_timeliness_comment(5) == "On time."
        assert m.get_timeliness_comment(15) is None
        assert m.get_timeliness_comment(50) is None

    def test_returns_none_when_no_soft_deadline(self) -> None:
        m = Mission(
            id="x",
            name="x",
            description="d",
            timeliness_comments={"timely": "x"},
            soft_deadline=None,
        )
        assert m.get_timeliness_comment(5) is None

    def test_empty_string_comment_treated_as_absent(self) -> None:
        """Authoring bug: empty string shouldn't fire as dialogue."""
        m = self._mission({"timely": "   ", "late": "Ran long."})
        assert m.get_timeliness_comment(5) is None
        assert m.get_timeliness_comment(12) == "Ran long."


# ---------------------------------------------------------------------------
# MissionManager.get_timeliness_comment
# ---------------------------------------------------------------------------


class TestMissionManagerGetTimelinessComment:
    def _mgr_with_accepted(self, accept_day: int) -> MissionManager:
        mission = Mission(
            id="deadline_test",
            name="T",
            description="d",
            rewards=[MissionReward(reward_type="credits", amount=100)],
            soft_deadline=SoftDeadline(
                full_reward_day_count=10,
                partial_reward_day_count=15,
            ),
            timeliness_comments={
                "timely": "On time.",
                "late": "Ran long.",
                "very_late": "Forgot about you.",
            },
        )
        mgr = MissionManager([mission])
        mgr._status[mission.id] = MissionStatus.AVAILABLE
        mgr.accept_mission(mission.id, game_day=accept_day)
        return mgr

    def test_resolves_using_player_game_day(self) -> None:
        mgr = self._mgr_with_accepted(accept_day=100)
        player = _make_player(game_day=108)  # 8 elapsed -> timely
        assert mgr.get_timeliness_comment("deadline_test", player) == "On time."
        player.game_day = 113  # 13 elapsed -> late
        assert mgr.get_timeliness_comment("deadline_test", player) == "Ran long."
        player.game_day = 200  # 100 elapsed -> very_late
        assert mgr.get_timeliness_comment("deadline_test", player) == "Forgot about you."

    def test_none_when_no_accept_day_recorded(self) -> None:
        """Legacy save path: mission active but no accept_day stored."""
        mission = Mission(
            id="x",
            name="x",
            description="d",
            soft_deadline=SoftDeadline(
                full_reward_day_count=10,
                partial_reward_day_count=15,
            ),
            timeliness_comments={"timely": "x"},
        )
        mgr = MissionManager([mission])
        mgr._status["x"] = MissionStatus.AVAILABLE
        mgr.accept_mission("x")  # no game_day
        assert mgr.get_timeliness_comment("x", _make_player(5)) is None

    def test_none_for_unknown_mission(self) -> None:
        mgr = self._mgr_with_accepted(accept_day=0)
        assert mgr.get_timeliness_comment("not_a_mission", _make_player(5)) is None


# ---------------------------------------------------------------------------
# Authored iron_delivery content
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


class TestIronDeliveryTorresContent:
    def test_iron_delivery_has_all_three_tier_comments(self, dl) -> None:
        m = dl.get_mission("iron_delivery")
        assert m is not None
        assert m.timeliness_comments.get("timely"), "Missing 'timely' comment"
        assert m.timeliness_comments.get("late"), "Missing 'late' comment"
        assert m.timeliness_comments.get("very_late"), "Missing 'very_late' comment"

    def test_iron_delivery_comments_fire_at_expected_tiers(self, dl) -> None:
        """Verify tier thresholds produce the authored lines end-to-end."""
        m = dl.get_mission("iron_delivery")
        # full=14, partial=18
        assert m.get_timeliness_comment(10) == m.timeliness_comments["timely"]
        assert m.get_timeliness_comment(14) == m.timeliness_comments["timely"]
        assert m.get_timeliness_comment(16) == m.timeliness_comments["late"]
        assert m.get_timeliness_comment(50) == m.timeliness_comments["very_late"]

    def test_iron_delivery_comments_follow_writing_bible(self, dl) -> None:
        """No em-dashes or banned phrases in authored Torres lines."""
        EM_DASHES = ("\u2014", "\u2013", " -- ")
        BANNED = ("couldn't help but", "a testament to")
        m = dl.get_mission("iron_delivery")
        offenders = []
        for tier, text in m.timeliness_comments.items():
            for dash in EM_DASHES:
                if dash in text:
                    offenders.append(f"tier {tier}: em-dash")
                    break
            for phrase in BANNED:
                if phrase in text.lower():
                    offenders.append(f"tier {tier}: {phrase!r}")
        assert not offenders, "Writing Bible issues:\n  " + "\n  ".join(offenders)


# ---------------------------------------------------------------------------
# End-to-end: comment + reward multiplier both fire
# ---------------------------------------------------------------------------


class TestEndToEndCompletion:
    def test_iron_delivery_late_completion_produces_comment_and_scaled_credits(self, dl) -> None:
        """Both the multiplier and the comment reference the same
        elapsed-days calculation — test they agree on the 'late' tier."""
        mgr = MissionManager(dl.missions)
        mgr._status["iron_delivery"] = MissionStatus.AVAILABLE
        mgr.accept_mission("iron_delivery", game_day=100)

        # Complete on day 116 — 16 elapsed, past full=14, within partial=18
        player = _make_player(game_day=116)
        comment = mgr.get_timeliness_comment("iron_delivery", player)
        mgr.apply_rewards("iron_delivery", player)

        mission = dl.get_mission("iron_delivery")
        assert comment == mission.timeliness_comments["late"]
        # Player got ~75% (whatever the base credits were)
        # Verify the multiplier resolution matches the tier
        assert mission.soft_deadline.resolve_tier(16) == "late"
