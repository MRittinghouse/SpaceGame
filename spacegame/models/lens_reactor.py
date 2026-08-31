"""LensReactor -- oblique-readout dispatcher for lens-aware NPC lines (A2-4A).

Given a player, a context string, and a caller-supplied default dict,
``choose_variant`` returns one authored NPC line from the loaded pool whose
lens exceeds its threshold for that player. Returns the caller's default when
no lens qualifies.

Design decisions (locked in A2-4A planning; see ROADMAP.md for rationale):

- Resolution logic lives here, not on LensInvestment, so the state store stays
  a pure accrual store. Resolution policy may change per-context in future sprints;
  keeping it out of the state model avoids a signature-breaking change.
- Dominant-lens rule: highest-threshold match per lens, then highest threshold
  across lenses wins overall. Ties broken alphabetically by lens_id (ascending)
  so 'community' beats 'vengeance' on equal thresholds. This is intentional and
  documented here; changing it changes authored content semantics.
- Seeding: random.Random(hash((game_day, context, player.name))) -- a local
  Random instance so global random state is never mutated. This mirrors the
  deterministic-market-price pattern used elsewhere in the project.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from spacegame.models.lens_reaction import LensReaction

if TYPE_CHECKING:
    from spacegame.models.player import Player


class LensReactor:
    """Selects one authored NPC line for a given player and context."""

    def __init__(self, pool: list[LensReaction]) -> None:
        """Initialize the reactor with a pre-loaded reaction pool.

        Args:
            pool: All LensReaction records from the DataLoader. The pool is
                stored as-is; filtering happens per ``choose_variant`` call.
                Linear scan is appropriate; the pool is small (<=200 records).
        """
        self._pool = pool

    def choose_variant(
        self,
        player: "Player",
        context: str,
        options: dict[str, list[str]],
    ) -> str:
        """Return one authored NPC line for the player's current lens state.

        Selection algorithm:
        1. Filter pool to records matching ``context``.
        2. For each candidate record, check
           ``player.lens_investment.is_at_or_above(lens_id, threshold)``.
        3. For each qualifying lens, keep only the highest-threshold record
           (so Wealth-80 beats Wealth-40 when both fire).
        4. Among all qualifying lenses, pick the one with the highest threshold.
           Ties broken alphabetically by lens_id (ascending -- 'community'
           beats 'vengeance'). This tie-break is intentional; see module doc.
        5. Pick one line from that record's ``lines`` pool using a seeded
           ``random.Random`` so the same ``(game_day, context, player.name)``
           always resolves the same string.
        6. When no record qualifies, return ``options["default"][0]``.

        Args:
            player: The player whose ``lens_investment`` is consulted. Never
                touched directly -- only ``is_at_or_above`` is called, keeping
                the compliance invariant (views never access raw investment).
            context: The authored seam identifier (e.g.
                ``"wreckers_hall_enrollment_pitch"``).
            options: Must include key ``"default"`` with a non-empty list.
                A missing key is a caller bug (raises ``KeyError``); an empty
                list is a data bug (raises ``IndexError`` on ``[0]``).

        Returns:
            One authored string from the winning lens pool, or
            ``options["default"][0]`` when nothing qualifies.

        Raises:
            KeyError: If ``options`` does not contain ``"default"``.
        """
        best_per_lens: dict[str, LensReaction] = {}
        for record in self._pool:
            if record.context != context:
                continue
            if not player.lens_investment.is_at_or_above(record.lens_id, record.threshold):
                continue
            existing = best_per_lens.get(record.lens_id)
            if existing is None or record.threshold > existing.threshold:
                best_per_lens[record.lens_id] = record

        if not best_per_lens:
            return options["default"][0]

        # Dominant lens: highest threshold; ties broken alphabetically by lens_id.
        dominant = min(
            best_per_lens.values(),
            key=lambda r: (-r.threshold, r.lens_id),
        )

        rng = random.Random(hash((player.game_day, context, player.name)))
        return rng.choice(dominant.lines)
