# Campaign, RPG & Crew System Requirements

> **Implementation Status** (Updated 2026-02-27): NOT YET STARTED
>
> This entire document describes Phase 2+ features. None of the systems below are implemented yet:
> - **Campaign/story missions**: Not started — `GameState.DIALOGUE` and `GameState.MISSION_BRIEFING` are reserved in config.py
> - **Crew recruitment/management**: Not started — ship data defines `crew_slots` but no crew system exists
> - **Faction reputation**: Not started — faction names exist in system data but no reputation tracking
> - **Dialogue system**: Not started
> - **Character captain skills (3rd tree)**: Not started — 2 of 3 planned skill trees are implemented
> - **Architecture readiness**: The game's view/model/engine architecture fully supports adding these systems incrementally

## 1. Overview

This document defines the narrative campaign, character progression (captain skills), and crew management systems that form the RPG layer of the space trading game. These systems enhance and complement the core trading gameplay while providing narrative context and character-driven motivation.

## 2. Design Philosophy

### 2.1 Core Principles

**Trading First, Story Enhances:**
- The game is fundamentally about space trading
- Story provides context, motivation, and rewards
- Never force players away from trading mechanics
- Story missions integrate trading objectives

**Crew as Trading Assets:**
- Crew members provide mechanical benefits to trading/ship operations
- Personal stories add emotional investment
- Simple to understand, meaningful in impact

**Meaningful Choices:**
- Player decisions affect story outcomes
- Choices have visible consequences
- Multiple valid approaches to problems

### 2.2 Integration Goals

- Story unlocks new trading opportunities
- Crew skills enhance economic gameplay
- Character progression feels rewarding
- Narrative doesn't interrupt gameplay flow

## 3. Campaign Structure

### 3.1 Main Campaign Overview

**Length:** 15-20 hours for full completion
**Structure:** Three-act narrative with branching paths
**Tone:** Space opera with personal stakes and galactic intrigue
**Theme:** Building something meaningful (your trading empire) in a changing galaxy

### 3.2 Act I: "New Beginnings" (5-7 hours)

**Story Goals:**
- Introduce the player character (captain) and starting circumstances
- Meet 2-3 core crew members
- Establish the central conflict/mystery
- Tutorial integrated into narrative

**Narrative Beats:**
1. **Opening**: You inherit/acquire a small trading ship under mysterious circumstances
2. **First Crew**: Recruit your first officer (pilot/navigator)
3. **The Hook**: Discover a conspiracy, lost artifact, or galactic threat during routine trade
4. **Escalation**: Get drawn into larger events beyond simple trading
5. **Act Break**: Major revelation that raises stakes and opens Act II

**Gameplay Integration:**
- Learn trading through story-mandated trades
- First crew member teaches navigation/basics
- Story unlocks 3-5 new systems to explore
- Economic foundation built while story unfolds

**Key Crew Recruitment:**
- First Officer (mandatory, story-given)
- Engineer (optional, increases ship efficiency)
- Merchant (optional, improves trade prices)

### 3.3 Act II: "Rising Tensions" (6-8 hours)

**Story Goals:**
- Expand the crew with diverse specialists
- Develop faction relationships
- Player makes significant choices affecting story direction
- Build toward climax

**Narrative Beats:**
1. **Expansion**: Establish yourself as a serious trader while investigating mystery
2. **Faction Choice**: Align with one or more factions (affects ending)
3. **Crew Development**: Personal missions for crew members unlock their backstories
4. **Complications**: Antagonist forces reveal themselves
5. **Crisis**: Major setback that forces player to choose a path
6. **Act Break**: Point of no return approaching

**Gameplay Integration:**
- Faction missions provide trading contracts
- Crew member abilities unlock through personal quests
- New systems unlock based on story progression
- Economic success enables story progression (need certain ship/credits)

**Key Crew Recruitment:**
- Diplomat/Negotiator (faction relationships)
- Combat Specialist (for dangerous routes)
- Scientist/Researcher (unlocks special cargo types)
- Smuggler/Rogue (black market access)

### 3.4 Act III: "Convergence" (4-5 hours)

**Story Goals:**
- Resolve central conflict
- Player choices determine ending
- Satisfying conclusion to character arcs
- Unlock sandbox mode

**Narrative Beats:**
1. **Preparation**: Final buildup, gathering resources/allies
2. **Confrontation**: Face the antagonist/resolve the mystery
3. **Climax**: Major story decision with consequences
4. **Resolution**: Different endings based on player choices
5. **Epilogue**: Show the results of player's decisions
6. **Sandbox Unlock**: "Continue your journey" post-campaign

**Gameplay Integration:**
- Final missions require significant trading success
- All crew abilities useful in resolution
- Faction choices pay off
- Economic empire is the foundation for story success

**Possible Endings:**
- Faction-specific endings (3-4 variations)
- Economic ending (pure trade baron)
- Rebel/Independence ending
- Sacrifice/Heroic ending
- Dark/Pragmatic ending

### 3.5 Campaign Missions

**Mission Types:**

#### Main Story Missions
- **Format**: Narrative dialogue + trading/travel objective
- **Example**: "Transport secret cargo to Beta System while avoiding inspections"
- **Rewards**: Story progression, system unlocks, crew members
- **Frequency**: 20-30 main missions across campaign

#### Crew Personal Missions
- **Format**: Focus on one crew member's backstory
- **Example**: Help your engineer reconcile with their family
- **Rewards**: Unlock crew ability upgrade, deepen relationship
- **Frequency**: 2-3 missions per crew member (20-40 total)

#### Faction Missions
- **Format**: Repeatable missions for faction reputation
- **Example**: Establish trade route for Colonial Union
- **Rewards**: Faction reputation, credits, occasional story impact
- **Frequency**: 5-10 per faction (20-40 total)

#### Side Stories
- **Format**: Self-contained short narratives
- **Example**: Investigate disappearance of traders in sector
- **Rewards**: Credits, unique items, lore
- **Frequency**: 10-20 optional side stories

### 3.6 Mission Structure Template

```
Mission: [Name]
Type: [Main/Crew/Faction/Side]
Giver: [NPC Name]
Location: [System/Station]

Briefing:
  - Dialogue introducing mission
  - Player can ask questions
  - Accept/Decline choice

Objectives:
  1. [Travel to X system]
  2. [Buy/Sell Y commodity]
  3. [Deliver to Z station]
  4. [Optional: Make choice A or B]

Complications (optional):
  - Random event during travel
  - Moral choice
  - Resource challenge

Resolution:
  - Dialogue upon completion
  - Consequences of choices revealed
  - Rewards granted

Rewards:
  - Credits: [Amount]
  - Reputation: [Faction, +/- Amount]
  - Story: [Unlock/Progress]
  - Items: [Ship upgrade, crew member, etc.]
```

## 4. Captain (Player Character) System

### 4.1 Character Creation

**Character Customization (MVP - Limited):**
- Name your captain
- Choose portrait from 4-6 options
- Select background (affects starting bonuses)

**Background Options:**
1. **Merchant Family** - Start with +10% trade profits, -10% ship costs
2. **Military Veteran** - Start with better ship defenses, +combat crew affinity
3. **Explorer** - Start with better scanner, +discovery bonuses
4. **Scrapper** - Start with cheaper repairs, +salvage from events

**Character Customization (Full Release):**
- Gender selection
- More portrait options (10-15)
- More detailed backgrounds with story implications
- Trait selection (2-3 traits affecting gameplay)

### 4.2 Captain Skills

**Skill System Philosophy:**
- Skills enhance trading and ship operations
- Clear, visible benefits
- No bad choices - all paths viable
- Simple to understand, strategic to optimize

**Skill Trees (3 Primary Trees):**

#### Trading Mastery
- **Focus**: Economic efficiency and profit
- **Level 1**: Negotiator - +5% on all sales
- **Level 2**: Bulk Buyer - -5% on purchases over 50 units
- **Level 3**: Market Sense - See price trends for 7 days instead of 5
- **Level 4**: Trade Connections - Access to exclusive contracts
- **Level 5**: Trade Baron - +10% profit on all trades

#### Navigation & Exploration
- **Focus**: Travel efficiency and discovery
- **Level 1**: Efficient Routing - -10% fuel consumption
- **Level 2**: Quick Jump - -20% travel time (if real-time travel)
- **Level 3**: Explorer's Eye - +50% discovery bonuses
- **Level 4**: Star Cartographer - Reveal adjacent unvisited systems
- **Level 5**: Master Navigator - Free pathfinding shows best profit routes

#### Leadership & Crew
- **Focus**: Crew effectiveness and ship operations
- **Level 1**: Inspiring Captain - Crew abilities +10% effectiveness
- **Level 2**: Crew Manager - Can have +1 crew member on ship
- **Level 3**: Crisis Leadership - Reduce negative event impacts by 25%
- **Level 4**: Reputation - +20% faction reputation gains
- **Level 5**: Fleet Admiral - Second ship operates at 75% efficiency when automated

**Skill Points:**
- Earn 1 skill point per level
- Level up by gaining experience
- Experience from: trades completed, missions finished, systems discovered
- Total of 15-20 skill points available across campaign
- Can't max all trees - forces choices

**Experience Curve:**
- Level 2: 5 trades or 2 missions
- Level 3: 15 trades or 5 missions
- Level 4: 30 trades or 10 missions
- Level 5: 50 trades or 15 missions
- (Scales up, approximately 15-20 levels available)

### 4.3 Player Stats and Tracking

**Visible Stats:**
- **Level**: Current character level
- **Experience**: Progress to next level
- **Total Trades**: Lifetime trade count
- **Total Profit**: Lifetime profit earned
- **Systems Discovered**: Exploration progress
- **Missions Completed**: Story/quest progress
- **Reputation**: Faction standings

**Hidden Stats (affect gameplay subtly):**
- Trade efficiency multiplier (from skills)
- Event luck modifier
- Crew morale impact

## 5. Crew System

### 5.1 Crew Philosophy

**Design Goals:**
- Each crew member feels unique (personality + mechanics)
- Crew provides tangible gameplay benefits
- Simple management (not micromanagement)
- Personal stories create attachment
- Crew integrates with ship systems

### 5.2 Crew Roles and Positions

**Ship Positions (based on ship size):**

#### Small Ships (Shuttle, Light Freighter)
- **Crew Slots**: 2-3
- **Positions**: Captain (player) + 2 crew

#### Medium Ships (Medium Freighter, Courier)
- **Crew Slots**: 4-5
- **Positions**: Captain + 4 crew

#### Large Ships (Hauler, Corvette)
- **Crew Slots**: 6-7
- **Positions**: Captain + 6 crew

**Crew Role Types:**

1. **Pilot/Navigator**
   - **Function**: Reduces fuel consumption or travel time
   - **Bonus**: -10 to -25% fuel costs (scales with rarity/level)

2. **Engineer**
   - **Function**: Improves ship efficiency and repairs
   - **Bonus**: -15% repair costs, reduces breakdown chance

3. **Merchant/Trader**
   - **Function**: Improves trade prices
   - **Bonus**: +5 to +15% profits on trades

4. **Diplomat**
   - **Function**: Improves faction relationships
   - **Bonus**: +25% reputation gains, reduces tariffs

5. **Combat Specialist**
   - **Function**: Improves ship defense (if combat exists)
   - **Bonus**: Reduce pirate encounter damage by 30-50%

6. **Scientist/Researcher**
   - **Function**: Unlocks special cargo or analysis
   - **Bonus**: Identify rare goods, +science faction rep

7. **Smuggler/Rogue**
   - **Function**: Black market access and evasion
   - **Bonus**: Access illegal goods, reduce inspection chance

8. **Cook/Morale Officer** (optional)
   - **Function**: Improves crew effectiveness
   - **Bonus**: All other crew +10% to their bonuses

### 5.3 Crew Member Attributes

**Each Crew Member Has:**

```
CrewMember {
    name: string
    role: enum (Pilot, Engineer, Merchant, etc.)
    portrait: image
    biography: string (short background)
    personality: string (one-line personality summary)

    // Mechanical Stats
    bonus_type: enum (FuelReduction, TradingProfit, etc.)
    bonus_amount: float (10%, 15%, etc.)
    level: int (1-5)

    // Story Integration
    recruited: bool
    loyalty: int (0-100, affects story and effectiveness)
    personal_quest_completed: bool
    story_flags: dict (tracks story choices involving this crew)

    // Dialogue
    idle_dialogue: list[string] (ambient ship chatter)
    mission_dialogue: dict (context-specific lines)
}
```

### 5.4 Crew Recruitment

**Recruitment Methods:**

1. **Story Recruitment** (mandatory crew)
   - First Officer given at campaign start
   - 1-2 others through main story

2. **Mission Recruitment** (optional, story-driven)
   - Meet during side missions
   - Complete a quest to recruit them
   - Example: Help engineer escape debt, they join you

3. **Station Recruitment** (optional, economic)
   - Available at certain stations
   - Pay recruitment fee (2,000-10,000 CR)
   - Random pool of available crew

4. **Event Recruitment** (optional, random)
   - Encounter during travel
   - Make choice to recruit or not
   - Example: Rescue stranded pilot

**Recruitment Costs:**
- Story crew: Free (part of mission)
- Station crew: 2,000-10,000 CR depending on rarity
- Event crew: Usually free, may require quest

### 5.5 Crew Progression

**Crew Leveling:**
- Crew gain experience when assigned to ship during trades/missions
- Level up after 10-20 trades/missions with them aboard
- Leveling increases their bonus (e.g., 10% → 12% → 15% → 18% → 20%)
- Maximum crew level: 5

**Loyalty System:**
- Loyalty ranges from 0-100
- High loyalty (75+): Maximum effectiveness, won't leave
- Medium loyalty (40-74): Normal effectiveness
- Low loyalty (0-39): Reduced effectiveness, may leave

**Loyalty Changes:**
- +5: Complete their personal quest
- +2: Successful mission with them aboard
- +1: Trade with them aboard
- -10: Ignore their personal quest for too long
- -5: Make story choice they disagree with
- -5: Let ship get too damaged without repairs

### 5.6 Crew Personal Quests

**Quest Structure:**
Each recruitable crew member has 1-3 personal missions that:
- Explore their backstory
- Create emotional connection
- Unlock upgraded ability or max loyalty
- Provide story branches

**Example Personal Quest:**

```
Crew: Elena Reeves (Engineer)
Quest: "Ghosts of the Forge"

Part 1: Elena reveals her past at an industrial station
  - Dialogue: She worked at Port Meridian shipyards
  - Trigger: After 10 trades with her aboard

Part 2: Message from her former mentor
  - They need help with failing station
  - Choice: Help (costs time/money) or Ignore
  - Consequence: Loyalty +10 if help, -5 if ignore

Part 3: Resolution
  - If helped: Unlock "Master Engineer" ability (+25% efficiency)
  - If ignored: Elena leaves after campaign Act II
  - Story impact: Port Meridian becomes ally or neutral
```

### 5.7 Crew Management UI

**Ship Crew Screen:**

```
┌──────────────────────────────────────────────────────┐
│ CREW ROSTER: Light Freighter "Endeavor"             │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ACTIVE CREW (3/3 slots)                             │
│  ┌────────────────────────────────────────────────┐ │
│  │ [Portrait] Marcus Chen - Pilot            Lv.3 │ │
│  │ Bonus: -15% Fuel Consumption                   │ │
│  │ Loyalty: 85/100 ████████░░                      │ │
│  │ "I've got your back, Captain."                 │ │
│  │ [Personal Quest Available]  [Remove]           │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ [Portrait] Elena Reeves - Engineer        Lv.2 │ │
│  │ Bonus: -12% Repair Costs                       │ │
│  │ Loyalty: 60/100 ██████░░░░                      │ │
│  │ [Personal Quest: "Ghosts of the Forge"]        │ │
│  │ [View Quest]  [Remove]                         │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  AVAILABLE CREW (Unassigned)                         │
│  - None                                              │
│                                                      │
│  [Visit Recruitment Office]  [Back to Ship]         │
└──────────────────────────────────────────────────────┘
```

### 5.8 Crew Dialogue System

**Dialogue Types:**

1. **Ambient Chatter** (immersion)
   - Random comments while aboard ship
   - React to trades, travel, events
   - Build personality

2. **Mission Dialogue** (story)
   - Key story moments
   - Personal quest dialogue
   - Player choices

3. **Contextual Comments** (feedback)
   - Comment on player decisions
   - Warn about dangers
   - Celebrate successes

**Dialogue Format:**
```
[Character Name]: "Dialogue text here."
  → [Player Response Option 1]
  → [Player Response Option 2]
  → [Player Response Option 3]

Consequence: [Story flag set, reputation change, etc.]
```

**Dialogue System Complexity:**

**MVP:**
- Linear dialogue (no branching)
- Simple player responses (flavor only)
- 5-10 lines per crew member per story beat

**Full Release:**
- Branching dialogue trees
- Player responses affect loyalty and story
- 20-30+ lines per crew member
- Personality-based responses

## 6. Story Integration with Trading

### 6.1 Mission Trading Objectives

**Types of Trading Missions:**

1. **Cargo Delivery**
   - "Transport 50 units of Medical Supplies to Proxima"
   - Player must buy goods and deliver
   - Reward: Credits + story progression

2. **Trade Route Establishment**
   - "Establish profitable route between Sol and Alpha Centauri"
   - Must complete 5 trades on route
   - Reward: Permanent route bonus, story unlock

3. **Market Manipulation**
   - "Drive up price of Electronics in Vega system"
   - Buy large quantities to affect market
   - Reward: Faction reputation, credits

4. **Smuggling Run**
   - "Deliver illegal goods without getting caught"
   - High risk, high reward
   - May require specific crew member

5. **Economic Sabotage**
   - "Disrupt rival faction's trade"
   - Creative mission design
   - Moral choice implications

### 6.2 Story-Unlocked Content

**What Story Progression Unlocks:**
- New star systems (gated behind story missions)
- Special commodities (unlocked after research missions)
- Ship upgrades (gifted or unlocked after crew quests)
- Black markets (unlocked through smuggler crew)
- Faction-exclusive contracts
- Legendary ships (endgame rewards)

### 6.3 Narrative Rewards for Economic Success

**Trading Success Enables Story:**
- Need certain ship to access story area
- Need credits to bribe/buy information
- Need reputation to gain faction trust
- Need cargo space for critical delivery

**Story Rewards Economic Success:**
- Story missions pay well
- Unlock profitable systems
- Provide unique trade opportunities
- Crew bonuses improve profit margins

## 7. Character Relationships

### 7.1 Relationship System (Full Release)

**Relationship Levels:**
- **Stranger** (0-20): Just recruited, minimal dialogue
- **Acquaintance** (21-40): Basic trust, some personal info shared
- **Friend** (41-70): Trust established, personal quest unlocked
- **Close Friend** (71-90): Deep trust, loyalty bonuses
- **Loyal** (91-100): Maximum trust, special dialogue, best bonuses

**Romance (Optional Post-MVP Feature):**
- Select crew members have romance options
- Requires high relationship level (75+)
- Additional personal quest chain
- Unique ending variations
- Purely optional, doesn't affect gameplay balance

### 7.2 Crew Interactions

**Crew-to-Crew Relationships:**
- Certain crew like/dislike each other
- Affects ship morale
- Creates dynamic dialogue
- Example: Engineer and Scientist debate technology, improves both bonuses

**Crew Conflicts:**
- Rare events where crew disagree
- Player must mediate
- Choices affect loyalties
- Adds drama and character depth

## 8. Campaign Pacing and Structure

### 8.1 Story-to-Trading Ratio

**Target Balance:**
- 60% Trading/Economic gameplay
- 30% Story missions and character interactions
- 10% Exploration and optional content

**Player Control:**
- Can always choose to trade instead of story missions
- Story missions available but not forced
- Can progress at own pace (with gentle nudges)

### 8.2 Story Gates

**Soft Gates (Recommended):**
- Story suggests you need better ship/credits
- Can attempt anyway (harder but possible)
- Natural pacing without hard blocks

**Hard Gates (Minimal Use):**
- Certain systems locked until story point
- Justified narratively (blockade, restricted access)
- Used sparingly (3-5 times across campaign)

### 8.3 Difficulty Scaling

**Story Mission Difficulty:**
- Early: Simple delivery, low risk
- Mid: Complex objectives, moderate risk
- Late: Multi-step missions, high risk

**Economic Scaling:**
- Story missions pay better than equivalent trading
- Balances time spent on narrative
- Keeps player economically viable

## 9. MVP vs Full Release

### 9.1 MVP Scope

**Story:**
- Linear 5-8 hour campaign
- 3-5 recruitable crew members
- 15-20 story missions
- Single ending

**Systems:**
- Basic captain skills (2 skill trees, 5 levels each)
- Simple crew bonuses (flat percentages)
- Linear dialogue (no branching)
- Basic loyalty system

### 9.2 Full Release Scope

**Story:**
- Branching 15-20 hour campaign
- 10-15 unique crew members
- 40-60 story missions
- 4-6 different endings
- Rich side content

**Systems:**
- Full skill trees (3 trees, deeper choices)
- Advanced crew progression and abilities
- Branching dialogue with consequences
- Relationship system with depth
- Crew personal quests (2-3 per crew)
- Romance options (optional)

## 10. Technical Requirements

### 10.1 Data Structures

**Campaign Progress:**
```python
CampaignState {
    current_act: int (1, 2, or 3)
    story_flags: dict[string, bool]
    completed_missions: list[string]
    available_missions: list[string]
    active_mission: string (current mission ID)
    ending_path: string (which ending player is on)
}
```

**Crew Data:**
```python
CrewMember {
    id: string
    name: string
    role: CrewRole
    level: int
    experience: int
    loyalty: int
    personal_quest_stage: int
    recruited: bool
    assigned_to_ship: bool
}
```

**Dialogue System:**
```python
DialogueNode {
    id: string
    speaker: string
    text: string
    responses: list[DialogueResponse]
    conditions: dict (check story flags)
    consequences: dict (set flags, change loyalty)
}
```

### 10.2 Save Data Integration

**Save File Must Include:**
- Campaign progress and story flags
- All crew members (recruited and available)
- Crew levels, loyalty, quest progress
- Captain skills and experience
- Active mission state
- Relationship levels
- Story choices made

## 11. Open Questions

- What is the central narrative mystery/conflict?
- Should crew permadeath exist or just temporary unavailability?
- How deep should romance system go (if included)?
- Should there be crew-based combat mechanics?
- How many total endings are feasible?
- Should there be voice acting or text-only?
- How much player customization for captain appearance?
- Should crew have randomized stats or fixed?

---

**Document Status**: Draft v1.0
**Last Updated**: 2025-10-18
**Dependencies**: Integrates with all existing systems
**Next Steps**: Define specific campaign story beats and crew character bios
