"""Build sharing and module blueprint commerce.

Encodes ShipBuild data as versioned, compressed, base64 text strings
for sharing. Also handles module blueprint purchases at stations.

Encodes ShipBuild data as versioned, compressed, base64 text strings
for sharing through Discord, Reddit, or any text channel. Import
applies strict security validation against untrusted external input.

Security model:
- JSON-only deserialization (never pickle/eval/exec)
- Size limits at every pipeline stage (base64, decompressed, parsed)
- Strict schema validation with allow-lists (not block-lists)
- ID validation against loaded game catalogs
- Coordinate bounds checking against declared weight class
- Generic error messages (no information leakage to attackers)

Part of the Shipbuilder Upgrade — Phase 11 (Build Sharing).
"""

from __future__ import annotations

import base64
import json
import zlib
from typing import Optional

from spacegame.models.ship_build import (
    FRAME_VARIANTS,
    WEIGHT_CLASSES,
    PlacedPixel,
    ShipBuild,
)
from spacegame.models.ship_module import PlacedModule, ShipModule
from spacegame.utils.logger import logger

# ============================================================================
# Constants
# ============================================================================

CODE_PREFIX = "AURELIA"
CODE_VERSION = 1

# Security limits
MAX_BASE64_SIZE = 50_000  # 50KB max for the base64 input string
MAX_DECOMPRESSED_SIZE = 200_000  # 200KB max after zlib decompression
MAX_MODULE_COUNT = 50  # Well above XLarge max of ~24
MAX_PIXEL_COUNT = 5_000  # Well above any valid build

# Valid values for schema validation
VALID_WEIGHT_CLASSES = frozenset(WEIGHT_CLASSES.keys())
VALID_FRAME_VARIANTS = frozenset({"wide", "tall"})
VALID_ROTATIONS = frozenset({0, 1, 2, 3})


# ============================================================================
# Export
# ============================================================================


def export_build_code(build: ShipBuild) -> str:
    """Export a ship build as a compact, shareable text code.

    Format: AURELIA:<version>:<base64-encoded-zlib-compressed-JSON>

    The JSON payload uses short keys to minimize size:
    - v: version, wc: weight_class, fv: frame_variant
    - m: modules list, p: hull pixels list

    Args:
        build: The ship build to export.

    Returns:
        A compact text string like 'AURELIA:1:eJzLSM3JyQ...'
    """
    # Build minimal payload with short keys
    payload: dict = {
        "v": CODE_VERSION,
        "wc": build.weight_class,
    }

    if build.frame_variant:
        payload["fv"] = build.frame_variant

    # Modules: only structural data (id, position, orientation)
    if build.modules:
        payload["m"] = [
            {
                "id": m.module_id,
                "x": m.x,
                "y": m.y,
                "r": m.rotation,
                "f": m.flipped,
            }
            for m in build.modules
        ]
    else:
        payload["m"] = []

    # Hull pixels: only position and material
    if build.pixels:
        payload["p"] = [{"x": p.x, "y": p.y, "m": p.material_id} for p in build.pixels]
    else:
        payload["p"] = []

    # Serialize → compress → encode
    # sort_keys=True for deterministic output
    json_bytes = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    compressed = zlib.compress(json_bytes, 9)  # Max compression
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")

    return f"{CODE_PREFIX}:{CODE_VERSION}:{encoded}"


# ============================================================================
# Import (Security-Hardened)
# ============================================================================


def import_build_code(
    code: str,
    module_catalog: dict[str, ShipModule],
    hull_materials: dict[str, object],
) -> tuple[Optional[ShipBuild], str]:
    """Import a ship build from a text code with full security validation.

    Pipeline: validate prefix → base64 decode → zlib decompress →
    JSON parse → schema validate → ID validate → bounds check →
    construct ShipBuild.

    SECURITY: This function processes UNTRUSTED external input.
    Every stage has defensive validation. No pickle, eval, or exec.
    Generic error messages prevent information leakage.

    Args:
        code: The build code string to import.
        module_catalog: Loaded module blueprints for ID validation.
        hull_materials: Loaded hull materials for ID validation.

    Returns:
        (ShipBuild, "") on success, (None, error_message) on failure.
    """
    generic_error = "Invalid build code"

    try:
        return _import_build_code_inner(code, module_catalog, hull_materials)
    except Exception:
        # Catch-all: ANY exception during import → generic error.
        # Never expose internal details to the caller.
        logger.debug(f"Build code import failed (length={len(code) if code else 0})")
        return None, generic_error


def _import_build_code_inner(
    code: str,
    module_catalog: dict[str, ShipModule],
    hull_materials: dict[str, object],
) -> tuple[Optional[ShipBuild], str]:
    """Inner import implementation. Exceptions propagate to the outer wrapper."""
    generic_error = "Invalid build code"

    # --- Stage 1: Prefix and version validation ---
    if not code or not isinstance(code, str):
        return None, generic_error

    parts = code.split(":", 2)
    if len(parts) != 3:
        return None, generic_error

    prefix, version_str, payload_b64 = parts

    if prefix != CODE_PREFIX:
        return None, generic_error

    try:
        version = int(version_str)
    except (ValueError, TypeError):
        return None, generic_error

    if version != CODE_VERSION:
        return None, generic_error

    # --- Stage 2: Size limit on base64 input ---
    if len(payload_b64) > MAX_BASE64_SIZE:
        return None, generic_error

    if not payload_b64:
        return None, generic_error

    # --- Stage 3: Base64 decode ---
    try:
        compressed = base64.urlsafe_b64decode(payload_b64)
    except Exception:
        return None, generic_error

    # --- Stage 4: Zlib decompress with size limit ---
    try:
        decompressor = zlib.decompressobj()
        decompressed = decompressor.decompress(compressed, MAX_DECOMPRESSED_SIZE)
        if decompressor.unconsumed_tail:
            # More data than our limit — potential zip bomb
            return None, generic_error
    except Exception:
        return None, generic_error

    # --- Stage 5: JSON parse ---
    try:
        data = json.loads(decompressed.decode("utf-8"))
    except Exception:
        return None, generic_error

    if not isinstance(data, dict):
        return None, generic_error

    # --- Stage 6: Schema validation ---

    # Weight class (required)
    wc = data.get("wc")
    if wc not in VALID_WEIGHT_CLASSES:
        return None, generic_error

    # Frame variant (optional)
    fv = data.get("fv")
    if fv is not None and fv not in VALID_FRAME_VARIANTS:
        return None, generic_error

    # Canvas bounds for coordinate checking
    canvas_w = WEIGHT_CLASSES[wc]["canvas_w"]
    canvas_h = WEIGHT_CLASSES[wc]["canvas_h"]
    if fv and wc in FRAME_VARIANTS and fv in FRAME_VARIANTS[wc]:
        canvas_w, canvas_h = FRAME_VARIANTS[wc][fv]

    # Modules list (required, may be empty)
    raw_modules = data.get("m")
    if not isinstance(raw_modules, list):
        return None, generic_error
    if len(raw_modules) > MAX_MODULE_COUNT:
        return None, generic_error

    # Pixels list (required, may be empty)
    raw_pixels = data.get("p")
    if not isinstance(raw_pixels, list):
        return None, generic_error
    if len(raw_pixels) > MAX_PIXEL_COUNT:
        return None, generic_error

    # --- Stage 7: Module validation ---
    validated_modules: list[PlacedModule] = []
    for entry in raw_modules:
        if not isinstance(entry, dict):
            return None, generic_error

        mod_id = entry.get("id")
        if not isinstance(mod_id, str) or mod_id not in module_catalog:
            return None, generic_error

        x = entry.get("x")
        y = entry.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return None, generic_error
        if x < 0 or y < 0 or x >= canvas_w or y >= canvas_h:
            return None, generic_error

        rot = entry.get("r", 0)
        if not isinstance(rot, int) or rot not in VALID_ROTATIONS:
            return None, generic_error

        flipped = entry.get("f", False)
        if not isinstance(flipped, bool):
            return None, generic_error

        validated_modules.append(
            PlacedModule(
                module_id=mod_id,
                x=x,
                y=y,
                rotation=rot,
                flipped=flipped,
            )
        )

    # --- Stage 8: Pixel validation ---
    validated_pixels: list[PlacedPixel] = []
    for entry in raw_pixels:
        if not isinstance(entry, dict):
            return None, generic_error

        x = entry.get("x")
        y = entry.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return None, generic_error
        if x < 0 or y < 0 or x >= canvas_w or y >= canvas_h:
            return None, generic_error

        mat_id = entry.get("m")
        if not isinstance(mat_id, str) or mat_id not in hull_materials:
            return None, generic_error

        validated_pixels.append(PlacedPixel(x=x, y=y, material_id=mat_id))

    # --- Stage 9: Construct validated ShipBuild ---
    build = ShipBuild(
        weight_class=wc,
        frame_variant=fv,
        modules=validated_modules,
        pixels=validated_pixels,
    )

    logger.debug(
        f"Build code imported: {wc}, {len(validated_modules)} modules, "
        f"{len(validated_pixels)} pixels"
    )
    return build, ""


# ============================================================================
# Blueprint Availability Check
# ============================================================================


def check_blueprint_availability(
    build: ShipBuild,
    module_catalog: dict[str, ShipModule],
    unlocked_modules: set[str],
) -> list[dict]:
    """Check which module blueprints in a build the player hasn't unlocked.

    Args:
        build: The imported build to check.
        module_catalog: Module blueprints for metadata lookup.
        unlocked_modules: Player's set of unlocked module IDs.

    Returns:
        List of dicts with module_id, name, category, unlock_method,
        unlock_source for each missing blueprint. Empty if all owned.
    """
    missing: list[dict] = []
    seen: set[str] = set()

    for placed in build.modules:
        mid = placed.module_id
        if mid in seen:
            continue
        seen.add(mid)

        if mid in unlocked_modules:
            continue

        module = module_catalog.get(mid)
        if module:
            missing.append(
                {
                    "module_id": mid,
                    "name": module.name,
                    "category": module.category,
                    "manufacturer": module.manufacturer,
                    "unlock_method": module.unlock_method,
                    "unlock_source": module.unlock_source,
                    "unlock_cost": module.unlock_cost,
                }
            )
        else:
            missing.append(
                {
                    "module_id": mid,
                    "name": mid,
                    "category": "unknown",
                    "manufacturer": "unknown",
                    "unlock_method": "unknown",
                    "unlock_source": "",
                    "unlock_cost": 0,
                }
            )

    return missing


# ============================================================================
# Blueprint Purchase
# ============================================================================


def purchase_module_blueprint(
    player: object,
    module_id: str,
    module_catalog: dict[str, ShipModule],
    price_modifier: float = 1.0,
) -> tuple[bool, str]:
    """Purchase a module blueprint at a station.

    Args:
        player: Player object with credits and unlocked_modules.
        module_id: ID of the module to purchase.
        module_catalog: Loaded module blueprints.
        price_modifier: Station-specific price multiplier.

    Returns:
        (success, message) tuple.
    """
    if module_id not in module_catalog:
        return False, "Unknown module"

    module = module_catalog[module_id]

    # Check if already owned
    if module_id in player.unlocked_modules:
        return False, f"Already owned: {module.name}"

    # Check unlock method — only purchasable modules can be bought
    if module.unlock_method not in ("purchase", "free"):
        method = module.unlock_method.replace("_", " ").title()
        return False, f"Not for sale (unlock via {method})"

    # Calculate price with station modifier
    price = int(module.unlock_cost * price_modifier)
    if price <= 0:
        # Free module — just unlock it
        player.unlocked_modules.add(module_id)
        return True, f"Blueprint acquired: {module.name}"

    # Check affordability
    if player.credits < price:
        return False, f"Cannot afford ({price:,} CR needed, you have {player.credits:,} CR)"

    # Purchase
    player.credits -= price
    player.unlocked_modules.add(module_id)
    return True, f"Blueprint acquired: {module.name} (-{price:,} CR)"


def get_station_modules(
    system_id: str,
    drydock_catalogs: dict[str, dict],
    module_catalog: dict[str, ShipModule],
) -> list[ShipModule]:
    """Get the list of module blueprints available at a station.

    Args:
        system_id: The station/system to check.
        drydock_catalogs: Per-station catalog data.
        module_catalog: All module blueprints.

    Returns:
        List of ShipModule objects available at this station, sorted by category then name.
    """
    catalog_entry = drydock_catalogs.get(system_id, {})
    module_ids = catalog_entry.get("modules_sold", [])

    modules = []
    for mid in module_ids:
        if mid in module_catalog:
            modules.append(module_catalog[mid])

    modules.sort(key=lambda m: (m.category, m.name))
    return modules
