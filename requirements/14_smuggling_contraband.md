# Smuggling & Contraband

## Implementation Status: PHASES A-D COMPLETE, PHASE E SPEC READY
**Cycle**: 4.3
**Priority**: P2 within Phase 4
**Campaign dependency**: Mission 07 (Tomas's tariff scheme), Mission 10 (Crimson Reach underground)
**Prerequisites**: Phase F (Ground Exploration) COMPLETE, existing trade/faction/permit systems

---

## Design Vision

Smuggling is the **risk/reward counterpart** to legitimate trading. Where legal trade is safe, predictable, and capped by tariffs and market forces, smuggling offers dramatically higher margins in exchange for the constant threat of detection, confiscation, and reputation damage. It is not a replacement for legal trade — it is a parallel economy that tempts the player to cross lines they may not be comfortable crossing.

The system must feel **morally gray, not cartoonishly criminal**. Tomas Drifter's tariff-dodging in Mission 07 establishes the tone: sometimes the "illegal" option is the one that feeds people. The Commerce Guild's tariffs are exploitative. The Miners Union can't afford medicine at Guild markup. The player should feel the tension between law and justice — not just "break rules for profit."

### Core Principles

1. **Opt-in, not required**: A player who never smuggles can complete Act One. Smuggling is a lucrative choice, not a mandatory mechanic.
2. **Escalating risk**: Early smuggling (restricted goods, tariff dodging) is low-risk. Moving to fully illegal cargo attracts real consequences.
3. **Faction-relative legality**: What's illegal in Guild space may be unremarkable at Crimson Reach. The law depends on where you are, not what you carry.
4. **Consequences that matter**: Getting caught costs credits, reputation, and cargo. Repeated offenses attract persistent attention.
5. **Narrative integration**: Smuggling feeds directly into the Act One story (Tomas, Malia, The Ledger conspiracy).
6. **Player clarity**: Every smuggling mechanic must be **explained to the player** through concise, contextual guidance. The player should never be surprised by a system they weren't told about. Tutorials are brief and integrated into gameplay — not walls of text.

### Player Onboarding & Clarity

Smuggling introduces several interlocking systems (legality, inspections, heat, black markets, hidden cargo). Each must be communicated to the player at the moment it becomes relevant, not all at once.

**Principles**:
- **Just-in-time teaching**: Explain a mechanic the first time the player encounters it, not before.
- **Concise tooltips over manuals**: A 1-2 sentence explanation at the point of decision beats a tutorial screen.
- **Risk transparency**: When the player is about to take an action with uncertain outcomes (e.g., intimidating an inspector, running illegal cargo), show them the odds or at minimum a qualitative risk indicator (low/medium/high/very high).
- **Consequence preview**: Before buying illegal goods, the trading UI should display what happens if caught ("ILLEGAL in Guild space — confiscation + fine + rep loss"). Before attempting intimidation during inspection, the dialogue option should say something like "Intimidate (Risky — failure doubles penalties)".
- **First-time contextual messages**: The first time the player encounters each of these, show a brief explanatory message:
  - First RESTRICTED/ILLEGAL commodity seen in market → "This item is [restricted/illegal] in [faction] space. Carrying it risks customs inspection."
  - First customs inspection → "Customs is scanning your cargo. You can comply, talk your way out (Persuasion), offer a bribe, or try to intimidate — but intimidation is a gamble."
  - First criminal heat gained → "Your criminal heat has increased. High heat attracts more inspections and eventually bounty hunters. Heat decays naturally over time."
  - First black market accessed → "Black markets trade without inspections or tariffs, but offer no faction reputation and charge a premium on legal goods."
  - First hidden compartment used → "Cargo in your hidden compartment has a lower chance of being detected during inspections — but penalties are doubled if it's found."
- **Social check transparency during inspections**: Show the player's effective skill level vs. the check difficulty *before* they commit. Color-code: green (likely success), yellow (coin flip), red (likely failure). This is consistent with the existing dialogue skill check UI (green/yellow/red stripe).
- **No hidden failure states**: If the player's criminal heat is approaching a bounty hunter threshold, warn them ("Your notoriety is attracting attention — bounty hunters may soon take interest").

---

## Existing Hooks

The codebase already has significant infrastructure that smuggling plugs into:

| System | Hook | Location |
|--------|------|----------|
| Commodity legality | `Legality` enum: LEGAL, RESTRICTED, ILLEGAL | `models/commodity.py` |
| Trade permits | `Player.trade_permits: set[str]`, gates buy/sell | `models/player.py` |
| Tariff system | `Economy.tariff_rate`, reputation modifiers | `models/system.py`, `models/faction.py` |
| Tariff reduction | Leadership skill node (-5% per level) | `data/progression/skills.json` |
| Faction reputation | -100 to +100 per faction, 5 tiers | `models/faction.py` |
| Danger levels | safe/moderate/dangerous per system | `models/system.py` |
| Station type | `Station.type`: major, minor (expandable) | `models/system.py` |
| Market variety | `Station.market_variety` field | `models/system.py` |
| Ship upgrades | Per-category slots: weapon, defense, utility | `models/ship.py` |
| Social skills | Persuasion, Intimidation, Observation | `models/social.py` |
| NPC disposition | Per-NPC 0-100, modifies social checks | `models/social.py` |

All 24 commodities currently have `"legality": "legal"`. The enum and field exist — they just need content.

---

## System Design

### 1. Commodity Legality by System

Legality is **not a global property** — it depends on the faction controlling the system you're in. A commodity has a *base* legality (from its JSON definition), but faction law enforcement varies:

| Legality | Guild Space | Union Space | Collective Space | Alliance Space | Crimson Reach |
|----------|-------------|-------------|-----------------|----------------|---------------|
| LEGAL | Free trade | Free trade | Free trade | Free trade | Free trade |
| RESTRICTED | Inspected, fined if no permit | Tolerated (warning only) | Confiscated for "research" | Ignored | Free trade |
| ILLEGAL | Confiscated + heavy fine + rep loss | Confiscated + moderate fine | Confiscated + banned from station | Light fine | Free trade |

**Key design point**: Crimson Reach doesn't recognize contraband — "a market that doesn't recognize the concept of contraband" (cultural guide). This makes Crimson Reach the natural hub for illegal goods, consistent with the lore.

#### New Commodities

Add to `data/economy/commodities.json`:

| ID | Name | Category | Base Price | Legality | Produced At | Consumed At |
|----|------|----------|-----------|----------|-------------|-------------|
| `weapons_components` | Weapons Components | INDUSTRIAL | 450 | RESTRICTED | Forgeworks, Iron Depths | Crimson Reach, black markets |
| `restricted_tech` | Restricted Tech | LUXURY | 800 | RESTRICTED | Nova Research, Axiom Labs | All (high demand) |
| `stolen_data` | Stolen Data | LUXURY | 600 | ILLEGAL | Crimson Reach | Axiom Labs (covertly), black markets |
| `combat_stims` | Combat Stimulants | INDUSTRIAL | 350 | ILLEGAL | Nova Research (covertly) | Breakstone, Crimson Reach |
| `contraband_medicine` | Diverted Medicine | BASIC | 200 | RESTRICTED | Axiom Labs | Haven's Rest, Breakstone, Verdant |

**Design notes**:
- `contraband_medicine` is the moral gray area commodity — it's cheap medicine diverted from Guild-controlled supply chains. Tomas's Mission 07 foreshadows this. It's RESTRICTED, not ILLEGAL, because the act of redistributing medicine isn't inherently criminal — the Guild just doesn't like it.
- `stolen_data` represents corporate espionage, encrypted intel, and stolen research. This ties into The Ledger conspiracy and Dex Halloran's information brokerage.
- `combat_stims` are manufactured at Nova Research's "restricted projects" wing (lore: "research programs that cross ethical lines"). Their illegality is unambiguous.
- `weapons_components` are military-grade parts that the factions want to control. The pirate attacks using "Guild-pattern drive cores" (Mission 12) hint at this supply chain.
- `restricted_tech` is dual-use advanced technology. Legal to own, illegal to trade without permits.

#### Model Changes

**`Commodity` model** — no structural changes needed. The `legality` field already exists.

**New model: `FactionLaw`** — maps (faction_id, legality) → enforcement behavior:

```python
@dataclass
class FactionLaw:
    """How a faction enforces legality levels."""
    faction_id: str
    inspection_chance: float  # Base chance of cargo scan on arrival (0.0-1.0)
    restricted_penalty: str   # "warn", "fine", "confiscate"
    illegal_penalty: str      # "fine", "confiscate", "ban"
    fine_multiplier: float    # Multiplied by cargo value
```

Data-driven: loaded from a new `data/economy/faction_laws.json`.

### 2. Detection & Inspection System

When the player arrives at a system, there is a chance of **customs inspection**. This is a gating event — it happens before the player can dock and trade.

#### Inspection Chance

Base chance depends on the system's faction:

| Faction | Base Inspection Chance |
|---------|----------------------|
| Commerce Guild | 20% |
| Science Collective | 15% |
| Miners Union | 10% |
| Frontier Alliance | 5% |
| Crimson Reach | 0% (no law enforcement) |

#### Modifiers to Inspection Chance

| Factor | Effect |
|--------|--------|
| Player has criminal_heat > 0 | +2% per heat point |
| Carrying any RESTRICTED cargo | +5% |
| Carrying any ILLEGAL cargo | +10% |
| Hidden Compartment upgrade | -10% |
| Signal Jammer upgrade | -5% |
| False Transponder upgrade | -8% |
| Observation skill (level 3+) | -3% (you spot checkpoints early) |
| Friendly+ faction reputation | -5% |
| Hostile faction reputation | +10% |

**Floor**: 2% in law-enforced systems (even allies can get unlucky).
**Ceiling**: 60% (there's always a chance of slipping through).
**Crimson Reach**: Always 0%.

#### Inspection Flow

1. **Arrival trigger**: On jumping to a new system, roll inspection chance.
2. **If triggered**: A customs scan event fires. The player sees a dialogue-style encounter: "Commerce Guild customs hails your ship. Prepare for routine cargo inspection."
3. **Scan resolution**: The scan checks all cargo. Each item's legality is evaluated against the local faction's laws.
   - **Hidden Compartment**: Cargo in hidden slots has a separate, lower detection chance (30% base, modified by upgrades/skills).
   - **Clean cargo only**: Scan passes, player docks normally. Small rep boost for compliance.
   - **Restricted goods found**: Penalty per faction law (warn/fine/confiscate).
   - **Illegal goods found**: Harsher penalty (fine + confiscation + rep loss + criminal heat).
4. **Social options during inspection**:
   - **Persuasion check**: Talk your way past ("These are medical supplies for the outer settlements"). Difficulty scales with cargo illegality and quantity. Success = scan waived.
   - **Bribe**: Pay credits to skip inspection. Cost scales with cargo value. Works better with high disposition toward the inspecting NPC.
   - **Intimidation check**: Only works at Unfriendly or lower reputation ("You don't want to open that hold"). High risk — failure doubles penalties.

#### Penalties

| Penalty Type | Effect |
|-------------|--------|
| Warning | Message only. No gameplay impact. First offense for RESTRICTED in tolerant factions. |
| Fine | Lose credits = cargo_value × fine_multiplier. Cargo kept. |
| Confiscation | Lose the offending cargo. No credit refund. |
| Rep loss | -10 (RESTRICTED caught) to -30 (ILLEGAL caught) with local faction. |
| Criminal heat | +5 (RESTRICTED) to +15 (ILLEGAL). Decays at -1 per game day. |
| Station ban | Temporary (5 game days). Cannot dock. Severe: ILLEGAL goods in Collective space. |

### 3. Criminal Heat

A new stat on `Player`: `criminal_heat: int = 0` (range 0-100).

- **Gained by**: Getting caught with contraband, failed smuggling contracts, attacking faction ships.
- **Decays at**: -1 per game day (natural cooling).
- **Effects**:
  - 0-10: No effect. Clean record.
  - 11-25: Increased inspection chance (+2% per point). Faction NPCs occasionally comment.
  - 26-50: Bounty hunter encounters during travel (5% chance per jump in faction space). Shakedowns increase.
  - 51-75: Faction stations charge double docking fees. Some NPCs refuse to deal.
  - 76-100: Active pursuit. Bounty hunter encounters at 15% per jump. Allied reputation with offended factions capped at Neutral.

Criminal heat is **per-player, not per-faction**. It represents your general reputation in the sector's underworld radar. Getting caught in Guild space also makes Union customs pay more attention — word travels.

#### Bounty Hunters

New enemy template type for space combat. Bounty hunters are tough, well-equipped opponents that specifically target the player. They cannot be bribed (they're being paid more by the faction). They can be:
- **Fought**: Standard combat. High difficulty. Good loot on victory.
- **Fled from**: Possible but hard (they have fast ships).
- **Negotiated with**: Persuasion check, very high difficulty. Success = they "lose your trail" for 5 days.

### 4. Black Markets

Black markets are **special trading interfaces** accessible at certain stations under certain conditions. They are not separate locations — they are hidden tabs or contacts within existing stations.

#### Access Requirements

| Location | Requirement |
|----------|-------------|
| Crimson Reach | Always available (Wrecker's Outpost IS the black market) |
| Any Frontier Alliance station | 30+ Alliance reputation AND Malia Torres contact (Mission 10) |
| Nexus Prime | 40+ criminal heat AND Dex Halloran contact (Mission 09) |
| Breakstone | 20+ Union reputation AND Marcus Jin crew member aboard |

#### Black Market Features

- **Buy/sell illegal and restricted goods** without inspection risk.
- **No tariffs** — black market prices have no faction tariff modifier.
- **Higher base prices for legal goods** (+15%) — convenience tax for anonymity.
- **Lower prices for illegal goods** (-10% vs. legitimate market) — supply is plentiful.
- **Smuggling contracts** available (see section 5).
- **Fence stolen cargo**: Sell confiscated/pirated goods at 60% value.
- **No reputation gain** from black market trades with any faction.

#### UI Integration

Black market access appears as an additional tab or button in the Trading View when available. Visual distinction: darker color scheme, different market name (e.g., "Wrecker's Market" at Crimson Reach, "The Back Room" elsewhere).

### 5. Smuggling Contracts

High-risk, high-reward delivery missions available through black market contacts and specific NPCs.

#### Contract Structure

```python
@dataclass
class SmugglingContract:
    """A smuggling delivery job."""
    id: str
    client_name: str           # Who's hiring (NPC name or alias)
    commodity_id: str           # What to deliver
    quantity: int               # How much
    source_system: str          # Where to pick up
    destination_system: str     # Where to deliver
    payment: int                # Credits on completion
    deadline_days: int          # Game days to complete
    penalty_on_failure: int     # Credits lost if caught or expired
    heat_on_completion: int     # Criminal heat gained even on success
    difficulty: str             # "low", "medium", "high"
```

#### Contract Generation

- Available at black markets and from specific NPCs (Malia Torres, Dex Halloran, Tomas Drifter).
- Deterministic seeding like trade contracts: `f"{game_day}_{system_id}_smuggling"`.
- 1-3 contracts available at any time per black market location.
- Contracts refresh every 3 game days.

#### Difficulty Scaling

| Difficulty | Commodity | Payment | Deadline | Heat Gain | Route Risk |
|-----------|-----------|---------|----------|-----------|------------|
| Low | RESTRICTED | 500-800 CR | 10 days | +3 | 1-2 jumps, safe/moderate systems |
| Medium | ILLEGAL | 1000-2000 CR | 7 days | +8 | 2-3 jumps, at least one dangerous system |
| High | ILLEGAL | 2500-5000 CR | 5 days | +15 | 3+ jumps, multiple dangerous systems, high inspection routes |

#### Contract Completion

- Deliver the goods to the destination system's black market contact.
- If caught by customs en route: contract fails, penalty applied, cargo confiscated.
- If deadline expires: contract fails, penalty applied. No heat gained (you just didn't deliver).
- On success: payment, heat gain, +5 reputation with the client's faction (if applicable).

### 6. Ship Modifications (Smuggling Upgrades)

Three new **utility slot** ship upgrades focused on evasion and concealment:

| ID | Name | Cost | Effect | Slot |
|----|------|------|--------|------|
| `hidden_compartment` | Hidden Compartment | 2500 CR | 30% of cargo capacity becomes "hidden" — separate hold with lower scan detection (30% base instead of 100%) | utility |
| `signal_jammer` | Signal Jammer | 1500 CR | -5% inspection chance on arrival. Bounty hunters take 1 extra day to find you. | utility |
| `false_transponder` | False Transponder | 3000 CR | -8% inspection chance. Can change displayed ship ID once per system visit (resets criminal heat effects for that system only). | utility |

#### Hidden Compartment Mechanics

- When installed, the player's cargo view shows two sections: **Main Hold** and **Hidden Hold**.
- Hidden hold capacity = 30% of ship's total cargo (rounded down, minimum 3).
- Main hold capacity reduced accordingly.
- During customs inspection, main hold is always scanned. Hidden hold has a 30% scan chance (modified by other upgrades and skills).
- Player must manually transfer cargo between holds (drag or button in cargo view).
- If hidden hold IS scanned and contraband is found: **double** the normal penalty (you tried to hide it).

#### Where to Buy

Smuggling upgrades are **not available at standard shipyards**. They can be purchased from:
- Crimson Reach (always available)
- Black markets at other stations (when unlocked)
- Malia Torres (after Mission 10, offers a discount)

### 7. Skill & Attribute Integration

#### Existing Skills That Apply

| Skill/Attribute | Smuggling Benefit |
|----------------|-------------------|
| Tariff Negotiation (Leadership) | Reduces tariffs, making some legal trade profitable enough to skip smuggling |
| Persuasion (Social) | Talk past customs inspections |
| Intimidation (Social) | Threaten customs (risky) |
| Observation (Social) | Spot checkpoints early (-3% inspection at level 3+) |
| Commerce (Attribute) | Better black market buy/sell prices |
| Synergy (Attribute) | Social effective level bonus helps all customs interactions |

#### New Skill Nodes (Optional — evaluate during implementation)

If the smuggling system feels like it needs dedicated progression, add 2-3 nodes to the Social or Leadership tree:

| Node | Tree | Effect | Prereq |
|------|------|--------|--------|
| `underworld_contacts` | Social | Black market access at 20 rep instead of 30. Smuggling contracts refresh 1 day faster. | silver_tongue |
| `clean_record` | Leadership | Criminal heat decays at -2/day instead of -1. | tariff_negotiation |

These are **deferred** — implement the base system first, evaluate whether skill nodes add meaningful depth.

### 8. Narrative Integration

#### Campaign Mission Connections

| Mission | Smuggling Tie-in |
|---------|-----------------|
| 07: Drifter's Deal | First exposure to tariff dodging. Tomas's scheme uses RESTRICTED goods (contraband_medicine equivalent). Tutorial for the moral gray area. |
| 09: Whispers at the Bar | Dex Halloran becomes a contact. Unlocks Nexus Prime black market access later. |
| 10: The Crimson Run | Malia Torres becomes a contact. Crimson Reach black market unlocked. First smuggling contract offered as follow-up. |
| 12+: Later missions | Smuggling infrastructure supports The Ledger conspiracy — stolen data and weapons components are the commodities The Ledger moves through the sector. |

#### NPC Roles in Smuggling

| NPC | Role |
|-----|------|
| Tomas Drifter | Introduces tariff evasion. Offers low-difficulty smuggling contracts from crew. Teaches the player the ropes. His recruitment mission already involves gray-market trade. |
| Malia Torres | Primary black market contact. Offers medium/high-difficulty contracts. Knows the underground network. Her Wrecker's Outpost is the smuggling hub. |
| Dex Halloran | Information broker. Sells intel on inspection schedules (temporary inspection chance reduction for a system). Unlocks Nexus Prime black market. |
| Officer Larsen | The face of Guild law enforcement. He's the customs inspector the player learns to dread — or outmaneuver. |

---

## Implementation Plan

### Phase A: Foundation (Models & Data)

1. Add 5 new commodities to `commodities.json` with RESTRICTED/ILLEGAL legality.
2. Create `FactionLaw` model and `faction_laws.json` data file.
3. Add `criminal_heat: int = 0` to `Player` with serialization.
4. Create `SmugglingContract` model with generation logic.
5. Create `InspectionResult` model for customs scan outcomes.

### Phase B: Detection & Enforcement

1. Implement inspection chance calculation (base + modifiers).
2. Create customs inspection event (dialogue-style encounter on system arrival).
3. Implement scan resolution: check cargo against local faction law.
4. Add social skill checks during inspection (persuasion/bribe/intimidation).
5. Implement penalties: fines, confiscation, rep loss, criminal heat.
6. Wire inspection trigger into game engine's travel flow.

### Phase C: Black Markets & Contracts

1. Implement black market access conditions per station.
2. Add black market trading interface (modified Trading View or overlay tab).
3. Implement smuggling contract generation and display.
4. Implement contract tracking (integrate with existing MissionManager or parallel system).
5. Implement contract completion and failure flows.

### Phase D: Ship Mods & Criminal Heat

1. Add 3 smuggling ship upgrades to upgrade data.
2. Implement hidden compartment cargo split (UI and model).
3. Implement criminal heat decay and threshold effects.
4. Add bounty hunter encounters for high criminal heat.
5. Implement false transponder system-level heat masking.

### Phase E: View Integration & Game Wiring

Phase E wires Phases A-D's model layer into the running game. This is the largest phase — it touches the game engine, trading view, encounter view, station hub, galaxy map, and save system.

#### Design Change: Black Market Access Permits

**Replaces**: The multi-condition `check_black_market_access()` approach (dialogue flags + rep + heat + crew checks evaluated every visit).

**New approach**: `Player.black_market_access: set[str]` — a set of system IDs, mirroring the `trade_permits` pattern.

**Rationale**: Trade permits proved that a single earned flag feels more deliberate than a silent threshold check. Black market access should feel like a milestone — you earned someone's trust, not just crossed a numerical threshold. The prerequisites (rep, heat, crew) gate the *unlock event* (a dialogue beat or mission reward), not the access check. Once earned, access persists.

**Unlock events per system**:

| System | Market Name | Unlock Trigger | Prerequisites |
|--------|-------------|---------------|---------------|
| crimson_reach | Wrecker's Market | Automatic on first visit | None — lawless zone |
| havens_rest | The Backyard | Malia Torres dialogue | Mission 10 complete |
| verdant | The Shed | Malia Torres dialogue | Mission 10 complete + 30+ Alliance rep |
| stellaris_port | The Quiet Dock | Malia Torres dialogue | Mission 10 complete + 30+ Alliance rep |
| nexus_prime | The Back Room | Dex Halloran dialogue | Mission 09 complete + 40+ criminal heat |
| breakstone | The Undershaft | Marcus Jin crew dialogue | Marcus recruited + 20+ Union rep |

**Key differences from old system**:
- Access is checked via `system_id in player.black_market_access` (O(1) set lookup)
- No re-evaluation of conditions each visit — unlock is permanent
- The market names are stored in the data/code, not on the player
- Crimson Reach auto-granted on `initialize_new_game()` (or first dock)
- Other systems unlocked through specific dialogue nodes that check prerequisites and call `player.grant_black_market_access(system_id)`
- Backward compatibility: `data.get("black_market_access", [])` in save deserialization

**Model changes**:
- Add `black_market_access: set[str] = field(default_factory=set)` to Player
- Add `has_black_market_access(system_id) -> bool` and `grant_black_market_access(system_id) -> None` to Player
- Serialize as list in `to_dict()`, deserialize as set in `from_dict()`
- Refactor `check_black_market_access()` in smuggling.py to use the player's set instead of computing conditions. Keep `get_black_market_name(system_id) -> Optional[str]` for UI display.
- Existing tests updated to reflect the simplified access model

#### E.1: Player Model + Save/Load

**Player model** (`models/player.py`):
- Add `black_market_access: set[str] = field(default_factory=set)`
- Add `has_black_market_access(system_id: str) -> bool`
- Add `grant_black_market_access(system_id: str) -> None`
- These mirror exactly `trade_permits` / `has_trade_permit()` / `grant_trade_permit()`

**Save manager** (`save_manager.py`):
- Serialize `black_market_access` as `list[str]` (JSON doesn't have sets)
- Deserialize with `set(data.get("black_market_access", []))` for backward compat
- Serialize `criminal_heat` (already exists on Player, verify it round-trips)

**Smuggling model** (`models/smuggling.py`):
- Refactor `check_black_market_access()` to a simpler `get_black_market_name(system_id: str) -> Optional[str]` that returns the market name from `_BLACK_MARKET_RULES` if one exists for that system, or None
- Keep `BlackMarketAccess` dataclass but simplify: callers check `player.has_black_market_access()` first, then get the name
- Add `get_black_market_systems() -> list[str]` for UI to know which systems have markets at all

**Game engine** (`engine/game.py`):
- In `initialize_new_game()`: grant `crimson_reach` black market access automatically
- Add `SmugglingContractManager` as `self.smuggling_contracts: Optional[SmugglingContractManager]` on Game
- Initialize from empty state on new game, restore from save on load
- Add criminal heat decay in `_check_day_advance()`: `player.criminal_heat = max(0, player.criminal_heat - 1)`
- Pass smuggling contract state through save/load chain

**Tests** (~12):
- Player black_market_access: grant, has, serialization round-trip
- Save backward compat: old saves without black_market_access load cleanly
- Criminal heat serialization round-trip
- Game initializes with crimson_reach access
- get_black_market_name returns name for valid systems, None for others
- SmugglingContractManager save/load round-trip

#### E.2: Customs Inspections in Game Engine

Wire inspection triggers into the travel flow. Inspections fire as encounter events when arriving at a new system.

**Game engine** (`engine/game.py`):
- After `_check_travel_encounter()` (which handles combat encounters), add `_check_customs_inspection()`
- `_check_customs_inspection()`:
  1. Get the arriving system's faction → look up FactionLaw from DataLoader
  2. If no faction law (Crimson Reach): skip
  3. Build cargo dict and legality map from player's ship cargo + DataLoader commodities
  4. Call `should_trigger_inspection()` with all modifiers
  5. If triggered: call `build_inspection_encounter()` → get EncounterDefinition
  6. Set `self._pending_inspection = encounter_definition`
  7. Transition to ENCOUNTER state (reuse existing EncounterView)

**DataLoader** (`data_loader.py`):
- Add `self.faction_laws: dict[str, FactionLaw] = {}` — keyed by faction_id
- Add `load_faction_laws()` called from `load_all()`
- Add `get_faction_law(faction_id: str) -> Optional[FactionLaw]`

**Encounter result handling** (`engine/game.py`):
- EncounterView already returns outcomes with MissionReward lists
- Add new reward types to mission reward processing:
  - `deduct_credits` (fines) — already exists
  - `confiscate_cargo` — remove specified cargo from player's ship
  - `add_criminal_heat` — increment player.criminal_heat
  - `modify_reputation` — adjust faction rep (already exists)
- These reward types are already defined in MissionReward; verify they're all handled in `_apply_encounter_rewards()`

**Inspection timing**:
- Inspections happen on **arrival at a system** (galaxy map travel), before docking at station
- Only one inspection per arrival (not per station visit)
- The encounter blocks station access until resolved — player must choose (comply/persuade/bribe/intimidate)
- If player passes or pays fine: proceed to station as normal
- If station ban: forced back to galaxy map, system marked banned for N days

**Tests** (~10):
- DataLoader loads faction laws
- _check_customs_inspection triggers when chance met
- _check_customs_inspection skips Crimson Reach
- Inspection encounter builds correctly with player state
- Comply outcome applies penalties
- Persuade outcome skips penalties on success
- Bribe deducts credits
- Criminal heat modifies inspection chance
- Station ban prevents docking
- Clean cargo passes inspection

#### E.3: Black Market in Trading View

Add a black market trading mode to the existing TradingView. Not a separate view — a mode toggle within Trading.

**Trading view** (`views/trading_view.py`):
- Add "BLACK MARKET" button/tab, visible only when `player.has_black_market_access(system_id)`
- When in black market mode:
  - Header shows market name (from `get_black_market_name()`) with dark gold accent
  - Commodity list shows ALL commodities (including RESTRICTED/ILLEGAL) without legality warnings
  - Prices use black market modifiers: `get_black_market_price_modifier(legality)` applied to base price
  - No tariffs applied
  - No faction rep gained from trades
  - No trade permit required (black market doesn't respect faction bureaucracy)
  - Legality indicators hidden (everything trades freely here)
- When in normal market mode (existing behavior):
  - RESTRICTED/ILLEGAL commodities visible but show legality warnings
  - Cannot buy ILLEGAL goods at legal markets (restricted can be bought with warning)
  - Existing tariff and permit checks apply
- Toggle button switches between modes; current mode persists within the visit

**Visual distinction**:
- Black market mode: darker panel tint, gold/amber accent colors, market name in header
- Normal mode: existing blue/white theme unchanged
- First-time contextual message when entering black market mode

**Legality indicators in normal market**:
- RESTRICTED commodities: yellow "RESTRICTED" tag, tooltip with faction penalty
- ILLEGAL commodities: red "ILLEGAL" tag, tooltip with faction penalty
- LEGAL commodities: no tag (current behavior)
- These tags appear next to commodity name in the buy/sell lists

**Tests** (~8):
- Black market button visible when access granted
- Black market button hidden when no access
- Black market mode applies price modifiers
- Black market mode skips tariffs
- Black market mode skips permit check
- Normal mode enforces legality warnings
- Normal mode enforces permits
- Market name displays correctly

#### E.4: Smuggling Contracts UI

Display smuggling contracts at black markets and allow accept/complete.

**Station hub or trading view**:
- When at a black market, show "CONTRACTS" section or button
- Lists available smuggling contracts (from `SmugglingContractManager.get_available_contracts()`)
- Each contract shows: commodity, quantity, source → destination, payment, deadline, heat gain, difficulty rating
- Color-coded difficulty: green (low), yellow (medium), red (high)
- "ACCEPT" button per contract (max 3 active)
- Active contracts shown in a sidebar or expandable panel

**Contract tracking display**:
- Galaxy map or status bar shows active smuggling contracts with remaining days
- Destination system highlighted on galaxy map (similar to mission markers)
- When at destination with correct cargo in hold: "DELIVER" button in black market
- Completion triggers payment + heat gain

**Contract expiration**:
- In `_check_day_advance()`: check for expired contracts via `smuggling_contracts.get_expired_contracts(current_day)`
- Apply failure penalties (credit deduction)
- Queue notification: "Contract expired: [contract description]"

**Tests** (~8):
- Contract list displayed at black market
- Accept contract up to max 3
- Complete contract at destination
- Expired contract applies penalty
- Contract destination marked on map
- Deliver button only at correct destination with correct cargo
- Active contracts persist across save/load
- Contract generation determinism matches model tests

#### E.5: Criminal Heat Display & Bounty Hunters

**Criminal heat display**:
- Station hub status bar: show heat indicator when > 0 (thermometer icon or numeric)
- Color coding: 1-10 white, 11-25 yellow, 26-50 orange, 51+ red
- Galaxy map: show heat in player stats panel
- Tooltip on hover: current heat, decay rate, threshold warnings

**Criminal heat decay**:
- Already wired in E.1 (`_check_day_advance`)
- `clean_record` skill node (if implemented): -2/day instead of -1

**Bounty hunter encounters**:
- In `_check_travel_encounter()` (or after it), add `_check_bounty_hunter()`
- Call `should_trigger_bounty_hunter()` with player state
- If triggered: call `build_bounty_hunter_encounter()` → EncounterDefinition
- Route to EncounterView (same as inspections)
- Fight outcome → transition to CombatView with bounty hunter enemy templates
- Surrender outcome → deduct credits, reduce heat
- Negotiate outcome → immunity period (track `_bounty_immunity_until` day on Game)

**Bounty hunter enemy templates**:
- Verify enemy templates exist in enemies JSON: `bounty_tracker`, `bounty_enforcer`, `bounty_vanguard`, `bounty_ace`, `faction_enforcer`
- If missing: add to `data/ships/enemies.json` with appropriate stats (tough, fast, good weapons)
- Should be faction-tagged for loot and flavor text

**Tests** (~6):
- Bounty hunter triggers at heat 26+
- Bounty hunter never triggers below heat 26
- Bounty hunter never triggers at Crimson Reach
- Signal jammer reduces bounty hunter chance
- Fight outcome transitions to combat
- Surrender deducts credits and reduces heat

#### E.6: Hidden Compartment UI

Add hidden compartment cargo management to the ship management or cargo view.

**Ship management view** or **trading view cargo panel**:
- When hidden compartment upgrade installed: show split cargo display
- "Main Hold: X/Y" and "Hidden Hold: X/Z"
- Transfer buttons: "HIDE →" and "← REVEAL" to move cargo between holds
- Only contraband (RESTRICTED/ILLEGAL) should be hideable (quality of life — don't let player accidentally hide legal goods)
- Visual: hidden hold section has darker background, lock icon

**Inspection integration**:
- When inspection fires, game engine checks if player has hidden compartment
- If yes: separate scan roll for hidden hold (`calculate_hidden_scan_chance()`)
- If hidden hold scanned and contraband found: doubled penalties via `resolve_inspection_with_hidden()`

**Tests** (~5):
- Transfer cargo to hidden hold
- Transfer cargo from hidden hold
- Hidden hold capacity enforced
- Hidden hold scan uses separate chance
- Doubled penalties when hidden contraband found

#### E.7: Smuggling Upgrades in Shipyard

Make the 3 smuggling upgrades purchasable at appropriate locations.

**Shipyard view**:
- Add `hidden_compartment`, `signal_jammer`, `false_transponder` to ship upgrades JSON
- These upgrades should have a `"source": "black_market"` tag or similar
- Shipyard view filters: standard shipyard shows standard upgrades; black market shows smuggling upgrades
- Crimson Reach shipyard always shows all upgrades
- Black market access required to see/buy smuggling upgrades elsewhere

**Upgrade data** (`data/ships/upgrades.json`):
- Verify the 3 smuggling upgrades exist with correct stats
- Add `combat_move` dicts if they have combat effects (signal jammer might affect flee chance)
- Tag with `"requires_black_market": true` or source field

**Tests** (~4):
- Smuggling upgrades visible at Crimson Reach
- Smuggling upgrades visible at black markets
- Smuggling upgrades hidden at standard shipyards
- Installing hidden compartment splits cargo display

#### E.8: Polish & Achievements

**Achievements** (add to `data/progression/achievements.json`):
- `first_smuggle`: "Shadow Trader" — complete 1 smuggling contract, reward 500 CR
- `heat_survivor`: "Wanted" — reach 50+ criminal heat, reward 200 XP
- `clean_getaway`: "Slippery" — pass 10 customs inspections with contraband aboard, reward 1000 CR

**Player stat fields** (for achievements):
- `smuggling_contracts_completed: int = 0`
- `inspections_passed_with_contraband: int = 0`
- `max_criminal_heat_reached: int = 0`

**First-time contextual messages** (from design vision section):
- Track via dialogue_flags: `"seen_first_contraband"`, `"seen_first_inspection"`, `"seen_first_heat_gain"`, `"seen_first_black_market"`, `"seen_first_hidden_compartment"`
- Show brief explanatory overlay on first encounter of each mechanic
- Messages defined in onboarding section of this document

**Notification integration**:
- Criminal heat changes: "+5 Criminal Heat" / "Criminal heat decayed to X"
- Contract events: "Contract accepted", "Contract completed: +X CR", "Contract expired"
- Bounty hunter warnings at heat thresholds

**Tests** (~5):
- Achievement data loads correctly
- Player smuggling stats serialize
- First-time flags prevent repeat messages
- Heat notifications fire at threshold crossings
- Contract notifications on accept/complete/expire

---

## Phase E Testing Strategy

Each step follows TDD (Red-Green-Refactor). Estimated ~58 new tests across E.1-E.8.

### Model Tests (E.1)
- Player black_market_access field: grant, has, round-trip
- Save backward compat (old saves without new fields)
- get_black_market_name for valid/invalid systems
- SmugglingContractManager save/load

### Engine Integration Tests (E.2, E.5)
- DataLoader loads faction laws
- Inspection trigger logic with modifiers
- Inspection encounter builds and resolves
- Bounty hunter trigger logic
- Criminal heat decay per day
- Encounter reward application (fines, confiscation, heat)

### View Tests (E.3, E.4, E.6, E.7)
- Black market tab visibility and mode toggle
- Black market pricing and tariff bypass
- Smuggling contract display and acceptance
- Hidden compartment cargo transfer
- Smuggling upgrade availability per location
- Legality indicators on normal market

### Achievement & Polish Tests (E.8)
- New achievements load and trigger
- New player stat fields serialize
- First-time message flags

---

## Metrics & Balance Targets

| Metric | Target |
|--------|--------|
| Smuggling profit margin vs. legal trade | 2x-4x (risk premium) |
| Average inspection evasion rate (no upgrades) | ~85% in Guild space |
| Average inspection evasion rate (full upgrades) | ~95% in Guild space |
| Criminal heat decay to zero from max | ~100 game days |
| Bounty hunter encounter difficulty | Comparable to "dangerous" system combat encounters |
| Time to unlock first black market | Mission 10 (mid Act One) |
| Smuggling contract completion rate (target) | 70-80% (should feel tense, not impossible) |

---

## What This Does NOT Include

- **Piracy mechanics**: Taking cargo from other ships. Deferred to Act Two fleet mechanics.
- **Smuggling mini-game**: No special gameplay for hiding cargo. The upgrades and skills handle it through stats.
- **Faction-specific contraband lists**: Phase 1 uses the base commodity legality. Per-faction contraband customization is a Phase 2 refinement if needed.
- **NPC smuggling crew member**: The Smuggler/Rogue crew archetype from `10_campaign_rpg_crew.md` is deferred. Existing crew (especially Tomas) provide smuggling bonuses through their existing ability systems.
- **Smuggling guilds/organizations**: No separate faction for criminals. Criminal reputation is tracked via heat, not a faction. Keeps the system simpler and avoids a "fifth faction" that dilutes the existing four.

---

## Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| `Legality` enum on Commodity | COMPLETE | 5 contraband commodities added |
| Trade permit system | COMPLETE | Bills of landing gate buy/sell |
| Tariff system | COMPLETE | Faction tariffs with rep modifiers |
| Social skills | COMPLETE | Persuasion/Intimidation/Observation |
| Ship upgrade slots (utility) | COMPLETE | Per-category slot system |
| Faction reputation | COMPLETE | -100 to +100, 5 tiers |
| Travel encounter system | COMPLETE | `_check_travel_encounter()` hook |
| Encounter view | COMPLETE | Renders EncounterDefinition with choices |
| Combat view | COMPLETE | Handles bounty hunter combat |
| Smuggling models (A-D) | COMPLETE | 1794 lines in `models/smuggling.py` |
| Faction laws data | COMPLETE | `data/economy/faction_laws.json` |
| Contraband commodities | COMPLETE | 5 entries in `commodities.json` |
| Smuggling tests (A-D) | COMPLETE | 5 test files, comprehensive coverage |
| Campaign Missions 07, 09, 10 | NOT STARTED | Narrative entry points for black market unlocks |

---

## Critical Files for Phase E

| File | Action |
|------|--------|
| `spacegame/models/player.py` | MODIFY — black_market_access set, smuggling stats |
| `spacegame/models/smuggling.py` | MODIFY — simplify access to permit model, add get_black_market_name |
| `spacegame/save_manager.py` | MODIFY — serialize new player fields |
| `spacegame/data_loader.py` | MODIFY — load faction laws |
| `spacegame/engine/game.py` | MODIFY — inspection hook, bounty hook, heat decay, contract manager |
| `spacegame/views/trading_view.py` | MODIFY — black market mode, legality indicators |
| `spacegame/views/station_hub_view.py` | MODIFY — heat display in status bar |
| `data/progression/achievements.json` | MODIFY — 3 new smuggling achievements |
| `tests/test_models/test_black_market.py` | MODIFY — update for permit-based access |
| `tests/test_views/test_trading_view.py` | MODIFY or CREATE — black market mode tests |
| `tests/test_engine/` | CREATE — inspection and bounty integration tests |
