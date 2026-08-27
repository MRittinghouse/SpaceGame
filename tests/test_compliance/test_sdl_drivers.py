"""Compliance: SDL_VIDEODRIVER and SDL_AUDIODRIVER must be dummy in the test suite.

Any worker that boots a Game() instance without SDL_VIDEODRIVER=dummy races on
real display initialisation.  Under pytest -n auto with 32 workers that race
produced intermittent [gwN] node down: Not properly terminated hangs.

Setting both vars in tests/conftest.py at import time is the fix (SUITE-1).
This test verifies the fix is in place so a future edit to conftest.py cannot
silently remove it.
"""

from __future__ import annotations

import os


class TestSDLDrivers:
    def test_sdl_videodriver_is_dummy(self) -> None:
        """SDL_VIDEODRIVER must be 'dummy' in the test environment."""
        val = os.environ.get("SDL_VIDEODRIVER")
        assert val == "dummy", (
            f"SDL_VIDEODRIVER is {val!r}; expected 'dummy'.\n"
            "tests/conftest.py must set os.environ.setdefault('SDL_VIDEODRIVER', 'dummy') "
            "before any pygame import.  Without this, workers that boot Game() instances "
            "race on real display initialisation and can hang or crash under -n auto."
        )

    def test_sdl_audiodriver_is_dummy(self) -> None:
        """SDL_AUDIODRIVER must be 'dummy' in the test environment."""
        val = os.environ.get("SDL_AUDIODRIVER")
        assert val == "dummy", (
            f"SDL_AUDIODRIVER is {val!r}; expected 'dummy'.\n"
            "tests/conftest.py must set os.environ.setdefault('SDL_AUDIODRIVER', 'dummy') "
            "before any pygame import."
        )
