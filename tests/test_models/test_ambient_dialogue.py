"""Tests for ambient crew dialogue system."""

from spacegame.models.ambient_dialogue import AmbientDialogueManager, AmbientLine

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
            crew_id="elena_reeves",
            text="That cargo was worth something.",
            context="player_action",
            action_type="sold_cargo",
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="Smart buy.",
            context="player_action",
            action_type="bought_cargo",
        ),
        AmbientLine(
            crew_id="marcus_jin",
            text="Good fight.",
            context="player_action",
            action_type="combat_victory",
        ),
        AmbientLine(
            crew_id="marcus_jin",
            text="Running again?",
            context="player_action",
            action_type="combat_retreat",
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="I know these docks.",
            context="idle",
        ),
        # Loyalty-gated player_action line
        AmbientLine(
            crew_id="elena_reeves",
            text="You always sell too early.",
            context="player_action",
            action_type="sold_cargo",
            min_loyalty=60,
        ),
    ]


class TestAmbientLineActionType:
    """Tests for the action_type field on AmbientLine."""

    def test_action_type_defaults_empty(self) -> None:
        line = AmbientLine(crew_id="elena_reeves", text="Hello.", context="idle")
        assert line.action_type == ""

    def test_action_type_set_explicitly(self) -> None:
        line = AmbientLine(
            crew_id="elena_reeves",
            text="Nice sale.",
            context="player_action",
            action_type="sold_cargo",
        )
        assert line.action_type == "sold_cargo"


class TestGetAllMatchingPlayerAction:
    """Tests for get_all_matching with player_action context."""

    def test_filters_by_action_type(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        matches = mgr.get_all_matching(
            context="player_action",
            crew_id="elena_reeves",
            action_type="sold_cargo",
        )
        texts = [line.text for _, line in matches]
        assert "That cargo was worth something." in texts
        assert "Smart buy." not in texts

    def test_no_match_wrong_action_type(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        matches = mgr.get_all_matching(
            context="player_action",
            crew_id="elena_reeves",
            action_type="combat_victory",
        )
        assert len(matches) == 0

    def test_action_type_ignored_for_non_player_action(self) -> None:
        """action_type filter only applies when context is player_action."""
        mgr = AmbientDialogueManager(_make_action_lines())
        matches = mgr.get_all_matching(
            context="idle",
            crew_id="elena_reeves",
            action_type="sold_cargo",
        )
        assert len(matches) >= 1
        assert all(line.context == "idle" for _, line in matches)

    def test_loyalty_gating_on_player_action(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        low = mgr.get_all_matching(
            context="player_action",
            crew_id="elena_reeves",
            action_type="sold_cargo",
            loyalty=10,
        )
        high = mgr.get_all_matching(
            context="player_action",
            crew_id="elena_reeves",
            action_type="sold_cargo",
            loyalty=80,
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
            context="player_action",
            crew_id="elena_reeves",
            action_type="bought_cargo",
            loyalty=50,
        )
        assert text == "Smart buy."

    def test_get_line_returns_none_for_wrong_action(self) -> None:
        mgr = AmbientDialogueManager(_make_action_lines())
        text = mgr.get_line(
            context="player_action",
            crew_id="elena_reeves",
            action_type="mission_expired",
            loyalty=50,
        )
        assert text is None


# ============================================================================
# Loyalty-Gated Dialogue Tier Tests
# ============================================================================


class TestLoyaltyDialogueTiers:
    """Tests for loyalty-gated dialogue progression across tiers."""

    def _make_tiered_lines(self) -> list[AmbientLine]:
        return [
            AmbientLine(crew_id="elena_reeves", text="Base idle.", context="idle", min_loyalty=0),
            AmbientLine(crew_id="elena_reeves", text="Warming up.", context="idle", min_loyalty=30),
            AmbientLine(
                crew_id="elena_reeves",
                text="We're a real crew now.",
                context="idle",
                min_loyalty=60,
            ),
            AmbientLine(
                crew_id="elena_reeves",
                text="I trust you with my life.",
                context="idle",
                min_loyalty=80,
            ),
        ]

    def test_tier_0_sees_base_only(self) -> None:
        mgr = AmbientDialogueManager(self._make_tiered_lines())
        matches = mgr.get_all_matching(
            context="idle",
            crew_id="elena_reeves",
            loyalty=0,
        )
        texts = [l.text for _, l in matches]
        assert texts == ["Base idle."]

    def test_tier_1_unlocks(self) -> None:
        mgr = AmbientDialogueManager(self._make_tiered_lines())
        matches = mgr.get_all_matching(
            context="idle",
            crew_id="elena_reeves",
            loyalty=30,
        )
        texts = [l.text for _, l in matches]
        assert "Base idle." in texts
        assert "Warming up." in texts
        assert "We're a real crew now." not in texts

    def test_tier_3_sees_all(self) -> None:
        mgr = AmbientDialogueManager(self._make_tiered_lines())
        matches = mgr.get_all_matching(
            context="idle",
            crew_id="elena_reeves",
            loyalty=100,
        )
        assert len(matches) == 4

    def test_get_random_idle_respects_loyalty_tiers(self) -> None:
        """get_random_idle only returns lines the crew member has unlocked."""
        lines = [
            AmbientLine(crew_id="elena_reeves", text="Base.", context="idle", min_loyalty=0),
            AmbientLine(crew_id="elena_reeves", text="Deep.", context="idle", min_loyalty=90),
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


# ============================================================================
# CB-2: AmbientLine flag fields (schema extension)
# ============================================================================


class TestAmbientLineFlagFields:
    """CB-2 acceptance criterion 1: AmbientLine has required_flags / excluded_flags."""

    def test_required_flags_default_empty(self) -> None:
        line = AmbientLine(crew_id="elena_reeves", text="Hello.", context="idle")
        assert line.required_flags == []

    def test_excluded_flags_default_empty(self) -> None:
        line = AmbientLine(crew_id="elena_reeves", text="Hello.", context="idle")
        assert line.excluded_flags == []

    def test_required_flags_can_be_set(self) -> None:
        line = AmbientLine(
            crew_id="elena_reeves",
            text="After the Uprising.",
            context="flag_triggered",
            required_flags=["marcus_uprising_inheritance_seen"],
        )
        assert line.required_flags == ["marcus_uprising_inheritance_seen"]

    def test_excluded_flags_can_be_set(self) -> None:
        line = AmbientLine(
            crew_id="marcus_jin",
            text="No repeat.",
            context="flag_triggered",
            excluded_flags=["some_event_done"],
        )
        assert line.excluded_flags == ["some_event_done"]

    def test_flag_fields_are_independent_lists(self) -> None:
        """Each instance has its own list — no shared mutable default."""
        line_a = AmbientLine(crew_id="elena_reeves", text="A.", context="idle")
        line_b = AmbientLine(crew_id="marcus_jin", text="B.", context="idle")
        line_a.required_flags.append("x")
        assert line_b.required_flags == [], "Shared mutable default would poison line_b."


# ============================================================================
# CB-2: player_flags filter on get_all_matching
# ============================================================================


def _make_flag_lines() -> list[AmbientLine]:
    """Lines for testing required_flags / excluded_flags filter."""
    return [
        AmbientLine(
            crew_id="elena_reeves",
            text="Uprising line.",
            context="flag_triggered",
            required_flags=["marcus_uprising_inheritance_seen"],
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="Two-flag line.",
            context="flag_triggered",
            required_flags=["marcus_uprising_inheritance_seen", "attended_silent_shaft"],
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="Excluded line.",
            context="flag_triggered",
            excluded_flags=["heard_dcmc_intelligence"],
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="Plain flag_triggered line.",
            context="flag_triggered",
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="Base idle.",
            context="idle",
        ),
    ]


class TestPlayerFlagsFilter:
    """CB-2 acceptance criterion 2: get_all_matching respects player_flags."""

    def test_required_flags_filter(self) -> None:
        mgr = AmbientDialogueManager(_make_flag_lines())
        # "Uprising line" requires marcus_uprising_inheritance_seen = True
        matches = mgr.get_all_matching(
            context="flag_triggered",
            crew_id="elena_reeves",
            player_flags={"marcus_uprising_inheritance_seen": True, "attended_silent_shaft": False},
        )
        texts = [l.text for _, l in matches]
        assert "Uprising line." in texts, "Line with met required_flag should match."
        assert "Two-flag line." not in texts, (
            "Line needing both flags should not match (one missing)."
        )

    def test_excluded_flags_filter(self) -> None:
        mgr = AmbientDialogueManager(_make_flag_lines())
        # "Excluded line" is blocked when heard_dcmc_intelligence is set
        matches = mgr.get_all_matching(
            context="flag_triggered",
            crew_id="elena_reeves",
            player_flags={"heard_dcmc_intelligence": True},
        )
        texts = [l.text for _, l in matches]
        assert "Excluded line." not in texts, "Line with set excluded_flag should not match."
        assert "Plain flag_triggered line." in texts, (
            "Plain line with no flag restrictions should still match."
        )

    def test_player_flags_none_is_no_op(self) -> None:
        """Backward compat: existing lines still match when player_flags=None."""
        # Use a basic idle line (no flag fields) — must still return
        lines = [
            AmbientLine(crew_id="elena_reeves", text="Old idle.", context="idle"),
        ]
        mgr = AmbientDialogueManager(lines)
        matches = mgr.get_all_matching(context="idle", crew_id="elena_reeves")
        assert len(matches) == 1, "player_flags=None (default) must not filter anything."

    def test_required_and_excluded_combined(self) -> None:
        """A line with both required AND excluded fields respects both."""
        lines = [
            AmbientLine(
                crew_id="elena_reeves",
                text="Combined.",
                context="flag_triggered",
                required_flags=["marcus_uprising_inheritance_seen"],
                excluded_flags=["attended_silent_shaft"],
            )
        ]
        mgr = AmbientDialogueManager(lines)
        # required met, excluded absent -> match
        matches = mgr.get_all_matching(
            context="flag_triggered",
            crew_id="elena_reeves",
            player_flags={"marcus_uprising_inheritance_seen": True, "attended_silent_shaft": False},
        )
        assert len(matches) == 1
        # required met, excluded present -> no match
        matches2 = mgr.get_all_matching(
            context="flag_triggered",
            crew_id="elena_reeves",
            player_flags={"marcus_uprising_inheritance_seen": True, "attended_silent_shaft": True},
        )
        assert len(matches2) == 0

    def test_flag_triggered_context_returned_when_eligible(self) -> None:
        """CB-2 criterion 3: flag_triggered lines appear when flag conditions met."""
        lines = [
            AmbientLine(
                crew_id="marcus_jin",
                text="He mentioned the Uprising.",
                context="flag_triggered",
                required_flags=["marcus_uprising_inheritance_seen"],
            )
        ]
        mgr = AmbientDialogueManager(lines)
        matches = mgr.get_all_matching(
            context="flag_triggered",
            crew_id="marcus_jin",
            player_flags={"marcus_uprising_inheritance_seen": True},
        )
        assert len(matches) == 1
        # Flag not set -> no match
        matches2 = mgr.get_all_matching(
            context="flag_triggered",
            crew_id="marcus_jin",
            player_flags={"marcus_uprising_inheritance_seen": False},
        )
        assert len(matches2) == 0


# ============================================================================
# CB-2: combat_after context + recency window
# ============================================================================


def _make_combat_lines() -> list[AmbientLine]:
    """Lines for combat_after context tests."""
    return [
        AmbientLine(
            crew_id="marcus_jin",
            text="Drive seals took a hit. Six hours, minimum. Combat isn't free.",
            context="combat_after",
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="Those range estimates were off. Note that for next time.",
            context="combat_after",
        ),
    ]


class TestCombatAfter:
    """CB-2 acceptance criterion 4: mark_combat + get_combat_after_line."""

    def test_mark_combat_records_day(self) -> None:
        mgr = AmbientDialogueManager(_make_combat_lines())
        assert mgr.last_combat_day is None
        mgr.mark_combat(5)
        assert mgr.last_combat_day == 5

    def test_combat_after_within_window_returns_line(self) -> None:
        mgr = AmbientDialogueManager(_make_combat_lines())
        mgr.mark_combat(0)
        result = mgr.get_combat_after_line(
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 50},
            current_day=2,
        )
        assert result is not None, "Should return a line within the 3-day window."
        crew_id, _text = result
        assert crew_id == "marcus_jin"

    def test_combat_after_on_day_zero_still_eligible(self) -> None:
        mgr = AmbientDialogueManager(_make_combat_lines())
        mgr.mark_combat(5)
        result = mgr.get_combat_after_line(
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 50},
            current_day=5,
        )
        assert result is not None

    def test_combat_after_outside_window_returns_none(self) -> None:
        mgr = AmbientDialogueManager(_make_combat_lines())
        mgr.mark_combat(0)
        result = mgr.get_combat_after_line(
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 50},
            current_day=4,  # 4 - 0 = 4 > default window 3
        )
        assert result is None, "Should return None outside the recency window."

    def test_combat_after_never_marked_returns_none(self) -> None:
        mgr = AmbientDialogueManager(_make_combat_lines())
        result = mgr.get_combat_after_line(
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 50},
            current_day=10,
        )
        assert result is None, "Should return None when combat never marked."

    def test_combat_after_respects_shown_set(self) -> None:
        mgr = AmbientDialogueManager(_make_combat_lines())
        mgr.mark_combat(0)
        # Only one marcus_jin combat_after line; exhaust it
        result1 = mgr.get_combat_after_line(
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 50},
            current_day=1,
        )
        assert result1 is not None
        result2 = mgr.get_combat_after_line(
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 50},
            current_day=1,
        )
        assert result2 is None, "Line should be in _shown after first fire."

    def test_combat_day_save_round_trip(self) -> None:
        mgr = AmbientDialogueManager(_make_combat_lines())
        mgr.mark_combat(7)
        state = mgr.to_dict()
        assert "last_combat_day" in state
        assert state["last_combat_day"] == 7

        mgr2 = AmbientDialogueManager(_make_combat_lines())
        mgr2.load_state(state)
        assert mgr2.last_combat_day == 7

    def test_load_state_missing_combat_day_defaults_none(self) -> None:
        """CB-2 criterion 6 + 20: old save without last_combat_day loads cleanly."""
        mgr = AmbientDialogueManager(_make_combat_lines())
        mgr.load_state({"shown_indices": []})  # Old save format, no last_combat_day
        assert mgr.last_combat_day is None


# ============================================================================
# CB-2: check_flag_lines
# ============================================================================


def _make_flag_trigger_lines() -> list[AmbientLine]:
    return [
        AmbientLine(
            crew_id="elena_reeves",
            text="He finally told us about his father.",
            context="flag_triggered",
            required_flags=["marcus_uprising_inheritance_seen"],
        ),
        AmbientLine(
            crew_id="marcus_jin",
            text="Prakash was more than compliance.",
            context="flag_triggered",
            required_flags=["heard_dcmc_intelligence"],
            excluded_flags=["attended_silent_shaft"],
        ),
        AmbientLine(
            crew_id="elena_reeves",
            text="Idle line, not flag_triggered.",
            context="idle",
        ),
    ]


class TestCheckFlagLines:
    """CB-2 acceptance criterion 5: check_flag_lines."""

    def test_returns_eligible_flag_triggered_line(self) -> None:
        mgr = AmbientDialogueManager(_make_flag_trigger_lines())
        result = mgr.check_flag_lines(
            player_flags={"marcus_uprising_inheritance_seen": True},
            recruited_ids=["elena_reeves"],
            loyalty_map={"elena_reeves": 0},
        )
        assert result is not None
        crew_id, text = result
        assert crew_id == "elena_reeves"
        assert "father" in text

    def test_skips_when_required_flag_missing(self) -> None:
        mgr = AmbientDialogueManager(_make_flag_trigger_lines())
        result = mgr.check_flag_lines(
            player_flags={},  # no flags set
            recruited_ids=["elena_reeves"],
            loyalty_map={"elena_reeves": 0},
        )
        assert result is None

    def test_skips_when_excluded_flag_set(self) -> None:
        mgr = AmbientDialogueManager(_make_flag_trigger_lines())
        result = mgr.check_flag_lines(
            player_flags={
                "heard_dcmc_intelligence": True,
                "attended_silent_shaft": True,  # excluded!
            },
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 0},
        )
        assert result is None

    def test_skips_when_min_loyalty_not_met(self) -> None:
        lines = [
            AmbientLine(
                crew_id="elena_reeves",
                text="High loyalty only.",
                context="flag_triggered",
                required_flags=["some_flag"],
                min_loyalty=80,
            )
        ]
        mgr = AmbientDialogueManager(lines)
        result = mgr.check_flag_lines(
            player_flags={"some_flag": True},
            recruited_ids=["elena_reeves"],
            loyalty_map={"elena_reeves": 10},
        )
        assert result is None

    def test_returns_none_when_no_match(self) -> None:
        mgr = AmbientDialogueManager(_make_flag_trigger_lines())
        result = mgr.check_flag_lines(
            player_flags={"unrelated_flag": True},
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 0},
        )
        assert result is None

    def test_marks_returned_line_shown(self) -> None:
        mgr = AmbientDialogueManager(_make_flag_trigger_lines())
        result1 = mgr.check_flag_lines(
            player_flags={"marcus_uprising_inheritance_seen": True},
            recruited_ids=["elena_reeves"],
            loyalty_map={"elena_reeves": 0},
        )
        assert result1 is not None
        # Second call: the line is now shown
        result2 = mgr.check_flag_lines(
            player_flags={"marcus_uprising_inheritance_seen": True},
            recruited_ids=["elena_reeves"],
            loyalty_map={"elena_reeves": 0},
        )
        assert result2 is None, "Line should not fire twice."

    def test_handles_empty_recruited(self) -> None:
        mgr = AmbientDialogueManager(_make_flag_trigger_lines())
        result = mgr.check_flag_lines(
            player_flags={"marcus_uprising_inheritance_seen": True},
            recruited_ids=[],
            loyalty_map={},
        )
        assert result is None


# ============================================================================
# CB-2: data-loader extension
# ============================================================================


class TestAmbientLoaderFlagFields:
    """CB-2 acceptance criterion 7: data_loader parses required_flags/excluded_flags."""

    def test_data_loader_parses_required_flags(self) -> None:
        """AmbientLine constructed from JSON-like dict carries required_flags."""
        from spacegame.models.ambient_dialogue import AmbientLine as AL

        line = AL(
            crew_id="elena_reeves",
            text="Test.",
            context="flag_triggered",
            required_flags=["marcus_uprising_inheritance_seen"],
            excluded_flags=["attended_silent_shaft"],
        )
        assert line.required_flags == ["marcus_uprising_inheritance_seen"]
        assert line.excluded_flags == ["attended_silent_shaft"]

    def test_data_loader_defaults_empty_lists(self) -> None:
        """Lines without flag fields default to empty lists (backward compat)."""
        line = AmbientLine(crew_id="marcus_jin", text="Plain.", context="idle")
        assert line.required_flags == []
        assert line.excluded_flags == []

    def test_loader_populates_flag_fields_from_json(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """load_ambient_dialogue reads required_flags/excluded_flags from JSON."""
        import json

        from spacegame.data_loader import DataLoader

        crew_dir = tmp_path / "crew"
        crew_dir.mkdir()
        sample = {
            "ambient_lines": [
                {
                    "crew_id": "elena_reeves",
                    "text": "Flagged line.",
                    "context": "flag_triggered",
                    "required_flags": ["heard_dcmc_intelligence"],
                    "excluded_flags": ["attended_silent_shaft"],
                },
                {
                    "crew_id": "marcus_jin",
                    "text": "Plain line.",
                    "context": "idle",
                },
            ]
        }
        (crew_dir / "ambient_dialogue.json").write_text(json.dumps(sample), encoding="utf-8")

        loader = DataLoader.__new__(DataLoader)
        loader.data_dir = tmp_path
        loader.ambient_lines = []

        loader.load_ambient_dialogue()

        assert len(loader.ambient_lines) == 2
        flagged = loader.ambient_lines[0]
        assert flagged.required_flags == ["heard_dcmc_intelligence"]
        assert flagged.excluded_flags == ["attended_silent_shaft"]
        plain = loader.ambient_lines[1]
        assert plain.required_flags == []
        assert plain.excluded_flags == []


# ============================================================================
# CB-2: content floor tests
# ============================================================================


class TestCb2ContentFloor:
    """CB-2 acceptance criteria 10-14: new lines meet per-context quotas."""

    def _load_lines(self) -> list[AmbientLine]:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        return dl.ambient_lines

    def test_destination_floor(self) -> None:
        """Criterion 10: home_system + faction_territory >= 64 total (baseline 44 + 20 new)."""
        lines = self._load_lines()
        count = sum(1 for l in lines if l.context in ("home_system", "faction_territory"))
        assert count >= 64, f"Destination lines: {count} (need >= 64)"

    def test_crew_pair_floor(self) -> None:
        """Criterion 11: inter_crew >= 67 (baseline 52 + 15 new)."""
        lines = self._load_lines()
        count = sum(1 for l in lines if l.context == "inter_crew")
        assert count >= 67, f"inter_crew lines: {count} (need >= 67)"

    def test_flag_triggered_floor(self) -> None:
        """Criterion 12: flag_triggered >= 10, with >= 5 distinct required flags."""
        lines = self._load_lines()
        ft_lines = [l for l in lines if l.context == "flag_triggered"]
        assert len(ft_lines) >= 10, f"flag_triggered count: {len(ft_lines)} (need >= 10)"
        all_flags: set[str] = set()
        for l in ft_lines:
            all_flags.update(l.required_flags)
        assert len(all_flags) >= 5, f"Distinct required_flags: {len(all_flags)} (need >= 5)"

    def test_combat_after_floor(self) -> None:
        """Criterion 13: combat_after >= 5, >= 1 per primary crew member."""
        lines = self._load_lines()
        ca_lines = [l for l in lines if l.context == "combat_after"]
        assert len(ca_lines) >= 5, f"combat_after count: {len(ca_lines)} (need >= 5)"
        primary = {"elena_reeves", "marcus_jin", "dr_priya_osei", "tomas_drifter"}
        for crew_id in primary:
            crew_ca = [l for l in ca_lines if l.crew_id == crew_id]
            assert len(crew_ca) >= 1, f"No combat_after line for {crew_id}"

    def test_idle_floor(self) -> None:
        """Criterion 14: idle >= 103 (baseline 93 + 10 new)."""
        lines = self._load_lines()
        count = sum(1 for l in lines if l.context == "idle")
        assert count >= 103, f"idle lines: {count} (need >= 103)"


# ============================================================================
# CB-2: backward compatibility regression test
# ============================================================================


class TestExistingLinesStillResolve:
    """CB-2 acceptance criterion 17: existing lines still fire after sprint."""

    def _load_manager(self) -> AmbientDialogueManager:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        return AmbientDialogueManager(dl.ambient_lines)

    def test_home_system_line_resolves(self) -> None:
        mgr = self._load_manager()
        result = mgr.get_line(
            context="home_system",
            crew_id="elena_reeves",
            system_id="stellaris_port",
        )
        assert result is not None, "elena_reeves home_system line at stellaris_port should resolve."

    def test_faction_territory_line_resolves(self) -> None:
        mgr = self._load_manager()
        result = mgr.get_line(
            context="faction_territory",
            crew_id="elena_reeves",
            faction_id="commerce_guild",
        )
        assert result is not None, "elena_reeves faction_territory line should resolve."

    def test_player_action_line_resolves(self) -> None:
        mgr = self._load_manager()
        result = mgr.get_player_action_line(
            action_type="combat_victory",
            recruited_ids=["marcus_jin"],
            loyalty_map={"marcus_jin": 50},
        )
        assert result is not None, "marcus_jin combat_victory player_action line should resolve."


# ============================================================================
# CB-2: voice fidelity sanity test
# ============================================================================


class TestPrimaryCrewVoiceMarkers:
    """CB-2 acceptance criterion 18: new lines include tonal markers per character_voices.md."""

    def _lines_for(self, crew_id: str) -> list[AmbientLine]:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        return [l for l in dl.ambient_lines if l.crew_id == crew_id]

    def test_elena_reeves_has_precise_register(self) -> None:
        """Elena: uses precise quantity/time words (minutes, credits, hours, percent, etc.)."""
        lines = self._lines_for("elena_reeves")
        markers = (
            "minute",
            "credit",
            "hour",
            "percent",
            "cost",
            "fuel",
            "rate",
            "margin",
            "ledger",
            "cargo",
            "tonnage",
            "coupling",
            "exactly",
        )
        hits = [l for l in lines if any(m in l.text.lower() for m in markers)]
        assert len(hits) >= 1, "Elena should have >= 1 line with a precise register marker."

    def test_marcus_jin_has_practical_register(self) -> None:
        """Marcus: short declarative sentences, equipment/documentation focus."""
        lines = self._lines_for("marcus_jin")
        markers = (
            "section",
            "paragraph",
            "combat isn't",
            "drive",
            "seal",
            "maintenance",
            "contract",
            "nobody reads",
            "preventative",
        )
        hits = [l for l in lines if any(m in l.text.lower() for m in markers)]
        assert len(hits) >= 1, "Marcus should have >= 1 line with a practical/documentation marker."

    def test_priya_osei_has_institutional_register(self) -> None:
        """Priya: Institute framing, 'on record', precision, dry implication."""
        lines = self._lines_for("dr_priya_osei")
        markers = (
            "institute",
            "on record",
            "recategorized",
            "documented",
            "collective",
            "data",
            "analysis",
            "recorded",
        )
        hits = [l for l in lines if any(m in l.text.lower() for m in markers)]
        assert len(hits) >= 1, "Priya should have >= 1 line with an institutional register marker."

    def test_tomas_drifter_has_frontier_register(self) -> None:
        """Tomas: 'Way I see it', first-name address, trade metric framing."""
        lines = self._lines_for("tomas_drifter")
        markers = (
            "way i see it",
            "elena",
            "marcus",
            "priya",
            "savings",
            "credits",
            "margins",
            "route",
            "jump",
            "drifter",
            "hull",
        )
        hits = [l for l in lines if any(m in l.text.lower() for m in markers)]
        assert len(hits) >= 1, (
            "Tomas should have >= 1 line with a frontier/first-name register marker."
        )
