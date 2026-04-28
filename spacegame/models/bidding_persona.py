"""SA-B2: AI bidder personas — value functions, behavior axes, archetypes.

A persona is a deterministic decider attached to an auction session. At
session load time it computes its effective value for each lot and a
ceiling above which it will not bid. During a round it decides when (if
ever) to counter-bid based on its four behavior axes.

All randomness is seeded from session and persona ids so SA-B2 tests can
reproduce timing decisions exactly. See ``requirements/sa_bidding_design.md``
§4 for the design rationale and the worked specs that drive the unit
tests.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from typing import Any, Optional

from spacegame.models.bidding_lot import AuctionLot

# Persona archetype ids (stable across saves).
PERSONA_PRENTISS = "aldous_prentiss"
PERSONA_KADE = "yuna_kade"
PERSONA_SALKO = "fenn_salko"
PERSONA_STELLARIS_SPECULATOR = "stellaris_speculator"
PERSONA_REACH_FLAVOR = "reach_buyer"

NAMED_RIVAL_IDS: frozenset[str] = frozenset({PERSONA_PRENTISS, PERSONA_KADE, PERSONA_SALKO})

# Rival display names — short, no honorifics, used in the rival panel
# and journal entry substitutions.
RIVAL_DISPLAY_NAMES: dict[str, str] = {
    PERSONA_PRENTISS: "Prentiss",
    PERSONA_KADE: "Kade",
    PERSONA_SALKO: "Salko",
}

# Salko's player-target escalation tracks lot categories the player has
# bid on across the most recent N sessions (design doc §4.5 + §10.9).
# Locked in SA-B2's plan as 3; tunable in SA-B6 post-playtest.
SALKO_ESCALATION_WINDOW = 3
SALKO_ESCALATION_BONUS = 0.70

# Counter-bid timing buckets per design doc §4.3. Aggression-axis maps
# the persona into one of three response windows.
AGGRESSION_HIGH_THRESHOLD = 0.7
AGGRESSION_MID_THRESHOLD = 0.4
AGGRESSION_HIGH_DELAY_MAX = 1.0  # Within 1 s of last bid.
AGGRESSION_MID_DELAY_MIN = 3.0
AGGRESSION_MID_DELAY_MAX = 7.0

# Snipe-window response: only personas with snipe_resistance >= 0.5 may
# counter a snipe-window bid. Locked at decision §11.3.
SNIPE_RESPONSE_THRESHOLD = 0.5


def _seeded_drift(session_id: str, persona_id: str) -> float:
    """Deterministic per-session drift in the range [-0.05, +0.05].

    Hashed from ``f"{session_id}_{persona_id}"`` per design doc §4.1 so
    the same session/persona combination always yields the same drift.
    Avoids the standard library ``random`` module so we don't perturb
    the global RNG state when computing values.
    """
    digest = hashlib.sha256(f"{session_id}_{persona_id}".encode("utf-8")).digest()
    # Take 8 bytes, interpret as unsigned 64-bit, normalize to [0, 1).
    raw: int = struct.unpack(">Q", digest[:8])[0]
    unit: float = raw / float(1 << 64)
    return -0.05 + unit * 0.10  # Maps [0, 1) -> [-0.05, +0.05).


def _seeded_unit(*tokens: Any) -> float:
    """Deterministic per-(token-tuple) float in [0, 1)."""
    key = "|".join(str(t) for t in tokens)
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    raw: int = struct.unpack(">Q", digest[:8])[0]
    return raw / float(1 << 64)


@dataclass(frozen=True)
class AIBidderPersona:
    """One AI bidder's hidden value function and behavior parameters.

    Frozen because a persona's parameters do not change mid-session;
    per-session drift is recomputed deterministically from
    ``(session_id, persona_id)``. Salko-style player-target escalation
    is applied at compute time using the player's recent bid categories
    (passed in by the caller, not stored on the persona).

    Attributes:
        persona_id: Stable id (one of ``PERSONA_*``). Drives the seeded
            drift hash; do not change between sessions.
        display_name: Short label used in the rival panel and journal
            substitutions (e.g. ``"Prentiss"``).
        desire_multipliers: Map of ``LOT_CATEGORY_*`` -> float. A
            category absent from the dict means ``0.0`` desire — the
            persona sits out lots in that category.
        ceiling_ratio: Multiplier applied to the persona's effective
            value to derive their hard ceiling (1.10 = pays 10% over
            appraisal).
        aggression: Behavior axis 0..1 (see design doc §4.2).
        patience: Behavior axis 0..1.
        signal_discipline: Behavior axis 0..1.
        snipe_resistance: Behavior axis 0..1.
        vs_player_ceiling_ratio: Salko-only override that swaps the
            ceiling ratio when the player is in the same session
            (default: ``None`` = no override).
        player_target_escalation_categories: Salko-only set of
            categories that receive the +0.70 escalation when the
            player has bid on them in recent sessions. Default empty.
        is_named_rival: True for Prentiss/Kade/Salko; False for the
            two procedural archetypes.
    """

    persona_id: str
    display_name: str
    desire_multipliers: dict[str, float] = field(default_factory=dict)
    ceiling_ratio: float = 1.0
    aggression: float = 0.5
    patience: float = 0.5
    signal_discipline: float = 0.5
    snipe_resistance: float = 0.5
    vs_player_ceiling_ratio: Optional[float] = None
    player_target_escalation_categories: frozenset[str] = field(default_factory=frozenset)
    is_named_rival: bool = False

    # ------------------------------------------------------------------
    # Value function
    # ------------------------------------------------------------------

    def desire_for(
        self,
        category: str,
        recent_player_categories: tuple[str, ...] = (),
    ) -> float:
        """Return the persona's desire multiplier for a given category.

        Salko's player-target escalation adds ``SALKO_ESCALATION_BONUS``
        if ``category`` is in ``player_target_escalation_categories`` and
        the player bid on that category in the recent window.

        Categories absent from ``desire_multipliers`` return 0.0, which
        causes :meth:`compute_effective_value` to return 0 and the
        persona to sit out the lot at :meth:`compute_ceiling`.
        """
        base = self.desire_multipliers.get(category, 0.0)
        if (
            category in self.player_target_escalation_categories
            and category in recent_player_categories
        ):
            base += SALKO_ESCALATION_BONUS
        return base

    def compute_effective_value(
        self,
        lot: AuctionLot,
        session_id: str,
        recent_player_categories: tuple[str, ...] = (),
    ) -> int:
        """Compute the persona's effective value for ``lot`` per design doc §4.1.

        ``effective_value = base_appraisal * desire * (1 + drift)``.

        Returns 0 for lots the persona has no interest in (desire 0.0).
        Drift is deterministic for ``(session_id, persona_id)``.
        """
        desire = self.desire_for(lot.category, recent_player_categories)
        if desire <= 0.0:
            return 0
        drift = _seeded_drift(session_id, self.persona_id)
        raw = lot.base_appraisal * desire * (1.0 + drift)
        return round(raw)

    def compute_ceiling(
        self,
        lot: AuctionLot,
        session_id: str,
        *,
        vs_player: bool = False,
        recent_player_categories: tuple[str, ...] = (),
    ) -> int:
        """Compute the persona's hard ceiling for ``lot``.

        If ``vs_player`` is True and the persona has a
        ``vs_player_ceiling_ratio`` override (Salko), that ratio is used
        instead of the default ceiling ratio. Returns 0 for lots the
        persona will not bid on.
        """
        ev = self.compute_effective_value(
            lot, session_id, recent_player_categories=recent_player_categories
        )
        if ev <= 0:
            return 0
        ratio = self.ceiling_ratio
        if vs_player and self.vs_player_ceiling_ratio is not None:
            ratio = self.vs_player_ceiling_ratio
        return round(ev * ratio)

    def session_signal_drift(self, session_id: str) -> float:
        """Expose the per-session drift for Sable's ceiling-jitter formula."""
        return _seeded_drift(session_id, self.persona_id)

    # ------------------------------------------------------------------
    # Counter-bid timing
    # ------------------------------------------------------------------

    def counter_bid_delay(
        self,
        session_id: str,
        round_number: int,
        round_duration_seconds: float,
        *,
        speed_multiplier: float = 1.0,
    ) -> float:
        """Return the seconds-after-last-bid this persona will counter.

        Maps the persona's ``aggression`` to one of three buckets per
        design doc §4.3. ``speed_multiplier`` < 1.0 (asap mode)
        compresses all timings proportionally; the result is clamped to
        a minimum 0.5 s spacing to keep AI activity readable.

        Determinism: jitter within each bucket is hashed from
        ``(session_id, persona_id, round_number)`` so tests can
        reproduce a given outcome.
        """
        seed_unit = _seeded_unit(session_id, self.persona_id, round_number)
        if self.aggression >= AGGRESSION_HIGH_THRESHOLD:
            base = seed_unit * AGGRESSION_HIGH_DELAY_MAX
        elif self.aggression >= AGGRESSION_MID_THRESHOLD:
            span = AGGRESSION_MID_DELAY_MAX - AGGRESSION_MID_DELAY_MIN
            base = AGGRESSION_MID_DELAY_MIN + seed_unit * span
        else:
            # Final 40% of the round.
            offset_into_window = seed_unit * (round_duration_seconds * 0.4)
            base = round_duration_seconds * 0.6 + offset_into_window
        compressed = base * speed_multiplier
        return max(0.5, compressed)

    def will_counter_snipe(self) -> bool:
        """True if this persona ever counters a snipe-window bid."""
        return self.snipe_resistance >= SNIPE_RESPONSE_THRESHOLD


# ---------------------------------------------------------------------------
# Archetype factories (design doc §4.5 worked specs)
# ---------------------------------------------------------------------------


def make_prentiss() -> AIBidderPersona:
    """Aldous Prentiss — heritage collector. Antiquities, measured cadence."""
    return AIBidderPersona(
        persona_id=PERSONA_PRENTISS,
        display_name=RIVAL_DISPLAY_NAMES[PERSONA_PRENTISS],
        desire_multipliers={
            "antiquity": 1.40,
            "faction_commodity": 0.70,
            "module": 0.80,
            "derelict_rights": 0.90,
            "contraband": 0.20,
            "rare_upgrade": 0.60,
        },
        ceiling_ratio=1.10,
        aggression=0.30,
        patience=0.80,
        signal_discipline=0.90,
        snipe_resistance=0.40,
        is_named_rival=True,
    )


def make_kade() -> AIBidderPersona:
    """Yuna Kade — Commerce Guild commissioner. Bids only the approved list."""
    return AIBidderPersona(
        persona_id=PERSONA_KADE,
        display_name=RIVAL_DISPLAY_NAMES[PERSONA_KADE],
        desire_multipliers={
            "faction_commodity": 1.00,
            "module": 0.50,
        },
        ceiling_ratio=1.00,
        aggression=0.70,
        patience=0.50,
        signal_discipline=0.95,
        snipe_resistance=0.80,
        is_named_rival=True,
    )


def make_salko() -> AIBidderPersona:
    """Fenn Salko — cold-grudge rival. Escalates on player-target categories."""
    return AIBidderPersona(
        persona_id=PERSONA_SALKO,
        display_name=RIVAL_DISPLAY_NAMES[PERSONA_SALKO],
        desire_multipliers={
            "module": 0.60,
            "antiquity": 0.60,
            "faction_commodity": 0.60,
            "rare_upgrade": 0.60,
            "derelict_rights": 0.60,
            "contraband": 0.60,
            "restricted_weapon": 0.60,
            "salvage_lot": 0.60,
        },
        ceiling_ratio=0.90,
        aggression=0.60,
        patience=0.90,
        signal_discipline=0.85,
        snipe_resistance=1.00,
        vs_player_ceiling_ratio=1.15,
        player_target_escalation_categories=frozenset(
            {
                "module",
                "antiquity",
                "faction_commodity",
                "rare_upgrade",
                "derelict_rights",
                "contraband",
                "restricted_weapon",
                "salvage_lot",
            }
        ),
        is_named_rival=True,
    )


def make_stellaris_speculator(
    elevated_category: str,
    instance_index: int = 1,
) -> AIBidderPersona:
    """Stellaris speculator — fills the ambient room.

    ``elevated_category`` is bumped to 1.20; the rest of the pool stays
    at the design-doc baseline. ``instance_index`` lets a session host
    multiple speculators with deterministic per-instance drift.
    """
    multipliers: dict[str, float] = {
        "module": 0.8,
        "antiquity": 0.9,
        "faction_commodity": 0.7,
        "rare_upgrade": 0.8,
        "derelict_rights": 0.5,
    }
    multipliers[elevated_category] = 1.20
    return AIBidderPersona(
        persona_id=f"{PERSONA_STELLARIS_SPECULATOR}_{instance_index}",
        display_name=f"Speculator {instance_index}",
        desire_multipliers=multipliers,
        ceiling_ratio=0.85,
        aggression=0.50,
        patience=0.40,
        signal_discipline=0.50,
        snipe_resistance=0.30,
        is_named_rival=False,
    )


def make_reach_flavor(instance_index: int = 1) -> AIBidderPersona:
    """Reach buyer — Crimson Reach ambient persona."""
    return AIBidderPersona(
        persona_id=f"{PERSONA_REACH_FLAVOR}_{instance_index}",
        display_name=f"Reach Buyer {instance_index}",
        desire_multipliers={
            "contraband": 1.20,
            "restricted_weapon": 1.10,
            "salvage_lot": 0.90,
            "module": 0.50,
            "antiquity": 0.50,
            "faction_commodity": 0.50,
            "rare_upgrade": 0.50,
            "derelict_rights": 0.50,
        },
        ceiling_ratio=0.90,
        aggression=0.80,
        patience=0.30,
        signal_discipline=0.30,
        snipe_resistance=0.60,
        is_named_rival=False,
    )


__all__ = [
    "AGGRESSION_HIGH_DELAY_MAX",
    "AGGRESSION_HIGH_THRESHOLD",
    "AGGRESSION_MID_DELAY_MAX",
    "AGGRESSION_MID_DELAY_MIN",
    "AGGRESSION_MID_THRESHOLD",
    "NAMED_RIVAL_IDS",
    "PERSONA_KADE",
    "PERSONA_PRENTISS",
    "PERSONA_REACH_FLAVOR",
    "PERSONA_SALKO",
    "PERSONA_STELLARIS_SPECULATOR",
    "RIVAL_DISPLAY_NAMES",
    "SALKO_ESCALATION_BONUS",
    "SALKO_ESCALATION_WINDOW",
    "SNIPE_RESPONSE_THRESHOLD",
    "AIBidderPersona",
    "make_kade",
    "make_prentiss",
    "make_reach_flavor",
    "make_salko",
    "make_stellaris_speculator",
]
