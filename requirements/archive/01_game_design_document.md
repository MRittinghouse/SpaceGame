# Game Design Document (GDD)

> **Implementation Status** (Updated 2026-02-27)
>
> - **Primary trading loop**: FULLY IMPLEMENTED — survey, plan, travel, trade, upgrade cycle is complete
> - **Galaxy & economy**: COMPLETE — 10 systems, 19 commodities, dynamic pricing, market events
> - **Ship progression**: COMPLETE — 6 ship types, 5 upgrades, shipyard purchase/comparison
> - **Character progression**: COMPLETE — 10-level XP system, 2 skill trees (Trading + Gathering)
> - **Mining/Salvaging/Refining**: COMPLETE — all three mini-game systems operational
> - **Save/Load**: COMPLETE — 12 save slots with autosave
> - **Secondary RPG/narrative loop**: NOT STARTED — campaign, crew, factions, dialogue are Phase 2+
> - **Fleet management**: NOT STARTED — deferred to Campaign Act Two (Cycle 5.3.1)
> - **Spec note**: Some systems were simplified from this document's vision during implementation (2 skill trees instead of 3, 10 levels instead of 20). See `11_implementation_roadmap.md` for details.

## 1. Game Overview

### 1.1 Concept
A narrative-driven space trading RPG where players command a ship and crew through a galaxy-spanning campaign. Build your trading empire through economic strategy while developing your character, recruiting crew members, and unraveling a compelling story across the stars.

### 1.2 Genre
- Space Trading Simulation (Core)
- RPG with character progression and crew management
- Economic Strategy
- Narrative Adventure
- Exploration

### 1.3 Target Audience
- **Primary**: Players who enjoy economic simulation, story-driven games, and character progression
- **Age Range**: 13+
- **Experience Level**: Casual to intermediate gamers
- **Appeal**: Fans of games like Elite, Space Trader, FTL, Mass Effect (trading focus), Sid Meier's Pirates, Sunless Sea

### 1.4 Platform
- PC (Windows/Mac/Linux)
- Built with PyGame framework
- Single-player experience

## 2. Core Gameplay Loop

### 2.1 Primary Loop (Trading Cycle)
1. **Survey** - Check market prices and opportunities across accessible star systems
2. **Plan** - Decide on profitable trade routes considering cargo capacity, fuel, and risk
3. **Travel** - Navigate between star systems, managing fuel and potential encounters
4. **Trade** - Buy low, sell high to generate profit
5. **Upgrade** - Invest profits in ship improvements, cargo expansion, or new vessels
6. **Expand** - Access new regions of space as reputation and capabilities grow

### 2.2 Secondary Loop (RPG/Narrative Layer)
1. **Story Missions** - Accept and complete campaign quests that advance the narrative
2. **Character Development** - Improve captain skills (trading, navigation, leadership, negotiation)
3. **Crew Management** - Recruit, assign, and develop crew members with unique abilities
4. **Character Interactions** - Engage in dialogue with NPCs, crew, and faction leaders
5. **Decision Points** - Make narrative choices that affect story outcomes and relationships
6. **Unlock Content** - Story progression unlocks new systems, characters, and opportunities

### 2.3 Integrated Gameplay
The trading and RPG systems interweave:
- **Story missions** often require specific cargo deliveries or trade route establishment
- **Crew members** provide bonuses to trading, combat, or navigation
- **Character skills** improve trading efficiency, negotiation prices, or crew effectiveness
- **Narrative choices** impact faction relationships and available trade opportunities

### 2.4 Session Flow
- **Early Game** (0-2 hours): Learn trading basics, meet initial crew, begin campaign storyline
- **Mid Game** (2-10 hours): Optimize trade routes, recruit specialists, advance main story arc
- **Late Game** (10+ hours): Operate multiple ships, complete faction storylines, resolve main campaign
- **Post-Game** (10+ hours): Sandbox mode with all systems unlocked, optional side stories

## 3. Victory and Progression Conditions

### 3.1 Campaign Victory (Story-Driven)
- **Main Campaign Completion**: Resolve the central narrative arc (15-20 hours)
- **Multiple Endings**: Player choices lead to different story conclusions
- **Faction Endings**: Align with specific factions for unique conclusions
- **Campaign unlocks sandbox mode** with all systems and features available

### 3.2 Sandbox Goals (Player-Driven, Post-Campaign or Optional)
- **Wealth Accumulation**: Reach specific credit milestones (100K, 1M, 10M)
- **Fleet Building**: Own and operate multiple ships simultaneously
- **Reputation Mastery**: Achieve maximum reputation with all major factions
- **Explorer**: Visit all star systems in the galaxy
- **Trade Baron**: Monopolize specific commodity markets
- **All Crew Recruited**: Find and recruit all unique crew members

### 3.3 Progression Markers
**Economic:**
- Credits earned
- Trade routes established
- Ship upgrades acquired
- Fleet size

**Exploration:**
- Systems discovered
- Rare commodities unlocked

**Character/RPG:**
- Captain skill levels
- Crew members recruited
- Story chapters completed
- Faction reputation levels
- Relationships with key NPCs

### 3.4 Game End State
- **Campaign Completion**: Satisfying narrative conclusion with epilogue
- **Sandbox Mode**: Continue playing after campaign with all content unlocked
- **Multiple Playthroughs**: Different choices lead to different experiences
- **New Game+**: Start with campaign bonuses (upgraded ship, experienced crew, starting capital)

## 4. Player Experience Goals

### 4.1 Intended Feel
- **Strategic Depth**: Meaningful economic decisions with risk/reward tradeoffs
- **Exploration Satisfaction**: Joy of discovering new systems and opportunities
- **Progression Clarity**: Clear sense of advancement and growing power
- **Manageable Complexity**: Deep systems that don't overwhelm new players
- **Narrative Investment**: Compelling story that motivates continued play
- **Character Connection**: Attachment to your crew and their personal stories
- **Player Agency**: Choices matter in both story and gameplay

### 4.2 Key Emotions
- **Anticipation**: Planning the next big trade run or story mission
- **Satisfaction**: Successfully completing a profitable route or quest
- **Curiosity**: What's in the next star system? What's the next story beat?
- **Achievement**: Upgrading to a better ship or unlocking new regions
- **Connection**: Building relationships with crew members
- **Tension**: Making difficult narrative choices with consequences
- **Wonder**: Discovering story revelations and lore

### 4.3 Accessibility Features
- Pause anytime (turn-based or pausable real-time)
- Tutorial system for new players
- Difficulty scaling based on player performance
- Save/load system for session flexibility

## 5. Core Pillars

### 5.1 Space Trading Simulation (Foundation)
The heart of the game is a living economy where player actions and external events affect prices. Trading remains the primary activity and source of player agency.

### 5.2 Narrative-Driven Campaign (Story Layer)
A compelling story with memorable characters drives player motivation and provides context for trading activities. The narrative complements rather than overshadows the trading gameplay.

### 5.3 Character & Crew Progression (RPG Layer)
Develop your captain's skills and build a crew of specialists. Character progression enhances trading effectiveness and unlocks new gameplay opportunities.

### 5.4 Meaningful Choices
Every decision (what to buy, where to go, what to upgrade, which crew to recruit, story choices) should have strategic weight in both economic and narrative contexts.

### 5.5 Gradual Progression
Players should always have a clear next step and feel continuous advancement in both wealth/power and story progression.

### 5.6 Exploration Reward
Venturing into unknown space should offer both risk and potential reward, including story discoveries and economic opportunities.

## 6. Inspiration and References

### 6.1 Reference Games
**Trading/Economic:**
- **Elite/Elite Dangerous**: Space trading and exploration
- **Space Trader (Palm/Mobile)**: Accessible trading mechanics
- **EVE Online**: Economic depth and complexity
- **Patrician/Port Royale**: Historical trading simulation mechanics

**Narrative/RPG:**
- **FTL**: Event-based space travel with crew management
- **Mass Effect**: Character development and meaningful choices
- **Sunless Sea**: Narrative-driven exploration with crew
- **Star Traders: Frontiers**: Story-driven space trading RPG
- **Citizen Sleeper**: Character-driven space station narrative

**Crew Management:**
- **FTL**: Simple but effective crew system
- **Darkest Dungeon**: Crew stress and personality mechanics
- **XCOM**: Team building and specialist roles

### 6.2 Unique Differentiators
- **Trading-first RPG**: Story enhances trading, not replaces it
- **Streamlined for single-player**: Focused narrative experience
- **Crew as trading assets**: Characters provide mechanical benefits and story
- **Accessible learning curve** with hidden depth in both systems
- **PyGame-based** for modding potential
- **Choice-driven narrative** that respects player agency

## 7. Scope and Scale

### 7.1 Minimum Viable Product (MVP)
**Trading Systems:**
- 10-20 star systems
- 8-12 tradeable commodities
- 3-5 ship types
- Basic trading interface
- Simple travel mechanics

**RPG/Narrative Systems:**
- Main campaign (5-8 hours, linear structure)
- 3-5 recruitable crew members
- Basic captain skills (2-3 skill trees)
- Simple dialogue system
- Save/load functionality

### 7.2 Full Release Vision (v1.0)
**Trading Systems:**
- 30-50 star systems
- 15-20 commodities with complex supply chains
- 8-12 ship types with unique characteristics
- Advanced market simulation

**RPG/Narrative Systems:**
- Full campaign (15-20 hours with branching paths)
- 10-15 unique crew members with personal stories
- Comprehensive skill system for captain
- Faction reputation affecting story
- Multiple endings based on choices
- Rich dialogue with meaningful choices
- Character relationship system
- Crew member quests and development
- Random story events and encounters
- Multiple save slots

### 7.3 Post-Release Potential
- **Story DLC**: New campaign chapters, crew members, storylines
- **Modding support**: Custom campaigns, crew, ships
- **Expanded galaxies**: New sectors with unique stories
- **Deeper faction interactions**: Faction-specific story arcs
- **Romance options**: Deepen crew relationships
- **Procedural story events**: Infinite replayability

## 8. Design Constraints

### 8.1 Technical Constraints
- Must run smoothly on mid-range hardware (5+ year old PCs)
- PyGame framework limitations
- 2D graphics and interface
- File-based save system

### 8.2 Design Constraints
- Single-player focused (no multiplayer in v1.0)
- Limited scope for initial release
- Prioritize depth over breadth
- Must be learnable within 15-30 minutes
- **Story complements trading**: Narrative never forces player away from trading
- **Crew management stays simple**: Easy to understand, meaningful but not overwhelming
- **Balanced pacing**: Story missions integrate with trading gameplay

## 9. Success Metrics

### 9.1 Player Engagement
- Average session length: 45-90 minutes (story + trading)
- Return rate: 70%+ players returning for multiple sessions
- Campaign completion rate: 50%+ players finish main story
- Sandbox engagement: 40%+ continue playing post-campaign

### 9.2 Game Balance
**Economic Balance:**
- No single trade route dominates for entire game
- Progression feels steady (not too fast or slow)
- All ship types have viable use cases

**Narrative Balance:**
- Story missions feel rewarding (both narratively and economically)
- Crew members all have useful abilities
- Player choices have visible consequences
- Story pacing doesn't interrupt trading flow

### 9.3 Character/Crew Engagement
- Players recruit at least 50% of available crew members
- At least 3 different playstyles emerge from skill choices
- Crew members feel distinct and memorable

## 10. Campaign and Story Integration

### 10.1 Campaign Structure
**Three-Act Structure:**
- **Act 1**: Introduction to trading, meet core crew, establish central conflict
- **Act 2**: Build your operation, faction choices, crew development, rising tension
- **Act 3**: Major story decisions, climax, resolution with player-determined outcome

### 10.2 Story Mission Types
- **Main Story Missions**: Advance primary narrative (required for campaign progression)
- **Crew Missions**: Personal stories for recruited crew members (optional, unlock abilities)
- **Faction Missions**: Build reputation and influence story direction (semi-optional)
- **Side Stories**: Self-contained narratives for flavor and rewards (optional)

### 10.3 Integration Philosophy
**"Trading with Purpose":**
- Story missions often require trading objectives (deliver cargo, establish routes)
- Campaign unlocks new systems and trading opportunities
- Crew abilities enhance trading efficiency
- Narrative context makes trading feel meaningful

## 11. Open Questions

**These should be resolved in subsequent requirement documents:**

- What is the exact travel mechanics? (Turn-based? Real-time with pause?)
- How complex should the economic simulation be?
- Should there be combat? If so, how deep?
- What role do random events play?
- How does difficulty scaling work?
- What's the central narrative conflict/mystery?
- How many skill trees for the captain?
- What crew roles/positions exist on ships?
- How deep should character relationships go?
- Should crew members have permadeath or just temporary unavailability?

---

**Document Status**: Draft v2.0 - RPG/Narrative Integration
**Last Updated**: 2025-10-18
**Requires Review**: Yes - needs team/stakeholder input on open questions and RPG scope