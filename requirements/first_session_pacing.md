# First Session Pacing Analysis

> The first 30 minutes decide whether the player keeps playing or quits.
> This document maps the emotional arc, identifies pacing gaps, and defines
> where each tutorial should trigger for maximum impact.

---

## The Emotional Arc We Want

The player's first session should follow a clear emotional trajectory. Each phase builds on the last. Nothing is wasted.

| Minutes | Phase | Emotion | What Happens |
|---------|-------|---------|-------------|
| 0-2 | Identity | Quiet determination | Name your captain. Name your ship. Choose your strengths. |
| 2-6 | Rock Bottom | Scarcity, grit | Build your shuttle from scraps. Spend your last credits on parts. |
| 6-10 | The World Doesn't Care | Vulnerability | Nexus Prime. Officer Larsen demands 250 CR. Bureaucracy. |
| 10-15 | First Job | Purpose | Cargo broker has work. Iron ore to Forgeworks. First travel. |
| 15-20 | First Competence | Satisfaction | Elena teaches trading. First real profit. "I understand this." |
| 20-25 | The World Gets Bigger | Discovery | Breakstone. Different station, different people, different rules. |
| 25-30 | This Is Personal | Belonging, grief | Marcus recognizes your name. Your father worked here. He died here. |

---

## Current Flow (What Exists Today)

### Minute 0-1: Name Input
- Player enters name (default "Captain") and optional ship name
- Character creation: 5 attribute points across 5 stats
- **Observation**: This is fine. Quick, personal, not overwhelming.
- **Gap**: No narrative framing. The player doesn't know WHY they're here yet. The act_one_reference says they're a 16-year-old orphan. Nothing on screen communicates this.

### Minute 1-2: Game Initialization
- Player spawns at Nexus Prime with a pre-built shuttle and 4,000 CR
- **Gap**: The player never earned the shuttle. It's just given. The scrapyard tutorial (P1) will fix this by making the player BUILD it, creating ownership and the feeling of starting from nothing.

### Minute 2-4: Galaxy Map (Tutorial Overlay Fires)
- Tutorial step 1 fires: "Welcome to Aurelia! You are a trader in a galaxy of opportunity."
- **Problem**: This overlay pauses the game to deliver a text wall. The player hasn't done anything yet. They don't have context for what "buy low sell high" means because they haven't seen a market. The tutorial explains a system the player hasn't encountered. This is information without experience.
- **Problem**: The tone is generic. "You are a trader in a galaxy of opportunity" tells the player nothing about who they are or why they should care.

### Minute 4-6: Bill of Landing
- Auto-triggered dialogue with Officer Larsen at Nexus Prime
- Larsen demands registration. Player doesn't have a bill of landing. Larsen threatens to confiscate goods. Player pays 250 CR.
- **Observation**: This is actually good. Larsen's bureaucratic indifference establishes the world's tone. The 250 CR cost stings (especially after P1's budget-tight ship building). The player's first interaction with authority is: "pay up or get out."
- **Gap**: Larsen's weapon warning is good world-building but arrives at a moment when the player can't act on it. They don't have credits for a weapon yet. This is information delivered too early.

### Minute 6-8: Cargo Broker / Iron Delivery
- Cargo broker dialogue at Nexus Prime
- Player receives 10 iron ore to deliver to Forgeworks
- First use of galaxy map to select a destination
- **Observation**: The delivery mission is a good "training wheels" quest. Simple objective, clear reward.
- **Gap**: Tutorial step 2 (Trading Basics) fires when the player enters the trading screen. But the player isn't trading yet. They're delivering someone else's cargo. The trading tutorial arrives before the player has a reason to trade. Mismatch between tutorial and player intent.

### Minute 8-12: First Travel
- Player selects Forgeworks on galaxy map and travels
- Tutorial step 3 fires after first trade: "To travel, select a destination..."
- **Gap**: Tutorial step 3 fires AFTER the player already traveled. The tutorial explains what the player just did, which is useless because they already figured it out. Teaching after the fact doesn't help.
- **Observation**: The travel itself is good. The encounter system is forgiving (early-game protection skews encounters non-hostile). The arrival at Forgeworks feels like an achievement.

### Minute 12-15: Forgeworks Delivery + Return
- Deliver iron ore to Forgeworks clerk. 600 CR + 40 XP.
- Return to Nexus Prime.
- **Observation**: This is the first clear reward. The player earned credits by completing a task. Satisfying.
- **Gap**: Tutorial step 4 (Activities) fires on activity trigger. If the player visits Forgeworks's mining or salvage, they get a text dump about three systems they haven't tried. Too much at once.

### Minute 15-20: Footing the Bill (Elena)
- Elena approaches at Nexus Prime cantina
- Current: Elena delivers trading advice via dialogue. Tutorial step 1 already covered this as an overlay.
- **Gap**: Elena's advice and the tutorial overlay cover the same ground. Redundant. The player heard about trading from the overlay, then hears it again from Elena, but neither involved actually DOING a trade. P2 (Elena's Lesson) will replace both with guided doing.

### Minute 20-25: Union Territory
- Player buys 5 food, travels to Breakstone, delivers
- **Observation**: This is a real trade (buy food, deliver). The player practices what Elena taught. Good reinforcement.
- **Strength**: Arriving at Breakstone feels different. The station chatter is Union-voiced. The atmosphere text is about mining. The faction color is amber. The world visibly changes.
- **Gap**: No explicit acknowledgment that the player just did their first real trade. The game doesn't celebrate the milestone.

### Minute 25-30: The Foreman's Son (Marcus)
- Marcus Jin recognizes the player's name. Reveals the connection to their father.
- **Observation**: This is the emotional peak of the opening. The player transitions from "random trader" to "someone with a story." The father's death from failing air recyclers gives the game its moral core.
- **Gap**: Mining tutorial (hint overlay) may have already fired at Breakstone, interrupting the narrative flow. The mining tutorial should come AFTER Marcus's revelation, not before. The emotional context ("my father worked these mines") makes the mining tutorial personal.

---

## Information Pacing Problems

### The "Front-Loading" Issue
The current tutorial system delivers 5 overlays within the first 15 minutes:
1. Welcome (minute 2)
2. Trading Basics (minute 6)
3. Traveling (minute 10)
4. Activities (minute 12)
5. Your Journey (minute 14)

This is too much too fast. The player receives abstract information about systems they haven't used yet. By minute 15, they've been interrupted 5 times by text walls.

### The "Teaching Before Doing" Issue
Every current tutorial explains a system before the player encounters it naturally. Trading basics appear before the first trade. Travel explanation appears after the first travel. Activity overview appears before any activity is tried. The tutorials are disconnected from the player's actual experience.

### The Correct Approach: Breadcrumbs, Not Textbooks
Each system should be introduced at the EXACT moment the player first needs it, through a character who has a reason to teach them:

| System | Teacher | Moment | Why It Works |
|--------|---------|--------|-------------|
| Ship Building | Scrapyard mechanic | Before Nexus Prime | "You need a ship to go anywhere" |
| Trading | Elena Reeves | After first delivery | "Let me show you how to make real money" |
| Navigation | Natural discovery | First galaxy map use | Route preview (U4) shows distance/fuel |
| Mining | Marcus Jin | After father revelation | "Your father worked these shafts" |
| Combat | Crew member | First forced encounter | "Here they come. I'll talk you through it" |
| Salvage | NPC at first site | First salvage visit | "Debris from the raids. Here's how you scan" |
| Refining | NPC at first forge | First refine visit | "Raw ore's worth nothing. Let me show you" |

No system is taught before the player needs it. Every teacher has a narrative reason to help. Every lesson involves DOING, not reading.

---

## Where Each P1-P5 Tutorial Triggers

### P1 (Ship Builder): Between character creation and Nexus Prime
- **Emotional context**: The player has nothing. They're building something from nothing.
- **Pacing**: 3-4 minutes of guided assembly. Feels like an accomplishment.
- **Exit state**: Player has a shuttle they BUILT. Arrives at Nexus Prime with a ship they earned.

### P2 (Trading): During Footing the Bill (mission 3)
- **Emotional context**: Player just completed a delivery. They understand moving cargo. Elena shows them the PROFIT side.
- **Pacing**: 2-3 minutes of guided trading. One buy, one sell, one profit.
- **Exit state**: Player made money through their own decision. First taste of competence.
- **Replaces**: Tutorial overlays 1 and 2 (Welcome + Trading Basics)

### P3 (Mining): During The Foreman's Son (mission 5), AFTER Marcus dialogue
- **Emotional context**: Marcus just told the player about their father's death in these mines. The mining tutorial is now personal.
- **Pacing**: 2-3 minutes. Simplified field. Marcus guides.
- **Exit state**: Player extracted ore from the same shafts that killed their father. Emotional weight.
- **Replaces**: Tutorial overlay 4 (Activities) and mining hint

### P4 (Combat): First forced encounter in campaign
- **Emotional context**: The player is being attacked. Crew member helps. Survival instinct.
- **Pacing**: 3-4 rounds of guided combat. Contextual hints based on what actually happens.
- **Exit state**: Player survived their first fight. Confidence.
- **Replaces**: Combat hint overlays (momentum, elemental, etc. remain as supplementary for later encounters)

### P5 (Salvage/Refining): First visit to each activity
- **Emotional context**: Player is exploring, trying new things. Low stakes, high curiosity.
- **Pacing**: 1-2 minutes each. Brief NPC intro, guided session.
- **Exit state**: Player understands the activity and found something valuable.

---

## Overlay Tutorials: What To Keep

The 5-step overlay system should be reworked for "Classic" mode (P17), but the story tutorials replace them for the default experience. The MINIGAME_HINTS (20 contextual hints) remain useful as supplementary reminders on repeat visits.

**Keep as supplementary (shown on second+ visit):**
- Ship builder hints (module placement, hull painting, tools)
- Combat momentum/elemental hints
- Mining/salvage/refining detailed mechanics

**Remove or replace with story tutorials (first visit):**
- "Welcome to Aurelia" overlay → P1 scrapyard establishes the world
- "Trading Basics" overlay → P2 Elena's guided trade
- "Traveling the Galaxy" overlay → Galaxy map route preview (U4) makes this self-evident
- "Activities" overview → P3/P5 teach each activity individually
- "Your Journey Ahead" goal list → Remove entirely. Goals emerge through gameplay, not checklists.

---

## Dead Time Analysis

### Between Bill of Landing and Iron Delivery (~1 minute)
The player has a trade permit but no immediate instruction. They might wander the market without purpose.
**Fix**: The cargo broker auto-triggers immediately after Larsen's dialogue ends. Keep the gap minimal.

### Between Iron Delivery return and Elena (~1 minute)
Player returns to Nexus Prime after delivering iron. Elena doesn't auto-trigger immediately.
**Fix**: Elena's dialogue should auto-trigger on return to Nexus Prime after iron delivery completion. No gap.

### Between Elena's lesson and Union Territory (~2 minutes)
Player has credits from Elena's trade, a quest to buy food and go to Breakstone. This gap is GOOD. The player needs a moment to explore the market on their own, practice what Elena taught.
**Fix**: None. This is intentional breathing room. The player should feel autonomous here.

### Between Union Territory and Marcus (~1 minute)
Player arrives at Breakstone, delivers food, earns trust. Marcus is available.
**Fix**: Marcus's auto-trigger should fire on Breakstone arrival after Union Territory completion. Minimize dead time between the delivery satisfaction and the narrative revelation.

---

## Milestone Celebrations

The current game doesn't explicitly celebrate milestones. Adding brief, non-disruptive acknowledgments would reinforce the player's progress:

- **First ship built** (P1 completion): Brief text: "Your shuttle. Your beginning." Ship name displayed.
- **First trade permit** (Bill of Landing): Already handled by Larsen's dialogue. Good.
- **First profitable trade** (P2 completion): Elena: "Credits in your account. That's the Expanse for you." This line exists in the P2 design. Good.
- **First new system** (arrival at Forgeworks): Station chatter + faction flavor text already handles this. Good.
- **First ore extracted** (P3): Marcus: "That crystal? Rare. Worth five times the common stuff." Exists in P3 design. Good.
- **First combat survived** (P4): Crew member: "Well done. Combat gets harder in dangerous systems." Exists in P4 design. Good.

The celebrations are woven into the tutorial dialogue, not separate popups. The characters acknowledge your progress, not the UI.

---

## Summary: What Changes

1. **P1 inserted** between character creation and Nexus Prime (scrapyard ship building)
2. **Tutorial overlays 1-4 replaced** by story tutorials P2-P5
3. **Tutorial overlay 5 removed** (goal list is unnecessary when goals emerge through play)
4. **Mining tutorial** moved to AFTER Marcus dialogue (emotional context)
5. **Elena's dialogue** becomes the trading tutorial (doing, not telling)
6. **Dead time gaps minimized** with auto-trigger timing
7. **Milestones celebrated** through character dialogue, not UI popups
8. **MINIGAME_HINTS kept** as supplementary reminders for repeat visits
9. **Classic mode preserved** (P17) for players who skip story tutorials
