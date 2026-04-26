# Roadmap Conventions

How `ROADMAP.md` is structured, lifecycled, and consumed by the multi-agent ralph loop.

---

## File layout

```
requirements/roadmap/
  ROADMAP.md           — single master file. All sprints live here as anchored sections.
  CONVENTIONS.md       — this file (sprint format, status flow, dependency rules).
  AGENT_GUIDE.md       — instructions for the loop dispatcher and per-sprint agents.
```

One file holds every sprint. Each sprint is an `<h3>` heading with a stable anchor (the sprint ID). The dispatcher and agents reference sprints by anchor (`ROADMAP.md#sa-1`, `ROADMAP.md#cb-1`, etc.).

---

## Why a single file with anchors

- **Atomic state.** All sprint statuses live in one file; the dispatcher reads one document to compute eligibility.
- **Anchor-based pickup.** The dispatcher tells an agent "execute the sprint at `#SA-1`" and the agent reads only that section.
- **Dependency graph in one place.** Cross-references (`Depends on: SA-PREP-1`) resolve in one file with no fragile path tracking.
- **Diffable.** Status transitions show up cleanly in `git log -p`.
- **Conflict-aware writes.** Agents only modify their own sprint section; git's line-level merge handles concurrent edits cleanly when sprints don't overlap.

---

## Sprint section template

Each sprint is an `<h3>` (`### SPRINT-ID — Title`). Stable IDs serve as anchors. Body fields are consistent:

```markdown
### SA-1 — Wreckers' Guild Hall (Salvage Contracts)

**Status**: todo
**Phase**: Phase I — Cluster B Anchors
**Size**: L
**Depends on**: SA-PREP-1, SA-A2, SA-B-EXT-1
**Blocks**: SA-P5, SA-B4
**Estimated effort**: 2-3 weeks

**Goal.** One paragraph. What this sprint achieves and why.

**Context to read.**
- `requirements/...`
- `spacegame/...`

**Touch zones.**
```
spacegame/views/wreckers_guild_view.py     (NEW)
spacegame/models/wreckers_guild.py          (NEW)
data/missions/wreckers_contracts.json       (NEW)
tests/test_models/test_wreckers_guild.py    (NEW)
```

**Deliverables.**
- New view: ...
- New model: ...
- N tests in ...

**Acceptance criteria.**
1. ...
2. ...

**Risks / open questions.**
- ...

**Activity log.**
- 2026-MM-DD — todo (created)

**Notes.** (Optional)
```

---

## Status lifecycle

```
todo → in-progress → review → done
                  ↘ blocked ↗
                  ↘ aborted (terminal, with reason in Notes)
```

- **todo**: not yet started. Eligible for pickup if dependencies are all `done` and touch zones don't conflict with `in-progress`.
- **in-progress**: an agent is actively working. Touch zones are reserved.
- **review**: implementation complete, tests passing, awaiting validation.
- **blocked**: agent encountered an issue requiring human input. Reason captured in Notes.
- **done**: terminal success. Acceptance criteria met, deliverables committed.
- **aborted**: terminal failure. Rare. Reason in Notes.

---

## Size scale

| Size | Effort | Typical scope |
|---|---|---|
| **S** | 1-3 days | One focused change |
| **M** | 3-10 days | One new view or model + tests + integration |
| **L** | 10-20 days | Multi-system change (a venue with shared infrastructure, multi-NPC arc) |
| **XL** | 20+ days | Whole subsystem (Politics core, Bidding mechanic) |

---

## Dependency rules

- A sprint can depend on any number of other sprints.
- A sprint becomes eligible (status can move from `todo` to `in-progress`) when ALL dependencies are `done`.
- Cycles are forbidden. Dispatcher detects and rejects cyclic dependencies.
- "Blocks" is the inverse of "Depends on" and is informational only (computed from the depends-on graph).

---

## Touch-zone conflict detection

Two sprints conflict if their touch zones overlap. The dispatcher reserves touch zones when a sprint moves to `in-progress` and releases them when it leaves.

- Glob patterns supported (`spacegame/views/*.py`).
- Single-file paths are exact matches.
- Conflicts are reported, not silently resolved. The loop picks a non-conflicting sprint instead.

When a sprint legitimately needs to share a touch zone with another in-progress sprint (e.g., both extend the same shared model), it lists the shared zone explicitly and the dispatcher serializes them.

---

## Concurrent-edit rules

Multiple agents writing to one file is safe IF:
- Each agent only modifies its own sprint section.
- Status updates are localized (a single line per sprint).
- The Activity log is append-only within each sprint.

Git's three-way merge handles these cleanly. The dispatcher should:
- Re-read `ROADMAP.md` before any write.
- Reject writes that touch sprints other than the agent's claimed sprint.
- Use `git add -p` or section-level patches if an agent's write spans non-sprint content (rare).

---

## Agent responsibilities per sprint

When an agent picks up a sprint:

1. Read its sprint section from `ROADMAP.md`.
2. Read all `Context to read` entries.
3. Plan the breakdown (record mentally; the master file does NOT carry per-sprint plan content — that lives in commits and Activity log entries).
4. Update `Status` to `in-progress` and append to `Activity log`. Commit this status change as a small commit.
5. Implement TDD-style.
6. Run lint + format + type-check + full test suite.
7. Commit. Reference the sprint ID in commit messages.
8. Update `Status` to `review` and append to `Activity log`.
9. If blocked, set `Status` to `blocked` with reason in Notes.

The agent never:
- Modifies another sprint's section.
- Pushes to remote.
- Skips the test suite.
- Marks `done` without satisfying acceptance criteria.
- Touches code outside the sprint's `Touch zones`.

---

## ID conventions

- **SA arc**: `SA-PREP-N` (Phase 0), `SA-A1`/`SA-A2` (Phase A), `SA-B-EXT-1` (Phase B), `SA-C1`/`SA-C2` (Phase C), `SA-N` (Phase I main), `SA-V` (Cargo Broker), `SA-PN` (Phase II Politics), `SA-BN` (Phase III Bidding), `SA-RN` (Phase IV Research), `SA-FN` (Phase V Financial), `SA-XN` (Phase VI Cohesion).
- **Followups**: prefix per topic (`CB-N` Crew Banter, `WB-N` Writing Bible scanner, `SI3-FOLLOW-N` flag scanner, `UI-BOUNDS-N` bounds harness).

---

## Adding a new sprint

1. Pick a stable ID per the conventions above.
2. Insert a new `<h3>` section in `ROADMAP.md` in the correct phase grouping. Status starts as `todo`.
3. Fill in all template fields.
4. Update the index table at the top of `ROADMAP.md`.
5. Commit with a clear message (`roadmap: add SA-X1 cross-anchor narrative threading`).
