# Views

All game screens extend `BaseView` and follow a strict lifecycle. See `base_view.py` for the abstract interface.

## BaseView Lifecycle

1. **`__init__()`** — Store references, create fonts, backgrounds, particle pools. Do NOT create pygame_gui elements here.
2. **`on_enter()`** — MUST call `super().on_enter()`. Initialize session data, call `_create_ui()`. Log entry with `logger.info()`.
3. **`update(dt: float)`** — Update background, particles, timers. Called every frame when active.
4. **`render(screen: pygame.Surface)`** — Draw to screen. Called every frame when active.
5. **`handle_event(event: pygame.event.Event)`** — Process pygame_gui button presses, mouse clicks, keyboard input.
6. **`on_exit()`** — MUST call `super().on_exit()`. Call `_destroy_ui()` to clean up all UI elements.

## Constructor Pattern

```python
def __init__(self, ui_manager: pygame_gui.UIManager, player: Player, ...):
    super().__init__()
    # 1. Dependencies
    self.ui_manager = ui_manager
    self.player = player
    self.next_state: Optional[GameState] = None

    # 2. Fonts (create once, reuse)
    self.title_font = pygame.font.Font(None, 32)
    self.info_font = pygame.font.Font(None, 20)

    # 3. UI element refs (Optional — created in _create_ui)
    self.some_button: Optional[pygame_gui.elements.UIButton] = None

    # 4. Visual systems
    self.background = AnimatedBackground("theme", WINDOW_WIDTH, WINDOW_HEIGHT, seed=42)
    self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    self._bg_dim.fill((0, 0, 0))
    self._bg_dim.set_alpha(120)
    self.particles = ParticlePool(100)
```

## _create_ui() / _destroy_ui()

Every view splits UI lifecycle into this paired pattern:

- **`_create_ui()`** — Instantiate all `pygame_gui` elements with `self.ui_manager`. Called from `on_enter()`.
- **`_destroy_ui()`** — Call `.kill()` on every element with null checks. Called from `on_exit()`.

Elements created in `_create_ui()` **must** be killed in `_destroy_ui()`. Leaking UI elements causes rendering artifacts and memory issues.

```python
def _destroy_ui(self) -> None:
    for elem in [self.buy_button, self.sell_button, self.list_panel]:
        if elem:
            elem.kill()
```

## State Transitions

```python
# Request transition by setting next_state
self.next_state = GameState.GALAXY_MAP

# Game.py reads this via get_next_state() and triggers transition
def get_next_state(self) -> Optional[GameState]:
    return self.next_state
```

Game.py checks `get_next_state()` each frame in `_handle_state_transitions()`, wraps changes in visual transitions, and resets the value.

## Render Order (back to front)

1. `self.background.render(screen)` — animated starfield
2. `screen.blit(self._bg_dim, (0, 0))` — dim overlay for readability
3. Title and header text
4. Main content (panels, lists, grids, cards)
5. `self.particles.render(screen)` — visual effects on top
6. Floating feedback messages (text that rises and fades)
7. Status/transaction messages at bottom of screen

## Message and Feedback Patterns

**Status messages** (bottom of screen, timed):
```python
def _show_message(self, msg: str) -> None:
    self.message = msg
    self.message_timer = 3.0
```

**Floating feedback** (rises from action point, fades):
```python
self.feedback_messages.append({
    "text": text, "x": x, "y": y, "timer": 1.0, "color": color
})
```

Decrement timers in `update()`, filter expired in `update()`, render if timer > 0.

## Registering a New View

1. Add `GameState.NEW_STATE` to the enum in `config.py`
2. Create `_ensure_<name>_view()` method in `Game` class (lazy initialization)
3. Inside that method: instantiate the view, call `self.state_manager.register_state()`
4. Add transition handling in `Game._handle_state_transitions()`
5. Wire up navigation from existing views (set `next_state` on button press)

## Mini-Game Views (Mining, Salvage, Refining)

- **Recreated** each visit via `_ensure_*_view()` — not persisted across state changes
- Accept config objects (e.g., `MiningConfig`) from `DataLoader` for per-system variation
- Accept `player.progression` reference for skill bonus calculations
- Return to `GameState.TRADING` when the player exits
