"""NV-1 audit: scan dialogues.json for skill-gated responses.

Walks ``data/dialogue/dialogues.json`` and identifies three categories of
skill-related responses:

  1. Explicit skill checks — responses with a ``skill_check`` field.
  2. Knowledge-flag responses — responses whose ``required_flags`` reference
     a knowledge flag (``knows_*``, ``spotted_*``, ``recognized_*``, etc.)
     that was set earlier by a skill-adjacent choice.
  3. Orphan bracket-prefix responses — responses whose text starts with a
     skill tag like ``[Perception]`` but lack a corresponding ``skill_check``
     structure. These are data-integrity flags.

Emits:
  - ``requirements/nv_audit_findings.md`` — canonical readable catalog,
    grouped by category then dialogue, with a grading table per entry.
  - ``requirements/nv_audit.csv`` — machine-readable companion.
  - Summary stats printed to stdout.

Usage:
    python -m tools.nv_audit

This produces audit data only. Grading happens in a subsequent manual pass
by editing the markdown findings doc in place.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIALOGUES_PATH = PROJECT_ROOT / "data" / "dialogue" / "dialogues.json"
FINDINGS_PATH = PROJECT_ROOT / "requirements" / "nv_audit_findings.md"
CSV_PATH = PROJECT_ROOT / "requirements" / "nv_audit.csv"

# Flag name prefixes treated as knowledge-derived (skill-adjacent gating).
KNOWLEDGE_FLAG_PREFIXES = (
    "knows_",
    "spotted_",
    "recognized_",
    "understood_",
    "deduced_",
    "noticed_",
    "realized_",
    "identified_",
    "caught_",
    "saw_",
    "detected_",
    "figured_",
)

# Skill tag prefixes for orphan-detection (responses with skill-like bracket
# prefix but no skill_check field). Mixed case because both exist in the wild.
SKILL_TAG_PREFIXES = (
    "[Persuasion",
    "[Intimidation",
    "[Perception",
    "[Observation",
    "[Deception",
    "[Technical",
    "[Piloting",
    "[Leadership",
    "[PERSUASION",
    "[INTIMIDATION",
    "[PERCEPTION",
    "[OBSERVATION",
    "[DECEPTION",
    "[TECHNICAL",
    "[PILOTING",
    "[LEADERSHIP",
)

# Known skill identifiers (values that skill_check.skill typically holds).
KNOWN_SKILLS = {
    "persuasion",
    "intimidation",
    "perception",
    "observation",
    "deception",
    "technical",
    "piloting",
    "leadership",
}


@dataclass
class AuditEntry:
    """One skill-gated response identified by the audit."""

    dialogue_id: str
    node_id: str
    response_index: int
    text: str
    category: str  # "explicit" | "knowledge" | "orphan"
    inferred_skill: str  # lowercase or "unknown"
    inferred_difficulty: Optional[int]
    required_flags: list[str] = field(default_factory=list)
    set_flag: Optional[str] = None
    set_flag_source: Optional[str] = None  # for knowledge: the setter location
    word_count: int = 0
    has_bracket_prefix: bool = False
    proposed_grade: str = ""  # blank until manual grading
    notes: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_bracket_prefix(text: str) -> str:
    """Return response body minus a leading ``[...]`` tag, if present."""
    if not text.startswith("["):
        return text
    close = text.find("]")
    if close < 0:
        return text
    return text[close + 1 :].strip()


def _infer_skill_from_prefix(text: str) -> str:
    """Guess skill from a bracket prefix like ``[Perception 2]``."""
    if not text.startswith("["):
        return "unknown"
    close = text.find("]")
    if close < 0:
        return "unknown"
    inner = text[1:close].strip()
    # Drop trailing difficulty number if present
    parts = inner.split()
    if parts:
        return parts[0].lower()
    return "unknown"


def _infer_skill_from_flag_name(flag: str) -> str:
    """Best-effort skill inference from a knowledge flag name.

    Returns ``unknown`` when heuristics can't decide. The audit flags these
    for manual skill assignment during grading.
    """
    low = flag.lower()
    # Specific content-based hints
    if "skim" in low or "watch" in low or "tap" in low:
        return "perception"
    if "lie" in low or "bluff" in low or "deception" in low:
        return "deception"
    if "persuad" in low or "convince" in low:
        return "persuasion"
    if "intimidat" in low or "threat" in low:
        return "intimidation"
    if "observ" in low or "notice" in low:
        return "observation"
    if "tech" in low or "engineer" in low:
        return "technical"
    return "unknown"


def _is_knowledge_flag(flag: str) -> bool:
    return any(flag.startswith(p) for p in KNOWLEDGE_FLAG_PREFIXES)


# ---------------------------------------------------------------------------
# Core audit
# ---------------------------------------------------------------------------


def audit_dialogues(dialogues_path: Path) -> list[AuditEntry]:
    """Walk every dialogue and collect skill-related responses."""
    with open(dialogues_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries: list[AuditEntry] = []

    # First pass: build a flag-setter index so knowledge entries can trace
    # back to the choice that granted them.
    flag_setter_index: dict[str, tuple[str, str, int, str]] = {}
    for dialogue in data.get("dialogues", []):
        dialogue_id = dialogue["id"]
        for node in dialogue.get("nodes", []):
            node_id = node["id"]
            for idx, resp in enumerate(node.get("responses", [])):
                flag = resp.get("set_flag")
                if flag:
                    flag_setter_index.setdefault(
                        flag, (dialogue_id, node_id, idx, resp.get("text", ""))
                    )
                sc = resp.get("skill_check") or {}
                sc_flag = sc.get("set_flag_on_success")
                if sc_flag:
                    flag_setter_index.setdefault(
                        sc_flag, (dialogue_id, node_id, idx, resp.get("text", ""))
                    )

    # Second pass: classify each response.
    for dialogue in data.get("dialogues", []):
        dialogue_id = dialogue["id"]
        for node in dialogue.get("nodes", []):
            node_id = node["id"]
            for idx, resp in enumerate(node.get("responses", [])):
                entry = _classify_response(
                    dialogue_id, node_id, idx, resp, flag_setter_index
                )
                if entry is not None:
                    entries.append(entry)

    return entries


def _classify_response(
    dialogue_id: str,
    node_id: str,
    response_index: int,
    response: dict,
    flag_setter_index: dict[str, tuple[str, str, int, str]],
) -> Optional[AuditEntry]:
    text = response.get("text", "") or ""
    required_flags = list(response.get("required_flags", []))
    set_flag = response.get("set_flag")
    skill_check = response.get("skill_check")
    has_bracket_prefix = text.startswith("[")

    category: Optional[str] = None
    inferred_skill = "unknown"
    inferred_difficulty: Optional[int] = None
    notes_parts: list[str] = []
    set_flag_source: Optional[str] = None

    # Category 1: explicit skill check
    if skill_check:
        category = "explicit"
        inferred_skill = str(skill_check.get("skill", "unknown")).lower()
        diff = skill_check.get("difficulty")
        if isinstance(diff, int):
            inferred_difficulty = diff

    # Category 2: knowledge-flag gated
    elif any(_is_knowledge_flag(f) for f in required_flags):
        category = "knowledge"
        knowledge_flags = [f for f in required_flags if _is_knowledge_flag(f)]
        # Try to infer skill from the knowledge flag name first, then from setter
        for kf in knowledge_flags:
            guess = _infer_skill_from_flag_name(kf)
            if guess != "unknown":
                inferred_skill = guess
                break
        # Trace back: if an unknown, check the setter response for a prefix hint
        if inferred_skill == "unknown":
            for kf in knowledge_flags:
                setter = flag_setter_index.get(kf)
                if setter:
                    sd, sn, si, stext = setter
                    if stext.startswith("["):
                        inferred_skill = _infer_skill_from_prefix(stext)
                        set_flag_source = f"{sd}::{sn}:{si}"
                        break
                    else:
                        set_flag_source = f"{sd}::{sn}:{si}"
        if inferred_skill == "unknown" and knowledge_flags:
            notes_parts.append(
                f"knowledge flag(s) {knowledge_flags} — skill needs manual assignment"
            )

    # Category 3: orphan bracket prefix
    elif any(text.startswith(p) for p in SKILL_TAG_PREFIXES):
        category = "orphan"
        inferred_skill = _infer_skill_from_prefix(text)
        notes_parts.append(
            "bracket prefix without skill_check — potential data integrity issue"
        )

    if category is None:
        return None

    word_count = len(_strip_bracket_prefix(text).split())

    return AuditEntry(
        dialogue_id=dialogue_id,
        node_id=node_id,
        response_index=response_index,
        text=text,
        category=category,
        inferred_skill=inferred_skill,
        inferred_difficulty=inferred_difficulty,
        required_flags=required_flags,
        set_flag=set_flag,
        set_flag_source=set_flag_source,
        word_count=word_count,
        has_bracket_prefix=has_bracket_prefix,
        proposed_grade="",
        notes="; ".join(notes_parts),
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def emit_csv(entries: list[AuditEntry], path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "dialogue_id",
                "node_id",
                "response_index",
                "category",
                "inferred_skill",
                "inferred_difficulty",
                "word_count",
                "has_bracket_prefix",
                "required_flags",
                "set_flag",
                "set_flag_source",
                "text",
                "proposed_grade",
                "notes",
            ]
        )
        for e in entries:
            w.writerow(
                [
                    e.dialogue_id,
                    e.node_id,
                    e.response_index,
                    e.category,
                    e.inferred_skill,
                    e.inferred_difficulty if e.inferred_difficulty is not None else "",
                    e.word_count,
                    "yes" if e.has_bracket_prefix else "no",
                    "|".join(e.required_flags),
                    e.set_flag or "",
                    e.set_flag_source or "",
                    e.text,
                    e.proposed_grade,
                    e.notes,
                ]
            )


def emit_markdown(entries: list[AuditEntry], path: Path) -> None:
    from collections import defaultdict

    # Stats
    total = len(entries)
    by_category: dict[str, int] = defaultdict(int)
    by_skill: dict[str, int] = defaultdict(int)
    for e in entries:
        by_category[e.category] += 1
        by_skill[e.inferred_skill] += 1

    lines: list[str] = []
    lines.append("# NV Audit Findings")
    lines.append("")
    lines.append(
        "**Generated by:** `python -m tools.nv_audit` — regenerate by re-running the tool."
    )
    lines.append("")
    lines.append(
        "This document catalogs every skill-gated response in "
        "`data/dialogue/dialogues.json` across three categories and provides a "
        "grading column for the NV voice rewrite pass. Grades are filled in "
        "manually after the audit tool runs."
    )
    lines.append("")
    lines.append("## Grading rubric")
    lines.append("")
    lines.append("- **D** — bare declarative; skill is a gate, response is empty")
    lines.append("- **C** — skill colors tone but no insight")
    lines.append("- **B** — skill reads the NPC / situation; response voiced accordingly")
    lines.append("- **A** — skill IS the insight; response carries what expertise reveals")
    lines.append("")
    lines.append("**Dual-voice convention (loose):**")
    lines.append("")
    lines.append(
        "- Speech skills (Persuasion, Intimidation, Deception) default to in-quote "
        "spoken dialogue."
    )
    lines.append(
        "- Observation skills (Perception, Observation) default to internal observation."
    )
    lines.append(
        "- Hybrid skills (Technical, Piloting, Leadership) choose per line."
    )
    lines.append("- Mix formats when the line serves both (observation → speech).")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total skill-gated responses: **{total}**")
    lines.append("- By category:")
    for cat in ("explicit", "knowledge", "orphan"):
        lines.append(f"  - `{cat}` — {by_category[cat]}")
    lines.append("- By inferred skill:")
    for skill, count in sorted(by_skill.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"  - `{skill}` — {count}")
    lines.append("")

    # Detail tables per category
    for cat_name, cat_label in (
        ("explicit", "Explicit skill checks"),
        ("knowledge", "Knowledge-flag gated responses"),
        ("orphan", "Orphan bracket-prefix responses (data integrity flag)"),
    ):
        cat_entries = [e for e in entries if e.category == cat_name]
        lines.append(f"## {cat_label} ({len(cat_entries)})")
        lines.append("")
        if not cat_entries:
            lines.append("_No entries in this category._")
            lines.append("")
            continue

        # Group by dialogue
        from collections import defaultdict

        by_dialogue: dict[str, list[AuditEntry]] = defaultdict(list)
        for e in cat_entries:
            by_dialogue[e.dialogue_id].append(e)

        for dialogue_id in sorted(by_dialogue.keys()):
            lines.append(f"### `{dialogue_id}`")
            lines.append("")
            lines.append(
                "| Node | Idx | Skill | Diff | Words | Grade | Text |"
            )
            lines.append("|------|-----|-------|------|-------|-------|------|")
            for e in sorted(
                by_dialogue[dialogue_id], key=lambda x: (x.node_id, x.response_index)
            ):
                safe_text = e.text.replace("|", "\\|").replace("\n", " ")
                if len(safe_text) > 120:
                    safe_text = safe_text[:117] + "..."
                diff = str(e.inferred_difficulty) if e.inferred_difficulty else ""
                grade = e.proposed_grade or "_?_"
                lines.append(
                    f"| `{e.node_id}` | {e.response_index} | {e.inferred_skill} | "
                    f"{diff} | {e.word_count} | {grade} | {safe_text} |"
                )
                if e.notes:
                    lines.append(f"|  |  |  |  |  |  | _note:_ {e.notes} |")
                if e.required_flags:
                    lines.append(
                        f"|  |  |  |  |  |  | _flags:_ {', '.join(e.required_flags)} |"
                    )
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    if not DIALOGUES_PATH.exists():
        print(f"ERROR: {DIALOGUES_PATH} not found.")
        return 1

    entries = audit_dialogues(DIALOGUES_PATH)

    emit_csv(entries, CSV_PATH)
    emit_markdown(entries, FINDINGS_PATH)

    from collections import defaultdict

    by_category: dict[str, int] = defaultdict(int)
    by_skill: dict[str, int] = defaultdict(int)
    for e in entries:
        by_category[e.category] += 1
        by_skill[e.inferred_skill] += 1

    print(f"NV audit complete. Found {len(entries)} skill-gated responses.")
    print("  By category:")
    for cat in ("explicit", "knowledge", "orphan"):
        print(f"    {cat}: {by_category[cat]}")
    print("  By inferred skill:")
    for skill, count in sorted(by_skill.items(), key=lambda x: (-x[1], x[0])):
        print(f"    {skill}: {count}")
    print(f"  Findings: {FINDINGS_PATH}")
    print(f"  CSV:      {CSV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
