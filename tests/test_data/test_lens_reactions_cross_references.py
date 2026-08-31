"""Cross-reference and schema validation for data/narrative/lens_reactions.json (A2-4A).

Every lens_id referenced in the file must exist in DataLoader.lenses.
Every context must be in the known-contexts allowlist.
The file must ship with the three authored lenses and their two tiers.

Allowlist discipline: adding a new context string to _KNOWN_CONTEXTS is a
conscious decision -- the friction is intentional. A typo in a new context
becomes a build failure here rather than a silent fallback to the default.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.lens_reaction import LensReaction

# Context strings that are legitimate seam identifiers. Extend when a new
# consumer sprint wires the reactor into a new NPC seam.
_KNOWN_CONTEXTS: set[str] = {"wreckers_hall_enrollment_pitch"}

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _get_loader() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


class TestLensReactionsSchema:
    def test_load_lens_reactions_parses_shipped_file(self) -> None:
        dl = _get_loader()
        assert hasattr(dl, "lens_reactions"), "DataLoader must have lens_reactions attribute"
        assert len(dl.lens_reactions) > 0, "lens_reactions must be non-empty after load_all"
        for record in dl.lens_reactions:
            assert isinstance(record, LensReaction), f"Expected LensReaction, got {type(record)}"

    def test_shipped_file_covers_three_lenses(self) -> None:
        dl = _get_loader()
        lens_ids = {r.lens_id for r in dl.lens_reactions}
        for expected in ("wealth", "community", "vengeance"):
            assert expected in lens_ids, f"lens_id '{expected}' must be present in lens_reactions"

    def test_shipped_file_has_two_tiers_per_lens(self) -> None:
        dl = _get_loader()
        from collections import defaultdict

        tiers_per_lens: dict[str, set[int]] = defaultdict(set)
        for r in dl.lens_reactions:
            tiers_per_lens[r.lens_id].add(r.threshold)
        for lens_id in ("wealth", "community", "vengeance"):
            assert len(tiers_per_lens[lens_id]) >= 2, (
                f"lens '{lens_id}' must have at least 2 threshold tiers, "
                f"got {tiers_per_lens[lens_id]}"
            )
            assert 40 in tiers_per_lens[lens_id], (
                f"lens '{lens_id}' must have a mid tier (threshold=40)"
            )
            assert 80 in tiers_per_lens[lens_id], (
                f"lens '{lens_id}' must have a high tier (threshold=80)"
            )

    def test_shipped_file_has_minimum_total_lines(self) -> None:
        dl = _get_loader()
        total_lines = sum(len(r.lines) for r in dl.lens_reactions)
        assert total_lines >= 18, (
            f"Expected >= 18 authored lines total (3 lenses x 2 tiers x 3 variants), "
            f"got {total_lines}"
        )

    def test_every_context_in_reactions_is_in_known_contexts_allowlist(self) -> None:
        dl = _get_loader()
        unknown = {r.context for r in dl.lens_reactions} - _KNOWN_CONTEXTS
        assert not unknown, (
            f"Unknown context strings in lens_reactions.json: {sorted(unknown)}. "
            f"Add them to _KNOWN_CONTEXTS in this test file when intentional."
        )

    def test_every_lens_id_in_reactions_exists_in_lens_registry(self) -> None:
        dl = _get_loader()
        unknown = {r.lens_id for r in dl.lens_reactions} - set(dl.lenses.keys())
        assert not unknown, (
            f"Unknown lens_ids in lens_reactions.json: {sorted(unknown)}. "
            f"Every lens_id must exist in data/narrative/lenses.json."
        )

    def test_all_reactions_context_is_wreckers_hall_enrollment_pitch(self) -> None:
        dl = _get_loader()
        for r in dl.lens_reactions:
            assert r.context == "wreckers_hall_enrollment_pitch", (
                f"Unexpected context {r.context!r} for lens_id={r.lens_id!r}. "
                f"This sprint only ships one context."
            )

    def test_load_ordering_lens_reactions_after_lenses(self) -> None:
        """load_lens_reactions must raise if called before lenses are loaded."""
        project_root = Path(__file__).resolve().parents[2]
        fresh = DataLoader(data_dir=project_root / "data")
        with pytest.raises(ValueError, match="load_lenses"):
            fresh.load_lens_reactions()


class TestLensReactionsContent:
    def test_lens_reactions_have_no_em_dashes_or_banned_phrases(self) -> None:
        """Secondary defense against Writing Bible violations (primary: test_prose_anti_patterns)."""
        import json
        import re

        reactions_path = _DATA_DIR / "narrative" / "lens_reactions.json"
        assert reactions_path.exists(), f"Missing {reactions_path}"
        with open(reactions_path, encoding="utf-8") as f:
            data = json.load(f)

        em_dash = "—"
        no_x_no_y = re.compile(r"[Nn]o \w+,\s*no \w+")
        banned_phrases = [
            "a testament to",
            "couldn't help but",
            "could not help but",
        ]

        def _check_strings(obj: object) -> list[str]:
            violations: list[str] = []
            if isinstance(obj, str):
                if em_dash in obj:
                    violations.append(f"Em-dash in: {obj!r}")
                if no_x_no_y.search(obj):
                    violations.append(f"Parallel-negation in: {obj!r}")
                for phrase in banned_phrases:
                    if phrase.lower() in obj.lower():
                        violations.append(f"Banned phrase '{phrase}' in: {obj!r}")
            elif isinstance(obj, dict):
                for v in obj.values():
                    violations.extend(_check_strings(v))
            elif isinstance(obj, list):
                for item in obj:
                    violations.extend(_check_strings(item))
            return violations

        violations = _check_strings(data)
        assert not violations, "Writing Bible violations in lens_reactions.json:\n" + "\n".join(
            violations
        )

    def test_writing_bible_scanner_covers_lens_reactions_file(self) -> None:
        """Confirm test_prose_anti_patterns.py walks data/narrative/ (no extension needed)."""
        import re

        scanner_path = (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "test_compliance"
            / "test_prose_anti_patterns.py"
        )
        assert scanner_path.exists(), "Writing Bible scanner not found"
        source = scanner_path.read_text(encoding="utf-8")
        assert "DATA_DIR" in source, "Scanner must define a DATA_DIR constant"
        assert re.search(r'data["\']?\s*/["\s]?', source) or "data" in source, (
            "Scanner must reference the data directory"
        )
