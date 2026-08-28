"""Tests for the Capstone data model and should_fire() predicate."""

from __future__ import annotations

import dataclasses
import inspect
import json

import pytest

from spacegame.models.capstone import Capstone, should_fire


def _valid_capstone(**overrides) -> Capstone:
    defaults = {
        "capstone_id": "vengeance_capstone",
        "lens_id": "vengeance",
        "capstone_threshold": 95,
        "cutscene_ref": None,
    }
    defaults.update(overrides)
    return Capstone(**defaults)


def _valid_dict(**overrides) -> dict:
    defaults = {
        "capstone_id": "vengeance_capstone",
        "lens_id": "vengeance",
        "capstone_threshold": 95,
        "cutscene_ref": None,
    }
    defaults.update(overrides)
    return defaults


class TestCapstoneSchema:
    def test_field_set_matches_spec(self) -> None:
        """Capstone must have exactly the four spec-declared fields."""
        field_names = {f.name for f in dataclasses.fields(Capstone)}
        assert field_names == {"capstone_id", "lens_id", "capstone_threshold", "cutscene_ref"}

    def test_is_frozen(self) -> None:
        """Capstone must be a frozen dataclass; mutation raises FrozenInstanceError."""
        c = _valid_capstone()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            c.capstone_id = "other"  # type: ignore[misc]

    def test_cutscene_ref_defaults_to_none(self) -> None:
        """cutscene_ref must default to None when not supplied."""
        c = Capstone(capstone_id="a", lens_id="b", capstone_threshold=10)
        assert c.cutscene_ref is None

    def test_module_docstring_states_session_continues_invariant(self) -> None:
        """The module docstring must assert that firing MUST NOT end the session."""
        import spacegame.models.capstone as mod

        doc = (mod.__doc__ or "").lower()
        # Check for key phrases about play continuing / not ending.
        assert any(phrase in doc for phrase in ("must not end", "does not end", "continue")), (
            "capstone.py module docstring must state the invariant that "
            "firing a capstone must not end the session. Got: %r" % mod.__doc__
        )

    def test_module_does_not_import_engine_or_views(self) -> None:
        """capstone.py must not import from spacegame.engine or spacegame.views."""
        import pathlib

        src = pathlib.Path(__file__).parent.parent.parent / "spacegame" / "models" / "capstone.py"
        text = src.read_text(encoding="utf-8")
        assert "from spacegame.engine" not in text, (
            "capstone.py imports from spacegame.engine — forbidden by the hook contract"
        )
        assert "from spacegame.views" not in text, (
            "capstone.py imports from spacegame.views — forbidden by the hook contract"
        )


class TestCapstoneRoundtrip:
    def test_roundtrip_preserves_all_fields_non_null_cutscene(self) -> None:
        """Round-trip through to_dict / json / from_dict preserves all fields."""
        c = _valid_capstone(cutscene_ref="cutscene_vengeance_01")
        data = json.loads(json.dumps(c.to_dict()))
        restored = Capstone.from_dict(data)
        assert restored.capstone_id == c.capstone_id
        assert restored.lens_id == c.lens_id
        assert restored.capstone_threshold == c.capstone_threshold
        assert restored.cutscene_ref == c.cutscene_ref

    def test_roundtrip_preserves_null_cutscene_ref(self) -> None:
        """Null cutscene_ref survives JSON serialization and from_dict."""
        c = _valid_capstone(cutscene_ref=None)
        d = c.to_dict()
        assert d["cutscene_ref"] is None, "to_dict() must emit cutscene_ref explicitly as null"
        # JSON round-trip: None → null → None
        data = json.loads(json.dumps(d))
        assert data["cutscene_ref"] is None
        restored = Capstone.from_dict(data)
        assert restored.cutscene_ref is None

    def test_from_dict_missing_cutscene_ref_defaults_to_none(self) -> None:
        """A dict without cutscene_ref key should produce a Capstone with cutscene_ref=None."""
        d = _valid_dict()
        d.pop("cutscene_ref", None)
        c = Capstone.from_dict(d)
        assert c.cutscene_ref is None

    @pytest.mark.parametrize("missing_field", ["capstone_id", "lens_id", "capstone_threshold"])
    def test_from_dict_missing_required_field_raises(self, missing_field: str) -> None:
        """Each required field missing must raise ValueError."""
        d = _valid_dict()
        del d[missing_field]
        with pytest.raises(ValueError):
            Capstone.from_dict(d)

    def test_from_dict_missing_capstone_id_error_says_unknown(self) -> None:
        """When capstone_id is missing the error message should say <unknown>."""
        d = _valid_dict()
        del d["capstone_id"]
        with pytest.raises(ValueError, match="<unknown>|capstone_id"):
            Capstone.from_dict(d)

    def test_from_dict_rejects_list_lens_id_empty(self) -> None:
        """lens_id as empty list must raise ValueError."""
        d = _valid_dict(lens_id=[])
        with pytest.raises(ValueError):
            Capstone.from_dict(d)

    def test_from_dict_rejects_list_lens_id_multi(self) -> None:
        """lens_id as multi-element list must raise ValueError."""
        d = _valid_dict(lens_id=["a", "b"])
        with pytest.raises(ValueError):
            Capstone.from_dict(d)

    def test_from_dict_rejects_non_int_threshold_string(self) -> None:
        """capstone_threshold as string must raise ValueError."""
        d = _valid_dict(capstone_threshold="high")
        with pytest.raises(ValueError):
            Capstone.from_dict(d)

    def test_from_dict_rejects_non_int_threshold_float(self) -> None:
        """capstone_threshold as float must raise ValueError."""
        d = _valid_dict(capstone_threshold=3.14)
        with pytest.raises(ValueError):
            Capstone.from_dict(d)


class TestShouldFire:
    def test_fires_when_all_conditions_met(self) -> None:
        """should_fire returns True when investment meets threshold, lens open, not yet reached."""
        c = _valid_capstone(capstone_threshold=95)
        assert should_fire(c, 95, set(), set()) is True

    def test_fires_when_investment_exceeds_threshold(self) -> None:
        """should_fire returns True when investment strictly exceeds the threshold."""
        c = _valid_capstone(capstone_threshold=95)
        assert should_fire(c, 100, set(), set()) is True

    def test_does_not_fire_below_threshold(self) -> None:
        """should_fire returns False when investment is exactly one below threshold."""
        c = _valid_capstone(capstone_threshold=95)
        assert should_fire(c, 94, set(), set()) is False

    def test_does_not_fire_when_lens_closed(self) -> None:
        """should_fire returns False when the capstone's lens_id is in closed_lenses."""
        c = _valid_capstone(capstone_threshold=95)
        assert should_fire(c, 95, {"vengeance"}, set()) is False

    def test_does_not_fire_when_already_reached(self) -> None:
        """should_fire returns False when capstone_id is already in capstones_reached."""
        c = _valid_capstone(capstone_threshold=95)
        assert should_fire(c, 95, set(), {"vengeance_capstone"}) is False

    def test_signature_takes_primitives_not_player(self) -> None:
        """should_fire parameters must be (Capstone, int, set[str], set[str])."""
        sig = inspect.signature(should_fire)
        params = list(sig.parameters.values())
        assert len(params) == 4, f"Expected 4 params, got {len(params)}"
        # Just check positional names; annotation enforcement is best-effort.
        names = [p.name for p in params]
        assert names[0] in ("capstone", "c"), f"First param should be 'capstone', got {names[0]!r}"


class TestCapstoneDataLoader:
    """Integration tests for DataLoader.load_capstones()."""

    def _write_capstones(self, tmp_path, capstones: list) -> None:
        narrative = tmp_path / "narrative"
        narrative.mkdir(parents=True, exist_ok=True)
        (narrative / "capstones.json").write_text(
            json.dumps({"capstones": capstones}), encoding="utf-8"
        )

    def test_load_from_tmp_path(self, tmp_path) -> None:
        """A valid capstone JSON loads into loader.capstones keyed by capstone_id."""
        from spacegame.data_loader import DataLoader

        cap = {
            "capstone_id": "wealth_capstone",
            "lens_id": "wealth",
            "capstone_threshold": 100,
            "cutscene_ref": None,
        }
        self._write_capstones(tmp_path, [cap])
        loader = DataLoader(data_dir=tmp_path)
        loader.load_capstones()
        assert "wealth_capstone" in loader.capstones
        assert loader.capstones["wealth_capstone"].lens_id == "wealth"
        assert loader.capstones["wealth_capstone"].capstone_threshold == 100

    def test_singleton_exposes_capstones(self) -> None:
        """get_data_loader().capstones must be a dict[str, Capstone] after load_all()."""
        from spacegame.data_loader import get_data_loader
        from spacegame.models.capstone import Capstone

        loader = get_data_loader()
        assert isinstance(loader.capstones, dict)
        # All values (if any) must be Capstone instances.
        for val in loader.capstones.values():
            assert isinstance(val, Capstone)

    def test_empty_stub_loads_without_error(self, tmp_path) -> None:
        """The shipped empty capstones.json must load without crashing."""
        from spacegame.data_loader import DataLoader

        self._write_capstones(tmp_path, [])
        loader = DataLoader(data_dir=tmp_path)
        loader.load_capstones()
        assert loader.capstones == {}

    def test_duplicate_capstone_id_raises(self, tmp_path) -> None:
        """Two capstones with the same capstone_id must raise ValueError naming the id."""
        from spacegame.data_loader import DataLoader

        cap = {
            "capstone_id": "dup_cap",
            "lens_id": "vengeance",
            "capstone_threshold": 50,
            "cutscene_ref": None,
        }
        self._write_capstones(tmp_path, [cap, cap])
        loader = DataLoader(data_dir=tmp_path)
        with pytest.raises(ValueError, match="dup_cap"):
            loader.load_capstones()

    def test_missing_capstones_file_is_warning_not_error(self, tmp_path) -> None:
        """Absent capstones.json returns empty dict (no crash)."""
        from spacegame.data_loader import DataLoader

        # Don't write any file; the data_dir exists but narrative/capstones.json does not.
        loader = DataLoader(data_dir=tmp_path)
        result = loader.load_capstones()
        assert result == {}
