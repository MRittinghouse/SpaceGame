"""Tests for ambient crew dialogue system."""

from spacegame.models.ambient_dialogue import AmbientLine, AmbientDialogueManager


# ============================================================================
# Helpers
# ============================================================================


def _make_lines() -> list[AmbientLine]:
    """Create test ambient lines covering all contexts."""
    return [
        AmbientLine(
            crew_id="elena_reeves",
            text="Stellaris Port. I used to know every docking clerk by name.",
            context="home_system",
            system_id="stellaris_port",
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="Guild territory. The ledger doesn't lie.",
            context="faction_territory",
            faction_id="commerce_guild",
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="I've been running fuel projections.",
            context="idle",
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="Jin, did you re-torque the port coupling?",
            context="inter_crew",
            required_crew="marcus_jin",
        ),
        AmbientLine(
            crew_id="marcus_jin",
            text="Breakstone. The ore dust never really washes off.",
            context="home_system",
            system_id="breakstone",
        ),
        AmbientLine(
            crew_id="marcus_jin",
            text="Engine's running clean.",
            context="idle",
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="High loyalty line.",
            context="idle",
            min_loyalty=70,
        ),
    ]


def _make_manager() -> AmbientDialogueManager:
    return AmbientDialogueManager(_make_lines())


# ============================================================================
# Context Selection Tests
# ============================================================================


class TestAmbientLineSelection:
    """Tests for selecting ambient lines by context."""

    def test_home_system_line(self) -> None:
        manager = _make_manager()
        line = manager.get_line(
            context="home_system",
            crew_id="elena_reeves",
            system_id="stellaris_port",
        )
        assert line is not None
        assert "Stellaris" in line

    def test_home_system_wrong_system_returns_none(self) -> None:
        manager = _make_manager()
        line = manager.get_line(
            context="home_system",
            crew_id="elena_reeves",
            system_id="breakstone",
        )
        assert line is None

    def test_faction_territory_line(self) -> None:
        manager = _make_manager()
        line = manager.get_line(
            context="faction_territory",
            crew_id="elena_reeves",
            faction_id="commerce_guild",
        )
        assert line is not None
        assert "Guild" in line

    def test_faction_territory_wrong_faction_returns_none(self) -> None:
        manager = _make_manager()
        line = manager.get_line(
            context="faction_territory",
            crew_id="elena_reeves",
            faction_id="industrial_union",
        )
        assert line is None

    def test_idle_line(self) -> None:
        manager = _make_manager()
        line = manager.get_line(
            context="idle",
            crew_id="elena_reeves",
        )
        assert line is not None

    def test_inter_crew_with_required_crew_present(self) -> None:
        manager = _make_manager()
        line = manager.get_line(
            context="inter_crew",
            crew_id="elena_reeves",
            recruited_ids=["elena_reeves", "marcus_jin"],
        )
        assert line is not None
        assert "Jin" in line

    def test_inter_crew_without_required_crew_returns_none(self) -> None:
        manager = _make_manager()
        line = manager.get_line(
            context="inter_crew",
            crew_id="elena_reeves",
            recruited_ids=["elena_reeves"],  # marcus not recruited
        )
        assert line is None


# ============================================================================
# Loyalty Filter Tests
# ============================================================================


class TestAmbientLoyaltyFilter:
    """Tests that min_loyalty filtering works."""

    def test_line_with_min_loyalty_met(self) -> None:
        manager = _make_manager()
        line = manager.get_line(
            context="idle",
            crew_id="elena_reeves",
            loyalty=75,
        )
        # Should be able to get the high-loyalty line
        assert line is not None

    def test_line_with_min_loyalty_not_met(self) -> None:
        manager = _make_manager()
        # Only get lines with min_loyalty <= 30
        lines = manager.get_all_matching(
            context="idle",
            crew_id="elena_reeves",
            loyalty=30,
        )
        high_loyalty_lines = [l for _, l in lines if "High loyalty" in l.text]
        assert len(high_loyalty_lines) == 0


# ============================================================================
# Cooldown / Repetition Tests
# ============================================================================


class TestAmbientCooldown:
    """Tests that shown lines are tracked to avoid repetition."""

    def test_shown_line_not_repeated_immediately(self) -> None:
        # Only one idle line for marcus
        manager = _make_manager()
        line1 = manager.get_line(context="idle", crew_id="marcus_jin")
        assert line1 is not None
        # After showing, the same line shouldn't appear immediately
        line2 = manager.get_line(context="idle", crew_id="marcus_jin")
        assert line2 is None  # Only one line, and it was shown


# ============================================================================
# Random Idle Tests
# ============================================================================


class TestRandomIdle:
    """Tests for random idle line selection."""

    def test_get_random_idle_returns_tuple(self) -> None:
        manager = _make_manager()
        result = manager.get_random_idle(
            recruited_ids=["elena_reeves", "marcus_jin"],
            loyalty_map={"elena_reeves": 30, "marcus_jin": 30},
        )
        assert result is not None
        crew_id, text = result
        assert crew_id in ["elena_reeves", "marcus_jin"]
        assert len(text) > 0

    def test_get_random_idle_no_crew_returns_none(self) -> None:
        manager = _make_manager()
        result = manager.get_random_idle(
            recruited_ids=[],
            loyalty_map={},
        )
        assert result is None


# ============================================================================
# Serialization Tests
# ============================================================================


class TestAmbientSerialization:
    """Tests for save/load of shown line state."""

    def test_shown_lines_persist(self) -> None:
        manager = _make_manager()
        # Show a line
        manager.get_line(context="idle", crew_id="marcus_jin")
        state = manager.to_dict()

        # Restore
        manager2 = _make_manager()
        manager2.load_state(state)

        # Should still be on cooldown
        line = manager2.get_line(context="idle", crew_id="marcus_jin")
        assert line is None  # Still on cooldown


# ============================================================================
# Player Action Context Tests
# ============================================================================


def _make_action_lines() -> list[AmbientLine]:
    """Create test lines for player_action context."""
    return [
        AmbientLine(
            crew_id="elena_reeves", text="That cargo was worth something.",
            context="player_action", action_type="sold_cargo",
        ),
        AmbientLine(
            crew_id="elena_reeves", text="Smart buy.",
            context="player_action", action_type="bought_cargo",
        ),
        AmbientLine(
            crew_id="marcus_jin", text="Good fight.",
            context="player_action", action_type="combat_victory",
        ),
        AmbientLine(
            crew_id="marcus_jin", text="Running again?",
            context="player_action", action_type="combat_retreat",
        ),
        AmbientLine(
            crew_id="elena_reeves", text="I know these docks.",
            context="idle",
        ),
        # Loyalty-gated player_action line
        AmbientLine(
            crew_id="elena_reeves", text="You always sell too early.",
            context="player_action", action_type="sold_cargo", min_loyalty=60,
        ),
    ]


class TestAmbientLineActionType:
    """Tests for the action_type field on AmbientLine."""

    def test_action_type_defaults_empty(self) -> None:
        line = AmbientLine(crew_id="elena_reeves", text="Hello.", context="idle")
        assert line.action_type == ""

    def test_action_type_set_explicitly(self) -> None:
        line = AmbientLine(
            crew_id="elena_reeves", text="Nice sale.",
            context="player_action", action_type="sold_cargo",
        )
        assert line.action_type == "sold_cargo"


class TestGetAllMatchingPlayerAction:
    """Tests for get_all_matching with player_action context."""

    def test_filters_by_action_type(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        matches = mgr.get_all_matching(
            context="player_action", crew_id="elena_reeves",
            action_type="sold_cargo",
        )
        texts = [line.text for _, line in matches]
        assert "That cargo was worth something." in texts
        assert "Smart buy." not in texts

    def test_no_match_wrong_action_type(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        matches = mgr.get_all_matching(
            context="player_action", crew_id="elena_reeves",
            action_type="combat_victory",
        )
        assert len(matches) == 0

    def test_action_type_ignored_for_non_player_action(self) -> None:
        """action_type filter only applies when context is player_action."""
        mgr = AmbientDialogueManager(_make_action_lines())
        matches = mgr.get_all_matching(
            context="idle", crew_id="elena_reeves",
            action_type="sold_cargo",
        )
        assert len(matches) >= 1
        assert all(line.context == "idle" for _, line in matches)

    def test_loyalty_gating_on_player_action(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        low = mgr.get_all_matching(
            context="player_action", crew_id="elena_reeves",
            action_type="sold_cargo", loyalty=10,
        )
        high = mgr.get_all_matching(
            context="player_action", crew_id="elena_reeves",
            action_type="sold_cargo", loyalty=80,
        )
        assert len(high) > len(low), "High loyalty should unlock more lines"


class TestGetPlayerActionLine:
    """Tests for the get_player_action_line convenience method."""

    def test_returns_line_for_matching_crew(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        result = mgr.get_player_action_line(
            action_type="combat_victory",
            recruited_ids=["marcus_jin", "elena_reeves"],
            loyalty_map={"marcus_jin": 50, "elena_reeves": 50},
        )
        assert result is not None
        crew_id, text = result
        assert crew_id == "marcus_jin"
        assert text == "Good fight."

    def test_returns_none_when_no_match(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        result = mgr.get_player_action_line(
            action_type="mission_expired",
            recruited_ids=["marcus_jin", "elena_reeves"],
            loyalty_map={"marcus_jin": 50, "elena_reeves": 50},
        )
        assert result is None

    def test_returns_none_when_no_crew_recruited(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        result = mgr.get_player_action_line(
            action_type="sold_cargo",
            recruited_ids=[],
            loyalty_map={},
        )
        assert result is None

    def test_respects_loyalty_gate(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        # With low loyalty, only base sold_cargo line available
        result = mgr.get_player_action_line(
            action_type="sold_cargo",
            recruited_ids=["elena_reeves"],
            loyalty_map={"elena_reeves": 10},
        )
        assert result is not None
        _, text = result
        assert text == "That cargo was worth something."

    def test_marks_line_shown(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        result1 = mgr.get_player_action_line(
            action_type="combat_victory",
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 50},
        )
        assert result1 is not None
        # Second call — only one line exists, should return None
        result2 = mgr.get_player_action_line(
            action_type="combat_victory",
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 50},
        )
        assert result2 is None


class TestGetLineWithActionType:
    """Tests for get_line() with the action_type parameter."""

    def test_get_line_filters_action_type(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        text = mgr.get_line(
            context="player_action", crew_id="elena_reeves",
            action_type="bought_cargo", loyalty=50,
        )
        assert text == "Smart buy."

    def test_get_line_returns_none_for_wrong_action(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        text = mgr.get_line(
            context="player_action", crew_id="elena_reeves",
            action_type="mission_expired", loyalty=50,
        )
        assert text is None


# ============================================================================
# Loyalty-Gated Dialogue Tier Tests
# ============================================================================


class TestLoyaltyDialogueTiers:
    """Tests for loyalty-gated dialogue progression across tiers."""

    def _make_tiered_lines(self) -> list[AmbientLine]:
        return [
            AmbientLine(crew_id="elena_reeves", text="Base idle.",
                         context="idle", min_loyalty=0),
            AmbientLine(crew_id="elena_reeves", text="Warming up.",
                         context="idle", min_loyalty=30),
            AmbientLine(crew_id="elena_reeves", text="We're a real crew now.",
                         context="idle", min_loyalty=60),
            AmbientLine(crew_id="elena_reeves", text="I trust you with my life.",
                         context="idle", min_loyalty=80),
        ]

    def test_tier_0_sees_base_only(self) -> None:
        mgr = AmbientDialogueManager(self._make_tiered_lines())
        matches = mgr.get_all_matching(
            context="idle", crew_id="elena_reeves", loyalty=0,
        )
        texts = [l.text for _, l in matches]
        assert texts == ["Base idle."]

    def test_tier_1_unlocks(self) -> None:
        mgr = AmbientDialogueManager(self._make_tiered_lines())
        matches = mgr.get_all_matching(
            context="idle", crew_id="elena_reeves", loyalty=30,
        )
        texts = [l.text for _, l in matches]
        assert "Base idle." in texts
        assert "Warming up." in texts
        assert "We're a real crew now." not in texts

    def test_tier_3_sees_all(self) -> None:
        mgr = AmbientDialogueManager(self._make_tiered_lines())
        matches = mgr.get_all_matching(
            context="idle", crew_id="elena_reeves", loyalty=100,
        )
        assert len(matches) == 4

    def test_get_random_idle_respects_loyalty_tiers(self) -> None:
        """get_random_idle only returns lines the crew member has unlocked."""
        lines = [
            AmbientLine(crew_id="elena_reeves", text="Base.",
                         context="idle", min_loyalty=0),
            AmbientLine(crew_id="elena_reeves", text="Deep.",
                         context="idle", min_loyalty=90),
        ]
        mgr = AmbientDialogueManager(lines)
        # With low loyalty, should only ever get "Base."
        for _ in range(10):
            mgr._shown.clear()
            result = mgr.get_random_idle(
                recruited_ids=["elena_reeves"],
                loyalty_map={"elena_reeves": 10},
            )
            if result is not None:
                assert result[1] == "Base."
