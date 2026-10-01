"""Combat engine goldens: seeded fights driven by a fixed policy (SP3 spec 6.3).

A fight starts from a PlayerCombatState built on the ship-type path (spec R1 moves the
module-hit path to SP4). Each round the policy queues every affordable equipment move in
list order at the first living target, then enemies act, then the round ends. The setup
records the full player state, the enemy template ids, and the payout player the victory
or negotiated reward runs on, so the Godot adapter rebuilds the same fight and the same
payout.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spacegame.data_loader import get_data_loader
from spacegame.models.action_queue import ActionQueue
from spacegame.models.combat import (
    CombatEncounter,
    CombatLogEntry,
    CombatMove,
    CombatResult,
    CombatState,
    EnemyShip,
    PlayerCombatState,
    build_player_combat_state,
)
from spacegame.models.combat_engine import CombatEngine
from spacegame.models.crew import CrewRoster
from spacegame.models.dual_tech import DUAL_TECH_PALETTE
from spacegame.models.player import Player
from spacegame.models.social import (
    MAX_SOCIAL_LEVEL,
    SOCIAL_SKILL_DEFINITIONS,
    SOCIAL_XP_THRESHOLDS,
    SocialManager,
)
from spacegame.models.upgrades import ShipUpgradeManager
from spacegame.sim_rng import stable_seed
from tools.parity.driver import Case
from tools.parity.snapshots import fresh_player, player_snapshot

MAX_ROUNDS = 40
BOSS_HULL = 5000
LOADOUTS: tuple[tuple[str, ...], ...] = (
    ("slug_thrower", "armor_plating"),
    ("plasma_caster", "basic_shield_gen"),
    ("ion_disruptor_weapon", "point_defense"),
    ("frost_projector", "emergency_repair"),
    ("voltaic_pulse", "reactive_armor"),
)
# Bosses multiply hull (and some multiply shields too), and the single-weapon
# loadouts above cannot bring every boss through its last phase within
# MAX_ROUNDS: with one 13-14 damage weapon per round, union_behemoth (hull
# 800 + shields 180) is still short of its 0.5 phase threshold at round 40.
# Boss fights instead install every weapon and defense upgrade from the five
# loadouts above (all five elements at once), and get a taller round budget.
# Measured against these seeds, the slowest boss (union_behemoth) reaches its
# last phase at round 43; BOSS_MAX_ROUNDS leaves headroom above that.
BOSS_LOADOUT: tuple[str, ...] = tuple(dict.fromkeys(item for pair in LOADOUTS for item in pair))
BOSS_MAX_ROUNDS = 50
# hp_threshold complications trigger only while combat runs, and the fixed
# policy's shuttle-vs-two-pirate_raiders fight ends (by killing both raiders)
# before the player's hull drops to 30% of a 400 hull. 112 is the boundary at
# these seeds: the largest hull for which the player's hull ratio still
# reaches <= 0.3 before the fight ends (113 falls just short, at 34/113).
MORALE_SHIFT_HULL = 112
COMPANIONS = ("elena_reeves", "marcus_jin", "dr_priya_osei", "tomas_drifter")
# A SocialManager.load_state() profile with persuasion maxed and every other skill at its
# default (level 1, xp 0). Only "persuasion" needs an entry: load_state only overwrites the
# skills a profile names, leaving the rest at the defaults it just reset to.
NEGOTIATE_PROFILE: dict[str, object] = {
    "skills": {
        "persuasion": {
            "id": "persuasion",
            "name": SOCIAL_SKILL_DEFINITIONS["persuasion"],
            "level": MAX_SOCIAL_LEVEL,
            "xp": SOCIAL_XP_THRESHOLDS[MAX_SOCIAL_LEVEL - 1],
        }
    },
    "disposition": {},
}


@dataclass
class Fight:
    """A running fight and the setup that rebuilds it."""

    engine: CombatEngine
    state: CombatState
    setup: dict[str, object]
    log_seen: int = 0


def _effects(active: list[tuple[Any, int]]) -> list[dict[str, object]]:
    return [{"effect": effect.to_dict(), "remaining": remaining} for effect, remaining in active]


def _move(move: CombatMove) -> dict[str, object]:
    # CombatMove.to_dict() omits "element" for the default (kinetic) to keep
    # authored JSON minimal. The golden setup needs every move's element
    # explicit so the port (and the coverage test) can see kinetic moves too.
    data = move.to_dict()
    data["element"] = move.element.value
    return data


def _player_state(p: PlayerCombatState) -> dict[str, object]:
    return {
        "hull": p.hull,
        "max_hull": p.max_hull,
        "shields": p.shields,
        "max_shields": p.max_shields,
        "energy": p.energy,
        "max_energy": p.max_energy,
        "energy_regen": p.energy_regen,
        "speed": p.speed,
        "evasion": p.evasion,
        "accuracy": p.accuracy,
        "cooldowns": dict(p.cooldowns),
        "active_effects": _effects(p.active_effects),
        "flee_bonus": p.flee_bonus,
        "armor": p.armor,
        "shield_regen": p.shield_regen,
        "defensive_identity": p.defensive_identity,
        "counterstrike_stacks": p.counterstrike_stacks,
        "shield_break_vulnerable": p.shield_break_vulnerable,
        "evasion_decay": p.evasion_decay,
        "ship_class_category": p.ship_class_category,
        "momentum": p.momentum.to_dict() if p.momentum else None,
        "critical_hp_surge_fired": p.critical_hp_surge_fired,
        "fire_at_will_active": p.fire_at_will_active,
        "crew_sync_used": p.crew_sync_used,
        "total_commitment_hits_remaining": p.total_commitment_hits_remaining,
        "total_commitment_armor_gained": p.total_commitment_armor_gained,
        "daring_gambit_turns": p.daring_gambit_turns,
        "armor_pierce_active": p.armor_pierce_active,
        "equipment_moves": [_move(m) for m in p.equipment_moves],
        "crew_moves": [_move(m) for m in p.crew_moves],
        "dual_tech_moves": [_move(m) for m in p.dual_tech_moves],
        "dialogue_flags": dict(sorted(p.dialogue_flags.items())),
    }


def _enemy_state(e: EnemyShip) -> dict[str, object]:
    return {
        "template_id": e.template.id,
        "current_hull": e.current_hull,
        "current_shields": e.current_shields,
        "current_energy": e.current_energy,
        "active_effects": _effects(e.active_effects),
        "cooldowns": dict(e.cooldowns),
        "is_fled": e.is_fled,
        "telegraphed_move": e.telegraphed_move.id if e.telegraphed_move else None,
        "current_phase_idx": e.current_phase_idx,
        "subsystem_hp": dict(e.subsystem_hp),
        "subsystems_destroyed": sorted(e.subsystems_destroyed),
        "engines_just_destroyed": e.engines_just_destroyed,
        "focused_subsystem": e.focused_subsystem,
    }


def state_snapshot(state: CombatState) -> dict[str, object]:
    """The structured combat state the goldens compare."""
    return {
        "round_number": state.round_number,
        "result": state.result.value,
        "player": _player_state(state.player),
        "enemies": [_enemy_state(e) for e in state.enemies],
        "negotiate_used": state.negotiate_used,
        "bribe_used": state.bribe_used,
        "negotiate_partial_loot": state.negotiate_partial_loot,
        "negotiate_rival_rep": state.negotiate_rival_rep,
        "revealed_bribe_cost": state.revealed_bribe_cost,
        "fired_complication_ids": sorted(state.fired_complication_ids),
        "shield_regen_multiplier": state.shield_regen_multiplier,
        "player_evasion_modifier": state.player_evasion_modifier,
        "enemy_accuracy_multiplier": state.enemy_accuracy_multiplier,
        "complication_flags": sorted(state.complication_flags),
    }


def _log(entries: list[CombatLogEntry]) -> list[list[object]]:
    return [[e.round_number, e.actor, e.action, e.hit] for e in entries]


def _take_log(fight: Fight) -> list[list[object]]:
    """Every ``combat_log`` entry appended since the last take.

    An engine call's return value is not the full story: a dual tech's cinematic
    reveal, and for some techs its own activation entry, are appended straight to
    ``state.combat_log`` without ever appearing in what the call returns. Reading
    the log itself, and tracking how much of it this fight has already recorded
    via ``log_seen``, is the only way to miss nothing.

    Args:
        fight: The fight whose log to read from.

    Returns:
        Every new entry since the last call, in golden log-row form.
    """
    entries = _log(fight.state.combat_log[fight.log_seen :])
    fight.log_seen = len(fight.state.combat_log)
    return entries


def _roster(loyalty: int) -> CrewRoster:
    roster = CrewRoster(get_data_loader().crew_templates)
    for crew_id in COMPANIONS:
        roster.recruit(crew_id, 4)
        roster.adjust_loyalty(crew_id, loyalty - 30)
    return roster


def build_fight(
    name: str,
    *,
    ship_type_id: str,
    loadout: tuple[str, ...],
    enemy_ids: tuple[str, ...],
    seed: int,
    crew_loyalty: int = 0,
    hull: int = 0,
    complication_ids: tuple[str, ...] = (),
    skill_levels: dict[str, int] | None = None,
) -> Fight:
    """Build a fight on the ship-type path.

    Args:
        name: Case name (recorded in the setup).
        ship_type_id: Player ship type.
        loadout: Upgrade ids to install, in order.
        enemy_ids: Enemy template ids.
        seed: The fight seed (encounter seed and engine seed alike).
        crew_loyalty: When positive, all four companions aboard at this loyalty.
        hull: When positive, overrides hull and max hull (bosses).
        complication_ids: Complications resolved from the data loader.
        skill_levels: Skills the player has learned, by id and level; recorded in the setup only when given.

    Returns:
        The fight.
    """
    dl = get_data_loader()
    player = fresh_player(ship_type_id=ship_type_id)
    for skill_id, level in (skill_levels or {}).items():
        player.progression.skills[skill_id].current_level = level
    upgrades = ShipUpgradeManager()
    for upgrade_id in loadout:
        ok, msg = upgrades.install(dl.upgrades[upgrade_id])
        assert ok, f"{name}: {upgrade_id} did not install: {msg}"
    roster = _roster(crew_loyalty) if crew_loyalty else None
    pcs = build_player_combat_state(
        player.ship,
        upgrades,
        roster,
        {},
        player_level=5,
        progression=player.progression,
        dialogue_flags={},
    )
    if hull:
        pcs.hull = pcs.max_hull = hull
    templates = [dl.enemy_templates[t] for t in enemy_ids]
    enemies = [EnemyShip.from_template(t) for t in templates]
    complications = [dl.complications[c] for c in complication_ids]
    encounter = CombatEncounter(enemy_templates=templates, encounter_seed=seed)
    state = CombatState(player=pcs, enemies=enemies, encounter=encounter, combat_log=[])
    engine = CombatEngine(state, seed=seed, complications=complications)
    setup: dict[str, object] = {
        "ship_type_id": ship_type_id,
        "loadout": list(loadout),
        "enemy_ids": list(enemy_ids),
        "seed": seed,
        "crew_loyalty": crew_loyalty,
        "hull": hull,
        "complication_ids": list(complication_ids),
        "player": _player_state(pcs),
        "payout_player": {
            "name": "ParityPilot",
            "credits": 0,
            "system_id": "nexus_prime",
            "ship_type": "shuttle",
            "fuel": 40,
        },
    }
    if skill_levels:
        setup["skill_levels"] = dict(skill_levels)
    return Fight(engine, state, setup)


def _record(fight: Fight, case: Case, call: str, args: list[object], result: object) -> None:
    case.record(call, args, result, state_snapshot(fight.state))


def _target(state: CombatState) -> int:
    return next((i for i, e in enumerate(state.enemies) if e.is_alive and not e.is_fled), 0)


def play_round(fight: Fight, case: Case, extra_moves: tuple[str, ...] = ()) -> None:
    """One round of the fixed policy, recorded step by step."""
    state, engine = fight.state, fight.engine
    target = _target(state)
    queue = ActionQueue(
        energy_available=state.player.energy, cooldowns=dict(state.player.cooldowns)
    )
    queued: list[str] = []
    candidates = [m for m in state.player.dual_tech_moves if m.id in extra_moves]
    candidates += engine.get_available_moves()
    for move in candidates:
        ok, _msg = queue.add(move.id, target, move)
        if ok:
            queued.append(move.id)
    engine.execute_player_turn(queue)
    _record(fight, case, "player_turn", [queued, target], _take_log(fight))
    if not engine.is_combat_over() and any(e.is_alive and not e.is_fled for e in state.enemies):
        engine.execute_enemy_turns()
        _record(fight, case, "enemy_turns", [], _take_log(fight))
    if not engine.is_combat_over():
        engine.end_round()
        _record(fight, case, "end_round", [], _take_log(fight))


def _finish(fight: Fight, case: Case, max_rounds: int = MAX_ROUNDS) -> None:
    rounds = 0
    while not fight.engine.is_combat_over() and rounds < max_rounds:
        play_round(fight, case)
        rounds += 1
    _payout(fight, case)


def _build_player(fields: Any) -> Player:
    """Construct the payout player from ``setup['payout_player']``'s five fields.

    This is the shape ``trade.py``, ``player.py`` and ``encounters.py`` already
    record: a player only ``fresh_player``'s five keyword arguments can rebuild,
    so the Godot adapter never has to guess what the payout ran on.
    """
    return fresh_player(
        name=fields["name"],
        credits=fields["credits"],
        system_id=fields["system_id"],
        ship_type_id=fields["ship_type"],
        fuel=fields["fuel"],
    )


def _payout(fight: Fight, case: Case) -> None:
    state = fight.state
    player = _build_player(fight.setup["payout_player"])
    seed = state.encounter.encounter_seed
    enemies = [
        {"template_id": e.template.id, "dead": not e.is_alive, "fled": e.is_fled}
        for e in state.enemies
    ]
    if state.result == CombatResult.VICTORY:
        victory = player.apply_combat_victory(state.enemies, seed)
        result: object = {"xp": victory.xp, "credits": victory.credits, "loot": victory.loot}
        case.record("apply_combat_victory", [enemies, seed], result, player_snapshot(player))
    elif state.result == CombatResult.NEGOTIATED:
        loot = player.apply_combat_negotiated(state.enemies, seed, state.negotiate_partial_loot)
        case.record(
            "apply_combat_negotiated",
            [enemies, seed, state.negotiate_partial_loot],
            loot,
            player_snapshot(player),
        )


def _new_case(name: str, fight: Fight) -> Case:
    return Case("combat", name, fight.setup)


def _template_fights() -> list[Case]:
    dl = get_data_loader()
    cases: list[Case] = []
    for index, (template_id, template) in enumerate(dl.enemy_templates.items()):
        fight = build_fight(
            f"fight_{template_id}",
            ship_type_id="war_frigate",
            loadout=BOSS_LOADOUT if template.is_boss else LOADOUTS[index % len(LOADOUTS)],
            enemy_ids=(template_id,),
            seed=stable_seed("parity_fight", template_id),
            hull=BOSS_HULL if template.is_boss else 0,
        )
        case = _new_case(f"fight_{template_id}", fight)
        _finish(fight, case, max_rounds=BOSS_MAX_ROUNDS if template.is_boss else MAX_ROUNDS)
        cases.append(case)
    return cases


def _complication_fights() -> list[Case]:
    cases: list[Case] = []
    for complication_id in get_data_loader().complications:
        hull = MORALE_SHIFT_HULL if complication_id == "morale_shift" else 400
        fight = build_fight(
            f"complication_{complication_id}",
            ship_type_id="shuttle",
            loadout=LOADOUTS[0],
            enemy_ids=("pirate_raider", "pirate_raider"),
            seed=stable_seed("parity_complication", complication_id),
            hull=hull,
            complication_ids=(complication_id,),
        )
        case = _new_case(f"complication_{complication_id}", fight)
        _finish(fight, case)
        cases.append(case)
    return cases


def _ultimate_fights() -> list[Case]:
    dl = get_data_loader()
    cases: list[Case] = []
    for category in dl.ship_ultimates:
        ship_type_id = min(
            t for t, st in dl.ship_types.items() if st.ship_class_category == category
        )
        fight = build_fight(
            f"ultimate_{category}",
            ship_type_id=ship_type_id,
            loadout=LOADOUTS[0],
            enemy_ids=("pirate_raider", "pirate_scout"),
            seed=stable_seed("parity_ultimate", category),
            hull=600,
        )
        assert fight.state.player.momentum is not None
        fight.state.player.momentum.current = 1.0
        fight.setup["momentum"] = 1.0
        # Re-record the player state now that momentum is pinned to 1.0, so the setup
        # the port rebuilds from matches the state the fight actually starts from.
        fight.setup["player"] = _player_state(fight.state.player)
        case = _new_case(f"ultimate_{category}", fight)
        fight.engine.execute_ultimate()
        _record(fight, case, "execute_ultimate", [], _take_log(fight))
        _finish(fight, case)
        cases.append(case)
    return cases


def _dual_tech_fights() -> list[Case]:
    cases: list[Case] = []
    for tech in DUAL_TECH_PALETTE.values():
        fight = build_fight(
            f"dual_tech_{tech.id}",
            ship_type_id="war_frigate",
            loadout=LOADOUTS[0],
            enemy_ids=("pirate_heavy",),
            seed=stable_seed("parity_dual_tech", tech.id),
            crew_loyalty=90,
            hull=600,
        )
        case = _new_case(f"dual_tech_{tech.id}", fight)
        play_round(fight, case, extra_moves=(tech.id,))
        _finish(fight, case)
        cases.append(case)
    return cases


def _resolution_fights() -> list[Case]:
    cases: list[Case] = []
    for kind in ("flee", "bribe", "negotiate", "negotiate_failed"):
        fight = build_fight(
            f"resolve_{kind}",
            ship_type_id="shuttle",
            loadout=LOADOUTS[0],
            enemy_ids=("pirate_raider",),
            seed=stable_seed("parity_resolve", kind),
        )
        engine = fight.engine
        social: dict[str, object] = {}
        if kind in ("negotiate", "negotiate_failed"):
            # "negotiate" carries a maxed persuasion so the check passes; "negotiate_failed"
            # keeps SocialManager's own defaults (level 1), which do not, preserving the
            # difficulty-message failure branch this fight recorded before this change.
            social = NEGOTIATE_PROFILE if kind == "negotiate" else {}
            fight.setup["social"] = social
        case = _new_case(f"resolve_{kind}", fight)
        if kind == "flee":
            ok, _logs = engine.attempt_flee()
            _record(fight, case, "attempt_flee", [], [ok, _take_log(fight)])
        elif kind == "bribe":
            ok, cost, _logs = engine.attempt_bribe(10_000)
            _record(fight, case, "attempt_bribe", [10_000], [ok, cost, _take_log(fight)])
        else:
            manager = SocialManager()
            manager.load_state(social)
            ok, msg, _logs = engine.attempt_negotiate("persuasion", manager, None)
            _record(
                fight,
                case,
                "attempt_negotiate",
                ["persuasion", None],
                [ok, msg, _take_log(fight)],
            )
        _finish(fight, case)
        cases.append(case)
    return cases


def _skill_fights() -> list[Case]:
    """A fight whose player has learned Shield Mastery (BB-75), the one skill case."""
    fight = build_fight(
        "skill_shield_mastery",
        ship_type_id="shuttle",
        loadout=LOADOUTS[0],
        enemy_ids=("pirate_raider",),
        seed=stable_seed("parity_skill", "shield_mastery"),
        skill_levels={"shield_mastery": 3},
    )
    case = _new_case("skill_shield_mastery", fight)
    _finish(fight, case)
    return [case]


def build_cases() -> list[Case]:
    """Every combat case."""
    get_data_loader().load_all()
    return [
        *_template_fights(),
        *_complication_fights(),
        *_ultimate_fights(),
        *_dual_tech_fights(),
        *_resolution_fights(),
        *_skill_fights(),
    ]
