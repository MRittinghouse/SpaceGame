"""Tests for spacegame.models.station_salience.

SL-1 (station_legibility.md): introduces system-mission relevance for
`unique`-card demotion in the station hub view.

SL-2: investment-card gating. `investment`-typed cards do not render
until the player crosses a credit threshold OR has been introduced to
investment via the Cargo-Broker mission (sets the `investment_introduced`
flag).

SL-3: `get_recommended_card` highlight selection. Pure function that
walks a hierarchy (mission objective → damage → cargo → faction-first →
resource opportunity → investment) and returns the most relevant card
to glow. Source enum distinguishes mission-objective glows (cyan, same
as the cantina PT-016 pattern) from broader recommendations (the card's
own accent color).

Mission objectives target *systems* (REACH_SYSTEM) or NPCs (TALK_TO_NPC,
which resolves to the NPC's home system). No objective type targets a
sub-station location ID, so mission relevance is evaluated at the system
level: when a system has any active mission objective, ALL `unique`-typed
locations at that system are elevated together.
"""

from __future__ import annotations

from spacegame.constants.flags import investment_introduced
from spacegame.models.location import Location
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.station_salience import (
    INVESTMENT_UNLOCK_CREDIT_THRESHOLD,
    RecommendationSource,
    get_recommended_card,
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


# ---------------------------------------------------------------------------
# SL-3: get_recommended_card hierarchy
# ---------------------------------------------------------------------------


def _make_ship_type(combat_hull: int = 100, cargo_capacity: int = 50) -> ShipType:
    """Minimal ShipType for SL-3 tests that need real hull/cargo math."""
    return ShipType(
        id="test_shuttle",
        name="Test Shuttle",
        ship_class="light",
        description="",
        cargo_capacity=cargo_capacity,
        fuel_capacity=100,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
        combat_hull=combat_hull,
    )


def _make_player(
    *,
    hull_pct: float = 1.0,
    cargo: dict[str, int] | None = None,
    systems_visited: set[str] | None = None,
    lifetime_credits: int = 0,
    flags: dict[str, bool] | None = None,
) -> Player:
    """Build a minimal Player with controllable hull, cargo, faction history."""
    st = _make_ship_type()
    ship = Ship(ship_type=st, current_fuel=100)
    ship.current_hull = max(1, int(st.combat_hull * hull_pct))
    if cargo is not None:
        ship.current_cargo = dict(cargo)
    p = Player(
        name="Test",
        credits=1000,
        current_system_id="test_system",
        ship=ship,
    )
    p.credits_earned_lifetime = lifetime_credits
    if systems_visited is not None:
        p.systems_visited = set(systems_visited)
    if flags is not None:
        p.dialogue_flags = dict(flags)
    return p


def _make_loc(loc_id: str, loc_type: str, system_id: str = "test_system") -> Location:
    """Build a minimal Location."""
    return Location(
        id=loc_id,
        name=f"Test {loc_id}",
        location_type=loc_type,
        description="",
        flavor_text="",
        system_id=system_id,
    )


# Locations on a typical mid-tier station — has every category we test against.
def _full_station_locs(system_id: str = "test_system") -> list[Location]:
    return [
        _make_loc("test_market", "market", system_id),
        _make_loc("test_repair", "repair_bay", system_id),
        _make_loc("test_cantina", "cantina", system_id),
        _make_loc("test_mining", "mining", system_id),
        _make_loc("test_investment", "investment", system_id),
    ]


def _system_with_factions_visited(*systems: str) -> set[str]:
    return set(systems)


class TestGetRecommendedCard:
    """Hierarchy: mission > damage > cargo > faction-first > resource > investment."""

    def test_returns_none_when_no_relevant_state(self) -> None:
        """Player healthy, has cargo, faction already visited, no missions →
        no recommendation. The function must produce None rather than
        defaulting to a card."""
        player = _make_player(
            hull_pct=1.0,
            cargo={"test_commodity": 5},  # not empty
            systems_visited={"test_system", "another_in_same_faction"},
        )
        # Locations include only neutral types so no resource branch fires.
        locs = [
            _make_loc("test_repair", "repair_bay"),
            _make_loc("test_cantina", "cantina"),
        ]
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=locs,
            mission_manager=None,
        )
        assert result is None

    def test_mission_objective_returns_cantina_with_mission_source(self) -> None:
        """TALK_TO_NPC with NPC at this system → cantina, MISSION_OBJECTIVE source."""
        m = Mission(
            id="m1",
            name="Talk",
            description="",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.TALK_TO_NPC,
                    target_id="test_npc",
                    description="Talk to test_npc",
                )
            ],
        )
        mgr = MissionManager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        player = _make_player(cargo={"x": 1}, systems_visited={"test_system", "other"})
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=_full_station_locs(),
            mission_manager=mgr,
            npc_home_systems={"test_npc": "test_system"},
        )
        assert result == ("test_cantina", RecommendationSource.MISSION_OBJECTIVE)

    def test_damaged_hull_returns_repair_bay(self) -> None:
        """Hull at 50% with repair_bay available → repair_bay, RECOMMENDATION."""
        player = _make_player(
            hull_pct=0.5,
            cargo={"x": 1},
            systems_visited={"test_system", "other"},
        )
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=_full_station_locs(),
            mission_manager=None,
        )
        assert result == ("test_repair", RecommendationSource.RECOMMENDATION)

    def test_damaged_hull_no_repair_bay_falls_through(self) -> None:
        """Hull damaged but station has no repair_bay → next branch wins."""
        player = _make_player(
            hull_pct=0.5,
            cargo={},  # empty → market branch
            systems_visited={"test_system", "other"},
        )
        # Station has market but no repair_bay
        locs = [_make_loc("test_market", "market"), _make_loc("test_cantina", "cantina")]
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=locs,
            mission_manager=None,
        )
        assert result == ("test_market", RecommendationSource.RECOMMENDATION)

    def test_empty_cargo_returns_market(self) -> None:
        """Empty cargo + market available → market, RECOMMENDATION."""
        player = _make_player(
            hull_pct=1.0,
            cargo={},
            systems_visited={"test_system", "other"},
        )
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=_full_station_locs(),
            mission_manager=None,
        )
        assert result == ("test_market", RecommendationSource.RECOMMENDATION)

    def test_first_faction_visit_returns_cantina(self) -> None:
        """This is the only system in this faction → cantina, RECOMMENDATION.

        Faction-first-visit is detected when the player has no other
        systems-visited entries belonging to the same faction. A cantina
        introduces the faction's NPCs.
        """
        player = _make_player(
            hull_pct=1.0,
            cargo={"x": 1},  # not empty (skips market branch)
            systems_visited={"test_system"},  # this is the only system visited
        )
        locs = [
            _make_loc("test_market", "market"),
            _make_loc("test_cantina", "cantina"),
        ]
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=locs,
            mission_manager=None,
            faction_systems={"test_faction": {"test_system", "another_test_system"}},
        )
        assert result == ("test_cantina", RecommendationSource.RECOMMENDATION)

    def test_faction_already_visited_skips_cantina_branch(self) -> None:
        """Having visited another system in this faction → no faction-first branch."""
        player = _make_player(
            hull_pct=1.0,
            cargo={"x": 1},
            systems_visited={"test_system", "another_test_system"},
        )
        locs = [
            _make_loc("test_market", "market"),
            _make_loc("test_cantina", "cantina"),
        ]
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=locs,
            mission_manager=None,
            faction_systems={"test_faction": {"test_system", "another_test_system"}},
        )
        # No higher branch fires; faction-first doesn't apply → None.
        assert result is None

    def test_mining_system_returns_mining(self) -> None:
        """Station has mining + cargo space → mining, RECOMMENDATION."""
        player = _make_player(
            hull_pct=1.0,
            cargo={"x": 1},  # not empty (skips market)
            systems_visited={"test_system", "other"},
        )
        locs = [
            _make_loc("test_market", "market"),
            _make_loc("test_mining", "mining"),
        ]
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=locs,
            mission_manager=None,
        )
        assert result == ("test_mining", RecommendationSource.RECOMMENDATION)

    def test_investment_unlocked_returns_investment(self) -> None:
        """Investment unlocked (via threshold) + station has investment → investment."""
        player = _make_player(
            hull_pct=1.0,
            cargo={"x": 1},
            systems_visited={"test_system", "other"},
            lifetime_credits=INVESTMENT_UNLOCK_CREDIT_THRESHOLD,
        )
        locs = [
            _make_loc("test_market", "market"),
            _make_loc("test_investment", "investment"),
        ]
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=locs,
            mission_manager=None,
        )
        assert result == ("test_investment", RecommendationSource.RECOMMENDATION)

    def test_investment_locked_does_not_recommend(self) -> None:
        """Investment locked → no investment branch; falls through."""
        player = _make_player(
            hull_pct=1.0,
            cargo={"x": 1},
            systems_visited={"test_system", "other"},
            lifetime_credits=0,
        )
        locs = [_make_loc("test_investment", "investment")]
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=locs,
            mission_manager=None,
        )
        assert result is None

    def test_hierarchy_mission_beats_damage(self) -> None:
        """Both mission objective and damaged hull active → mission wins."""
        m = Mission(
            id="m1",
            name="Talk",
            description="",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.TALK_TO_NPC,
                    target_id="test_npc",
                    description="",
                )
            ],
        )
        mgr = MissionManager([m])
        mgr._status["m1"] = MissionStatus.ACTIVE
        player = _make_player(
            hull_pct=0.3, cargo={"x": 1}, systems_visited={"test_system", "other"}
        )
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=_full_station_locs(),
            mission_manager=mgr,
            npc_home_systems={"test_npc": "test_system"},
        )
        assert result == ("test_cantina", RecommendationSource.MISSION_OBJECTIVE)

    def test_hierarchy_damage_beats_cargo(self) -> None:
        """Damaged hull AND empty cargo → damage wins."""
        player = _make_player(hull_pct=0.5, cargo={}, systems_visited={"test_system", "other"})
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=_full_station_locs(),
            mission_manager=None,
        )
        assert result == ("test_repair", RecommendationSource.RECOMMENDATION)

    def test_damage_threshold_is_inclusive_of_70_percent(self) -> None:
        """Hull at exactly 70% should NOT trigger repair (default threshold is < 0.7)."""
        player = _make_player(
            hull_pct=0.7, cargo={"x": 1}, systems_visited={"test_system", "other"}
        )
        result = get_recommended_card(
            player=player,
            system_id="test_system",
            faction_id="test_faction",
            locations=_full_station_locs(),
            mission_manager=None,
        )
        # Hull at 70% is not damaged enough (strict <). Falls through.
        assert result != ("test_repair", RecommendationSource.RECOMMENDATION)
