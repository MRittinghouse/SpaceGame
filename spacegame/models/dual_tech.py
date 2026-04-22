"""
Dual tech system — Chrono Trigger-style paired crew abilities.

See ``requirements/combat_balance_design.md §5`` for design intent.

**Scope of this module (B8.1):**
- Data definitions for all 6 pair dual techs + 1 triad ("Crew Sync").
- Availability logic: which techs can the player queue right now, given
  the current crew roster state.
- Two executable moves (Gun Run, Focused Barrage) that compile cleanly
  into existing ``CombatMove`` effects — they need no new engine hooks.

**Deferred to B8.2 (see §12 deferred log):**
- Fire at Will, Power Drift, Daring Gambit, Total Commitment, Crew Sync
  — each needs a dedicated engine hook (turn-scoped energy discount,
  regen mods, incoming-damage interception, etc.). They're defined here
  as data but not yet wired into combat.
- First-use cinematic dialogue reveal (narrative content).
- Combat view's "Coordinated" section (UI integration).

Prereq gate for availability:
    - Every participating crew member is RECRUITED
    - Every participating crew member has loyalty >= tech.loyalty_req
    - Every participating crew member is in the "bridge crew" set for
      the current combat (the game currently treats all recruited crew
      as bridge crew; see §12 deferred).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spacegame.models.combat import (
    CombatEffect,
    CombatMove,
    EffectTarget,
    EffectType,
)

# ============================================================================
# Data model
# ============================================================================


@dataclass(frozen=True)
class DualTech:
    """A coordinated bridge-crew ability.

    Attributes:
        id: Stable identifier used in saves and UI references.
        name: Player-facing display name.
        crew_ids: IDs of participating crew (2 for pair, 4 for triad).
        loyalty_req: Minimum loyalty each participating crew must reach.
        energy_cost: Ship energy consumed when activated.
        cooldown: Rounds before the tech can fire again.
        description: One-line narrative flavor.
        once_per_combat: If True, may only fire once per encounter (Crew Sync).
        implementation_ready: If False, this tech is defined but not yet
            executable — see B8.2 deferred work.
    """

    id: str
    name: str
    crew_ids: tuple[str, ...]
    loyalty_req: int
    energy_cost: int
    cooldown: int
    description: str
    once_per_combat: bool = False
    implementation_ready: bool = False


# ============================================================================
# Palette — all 6 pairs + 1 triad. See design doc §5.
# ============================================================================


# Canonical companion IDs from data/crew/crew_members.json.
_ELENA = "elena_reeves"
_MARCUS = "marcus_jin"
_PRIYA = "dr_priya_osei"
_TOMAS = "tomas_drifter"


DUAL_TECH_PALETTE: dict[str, DualTech] = {
    "fire_at_will": DualTech(
        id="fire_at_will",
        name="Fire at Will",
        crew_ids=(_ELENA, _MARCUS),
        loyalty_req=50,  # Design doc L2 (30-50 tier).
        energy_cost=6,
        cooldown=4,
        description=(
            "Elena cuts the firing solutions, Marcus synchronizes the "
            "mounts. Every equipped weapon fires this turn at half energy "
            "cost, with no cooldown aftermath."
        ),
        implementation_ready=True,  # B8.2: turn-scoped energy discount wired.
    ),
    "daring_gambit": DualTech(
        id="daring_gambit",
        name="Daring Gambit",
        crew_ids=(_ELENA, _TOMAS),
        loyalty_req=50,
        energy_cost=4,
        cooldown=4,
        description=(
            "Elena calls the vector, Tomas threads the ledger. +40% "
            "evasion for two turns; a successful dodge returns a "
            "25-damage counter."
        ),
        implementation_ready=True,  # B8.2: evasion wired; counter-on-dodge deferred to B8.3.
    ),
    "total_commitment": DualTech(
        id="total_commitment",
        name="Total Commitment",
        crew_ids=(_ELENA, _PRIYA),
        loyalty_req=70,  # Design doc L3 (70-85 tier).
        energy_cost=8,
        cooldown=6,
        description=(
            "Priya reroutes structural integrity, Elena holds the heading "
            "through every impact. The next three incoming hull hits "
            "become armor stacks (cap +8 armor for this fight)."
        ),
        implementation_ready=True,  # B8.3: hull-damage interception wired.
    ),
    "focused_barrage": DualTech(
        id="focused_barrage",
        name="Focused Barrage",
        crew_ids=(_MARCUS, _PRIYA),
        loyalty_req=70,
        energy_cost=8,
        cooldown=5,
        description=(
            "Marcus opens a single mount's safeties, Priya overcharges the "
            "capacitor. One weapon fires at double damage, ignores all "
            "armor, +25% crit chance."
        ),
        implementation_ready=True,  # Expressible as a single-target damage move.
    ),
    "gun_run": DualTech(
        id="gun_run",
        name="Gun Run",
        crew_ids=(_MARCUS, _TOMAS),
        loyalty_req=50,
        energy_cost=6,
        cooldown=4,
        description=(
            "Tomas flies the strafing line, Marcus keeps the mounts hot "
            "through the pass. Every enemy on the field takes 35 damage."
        ),
        implementation_ready=True,  # Expressible as AOE damage move.
    ),
    "power_drift": DualTech(
        id="power_drift",
        name="Power Drift",
        crew_ids=(_PRIYA, _TOMAS),
        loyalty_req=50,
        energy_cost=4,
        cooldown=4,
        description=(
            "Priya bleeds the reactor, Tomas cashes the momentum. +6 "
            "energy this turn; all weapon cooldowns reduced by 2."
        ),
        implementation_ready=True,  # B8.2: regen + cooldown-tick wired.
    ),
    # ---- Triad ----
    "crew_sync": DualTech(
        id="crew_sync",
        name="Crew Sync",
        crew_ids=(_ELENA, _MARCUS, _PRIYA, _TOMAS),
        loyalty_req=70,
        energy_cost=12,
        cooldown=0,  # Gated by once_per_combat, not cooldown.
        description=(
            "The bridge moves as one. Every weapon fires at double damage "
            "ignoring armor, 40% of hull restored, +4 evasion for three "
            "turns."
        ),
        once_per_combat=True,
        implementation_ready=True,  # B8.2: compound effects wired; armor-ignoring deferred.
    ),
}


PAIR_TECH_IDS: tuple[str, ...] = (
    "fire_at_will",
    "daring_gambit",
    "total_commitment",
    "focused_barrage",
    "gun_run",
    "power_drift",
)
TRIAD_TECH_IDS: tuple[str, ...] = ("crew_sync",)


# ============================================================================
# Availability logic
# ============================================================================


def _get_loyalty(crew_roster: Any, crew_id: str) -> int | None:
    """Return loyalty value for a recruited crew member, else None."""
    if crew_roster is None:
        return None
    state = crew_roster.get_member_state(crew_id)
    if state is None:
        return None
    return int(state.get("loyalty", 0))


def is_dual_tech_available(
    tech: DualTech,
    crew_roster: Any,
    bridge_crew_ids: set[str] | None = None,
) -> tuple[bool, str]:
    """Check whether a dual tech's prerequisites are satisfied.

    Args:
        tech: The dual tech being checked.
        crew_roster: ``CrewRoster`` with recruited state.
        bridge_crew_ids: Optional set of crew IDs currently on the bridge
            (available this combat). If None, all recruited crew are
            considered bridge-available.

    Returns:
        (available, reason). ``reason`` is a short string explaining why
        the tech is locked (or "OK" when available).
    """
    for cid in tech.crew_ids:
        loyalty = _get_loyalty(crew_roster, cid)
        if loyalty is None:
            return False, f"{cid} not recruited"
        if loyalty < tech.loyalty_req:
            return False, (
                f"{cid} loyalty {loyalty} < required {tech.loyalty_req}"
            )
        if bridge_crew_ids is not None and cid not in bridge_crew_ids:
            return False, f"{cid} not on bridge this combat"
    return True, "OK"


def compute_available_dual_techs(
    crew_roster: Any,
    bridge_crew_ids: set[str] | None = None,
) -> list[DualTech]:
    """Return the dual techs the player can currently queue.

    Filters ``DUAL_TECH_PALETTE`` to the subset whose prerequisites are
    satisfied. Order matches ``PAIR_TECH_IDS`` + ``TRIAD_TECH_IDS`` so
    the UI can render a stable list.

    Args:
        crew_roster: The player's crew roster.
        bridge_crew_ids: Crew IDs currently on the bridge, or None to
            treat all recruited crew as bridge-available.

    Returns:
        Ordered list of available DualTech instances.
    """
    available: list[DualTech] = []
    for tid in PAIR_TECH_IDS + TRIAD_TECH_IDS:
        tech = DUAL_TECH_PALETTE[tid]
        ok, _ = is_dual_tech_available(tech, crew_roster, bridge_crew_ids)
        if ok:
            available.append(tech)
    return available


# ============================================================================
# Executable dual techs — B8.1 scope: Gun Run + Focused Barrage.
# ============================================================================
#
# These compile cleanly to CombatMove. They ride the existing ActionQueue
# + combat engine for resolution without requiring new hooks.


def build_gun_run_move() -> CombatMove:
    """Gun Run (Marcus + Tomas) — AOE 35 damage to all enemies.

    Uses the existing ``aoe`` flag on CombatMove so the engine's
    standard damage pipeline handles it.
    """
    tech = DUAL_TECH_PALETTE["gun_run"]
    return CombatMove(
        id=tech.id,
        name=tech.name,
        description=tech.description,
        effects=[
            CombatEffect(
                type=EffectType.DAMAGE,
                value=35.0,
                target=EffectTarget.ENEMY,
            )
        ],
        energy_cost=tech.energy_cost,
        cooldown=tech.cooldown,
        aoe=True,
        accuracy_modifier=15,  # Coordinated attack hits reliably.
    )


def build_focused_barrage_move() -> CombatMove:
    """Focused Barrage (Marcus + Priya) — single-target, very high damage.

    Armor-ignoring and 25%-crit-boost behaviors are NOT yet wired into
    the CombatEffect system — logged as B8.3 deferred. This move
    implements the base damage portion (roughly 2× typical tech damage,
    ≈55 dmg) so the tech is at least usable.
    """
    tech = DUAL_TECH_PALETTE["focused_barrage"]
    return CombatMove(
        id=tech.id,
        name=tech.name,
        description=tech.description,
        effects=[
            CombatEffect(
                type=EffectType.DAMAGE,
                value=55.0,
                target=EffectTarget.ENEMY,
            )
        ],
        energy_cost=tech.energy_cost,
        cooldown=tech.cooldown,
        accuracy_modifier=20,
    )


def build_fire_at_will_move() -> CombatMove:
    """Fire at Will (Elena + Marcus) — activates a turn-scoped flag.

    The activation itself has no damage/effect payload. The combat
    engine's dual-tech dispatch sets ``player.fire_at_will_active = True``
    on resolution; subsequent weapon moves in the same turn then fire
    at half energy cost and skip cooldown assignment.
    """
    tech = DUAL_TECH_PALETTE["fire_at_will"]
    return CombatMove(
        id=tech.id,
        name=tech.name,
        description=tech.description,
        effects=[],  # Engine dispatch applies the flag; no CombatEffect pipeline.
        energy_cost=tech.energy_cost,
        cooldown=tech.cooldown,
    )


def build_power_drift_move() -> CombatMove:
    """Power Drift (Priya + Tomas) — immediate energy boost + cooldown wipe.

    Combat engine dispatch applies: +6 to player.energy (clamped at max)
    and subtracts 2 from every active cooldown. No ongoing state.
    """
    tech = DUAL_TECH_PALETTE["power_drift"]
    return CombatMove(
        id=tech.id,
        name=tech.name,
        description=tech.description,
        effects=[],
        energy_cost=tech.energy_cost,
        cooldown=tech.cooldown,
    )


def build_daring_gambit_move() -> CombatMove:
    """Daring Gambit (Elena + Tomas) — +40 evasion for 2 turns.

    Counter-on-dodge portion is deferred to B8.3. The evasion buff is
    expressed through the standard ``EVASION_MOD`` active-effect
    pipeline, so tick_effects handles cleanup automatically.
    """
    tech = DUAL_TECH_PALETTE["daring_gambit"]
    return CombatMove(
        id=tech.id,
        name=tech.name,
        description=tech.description,
        effects=[
            CombatEffect(
                type=EffectType.EVASION_MOD,
                value=40.0,
                duration=2,
                target=EffectTarget.SELF,
            )
        ],
        energy_cost=tech.energy_cost,
        cooldown=tech.cooldown,
    )


def build_total_commitment_move() -> CombatMove:
    """Total Commitment (Elena + Priya) — intercepts next 3 hull hits.

    Activation primes a 3-hit counter on PlayerCombatState. During
    combat, each incoming hull hit is converted to armor (+2 per hit,
    cap +8 for this fight) via a hook in _apply_direct_damage.
    """
    tech = DUAL_TECH_PALETTE["total_commitment"]
    return CombatMove(
        id=tech.id,
        name=tech.name,
        description=tech.description,
        effects=[],
        energy_cost=tech.energy_cost,
        cooldown=tech.cooldown,
    )


def build_crew_sync_move() -> CombatMove:
    """Crew Sync (all four senior crew) — compound one-shot finale.

    Applies via the standard effect pipeline:
    - 40% hull restore (value=0 placeholder; engine dispatch computes from max_hull)
    - +4 evasion for 3 turns
    - +100% damage boost for 1 turn
    Engine dispatch also sets ``player.crew_sync_used = True`` to enforce
    the once-per-combat rule. Armor-ignoring damage behavior is
    deferred to B8.3.
    """
    tech = DUAL_TECH_PALETTE["crew_sync"]
    return CombatMove(
        id=tech.id,
        name=tech.name,
        description=tech.description,
        # Note: HULL_RESTORE with value=0 is a placeholder; engine dispatch
        # replaces with 40% of max_hull. Keeping effects non-empty lets the
        # move log naturally.
        effects=[
            CombatEffect(
                type=EffectType.EVASION_MOD,
                value=4.0,
                duration=3,
                target=EffectTarget.SELF,
            ),
            CombatEffect(
                type=EffectType.DAMAGE_BOOST,
                value=100.0,  # +100% damage
                duration=1,
                target=EffectTarget.SELF,
            ),
        ],
        energy_cost=tech.energy_cost,
        cooldown=tech.cooldown,
    )


# ID → factory map for techs with execution.
_EXECUTABLE_FACTORIES: dict[str, Any] = {
    "gun_run": build_gun_run_move,
    "focused_barrage": build_focused_barrage_move,
    "fire_at_will": build_fire_at_will_move,
    "power_drift": build_power_drift_move,
    "daring_gambit": build_daring_gambit_move,
    "crew_sync": build_crew_sync_move,
    "total_commitment": build_total_commitment_move,
}


# ============================================================================
# Engine-side activation helpers — called from combat_engine when a
# dual-tech move resolves. These apply effects that can't be expressed
# as plain CombatEffect entries.
# ============================================================================


def activate_power_drift(player: Any) -> list[str]:
    """Apply Power Drift's immediate effects: +6 energy and -2 on all cooldowns.

    Power Drift excludes its own cooldown key from the reduction — the
    design intent is that the tech wipes *weapon* cooldowns so the
    player can alpha-strike again, not that it refunds its own.

    Returns a list of log strings describing what happened.
    """
    logs: list[str] = []
    gained = min(6, player.max_energy - player.energy)
    player.energy += gained
    logs.append(f"Power Drift: +{gained} energy")
    affected = 0
    for key in list(player.cooldowns.keys()):
        if key == "power_drift":
            continue
        old = player.cooldowns[key]
        if old > 0:
            player.cooldowns[key] = max(0, old - 2)
            affected += 1
    if affected:
        logs.append(f"Power Drift: {affected} weapon cooldown(s) reduced by 2")
    return logs


def activate_fire_at_will(player: Any) -> list[str]:
    """Set the fire-at-will flag; the engine's weapon resolution reads it."""
    player.fire_at_will_active = True
    return ["Fire at Will: weapons fire this turn at half energy, no cooldown"]


def activate_crew_sync(player: Any) -> tuple[bool, list[str]]:
    """Apply Crew Sync's compound effect if it hasn't fired yet this combat.

    B8.3 additions: sets ``armor_pierce_active`` so the player's attacks
    this turn bypass defender armor. The flag is cleared by
    ``tick_armor_pierce_on_end_round``.

    Returns:
        (applied, log_entries). If already used this combat, applied is
        False and no state changes are made (caller should refund energy).
    """
    if getattr(player, "crew_sync_used", False):
        return False, ["Crew Sync already fired this combat"]
    player.crew_sync_used = True
    player.armor_pierce_active = True
    logs = ["Crew Sync: the bridge moves as one"]
    heal_amount = int(player.max_hull * 0.40)
    restored = min(heal_amount, player.max_hull - player.hull)
    player.hull += restored
    if restored > 0:
        logs.append(f"Crew Sync: hull restored +{restored}")
    return True, logs


# ============================================================================
# B8.3 additions — Total Commitment + Daring Gambit counter + cleanup
# ============================================================================


# Per-hit armor gain and total cap for Total Commitment.
TOTAL_COMMITMENT_HITS = 3
TOTAL_COMMITMENT_ARMOR_PER_HIT = 3
TOTAL_COMMITMENT_ARMOR_CAP = 8


def activate_total_commitment(player: Any) -> list[str]:
    """Prime the Total Commitment hit-to-armor intercept."""
    player.total_commitment_hits_remaining = TOTAL_COMMITMENT_HITS
    player.total_commitment_armor_gained = 0
    return [
        f"Total Commitment: next {TOTAL_COMMITMENT_HITS} hull hits convert to armor"
    ]


def activate_daring_gambit_counter(player: Any) -> list[str]:
    """Arm the 2-turn counter-on-dodge window for Daring Gambit.

    The +40 evasion buff is applied via the standard EVASION_MOD effect
    pipeline in ``build_daring_gambit_move``. This helper adds the
    counter-on-dodge window, tracked as a turn counter that ticks in
    end_round.
    """
    player.daring_gambit_turns = 2
    return ["Daring Gambit: counter-on-dodge armed for 2 turns"]


def intercept_total_commitment_hull_damage(
    player: Any,
    hull_damage: int,
) -> tuple[int, list[str]]:
    """If Total Commitment is primed, convert this hull hit to armor.

    Called from ``_apply_direct_damage`` before the hull-subtract step.

    Args:
        player: The defender (PlayerCombatState).
        hull_damage: Incoming hull damage about to land.

    Returns:
        (remaining_hull_damage, log_messages). The returned damage is
        what the engine should still apply after interception. Log
        messages describe armor gains or absorbed hits.
    """
    if (
        hull_damage <= 0
        or getattr(player, "total_commitment_hits_remaining", 0) <= 0
    ):
        return hull_damage, []

    player.total_commitment_hits_remaining -= 1

    # Armor gain per hit, capped by the per-fight limit.
    cap_room = TOTAL_COMMITMENT_ARMOR_CAP - player.total_commitment_armor_gained
    gained = min(TOTAL_COMMITMENT_ARMOR_PER_HIT, cap_room)
    if gained > 0:
        player.armor += gained
        player.total_commitment_armor_gained += gained
        return 0, [
            f"Total Commitment: hit absorbed, +{gained} armor "
            f"(gauntlet: {player.total_commitment_armor_gained}/"
            f"{TOTAL_COMMITMENT_ARMOR_CAP})"
        ]
    # Cap reached — still absorb the hit but no further armor gain.
    return 0, ["Total Commitment: hit absorbed (armor cap reached)"]


@dataclass(frozen=True)
class DualTechStatus:
    """UI-facing snapshot of one dual tech's availability.

    Produced by ``describe_all_dual_techs`` so the crew-roster view can
    render locked/unlocked entries without reaching into the roster's
    internals. Also lets tests assert on structure instead of rendered
    pixels.
    """

    tech: DualTech
    is_available: bool
    lock_reason: str  # "OK" when available; human-readable otherwise
    crew_loyalties: tuple[tuple[str, int | None], ...]
    # crew_loyalties: ((crew_id, current_loyalty_or_None_if_not_recruited), ...)


def describe_all_dual_techs(
    crew_roster: Any,
    bridge_crew_ids: set[str] | None = None,
) -> list[DualTechStatus]:
    """Produce a UI snapshot of every dual tech in the palette.

    Returns an ordered list (pairs then triad) with each tech's
    availability state and the current loyalty of each participating
    crew member. Intended for the crew-roster view's "locked techs"
    discoverability panel.

    Args:
        crew_roster: Player's CrewRoster, or None if no crew.
        bridge_crew_ids: Optional bridge filter (None = all recruited).

    Returns:
        List of DualTechStatus, one per tech in canonical order.
    """
    out: list[DualTechStatus] = []
    for tid in PAIR_TECH_IDS + TRIAD_TECH_IDS:
        tech = DUAL_TECH_PALETTE[tid]
        ok, reason = is_dual_tech_available(tech, crew_roster, bridge_crew_ids)
        loyalties: list[tuple[str, int | None]] = []
        for cid in tech.crew_ids:
            loyalties.append((cid, _get_loyalty(crew_roster, cid)))
        out.append(
            DualTechStatus(
                tech=tech,
                is_available=ok,
                lock_reason=reason,
                crew_loyalties=tuple(loyalties),
            )
        )
    return out


def inject_available_dual_techs(
    player: Any,
    crew_roster: Any,
    bridge_crew_ids: set[str] | None = None,
) -> int:
    """Populate ``player.dual_tech_moves`` with currently-available techs.

    Called at the start of combat (from ``build_player_combat_state``).
    Techs become visible to the combat view alongside weapon moves, so
    the player can queue them like any other ability. Unavailable techs
    are simply omitted — the UI shows only what's queueable.

    Args:
        player: The PlayerCombatState to populate.
        crew_roster: The player's CrewRoster.
        bridge_crew_ids: Optional filter (None = all recruited crew).

    Returns:
        Number of techs injected.
    """
    if crew_roster is None:
        return 0

    moves: list[CombatMove] = []
    for tech in compute_available_dual_techs(crew_roster, bridge_crew_ids):
        move = build_dual_tech_move(tech.id)
        if move is None:
            continue
        # Place dual techs under a distinct category so the UI can
        # group them if desired. Falls back to "utility" tab in the
        # current combat view.
        move.category = "coordinated"
        moves.append(move)

    player.dual_tech_moves = moves
    return len(moves)


def tick_dual_tech_end_of_round(player: Any) -> list[str]:
    """Tick turn-scoped dual tech state at end of round.

    Clears ``armor_pierce_active`` and decrements
    ``daring_gambit_turns``. Called from CombatEngine.end_round.
    """
    logs: list[str] = []
    if getattr(player, "armor_pierce_active", False):
        player.armor_pierce_active = False
    if getattr(player, "daring_gambit_turns", 0) > 0:
        player.daring_gambit_turns -= 1
        if player.daring_gambit_turns == 0:
            logs.append("Daring Gambit counter window closed")
    return logs


def build_dual_tech_move(tech_id: str) -> CombatMove | None:
    """Return a CombatMove for an executable dual tech, or None.

    Args:
        tech_id: The dual tech ID.

    Returns:
        A CombatMove instance if the tech has a B8.1 executor, else None.
    """
    factory = _EXECUTABLE_FACTORIES.get(tech_id)
    if factory is None:
        return None
    return factory()
