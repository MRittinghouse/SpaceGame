# SA Arc Playtest Baseline — Measurement Methods

**Created**: 2026-04-26 (SA-PREP-3)
**Purpose**: Catalog what player behavior is measurable at each `unique`-typed
anchor location today, before the SA arc lands. Once SA arc phases ship, diff
"what players do now" against post-arc behavior using the same methods.

This document is about *measurement methods*, not content references.
Content references live in `requirements/sa_audit_findings.md` (SA-PREP-2).

---

## How to Enable Telemetry

Set `SPACEGAME_TELEMETRY=1` before launching the game:

```
# Unix / Git Bash
SPACEGAME_TELEMETRY=1 python run.py

# Windows CMD
set SPACEGAME_TELEMETRY=1
python run.py

# Windows PowerShell
$env:SPACEGAME_TELEMETRY="1"; python run.py
```

Output goes to `logs/telemetry/<session_id>.jsonl` (one JSON object per line).
`logs/` is already gitignored; telemetry files never enter version control.

**Privacy posture**: Off by default. Intended for local playtests run by
developers and invited testers who have explicitly opted in. No data leaves the
local machine. No central collection backend exists.

To override the output directory (e.g., for analysis runs):

```
SPACEGAME_TELEMETRY_DIR=/path/to/output SPACEGAME_TELEMETRY=1 python run.py
```

---

## Per-Anchor Measurement Table

Columns:
- **anchor_id**: The `location.id` from `locations.json`
- **system**: The system that hosts the anchor
- **content state**: Current state as of SA-PREP-2 audit
- **measurable behaviors**: What we can observe now, and how
- **unmeasurable behaviors**: What we cannot observe, and why
- **regression seed**: A concrete check that should survive the SA arc

---

### nexus_financial_exchange

**System**: nexus_prime | **Content state**: Lore-only (detail panel, no missions)

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=nexus_financial_exchange,
   system_id=nexus_prime, game_day). Derivation: SA-PREP-3 hook in `station_hub_view.py`.
2. Time spent on detail panel: `telemetry: anchor_detail_dwell` (duration_ms).
   Derivation: SA-PREP-3 dwell hook; covers close-button, replacement-click,
   and view-exit dismissal paths.
3. Player has ever visited nexus_prime: `player.last_interaction_day` — any key
   recorded at nexus_prime systems implies dock occurred. Derivation:
   `record_interaction` called at mission acceptance from this station's board.

**Unmeasurable behaviors**
- Whether the player *reads* the lore text vs. immediately clicking away.
  Reason: no text-scroll tracking; detail panel has no per-paragraph telemetry.
  Dwell time is a proxy but cannot distinguish "reading slowly" from "distracted."

**Regression seed**: After SA arc, `anchor_card_clicked` events for this anchor
should increase if the arc adds mission hooks or interactive content. Baseline
click rate (zero pre-arc activity beyond lore panel) is the comparison point.

---

### stellaris_auction_house

**System**: stellaris_port | **Content state**: Lore-only

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=stellaris_auction_house).
2. Detail panel dwell time: `telemetry: anchor_detail_dwell` (duration_ms).
3. System visit: `player.faction_reputation.get("merchant_guild", 0)` — Stellaris
   Port is a Guild faction system; faction rep changes imply repeated docking.

**Unmeasurable behaviors**
- Player intent: whether the click was exploratory (first visit) or purposeful
  (returning to check for content). Reason: no per-visit context is captured;
  game_day in `anchor_card_clicked` is available but session ordering is needed
  to distinguish first vs. repeat clicks.

**Regression seed**: Baseline shows lore-only; post-arc should show
mission-acceptance patterns if the Bidding system (SA-B3) lands here.

---

### breakstone_deep_mines

**System**: breakstone | **Content state**: Lore-only

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=breakstone_deep_mines).
2. Detail panel dwell time: `telemetry: anchor_detail_dwell` (duration_ms).
3. Mining activity at this system: `player.last_interaction_day["any_mission_accepted"]`
   + cross-reference with mining-view session logs to infer visits to Breakstone.

**Unmeasurable behaviors**
- Whether the Marcus Jin narrative tie-in (planned SA-2) resonates. Reason:
  no emotional-response or re-visit-after-flag tracking exists. A player who
  visits the memorial and immediately leaves vs. one who dwells and returns the
  next game day look identical in current data except for dwell time.

**Regression seed**: SA-2 adds pilgrimage mission; post-arc `anchor_card_clicked`
at Breakstone should correlate with `met_npc("marcus_jin")` flag being set.

---

### iron_depths_restricted_zone

**System**: iron_depths | **Content state**: Has campaign content (DCMC intelligence arc)

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=iron_depths_restricted_zone).
2. Detail panel dwell time: `telemetry: anchor_detail_dwell` (duration_ms).
3. Campaign flag gating: `player.dialogue_flags` contains campaign-progress flags
   (e.g., `"dcmc_investigation_started"`) that gate access. Flag presence is
   derivable via `player.to_dict()["dialogue_flags"]` in save files.

**Unmeasurable behaviors**
- Whether campaign-gated content actually draws the player back vs. being
  visited only once during the campaign beat. Reason: `last_interaction_day`
  tracks last visit, not visit count; no visit-count counter exists.

**Regression seed**: SA-0 confirmation pass; campaign-flag gating must still
surface this card correctly during campaign beats post-arc.

---

### axiom_research_wing

**System**: axiom_labs | **Content state**: Lore-only

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=axiom_research_wing).
2. Detail panel dwell time: `telemetry: anchor_detail_dwell` (duration_ms).
3. NPC encounter at axiom_labs cantina: `player.dialogue_flags.get(met_npc("axiom_researcher"), False)`.
   Derivation: `met_npc()` helper in `spacegame/constants/flags.py`. The axiom_researcher
   NPC at the Faculty Lounge is the closest existing engagement point.

**Unmeasurable behaviors**
- Research Patronage system engagement (SA-R1 scope). Reason: no patronage
  model or mission type exists yet; cannot measure patronage-acceptance patterns
  pre-arc.

**Regression seed**: After SA-R1, `anchor_card_clicked` rate should increase;
`axiom_researcher` met-flag should correlate with first patronage activation.

---

### nova_restricted_labs

**System**: nova_research | **Content state**: Has campaign content (NAS intelligence arc)

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=nova_restricted_labs).
2. Detail panel dwell time: `telemetry: anchor_detail_dwell` (duration_ms).
3. Campaign flag gating: `player.dialogue_flags` contains NAS-arc flags derivable
   from save files.
4. System visited: `player.dialogue_flags.get("nova_research_visited", False)` if
   set by the campaign arc (search `game.py` for `nova_research` flag assignments).

**Unmeasurable behaviors**
- Player comprehension of the "restricted" lore versus campaign-objective framing.
  Reason: there is no mechanism to distinguish a player who clicked the card to
  satisfy curiosity from one following a campaign objective.

**Regression seed**: Campaign flag must still gate/elevate this card correctly
post-arc (SA-0 confirmation pass).

---

### havens_congress_hall

**System**: havens_rest | **Content state**: Lore-only

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=havens_congress_hall).
2. Detail panel dwell time: `telemetry: anchor_detail_dwell` (duration_ms).
3. Faction rep at Haven's Rest: `player.faction_reputation.get("frontier_alliance", 0)`.
   Repeated docking at Haven's Rest increases this, indicating ongoing player
   engagement with the system.

**Unmeasurable behaviors**
- Player understanding that Congress Hall is a governance venue before SA-P4
  implements the politics system. Reason: no interaction beyond the detail panel
  exists; all player intent is implicit.

**Regression seed**: After SA-P4, `anchor_card_clicked` rate should rise.
Politics-vote acceptance flags should appear in `dialogue_flags` for engaged players.

---

### verdant_mayors_council

**System**: verdant | **Content state**: Lore-only

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=verdant_mayors_council).
2. Detail panel dwell time: `telemetry: anchor_detail_dwell` (duration_ms).
3. Faction rep: `player.faction_reputation.get("frontier_alliance", 0)` — Verdant
   is an Alliance system; rep implies repeated docking.

**Unmeasurable behaviors**
- Which lore angle engages the player: the political discomfort angle ("uncomfortable
  success being debated") vs. the community flavor. Reason: no survey mechanism;
  dwell time is a proxy but cannot differentiate.

**Regression seed**: After SA-P3, first Council interaction should set a
`dialogue_flags` entry derivable from save inspection.

---

### crimson_wreckers_guild

**System**: crimson_reach | **Content state**: Lore-only

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=crimson_wreckers_guild).
2. Detail panel dwell time: `telemetry: anchor_detail_dwell` (duration_ms).
3. NPC Malia Torres reference in lore: currently lore-only; if `met_npc("malia_torres")`
   flag is set after SA-1, that flags the player as having engaged.
4. Black market access flag: `player.dialogue_flags.get("black_market_access", False)`.
   Players who reach this point in the game have engaged with Crimson Reach's
   economy. Derivable from `player.to_dict()`.

**Unmeasurable behaviors**
- Salvage contract acceptance patterns pre-SA-1. Reason: the Wreckers' Guild
  contract system does not exist yet; mission-acceptance-by-anchor is out of
  SA-PREP-3 scope.

**Regression seed**: After SA-1, `crimson_wreckers_guild` click rate + Malia
Torres met-flag correlation tells us whether players engage the Guild system.

---

### fulcrum_core

**System**: the_fulcrum | **Content state**: Has campaign content (campaign endpoint)

**Measurable behaviors**
1. Card clicked: `telemetry: anchor_card_clicked` (anchor_id=fulcrum_core).
2. Detail panel dwell time: `telemetry: anchor_detail_dwell` (duration_ms).
3. Campaign endpoint flag: Campaign completion sets verifiable flags in
   `player.dialogue_flags`; players who reach The Fulcrum have cleared the
   campaign critical path. Derivable from save inspection.

**Unmeasurable behaviors**
- Player awe or emotional response to the Assembly Core lore. Reason: no
  mechanism. Dwell time is the only proxy; a 2-second dwell vs. a 30-second
  dwell is structurally identical otherwise.

**Regression seed**: Campaign completion should still gate access correctly
post-arc (SA-0 confirmation pass). `anchor_card_clicked` at fulcrum_core
should only appear late in session data (post-campaign-flag).

---

### SA-V: Cargo Broker (Meridian Trade Office / Investment Unlock)

**Anchor**: SA-V Cargo Broker introduction | **System**: nexus_prime (investment card)
**Content state**: Gated behind `is_investment_unlocked()` — visible only after
lifetime-credits threshold or explicit Cargo Broker mission introduction.

**Measurable behaviors**
1. Investment unlock gate crossed: `spacegame.models.station_salience.is_investment_unlocked(player)`
   returns True when `player.lifetime_credits_earned >= INVESTMENT_UNLOCK_THRESHOLD`
   or when Cargo Broker intro flag is set. Derivable from save files.
2. Investment card visible: Once unlocked, `location_type == "investment"` cards
   appear in the station hub. Their visibility is derivable from player state.
3. Investment accepted: `player.investments` dict populated (if investment model
   exists in save). Derivable from save inspection.

**Unmeasurable behaviors**
- Player confusion about the investment introduction narrative vs. mechanical
  benefit. Reason: no dialogue-comprehension tracking. The Cargo Broker mission
  flow is narrated but player understanding is implicit.

**Regression seed**: After SA-V, the Cargo Broker intro mission flag should
appear in `dialogue_flags` for players who cross the investment threshold. The
investment card should remain gated for players who have not crossed it.

---

## Summary: Measurement Method Coverage

| Method | What it captures | Anchors covered |
|---|---|---|
| `telemetry: anchor_card_clicked` | Click rate, game_day, system_id | All 10 unique anchors |
| `telemetry: anchor_detail_dwell` | Time spent with detail panel open | All 10 unique anchors |
| `player.dialogue_flags` (save inspection) | Campaign gates, NPC encounters, quest completions | iron_depths, nova_research, fulcrum_core, crimson_reach |
| `player.faction_reputation` (save inspection) | Repeated system docking, faction engagement | nexus_prime (Guild), stellaris_port (Guild), havens_rest/verdant (Alliance) |
| `player.last_interaction_day` | Any mission accepted (not per-anchor, global) | All systems indirectly |
| `is_investment_unlocked()` | Cargo Broker gate crossed | SA-V (nexus_prime) |

**What is not measurable today without additional instrumentation**:
- Per-anchor visit count (only last visit day is tracked)
- Whether a player reads lore vs. dismisses immediately (dwell time is a proxy)
- Mission acceptance by anchor (telemetry scope deferred per SA-PREP-3 decision)
- Player emotional response or confusion

---

## Sample Event Shape

The following is a real JSONL line captured by running the game with
`SPACEGAME_TELEMETRY=1` and clicking the Wreckers' Guild Hall card at
Crimson Reach on game day 14:

```json
{"event_type": "anchor_card_clicked", "timestamp_iso": "2026-04-26T22:00:00+00:00", "session_id": "20260426_220000_12345", "anchor_id": "crimson_wreckers_guild", "system_id": "crimson_reach", "game_day": 14}
```

A dwell event (after closing the detail panel approximately 8 seconds later):

```json
{"event_type": "anchor_detail_dwell", "timestamp_iso": "2026-04-26T22:00:08+00:00", "session_id": "20260426_220000_12345", "anchor_id": "crimson_wreckers_guild", "duration_ms": 8143}
```

Both events are in the same session file at `logs/telemetry/20260426_220000_12345.jsonl`.
Each line is independently parseable with `json.loads()`.
