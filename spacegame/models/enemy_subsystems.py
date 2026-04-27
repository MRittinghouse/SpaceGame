"""Tag-based subsystem targeting (Combat overhaul §11.2).

Each enemy declares 1-4 targetable subsystems drawn from a canonical
6-tag palette. Destroying a subsystem applies a distinct mechanical
effect — damage reduction, shield collapse, tempo skip, etc. — so
players who choose to focus fire on subsystems unlock strategic depth
beyond "chip hull until dead."

Key decisions (see spec §11.2):
  - 6 canonical tags; no per-enemy custom subsystems
  - Every subsystem has a distinct, readable effect
  - Subsystem HP = 25% of enemy hull per subsystem (moderate commitment)
  - Subsystems are **opt-in**: no focus selected = normal hull damage
    only. Choose to engage the tactical layer or play the classic way.

The runtime flow:
  1. Player cycles subsystem focus on current target (combat_view hook)
  2. Attacks against that enemy route damage to the focused subsystem
     AND full hull damage (not split — hitting the weapon also hits the
     ship around it)
  3. When a subsystem's HP hits 0, :func:`apply_subsystem_destruction`
     mutates the enemy's runtime state per the subsystem's effect
  4. Combat engine consults the mutated state each turn (evasion, damage
     output, accuracy, energy regen, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SubsystemTag(Enum):
    """Canonical targetable subsystems (spec §11.2)."""

    WEAPON_ARRAY = "weapon_array"
    SHIELD_GENERATOR = "shield_generator"
    ENGINE = "engine"
    SENSOR_ARRAY = "sensor_array"
    COCKPIT = "cockpit"
    REACTOR = "reactor"


# Cockpit is a "risk target" — lower HP than other subsystems but
# destroying it kills the enemy outright. Multiplier applied to baseline
# (0.25 * enemy.hull) when initializing subsystem HP.
_COCKPIT_HP_MULTIPLIER = 0.40  # Cockpit HP = 10% of enemy hull

# Baseline subsystem HP as fraction of enemy max hull. A subsystem
# absorbs this much damage before destruction; tuning lever for how
# committing the tactical choice is.
_BASELINE_HP_FRACTION = 0.25


def subsystem_max_hp(tag: str, enemy_max_hull: int) -> int:
    """Return starting HP for a subsystem on an enemy with ``enemy_max_hull``.

    Unknown tags default to the baseline fraction.
    """
    base = max(1, int(enemy_max_hull * _BASELINE_HP_FRACTION))
    if tag == SubsystemTag.COCKPIT.value:
        return max(1, int(base * _COCKPIT_HP_MULTIPLIER))
    return base


# ---------------------------------------------------------------------------
# Effect descriptors — what happens when a subsystem reaches 0 HP
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubsystemEffect:
    """Descriptor for the mechanical effect of destroying a subsystem.

    Effects are applied by :func:`apply_subsystem_destruction` via state
    mutations on the target :class:`EnemyShip`. Keeping the descriptors
    declarative (numbers, not functions) lets tests audit the palette
    without invoking combat engine paths.
    """

    tag: str
    log_text: str  # Combat log line when destroyed
    damage_multiplier: float = 1.0  # Multiplier on enemy's outgoing damage
    accuracy_delta: int = 0  # Flat delta on enemy accuracy
    disable_shield_regen: bool = False
    strip_current_shields: bool = False
    evasion_override: int | None = None  # None = unchanged; 0 = wipe
    disable_flee: bool = False
    disable_energy_regen: bool = False
    trigger_tempo_skip: bool = False  # Enemy skips next turn
    instant_kill: bool = False  # Cockpit — sets hull to 0


SUBSYSTEM_PALETTE: dict[str, SubsystemEffect] = {
    SubsystemTag.WEAPON_ARRAY.value: SubsystemEffect(
        tag=SubsystemTag.WEAPON_ARRAY.value,
        log_text="Weapon array destroyed — their damage drops sharply",
        damage_multiplier=0.60,  # 40% reduction
    ),
    SubsystemTag.SHIELD_GENERATOR.value: SubsystemEffect(
        tag=SubsystemTag.SHIELD_GENERATOR.value,
        log_text="Shield generator destroyed — barrier collapses",
        disable_shield_regen=True,
        strip_current_shields=True,
    ),
    SubsystemTag.ENGINE.value: SubsystemEffect(
        tag=SubsystemTag.ENGINE.value,
        log_text="Engines crippled — evasion lost, fleeing no longer an option",
        evasion_override=0,
        disable_flee=True,
        trigger_tempo_skip=True,
    ),
    SubsystemTag.SENSOR_ARRAY.value: SubsystemEffect(
        tag=SubsystemTag.SENSOR_ARRAY.value,
        log_text="Sensor array destroyed — their targeting falters",
        accuracy_delta=-30,
    ),
    SubsystemTag.COCKPIT.value: SubsystemEffect(
        tag=SubsystemTag.COCKPIT.value,
        log_text="Cockpit struck — ship goes dark",
        instant_kill=True,
    ),
    SubsystemTag.REACTOR.value: SubsystemEffect(
        tag=SubsystemTag.REACTOR.value,
        log_text="Reactor destroyed — their systems starve for power",
        disable_energy_regen=True,
    ),
}


CANONICAL_TAGS: tuple[str, ...] = tuple(t.value for t in SubsystemTag)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def is_valid_tag(tag: str) -> bool:
    """True when ``tag`` is one of the canonical subsystem palette entries."""
    return tag in SUBSYSTEM_PALETTE


def get_effect(tag: str) -> SubsystemEffect | None:
    """Return the effect descriptor for a tag, or ``None`` if unknown."""
    return SUBSYSTEM_PALETTE.get(tag)


# ---------------------------------------------------------------------------
# Damage routing + destruction
# ---------------------------------------------------------------------------


def apply_subsystem_damage(
    enemy: Any,  # EnemyShip — Any-typed to avoid circular import
    damage: int,
    tag: str,
) -> SubsystemEffect | None:
    """Chip ``damage`` HP off the given subsystem on ``enemy``.

    Returns the :class:`SubsystemEffect` descriptor when this hit
    destroys the subsystem, or ``None`` otherwise. Callers apply the
    effect via :func:`apply_subsystem_destruction`.

    Safe no-op when the subsystem isn't targetable on this enemy,
    already destroyed, or the tag is unknown.
    """
    if damage <= 0:
        return None
    if tag in enemy.subsystems_destroyed:
        return None
    if tag not in enemy.subsystem_hp:
        return None
    remaining = enemy.subsystem_hp[tag] - damage
    if remaining > 0:
        enemy.subsystem_hp[tag] = remaining
        return None
    # Destruction.
    enemy.subsystem_hp[tag] = 0
    enemy.subsystems_destroyed.add(tag)
    return SUBSYSTEM_PALETTE.get(tag)


def apply_subsystem_destruction(
    enemy: Any,  # EnemyShip
    effect: SubsystemEffect,
) -> list[str]:
    """Mutate ``enemy`` to reflect a subsystem's destruction effect.

    Returns the list of log messages generated (typically a single
    entry — the effect's log_text). Idempotent with respect to already-
    applied state, so safe to call multiple times on the same effect.
    """
    messages: list[str] = [effect.log_text]

    if effect.strip_current_shields:
        enemy.current_shields = 0

    if effect.evasion_override is not None:
        # Effective evasion is computed from subsystems_destroyed now,
        # so no explicit write needed — the override_flag path is
        # already live via ``EnemyShip.effective_evasion``.
        pass

    if effect.trigger_tempo_skip:
        enemy.engines_just_destroyed = True

    if effect.instant_kill:
        enemy.current_hull = 0
        enemy.current_shields = 0

    # Damage multiplier / accuracy delta / disable_flee / disable_shield_regen
    # / disable_energy_regen are all read at decision time via
    # ``EnemyShip.damage_multiplier``, ``.effective_accuracy``,
    # ``.can_flee``, ``.can_regen_shields``, ``.can_regen_energy`` — no
    # state mutation needed here.

    return messages


def consume_engine_tempo_skip(enemy: Any) -> bool:  # EnemyShip
    """Return True and clear the flag if engines were just destroyed.

    Mirrors the ``_frozen`` check pattern in combat_engine's enemy
    turn loop. Exactly one tempo skip per engine-destruction event.
    """
    if enemy.engines_just_destroyed:
        enemy.engines_just_destroyed = False
        return True
    return False
