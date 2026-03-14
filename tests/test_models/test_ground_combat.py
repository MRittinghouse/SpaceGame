"""Tests for ground combat 'Dice & Grit' system (Phase C)."""

import pytest

from spacegame.models.attributes import AttributeSheet
from spacegame.models.ground_combat import (
    GROUND_ENEMY_TEMPLATES,
    CombatAction,
    CombatOutcome,
    ExchangeResult,
    GroundCombatEngine,
    GroundCombatState,
    GroundCombatantStats,
    SocialSkillType,
    build_player_ground_combat_stats,
    make_enemy_from_template,
)
from spacegame.models.progression import PlayerProgression, SkillTreeType


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_player(**overrides: object) -> GroundCombatantStats:
    """Create player combatant stats with defaults."""
    defaults: dict = {
        "hp": 8,
        "max_hp": 8,
        "attack_mod": 0,
        "defense_mod": 0,
        "shield": 0,
        "rerolls": 0,
    }
    defaults.update(overrides)
    return GroundCombatantStats(**defaults)


def _make_enemy(**overrides: object) -> GroundCombatantStats:
    """Create enemy combatant stats with defaults."""
    defaults: dict = {
        "hp": 4,
        "max_hp": 4,
        "attack_mod": 2,
        "defense_mod": 2,
        "shield": 0,
        "rerolls": 0,
        "talk_difficulty": 6,
        "name": "Guild Security",
        "is_automated": False,
    }
    defaults.update(overrides)
    return GroundCombatantStats(**defaults)


class TestGroundCombatantStats:
    """Tests for combatant stat dataclass."""

    def test_player_defaults(self) -> None:
        stats = _make_player()
        assert stats.hp == 8
        assert stats.max_hp == 8
        assert stats.attack_mod == 0
        assert stats.defense_mod == 0
        assert stats.shield == 0
        assert stats.rerolls == 0

    def test_enemy_with_talk_difficulty(self) -> None:
        stats = _make_enemy(talk_difficulty=8)
        assert stats.talk_difficulty == 8
        assert not stats.is_automated

    def test_automated_enemy(self) -> None:
        stats = _make_enemy(is_automated=True, talk_difficulty=None)
        assert stats.is_automated

    def test_is_defeated(self) -> None:
        stats = _make_player(hp=0)
        assert stats.is_defeated

    def test_is_not_defeated(self) -> None:
        stats = _make_player(hp=1)
        assert not stats.is_defeated

    def test_take_damage_reduces_hp(self) -> None:
        stats = _make_player(hp=8, shield=0)
        stats.take_damage(3)
        assert stats.hp == 5

    def test_take_damage_does_not_go_below_zero(self) -> None:
        stats = _make_player(hp=2)
        stats.take_damage(5)
        assert stats.hp == 0

    def test_shield_absorbs_damage(self) -> None:
        stats = _make_player(hp=8, shield=4)
        stats.take_damage(3)
        assert stats.shield == 1
        assert stats.hp == 8, "Shield should have absorbed all damage"

    def test_shield_partially_absorbs(self) -> None:
        stats = _make_player(hp=8, shield=2)
        stats.take_damage(5)
        assert stats.shield == 0
        assert stats.hp == 5, "Remaining 3 damage should hit HP"

    def test_below_quarter_hp(self) -> None:
        stats = _make_player(hp=1, max_hp=8)
        assert stats.is_below_quarter_hp

    def test_not_below_quarter_hp(self) -> None:
        stats = _make_player(hp=2, max_hp=8)
        assert not stats.is_below_quarter_hp


class TestExchangeResolution:
    """Tests for the core exchange mechanic (1d6 + mod vs 1d6 + mod)."""

    def test_player_wins_exchange(self) -> None:
        """Player roll > enemy roll => enemy takes damage."""
        result = GroundCombatEngine.resolve_exchange(
            player_roll=5, player_mod=1,  # total 6
            enemy_roll=2, enemy_mod=1,    # total 3
        )
        assert result.player_damage == 0
        assert result.enemy_damage == 3, "Damage = difference (6-3)"
        assert not result.player_crit
        assert not result.enemy_crit

    def test_enemy_wins_exchange(self) -> None:
        """Enemy roll > player roll => player takes damage."""
        result = GroundCombatEngine.resolve_exchange(
            player_roll=1, player_mod=0,  # total 1
            enemy_roll=4, enemy_mod=2,    # total 6
        )
        assert result.player_damage == 5
        assert result.enemy_damage == 0

    def test_tie_exchange(self) -> None:
        """Tie => 1 damage to both."""
        result = GroundCombatEngine.resolve_exchange(
            player_roll=3, player_mod=1,  # total 4
            enemy_roll=2, enemy_mod=2,    # total 4
        )
        assert result.player_damage == 1
        assert result.enemy_damage == 1

    def test_minimum_damage_is_one(self) -> None:
        """Even a 1-point difference deals 1 damage."""
        result = GroundCombatEngine.resolve_exchange(
            player_roll=3, player_mod=0,  # total 3
            enemy_roll=2, enemy_mod=0,    # total 2
        )
        assert result.enemy_damage == 1

    def test_player_crit_on_natural_six(self) -> None:
        """Natural 6 = critical hit, double damage."""
        result = GroundCombatEngine.resolve_exchange(
            player_roll=6, player_mod=0,  # total 6, crit
            enemy_roll=3, enemy_mod=0,    # total 3
        )
        assert result.player_crit
        assert result.enemy_damage == 6, "Crit doubles the 3 difference"
        assert result.enemy_staggers

    def test_enemy_crit_on_natural_six(self) -> None:
        """Enemy natural 6 = crit, double damage to player."""
        result = GroundCombatEngine.resolve_exchange(
            player_roll=2, player_mod=0,  # total 2
            enemy_roll=6, enemy_mod=0,    # total 6
        )
        assert result.enemy_crit
        assert result.player_damage == 8, "Crit doubles the 4 difference"

    def test_both_crit(self) -> None:
        """Both roll 6 — tie with crits, 1 damage each doubled to 2."""
        result = GroundCombatEngine.resolve_exchange(
            player_roll=6, player_mod=0,
            enemy_roll=6, enemy_mod=0,
        )
        assert result.player_crit
        assert result.enemy_crit
        assert result.player_damage == 2, "Tie damage 1 doubled by enemy crit"
        assert result.enemy_damage == 2, "Tie damage 1 doubled by player crit"

    def test_crit_minimum_damage_doubled(self) -> None:
        """Crit with small difference still doubles."""
        result = GroundCombatEngine.resolve_exchange(
            player_roll=6, player_mod=0,  # total 6
            enemy_roll=5, enemy_mod=0,    # total 5
        )
        assert result.player_crit
        assert result.enemy_damage == 2, "1 damage doubled to 2"


class TestCombatStateConstruction:
    """Tests for GroundCombatState initialization."""

    def test_basic_construction(self) -> None:
        player = _make_player()
        enemies = [_make_enemy()]
        state = GroundCombatState(player=player, enemies=enemies)
        assert state.round_number == 0
        assert state.outcome == CombatOutcome.IN_PROGRESS
        assert state.target_index == 0

    def test_multiple_enemies(self) -> None:
        player = _make_player()
        enemies = [_make_enemy(name="A"), _make_enemy(name="B")]
        state = GroundCombatState(player=player, enemies=enemies)
        assert len(state.enemies) == 2

    def test_ambush_bonus(self) -> None:
        player = _make_player()
        state = GroundCombatState(
            player=player, enemies=[_make_enemy()], is_ambush=True
        )
        assert state.is_ambush

    def test_disadvantaged_start(self) -> None:
        player = _make_player()
        state = GroundCombatState(
            player=player, enemies=[_make_enemy()], is_disadvantaged=True
        )
        assert state.is_disadvantaged


class TestOutnumberedPenalty:
    """Tests for the outnumbered penalty."""

    def test_one_enemy_no_penalty(self) -> None:
        state = GroundCombatState(
            player=_make_player(), enemies=[_make_enemy()]
        )
        assert state.outnumbered_penalty == 0

    def test_two_enemies_penalty_one(self) -> None:
        state = GroundCombatState(
            player=_make_player(),
            enemies=[_make_enemy(name="A"), _make_enemy(name="B")],
        )
        assert state.outnumbered_penalty == 1

    def test_three_enemies_penalty_two(self) -> None:
        state = GroundCombatState(
            player=_make_player(),
            enemies=[_make_enemy(name="A"), _make_enemy(name="B"), _make_enemy(name="C")],
        )
        assert state.outnumbered_penalty == 2

    def test_defeated_enemies_not_counted(self) -> None:
        enemies = [_make_enemy(name="A"), _make_enemy(name="B", hp=0)]
        state = GroundCombatState(player=_make_player(), enemies=enemies)
        assert state.outnumbered_penalty == 0, "Defeated enemy shouldn't count"


class TestMomentumCombo:
    """Tests for the momentum combo mechanic."""

    def test_no_momentum_initially(self) -> None:
        state = GroundCombatState(
            player=_make_player(), enemies=[_make_enemy()]
        )
        assert state.consecutive_wins == 0
        assert state.momentum_bonus == 0

    def test_two_wins_no_bonus_yet(self) -> None:
        state = GroundCombatState(
            player=_make_player(), enemies=[_make_enemy()]
        )
        state.consecutive_wins = 2
        assert state.momentum_bonus == 2, "3rd exchange gets +2 bonus"

    def test_loss_resets_momentum(self) -> None:
        state = GroundCombatState(
            player=_make_player(), enemies=[_make_enemy()]
        )
        state.consecutive_wins = 2
        state.record_exchange_outcome(player_won=False)
        assert state.consecutive_wins == 0


class TestFightAction:
    """Tests for the fight action with deterministic rolls."""

    def test_fight_damages_target_enemy(self) -> None:
        player = _make_player(attack_mod=2)
        enemy = _make_enemy(hp=4, defense_mod=0)
        state = GroundCombatState(player=player, enemies=[enemy])

        result = state.execute_fight(player_roll=5, enemy_roll=2)
        # Player total: 5+2=7, enemy total: 2+0=2, diff=5
        assert enemy.hp < 4, "Enemy should have taken damage"

    def test_fight_player_takes_damage(self) -> None:
        player = _make_player(hp=8, attack_mod=0)
        enemy = _make_enemy(attack_mod=3)
        state = GroundCombatState(player=player, enemies=[enemy])

        result = state.execute_fight(player_roll=1, enemy_roll=5)
        assert player.hp < 8, "Player should have taken damage"

    def test_fight_outnumbered_penalty_applied(self) -> None:
        player = _make_player(attack_mod=0, defense_mod=0)
        enemies = [_make_enemy(name="A", defense_mod=0), _make_enemy(name="B")]
        state = GroundCombatState(player=player, enemies=enemies)

        # With outnumbered penalty of -1, player effective attack = -1
        result = state.execute_fight(player_roll=4, enemy_roll=4)
        # Player total: 4 + 0 - 1 = 3, enemy total: 4 + 0 = 4
        # Enemy wins: player takes 1 damage
        assert result.player_damage > 0, "Outnumbered penalty should hurt player"

    def test_fight_ambush_first_exchange(self) -> None:
        player = _make_player(attack_mod=0)
        enemy = _make_enemy(defense_mod=0)
        state = GroundCombatState(
            player=player, enemies=[enemy], is_ambush=True
        )

        result = state.execute_fight(player_roll=3, enemy_roll=6)
        # Ambush: +3 attack, enemy doesn't get defense
        # Player total: 3 + 0 + 3 = 6, enemy total: 0 (no defense roll)
        assert result.enemy_damage > 0, "Ambush should hit enemy"
        assert result.player_damage == 0, "Enemy can't defend during ambush"

    def test_ambush_only_first_exchange(self) -> None:
        player = _make_player()
        enemy = _make_enemy(hp=20, defense_mod=0)
        state = GroundCombatState(
            player=player, enemies=[enemy], is_ambush=True
        )

        # First exchange — ambush applies
        state.execute_fight(player_roll=3, enemy_roll=3)
        # Second exchange — no ambush
        result = state.execute_fight(player_roll=3, enemy_roll=5)
        assert result.player_damage > 0, "No ambush protection on second exchange"

    def test_disadvantaged_first_exchange(self) -> None:
        player = _make_player(attack_mod=0, defense_mod=0)
        enemy = _make_enemy(attack_mod=0, defense_mod=0)
        state = GroundCombatState(
            player=player, enemies=[enemy], is_disadvantaged=True
        )

        result = state.execute_fight(player_roll=4, enemy_roll=4)
        # Disadvantaged: -2 to player's first exchange
        # Player total: 4 + 0 - 2 = 2, enemy total: 4 + 0 = 4
        assert result.player_damage == 2, "Disadvantaged penalty should apply"

    def test_momentum_bonus_applied(self) -> None:
        player = _make_player(attack_mod=0)
        enemy = _make_enemy(hp=20, defense_mod=0)
        state = GroundCombatState(player=player, enemies=[enemy])
        state.consecutive_wins = 2  # Next exchange gets +2

        result = state.execute_fight(player_roll=3, enemy_roll=3)
        # Player total: 3 + 0 + 2 = 5, enemy total: 3 + 0 = 3
        assert result.enemy_damage == 2, "Momentum should add +2 attack"

    def test_enemy_staggers_on_crit(self) -> None:
        player = _make_player()
        enemy = _make_enemy(hp=20, defense_mod=0)
        state = GroundCombatState(player=player, enemies=[enemy])

        result = state.execute_fight(player_roll=6, enemy_roll=2)
        assert result.enemy_staggers, "Crit should stagger enemy"

    def test_all_enemies_defeated_ends_combat(self) -> None:
        player = _make_player(attack_mod=5)
        enemy = _make_enemy(hp=1, defense_mod=0)
        state = GroundCombatState(player=player, enemies=[enemy])

        state.execute_fight(player_roll=6, enemy_roll=1)
        assert enemy.is_defeated
        assert state.outcome == CombatOutcome.VICTORY

    def test_player_defeated_ends_combat(self) -> None:
        player = _make_player(hp=1, attack_mod=0, defense_mod=0)
        enemy = _make_enemy(attack_mod=5)
        state = GroundCombatState(player=player, enemies=[enemy])

        state.execute_fight(player_roll=1, enemy_roll=6)
        assert player.is_defeated
        assert state.outcome == CombatOutcome.DEFEAT

    def test_target_cycling(self) -> None:
        enemies = [_make_enemy(name="A", hp=10), _make_enemy(name="B", hp=10)]
        state = GroundCombatState(player=_make_player(), enemies=enemies)
        assert state.target_index == 0
        state.cycle_target()
        assert state.target_index == 1
        state.cycle_target()
        assert state.target_index == 0, "Should wrap around"

    def test_target_skips_defeated(self) -> None:
        enemies = [
            _make_enemy(name="A", hp=0),
            _make_enemy(name="B", hp=10),
        ]
        state = GroundCombatState(player=_make_player(), enemies=enemies)
        state.target_index = 0
        state.cycle_target()
        assert state.target_index == 1, "Should skip defeated enemy"


class TestRetreatAction:
    """Tests for the retreat mechanic."""

    def test_successful_retreat(self) -> None:
        state = GroundCombatState(
            player=_make_player(),
            enemies=[_make_enemy()],
            can_retreat=True,
        )
        # Retreat roll: 1d6 + retreat_mod vs base 4 + 1 per enemy = 5
        success = state.attempt_retreat(roll=6, retreat_mod=0)
        # 6 + 0 = 6 >= 5 => success
        assert success
        assert state.outcome == CombatOutcome.RETREATED

    def test_failed_retreat(self) -> None:
        player = _make_player(hp=8)
        enemy = _make_enemy(attack_mod=2)
        state = GroundCombatState(
            player=player, enemies=[enemy], can_retreat=True
        )
        success = state.attempt_retreat(roll=1, retreat_mod=0)
        # 1 + 0 = 1 < 5 => fail
        assert not success
        assert state.outcome == CombatOutcome.IN_PROGRESS

    def test_failed_retreat_enemy_free_attack(self) -> None:
        player = _make_player(hp=8, defense_mod=0)
        enemy = _make_enemy(attack_mod=2)
        state = GroundCombatState(
            player=player, enemies=[enemy], can_retreat=True
        )
        state.attempt_retreat(roll=1, retreat_mod=0, free_attack_rolls=[5])
        assert player.hp < 8, "Failed retreat should incur free attack"

    def test_retreat_impossible_when_cornered(self) -> None:
        state = GroundCombatState(
            player=_make_player(),
            enemies=[_make_enemy()],
            can_retreat=False,
        )
        success = state.attempt_retreat(roll=6, retreat_mod=5)
        assert not success, "Cannot retreat when cornered"

    def test_retreat_difficulty_scales_with_enemies(self) -> None:
        enemies = [_make_enemy(name="A"), _make_enemy(name="B"), _make_enemy(name="C")]
        state = GroundCombatState(
            player=_make_player(), enemies=enemies, can_retreat=True
        )
        # Difficulty = 4 + 3 enemies = 7
        success = state.attempt_retreat(roll=6, retreat_mod=0)
        # 6 < 7 => fail
        assert not success


class TestTalkAction:
    """Tests for the talk/negotiate mechanic."""

    def test_successful_talk(self) -> None:
        enemy = _make_enemy(talk_difficulty=4)
        state = GroundCombatState(
            player=_make_player(), enemies=[enemy]
        )
        success = state.attempt_talk(
            roll=5, social_mod=0, skill_type=SocialSkillType.PERSUASION
        )
        # 5 + 0 = 5 >= 4 => success
        assert success
        assert state.outcome == CombatOutcome.TALKED

    def test_failed_talk(self) -> None:
        player = _make_player(hp=8)
        enemy = _make_enemy(talk_difficulty=8, attack_mod=2)
        state = GroundCombatState(player=player, enemies=[enemy])
        success = state.attempt_talk(
            roll=3, social_mod=0, skill_type=SocialSkillType.PERSUASION
        )
        assert not success
        assert state.outcome == CombatOutcome.IN_PROGRESS

    def test_failed_talk_enemy_free_attack(self) -> None:
        player = _make_player(hp=8, defense_mod=0)
        enemy = _make_enemy(talk_difficulty=8, attack_mod=2)
        state = GroundCombatState(player=player, enemies=[enemy])
        state.attempt_talk(
            roll=1, social_mod=0,
            skill_type=SocialSkillType.PERSUASION,
            free_attack_rolls=[5],
        )
        assert player.hp < 8, "Failed talk costs a free attack"

    def test_cannot_talk_to_automated(self) -> None:
        enemy = _make_enemy(is_automated=True, talk_difficulty=None)
        state = GroundCombatState(
            player=_make_player(), enemies=[enemy]
        )
        success = state.attempt_talk(
            roll=6, social_mod=5, skill_type=SocialSkillType.PERSUASION
        )
        assert not success, "Cannot talk to automated enemies"

    def test_same_skill_cannot_be_used_twice(self) -> None:
        enemy = _make_enemy(talk_difficulty=10)
        state = GroundCombatState(
            player=_make_player(), enemies=[enemy]
        )
        # First attempt fails
        state.attempt_talk(
            roll=1, social_mod=0, skill_type=SocialSkillType.PERSUASION
        )
        assert not state.can_use_social_skill(SocialSkillType.PERSUASION)
        assert state.can_use_social_skill(SocialSkillType.INTIMIDATION)

    def test_multiple_enemies_uses_highest_talk_difficulty(self) -> None:
        enemies = [
            _make_enemy(name="A", talk_difficulty=4),
            _make_enemy(name="B", talk_difficulty=8),
        ]
        state = GroundCombatState(
            player=_make_player(), enemies=enemies
        )
        # Must beat highest difficulty (8)
        success = state.attempt_talk(
            roll=5, social_mod=2, skill_type=SocialSkillType.PERSUASION
        )
        # 5 + 2 = 7 < 8 => fail
        assert not success

    def test_intimidation_bonus_after_kill(self) -> None:
        enemies = [
            _make_enemy(name="A", hp=0),  # Already defeated
            _make_enemy(name="B", talk_difficulty=6),
        ]
        state = GroundCombatState(
            player=_make_player(), enemies=enemies
        )
        state.enemies_defeated_count = 1
        bonus = state.get_intimidation_bonus()
        assert bonus == 2, "+2 intimidation after defeating an enemy"

    def test_no_intimidation_bonus_without_kills(self) -> None:
        state = GroundCombatState(
            player=_make_player(), enemies=[_make_enemy()]
        )
        assert state.get_intimidation_bonus() == 0


class TestLastStandMechanic:
    """Tests for the Last Stand skill bonus."""

    def test_last_stand_bonus_when_low_hp(self) -> None:
        player = _make_player(hp=1, max_hp=8)
        state = GroundCombatState(
            player=player, enemies=[_make_enemy()], has_last_stand=True
        )
        assert state.last_stand_bonus == 3

    def test_no_last_stand_above_quarter(self) -> None:
        player = _make_player(hp=5, max_hp=8)
        state = GroundCombatState(
            player=player, enemies=[_make_enemy()], has_last_stand=True
        )
        assert state.last_stand_bonus == 0

    def test_no_last_stand_without_skill(self) -> None:
        player = _make_player(hp=1, max_hp=8)
        state = GroundCombatState(
            player=player, enemies=[_make_enemy()], has_last_stand=False
        )
        assert state.last_stand_bonus == 0


class TestIntimidatingPresence:
    """Tests for the Intimidating Presence skill."""

    def test_first_exchange_debuff(self) -> None:
        state = GroundCombatState(
            player=_make_player(),
            enemies=[_make_enemy(defense_mod=0)],
            has_intimidating_presence=True,
        )
        assert state.intimidating_presence_debuff == 2

    def test_debuff_only_first_exchange(self) -> None:
        enemy = _make_enemy(hp=20, defense_mod=0)
        state = GroundCombatState(
            player=_make_player(),
            enemies=[enemy],
            has_intimidating_presence=True,
        )
        state.execute_fight(player_roll=3, enemy_roll=3)
        # After first exchange, debuff gone
        assert state.intimidating_presence_debuff == 0


class TestCombatOutcome:
    """Tests for combat outcome determination."""

    def test_in_progress_initially(self) -> None:
        state = GroundCombatState(
            player=_make_player(), enemies=[_make_enemy()]
        )
        assert state.outcome == CombatOutcome.IN_PROGRESS

    def test_victory_all_defeated(self) -> None:
        state = GroundCombatState(
            player=_make_player(), enemies=[_make_enemy(hp=0)]
        )
        state._check_outcome()
        assert state.outcome == CombatOutcome.VICTORY

    def test_defeat_player_dead(self) -> None:
        state = GroundCombatState(
            player=_make_player(hp=0), enemies=[_make_enemy()]
        )
        state._check_outcome()
        assert state.outcome == CombatOutcome.DEFEAT


class TestSerialization:
    """Tests for to_dict / from_dict round-trip."""

    def test_combatant_round_trip(self) -> None:
        stats = _make_player(hp=5, shield=2, rerolls=1)
        data = stats.to_dict()
        restored = GroundCombatantStats.from_dict(data)
        assert restored.hp == 5
        assert restored.shield == 2
        assert restored.rerolls == 1

    def test_combat_state_round_trip(self) -> None:
        player = _make_player(hp=6)
        enemies = [_make_enemy(hp=3, name="Guard")]
        state = GroundCombatState(
            player=player, enemies=enemies,
            is_ambush=True, is_disadvantaged=False,
            can_retreat=True, has_last_stand=True,
        )
        state.consecutive_wins = 2
        state.round_number = 3
        state.used_social_skills.add(SocialSkillType.PERSUASION)

        data = state.to_dict()
        restored = GroundCombatState.from_dict(data)
        assert restored.player.hp == 6
        assert len(restored.enemies) == 1
        assert restored.enemies[0].name == "Guard"
        assert restored.is_ambush
        assert restored.can_retreat
        assert restored.has_last_stand
        assert restored.consecutive_wins == 2
        assert restored.round_number == 3
        assert SocialSkillType.PERSUASION in restored.used_social_skills


class TestRerolls:
    """Tests for the re-roll mechanic."""

    def test_player_has_rerolls(self) -> None:
        player = _make_player(rerolls=1)
        state = GroundCombatState(player=player, enemies=[_make_enemy()])
        assert state.can_reroll

    def test_no_rerolls_available(self) -> None:
        player = _make_player(rerolls=0)
        state = GroundCombatState(player=player, enemies=[_make_enemy()])
        assert not state.can_reroll

    def test_use_reroll_decrements(self) -> None:
        player = _make_player(rerolls=2)
        state = GroundCombatState(player=player, enemies=[_make_enemy()])
        state.use_reroll()
        assert player.rerolls == 1


class TestEnemyTemplates:
    """Tests for enemy type templates."""

    def test_all_templates_defined(self) -> None:
        expected = {
            "guild_security", "union_worker", "pirate_thug",
            "collective_drone", "alliance_scrapper", "elite_guard",
            "station_sentry", "crimson_enforcer",
        }
        assert set(GROUND_ENEMY_TEMPLATES.keys()) == expected

    def test_make_guild_security(self) -> None:
        stats = make_enemy_from_template("guild_security")
        assert stats.name == "Guild Security"
        assert stats.hp == 4
        assert stats.attack_mod == 2
        assert stats.defense_mod == 2
        assert stats.talk_difficulty == 6
        assert not stats.is_automated

    def test_make_collective_drone_automated(self) -> None:
        stats = make_enemy_from_template("collective_drone")
        assert stats.is_automated
        assert stats.talk_difficulty is None

    def test_make_elite_guard(self) -> None:
        stats = make_enemy_from_template("elite_guard")
        assert stats.hp == 6
        assert stats.attack_mod == 3
        assert stats.defense_mod == 3
        assert stats.talk_difficulty == 9

    def test_unknown_template_raises(self) -> None:
        with pytest.raises(KeyError):
            make_enemy_from_template("nonexistent")


class TestBuildPlayerStats:
    """Tests for the player combat stats factory."""

    def test_base_stats_no_bonuses(self) -> None:
        stats = build_player_ground_combat_stats()
        assert stats.hp == 10
        assert stats.attack_mod == 0
        assert stats.defense_mod == 0
        assert stats.rerolls == 0

    def test_attribute_bonuses(self) -> None:
        attrs = AttributeSheet(values={"acu": 4, "res": 4, "com": 1, "ing": 1, "syn": 1})
        stats = build_player_ground_combat_stats(attributes=attrs)
        # ACU 4: +2 attack
        assert stats.attack_mod == 2
        # RES 4: +2 defense, +2 HP
        assert stats.defense_mod == 2
        assert stats.hp == 12

    def test_scrapper_skill_bonus(self) -> None:
        prog = PlayerProgression()
        prog.skills["scrapper"].current_level = 1
        stats = build_player_ground_combat_stats(progression=prog)
        assert stats.attack_mod == 1

    def test_tough_hide_skill_bonus(self) -> None:
        prog = PlayerProgression()
        prog.skills["tough_hide"].current_level = 1
        stats = build_player_ground_combat_stats(progression=prog)
        assert stats.hp == 12  # 10 base + 2

    def test_quick_reflexes_reroll(self) -> None:
        prog = PlayerProgression()
        prog.skills["scrapper"].current_level = 1
        prog.skills["quick_reflexes"].current_level = 1
        stats = build_player_ground_combat_stats(progression=prog)
        assert stats.rerolls == 1

    def test_veteran_bonus(self) -> None:
        prog = PlayerProgression()
        # Unlock prereq chain
        prog.skills["scrapper"].current_level = 1
        prog.skills["quick_reflexes"].current_level = 1
        prog.skills["intimidating_presence"].current_level = 1
        prog.skills["tough_hide"].current_level = 1
        prog.skills["last_stand"].current_level = 1
        prog.skills["veteran"].current_level = 1
        stats = build_player_ground_combat_stats(progression=prog)
        # Veteran: +1 reroll, +1 HP on top of quick reflexes (+1 reroll) and tough hide (+2 HP)
        assert stats.rerolls == 2
        assert stats.hp == 13  # 10 + 2 (tough hide) + 1 (veteran)

    def test_full_integration(self) -> None:
        """All bonuses stacked together."""
        attrs = AttributeSheet(values={"acu": 4, "res": 4, "com": 1, "ing": 1, "syn": 1})
        prog = PlayerProgression()
        prog.skills["scrapper"].current_level = 1
        prog.skills["tough_hide"].current_level = 1
        stats = build_player_ground_combat_stats(attributes=attrs, progression=prog)
        # HP: 10 base + 2 (RES) + 2 (tough hide) = 14
        assert stats.hp == 14
        # Attack: 0 + 2 (ACU) + 1 (scrapper) = 3
        assert stats.attack_mod == 3
        # Defense: 0 + 2 (RES) = 2
        assert stats.defense_mod == 2


class TestGroundSkillTree:
    """Tests for ground combat skill nodes in the progression system."""

    def test_ground_tree_type_exists(self) -> None:
        assert SkillTreeType.GROUND.value == "ground"

    def test_ground_skills_in_default_progression(self) -> None:
        prog = PlayerProgression()
        ground_skills = prog.get_skill_tree(SkillTreeType.GROUND)
        assert len(ground_skills) == 6

    def test_ground_skill_ids(self) -> None:
        prog = PlayerProgression()
        ground_ids = {s.id for s in prog.get_skill_tree(SkillTreeType.GROUND)}
        expected = {
            "scrapper", "tough_hide", "quick_reflexes",
            "intimidating_presence", "last_stand", "veteran",
        }
        assert ground_ids == expected

    def test_scrapper_no_prerequisite(self) -> None:
        prog = PlayerProgression()
        assert prog.skills["scrapper"].prerequisite_id is None

    def test_tough_hide_no_prerequisite(self) -> None:
        prog = PlayerProgression()
        assert prog.skills["tough_hide"].prerequisite_id is None

    def test_quick_reflexes_requires_scrapper(self) -> None:
        prog = PlayerProgression()
        assert prog.skills["quick_reflexes"].prerequisite_id == "scrapper"

    def test_veteran_requires_intimidating_presence(self) -> None:
        prog = PlayerProgression()
        assert prog.skills["veteran"].prerequisite_id == "intimidating_presence"

    def test_can_level_scrapper_with_points(self) -> None:
        prog = PlayerProgression()
        prog.skill_points = 1
        success, msg = prog.level_up_skill("scrapper")
        assert success, msg
        assert prog.skills["scrapper"].current_level == 1

    def test_cannot_level_quick_reflexes_without_scrapper(self) -> None:
        prog = PlayerProgression()
        prog.skill_points = 1
        success, _ = prog.level_up_skill("quick_reflexes")
        assert not success
