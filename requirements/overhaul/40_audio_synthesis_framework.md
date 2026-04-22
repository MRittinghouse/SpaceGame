# Audio Framework

> **Status:** DESIGN — Tier 3 parallel-track doc. The original master-plan title ("Audio Synthesis Framework") implied a procedural-synthesis-heavy scope; reality is that Aurelia's audio infrastructure is **already mature** (AudioManager + pygame.mixer + 72 audio assets + manifest-driven loading + 3-tier volume mixing). The gap is not engineering — it's **design discipline**. This doc defines the vocabulary, mix rules, and integration points that turn the existing engine into a coherent sonic identity.
>
> Inherits from `20_aesthetic_bible.md` (aesthetic voice), and informs every Tier 2 overhaul doc (combat cinematic audio cues, station hub ambient beds, mining click feedback, etc.).

---

## Table of Contents

1. Current state — honest assessment
2. Target feel — what Aurelia sounds like
3. Audio palette — vocabulary and taxonomy
4. Mix discipline — volume tiers, priority, ducking
5. Music and ambient orchestration
6. Integration points per Tier 2 system
7. Procedural audio — future research
8. Anti-patterns
9. Governance and discipline
10. Out of scope

---

## 1. Current state — honest assessment

### 1.1 What's already in place

- **`AudioManager` singleton** (`spacegame/engine/audio_manager.py`, 403 lines) with graceful degradation if `pygame.mixer` init fails. Clean API surface; save-compatible.
- **Three volume tiers** (master, music, SFX, ambient) with independent control and persistence via `AudioConfig`.
- **Manifest-driven asset loading** — `spacegame/data/assets/audio/manifest.json` (277 lines) maps semantic IDs (e.g., `mining_click`, `combat_explosion`, `ui_confirm`) to file paths + per-sound volume defaults.
- **72 audio assets committed:**
  - **11 music tracks** — `main_theme`, `combat_intense`, `galaxy_exploration`, `mining_rhythm`, `station_hub`, `defeat_somber`, `victory_fanfare`, `frontier_danger`, `ground_stealth`, `dialogue_intimate`, `dialogue_neutral`
  - **4 ambient loops** — `ambient_space`, `ambient_station`, `ambient_combat`, `ambient_ground`
  - **57 SFX** across nine categories — combat, mining, salvage, trading, navigation, UI, builder, activity, ground
- **15 views trigger SFX** currently — the event-driven SFX layer is live.

### 1.2 What's weak — the central gap

**Music and ambient APIs exist but are unused.** No view currently triggers music transitions. No ambient loops are wired to gameplay states. The engine knows how to cross-fade between two music tracks over 3 seconds; no code calls that method. Similarly: `ambient_combat` exists as an asset; no combat state activates it.

This is the single biggest gap. Aurelia has a **working audio engine with a silent atmospheric layer**. Every Tier 2 doc referenced audio cues (jump cinematic, prestige moment, named encounters) without knowing the ambient/music orchestration rules — because the rules don't exist.

### 1.3 Secondary gaps

**Gap 1: No categorical mixing rules.** SFX triggers in combat fire at the same volume as SFX in station hub, even though the listener expects different contexts. No ducking (lowering music under dialogue), no priority system (an ambient spark shouldn't drown an important encounter sting).

**Gap 2: No faction / scene audio identity.** The 11 music tracks are scene-generic. A Collective research station should sound different from a Crimson Reach station; currently both default to `station_hub`. No faction-specific variants exist, and no system maps faction → music.

**Gap 3: No Tier 2 integration specifics.** Master plan's ambitions for audio (combat dual tech stings, jump cinematic audio cue, mining prestige transition sound) are referenced generically in Tier 2 docs as "Tier 3 audio concern." This doc is where they get *specific*.

**Gap 4: No procedural audio.** All assets are pre-recorded WAV/MP3. No sndarray synthesis, no parameterized SFX generation, no dynamic audio response to game state. The master plan's framing ("Audio Synthesis Framework") hinted at this direction; it remains future research (§7).

**Gap 5: Mix discipline absent.** No documented rule for "how loud should a UI click be relative to a combat hit." Volume defaults in the manifest are per-file, set without reference to a canonical scale. First-pass levels without a discipline document.

### 1.4 What this doc addresses

- Gap 1 (categorical rules) via mix discipline (§4)
- Gap 2 (no faction identity) via faction-specific music variants + scene identity (§5)
- Gap 3 (no Tier 2 integration) via per-system integration point catalog (§6)
- Gap 4 (no procedural audio) via deferred research direction (§7)
- Gap 5 (mix discipline) via volume tier standards + ducking rules (§4)
- Master gap (music/ambient unused) via orchestration rules (§5)

---

## 2. Target feel — what Aurelia sounds like

### 2.1 The voice

Aurelia sounds **industrial-worked, acoustically-present, sparingly-scored**. Three descriptors, each with discipline:

- **Industrial-worked** — mechanical authenticity over synthesis drama. A ship's engine hum is a pressure vessel running, not a spaceship theme park. A forge's sound is metal striking metal, not fantasy-forge magic. Machinery, weight, physics. Pairs directly with AB §1.1's "lived-in industrial" visual voice.
- **Acoustically-present** — sound is physical. Footsteps on grated decking, breath in a helmet, coolant flow through pipes, distant thunder of capital engines. Audio establishes space-as-place.
- **Sparingly-scored** — music is *reserved*, not constant. Scenes without music trust ambient + SFX to carry mood. Music enters for weight, exits when weight passes. No backgrounded score that the player stops hearing.

### 2.2 Reference constellation

What Aurelia reaches toward:

- **Alien (1979)** / **Alien: Isolation (2014)** — diegetic industrial sound (hull creaks, air circulation, distant machinery) as primary mood carrier. Minimal score. When music enters, it *means something*.
- **Signalis (2022)** — extremely restrained scoring. Long silences. When a synth line enters, the effect is devastating. Every sound authored with weight.
- **Death Stranding (2019)** — ambient journey with deliberate musical punctuation. A long trek is mostly footsteps, wind, occasional mechanical. Music surfaces at vista moments; hits hard because it's rare.
- **The Expanse TV series (sound design)** — realistic spacecraft audio (vacuum silence from outside; interior noise from inside; physics-accurate). Serves as direct cultural-fit reference.
- **Hades (2020)** — music as character. Distinct themes per location, dynamic layering, musical identity stitching gameplay together.

What Aurelia rejects:

- **Mass Effect's wall-to-wall orchestral score.** Beautiful but constant; eventually backgrounds out.
- **Elder Scrolls / Witcher ambient-bardic convention.** Wrong cultural register (fantasy-world exploration music doesn't fit industrial sci-fi).
- **Procedural-infinite synthesis drone** (No Man's Sky's procedural music).  Musically flat over long sessions.
- **Chiptune / retro-wave nostalgia.** Visually Aurelia is pixel art but NOT retro-gaming tribute; audio shouldn't do that either.

### 2.3 Tonal rules

- **Silence is canonical.** A scene with no music is not broken. Many scenes work better with ambient + SFX only.
- **Music earns its entrance.** A music track fading in should correlate with a narrative or gameplay beat, not a state transition.
- **Ambient carries baseline mood.** In any scene with no active music, ambient establishes place.
- **SFX respect listener bandwidth.** No more than ~6 distinct simultaneous SFX voices. Beyond that, ducking + priority system culls.
- **Dialogue is sacrosanct.** When dialogue is playing (even if text-only with no voiced audio), music and SFX duck to 40% to respect the narrative moment.

---

## 3. Audio palette — vocabulary and taxonomy

Parallel to the visual palette (AB §2), the audio palette defines disciplined categories. The existing manifest's 9 categories are retained and codified.

### 3.1 Categorical taxonomy

**Nine canonical categories** (matching current manifest structure). Each has mixing rules, volume ceilings, and use conventions:

| Category | Volume ceiling (multiplier of SFX master) | Purpose | Discipline |
|---|---|---|---|
| `combat` | 1.0 | Impacts, weapon fire, shields, explosions | Loudest permitted — combat reads as high-stakes |
| `mining` | 0.75 | Click, break, chain, drill, energy | Pleasant repeated-action — never grates |
| `salvage` | 0.70 | Scan, reveal, extract, corrupt | Tense precision; corruption sounds louder |
| `trading` | 0.55 | Buy, sell, refuel, fail | Tactile commercial — feedback, not spectacle |
| `navigation` | 0.80 | Dock, jump, arrive, select | Transition weight; jumps are bigger than selects |
| `ui` | 0.45 | Click, hover, confirm, error, cancel, scroll | Subtle feedback — never louder than gameplay |
| `builder` | 0.60 | Place, rotate, remove, variant | Tactile craft — each action feels intentional |
| `activity` | 0.70 | Refine, repair, achievement, unlock | Moment-weighted — achievements loudest; actions moderate |
| `ground` | 0.85 | Step, door, pickup, alert, combat | Close-proximity weight — footsteps carry character |

Volume ceilings are *hard caps* at category level. Individual assets within a category may be quieter (manifest-defined) but never exceed the ceiling.

### 3.2 Music taxonomy

**11 tracks, four usage tiers:**

| Tier | Tracks | Usage |
|---|---|---|
| **Foundation** | `main_theme`, `galaxy_exploration`, `station_hub` | Default scene music — sets baseline mood |
| **Intensity** | `combat_intense`, `ground_stealth`, `frontier_danger` | Elevated-threat scenes |
| **Resolution** | `victory_fanfare`, `defeat_somber` | Outcome punctuation — short, memorable, doesn't loop |
| **Intimate** | `dialogue_intimate`, `dialogue_neutral`, `mining_rhythm` | Scene-specific subtext — one-on-one, focused work, ambient activity |

### 3.3 Ambient taxonomy

**4 loops, four spaces:**

| Loop | Space | Texture |
|---|---|---|
| `ambient_space` | Cockpit, galaxy map, travel | Low rumble + occasional distant mechanical + comm chatter |
| `ambient_station` | Station hub (any faction, default) | Hum of civilization + distant machinery + occasional PA |
| `ambient_combat` | Combat view (pre-engagement, calm phases) | Tense hum + distant threats + ship systems |
| `ambient_ground` | Ground exploration | Footstep acoustics + environment-specific (duct hiss, reactor hum, open-air wind) |

**Gap to fill (Phase A2 — §10):** faction-specific ambient variants for station hub. v1 scope adds:

- `ambient_station_guild` — commerce hum with transit whoosh + PA announcements
- `ambient_station_union` — industrial heavy, clangs, steam
- `ambient_station_collective` — clean hum, electronic tones, quiet
- `ambient_station_frontier` — patch-worked creak, distant music from cantina, wind
- `ambient_station_reach` — dim, tense, occasional distant yelling

### 3.4 SFX naming conventions

All new SFX follow: `{category}_{action}_{modifier}` — e.g., `combat_hit_plasma`, `mining_click_rare`, `ui_confirm_positive`. Existing manifest entries are already conventional; future additions follow.

---

## 4. Mix discipline — volume tiers, priority, ducking

### 4.1 Volume tiers (hierarchy)

```
master_volume (0.0 – 1.0)
  ├── music_volume (0.0 – 1.0)    → applied to all music tracks
  ├── sfx_volume (0.0 – 1.0)      → applied to all SFX channels
  └── ambient_volume (0.0 – 1.0)  → applied to ambient loops
```

Each tier persists in save data. Category volume ceilings (§3.1) apply as multipliers *within* the SFX tier.

### 4.2 Priority system (SFX culling)

pygame.mixer default channel count is 8. Aurelia reserves:
- 2 channels for music (cross-fade pair)
- 2 channels for ambient (cross-fade pair)
- 4 channels for SFX (dynamic, priority-managed)

When more than 4 SFX attempt simultaneous playback, a **priority system** culls:

| Priority | Category examples | Never culled |
|---|---|---|
| Critical (1.0) | Combat explosion, dual tech sting, boss-specific cues, prestige cinematic | Yes |
| High (0.8) | Weapon fire, shield hit, named encounter entry, achievement unlock | Yes |
| Normal (0.6) | Click sounds, standard transitions, activity completions | If outbid |
| Low (0.4) | Hover, ambient spark, minor UI feedback | Frequently culled |

Implementation: when a new SFX wants to play and all channels are busy, the lowest-priority playing SFX is stopped *if* the incoming SFX has higher priority. If equal or lower, the incoming is dropped.

### 4.3 Ducking rules

**Music ducks under specific events:**
- Dialogue active → music → 40% (recovers to 100% on dialogue end + 0.5s)
- Critical SFX (priority 1.0) → music → 60% for duration + 0.5s fade-back
- Scene transition → music crossfades to next track

**Ambient ducks under music:**
- When music is playing → ambient → 70%
- When music fades out → ambient recovers gradually (0.8s fade-in to 100%)

**SFX does not duck** — SFX is always at full mix (within category ceiling). Ducking SFX would make combat feel muffled.

### 4.4 Spatial audio (stereo panning)

pygame.mixer supports basic stereo panning via `Channel.set_volume(left, right)`. Aurelia uses this for:
- Combat: projectile direction (left/right based on attacker-target relative position)
- Ground: enemy sounds panned toward enemy position
- Ambient: nothing (ambient stays centered)

Full 3D audio is out of scope; stereo panning is the discipline level.

---

## 5. Music and ambient orchestration

The central design work. Orchestration rules for when specific music and ambient tracks play.

### 5.1 Scene-to-music mapping

| Scene / state | Default music | Transition rule |
|---|---|---|
| Main menu / title | `main_theme` | Loops; fades out on game start |
| Galaxy map | `galaxy_exploration` | Fades in on galaxy-map open; fades out on travel start |
| Travel jump sequence | — (no music; SFX-dominant) | Jump audio cue replaces music briefly |
| Station hub (default) | `station_hub` | Fades in on dock; faction-specific overrides possible |
| Station hub (Crimson Reach) | `frontier_danger` | Faction override |
| Station hub (ground/outpost variants) | `station_hub` mix with `ambient_ground` | Crossfade rule |
| Cockpit (idle at station) | — (no music; `ambient_station`) | Silence discipline — station is a place, not a music cue |
| Cockpit (idle in space) | — (no music; `ambient_space`) | Silence discipline |
| Combat (pre-engagement) | Brief `combat_intense` intro (8s) | Plays on first enemy contact; fades to ambient if combat doesn't escalate |
| Combat (engagement active) | `combat_intense` loop | Full volume; phase-based layering in future (§5.4) |
| Combat (boss / legendary) | `combat_intense` + boss sting overlay | Layer rule |
| Combat (resolution — victory) | `victory_fanfare` (one-shot, 4-8s) | Non-looping; returns to scene default |
| Combat (resolution — defeat) | `defeat_somber` (one-shot, 6-10s) | Non-looping; sobering |
| Ground exploration (stealth) | `ground_stealth` | Begins on ground deployment |
| Ground exploration (combat) | `combat_intense` | Overrides `ground_stealth` during active combat |
| Mining session | `mining_rhythm` | Plays during session; fades out on exit |
| Salvage session | — (no music; `ambient_combat` replaces) | Tension through silence + ambient |
| Refining session | — (no music; ambient + forge SFX carries) | Silence discipline — the forge sounds itself |
| Dialogue (intimate / personal) | `dialogue_intimate` | Ducks ambient; plays through conversation |
| Dialogue (neutral / transactional) | `dialogue_neutral` | Ducks ambient; plays through conversation |
| Dialogue (tense / confrontation) | `frontier_danger` | Scene-specific override |

### 5.2 Ambient-to-scene mapping

Ambient always plays in the background of every scene (unless music explicitly suppresses it). Defaults:

| Scene | Ambient |
|---|---|
| Cockpit (in space) | `ambient_space` |
| Cockpit (docked) | `ambient_station` |
| Station hub | `ambient_station` (+ faction variant per §3.3) |
| Combat | `ambient_combat` (even when `combat_intense` music is playing, ambient provides bed) |
| Ground exploration | `ambient_ground` |
| Mining / salvage / refining | Appropriate scene-specific ambient (mining → space variant; salvage → scene-specific; refining → forge ambient layer) |
| Galaxy map | `ambient_space` |

### 5.3 Dynamic transitions

**Fade curves** (via `AudioManager.fade_in` / `fade_out`):
- **Scene-to-scene transition** — 1.5s crossfade
- **Music fade-in on state entry** — 2.0s fade-in
- **Music fade-out on state exit** — 1.2s fade-out
- **Ambient swap** — 0.8s fade (faster, less noticeable)
- **Combat music entry on engagement** — 0.5s fade-in (quick, punchy)
- **Jump cinematic audio** — no fade; sharp SFX-driven
- **Prestige cinematic audio** — 0.5s music duck, then cinematic audio plays, then music restores over 2.0s

### 5.4 Future layering (deferred)

Target future state: **dynamic music layering** where combat music gains intensity layers as the battle progresses (drums join at phase 2, brass at phase 3, etc.). Not v1. Noted for future research — requires either:
- Pre-authored stems per music track (expensive; many assets to produce)
- Procedural synthesis layer (links to §7 procedural audio research)

### 5.5 Silence as signal

Rules for when *no music* is appropriate:

- **Contemplative moments** — standing in cockpit deciding next action; reviewing journals; examining map at galactic zoom. Ambient carries.
- **Transitions** — jumps, scene changes where music would fight the transition.
- **Tension-through-silence** — Salvage's corruption-pressure moments; deep ground exploration stealth sections.
- **Post-climax recovery** — after a dual tech cinematic, return to silence + ambient lets the moment breathe.

Silence is designed, not accidental. An audio pass's success is measured partly by *where music isn't*.

---

## 6. Integration points per Tier 2 system

Specific hooks each Tier 2 doc references that audio must support.

### 6.1 Combat (30)

- **Weapon fire SFX per element** — existing SFX library has `laser`, `missile`, generic `combat_hit`. Per §34 dual-tech direction and AB §3.5 elemental discipline, expand to element-specific:
  - `combat_hit_kinetic` (existing `combat_hit`)
  - `combat_hit_plasma` (fire / burn character)
  - `combat_hit_ion` (electrical / buzz character)
  - `combat_hit_cryo` (glass-shatter / chill character)
  - `combat_hit_voltaic` (arc-flash / crack character)
- **Dual tech sting** — 1-2 second musical sting that plays at tech-name-hold moment (t=0.9-1.5 of cinematic). Composed per tech type (~7 techs = 7 stings). Currently none.
- **Ultimate charge sound** — building hum during ultimate cinematic charge phase (t=1.5-3.0). One SFX, pitch-escalating (or multiple layered). Currently none.
- **Arena entry audio cue** — brief, punchy "engagement begins" tone synchronized with camera push-in (combat §4.8). Currently none.

### 6.2 Ship builder (31)

- **Module place SFX** — existing `builder_place` — good. Audit volume (may be too low currently).
- **Module rotate SFX** — existing `builder_rotate` — good.
- **Confirm build scale-pop** — existing builder SFX plus `activity_unlock` layered for "ship finalized" weight. Coordinate (§31 §4.9).
- **Test flight audio** — §31 §4.7 test flight sequence needs distinct audio: engine-ignite, thrust, maneuver, weapon-test, idle. Each maps to existing or new SFX.

### 6.3 Mining (32)

- **Tier-weighted click SFX** — existing `mining_click` covers tier 1-2. Tier 3 rare and tier 4 legendary need distinct SFX (`mining_click_rare`, `mining_click_legendary`). Currently generic.
- **Skill voice audio delivery** — §32 §5.2 skill voices currently text-only. If future voice acting happens, audio framework supports `voiceover` channel. Text-only for v1.
- **Depth layer transition** — existing `activity_unlock` or new SFX per layer. Target: one-shot played at layer-transition banner.
- **Prestige cinematic audio** — §32 §8.4 prestige cinematic needs distinct audio: music duck, cinematic build (2-3s), ceremonial chime at numerical celebration moment. Currently none.
- **Drone working SFX** — ambient background when drones are active. Very quiet, repeated.

### 6.4 Galaxy map (33)

- **Jump sequence audio** (§33 §4.1) — 4-phase:
  - Phase A Charge (1.0s): rising hum (0-2s peak)
  - Phase B Flash (0.15s): SHARP tone (snap)
  - Phase B-C Streak (1.2s): rushing-through-space sound
  - Phase D Arrival (0.5s): resolving tone / dust-settling
  
  Currently the only navigation SFX is `navigation_jump`. Expand to 4-segment sequence.
- **Zoom transition SFX** — subtle whoosh on each zoom-tier change (close → default → regional → galactic).
- **Landmark discovery chime** — when a landmark icon first becomes visible.

### 6.5 Trading (34)

- **Transaction confirmation SFX** — existing `trading_buy`, `trading_sell` — good. Tier per tier-4 damage number (§34 §4.9 stamp-down).
- **Ticker scroll** — no SFX (ticker is visual; audio would fatigue).
- **Market Intel Panel open** — discrete data-access tone (short synth blip). New SFX needed.
- **Permit stamp application** — distinct "stamp" sound when a permit unlocks. New.

### 6.6 Station hub (35)

- **Docking cinematic audio** (§35 §4.10) — airlock hiss + rumble + click of docking; existing `navigation_dock` can extend.
- **Faction-specific ambient variants** — §3.3 defines 5 new ambient loops per faction. Priority Phase A2.
- **Entrance tagline chime** — subtle audio cue synchronized with faction-tagline reveal.
- **News ticker headline chime** — when a particularly important headline surfaces. Rare.

### 6.7 Salvage (36)

- **Tier-weighted extraction feedback SFX** — existing `salvage_scan`, `salvage_extract` — good. Tier 3 rare + tier 4 legendary need distinct SFX.
- **Corruption pressure audio** — heartbeat pulse should get louder as corruption timer depletes. Heartbeat SFX exists implicitly in current atmosphere; formalize.
- **Named encounter intro** — specific SFX for each of 5 named wrecks (Signal Ship broadcasts, etc.). New.
- **Module recovery cinematic audio** — §36 §4.7 module recovery needs extraction sound + weighty "thunk" for module appearing in inventory. New.

### 6.8 Refining (37)

- **Forge atmosphere layering** — existing heat-scaling atmosphere is visual only. Add audio layer: forge hum that intensifies with queue load. New SFX.
- **Gold mastery-up** — extended celebration needs weight. Currently `activity_achievement`; extend with a specific gold-tier SFX.
- **Quality variance S-grade** — distinct chime for S-grade output. New.
- **Exposition event announcement** — subtle audio cue (bell-or-gong-like) when Exposition activates. New.

### 6.9 Ground exploration (38)

- **Expedition Resolve thresholds** — ambient shifts tone when crossing thresholds (Steady → Pressed → Strained → Broken). Existing `ambient_ground` can layer.
- **Named encounter intros** — 5 named NPCs get distinct entry audio. New.
- **Affliction audio cues** — subtle UI chime when crew member develops affliction at result screen. New.
- **Expedition voice delivery** — text-only v1, audio framework supports future voiceover channel.
- **Party combat audio** — positional stereo panning per party member position. Existing panning infrastructure.

---

## 7. Procedural audio — future research

The master plan's original "Audio Synthesis Framework" naming hinted at procedural sound generation. Deferred to future work. Research directions when bandwidth exists:

### 7.1 sndarray-based synthesis

pygame supports `sndarray` for raw audio manipulation. Viable for:
- **Parameterized SFX variation** — one "click" SFX that varies pitch/envelope per trigger context (reduces perceived repetition)
- **Generative drones** — procedural ambient pads for niche scenes (e.g., The Long Dark / abyssal wreck content)
- **Retro-chip-style bleeps** — if needed for diegetic computer interfaces

Cost: moderate complexity. Requires audio DSP knowledge.

### 7.2 Dynamic music layering via stems

Pre-author music tracks with separate stems (drums / bass / brass / strings). Engine blends stems based on game state. Existing AudioManager doesn't support this; would require extension.

Cost: significant — both engineering and content authoring.

### 7.3 Physics-based SFX

Real-time synthesis of metal-on-metal, wind, footsteps via procedural models. Very advanced. Not Aurelia-scoped near-term.

### 7.4 Decision framework

Procedural audio is pursued only when:
1. A specific gameplay moment cannot be served by pre-recorded assets
2. Asset authoring for that moment would be prohibitively expensive
3. Procedural approach produces quality comparable to or better than what the asset would be

Until these conditions intersect, Aurelia's audio remains curated-recorded-assets discipline.

---

## 8. Anti-patterns

### 8.1 Wall-to-wall music

**Don't:** music playing during every scene, every moment. Listener fatigue guaranteed; silence value destroyed.

**Do:** Reserve music for scenes defined in §5.1. Default to ambient + SFX.

### 8.2 Mismatched tonal music

**Don't:** `combat_intense` playing during a peaceful ground dialogue; `dialogue_intimate` playing during a firefight.

**Do:** Music choice reinforces scene register. State transitions trigger music transitions; music lags state by ≤1s.

### 8.3 SFX density without priority discipline

**Don't:** 12 simultaneous particle effects each emitting their own SFX, producing cacophony.

**Do:** Particle systems emit SFX sparingly (e.g., one SFX per "event" — a shield break triggers one SFX, not one per shard fragment). Priority system culls when overloaded.

### 8.4 Unmuted silence

**Don't:** treat scene silence as "the audio system is off." Ambient ALWAYS plays during gameplay; silence is an intentional choice of ambient variant.

**Do:** Every scene defines explicit ambient + music selection, even if that selection is "none for now, ambient only."

### 8.5 Audio as replacement for visual feedback

**Don't:** rely on SFX alone to communicate critical gameplay state (hit landing, enemy detecting player, etc.). Visual is primary; audio reinforces.

**Do:** Audio complements, never replaces. Player with audio disabled should still understand what's happening.

### 8.6 Generic tracks overriding specific moments

**Don't:** fall back to `main_theme` during every non-specific moment. Makes those moments feel templated.

**Do:** When a moment doesn't have a specific scored track, default to ambient + silence. Ambient carries more identity than a mismatched music track.

---

## 9. Governance and discipline

### 9.1 New audio assets require:

1. **Categorical placement** — which of 9 SFX categories (or music / ambient) does it belong to?
2. **Volume default** calibrated against category ceiling
3. **Naming convention compliance** (§3.4)
4. **Manifest entry** in `data/assets/audio/manifest.json`
5. **At least one integration point** — an existing or planned use case

Orphan assets (in manifest but never triggered) are flagged during audits and removed or repurposed.

### 9.2 Trigger points document

Each Tier 2 system maintains a "trigger points" section listing every SFX/music trigger it emits (ideally in its doc, see §6 above for v1). When a new trigger is added, both the system's doc and this doc's §6 update.

### 9.3 Mix audits

Periodic audit pass: play the game for a session, listen for:
- Tracks backgrounded out (you stopped hearing them)
- SFX too loud (fatiguing after session)
- Music stomping on dialogue
- Ambient silences that should have something

Flag issues; tune volumes in manifest; revise orchestration rules if patterns emerge.

### 9.4 Accessibility

- All audio content has **text / visual equivalent** per anti-pattern §8.5.
- Volume tiers granular enough for audio-sensitive players.
- Future: optional "audio description" layer that narrates important audio events (deferred; accessibility pass).

### 9.5 Versioning

This doc versions as audio scope expands. Revision history at header.

---

## 10. Out of scope

- **Voice acting** — dialogue remains text-only in v1; voiceover channel API reserved but unused
- **Binaural / HRTF 3D audio** — stereo panning is the discipline ceiling
- **Adaptive music generation (AI)** — category excluded per Aurelia's no-AI-content constraint
- **Licensed music** — all music is original or commissioned; no pop-song soundtrack
- **Per-platform audio optimization** — single-build audio; no platform-specific mixing
- **Audio-driven gameplay** — no rhythm-based mechanics; audio is response layer, not input layer
- **Procedural audio** beyond §7 research scope

---

*Revision history:*
- *v1 — initial Tier 3 framework, aligned to existing AudioManager + manifest + 72-asset corpus. Defines discipline; engineering already present.*

*Next Tier 3 doc: `41_vfx_particle_vocabulary.md` — formalizes the particle taxonomy already present in `particles.py` + domain-specific VFX files.*
