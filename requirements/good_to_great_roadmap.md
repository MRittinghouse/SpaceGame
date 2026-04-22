# Good to Great: Comprehensive Polish Roadmap

## Context

The game has reliable quest systems (Q1-Q8), a living world (SP1-SP8), and a polished UI (U1-U7). Now we make the experience feel effortless, atmospheric, and addictive. No campaign expansion (Act Two is out of scope). This is purely about making the existing game the best version of itself.

Seven categories, 18 phases, organized into 9 implementation sprints.

## Categories

| Category | Phases | Goal |
|----------|--------|------|
| First Impression | P0 | The opening session hooks or loses the player |
| Tutorial & Onboarding | P1-P5 | Teach through story, not tooltips |
| Quality of Life | P6-P8 | Remove every friction point |
| Sound & Atmosphere | P9-P10 | Audio creates emotion |
| Economy & Balance | P11-P12 | Core loop feels satisfying and addictive |
| Accessibility | P13-P15 | Everyone can play |
| Narrative Staging | P16-P17 | Key moments land harder |

---

## P0: First Session Pacing Audit

**Goal**: Before implementing any individual tutorial, map the emotional arc of the first 30 minutes and identify where engagement drops.

**Why this comes first**: The tutorials (P1-P5) teach mechanics. But mechanics taught at the wrong moment, in the wrong order, or without emotional context won't stick. The player's first session should follow: isolation ("you're alone with nothing") -> first competence ("I made a trade and it worked") -> first connection ("Elena helped me, Marcus recognized my name").

**Design**:
- Play through the complete new-game experience from name input to completing Union Territory (missions 1-4)
- Document minute-by-minute: what is the player doing? What are they feeling? Where do they wait? Where are they confused? Where are they bored?
- Map where each tutorial (P1-P5) should trigger in this flow for maximum impact
- Identify any dead time between missions where the player has no clear goal
- Verify the emotional beats land: Does Officer Larsen's 250 CR demand feel like a gut punch? Does Elena's help feel like warmth? Does arriving at Breakstone feel like entering a new world?
- Output: a first-session timeline document that guides P1-P5 implementation

**This is an analysis phase, not an engineering phase.** The output is a document, not code. But it shapes everything that follows.

---

## P1: Story-Tied Ship Builder Tutorial ("First Ship")

**Narrative**: After character creation, the player starts in a scrapyard drydock instead of spawning with a pre-built shuttle. A mechanic NPC guides them through purchasing parts and assembling their ship. "You scraped together enough credits for a hull frame. Now you need parts."

**Design — Two phases: Shop then Build**:

**Phase A: Parts Shop**
- New `GameState.TUTORIAL_SHOP` — a simplified shop interface showing only the 4 parts the player needs: cockpit module, engine module, reactor module, cargo bay module
- Each part has a price. The player starts with exactly enough credits to buy all four (tight budget, no waste)
- A mechanic NPC narrates in a docked panel: "You'll need a cockpit first. Without it, you're just sitting in a frame." -> "Good. Engine next. Nothing moves without thrust." -> "Reactor powers everything. Don't skip this one." -> "Cargo bay. You're a trader, not a tourist."
- Each purchase is a real buy action using the existing transaction system
- The budget constraint is the narrative tension: if you buy all four, you have almost nothing left. That's the feeling of starting from zero.

**Phase B: Assembly**
- New `GameState.TUTORIAL_BUILDER` — specialized builder view wrapping `ShipBuilderView`
- The parts purchased in Phase A are the only items in the catalog
- Step-by-step guidance: "Place your cockpit" -> "Now your engine toward the stern" -> "Reactor goes in the core" -> "Cargo bay wherever you have room"
- Each step validates the player placed the correct slot type before advancing
- Narration appears in a docked panel (not overlay), styled like dialogue
- On completion, ship is confirmed and game transitions to Nexus Prime

**Files**: config.py (2 new GameStates), game.py (new-game flow), new tutorial_shop_view.py, new tutorial_builder_view.py, ship_builder_view.py (reuse), data/tutorial/builder_parts.json

---

## P2: Story-Tied Trading Tutorial ("Elena's Lesson")

**Narrative**: Elena Reeves (mission `footing_the_bill`) teaches trading through doing. She walks you through your first real trade, explaining not just "buy low sell high" but WHY prices differ.

**Design**:
- After Elena's dialogue sets a flag, the trading view enters guided mode:
  - Pulsing highlight on target commodity row
  - Docked instruction panel: "See textiles? They're cheap here because Nexus Prime produces them. Forgeworks doesn't. Buy 5."
  - Player performs the real buy action
  - Elena: "Good. Now look at the trend column. See 'BUY HERE'? That means this system produces this commodity at lower prices."
  - On arrival at Forgeworks: "Open the market. See the price difference? That's your profit margin."
  - Player performs the sell. Elena: "Credits in your account. That's the Expanse for you. Move things where they're needed."
- Teaches: buy/sell, price differences between systems, specialty indicators, profit
- Removes/replaces the old tutorial overlay step for trading
- Driven by dialogue flags (existing mechanism)

**Files**: tutorial_manager.py, trading_view.py, missions.json (footing_the_bill tweak), dialogues.json

---

## P3: Story-Tied Mining Tutorial ("Marcus's Lesson")

**Narrative**: Mission `the_foremans_son` at Breakstone. Marcus Jin walks you through your first mining session after the narrative dialogue about your father.

**Design**:
- Mining view enters `tutorial_mode` with:
  - Simplified field (3-4 rocks including one guaranteed rare ore drop)
  - Step narration from Marcus: "See the hardness bar? Darker means tougher. Start with the light ones." -> "Try a right-click. Empowered strike. Uses energy but hits harder." -> "That crystal? Rare. Worth five times the common stuff."
  - Validates each action before advancing
  - Guaranteed rare drop so the player immediately sees the value proposition
- Driven by mission state flag

**Files**: mining_view.py, game.py (view factory), missions.json

---

## P4: Story-Tied Combat Tutorial ("First Contact")

**Narrative**: First forced encounter in the mission chain. A crew member provides turn-by-turn guidance during the fight, contextual to what actually happens in the combat.

**Design**:
- `CombatTutorialHelper` observes `CombatEngine` state after each round and emits contextual guidance:
  - Round 1: "Select a weapon from the action panel. Click to queue it, then hit Execute."
  - If shields hit: "Your shields absorbed that. Use a defense action to restore them."
  - If hull damaged: "Hull damage. That's permanent until you repair. Watch your health bar."
  - If momentum reaches 25%: "Momentum building. At 25%, your crew can use special abilities."
  - On victory: "Well done. Combat gets harder in dangerous systems."
- Hints are **contextual** to actual combat events, not scripted. If shields weren't hit, the shield hint never fires.
- Rendered in a non-blocking panel alongside the combat log
- Triggered by a mission flag, cleared after first victory
- Weakened enemy (low hull, limited weapons) so the player can learn without dying

**Files**: combat_view.py, new combat_tutorial_helper.py, missions.json

---

## P5: Salvage & Refining Tutorials

**Narrative**: On first visit to salvage/refining locations, brief NPC intro sets the scene, then guided session.

**Design**: Same pattern as P3. Add `tutorial_mode` to SalvageView and RefiningView. 2-3 guided steps each. Driven by dialogue flags. Each guarantees at least one valuable discovery so the player sees the point immediately.

**Files**: salvage_view.py, refining_view.py, tutorial_manager.py

---

## P6: Keyboard Shortcuts & Tooltip Improvements

**Design**:
- **Keyboard shortcuts for all core views:**
  - Trading: B/S buy/sell, M/X buy-max/sell-max, R refuel, T rest, Tab switch tables, 1-9 for row selection
  - Station Hub: 1-6 for locations, Enter to visit, Esc to undock
  - Galaxy Map: first-letter navigation for systems, Enter to travel
  - Display shortcut hints on buttons: "[B] BUY" instead of "BUY"
- **Centralized KeyBindings config** for future remapping (P15)
- **Tooltip improvements:**
  - Ship builder: hover a module to see stat changes before placing
  - Combat: hover a move button to see damage/energy details
  - Trading: hover a commodity to see cargo held + purchase price

**Files**: config.py or new keybindings.py, trading_view.py, station_hub_view.py, galaxy_map_view.py, ship_builder_view.py, combat_view.py

---

## P7: Trade Route Memory & Cargo Comparison

**Design**:
- Cargo table shows purchase price vs. current market price with green/red profit/loss delta
- "Best Routes" panel below cargo table: which systems pay more for cargo the player currently holds
- Hover commodity in market table: shows how many the player holds at what cost
- Uses existing `TradeRouteTracker` model and `ship.cargo` purchase price data

**Files**: trading_view.py, trade_route.py, ship.py

---

## P8: Fast Travel, Auto-Sell & Save QoL

**Design**:
- **Fast Travel**: "Plot Course" on galaxy map. Consumes fuel for multi-hop. Encounter rolls at each hop. Pauses on encounter. Unlocked after visiting 4+ systems.
- **Auto-Sell Presets**: "Sell All Ore" / "Sell All Salvage" buttons. Optional "sell on arrival" preferences.
- **Save QoL**:
  - Named saves (player can label their save slots)
  - Autosave frequency setting (every N days or on dock)
  - Save file corruption recovery (detect invalid saves, offer to load backup)

**Files**: galaxy_map_view.py, encounter.py, trading_view.py, player.py, save_manager.py, settings_view.py

---

## P9: Dynamic Music Intensity

**Design**:
- `MusicContext` dataclass: state, danger_level, faction_id, player_health_pct
- `resolve_music(context)` replaces static `_STATE_MUSIC` dict lookup
- **Combat**: crossfade to more intense variant when player health drops below 30%
- **Station**: per-faction ambient tint (existing `frontier_danger` track currently unused — wire it to dangerous system travel)
- **Galaxy map**: crossfade from exploration to frontier_danger when approaching dangerous systems
- Implement crossfade in `AudioManager.update()` (method exists, currently no-op)

**Files**: audio_manager.py, game.py (_STATE_MUSIC), manifest.json

---

## P10: Missing SFX & Ambient Polish

**Design**:
- Add to manifest: `level_up`, `dialogue_tick` (subtle typewriter), `quest_complete`, `crew_recruit`, `reputation_change`
- Per-faction ambient variants: `ambient_station_commerce`, `ambient_station_miners`, `ambient_station_science`, `ambient_station_frontier`
- Faction-aware ambient resolution in game.py
- Add `dialogue_tick` to dialogue_view typewriter effect (very subtle, rhythmic)

**Files**: manifest.json, game.py (_STATE_AMBIENT), dialogue_view.py

---

## P11: Balance Config File

**Design**:
- Create `data/economy/balance.json` containing:
  - Starting conditions (credits, fuel, ship type)
  - XP rates per activity
  - Encounter chance modifiers by danger level
  - Early-game protection threshold
  - Commodity price variance ranges
  - Mission reward multipliers
  - Rest cost per day (currently free, configurable)
- `DataLoader.load_all()` reads this. Config.py constants become defaults overridable by balance.json.
- Enables difficulty presets (Easy/Normal/Hard) by swapping balance configs

**Files**: config.py, data_loader.py, new data/economy/balance.json

---

## P12: Core Loop Pacing & Session Flow

**Design**:
- **First trade bonus**: Double profit on literal first commodity sale (flag-gated, one-time). Narratively: Elena's tip pays off.
- **Tutorial mining guarantee**: First mining session guarantees rare ore drop (seeded field)
- **Reward curve verification**: Audit early mission rewards vs. ship upgrade costs and fuel expenses. Ensure the player can afford their first upgrade within 30 minutes of play.
- **Rest cost**: Small daily expense when resting (configurable in balance.json) so active play is incentivized over day-skipping
- **Session flow audit**: Play a full 60-minute session. Document where engagement peaks and drops. Is there a "one more trade" pull? Does upgrading the ship feel rewarding? Where does tedium creep in? Output: tuning recommendations applied to balance.json.

**Files**: market.py, mining.py, balance.json

---

## P13: Colorblind Mode & Seizure Safety

**Design**:
- **Colorblind palettes**: `ColorMode` enum: NORMAL, DEUTERANOPIA, PROTANOPIA, TRITANOPIA
- Colorblind-safe palette remappings in palettes.py
- Replace red/green indicators with shape indicators (up/down arrows, +/- symbols) IN ADDITION to color
- Pattern fills for faction-colored elements where color is the sole differentiator
- Settings dropdown in SettingsView
- **Seizure safety audit**: Review all screen shake, flash overlay, particle burst effects for rapid strobing. Add intensity caps. Document results. Consider a "reduce screen effects" toggle.
- **Settings persistence**: All new settings (colorblind mode, font scale, key bindings from P14-P15) use a unified settings file alongside existing audio/resolution prefs.

**Files**: palettes.py, config.py (Colors class), settings_view.py, save_manager.py (settings persistence)

---

## P14: Font Scaling & High Contrast

**Design**:
- `font_scale: float` setting (0.8 to 1.5), multiplied into `scaled_font_size()` in fonts.py
- High contrast mode: separate palette (pure black backgrounds, bright white text, vivid borders)
- Both settings in SettingsView with live preview
- Settings persisted via the unified settings system from P13

**Files**: fonts.py (scaled_font_size, FontCache), settings_view.py, palettes.py

---

## P15: Key Remapping

**Design**:
- `KeyBindings` dataclass mapping action names to `pygame.K_*` constants
- Default bindings loaded from `data/keybindings.json`. Player overrides stored in settings.
- All views replace hardcoded `pygame.K_*` checks with `keybindings.get("action_name")` lookups
- SettingsView "Controls" section showing current bindings with click-to-rebind
- Builds on the centralized keybindings infrastructure from P6

**Files**: new keybindings.py, settings_view.py, all view files

---

## P16: Emotional Peaks Staging

**Design** (no new content, better presentation of existing moments):

1. **Marcus revelation** (Mission 5, The Foreman's Son): Slow dim, music shift to `dialogue_intimate`, dust particle effect symbolizing the recycler dust that killed the father.

2. **First pirate attack** (Mission 12, Under Fire): Longer intro beat. `combat_intense` music fades in during the encounter choice screen before combat begins. WARP_TRAIL particle effect as pirates drop out of warp.

3. **Embassy summit** (Mission 14): Each faction speaker's dialogue panel tinted with their faction accent color. Music shifts between neutral and intimate as speakers change.

4. **Act One finale** (Missions 16-17): Victory fanfare (`victory_fanfare` track exists but only mapped to combat). Use it during mission completion dialogue. Extended transition effect. Screen effects for the Collapse sequence.

5. **Crew recruitment moments**: When a companion joins for the first time, brief musical sting + screen effect. These are emotionally significant — the player is no longer alone.

- `NarrativeStagingConfig` added to mission JSON: screen effects, music override, particles, transition type

**Files**: game.py, dialogue_view.py, screen_effects.py, missions.json

---

## P17: Tutorial System Cleanup

**Design**:
- Keep `TutorialOverlay` + `TutorialManager` as fallback for players who skip story tutorials or load a mid-game save
- Add `tutorial_approach` setting: "Story" (default) vs "Classic" (overlay tooltips)
- MINIGAME_HINTS remain as supplementary reminders (shown on second+ visits) regardless of mode
- Remove redundancy between story tutorial flags and classic tutorial state
- Ensure all story tutorial flags are properly set even when skipping, so the game doesn't re-trigger tutorials on a loaded save

**Files**: tutorial_manager.py, tutorial_overlay.py, settings_view.py

---

## Implementation Order (9 Sprints)

| Sprint | Phases | Focus | Rationale |
|--------|--------|-------|-----------|
| 0 | P0 | First session pacing audit | Analysis before implementation |
| 1 | P6, P11 | Keyboard shortcuts + tooltips + balance config | Low-risk infrastructure |
| 2 | P1, P2 | Ship builder + trading tutorials | Defines the story tutorial pattern |
| 3 | P3, P4, P5 | Mining, combat, salvage/refining tutorials | Apply the pattern |
| 4 | P7, P8 | Trade routes, fast travel, auto-sell, save QoL | Player convenience |
| 5 | P9, P10 | Dynamic music + missing SFX | Atmosphere |
| 6 | P12 | Core loop pacing + session flow audit | Depends on P11 balance config |
| 7 | P13, P14, P15 | Colorblind, font scaling, key remapping, seizure safety | Accessibility |
| 8 | P16, P17 | Emotional peaks + tutorial cleanup | Final polish |

## Verification
- After each sprint: pytest (all pass), ruff (clean), manual playtest
- **P0**: Output is a document (first-session timeline), not code
- **Story tutorials**: Test guided state transitions, flag integration, skip fallback, budget constraints (P1)
- **QoL**: Test keyboard shortcuts fire same logic as buttons. Test fast travel fuel calculations and encounter interruption. Test save naming persistence.
- **Audio**: Test resolve_music() returns correct track IDs (mocked mixer). Test crossfade timing.
- **Economy**: Test balance config loading and override behavior. Test first-trade bonus applies exactly once.
- **Accessibility**: Test palette remapping produces valid RGB tuples. Test font scaling at boundary values (0.8, 1.0, 1.5). Test keybind serialization round-trips. Seizure safety audit documented.
- **Emotional peaks**: Test staging config loads from mission JSON. Visual verification via playtest.

## Future Work (Noted, Not In Scope)
- **Player identity visibility**: NPCs reacting to player titles/playstyle. Partially implemented in SP3 (Master Negotiator). Full implementation is a content expansion, not polish.
- **Campaign Act Two**: Explicitly out of scope until this polish pass is complete.
- **Multiplayer/networking**: Architecture change, not polish.
