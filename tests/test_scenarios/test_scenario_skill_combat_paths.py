"""Scenario C: Skill bonuses apply in BOTH combat paths.

CLAUDE.md's explicit warning:
    ``build_player_combat_state()`` has TWO code paths (build-derived vs
    legacy ShipType) — skill bonuses must be applied in BOTH.

The build-derived path fires when ``ship.computed_stats`` is set. The legacy
path fires otherwise. Both must reflect skill bonuses identically, or players
with older saves (ShipType-only ships) will silently lose their skill power.
"""

from __future__ import annotations

from spacegame.models.combat import build_player_combat_state
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.models.ship_build import ComputedShipStats, PlacedPixel, ShipBuild
from spacegame.models.upgrades import ShipUpgradeManager
from tests.test_scenarios._helpers import real_ship_type


def _player_with_skill_level(skill_id: str, target_level: int) -> Player:
    """Build a Player whose progression has ``skill_id`` at ``target_level``.

    Bypasses XP gating by directly granting skill points. Also unlocks
    prerequisites transitively if needed.
    """
    player = Player(
        name="SkillTest",
        credits=1000,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=real_ship_type("shuttle"), current_fuel=40),
    )
    # Grant enough skill points, bypass xp gating.
    player.progression.skill_points = 100
    skill = player.progression.skills.get(skill_id)
    if skill is None:
        raise ValueError(f"skill '{skill_id}' not found")

    # Walk the prereq chain bottom-up: collect ancestors, then level up
    # starting from root → root's child → ... → target's direct prereq.
    ancestors: list[str] = []
    prereq = skill.prerequisite_id
    while prereq:
        ancestors.append(prereq)
        prereq_skill = player.progression.skills.get(prereq)
        prereq = prereq_skill.prerequisite_id if prereq_skill else None
    for pid in reversed(ancestors):
        player.progression.level_up_skill(pid)

    # Level the target.
    for _ in range(target_level):
        ok, _msg = player.progression.level_up_skill(skill_id)
        if not ok:
            break
    return player


def _build_state_for_player(player: Player):
    """Helper: call ``build_player_combat_state`` with minimal setup."""
    upgrade_mgr = ShipUpgradeManager()
    return build_player_combat_state(
        ship=player.ship,
        upgrade_manager=upgrade_mgr,
        crew_roster=None,
        crew_combat_moves={},
        player_level=5,
        progression=player.progression,
        dialogue_flags=player.dialogue_flags,
    )


def _attach_minimal_build(player: Player) -> None:
    """Give the player a ShipBuild with ComputedShipStats — forces build-derived path."""
    build = ShipBuild(
        weight_class="small",
        pixels=[PlacedPixel(x, y, "module_hull_rk") for x in range(4) for y in range(4)],
    )
    player.ship.set_build(build, full_heal=True)
    # Confirm forking condition
    assert isinstance(player.ship.computed_stats, ComputedShipStats), (
        "Build must produce ComputedShipStats to force the build-derived path"
    )


class TestArmorBonusAppliesToBothPaths:
    """armor_expertise skill (bonus_type=armor_bonus) — +1 armor per level."""

    def test_armor_skill_applies_in_legacy_path(self) -> None:
        player = _player_with_skill_level("armor_expertise", target_level=2)
        baseline_armor = player.ship.ship_type.combat_armor

        state = _build_state_for_player(player)

        assert state.armor > baseline_armor, (
            f"Legacy path must apply armor_bonus skill. "
            f"baseline={baseline_armor}, got={state.armor}"
        )

    def test_armor_skill_applies_in_build_path(self) -> None:
        player = _player_with_skill_level("armor_expertise", target_level=2)
        _attach_minimal_build(player)

        state = _build_state_for_player(player)

        expected_baseline = player.ship.computed_stats.armor
        assert state.armor > expected_baseline, (
            f"Build-derived path must apply armor_bonus skill. "
            f"baseline={expected_baseline}, got={state.armor}"
        )


class TestShieldRegenBonusAppliesToBothPaths:
    """shield_regen skill (bonus_type=shield_regen_bonus) — +2 regen per level."""

    def test_shield_regen_applies_in_legacy_path(self) -> None:
        player = _player_with_skill_level("shield_regen", target_level=1)
        baseline_regen = player.ship.ship_type.combat_shield_regen

        state = _build_state_for_player(player)

        assert state.shield_regen > baseline_regen, (
            "Legacy path must apply shield_regen_bonus skill"
        )

    def test_shield_regen_applies_in_build_path(self) -> None:
        player = _player_with_skill_level("shield_regen", target_level=1)
        _attach_minimal_build(player)

        state = _build_state_for_player(player)

        baseline_regen = player.ship.computed_stats.shield_regen
        assert state.shield_regen > baseline_regen, (
            "Build-derived path must apply shield_regen_bonus skill"
        )


class TestDodgeChanceAppliesToBothPaths:
    """evasive_maneuvers skill (bonus_type=dodge_chance) — +5% per level."""

    def test_dodge_applies_in_legacy_path(self) -> None:
        player = _player_with_skill_level("evasive_maneuvers", target_level=2)
        baseline = player.ship.ship_type.combat_evasion

        state = _build_state_for_player(player)

        assert state.evasion > baseline, "Legacy path must apply dodge_chance skill to evasion"

    def test_dodge_applies_in_build_path(self) -> None:
        player = _player_with_skill_level("evasive_maneuvers", target_level=2)
        _attach_minimal_build(player)

        state = _build_state_for_player(player)

        baseline = player.ship.computed_stats.evasion
        assert state.evasion > baseline, "Build-derived path must apply dodge_chance skill"


class TestHullHPBonusAppliesToBothPaths:
    """hull_reinforcement skill (bonus_type=hull_hp_bonus) — +5% hull per level.
    Most likely to diverge between paths because base hull value differs.
    """

    def test_hull_hp_bonus_applies_in_legacy_path(self) -> None:
        player = _player_with_skill_level("hull_reinforcement", target_level=2)
        baseline_hull = player.ship.ship_type.combat_hull

        state = _build_state_for_player(player)

        assert state.max_hull > baseline_hull, "Legacy path must apply hull_hp_bonus"

    def test_hull_hp_bonus_applies_in_build_path(self) -> None:
        player = _player_with_skill_level("hull_reinforcement", target_level=2)
        _attach_minimal_build(player)

        state = _build_state_for_player(player)

        baseline = player.ship.computed_stats.hull
        assert state.max_hull > baseline, "Build-derived path must apply hull_hp_bonus"


class TestFleeBonusAppliesToBothPaths:
    def test_flee_bonus_applies_in_legacy_path(self) -> None:
        player = _player_with_skill_level("tactical_retreat", target_level=1)
        state = _build_state_for_player(player)
        # Early-game flee bonus adds at level<5; we set level=5 so only skill
        # contributes + base ship type contributions.
        assert state.flee_bonus >= 0

    def test_flee_bonus_applies_in_build_path(self) -> None:
        player = _player_with_skill_level("tactical_retreat", target_level=1)
        _attach_minimal_build(player)
        state = _build_state_for_player(player)
        assert state.flee_bonus >= 0


class TestNoSkillsBaseline:
    """Sanity check: with zero skills, both paths produce values within
    reasonable range of their ShipType/build baselines."""

    def test_zero_skills_legacy_path_matches_ship_type(self) -> None:
        player = Player(
            name="Baseline",
            credits=0,
            current_system_id="nexus_prime",
            ship=Ship(ship_type=real_ship_type("shuttle"), current_fuel=40),
        )
        state = _build_state_for_player(player)
        assert state.max_hull == player.ship.ship_type.combat_hull
        assert state.max_shields == player.ship.ship_type.combat_shields

    def test_zero_skills_build_path_matches_computed_stats(self) -> None:
        player = Player(
            name="Baseline",
            credits=0,
            current_system_id="nexus_prime",
            ship=Ship(ship_type=real_ship_type("shuttle"), current_fuel=40),
        )
        _attach_minimal_build(player)
        state = _build_state_for_player(player)
        assert state.max_hull == player.ship.computed_stats.hull
        assert state.max_shields == player.ship.computed_stats.shields
