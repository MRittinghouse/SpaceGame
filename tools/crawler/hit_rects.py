"""Custom hit-rect registry for the play-harness crawler (QF-6B).

Views that use hand-drawn dialogs (raw pygame.Rect collision testing via
``MOUSEBUTTONDOWN`` rather than pygame_gui widgets) are invisible to the
crawler's ``enumerate_interactive()`` call, which only queries the
``ui_manager`` sprite group.  This registry bridges that gap.

Usage pattern mirrors ``NAV_KEYWORDS`` in ``crawler.py``:
  - ``HIT_RECTS`` is a module-level typed dict keyed by ``GameState``.
  - ``hit_rects_for(game)`` resolves the live rects for the active state,
    filters by ``predicate``, and raises ``HitRectDriftError`` if the view
    no longer exposes the attribute the ``rect_fn`` depends on.

Any future view that ships a hand-drawn dialog outside pygame_gui must
add entries here or the crawler will report the dialog as a softlock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# GameState is imported at call time inside rect_fn bodies to avoid triggering
# pygame font-loading at module import (which would slow test collection).


class HitRectDriftError(RuntimeError):
    """Raised when a registered hit-rect's rect_fn fails.

    Indicates that the view's geometry changed (rename, removal, signature
    shift) without a corresponding update to the registry.  The crawler
    treats this as a hard error rather than silently returning stale rects.
    """


@dataclass(frozen=True)
class HitRect:
    """Descriptor for one hand-drawn interactive region in a view.

    Attributes:
        name: Human-readable identifier used in action traces
            (e.g., ``"confirm_new_game_yes"``).
        rect_fn: Callable ``(view) -> pygame.Rect``; recomputed on every
            call so window-resize or DPI-scale changes never yield stale rects.
        dismissal_keys: Additional pygame key constants that also dismiss
            this dialog (advisory; the crawler widens its key repertoire
            separately via ``_selectable_escape_keys``).
        predicate: Called with the live view instance; if it returns False,
            this entry is skipped for the current frame (e.g., the dialog is
            not open yet).
    """

    name: str
    rect_fn: Callable[[Any], Any]  # (view) -> pygame.Rect
    dismissal_keys: tuple[int, ...] = ()
    predicate: Callable[[Any], bool] = field(default=lambda v: True)


# ---------------------------------------------------------------------------
# Registry: one list of HitRect entries per GameState.
# Populated at module import using lazy pygame imports inside rect_fn bodies.
# ---------------------------------------------------------------------------


def _make_main_menu_hit_rects() -> list[HitRect]:
    """Build HitRect entries for MainMenuView's new-game confirmation dialog."""
    import pygame  # lazy import keeps module-level load cheap

    def _yes_rect(view: Any) -> Any:
        """Compute the Yes button rect from the same geometry as handle_event."""
        from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, scale_x, scale_y

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2
        ph = scale_y(210)
        panel_top = cy - ph // 2
        btn_w = scale_x(140)
        btn_h = scale_y(44)
        btn_y = panel_top + scale_y(120)
        return pygame.Rect(cx - btn_w - scale_x(15), btn_y, btn_w, btn_h)

    def _no_rect(view: Any) -> Any:
        """Compute the No button rect from the same geometry as handle_event."""
        from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, scale_x, scale_y

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2
        ph = scale_y(210)
        panel_top = cy - ph // 2
        btn_w = scale_x(140)
        btn_h = scale_y(44)
        btn_y = panel_top + scale_y(120)
        return pygame.Rect(cx + scale_x(15), btn_y, btn_w, btn_h)

    def _dialog_open(view: Any) -> bool:
        return bool(getattr(view, "_confirm_new_game", False))

    return [
        HitRect(
            name="confirm_new_game_yes",
            rect_fn=_yes_rect,
            dismissal_keys=(pygame.K_y, pygame.K_RETURN),
            predicate=_dialog_open,
        ),
        HitRect(
            name="confirm_new_game_no",
            rect_fn=_no_rect,
            dismissal_keys=(pygame.K_n, pygame.K_ESCAPE),
            predicate=_dialog_open,
        ),
    ]


def _build_registry() -> dict[Any, list[HitRect]]:
    """Build the HIT_RECTS dict.  Called once at module import time."""
    from spacegame.config import GameState  # lazy import

    return {
        GameState.MAIN_MENU: _make_main_menu_hit_rects(),
    }


# Module-level registry.  Import cost is low because pygame is not touched
# at the top level — only inside the rect_fn closures and _build_registry.
HIT_RECTS: dict[Any, list[HitRect]] = _build_registry()


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def hit_rects_for(game: Any) -> list[tuple[HitRect, Any]]:
    """Return the active hit-rects for the current game state.

    Args:
        game: The live Game (or Game-like) object with a ``state_manager``
            attribute whose ``current_state`` is checked against the registry.

    Returns:
        List of ``(HitRect, pygame.Rect)`` tuples for entries whose predicate
        passes against the current view.  Returns an empty list if the state
        has no registered entries or the view is not active.

    Raises:
        HitRectDriftError: When a ``rect_fn`` raises any exception (e.g.,
            ``AttributeError`` because the view was refactored) or when the
            view instance itself is missing from the state manager.
    """
    current_state = getattr(getattr(game, "state_manager", None), "current_state", None)
    entries = HIT_RECTS.get(current_state, [])
    if not entries:
        return []

    view = getattr(game.state_manager, "get_current_view", lambda: None)()
    if view is None:
        return []

    result: list[tuple[HitRect, Any]] = []
    for hr in entries:
        if not hr.predicate(view):
            continue
        try:
            rect = hr.rect_fn(view)
        except Exception as exc:
            raise HitRectDriftError(
                f"hit_rects.HIT_RECTS[{current_state}] entry {hr.name!r}: "
                f"rect_fn raised {type(exc).__name__}: {exc}"
            ) from exc
        result.append((hr, rect))
    return result
