"""Tests for Phase 11 — Build sharing (import/export codes).

Covers export determinism, import round-trips, security validation
(size limits, schema validation, ID validation, coordinate bounds),
blueprint availability checks, and error handling.
"""

import base64
import json
import zlib

from spacegame.models.build_sharing import (
    export_build_code,
    import_build_code,
    check_blueprint_availability,
    CODE_PREFIX,
    CODE_VERSION,
    MAX_BASE64_SIZE,
    MAX_DECOMPRESSED_SIZE,
    MAX_MODULE_COUNT,
    MAX_PIXEL_COUNT,
)
from spacegame.models.ship_build import (
    ShipBuild,
    PlacedPixel,
    HullMaterial,
    WEIGHT_CLASSES,
)
from spacegame.models.ship_module import ShipModule, PlacedModule


# ============================================================================
# Helpers
# ============================================================================


def _materials() -> dict[str, HullMaterial]:
    return {
        "standard_plate": HullMaterial(
            id="standard_plate",
            name="SP",
            description="",
            color_primary=(112, 120, 136),
        ),
        "m": HullMaterial(
            id="m",
            name="M",
            description="",
            color_primary=(128, 128, 128),
        ),
    }


def _module_catalog() -> dict[str, ShipModule]:
    return {
        "cockpit_rk": ShipModule(
            id="cockpit_rk",
            name="Cockpit",
            description="",
            category="cockpit",
            manufacturer="reyes_kowalski",
            pixel_grid=[["H", "H"], ["H", "H"]],
            material_map={"H": "m"},
            provides={"slot_type": "core"},
            weight=2.0,
            base_cost=1000,
        ),
        "engine_rk": ShipModule(
            id="engine_rk",
            name="Engine",
            description="",
            category="engine",
            manufacturer="reyes_kowalski",
            pixel_grid=[["H", "E", "H"]],
            material_map={"H": "m", "E": "m"},
            provides={"slot_type": "engine"},
            weight=1.5,
            base_cost=800,
        ),
    }


def _sample_build() -> ShipBuild:
    build = ShipBuild(weight_class="tiny")
    build.modules = [
        PlacedModule(module_id="cockpit_rk", x=5, y=5, rotation=0, flipped=False),
        PlacedModule(module_id="engine_rk", x=0, y=5, rotation=1, flipped=True),
    ]
    build.pixels = [
        PlacedPixel(x=3, y=5, material_id="standard_plate"),
        PlacedPixel(x=4, y=5, material_id="standard_plate"),
    ]
    return build


# ============================================================================
# Export
# ============================================================================


class TestExport:
    """Test build code export."""

    def test_export_produces_string(self) -> None:
        build = _sample_build()
        code = export_build_code(build)
        assert isinstance(code, str)
        assert len(code) > 0

    def test_export_has_prefix(self) -> None:
        build = _sample_build()
        code = export_build_code(build)
        assert code.startswith(f"{CODE_PREFIX}:{CODE_VERSION}:")

    def test_export_deterministic(self) -> None:
        """Same build should always produce the same code."""
        build = _sample_build()
        code1 = export_build_code(build)
        code2 = export_build_code(build)
        assert code1 == code2

    def test_export_empty_build(self) -> None:
        build = ShipBuild(weight_class="tiny")
        code = export_build_code(build)
        assert code.startswith(f"{CODE_PREFIX}:{CODE_VERSION}:")

    def test_export_with_frame_variant(self) -> None:
        build = ShipBuild(weight_class="medium", frame_variant="wide")
        code = export_build_code(build)
        assert len(code) > 10


# ============================================================================
# Import — Round Trip
# ============================================================================


class TestImportRoundTrip:
    """Test export → import round-trip preserves build data."""

    def test_round_trip_modules(self) -> None:
        build = _sample_build()
        catalog = _module_catalog()
        materials = _materials()
        code = export_build_code(build)
        restored, err = import_build_code(code, catalog, materials)
        assert restored is not None, f"Import failed: {err}"
        assert restored.weight_class == "tiny"
        assert len(restored.modules) == 2
        assert restored.modules[0].module_id == "cockpit_rk"
        assert restored.modules[0].x == 5
        assert restored.modules[0].y == 5
        assert restored.modules[1].rotation == 1
        assert restored.modules[1].flipped is True

    def test_round_trip_hull_pixels(self) -> None:
        build = _sample_build()
        catalog = _module_catalog()
        materials = _materials()
        code = export_build_code(build)
        restored, err = import_build_code(code, catalog, materials)
        assert restored is not None, f"Import failed: {err}"
        assert len(restored.pixels) == 2
        assert restored.pixels[0].material_id == "standard_plate"

    def test_round_trip_frame_variant(self) -> None:
        build = ShipBuild(weight_class="medium", frame_variant="tall")
        catalog = _module_catalog()
        materials = _materials()
        code = export_build_code(build)
        restored, err = import_build_code(code, catalog, materials)
        assert restored is not None, f"Import failed: {err}"
        assert restored.frame_variant == "tall"

    def test_round_trip_empty_build(self) -> None:
        build = ShipBuild(weight_class="small")
        catalog = _module_catalog()
        materials = _materials()
        code = export_build_code(build)
        restored, err = import_build_code(code, catalog, materials)
        assert restored is not None, f"Import failed: {err}"
        assert restored.weight_class == "small"
        assert len(restored.modules) == 0
        assert len(restored.pixels) == 0


# ============================================================================
# Import — Security: Size Limits
# ============================================================================


class TestImportSizeLimits:
    """Test that oversized payloads are rejected."""

    def test_reject_oversized_base64(self) -> None:
        """Base64 strings > MAX_BASE64_SIZE should be rejected."""
        huge_code = f"{CODE_PREFIX}:{CODE_VERSION}:" + "A" * (MAX_BASE64_SIZE + 1)
        catalog = _module_catalog()
        materials = _materials()
        result, err = import_build_code(huge_code, catalog, materials)
        assert result is None
        assert "invalid" in err.lower() or "code" in err.lower()

    def test_reject_zip_bomb(self) -> None:
        """Compressed data that expands beyond limit should be rejected."""
        # Create data that compresses well but expands large
        huge_json = json.dumps(
            {"wc": "tiny", "m": [], "p": [{"x": 0, "y": 0, "m": "a"} for _ in range(10000)]}
        )
        compressed = zlib.compress(huge_json.encode("utf-8"), 9)
        encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
        code = f"{CODE_PREFIX}:{CODE_VERSION}:{encoded}"
        catalog = _module_catalog()
        materials = _materials()
        result, err = import_build_code(code, catalog, materials)
        # Should reject: either decompressed size or pixel count exceeded
        assert result is None


# ============================================================================
# Import — Security: Schema Validation
# ============================================================================


class TestImportSchemaValidation:
    """Test strict schema validation of imported data."""

    def _make_code(self, data: dict) -> str:
        """Helper: manually encode a data dict into a build code."""
        payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
        compressed = zlib.compress(payload.encode("utf-8"))
        encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
        return f"{CODE_PREFIX}:{CODE_VERSION}:{encoded}"

    def test_reject_invalid_weight_class(self) -> None:
        code = self._make_code({"v": 1, "wc": "GIGANTIC", "m": [], "p": []})
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_reject_invalid_frame_variant(self) -> None:
        code = self._make_code({"v": 1, "wc": "medium", "fv": "HUGE", "m": [], "p": []})
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_reject_unknown_module_id(self) -> None:
        code = self._make_code(
            {
                "v": 1,
                "wc": "tiny",
                "m": [
                    {"id": "HACKED_MODULE", "x": 0, "y": 0, "r": 0, "f": False},
                ],
                "p": [],
            }
        )
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_reject_unknown_material_id(self) -> None:
        code = self._make_code(
            {
                "v": 1,
                "wc": "tiny",
                "m": [],
                "p": [
                    {"x": 0, "y": 0, "m": "HACKED_MATERIAL"},
                ],
            }
        )
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_reject_out_of_bounds_module(self) -> None:
        code = self._make_code(
            {
                "v": 1,
                "wc": "tiny",
                "m": [
                    {"id": "cockpit_rk", "x": 100, "y": 100, "r": 0, "f": False},
                ],
                "p": [],
            }
        )
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_reject_out_of_bounds_pixel(self) -> None:
        code = self._make_code(
            {
                "v": 1,
                "wc": "tiny",
                "m": [],
                "p": [
                    {"x": 999, "y": 999, "m": "standard_plate"},
                ],
            }
        )
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_reject_negative_coordinates(self) -> None:
        code = self._make_code(
            {
                "v": 1,
                "wc": "tiny",
                "m": [
                    {"id": "cockpit_rk", "x": -5, "y": 0, "r": 0, "f": False},
                ],
                "p": [],
            }
        )
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_reject_invalid_rotation(self) -> None:
        code = self._make_code(
            {
                "v": 1,
                "wc": "tiny",
                "m": [
                    {"id": "cockpit_rk", "x": 0, "y": 0, "r": 99, "f": False},
                ],
                "p": [],
            }
        )
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_reject_too_many_modules(self) -> None:
        mods = [{"id": "cockpit_rk", "x": 0, "y": 0, "r": 0, "f": False}] * (MAX_MODULE_COUNT + 1)
        code = self._make_code({"v": 1, "wc": "tiny", "m": mods, "p": []})
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_reject_too_many_pixels(self) -> None:
        pixels = [{"x": 0, "y": 0, "m": "standard_plate"}] * (MAX_PIXEL_COUNT + 1)
        code = self._make_code({"v": 1, "wc": "tiny", "m": [], "p": pixels})
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is None

    def test_accept_valid_minimal_build(self) -> None:
        code = self._make_code(
            {
                "v": 1,
                "wc": "tiny",
                "m": [
                    {"id": "cockpit_rk", "x": 5, "y": 5, "r": 0, "f": False},
                ],
                "p": [
                    {"x": 3, "y": 5, "m": "standard_plate"},
                ],
            }
        )
        result, err = import_build_code(code, _module_catalog(), _materials())
        assert result is not None, f"Valid build should import: {err}"


# ============================================================================
# Import — Security: Malformed Input
# ============================================================================


class TestImportMalformedInput:
    """Test graceful handling of corrupted or malicious input."""

    def test_empty_string(self) -> None:
        result, err = import_build_code("", _module_catalog(), _materials())
        assert result is None

    def test_no_prefix(self) -> None:
        result, err = import_build_code("not_a_build_code", _module_catalog(), _materials())
        assert result is None

    def test_wrong_prefix(self) -> None:
        result, err = import_build_code("HACKED:1:abc123", _module_catalog(), _materials())
        assert result is None

    def test_invalid_base64(self) -> None:
        result, err = import_build_code(
            f"{CODE_PREFIX}:{CODE_VERSION}:!!!not_base64!!!", _module_catalog(), _materials()
        )
        assert result is None

    def test_valid_base64_invalid_zlib(self) -> None:
        encoded = base64.urlsafe_b64encode(b"not compressed data").decode("ascii")
        result, err = import_build_code(
            f"{CODE_PREFIX}:{CODE_VERSION}:{encoded}", _module_catalog(), _materials()
        )
        assert result is None

    def test_valid_zlib_invalid_json(self) -> None:
        compressed = zlib.compress(b"not json {{{")
        encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
        result, err = import_build_code(
            f"{CODE_PREFIX}:{CODE_VERSION}:{encoded}", _module_catalog(), _materials()
        )
        assert result is None

    def test_valid_json_missing_required_fields(self) -> None:
        compressed = zlib.compress(json.dumps({"hello": "world"}).encode())
        encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
        result, err = import_build_code(
            f"{CODE_PREFIX}:{CODE_VERSION}:{encoded}", _module_catalog(), _materials()
        )
        assert result is None

    def test_version_0_rejected(self) -> None:
        result, err = import_build_code(f"{CODE_PREFIX}:0:abc", _module_catalog(), _materials())
        assert result is None

    def test_version_999_rejected(self) -> None:
        result, err = import_build_code(f"{CODE_PREFIX}:999:abc", _module_catalog(), _materials())
        assert result is None


# ============================================================================
# Blueprint Availability
# ============================================================================


class TestBlueprintAvailability:
    """Test blueprint availability checking for imported builds."""

    def test_all_owned(self) -> None:
        build = _sample_build()
        catalog = _module_catalog()
        unlocked = {"cockpit_rk", "engine_rk"}
        missing = check_blueprint_availability(build, catalog, unlocked)
        assert missing == []

    def test_missing_one(self) -> None:
        build = _sample_build()
        catalog = _module_catalog()
        unlocked = {"cockpit_rk"}  # Missing engine_rk
        missing = check_blueprint_availability(build, catalog, unlocked)
        assert len(missing) == 1
        assert missing[0]["module_id"] == "engine_rk"

    def test_missing_all(self) -> None:
        build = _sample_build()
        catalog = _module_catalog()
        unlocked: set[str] = set()
        missing = check_blueprint_availability(build, catalog, unlocked)
        assert len(missing) == 2

    def test_empty_build_no_missing(self) -> None:
        build = ShipBuild(weight_class="tiny")
        catalog = _module_catalog()
        missing = check_blueprint_availability(build, catalog, set())
        assert missing == []

    def test_missing_includes_unlock_info(self) -> None:
        build = _sample_build()
        catalog = _module_catalog()
        unlocked = {"cockpit_rk"}
        missing = check_blueprint_availability(build, catalog, unlocked)
        assert "module_id" in missing[0]
        assert "name" in missing[0]
        assert "category" in missing[0]
