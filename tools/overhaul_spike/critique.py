"""
Automated critique harness for the spike.

The agentic workflow doc named these dimensions; this file implements
the v1 checks. Each returns (passed, diagnostic_string) so the spike
runner can produce a structured report.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import pygame

from .palette import palette_array


@dataclass(frozen=True)
class CritiqueResult:
    name: str
    passed: bool
    diagnostic: str


# ---------------------------------------------------------------------------
# Palette compliance
# ---------------------------------------------------------------------------

def check_palette_compliance(
    surface: pygame.Surface,
    tolerance_rgb: float = 12.0,
    min_pct: float = 0.90,
) -> CritiqueResult:
    """Strict pointwise check: ≥min_pct of opaque pixels within tolerance of a palette color.

    Useful for flat pixel-art assets where every color IS a palette entry.
    For gradient-rendered assets (ships, modules with lighting), use
    ``check_palette_line_compliance`` instead — it tests that pixels lie
    on interpolations BETWEEN palette entries, which is the actual design
    intent of a gradient-shaded material.
    """
    palette = palette_array()  # (N, 3)
    rgb = pygame.surfarray.pixels3d(surface).astype(np.int32)
    alpha = pygame.surfarray.pixels_alpha(surface).astype(np.int32)
    diff = rgb[:, :, None, :] - palette[None, None, :, :]
    d2 = np.sum(diff * diff, axis=-1)
    min_d2 = d2.min(axis=-1)
    within = min_d2 <= (tolerance_rgb ** 2)
    opaque = alpha > 16
    opaque_count = int(opaque.sum())
    if opaque_count == 0:
        return CritiqueResult(
            "palette_compliance", False, "no opaque pixels in surface"
        )
    compliant = int((within & opaque).sum())
    pct = compliant / opaque_count
    ok = pct >= min_pct
    return CritiqueResult(
        "palette_compliance",
        ok,
        f"{pct:.1%} within {tolerance_rgb:.0f} RGB of palette (target {min_pct:.0%})",
    )


def check_palette_line_compliance(
    surface: pygame.Surface,
    tolerance_rgb: float = 10.0,
    min_pct: float = 0.95,
) -> CritiqueResult:
    """Gradient-aware palette compliance.

    A pixel is compliant if it lies within ``tolerance_rgb`` of ANY
    line segment between two palette entries. This matches the design
    intent of gradient-shaded materials: interpolated colors between
    palette points are on-palette in spirit, even if they aren't
    exact palette entries.

    Math per pixel p, segment (a, b):
        t = clamp(((p-a) . (b-a)) / ((b-a) . (b-a)), 0, 1)
        projected = a + t(b-a)
        dist = ||p - projected||
    Compliant if min dist across all segments <= tolerance.
    """
    palette = palette_array().astype(np.float32)  # (N, 3)
    N = palette.shape[0]
    rgb = pygame.surfarray.pixels3d(surface).astype(np.float32)
    alpha = pygame.surfarray.pixels_alpha(surface)
    opaque = alpha > 16
    if not opaque.any():
        return CritiqueResult(
            "palette_line_compliance", False, "no opaque pixels"
        )
    pixels = rgb[opaque]  # (P, 3)

    # Build all palette-to-palette segments: (M, 3) starts, (M, 3) ends.
    ia, ib = np.triu_indices(N, k=1)
    a = palette[ia]  # (M, 3)
    b = palette[ib]  # (M, 3)
    ab = b - a       # (M, 3)
    ab_len2 = np.sum(ab * ab, axis=-1)  # (M,)
    ab_len2 = np.where(ab_len2 == 0, 1e-9, ab_len2)  # guard

    # Broadcasting: pixels (P, 1, 3), a (1, M, 3), ab (1, M, 3), ab_len2 (1, M)
    pa = pixels[:, None, :] - a[None, :, :]  # (P, M, 3)
    t_raw = np.sum(pa * ab[None, :, :], axis=-1) / ab_len2[None, :]  # (P, M)
    t = np.clip(t_raw, 0.0, 1.0)
    proj = a[None, :, :] + t[:, :, None] * ab[None, :, :]  # (P, M, 3)
    diff = pixels[:, None, :] - proj
    d2 = np.sum(diff * diff, axis=-1)  # (P, M)
    min_d = np.sqrt(d2.min(axis=-1))   # (P,)
    compliant = int((min_d <= tolerance_rgb).sum())
    pct = compliant / pixels.shape[0]
    ok = pct >= min_pct
    return CritiqueResult(
        "palette_line_compliance",
        ok,
        f"{pct:.1%} within {tolerance_rgb:.0f} RGB of palette graph (target {min_pct:.0%})",
    )


# ---------------------------------------------------------------------------
# Silhouette readability
# ---------------------------------------------------------------------------

def check_silhouette_readability(
    surface: pygame.Surface,
    background_rgb: tuple[int, int, int] = (10, 12, 20),
    min_edge_contrast: float = 30.0,
) -> CritiqueResult:
    """Edge pixels should have ≥ min_edge_contrast against the scene bg.

    Uses alpha edge detection: where alpha transitions from 0 to >128, we
    look at the RGB value and compute Euclidean distance to the background.
    """
    alpha = pygame.surfarray.pixels_alpha(surface).astype(np.int32)
    rgb = pygame.surfarray.pixels3d(surface).astype(np.int32)
    # Simple edge: alpha > 128 AND at least one neighbor with alpha < 64.
    core = alpha > 128
    # Shift and compare
    pad = np.pad(alpha, 1, constant_values=0)
    neighbors_low = (
        (pad[:-2, 1:-1] < 64) | (pad[2:, 1:-1] < 64)
        | (pad[1:-1, :-2] < 64) | (pad[1:-1, 2:] < 64)
    )
    edge = core & neighbors_low
    if not edge.any():
        return CritiqueResult(
            "silhouette_readability", False, "no edge pixels detected"
        )
    bg = np.array(background_rgb, dtype=np.int32)
    edge_pixels = rgb[edge]
    diff = edge_pixels - bg
    contrasts = np.sqrt((diff * diff).sum(axis=-1))
    avg = float(contrasts.mean())
    ok = avg >= min_edge_contrast
    return CritiqueResult(
        "silhouette_readability",
        ok,
        f"avg edge contrast {avg:.1f} (target ≥ {min_edge_contrast})",
    )


# ---------------------------------------------------------------------------
# Alpha discipline
# ---------------------------------------------------------------------------

def check_alpha_discipline(surface: pygame.Surface) -> CritiqueResult:
    """Reject surfaces where a large band of pixels is mid-alpha (64..192).

    Mid-alpha pixels outside the expected antialiasing zone often
    indicate an accidental transparency bug. We allow a reasonable
    percentage from true antialiased edges (~10% typical).
    """
    alpha = pygame.surfarray.pixels_alpha(surface)
    total = alpha.size
    mid = int(((alpha >= 64) & (alpha <= 192)).sum())
    pct = mid / total
    ok = pct <= 0.15  # up to 15% mid-alpha is fine for AA edges
    return CritiqueResult(
        "alpha_discipline",
        ok,
        f"{pct:.1%} mid-alpha pixels (limit 15%)",
    )


# ---------------------------------------------------------------------------
# Determinism (by hash)
# ---------------------------------------------------------------------------

def hash_surface(surface: pygame.Surface) -> str:
    """SHA-256 of the raw pixel data. Used for determinism testing."""
    rgb = pygame.surfarray.pixels3d(surface)
    alpha = pygame.surfarray.pixels_alpha(surface)
    h = hashlib.sha256()
    h.update(rgb.tobytes())
    h.update(alpha.tobytes())
    return h.hexdigest()[:16]


def check_determinism(
    render_fn, *args, runs: int = 3, **kwargs
) -> CritiqueResult:
    """Render the same inputs N times; hash each; assert all identical."""
    hashes = []
    for _ in range(runs):
        surf = render_fn(*args, **kwargs)
        hashes.append(hash_surface(surf))
    ok = len(set(hashes)) == 1
    return CritiqueResult(
        "determinism",
        ok,
        f"{runs} renders produced {len(set(hashes))} distinct hash(es)",
    )


# ---------------------------------------------------------------------------
# Detail density (edge density via cheap Sobel)
# ---------------------------------------------------------------------------

def check_detail_density(
    surface: pygame.Surface,
    target_range: tuple[float, float] = (0.04, 0.35),
) -> CritiqueResult:
    """Edge-pixels per total-opaque-pixels — a cheap "busyness" metric.

    Too low = flat and lazy. Too high = unreadable noise.
    """
    rgb = pygame.surfarray.pixels3d(surface).astype(np.float32)
    alpha = pygame.surfarray.pixels_alpha(surface).astype(np.float32)
    # Convert to luminance for edge detection
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    # Cheap gradient magnitude
    dx = np.abs(np.diff(lum, axis=0, prepend=lum[:1]))
    dy = np.abs(np.diff(lum, axis=1, prepend=lum[:, :1]))
    grad = dx + dy
    edges = grad > 8.0  # threshold
    opaque = alpha > 16
    opaque_count = int(opaque.sum())
    if opaque_count == 0:
        return CritiqueResult(
            "detail_density", False, "no opaque pixels"
        )
    density = float((edges & opaque).sum()) / opaque_count
    lo, hi = target_range
    ok = lo <= density <= hi
    return CritiqueResult(
        "detail_density",
        ok,
        f"edge/opaque density = {density:.3f} (target {lo}-{hi})",
    )


# ---------------------------------------------------------------------------
# Variant distinctness — do N renders with different profiles differ?
# ---------------------------------------------------------------------------

def check_variant_distinctness(
    surfaces: list[pygame.Surface],
    min_mean_diff: float = 15.0,
) -> CritiqueResult:
    """Pairwise mean pixel-diff across N surfaces. Assets should be different.

    Compares ONLY opaque pixels (union of opaque regions across surfaces).
    Transparent pixels are uniformly 0 across variants and would dilute
    the metric toward zero for small subjects on a large canvas.
    """
    if len(surfaces) < 2:
        return CritiqueResult(
            "variant_distinctness", True, "only 1 variant — check skipped"
        )
    arrs = [
        pygame.surfarray.pixels3d(s).astype(np.int32) for s in surfaces
    ]
    # Union of opaque regions: any pixel that's opaque in at least one variant.
    alphas = [pygame.surfarray.pixels_alpha(s) for s in surfaces]
    union_opaque = np.zeros_like(alphas[0], dtype=bool)
    for a in alphas:
        union_opaque |= a > 16
    if not union_opaque.any():
        return CritiqueResult(
            "variant_distinctness", False, "no opaque pixels across any variant"
        )
    diffs = []
    for i in range(len(arrs)):
        for j in range(i + 1, len(arrs)):
            d = np.abs(arrs[i][union_opaque] - arrs[j][union_opaque]).mean()
            diffs.append(float(d))
    avg = float(np.mean(diffs))
    ok = avg >= min_mean_diff
    return CritiqueResult(
        "variant_distinctness",
        ok,
        f"pairwise mean RGB diff (opaque) = {avg:.1f} (target ≥ {min_mean_diff})",
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def format_report(asset_label: str, results: list[CritiqueResult]) -> str:
    lines = [f"CRITIQUE — {asset_label}"]
    passed = sum(1 for r in results if r.passed)
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        lines.append(f"  [{mark}] {r.name:28s} {r.diagnostic}")
    lines.append(f"  -> {passed}/{len(results)} checks passed")
    return "\n".join(lines)
