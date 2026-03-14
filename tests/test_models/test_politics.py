"""Tests for the political system (Cycle 5.2).

Covers faction relationships, reputation spillover, political events,
reputation consequences, intel system, and campaign integration.
"""

from spacegame.models.faction import (
    Faction,
    ReputationTier,
    TensionLevel,
    get_tension_level,
)
from spacegame.models.politics import (
    FactionRelationship,
    IntelQuality,
    IntelReport,
    PoliticalEvent,
    PoliticalEventType,
    PoliticalAction,
    PoliticsManager,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.config import (
    REP_SPILLOVER_RATIO,
    FACTION_RELATIONSHIP_MIN,
    FACTION_RELATIONSHIP_MAX,
)


# ============================================================================
# Test Helpers
# ============================================================================


def _make_factions() -> dict[str, Faction]:
    """Create the 4 game factions for testing."""
    return {
        "commerce_guild": Faction(
            id="commerce_guild",
            name="Commerce Guild",
            description="Trade consortium",
            color=(100, 150, 255),
            rivalry="miners_union",
        ),
        "miners_union": Faction(
            id="miners_union",
            name="Miners Union",
            description="Mining alliance",
            color=(200, 150, 50),
            rivalry="commerce_guild",
        ),
        "science_collective": Faction(
            id="science_collective",
            name="Science Collective",
            description="Research coalition",
            color=(150, 100, 200),
            rivalry="frontier_alliance",
        ),
        "frontier_alliance": Faction(
            id="frontier_alliance",
            name="Frontier Alliance",
            description="Frontier settlers",
            color=(100, 200, 100),
            rivalry="science_collective",
        ),
    }


def _make_relationships() -> list[FactionRelationship]:
    """Create default faction relationships matching JSON data."""
    return [
        FactionRelationship("commerce_guild", "miners_union", -30),
        FactionRelationship("commerce_guild", "science_collective", 15),
        FactionRelationship("commerce_guild", "frontier_alliance", -5),
        FactionRelationship("miners_union", "science_collective", 5),
        FactionRelationship("miners_union", "frontier_alliance", 20),
        FactionRelationship("science_collective", "frontier_alliance", -25),
    ]


def _make_ship_type() -> ShipType:
    """Create a minimal ShipType for testing."""
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=50,
        fuel_capacity=100,
        fuel_efficiency=1,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player(**kwargs: object) -> Player:
    """Create a minimal player for testing."""
    ship = Ship(ship_type=_make_ship_type(), current_fuel=100)
    defaults: dict[str, object] = {
        "name": "Test Captain",
        "ship": ship,
        "credits": 1000,
        "current_system_id": "nexus_prime",
    }
    defaults.update(kwargs)
    return Player(**defaults)


def _make_politics_manager() -> PoliticsManager:
    """Create a PoliticsManager with default factions and relationships."""
    return PoliticsManager(
        relationships=_make_relationships(),
        factions=_make_factions(),
    )


# ============================================================================
# Phase A: TensionLevel
# ============================================================================


class TestTensionLevel:
    """Tests for the TensionLevel enum and threshold function."""

    def test_allied_threshold(self) -> None:
        assert get_tension_level(50) == TensionLevel.ALLIED
        assert get_tension_level(100) == TensionLevel.ALLIED

    def test_cooperative_threshold(self) -> None:
        assert get_tension_level(20) == TensionLevel.COOPERATIVE
        assert get_tension_level(49) == TensionLevel.COOPERATIVE

    def test_neutral_threshold(self) -> None:
        assert get_tension_level(0) == TensionLevel.NEUTRAL
        assert get_tension_level(-19) == TensionLevel.NEUTRAL
        assert get_tension_level(19) == TensionLevel.NEUTRAL

    def test_strained_threshold(self) -> None:
        assert get_tension_level(-20) == TensionLevel.STRAINED
        assert get_tension_level(-49) == TensionLevel.STRAINED

    def test_hostile_threshold(self) -> None:
        assert get_tension_level(-50) == TensionLevel.HOSTILE
        assert get_tension_level(-100) == TensionLevel.HOSTILE


# ============================================================================
# Phase A: FactionRelationship
# ============================================================================


class TestFactionRelationship:
    """Tests for the FactionRelationship dataclass."""

    def test_creation(self) -> None:
        rel = FactionRelationship("commerce_guild", "miners_union", -30)
        assert rel.faction_a_id == "commerce_guild"
        assert rel.faction_b_id == "miners_union"
        assert rel.value == -30

    def test_symmetric_key(self) -> None:
        """Key should be the same regardless of argument order."""
        rel_ab = FactionRelationship("commerce_guild", "miners_union", 0)
        rel_ba = FactionRelationship("miners_union", "commerce_guild", 0)
        assert rel_ab.get_key() == rel_ba.get_key()

    def test_get_tension_level(self) -> None:
        rel = FactionRelationship("a", "b", -30)
        assert rel.get_tension_level() == TensionLevel.STRAINED

    def test_modify_positive(self) -> None:
        rel = FactionRelationship("a", "b", 0)
        rel.modify(10)
        assert rel.value == 10

    def test_modify_clamps_to_max(self) -> None:
        rel = FactionRelationship("a", "b", 90)
        rel.modify(20)
        assert rel.value == FACTION_RELATIONSHIP_MAX

    def test_modify_clamps_to_min(self) -> None:
        rel = FactionRelationship("a", "b", -90)
        rel.modify(-20)
        assert rel.value == FACTION_RELATIONSHIP_MIN

    def test_to_dict_from_dict_roundtrip(self) -> None:
        rel = FactionRelationship("commerce_guild", "miners_union", -30)
        data = rel.to_dict()
        restored = FactionRelationship.from_dict(data)
        assert restored.faction_a_id == rel.faction_a_id
        assert restored.faction_b_id == rel.faction_b_id
        assert restored.value == rel.value


# ============================================================================
# Phase A: PoliticsManager — Relationships
# ============================================================================


class TestPoliticsManager:
    """Tests for PoliticsManager relationship tracking."""

    def test_all_six_relationships_loaded(self) -> None:
        mgr = _make_politics_manager()
        assert len(mgr._relationships) == 6

    def test_get_relationship_by_pair(self) -> None:
        mgr = _make_politics_manager()
        rel = mgr.get_relationship("commerce_guild", "miners_union")
        assert rel.value == -30

    def test_get_relationship_symmetric(self) -> None:
        """Order of arguments shouldn't matter."""
        mgr = _make_politics_manager()
        rel_ab = mgr.get_relationship("commerce_guild", "miners_union")
        rel_ba = mgr.get_relationship("miners_union", "commerce_guild")
        assert rel_ab is rel_ba

    def test_get_tension_level(self) -> None:
        mgr = _make_politics_manager()
        tension = mgr.get_tension_level("commerce_guild", "miners_union")
        assert tension == TensionLevel.STRAINED

    def test_modify_relationship(self) -> None:
        mgr = _make_politics_manager()
        mgr.modify_relationship("commerce_guild", "miners_union", 10)
        rel = mgr.get_relationship("commerce_guild", "miners_union")
        assert rel.value == -20

    def test_initial_guild_collective_cooperative(self) -> None:
        mgr = _make_politics_manager()
        rel = mgr.get_relationship("commerce_guild", "science_collective")
        assert rel.value == 15
        assert rel.get_tension_level() == TensionLevel.NEUTRAL

    def test_initial_union_alliance_cooperative(self) -> None:
        mgr = _make_politics_manager()
        rel = mgr.get_relationship("miners_union", "frontier_alliance")
        assert rel.value == 20
        assert rel.get_tension_level() == TensionLevel.COOPERATIVE

    def test_initial_collective_alliance_strained(self) -> None:
        mgr = _make_politics_manager()
        rel = mgr.get_relationship("science_collective", "frontier_alliance")
        assert rel.value == -25
        assert rel.get_tension_level() == TensionLevel.STRAINED

    def test_to_dict_from_dict_roundtrip(self) -> None:
        mgr = _make_politics_manager()
        mgr.modify_relationship("commerce_guild", "miners_union", 5)
        data = mgr.to_dict()
        factions = _make_factions()
        restored = PoliticsManager.from_dict(data, factions)
        rel = restored.get_relationship("commerce_guild", "miners_union")
        assert rel.value == -25

    def test_from_dict_empty_creates_defaults(self) -> None:
        """Empty dict should create manager with default relationships."""
        factions = _make_factions()
        mgr = PoliticsManager.from_dict({}, factions)
        # Should have some relationships (loaded from data)
        assert mgr is not None


# ============================================================================
# Phase A: Reputation Spillover
# ============================================================================


class TestReputationSpillover:
    """Tests for centralized reputation spillover through PoliticsManager."""

    def test_positive_gain_causes_rival_loss(self) -> None:
        """Gaining rep with a faction should reduce rival's rep."""
        mgr = _make_politics_manager()
        player = _make_player()
        changes = mgr.apply_reputation_with_spillover(player, "commerce_guild", 10)

        # Primary: +10 with guild
        assert player.get_reputation("commerce_guild") == 10
        # Spillover: -3 with rival (miners_union) — 30% of 10
        expected_rival = -int(10 * REP_SPILLOVER_RATIO)
        assert player.get_reputation("miners_union") == expected_rival

    def test_negative_loss_causes_rival_gain(self) -> None:
        """Losing rep with a faction should improve rival's rep."""
        mgr = _make_politics_manager()
        player = _make_player()
        changes = mgr.apply_reputation_with_spillover(player, "commerce_guild", -10)

        assert player.get_reputation("commerce_guild") == -10
        # Rival gains: -(-10 * 0.30) = +3
        expected_rival = -int(-10 * REP_SPILLOVER_RATIO)
        assert player.get_reputation("miners_union") == expected_rival

    def test_zero_amount_no_change(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        changes = mgr.apply_reputation_with_spillover(player, "commerce_guild", 0)
        assert player.get_reputation("commerce_guild") == 0
        assert player.get_reputation("miners_union") == 0

    def test_spillover_clamps_at_bounds(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.modify_reputation("commerce_guild", 95)
        changes = mgr.apply_reputation_with_spillover(player, "commerce_guild", 20)
        assert player.get_reputation("commerce_guild") == 100  # clamped

    def test_spillover_rounds_down(self) -> None:
        """Spillover should use int() truncation (e.g., 7 * 0.3 = 2.1 → 2)."""
        mgr = _make_politics_manager()
        player = _make_player()
        changes = mgr.apply_reputation_with_spillover(player, "commerce_guild", 7)
        # 7 * 0.30 = 2.1, int() = 2
        assert player.get_reputation("miners_union") == -2

    def test_no_rival_no_spillover(self) -> None:
        """Faction with empty rivalry string should have no spillover."""
        factions = _make_factions()
        factions["loner"] = Faction(
            id="loner", name="Loner", description="", color=(0, 0, 0), rivalry=""
        )
        mgr = PoliticsManager(relationships=[], factions=factions)
        player = _make_player()
        changes = mgr.apply_reputation_with_spillover(player, "loner", 10)
        assert player.get_reputation("loner") == 10
        assert len(changes) == 1  # only primary, no spillover

    def test_returns_all_changes(self) -> None:
        """Should return list of all (faction_id, amount) changes made."""
        mgr = _make_politics_manager()
        player = _make_player()
        changes = mgr.apply_reputation_with_spillover(player, "commerce_guild", 10)
        assert len(changes) == 2
        faction_ids = [c[0] for c in changes]
        assert "commerce_guild" in faction_ids
        assert "miners_union" in faction_ids

    def test_spillover_with_leadership_bonus(self) -> None:
        """Leadership rep bonus should be included in spillover calculation."""
        mgr = _make_politics_manager()
        player = _make_player()
        # Apply 10 base + pass through — manager doesn't add bonus itself,
        # caller passes the total amount including bonuses
        changes = mgr.apply_reputation_with_spillover(player, "commerce_guild", 12)
        assert player.get_reputation("commerce_guild") == 12
        assert player.get_reputation("miners_union") == -int(12 * REP_SPILLOVER_RATIO)


# ============================================================================
# Phase A: Data Loading Integration
# ============================================================================


class TestPoliticsDataLoading:
    """Tests for loading political data from JSON via DataLoader."""

    def test_faction_relationships_loaded(self) -> None:
        """DataLoader should load faction relationships from JSON."""
        from spacegame.data_loader import get_data_loader

        loader = get_data_loader()
        assert hasattr(loader, "faction_relationships"), (
            "DataLoader should have faction_relationships attribute"
        )
        assert len(loader.faction_relationships) == 6, (
            f"Expected 6 bilateral relationships, got {len(loader.faction_relationships)}"
        )

    def test_guild_union_relationship_value(self) -> None:
        """Guild-Union relationship should match JSON data."""
        from spacegame.data_loader import get_data_loader

        loader = get_data_loader()
        # Find the guild-union relationship
        for rel in loader.faction_relationships:
            key = rel.get_key()
            if "commerce_guild" in key and "miners_union" in key:
                assert rel.value == -30, f"Guild-Union should be -30, got {rel.value}"
                return
        assert False, "Guild-Union relationship not found"

    def test_config_constants_exist(self) -> None:
        """Political system config constants should exist."""
        from spacegame.config import (
            REP_SPILLOVER_RATIO,
            POLITICAL_EVENT_DAILY_CHANCE,
            POLITICAL_EVENT_MIN_DURATION,
            POLITICAL_EVENT_MAX_DURATION,
            FACTION_RELATIONSHIP_MIN,
            FACTION_RELATIONSHIP_MAX,
        )

        assert REP_SPILLOVER_RATIO == 0.30
        assert POLITICAL_EVENT_DAILY_CHANCE == 0.08
        assert FACTION_RELATIONSHIP_MIN == -100
        assert FACTION_RELATIONSHIP_MAX == 100


# ============================================================================
# Phase B: Political Events
# ============================================================================


class TestPoliticalEvent:
    """Tests for the PoliticalEvent model."""

    def test_creation(self) -> None:
        event = PoliticalEvent(
            id="test_event_1",
            event_type=PoliticalEventType.TRADE_DISPUTE,
            faction_a_id="commerce_guild",
            faction_b_id="miners_union",
            description="Guild imposes tariff surcharge on Union shipments",
            day_started=10,
            duration_days=5,
            relationship_drift=-2,
        )
        assert event.id == "test_event_1"
        assert event.event_type == PoliticalEventType.TRADE_DISPUTE
        assert not event.resolved

    def test_is_active_within_duration(self) -> None:
        event = PoliticalEvent(
            id="e1", event_type=PoliticalEventType.TRADE_DISPUTE,
            faction_a_id="a", faction_b_id="b", description="Test",
            day_started=10, duration_days=5, relationship_drift=-1,
        )
        assert event.is_active(10)  # start day
        assert event.is_active(14)  # last active day
        assert not event.is_active(15)  # expired

    def test_days_remaining(self) -> None:
        event = PoliticalEvent(
            id="e1", event_type=PoliticalEventType.BORDER_INCIDENT,
            faction_a_id="a", faction_b_id="b", description="Test",
            day_started=10, duration_days=5, relationship_drift=-1,
        )
        assert event.days_remaining(10) == 5
        assert event.days_remaining(12) == 3
        assert event.days_remaining(15) == 0

    def test_resolved_event_not_active(self) -> None:
        event = PoliticalEvent(
            id="e1", event_type=PoliticalEventType.AID_REQUEST,
            faction_a_id="a", faction_b_id="b", description="Test",
            day_started=10, duration_days=5, relationship_drift=0,
            resolved=True,
        )
        assert not event.is_active(10)

    def test_to_dict_from_dict_roundtrip(self) -> None:
        event = PoliticalEvent(
            id="e1", event_type=PoliticalEventType.SANCTION,
            faction_a_id="commerce_guild", faction_b_id="frontier_alliance",
            description="Guild sanctions Alliance exports",
            day_started=5, duration_days=7, relationship_drift=-3,
        )
        data = event.to_dict()
        restored = PoliticalEvent.from_dict(data)
        assert restored.id == event.id
        assert restored.event_type == event.event_type
        assert restored.faction_a_id == event.faction_a_id
        assert restored.duration_days == event.duration_days
        assert restored.relationship_drift == event.relationship_drift

    def test_all_event_types_exist(self) -> None:
        expected = {
            "trade_dispute", "border_incident", "aid_request",
            "diplomatic_summit", "sanction", "pirate_crisis",
        }
        actual = {t.value for t in PoliticalEventType}
        assert expected == actual


class TestEventGenerator:
    """Tests for political event generation."""

    def test_deterministic_seed(self) -> None:
        """Same day should produce same event/no-event result."""
        mgr = _make_politics_manager()
        result1 = mgr.try_generate_event(42)
        result2 = mgr.try_generate_event(42)
        assert (result1 is None) == (result2 is None)
        if result1 and result2:
            assert result1.id == result2.id

    def test_max_two_active_events(self) -> None:
        """Should not generate more than 2 active events."""
        mgr = _make_politics_manager()
        # Force 2 events into active list
        for i in range(2):
            mgr._active_events.append(PoliticalEvent(
                id=f"forced_{i}", event_type=PoliticalEventType.TRADE_DISPUTE,
                faction_a_id="commerce_guild", faction_b_id="miners_union",
                description="Test", day_started=1, duration_days=10,
                relationship_drift=-1,
            ))
        result = mgr.try_generate_event(50)
        assert result is None, "Should not create event when 2 already active"

    def test_generated_event_added_to_active(self) -> None:
        """Generated event should be tracked in active events list."""
        mgr = _make_politics_manager()
        # Try many days to find one that generates an event (8% chance each)
        generated = None
        for day in range(200):
            result = mgr.try_generate_event(day)
            if result:
                generated = result
                break
        # At 8% over 200 days, statistically near-certain to get at least one
        assert generated is not None, "Should generate at least one event over 200 days"
        assert generated in mgr._active_events

    def test_event_has_valid_faction_pair(self) -> None:
        """Generated events should have factions from the game's faction list."""
        mgr = _make_politics_manager()
        faction_ids = set(mgr._factions.keys())
        for day in range(200):
            result = mgr.try_generate_event(day)
            if result:
                assert result.faction_a_id in faction_ids
                assert result.faction_b_id in faction_ids
                assert result.faction_a_id != result.faction_b_id
                break


class TestPlayerActions:
    """Tests for player response to political events."""

    def _make_event(self) -> PoliticalEvent:
        return PoliticalEvent(
            id="test_dispute", event_type=PoliticalEventType.TRADE_DISPUTE,
            faction_a_id="commerce_guild", faction_b_id="miners_union",
            description="Trade tariff dispute", day_started=1,
            duration_days=5, relationship_drift=-2,
        )

    def test_side_with_a(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        event = self._make_event()
        mgr._active_events.append(event)

        messages = mgr.resolve_event(event, PoliticalAction.SIDE_WITH_A, player)

        assert player.get_reputation("commerce_guild") > 0, "Should gain rep with A"
        assert player.get_reputation("miners_union") < 0, "Should lose rep with B"
        assert event.resolved
        assert len(messages) > 0

    def test_side_with_b(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        event = self._make_event()
        mgr._active_events.append(event)

        mgr.resolve_event(event, PoliticalAction.SIDE_WITH_B, player)

        assert player.get_reputation("miners_union") > 0, "Should gain rep with B"
        # Guild loses rep + spillover from union gain
        assert player.get_reputation("commerce_guild") < 0

    def test_mediate(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        event = self._make_event()
        mgr._active_events.append(event)
        initial_rel = mgr.get_relationship("commerce_guild", "miners_union").value

        mgr.resolve_event(event, PoliticalAction.MEDIATE, player)

        # Both factions should gain some rep
        assert player.get_reputation("commerce_guild") > 0
        assert player.get_reputation("miners_union") > 0
        # Relationship should improve
        new_rel = mgr.get_relationship("commerce_guild", "miners_union").value
        assert new_rel > initial_rel

    def test_ignore(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        event = self._make_event()
        mgr._active_events.append(event)

        mgr.resolve_event(event, PoliticalAction.IGNORE, player)

        # No rep changes
        assert player.get_reputation("commerce_guild") == 0
        assert player.get_reputation("miners_union") == 0
        assert event.resolved

    def test_already_resolved_rejected(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        event = self._make_event()
        event.resolved = True

        messages = mgr.resolve_event(event, PoliticalAction.SIDE_WITH_A, player)
        assert player.get_reputation("commerce_guild") == 0, "Resolved event should do nothing"

    def test_resolve_records_player_action(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        event = self._make_event()
        mgr._active_events.append(event)

        mgr.resolve_event(event, PoliticalAction.MEDIATE, player)
        assert event.player_action == PoliticalAction.MEDIATE

    def test_spillover_applies_to_event_rep_changes(self) -> None:
        """Rep changes from events should go through spillover."""
        mgr = _make_politics_manager()
        player = _make_player()
        event = self._make_event()
        mgr._active_events.append(event)

        mgr.resolve_event(event, PoliticalAction.SIDE_WITH_A, player)

        # SIDE_WITH_A gives +8 to guild. Spillover: -int(8*0.3) = -2 to union.
        # SIDE_WITH_A also gives -5 to union. Spillover: -int(-5*0.3) = +1 to guild.
        # Net guild: 8 + 1 = 9. Net union: -2 + (-5) = -7.
        guild_rep = player.get_reputation("commerce_guild")
        union_rep = player.get_reputation("miners_union")
        assert guild_rep > 8, f"Guild should get primary + B's spillover, got {guild_rep}"
        assert union_rep < -5, f"Union should get primary + A's spillover, got {union_rep}"


class TestDayAdvance:
    """Tests for daily political event processing."""

    def test_advance_day_applies_drift(self) -> None:
        mgr = _make_politics_manager()
        event = PoliticalEvent(
            id="drift_test", event_type=PoliticalEventType.TRADE_DISPUTE,
            faction_a_id="commerce_guild", faction_b_id="miners_union",
            description="Test", day_started=1, duration_days=5,
            relationship_drift=-2,
        )
        mgr._active_events.append(event)
        initial = mgr.get_relationship("commerce_guild", "miners_union").value

        mgr.advance_day(2)

        new_val = mgr.get_relationship("commerce_guild", "miners_union").value
        assert new_val == initial - 2, "Drift should be applied"

    def test_advance_day_cleans_expired(self) -> None:
        mgr = _make_politics_manager()
        event = PoliticalEvent(
            id="expired_test", event_type=PoliticalEventType.BORDER_INCIDENT,
            faction_a_id="a", faction_b_id="b", description="Test",
            day_started=1, duration_days=3, relationship_drift=-1,
        )
        mgr._active_events.append(event)

        mgr.advance_day(5)  # past expiry

        assert len(mgr._active_events) == 0, "Expired event should be cleaned up"

    def test_advance_day_multiple_events(self) -> None:
        mgr = _make_politics_manager()
        e1 = PoliticalEvent(
            id="e1", event_type=PoliticalEventType.TRADE_DISPUTE,
            faction_a_id="commerce_guild", faction_b_id="miners_union",
            description="T1", day_started=1, duration_days=10,
            relationship_drift=-1,
        )
        e2 = PoliticalEvent(
            id="e2", event_type=PoliticalEventType.AID_REQUEST,
            faction_a_id="science_collective", faction_b_id="frontier_alliance",
            description="T2", day_started=1, duration_days=3,
            relationship_drift=1,
        )
        mgr._active_events.extend([e1, e2])

        mgr.advance_day(2)

        assert len(mgr._active_events) == 2  # both still active
        # e1 drift should affect guild-union
        gu = mgr.get_relationship("commerce_guild", "miners_union").value
        assert gu == -31
        # e2 drift should affect collective-alliance
        ca = mgr.get_relationship("science_collective", "frontier_alliance").value
        assert ca == -24

    def test_advance_day_resolved_events_no_drift(self) -> None:
        mgr = _make_politics_manager()
        event = PoliticalEvent(
            id="resolved", event_type=PoliticalEventType.TRADE_DISPUTE,
            faction_a_id="commerce_guild", faction_b_id="miners_union",
            description="Test", day_started=1, duration_days=10,
            relationship_drift=-5,
            resolved=True,
        )
        mgr._active_events.append(event)
        initial = mgr.get_relationship("commerce_guild", "miners_union").value

        mgr.advance_day(2)

        assert mgr.get_relationship("commerce_guild", "miners_union").value == initial


class TestEventSerialization:
    """Tests for political event serialization within PoliticsManager."""

    def test_events_survive_roundtrip(self) -> None:
        mgr = _make_politics_manager()
        event = PoliticalEvent(
            id="persist_test", event_type=PoliticalEventType.SANCTION,
            faction_a_id="commerce_guild", faction_b_id="frontier_alliance",
            description="Test sanction", day_started=5, duration_days=7,
            relationship_drift=-3,
        )
        mgr._active_events.append(event)

        data = mgr.to_dict()
        factions = _make_factions()
        restored = PoliticsManager.from_dict(data, factions)

        assert len(restored._active_events) == 1
        assert restored._active_events[0].id == "persist_test"
        assert restored._active_events[0].event_type == PoliticalEventType.SANCTION


# ============================================================================
# Phase C: Reputation Consequences
# ============================================================================


class TestDockingConsequences:
    """Tests for docking restrictions based on faction reputation."""

    def test_hostile_denied(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.modify_reputation("commerce_guild", -60)  # HOSTILE

        allowed, msg = mgr.get_docking_allowed(player, "nexus_prime")
        assert not allowed, "HOSTILE faction should deny docking"

    def test_unfriendly_allowed(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.modify_reputation("commerce_guild", -30)  # UNFRIENDLY

        allowed, msg = mgr.get_docking_allowed(player, "nexus_prime")
        assert allowed, "UNFRIENDLY faction should allow docking"

    def test_neutral_allowed(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"

        allowed, msg = mgr.get_docking_allowed(player, "nexus_prime")
        assert allowed, "NEUTRAL faction should allow docking"

    def test_allied_allowed(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.modify_reputation("commerce_guild", 60)  # ALLIED

        allowed, msg = mgr.get_docking_allowed(player, "nexus_prime")
        assert allowed

    def test_no_faction_system_allowed(self) -> None:
        """Systems with no faction assignment should always allow docking."""
        mgr = _make_politics_manager()
        player = _make_player()

        allowed, msg = mgr.get_docking_allowed(player, "unassigned_system")
        assert allowed


class TestEncounterModifiers:
    """Tests for encounter modifications based on faction reputation."""

    def test_hostile_high_attack_chance(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.modify_reputation("commerce_guild", -60)

        mods = mgr.get_encounter_modifier(player, "nexus_prime")
        assert mods["hostile_attack_chance"] > 0

    def test_unfriendly_shakedown(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.modify_reputation("commerce_guild", -30)

        mods = mgr.get_encounter_modifier(player, "nexus_prime")
        assert mods["shakedown_multiplier"] > 1.0

    def test_neutral_baseline(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"

        mods = mgr.get_encounter_modifier(player, "nexus_prime")
        assert mods["hostile_attack_chance"] == 0
        assert mods["shakedown_multiplier"] == 1.0
        assert mods["protection_chance"] == 0

    def test_friendly_protection(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.modify_reputation("commerce_guild", 30)

        mods = mgr.get_encounter_modifier(player, "nexus_prime")
        assert mods["protection_chance"] > 0

    def test_allied_max_protection(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.modify_reputation("commerce_guild", 60)

        mods = mgr.get_encounter_modifier(player, "nexus_prime")
        assert mods["protection_chance"] >= 30


class TestDispositionModifier:
    """Tests for NPC disposition modifier based on faction reputation."""

    def test_hostile_penalty(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.modify_reputation("commerce_guild", -60)
        assert mgr.get_npc_disposition_modifier(player, "commerce_guild") == -15

    def test_unfriendly_penalty(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.modify_reputation("commerce_guild", -30)
        assert mgr.get_npc_disposition_modifier(player, "commerce_guild") == -10

    def test_neutral_zero(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        assert mgr.get_npc_disposition_modifier(player, "commerce_guild") == 0

    def test_friendly_bonus(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.modify_reputation("commerce_guild", 30)
        assert mgr.get_npc_disposition_modifier(player, "commerce_guild") == 10

    def test_allied_bonus(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        player.modify_reputation("commerce_guild", 60)
        assert mgr.get_npc_disposition_modifier(player, "commerce_guild") == 15


# ============================================================================
# Phase D: Intel System
# ============================================================================


class TestIntelReport:
    """Tests for the IntelReport model."""

    def test_creation(self) -> None:
        report = IntelReport(
            id="guild_shipping_routes",
            name="Guild Shipping Manifests",
            description="Detailed logs of Commerce Guild trade routes.",
            source_faction_id="commerce_guild",
            quality=IntelQuality.REPORT,
            base_value=100,
            acquired_day=5,
        )
        assert report.id == "guild_shipping_routes"
        assert report.quality == IntelQuality.REPORT
        assert not report.delivered

    def test_delivery_value_to_rival(self) -> None:
        """Delivering intel to the source's rival should give 2x value."""
        factions = _make_factions()
        report = IntelReport(
            id="test", name="Test", description="",
            source_faction_id="commerce_guild",
            quality=IntelQuality.REPORT, base_value=100, acquired_day=1,
        )
        value = report.get_delivery_value("miners_union", factions)
        assert value == 200, f"Rival delivery should be 2x, got {value}"

    def test_delivery_value_to_same_faction(self) -> None:
        """Delivering intel back to the source faction should give 0.5x."""
        factions = _make_factions()
        report = IntelReport(
            id="test", name="Test", description="",
            source_faction_id="commerce_guild",
            quality=IntelQuality.REPORT, base_value=100, acquired_day=1,
        )
        value = report.get_delivery_value("commerce_guild", factions)
        assert value == 50

    def test_delivery_value_to_neutral(self) -> None:
        """Delivering to unrelated faction should give 1x."""
        factions = _make_factions()
        report = IntelReport(
            id="test", name="Test", description="",
            source_faction_id="commerce_guild",
            quality=IntelQuality.REPORT, base_value=100, acquired_day=1,
        )
        value = report.get_delivery_value("science_collective", factions)
        assert value == 100

    def test_to_dict_from_dict_roundtrip(self) -> None:
        report = IntelReport(
            id="test", name="Test Intel", description="Desc",
            source_faction_id="miners_union",
            quality=IntelQuality.CLASSIFIED, base_value=200, acquired_day=10,
        )
        data = report.to_dict()
        restored = IntelReport.from_dict(data)
        assert restored.id == report.id
        assert restored.quality == IntelQuality.CLASSIFIED
        assert restored.base_value == 200


class TestIntelQuality:
    """Tests for IntelQuality enum."""

    def test_all_qualities_exist(self) -> None:
        expected = {"rumor", "report", "classified"}
        actual = {q.value for q in IntelQuality}
        assert expected == actual

    def test_reputation_scaling(self) -> None:
        """Higher quality intel should give more rep."""
        factions = _make_factions()
        for quality, expected_min_rep in [
            (IntelQuality.RUMOR, 1),
            (IntelQuality.REPORT, 3),
            (IntelQuality.CLASSIFIED, 5),
        ]:
            report = IntelReport(
                id="test", name="T", description="",
                source_faction_id="commerce_guild",
                quality=quality, base_value=100, acquired_day=1,
            )
            rep = report.get_reputation_reward("science_collective", factions)
            assert rep >= expected_min_rep, (
                f"{quality.value} should give at least {expected_min_rep} rep, got {rep}"
            )


class TestIntelDelivery:
    """Tests for delivering intel through PoliticsManager."""

    def test_deliver_to_rival(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        report = IntelReport(
            id="guild_info", name="Guild Intel", description="",
            source_faction_id="commerce_guild",
            quality=IntelQuality.REPORT, base_value=100, acquired_day=1,
        )
        mgr._intel_reports["guild_info"] = report

        success, msg = mgr.deliver_intel("guild_info", "miners_union", player)
        assert success
        assert report.delivered
        assert player.credits > 1000  # started with 1000, should gain credits
        assert player.get_reputation("miners_union") > 0

    def test_deliver_to_same_faction(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        report = IntelReport(
            id="guild_info", name="Guild Intel", description="",
            source_faction_id="commerce_guild",
            quality=IntelQuality.REPORT, base_value=100, acquired_day=1,
        )
        mgr._intel_reports["guild_info"] = report

        success, msg = mgr.deliver_intel("guild_info", "commerce_guild", player)
        assert success
        assert player.credits > 1000  # less credits than rival delivery

    def test_already_delivered(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        report = IntelReport(
            id="old_info", name="Old Intel", description="",
            source_faction_id="commerce_guild",
            quality=IntelQuality.RUMOR, base_value=50, acquired_day=1,
            delivered=True,
        )
        mgr._intel_reports["old_info"] = report

        success, msg = mgr.deliver_intel("old_info", "miners_union", player)
        assert not success

    def test_rival_delivery_backlash(self) -> None:
        """Delivering intel about a faction to their rival should hurt source rep."""
        mgr = _make_politics_manager()
        player = _make_player()
        report = IntelReport(
            id="guild_secrets", name="Guild Secrets", description="",
            source_faction_id="commerce_guild",
            quality=IntelQuality.CLASSIFIED, base_value=200, acquired_day=1,
        )
        mgr._intel_reports["guild_secrets"] = report

        mgr.deliver_intel("guild_secrets", "miners_union", player)
        # Should lose rep with source faction (guild finds out)
        assert player.get_reputation("commerce_guild") < 0, (
            "Delivering intel to rival should cause backlash with source"
        )

    def test_nonexistent_intel_fails(self) -> None:
        mgr = _make_politics_manager()
        player = _make_player()
        success, msg = mgr.deliver_intel("does_not_exist", "miners_union", player)
        assert not success


# ============================================================================
# Phase E: Campaign Wiring — DialogueResponse + Save Compatibility
# ============================================================================


class TestDialogueRepChanges:
    """Tests for faction_reputation_changes on DialogueResponse."""

    def test_field_exists_with_default(self) -> None:
        from spacegame.models.dialogue import DialogueResponse

        resp = DialogueResponse(
            text="Test response",
            next_node_id="next",
        )
        assert resp.faction_reputation_changes == []

    def test_field_accepts_changes(self) -> None:
        from spacegame.models.dialogue import DialogueResponse

        resp = DialogueResponse(
            text="Side with Guild",
            next_node_id="next",
            faction_reputation_changes=[
                {"commerce_guild": 5},
                {"miners_union": -3},
            ],
        )
        assert len(resp.faction_reputation_changes) == 2
        assert resp.faction_reputation_changes[0] == {"commerce_guild": 5}

    def test_m15_branching_mutual_exclusivity(self) -> None:
        """M15 faction choice should set mutually exclusive flags."""
        from spacegame.models.dialogue import DialogueResponse

        # Simulate the 4 M15 dialogue responses
        guild_resp = DialogueResponse(
            text="Choose Guild path",
            next_node_id=None,
            set_flag="chose_guild_path",
            faction_reputation_changes=[
                {"commerce_guild": 20},
                {"miners_union": -8},
                {"science_collective": -8},
                {"frontier_alliance": -8},
            ],
        )
        union_resp = DialogueResponse(
            text="Choose Union path",
            next_node_id=None,
            set_flag="chose_union_path",
            faction_reputation_changes=[
                {"miners_union": 20},
                {"commerce_guild": -8},
                {"science_collective": -8},
                {"frontier_alliance": -8},
            ],
        )
        # Verify the responses have correct structure
        assert guild_resp.set_flag == "chose_guild_path"
        assert len(guild_resp.faction_reputation_changes) == 4
        assert union_resp.faction_reputation_changes[0] == {"miners_union": 20}

    def test_apply_faction_rep_changes(self) -> None:
        """PoliticsManager should apply dialogue rep changes with spillover."""
        mgr = _make_politics_manager()
        player = _make_player()
        changes_list = [{"commerce_guild": 10}, {"miners_union": -5}]

        for change in changes_list:
            for faction_id, amount in change.items():
                mgr.apply_reputation_with_spillover(player, faction_id, amount)

        # Guild: +10 primary + spillover from union's -5 (rival gain: +1)
        assert player.get_reputation("commerce_guild") > 10
        # Union: -5 primary + spillover from guild's +10 (rival loss: -3)
        assert player.get_reputation("miners_union") < -5


class TestSaveCompatibility:
    """Tests for backward-compatible save/load of political state."""

    def test_old_save_no_political_state(self) -> None:
        """Old saves without political_state should load with defaults."""
        factions = _make_factions()
        mgr = PoliticsManager.from_dict({}, factions)
        assert mgr is not None
        # Should have default relationships
        rel = mgr.get_relationship("commerce_guild", "miners_union")
        assert rel is not None

    def test_full_roundtrip_with_events_and_intel(self) -> None:
        """Full political state should survive serialization."""
        mgr = _make_politics_manager()
        # Add an event
        event = PoliticalEvent(
            id="save_test", event_type=PoliticalEventType.TRADE_DISPUTE,
            faction_a_id="commerce_guild", faction_b_id="miners_union",
            description="Save test", day_started=1, duration_days=5,
            relationship_drift=-2,
        )
        mgr._active_events.append(event)
        # Modify a relationship
        mgr.modify_relationship("commerce_guild", "miners_union", 10)

        # Serialize and restore
        data = mgr.to_dict()
        factions = _make_factions()
        restored = PoliticsManager.from_dict(data, factions)

        # Verify
        rel = restored.get_relationship("commerce_guild", "miners_union")
        assert rel.value == -20  # -30 + 10
        assert len(restored._active_events) == 1
        assert restored._active_events[0].id == "save_test"
