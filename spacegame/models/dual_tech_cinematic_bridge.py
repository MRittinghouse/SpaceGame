"""Bridge between existing dual tech mechanics and the cinematic.

The dual tech mechanical system (`models/dual_tech.py`) was shipped in
B8.2/B8.3 as data + activation logic. The cinematic framework (C5) was
shipped as a separate rendering primitive. This module wires them
together: maps each tech id to its element palette + crew portraits so
combat_view can fire `trigger_dual_tech(...)` at dispatch time.

Element assignments are narrative choices — each tech's description in
`models/dual_tech.py` guides the element pair (e.g., Power Drift =
"reactor bleed + momentum" → voltaic + ion). These are hard-coded because
adding element fields to DualTech would force a data migration; the
cinematic layer is the right owner for visual-language concerns.

See:
  - `requirements/overhaul/30_overhaul_space_combat.md §4.3` (spec)
  - `spacegame/models/dual_tech.py` (mechanical data)
  - `spacegame/engine/dual_tech_cinematic.py` (timeline primitive)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Element pair per tech id
# ---------------------------------------------------------------------------
#
# Element choices follow narrative intent from each tech's description:
#   fire_at_will      — Elena cuts solutions, Marcus synchs mounts → all-weapons
#                       coordinated barrage. Plasma (weapon heat) + kinetic.
#   daring_gambit     — Elena calls vector, Tomas threads the ledger → evasion
#                       precision + counter. Cryo (sharp cold read) + kinetic.
#   total_commitment  — Priya reroutes integrity, Elena holds heading → armor
#                       conversion. Cryo (ice armor) + plasma (reactor stress).
#   focused_barrage   — Marcus opens safeties, Priya overcharges cap → single
#                       devastating shot. Plasma + voltaic (overcharge).
#   gun_run           — Tomas flies strafing line, Marcus keeps mounts hot →
#                       AOE sweep. Plasma + kinetic (strafe gunfire).
#   power_drift       — Priya bleeds reactor, Tomas cashes momentum → energy
#                       burst + cooldown relief. Voltaic + ion (reactor arc).
#   crew_sync         — The bridge moves as one → ultimate synthesis. Ion +
#                       voltaic (all-systems flare).

DUAL_TECH_ELEMENTS: dict[str, tuple[str, str]] = {
    "fire_at_will": ("plasma", "kinetic"),
    "daring_gambit": ("cryo", "kinetic"),
    "total_commitment": ("cryo", "plasma"),
    "focused_barrage": ("plasma", "voltaic"),
    "gun_run": ("plasma", "kinetic"),
    "power_drift": ("voltaic", "ion"),
    "crew_sync": ("ion", "voltaic"),
}

# Tech ids that count as ultimates — extended 4.5s cinematic with CHARGE
# phase before impact. Crew Sync is the canonical ultimate (once-per-combat,
# triad-participants).
ULTIMATE_TECH_IDS: frozenset[str] = frozenset({"crew_sync"})


# ---------------------------------------------------------------------------
# Snapshot returned to combat_view
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DualTechCinematicInputs:
    """Parameters ready to hand to ``combat_view.trigger_dual_tech()``.

    Portrait surfaces + trail endpoints are NOT resolved here — they
    depend on view-local state (crew roster sprites, screen-space
    positions). The bridge returns the palette + name + is_ultimate;
    the view resolves portraits from crew ids and picks trail endpoints.
    """

    tech_id: str
    tech_name: str
    crew_ids: tuple[str, ...]
    dominant_element: str
    secondary_element: str
    is_ultimate: bool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_cinematic_inputs(tech_id: str) -> Optional[DualTechCinematicInputs]:
    """Return the cinematic inputs for a known dual tech.

    Returns ``None`` for move ids that aren't registered dual techs —
    combat_view uses this as a gate: if inputs are None, no cinematic
    fires and the move dispatches normally.
    """
    elements = DUAL_TECH_ELEMENTS.get(tech_id)
    if elements is None:
        return None
    # Pull the mechanical DualTech entry for its display name + crew list.
    from spacegame.models.dual_tech import DUAL_TECH_PALETTE

    tech = DUAL_TECH_PALETTE.get(tech_id)
    if tech is None:
        return None
    return DualTechCinematicInputs(
        tech_id=tech_id,
        tech_name=tech.name.upper(),  # Cinematic uses shouty caps treatment
        crew_ids=tech.crew_ids,
        dominant_element=elements[0],
        secondary_element=elements[1],
        is_ultimate=tech_id in ULTIMATE_TECH_IDS,
    )


def is_dual_tech_move(move_id: str) -> bool:
    """True when ``move_id`` is a registered dual tech (triggers cinematic)."""
    return move_id in DUAL_TECH_ELEMENTS
