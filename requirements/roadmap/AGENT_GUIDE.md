# Agent Guide — Multi-Agent Ralph Loop

How an agent loop runs against `ROADMAP.md`. How a single agent picks up, plans, executes, and validates a sprint.

The master file is `requirements/roadmap/ROADMAP.md`. Each sprint is an `<h3>` section anchored by its ID (e.g., `#SA-1`, `#CB-1`). Dispatcher hands an agent a sprint ID; agent reads only that section + its context links.

---

## Loop dispatcher (caller-side)

The dispatcher is what runs outside any single agent invocation. It's responsible for:

1. **Pickup decision**. Walk all sprint files, find ones with `Status: todo` whose dependencies are all `Status: done`. Filter out those with touch-zone conflicts against currently `in-progress` sprints. From the eligible set, select one (priority order: smaller sprints first to maintain flow, or strict dependency-graph topological order).
2. **Agent invocation**. Launch an agent with the sprint file path as the primary input. The agent's prompt is "execute this sprint per the conventions in `requirements/roadmap/CONVENTIONS.md` and `requirements/roadmap/AGENT_GUIDE.md`."
3. **Status reconciliation**. After the agent returns, parse the sprint file to confirm status moved to `review` or `done`. If the agent set `blocked`, surface for human review. If the agent crashed without updating, mark the sprint as `todo` again (with a note in Activity log) and the dispatcher decides whether to retry.
4. **Conflict detection**. Maintain a live set of touch zones reserved by `in-progress` sprints. Refuse to pick up a sprint whose touch zones overlap with the reserved set.

The dispatcher is OUT of scope for this doc — this guide assumes a working dispatcher and focuses on what the agent does once invoked.

---

## Agent workflow

When invoked with a sprint file:

### 1. Read the sprint file

Open the sprint file in full. Note `Status`, `Depends on`, `Touch zones`, `Acceptance criteria`. If `Status` is anything other than `todo` or `in-progress`, abort — something is wrong.

### 2. Read context

Walk every entry in `Context to read`. Read each in full unless the file is unreasonably large; for large docs, read targeted sections. Note assumptions, conventions, related code. Do NOT skim.

### 3. Plan

Fill in the `Plan` section of the sprint file. The plan should:
- Break the sprint into 3-10 concrete tasks.
- Identify the test surfaces (which test files, what to assert).
- Note risk areas — places where assumptions might be wrong, places where the spec is underspecified.
- Identify any decisions that should be locked before implementation begins.

If during planning you realize the sprint is genuinely larger than estimated (would require dramatically different scope or splitting into multiple sprints), STOP and:
- Set `Status` to `blocked` with a clear reason in `Notes`.
- Propose the sprint split or rescope in `Risks / open questions`.
- Append to `Activity log`.
- Return.

Do not unilaterally re-scope. Humans decide whether to split.

### 4. Update status

Move `Status` from `todo` to `in-progress`. Append a timestamped entry to `Activity log`. Commit this status change as a separate small commit so the dispatcher's view is consistent.

### 5. Implement (TDD)

For each task in the plan:
1. Write the failing test(s) that capture the acceptance criterion the task addresses.
2. Run tests, confirm they fail in the expected way.
3. Implement the minimum code to make them pass.
4. Refactor if needed.
5. Run the full test suite to confirm no regressions.

Commits during this phase:
- Reference the sprint ID in every commit message: `SA-1: add Wreckers' Guild Hall view skeleton`.
- Smaller commits over fewer larger ones — this lets the dispatcher recover from agent crashes mid-sprint.
- Run lint + format before each commit.

### 6. Validate against acceptance criteria

Walk every entry in `Acceptance criteria`. For each, write down (in `Activity log` or `Notes`) what specifically validates it: which test, which manual check, which output. If any criterion can't be validated, the sprint isn't done.

### 7. Run the full test suite

`python -m pytest -n auto -q` (per `CLAUDE.md`'s parallel testing convention). Record the test count delta in `Activity log`. If any tests fail, fix them or set `Status` to `blocked`.

### 8. Update status to review

Move `Status` to `review`. Append to `Activity log`. Commit this final state change.

### 9. Hand off

The dispatcher (or a follow-on validation agent, or a human) reviews and moves `Status` to `done` if all is well. If the validator finds issues, status moves back to `in-progress` and the original agent (or a new one) picks up the corrections.

---

## Required reading — every phase

Beyond this guide and `{CONVENTIONS_PATH}`, every phase agent must read these two docs at the start:

- **`requirements/agent_principles.md`** — meta-preferences for how to approach work on this project. Honesty over rubber-stamping, scope discipline, real engineering depth, when to block instead of guessing. Read in full once per phase.
- **`requirements/aurelia_voice_examples.md`** — paired wrong/right examples and a 16-item diagnostic checklist for player-facing voice. Read in full when authoring or modifying any player-facing content (NPC dialogue, missions, journals, ambient lines, tutorial copy, UI strings); skim at minimum if your sprint touches none of these.

These two docs concentrate judgment calls and pattern-matching that the per-prompt instructions and the Writing Bible scanner cannot encode.

---

## Constraints the agent must respect

### Code style and project conventions

Per `CLAUDE.md` at the repo root:
- Ruff format + lint, 100-char lines.
- MyPy strict typing.
- TDD — failing tests first.
- Google docstring style.
- No emojis unless explicitly requested.
- No em-dashes in user-facing content (Writing Bible).
- Models contain data + logic. Views own UI lifecycle. DataLoader is a singleton.

### Worldbuilding

Per `requirements/cultural_guide.md`, `requirements/dialogue_writing_guide.md`, and `requirements/aurelia_voice_examples.md`:
- Year 2335, Aurelia Expanse setting.
- Banned NPC names: Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose.
- No "couldn't help but," no "a testament to," no "no X, no Y" parallel-negation rhetoric (Reach tagline excepted).
- No GenAI tone defaults — read the writing guide AND the 30 paired examples in `aurelia_voice_examples.md`. The Writing Bible scanner is the floor; the examples doc is the standard.
- The scanner catches mechanical tells (em-dashes, banned phrases). It does not catch the structural tells in the diagnostic checklist (universal-wisdom NPCs, "Captain" default address, reverence-of-the-ordinary register, mysticism about the void). You are responsible for those.

### Onboarding principles

Per `requirements/onboarding_design.md` (six principles):
- Prefer character over UI overlays — but player experience wins.
- One NPC owns one cluster.
- Progressive disclosure.
- Transparency where the world can't narrate.
- Soft break into autonomy.
- Voice-check everything.

### Flag conventions

Cross-module flags go through `spacegame/constants/flags.py`. Per-view flags can be inline. Per-mission flags are in mission JSON `set_flag` actions.

### Commit hygiene

- Commit message references sprint ID.
- Commit message body explains WHY, not just WHAT.
- Co-author trailer included per CLAUDE.md.
- Smaller commits over larger when convenient for recovery.
- Never push without explicit human approval — the agent commits locally.

### Cost-conscious tool usage

The harness gives you broad agency: Write/Edit, Bash, Task (subagents), WebFetch, WebSearch are all available. With agency comes a small obligation to use cheaper tools first.

- **Read first, search second, delegate third.** If the answer is in a file you already know about, Read it. If you need to find a symbol, Grep it. Only spawn a Task subagent for parallel research that genuinely needs another context window (e.g., "audit 12 separate dialogue files for voice drift").
- **Don't WebFetch what's in CLAUDE.md or `requirements/`.** Project conventions, character voices, the Writing Bible, the architecture map are all in the repo. Only WebFetch external library docs (pygame, pytest, libraries you didn't write).
- **One Task subagent at a time, unless they're truly independent.** Three parallel subagents is great when each looks at a separate file set. Three subagents that all need the same context is a triple-cost duplicate.
- **Don't loop a tool to brute-force.** If a Grep returns no matches, don't run 8 variations. Re-read the surrounding context first.

These are guidance, not enforcement. The harness's per-phase timeout will eventually catch runaway loops, but the cost shows up earlier in your token budget.

---

## Sprint state machine — what to do when

| Sprint state | Agent action |
|---|---|
| `todo`, all deps done, eligible | Pick up. Move to `in-progress`. |
| `todo`, deps not done | Skip. Dispatcher should not have offered this. |
| `in-progress`, agent crashed earlier | Resume from Activity log. Re-read Plan. |
| `blocked` | Skip. Human needs to unblock. |
| `review` | Validate against Acceptance criteria. Move to `done` if all met. |
| `done` | Skip. |
| `aborted` | Skip. |

---

## Re-entrance and recovery

If a sprint's agent crashes mid-execution:

1. The next agent invocation finds `Status: in-progress` and reads the Activity log.
2. The Activity log should reflect commits made so far.
3. The new agent re-reads the Plan and resumes from the point implied by the log + the git state.
4. If the recovery path is unclear, the agent sets `Status: blocked` with reason and returns.

This is why per-task TDD with small commits matters — the file system + git history serve as the recovery state.

---

## Parallelism rules

The dispatcher decides which sprints run in parallel. From an individual agent's perspective:

- Don't read or modify another sprint's `Activity log` or `Status`.
- Don't modify files outside your sprint's `Touch zones`. If you discover you need to, set `Status: blocked` and explain.
- Don't run `git pull` mid-sprint — the dispatcher controls main-branch state.
- Don't push to remote — that's a human decision.

---

## What the agent never does

- Modify `INDEX.md` by hand (it's generated, or updated by a human / dispatcher).
- Skip the test suite "to save time."
- Mark a sprint `done` without satisfying every acceptance criterion.
- Change a sprint's `Touch zones` after starting.
- Pick up a sprint whose status is anything other than `todo` (resume) or `in-progress` (recovery).
- Touch another sprint's file.
- Push to remote.
- Create new sprint IDs without human approval.

---

## Escalation patterns

When the agent should escalate (set `Status: blocked` and stop):

- Acceptance criterion is unverifiable as written.
- Sprint scope is materially larger than estimated.
- A required design decision isn't locked.
- A dependency turns out to be insufficient (need to extend a system the dependency was supposed to deliver).
- A test that was passing before now fails for unclear reasons after sprint changes.
- The Writing Bible compliance scanner catches violations the agent can't reasonably eliminate.
- The change requires touching code outside the sprint's declared `Touch zones`.

When in doubt, escalate. A blocked sprint with a clear explanation is more useful than a half-done sprint with a confused commit history.
