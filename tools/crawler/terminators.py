"""Registry of interactions that end the game session.

The crawler must never trigger these. If it does, ``Game.running`` flips to
False, ``Game.step`` early-returns, and every remaining action in the session is
a silent no-op -- the run *looks* like it explored while doing nothing.

## Why identity, not text

The obvious guard is a text blacklist, and the crawler originally shipped one::

    _EXCLUDED_INTERACTIVE_TEXTS = frozenset({"QUIT GAME"})

The main menu's button reads ``"Exit"``, so that guard never matched and cold-boot
crawls were terminating themselves. The tempting repair is to widen the pattern to
``exit|quit|leave``. That is actively worse. The codebase contains::

    "Exit"        -> main menu, DOES terminate
    "QUIT GAME"   -> pause menu, DOES terminate
    "Exit (Esc)"  -> closes a view, does NOT terminate
    "LEAVE"       -> leaves a venue, does NOT terminate
    "Leave"       -> leaves a venue, does NOT terminate

A pattern blacklist would exclude three legitimate navigation buttons and shrink
coverage while appearing to fix the bug.

So this registry keys on **object identity**: the actual attribute on the actual
view whose handler terminates. Renaming a button's label cannot break it, and it
cannot over-match.

## Keeping this registry honest

A registry is only as good as its completeness, and nothing about adding a new
quit button forces anyone to update this file. That is what
``tests/test_crawler/test_terminators.py`` is for: it scans the view layer for
handlers that call ``sys.exit()`` or post ``pygame.QUIT`` and fails if any site
is not represented here. Add a terminator without registering it and the suite
tells you.
"""

from __future__ import annotations

from typing import Any

import pygame

from spacegame.config import GameState

# view attribute name on Game  ->  attribute names on that view whose handlers
# terminate the session.
TERMINATING_BUTTON_ATTRS: dict[str, frozenset[str]] = {
    "main_menu_view": frozenset({"exit_button"}),
    "pause_menu_view": frozenset({"quit_button"}),
}

# Keys that terminate the session while a given state is active. StartupView
# quits on ESC, so the crawler's escape-key repertoire is a second vector and
# not only its clicks.
TERMINATING_KEYS_BY_STATE: dict[GameState, frozenset[int]] = {
    GameState.STARTUP: frozenset({pygame.K_ESCAPE}),
}


def terminating_element_ids(game: Any) -> set[int]:
    """Return ``id()`` of every live element that would end the session.

    Identity-based on purpose: see the module docstring. Missing views and
    unset attributes are skipped rather than raising, because view lifecycle is
    lazy and most views do not exist at any given moment.

    Args:
        game: The live ``Game`` instance.

    Returns:
        Set of object ids to exclude from crawler enumeration.
    """
    ids: set[int] = set()
    if game is None:
        return ids

    for view_attr, button_attrs in TERMINATING_BUTTON_ATTRS.items():
        view = getattr(game, view_attr, None)
        if view is None:
            continue
        for button_attr in button_attrs:
            button = getattr(view, button_attr, None)
            if button is not None:
                ids.add(id(button))
    return ids


def terminating_keys(state: GameState | None) -> frozenset[int]:
    """Return key codes that would end the session in ``state``."""
    if state is None:
        return frozenset()
    return TERMINATING_KEYS_BY_STATE.get(state, frozenset())
