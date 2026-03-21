# Content Requirements

> **Implementation Status** (Updated 2026-02-27): MVP COMPLETE, EXCEEDS TARGETS + PHASE 1 COMPLETE
>
> - **Star systems**: 10 implemented (MVP target: 10-15) — MET
> - **Commodities**: 19 implemented (MVP target: 8-12) — EXCEEDED
> - **Ship types**: 6 implemented (MVP target: 4-6) — MET
> - **Ship upgrades**: 5 implemented
> - **Skill trees**: 2 trees, 10 skills
> - **Mining**: 4 rock types, 2 system configs
> - **Salvage**: 3 item types, 2 system configs
> - **Refining**: 6 recipes
> - **Market events**: 4 types (shortage, surplus, disaster, boom) — fully surfaced with modal/banner notifications, galaxy map indicators, trading view banners, persistent event log
> - **Achievements**: 21 achievements across 6 categories (trading, wealth, exploration, mining, salvage, progression) with varied rewards (XP, credits, skill points) — IMPLEMENTED
> - **Player statistics**: Lifetime stat tracking (credits earned/spent, trades, jumps, fuel, ore mined, items salvaged/refined, largest profit) — IMPLEMENTED
> - **Tutorial**: 5-step interactive tutorial with auto-trigger, skip, and replay — IMPLEMENTED
> - **Factions**: Referenced in system data but not functionally implemented — Phase 2+
> - **Narrative content**: NOT STARTED — missions, dialogue, crew backstories are Phase 2+
> - **v1.0 expansion targets** (30-50 systems, 8-12 ships, 20-30 event types): NOT STARTED

## 1. Overview

This document defines the specific content that needs to be created for the game, including star systems, commodities, ships, factions, events, and narrative elements. It provides concrete specifications to guide content creation.

## 2. Scope Definition

### 2.1 MVP Content Goals

**Minimum Viable Product should include:**
- 10-15 star systems
- 8-12 tradeable commodities
- 4-6 ship types
- 3-4 major factions
- Basic random events (5-10 types)
- Minimal narrative/flavor text

### 2.2 Full Release Content Goals

**Version 1.0 should include:**
- 30-50 star systems
- 15-20 tradeable commodities
- 8-12 ship types
- 5-6 major factions
- Extensive event system (20-30 event types)
- Rich narrative elements and lore
- 10-15 special missions/quests

### 2.3 Post-Release Expansions

**Future DLC/Updates could add:**
- New sectors (20-30 additional systems)
- Exotic commodities and luxury goods
- Specialized ship variants
- New factions and storylines
- Seasonal events
- Procedurally generated content

## 3. Star Systems Content

### 3.1 System Types Distribution

**For 15-system MVP:**
- **Trade Hubs**: 2 systems (13%)
- **Agricultural**: 3 systems (20%)
- **Industrial**: 3 systems (20%)
- **Mining**: 3 systems (20%)
- **Research**: 2 systems (13%)
- **Frontier**: 2 systems (13%)

### 3.2 System Naming Conventions

**Categories:**
- **Real Stars**: Sol, Alpha Centauri, Proxima, Sirius, Vega
- **Greek Letters**: Beta Hydri, Gamma Pavonis, Delta Eridani
- **Descriptive**: New Terra, Port Meridian, Haven's Edge
- **Fictional**: Zaros Prime, Nexus Station, The Crucible

### 3.3 MVP System Specifications

#### System 1: Sol (Starting System)
- **Type**: Trade Hub
- **Faction**: Trade Federation
- **Danger**: Safe
- **Stations**: 2 (Main Station, Orbital Platform)
- **Production**: Manufactured Goods
- **Consumption**: Raw Materials, Food
- **Description**: "Humanity's birthplace and the heart of galactic trade. Sol Station serves as the central hub for new traders."
- **Connected To**: Alpha Centauri, Proxima, Vega

#### System 2: Alpha Centauri
- **Type**: Agricultural
- **Faction**: Colonial Union
- **Danger**: Safe
- **Stations**: 1 (Centauri Farms)
- **Production**: Food, Textiles
- **Consumption**: Machinery, Fuel
- **Description**: "Vast agricultural colonies spread across three terraformed worlds. The breadbasket of the core systems."
- **Connected To**: Sol, Proxima, Beta Hydri

#### System 3: Proxima
- **Type**: Industrial
- **Faction**: Industrial Consortium
- **Danger**: Moderate
- **Stations**: 2 (Factory Prime, Assembly Dock)
- **Production**: Machinery, Electronics
- **Consumption**: Metals, Food
- **Description**: "Sprawling factory complexes orbit a red dwarf star. The industrial engine of the galaxy."
- **Connected To**: Sol, Alpha Centauri, Sirius

#### System 4: Vega
- **Type**: Mining
- **Faction**: Industrial Consortium
- **Danger**: Moderate
- **Stations**: 1 (Mining Outpost 7)
- **Production**: Common Metals, Rare Metals
- **Consumption**: Food, Machinery, Fuel
- **Description**: "Rich asteroid fields surround Vega. Miners work around the clock extracting precious ores."
- **Connected To**: Sol, Gamma Pavonis

#### System 5: Sirius
- **Type**: Research
- **Faction**: Research Collective
- **Danger**: Safe
- **Stations**: 1 (Sirius Research Institute)
- **Production**: Electronics, Medical Supplies
- **Consumption**: Rare Metals, Food
- **Description**: "A gleaming research station where the galaxy's brightest minds push the boundaries of science."
- **Connected To**: Proxima, Delta Eridani

#### System 6: Beta Hydri
- **Type**: Agricultural
- **Faction**: Colonial Union
- **Danger**: Safe
- **Stations**: 1 (Hydri Plantations)
- **Production**: Food, Textiles
- **Consumption**: Fuel, Machinery
- **Description**: "Tropical paradise worlds known for exotic crops and luxury textiles."
- **Connected To**: Alpha Centauri, New Terra

#### System 7: Gamma Pavonis
- **Type**: Mining
- **Faction**: Independent Spacers
- **Danger**: Moderate
- **Stations**: 1 (Pavonis Mining Co.)
- **Production**: Rare Metals, Fuel
- **Consumption**: Food, Machinery
- **Description**: "Independent mining operation in a lawless region. High profits, higher risks."
- **Connected To**: Vega, The Frontier

#### System 8: Delta Eridani
- **Type**: Industrial
- **Faction**: Industrial Consortium
- **Danger**: Moderate
- **Stations**: 1 (Delta Works)
- **Production**: Machinery, Manufactured Goods
- **Consumption**: Metals, Electronics
- **Description**: "A secondary industrial center specializing in heavy machinery."
- **Connected To**: Sirius, New Terra

#### System 9: New Terra
- **Type**: Trade Hub
- **Faction**: Trade Federation
- **Danger**: Safe
- **Stations**: 2 (Port Authority, Trade Exchange)
- **Production**: Luxury Goods
- **Consumption**: All goods (trade hub)
- **Description**: "A bustling commercial center at the crossroads of major trade routes."
- **Connected To**: Beta Hydri, Delta Eridani, Haven's Edge

#### System 10: Haven's Edge
- **Type**: Frontier
- **Faction**: Independent Spacers
- **Danger**: Dangerous
- **Stations**: 1 (Edge Station - small outpost)
- **Production**: None (trade only)
- **Consumption**: All goods (high prices)
- **Description**: "The last civilized stop before uncharted space. Traders and outlaws mingle freely."
- **Connected To**: New Terra, The Frontier, Zaros Prime

#### System 11: The Frontier
- **Type**: Frontier
- **Faction**: None (Lawless)
- **Danger**: Dangerous
- **Stations**: 1 (Freeport Station - small)
- **Production**: Illegal Goods (black market)
- **Consumption**: Weapons, Fuel
- **Description**: "No laws, no questions. Fortune favors the bold... or the reckless."
- **Connected To**: Gamma Pavonis, Haven's Edge

#### System 12: Zaros Prime
- **Type**: Research
- **Faction**: Research Collective
- **Danger**: Moderate
- **Stations**: 1 (Zaros Lab)
- **Production**: Medical Supplies, Electronics
- **Consumption**: Rare Metals, Luxury Goods
- **Description**: "Cutting-edge xenobiology research station studying alien artifacts."
- **Connected To**: Haven's Edge, Omega Station

#### System 13: Omega Station
- **Type**: Mining
- **Faction**: Industrial Consortium
- **Danger**: Dangerous
- **Stations**: 1 (Omega Deep Mine)
- **Production**: Rare Metals, Precious Metals
- **Consumption**: Food, Fuel, Medical Supplies
- **Description**: "Deep space mining operation. High yield, high danger from unstable asteroids."
- **Connected To**: Zaros Prime, Vega

#### System 14: Port Meridian
- **Type**: Industrial
- **Faction**: Trade Federation
- **Danger**: Safe
- **Stations**: 1 (Meridian Shipyards)
- **Production**: Ships (shipyard location), Manufactured Goods
- **Consumption**: Metals, Electronics
- **Description**: "Premier shipyards where the finest trading vessels are constructed."
- **Connected To**: Sol, New Terra

#### System 15: Elysium
- **Type**: Agricultural
- **Faction**: Colonial Union
- **Danger**: Safe
- **Stations**: 1 (Elysium Estates)
- **Production**: Luxury Goods, Food
- **Consumption**: Art, Precious Metals
- **Description**: "Luxury resort world catering to wealthy traders and tourists."
- **Connected To**: New Terra, Beta Hydri

### 3.4 Galaxy Connectivity Map

```
        Sol ─────── Vega ─────── Gamma Pavonis ─── The Frontier
         │           │                                    │
         │           │                                    │
    Alpha Centauri   └── Omega Station                   │
         │               └── Zaros Prime                  │
         │                       │                        │
    Beta Hydri             Haven's Edge ──────────────────┘
         │                       │
         │                       │
    Elysium ────── New Terra ────┤
                        │        │
                   Port Meridian │
                        │        │
    Proxima ─── Sirius ─ Delta Eridani
```

## 4. Commodity Content

### 4.1 MVP Commodity List (12 items)

#### Basic Commodities (4)

1. **Food & Water**
   - Base Price: 50 CR
   - Variance: ±20%
   - Volume: 1 unit/cargo
   - Production: Agricultural systems
   - High Demand: All systems

2. **Textiles**
   - Base Price: 80 CR
   - Variance: ±25%
   - Volume: 1 unit/cargo
   - Production: Agricultural systems
   - High Demand: Trade hubs, Frontier

3. **Fuel (Hydrogen)**
   - Base Price: 40 CR
   - Variance: ±15%
   - Volume: 1 unit/cargo
   - Production: Mining systems
   - High Demand: All systems (universal need)

4. **Common Metals (Iron, Copper)**
   - Base Price: 100 CR
   - Variance: ±30%
   - Volume: 2 units/cargo
   - Production: Mining systems
   - High Demand: Industrial systems

#### Industrial Commodities (4)

5. **Machinery**
   - Base Price: 250 CR
   - Variance: ±35%
   - Volume: 5 units/cargo
   - Production: Industrial systems
   - High Demand: Agricultural, Mining systems

6. **Electronics**
   - Base Price: 400 CR
   - Variance: ±40%
   - Volume: 2 units/cargo
   - Production: Research, Industrial systems
   - High Demand: All systems

7. **Rare Metals (Platinum, Titanium)**
   - Base Price: 600 CR
   - Variance: ±50%
   - Volume: 3 units/cargo
   - Production: Mining systems
   - High Demand: Research, Industrial systems

8. **Manufactured Goods**
   - Base Price: 350 CR
   - Variance: ±40%
   - Volume: 3 units/cargo
   - Production: Industrial, Trade hub systems
   - High Demand: Frontier, Agricultural systems

#### Luxury Commodities (4)

9. **Medical Supplies**
   - Base Price: 800 CR
   - Variance: ±60%
   - Volume: 2 units/cargo
   - Production: Research systems
   - High Demand: Mining, Frontier, dangerous systems

10. **Luxury Goods (Art, Jewelry)**
    - Base Price: 1,200 CR
    - Variance: ±70%
    - Volume: 1 unit/cargo
    - Production: Trade hubs, special systems
    - High Demand: Research systems, wealthy systems

11. **Precious Metals (Gold, Silver)**
    - Base Price: 1,500 CR
    - Variance: ±60%
    - Volume: 2 units/cargo
    - Production: Mining systems (rare)
    - High Demand: Trade hubs, Luxury systems

12. **Exotic Goods (Alien Artifacts - optional illegal)**
    - Base Price: 2,500 CR
    - Variance: ±80%
    - Volume: 1 unit/cargo
    - Legality: Restricted (illegal in some systems)
    - Production: Frontier, special events
    - High Demand: Research systems, Black markets

### 4.2 Commodity Icons/Visual Design

Each commodity needs a simple icon (32x32 or 64x64 pixels):
- **Food**: Wheat or apple icon
- **Textiles**: Fabric bolt
- **Fuel**: Fuel canister or hydrogen molecule
- **Common Metals**: Ingot or ore chunk
- **Machinery**: Gear or wrench
- **Electronics**: Circuit board or chip
- **Rare Metals**: Shiny ingot or crystal
- **Manufactured Goods**: Box or crate
- **Medical Supplies**: Medical cross or pill bottle
- **Luxury Goods**: Diamond or crown
- **Precious Metals**: Gold bar
- **Exotic Goods**: Alien artifact or mysterious object

## 5. Ship Content

### 5.1 MVP Ship Types (6 ships)

#### 1. Shuttle
- **Class**: Starter
- **Cargo**: 50 units
- **Fuel Capacity**: 100 units
- **Fuel Efficiency**: 10 units/jump
- **Price**: 5,000 CR (or free starter ship)
- **Resale**: 3,000 CR
- **Availability**: All shipyards
- **Description**: "A basic transport shuttle. Gets you started, but you'll outgrow it quickly."

#### 2. Light Freighter
- **Class**: Early-game trader
- **Cargo**: 150 units
- **Fuel Capacity**: 150 units
- **Fuel Efficiency**: 15 units/jump
- **Price**: 25,000 CR
- **Resale**: 17,500 CR
- **Availability**: All shipyards
- **Description**: "Reliable workhorse for aspiring traders. Balanced stats for diverse routes."

#### 3. Medium Freighter
- **Class**: Mid-game trader
- **Cargo**: 300 units
- **Fuel Capacity**: 250 units
- **Fuel Efficiency**: 20 units/jump
- **Price**: 100,000 CR
- **Resale**: 70,000 CR
- **Availability**: Major stations only
- **Description**: "Serious cargo capacity for established traders. The backbone of interstellar commerce."

#### 4. Fast Courier
- **Class**: Specialist (speed)
- **Cargo**: 100 units
- **Fuel Capacity**: 300 units
- **Fuel Efficiency**: 8 units/jump
- **Speed**: 2x travel speed (if real-time)
- **Price**: 150,000 CR
- **Resale**: 105,000 CR
- **Availability**: Select shipyards (Port Meridian, New Terra)
- **Description**: "Speed is money. Perfect for time-sensitive luxury goods and rapid trading."

#### 5. Heavy Hauler
- **Class**: Late-game bulk trader
- **Cargo**: 600 units
- **Fuel Capacity**: 350 units
- **Fuel Efficiency**: 35 units/jump
- **Price**: 500,000 CR
- **Resale**: 350,000 CR
- **Availability**: Major shipyards only
- **Description**: "Massive cargo holds for bulk commodity trading. High operating costs, high rewards."

#### 6. Corvette
- **Class**: Specialist (combat-capable)
- **Cargo**: 200 units
- **Fuel Capacity**: 250 units
- **Fuel Efficiency**: 18 units/jump
- **Defense**: High armor/shields (reduces pirate damage)
- **Price**: 750,000 CR
- **Resale**: 525,000 CR
- **Availability**: Special shipyards only
- **Description**: "Armed trader for dangerous routes. Sacrifices cargo for survivability."

### 5.2 Ship Visual Design

Each ship needs a simple sprite (64x64 to 128x128 pixels):
- **Shuttle**: Small, boxy design
- **Light Freighter**: Classic spaceship silhouette
- **Medium Freighter**: Larger with visible cargo pods
- **Fast Courier**: Sleek, aerodynamic look
- **Heavy Hauler**: Massive bulk freighter
- **Corvette**: Angular, armored appearance

## 6. Faction Content

### 6.1 MVP Factions (4)

#### 1. Trade Federation
- **Focus**: Commerce and trade
- **Controlled Systems**: Sol, New Terra, Port Meridian
- **Reputation Benefits**:
  - -1% tariffs per 10 rep points
  - Access to exclusive trade contracts at 75+ rep
- **Rival Factions**: Independent Spacers (-0.3 ratio)
- **Description**: "The Trade Federation governs the core systems, promoting free trade and economic prosperity. Their efficient bureaucracy keeps commerce flowing smoothly."
- **Aesthetic**: Clean, corporate, blue/gold colors

#### 2. Colonial Union
- **Focus**: Agriculture and settlement
- **Controlled Systems**: Alpha Centauri, Beta Hydri, Elysium
- **Reputation Benefits**:
  - Discounts on agricultural goods at 50+ rep
  - Access to colonial expansion missions at 60+ rep
- **Rival Factions**: Industrial Consortium (-0.2 ratio)
- **Description**: "The Colonial Union represents the frontier settlers and agricultural worlds. They value hard work, community, and sustainable growth."
- **Aesthetic**: Rustic, green/brown colors, agrarian

#### 3. Industrial Consortium
- **Focus**: Manufacturing and mining
- **Controlled Systems**: Proxima, Vega, Delta Eridani, Omega Station
- **Reputation Benefits**:
  - Discounts on machinery and metals at 50+ rep
  - Priority access to ship upgrades at 65+ rep
- **Rival Factions**: Colonial Union (-0.2 ratio)
- **Description**: "The Industrial Consortium controls the galaxy's manufacturing might. Efficiency and production are their creed."
- **Aesthetic**: Industrial, gray/orange colors, mechanical

#### 4. Independent Spacers
- **Focus**: Freedom and autonomy
- **Controlled Systems**: Gamma Pavonis, Haven's Edge, The Frontier
- **Reputation Benefits**:
  - Access to black markets at 50+ rep
  - Reduced pirate encounters at 70+ rep (if implemented)
- **Rival Factions**: Trade Federation (-0.3 ratio)
- **Description**: "Independent traders, miners, and adventurers who reject centralized authority. Freedom comes first, profit second."
- **Aesthetic**: Scrappy, diverse, purple/gray colors

#### 5. Research Collective (Optional 5th faction)
- **Focus**: Science and knowledge
- **Controlled Systems**: Sirius, Zaros Prime
- **Reputation Benefits**:
  - Discounts on electronics and medical supplies at 50+ rep
  - Access to experimental ship upgrades at 75+ rep
- **Rival Factions**: None (neutral with all)
- **Description**: "The Research Collective is dedicated to advancing knowledge and technology. They value discovery above all else."
- **Aesthetic**: High-tech, white/cyan colors, futuristic

### 6.2 Faction Missions (Post-MVP)

Each faction offers missions at high reputation:
- **Trade Federation**: Deliver goods on tight schedules
- **Colonial Union**: Aid missions to struggling colonies
- **Industrial Consortium**: Transport raw materials for production quotas
- **Independent Spacers**: Smuggling runs (high risk/reward)
- **Research Collective**: Deliver rare samples and data

## 7. Random Events Content

### 7.1 MVP Events (10 types)

#### Positive Events

1. **Market Boom**
   - **Trigger**: 10% chance on system arrival
   - **Effect**: +20% to all prices for 3 game days
   - **Text**: "Economic boom sweeps [System]! Prices are soaring."

2. **Surplus Discovery**
   - **Trigger**: 8% chance on system arrival
   - **Effect**: One commodity -30% price, high supply
   - **Text**: "A massive surplus of [Commodity] floods the market."

3. **First Discovery Bonus**
   - **Trigger**: Visiting system for first time
   - **Effect**: Earn 500-2,000 CR
   - **Text**: "First discovery bonus: [Amount] CR for charting [System]."

4. **Trade Tip**
   - **Trigger**: 5% chance at station
   - **Effect**: Reveal profitable route suggestion
   - **Text**: "A fellow trader whispers: '[System] is buying [Commodity] at premium prices.'"

#### Negative Events

5. **Market Crash**
   - **Trigger**: 5% chance on system arrival
   - **Effect**: -20% to all prices for 3 game days
   - **Text**: "Economic downturn hits [System]. Prices plummet."

6. **Shortage**
   - **Trigger**: 10% chance on system arrival
   - **Effect**: One commodity +40% price, low supply
   - **Text**: "Critical shortage of [Commodity]! Prices skyrocket."

7. **Fuel Leak**
   - **Trigger**: 3% chance during travel
   - **Effect**: Lose 10-20 fuel units
   - **Text**: "Warning: Fuel leak detected. You've lost [Amount] fuel."

#### Neutral Events

8. **Distress Signal**
   - **Trigger**: 5% chance during travel
   - **Effect**: Choice - help for rep gain or ignore
   - **Text**: "You receive a distress signal. Respond? (costs fuel, grants reputation)"

9. **Inspection**
   - **Trigger**: 5% chance with illegal cargo
   - **Effect**: Confiscation or fine if carrying illegal goods
   - **Text**: "Security inspection! Your illegal cargo is confiscated and you're fined [Amount] CR."

10. **Debris Field**
    - **Trigger**: 3% chance during travel
    - **Effect**: Find salvage (random commodity, 5-15 units)
    - **Text**: "You discover a debris field. Salvage recovered: [Commodity] x [Amount]."

### 7.2 Event Expansion (Post-MVP)

Future events:
- **Pirate Encounters**: Combat or bribe options
- **Natural Disasters**: System-wide supply disruptions
- **Political Events**: Faction wars, trade embargoes
- **Special Encounters**: Unique NPCs, rare opportunities
- **Timed Events**: Limited-time market opportunities

## 8. Narrative and Flavor Text

### 8.1 Tutorial Narrative (Brief)

**Opening Text (Optional):**
> "The year is 2387. Humanity has spread across dozens of star systems, connected by faster-than-light jump gates. The galaxy's economy thrives on traders like you—willing to risk the void for profit.
>
> You've just acquired your first ship, a modest shuttle. Your goal? Build a trading empire across the stars. Buy low, sell high, and watch your fortune grow. The galaxy awaits, Captain."

### 8.2 Station Descriptions

Each station type has flavor text:
- **Major Stations**: "Bustling corridors filled with traders from across the galaxy."
- **Minor Outposts**: "A small, utilitarian station serving local needs."
- **Frontier Stations**: "Rough and ready. Keep your hand on your credits."

### 8.3 Achievement Flavor Text

- **"First Fortune"**: "100,000 credits earned. You're no longer a rookie."
- **"Galactic Explorer"**: "You've seen it all. Every system mapped."
- **"Trade Baron"**: "10 million credits. The galaxy bows to your wealth."

### 8.4 Ship Purchase Flavor

When buying a ship:
> "The shipyard technician shakes your hand. 'She's all yours, Captain. Treat her well and she'll make you rich.'"

### 8.5 Lore Elements (Optional)

**Background Lore:**
- Jump gate technology discovered in 2250
- First colonies established in 2280
- Trade Federation formed in 2300
- Current era: Free trade expansion phase

**Alien Artifacts:**
- Hints of ancient alien civilization
- Mysterious artifacts fuel research
- No living aliens encountered (yet)

## 9. Audio Content (Post-MVP)

### 9.1 Sound Effects Needed

- **UI Sounds**: Button click, hover, error beep
- **Transaction**: Cash register ding, trade complete
- **Travel**: Jump whoosh, engine hum
- **Events**: Alert klaxon, achievement chime
- **Ambient**: Station background noise, space hum

### 9.2 Music Tracks

- **Main Menu**: Ambient space theme
- **Galaxy Map**: Calm exploration music
- **Trading**: Upbeat, business-like track
- **Danger**: Tense music for risky situations

## 10. Visual Assets

### 10.1 UI Assets Needed

- **Backgrounds**: Starfield, station interior, menu backdrop
- **Icons**: 12 commodity icons, ship icons, UI action icons
- **Fonts**: Sci-fi or clean sans-serif, multiple sizes
- **Buttons**: Standard button states (normal, hover, pressed, disabled)

### 10.2 Ship Sprites

- 6 ship sprites (side or 3/4 view)
- Simple, recognizable silhouettes
- Optional: Animated thrusters or lights

### 10.3 Map Graphics

- **System Nodes**: Circular icons, color-coded by type
- **Connection Lines**: Simple lines or dashed routes
- **Selection**: Highlight/glow effect
- **HUD Elements**: Fuel gauge, cargo bar, credit display

## 11. Localization (Post-MVP)

### 11.1 Text to Translate

- All UI labels and buttons
- System and station names
- Commodity names and descriptions
- Event text and dialogues
- Tutorial and help text

### 11.2 Supported Languages (Future)

- English (primary)
- Spanish, French, German, Japanese, Chinese (expansion)

## 12. Content Creation Pipeline

### 12.1 Asset Creation Workflow

1. **Design**: Spec out asset (size, style, purpose)
2. **Create**: Artist/designer creates asset
3. **Review**: Check against requirements
4. **Integrate**: Add to game data files
5. **Test**: Verify in-game appearance and function

### 12.2 Data Entry Workflow

1. **Define**: Specify commodity/ship/system attributes
2. **Create JSON**: Add entry to config file
3. **Validate**: Check JSON syntax and values
4. **Test**: Load in game and verify behavior
5. **Balance**: Adjust values based on playtesting

### 12.3 Content Versioning

- Track content changes in git
- Version config files with game version
- Maintain backward compatibility for saves

## 13. Content Testing and Balancing

### 13.1 Balance Targets

**Commodity Prices:**
- No single route should dominate (>100% profit margin)
- All commodities should have viable trading opportunities
- Price variance should feel dynamic but not random

**Ship Progression:**
- Each ship upgrade should feel meaningful
- Purchase costs align with 2-5 hours of gameplay per tier
- No ship obsoletes all others

**Event Frequency:**
- Events feel special but not overwhelming
- Positive and negative events roughly balanced
- Critical failures (fuel loss) rare enough not to frustrate

### 13.2 Playtesting Checklist

- [ ] All systems reachable from starting position
- [ ] All commodities available somewhere
- [ ] All ships purchasable in at least one location
- [ ] Reputation gains/losses feel fair
- [ ] Events trigger at reasonable rates
- [ ] Progression curve feels smooth

## 14. Content Expansion Roadmap

### 14.1 Priority 1 (Post-MVP)

- Expand to 30 systems
- Add 5 more commodities
- Implement mission system
- Add more random events

### 14.2 Priority 2 (v1.5)

- Second galaxy sector (20 systems)
- Combat system and pirate encounters
- Special quest lines
- Unique ship variants

### 14.3 Priority 3 (v2.0)

- Modding support for custom content
- Procedural galaxy generation
- Seasonal events
- Multiplayer trading (stretch goal)

## 15. Open Questions

- Should systems have multiple stations or keep it simple (1-2 per system)?
- How much lore/narrative is too much for a trading sim?
- Should there be unique "legendary" ships?
- Are commodities strictly economic or do some have quest purposes?
- Should player be able to name their ship?

---

**Document Status**: Draft v1.0
**Last Updated**: 2025-10-18
**Next Steps**: Begin content creation and integration into game data files
