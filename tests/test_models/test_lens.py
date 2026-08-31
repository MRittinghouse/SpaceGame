"""Tests for the Lens data model and registry loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spacegame.models.lens import _REQUIRED_FIELDS, Lens


def _make_lens_dict(**overrides) -> dict:
    """Return a valid lens dict, merging any overrides."""
    base = {
        "lens_id": "test_lens",
        "name": "Test Lens",
        "core_fantasy": "A one-line core fantasy.",
        "question": "What does the player ask?",
        "sees": "What it notices in places.",
        "wants": "What the character wants.",
        "trades": "What they give up.",
        "investment_from": ["trade_action", "haul_action"],
        "minigame_shape": "optimisation_under_scarcity",
        "voice": "Direct, calculating.",
        "tier_unlocks": ["market_insight", "route_mastery"],
    }
    base.update(overrides)
    return base


def _make_lens(**overrides) -> Lens:
    """Return a valid Lens instance."""
    return Lens.from_dict(_make_lens_dict(**overrides))


class TestLensSchema:
    def test_field_set_matches_spec(self) -> None:
        """All 11 spec-declared fields must be present on the dataclass."""
        expected = {
            "lens_id",
            "name",
            "core_fantasy",
            "question",
            "sees",
            "wants",
            "trades",
            "investment_from",
            "minigame_shape",
            "voice",
            "tier_unlocks",
        }
        import dataclasses

        actual = {f.name for f in dataclasses.fields(Lens)}
        assert actual == expected, f"Field mismatch. Expected {expected}, got {actual}"

    def test_dataclass_is_frozen(self) -> None:
        """Mutation of a Lens instance must raise FrozenInstanceError."""
        import dataclasses

        lens = _make_lens()
        with pytest.raises(dataclasses.FrozenInstanceError):
            lens.name = "mutated"  # type: ignore[misc]

    def test_investment_from_type_is_tuple(self) -> None:
        lens = _make_lens(investment_from=["a", "b"])
        assert isinstance(lens.investment_from, tuple)

    def test_tier_unlocks_type_is_tuple(self) -> None:
        lens = _make_lens(tier_unlocks=["x", "y"])
        assert isinstance(lens.tier_unlocks, tuple)

    def test_required_fields_constant_covers_all_eleven(self) -> None:
        assert len(_REQUIRED_FIELDS) == 11

    def test_all_required_fields_are_dataclass_fields(self) -> None:
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(Lens)}
        for req in _REQUIRED_FIELDS:
            assert req in field_names, f"Required field '{req}' missing from dataclass"


class TestLensRoundtrip:
    def test_to_dict_from_dict_preserves_every_field(self) -> None:
        """Round-trip must preserve all 11 fields, with tuples restored as tuples."""
        original = _make_lens(
            lens_id="wealth",
            name="Wealth",
            core_fantasy="Accumulate enough to never be powerless again.",
            question="What will you sacrifice to become untouchable?",
            sees="Salvage tonnage and a supply gap to exploit.",
            wants="Resources, leverage, and market dominance.",
            trades="Time, loyalty, and anything that does not multiply.",
            investment_from=("trade_profit", "bulk_haul", "undercut_rival"),
            minigame_shape="optimisation_under_scarcity",
            voice="Precise. Speaks in quantities and rates.",
            tier_unlocks=("market_insight_1", "route_mastery_2"),
        )

        as_dict = original.to_dict()
        # Simulate JSON serialization round-trip (tuples become lists)
        as_json = json.loads(json.dumps(as_dict))
        restored = Lens.from_dict(as_json)

        assert restored.lens_id == original.lens_id
        assert restored.name == original.name
        assert restored.core_fantasy == original.core_fantasy
        assert restored.question == original.question
        assert restored.sees == original.sees
        assert restored.wants == original.wants
        assert restored.trades == original.trades
        assert restored.investment_from == original.investment_from
        assert restored.minigame_shape == original.minigame_shape
        assert restored.voice == original.voice
        assert restored.tier_unlocks == original.tier_unlocks

        # Confirm tuple types survived the JSON round-trip
        assert isinstance(restored.investment_from, tuple)
        assert isinstance(restored.tier_unlocks, tuple)
        assert restored == original

    def test_to_dict_emits_lists_for_tuple_fields(self) -> None:
        lens = _make_lens()
        d = lens.to_dict()
        assert isinstance(d["investment_from"], list)
        assert isinstance(d["tier_unlocks"], list)

    def test_to_dict_has_all_eleven_keys(self) -> None:
        d = _make_lens().to_dict()
        for field in _REQUIRED_FIELDS:
            assert field in d, f"to_dict() missing key '{field}'"


class TestLensValidation:
    def test_missing_minigame_shape_raises_value_error_naming_lens_id(self) -> None:
        data = _make_lens_dict()
        del data["minigame_shape"]
        with pytest.raises(ValueError, match="minigame_shape"):
            Lens.from_dict(data)

    @pytest.mark.parametrize("field", list(_REQUIRED_FIELDS))
    def test_missing_required_field_raises(self, field: str) -> None:
        data = _make_lens_dict()
        del data[field]
        with pytest.raises(ValueError):
            Lens.from_dict(data)

    def test_non_snake_case_lens_id_raises(self) -> None:
        for bad_id in ("Vengeance", "political-power", "1lens", "WEALTH"):
            data = _make_lens_dict(lens_id=bad_id)
            with pytest.raises(ValueError, match="snake_case"):
                Lens.from_dict(data)

    def test_valid_snake_case_ids_accepted(self) -> None:
        for good_id in ("vengeance", "political_power", "lens_2b", "a"):
            lens = _make_lens(lens_id=good_id)
            assert lens.lens_id == good_id

    def test_investment_from_as_string_raises(self) -> None:
        data = _make_lens_dict(investment_from="not_a_list")
        with pytest.raises(ValueError, match="investment_from"):
            Lens.from_dict(data)

    def test_tier_unlocks_as_dict_raises(self) -> None:
        data = _make_lens_dict(tier_unlocks={"key": "val"})
        with pytest.raises(ValueError, match="tier_unlocks"):
            Lens.from_dict(data)

    def test_error_message_names_offending_lens_id(self) -> None:
        data = _make_lens_dict(lens_id="bad_lens")
        del data["sees"]
        with pytest.raises(ValueError, match="bad_lens"):
            Lens.from_dict(data)


class TestLensRegistry:
    """Tests for DataLoader lens loading integration."""

    def _write_lenses_json(self, tmp_path: Path, lenses: list) -> None:
        narrative_dir = tmp_path / "narrative"
        narrative_dir.mkdir(parents=True, exist_ok=True)
        (narrative_dir / "lenses.json").write_text(json.dumps({"lenses": lenses}), encoding="utf-8")

    def test_load_from_tmp_path(self, tmp_path: Path) -> None:
        """Loading a valid lens from tmp_path yields one entry keyed by lens_id."""
        from spacegame.data_loader import DataLoader

        lens_data = _make_lens_dict(lens_id="wealth")
        self._write_lenses_json(tmp_path, [lens_data])

        loader = DataLoader(data_dir=tmp_path)
        loader.load_lenses()

        assert "wealth" in loader.lenses
        assert isinstance(loader.lenses["wealth"], Lens)
        assert loader.lenses["wealth"].name == "Test Lens"

    def test_empty_stub_loads_without_error(self, tmp_path: Path) -> None:
        """An empty lenses.json stub must load without crashing."""
        from spacegame.data_loader import DataLoader

        self._write_lenses_json(tmp_path, [])
        loader = DataLoader(data_dir=tmp_path)
        loader.load_lenses()
        assert loader.lenses == {}

    def test_missing_file_does_not_crash(self, tmp_path: Path) -> None:
        """If lenses.json does not exist, load_lenses() logs a warning and returns."""
        from spacegame.data_loader import DataLoader

        loader = DataLoader(data_dir=tmp_path)
        loader.load_lenses()
        assert loader.lenses == {}

    def test_singleton_exposes_lenses(self) -> None:
        """get_data_loader() must expose a lenses dict after load_all()."""
        from spacegame.data_loader import get_data_loader

        loader = get_data_loader()
        assert hasattr(loader, "lenses")
        assert isinstance(loader.lenses, dict)

    def test_duplicate_lens_id_raises(self, tmp_path: Path) -> None:
        """Duplicate lens_id values in lenses.json must raise ValueError."""
        from spacegame.data_loader import DataLoader

        duplicate = _make_lens_dict(lens_id="dupe_lens")
        self._write_lenses_json(tmp_path, [duplicate, duplicate])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="dupe_lens"):
            loader.load_lenses()

    def test_invalid_lens_in_file_raises(self, tmp_path: Path) -> None:
        """A lens missing a required field should raise ValueError during load."""
        from spacegame.data_loader import DataLoader

        bad = _make_lens_dict()
        del bad["minigame_shape"]
        self._write_lenses_json(tmp_path, [bad])

        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="minigame_shape"):
            loader.load_lenses()

    def test_real_lenses_json_loads_all_sixteen_entries(self) -> None:
        """The real data/narrative/lenses.json loads all sixteen lens definitions cleanly.

        A2-5 landed eight entries (vengeance through revolution); A2-6 appended the
        second eight (empire through preservation). This test verifies the file loads
        without error and produces the full sixteen-id set.
        """
        from spacegame.config import PROJECT_ROOT
        from spacegame.data_loader import DataLoader

        loader = DataLoader(data_dir=PROJECT_ROOT / "data")
        loader.load_lenses()
        assert len(loader.lenses) == 16, (
            f"Expected 16 lenses after A2-6; found {len(loader.lenses)}."
        )
        expected_ids = {
            "vengeance",
            "wealth",
            "political_power",
            "exploration",
            "discovery",
            "justice",
            "crime",
            "revolution",
            "empire",
            "community",
            "legacy",
            "faith",
            "transcendence",
            "connection",
            "truth",
            "preservation",
        }
        assert set(loader.lenses.keys()) == expected_ids


class TestCommunityWealthSameWound:
    """Unit-test the community/wealth 'same wound' constraint against the real JSON.

    Loads data/narrative/lenses.json directly (not via singleton) so this test
    can run in isolation from the full load_all() chain. Skip-cleanly if either
    lens is absent (guards against a partial JSON state during development).
    """

    _COMMUNITY_DISCRIMINANTS: frozenset[str] = frozenset(
        {"survivors", "cryo", "families", "housing", "shelter", "people"}
    )
    _WEALTH_DISCRIMINANTS: frozenset[str] = frozenset(
        {"supply", "gap", "route", "margin", "tonnage", "price"}
    )

    def _load_real(self) -> dict:
        from spacegame.config import PROJECT_ROOT
        from spacegame.data_loader import DataLoader

        loader = DataLoader(data_dir=PROJECT_ROOT / "data")
        loader.load_lenses()
        return loader.lenses

    def test_community_sees_not_equal_to_wealth_sees(self) -> None:
        """community.sees and wealth.sees must be distinct strings."""
        lenses = self._load_real()
        comm = lenses.get("community")
        wlth = lenses.get("wealth")
        if comm is None or wlth is None:
            pytest.skip("'community' or 'wealth' not yet in lenses.json.")
        assert comm.sees != wlth.sees, (
            "community.sees == wealth.sees -- the same wound must produce opposite readings."
        )

    def test_community_sees_contains_person_word(self) -> None:
        """community.sees must contain at least one person-focused discriminant word."""
        lenses = self._load_real()
        comm = lenses.get("community")
        wlth = lenses.get("wealth")
        if comm is None or wlth is None:
            pytest.skip("'community' or 'wealth' not yet in lenses.json.")
        sees_lower = comm.sees.lower()
        found = any(word in sees_lower for word in self._COMMUNITY_DISCRIMINANTS)
        assert found, (
            f"community.sees does not contain a person discriminant from "
            f"{sorted(self._COMMUNITY_DISCRIMINANTS)!r}: {comm.sees!r}"
        )

    def test_wealth_sees_contains_market_word(self) -> None:
        """wealth.sees must contain at least one market-focused discriminant word."""
        lenses = self._load_real()
        comm = lenses.get("community")
        wlth = lenses.get("wealth")
        if comm is None or wlth is None:
            pytest.skip("'community' or 'wealth' not yet in lenses.json.")
        sees_lower = wlth.sees.lower()
        found = any(word in sees_lower for word in self._WEALTH_DISCRIMINANTS)
        assert found, (
            f"wealth.sees does not contain a market discriminant from "
            f"{sorted(self._WEALTH_DISCRIMINANTS)!r}: {wlth.sees!r}"
        )
