"""Centralized keybinding system.

Provides a single source of truth for all keyboard shortcuts. Views
reference actions by name instead of hardcoding pygame key constants.
Player overrides are persisted in save settings.

Usage:
    from spacegame.engine.keybindings import get_keybindings
    kb = get_keybindings()
    if event.key == kb.get("trade_buy"):
        self._execute_buy()
"""

from typing import Optional

import pygame

from spacegame.utils.logger import logger

# Default keybindings (action_name -> pygame key constant)
_DEFAULT_BINDINGS: dict[str, int] = {
    # Trading
    "trade_buy": pygame.K_b,
    "trade_buy_max": pygame.K_m,
    "trade_sell": pygame.K_s,
    "trade_sell_max": pygame.K_x,
    "trade_sell_all": pygame.K_a,
    "trade_refuel": pygame.K_r,
    "trade_rest": pygame.K_t,
    "trade_tab_switch": pygame.K_TAB,
    # Navigation
    "nav_back": pygame.K_ESCAPE,
    "nav_confirm": pygame.K_RETURN,
    # Galaxy map
    "galaxy_journal": pygame.K_j,
    # Combat
    "combat_flee": pygame.K_f,
    "combat_execute": pygame.K_RETURN,
    "combat_undo": pygame.K_BACKSPACE,
    "combat_tab": pygame.K_TAB,
    "combat_ultimate": pygame.K_u,
    # Ship builder
    "builder_rotate": pygame.K_r,
    "builder_flip": pygame.K_q,
    "builder_mirror": pygame.K_x,
    "builder_tab": pygame.K_TAB,
    "builder_undo": pygame.K_z,
    "builder_redo": pygame.K_y,
}


class KeyBindings:
    """Manages keyboard shortcut bindings with player overrides."""

    def __init__(self) -> None:
        self._bindings: dict[str, int] = dict(_DEFAULT_BINDINGS)

    def get(self, action: str) -> int:
        """Get the key constant for an action.

        Args:
            action: Action name (e.g., "trade_buy").

        Returns:
            Pygame key constant, or 0 if action not found.
        """
        return self._bindings.get(action, 0)

    def set(self, action: str, key: int) -> None:
        """Override a keybinding.

        Args:
            action: Action name.
            key: New pygame key constant.
        """
        self._bindings[action] = key

    def reset_to_defaults(self) -> None:
        """Reset all bindings to defaults."""
        self._bindings = dict(_DEFAULT_BINDINGS)

    def get_action_label(self, action: str) -> str:
        """Get a human-readable label for the key bound to an action.

        Args:
            action: Action name.

        Returns:
            Key name string (e.g., "B", "Enter", "Escape").
        """
        key = self._bindings.get(action, 0)
        if key == 0:
            return "?"
        return pygame.key.name(key).upper()

    def get_all_bindings(self) -> dict[str, int]:
        """Get all current bindings."""
        return dict(self._bindings)

    def to_dict(self) -> dict[str, str]:
        """Serialize for save system (store key names, not ints)."""
        return {action: pygame.key.name(key) for action, key in self._bindings.items()}

    def load_overrides(self, data: dict[str, str]) -> None:
        """Load player overrides from saved data.

        Args:
            data: Dict of action -> key_name strings.
        """
        for action, key_name in data.items():
            if action in _DEFAULT_BINDINGS:
                try:
                    key = pygame.key.key_code(key_name)
                    self._bindings[action] = key
                except ValueError:
                    logger.warning(f"Unknown key name in keybindings: {key_name}")


# Singleton
_keybindings: Optional[KeyBindings] = None


def get_keybindings() -> KeyBindings:
    """Get the singleton KeyBindings instance."""
    global _keybindings
    if _keybindings is None:
        _keybindings = KeyBindings()
    return _keybindings
