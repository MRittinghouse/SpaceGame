"""
Phase B8.4 — Surface-layer integration tests.

Covers what B8.4 wired:
- ``inject_available_dual_techs`` populates ``player.dual_tech_moves``
  with the techs the current crew qualifies for.
- ``build_player_combat_state`` calls the injection so the combat view
  sees dual techs as combat-start state.
- ``ActionQueue`` applies the Fire at Will discount at queue time,
  enabling the player to pre-plan bigger alpha strikes.

Combat view rendering and cinematic dialogue are out of scope — see
the Deferred Items Log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spacegame.models.action_queue import ActionQueue
from spacegame.models.combat import (
    CombatEffect,
    CombatMove,
    EffectType,
    PlayerCombatState,
)
from spacegame.models.dual_tech import (
    DUAL_TECH_PALETTE,
    build_fire_at_will_move,
    inject_available_dual_techs,
)

# ============================================================================
# Roster + player helpers
# ============================================================================


@dataclass
class _FakeRoster:
    states: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_member_state(self, template_id: str) -> dict[str, Any] | None:
        return self.states.get(template_id)

    def get_recruited_members(self) -> list:
        """build_player_combat_state iterates this for crew_moves."""
        return []


def _roster(**crew_loyalties: int) -> _FakeRoster:
    return _FakeRoster(
        states={cid: {"loyalty": loy} for cid, loy in crew_loyalties.items()}
    )


def _player() -> PlayerCombatState:
    return PlayerCombatState(
        hull=100,
        max_hull=100,
        shields=0,
        max_shields=0,
        energy=20,
        max_energy=20,
        energy_regen=5,
        speed=6,
        evasion=0,
        accuracy=90,
        equipment_moves=[],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
    )


ELENA = "elena_reeves"
MARCUS = "marcus_jin"
PRIYA = "dr_priya_osei"
TOMAS = "tomas_drifter"


# ============================================================================
# Injection — empty, partial, full roster
# ============================================================================


class TestInjection:
    def test_no_crew_leaves_dual_tech_moves_empty(self) -> None:
        player = _player()
        n = inject_available_dual_techs(player, _roster())
        assert n == 0
        assert player.dual_tech_moves == []

    def test_none_roster_is_noop(self) -> None:
        player = _player()
        n = inject_available_dual_techs(player, None)
        assert n == 0
        assert player.dual_tech_moves == []

    def test_l2_pair_unlocks_one_tech(self) -> None:
        """Elena + Marcus at L2 (50) unlocks Fire at Will only."""
        player = _player()
        roster = _roster(**{ELENA: 60, MARCUS: 60})
        n = inject_available_dual_techs(player, roster)
        assert n == 1
        assert {m.id for m in player.dual_tech_moves} == {"fire_at_will"}

    def test_all_max_loyalty_injects_everything(self) -> None:
        player = _player()
        roster = _roster(**{ELENA: 100, MARCUS: 100, PRIYA: 100, TOMAS: 100})
        n = inject_available_dual_techs(player, roster)
        # 6 pairs + 1 triad.
        assert n == 7
        assert {m.id for m in player.dual_tech_moves} == set(
            DUAL_TECH_PALETTE.keys()
        )

    def test_injected_moves_are_tagged_coordinated(self) -> None:
        """The UI uses the ``category`` field to route to tabs."""
        player = _player()
        roster = _roster(**{ELENA: 60, MARCUS: 60})
        inject_available_dual_techs(player, roster)
        for move in player.dual_tech_moves:
            assert move.category == "coordinated", (
                f"{move.id} should be tagged coordinated, got {move.category}"
            )

    def test_second_injection_replaces_previous(self) -> None:
        """Running injection twice should reflect the current roster,
        not accumulate."""
        player = _player()
        inject_available_dual_techs(
            player, _roster(**{ELENA: 100, MARCUS: 100, PRIYA: 100, TOMAS: 100})
        )
        assert len(player.dual_tech_moves) == 7
        # Roster changes — only 2 crew qualified now.
        inject_available_dual_techs(player, _roster(**{ELENA: 60, MARCUS: 60}))
        assert len(player.dual_tech_moves) == 1


# ============================================================================
# build_player_combat_state calls the injection
# ============================================================================


class TestBuildPlayerCombatStateInjection:
    def test_build_state_includes_dual_tech_moves(self) -> None:
        """Smoke test: when a crew_roster is provided, the resulting
        PlayerCombatState surface should include dual_tech_moves."""
        from spacegame.models.combat import build_player_combat_state
        from spacegame.models.ship import Ship, ShipType

        # Minimal ship — legacy path will be used (no build).
        st = ShipType(
            id="test",
            name="Test",
            ship_class="early_game",
            description="",
            cargo_capacity=50,
            fuel_capacity=50,
            fuel_efficiency=10,
            speed_multiplier=1.0,
            purchase_price=0,
            resale_value=0,
            crew_slots=4,
            special_abilities=[],
            availability="common",
            combat_hull=100,
            combat_shields=20,
            combat_energy=20,
            combat_energy_regen=4,
            combat_speed=5,
            combat_evasion=10,
            combat_accuracy=70,
        )
        ship = Ship(ship_type=st, current_fuel=50)
        from spacegame.models.upgrades import ShipUpgradeManager

        roster = _roster(**{ELENA: 100, MARCUS: 100})

        state = build_player_combat_state(
            ship=ship,
            upgrade_manager=ShipUpgradeManager(),
            crew_roster=roster,  # type: ignore[arg-type]
            crew_combat_moves={},
        )
        assert hasattr(state, "dual_tech_moves")
        ids = {m.id for m in state.dual_tech_moves}
        assert "fire_at_will" in ids, (
            f"Elena + Marcus @ 100 should unlock Fire at Will; got {ids}"
        )


# ============================================================================
# ActionQueue — Fire at Will queue-time prediction
# ============================================================================


def _weapon(wid: str = "laser", damage: float = 20.0, energy: int = 4) -> CombatMove:
    return CombatMove(
        id=wid,
        name=wid.title(),
        description="",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy,
        cooldown=0,
    )


class TestFireAtWillQueueTimePrediction:
    def test_weapon_costs_full_when_faw_not_queued(self) -> None:
        """Baseline: without FAW in queue, a 4-energy weapon costs 4."""
        q = ActionQueue(energy_available=10)
        laser = _weapon(energy=4)
        q.add(laser.id, 0, laser)
        assert q.energy_committed == 4
        assert q.energy_remaining == 6

    def test_weapon_after_faw_costs_half(self) -> None:
        """Queue FAW (6E), then a weapon (base 4E) — weapon is charged 2E."""
        q = ActionQueue(energy_available=20)
        faw = build_fire_at_will_move()
        laser = _weapon(energy=4)

        ok, _ = q.add(faw.id, 0, faw)
        assert ok
        assert q.energy_committed == 6  # FAW full cost

        ok, _ = q.add(laser.id, 0, laser)
        assert ok
        # FAW (6) + halved laser (2) = 8 committed.
        assert q.energy_committed == 8

    def test_can_add_agrees_with_add_under_faw(self) -> None:
        """With FAW queued, can_add should predict the discount — a
        weapon that wouldn't fit at full cost fits at half."""
        q = ActionQueue(energy_available=7)
        faw = build_fire_at_will_move()
        q.add(faw.id, 0, faw)  # 6E. 1E remaining.

        # Full-cost weapon (2E) would not fit in 1E.
        # Half-cost weapon (1E) should fit.
        laser = _weapon("l1", energy=2)  # halved → 1E
        can, _ = q.can_add(laser.id, laser)
        assert can, "Laser (2E base → 1E discounted) should fit in 1E remaining"

    def test_multiple_weapons_all_discounted_after_faw(self) -> None:
        """Every weapon queued after FAW is discounted — not just the first."""
        q = ActionQueue(energy_available=20)
        q.add("fire_at_will", 0, build_fire_at_will_move())
        for i in range(3):
            w = _weapon(f"l{i}", energy=4)
            ok, _ = q.add(w.id, 0, w)
            assert ok
        # FAW (6) + 3 lasers @ 2 each (6) = 12 total committed.
        assert q.energy_committed == 12

    def test_non_weapon_move_not_discounted_under_faw(self) -> None:
        """Fire at Will's discount targets weapons only — a heal or
        buff queued after it pays full price."""
        q = ActionQueue(energy_available=20)
        q.add("fire_at_will", 0, build_fire_at_will_move())

        # Non-damage "utility" move (e.g., shield restore stand-in).
        buff = CombatMove(
            id="buff",
            name="Buff",
            description="",
            effects=[
                CombatEffect(
                    type=EffectType.EVASION_MOD, value=10.0, duration=2
                )
            ],
            energy_cost=4,
            cooldown=0,
        )
        q.add(buff.id, 0, buff)
        # FAW (6) + buff full cost (4) = 10.
        assert q.energy_committed == 10

    def test_weapon_before_faw_pays_full_cost(self) -> None:
        """Queuing a weapon BEFORE FAW means no discount applies to it —
        the discount only flows to weapons queued AFTER FAW."""
        q = ActionQueue(energy_available=20)
        laser = _weapon(energy=4)
        q.add(laser.id, 0, laser)
        assert q.energy_committed == 4

        q.add("fire_at_will", 0, build_fire_at_will_move())
        # Laser already committed at 4; FAW 6. Total 10.
        assert q.energy_committed == 10

    def test_clear_resets_fire_at_will_flag(self) -> None:
        """After clear, re-queuing a weapon should not get discounted."""
        q = ActionQueue(energy_available=20)
        q.add("fire_at_will", 0, build_fire_at_will_move())
        q.clear()
        laser = _weapon(energy=4)
        q.add(laser.id, 0, laser)
        assert q.energy_committed == 4  # Full cost, no discount.
