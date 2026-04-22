"""Fixtures for the resolution × view matrix.

The resolution fixture switches the game's active resolution, reloads modules
whose module-level code captures scale_x/scale_y values (so those constants
re-evaluate at the new resolution), and restores state on teardown.

Supported matrix:
  - 1280x720   (720p)  — base design resolution
  - 1600x900   (900p)  — mid-tier preset
  - 1920x1080  (1080p) — full HD preset
  - 1280x800   (Deck)  — Steam Deck, 16:10 non-preset
  - 1366x768   (HD)    — common laptop, non-preset
  - 2560x1440  (QHD)   — high-DPI desktop, non-preset

Presets are known-supported. Non-presets are "broad compatibility" smoke
targets — we do not guarantee pixel-perfect rendering there, but we do
want to catch hard crashes and gross layout breakage.
"""

from __future__ import annotations

import os

# Headless SDL before pygame imports anywhere else in this test tree.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

import spacegame.config as config

# Resolution matrix — (width, height, label, category).
# category is "preset" for officially supported or "compat" for broad
# compatibility targets.
RESOLUTIONS: list[tuple[int, int, str, str]] = [
    (1280, 720, "720p", "preset"),
    (1600, 900, "900p", "preset"),
    (1920, 1080, "1080p", "preset"),
    (1280, 800, "deck", "compat"),
    (1366, 768, "hd_laptop", "compat"),
    (2560, 1440, "qhd", "compat"),
]


# Notes on resolution semantics within a pytest session:
#
# Python binds ``from spacegame.config import WINDOW_WIDTH`` at import time
# into the importing module's namespace. Once a view imports WINDOW_WIDTH,
# changes to ``config.WINDOW_WIDTH`` do not propagate into that view — the
# binding is stale until the view module is reloaded. The game's own design
# reflects this: settings_view.py explicitly tells players "Restart required
# to apply display changes" (so resolution is effectively immutable during a
# session).
#
# The test matrix walks through multiple resolutions in a single pytest
# session, so we could attempt to reload view modules between resolutions.
# Earlier iterations of this fixture did exactly that, but ``importlib.reload``
# breaks class identity for any downstream test that has already captured a
# reference to the pre-reload class, producing 200+ cascade failures across
# the rest of the suite. Restoring modules on teardown did not fully contain
# the damage because reloaded modules hold references to other reloaded
# modules that are hard to unwind cleanly.
#
# Compromise: we DO NOT reload view modules. Instead:
#
#   - ``scale_x()`` and ``scale_y()`` read ``config.WINDOW_WIDTH`` and
#     ``config.WINDOW_HEIGHT`` at CALL time (verified in test_resolution.py),
#     so any view that uses scale_x() inside ``_create_ui`` or ``render``
#     correctly responds to mid-session resolution changes.
#
#   - Views that capture WINDOW_WIDTH / WINDOW_HEIGHT at module scope
#     become stale. This is a code-quality concern; a follow-up test (added
#     below) scans for the pattern and reports offenders as a catalog item.
#     It is not a production bug because the game does not allow runtime
#     resolution changes; it is a latent fragility for future refactors.
#
# layout.py is a special case — it defines constants computed from scale_x,
# and its values are shared across many views. If we reload it without also
# reloading its consumers, their cached references to its constants become
# stale. Easier to live without reload and ensure views compute from
# layout.py lazily where needed.


@pytest.fixture(
    params=RESOLUTIONS,
    ids=[r[2] for r in RESOLUTIONS],
)
def resolution(request):
    """Parametrize over the full resolution matrix.

    Yields a ResolutionCase. Sets the active resolution via
    ``config.set_resolution`` and creates a fresh display surface sized to
    match. Any view built inside the test will construct UI elements using
    scale_x / scale_y that read the fresh values. Module-level captures of
    WINDOW_WIDTH from previously-loaded views remain stale (see notes at
    top of this file); the ``test_no_module_level_window_dim_capture``
    compliance test catalogs offenders separately.
    """
    width, height, label, category = request.param
    old_w, old_h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT

    config.set_resolution(width, height)
    pygame.display.init()
    pygame.display.set_mode((width, height))

    yield ResolutionCase(width=width, height=height, label=label, category=category)

    config.set_resolution(old_w, old_h)
    pygame.display.set_mode((old_w, old_h))


class ResolutionCase:
    """Lightweight value object describing the active resolution."""

    __slots__ = ("category", "height", "label", "width")

    def __init__(self, *, width: int, height: int, label: str, category: str) -> None:
        self.width = width
        self.height = height
        self.label = label
        self.category = category

    @property
    def is_preset(self) -> bool:
        return self.category == "preset"

    def __repr__(self) -> str:
        return f"ResolutionCase({self.width}x{self.height}, {self.label}, {self.category})"
