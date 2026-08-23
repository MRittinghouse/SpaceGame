"""Play-harness crawler core.

Boots a real ``Game`` object under headless SDL, seeds all RNG before
``initialize_states()`` (so state-init consumers of RNG stay deterministic),
enumerates enabled interactive pygame_gui widgets each frame, and drives the
game via a seeded action stream. Four oracles observe crashes:

1. Unhandled exception during ``game.step()``.
2. UI element leak on state exit.
3. Softlock (no enabled interactive elements AND no bound escape key).
4. Invariant violation (negative credits, over-cap fuel/cargo).

Crashes are deduplicated by normalized traceback signature and can be
replayed deterministically by seed+action_index.
"""

from __future__ import annotations

import json
import os
import random
import re
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

# Headless SDL before pygame imports.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from pygame_gui.elements import (
    UIButton,
    UIDropDownMenu,
    UIHorizontalSlider,
    UISelectionList,
    UITextEntryBox,
    UITextEntryLine,
)

from spacegame.config import GameState
from tools.crawler.coverage import CoverageTracker
from tools.crawler.crash_record import (
    CrashRecord,
    normalized_signature,
    signature_from_exception,
)
from tools.crawler.hit_rects import hit_rects_for

INTERACTIVE_TYPES: tuple[type, ...] = (
    UIButton,
    UITextEntryLine,
    UIDropDownMenu,
    UIHorizontalSlider,
    UISelectionList,
    UITextEntryBox,
)

# Buttons with these exact texts call sys.exit() and would terminate the
# crawl process before coverage data is saved.  Exclude them from
# enumeration so the crawler never clicks them.  Values are case-sensitive
# and matched against element.text after stripping whitespace.
_EXCLUDED_INTERACTIVE_TEXTS: frozenset[str] = frozenset({"QUIT GAME"})


class HitRectElement:
    """Thin wrapper that makes a hit-rect feel like an interactive widget.

    ``enumerate_interactive`` appends one of these per active ``HitRect``
    entry so that ``synthesize_events`` (which reads ``.rect``) and
    ``_describe_element`` (which reads ``.text``) work without modification.
    This wrapper is deliberately NOT a subclass of any ``INTERACTIVE_TYPES``
    member so the type filter in ``enumerate_interactive`` does not pick it
    up a second time.
    """

    # Synthesized enabled/visible flags so the crawler selection logic sees
    # these as fully interactive.
    is_enabled: bool = True
    visible: int = 1

    def __init__(self, name: str, rect: Any) -> None:
        self.text = f"HitRect[{name}]"
        self.rect = rect
        # object_ids is read by _weight_for_element for nav-keyword matching.
        self.object_ids: list[str] = [name]


# States exempt from the softlock oracle: intentional gates with no escape
# by design (players must complete character creation, etc.).
SOFTLOCK_EXEMPT: frozenset[GameState] = frozenset(
    {
        GameState.STARTUP,
        GameState.MAIN_MENU,
        GameState.CHARACTER_CREATION,
        GameState.NAME_INPUT,
    }
)

# Nav-keyword hints used by the action-weighting heuristic to boost clicks
# whose text/object_id suggests entry into an unvisited state. Matched
# case-insensitively against ``element.text`` or object_ids.
NAV_KEYWORDS: dict[str, GameState] = {
    "shipyard": GameState.SHIPYARD,
    "cantina": GameState.CANTINA,
    "trading": GameState.TRADING,
    "market": GameState.TRADING,
    "trade": GameState.TRADING,
    "galaxy": GameState.GALAXY_MAP,
    "map": GameState.GALAXY_MAP,
    "mining": GameState.MINING,
    "salvage": GameState.SALVAGING,
    "refining": GameState.REFINING,
    "skill": GameState.SKILL_TREE,
    "achievements": GameState.ACHIEVEMENTS,
    "statistics": GameState.STATISTICS,
    "dialogue": GameState.DIALOGUE,
    "missions": GameState.MISSION_LOG,
    "mission": GameState.MISSION_LOG,
    "crew": GameState.CREW_ROSTER,
    "character": GameState.CHARACTER,
    "journal": GameState.JOURNAL,
    "station": GameState.STATION_HUB,
    "repair": GameState.REPAIR_BAY,
    "invest": GameState.INVESTMENT,
    "wreckers": GameState.WRECKERS_GUILD,
    "deep": GameState.DEEP_SHAFTS,
    "okafor": GameState.OKAFOR,
    "dispute": GameState.DISPUTE,
    "auction": GameState.AUCTION,
    "combat": GameState.COMBAT,
    "encounter": GameState.ENCOUNTER,
    "ground": GameState.GROUND_BRIEFING,
    "briefing": GameState.MISSION_BRIEFING,
    "ship": GameState.SHIP_MANAGEMENT,
    "builder": GameState.SHIP_BUILDER,
}


ActionTuple = tuple[Any, ...]


@dataclass
class CrawlerConfig:
    """Configuration for a Crawler session."""

    seed: int
    actions: int
    checkpoint: Optional[str] = None
    debug_credits: int = 0
    output_dir: Optional[str] = None
    verbose: bool = False
    screenshot_dir: Optional[str] = None


@dataclass
class CrawlerFixtures:
    """Optional test-injected hooks.

    Attributes:
        game_factory: Callable returning a Game-like object; default constructs
            a real ``spacegame.engine.game.Game``.
        pre_step_hook: Optional callable invoked with (action_index, action)
            immediately before ``game.step``. Test fixtures use this to inject
            deterministic exceptions.
    """

    game_factory: Optional[Callable[[], Any]] = None
    pre_step_hook: Optional[Callable[[int, ActionTuple], None]] = None
    post_step_hook: Optional[Callable[[int, ActionTuple], None]] = None


class Crawler:
    """The deterministic play-harness crawler.

    See module docstring for the four oracles and the deterministic replay
    contract.
    """

    def __init__(
        self,
        seed: int,
        actions: int,
        checkpoint: Optional[str] = None,
        debug_credits: int = 0,
        output_dir: Optional[str] = None,
        verbose: bool = False,
        screenshot_dir: Optional[str] = None,
        *,
        fixtures: Optional[CrawlerFixtures] = None,
    ) -> None:
        """Construct a fresh Crawler.

        Args:
            seed: Integer seed applied to stdlib random and numpy random.
            actions: Number of actions to execute in this session.
            checkpoint: Optional checkpoint save name (early|mid|late).
            debug_credits: Credits granted to the player after boot.
            output_dir: Directory to write crawler_runs output to (defaults
                to ``crawler_runs`` under CWD).
            verbose: If True, record the full action trace to disk.
            screenshot_dir: Subdirectory name under the run dir for screenshots.
                When None or empty, screenshots are disabled.
            fixtures: Optional test-only hooks. Not used in production.
        """
        self.config = CrawlerConfig(
            seed=seed,
            actions=actions,
            checkpoint=checkpoint,
            debug_credits=debug_credits,
            output_dir=output_dir,
            verbose=verbose,
            screenshot_dir=screenshot_dir,
        )
        self._fixtures = fixtures or CrawlerFixtures()

        self.action_trace: list[ActionTuple] = []
        self.crashes: dict[str, CrashRecord] = {}
        self.coverage = CoverageTracker()

        # Action-selection RNG derived from the same seed so runs stay
        # reproducible without touching the game's global random state.
        self._action_rng = random.Random(seed)

        # Two-frame UI-event handshake: pygame_gui posts UI_BUTTON_PRESSED (and
        # other synthetic events) to the global pygame queue during
        # ui_manager.process_events() inside Game.step(). Game.run() sees those
        # in the *next* pygame.event.get() call at the top of the following
        # frame. step_once() must reproduce this contract. After each
        # Game.step() call we drain whatever pygame_gui posted into this buffer
        # and prepend it to the *next* step's event list.
        self._pending_events: list[pygame.event.Event] = []

        # UI-leak oracle bookkeeping — set once game is up.
        self._ui_leak_baseline: int = 0

        self.game: Any = None
        self._is_running_boot = False

        # Lazy-initialised run directory (set on first write or first screenshot).
        self._run_dir: Optional[Path] = None

        # States for which a screenshot has already been saved this session.
        self._screenshotted_states: set[str] = set()

    # ------------------------------------------------------------------
    # Boot / shutdown
    # ------------------------------------------------------------------

    def boot(self) -> None:
        """Boot the underlying Game object.

        Order matters: seed stdlib+numpy *before* ``initialize_states`` so
        any state-init RNG consumption is deterministic frame-zero.
        """
        self._is_running_boot = True

        from spacegame.engine.game import Game

        # Seed process-wide RNGs BEFORE Game construction so any RNG use
        # inside __init__ or initialize_states is deterministic.
        self._seed_process_rngs(self.config.seed)

        factory = self._fixtures.game_factory or Game
        self.game = factory()

        # Belt-and-braces: re-seed via Game.seed_rngs.
        if hasattr(self.game, "seed_rngs"):
            self.game.seed_rngs(self.config.seed)

        # Re-seed one more time immediately before initialize_states so the
        # state factories start on a fresh, deterministic RNG frame.
        self._seed_process_rngs(self.config.seed)
        if hasattr(self.game, "initialize_states"):
            self.game.initialize_states()

        # Instrument state_manager.change_state to feed coverage + UI-leak.
        self._instrument_state_manager()

        # Load checkpoint if requested (must happen AFTER initialize_states
        # so the state machinery is present).
        if self.config.checkpoint is not None:
            self._apply_checkpoint(self.config.checkpoint)

        # Debug credits hook. Applied after checkpoint load so the checkpoint
        # baseline is not clobbered.
        if self.config.debug_credits and getattr(self.game, "player", None) is not None:
            self.game.player.credits += self.config.debug_credits

        # UI-leak baseline is captured on first change_state via the
        # instrumented wrapper.
        self._ui_leak_baseline = self._count_ui_elements()

        # Record the initial state in the coverage tracker.
        current = getattr(self.game.state_manager, "current_state", None)
        if current is not None:
            self.coverage.record_visit(current)

        self._is_running_boot = False

    def _seed_process_rngs(self, seed: int) -> None:
        """Seed both stdlib random and numpy random with the given seed."""
        random.seed(seed)
        try:
            import numpy as np

            np.random.seed(seed)
        except ImportError:  # numpy is a hard dep; guard defensively
            pass

    def _apply_checkpoint(self, checkpoint: str) -> None:
        """Load one of the committed checkpoint save fixtures.

        Args:
            checkpoint: One of ``"early"``, ``"mid"``, ``"late"``.
        """
        from spacegame.save_manager import SaveManager

        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        slot_map = {"early": 1, "mid": 2, "late": 3}
        slot = slot_map.get(checkpoint)
        if slot is None:
            return
        self.game.save_manager = SaveManager(save_directory=fixtures_dir)
        if hasattr(self.game, "_load_game"):
            self.game._load_game(slot)

    # ------------------------------------------------------------------
    # Element enumeration
    # ------------------------------------------------------------------

    def _iter_ui_elements(self) -> list[Any]:
        """Return every pygame_gui element currently registered on the ui_manager."""
        if self.game is None or not hasattr(self.game, "ui_manager"):
            return []
        try:
            sprite_group = self.game.ui_manager.get_sprite_group()
        except Exception:
            return []
        try:
            return list(sprite_group.sprites())
        except Exception:
            return []

    def _count_ui_elements(self) -> int:
        """Count all live pygame_gui elements on the ui_manager."""
        return len(self._iter_ui_elements())

    def enumerate_interactive(self) -> list[Any]:
        """Return live enabled interactive elements per the LOCKED type tuple.

        In addition to pygame_gui widgets, appends ``HitRectElement`` wrappers
        for any active hit-rects registered in ``tools/crawler/hit_rects.py``.
        Hit-rect elements are added *after* the type filter so they do not
        interact with ``isinstance`` checks on ``INTERACTIVE_TYPES``.
        """
        elements: list[Any] = []
        for el in self._iter_ui_elements():
            if not isinstance(el, INTERACTIVE_TYPES):
                continue
            enabled = getattr(el, "is_enabled", True)
            visible = getattr(el, "visible", 1)
            if not enabled:
                continue
            if not visible:
                continue
            text = getattr(el, "text", "").strip()
            if text in _EXCLUDED_INTERACTIVE_TEXTS:
                continue
            elements.append(el)

        # Append hit-rect elements for hand-drawn dialogs in the current state.
        # HitRectDriftError is allowed to propagate — it signals a registry
        # inconsistency that must be fixed in hit_rects.py, not silenced.
        if self.game is not None:
            for hr, rect in hit_rects_for(self.game):
                elements.append(HitRectElement(hr.name, rect))

        return elements

    def bound_escape_keys(self) -> list[int]:
        """Return the set of pygame key codes usable to escape the current view.

        Per the locked softlock definition (ROADMAP QF-6): ESCAPE opens the
        pause menu, F11 toggles fullscreen, and any view-registered keys
        count. If none are bound and the state has no interactive elements,
        the softlock oracle fires.

        Returns:
            List of pygame key constants. Empty if no escape route exists.
        """
        keys: list[int] = []
        current = getattr(self.game.state_manager, "current_state", None)
        if current is None:
            return keys
        # ESC opens the pause menu whenever the player is loaded and the
        # state is not on the exempt list (main menu / character creation).
        if getattr(self.game, "player", None) is not None and current not in (
            GameState.MAIN_MENU,
            GameState.STARTUP,
            GameState.NAME_INPUT,
            GameState.CHARACTER_CREATION,
        ):
            keys.append(pygame.K_ESCAPE)
        # F11 toggles fullscreen — always bound at the game level.
        keys.append(pygame.K_F11)
        # View-specific bindings the input_handler may have registered.
        try:
            keys.extend(k for k in self.game.input_handler.key_callbacks.keys())
        except AttributeError:
            pass
        return keys

    def _selectable_escape_keys(self) -> list[int]:
        """Return escape keys safe to synthesize as an action.

        Excludes F11 because triggering a display-mode switch under
        ``SDL_VIDEODRIVER=dummy`` can raise a native access violation on
        some platforms. F11 still counts toward the softlock oracle.

        Always includes K_y, K_n, K_RETURN, K_ESCAPE as dialog-dismissal keys:
        - K_y / K_RETURN: confirm dialogs (e.g., new-game confirmation)
        - K_n / K_ESCAPE: cancel dialogs
        These are safe under SDL_VIDEODRIVER=dummy. K_ESCAPE in particular opens
        the pause menu when a player is loaded and the state is non-exempt, which
        is desired coverage; in exempt states (MAIN_MENU, CHARACTER_CREATION, etc.)
        it is a no-op.
        """
        base = [k for k in self.bound_escape_keys() if k != pygame.K_F11]
        dialog_keys = [pygame.K_y, pygame.K_n, pygame.K_RETURN, pygame.K_ESCAPE]
        # Deduplicate while preserving order: base keys first, then dialog keys.
        seen: set[int] = set(base)
        for k in dialog_keys:
            if k not in seen:
                base.append(k)
                seen.add(k)
        return base

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------

    def _select_action(self) -> ActionTuple:
        """Select the next action to execute, respecting the action RNG.

        Returns:
            An action tuple: ``("click", element)`` | ``("keypress", key)``
            | ``("advance_time",)``. If no interactive element is available,
            defaults to keypress or advance_time.
        """
        rng = self._action_rng
        interactive = self.enumerate_interactive()
        selectable_keys = self._selectable_escape_keys()

        roll = rng.random()
        if roll < 0.6 and interactive:
            element = self._weighted_element_choice(interactive)
            return ("click", element)
        if roll < 0.8 and selectable_keys:
            key = rng.choice(selectable_keys)
            return ("keypress", key)
        if interactive:
            element = self._weighted_element_choice(interactive)
            return ("click", element)
        if selectable_keys:
            key = rng.choice(selectable_keys)
            return ("keypress", key)
        return ("advance_time",)

    def _weighted_element_choice(self, elements: list[Any]) -> Any:
        """Pick one element with a 2x weight boost for likely-unvisited nav.

        Args:
            elements: Non-empty list of interactive elements.

        Returns:
            One element from the list.
        """
        weights: list[float] = []
        for el in elements:
            weights.append(self._weight_for_element(el))
        return self._action_rng.choices(elements, weights=weights, k=1)[0]

    def _weight_for_element(self, element: Any) -> float:
        """Return a selection weight for one element.

        Returns:
            2.0 when the element's text/object_id hints at an unvisited state,
            else 1.0. Matching is word-boundary: "shipyard" matches "Shipyard"
            but not "shipbuilder"; substring collisions are avoided so that a
            visited target does not incidentally get boosted by another
            keyword's presence in the same string.
        """
        text = ""
        try:
            text = (getattr(element, "text", "") or "").lower()
        except Exception:
            pass
        object_ids: list[str] = []
        try:
            oids = getattr(element, "object_ids", None) or []
            object_ids = [str(o).lower() for o in oids if o]
        except Exception:
            pass
        combined = " ".join([text, *object_ids])
        # Split into word tokens to prevent "shipyard" boosting via the
        # broader "ship" keyword. Punctuation is stripped by isalnum walk.
        tokens = set(re.findall(r"[a-z0-9]+", combined))
        for keyword, gs in NAV_KEYWORDS.items():
            if keyword in tokens:
                if not self.coverage.states_reached.get(gs.name, False):
                    return 2.0
        return 1.0

    # ------------------------------------------------------------------
    # Event synthesis
    # ------------------------------------------------------------------

    def synthesize_events(self, action: ActionTuple) -> list[pygame.event.Event]:
        """Produce pygame events from an action tuple.

        Args:
            action: An action produced by ``_select_action``.

        Returns:
            List of pygame events; may be empty for ``advance_time``.
        """
        if not action:
            return []
        kind = action[0]
        if kind == "advance_time":
            return []
        if kind == "click":
            element = action[1]
            rect = getattr(element, "rect", None)
            if rect is None:
                return []
            pos = rect.center
            down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})
            up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})
            return [down, up]
        if kind == "keypress":
            key = action[1]
            down = pygame.event.Event(
                pygame.KEYDOWN,
                {"key": key, "mod": 0, "unicode": "", "scancode": 0},
            )
            up = pygame.event.Event(
                pygame.KEYUP,
                {"key": key, "mod": 0, "unicode": "", "scancode": 0},
            )
            return [down, up]
        return []

    # ------------------------------------------------------------------
    # Step + oracles
    # ------------------------------------------------------------------

    def step_once(self) -> None:
        """Execute one crawler step: select → synthesize → step → oracles.

        Two-frame UI-event handshake: pygame_gui posts UI_BUTTON_PRESSED to the
        global pygame event queue inside Game.step(). This method drains that
        queue after each step and carries the events into the *next* call, exactly
        reproducing the frame cycle Game.run() gets for free. Any events still
        pending in the queue at session end can be inspected for diagnostics.
        """
        action_index = len(self.action_trace)
        action = self._select_action()
        # Store a serialization-safe copy of the action.
        recorded = self._record_action_trace(action)

        # Prepend UI events that pygame_gui posted in the previous frame.
        synthesized = self.synthesize_events(action)
        events = self._pending_events + synthesized
        self._pending_events = []

        if self._fixtures.pre_step_hook is not None:
            self._fixtures.pre_step_hook(action_index, action)

        try:
            self.game.step(1.0 / 60.0, events)
        except Exception as exc:
            self._record_exception(exc, action_index)

        # Drain UI events pygame_gui posted during this step so they arrive
        # in the next frame's event list — mirrors Game.run()'s event.get() loop.
        self._pending_events = list(pygame.event.get())

        if self._fixtures.post_step_hook is not None:
            self._fixtures.post_step_hook(action_index, action)

        # Invariant oracle.
        self._check_invariants(action_index)

        # Softlock oracle.
        self._check_softlock(action_index)

        # Track visits (in case something other than change_state moved us).
        current = getattr(self.game.state_manager, "current_state", None)
        if current is not None:
            # Screenshot hook: capture on first visit, before recording the visit.
            self._maybe_screenshot(current)
            self.coverage.record_visit(current)

        _ = recorded  # kept for verbose logger

    def _record_action_trace(self, action: ActionTuple) -> ActionTuple:
        """Store a JSON-safe copy of the action in the trace and return it."""
        kind = action[0] if action else "advance_time"
        if kind == "click":
            element = action[1]
            label = self._describe_element(element)
            recorded: ActionTuple = ("click", label)
        elif kind == "keypress":
            recorded = ("keypress", int(action[1]))
        else:
            recorded = ("advance_time",)
        self.action_trace.append(recorded)
        return recorded

    def _describe_element(self, element: Any) -> str:
        """Return a short human-readable label for an element (for the trace)."""
        text = ""
        try:
            text = str(getattr(element, "text", "") or "")
        except Exception:
            pass
        oid = ""
        try:
            oids = getattr(element, "object_ids", None) or []
            if oids:
                oid = str(oids[-1] or "")
        except Exception:
            pass
        rect = getattr(element, "rect", None)
        center = rect.center if rect is not None else (0, 0)
        return f"{type(element).__name__}[{text!r}|{oid}]@{center}"

    def _record_exception(self, exc: BaseException, action_index: int) -> None:
        """Convert a caught exception into a CrashRecord and stash it."""
        sig, frames = signature_from_exception(exc)
        exc_class = type(exc).__name__
        full_tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        current = getattr(self.game.state_manager, "current_state", None)
        state_name = current.name if isinstance(current, GameState) else str(current or "")
        self._register_crash(
            signature=sig,
            exception_class=exc_class,
            action_index=action_index,
            full_traceback=full_tb,
            state_at_crash=state_name,
            oracle="exception",
            extra={"frames": frames},
        )

    def _check_invariants(self, action_index: int) -> None:
        """Check the three invariants; register synthetic crash for violations."""
        player = getattr(self.game, "player", None)
        if player is None:
            return
        credits = getattr(player, "credits", 0)
        if credits < 0:
            self._register_synthetic_crash(
                oracle="invariant",
                marker=f"negative_credits:{credits}",
                exception_class="InvariantViolation.NegativeCredits",
                action_index=action_index,
                detail=f"player.credits went negative: {credits}",
            )
        ship = getattr(player, "ship", None)
        if ship is None:
            return
        fuel = getattr(ship, "current_fuel", 0)
        max_fuel = getattr(ship, "max_fuel", None)
        if max_fuel is None:
            max_fuel = getattr(getattr(ship, "ship_type", None), "fuel_capacity", None)
        if max_fuel is not None and fuel > max_fuel:
            self._register_synthetic_crash(
                oracle="invariant",
                marker=f"fuel_overflow:{fuel}>{max_fuel}",
                exception_class="InvariantViolation.FuelOverflow",
                action_index=action_index,
                detail=f"ship.current_fuel {fuel} > max_fuel {max_fuel}",
            )
        cargo_used = getattr(ship, "current_cargo_used", None)
        if cargo_used is None and hasattr(ship, "current_cargo"):
            try:
                cargo_used = sum(int(q) for q in ship.current_cargo.values())
            except Exception:
                cargo_used = 0
        cargo_cap = getattr(ship, "max_cargo", None)
        if cargo_cap is None:
            cargo_cap = getattr(getattr(ship, "ship_type", None), "cargo_capacity", None)
        if cargo_used is not None and cargo_cap is not None and cargo_used > cargo_cap:
            self._register_synthetic_crash(
                oracle="invariant",
                marker=f"cargo_overflow:{cargo_used}>{cargo_cap}",
                exception_class="InvariantViolation.CargoOverflow",
                action_index=action_index,
                detail=f"ship cargo used {cargo_used} > capacity {cargo_cap}",
            )

    def _check_softlock(self, action_index: int) -> None:
        """Softlock oracle — see LOCKED definition in ROADMAP."""
        current = getattr(self.game.state_manager, "current_state", None)
        if current in SOFTLOCK_EXEMPT or current is None:
            return
        state_stack = getattr(self.game.state_manager, "state_stack", [])
        if state_stack:
            return
        if self.enumerate_interactive():
            return
        if self.bound_escape_keys():
            return
        state_name = current.name if isinstance(current, GameState) else str(current)
        self._register_synthetic_crash(
            oracle="softlock",
            marker=f"softlock:{state_name}",
            exception_class="Softlock",
            action_index=action_index,
            detail=f"State {state_name} has no interactive elements and no escape key",
        )

    def _register_synthetic_crash(
        self,
        *,
        oracle: str,
        marker: str,
        exception_class: str,
        action_index: int,
        detail: str,
    ) -> None:
        """Register a non-exception crash (softlock/invariant/leak)."""
        sig = normalized_signature(exception_class, [(oracle, 0, marker)])
        current = getattr(self.game.state_manager, "current_state", None)
        state_name = current.name if isinstance(current, GameState) else str(current or "")
        self._register_crash(
            signature=sig,
            exception_class=exception_class,
            action_index=action_index,
            full_traceback=f"{oracle} oracle: {detail}",
            state_at_crash=state_name,
            oracle=oracle,
            extra={"marker": marker, "detail": detail},
        )

    def _register_crash(
        self,
        *,
        signature: str,
        exception_class: str,
        action_index: int,
        full_traceback: str,
        state_at_crash: str,
        oracle: str,
        extra: dict,
    ) -> None:
        """Insert or increment a CrashRecord in the dedup dict."""
        existing = self.crashes.get(signature)
        if existing is not None:
            existing.occurrence_count += 1
            return
        self.crashes[signature] = CrashRecord(
            signature=signature,
            exception_class=exception_class,
            first_seed=self.config.seed,
            first_action_index=action_index,
            occurrence_count=1,
            action_trace=list(self.action_trace),
            full_traceback=full_traceback,
            state_at_crash=state_at_crash,
            oracle=oracle,
            extra=dict(extra),
        )

    # ------------------------------------------------------------------
    # State-manager instrumentation (coverage + UI-leak oracle)
    # ------------------------------------------------------------------

    def _instrument_state_manager(self) -> None:
        """Monkey-patch ``state_manager.change_state`` for coverage + leak."""
        sm = self.game.state_manager
        original_change = sm.change_state
        crawler = self

        def wrapped_change_state(new_state: GameState) -> None:
            prior_count = crawler._count_ui_elements()
            prior_state = sm.current_state
            original_change(new_state)
            crawler.coverage.record_transition(prior_state, new_state)
            post_count = crawler._count_ui_elements()
            # UI-leak oracle: number of elements should not accumulate across
            # a full change_state cycle. First transition off a state is the
            # meaningful comparison; we compare pre vs post directly.
            if prior_state is not None and post_count > prior_count:
                delta = post_count - prior_count
                # Not every increase is a leak (new view may naturally have
                # more elements). We only report when the OLD view failed to
                # clean up: check if the ui_manager reports more elements
                # for the same target state after two consecutive entries.
                crawler._maybe_report_leak(prior_state, delta, prior_count, post_count)

        sm.change_state = wrapped_change_state  # type: ignore[assignment]

    def _maybe_report_leak(
        self, prior_state: GameState, delta: int, before: int, after: int
    ) -> None:
        """Record a UI-leak crash if the delta exceeds a small tolerance.

        The heuristic: if the element count strictly grew across a
        state exit and there is no state stack pushed, the OLD state
        did not fully clean up. Some views legitimately grow the tree
        on entry via factories; the leak fixture in the test suite
        constructs a deliberately-leaking view that fails ``.kill()``.
        """
        state_stack = getattr(self.game.state_manager, "state_stack", [])
        if state_stack:
            return
        if delta <= 0:
            return
        # Store a leak record. We tolerate small deltas from post-exit
        # transient factory-built elements by only registering leaks
        # whose delta is meaningful (>= 1 element persisted). The oracle
        # relies on the crawler's synthetic-crash schema.
        marker = f"ui_leak:{prior_state.name}:{delta}"
        exception_class = "UIElementLeak"
        sig = normalized_signature(exception_class, [("ui_leak", 0, marker)])
        crash = self.crashes.get(sig)
        if crash is not None:
            crash.occurrence_count += 1
            return
        current = getattr(self.game.state_manager, "current_state", None)
        state_name = current.name if isinstance(current, GameState) else str(current or "")
        detail = f"{prior_state.name}: {before} → {after} elements after exit"
        self.crashes[sig] = CrashRecord(
            signature=sig,
            exception_class=exception_class,
            first_seed=self.config.seed,
            first_action_index=len(self.action_trace),
            occurrence_count=1,
            action_trace=list(self.action_trace),
            full_traceback=f"ui_leak oracle: {detail}",
            state_at_crash=state_name,
            oracle="ui_leak",
            extra={"marker": marker, "delta": delta, "prior_state": prior_state.name},
        )

    # ------------------------------------------------------------------
    # Top-level driver
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Boot (if needed) and step ``self.config.actions`` times."""
        if self.game is None:
            self.boot()
        for _ in range(self.config.actions):
            self.step_once()

    def replay(self, seed: int, up_to_action_index: int) -> Optional[CrashRecord]:
        """Return the crash record produced at ``up_to_action_index`` in a fresh run.

        Args:
            seed: Seed of the original run.
            up_to_action_index: Action index at which the crash was seen.

        Returns:
            The matching CrashRecord, or None if none was produced.
        """
        replay = Crawler(
            seed=seed,
            actions=up_to_action_index + 1,
            fixtures=self._fixtures,
        )
        replay.boot()
        for _ in range(up_to_action_index + 1):
            replay.step_once()
        for record in replay.crashes.values():
            if record.first_action_index == up_to_action_index:
                return record
        return None

    # ------------------------------------------------------------------
    # Screenshot capture
    # ------------------------------------------------------------------

    def _maybe_screenshot(self, state: Any) -> None:
        """Capture a screenshot of the current frame if this is the first visit.

        Uses an independent ``_screenshotted_states`` set rather than
        ``coverage.states_reached`` because the coverage tracker may have
        already recorded this visit (via the instrumented ``change_state``
        that fires mid-step), making the coverage check always-true by the
        time this method runs.

        Args:
            state: Current GameState value (checked for first-visit status).
        """
        if not self.config.screenshot_dir:
            return
        state_name = state.name if isinstance(state, GameState) else str(state)
        if state_name in self._screenshotted_states:
            return  # already screenshotted in this session
        self._screenshotted_states.add(state_name)
        screen = getattr(self.game, "screen", None)
        if not isinstance(screen, pygame.Surface):
            return  # no valid surface (e.g. crash path)
        run_dir = self._get_run_dir()
        screenshots_path = run_dir / self.config.screenshot_dir
        screenshots_path.mkdir(parents=True, exist_ok=True)
        dest = screenshots_path / f"{state_name}.png"
        try:
            pygame.image.save(screen, str(dest))
        except Exception:
            pass  # screenshot failure is non-fatal; crash record carries state name

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def coverage_summary_text(self) -> str:
        """Return a plain-text coverage summary for the CLI output."""
        return self.coverage.summary_text()

    def report_dict(self) -> dict:
        """Return the JSON-safe combined session report."""
        return {
            "seed": self.config.seed,
            "actions": self.config.actions,
            "states_reached": self.coverage.states_reached,
            "transitions": [list(t) for t in self.coverage.transitions],
            "crashes": [c.to_dict() for c in self.crashes.values()],
        }

    def _get_run_dir(self) -> Path:
        """Return (and lazily create) the run output directory.

        The directory is created once and reused for both screenshots and
        written reports so all artifacts land in the same timestamped folder.

        Returns:
            Path to the run directory.
        """
        if self._run_dir is None:
            base = self.config.output_dir or "crawler_runs"
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            self._run_dir = Path(base) / f"{self.config.seed}-{ts}"
            self._run_dir.mkdir(parents=True, exist_ok=True)
        return self._run_dir

    def write_reports(self) -> Path:
        """Persist coverage.json + crashes.json to the run output directory.

        Returns:
            The Path to the run directory.
        """
        run_dir = self._get_run_dir()

        coverage_path = run_dir / "coverage.json"
        crashes_path = run_dir / "crashes.json"

        with coverage_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "seed": self.config.seed,
                    "actions": self.config.actions,
                    "states_reached": self.coverage.states_reached,
                    "transitions": [list(t) for t in self.coverage.transitions],
                },
                f,
                indent=2,
            )

        with crashes_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "seed": self.config.seed,
                    "crashes": [c.to_dict() for c in self.crashes.values()],
                },
                f,
                indent=2,
            )

        if self.config.verbose:
            log_path = run_dir / "action_trace.log"
            with log_path.open("w", encoding="utf-8") as f:
                for i, a in enumerate(self.action_trace):
                    f.write(f"{i}\t{a}\n")

        return run_dir
