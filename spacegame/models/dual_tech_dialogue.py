"""
First-use cinematic reveal scenes for dual techs.

When a dual tech is activated for the first time in any combat, the
engine fires the reveal — a short scripted moment that introduces the
coordinated ability through character voice before the mechanical
effect resolves. See ``requirements/combat_balance_design.md §5.5`` for
design intent and ``requirements/character_voices.md`` for voice
references used while writing these.

Flow:
  1. Dual tech activates (see ``activate_*`` helpers in ``dual_tech.py``)
  2. Engine calls ``check_and_mark_reveal(dialogue_flags, tech_id)``
  3. If not yet revealed: the function marks the flag True and returns
     the scene; engine appends each line as a log entry, then resolves
     the tech normally
  4. All subsequent activations skip the scene (flag already True)

The dialogue data lives here as structured text. If/when a richer
dialogue system wants to own dual-tech reveals (branching, portraits,
etc.), this module can be retired in favor of that integration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DualTechRevealLine:
    """One beat of a reveal scene."""

    speaker: str         # Character name, e.g. "Elena", "Marcus", or "" for stage direction
    text: str            # Spoken line or stage direction


@dataclass(frozen=True)
class DualTechReveal:
    """A one-shot reveal scene for a dual tech."""

    tech_id: str
    lines: tuple[DualTechRevealLine, ...]
    announcement: str   # Short gameplay confirmation, e.g. "Fire at Will unlocked."

    def to_log_entries(self) -> list[str]:
        """Flatten the scene into log-friendly strings for the combat log.

        Each spoken line is rendered as ``Speaker: text``. Stage
        directions (empty speaker) are rendered as-is. The announcement
        closes the scene.
        """
        out: list[str] = []
        for line in self.lines:
            if line.speaker:
                out.append(f"{line.speaker}: {line.text}")
            else:
                out.append(line.text)
        out.append(self.announcement)
        return out


# ============================================================================
# Scenes — see §5.5 of the balance design doc.
# Voices per requirements/character_voices.md.
# ============================================================================


def _line(speaker: str, text: str) -> DualTechRevealLine:
    return DualTechRevealLine(speaker=speaker, text=text)


DUAL_TECH_REVEALS: dict[str, DualTechReveal] = {
    # Elena + Marcus — Fire at Will
    "fire_at_will": DualTechReveal(
        tech_id="fire_at_will",
        lines=(
            _line("Elena", "Captain, I can coordinate every mount if Marcus opens the interlocks."),
            _line("Marcus", "Opening them. Call your shots."),
        ),
        announcement="*Fire at Will is now available.*",
    ),

    # Elena + Tomas — Daring Gambit
    "daring_gambit": DualTechReveal(
        tech_id="daring_gambit",
        lines=(
            _line("Elena", (
                "If they commit to that firing angle, there's a window at "
                "thirty-eight degrees low. It closes in four seconds."
            )),
            _line("Tomas", "Four seconds is plenty. Count me in."),
        ),
        announcement="*Daring Gambit is now available.*",
    ),

    # Elena + Priya — Total Commitment
    "total_commitment": DualTechReveal(
        tech_id="total_commitment",
        lines=(
            _line("Priya", (
                "Captain, I can reroute the next three hull impacts through "
                "the structural matrix. The damage becomes reinforcement."
            )),
            _line("Elena", "Tell me when. I'll hold the heading."),
            _line("Priya", "Now, Captain. And thank you."),
        ),
        announcement="*Total Commitment is now available.*",
    ),

    # Marcus + Priya — Focused Barrage
    "focused_barrage": DualTechReveal(
        tech_id="focused_barrage",
        lines=(
            _line("Marcus", (
                "Doc. The starboard mount. I can pop the safeties if you can "
                "handle the capacitor."
            )),
            _line("Priya", (
                "Load tolerance is rated for 1.8 times nominal. I can push "
                "2.1 for approximately one discharge. Fascinating."
            )),
            _line("Marcus", "Do it."),
        ),
        announcement="*Focused Barrage is now available.*",
    ),

    # Marcus + Tomas — Gun Run
    "gun_run": DualTechReveal(
        tech_id="gun_run",
        lines=(
            _line("Tomas", (
                "If you keep the guns hot, I can walk us through the whole line."
            )),
            _line("Marcus", "Call the pass. I'll keep them firing."),
        ),
        announcement="*Gun Run is now available.*",
    ),

    # Priya + Tomas — Power Drift
    "power_drift": DualTechReveal(
        tech_id="power_drift",
        lines=(
            _line("Priya", (
                "Captain, I can release excess reactor pressure directly into "
                "the capacitor bank. The timing would require very precise "
                "flight maneuvers."
            )),
            _line("Tomas", "Doc. I fly the frontier. Precise is the only thing I do."),
            _line("Priya", "Then we are fortunate."),
        ),
        announcement="*Power Drift is now available.*",
    ),

    # Triad — Crew Sync
    "crew_sync": DualTechReveal(
        tech_id="crew_sync",
        lines=(
            _line("", "Elena looks at each of them."),
            _line("", (
                "Marcus checks his suit seals. Priya closes her console. "
                "Tomas's hands settle on the flight controls."
            )),
            _line("", "Nobody speaks."),
            _line("", (
                "The ship answers first — reactor resonant, every system "
                "aligned with every other."
            )),
            _line("Elena", "Together."),
        ),
        announcement="*Crew Sync is now available.*",
    ),
}


# ============================================================================
# Persistence helper
# ============================================================================


def reveal_flag_key(tech_id: str) -> str:
    """The ``dialogue_flags`` key used to record that a tech has been revealed."""
    return f"dual_tech_{tech_id}_revealed"


def check_and_mark_reveal(
    dialogue_flags: dict[str, bool],
    tech_id: str,
) -> DualTechReveal | None:
    """Return the reveal scene if this is the first activation; else None.

    Side effect: on first hit, marks the dialogue flag so subsequent
    activations skip the scene.

    Args:
        dialogue_flags: The player's dialogue-flags dict (mutated in place).
        tech_id: The dual tech being activated.

    Returns:
        The DualTechReveal for this tech if unseen, else None.
    """
    reveal = DUAL_TECH_REVEALS.get(tech_id)
    if reveal is None:
        return None
    key = reveal_flag_key(tech_id)
    if dialogue_flags.get(key):
        return None
    dialogue_flags[key] = True
    return reveal
