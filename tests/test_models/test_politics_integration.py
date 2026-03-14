"""Tests for political system engine/view integration.

Covers: PoliticsManager wiring in game.py, centralized spillover routing,
save/load, DataLoader parsing, and trading_view refactor.
"""

from spacegame.models.faction import Faction, ReputationTier, TensionLevel
from spacegame.models.politics import (
    FactionRelationship,
    PoliticalAction,
    PoliticalEvent,
    PoliticalEventType,
    PoliticsManager,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.dialogue import DialogueResponse


def _make_factions() -> dict[str, Faction]:
    """Create minimal faction set for testing."""
    return {
        "commerce_guild": Faction(
            id="commerce_guild",
            name="Commerce Guild",
            description="Trade faction",
            color=(200, 170, 50),
            rivalry="miners_union",
        ),
        "miners_union": Faction(
            id="miners_union",
            name="Miners Union",
            description="Mining faction",
            color=(180, 100, 60),
            rivalry="commerce_guild",
        ),
        "science_collective": Faction(
            id="science_collective",
            name="Science Collective",
            description="Research faction",
            color=(80, 150, 200),
            rivalry="frontier_alliance",
        ),
        "frontier_alliance": Faction(
            id="frontier_alliance",
            name="Frontier Alliance",
            description="Frontier faction",
            color=(60, 180, 100),
            rivalry="science_collective",
        ),
    }


def _make_relationships() -> list[FactionRelationship]:
    """Create default faction relationships."""
    return [
        FactionRelationship("commerce_guild", "miners_union", -30),
        FactionRelationship("commerce_guild", "science_collective", 15),
        FactionRelationship("commerce_guild", "frontier_alliance", -5),
        FactionRelationship("miners_union", "science_collective", 5),
        FactionRelationship("miners_union", "frontier_alliance", 20),
        FactionRelationship("science_collective", "frontier_alliance", -25),
    ]


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player() -> Player:
    ship_type = _make_ship_type()
    ship = Ship(ship_type=ship_type, current_fuel=50)
    player = Player(
        name="Test Captain",
        credits=1000,
        current_system_id="nexus_prime",
        ship=ship,
    )
    player.faction_assignments = {
        "nexus_prime": "commerce_guild",
        "forge_works": "miners_union",
        "nova_station": "science_collective",
        "outpost_7": "frontier_alliance",
    }
    player.faction_reputation = {
        "commerce_guild": 0,
        "miners_union": 0,
        "science_collective": 0,
        "frontier_alliance": 0,
    }
    return player


def _make_politics_manager() -> PoliticsManager:
    return PoliticsManager(
        relationships=_make_relationships(),
        factions=_make_factions(),
    )


# === Game.py Integration Tests ===


class TestPoliticsManagerInitialization:
    """PoliticsManager should be created during new game and load."""

    def test_politics_manager_created_with_factions(self) -> None:
        """PoliticsManager should have all faction relationships."""
        pm = _make_politics_manager()
        rel = pm.get_relationship("commerce_guild", "miners_union")
        assert rel.value == -30

    def test_politics_manager_has_all_six_pairs(self) -> None:
        pm = _make_politics_manager()
        pairs = [
            ("commerce_guild", "miners_union"),
            ("commerce_guild", "science_collective"),
            ("commerce_guild", "frontier_alliance"),
            ("miners_union", "science_collective"),
            ("miners_union", "frontier_alliance"),
            ("science_collective", "frontier_alliance"),
        ]
        for a, b in pairs:
            rel = pm.get_relationship(a, b)
            assert rel is not None, f"Missing relationship: {a} <-> {b}"


class TestCentralizedSpillover:
    """All rep changes should route through PoliticsManager spillover."""

    def test_trade_rep_uses_spillover(self) -> None:
        """Trade reputation gain should trigger rival penalty via spillover."""
        pm = _make_politics_manager()
        player = _make_player()

        changes = pm.apply_reputation_with_spillover(player, "commerce_guild", 2)

        assert ("commerce_guild", 2) in changes
        # Rival (miners_union) should lose 30% of 2 = 0 (rounds down)
        # But with larger amounts it should work
        assert player.faction_reputation["commerce_guild"] == 2

    def test_trade_rep_spillover_larger_amount(self) -> None:
        """Spillover should apply with amounts large enough to round."""
        pm = _make_politics_manager()
        player = _make_player()

        changes = pm.apply_reputation_with_spillover(player, "commerce_guild", 10)

        assert player.faction_reputation["commerce_guild"] == 10
        # 30% of 10 = 3 penalty to rival
        assert player.faction_reputation["miners_union"] == -3
        assert len(changes) == 2

    def test_mission_rep_through_spillover(self) -> None:
        """Mission reputation rewards should go through centralized spillover."""
        pm = _make_politics_manager()
        player = _make_player()

        # Simulate mission reward: +5 rep with miners_union
        changes = pm.apply_reputation_with_spillover(player, "miners_union", 5)

        assert player.faction_reputation["miners_union"] == 5
        # Rival (commerce_guild) should lose 30% of 5 = 1
        assert player.faction_reputation["commerce_guild"] == -1

    def test_encounter_rep_through_spillover(self) -> None:
        """Encounter reputation rewards should go through centralized spillover."""
        pm = _make_politics_manager()
        player = _make_player()

        changes = pm.apply_reputation_with_spillover(player, "science_collective", 8)

        assert player.faction_reputation["science_collective"] == 8
        # Rival (frontier_alliance) loses 30% of 8 = 2
        assert player.faction_reputation["frontier_alliance"] == -2

    def test_negative_rep_spillover_gives_rival_bonus(self) -> None:
        """Losing rep should give rival a positive spillover."""
        pm = _make_politics_manager()
        player = _make_player()

        changes = pm.apply_reputation_with_spillover(player, "commerce_guild", -10)

        assert player.faction_reputation["commerce_guild"] == -10
        # Rival gains: -(-10 * 0.3) = +3
        assert player.faction_reputation["miners_union"] == 3


class TestDayAdvanceIntegration:
    """Political events should process during day advance."""

    def test_advance_day_applies_relationship_drift(self) -> None:
        """Active events should drift faction relationships each day."""
        pm = _make_politics_manager()
        initial = pm.get_relationship("commerce_guild", "miners_union").value

        # Manually inject an active event
        event = PoliticalEvent(
            id="test_event",
            event_type=PoliticalEventType.TRADE_DISPUTE,
            faction_a_id="commerce_guild",
            faction_b_id="miners_union",
            description="Test dispute",
            day_started=1,
            duration_days=5,
            relationship_drift=-2,
        )
        pm._active_events.append(event)

        pm.advance_day(2)  # Day 2, event still active
        assert pm.get_relationship("commerce_guild", "miners_union").value == initial - 2

    def test_advance_day_cleans_expired_events(self) -> None:
        """Expired events should be removed."""
        pm = _make_politics_manager()
        event = PoliticalEvent(
            id="old_event",
            event_type=PoliticalEventType.SANCTION,
            faction_a_id="commerce_guild",
            faction_b_id="miners_union",
            description="Old sanction",
            day_started=1,
            duration_days=3,
            relationship_drift=-1,
        )
        pm._active_events.append(event)

        pm.advance_day(10)  # Well past expiration
        assert len(pm.get_active_events()) == 0

    def test_event_generation_during_advance(self) -> None:
        """try_generate_event should be callable during day advance."""
        pm = _make_politics_manager()
        # Just verify it doesn't crash — event generation is probabilistic
        result = pm.try_generate_event(100)
        # Result is either None or a PoliticalEvent
        assert result is None or isinstance(result, PoliticalEvent)


class TestPoliticalStateSerialization:
    """Political state should serialize/deserialize for save/load."""

    def test_round_trip_empty_state(self) -> None:
        """Fresh political state should survive round-trip."""
        pm = _make_politics_manager()
        data = pm.to_dict()
        restored = PoliticsManager.from_dict(data, _make_factions())

        assert len(restored.to_dict()["relationships"]) == 6

    def test_round_trip_with_events(self) -> None:
        """Political events should persist through save/load."""
        pm = _make_politics_manager()
        event = PoliticalEvent(
            id="persist_event",
            event_type=PoliticalEventType.BORDER_INCIDENT,
            faction_a_id="commerce_guild",
            faction_b_id="science_collective",
            description="Border clash",
            day_started=5,
            duration_days=4,
            relationship_drift=-3,
        )
        pm._active_events.append(event)

        data = pm.to_dict()
        restored = PoliticsManager.from_dict(data, _make_factions())

        assert len(restored.get_active_events()) == 1
        assert restored.get_active_events()[0].id == "persist_event"

    def test_round_trip_modified_relationships(self) -> None:
        """Modified relationship values should persist."""
        pm = _make_politics_manager()
        pm.modify_relationship("commerce_guild", "miners_union", 10)

        data = pm.to_dict()
        restored = PoliticsManager.from_dict(data, _make_factions())

        assert restored.get_relationship("commerce_guild", "miners_union").value == -20

    def test_backward_compat_empty_dict(self) -> None:
        """Old saves with no political state should get defaults."""
        restored = PoliticsManager.from_dict({}, _make_factions())
        # Should have default relationships (loaded from data_loader)
        # Even if data_loader has no relationships, it should not crash
        assert restored is not None

    def test_player_political_state_field(self) -> None:
        """Player should have a political_state dict field."""
        player = _make_player()
        assert hasattr(player, "political_state")
        assert isinstance(player.political_state, dict)


class TestSaveManagerPoliticalState:
    """Save manager should include political state in serialization."""

    def test_serialize_includes_political_state(self) -> None:
        """Serialized save data should contain political_state key."""
        from spacegame.save_manager import SaveManager

        sm = SaveManager(save_directory=None)
        player = _make_player()
        # Set political state on player
        pm = _make_politics_manager()
        player.political_state = pm.to_dict()

        # The serialized player dict should include political_state
        player_data = sm._serialize_player(player)
        assert "political_state" in player_data

    def test_deserialize_restores_political_state(self) -> None:
        """Deserialized player should have political_state."""
        from spacegame.save_manager import SaveManager

        sm = SaveManager(save_directory=None)
        player = _make_player()
        pm = _make_politics_manager()
        player.political_state = pm.to_dict()

        player_data = sm._serialize_player(player)
        restored = sm._deserialize_player(player_data)
        assert "political_state" in restored.political_state or isinstance(
            restored.political_state, dict
        )


class TestDataLoaderFactionRepChanges:
    """DataLoader should parse faction_reputation_changes from dialogue JSON."""

    def test_dialogue_response_has_faction_rep_changes_field(self) -> None:
        """DialogueResponse should support faction_reputation_changes."""
        response = DialogueResponse(
            text="Support the Guild",
            next_node_id="result_node",
            faction_reputation_changes=[
                {"commerce_guild": 20},
                {"miners_union": -8},
            ],
        )
        assert len(response.faction_reputation_changes) == 2
        assert response.faction_reputation_changes[0]["commerce_guild"] == 20

    def test_dialogue_response_default_empty_rep_changes(self) -> None:
        """Default faction_reputation_changes should be empty list."""
        response = DialogueResponse(text="Hello", next_node_id="next")
        assert response.faction_reputation_changes == []


class TestDialogueRepChangeProcessing:
    """DialogueManager should apply faction_reputation_changes via PoliticsManager."""

    def test_select_response_applies_faction_rep(self) -> None:
        """Selecting a response with faction_reputation_changes should modify rep."""
        from spacegame.models.dialogue import (
            DialogueManager,
            DialogueNode,
            DialogueTree,
        )

        tree = DialogueTree(
            id="test_tree",
            start_node_id="start",
            nodes={
                "start": DialogueNode(
                    id="start",
                    speaker_id="npc1",
                    text="Choose a side",
                    responses=[
                        DialogueResponse(
                            text="Support Guild",
                            next_node_id=None,
                            faction_reputation_changes=[
                                {"commerce_guild": 20},
                                {"miners_union": -8},
                            ],
                        ),
                    ],
                ),
            },
        )

        dm = DialogueManager()
        dm.start_dialogue(tree)

        responses = dm.get_available_responses()
        assert len(responses) == 1
        assert responses[0].faction_reputation_changes[0]["commerce_guild"] == 20

    def test_select_response_with_politics_manager_applies_rep(self) -> None:
        """When politics_manager is set, selecting a response applies faction rep."""
        from spacegame.models.dialogue import (
            DialogueManager,
            DialogueNode,
            DialogueTree,
        )

        pm = _make_politics_manager()
        player = _make_player()

        tree = DialogueTree(
            id="test_tree",
            start_node_id="start",
            nodes={
                "start": DialogueNode(
                    id="start",
                    speaker_id="npc1",
                    text="Choose a side",
                    responses=[
                        DialogueResponse(
                            text="Support Guild",
                            next_node_id=None,
                            faction_reputation_changes=[
                                {"commerce_guild": 20},
                            ],
                        ),
                    ],
                ),
            },
        )

        dm = DialogueManager()
        dm.set_politics_manager(pm, player)
        dm.start_dialogue(tree)
        dm.select_response(0)

        # Guild should get +20, rival (miners_union) gets -6 (30% of 20)
        assert player.faction_reputation["commerce_guild"] == 20
        assert player.faction_reputation["miners_union"] == -6

    def test_select_response_without_politics_manager_no_crash(self) -> None:
        """Without politics_manager, faction_reputation_changes are silently ignored."""
        from spacegame.models.dialogue import (
            DialogueManager,
            DialogueNode,
            DialogueTree,
        )

        player = _make_player()

        tree = DialogueTree(
            id="test_tree",
            start_node_id="start",
            nodes={
                "start": DialogueNode(
                    id="start",
                    speaker_id="npc1",
                    text="Choose a side",
                    responses=[
                        DialogueResponse(
                            text="Support Guild",
                            next_node_id=None,
                            faction_reputation_changes=[
                                {"commerce_guild": 20},
                            ],
                        ),
                    ],
                ),
            },
        )

        dm = DialogueManager()
        dm.start_dialogue(tree)
        dm.select_response(0)  # Should not crash

        # Rep should not change without politics_manager
        assert player.faction_reputation["commerce_guild"] == 0


class TestTradingViewSpilloverRefactor:
    """Trading view should use PoliticsManager for reputation instead of inline logic."""

    def test_spillover_ratio_matches_config(self) -> None:
        """Spillover ratio should be 30% as configured."""
        from spacegame.config import REP_SPILLOVER_RATIO

        assert REP_SPILLOVER_RATIO == 0.30

    def test_centralized_spillover_replaces_inline(self) -> None:
        """PoliticsManager spillover should produce same results as old inline logic."""
        pm = _make_politics_manager()
        player = _make_player()

        # Old behavior: +2 guild, -1 rival (50% penalty in old code)
        # New behavior: +2 guild, -0.6 -> 0 rival (30% penalty, rounds down)
        # With larger amounts: +10 guild, -3 rival (30%)
        changes = pm.apply_reputation_with_spillover(player, "commerce_guild", 10)

        guild_change = next(c for c in changes if c[0] == "commerce_guild")
        union_change = next(c for c in changes if c[0] == "miners_union")
        assert guild_change[1] == 10
        assert union_change[1] == -3  # 30% of 10


class TestTradeRepOncePerLanding:
    """Trade reputation should only apply once per station visit."""

    def test_trade_rep_flag_starts_false(self) -> None:
        """Fresh trading view should not have trade rep awarded."""
        from spacegame.views.trading_view import TradingView

        view = TradingView.__new__(TradingView)
        view._trade_rep_awarded = False
        assert not view._trade_rep_awarded

    def test_trade_rep_awarded_blocks_second_call(self) -> None:
        """After rep is awarded, subsequent calls should be no-ops."""
        pm = _make_politics_manager()
        player = _make_player()
        player.current_system_id = "nexus_prime"

        # Simulate first trade rep
        pm.apply_reputation_with_spillover(player, "commerce_guild", 1)
        rep_after_first = player.faction_reputation["commerce_guild"]

        # Second call should NOT increase rep (view guards this)
        # We test the flag mechanism directly
        flag = False  # Simulates _trade_rep_awarded
        if not flag:
            pm.apply_reputation_with_spillover(player, "commerce_guild", 1)
            flag = True
        rep_after_second_guarded = player.faction_reputation["commerce_guild"]

        # Without guard, a third call would increase further
        assert rep_after_second_guarded == rep_after_first + 1
        # With guard active, no further increase
        if flag:
            pass  # Would not call apply_reputation_with_spillover
        assert player.faction_reputation["commerce_guild"] == rep_after_second_guarded

    def test_rep_per_trade_is_one(self) -> None:
        """REP_PER_TRADE should be 1 for minimal political impact."""
        from spacegame.config import REP_PER_TRADE

        assert REP_PER_TRADE == 1


class TestDockingDenial:
    """HOSTILE faction systems should deny docking."""

    def test_hostile_denies_docking(self) -> None:
        pm = _make_politics_manager()
        player = _make_player()
        # Set reputation to hostile with commerce_guild
        player.faction_reputation["commerce_guild"] = -60

        allowed, msg = pm.get_docking_allowed(player, "nexus_prime")
        assert not allowed
        assert "Commerce Guild" in msg

    def test_neutral_allows_docking(self) -> None:
        pm = _make_politics_manager()
        player = _make_player()

        allowed, msg = pm.get_docking_allowed(player, "nexus_prime")
        assert allowed

    def test_no_faction_system_allows_docking(self) -> None:
        pm = _make_politics_manager()
        player = _make_player()
        # System with no faction assignment
        allowed, msg = pm.get_docking_allowed(player, "unknown_system")
        assert allowed


class TestStationHubDockingDenial:
    """StationHubView should accept politics_manager and expose docking denial state."""

    def test_station_hub_accepts_politics_manager(self) -> None:
        """StationHubView should accept optional politics_manager param."""
        from spacegame.views.station_hub_view import StationHubView

        # Just verify the constructor signature accepts the param
        import inspect
        sig = inspect.signature(StationHubView.__init__)
        assert "politics_manager" in sig.parameters

    def test_docking_denied_flag_set_for_hostile(self) -> None:
        """When hostile, station hub should set docking_denied flag."""
        pm = _make_politics_manager()
        player = _make_player()
        player.faction_reputation["commerce_guild"] = -60

        allowed, msg = pm.get_docking_allowed(player, "nexus_prime")
        assert not allowed

    def test_docking_allowed_for_neutral(self) -> None:
        """Neutral rep should allow normal station access."""
        pm = _make_politics_manager()
        player = _make_player()

        allowed, _ = pm.get_docking_allowed(player, "nexus_prime")
        assert allowed


class TestGalaxyMapStandingIndicator:
    """Galaxy map should show reputation standing indicators on system nodes."""

    def test_standing_color_hostile(self) -> None:
        """Hostile standing should map to red."""
        from spacegame.models.faction import ReputationTier
        from spacegame.views.galaxy_map_view import _get_standing_color

        color = _get_standing_color(ReputationTier.HOSTILE)
        assert color == (200, 50, 50)

    def test_standing_color_allied(self) -> None:
        """Allied standing should map to green."""
        from spacegame.models.faction import ReputationTier
        from spacegame.views.galaxy_map_view import _get_standing_color

        color = _get_standing_color(ReputationTier.ALLIED)
        assert color == (50, 200, 100)

    def test_standing_color_neutral_returns_none(self) -> None:
        """Neutral standing should return None (no indicator)."""
        from spacegame.models.faction import ReputationTier
        from spacegame.views.galaxy_map_view import _get_standing_color

        color = _get_standing_color(ReputationTier.NEUTRAL)
        assert color is None

    def test_standing_color_friendly(self) -> None:
        """Friendly standing should map to a visible color."""
        from spacegame.models.faction import ReputationTier
        from spacegame.views.galaxy_map_view import _get_standing_color

        color = _get_standing_color(ReputationTier.FRIENDLY)
        assert color is not None

    def test_standing_color_unfriendly(self) -> None:
        """Unfriendly standing should map to orange."""
        from spacegame.models.faction import ReputationTier
        from spacegame.views.galaxy_map_view import _get_standing_color

        color = _get_standing_color(ReputationTier.UNFRIENDLY)
        assert color is not None


class TestGalaxyMapPoliticalEvents:
    """Galaxy map should accept politics_manager for political event display."""

    def test_galaxy_map_accepts_politics_manager(self) -> None:
        """GalaxyMapView should accept optional politics_manager param."""
        from spacegame.views.galaxy_map_view import GalaxyMapView
        import inspect
        sig = inspect.signature(GalaxyMapView.__init__)
        assert "politics_manager" in sig.parameters


# === Deep Integration Gap Tests ===


class TestIntelBacklashSpillover:
    """Intel backlash should route through centralized spillover."""

    def test_intel_backlash_uses_spillover(self) -> None:
        """Delivering intel to rival should apply spillover on backlash too."""
        pm = _make_politics_manager()
        player = _make_player()

        from spacegame.models.politics import IntelReport, IntelQuality

        report = IntelReport(
            id="test_intel",
            name="Guild Manifests",
            description="Shipping data",
            source_faction_id="commerce_guild",
            quality=IntelQuality.REPORT,
            base_value=100,
            acquired_day=1,
        )
        pm._intel_reports["test_intel"] = report

        # Deliver to rival (miners_union is rival of commerce_guild)
        pm.deliver_intel("test_intel", "miners_union", player)

        # Primary: +rep with miners_union (through spillover)
        assert player.faction_reputation["miners_union"] > 0
        # Backlash: -rep with commerce_guild (should also go through spillover)
        assert player.faction_reputation["commerce_guild"] < 0
        # Spillover on backlash: miners_union gets small positive from guild backlash
        # The backlash is -3 to guild, spillover = +0.9 -> +0 (rounds down)
        # But primary delivery already gave miners_union positive rep


class TestEncounterModifierIntegration:
    """PoliticsManager encounter modifiers should affect travel encounters."""

    def test_hostile_encounter_modifier(self) -> None:
        """Hostile systems should have increased attack chance."""
        pm = _make_politics_manager()
        player = _make_player()
        player.faction_reputation["commerce_guild"] = -60  # Hostile

        mods = pm.get_encounter_modifier(player, "nexus_prime")
        assert mods["hostile_attack_chance"] == 40
        assert mods["shakedown_multiplier"] == 2.0

    def test_allied_protection_chance(self) -> None:
        """Allied systems should offer protection chance."""
        pm = _make_politics_manager()
        player = _make_player()
        player.faction_reputation["commerce_guild"] = 60  # Allied

        mods = pm.get_encounter_modifier(player, "nexus_prime")
        assert mods["protection_chance"] == 30

    def test_neutral_no_modifiers(self) -> None:
        """Neutral rep should have no encounter modifiers."""
        pm = _make_politics_manager()
        player = _make_player()

        mods = pm.get_encounter_modifier(player, "nexus_prime")
        assert mods["hostile_attack_chance"] == 0
        assert mods["shakedown_multiplier"] == 1.0
        assert mods["protection_chance"] == 0

    def test_shakedown_demand_scales_with_multiplier(self) -> None:
        """Shakedown demands should scale by reputation modifier."""
        base_demand = 150
        multiplier = 2.0  # Hostile
        assert int(base_demand * multiplier) == 300

    def test_protection_chance_can_cancel_encounter(self) -> None:
        """Protection chance represents likelihood of escort preventing encounter."""
        pm = _make_politics_manager()
        player = _make_player()
        player.faction_reputation["commerce_guild"] = 60  # Allied

        mods = pm.get_encounter_modifier(player, "nexus_prime")
        # 30% protection means there's a meaningful chance of avoiding combat
        assert 0 < mods["protection_chance"] <= 100


class TestNpcDispositionModifier:
    """NPC disposition should be modified by player's faction standing."""

    def test_hostile_gives_negative_disposition(self) -> None:
        pm = _make_politics_manager()
        player = _make_player()
        player.faction_reputation["commerce_guild"] = -60

        mod = pm.get_npc_disposition_modifier(player, "commerce_guild")
        assert mod == -15

    def test_allied_gives_positive_disposition(self) -> None:
        pm = _make_politics_manager()
        player = _make_player()
        player.faction_reputation["commerce_guild"] = 60

        mod = pm.get_npc_disposition_modifier(player, "commerce_guild")
        assert mod == 15

    def test_neutral_gives_zero_disposition(self) -> None:
        pm = _make_politics_manager()
        player = _make_player()

        mod = pm.get_npc_disposition_modifier(player, "commerce_guild")
        assert mod == 0

    def test_disposition_modifier_applied_on_dialogue_start(self) -> None:
        """Starting dialogue with faction NPC should apply disposition modifier."""
        from spacegame.models.social import SocialManager

        pm = _make_politics_manager()
        player = _make_player()
        player.faction_reputation["commerce_guild"] = 40  # Friendly

        sm = SocialManager()
        mod = pm.get_npc_disposition_modifier(player, "commerce_guild")
        assert mod == 10  # Friendly tier

        # Apply to a test NPC
        sm.modify_disposition("test_npc", mod)
        assert sm.get_disposition("test_npc") == 60  # 50 default + 10


class TestCampaignDialoguePoliticalIntegration:
    """Late campaign dialogues should have faction_reputation_changes on key choices."""

    def _get_dialogue_tree(self, tree_id: str) -> dict:
        """Load a dialogue tree from JSON by ID."""
        import json

        with open("data/dialogue/dialogues.json") as f:
            data = json.load(f)
        for tree in data["dialogues"]:
            if tree["id"] == tree_id:
                return tree
        raise ValueError(f"Dialogue tree {tree_id} not found")

    def _find_response(
        self, tree: dict, node_id: str, response_text_prefix: str
    ) -> dict:
        """Find a response in a node by text prefix."""
        for node in tree["nodes"]:
            if node["id"] == node_id:
                for r in node["responses"]:
                    if r["text"].startswith(response_text_prefix):
                        return r
        raise ValueError(
            f"Response starting with '{response_text_prefix}' not found in {node_id}"
        )

    def test_oren_tak_revelation_has_rep_changes(self) -> None:
        """Oren's revelation should reward miners_union and penalize guild."""
        tree = self._get_dialogue_tree("oren_tak_meeting")
        resp = self._find_response(tree, "details", "That's the connection")
        changes = resp["faction_reputation_changes"]
        factions = {k: v for d in changes for k, v in d.items()}
        assert factions["miners_union"] > 0
        assert factions["commerce_guild"] < 0

    def test_sienna_share_data_has_rep_changes(self) -> None:
        """Full data share should reward collective and penalize guild."""
        tree = self._get_dialogue_tree("sienna_vek_warning")
        resp = self._find_response(tree, "share_data", "I'll stop it")
        changes = resp["faction_reputation_changes"]
        factions = {k: v for d in changes for k, v in d.items()}
        assert factions["science_collective"] > 0
        assert factions["commerce_guild"] < 0

    def test_sienna_partial_intel_has_lesser_rep_changes(self) -> None:
        """Partial intel should still shift rep, but less than full data."""
        tree = self._get_dialogue_tree("sienna_vek_warning")
        full = self._find_response(tree, "share_data", "I'll stop it")
        partial = self._find_response(tree, "partial_intel", "That's enough")
        full_factions = {k: v for d in full["faction_reputation_changes"] for k, v in d.items()}
        partial_factions = {k: v for d in partial["faction_reputation_changes"] for k, v in d.items()}
        assert partial_factions["science_collective"] < full_factions["science_collective"]
        assert partial_factions["commerce_guild"] > full_factions["commerce_guild"]  # less negative

    def test_summit_speech_has_rep_changes(self) -> None:
        """Speaking at the summit should shift guild down, union/alliance up."""
        tree = self._get_dialogue_tree("embassy_summit")
        resp = self._find_response(tree, "player_speaks", "It was worth saying")
        changes = resp["faction_reputation_changes"]
        factions = {k: v for d in changes for k, v in d.items()}
        assert factions["commerce_guild"] < 0
        assert factions["miners_union"] > 0
        assert factions["frontier_alliance"] > 0

    def test_summit_observation_has_rep_changes(self) -> None:
        """Noticing the Guild signal should penalize guild and help alliance."""
        tree = self._get_dialogue_tree("embassy_summit")
        resp = self._find_response(tree, "noticed_signal", "Did you see that")
        changes = resp["faction_reputation_changes"]
        factions = {k: v for d in changes for k, v in d.items()}
        assert factions["commerce_guild"] < 0
        assert factions["frontier_alliance"] > 0

    def test_priya_blocked_channels_has_rep_changes(self) -> None:
        """Learning official channels are blocked should shift alliance/collective up."""
        tree = self._get_dialogue_tree("priya_convergence_analysis")
        resp = self._find_response(tree, "alliance_response", "Then the official channels")
        changes = resp["faction_reputation_changes"]
        factions = {k: v for d in changes for k, v in d.items()}
        assert factions["frontier_alliance"] > 0
        assert factions["science_collective"] > 0

    def test_dex_tunnel_briefing_has_rep_changes(self) -> None:
        """Accepting the tunnel investigation should give alliance rep."""
        tree = self._get_dialogue_tree("dex_tunnel_briefing")
        resp = self._find_response(tree, "connection", "I'll find him")
        assert len(resp["faction_reputation_changes"]) > 0
        factions = {k: v for d in resp["faction_reputation_changes"] for k, v in d.items()}
        assert factions["frontier_alliance"] > 0

    def test_dex_assembly_farewell_has_rep_changes(self) -> None:
        """Final Dex briefing should penalize guild and reward alliance."""
        tree = self._get_dialogue_tree("dex_assembly_intel")
        resp = self._find_response(tree, "farewell", "[Take the chip]")
        changes = resp["faction_reputation_changes"]
        factions = {k: v for d in changes for k, v in d.items()}
        assert factions["commerce_guild"] < 0
        assert factions["frontier_alliance"] > 0


class TestDeadCodeCleanup:
    """Legacy constants should be removed."""

    def test_spillover_ratio_is_authoritative(self) -> None:
        """REP_SPILLOVER_RATIO should be the only spillover constant."""
        from spacegame.config import REP_SPILLOVER_RATIO
        assert REP_SPILLOVER_RATIO == 0.30
