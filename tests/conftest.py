"""Session-wide pytest configuration for the SpaceGame test suite.

The only purpose right now: silence pygame audio output during tests.
Without this, every sound the game models would normally trigger (UI
clicks, dock chimes, weapon impacts, etc.) gets played to the system
audio device when the corresponding test runs. Across an 8000+ test
suite, that's a continuous cacophony — distracting and grating.

`SDL_AUDIODRIVER=dummy` switches SDL to a null audio driver. pygame's
mixer APIs (`pygame.mixer.init`, `Sound.play`, `Channel.set_volume`,
etc.) continue to function and report success; they just produce no
audible output. Tests that exercise mixer state remain valid.

The env var is set with `setdefault`, so a developer who explicitly
wants audio (e.g., debugging an audio-pipeline test by ear) can
override:
  SDL_AUDIODRIVER=directsound python -m pytest tests/test_engine/test_audio_orchestrator.py

This file must set the env var at module import time so it lands
before any test or fixture imports pygame.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
