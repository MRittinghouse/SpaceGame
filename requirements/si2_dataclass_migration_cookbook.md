# SI-2 Dataclass Migration Cookbook

Recipe for migrating a module-level `list[dict]` content table into a
frozen dataclass. One page, scannable. Every SI-2 migration follows
this. Commit messages reference this doc by filename.

## Why migrate

The Stability Initiative origin bugs (`KeyError: 'slot_def_id'`, twice
in the same sprint) came from dict-indexed content. A typo in one
reader compiled cleanly and crashed at runtime in a cold code path.

Dataclass attribute access turns the typo into an immediate
AttributeError at access time — even if MyPy is bypassed by dynamic
dataflow. This is the stronger defense and the SI-3 rule for all new
content going forward.

## When to migrate (scope boundary)

**Migrate:** module-level *schema* tables where the keys are a fixed
shape. Examples: `TUTORIAL_PARTS` (every entry has `part_id`, `name`,
`cost`, …). Scanner B flags these automatically.

**Don't migrate:** nested *content-data* dicts where keys are
user-supplied IDs. Example: `Recipe.inputs: dict[str, int]` — the keys
are commodity_ids, which *are* content, not schema. Typifying them
would just swap dict-keyed content for a second dataclass layer with
the same semantics.

Rule of thumb: if the *keys* are a fixed vocabulary you could write in
an enum, migrate. If the keys are data the player or designer
supplies, leave it as a dict.

## The template

`spacegame/views/tutorial_shop_view.py` lines 47-63 (`TutorialPart`) is
the canonical reference. Frozen, explicit field list, no methods unless
the data genuinely has behavior (see `Recipe.can_craft` for an example
where methods belong on the type).

```python
@dataclass(frozen=True)
class TutorialPart:
    part_id: str
    name: str
    description: str
    cost: int
    narration: str
    tag: str
```

Declaration:

```python
TUTORIAL_PARTS: list[TutorialPart] = [
    TutorialPart(part_id="scrapyard_thruster", ...),
    ...
]
```

## Recipe

1. **Define the dataclass.** `@dataclass(frozen=True)`, explicit
   fields with types. Module-local unless the type needs to cross
   module boundaries (rare for content tables).

2. **Convert the declaration.** Replace
   `X: list[dict[str, Any]] = [{"k": "v", ...}, ...]` with
   `X: list[MyType] = [MyType(k="v", ...), ...]`. Keep the same
   variable name so call sites don't break on import.

3. **Grep-replace call sites.**
   `grep "X\[" spacegame/ tests/` — every indexer (`entry["foo"]`)
   becomes `entry.foo`. Ruff format after.

4. **Run the type check.** `mypy spacegame/` surfaces any reader that
   was doing `entry.get(k)` or passing the dict to a dict-typed
   helper — those need case-by-case fixes.

5. **Run the tests.** Fixtures that mirror the old dict shape will
   fail. Update them to construct real dataclass instances. See
   `tests/test_views/test_ship_builder_tutorial_narration.py::_tutorial_parts`
   for the pattern.

6. **Drop the allowlist entry.**
   `tests/test_compliance/test_list_dict_content_discipline.py` —
   remove the `<path>::<var>` line from `KNOWN_ORPHANS`. Re-run
   `pytest tests/test_compliance/`. Both assertions must pass: the new
   code is compliant, and the allowlist isn't stale.

7. **Commit.** Message references this doc:
   `SI-2: migrate <TableName> from list[dict] to dataclass (cookbook: requirements/si2_dataclass_migration_cookbook.md)`.

## JSON-loaded tables

If the table is loaded from JSON via `DataLoader._parse_*()`, add a
`from_dict` classmethod on the dataclass and update the loader to call
it. Keep `to_dict` only if the table is save-serialized (most content
tables aren't — they're loaded once at startup and never written).

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> "MyType":
    return cls(
        field_a=data["field_a"],
        field_b=data.get("field_b", 0),  # defaults for forward compat
    )
```

`Recipe.from_dict` in `spacegame/models/refining.py` is a working
example for JSON-backed content.

## What NOT to do

- Don't add a `__post_init__` validator unless the content is player-
  or modder-authored. Hand-authored JSON with a type hint is enough.
- Don't migrate to `TypedDict`. It catches typos in MyPy but not at
  runtime. Dataclass is the stronger defense and enables methods.
- Don't expand scope mid-migration. If you find a related dict that
  also needs migrating, file it for a follow-up commit.
- Don't add pydantic. See SI-2 design discussion — runtime
  validation's value doesn't clear the dependency-cost bar for us
  right now.

## Verification checklist

Before marking a migration done:

- [ ] `pytest tests/test_compliance/` — scanner passes, allowlist is not stale
- [ ] `ruff check spacegame/ tests/` — clean on touched files
- [ ] `mypy spacegame/` — no new errors
- [ ] Full test suite runs — no broken fixtures
- [ ] Commit message cites this cookbook by path
