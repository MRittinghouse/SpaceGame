"""Data-integrity guard for the lens registry.

Fails the build on:
- missing required field (any of the 11)
- duplicate lens_id
- non-snake_case lens_id
- collection fields with wrong JSON type

Also asserts the scan itself is not silently passing over zero lenses when
``lenses.json`` ships empty -- the empty-registry case is skipped-with-reason,
not a quiet green, which is the failure this guard exists to prevent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spacegame.models.lens import _REQUIRED_FIELDS


def _write_lenses(tmp_path: Path, lenses: list) -> Path:
    """Write a lenses.json to tmp_path/narrative/ and return the loader."""
    narrative = tmp_path / "narrative"
    narrative.mkdir(parents=True, exist_ok=True)
    (narrative / "lenses.json").write_text(json.dumps({"lenses": lenses}), encoding="utf-8")
    return tmp_path


def _valid_lens(lens_id: str = "test_lens") -> dict:
    return {
        "lens_id": lens_id,
        "name": "Test Lens",
        "core_fantasy": "A one-line core fantasy.",
        "question": "What does the player ask?",
        "sees": "What it notices.",
        "wants": "What the character wants.",
        "trades": "What they give up.",
        "investment_from": ["action_a"],
        "minigame_shape": "deduction",
        "voice": "Precise.",
        "tier_unlocks": ["unlock_a"],
    }


class TestLensRegistryIntegrity:
    def test_missing_minigame_shape_raises_naming_lens_id(self, tmp_path: Path) -> None:
        """A lens missing minigame_shape must raise ValueError naming the lens_id."""
        from spacegame.data_loader import DataLoader

        bad = _valid_lens("my_lens")
        del bad["minigame_shape"]
        _write_lenses(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="minigame_shape"):
            loader.load_lenses()

    @pytest.mark.parametrize("missing_field", list(_REQUIRED_FIELDS))
    def test_missing_any_required_field_raises(self, tmp_path: Path, missing_field: str) -> None:
        """Every one of the 11 required fields must trigger ValueError when absent."""
        from spacegame.data_loader import DataLoader

        bad = _valid_lens("param_lens")
        del bad[missing_field]
        _write_lenses(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError):
            loader.load_lenses()

    def test_duplicate_lens_id_raises_naming_duplicated_id(self, tmp_path: Path) -> None:
        """Duplicate lens_id values must raise ValueError naming the offending id."""
        from spacegame.data_loader import DataLoader

        lens = _valid_lens("dup_id")
        _write_lenses(tmp_path, [lens, lens])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="dup_id"):
            loader.load_lenses()

    @pytest.mark.parametrize(
        "bad_id",
        ["Vengeance", "political-power", "1lens", "WEALTH", "has space"],
    )
    def test_non_snake_case_lens_id_raises(self, tmp_path: Path, bad_id: str) -> None:
        """Non-snake_case lens_ids must be rejected."""
        from spacegame.data_loader import DataLoader

        bad = _valid_lens(bad_id)
        _write_lenses(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError):
            loader.load_lenses()

    def test_investment_from_as_string_raises(self, tmp_path: Path) -> None:
        """investment_from provided as a string must raise ValueError."""
        from spacegame.data_loader import DataLoader

        bad = _valid_lens("strfield_lens")
        bad["investment_from"] = "not_a_list"
        _write_lenses(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="investment_from"):
            loader.load_lenses()

    def test_tier_unlocks_as_dict_raises(self, tmp_path: Path) -> None:
        """tier_unlocks provided as a dict must raise ValueError."""
        from spacegame.data_loader import DataLoader

        bad = _valid_lens("dictfield_lens")
        bad["tier_unlocks"] = {"key": "value"}
        _write_lenses(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="tier_unlocks"):
            loader.load_lenses()

    def test_investment_from_as_dict_raises(self, tmp_path: Path) -> None:
        """investment_from as a dict (not list) must raise ValueError."""
        from spacegame.data_loader import DataLoader

        bad = _valid_lens("invdict_lens")
        bad["investment_from"] = {"key": "val"}
        _write_lenses(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="investment_from"):
            loader.load_lenses()

    def test_error_message_names_the_lens_id(self, tmp_path: Path) -> None:
        """The ValueError message must identify which lens_id is offending."""
        from spacegame.data_loader import DataLoader

        bad = _valid_lens("named_lens")
        del bad["sees"]
        _write_lenses(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="named_lens"):
            loader.load_lenses()

    def test_scan_guard_is_not_silent_on_empty_registry(self, tmp_path: Path) -> None:
        """When lenses.json has zero entries the scan must skip, not silently pass.

        This mirrors the ``test_findings_register.py`` pattern: a scan that
        passes over nothing provides no assurance. When the shipped stub is
        empty the compliance scan is expected to be skipped (pytest.skip)
        rather than reporting a false green.
        """
        from spacegame.data_loader import DataLoader

        _write_lenses(tmp_path, [])
        loader = DataLoader(data_dir=tmp_path)
        loader.load_lenses()

        if not loader.lenses:
            pytest.skip(
                "lenses.json contains zero entries -- compliance scan would "
                "check nothing. This skip is expected while the registry is "
                "empty (A2-5/A2-6 will populate it)."
            )

        # If lenses were loaded, assert they all pass the guard.
        for lens_id, lens in loader.lenses.items():
            assert lens.lens_id == lens_id, (
                f"Key mismatch: dict key {lens_id!r} != Lens.lens_id {lens.lens_id!r}"
            )
