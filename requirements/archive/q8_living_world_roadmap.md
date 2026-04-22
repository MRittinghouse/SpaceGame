# Q8 Expanded: Living World Dialogue Overhaul (SP1-SP8) — Second Pass

## Context

Q1-Q7 made the quest pipeline mechanically reliable. Q8 transforms the world itself. Our research reveals a striking gap: the game has **rich mechanical systems** (social skills, disposition, faction reputation, crew loyalty, player titles, 9 skill trees with social branches) that are **almost entirely disconnected from dialogue**. Zero skill checks, zero disposition changes, zero crew loyalty effects in any of the 34 main dialogue trees. NPCs appear once and vanish. Peripheral stations have 1-2 NPCs. The cultural guide defines vivid faction voices that existing dialogue barely uses.

This roadmap addresses not just the technical gaps but the narrative craft: how to write dialogue that shows instead of tells, how to make mechanical systems feel like natural conversation, and how to make each station feel like a place people actually live.

## Critical Findings from Second Pass

### Mechanical Systems Built But Unused in Dialogue
- **Social tree skills**: Silver Tongue, Commanding Presence, Keen Insight (+1-2 to social skills), Master Negotiator (special dialogue options), Empathic Read (NPC disposition visible), Cultural Savant (+1 social in faction systems), Voice of the Expanse (peaceful encounter resolutions) -- ALL exist as progression data but NONE are checked in dialogue
- **Player identity**: Titles (Tycoon, Void Wolf, etc.) and playstyle (Trader, Fighter, etc.) are computed but NPCs never reference them
- **Faction reputation tiers**: Hostile/Unfriendly/Neutral/Friendly/Allied defined with ranges but dialogue doesn't scale
- **Synergy attribute**: Already wired to boost social checks via `get_synergy_social_bonus()` but underused because almost no checks exist

### Narrative Craft Gaps
- No station atmosphere documents (what does each station FEEL like?)
- No "civilian voice" guidance (how do ordinary dock workers talk?)
- No dialogue anti-patterns document (what to avoid)
- No subtext guidance for non-companion NPCs
- No pacing rules (when to be terse vs. when to breathe)
- No inter-faction dialogue clash examples

---

## Phase Overview

| Phase | Focus | Type | Key Innovation |
|-------|-------|------|----------------|
| SP1 | Writing Bible | Documentation | Craft foundation for all content |
| SP2 | NPC Multi-State System | Code | NPCs evolve with progression |
| SP3 | Skill Tree Integration | Code + data | Social skills matter in dialogue |
| SP4 | Mechanical Consequence Retrofit | Data | Existing dialogues gain depth |
| SP5 | Disposition UI | Code | Social system becomes visible |
| SP6 | New NPCs & Station Atmosphere | Content | World feels inhabited |
| SP7 | Station Chatter Expansion | Code + content | World reacts to player |
| SP8 | Faction Gates & Content Audit | Code + tests | Reputation drives content |

---

## SP1: The Writing Bible

**Goal**: A comprehensive reference document that any future dialogue author can follow to write content that feels authentic to the Aurelia Expanse.

**Deliverable**: `requirements/dialogue_writing_guide.md`

### Section 1: Narrative Philosophy

**Show, Don't Tell — The Core Principle**

Every line of dialogue should reveal character, culture, or world through natural speech rather than exposition.

BAD (telling): "The Commerce Guild is corrupt and exploits workers through unfair tariffs."
GOOD (showing): "Customs held my cargo for three days. Inspection fee doubled since last month. They called it a 'regulatory adjustment.' My family ate station rations while I waited."

BAD (telling): "This is a dangerous mining station."
GOOD (showing): "The air recycler's been whining since third shift. Maintenance says it's fine. Maintenance said that about the one on Level 8 too, before it killed two people."

BAD (telling): "I'm sad about my past."
GOOD (showing): "I keep a list. Every name, every date. I don't know why. Knowing doesn't change anything. But forgetting feels worse."

**The Subtext Principle**: What characters SAY and what they MEAN should often differ. Subtext creates depth:
- "That's an interesting choice." = "That's a bad choice and I'm being polite."
- "I filed a report." = "I did everything I could and it didn't matter."
- "Not bad." (from a Union worker) = Genuine high praise.
- "I need more data." (from a Collective scientist) = "I'm overwhelmed and using precision as armor."

**The Iceberg Principle**: Characters know more than they say. A dock worker doesn't explain the tariff system — they complain about how it affects their paycheck. A Guild auditor doesn't monologue about corruption — they note a discrepancy in a ledger and go quiet.

### Section 2: Faction Voice Rules

**Commerce Guild** — Conversation as negotiation:
- Full sentences, proper grammar. Titles and honorifics until invited otherwise.
- Frames everything transactionally: "I'm authorized to offer...", "Per the terms of..."
- Small talk has an agenda. A Guild NPC asking "How's business?" is probing for market intel.
- Avoids contractions in professional contexts. Uses them when genuinely relaxed (rare).
- Arabic/Dutch trade terms as flavor: "The sukuk is favorable" (bond), "Vrij haven" (free port).
- NEVER: slang, emotional outbursts, admitting ignorance without a plan to fix it.

**Miners' Union** — Actions speak louder:
- Short declarative sentences. First names immediately — titles are insulting.
- Dark humor about danger: "Could be worse. Usually is." "That drill's tired."
- Equipment has personality: "She's running hot", "Old Bessie's got another shift in her."
- Tests trust through tasks, not words. "Help me move these crates" = "I'm deciding if I like you."
- Welsh/Russian/Portuguese mining loanwords as flavor.
- NEVER: flowery language, unearned compliments, defending Union brass without caveats.

**Science Collective** — Precision as love language:
- Qualifiers on everything: "The data suggests...", "Statistically speaking..."
- Self-corrects in real time: "That was imprecise. Let me rephrase."
- Uncomfortable with emotions; translates them: "I feel... I believe the appropriate word is 'grateful.'"
- Full titles on first introduction. No contractions. No unqualified opinions.
- German/Sanskrit technical terms as flavor.
- NEVER: slang, dismissing lived experience, claiming certainty without evidence.

**Frontier Alliance** — Stories instead of answers:
- Answers questions with anecdotes and proverbs from blended Earth cultures.
- "Way I see it...", "My grandmother used to say...", "You haven't eaten."
- Judges by actions, not credentials. Food-sharing as social ritual.
- Comfortable with silence. Distrusts fancy words.
- Swahili/Filipino/Australian proverbs as flavor.
- NEVER: titles, formal address, trusting institutions over individuals.

### Section 3: Writing For Ordinary People

Most NPCs are not faction leaders, quest-givers, or plot devices. They're the people who keep stations running.

**Dock worker voice**: Talks about shifts, overtime, aching joints, the new foreman who doesn't know what they're doing. Complains about food in the commissary. Knows which airlocks stick.

**Clerk voice**: Talks about forms, backlogs, unreasonable deadlines. Has opinions about the regulation changes. Knows which office to avoid on Tuesdays.

**Farmer voice**: Talks about soil, weather patterns (artificial), crop yields, the new irrigation system that doesn't work properly. Shares food. Measures time in harvests.

**Mechanic voice**: Talks about parts availability, that one component nobody stocks anymore, the ship that came in last week with the worst hull patching they've ever seen.

These people don't care about the player's quest. They have their own problems. The player overhears their world, and THAT makes it feel real.

### Section 4: Pacing and Structure

**The 3-Node Minimum**: Even the shortest NPC interaction needs: greeting -> substance -> farewell. No single-node NPCs (they feel like signs, not people).

**The Optional Branch Rule**: Every tree with 5+ nodes should have at least one branch that's pure character/world-building — no quest progress, just a conversation that makes the NPC feel like a person.

**When to Be Terse**: Danger situations, combat briefings, emergency NPCs. Short sentences. No pleasantries. "Hull breach, Deck 3. Seal it or we lose atmosphere."

**When to Breathe**: Cantina conversations, post-mission debriefs, loyalty-unlocked dialogue. Let characters ramble. Let them pause. Let them change the subject and come back.

**Exit Opportunities**: Every 3-4 nodes, give the player a graceful exit ("[Leave]", "I should go", "Thanks for your time"). Trapped conversations feel hostile.

### Section 5: Dialogue Anti-Patterns

- **The Exposition Dump**: NPC explains the world to the player. Characters don't do this. They assume shared context.
- **The Narrated Emotion**: "she said angrily" in dialogue text. Use expression tags and let the words carry the emotion.
- **The Helpful Stranger**: NPCs who volunteer critical information without reason. People guard information; they share it when they trust you or want something.
- **The Monologue**: NPC talks for 4+ lines without player input. Break long speeches into nodes with reaction options.
- **The Binary Choice**: "Help me (good) / Go away (evil)". Real choices have costs on both sides.

### Section 6: Mechanical Integration Standards

- **Disposition changes**: Every tree 4+ nodes needs at least one. +3 to +5 for respectful/perceptive responses. -3 to -5 for dismissive/rude ones. Make them feel earned.
- **Skill checks**: Difficulty 1-2 early-game, 3-4 mid-game, 5 critical moments only. Failure paths must be meaningful (worse deal, lost info, lower disposition — never a dead end).
- **Faction rep**: Any faction-affiliated NPC should have at least one path that nudges faction rep (+1/-1). Small amounts signal that relationships are tracked.
- **Crew loyalty**: When a companion is present and the dialogue touches their values, include crew_loyalty_changes. Elena cares about precision, Marcus about worker safety, Priya about evidence, Tomas about freedom.
- **Expression minimum**: 3 distinct expressions per tree. Use the 20-set standard.

### Section 7: Connecting Skills to Narrative

Social tree skills should create moments that feel like CHARACTER skills, not player stats:

- **Observation check**: "You notice the tremor in her hands" — not "Your observation skill detected something." The player character sees something. The skill determines whether you get to.
- **Persuasion check**: The player's dialogue option should sound like persuasion — "What if we approached this differently?" — not "[Persuasion] Convince them."
- **Intimidation check**: Show physical presence or quiet authority — "I've seen what happens to people who lie to me" — not "[Intimidation] Threaten them."
- **Empathic Read** (skill tree): When active, disposition is visible. More importantly, internal monologue hints appear: "*She's measuring every word. Whatever she's hiding, it matters to her.*"
- **Master Negotiator** (skill tree): Unlocks dialogue options tagged with special_dialogue that offer creative solutions unavailable to other players.

---

## SP2: NPC Multi-State System

**Goal**: NPCs evolve across game progression instead of appearing once and vanishing.

### Technical Design

New optional `dialogue_states` array on NPC JSON:
```json
"dialogue_states": [
  {"state_id": "quest_active", "dialogue_id": "neve_in_progress",
   "required_flags": ["price_of_info_accepted"],
   "excluded_flags": ["price_of_info_complete"]},
  {"state_id": "post_quest", "dialogue_id": "neve_resolved",
   "required_flags": ["price_of_info_complete"]}
]
```

Resolution: iterate in order, return first match. No match -> base `dialogue_id`. Empty array -> legacy behavior.

### Code Changes
- `spacegame/models/dialogue.py`: Add `dialogue_states` field, `get_active_dialogue_id(flags)` method
- `spacegame/data_loader.py`: Parse `dialogue_states`
- `spacegame/views/cantina_view.py`: Resolve active dialogue_id from flags
- `spacegame/engine/game.py`: In `start_dialogue()`, use resolved dialogue_id

### Pilot NPCs
- **Neve Osei** (Nexus Prime): pre-quest / quest-active / post-quest
- **Petra Vance** (Forgeworks): pre-quest / quest-active / post-quest
- **Cassiel Maren** (Stellaris Port): pre-quest / appraisal-phase / confrontation-phase / post-quest

Each post-quest state should be a 3-4 node tree where the NPC reflects on what happened, reacts to the player's choices, and reveals something new about their life. These are not quest objectives — they're character moments.

### Tests
- Unit: state resolution with various flag combinations
- Data: every dialogue_states[].dialogue_id exists
- Integration: NPC shows different dialogue after quest completion

---

## SP3: Skill Tree & Mechanical Hook Integration

**Goal**: Wire the existing social skill tree into dialogue so player investment in social skills has tangible narrative payoff.

### Empathic Read Implementation
The skill "Empathic Read" (`npc_disposition_visible`) exists in the progression tree. Wire it:
- `spacegame/views/dialogue_view.py`: Check player's progression for `npc_disposition_visible` bonus. If active, show disposition bar (SP5 provides the UI). If not active, disposition is hidden.
- This means SP5's disposition UI is gated on a skill tree investment — making the skill feel rewarding.
- Additionally, when Empathic Read is active, show brief italic subtext in dialogue nodes that hint at NPC emotional state: "*She's choosing her words carefully.*" Implement via an optional `subtext` field on DialogueNode, only rendered when Empathic Read is active.

### Master Negotiator Implementation
The skill "Master Negotiator" (`special_dialogue`) unlocks unique dialogue options:
- When dialogue responses have `required_flags: ["has_special_dialogue"]`, they only appear if the player has invested in Master Negotiator.
- `spacegame/engine/game.py`: When starting dialogue, if player has `special_dialogue` bonus, set a temporary flag `has_special_dialogue` in the dialogue manager.
- Content: Add 1 Master Negotiator response to 5-6 key dialogues (Elena cantina, Hanna dock, Reva distress, embassy summit, Dex briefing, Cassiel confrontation). These should offer creative third options that aren't available otherwise.

### Cultural Savant Implementation
The skill "Cultural Savant" (`faction_social_bonus`) gives +1 to social checks in faction-aligned systems:
- This is already wired through `SocialManager.get_effective_level()` via `progression.get_bonus()`. Verify it actually affects check resolution by adding a test.
- Content impact: This makes mid-game skill checks at faction stations easier, rewarding social tree investment.

### Faction Reputation in Dialogue Start
`PoliticsManager.get_npc_disposition_modifier()` already applies faction-based disposition when dialogue starts. Verify this is working and add logging so we can see the effect.

### Files
- `spacegame/views/dialogue_view.py` (Empathic Read rendering, subtext)
- `spacegame/models/dialogue.py` (optional `subtext` field on DialogueNode)
- `spacegame/data_loader.py` (parse subtext)
- `spacegame/engine/game.py` (Master Negotiator flag injection)
- `data/dialogue/dialogues.json` (5-6 Master Negotiator responses, 3-4 subtext hints)

---

## SP4: Mechanical Consequence Retrofit

**Goal**: Add skill checks, disposition changes, and faction rep to ALL 34 existing main dialogues.

### Tier 1 — Key Story NPCs (skill checks + disposition)
- `elena_cantina`: Observation check (d1) — notice her folding habit. +5 disposition for sitting down, -3 for "Mind your own business."
- `marcus_recognition`: Persuasion check (d2) — get details about the buried report. +5 for silence (he respects it).
- `hanna_voss_dock`: Observation check (d2) — notice the prosthetic. +1 miners_union for asking about murals.
- `reva_distress`: Persuasion check (d3) — negotiate better escort terms. +2 commerce_guild for helping.
- `dex_cantina`: Intimidation check (d2) — push for more info. -2 disposition if you push too hard.
- `priya_stranded`: Observation check (d1) — notice the sample degradation urgency. +3 disposition for asking about her research.

### Tier 2 — Side Quest NPCs (disposition changes)
Every side quest NPC dialogue: minimum one positive (+3) and one negative (-3) disposition response.

### Tier 3 — Progression NPCs (faction rep + crew loyalty)
Embassy summit, Dex briefings, campaign NPCs: every major decision has a faction consequence (+1/-1 minimum). When companion is present, dialogue choices that align/conflict with their values adjust crew loyalty.

### Expression Enrichment
Expand all trees from 11-set to 20-set: add determined, frustrated, grateful, vulnerable, cautious, thoughtful, bitter, amused, relieved where emotionally appropriate.

---

## SP5: Disposition UI Visibility

**Goal**: Make the social system visible. Gated on Empathic Read skill from SP3.

### Disposition Bar
Five tiers rendered next to NPC portrait:
- 0-20: "Wary" (cool blue)
- 21-40: "Neutral" (gray)
- 41-60: "Friendly" (warm yellow)
- 61-80: "Trusted" (green)
- 81-100: "Close Ally" (gold)

Only visible when player has Empathic Read skill. Without it, the bar is hidden — player must invest in the social tree to see relationship status.

### Change Feedback
Floating "+5 Trust" / "-3 Trust" on disposition changes (always visible, even without Empathic Read — the player should always know their choice had an effect, even if they can't see the number).

### Skill Check Tooltip
On hover, show: "Observation 3 vs Difficulty 2" with green/yellow/red color coding. This makes the system legible.

### Files
- `spacegame/views/dialogue_view.py`
- `spacegame/config.py` (tier constants)

---

## SP6: New NPCs & Station Atmosphere

**Goal**: 8 new atmosphere NPCs making peripheral stations feel inhabited. Every NPC follows SP1 writing rules, uses multi-state from SP2, and has mechanical hooks from SP3/SP4.

### Iron Depths (1 NPC -> 3)

**Jez Okafor** — Shift Supervisor, Miners' Union
- Voice: Union direct. Mining jargon. Gallows humor. Measures time in shifts.
- 7 nodes. Observation check (d3) for hand tremor (vibration damage). Disposition-gated: at 60+ shares real accident numbers the Union suppresses.
- Multi-state: post-Sienna-Vek comments on the fallout.
- Shows instead of tells: "Third shift lost two drills this week. Management's response was a memo about 'operational awareness.' I wrote that memo. Made me sick."

**Naveen Prakash** — Guild Compliance Auditor
- Voice: Guild formal, but uncomfortable. Clearly hates his posting. Formal sentences with cracks.
- 7 nodes. Persuasion check (d2) to get him to admit the audit is a farce.
- Faction rep: sympathizing with Union gives -1 commerce_guild, +1 miners_union.
- Shows instead of tells: "The inspection forms have a field for 'worker satisfaction.' It's a dropdown. The options are 'Satisfactory,' 'Good,' and 'Excellent.' There's no field for 'We haven't replaced the air filters in four months.'"

### Haven's Rest (2 -> 4)

**Dimi Torr** — Fishmonger, Frontier Alliance
- Voice: Alliance proverbs and food metaphors. Knows everyone. Measures trust in meals shared.
- 5 nodes. Pure atmosphere NPC — no quest, no hide flag. Permanent fixture.
- Shows instead of tells: "My grandmother used to say, 'A hungry neighbor is a dangerous neighbor.' She wasn't talking about food."

**Issa Kadeer** — Refugee Coordinator, Unaligned
- Voice: Exhausted compassion. Bureaucratic precision born from caring too much, not too little.
- 6 nodes. Persuasion check (d2) for details about a specific refugee.
- Shows instead of tells: "Seventeen arrivals this week. The youngest is four. She doesn't speak yet — or she does, and nobody here speaks her language. I'm not sure which is worse."

### Stellaris Port (2 -> 4)

**Rudo Kamara** — Art Appraiser, Commerce Guild
- Voice: Assessments as speech. Evaluates everything, including people. Dry wit.
- 6 nodes. References Cassiel quest if complete (multi-state). Disposition-gated: at 70+ offers off-market appraisals.
- Shows instead of tells: "Interesting provenance. Questionable taste. But then, the market rarely rewards taste." *He pauses.* "I said that about the Maren collection too. Before the isotope results came back."

**Suki Tannenbaum** — Maintenance Chief, Unaligned
- Voice: Alliance-influenced despite working at Guild station. Sees the station from below.
- 5 nodes. Class contrast: promenade above vs. maintenance tunnels below.
- Shows instead of tells: "Upstairs they polish the chandeliers twice a week. Down here I've been requesting a new pressure valve for three months. Same station. Different gravity."

### Verdant (2 -> 4)

**Bren Solvay** — Grain Trader, Frontier Alliance
- Voice: Farming metaphors, shrewd negotiator dressed as friendly neighbor.
- 5 nodes. +1 frontier_alliance for siding against Guild pricing margins.
- Shows instead of tells: "The Guild takes fourteen percent on every shipment of grain that leaves Verdant. They call it 'logistics facilitation.' I call it 'the reason Haven's Rest pays twice what they should for bread.'"

**Chandra Osei** — Field Researcher, Science Collective
- Voice: Academic but relaxed (contrast with Priya). Curious about soil more than politics.
- 6 nodes. Multi-state: adds dialogue if Priya is recruited. Priya's cousin — family dynamics.
- Shows instead of tells: "Priya sends me papers. I send her soil samples. She turns them into equations. I turn her equations into better yields. It works. We just don't talk about the parts where the Collective patents my grandmother's farming techniques."

### Writing Checklist for All New NPCs
- [ ] Follows faction voice rules from SP1
- [ ] Minimum 5 nodes with optional-chat branch
- [ ] At least one disposition_change
- [ ] 3+ expressions from 20-set standard
- [ ] Uses multi-state for at least one transition
- [ ] Show-don't-tell in every substantive node
- [ ] Subtext layer: what they say vs. what they mean
- [ ] No exposition dumps, no binary choices, no monologues
- [ ] Names cross-checked against banned list

---

## SP7: Station Chatter Expansion

**Goal**: 60 new chatter lines + flag-gated progression. Stations react to the player's journey.

### Technical: Flag-Gated Chatter
Add `required_flags` and `excluded_flags` to ChatterLine dataclass. Update StationChatterManager.get_chatter() to accept and filter on player_flags.

### Progression-Gated Lines (15)
Lines that appear only after specific story events:
- Nexus Prime post-conspiracy: "Did you hear? Someone cracked a Guild cipher. The officers aren't denying it hard enough."
- Breakstone post-food-delivery: "That independent trader brought food through again. Starting to think they're not all profiteers."
- Iron Depths post-Sienna: "Three shift supervisors quit after Vek's warning. Management's furious. The rest of us are just... not surprised."
- Haven's Rest post-refugee-quest: "The coordinator looks exhausted. More arrivals every week. Someone should help."
- Stellaris Port post-Cassiel: "The Maren collection's been pulled from the exchange. Nobody's saying why."

### Ordinary Life Lines (45)
Faction-flavored everyday dialogue:

**Guild stations**: "Futures on purified crystal are up. Again. If you believed the fundamentals, you'd sell. Nobody believes the fundamentals." / "Director Huang's office issued three memos today. One contradicted the other two."

**Union stations**: "Second double shift this week. Bonus pay's nice. Knees aren't." / "The new drill bits are rated for 200 hours. They last 140. Ask me how I know."

**Collective stations**: "Peer review rejected my paper. The reviewer's critique was longer than the paper. I respect that, honestly." / "The cafeteria's serving 'nutritionally optimized protein.' That's a fancy way to say it tastes like nothing."

**Alliance stations**: "Harvest was good this season. The Guild wanted twenty percent more for transport. We said no. They said 'for now.'" / "My kid started school at the community center. Teacher asked what they want to be. Said 'not hungry.' We laughed. Then we didn't."

### Player-Echo Lines
Category `player_echo` with `action_type` triggers:
- After large trade: "Some trader moved serious cargo through here today. Prices shifted before they'd even undocked."
- After combat near system: "Security sensors picked up weapons fire in the approach corridor. Whoever it was, they handled it."
- After smuggling: "Customs flagged an irregular manifest today. Didn't find anything. Some people are just lucky."

### Files
- `spacegame/models/station_chatter.py` (flag fields)
- `spacegame/data_loader.py` (parse flags)
- `spacegame/views/station_hub_view.py` (pass player flags)
- `data/crew/station_chatter.json` (60 new lines)

---

## SP8: Faction Gates, Testing & Content Audit

### Faction-Gated Missions
Add optional `required_reputation` to Mission dataclass. Check in `update_availability()`. Show locked missions on station board with "Requires: Miners' Union -- Friendly" label.

Pilot: 3-5 existing side missions with low reputation thresholds (10-15, just above neutral).

### Comprehensive Testing
- Data validation: dialogue_states references, flag reachability, banned names, expression counts, disposition_change presence
- Integration: multi-state NPC walks, skill check resolution with tree bonuses, faction-gated mission lock/unlock
- Content audit: read all new dialogue aloud for voice consistency, cross-reference against character_voices.md

### Regression
- Existing 37 NPCs without dialogue_states work unchanged
- Existing 148 chatter lines without flags work unchanged
- Pre-SP2 saves load correctly

---

## Phase Dependencies

```
SP1 (writing bible) --+--> SP4 (retrofit dialogues)
                      +--> SP6 (new NPCs)
                      +--> SP7 (chatter expansion)

SP2 (multi-state) ----+--> SP4 (pilot NPCs use it)
                      +--> SP6 (new NPCs use it)

SP3 (skill hooks) ----+--> SP4 (checks in retrofitted dialogues)
                      +--> SP5 (Empathic Read gates disposition UI)

SP5 (disposition UI) -- after SP3

SP8 (gates + audit) -- after all others
```

**Execution order**: SP1 -> SP2 -> SP3 -> SP4 -> SP5 -> SP6 -> SP7 -> SP8

## Verification
After each phase: pytest (all pass), ruff (clean), manual playtest.
After SP8: full content audit per SP1 writing bible.
