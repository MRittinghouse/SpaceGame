"""Tests for frozen-mode (PyInstaller) path resolution."""

import sys
from pathlib import Path
from unittest.mock import patch

from spacegame.config import _resolve_root


class TestResolveRoot:
    """_resolve_root() returns correct path in dev and frozen modes."""

    def test_dev_mode_returns_project_root(self) -> None:
        root = _resolve_root()
        # In dev mode, PROJECT_ROOT is two levels up from config.py
        assert root.is_dir()
        assert (root / "spacegame").is_dir()
        assert (root / "data").is_dir()

    def test_frozen_mode_returns_meipass(self, tmp_path: Path) -> None:
        fake_meipass = str(tmp_path)
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", fake_meipass, create=True):
                root = _resolve_root()
                assert root == tmp_path


class TestDataLoaderUsesConfigRoot:
    """DataLoader default data_dir derives from config.PROJECT_ROOT."""

    def test_default_data_dir(self) -> None:
        from spacegame.config import PROJECT_ROOT
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        assert loader.data_dir == PROJECT_ROOT / "data"
