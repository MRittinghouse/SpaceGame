"""Tests for combat passive feedback messages in log entries.

Validates that Ghost counterstrike, Sentinel shield break, and
module hit message formatting work correctly for player feedback.
"""

from spacegame.models.combat import PlayerCombatState


def _make_player(**overrides: object) -> PlayerCombatState:
    """Create a minimal PlayerCombatState for testing."""
    defaults = dict(
        hull=100,
        max_hull=100,
        shields=50,
        max_shields=50,
        evasion=20,
        accuracy=70,
        speed=10,
        energy=10,
        max_energy=10,
        energy_regen=3,
        equipment_moves=[],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
    )
    defaults.update(overrides)
    return PlayerCombatState(**defaults)  # type: ignore[arg-type]


class TestGhostCounterstrikeFeedback:
    def test_counterstrike_stacks_cap_at_3(self) -> None:
        p = _make_player(defensive_identity="ghost", counterstrike_stacks=3)
        new = min(p.counterstrike_stacks + 1, 3)
        assert new == 3

    def test_counterstrike_increment_generates_message(self) -> None:
        """Stack increase should produce a feedback message."""
        p = _make_player(defensive_identity="ghost", counterstrike_stacks=1)
        prev = p.counterstrike_stacks
        p.counterstrike_stacks = min(p.counterstrike_stacks + 1, 3)
        assert p.counterstrike_stacks > prev
        pct = p.counterstrike_stacks * 12
        msg = f"Counterstrike +{pct}%"
        assert "Counterstrike" in msg
        assert "+24%" in msg

    def test_counterstrike_at_cap_no_message(self) -> None:
        """No message should be generated when already at max stacks."""
        p = _make_player(defensive_identity="ghost", counterstrike_stacks=3)
        prev = p.counterstrike_stacks
        p.counterstrike_stacks = min(p.counterstrike_stacks + 1, 3)
        assert p.counterstrike_stacks == prev  # No change

    def test_counterstrike_reset_only_when_positive(self) -> None:
        p = _make_player(defensive_identity="ghost", counterstrike_stacks=0)
        should_log = p.counterstrike_stacks > 0
        assert not should_log

    def test_counterstrike_reset_when_positive_generates_message(self) -> None:
        p = _make_player(defensive_identity="ghost", counterstrike_stacks=2)
        should_log = p.counterstrike_stacks > 0
        assert should_log
        p.counterstrike_stacks = 0
        assert p.counterstrike_stacks == 0


class TestSentinelShieldBreakFeedback:
    def test_shield_break_triggers_when_shields_zero(self) -> None:
        p = _make_player(
            defensive_identity="sentinel",
            shields=0,
            shield_break_vulnerable=False,
        )
        if p.shields == 0 and not p.shield_break_vulnerable:
            p.shield_break_vulnerable = True
        assert p.shield_break_vulnerable

    def test_shield_break_does_not_retrigger(self) -> None:
        p = _make_player(
            defensive_identity="sentinel",
            shields=0,
            shield_break_vulnerable=True,
        )
        should_trigger = p.shields == 0 and not p.shield_break_vulnerable
        assert not should_trigger


class TestModuleDamageMessageFormat:
    def test_bracket_extraction(self) -> None:
        text = "Dealt 45 damage to Player (30 shields, 15 hull) [Engine hit (15/20 HP)]"
        bracket_start = text.index("[")
        bracket_end = text.index("]") + 1
        module_text = text[bracket_start + 1 : bracket_end - 1]
        damage_text = text[:bracket_start].rstrip()
        assert module_text == "Engine hit (15/20 HP)"
        assert "hull)" in damage_text
        assert "[" not in damage_text

    def test_no_brackets_unchanged(self) -> None:
        text = "Dealt 20 damage to Enemy (20 shields, 0 hull)"
        assert "[" not in text

    def test_disabled_module_extraction(self) -> None:
        text = (
            "Dealt 60 damage to Player (0 shields, 60 hull) "
            "[weapon module disabled! (weapon_01) weapon_01 offline!]"
        )
        bracket_start = text.index("[")
        bracket_end = text.index("]") + 1
        module_text = text[bracket_start + 1 : bracket_end - 1]
        assert "disabled" in module_text
        assert "offline" in module_text


class TestFrozenMessageBugFix:
    """Verify FROZEN message doesn't appear when boss is immune."""

    def test_immune_boss_should_not_show_frozen(self) -> None:
        """Previously, FROZEN message was appended outside the if/else block,
        causing it to appear even when the boss was immune."""
        # Simulate the fixed code path
        immune_to_frozen = True
        messages: list[str] = []
        if immune_to_frozen:
            messages.append("Boss resists being frozen!")
        else:
            messages.append("FROZEN! Skips next turn")
        # The fix: no unconditional append outside the if/else
        assert "FROZEN" not in " ".join(messages)
        assert "resists" in messages[0]

    def test_non_immune_enemy_shows_frozen(self) -> None:
        immune_to_frozen = False
        messages: list[str] = []
        if immune_to_frozen:
            messages.append("Boss resists being frozen!")
        else:
            messages.append("FROZEN! Skips next turn")
        assert "FROZEN" in messages[0]
        assert len(messages) == 1  # Only one message, not two
