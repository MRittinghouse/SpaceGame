# Bidding System Design

**Sprint**: SA-B1 | **Phase**: III | **Author**: SA-B1 implementation agent

This document is the single source of truth for the Aurelia Bidding system. SA-B2 reads sections 1 through 8 before writing a line of code. SA-B3 (Stellaris Auction House) reads sections 2, 3, 4, 5, 7, 9, and 11. SA-B4 (Crimson Reach) reads sections 2, 3, 4, 5, 6, 7, 9, and 11. SA-B5 (Player-Initiated Auctions) reads sections 2, 3, 5, 8, and 11. SA-B6 (Polish and Tuning) reads sections 4, 5, and 10. The hand-off table at section 12 maps each downstream sprint to its relevant sections.

All decisions in section 11 are locked. SA-B2 implementers do not re-litigate locked decisions. Open items deferred to SA-B2 are explicitly named in section 10.

---

## 1. Scope and Relationship to Existing Systems

### 1.1 What the Bidding system does

The Bidding system is venue-based competitive acquisition. The player enters a specific location -- Stellaris Auction House (Stellaris Port) or the Crimson Reach Black Market (Crimson Reach) -- where lots are posted on a fixed schedule, AI bidder personas compete for the same lots, and the player wins by submitting the highest accepted bid above the lot's hidden reserve.

This is active competitive engagement. The player participates in real-time bidding, not just browsing a price board. Auction sessions persist across game sessions; a lot won in session two is remembered in session three. Named rivals carry history across sessions via CaptainMemory.

### 1.2 What the Bidding system is NOT

The Bidding system does not alter commodity market pricing. Lots traded in auctions are unique items, modules, and restricted commodities that do not exist in the bulk commodity market. Winning a legendary module at auction does not change the market price of common weapon components. The two systems are orthogonal. **Decision locked. See Section 11, decision 9.**

The Bidding system is not a replacement for the boss-drop pipeline. Legendary modules remain obtainable through combat; auctions provide a complementary acquisition path via re-issues and alternate variants. **Decision locked. See Section 11, decision 10.**

### 1.3 Venues

| Venue | Location | Access gate | Auction cadence | Lot categories |
|---|---|---|---|---|
| Stellaris Auction House | Stellaris Port | Stellaris Port standing tier | Every 5-7 game-days | Modules, antiquities, faction_commodity, art, rare_upgrade, derelict_rights |
| Crimson Reach Black Market | Crimson Reach | Wreckers' Guild membership tier | Irregular (demand-driven) | contraband, restricted_weapon, salvage_lot, faction_commodity |

### 1.4 Relationship to Wreckers' Guild membership (SA-1)

The Crimson Reach Black Market requires Wreckers' Guild membership to access. Membership tier (as established by SA-1) gates which lot tiers the player can bid on at the Reach:

| Wreckers' Guild tier | Lots accessible |
|---|---|
| Associate | Basic contraband, common salvage lots |
| Member | Restricted weapons, mid-tier faction commodities |
| Trusted | Premium contraband, high-value salvage |
| Veteran | All Reach lots including guild-reserve headliners |

Players without Wreckers' Guild membership cannot enter the Crimson Reach Black Market auction. The venue entry check happens at the station_hub_view navigation layer, before the auction view loads.

### 1.5 Relationship to Stellaris Port standing

Stellaris Auction House uses Stellaris Port standing to gate lot tiers:

| Stellaris Port standing tier | Lots accessible |
|---|---|
| Apprentice | Common modules, open-market antiquities |
| Regular | Faction-restricted commodities, mid-range modules |
| Certified | Legendary module re-issues, premium antiquities |
| Patron | All Stellaris lots including headliner events |

**Decision locked. See Section 11, decision 8.**

### 1.6 Module layout

```
spacegame/models/bidding_lot.py          -- NEW (SA-B2): AuctionLot frozen dataclass
spacegame/models/bidding_persona.py      -- NEW (SA-B2): AIBidderPersona, persona constants
spacegame/models/bidding_round.py        -- NEW (SA-B2): RoundState, bid tracking
spacegame/models/bidding.py              -- NEW (SA-B2): AuctionState manager
spacegame/views/auction_view.py          -- NEW (SA-B2): AuctionView
spacegame/config.py                      -- MODIFIED (SA-B2): GameState.AUCTION added
spacegame/constants/flags.py             -- MODIFIED (SA-B2): auction flag helpers added
```

---

## 2. Auction Lifecycle and Round Structure

### 2.1 Session schedule

**Stellaris Auction House**: Auctions fire every 5 to 7 game-days (randomly drawn in that range at the close of each session). The 5-7 day range introduces scheduling uncertainty without making the cadence feel unreliable. SA-B3 content authors set this in the venue config.

**Crimson Reach Black Market**: Auctions fire when the Wreckers' Guild's lot pool has accumulated enough items to fill a session (minimum 4 lots). The cadence is demand-driven rather than calendar-based, reinforcing the Reach's informal character. SA-B4 content authors define the accumulation threshold.

**Decision locked. See Section 11, decision 5.**

### 2.2 Session structure

A single auction session has five phases:

1. **Preview phase** (begins when the next auction is scheduled): Lots are visible in the auction house lobby. The player can review lot descriptions and categories. Estimated price ranges are hidden unless the player has the `lot_appraiser` skill (at any level). Preview phase ends when the session opens.

2. **Opening call** (session start): Cassian Velo (Stellaris) or the Reach floor manager announces the session. Rival bidder personas load their session configurations. The session lot list is final.

3. **Lot-by-lot bidding** (main phase): Each lot proceeds through one to three ascending bid rounds before closing. See section 2.3 for per-round structure.

4. **Post-session social phase**: After all lots close, a brief text-based social moment fires. Rivals who attended may comment on the session. Sable Trent (if crew) delivers a post-session read. Journal entries fire based on session outcomes. See section 9 for content details.

5. **Session close**: Auction state serializes. Last-auction-day records for the venue update. Next session is scheduled. The player returns to the station hub.

### 2.3 Per-round phase order (ascending bid model)

**Decision locked. See Section 11, decision 1.**

Each lot proceeds through ascending bid rounds. Standard lots run two rounds. Headliner lots run three rounds.

Each round has this exact phase order:

1. **Open call**: Velo announces the lot (first round only) or announces the current price (subsequent rounds). Current high bid is displayed. Timer starts.

2. **Bid window**: All bidders (player and AI) may submit bids. The minimum valid bid is the current price plus the minimum increment. The timer counts down. During the snipe window (see section 5.3), a single timer restart fires if anyone bids. After restart, no further restarts in that round.

3. **Round close**: Timer expires. If no new bids were submitted above the previous round's high, the lot closes at the current high bid (subject to reserve). If the round's winning bid exceeds the reserve, the lot sells. If multiple rounds remain, the next round opens at the current high bid.

4. **Lot resolution**: Sale confirmed (if reserve met), withdrawn (if reserve not met), or advanced to next round.

### 2.4 Time pressure speed setting

The player can adjust bid speed from the auction settings panel (accessible before the session opens):

| Setting | Round duration | Snipe window |
|---|---|---|
| Slow | 45 seconds | 5 seconds |
| Normal (default) | 30 seconds | 5 seconds |
| Fast | 15 seconds | 3 seconds |
| Asap | 8 seconds | 2 seconds |

Default is Normal. Setting persists per player (saved in player config, not per auction). **Decision locked. See Section 11, decision 6.**

On round timeout with no bids above the previous high: current high bidder wins the round. If it is the final round and reserve is met, that bidder wins the lot.

### 2.5 Multi-session persistence

In-progress auctions serialize at the session boundary (after section close, before the preview phase of the next session). The session cannot be resumed mid-lot. If the player leaves the auction house during a live lot, the player's position is dropped for that lot and the AI resolves the lot without player participation.

Active session state is stored in `player.auction_state.active_auction_id`. If `active_auction_id` is None, no auction is in progress and the player sees the preview or a "next auction in N days" message.

### 2.6 Auction lifecycle state diagram

```
                    [SCHEDULED]
                        |
               player enters auction house
               during preview window
                        |
                   [PREVIEW]
                        |
               session open time reached
                        |
                   [SESSION_OPEN]
                        |
             +----------+----------+
             |          |          |
         lot opens   lot closes  session ends
             |          |          |
         [LOT_OPEN] [LOT_CLOSED] [SESSION_CLOSE]
             |
         round fires
             |
     +-------+-------+
     |               |
  bid window     round expires
     |               |
  [BID_WINDOW]  [ROUND_CLOSE]
                     |
              more rounds? --- yes --> next LOT_OPEN round
                     |
                    no
                     |
               reserve check
                     |
            +--------+--------+
            |                 |
        met: SOLD        not met: WITHDRAWN
            |
      advance to next lot / session close
```

---

## 3. Lot Schema and Generation Algorithm

### 3.1 Lot schema (frozen dataclass)

SA-B2 implements `AuctionLot` as a `@dataclass(frozen=True)` in `spacegame/models/bidding_lot.py`.

Required fields:

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique lot identifier (e.g., `"kings_repeater_reissue_lot_2332"`) |
| `headline` | `str` | Display name shown in preview and during bidding |
| `description` | `str` | Flavor text paragraph (displayed in preview; collapsed in live round) |
| `category` | `str` | One of the category constants defined in `bidding_lot.py` |
| `venue` | `str` | `"stellaris"` or `"crimson_reach"` |
| `base_appraisal` | `int` | Fair market value in credits (used by AI personas, hidden from player by default) |
| `reserve_pct` | `float` | Reserve price as fraction of base_appraisal (range: 0.60 to 0.90) |
| `faction_gate` | `Optional[str]` | Faction ID required to see and bid on this lot (None = unrestricted) |
| `rep_tier_required` | `str` | Minimum standing tier string: `"apprentice"`, `"regular"`, `"certified"`, `"patron"`, or `"none"` |
| `is_headliner` | `bool` | True if this lot runs three rounds instead of two |
| `season_tag` | `Optional[str]` | Links to a seasonal event that boosts this lot's pool weight (None = untagged) |
| `contraband` | `bool` | True if this lot triggers legal-consequence checks at Stellaris |
| `source_module_id` | `Optional[str]` | For module re-issues: links to the canonical module ID in `modules.json` |
| `recently_seen_count` | `int` | How many sessions this lot has been in the pool unsold (used for exclusion logic) |

Derived property (computed, not stored):

| Property | Computation |
|---|---|
| `reserve_price` | `int(base_appraisal * reserve_pct)` |

### 3.2 Lot categories

```python
LOT_CATEGORY_MODULE = "module"              # ship module (legendary re-issue or premium)
LOT_CATEGORY_ANTIQUITY = "antiquity"        # pre-Compact artifact, art, historical items
LOT_CATEGORY_FACTION_COMMODITY = "faction_commodity"  # restricted supply goods
LOT_CATEGORY_RARE_UPGRADE = "rare_upgrade"  # non-module ship upgrade
LOT_CATEGORY_DERELICT_RIGHTS = "derelict_rights"  # salvage license for a specific wreck
LOT_CATEGORY_CONTRABAND = "contraband"      # illegal goods (Reach only; triggers consequences at Stellaris)
LOT_CATEGORY_RESTRICTED_WEAPON = "restricted_weapon"  # licensed-only weapons (Reach primary)
LOT_CATEGORY_SALVAGE_LOT = "salvage_lot"    # bulk salvage bundle
```

### 3.3 Lot pool generation algorithm

At session creation time, the lot pool is drawn from the venue's master lot catalog:

**Input signals** (in priority order):

1. **Venue filter**: Only lots with matching `venue` field enter the candidate pool.
2. **Player rep tier filter**: Only lots with `rep_tier_required` at or below the player's current standing tier enter the candidate pool.
3. **Faction gate filter**: Lots with a `faction_gate` are only included if the player has positive standing with that faction (standing >= 0).
4. **Recently-seen exclusion**: Lots with `recently_seen_count >= 5` are excluded from the draw. Count resets to 0 when the lot is sold. **Decision locked. See Section 11, decision 7.**

**Weighting**:

Each candidate lot's draw weight is:

```
draw_weight = base_weight * rep_tier_multiplier * season_multiplier * headliner_cap
```

Where:
- `base_weight`: 1.0 for all standard lots
- `rep_tier_multiplier`: +0.3 per tier above the minimum (a "regular" lot in a "patron" session has multiplier 1.6)
- `season_multiplier`: 2.0 if lot's `season_tag` matches the current active season; otherwise 1.0
- `headliner_cap`: At most one headliner lot per session. If a headliner is already drawn, all remaining headliner lots have weight 0.

**Session composition**:

- Stellaris: 6 lots per standard session; 8 lots per headliner session (when `is_headliner` lot present)
- Reach: 4 lots per session (minimum threshold for session to fire)
- Draw without replacement until session is filled

**Worked example: drawing a Stellaris session**

Candidate pool after filters: 12 lots remaining. Player is "certified" tier.

```
draw sequence:
  1. headliner_cap check: one headliner allowed; kings_repeater_reissue weight = 2.0 (season active)
  2. draw lot 1: kings_repeater_reissue (headliner, weight 2.0) -- selected; headliner_cap now 0 for subsequent
  3. draw lots 2-6 from remaining 11 candidates at standard weights
  4. result: 6-lot session with 1 headliner
```

### 3.4 Worked example lots

**Example 1: Legendary module re-issue (Stellaris headliner)**

```
id:              kings_repeater_reissue_lot_2332
headline:        "The King's Repeater (Re-issue, Documented)"
description:     "Stellaris Engineering ran twelve re-issues of the King's Repeater
                  across three decades. This unit carries the original barrel assembly
                  from the Corsair King's flagship -- the repeater mechanism that
                  started the re-issue program. Axiom-certified. Provenance documentation
                  included. You are not getting these papers with a second copy."
category:        module
venue:           stellaris
base_appraisal:  28000
reserve_pct:     0.75          (reserve = 21000)
faction_gate:    None
rep_tier_required: certified
is_headliner:    True
season_tag:      None
contraband:      False
source_module_id: legendary_kings_repeater
recently_seen_count: 0
```

Note: This re-issue is mechanically equivalent to `legendary_kings_repeater` from `modules.json`. The boss-drop version (from the Corsair King encounter) is still acquirable through combat. This lot represents a documented second unit that passed through legitimate channels. SA-B3 authors the exact lot catalog; this example establishes the re-issue convention.

**Example 2: Faction-restricted commodity (Stellaris, regular tier)**

```
id:              axiom_nav_array_lot_14c
headline:        "Axiom-Series Navigational Array (Series C, Lot 14)"
description:     "Fourteen units certified under Axiom Labs' standard export license.
                  Commerce Guild distribution channels; recipient requires standing
                  verification before delivery. Series C arrays run hotter than the
                  B-series but log the sightline data you need for frontier nav."
category:        faction_commodity
venue:           stellaris
base_appraisal:  8500
reserve_pct:     0.82          (reserve = 6970)
faction_gate:    commerce_guild
rep_tier_required: regular
is_headliner:    False
season_tag:      None
contraband:      False
source_module_id: None
recently_seen_count: 0
```

**Example 3: Reach contraband lot**

```
id:              unstamped_fuel_additive_lot_reach_88
headline:        "Unstamped Fuel Additives (4 units, mixed grade)"
description:     "Four canisters. Two are Navigator-grade suppressants. Two are
                  something the vendor declined to classify. Tested functional.
                  Papers not included and not discussed. Standard floor terms apply."
category:        contraband
venue:           crimson_reach
base_appraisal:  6000
reserve_pct:     0.65          (reserve = 3900)
faction_gate:    None
rep_tier_required: apprentice
is_headliner:    False
season_tag:      None
contraband:      True
source_module_id: None
recently_seen_count: 0
```

---

## 4. AI Bidder Persona Model

### 4.1 Value function

Each AI bidder computes their effective value for a lot at session load time:

```
effective_value = base_appraisal * persona_desire_mult * (1 + session_signal_drift)
ceiling         = effective_value * ceiling_ratio
```

Where:
- `base_appraisal`: the lot's published appraisal value (section 3.1)
- `persona_desire_mult`: persona-specific multiplier based on lot category and persona's interest profile (defined per persona below)
- `session_signal_drift`: a per-session random float in the range `[-0.05, +0.05]`, drawn once when the session loads. Represents the persona's imperfect information. Seed: `f"{session_id}_{persona_id}"` (deterministic per session)
- `ceiling_ratio`: persona-specific scalar that sets how far above effective value the persona will bid (1.0 = bids exactly to appraisal; 1.15 = 15% over appraisal in high-desire situations)

A persona whose `effective_value` for a lot falls below the lot's starting bid (opening price = `reserve_price + one minimum increment`) does not bid on that lot at all.

### 4.2 Behavior axes

Each persona has four behavior axes, each a float in [0.0, 1.0]:

| Axis | 0.0 behavior | 1.0 behavior |
|---|---|---|
| `aggression` | Waits for others to move first; enters after round two | Counters immediately after any bid lands |
| `patience` | Folds before ceiling when bid pace slows | Holds to ceiling regardless of round |
| `signal_discipline` | Bid timing is predictable (Sable reads the tell easily) | Bid timing is variable (hard to read) |
| `snipe_resistance` | Does not respond to snipe-window bids | Always counters a snipe-window bid up to ceiling |

### 4.3 Counter-bid timing

Within a round's bid window, an AI persona counter-bids based on their aggression axis:
- aggression >= 0.7: counter fires within 1 second of any competing bid
- aggression 0.4 to 0.7: counter fires within 3-7 seconds (random in range)
- aggression < 0.4: counter fires in the final 40% of the round (if at all)

At asap speed, all timing compresses proportionally (minimum 0.5 seconds between AI actions).

### 4.4 Persona count

Five archetypes. Three are named voiced rivals (Prentiss, Kade, Salko). Two are procedural (Stellaris Speculator, Reach Flavor). **Decision locked. See Section 11, decision 2.**

### 4.5 Worked persona specs

**Aldous Prentiss (heritage-collector)**

Voice sheet: `requirements/character_voices.md`, section "Aldous Prentiss."

```
persona_id:           aldous_prentiss
desire_multipliers:
  antiquity:          1.40   (pre-Compact items are his primary interest)
  faction_commodity:  0.70   (will bid if Guild-affiliated, otherwise passes)
  module:             0.80   (buys modules occasionally, not his focus)
  derelict_rights:    0.90   (heritage sites interest him)
  contraband:         0.20   (avoids; beneath his register)
  rare_upgrade:       0.60
ceiling_ratio:        1.10   (pays a premium for lots he wants)
aggression:           0.30   (measured; small certain bids; doesn't rush)
patience:             0.80   (holds until near ceiling)
signal_discipline:    0.90   (near-zero timing leak; very hard to read)
snipe_resistance:     0.40   (notes the snipe; recalibrates; doesn't scramble)
```

In play: Prentiss enters a lot he wants in round two with a small precise bid. He raises by the minimum increment. He does not overpay dramatically. If outbid near his ceiling, he stops. He does not congratulate the winner. He files it and reads the next lot.

**Commissioner Yuna Kade (institutional)**

Voice sheet: `requirements/character_voices.md`, section "Commissioner Yuna Kade."

```
persona_id:           yuna_kade
desire_multipliers:
  faction_commodity:  1.00   (exactly; bids on her approved acquisition list)
  module:             0.50   (only if on list; most modules are not)
  all other:          0.00   (no discretion; does not bid outside list)
ceiling_ratio:        1.00   (authorized budget exactly; never exceeds)
aggression:           0.70   (consistent, methodical; bids on schedule)
patience:             0.50   (folds at ceiling; no emotional response)
signal_discipline:    0.95   (institutional training; near-zero signal)
snipe_resistance:     0.80   (has pre-authorized ceiling; matches snipes up to it)
```

In play: Kade's desire_mult for lots not on her list is 0.0, so she sits out most lots completely. When a target lot appears, she bids consistently and methodically up to her ceiling, then stops. She never appears to want it more than she does.

Implementation note: SA-B3 authors Kade's acquisition list as a per-session configuration. The lot catalog should include at least 2 to 3 lots per Stellaris session that Kade is configured to want.

**Captain Fenn Salko (cold-grudge)**

Voice sheet: `requirements/character_voices.md`, section "Captain Fenn Salko."

```
persona_id:           fenn_salko
desire_multipliers:
  base (all categories): 0.60  (below-average general interest)
  player_target_escalation: +0.70 added to any category the player has bid on
    in the last 3 sessions (SA-B2 tracks via session_history)
ceiling_ratio:
  default:          0.90   (conservative when player is not involved)
  vs_player:        1.15   (15% over appraisal when competing against player)
aggression:         0.60   (flat and immediate; states a number)
patience:           0.90   (almost never folds; carries the account)
signal_discipline:  0.85   (careful but not institutional; readable with effort)
snipe_resistance:   1.00   (always counters if the snipe came from the player)
```

In play: Salko attends sessions where the player is present. His interest escalates specifically on lots the player has recently wanted. He does not bid theatrically; he states a number and holds it. The rivalry is quiet, not performed.

SA-B2 implementation note: the `player_target_escalation` rule requires SA-B2 to track which lot categories the player has actively bid on (not just viewed) across the last 3 sessions. This is stored in `player.auction_state.recent_bid_categories`.

**Stellaris Speculator (procedural archetype, Stellaris)**

```
persona_id:           stellaris_speculator_[N]   (N drawn per session)
desire_multipliers:   drawn from a session-weighted category pool:
  pool:               {module: 0.8, antiquity: 0.9, faction_commodity: 0.7,
                       rare_upgrade: 0.8, derelict_rights: 0.5}
  one category elevated to 1.2 per session (simulates a specific buyer at this session)
ceiling_ratio:        0.85   (risk-adjusted; won't significantly overpay)
aggression:           0.50   (responsive but not aggressive)
patience:             0.40   (folds before ceiling if pace slows)
signal_discipline:    0.50   (mid-range; readable with Sable's help)
snipe_resistance:     0.30   (does not respond to snipes)
```

In play: the Speculator fills the ambient room. SA-B3 authors a pool of 2 to 3 speculator instances per session to create the feeling of a contested room without over-populating with named personas.

**Reach Flavor (procedural archetype, Crimson Reach, SA-B4)**

```
persona_id:           reach_buyer_[N]
desire_multipliers:
  contraband:         1.20
  restricted_weapon:  1.10
  salvage_lot:        0.90
  all other:          0.50
ceiling_ratio:        0.90   (Reach-priced; conservative on anything not contraband)
aggression:           0.80   (aggressive bidding style; enters fast)
patience:             0.30   (drops out quickly once near ceiling)
signal_discipline:    0.30   (very readable)
snipe_resistance:     0.60
```

SA-B4 configures Reach session persona pools. SA-B1 records the archetype for SA-B4 to inherit.

---

## 5. Player Input Model

### 5.1 Available actions per round

During the bid window, the player may take exactly one action per round:

| Action | Conditions | Effect |
|---|---|---|
| Raise by minimum increment | Player not currently high bidder, round open | Submits current_price + min_increment |
| Raise by custom amount | Player not currently high bidder, round open | Player enters credit amount; must be >= current_price + min_increment |
| Hold | Any | No bid submitted this round; player remains eligible for next round |
| Fold | Any | Player withdraws from this lot; cannot re-enter bidding for this lot |

A player who holds in both rounds of a standard lot and in all three rounds of a headliner lot is treated as having abstained from that lot. No CaptainMemory consequence fires for abstention.

### 5.2 Minimum increment scale

| Lot base_appraisal range | Minimum increment |
|---|---|
| 0 to 2,000 | 50 credits |
| 2,001 to 10,000 | 200 credits |
| 10,001 to 30,000 | 500 credits |
| 30,001+ | 1,000 credits |

### 5.3 Snipe window

The snipe window is the final N seconds of each round's timer (N per speed setting, section 2.4). If any player submits a bid during the snipe window:

1. The round timer resets to the snipe window duration (one reset per round; no chain-resets).
2. AI personas with `snipe_resistance >= 0.5` may counter within their aggression-based timing.
3. After the reset expires, the round closes normally.

The snipe window creates a moment of tension at round close. It cannot chain-extend indefinitely because the reset fires at most once per round.

### 5.4 Reserve-price interaction

Every lot has a hidden reserve price (`base_appraisal * reserve_pct`). If the winning bid at lot close is below the reserve:

- The lot is withdrawn ("reserve not met").
- No credit transfer occurs.
- The lot is returned to the pool with `recently_seen_count` incremented.
- The player is shown: "Reserve not met. The lot is withdrawn."

The player cannot see the reserve price directly. **Decision locked. See Section 11, decision 3.**

With `lot_appraiser` skill (any level), the player sees a banded estimate in the preview phase: "Reserve: likely in the range X to Y." The band width narrows at lot_appraiser level 2. See section 7 for the bonus contract.

### 5.5 Default visibility (no crew or skill bonuses)

The player sees:
- Current high bid amount
- Who is winning (player or "another bidder"; no names)
- Round timer countdown
- Lot description and category
- Round number and total rounds
- Result of each closed round (sold / reserve not met / next round)

The player does NOT see:
- AI bidder identities during live bidding
- AI bidder ceiling estimates
- Reserve price (exact)
- Other bidders' bid histories (only the current high bid)

### 5.6 Visibility with crew and skill bonuses

With `auction_bid_visibility` crew bonus (Sable Trent):
- Named rivals (Prentiss, Kade, Salko) are identified by name during live bidding
- Sable provides a real-time ceiling estimate for each named rival: shown as "Ceiling: approx. X" in the crew panel
- Procedural personas are shown as "Bidder [type]" (e.g., "Bidder: Speculator") but ceiling is not disclosed for procedurals

With `auction_lot_appraisal_bonus` (Sable Trent crew + lot_appraiser skill, stacked):
- Post-auction valuation report fires after each lot closes
- Level 1 (Sable only, 0.10 bonus): "Fair market value: approx. X" (within 15% of base_appraisal)
- Level 2 (Sable + lot_appraiser L1, 0.20 total): "Fair market value: X to Y" (within 8%)
- Level 3 (Sable + lot_appraiser L2, 0.25 total): "Fair market value: X" (exact base_appraisal disclosed)

See section 7 for full stacking rules.

---

## 6. Captain Memory Integration

### 6.1 Outcome constant

Auction losses (player submits a bid but is outbid and does not win the lot) record `OUTCOME_OUTBID` in CaptainMemory. SA-B2 introduces this constant in `spacegame/models/captain_memory.py`. It does not trigger a status transition (like `OUTCOME_DEFEAT` in combat); it accumulates toward `RESOLUTION_THRESHOLD`. **Decision locked. See Section 11, decision 4.**

```python
# In captain_memory.py (SA-B2 adds this):
OUTCOME_OUTBID = "outbid"
```

`OUTCOME_OUTBID` behaves like `OUTCOME_DEFEAT` and `OUTCOME_FLED` in the existing resolution logic: it increments `encounter_count` and `last_seen_day`, sets `last_outcome`, but does not trigger a status transition on its own. After `RESOLUTION_THRESHOLD` (3) encounters with no resolution, the rival auto-retires to `STATUS_WANDERER`.

### 6.2 When a rival appears at a venue

On player entry to an auction session, the session loads its rival roster from the venue's persona configuration (SA-B3/B4). For each named rival in the roster:

1. Check `CaptainMemory` for that captain_id.
2. If no memory exists: create a new `CaptainMemory` entry with `encounter_count=0`, `status=STATUS_ACTIVE`.
3. If memory exists and `status == STATUS_ACTIVE`: rival is present this session.
4. If memory exists and `status != STATUS_ACTIVE` (resolved): rival does not appear. The venue may show a brief note ("Prentiss hasn't been in for a while") if SA-B3 content authors choose to add it.

The rival's presence is not guaranteed every session. SA-B3 defines a per-rival attendance frequency (e.g., Prentiss attends 70% of sessions at which he is eligible; Salko attends any session where the player attends). SA-B1 records the design intent; SA-B3 sets the exact values.

### 6.3 Recording outcomes

An `OUTCOME_OUTBID` entry fires when:
- A named rival (Prentiss, Kade, or Salko) was in the same session
- The player bid on at least one lot that the rival also bid on
- The rival won that lot (player did not)

If the player wins the lot that the rival bid on, no CaptainMemory entry fires (the player won; no rival record needed).

If the player folds before the lot closes, no record fires.

The outcome records per-lot, not per-session. A session where the player loses three lots to Salko records three `OUTCOME_OUTBID` entries.

### 6.4 Auto-retire semantics

After 3 accumulated outbid encounters with a named rival (without any resolution), the rival's status transitions to `STATUS_WANDERER`. In context: the rival "stopped coming to auctions" or "pivoted to different markets." SA-B3 authors a brief flavor note for this state.

Resolution in auction context: the existing resolution outcomes (`OUTCOME_VICTORY`, `OUTCOME_NEGOTIATED`, `OUTCOME_BRIBED`) do not apply in an auction setting. The only non-accumulating outcome for auction rivals is auto-retire. SA-B2 may introduce a new resolution outcome (e.g., `OUTCOME_OUTCOMPETED`) if a player achieving a significant win streak against a rival should resolve the rivalry before the threshold. SA-B1 records this as an open item for SA-B2. See section 10.

---

## 7. Crew and Skill Bonus Consumption

### 7.1 auction_bid_visibility (Sable Trent, crew ability)

**Source**: `sable_trent` crew template, `data/crew/crew_members.json`, ability level 1.
**Bonus type**: `auction_bid_visibility` (value: 1.0)
**Effect on auction view**:

1. Named rivals (Prentiss, Kade, Salko) are identified by name in the rival panel during live bidding.
2. For each named rival, Sable's ceiling estimate is displayed in the crew panel as a specific number: "Prentiss: ceiling approx. 6,200." This is computed as `persona.ceiling + persona.session_signal_drift * persona.ceiling * 0.15` (a Sable-estimation error that is wider than the actual ceiling variance, representing Sable's read being good but not perfect).
3. Procedural personas (Speculator, Reach Flavor) are labeled by archetype: "Speculator" or "Reach Buyer." No ceiling displayed for procedurals.
4. Post-session: Sable delivers one line of post-session dialogue (see section 9). Content authored in SA-B3.

**What it does NOT do**: It does not change bidding mechanics. Sable sees the room; you still have to decide.

### 7.2 auction_lot_appraisal_bonus (Sable Trent + lot_appraiser skill, stacked)

**Sources**:
- `sable_trent` crew, ability level 1: `auction_lot_appraisal_bonus` = 0.10
- `lot_appraiser` skill, level 1: `auction_lot_appraisal_bonus` = 0.05
- `lot_appraiser` skill, level 2: `auction_lot_appraisal_bonus` = 0.05 (cumulative)

The bonus is additive. Stacking rules:

| Active bonuses | Total appraisal_bonus | Post-win effect |
|---|---|---|
| Sable (no skill) | 0.10 | "Fair market value: approx. X" (X within 15% of base_appraisal) |
| Sable + lot_appraiser L1 | 0.15 | "Fair market value: X to Y" (range within 8%) |
| Sable + lot_appraiser L2 | 0.20 | "Fair market value: X" (exact base_appraisal) |
| lot_appraiser L1 (no Sable) | 0.05 | Post-win: "Estimate: X to Y" (range within 20%; wider without Sable) |
| lot_appraiser L2 (no Sable) | 0.10 | Post-win: "Estimate: X to Y" (range within 12%) |

**Preview phase effect** (lot_appraiser at any level, with or without Sable):
- Reserve banded estimate shown: "Reserve likely: X to Y" where X = base_appraisal * (reserve_pct - 0.10) and Y = base_appraisal * (reserve_pct + 0.10)

**Implementation contract for SA-B2**:
- Read `crew_roster.get_bonus("auction_bid_visibility")` to determine if Sable is active
- Read `progression.get_bonus("auction_lot_appraisal_bonus") + crew_roster.get_bonus("auction_lot_appraisal_bonus")` to compute total appraisal bonus
- Apply bonus thresholds to determine which post-win message to display
- SA-B2 does not need to add new bonus types; both are already wired in SA-A2 (crew) and SA-C2 (skill tree)

### 7.3 What is NOT changed by crew or skill bonuses

- Lot reserve price (it is what it is; bonuses only reveal more information about it)
- AI bidder ceiling values (Sable reads them but does not change them)
- Bid increment minimums
- Round duration or snipe window

---

## 8. Save/Load Schema

### 8.1 AuctionState (new model, SA-B2)

SA-B2 creates `spacegame/models/bidding.py` containing `AuctionState`. This object is serialized as a field on `Player` (via `Player.to_dict()` / `Player.from_dict()`).

All `from_dict()` reads use `data.get("field", default)` per CLAUDE.md migration discipline.

| Field | Type | Default | Description |
|---|---|---|---|
| `pending_lot_pool` | `list[dict[str, Any]]` | `[]` | Lots generated for the next scheduled session; not yet played |
| `active_auction_id` | `Optional[str]` | `None` | Venue ID of the auction in progress (None if no active session) |
| `active_session_lots` | `list[dict[str, Any]]` | `[]` | Lot list for the current session (populated at session open) |
| `active_round` | `int` | `0` | Current round number within the active lot; 0 if no active lot |
| `active_lot_index` | `int` | `0` | Index into active_session_lots for the current lot |
| `session_history` | `list[dict[str, Any]]` | `[]` | Records of completed sessions (lot outcomes, prices, winner) |
| `last_auction_day` | `dict[str, int]` | `{}` | venue_id to game_day of last completed session |
| `next_auction_day` | `dict[str, int]` | `{}` | venue_id to scheduled game_day of next session |
| `recent_bid_categories` | `list[str]` | `[]` | Category strings of lots player bid on in last 3 sessions; used by Salko escalation |
| `rival_session_attendance` | `dict[str, list[str]]` | `{}` | session_id to list of captain_ids present; for post-session CaptainMemory processing |
| `won_lots` | `list[str]` | `[]` | lot IDs won by the player; persists across sessions for journal and achievement checks |
| `speed_setting` | `str` | `"normal"` | Player's preferred speed: "slow", "normal", "fast", or "asap" |

### 8.2 Per-lot save state

Each item in `active_session_lots` and `session_history` is a serialized lot dict. For in-progress lots, additionally saved:

| Field | Type | Default | Description |
|---|---|---|---|
| `lot_id` | `str` | required | The lot's id |
| `current_high_bid` | `int` | `0` | Current winning bid |
| `current_high_bidder_id` | `Optional[str]` | `None` | persona_id of high bidder, or "player" |
| `rounds_completed` | `int` | `0` | Rounds already closed for this lot |
| `status` | `str` | `"open"` | "open", "sold", "withdrawn", "pending" |
| `sale_price` | `Optional[int]` | `None` | Final price if sold |

### 8.3 Migration discipline

Any field added to `AuctionState` after SA-B2 ships must use `data.get("field", default)` in `from_dict()`. No field may be required (no bare `data["field"]`) in `from_dict()` after the initial schema ships.

Existing saves that predate the auction system have no `auction_state` key on the player dict. `Player.from_dict()` must handle this with:

```python
auction_data = data.get("auction_state", {})
self.auction_state = AuctionState.from_dict(auction_data)
```

All `AuctionState` fields default to safe values (empty lists, empty dicts, None, "normal"), so an old save loads cleanly into a first-time auction player.

---

## 9. Tutorial, Journal, News, and Crew-Banter Hooks

### 9.1 First-auction FirstTimeTipOverlay

**Trigger flag**: `auction_first_session_entered` (set in `spacegame/constants/flags.py` by SA-B2)
**Trigger condition**: Player enters Stellaris Auction House or Crimson Reach Black Market for the first time
**Fires once, then suppresses**

Overlay copy (terse, declarative, no flavor):

```
"Three-round ascending bid. Timer hits zero, highest bid takes the lot.
Reserve not met means it does not sell.
Hold to skip a round. Fold to exit a lot entirely."
```

This follows the onboarding design overlay style (section 9a of `requirements/onboarding_design.md`): short, declarative, no flavor text, dismiss button reads "Got it."

### 9.2 Journal entry templates

**First auction session entered** (fires on first auction session regardless of outcome):

```
Entry title:  "First Session"
Entry body:   "Lot prices here move differently than the commodity floor.
               The ceiling is whatever the room will pay.
               Sable said two words the whole time. Both were correct."
```

(Last sentence omitted if Sable is not in crew.)

**First lot won**:

```
Entry title:  "Won the Lot"
Entry body:   "Took [lot_headline] at [winning_price] credits.
               [IF Sable active: Sable flagged the ceiling two rounds early. Filed that.]
               [IF no Sable: Went in blind. Got lucky or got it right. Will know which later.]"
```

**First rivalry formed (any named rival records first OUTCOME_OUTBID)**:

```
Entry title:  "[rival_display_name] Was There"
Entry body:   "[rival_display_name] bid on [lot_headline]. Lost that one.
               I know what the lot was."
```

(No em-dashes. No grand framing. The rivalry is specific and filed.)

### 9.3 News ticker templates

SA-X5 authors the full news ticker content. SA-B1 establishes two template stubs that SA-B2 can wire immediately:

**Headliner lot sold**:
```
"[lot_headline] sells at [venue_display_name]. Price undisclosed."
```

**Headliner lot withdrawn (reserve not met)**:
```
"[lot_headline] withdrawn from [venue_display_name] floor. Reserve not met."
```

Headlines must be under 80 characters after substitution. SA-B3 authors content for the full news ticker integration in the lot catalog.

### 9.4 Crew-banter trigger flags

These flags are set by the auction system and read by the crew banter system (SA-X6). SA-B2 registers them in `spacegame/constants/flags.py`.

| Flag name | Set when |
|---|---|
| `auction_first_session_complete` | Player completes first auction session (all lots closed) |
| `auction_first_win` | Player wins their first lot at any venue |
| `auction_rival_prentiss_encountered` | Prentiss appears in same session as player for first time |
| `auction_rival_kade_encountered` | Kade appears in same session as player for first time |
| `auction_rival_salko_encountered` | Salko appears in same session as player for first time |
| `auction_first_rivalry_formed` | First OUTCOME_OUTBID recorded against any named rival |
| `auction_sable_ceiling_correct` | Sable's ceiling estimate was within 5% of actual rival ceiling post-session |

SA-X6 (crew reactions and anchor banter) authors the actual banter dialogue lines that these flags gate. SA-B2 and SA-B3 set the flags; SA-X6 writes the banter.

### 9.5 Achievement stub identifiers

SA-X7 authors full achievement content. SA-B1 establishes the stub IDs that SA-B2 can register:

| Achievement ID | Condition |
|---|---|
| `achievement_auction_first_win` | Win first lot at any venue |
| `achievement_auction_champion` | Win 5 lots at Stellaris Auction House |
| `achievement_auction_rival_retired` | A named rival auto-retires (STATUS_WANDERER) |
| `achievement_auction_perfect_read` | Win lot within 2% of Sable's ceiling estimate (Sable active) |
| `achievement_auction_reach_debut` | Win first lot at Crimson Reach (SA-B4) |
| `achievement_auction_seller` | List and sell a lot as player-seller (SA-B5) |

---

## 10. Open Items Deferred to SA-B2

The following are explicitly deferred to SA-B2 to implement. SA-B2 implementers do not need human approval to resolve these; they are within SA-B2's scope.

1. **UI layout specifics**: exact panel dimensions, rival panel placement, bid history scroll behavior, lot image/icon display. SA-B2 owns this.

2. **Animation and timing details**: bid-land animation, round-close animation, lot-sold celebration, reserve-not-met animation. SA-B2 owns this.

3. **Exact minimum bid for opening call**: the opening bid for each lot (the first valid bid the player or AI can submit). Recommendation: `reserve_price + one minimum increment`. SA-B2 decides.

4. **Cassian Velo on-floor dialogue lines**: exact text for "lot is open," "we are at X," "lot is closed," "reserve not met." SA-B3 authors Velo's full voice (SA-B1 establishes the voice sheet reference; SA-B3 writes the content).

5. **Rival auto-resolution above RESOLUTION_THRESHOLD**: whether to introduce `OUTCOME_OUTCOMPETED` for a player who achieves a win streak against a named rival before the threshold. SA-B2 decides based on playtest feel.

6. **Reach floor manager NPC voice**: the Reach Black Market does not have Velo's ceremonial voice. SA-B4 authors the Reach floor manager voice. SA-B1 establishes the venue exists.

7. **Sound design**: bid-land sounds, timer sounds, auctioneer cadence audio. SA-B2 wires audio hooks; SA-X9 delivers audio assets.

8. **Balance tuning**: persona desire_mult values, ceiling_ratio values, min increment scale. SA-B1 establishes initial values; SA-B6 tunes after playtesting.

9. **Salko escalation tracking period**: SA-B1 says "last 3 sessions." SA-B2 may adjust this if 3 sessions produces too-frequent escalation.

10. **Post-session social phase content depth**: SA-B1 specifies a brief text-based moment. SA-B3 authors the exact content volume and trigger conditions.

---

## 11. Locked Decisions

The following decisions are locked. SA-B2 and downstream sprints do not re-litigate them.

1. **Round format: ascending bid.** Rationale: most game-feel-friendly; creates mounting time pressure; pairs with Velo's ceremonial auctioneer cadence (voice sheet specifies ascending format naturally). Source: `station_anchors.md` decision 5.

2. **AI persona count: 5 archetypes.** Three named rivals (Prentiss, Kade, Salko) carry the recurring-rival surface. Two procedural archetypes (Stellaris Speculator, Reach Flavor) fill ambient room at each venue. Adding more named rivals before SA-B3/B4 ship would require voice sheets that do not yet exist.

3. **Reserve-price mechanic: every lot has a hidden reserve; reserve not met means no sale; default player visibility is none.** Rationale: realistic auction mechanic; creates risk of under-bidding (player learns to read room); `lot_appraiser` skill has concrete value in the preview phase.

4. **Captain Memory outcome constant: SA-B2 introduces `OUTCOME_OUTBID`.** Rationale: `OUTCOME_DEFEAT` is semantically combat-specific; auction loss is a social-commercial outcome. New constant is additive (does not change existing combat logic).

5. **Auction schedule cadence: Stellaris every 5-7 game-days; Reach irregular (demand-driven).** Rationale: Stellaris is institutional (calendar-based reflects Commerce Guild reliability); Reach is opportunistic (demand-driven reflects Wreckers' improvised culture).

6. **Time pressure: player-adjustable (slow/normal/fast/asap), default normal.** Rationale: accessibility for players who find real-time bidding stressful; matches existing pattern of player-adjustable speed in skill-check display preferences.

7. **Lot pool recently-seen exclusion window: 5 auctions.** Rationale: prevents repetitive pool; 5 auctions is approximately 25-35 game-days at Stellaris, long enough for meaningful rotation.

8. **Faction-restricted lot tier mapping: Stellaris uses Port standing (apprentice/regular/certified/patron); Reach uses Wreckers' Guild membership tier.** Rationale: each venue's access system is native to that venue's fiction; Port standing and Wreckers' membership already established by SA-1 and station reputation systems.

9. **Auction outcomes do not shift commodity prices.** Rationale: auctions trade in unique items and restricted goods, not bulk commodities; cross-system price drift would produce unpredictable simulation coupling and hard-to-balance tuning interactions.

10. **Legendary modules: auctions surface re-issues and alternate variants; existing 6 boss-drop modules remain boss-acquirable.** Rationale: preserves the boss-fight reward loop; adds auction as a complementary path for players who want to acquire legendary modules without boss encounters.

11. **Player-initiated auctions (SA-B5): same engine, reversed direction (player as seller, AI buyer pool, listing fees).** Rationale: leverages SA-B2's AuctionState infrastructure without a separate system; player experiences both sides of the same mechanic, reinforcing understanding of AI bidder behavior.

12. **Pre-auction preview: lots visible during preview; estimated price range hidden unless `lot_appraiser` skill present.** Rationale: creates a strategic planning phase before the session opens; `lot_appraiser` skill has concrete pre-session value (not just post-win value).

---

## 12. Hand-off Map

| Downstream sprint | Sections to read | Notes |
|---|---|---|
| SA-B2 (Bidding Core) | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 | Read all sections before implementation. Section 10 lists explicit open items for SA-B2 to resolve. Section 8 is the implementation contract for save/load. |
| SA-B3 (Stellaris Auction House) | 2, 3, 4, 5, 7, 9, 11 | Section 3.4 (example lots) establishes re-issue convention for SA-B3's lot catalog. Section 4.5 (persona specs) is SA-B3's primary input for rival configuration. Section 9 (hooks) is SA-B3's input for Velo dialogue stubs and crew banter flags. |
| SA-B4 (Crimson Reach) | 1.4, 2, 3, 4.5 (Salko + Reach Flavor), 5, 6, 7, 9.4, 11 | Section 1.4 establishes Wreckers' Guild tier gating. Section 3.4 (example 3) is the Reach contraband lot template. Section 4.5 (Reach Flavor archetype) is SA-B4's persona input. Section 6 applies at Reach as well. |
| SA-B5 (Player-Initiated Auctions) | 2, 3, 5, 8, 11 | Section 2 lifecycle applies mirrored. Section 3 (lot schema) is the basis for player listing schema. Section 5 input model is SA-B5's mirror reference. Section 8 (save/load) must extend AuctionState with player-listing fields. |
| SA-B6 (Polish and Tuning) | 4, 5, 10 | Section 4 (persona specs) is tuning input. Section 5.2 (increment scale) is balance tuning target. Section 10 (open items) lists outstanding balance decisions SA-B6 will address post-playtest. |
| SA-X5 (News Ticker) | 9.3 | Section 9.3 establishes template stubs; SA-X5 expands to full ticker content. |
| SA-X6 (Crew Reactions) | 9.4 | Section 9.4 lists all crew banter trigger flags; SA-X6 authors banter content. |
| SA-X7 (Achievements) | 9.5 | Section 9.5 lists stub achievement IDs; SA-X7 authors achievement metadata and unlock conditions. |
