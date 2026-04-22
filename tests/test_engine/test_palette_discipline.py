"""Palette discipline regression guard.

Cross-file source audits that ensure Aurelia's rendering stack keeps
routing through the canonical palette module rather than hand-rolled
RGB tuples or substring lookup tables. These tests are the safety net
for future maintainers: if a refactor quietly reintroduces a legacy
pattern we worked hard to remove, CI should notice.

Paired with the per-JSON compliance tests in ``test_content_catalog``
and the band-aware integration tests in ``test_ship_composite``.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHIP_COMPOSITE = _REPO_ROOT / "spacegame" / "engine" / "ship_composite.py"
_SHIP_BUILD = _REPO_ROOT / "spacegame" / "models" / "ship_build.py"
_MATERIAL_PALETTE = _REPO_ROOT / "spacegame" / "engine" / "material_palette.py"
_SHIP_PRESETS = _REPO_ROOT / "spacegame" / "models" / "ship_presets.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestShipCompositeDiscipline:
    """ShipComposite must route color through the canonical palette."""

    def test_does_not_reintroduce_emissive_substring_table(self) -> None:
        source = _read(_SHIP_COMPOSITE)
        assert "_EMISSIVE_MATERIAL_RULES" not in source, (
            "Substring-based emissive lookup was removed in Session 3. "
            "Read material.emissive_role via get_role() instead."
        )

    def test_does_not_reintroduce_rivet_substring_table(self) -> None:
        source = _read(_SHIP_COMPOSITE)
        assert "_RIVET_DENSITY_RULES" not in source, (
            "Substring-based rivet lookup was removed in Session 3. "
            "Read material.rivet_density directly."
        )
        assert "_DEFAULT_RIVET_DENSITY" not in source, (
            "Default rivet density constant is gone; the field has a "
            "dataclass-level default on HullMaterial now."
        )

    def test_imports_canonical_palette_module(self) -> None:
        """Band/role resolution must come from material_palette, not local data."""
        source = _read(_SHIP_COMPOSITE)
        # Either direct or deferred imports are acceptable — we just
        # require that the palette module is actually referenced.
        assert "material_palette" in source, (
            "ship_composite.py should import helpers from "
            "spacegame.engine.material_palette to resolve bands/roles."
        )

    def test_does_not_hardcode_material_band_synthesis(self) -> None:
        """Bible §2.2 bands are canonical; synthesizing from RGB is forbidden."""
        source = _read(_SHIP_COMPOSITE)
        # The legacy synthesizer called _lighten on a primary color; it's
        # been removed. A regression would typically reintroduce it.
        assert "def _lighten" not in source, (
            "_lighten() belongs to legacy band synthesis and was removed. "
            "Use the canonical band from get_band() / apply_category_offset()."
        )


class TestHullMaterialDiscipline:
    """HullMaterial data model must not regrow raw-RGB storage fields."""

    def test_dataclass_declares_no_raw_color_fields(self) -> None:
        """color_primary / _accent / _highlight are derived properties now."""
        source = _read(_SHIP_BUILD)
        # Positive check: they appear only as @property accessors, never as
        # dataclass field declarations like `color_primary: tuple[...]`.
        for field in ("color_primary", "color_accent", "color_highlight"):
            # Pattern for dataclass field: `name: tuple[int, int, int]`
            field_decl = f"{field}: tuple[int, int, int]"
            assert field_decl not in source, (
                f"{field} must stay a @property, not a dataclass field. "
                f"Storage is shade_band + render params."
            )

    def test_shade_band_is_declared_as_field(self) -> None:
        source = _read(_SHIP_BUILD)
        assert "shade_band: str" in source, (
            "HullMaterial must declare shade_band as a required str field."
        )


class TestConstructionSiteDiscipline:
    """No production code constructs HullMaterial with the removed kwargs."""

    _PROD_FILES = (_SHIP_COMPOSITE, _SHIP_PRESETS, _SHIP_BUILD)

    def test_no_color_primary_kwarg_in_production_constructors(self) -> None:
        for path in self._PROD_FILES:
            source = _read(path)
            assert "color_primary=" not in source, (
                f"{path.name} passes color_primary= to a constructor. "
                f"Use shade_band= + render params instead."
            )

    def test_no_color_accent_kwarg_in_production_constructors(self) -> None:
        for path in self._PROD_FILES:
            source = _read(path)
            assert "color_accent=" not in source, (
                f"{path.name} passes color_accent= to a constructor. "
                f"Accent color derives from shade_band automatically."
            )

    def test_no_color_highlight_kwarg_in_production_constructors(self) -> None:
        for path in self._PROD_FILES:
            source = _read(path)
            assert "color_highlight=" not in source, (
                f"{path.name} passes color_highlight= to a constructor. "
                f"Highlight color derives from shade_band automatically."
            )


class TestPaletteModuleSurface:
    """material_palette exposes the minimal public API downstream needs."""

    def test_required_public_functions_exist(self) -> None:
        from spacegame.engine import material_palette

        required = (
            "get_band",
            "get_role",
            "band_names",
            "role_names",
            "is_valid_band",
            "is_valid_role",
            "snap_to_band",
            "snap_to_role",
            "lerp_in_band",
            "apply_category_offset",
            "set_colorblind_profile",
            "get_active_profile",
            "assert_band_compliance",
            "assert_role_compliance",
        )
        for name in required:
            assert hasattr(material_palette, name), (
                f"material_palette.{name} missing — public API regression."
            )

    def test_colorblind_profiles_exported(self) -> None:
        from spacegame.engine import material_palette

        assert hasattr(material_palette, "PROTANOPIA")
        assert hasattr(material_palette, "DEUTERANOPIA")
        assert hasattr(material_palette, "TRITANOPIA")

    def test_band_and_role_tables_are_nonempty(self) -> None:
        from spacegame.engine.material_palette import MATERIAL_BANDS, PALETTE_ROLES

        assert len(MATERIAL_BANDS) >= 7
        assert len(PALETTE_ROLES) >= 20
