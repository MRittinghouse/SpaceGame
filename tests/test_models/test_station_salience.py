"""Tests for spacegame.models.station_salience.

SL-1 (station_legibility.md): introduces system-mission relevance for
`unique`-card demotion in the station hub view.

SL-2: investment-card gating. `investment`-typed cards do not render
until the player crosses a credit threshold OR has been introduced to
investment via the Cargo-Broker mission (sets the `investment_introduced`
flag).

SL-3 will extend this module with `get_recommended_card` for per-card
cyan-glow highlighting.

Mission objectives target *systems* (REACH_SYSTEM) or NPCs (TALK_TO_NPC,
which resolves to the NPC's home system). No objective type targets a
sub-station location ID, so mission relevance is evaluated at the system
level: when a system has any active mission objective, ALL `unique`-typed
locations at that system are elevated together.
"""

from __future__ import annotations

from spacegame.constants.flags import investment_introduced
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.station_salience import (
    INVESTMENT_UNLOCK_CREDIT_THRESHOLD,
    is_investment_unlocked,
    is_system_mission_relevant,
)


def _make_manager(missions: list[Mission]) -> MissionManager:
    """Build a MissionManager with the given missions registered."""
    return MissionManager(missions)


def _reach_system_mission(mission_id: str, system_id: str) -> Mission:
    """Construct a minimal mission with a single REACH_SYSTEM objective."""
    return Mission(
        id=mission_id,
        name=f"Mission {mission_id}",
        description="",
        objectives=[
            MissionObjective(
                type=ObjectiveType.REACH_SYSTEM,
                target_id=system_id,
                description=f"Reach {system_id}",
            )
        ],
    )


def _talk_to_npc_mission(mission_id: str, npc_id: str) -> Mission:
    """Construct a minimal mission with a single TALK_TO_NPC objective."""
    return Mission(
        id=mission_id,
        name=f"Mission {mission_id}",
        description="",
        objectives=[
            MissionObjective(
                type=ObjectiveType.TALK_TO_NPC,
                target_id=npc_id,
                description=f"Talk to {npc_id}",
            )
        ],
    )


class TestIsSystemMissionRelevant:
    """is_system_mission_relevant — does any active mission target this system?"""

    def test_returns_false_when_mission_manager_is_none(self) -> None:
        """No mission manager (tutorial states, dev launches) → not relevant."""
        assert is_system_mission_relevant(None, "iron_depths") is False

    def test_returns_false_when_no_active_missions(self) -> None:
        """Empty manager → no relevance."""
        mgr = _make_manager([])
        assert is_system_mission_relevant(mgr, "iron_depths") is False

    def test_returns_false_when_active_mission_targets_different_system(self) -> None:
        """Active mission for system A → system B is not relevant."""
        m = _reach_system_mission("m1", "the_fulcrum")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        assert is_system_mission_relevant(mgr, "iron_depths") is False

    def test_returns_true_when_reach_system_objective_targets_this_system(self) -> None:
        """The Fulcrum case: campaign mission to reach a system makes that system relevant."""
        m = _reach_system_mission("m1", "the_fulcrum")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        assert is_system_mission_relevant(mgr, "the_fulcrum") is True

    def test_returns_true_when_talk_to_npc_objective_resolves_to_this_system(self) -> None:
        """TALK_TO_NPC at an NPC whose home system is this one → relevant."""
        m = _talk_to_npc_mission("m1", "marcus_jin")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        npc_homes = {"marcus_jin": "breakstone"}
        assert is_system_mission_relevant(mgr, "breakstone", npc_homes) is True

    def test_talk_to_npc_without_npc_home_mapping_does_not_match(self) -> None:
        """If npc_home_systems isn't passed, TALK_TO_NPC objectives don't contribute."""
        m = _talk_to_npc_mission("m1", "marcus_jin")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        assert is_system_mission_relevant(mgr, "breakstone") is False

    def test_completed_mission_does_not_make_system_relevant(self) -> None:
        """Only ACTIVE missions count. Completed missions don't elevate cards."""
        m = _reach_system_mission("m1", "the_fulcrum")
        mgr = _make_manager([m])
        mgr._status["m1"] = MissionStatus.COMPLETED
        assert is_system_mission_relevant(mgr, "the_fulcrum") is False

    def test_multiple_active_missions_any_match_returns_true(self) -> None:
        """If any active mission targets the system, return True."""
        m1 = _reach_system_mission("m1", "the_fulcrum")
        m2 = _reach_system_mission("m2", "iron_depths")
        mgr = _make_manager([m1, m2])
        mgr._status["m1"] = MissionStatus.ACTIVE
        mgr._status["m2"] = MissionStatus.ACTIVE
        assert is_system_mission_relevant(mgr, "iron_depths") is True
        assert is_system_mission_relevant(mgr, "the_fulcrum") is True
        assert is_system_mission_relevant(mgr, "nexus_prime") is False


class _StubPlayer:
    """Minimal player stub for is_investment_unlocked tests.

    is_investment_unlocked reads only ``credits_earned_lifetime`` and
    ``dialogue_flags``, so a full Player (which requires Ship + ShipType)
    is unnecessary here. Tests exercising the full save/load chain or
    flag wiring through MissionManager use the real Player elsewhere.
    """

    def __init__(self, lifetime: int = 0, flags: dict[str, bool] | None = None) -> None:
        self.credits_earned_lifetime = lifetime
        self.dialogue_flags: dict[str, bool] = flags or {}


class TestIsInvestmentUnlocked:
    """is_investment_unlocked — credit threshold OR introduction flag."""

    def test_default_threshold_is_25k(self) -> None:
        """SL-2 locked decision: 25,000 CR floor."""
        assert INVESTMENT_UNLOCK_CREDIT_THRESHOLD == 25_000

    def test_returns_false_for_fresh_save(self) -> None:
        """Zero credits, no flag → locked."""
        assert is_investment_unlocked(_StubPlayer()) is False

    def test_returns_false_below_threshold_no_flag(self) -> None:
        """24,999 lifetime credits is one short of 25,000 — still locked."""
        assert is_investment_unlocked(_StubPlayer(lifetime=24_999)) is False

    def test_returns_true_at_threshold_no_flag(self) -> None:
        """Exactly 25,000 lifetime credits unlocks (boundary inclusive)."""
        assert is_investment_unlocked(_StubPlayer(lifetime=25_000)) is True

    def test_returns_true_above_threshold_no_flag(self) -> None:
        """Comfortably above threshold → unlocked via credit gate."""
        assert is_investment_unlocked(_StubPlayer(lifetime=50_000)) is True

    def test_returns_true_below_threshold_with_flag(self) -> None:
        """Cargo Broker mission has fired but credits are low → unlocked via flag."""
        flags = {investment_introduced(): True}
        assert is_investment_unlocked(_StubPlayer(lifetime=1_000, flags=flags)) is True

    def test_returns_true_when_both_gates_met(self) -> None:
        """Both gates true → unlocked (OR semantics, no toggle)."""
        flags = {investment_introduced(): True}
        assert is_investment_unlocked(_StubPlayer(lifetime=100_000, flags=flags)) is True

    def test_custom_threshold_respected(self) -> None:
        """Threshold is parametrizable for playtest tuning."""
        assert is_investment_unlocked(_StubPlayer(lifetime=11_000), threshold=10_000) is True
        assert is_investment_unlocked(_StubPlayer(lifetime=9_000), threshold=10_000) is False

    def test_falsy_flag_value_does_not_unlock(self) -> None:
        """A flag set to False (explicitly cleared) does not unlock."""
        flags = {investment_introduced(): False}
        assert is_investment_unlocked(_StubPlayer(lifetime=0, flags=flags)) is False


class TestInvestmentIntroducedFlag:
    """The flag-registry helper produces a stable string."""

    def test_flag_name_is_canonical(self) -> None:
        """Flag string is the SL-2 canonical name. Producer (mission) and
        consumer (is_investment_unlocked) must agree on this exact value."""
        assert investment_introduced() == "investment_introduced"
