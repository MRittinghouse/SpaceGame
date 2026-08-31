"""Dilemma engine data + coordinator (A2-8).

Ships the model layer for Act II's dilemma system:

- :class:`Dilemma` — a data record describing two or three lenses that
  cross a threshold together and force a choice; also carries the
  telegraph copy that fires before collision.
- :class:`DilemmaOutcome` — one entry per pole, naming which lens wins,
  which lens(es) close, which tier flags unlock, the outcome-summary
  flag, and the narration line the resolution view surfaces.
- :class:`DilemmaRuntimeState` — the per-save runtime bookkeeping
  (telegraphed set, per-dilemma telegraph cursor, resolved map,
  closed-lens set). Lives on ``Player.dilemma_state``.
- :class:`DilemmaCheckResult` — the small typed result returned by the
  coordinator so ``engine/game.py`` can dispatch without a
  ``dict[str, Any]``.
- :func:`check_collision`, :func:`check_telegraph` — pure predicates
  in the shape of :func:`spacegame.models.capstone.should_fire`.
- :func:`check_dilemmas` — the model-layer coordinator ``game.py``
  calls. It reads ``player.lens_investment`` and
  ``player.dilemma_state`` inside the model layer so that the
  compliance guard ``tests/test_compliance/test_lens_investment_never_rendered.py``
  can continue to forbid ``LensInvestment`` tokens under
  ``spacegame/engine/`` and ``spacegame/views/``.

A2-10 will extend this module (or the resolve callback) with the
close-lens walk and ``tier_unlocks`` flag setting. A2-8 ships the
plumbing only — no real dilemma data lives in
``data/narrative/dilemmas/`` yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DilemmaOutcome:
    """One outcome per pole of a :class:`Dilemma`.

    A2-8 ships the field layout; ``tier_unlocks`` is not enforced yet
    (A2-9 will add the build-failing integrity guard that requires
    every outcome to name at least one tier flag).
    """

    winning_lens_id: str
    closes: list[str]
    tier_unlocks: list[str]
    outcome_flag: str
    narration_summary: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "winning_lens_id": self.winning_lens_id,
            "closes": list(self.closes),
            "tier_unlocks": list(self.tier_unlocks),
            "outcome_flag": self.outcome_flag,
            "narration_summary": self.narration_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DilemmaOutcome":
        """Restore a DilemmaOutcome from save/JSON data."""
        return cls(
            winning_lens_id=data["winning_lens_id"],
            closes=list(data.get("closes", [])),
            tier_unlocks=list(data.get("tier_unlocks", [])),
            outcome_flag=data["outcome_flag"],
            narration_summary=data["narration_summary"],
        )


@dataclass
class Dilemma:
    """A dilemma between two or three lenses that must be resolved.

    ``poles`` names the participating lens ids. ``collision_requires``
    is the number of those poles that must individually cross
    ``collision_threshold`` for the dilemma to fire. Pair dilemmas use
    ``collision_requires=2``; the D3 triangle also uses
    ``collision_requires=2`` because only two of the three need to
    burn hot for the third to be forced into a corner.

    ``telegraph_lines`` is the round-robin pool the coordinator cycles
    through on re-delivery; ``len(telegraph_lines) >= 1`` is required
    by the round-robin cursor arithmetic.
    """

    id: str
    poles: list[str]
    collision_requires: int
    telegraph_threshold: int
    collision_threshold: int
    telegraph_npc_id: str
    telegraph_lines: list[str]
    outcomes: list[DilemmaOutcome]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "id": self.id,
            "poles": list(self.poles),
            "collision_requires": self.collision_requires,
            "telegraph_threshold": self.telegraph_threshold,
            "collision_threshold": self.collision_threshold,
            "telegraph_npc_id": self.telegraph_npc_id,
            "telegraph_lines": list(self.telegraph_lines),
            "outcomes": [o.to_dict() for o in self.outcomes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dilemma":
        """Restore a Dilemma from save/JSON data."""
        return cls(
            id=data["id"],
            poles=list(data["poles"]),
            collision_requires=data["collision_requires"],
            telegraph_threshold=data["telegraph_threshold"],
            collision_threshold=data["collision_threshold"],
            telegraph_npc_id=data["telegraph_npc_id"],
            telegraph_lines=list(data.get("telegraph_lines", [])),
            outcomes=[DilemmaOutcome.from_dict(o) for o in data.get("outcomes", [])],
        )


@dataclass
class DilemmaRuntimeState:
    """Per-save runtime bookkeeping for the dilemma engine.

    ``telegraphed``: dilemma ids where the telegraph has fired at least
    once. Read by the coordinator to decide newly vs re-telegraphed.

    ``telegraph_cursor``: per-dilemma round-robin index into
    ``telegraph_lines``. Advances modulo ``len(telegraph_lines)`` on
    every re-delivery so the character always has a fresh thing to say
    rather than repeating line[0].

    ``resolved``: dilemma id → winning ``lens_id`` for every collision
    the player has closed out. The coordinator skips resolved
    dilemmas entirely.

    ``closed_lenses``: set of lens ids that dilemma resolution has
    permanently closed. Populated by A2-10; A2-8 ships the field so
    A2-10 requires no save migration.
    """

    telegraphed: set[str] = field(default_factory=set)
    telegraph_cursor: dict[str, int] = field(default_factory=dict)
    resolved: dict[str, str] = field(default_factory=dict)
    closed_lenses: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict.

        Sets are emitted as sorted lists so the save file is stable
        (byte-identical for the same in-memory state); the loader
        rehydrates them as sets.
        """
        return {
            "telegraphed": sorted(self.telegraphed),
            "telegraph_cursor": dict(self.telegraph_cursor),
            "resolved": dict(self.resolved),
            "closed_lenses": sorted(self.closed_lenses),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "DilemmaRuntimeState":
        """Restore a DilemmaRuntimeState from save data.

        Missing keys, ``None``, and non-dict inputs all default to the
        empty state — per CLAUDE.md's save-migration rule, legacy saves
        without ``dilemma_state`` must load cleanly.
        """
        if not isinstance(data, dict):
            return cls()
        telegraphed_raw = data.get("telegraphed", [])
        telegraph_cursor_raw = data.get("telegraph_cursor", {})
        resolved_raw = data.get("resolved", {})
        closed_lenses_raw = data.get("closed_lenses", [])
        return cls(
            telegraphed=set(telegraphed_raw) if isinstance(telegraphed_raw, list) else set(),
            telegraph_cursor=(
                dict(telegraph_cursor_raw) if isinstance(telegraph_cursor_raw, dict) else {}
            ),
            resolved=dict(resolved_raw) if isinstance(resolved_raw, dict) else {},
            closed_lenses=(
                set(closed_lenses_raw) if isinstance(closed_lenses_raw, list) else set()
            ),
        )


@dataclass
class DilemmaCheckResult:
    """Typed classification of every loaded dilemma after a check.

    Kept as a small dataclass rather than a ``dict[str, Any]`` so
    ``game.py`` can iterate the fields with static typing and no key
    typos.
    """

    newly_telegraphed: list[str] = field(default_factory=list)
    re_telegraphed: list[str] = field(default_factory=list)
    newly_collided: list[str] = field(default_factory=list)


def _poles_at_or_above(dilemma: Dilemma, investment: Any, threshold: int) -> int:
    """Count how many of ``dilemma.poles`` are individually ≥ threshold."""
    return sum(1 for pole in dilemma.poles if investment.is_at_or_above(pole, threshold))


def check_collision(dilemma: Dilemma, investment: Any) -> bool:
    """Return True iff enough poles have individually crossed collision.

    A collision fires when at least ``dilemma.collision_requires`` of
    ``dilemma.poles`` are individually at or above
    ``dilemma.collision_threshold``. Investment is *never* summed
    across poles — a 200/0 split is one pole, not a collision.

    Pure predicate; no side effects. Follows the
    :func:`spacegame.models.capstone.should_fire` shape.
    """
    return (
        _poles_at_or_above(dilemma, investment, dilemma.collision_threshold)
        >= dilemma.collision_requires
    )


def check_telegraph(dilemma: Dilemma, investment: Any) -> bool:
    """Return True iff enough poles have individually crossed telegraph.

    Mirrors :func:`check_collision` at the lower ``telegraph_threshold``
    so the telegraph strictly leads the collision (invariant: any
    fixture with ``telegraph_threshold < collision_threshold`` cannot
    collide without also telegraphing first).
    """
    return (
        _poles_at_or_above(dilemma, investment, dilemma.telegraph_threshold)
        >= dilemma.collision_requires
    )


def build_investment_snapshot(dilemma: Dilemma, player: Any) -> dict[str, int]:
    """Return the immutable per-pole snapshot the resolution view needs.

    Model-layer helper so the engine can hand
    :class:`spacegame.views.dilemma_resolution_view.DilemmaResolutionView`
    a plain ``dict[str, int]`` without importing the investment
    substrate directly (the compliance scanner for that substrate
    forbids the engine and views from touching its tokens).

    Args:
        dilemma: The collided dilemma. Only its ``poles`` are read.
        player: Anything exposing ``lens_investment.get_investment(pole)``.

    Returns:
        A fresh dict mapping each pole id to its current investment
        value. Missing poles read as 0 via ``get_investment``.
    """
    return {pole: player.lens_investment.get_investment(pole) for pole in dilemma.poles}


def check_dilemmas(player: Any, dilemmas: dict[str, Dilemma]) -> DilemmaCheckResult:
    """Classify every loaded dilemma against a player's current state.

    Reads ``player.lens_investment`` and ``player.dilemma_state``
    inside the model layer so callers under ``spacegame/engine/`` and
    ``spacegame/views/`` never touch the forbidden tokens.

    Iteration order matches ``dilemmas`` insertion order. Dilemmas
    already in ``player.dilemma_state.resolved`` are skipped entirely
    — a resolved dilemma cannot re-fire regardless of subsequent
    investment.

    Args:
        player: Any object exposing ``lens_investment`` (with
            :meth:`~spacegame.models.lens_investment.LensInvestment.is_at_or_above`)
            and ``dilemma_state`` (a :class:`DilemmaRuntimeState`).
        dilemmas: The registry (typically ``DataLoader.dilemmas``).

    Returns:
        :class:`DilemmaCheckResult` with each dilemma id filed into
        exactly one of ``newly_telegraphed`` / ``re_telegraphed``
        (mutually exclusive), plus a possible parallel filing into
        ``newly_collided`` when a first-ever check jumps past both
        thresholds in one step.
    """
    result = DilemmaCheckResult()
    investment = player.lens_investment
    runtime: DilemmaRuntimeState = player.dilemma_state
    for dilemma_id, dilemma in dilemmas.items():
        if dilemma_id in runtime.resolved:
            continue

        telegraphed_now = check_telegraph(dilemma, investment)
        if telegraphed_now:
            if dilemma_id in runtime.telegraphed:
                result.re_telegraphed.append(dilemma_id)
            else:
                result.newly_telegraphed.append(dilemma_id)

        if check_collision(dilemma, investment):
            result.newly_collided.append(dilemma_id)

    return result
