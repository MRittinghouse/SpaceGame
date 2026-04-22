"""
Phase B8.4 tail — Reveal scene integrity + engine emission tests.

Covers:
- DUAL_TECH_REVEALS palette integrity (one scene per tech, non-empty lines,
  sensible announcement).
- check_and_mark_reveal: returns the scene once, then None; marks the
  flag in place.
- Combat engine emits reveal log entries on first activation of each
  dual tech, and does NOT re-emit on subsequent activations.
"""

from __future__ import annotations

from spacegame.models.combat import (
    CombatEffect,
    CombatEncounter,
    CombatMove,
    CombatState,
    EffectTarget,
    EffectType,
    EnemyBehavior,
    EnemyShip,
    EnemyShipTemplate,
    PlayerCombatState,
)
from spacegame.models.combat_engine import CombatEngine
from spacegame.models.dual_tech import (
    DUAL_TECH_PALETTE,
    build_dual_tech_move,
)
from spacegame.models.dual_tech_dialogue import (
    DUAL_TECH_REVEALS,
    DualTechReveal,
    check_and_mark_reveal,
    reveal_flag_key,
)

# ============================================================================
# Palette integrity
# ============================================================================


class TestRevealPaletteIntegrity:
    def test_one_reveal_per_palette_tech(self) -> None:
        """Every dual tech in the gameplay palette has a reveal scene."""
        missing = set(DUAL_TECH_PALETTE.keys()) - set(DUAL_TECH_REVEALS.keys())
        assert not missing, f"Dual techs missing reveal scenes: {missing}"

    def test_no_orphan_reveals(self) -> None:
        """Reverse check: no reveals reference a tech_id the palette doesn't have."""
        orphans = set(DUAL_TECH_REVEALS.keys()) - set(DUAL_TECH_PALETTE.keys())
        assert not orphans, f"Reveal scenes for nonexistent techs: {orphans}"

    def test_each_reveal_has_nonempty_lines(self) -> None:
        for tid, reveal in DUAL_TECH_REVEALS.items():
            assert len(reveal.lines) >= 2, (
                f"{tid} reveal has only {len(reveal.lines)} lines; scenes need "
                f"at least a call + response"
            )
            for line in reveal.lines:
                assert line.text.strip(), f"{tid} reveal has empty line text"

    def test_announcement_format(self) -> None:
        """Announcements are the 'X is now available.' closer that confirms
        the unlock."""
        for tid, reveal in DUAL_TECH_REVEALS.items():
            assert reveal.announcement, f"{tid} reveal missing announcement"
            assert "available" in reveal.announcement.lower(), (
                f"{tid} announcement should confirm the unlock: "
                f"{reveal.announcement}"
            )

    def test_tech_id_matches_key(self) -> None:
        for key, reveal in DUAL_TECH_REVEALS.items():
            assert key == reveal.tech_id, (
                f"Palette key {key!r} != reveal.tech_id {reveal.tech_id!r}"
            )

    def test_to_log_entries_renders_scene(self) -> None:
        """to_log_entries produces one string per line plus the announcement."""
        reveal = DUAL_TECH_REVEALS["gun_run"]
        entries = reveal.to_log_entries()
        # 2 lines + announcement = 3 entries.
        assert len(entries) == len(reveal.lines) + 1
        assert entries[-1] == reveal.announcement


# ============================================================================
# check_and_mark_reveal — once-only behavior
# ============================================================================


class TestCheckAndMarkReveal:
    def test_first_call_returns_reveal_and_marks_flag(self) -> None:
        flags: dict[str, bool] = {}
        result = check_and_mark_reveal(flags, "gun_run")
        assert isinstance(result, DualTechReveal)
        assert flags[reveal_flag_key("gun_run")] is True

    def test_second_call_returns_none(self) -> None:
        flags: dict[str, bool] = {}
        first = check_and_mark_reveal(flags, "gun_run")
        assert first is not None
        second = check_and_mark_reveal(flags, "gun_run")
        assert second is None

    def test_unknown_tech_id_returns_none(self) -> None:
        flags: dict[str, bool] = {}
        assert check_and_mark_reveal(flags, "not_a_tech") is None
        assert flags == {}, "Unknown tech should not mark any flag"

    def test_different_techs_have_independent_flags(self) -> None:
        flags: dict[str, bool] = {}
        check_and_mark_reveal(flags, "gun_run")
        # Other techs still unseen.
        result = check_and_mark_reveal(flags, "fire_at_will")
        assert result is not None


# ============================================================================
# Combat engine emits reveal on first activation
# ============================================================================


def _weapon(
    wid: str = "laser", damage: float = 20.0, energy: int = 2
) -> CombatMove:
    return CombatMove(
        id=wid,
        name=wid.title(),
        description="",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy,
        cooldown=0,
    )


def _enemy_template() -> EnemyShipTemplate:
    attack = CombatMove(
        id="bite",
        name="Bite",
        description="",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=5, target=EffectTarget.ENEMY)],
        energy_cost=0,
    )
    return EnemyShipTemplate(
        id="dummy",
        name="Dummy",
        description="",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=1000,
        shields=0,
        energy=10,
        energy_regen=3,
        speed=1,
        evasion=0,
        accuracy=50,
        moves=[attack],
        loot_table=[],
        flee_threshold=0.0,
    )


def _build_engine(flags: dict[str, bool] | None = None) -> tuple[CombatEngine, PlayerCombatState]:
    player = PlayerCombatState(
        hull=200, max_hull=200, shields=0, max_shields=0,
        energy=30, max_energy=30, energy_regen=5,
        speed=6, evasion=0, accuracy=95,
        equipment_moves=[], crew_moves=[],
        active_effects=[], cooldowns={},
        dialogue_flags=flags if flags is not None else {},
    )
    tpl = _enemy_template()
    state = CombatState(
        player=player,
        enemies=[EnemyShip.from_template(tpl)],
        encounter=CombatEncounter(enemy_templates=[tpl], encounter_seed=0),
        combat_log=[],
    )
    return CombatEngine(state, seed=0), player


def _fire_dual_tech(engine: CombatEngine, player: PlayerCombatState, tech_id: str) -> list:
    move = build_dual_tech_move(tech_id)
    assert move is not None
    if move not in player.equipment_moves:
        player.equipment_moves.append(move)
    return engine.execute_player_move(move.id, 0)


def _find_reveal_entries(state: CombatState, tech_id: str) -> list:
    """Find combat log entries tagged as a reveal for the given tech."""
    # Reveal entries have the action "{move.name} (reveal)".
    palette_entry = DUAL_TECH_PALETTE[tech_id]
    marker = f"{palette_entry.name} (reveal)"
    return [e for e in state.combat_log if e.action == marker]


class TestEngineRevealEmission:
    def test_first_activation_emits_reveal(self) -> None:
        flags: dict[str, bool] = {}
        engine, player = _build_engine(flags)
        _fire_dual_tech(engine, player, "gun_run")

        reveals = _find_reveal_entries(engine.get_state(), "gun_run")
        assert len(reveals) == 1, (
            f"Expected 1 reveal entry on first activation; got "
            f"{[(e.action, e.effects_applied) for e in engine.get_state().combat_log]}"
        )
        # Flag persisted to the dialogue_flags dict.
        assert flags[reveal_flag_key("gun_run")] is True

    def test_second_activation_does_not_re_emit(self) -> None:
        flags: dict[str, bool] = {}
        engine, player = _build_engine(flags)
        _fire_dual_tech(engine, player, "gun_run")
        # Clear the log to isolate re-fire.
        engine.get_state().combat_log.clear()
        # Reset cooldown so activation isn't blocked.
        player.cooldowns.clear()
        _fire_dual_tech(engine, player, "gun_run")
        reveals = _find_reveal_entries(engine.get_state(), "gun_run")
        assert reveals == [], (
            f"Reveal should fire only once per combat history; "
            f"got re-emission: {reveals}"
        )

    def test_flag_persisted_across_engines(self) -> None:
        """Emulate new combat session: reuse the dialogue_flags dict."""
        flags: dict[str, bool] = {}
        engine1, p1 = _build_engine(flags)
        _fire_dual_tech(engine1, p1, "gun_run")

        # New combat with same flags dict.
        engine2, p2 = _build_engine(flags)
        _fire_dual_tech(engine2, p2, "gun_run")
        reveals = _find_reveal_entries(engine2.get_state(), "gun_run")
        assert reveals == [], "Reveal must not re-fire in a later combat"

    def test_each_tech_reveals_independently(self) -> None:
        """Using one tech shouldn't suppress reveals for others."""
        flags: dict[str, bool] = {}
        engine, player = _build_engine(flags)
        _fire_dual_tech(engine, player, "gun_run")
        player.cooldowns.clear()
        _fire_dual_tech(engine, player, "fire_at_will")
        # Clear the cd so we can activate.
        assert flags[reveal_flag_key("gun_run")] is True
        assert flags[reveal_flag_key("fire_at_will")] is True
        # Both reveals appear in the log.
        assert len(_find_reveal_entries(engine.get_state(), "gun_run")) == 1
        assert len(_find_reveal_entries(engine.get_state(), "fire_at_will")) == 1


# ============================================================================
# Caller wire-up — flags persist through build_player_combat_state
# ============================================================================


class TestBuildPlayerCombatStateDialogueFlagsWireup:
    """Verifies the caller-side wire-up: when ``build_player_combat_state``
    receives a dialogue_flags dict, the resulting PlayerCombatState holds
    it by reference. Reveals marked in one combat persist when a new
    combat state is built from the same dict — the guarantee that
    in-game sessions see reveals exactly once, not every combat."""

    def test_flags_attached_by_reference(self) -> None:
        """Mutations to state.dialogue_flags must surface in the
        caller's dict (not a copy)."""
        from spacegame.models.combat import build_player_combat_state
        from spacegame.models.ship import Ship, ShipType
        from spacegame.models.upgrades import ShipUpgradeManager

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
            crew_slots=1,
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
        flags: dict[str, bool] = {}

        state = build_player_combat_state(
            ship=ship,
            upgrade_manager=ShipUpgradeManager(),
            crew_roster=None,
            crew_combat_moves={},
            dialogue_flags=flags,
        )

        # Mutate via the combat state; the caller's dict sees the change.
        state.dialogue_flags["dual_tech_gun_run_revealed"] = True
        assert flags["dual_tech_gun_run_revealed"] is True, (
            "dialogue_flags must be attached by reference, not copied"
        )

    def test_reveals_persist_across_two_combat_states(self) -> None:
        """Simulates gameplay: combat 1 fires a reveal; combat 2 built
        from the same flags dict sees the flag already set and skips."""
        from spacegame.models.combat import build_player_combat_state
        from spacegame.models.ship import Ship, ShipType
        from spacegame.models.upgrades import ShipUpgradeManager

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
            crew_slots=1,
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
        flags: dict[str, bool] = {}

        # --- Combat 1
        state1 = build_player_combat_state(
            ship=Ship(ship_type=st, current_fuel=50),
            upgrade_manager=ShipUpgradeManager(),
            crew_roster=None,
            crew_combat_moves={},
            dialogue_flags=flags,
        )
        tpl = _enemy_template()
        cs1 = CombatState(
            player=state1,
            enemies=[EnemyShip.from_template(tpl)],
            encounter=CombatEncounter(enemy_templates=[tpl], encounter_seed=0),
            combat_log=[],
        )
        engine1 = CombatEngine(cs1, seed=0)
        _fire_dual_tech(engine1, state1, "gun_run")
        assert flags[reveal_flag_key("gun_run")] is True
        assert len(_find_reveal_entries(cs1, "gun_run")) == 1

        # --- Combat 2 — same flags dict. Reveal should NOT re-fire.
        state2 = build_player_combat_state(
            ship=Ship(ship_type=st, current_fuel=50),
            upgrade_manager=ShipUpgradeManager(),
            crew_roster=None,
            crew_combat_moves={},
            dialogue_flags=flags,
        )
        cs2 = CombatState(
            player=state2,
            enemies=[EnemyShip.from_template(tpl)],
            encounter=CombatEncounter(enemy_templates=[tpl], encounter_seed=0),
            combat_log=[],
        )
        engine2 = CombatEngine(cs2, seed=0)
        _fire_dual_tech(engine2, state2, "gun_run")
        assert _find_reveal_entries(cs2, "gun_run") == [], (
            "Reveal must not re-fire in a later combat built from the same "
            "dialogue_flags dict"
        )
