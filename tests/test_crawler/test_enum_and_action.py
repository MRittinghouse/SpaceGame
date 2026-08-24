"""Element enumeration + action selection tests (QF-6, Task 3)."""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace

import pygame
import pygame_gui

from tools.crawler.crawler import Crawler, CrawlerFixtures


class FakeStateManager:
    def __init__(self) -> None:
        self.current_state = None
        self.state_stack: list = []

    def change_state(self, new_state: Any) -> None:
        self.current_state = new_state


class FakeGameWithUI:
    """Real pygame_gui UIManager wrapped by a minimal Game."""

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((800, 600))
        self.ui_manager = pygame_gui.UIManager((800, 600))
        self.state_manager = FakeStateManager()
        self.player = None

        from spacegame.engine.input_handler import InputHandler

        self.input_handler = InputHandler()

    def seed_rngs(self, seed: int) -> None:  # pragma: no cover - trivial
        return

    def initialize_states(self) -> None:  # pragma: no cover - trivial
        return


def _make_crawler(game: FakeGameWithUI, seed: int = 42) -> Crawler:
    crawler = Crawler(
        seed=seed,
        actions=0,
        fixtures=CrawlerFixtures(game_factory=lambda: game),
    )
    crawler.boot()
    return crawler


class TestEnumerateInteractive:
    """LOCKED: only enabled interactive types listed in ROADMAP count."""

    def test_enumerate_returns_only_enabled_interactive(self) -> None:
        game = FakeGameWithUI()
        # Two buttons: one enabled, one disabled. Enumeration must return
        # only the enabled one.
        enabled = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 10, 100, 30),
            text="Enabled",
            manager=game.ui_manager,
        )
        disabled = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(150, 10, 100, 30),
            text="Disabled",
            manager=game.ui_manager,
        )
        disabled.disable()

        crawler = _make_crawler(game)

        interactive = crawler.enumerate_interactive()
        assert enabled in interactive
        assert disabled not in interactive

    def test_enumerate_excludes_non_interactive_types(self) -> None:
        game = FakeGameWithUI()
        # UILabel is NOT in the interactive tuple, must not appear.
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(10, 10, 100, 30),
            text="Label",
            manager=game.ui_manager,
        )
        pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(150, 10, 100, 30),
            text="Real",
            manager=game.ui_manager,
        )

        crawler = _make_crawler(game)

        interactive = crawler.enumerate_interactive()
        assert len(interactive) == 1
        assert interactive[0].text == "Real"


class TestActionSelection:
    """Deterministic action selection given a fixed seed."""

    def test_action_selection_is_deterministic_per_seed(self) -> None:
        game_a = FakeGameWithUI()
        game_b = FakeGameWithUI()
        for game in (game_a, game_b):
            for i in range(5):
                pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(10 + i * 20, 10, 20, 20),
                    text=f"btn{i}",
                    manager=game.ui_manager,
                )

        crawler_a = _make_crawler(game_a, seed=99)
        crawler_b = _make_crawler(game_b, seed=99)

        seq_a = [crawler_a._select_action() for _ in range(30)]
        seq_b = [crawler_b._select_action() for _ in range(30)]

        # Kinds must match exactly. Element references differ (they are
        # constructed on different UIManagers) but element text/positions
        # come out of the identical RNG stream and therefore label chain.
        kinds_a = [a[0] for a in seq_a]
        kinds_b = [a[0] for a in seq_b]
        assert kinds_a == kinds_b, "action kinds diverge across identically-seeded runs"

    def test_action_selection_falls_back_when_no_interactive(self) -> None:
        game = FakeGameWithUI()
        crawler = _make_crawler(game, seed=1)
        # No interactive elements exist. Selection should not raise; it
        # should return either keypress or advance_time.
        for _ in range(20):
            action = crawler._select_action()
            assert action[0] in ("keypress", "advance_time")


class TestSelectableEscapeKeysIncludeDialogDismissal:
    """AC-4: K_y, K_n, K_RETURN, K_ESCAPE always appear in selectable escape keys."""

    def test_selectable_escape_keys_include_dialog_dismissal(self) -> None:
        """K_y, K_n, K_RETURN, K_ESCAPE must always be selectable from MAIN_MENU."""
        game = FakeGameWithUI()
        from spacegame.config import GameState

        game.state_manager.current_state = GameState.MAIN_MENU
        crawler = _make_crawler(game)

        selectable = crawler._selectable_escape_keys()

        for key_name, key_const in [
            ("K_y", pygame.K_y),
            ("K_n", pygame.K_n),
            ("K_RETURN", pygame.K_RETURN),
            ("K_ESCAPE", pygame.K_ESCAPE),
        ]:
            assert key_const in selectable, (
                f"pygame.{key_name} ({key_const}) must be in _selectable_escape_keys"
            )


class TestSessionTerminatingButtonsExcluded:
    """enumerate_interactive honours the identity-based terminator registry.

    Exclusion used to be text-based (``frozenset({"QUIT GAME"})``), which never
    matched the main menu's ``"Exit"`` button and let cold-boot crawls quit
    themselves. It is now keyed on object identity via
    ``tools/crawler/terminators.py``; see ``test_terminators.py`` for the unit
    coverage and the registry-completeness scan. This test covers the
    integration: that enumeration actually consults the registry.
    """

    def test_registered_terminator_is_excluded(self) -> None:
        game = FakeGameWithUI()
        quit_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 10, 100, 30),
            text="QUIT GAME",
            manager=game.ui_manager,
        )
        normal_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(150, 10, 100, 30),
            text="RESUME",
            manager=game.ui_manager,
        )
        # Register it the way the real game exposes it.
        game.pause_menu_view = SimpleNamespace(quit_button=quit_btn)

        crawler = _make_crawler(game)
        interactive = crawler.enumerate_interactive()

        assert quit_btn not in interactive, (
            "A registered session-terminating button must not be enumerated; "
            "clicking it ends the run."
        )
        assert normal_btn in interactive, (
            "Non-terminating buttons must still appear in enumerate_interactive"
        )

    def test_lookalike_text_is_not_excluded(self) -> None:
        """Text is deliberately NOT the signal.

        ``"Exit (Esc)"``, ``"LEAVE"`` and ``"Leave"`` all exist in the view
        layer and none of them terminate the session. A text blacklist wide
        enough to catch the real ``"Exit"`` would blacklist these too and
        shrink coverage while looking like a fix.
        """
        game = FakeGameWithUI()
        lookalike = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, 60, 100, 30),
            text="Exit (Esc)",
            manager=game.ui_manager,
        )
        crawler = _make_crawler(game)
        assert lookalike in crawler.enumerate_interactive()
