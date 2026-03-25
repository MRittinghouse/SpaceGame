"""Tests for Phase U2.5a — Combat Action Queue.

Covers queue building, validation (energy, cooldowns, once-per-turn),
queue execution, undo, and edge cases.
"""

from spacegame.models.action_queue import ActionQueue, QueuedAction
from spacegame.models.combat import CombatMove, CombatEffect, EffectType, EffectTarget


# ============================================================================
# Helpers
# ============================================================================


def _laser() -> CombatMove:
    return CombatMove(
        id="laser",
        name="Laser Cannon",
        description="Pew pew",
        effects=[
            CombatEffect(type=EffectType.DAMAGE, value=15.0, duration=0, target=EffectTarget.ENEMY)
        ],
        energy_cost=2,
        cooldown=0,
    )


def _plasma() -> CombatMove:
    return CombatMove(
        id="plasma",
        name="Plasma Repeater",
        description="Burn",
        effects=[
            CombatEffect(type=EffectType.DAMAGE, value=20.0, duration=0, target=EffectTarget.ENEMY)
        ],
        energy_cost=3,
        cooldown=2,
    )


def _torpedo() -> CombatMove:
    return CombatMove(
        id="torpedo",
        name="Torpedo",
        description="Big boom",
        effects=[
            CombatEffect(type=EffectType.DAMAGE, value=40.0, duration=0, target=EffectTarget.ENEMY)
        ],
        energy_cost=5,
        cooldown=3,
    )


def _shield_restore() -> CombatMove:
    return CombatMove(
        id="shield_restore",
        name="Shield Restore",
        description="Fix shields",
        effects=[
            CombatEffect(
                type=EffectType.SHIELD_RESTORE, value=20.0, duration=0, target=EffectTarget.SELF
            )
        ],
        energy_cost=2,
        cooldown=1,
    )


def _all_moves() -> dict[str, CombatMove]:
    return {m.id: m for m in [_laser(), _plasma(), _torpedo(), _shield_restore()]}


# ============================================================================
# Queue Building
# ============================================================================


class TestQueueBuilding:
    def test_empty_queue(self) -> None:
        q = ActionQueue(energy_available=12)
        assert len(q.actions) == 0
        assert q.energy_remaining == 12

    def test_add_one_action(self) -> None:
        q = ActionQueue(energy_available=12)
        ok, msg = q.add("laser", 0, _laser())
        assert ok, msg
        assert len(q.actions) == 1
        assert q.energy_remaining == 10

    def test_add_multiple_actions(self) -> None:
        q = ActionQueue(energy_available=12)
        q.add("laser", 0, _laser())
        q.add("plasma", 0, _plasma())
        q.add("shield_restore", -1, _shield_restore())
        assert len(q.actions) == 3
        assert q.energy_remaining == 5  # 12 - 2 - 3 - 2

    def test_energy_tracking(self) -> None:
        q = ActionQueue(energy_available=10)
        q.add("laser", 0, _laser())  # -2 → 8
        q.add("plasma", 0, _plasma())  # -3 → 5
        q.add("torpedo", 0, _torpedo())  # -5 → 0
        assert q.energy_remaining == 0
        assert q.energy_committed == 10


# ============================================================================
# Validation
# ============================================================================


class TestQueueValidation:
    def test_reject_insufficient_energy(self) -> None:
        q = ActionQueue(energy_available=3)
        ok, msg = q.add("torpedo", 0, _torpedo())  # Costs 5
        assert not ok
        assert "energy" in msg.lower()
        assert len(q.actions) == 0

    def test_reject_duplicate_weapon_same_turn(self) -> None:
        q = ActionQueue(energy_available=12)
        q.add("laser", 0, _laser())
        ok, msg = q.add("laser", 0, _laser())  # Same weapon twice
        assert not ok
        assert "already" in msg.lower() or "once" in msg.lower()

    def test_reject_move_on_cooldown(self) -> None:
        q = ActionQueue(energy_available=12, cooldowns={"plasma": 1})
        ok, msg = q.add("plasma", 0, _plasma())
        assert not ok
        assert "cooldown" in msg.lower()

    def test_allow_different_weapons_same_turn(self) -> None:
        q = ActionQueue(energy_available=12)
        ok1, _ = q.add("laser", 0, _laser())
        ok2, _ = q.add("plasma", 0, _plasma())
        assert ok1 and ok2

    def test_energy_depletes_across_queue(self) -> None:
        q = ActionQueue(energy_available=6)
        q.add("laser", 0, _laser())  # -2 → 4
        q.add("plasma", 0, _plasma())  # -3 → 1
        ok, msg = q.add("shield_restore", -1, _shield_restore())  # Costs 2, only 1 left
        assert not ok
        assert "energy" in msg.lower()


# ============================================================================
# Undo
# ============================================================================


class TestQueueUndo:
    def test_undo_last(self) -> None:
        q = ActionQueue(energy_available=12)
        q.add("laser", 0, _laser())
        q.add("plasma", 0, _plasma())
        assert q.energy_remaining == 7
        ok = q.remove_last()
        assert ok
        assert len(q.actions) == 1
        assert q.energy_remaining == 10  # Plasma refunded

    def test_undo_restores_weapon_availability(self) -> None:
        q = ActionQueue(energy_available=12)
        q.add("laser", 0, _laser())
        q.remove_last()
        # Should be able to re-add the laser
        ok, _ = q.add("laser", 0, _laser())
        assert ok

    def test_undo_empty_queue(self) -> None:
        q = ActionQueue(energy_available=12)
        ok = q.remove_last()
        assert not ok

    def test_multiple_undos(self) -> None:
        q = ActionQueue(energy_available=12)
        q.add("laser", 0, _laser())
        q.add("plasma", 0, _plasma())
        q.add("torpedo", 0, _torpedo())
        q.remove_last()
        q.remove_last()
        assert len(q.actions) == 1
        assert q.actions[0].move_id == "laser"
        assert q.energy_remaining == 10


# ============================================================================
# Queue Properties
# ============================================================================


class TestQueueProperties:
    def test_get_queued_move_ids(self) -> None:
        q = ActionQueue(energy_available=12)
        q.add("laser", 0, _laser())
        q.add("plasma", 1, _plasma())
        ids = q.get_queued_move_ids()
        assert ids == {"laser", "plasma"}

    def test_is_empty(self) -> None:
        q = ActionQueue(energy_available=12)
        assert q.is_empty
        q.add("laser", 0, _laser())
        assert not q.is_empty

    def test_clear(self) -> None:
        q = ActionQueue(energy_available=12)
        q.add("laser", 0, _laser())
        q.add("plasma", 0, _plasma())
        q.clear()
        assert q.is_empty
        assert q.energy_remaining == 12

    def test_action_list_contents(self) -> None:
        q = ActionQueue(energy_available=12)
        q.add("laser", 0, _laser())
        q.add("plasma", 1, _plasma())
        assert q.actions[0].move_id == "laser"
        assert q.actions[0].target_idx == 0
        assert q.actions[0].energy_cost == 2
        assert q.actions[1].move_id == "plasma"
        assert q.actions[1].target_idx == 1
        assert q.actions[1].energy_cost == 3


# ============================================================================
# Edge Cases
# ============================================================================


class TestQueueEdgeCases:
    def test_zero_energy_move(self) -> None:
        """A move with 0 energy cost should always be queueable."""
        free_move = CombatMove(
            id="free",
            name="Free Strike",
            description="",
            effects=[],
            energy_cost=0,
            cooldown=0,
        )
        q = ActionQueue(energy_available=0)
        ok, _ = q.add("free", 0, free_move)
        assert ok

    def test_self_target_action(self) -> None:
        """Self-targeted abilities (shields) use target_idx=-1 by convention."""
        q = ActionQueue(energy_available=12)
        ok, _ = q.add("shield_restore", -1, _shield_restore())
        assert ok
        assert q.actions[0].target_idx == -1

    def test_queue_respects_existing_cooldowns(self) -> None:
        """Cooldowns from previous rounds should block queueing."""
        q = ActionQueue(energy_available=12, cooldowns={"torpedo": 2, "plasma": 1})
        ok_torpedo, _ = q.add("torpedo", 0, _torpedo())
        ok_plasma, _ = q.add("plasma", 0, _plasma())
        ok_laser, _ = q.add("laser", 0, _laser())
        assert not ok_torpedo
        assert not ok_plasma
        assert ok_laser
