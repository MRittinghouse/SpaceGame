# Player Progression Requirements

> **Implementation Status** (Updated 2026-02-27): CORE COMPLETE, RPG EXTENSIONS PLANNED
>
> - **Wealth progression**: COMPLETE — credits, ship purchases, upgrade investment
> - **Asset progression**: COMPLETE — 6 ship types, 5 upgrades
> - **XP/Leveling**: COMPLETE — 10-level system with cumulative thresholds (simplified from the 20-level spec) — `models/progression.py`
> - **Skill trees**: COMPLETE — 2 trees (Trading Mastery + Resource Gathering) with 10 skills total (the 3rd tree, Leadership/Operations, deferred until crew system exists) — `data/progression/skill_trees.json`
> - **Discovery**: COMPLETE — systems_visited tracking
> - **Crew development**: NOT IMPLEMENTED — Phase 2+
> - **Faction reputation**: NOT IMPLEMENTED — Phase 2+
> - **Story/campaign progress**: NOT IMPLEMENTED — Phase 2+
> - **Achievements**: NOT IMPLEMENTED — Phase 1 (next)
> - **Spec note**: Level cap is 10 (not 20) and XP sources are simpler than this spec. Skill bonuses use flat values and percentage reductions rather than multipliers.

## 1. Overview

Player progression provides motivation, goals, and a sense of advancement. This document defines how players grow in power, unlock new capabilities, and measure their success.

## 2. Progression Dimensions

### 2.1 Core Progression Axes

Players progress along multiple independent but interconnected axes:

1. **Wealth** - Credits accumulated
2. **Assets** - Ships and upgrades owned
3. **Character Level & Skills** - Captain abilities and specialization
4. **Crew Development** - Recruiting and leveling crew members
5. **Reputation** - Standing with factions
6. **Discovery** - Systems explored and mapped
7. **Story Progress** - Campaign advancement and choices
8. **Achievements** - Meta-progression goals

### 2.2 RPG Integration

The progression system integrates trading/economic advancement with RPG character development:
- **Economic success** funds ship upgrades and enables story progression
- **Character skills** improve trading efficiency and unlock options
- **Crew members** provide bonuses and enable new gameplay strategies
- **Story progression** unlocks new systems, crew, and opportunities

## 3. Wealth Progression

### 3.1 Credit Milestones

**Early Game (0-2 hours)**
- Starting: 1,000-5,000 CR
- First Goal: 25,000 CR (first ship upgrade)
- Milestone: 50,000 CR (comfortable buffer)

**Mid Game (2-10 hours)**
- First Milestone: 100,000 CR (medium ship purchase)
- Second Milestone: 250,000 CR (ship + upgrades)
- Major Goal: 500,000 CR (heavy ship unlock)

**Late Game (10-20 hours)**
- Elite Trader: 1,000,000 CR
- Tycoon: 5,000,000 CR
- Trade Baron: 10,000,000+ CR

### 3.2 Income Scaling

**Expected earnings per hour:**
- Hour 1-2: 2,000-5,000 CR/hr
- Hour 3-5: 10,000-20,000 CR/hr
- Hour 6-10: 30,000-60,000 CR/hr
- Hour 11-15: 75,000-150,000 CR/hr
- Hour 16+: 200,000+ CR/hr

### 3.3 Wealth Sinks

To prevent infinite accumulation and maintain challenge:
- **Ship Purchases**: Major expenses (25K to 1M+ CR)
- **Ship Upgrades**: 10-100K CR per upgrade
- **Crew Recruitment**: 2,000-10,000 CR per crew member
- **Crew Equipment**: Optional gear for crew members (5,000-20,000 CR)
- **Docking Fees**: 100-1,000 CR per visit
- **Fuel Costs**: Ongoing operational expense
- **Repairs/Maintenance**: 1-5% of ship value periodically
- **Tariffs**: 0-5% of transaction value
- **Fines**: Penalty for illegal activities
- **Story Expenses**: Bribes, information purchases, mission costs

## 4. Asset Progression

### 4.1 Ship Ownership Ladder

1. **Starter** - Shuttle (free or 5K)
2. **Apprentice** - Light Freighter (25K)
3. **Trader** - Medium Freighter (100K)
4. **Specialist** - Courier/Hauler (150-500K)
5. **Magnate** - Heavy Ship or Fleet (500K-1M)
6. **Baron** - Multiple Ships (1M+)

### 4.2 Upgrade Tiers

**Basic Upgrades (10-50K CR)**
- Cargo expansion (+10%)
- Fuel tank upgrade
- Basic scanner

**Advanced Upgrades (50-150K CR)**
- Engine efficiency
- Advanced navigation computer
- Enhanced cargo (+20%)

**Elite Upgrades (150K+ CR)**
- Elite scanner (full system reveal)
- Fleet management AI
- Luxury cabin (special contracts)

### 4.3 Asset Milestones

- **First Upgrade**: Player customizes ship for first time
- **First New Ship**: Major upgrade from starter
- **First Specialized Ship**: Commit to a playstyle
- **First Fleet Ship**: Transition to multi-ship operations
- **Full Fleet**: Maximum ship ownership (5 ships)

## 5. Reputation System

### 5.1 Faction Reputation

Each faction has a reputation scale:
- **Range**: -100 (Hostile) to +100 (Revered)
- **Starting**: 0 (Neutral)
- **Impact**: Access, prices, opportunities

### 5.2 Reputation Levels

#### Negative Reputation
- **-100 to -51: Hostile** - Denied docking, attacked on sight
- **-50 to -26: Unfriendly** - High tariffs, limited access
- **-25 to -1: Suspicious** - Increased fees, cold reception

#### Neutral Reputation
- **0 to 24: Neutral** - Standard treatment

#### Positive Reputation
- **25 to 49: Friendly** - Small discounts, minor perks
- **50 to 74: Respected** - Better prices, access to restricted systems
- **75 to 99: Honored** - Significant bonuses, special missions
- **100: Revered** - Maximum benefits, exclusive content

### 5.3 Gaining Reputation

**Positive Actions:**
- Completing faction missions (+5 to +20)
- Trading in faction systems (+1 per trade)
- Delivering aid during crises (+10 to +30)
- Defending faction interests (+15 to +40)

**Negative Actions:**
- Trading with rival factions (-1 to -5)
- Smuggling illegal goods if caught (-20 to -50)
- Attacking faction ships (-30 to -100)
- Mission failures (-5 to -15)

### 5.4 Reputation Benefits

**Economic Benefits:**
- -1% tariff per 10 reputation points (max -10% at 100 rep)
- -5% docking fees at 50+ reputation
- Access to faction-exclusive goods at 75+ reputation

**Access Benefits:**
- Restricted systems unlock at 50+ reputation
- Special missions available at 60+ reputation
- Black market access at specific thresholds (faction-dependent)

**Gameplay Benefits:**
- Priority docking at busy stations
- Advanced warning of market events
- Protection from pirates in faction space (post-MVP)

### 5.5 Faction Relationships

**Major Factions (3-5 total):**
- **Trade Federation** - Merchant guild, economic focus
- **Colonial Union** - Settlers and frontier, agricultural
- **Industrial Consortium** - Manufacturing and mining
- **Independent Spacers** - Neutral, free traders
- **Research Collective** - Science and technology (optional)

**Faction Rivalries:**
- Gaining rep with one faction may reduce rep with rivals
- Example: Trade Federation vs. Independent Spacers (-0.5 ratio)
- Creates strategic choices in player alignment

## 6. Discovery and Exploration

### 6.1 Discovery Metrics

**Systems Discovered:**
- Total systems in galaxy: 10-100 (depending on scope)
- Track percentage explored
- Milestones at 25%, 50%, 75%, 100%

**Cartography Data:**
- First discovery bonuses (500-2,000 CR per system)
- Sell exploration data to factions
- Complete star charts unlock navigation bonuses

### 6.2 Exploration Progression

**Phase 1: Local Space (0-5 systems)**
- Learn mechanics in safe starter region
- Build initial capital

**Phase 2: Regional Expansion (5-15 systems)**
- Explore adjacent sectors
- Discover new trade opportunities

**Phase 3: Deep Space (15-30 systems)**
- High-risk, high-reward frontier systems
- Rare commodities and special locations

**Phase 4: Full Galaxy (30+ systems)**
- Complete exploration
- Unlock secret systems and endgame content

### 6.3 Exploration Rewards

- **Credits**: Discovery bonuses
- **Knowledge**: Market data, route optimization
- **Access**: Hidden systems, special stations
- **Achievements**: Explorer titles and badges

## 7. Captain Skills and Character Progression

### 7.1 Character Leveling System

**Experience Gain:**
- Complete trades: 10-20 XP each
- Complete story missions: 100-200 XP each
- Discover new systems: 50 XP each
- Complete crew quests: 150 XP each

**Level Progression:**
- Level 1-5: 500 XP per level (early game)
- Level 6-10: 1,000 XP per level (mid game)
- Level 11-15: 2,000 XP per level (late game)
- Level 16-20: 3,000 XP per level (endgame)

**Rewards per Level:**
- 1 Skill Point to spend on skill trees
- Small stat boost (optional: +1% trading efficiency, +5 max cargo, etc.)

### 7.2 Skill Trees (Core System)

**Three Primary Skill Trees:**

#### Trading Mastery
- Focus: Economic efficiency and profit maximization
- Levels 1-5: Each level improves trading bonuses
- Example skills: Negotiation, Bulk Buying, Market Analysis, Trade Connections, Trade Baron

#### Navigation & Exploration
- Focus: Travel efficiency and discovery rewards
- Levels 1-5: Each level improves travel/exploration
- Example skills: Efficient Routing, Quick Jump, Explorer's Eye, Star Cartographer, Master Navigator

#### Leadership & Crew
- Focus: Crew effectiveness and fleet operations
- Levels 1-5: Each level improves crew/leadership
- Example skills: Inspiring Captain, Crew Manager, Crisis Leadership, Reputation Builder, Fleet Admiral

**See Campaign/RPG/Crew document (Section 4.2) for detailed skill tree breakdown**

### 7.3 Skill Point Allocation

- **Total Skill Points**: 15-20 across full campaign
- **Cannot max all trees**: Forces meaningful choices
- **Respec Option**: Available at major stations for fee (10,000 CR)
- **Build Variety**: Different playstyles emerge from choices

### 7.4 Legacy Perk System (Optional/Post-MVP)

Achievement-based perks that complement skill trees:

### 7.2 Perk Categories

#### Trading Perks
- **Negotiator**: -2% on all purchases
- **Silver Tongue**: +2% on all sales
- **Market Analyst**: See price trends for longer history
- **Bulk Discount**: -5% when buying 100+ units

#### Navigation Perks
- **Fuel Efficiency**: -10% fuel consumption
- **Fast Travel**: -20% travel time (if real-time)
- **Navigator**: Improved autopilot routing
- **Explorer**: +50% discovery bonuses

#### Economic Perks
- **Investor**: Passive income from parked credits
- **Insurance Broker**: -50% repair costs
- **Tax Haven**: -2% tariffs universally
- **Black Market Contact**: Access to black markets

#### Fleet Perks
- **Fleet Commander**: Unlock fleet management
- **Automated Trading**: AI ships earn 50% normal profit
- **Logistics Master**: +10% cargo on all ships

### 7.3 Perk Unlock Conditions

Examples:
- **Negotiator**: Complete 100 trades
- **Explorer**: Discover 15 systems
- **Fleet Commander**: Own 3 ships simultaneously
- **Market Analyst**: Trade in 10 different systems
- **Fuel Efficiency**: Travel 100 jumps

### 7.4 Perk Selection

- Player earns perks by completing milestones
- Can have 3-5 active perks at once
- Swap perks at major stations (for a fee)
- Creates builds and playstyles

## 7.5 Crew Progression System

### Crew Recruitment Milestones
1. **First Crew** - Story-given First Officer (automatic)
2. **Small Crew** - Recruit 3 crew members
3. **Full Crew** - Fill all ship slots (varies by ship)
4. **Diverse Crew** - Recruit one of each role type
5. **All Crew** - Recruit all unique crew members (completionist goal)

### Crew Leveling
**Experience for Crew:**
- Crew members level up when assigned to ship during trades/missions
- XP per trade with crew aboard: 5-10 XP
- XP per mission with crew aboard: 50-100 XP
- Crew levels: 1-5 (maximum)

**Leveling Benefits:**
- Level 1: Base bonus (e.g., -10% fuel consumption)
- Level 2: Improved bonus (e.g., -12% fuel consumption)
- Level 3: Enhanced bonus (e.g., -15% fuel consumption)
- Level 4: Superior bonus (e.g., -18% fuel consumption)
- Level 5: Master bonus (e.g., -20% fuel consumption)

### Crew Loyalty Progression
- **0-39**: Low loyalty - Reduced effectiveness, may leave
- **40-74**: Medium loyalty - Normal effectiveness
- **75-100**: High loyalty - Maximum effectiveness, special dialogue

**Loyalty Gains:**
- Complete their personal quest: +10
- Take them on missions: +2 per mission
- Keep ship well-maintained: +1 periodically

**Loyalty Losses:**
- Ignore personal quest: -10
- Story choices they disagree with: -5
- Ship takes heavy damage: -3

### Crew Abilities and Bonuses
**Each crew member provides:**
- **Primary Bonus**: Based on role (pilot, engineer, merchant, etc.)
- **Secondary Ability**: Unlocked at level 3
- **Master Ability**: Unlocked at level 5 or quest completion

**Example - Elena Reeves (Engineer):**
- Level 1: -10% repair costs
- Level 3: +5% fuel efficiency (secondary ability)
- Level 5 + Quest: Emergency Repairs (can repair 50% damage mid-flight, once per day)

## 8. Story Progress Tracking

### 8.1 Campaign Progression Markers

**Act I Progress:**
- Story missions completed: 0/8
- Core crew recruited: 0/2
- Systems unlocked: 0/5

**Act II Progress:**
- Story missions completed: 0/12
- Optional crew recruited: 0/6
- Faction choice made: Yes/No
- Crew personal quests completed: 0/15

**Act III Progress:**
- Story missions completed: 0/8
- Ending path chosen: [Faction/Independent/etc.]
- Final confrontation: Pending/Complete

### 8.2 Story Milestones

- **"Campaign Started"**: Begin main story
- **"Act I Complete"**: Finish first story arc
- **"Crew Member Recruited"**: First optional crew join
- **"Personal Connection"**: Complete first crew quest
- **"Faction Aligned"**: Choose faction path
- **"Act II Complete"**: Finish second arc
- **"Point of No Return"**: Enter final act
- **"Campaign Complete"**: Finish main story
- **"Sandbox Unlocked"**: Post-campaign mode available

## 9. Achievements and Meta-Progression

### 9.1 Achievement Categories

#### Wealth Achievements
- "First Fortune" - Earn 100K CR
- "Millionaire" - Earn 1M CR
- "Trade Baron" - Earn 10M CR

#### Trading Achievements
- "Merchant" - Complete 50 trades
- "Master Trader" - Complete 500 trades
- "Deal Maker" - Earn 100K profit in single trade

#### Exploration Achievements
- "Star Gazer" - Discover 5 systems
- "Voyager" - Discover 25 systems
- "Galactic Explorer" - Discover all systems

#### Ship Achievements
- "Ship Owner" - Purchase first ship
- "Fleet Admiral" - Own 5 ships simultaneously
- "Fully Loaded" - Max out all upgrades on one ship

#### Faction Achievements
- "Diplomat" - Reach 50 rep with any faction
- "Allied" - Reach 75 rep with any faction
- "Hero" - Reach 100 rep with any faction
- "Universalist" - Reach 50 rep with all factions

#### Story/Campaign Achievements
- "Campaign Complete" - Finish main story
- "Hero's Journey" - Complete all three acts
- "Every Path" - See all endings (multiple playthroughs)
- "Completionist" - Complete all story missions and side quests

#### Crew Achievements
- "First Mate" - Recruit your first crew member
- "Full House" - Fill all crew slots on ship
- "Crew Bonds" - Complete 5 crew personal quests
- "Master & Commander" - Complete all crew quests
- "Loyal Following" - Get all crew to 75+ loyalty
- "Diverse Crew" - Recruit one of each crew role type
- "Collector" - Recruit all unique crew members

#### Character Development Achievements
- "Skilled Captain" - Reach level 10
- "Master Trader" - Max out Trading skill tree
- "Explorer Elite" - Max out Navigation skill tree
- "Leader of Leaders" - Max out Leadership skill tree
- "Renaissance Captain" - Spend at least 3 points in each skill tree

#### Special Achievements
- "Speedrunner" - Earn 1M CR in under 10 hours
- "Risk Taker" - Trade in all dangerous systems
- "Smuggler" - Successfully smuggle 100 illegal goods
- "Philanthropist" - Donate 100K CR to aid missions

### 9.2 Achievement Rewards

- **Cosmetic**: Badges, titles, ship skins (optional)
- **Mechanical**: Unlock perks or bonuses
- **Meta**: Leaderboards, New Game+ bonuses
- **Satisfaction**: Bragging rights, completion percentage

### 9.3 Statistics Tracking

Track player statistics:

**Economic Stats:**
- Total credits earned (lifetime)
- Trades completed
- Total profit from trades
- Largest single profit
- Ships owned (current and lifetime)

**Exploration Stats:**
- Total jumps traveled
- Systems discovered
- Total distance traveled

**Character Stats:**
- Current level and XP
- Skill points spent per tree
- Total missions completed
- Story progress percentage

**Crew Stats:**
- Crew members recruited (current/total available)
- Crew quests completed
- Average crew loyalty
- Highest crew level

**Faction Stats:**
- Reputation levels with each faction
- Faction missions completed

**Meta Stats:**
- Achievements unlocked
- Playtime
- Campaign completion percentage

## 10. New Game+ and Replayability

### 10.1 New Game+ Features (Post-MVP)

After completing the campaign, offer:
- **Starting Bonus**: Begin with 50K-100K CR
- **Ship Unlock**: Start with medium ship instead of shuttle
- **Skill Points**: Start with 3 skill points to spend immediately
- **Crew Bonus**: One crew member of player's choice starts recruited
- **Knowledge Retention**: Some systems pre-discovered (story areas still gated)
- **Harder Mode**: Optional increased difficulty (higher prices, lower profits, more events)
- **Story Choices**: Make different decisions for new endings

### 10.2 Replayability Elements

- **Branching Story**: Different choices lead to different outcomes
- **Multiple Endings**: 4-6 different endings to discover
- **Different Factions**: Align with different factions each playthrough
- **Different Crew**: Recruit different crew combinations
- **Skill Builds**: Try different captain skill specializations
- **Ship Specialization**: Focus on different ship types
- **Challenge Runs**: Self-imposed constraints (e.g., no upgrades, single ship only)
- **Procedural Galaxy** (post-MVP): Different layout each playthrough

## 11. Progression Pacing

### 11.1 Early Game (0-2 hours)

**Economic Goals:**
- Learn trading mechanics
- Earn first 25K CR
- Purchase first upgrade or better ship
- Discover 3-5 systems

**RPG Goals:**
- Meet first crew member (First Officer)
- Complete Campaign Act I introduction
- Reach character level 3-5
- Spend first skill points

**Feeling:**
- Rapid learning curve
- Frequent small victories
- Clear next steps
- Story hooks player interest

### 11.2 Mid Game (2-10 hours)

**Economic Goals:**
- Build stable trade routes
- Acquire specialized ship
- Reach 50+ rep with a faction
- Discover 10-20 systems
- Earn first 100K-500K CR

**RPG Goals:**
- Recruit 3-6 crew members
- Complete Campaign Acts I & II
- Reach character level 8-12
- Complete 2-3 crew personal quests
- Make major faction choice
- Develop skill specialization

**Feeling:**
- Strategic optimization
- Meaningful choices
- Growing power
- Story momentum builds
- Attachment to crew forming

### 11.3 Late Game (10-20 hours)

**Economic Goals:**
- Fleet management (if pursuing)
- Maximize profits
- Complete exploration
- Achieve 75+ rep with multiple factions
- Acquire endgame ships
- Earn 1M+ CR

**RPG Goals:**
- Complete Campaign Act III
- Recruit all desired crew members (8-12 total)
- Reach character level 15-20
- Complete majority of crew quests
- Make final story choices
- Max loyalty with key crew
- Reach ending and resolution

**Feeling:**
- Mastery and dominance
- Complex optimization
- Emotional investment in story conclusion
- Satisfaction of character arcs completing
- Completionist goals

### 11.4 Post-Game (20+ hours, optional)

**Sandbox Mode:**
- Continue after campaign
- All systems unlocked
- Focus on economic goals
- Complete remaining side content
- Try different playstyles
- Achieve 100% completion

## 12. Progression Feedback

### 12.1 UI Indicators

- **Progress Bars**: Visual rep for reputation, exploration, XP to next level
- **Level-Up Notifications**: Clear notification when captain levels up
- **Crew Status**: Show crew levels and loyalty at a glance
- **Milestone Notifications**: Pop-up when reaching goals
- **Statistics Screen**: Detailed breakdown of all progression
- **Next Goal Suggestions**: Hint at upcoming milestones (story and economic)
- **Campaign Progress**: Show current Act and % completion

### 12.2 Reward Moments

- **Captain Level-Up**: Flash + skill point to spend
- **Crew Level-Up**: Notification showing improved bonus
- **Crew Recruited**: Introduction dialogue and profile reveal
- **Crew Quest Complete**: Unlock upgraded ability, loyalty boost
- **Story Milestone**: Cinematics or special dialogue
- **Ship Upgrade**: Visual/functional improvement
- **Reputation Threshold**: Cross into new tier
- **Achievement Unlock**: Flash notification + reward
- **Discovery**: First visit to new system
- **Campaign Act Complete**: Satisfying act conclusion + rewards

## 13. Balance Considerations

### 13.1 Avoid Grind

- Progression should feel steady, not repetitive
- Multiple paths to same goal (trade OR story missions for XP)
- Diminishing returns on repetitive actions
- Story missions provide significant XP to avoid pure grinding
- Crew leveling happens naturally through gameplay

### 13.2 Meaningful Choices

- No single "optimal" path (skill tree choices, crew choices, story choices)
- Different playstyles should be viable
- Different crew combinations offer different advantages
- Trade-offs between short-term and long-term goals
- Story choices have real consequences

### 13.3 Smooth Difficulty Curve

- Early game forgiving, teaches mechanics
- Mid game offers strategic depth
- Late game provides mastery and optimization challenges

## 14. Technical Requirements

### 14.1 Progression Data Storage

```
PlayerProgress {
    // Economic Progression
    credits_current: int
    credits_lifetime: int
    ships_owned: list[PlayerShip]

    // Character Progression
    captain_level: int
    captain_experience: int
    skill_points_available: int
    skills_purchased: dict[string, int]  // skill_id -> level

    // Crew Progression
    crew_roster: list[CrewMember]
    crew_active: list[string]  // crew IDs on current ship

    // Story Progression
    campaign_act: int
    story_flags: dict[string, bool]
    completed_missions: list[string]
    active_mission: string

    // World Progression
    systems_discovered: list[string]
    faction_reputation: dict[string, int]

    // Legacy Systems
    perks_unlocked: list[string]
    perks_active: list[string]
    achievements: list[string]

    // Statistics
    statistics: {
        trades_completed: int
        jumps_traveled: int
        total_profit: int
        largest_single_profit: int
        missions_completed: int
        crew_quests_completed: int
        systems_discovered_count: int
        ...
    }
}
```

### 14.2 Save Compatibility

- Progression data persists across sessions
- Forward-compatible with future updates
- Export/import for backup (optional)
- Campaign state fully saved (story flags, choices made)
- Crew state fully saved (levels, loyalty, quest progress)

## 15. Open Questions

- How punishing should reputation loss be?
- Should perks be permanent or swappable? (Currently: swappable at stations)
- What happens at max reputation (prestige system)?
- Should there be seasonal events or time-limited goals?
- Leaderboards or competitive elements?
- Should crew have permadeath or just temporary unavailability?
- How deep should romance/relationship mechanics go?
- Should there be voice acting for story content?

---

**Document Status**: Draft v2.0 - RPG/Campaign Integration
**Last Updated**: 2025-10-18
**Dependencies**: All systems (ships, economy, galaxy, factions, campaign, crew)
