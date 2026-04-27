"""RC-3: captain variant content integrity.

The variants file may be empty in RC-3 (content lands in RC-4) — these
tests assert structural correctness rather than coverage.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.captain_variant import VALID_MEETING_STATES


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


class TestVariantCoverage:
    """RC-4 ratchets: every captain must have at least a return variant.
    Future content can add post-resolution variants; the floor enforces
    that recurring rivalries don't go silent on the second meeting."""

    def test_every_captain_has_return_variant(self, dl) -> None:
        from spacegame.models.captain_variant import MEETING_STATE_RETURN

        captains_with_return = {
            cid for (cid, state) in dl.captain_variants if state == MEETING_STATE_RETURN
        }
        missing = set(dl.captains.keys()) - captains_with_return
        assert not missing, (
            f"Captains without a return variant: {sorted(missing)}. "
            "Every captain must have at least one return-meeting variant "
            "so recurring encounters acknowledge prior meetings."
        )

    def test_minimum_total_variant_count(self, dl) -> None:
        """RC-4 ships at least 17 variants (one per captain). Floor allows
        the system to grow without regression."""
        assert len(dl.captain_variants) >= 17, (
            f"Only {len(dl.captain_variants)} variants loaded, expected >= 17"
        )


class TestVariantStructure:
    def test_variants_load_into_lookup_dict(self, dl) -> None:
        """The captain_variants attribute is a dict (possibly empty)."""
        assert isinstance(dl.captain_variants, dict)

    def test_every_variant_captain_id_resolves(self, dl) -> None:
        """No variant references a non-existent captain."""
        for (captain_id, _state), variant in dl.captain_variants.items():
            assert captain_id in dl.captains, f"Variant references unknown captain '{captain_id}'"
            assert variant.captain_id == captain_id

    def test_every_variant_meeting_state_in_registry(self, dl) -> None:
        for (_captain_id, state), variant in dl.captain_variants.items():
            assert state in VALID_MEETING_STATES, f"Variant uses invalid meeting_state '{state}'"
            assert variant.meeting_state == state

    def test_every_variant_has_at_least_one_authored_field(self, dl) -> None:
        """A variant with all empty fields is dead content (would resolve
        identical to base) — likely an authoring slip."""
        for (cid, state), v in dl.captain_variants.items():
            authored = any(
                getattr(v, field).strip()
                for field in (
                    "pre_combat_hail",
                    "surrender_line",
                    "retreat_line",
                    "victory_line",
                    "defeat_line",
                )
            )
            assert authored, f"Variant ({cid}, {state}) has no authored fields"

    def test_no_duplicate_variant_keys(self, dl) -> None:
        """The lookup dict deduplicates by definition. If the source file
        had duplicates, only one survives — this is a sanity check that
        the source file produced N keys for N entries."""
        import json
        from pathlib import Path

        path = Path(__file__).parent.parent.parent / "data" / "combat" / "captain_variants.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        keys_in_file = [(v["captain_id"], v["meeting_state"]) for v in raw.get("variants", [])]
        assert len(keys_in_file) == len(set(keys_in_file)), (
            "Duplicate (captain_id, meeting_state) entries in variants file"
        )


class TestVariantWritingBible:
    """Variants must follow Writing Bible discipline (no em-dashes,
    no banned phrases)."""

    EM_DASHES = ("\u2014", "\u2013", " -- ")
    BANNED_PHRASES = ("couldn't help but", "a testament to", "could not help but")

    def _all_variant_strings(self, dl) -> list[tuple[str, str]]:
        out = []
        for (cid, state), v in dl.captain_variants.items():
            for field_name in (
                "pre_combat_hail",
                "surrender_line",
                "retreat_line",
                "victory_line",
                "defeat_line",
            ):
                text = getattr(v, field_name, "")
                if text:
                    out.append((f"variant:{cid}:{state}:{field_name}", text))
        return out

    def test_no_em_dashes(self, dl) -> None:
        offenders = []
        for loc, text in self._all_variant_strings(dl):
            for dash in self.EM_DASHES:
                if dash in text:
                    offenders.append(f"{loc}: {text[:80]!r}")
                    break
        assert not offenders, "Em-dashes in captain variants:\n  " + "\n  ".join(offenders)

    def test_no_banned_phrases(self, dl) -> None:
        offenders = []
        for loc, text in self._all_variant_strings(dl):
            text_lower = text.lower()
            for phrase in self.BANNED_PHRASES:
                if phrase in text_lower:
                    offenders.append(f"{loc}: {phrase!r}")
        assert not offenders, "Banned phrases in captain variants:\n  " + "\n  ".join(offenders)
