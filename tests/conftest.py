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

Two autouse fixtures apply to every test: ``_reset_sim_rng_entropy`` restores
OS entropy for ``SimRng.from_entropy()`` after each test, and
``_act_two_v1_marker`` turns archived Act II v1 content on for tests marked
``act_two_v1``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


@pytest.fixture(autouse=True)
def _reset_sim_rng_entropy() -> Iterator[None]:
    """Restore OS entropy for ``SimRng.from_entropy()`` after every test.

    ``Game.seed_rngs`` (and any test that calls ``seed_entropy``) seeds a
    process-wide fallback. Without this reset, later entropy-defaulted models in
    the same xdist worker draw order-dependent streams. ``sim_rng`` imports no
    pygame; the import is local to match this file's convention.
    """
    yield
    from spacegame.sim_rng import seed_entropy

    seed_entropy(None)


@pytest.fixture(autouse=True)
def _act_two_v1_marker(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn archived Act II v1 content on for tests marked ``act_two_v1``.

    Imports are local so the SDL environment variables above are set before
    anything pulls in pygame.
    """
    if request.node.get_closest_marker("act_two_v1") is None:
        return
    import spacegame.config as sg_config
    from spacegame.data_loader import get_data_loader

    monkeypatch.setattr(sg_config, "ACT_TWO_V1_ENABLED", True)
    loader = get_data_loader()
    if not loader.lenses:
        loader.load_act_two_v1()
