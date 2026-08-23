"""Checkpoint fixture tests (QF-6, Task 12)."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from spacegame.save_manager import SaveManager  # noqa: E402


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tools" / "crawler" / "fixtures"


@pytest.fixture(scope="module")
def save_manager() -> SaveManager:
    return SaveManager(save_directory=FIXTURES_DIR)


class TestCheckpointFixtures:
    def test_early_checkpoint_present(self, save_manager: SaveManager) -> None:
        data = save_manager.load_game(1)
        assert data is not None
        player = data["player"]
        assert player.credits < 5000
        assert player.ship.ship_type.id == "shuttle"

    def test_mid_checkpoint_present(self, save_manager: SaveManager) -> None:
        data = save_manager.load_game(2)
        assert data is not None
        player = data["player"]
        assert 10_000 <= player.credits <= 100_000
        assert len(player.systems_visited) >= 3

    def test_late_checkpoint_present(self, save_manager: SaveManager) -> None:
        data = save_manager.load_game(3)
        assert data is not None
        player = data["player"]
        assert player.credits >= 100_000
        assert len(player.systems_visited) >= 5

    def test_all_fixture_files_committed(self) -> None:
        for slot in (1, 2, 3):
            path = FIXTURES_DIR / f"save_slot_{slot}.json"
            assert path.exists(), f"missing checkpoint fixture {path}"
