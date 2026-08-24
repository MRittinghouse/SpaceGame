# Raising-Accessor Pattern

**Applies to:** view classes and other components with `Optional[X]`
attributes whose lifetime is bounded by a well-defined start/stop pair
(usually `on_enter()` / `on_exit()`, sometimes `__init__` +
`shutdown()`).

**Introduced by:** QF-8. Named model for Spec B's `Game.player`.

## Why this pattern exists

Before QF-8, `Market`, `SalvageSession`, `MiningSession`, `RefiningSession`,
and several UI-element fields on views were all typed `Optional[X]` and
assigned inside `on_enter()`. Downstream methods used `self.market.get_price(...)`
without a guard, on the reasonable assumption that they only run
between `on_enter()` and `on_exit()`. MyPy correctly disagreed and
emitted ~90 `union-attr` errors.

Three fix shapes were considered:

| Fix | Erases N errors | Runtime safety improvement | Composes across a class |
|---|---|---|---|
| Local `assert self.market is not None` at each callsite | ~1 per callsite | No (assertion just crashes with a generic message) | No (verbose) |
| Sprinkled `if self.market is not None:` guards | ~1 per callsite | Slight (silent no-op instead of crash -- often worse) | No |
| **Raising accessor property (this doc)** | ~N in a single edit | Named `RuntimeError` at the exact lifecycle violation | Yes |

The raising accessor wins on all three axes for lifecycle-scoped
attributes. It is the pattern to reach for.

## The recipe

Start with:

```python
class TradingView(BaseView):
    def __init__(self, ...):
        self.market: Optional[Market] = None

    def on_enter(self) -> None:
        self.market = Market(...)

    def _execute_buy(self, cid: str) -> None:
        stock = self.market.get_stock(cid)          # ← mypy union-attr
        ...
```

Change to:

```python
class TradingView(BaseView):
    def __init__(self, ...):
        # QF-8 raising accessor: raw storage in `_market`, public
        # `market` @property is non-Optional and raises if unset.
        self._market: Optional[Market] = None

    @property
    def market(self) -> Market:
        """Return the live Market for this view's lifecycle.

        Raises:
            RuntimeError: If accessed before ``on_enter()`` or after
                ``on_exit()``.
        """
        if self._market is None:
            raise RuntimeError(
                "TradingView.market accessed before on_enter() "
                "(or after on_exit()); market is created inside on_enter "
                "and cleared on exit."
            )
        return self._market

    def on_enter(self) -> None:
        self._market = Market(...)          # ← assign to raw storage

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()
        self._market = None                 # ← clear on exit

    def _execute_buy(self, cid: str) -> None:
        stock = self.market.get_stock(cid)  # ← unchanged; property returns non-Optional
        ...
```

Notice:

- The **assignment** in `on_enter` moves to the underscore storage.
- `on_exit` also **clears** the underscore storage, so the accessor
  raises after exit too (not just before enter). Without this, a stale
  reference silently survives across `on_enter → on_exit → ...` cycles.
- Every read that used `self.market.X` is **unchanged** -- the property
  returns non-Optional `Market`, so mypy is happy and callers stay clean.
- The docstring names both the class and the lifecycle method, so the
  runtime `RuntimeError` message points a maintainer at the right file.

## Lifecycle-guard migration

The old code sometimes used the Optional attribute as a lifecycle
predicate:

```python
market_commodities = self.market.commodities if self.market else self.commodities
```

or

```python
if self.market and hasattr(self.market, "_player_supply_demand"):
    ...

if not self.session:
    return
```

These are the tricky part of the migration. **Every truth-test on the
public name must migrate to the raw underscore storage**, otherwise the
truth-test itself will trigger the accessor's `RuntimeError` on a fresh
instance:

```python
# BEFORE
if not self.session:
    return
if self.session.corruption_started:
    ...

# AFTER
if self._session is None:      # ← raw storage, truth-tests safe
    return
if self.session.corruption_started:  # ← inside the guarded block; property is fine
    ...
```

The rule of thumb: **inside `if self._x is not None:` blocks, use the
public property (`self.x`) freely -- mypy narrowed it in the enclosing
callsite, and the property returns non-Optional.**

Ternaries and compound conditions get the same treatment:

```python
# BEFORE
grid_size = self.session.derelict_type.grid_size if self.session else 5

# AFTER
grid_size = self._session.derelict_type.grid_size if self._session is not None else 5
```

Bulk-migrating a view with 25+ guards is mechanical enough to script
(see the sed-style loop used in QF-8's MiningView commit).

## When to apply

Apply the raising-accessor pattern when **all** of these hold:

1. The attribute is `Optional[X]` and typed that way today because it
   is created inside a lifecycle method (`on_enter`, `__init__` after
   some deferred init step, etc.) rather than in `__init__` directly.
2. The attribute has **multiple callsites** -- the pattern's payoff
   comes from collapsing many union-attr errors into a single property
   definition. For a one-off callsite, a local guard is fine.
3. Access outside the lifecycle window is a **bug**, not an expected
   state -- the property escalates it to `RuntimeError` at the exact
   point of misuse.

Canonical QF-8 examples:

- `spacegame/views/trading_view.py::TradingView.market` -- 26 callsites
  collapsed into one property.
- `spacegame/views/salvage_view.py::SalvageView.session` -- 25 callsites.
- `spacegame/views/mining_view.py::MiningView.session` -- 11 callsites.
- `spacegame/views/refining_view.py::RefiningView.session` -- 5 callsites.
- `spacegame/views/settings_view.py::SettingsView.apply_button` and
  `.save_dir_display` -- 6 and 2 callsites, both created inside
  `_create_ui`.
- `spacegame/views/save_load_view.py::SaveLoadView.confirm_button` --
  2 callsites.

## When NOT to apply

Use a local None-guard, not this pattern, when:

- **Single-callsite Optional.** Adding an accessor to a class for one
  read is scaffolding. Prefer `if x is None: return` or `x = a or default`.
  Examples in QF-8: `spacegame/models/salvage.py::SalvageSession.update`
  (single `cell.config` lookup); `spacegame/views/investment_view.py`
  (one `get_template()` chain); `spacegame/views/crew_roster_view.py`
  (one `crew_roster` access).
- **Transient per-frame values.** Rects computed inside `handle_event`
  or `render` are not lifecycle-scoped; a local narrowing after
  `getattr(self, "_x_rect", None)` is the right shape (see
  `spacegame/views/combat_view.py` void-release / overdrive rects).
- **Player-shaped attributes on shared models.** `Player.momentum` and
  friends are Player-domain, not view-domain. They are Spec B's terrain
  and get their own accessor unification pass there. In QF-8, callsites
  in `combat_engine.py` use local `is not None` guards rather than
  reaching across into Player's schema.
- **Cache lookups.** `dict.get(key)` legitimately returns None, and the
  callsite genuinely wants a fall-through path. Guard locally.

## Testing the contract

Every raising accessor gets a three-part regression test:

```python
def test_market_raises_before_on_enter(self) -> None:
    view = _make_trading_view()
    with pytest.raises(RuntimeError) as excinfo:
        _ = view.market
    msg = str(excinfo.value)
    assert "TradingView" in msg
    assert "market" in msg
    assert "on_enter" in msg

def test_market_returns_after_on_enter(self) -> None:
    view = _make_trading_view()
    view.on_enter()
    try:
        assert view.market is not None
    finally:
        view.on_exit()

def test_market_raises_after_on_exit(self) -> None:
    view = _make_trading_view()
    view.on_enter()
    view.on_exit()
    with pytest.raises(RuntimeError):
        _ = view.market
```

The four session-shaped views in QF-8 all have this test triplet in
`tests/test_views/test_view_accessor_contracts.py`. Copy the shape when
adding a new accessor.

## Test-code migration note

Tests that bypass `__init__` (e.g., `TradingView.__new__(TradingView)`)
and set `view.market = MagicMock()` will break: the property has no
setter, by design. Migrate those to `view._market = MagicMock()` -- the
raw underscore storage is what the property reads.

## Spec B cross-link

Spec A Section 4 names `Game.player` as the flagship application of
this pattern. When Spec B lands, `Game.player` becomes a raising
accessor with `_player` as raw storage, and the ~106 `Game.*.player.X`
union-attr errors currently baselined in `game.py` collapse into a
single edit. The doc here is the reference; the recipe is the same.
