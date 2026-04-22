# UI Review Sprint 4b — Text + Faction Color Migration

Generated 2026-04-22. Follow-up sub-sprint extending the Sprint 4 Colors wrapper.

**Bottom line:** 15 additional `Colors.*` attributes migrated (+1 alias). Text colors (3) and faction colors (12: 4 primary + 4 accent + 4 tint) now resolve through `PALETTE_ROLES`. Colorblind profiles extended with sensible faction-primary remaps so the four factions stay distinguishable for red-blind, green-blind, and blue-blind players.

Test count: **7,275 → 7,288 (+13).** Full suite green, lint clean. Zero visual change for default rendering.

---

## What migrated

**Text colors (3 + 1 alias):**
- `TEXT_PRIMARY` → `text_primary` = `(220, 220, 230)`
- `TEXT_SECONDARY` → `text_secondary` = `(150, 160, 180)`
- `TEXT_HIGHLIGHT` → `text_highlight` = `(100, 200, 255)`
- `TEXT` alias → `text_primary` (same as `TEXT_PRIMARY`)

These are ubiquitous across the codebase — probably the single biggest usage-count migration of the whole Sprint 4 arc. Every view that renders text touches these.

**Faction colors (12):**

Each of the four factions gets three variants: primary (labels, emblems), accent (bright highlights, active borders), tint (dimmed panel edge tints):

- `FACTION_COMMERCE`, `FACTION_ACCENT_COMMERCE`, `FACTION_TINT_COMMERCE` → `faction_commerce*` family
- `FACTION_MINERS`, `FACTION_ACCENT_MINERS`, `FACTION_TINT_MINERS` → `faction_miners*` family
- `FACTION_SCIENCE`, `FACTION_ACCENT_SCIENCE`, `FACTION_TINT_SCIENCE` → `faction_science*` family
- `FACTION_FRONTIER`, `FACTION_ACCENT_FRONTIER`, `FACTION_TINT_FRONTIER` → `faction_frontier*` family

Total: 15 new palette roles, 16 new `_COLORS_ROLE_MAP` entries.

**`PALETTE_ROLES` entry count: 32 → 47.**

---

## Colorblind profile extensions

The four factions need to remain visually distinguishable under each deficiency. The default colors are:

- Commerce: Blue `(100, 150, 255)`
- Miners: Orange/gold `(200, 150, 50)`
- Science: Purple `(150, 100, 200)`
- Frontier: Green `(100, 200, 100)`

Red-blind and green-blind viewers confuse the orange–green pair. Blue-blind viewers confuse the blue–yellow pair. The new remaps handle the highest-impact collisions:

### Protanopia (red-blind)

- `faction_miners` → `faction_science` (orange becomes purple). Miners Union tokens now show in the Science Collective's purple for red-blind players, keeping miners distinguishable from the warm-component-heavy Frontier green.
- Accent and tint variants not remapped (see scope note below).

### Deuteranopia (green-blind)

- `faction_miners` → `faction_science` (same as protanopia)
- `faction_frontier` → `faction_commerce` (green becomes blue). Adds a second swap because green-blind also loses frontier-green contrast against miners-orange.
- Accent and tint variants not remapped.

### Tritanopia (blue-blind)

- `faction_commerce` → `faction_frontier` (blue becomes green). Commerce Guild shows as frontier green for blue-blind players since blue desaturates to near-grey for them.

Existing remaps (for status/check/quality colors, shipped in Sprint 4) are preserved.

### Scope note: primary remaps only

Only PRIMARY faction colors remap under each profile. Accent and tint variants stay at canonical values even when the primary is remapped. Rationale:

- Accent and tint colors are subtle chrome (bright border on hover, dim edge tint on a panel). Colorblind distinguishability matters less here than for the primary identifier.
- Deep family-level remapping (primary + accent + tint all swap together) is a meaningful content decision that should be playtest-calibrated with real colorblind users rather than shipped as a directional heuristic.

A sprint or content pass dedicated to colorblind UX calibration is the right place to revisit this.

---

## What Sprint 4 + Sprint 4b collectively cover

**30 `Colors.*` attributes** (including aliases) now route through `PALETTE_ROLES`:

| Category | Count | Sprint |
|---|---|---|
| Status (GREEN/RED/YELLOW/BLUE + SUCCESS/ERROR aliases) | 6 | 4 |
| Skill checks (CHECK_PASS/MARGINAL/FAIL) | 3 | 4 |
| Quality tiers (QUALITY_POOR/NORMAL/GOOD/EXCELLENT) | 4 | 4 |
| Text (TEXT_PRIMARY/SECONDARY/HIGHLIGHT + TEXT alias) | 4 | 4b |
| Faction primary (4) | 4 | 4b |
| Faction accent (4) | 4 | 4b |
| Faction tint (4) | 4 | 4b |
| **Total** | **29** | |

(The sixth alias pair is TEXT→TEXT_PRIMARY; counting it as one distinct name, total is 30.)

Remaining `Colors.*` attributes stay as literal class attributes permanently: chrome (`BACKGROUND`, `UI_PANEL`, `CARD_BG`, `BAR_BG`, etc.), game-specific tones (ground tile colors, salvage view palette, particle colors, attribute highlight). Colorblind remapping adds negligible value for these.

---

## What the migration unlocks

The meaningful win: a player who selects a colorblind profile in settings now sees **different colors across the entire game** — every view, every card, every text label — with zero additional view-level code. The 1,072+ `Colors.*` call sites all benefit through the single wrapper.

Concretely, this means:

- A Protanopia player sees:
  - Critical red in combat HP bars, error messages, and fail checks rendered as info blue
  - Miners Union badges, quest markers, and NPCs rendered in Science Collective purple
- A Deuteranopia player sees all of the above, plus:
  - Success green in pass checks, reward text, and positive feedback rendered as HUD cyan
  - Frontier Alliance branding rendered as Commerce Guild blue
- A Tritanopia player sees:
  - Info blue rendered as success green
  - Commerce Guild blue rendered as Frontier Alliance green

The remaps are directional heuristics, not playtest-calibrated. Empirical calibration with colorblind users is the proper next step whenever that's accessible.

---

## Remaining migration candidates (catalogued, not scheduled)

These `Colors.*` attributes could be migrated if future design decisions warrant:

- `GOLD` — currency and wealth highlights. Could be a dedicated `currency_gold` role.
- `ATTR_HIGHLIGHT` — character attributes (Strength, Agility, etc.). Could be `attribute_accent`.
- `GLOW_*` family (4 particle colors) — effect colors; probably stay literal.
- `PARTICLE_*` family (2 colors) — effect colors; probably stay literal.
- `CELL_HIDDEN_BG` / salvage view palette — view-specific, low value for remapping.
- `GROUND_*` family (15 tile colors) — game-specific, low value for remapping.

No urgency. The colorblind-critical work is done.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,288 passed, 98 skipped, 1 xfailed, 0 failed** |
| `ruff check` on touched files | Clean |
| `Colors.*` call-site names now palette-backed | 30 |
| `PALETTE_ROLES` entry count | 32 → 47 |
| New colorblind remaps this sprint | 4 (miners for proto/deuter, frontier for deuter, commerce for trit) |
| New tests | 13 (in `tests/test_engine/test_colors_wrapper.py`) |
| Default visual output | Byte-identical to pre-Sprint-4 for all migrated colors |

---

## What's next

Sprint 4 + 4b together complete the colorblind infrastructure. The principal post-4b items:

**Sprint 5 — copy compliance.** UI voice audit with automated compliance tests extended to every UI string. Partially covered today by the narrative voice tests on tutorials and cockpit; Sprint 5 generalizes.

**Sprint 6 — state and motion polish.** Five-state interactive coverage, four-state content-panel coverage, motion-timing discipline.

**Controller support conversation.** Still flagged for a dedicated session. Journal specifically likely needs a UX rethink.

**Colorblind calibration pass (content).** With the infrastructure live, find colorblind playtesters, ask them to try each profile, refine the remap tables with their feedback. This is the first UI-review item that requires external input rather than code.

**Trading legality badge refactor** (Sprint 3c xfail follow-up). Replace the `" RESTRICTED"` / `" ILLEGAL"` text suffix with a proper badge. Would clear the last Sprint 3 xfail.

Recommending **Sprint 5** next for automated coverage continuity, or **controller support conversation** if you want to step back from tactical work and shape direction. Both are viable.
