"""PT-F: display flags composition for RESIZABLE window support.

The build_display_flags() helper composes pygame display flags based on
fullscreen state. In windowed mode, RESIZABLE lets the player drag the
window; in fullscreen, it has no effect and is excluded. pygame.SCALED
is always included because it handles rendering-to-window scaling while
keeping our logical coordinate space fixed.
"""

from __future__ import annotations

import pygame

from spacegame.engine.game import build_display_flags


class TestBuildDisplayFlags:
    def test_always_includes_scaled(self) -> None:
        """SCALED must be present in both modes — it's how we scale the
        logical render surface to the physical window."""
        assert build_display_flags(fullscreen=False) & pygame.SCALED
        assert build_display_flags(fullscreen=True) & pygame.SCALED

    def test_windowed_mode_includes_resizable(self) -> None:
        flags = build_display_flags(fullscreen=False)
        assert flags & pygame.RESIZABLE, "Windowed mode must allow window resize"

    def test_windowed_mode_excludes_fullscreen(self) -> None:
        flags = build_display_flags(fullscreen=False)
        assert not (flags & pygame.FULLSCREEN)

    def test_fullscreen_mode_includes_fullscreen(self) -> None:
        flags = build_display_flags(fullscreen=True)
        assert flags & pygame.FULLSCREEN

    def test_fullscreen_mode_excludes_resizable(self) -> None:
        """RESIZABLE is meaningless in fullscreen and should not leak through."""
        flags = build_display_flags(fullscreen=True)
        assert not (flags & pygame.RESIZABLE)

    def test_returns_int(self) -> None:
        """Flags must be an int (bitmask), not a pygame constant alone."""
        assert isinstance(build_display_flags(False), int)
        assert isinstance(build_display_flags(True), int)


class TestDisplayFlagsContract:
    """Integration-adjacent: confirm the flags round-trip through pygame's
    set_mode → get_flags() path."""

    def test_flags_accepted_by_set_mode(self) -> None:
        """The composed flags must be valid input to pygame.display.set_mode.

        We don't verify flag round-trip through get_flags() because the
        dummy SDL driver used in CI doesn't faithfully preserve every
        flag (SCALED depends on a fast renderer that's unavailable in
        headless mode). The contract we care about is "set_mode accepts
        these flags without raising"; real-driver behavior is out of
        scope for unit tests.
        """
        import os

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        if not pygame.get_init():
            pygame.init()
        flags = build_display_flags(fullscreen=False)
        surf = pygame.display.set_mode((1280, 720), flags=flags)
        assert surf is not None
