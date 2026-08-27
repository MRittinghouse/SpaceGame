"""Session-wide pytest configuration for the SpaceGame test suite.

Sets SDL_AUDIODRIVER and SDL_VIDEODRIVER to dummy before any pygame import.

``SDL_AUDIODRIVER=dummy`` switches SDL to a null audio driver.  pygame's
mixer APIs continue to function and report success; they just produce no
audible output.  Tests that exercise mixer state remain valid.

``SDL_VIDEODRIVER=dummy`` switches SDL to an off-screen display driver.
Any worker that boots a ``Game()`` instance without this env var races on
real display initialisation; under ``pytest -n auto`` with 32 workers that
race produced intermittent worker deaths (``[gwN] node down: Not properly
terminated``).  Setting it project-wide here, before any worker imports
pygame, eliminates the root-cause race.

Both vars are set with ``setdefault``, so a developer can override either
from the command line:
  SDL_VIDEODRIVER=directx SDL_AUDIODRIVER=directsound python -m pytest ...

This file must set the env vars at module import time so they land before
any test or fixture imports pygame.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
