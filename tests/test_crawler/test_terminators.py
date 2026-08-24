"""Session-terminating interactions must be excluded by identity, and the
registry that lists them must stay complete.

Background: the crawler originally excluded quit buttons by text
(``frozenset({"QUIT GAME"})``). The main menu's button reads ``"Exit"``, so the
guard never matched and cold-boot crawls terminated themselves at action zero,
then silently burned their remaining budget on no-ops. See
``tools/crawler/terminators.py`` for why widening the text pattern would have
been worse than leaving it broken.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pygame

from spacegame.config import GameState
from tools.crawler.terminators import (
    TERMINATING_BUTTON_ATTRS,
    TERMINATING_KEYS_BY_STATE,
    terminating_element_ids,
    terminating_keys,
)

VIEWS_DIR = Path(__file__).resolve().parents[2] / "spacegame" / "views"


class _FakeButton:
    pass


class _FakeView:
    def __init__(self, **attrs: object) -> None:
        for k, v in attrs.items():
            setattr(self, k, v)


class _FakeGame:
    def __init__(self, **views: object) -> None:
        for k, v in views.items():
            setattr(self, k, v)


class TestIdentityExclusion:
    def test_registered_button_is_excluded_by_identity(self) -> None:
        btn = _FakeButton()
        game = _FakeGame(main_menu_view=_FakeView(exit_button=btn))
        assert id(btn) in terminating_element_ids(game)

    def test_unregistered_button_is_not_excluded(self) -> None:
        """A button that merely *looks* like a quit button stays enumerable.

        This is the deliberate behaviour change. ``"Exit (Esc)"``, ``"LEAVE"``
        and ``"Leave"`` all exist in the view layer and none of them terminate
        the session; a text blacklist wide enough to catch ``"Exit"`` would
        blacklist those too and shrink coverage while appearing to fix a bug.
        """
        decoy = _FakeButton()
        game = _FakeGame(main_menu_view=_FakeView(exit_button=_FakeButton()))
        assert id(decoy) not in terminating_element_ids(game)

    def test_missing_view_is_tolerated(self) -> None:
        """View lifecycle is lazy; most views do not exist at a given moment."""
        assert terminating_element_ids(_FakeGame()) == set()
        assert terminating_element_ids(None) == set()

    def test_startup_escape_key_is_banned(self) -> None:
        """StartupView quits on ESC, so keys are a second termination vector."""
        assert pygame.K_ESCAPE in terminating_keys(GameState.STARTUP)

    def test_other_states_do_not_ban_escape(self) -> None:
        assert terminating_keys(GameState.GALAXY_MAP) == frozenset()
        assert terminating_keys(None) == frozenset()


class TestRegistryCompleteness:
    """The registry is only useful if it is complete.

    Nothing about adding a new quit button forces anyone to update
    ``terminators.py``. This scan finds every view module that terminates the
    process and fails when one is not represented in either registry, so the
    next terminator cannot be added silently.
    """

    @staticmethod
    def _modules_that_terminate() -> set[str]:
        found: set[str] = set()
        for path in VIEWS_DIR.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                # sys.exit(...)
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "exit"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "sys"
                ):
                    found.add(path.stem)
                # pygame.event.post(pygame.event.Event(pygame.QUIT))
                if isinstance(func, ast.Attribute) and func.attr == "post":
                    if "QUIT" in ast.dump(node):
                        found.add(path.stem)
        return found

    def test_every_terminating_view_is_registered(self) -> None:
        terminating = self._modules_that_terminate()
        assert terminating, "AST scan found no terminating views — the scan itself is broken."

        registered_by_button = set(TERMINATING_BUTTON_ATTRS)
        # States map to view modules by convention (STARTUP -> startup_view).
        registered_by_key = {f"{state.name.lower()}_view" for state in TERMINATING_KEYS_BY_STATE}
        covered = registered_by_button | registered_by_key

        missing = terminating - covered
        assert not missing, (
            "These view modules terminate the session but are absent from "
            "tools/crawler/terminators.py, so the crawler can quit its own "
            f"run by touching them: {sorted(missing)}. Register the button "
            "attribute (or the key, for keyboard-driven quits) there."
        )
