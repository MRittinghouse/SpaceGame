"""Tests for screen transition effects."""

import pygame
import pytest

from spacegame.engine.transitions import TransitionManager, TransitionType


@pytest.fixture(autouse=True, scope="module")
def _init_pygame() -> None:
    pygame.init()


@pytest.fixture()
def screen() -> pygame.Surface:
    return pygame.Surface((320, 240))


@pytest.fixture()
def manager() -> TransitionManager:
    return TransitionManager()


class TestTransitionLifecycle:
    """Transition starts, progresses, fires callback, and ends."""

    def test_not_active_initially(self, manager: TransitionManager) -> None:
        assert not manager.active

    def test_start_activates(self, manager: TransitionManager, screen: pygame.Surface) -> None:
        manager.start(TransitionType.FADE, 0.4, old_surface=screen)
        assert manager.active

    def test_callback_fires_at_midpoint(self, manager: TransitionManager, screen: pygame.Surface) -> None:
        called = []
        manager.start(TransitionType.FADE, 0.4, callback=lambda: called.append(True), old_surface=screen)
        manager.update(0.15)
        assert len(called) == 0
        manager.update(0.1)  # past midpoint (0.2)
        assert len(called) == 1

    def test_callback_fires_only_once(self, manager: TransitionManager, screen: pygame.Surface) -> None:
        count = [0]
        manager.start(TransitionType.FADE, 0.4, callback=lambda: count.__setitem__(0, count[0] + 1), old_surface=screen)
        manager.update(0.25)
        manager.update(0.05)
        manager.update(0.05)
        assert count[0] == 1

    def test_ends_after_duration(self, manager: TransitionManager, screen: pygame.Surface) -> None:
        manager.start(TransitionType.FADE, 0.4, old_surface=screen)
        manager.update(0.5)
        assert not manager.active

    def test_old_screen_cleared_on_end(self, manager: TransitionManager, screen: pygame.Surface) -> None:
        manager.start(TransitionType.FADE, 0.4, old_surface=screen)
        manager.update(0.5)
        assert manager.old_screen is None


class TestTransitionRendering:
    """Each transition type renders without error."""

    @pytest.mark.parametrize("ttype", list(TransitionType))
    def test_render_at_start(self, manager: TransitionManager, screen: pygame.Surface, ttype: TransitionType) -> None:
        manager.start(ttype, 0.4, old_surface=screen)
        manager.update(0.01)
        manager.render(screen)

    @pytest.mark.parametrize("ttype", list(TransitionType))
    def test_render_at_midpoint(self, manager: TransitionManager, screen: pygame.Surface, ttype: TransitionType) -> None:
        manager.start(ttype, 0.4, old_surface=screen)
        manager.update(0.2)
        manager.render(screen)

    @pytest.mark.parametrize("ttype", list(TransitionType))
    def test_render_near_end(self, manager: TransitionManager, screen: pygame.Surface, ttype: TransitionType) -> None:
        manager.start(ttype, 0.4, old_surface=screen)
        manager.update(0.38)
        manager.render(screen)

    def test_render_inactive_is_noop(self, manager: TransitionManager, screen: pygame.Surface) -> None:
        manager.render(screen)  # should not crash


class TestPixelateTransition:
    """PIXELATE transition produces visible pixelation effect."""

    def test_pixelate_modifies_screen(self, manager: TransitionManager) -> None:
        """At peak intensity, screen should be visibly different."""
        screen = pygame.Surface((160, 120))
        # Draw some content
        pygame.draw.circle(screen, (255, 0, 0), (80, 60), 30)
        original = screen.copy()

        manager.start(TransitionType.PIXELATE, 0.4, old_surface=screen)
        manager.update(0.2)  # midpoint = peak
        manager.render(screen)

        # Screen should differ from original
        assert screen.get_at((80, 60)) != original.get_at((80, 60)) or \
               screen.get_at((50, 30)) != original.get_at((50, 30))

    def test_pixelate_near_start_minimal_effect(self, manager: TransitionManager) -> None:
        screen = pygame.Surface((160, 120))
        manager.start(TransitionType.PIXELATE, 0.4, old_surface=screen)
        manager.update(0.005)
        manager.render(screen)  # Should not crash, minimal effect


class TestTransitionTypeEnum:
    """All expected transition types exist."""

    def test_fade_exists(self) -> None:
        assert TransitionType.FADE.value == "fade"

    def test_warp_exists(self) -> None:
        assert TransitionType.WARP.value == "warp"

    def test_slide_exists(self) -> None:
        assert TransitionType.SLIDE.value == "slide"

    def test_pixelate_exists(self) -> None:
        assert TransitionType.PIXELATE.value == "pixelate"

    def test_four_types(self) -> None:
        assert len(TransitionType) == 4
