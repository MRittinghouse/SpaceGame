# Aurelia: A Ledger of Stars. Overhaul Master Design

> **Moved.** The living copy is in the `aurelia` repo at `docs/specs/2026-09-25-aurelia-overhaul-master-design.md`. This copy is frozen as of the SP2-b merge (2026-09-26); edit the aurelia copy.

- **Date:** 2026-09-25
- **Status:** Approved section by section in a paired brainstorm (2026-09-25). This written form awaits
  the author's review.
- **Scope:** Program level. Every sub-project in Section 10 gets its own paired brainstorm, sub-spec,
  and plans. This document binds them; a sub-spec that contradicts it needs an explicit amendment here.
- **Supersedes:**
  - the engine-migration rejection in `2026-08-23-quality-foundation-design.md`
  - the 2026-08-28 direction that "the pygame core stays"
  - the pixel-canvas ship builder
  - the three-tier currency rule in the overhaul corpus
  - `requirements/overhaul/20_aesthetic_bible.md` as the governing art bible (its palette carries
    forward into the pixel bible)
  - the Act II v1 lens arc (A2-1 to A2-21) as shipping content
- **Still binding:** `requirements/dialogue_writing_guide.md`, `requirements/character_voices.md`,
  `requirements/cultural_guide.md`, the creative direction (the ambition bar and the Act I / Act II
  boundary), the banned-names list, and the deterministic-outcome rule.

---

## 0. Summary

Aurelia moves to Godot 4.7 and typed GDScript. The simulation is ported at parity against the Python
build, which becomes the reference implementation. The experience is redesigned rather than
translated: the diagnosis in Section 1 shows that most of what makes the game feel clunky is design,
and a straight port would carry it across.

The redesign has five pillars. The ship becomes one design system shared by an Armored Core garage,
the living map, and a turn-based fight made visceral. Space becomes a place: a living map the player
does not pilot, where encounters come from the world and can be seen coming. Stations become places
too, with panels that open over the scene instead of full-screen swaps. Every activity becomes a
career with its own identity, easy to pick up and deep enough to master. The art moves to high-res 2D
pixel art built so that consistency comes from the pipeline rather than from careful prompting.

The work is sequenced slice-first. Art direction and the foundation run in parallel, the port runs
autonomously in waves, and the Ship, Space, and Stations sub-projects meet in a Nexus Prime vertical
slice that decides whether the direction holds before breadth is built. Act I is completed and
polished first. Act II is then rebuilt in its own galaxy to finish the story.

### Decision log

| # | Decision | Notes |
|---|---|---|
| D1 | Port Aurelia to Godot 4.7, typed GDScript | Reverses the 2026-08-23 rejection. Everember proved the Godot, MCP Pro, and AI-art workflow. |
| D2 | Act I first. Act II v1 is archived, not ported. Act II is rebuilt later in its own galaxy to finish the plot | Act II v1 was written into the Act I galaxy (Section 1.4). |
| D3 | Travel is a living map the player does not pilot | The author chose this over piloted in-system flight: "We focus on our encounters." |
| D4 | Combat stays turn-based and is made visceral | The author chose this over piloted and tactical real-time. The combat engine is in port scope. |
| D5 | Slice-first sequencing | Chosen over port-first and art-first. |
| D6 | The ship is one design system across garage, map, and fight | Section 3. |
| D7 | Art direction is high-res 2D pixel art | Section 5. |
| D8 | The pixel-canvas builder is retired; authored parts are assembled Armored Core style | Section 3.1. |
| D9 | Borrow heavily from Armored Core and Starfield | Section 3.8. |
| D10 | Substantial variety in parts and styles | Section 3.5. |
| D11 | The Everember image-model hold does not apply to Aurelia. gpt-image-2.5 is the presumed default, confirmed by a validation cycle first | Section 5.3. |
| D12 | Every activity is a career under the Career Charter | Section 7.1. |
| D13 | One economy: credits plus materials | Supersedes the corpus's three-tier currency rule. Section 7.6. |
| D14 | Ralph retires. Execution follows the Everember runbook | Section 11. |

---

## 1. Why: the diagnosis

Measured on 2026-09-25 by three read-only surveys of the repo. Figures marked "read in code" were not
confirmed at runtime.

### 1.1 The systems are real

| Area | Lines | Notes |
|---|---|---|
| `spacegame/models/` | 42,227 (104 files) | Zero pygame imports. Star-shaped around `Player`, not tangled: 167 import edges among 103 modules, 48 modules import no other model. |
| `spacegame/engine/` | 21,625 (43 files) | 2,709 lines pure logic; the rest imports pygame, including `game.py` at 7,161. |
| `spacegame/views/` | 45,912 (51 files) | Rewritten in full. |
| `tests/` | 167,693 | 10,633 tests. |
| `data/` | 2.39 MB (86 JSON files) | Ports as-is. Content refers to assets by identity, never by file path. |

### 1.2 The clunk is mostly design

- **Every action is a full-screen swap.** `GameState` has 43 members, 38 of them live, served by 41
  views. Only 2 states are overlays. `game.py` has 71 transition calls, 54 of them the same 0.3 s fade.
- **A single buy, fly, sell leg costs about 12 to 13 clicks, 6 fades, and 4 screens** without an
  encounter. Travel is a dot moving for `0.5 + dist/180` seconds. Encounters are a hidden roll of 0,
  20, or 40 percent by danger (`data/economy/balance.json`).
- **The ship has no presence.** Combat is "a static camera watching a pool fight"
  (`requirements/overhaul/30_overhaul_space_combat.md`). The market is "a text-read task" with zero
  charts (`34_overhaul_trading.md`). Mining is about 9 clicks per common rock.
- **Every screen looks alike.** 34 of 41 views use the same procedural starfield and dim overlay. 40 of
  71 NPCs have no portrait. Six painted backgrounds have zero callers.
- **Built, never wired.** `ui_chrome.py` (428 lines), `journal_surface.py` (471),
  `skill_voice_overlay.py`, and `audio_orchestrator.py` (417) have zero call sites. Every overhaul doc
  from 30 to 38 is still at status DESIGN.
- **Inconsistent input.** The main loop consumes ESC for the pause menu before any view sees it
  (`game.py:6899`, read in code). The galaxy tip says "click again to travel" and nothing handles it.
  Refuel defaults to one unit (F-001, still open at `trading_view.py:323,1262`).
- **Two UI systems mixed.** 414 pygame_gui references against 1,068 raw blits and 839 font renders
  cause the tooltip z-order, text-wrap, focus, and scrolling bugs.
- **Legibility work stalled.** Findings F-001 to F-003 were routed to a Spec C that was never written.
  Only three playtest sessions are on record (2026-04-22, 04-23, 05-05), all covering the first two
  hours.

Ranked root causes, and whether a port fixes them:

| Rank | Root cause | Port fixes it? |
|---|---|---|
| 1 | Every action is a full-screen menu swap | No. Design. |
| 2 | The ship has no physical presence in the world | Partly. Mostly design. |
| 3 | Mixed pygame_gui and hand-drawn UI | Yes. Godot's Control and Theme system. |
| 4 | Legibility work stalled after the last playtest | No. Process. |
| 5 | Presentation work built but never wired | No. Process. |
| 6 | Every screen looks alike | No. Art and design. |
| 7 | Inconsistent input | No, if copied as-is. |
| 8 | Breadth over depth (five hub layouts, three mini-game currencies, four venue styles) | No. Design. |

**Conclusion: port the simulation, redesign the experience.**

### 1.3 The campaign

- Act I has 22 missions, 17 on the critical path, and about 95K words of narrative across all sources
  (136 dialogue trees in `dialogues.json`).
- The objective mix is courier-heavy: 19 `has_flag`, 14 `reach_system`, 3 `collect_cargo`, 2
  `talk_to_npc`, 1 `complete_trade`.
- Nothing consumes `act_one_complete` or `expanse_collapsed`. After "[End of Act One]" the player stays
  in the destroyed Expanse with every NPC alive (inferred from grep).
- Coherence breaks: the finale's `alliance_escort` node ("Everyone comes through") breaks the
  no-refugees canon; journal entry `auto_m17_horizon` reports "The factions are talking";
  `auto_m16_ledger` waits on a flag nothing sets; `data/ground/campaign/mission_16_pirate_base.json`
  is orphaned; Elena and Marcus narrate the finale even if never recruited; the last two finale options
  converge on the same node.
- No scenario test walks the critical path. Whether Act I can be finished is unverified.

### 1.4 Act II v1

The A2 arc (99 commits touching 97 files) was written into the Act I galaxy: 11 scar NPCs live at Act I
stations, 16 lens hooks fire on Act I actions with no act gate, Aldric Senn sits at `the_fulcrum`, and a
dilemma line references "before the Fulcrum burned" before it can have burned. All 16 capstones have
`cutscene_ref: null`, none of the 16 lens mini-games exist, and there is no Act II cast, galaxy, or act
gate. Untangling it would mean rewriting most of it in the engine being retired.

### 1.5 A live determinism bug

At least 14 seeding sites use Python's salted `hash()` (`procedural_missions.py:65`,
`lens_reactor.py:104`, 11 sites in `game.py`, `enemy_build_generator.py:142`), so bounties, customs,
enemy seeds, and procedural missions differ on every launch. `PYTHONHASHSEED` is set nowhere. Section
9.3 fixes it as a precondition of the port.

---

## 2. Vision and pillars

**North star.** You are a captain aboard a ship in a place, and every screen is a window from where
you stand.

**Pillars.**
1. **The ship is one design system** (Section 3).
2. **Space is a place** (Section 4).
3. **Stations are places, and panels open in place** (Section 6).
4. **Every activity is a career** (Section 7).
5. **Act I builds what Act II destroys** (Section 8).

**Standing creative bar.** Freedom of choice that the universe rewards, clear and rewarding play, a
universe that feels vast and alive with the player a piece of it, characters who feel human, writing
that feels real, originality over tropes, and breadth with depth.

**Touchstones.**
- Armored Core (AC6 above all): the garage, parts, stagger, the mercenary economy.
- Starfield: ship parts, shipyards, power allocation, system targeting, boarding, landing.
- Darkest Dungeon, Into the Breach, Chrono Trigger: turn-based fights that feel like fights.
- Sunless Sea and Citizen Sleeper: ports and stations as written places.
- The Last Night, Blasphemous, Eastward: high-res pixel art under modern light.
- Dead Cells: 3D models rendered into pixel art.
- FTL and Cosmoteer: parts you can shoot off.

---

## 3. The Ship

### 3.1 Retired and kept

**Retired, not ported:** the pixel-canvas builder (56 shapes, 16 per-pixel materials, placed pixels),
pixel physics (`ship_physics.py`: center of mass, articulation points, frontal profile), and the numpy
compositor (`engine/ship_composite.py`). About 2,600 lines leave the port.

**Kept and re-mapped into the new model:** the stat content of 170 parts, 144 modules, and 24 ship
types; the manufacturers and their identities; the five elements; and per-part combat state (module HP,
disable effects, detachment, from `module_combat.py` and `enemy_subsystems.py`).

### 3.2 Frame plus parts in slots

The Armored Core structure, translated to ships. The Ship sub-spec finalizes the slot set.

| Slot | AC analog | Governs |
|---|---|---|
| **Frame** (hull) | Core and legs | Silhouette, weight class, load limit, which sockets exist |
| **Bridge** | Head | Sensors, crew capacity, scan range on the map |
| **Reactor** | Generator | Energy pool and regen; its output is the energy-load gauge and the power pips (3.8) |
| **Drive** | Booster | Initiative and evasion in the fight; speed and fuel on the map |
| **Fire control** | FCS | Accuracy, lock-on, crits |
| **Weapons** (main and auxiliary hardpoints) | Arm and back units | The player's moves, each with its own firing animation and element effects |
| **Defense** | (none) | Shield projector or armor plating |
| **Bays** | (none) | Cargo pods, mining rig, salvage arm, drone bay, scanner suite, shielded hold, fabricator: the link to every career (7.2) |
| **Expansion** | Expansion | One signature ability |

### 3.3 The mounting standard

Every frame sprite exposes sockets. A socket is an anchor point, a facing, a size class, and a draw
layer. Every part carries the matching anchor, so any part of a size class fits any socket of that
class. Every part is drawn in one canonical view (5.1) with one light direction and one palette, drawn
once and used in the garage, the fight, and as the map token. This is what makes a mixed build look
built rather than pasted.

### 3.4 Part states

Each part has idle, active (firing, thrusting, charging), damaged, and destroyed or detached states.
Weapons also carry muzzle and projectile effects per element.

### 3.5 Variety

**Manufacturers are design languages.** The data already names seven: Reyes-Kowalski, Foundry,
Meridian, Sable, Salvage Rat, Talon, and Sung Dynamics. Each gets its own silhouette grammar, panel
language, materials, engine-glow color, weapon sound, and catalog voice. A Sable part reads as Sable at
a glance, and mixing makers is how a player builds something personal.

**Six axes on top of the makers:**
1. **Frames:** many silhouettes across weight classes and roles (courier, hauler, gunship, miner,
   salvager, explorer, yacht). Each frame's socket layout changes how the same parts arrange.
2. **Marks:** tiers that are visible. A Mk III drive looks like a Mk III drive.
3. **Surface:** liveries, decals, faction markings, an emblem editor, and wear states (factory-new,
   battle-worn, salvage-patched).
4. **Uniques:** parts won from bosses, found in salvage, or earned in the campaign, with their own art
   and behavior.
5. **Faction kits:** pirates field kitbashed Salvage Rat junk with mismatched parts; the Guild is
   corporate and uniform; the Union industrial; the Collective lab-sleek; the Frontier improvised.
   Enemies look like who they are.
6. **Act II makers:** a new galaxy brings its own manufacturers, and the player's Act I parts become
   the last of their kind.

**Opening bid for Act I:** about 24 frames (one per current ship type) and 250 or more parts across the
seven makers, plus faction and boss uniques. The Ship sub-spec sets the final counts.

### 3.6 The garage

The player's ship stands on a gantry in a hangar bay under work lights. Parts appear as manufacturer
catalog cards with stat bars and live deltas. Two Armored Core gauges govern every fit: weight against
the frame's load limit, and energy draw against the reactor's output. Schematics save and load.
Liveries, the emblem, and the ship's name live here. Parts are sold where they are made (3.8), so the
garage pulls the player across the map.

### 3.7 The test range

One button in the garage starts a no-stakes fight against a training drone with the current build. It
is the shortest loop from building to feeling.

### 3.8 Borrowed from Armored Core and Starfield

| Borrow | From | Becomes in Aurelia |
|---|---|---|
| Stagger (ACS) | AC6 | A stagger gauge per ship, filled by impact. A full gauge opens a punish window: a turn of heavy damage, a camera push, the big hit. Pairs with telegraphs: read the intent, pressure it, break it. |
| Load limits and energy load | AC | The garage's two gauges. Overweight costs initiative and evasion. |
| Defense by damage type | AC | Resistances per element (kinetic, plasma, ion, cryo, voltaic) on parts, so loadouts counter builds. |
| Charge, ammo, overheat | AC | Weapon personalities: a railgun that spends a turn charging, a cannon with finite ammo per sortie, a laser that overheats. |
| Payout minus costs | AC | Every fight ends in a debrief ledger: bounty or contract pay, minus ammo, minus repairs. |
| The Arena | AC | A ranked ladder of named rival captains with builds and emblems, likely hosted at Crimson Reach. |
| The handler on comms | AC6 | A crew member talks the player through fights: Elena calling shots, Marcus reporting damage. Builds on the existing combat interjections. |
| Manufacturer design languages | Both | Section 3.5. |
| Parts sold where they are made | Starfield | Foundry parts at Forgeworks. |
| Reactor power allocation | Starfield | Each turn the player splits the reactor's pips across weapons, shields, drive, and systems. The reactor fitted in the garage sets the pip count. |
| Targeting ship systems | Starfield | Module targeting: kill the drive and they cannot flee, kill the weapons and they cannot hurt you. |
| Disable, board, capture | Starfield | A disabled ship can be boarded through the away-team layer (7.3), then kept, sold, or stripped for parts. |
| Habs make the interior | Starfield | The ship's interior cutaway (6.2) is assembled from the installed bays. |
| Shielded cargo and contraband scans | Starfield | A shielded-hold part type, and a customs scan on arrival that can be seen coming. |
| Hails before fights | Starfield | Encounter scenes (4.3). |
| Skill-gated ship classes | Starfield | The skill trees gate heavier frames and reactor classes. |
| Scanning and landing sites | Starfield | Planets (7.3). |

**Not borrowed:** real-time piloting and dogfighting (D4), Starfield's disconnected travel between
space and ground, and Starfield's empty procedural planets.

### 3.9 Fight staging

Ships appear at scale, and weapons fire from their real hardpoints on the sprite. A hit lands on the
targeted module with hit-stop, a camera push, sparks, and scorch where it struck. A destroyed module
goes dark; a severed one breaks away. Enemy intent reads on the hull: a weapon glows before it fires.
Turns resolve fast, and animations can be sped up or skipped. The dual-tech cinematic framework, built
and never triggered, is finally wired. The fight happens under the sky of the system it happens in
(4.3). Enemies are built from the same kit; bosses get hand-authored builds and unique parts.

### 3.10 The build-to-fight contract

Every garage stat has a consequence the player can see in the fight: weight, reactor, drive, fire
control, hardpoints, defense, and part resistances. The Ship sub-spec maps each one exactly.

**The rule: if a stat has no visible consequence in the fight, it does not belong in the garage.**

### 3.11 Sequencing inside the Ship

The current combat engine is ported at parity first (Section 9.4). Stagger, power pips, ammo and heat,
and the boarding hook are added only after parity is green, so the reference traces can always tell a
porting bug from a design change.

---

## 4. Space and encounters

### 4.1 Two map scales, both alive, neither piloted

- **The Expanse:** the 12 systems linked by jump lanes.
- **Each system:** its star, planets, stations, belts, wrecks, and jump points in hi-res pixel art,
  with bodies moving in their orbits.

The player picks a destination and the ship flies itself there, compressed to a few seconds per leg.
Along the way the player can still act: change course, stop, scan, hail. A multi-leg route is one
order and stops only for real events.

### 4.2 A visible world

- **Traffic:** haulers, patrols, customs cutters, miners, and pirates on their own business, driven by
  the living-universe sim. The ore hauler on the lane is a real shipment that will move Forgeworks'
  prices.
- **Hazards:** debris fields, storms, radiation zones.
- **Territory:** faction control shown on the map.

### 4.3 Encounters are what travel plays like

- **They come from the world.** The hidden 0 / 20 / 40 percent roll is removed. A pirate picket sits
  on a lane because the lane is lucrative and patrols are thin. The player can read that danger and
  change it.
- **They can be seen coming.** Route around (costs time and fuel), wait it out, run dark (a threshold
  check under the deterministic rule), join a convoy, or meet it.
- **Meeting one opens a scene:** a pixel vignette of both ships with dialogue and choices: pay, bluff,
  trade, help, flee, or fight. The roughly 35K words of existing encounter writing is ported into this
  form.
- **Fights happen where the player is.** The camera moves from the map into the combat stage under the
  same system's sky. The generic arena and the fade are both removed.

### 4.4 Destinations inside a system

| Destination | Leads to |
|---|---|
| Station | Dock (Section 6) |
| Planet | Land (Section 7.3) |
| Belt | Mine (Prospector) |
| Wreck | Board and salvage (Salvager) |
| Beacon or anomaly | Story |

### 4.5 Jumps and time

Jumps are short, skippable cinematics at the system's edge, arriving under a new star. Travel costs
days and the map shows them passing: orbits turn, traffic moves on, news arrives. Markets and events
already run on the game-day clock.

### 4.6 The galaxy map as an instrument

Route planning, known prices with the age of that knowledge, rumors, faction territory, the player's
reputation and wake, and active missions.

### 4.7 System identity

Every system has its own star type and sky, planets, and traffic character: ore haulers at Forgeworks,
pirates around Crimson Reach.

---

## 5. Art and animation

### 5.1 Direction

- **High-res 2D pixel art:** dense, detailed pixel art lit with Godot 2D lights, normal maps, glow,
  and GPU particles.
- **Internal resolution 960x540**, scaled by whole numbers (2x at 1080p, 4x at 4K). Displays that are
  not an exact multiple (1440p, the Steam Deck's 1280x800) use a sharp-bilinear upscale shader. The art
  sub-spec confirms the resolution.
- **One canonical view for ship parts.** The bake-off chooses between a pure side profile (JRPG facing
  battles, simple sockets) and a three-quarter view (more depth, a stronger garage shot, harder
  sockets).
- **Pixel style bible v2** replaces the procedural-era aesthetic bible. It carries the canonical
  palette (65 percent conservative, 35 percent high contrast) forward and adds faction and manufacturer
  sub-palettes.

### 5.2 Two layers

The world renders in a pixel-perfect viewport. UI and text render in a native-resolution layer:
pixel-styled chrome and headings at whole-number scale, a clean readable face for prose and numbers,
and a player text-size setting. A text-heavy trading RPG cannot put dense prose and market tables
through a 960x540 viewport.

### 5.3 Who makes what

| Asset class | Pipeline |
|---|---|
| Frames, parts, props, commodity icons | **Claude-authored 3D.** Manufacturer kitbash libraries and part blockouts scripted in Blender's Python (`bpy`), rendered on a fixed camera and light rig, then a pixel pass: palette lock, outline, cluster cleanup. The rig also renders a normal pass, so every sprite ships with a normal map and Godot's 2D lights shade it under any star. |
| Shaders and VFX | **Claude-authored:** hull materials, engine glow, heat, damage and scorch, shield bubbles, jump distortion, animated skies, rotating planets, GPU particles per element. |
| UI chrome | **Claude-authored:** nine-slice frames per faction language, badges, glyphs. |
| Portraits | **Image model, then a pixel pass and cleanup.** Every NPC gets one. Principals get 3 to 5 expressions plus blink and talk frames. |
| Backdrops (station interiors, planet surfaces, key cutscene art) | **Image model concept, then a pixel pass**, with Blender blockouts wherever a layout must hold (the method that won Everember's Spike A). |
| Characters (station crowds, away teams) | **PixelLab or Blender renders**, decided by the bake-off. |

**Models.** The Everember hold does not apply to Aurelia. gpt-image-2.5 is the presumed default for the
image-model classes. The art sub-project opens with a validation cycle of the current models and
tools, because the field has moved since Everember's bake-offs, and records each class's winner with
its reason.

### 5.4 Animation

- **Ships:** turret sweeps and thruster frames rendered from Blender; recoil, hit-stop, shake, and part
  detachment as Godot tweens; glow and heat in shaders.
- **Portraits:** layered, with blink and mouth frames, expression swaps, and a subtle breathing idle.
- **Places:** idle loops for crowds, cranes, signs, and traffic. No station is ever still.
- **Cutscenes:** in engine, as timelines driving camera, lights, dialogue, and sprites. Painted key
  frames only where one image must carry the moment, such as the star collapsing.

### 5.5 Tooling and gates

- Everember's `tools/art` carries over: providers, provenance sidecars, manifest, contact sheets,
  re-render.
- New: the Blender render rig and the pixel pass.
- An automated palette-compliance check.
- Contact-sheet review with the author. Art ships as provisional until the author approves it.
- Spend caps are paired decisions.

### 5.6 Sound

Sound direction is part of the art sub-project: music that shifts by faction and system, a sound for
every verb, and the voice of each manufacturer's weapons. Sound work then runs through every
sub-project from the Ship onward.

---

## 6. Stations, the ship interior, and UI

### 6.1 The station is a place

Each station is a side-view cutaway in hi-res pixel art, split into a few districts: the market deck,
the shipyard and garage, the cantina, offices, and venues. The camera pans between districts. Crowds
move, cranes work, signs flicker, and NPCs stand where they live and work. The player clicks where to
go; there is no walking avatar, which keeps the click count down (the Stations sub-spec may revisit
this). Every station is its own place within its faction's language: Nexus Prime's Aurelia Core with
the colony ship's stamped hull plates, Forgeworks under the foundry glow.

### 6.2 The ship is the other place

A cutaway of the player's ship, assembled from the installed bays, reachable from anywhere. The crew
live in its rooms. Conversations, banter, and crew quest beats happen there. It is the one place that
survives into Act II, so it must be the most loved place in the game.

### 6.3 Panels open in place

The market, garage, missions, and dialogue open over the scene with the place visible behind them.
The scene changes only for undocking, jumping, fighting, or landing. A persistent dock bar holds the
station's services, which ends the hub, back, hub pattern. A pixel-chrome HUD always shows credits,
cargo, fuel, the date, and the current objective.

### 6.4 Dialogue

Portraits with expressions, and the speaker visible in the scene. Skill checks show their threshold
before the player chooses. The game never rolls behind the player's back.

### 6.5 Trading

One market panel with quick quantity gestures (drag, max, "sell what's profitable"), a price-history
sparkline per row, where each good sells best from the prices the player knows and the age of that
knowledge, the player's own market impact, and the manifest as a document to read. Refuel and repair
default to full, with the cost shown.

### 6.6 One input grammar

ESC, right-click, and the gamepad's B button always mean back. One confirm. Consistent hotkeys. Every
panel works on a gamepad. Every number has a tooltip that says why: the player always understands
what happened and why.

### 6.7 Onboarding

Everember's People and Guide kernel systems: a named dock boss at Nexus Prime gives orders, not
lessons, in the established tutorial voice. Services unlock as the story reaches them. The 14
first-time tip modals become in-place callouts. The first hour is storyboarded so that walls of text
disappear (an internal analysis counted five in the first 15 minutes).

### 6.8 Venues share one grammar

Auctions, disputes, research, and finance currently use four interaction styles. They move to one
table pattern: the participants, the stakes, the player's moves, the outcome. One grammar, four
flavors.

### 6.9 No dead ends

The Guild will always extend credit, at a price. Debt becomes a story engine and replaces the
stranded-player softlock (F-005).

---

## 7. Planets, activities, and the Career Charter

### 7.1 The Career Charter

Every activity is a career: a full mini-game with its own identity, easy to pick up and deep enough to
master. Every career sub-spec must satisfy all seven points before approval.

1. **Its own identity:** a faction home, its own verbs, visual language, sound, and voice. The
   proposed roster, confirmed by the sub-specs:

   | Career | Activity | Home |
   |---|---|---|
   | Merchant | Trading and the venues | Commerce Guild |
   | Mercenary | Bounties and the Arena | Crimson Reach |
   | Prospector | Mining | Miners Union |
   | Salvager | Boarding derelicts | Frontier Alliance |
   | Fabricator | The Forge | Science Collective |
   | Smuggler | Shielded holds, customs, dark lanes | (sub-spec decides) |
   | Surveyor | Planets, scanning, first landings | (sub-spec decides) |

2. **Easy to pick up:** a first session that pays off in minutes, rules readable on sight, opened by a
   supervisor who gives orders.
3. **Mastery in play, not only stats:** expert techniques, risk-and-reward decisions, and a
   performance rank per run. Skill beats grind.
4. **A career track:** ranks and titles, career contracts, a mentor, and gear (the bay parts). Each
   track ties into the skill trees.
5. **A narrative arc:** each career has its own story campaign (the Prospector's Road, the Wrecker's
   Log, and so on) that touches the main plot.
6. **Synergy where it is honest:** ore feeds the Forge, the Forge feeds the garage, salvage yields
   parts and evidence, the Merchant moves everything, the Mercenary protects and captures. Never
   mandatory: any career can carry a playthrough.
7. **One shell:** every career shares the UI grammar, the debrief ledger, and the reward language.

### 7.2 Bays are your career

The bay parts a player fits decide what work the ship can do. The build-to-fight contract extends to a
build-to-work contract: a better rig visibly mines better. The garage is the center of the whole game,
not only of combat.

### 7.3 Planets and the away-team layer

**Planets.** From orbit, the player scans to reveal points of interest, then chooses where to land. A
short descent cinematic plays. On the ground: a hi-res pixel map, top-down at a three-quarter angle,
with fog of war. Points of interest include ruins, outposts, crash sites, settlements with people in
them, deposits, and story sites. Every planet is curated: authored places carry it, and procedural
generation fills the gaps between them.

**One away-team layer.** The player and up to two or three crew move turn-based on a tile grid, with
cover, positioning, readable enemy intent, and each crew member's abilities. The same layer serves:
- planet exploration, replacing the current three-screen ground flow and its dice combat
- boarding derelicts: salvage becomes walking the decks, scanning rooms, reading the dead crew's logs,
  and managing breaches and power (the existing salvage logic maps onto room scanning)
- boarding disabled ships: the capture borrow (3.8)
- mission sites: the Iron Depths facility becomes a place walked through

### 7.4 Mining

The clicker is retired. At a belt, the rig works a pixel cross-section of the asteroid: the player
reads fracture lines and manages drill heat, and the rig's stats set the margins. Planet deposits use
the same system. The Prospector identity and its Union campaign stay as the content plan.

### 7.5 Refining

The Forge: the player's fabricator bay, or a station's foundry for bigger jobs. Recipe chains are
visible, profit is estimated at the prices the player knows, and discovered recipes are kept in a book.
Lighter than the other careers, as the corpus intended.

### 7.6 One economy

Credits plus materials. The per-mini-game upgrade currencies are removed. This supersedes the overhaul
corpus's three-tier currency discipline.

### 7.7 Careers feed the story

Missions run through careers: salvage the wreck for evidence, mine the ore the Ledger needs, forge the
access chip. Every career is a way into the plot.

---

## 8. The campaign

### 8.1 Act I builds what Act II destroys

- **People to miss.** Every station has recurring characters with small arcs, and NPCs remember what
  the player did. The world notices the player through news, titles, and greetings. Grief in Act II
  only lands if the Expanse was loved.
- **The conspiracy leaves a trace in the market.** Project Convergence needs sixteen lensing arrays,
  and that supply chain moves prices before anyone says "Ledger." Each career sees it through its own
  lens: odd ore orders for Prospectors, wrecks from array tests for Salvagers, rerouted cargo for
  Merchants and Smugglers. Players who read the traces can find the plot early, and the story
  acknowledges them when they do.
- **Missions use the careers and the ship**, replacing the courier-heavy objective mix.
- **The perpetrators are on stage.** Aldric Senn and the Ledger leadership are met in Act I and, per
  canon, escape.
- **A real finale choice:** what the player carries out through the gate, the evidence (truth) or the
  perpetrators' trail (vengeance). The collapse and the gate run are the game's signature in-engine
  set piece. Canon holds: only the crew and the perpetrators get out.
- **Deeper companions:** two-speaker banter (single-speaker only today), scenes aboard the ship,
  personal quests re-staged through careers and places, and loyalty that changes more than bonus
  multipliers.
- **Keepsakes:** music, recipes, and recordings collected into the Captain's Log, which writes itself
  in the player's voice. After the collapse it is the only surviving record of the Expanse, and the
  keepsakes are the last copies. The title pays off.
- **Coherence and pacing:** the fixes listed in 1.3, companion finale lines conditional on
  recruitment, `act_one_complete` consumed, a scenario test that walks the critical path, the first hour
  storyboarded, and the Station Anchors venues threaded into the story.

### 8.2 Act II

Designed only after Act I plays at quality (milestone M3).

- **A new galaxy, written fresh:** new cast, places, factions, manufacturers, culture guide, and voice
  sheets.
- **Isolation in grief is the texture.** The crew are the only people who remember. Everyone else
  reacts inadequately: disbelief, indifference, opportunism, collectors who want the keepsakes.
- **Truth against Vengeance is the spine.** The perpetrators are the only other witnesses, and killing
  them ends the only path to the truth.
- **Kept from Act II v1:** the dilemmas that permanently close options (and their eight texts, after a
  canon check), and ambition as identity, cut from 16 lenses to a few deep ambitions built on the
  careers ("rebuild from nothing" is a career story).
- **Systems travel:** every career, the garage, the map, and the fights.
- **A real ending:** authored endings shaped by the Truth or Vengeance choice and the player's
  ambition, with open play afterward. The Act II sub-spec decides the form.

---

## 9. Tech and port strategy

### 9.1 Repositories

A new Godot repo at `PycharmProjects\aurelia`, seeded from Everember (`fantasy-idler`): the gate script
(`tools/gate.py`), gdUnit4, gdformat and gdlint with `.gdlintrc`, warnings as errors, the pre-commit
installer, Godot MCP Pro, the art toolkit, and the sandbox launcher. `SpaceGame` stays as the reference
implementation and is frozen except for the work in 9.3. A sync tool copies `data/` across during the
port; after cutover the new repo owns the content. This document moves into the new repo when the
Foundation sub-project creates it.

### 9.2 Architecture

- **The simulation holds no nodes.** A `SimRoot` (RefCounted, signals) owns state. The day-ticked
  managers become `KernelSystem`s: markets, traffic, politics, galaxy events, news, investment.
- **Screens bind through signals, and every state change goes through a simulation method.** This
  closes the roughly 95 places where `game.py` (about 40) and the views (about 55) mutate the player
  directly.
- **`game.py` is replaced, not translated.** Its job moves to `SimRoot` plus one controller per place:
  map, station, garage, fight, planet.
- **Skills move from code (`create_default_skills()`) into JSON.**
- **Typed GDScript throughout, with a line cap per file.**
- **A sandbox per place and per activity** (`--sandbox nexus_prime`, `--sandbox combat:<id>`), each
  playable standalone.

### 9.3 Python work before porting

1. **One portable random generator** (PCG32 seeded from an md5 of the key string), injected
   everywhere. Fix the salted-`hash()` seeds (1.5) and the 37 unseeded global `random` calls (mining 12,
   salvage 9, events 7, others). Pin rounding and floor division with matching helpers on both sides:
   Python rounds half to even and GDScript rounds half away from zero; `//` floors while truncation
   does not, for negatives. The Python work re-baselines the affected tests.
2. **A trace recorder** that drives seeded scenarios (reusing the 684 scenario tests) and writes a
   `to_dict()` snapshot after each step as golden files.
3. **Act II switched off** at its hook sites so the reference behaves as Act I only, and the archive
   commit tagged (`act2-v1-archive`).

### 9.4 Parity

The Godot suite replays the same commands and compares snapshots; a regen tool refreshes the golden
files (Everember's `baseline_test.gd` and `regen_baselines.py` pattern). Loaders cast integers because
Godot parses every JSON number as a float. Each subsystem is ported at parity first and redesigned only
after its parity is green.

### 9.5 Port scope

**Ported:** the models (except as below), `data_loader` and its parsers, the combat engine and its
content, the narrative and flag systems, economy, galaxy, crew, progression, politics and events, and
the Station Anchors venues that are done.

**Not ported:** the pixel-canvas builder, ship physics, and the compositor (3.1); Act II v1's lens,
dilemma, capstone, and post-capstone modules (Appendix B); the old tutorial manager (replaced by the
Guide rails); old saves (a new versioned schema from day one, no import, per the alpha stance). For
activities being redesigned (mining, salvage, ground), each career sub-spec decides between port then
redesign and rebuild.

### 9.6 Tests

Parity traces cover what is ported, unit tests cover what is new, and a scenario test walks Act I's
critical path. Simulation tests stay out of the scene tree to keep the suite fast; gdUnit4 averages
about 55 ms per test in Everember.

### 9.7 Platforms and budget

Windows and Steam first; Linux comes with the engine. The Steam Deck is a target, so every screen is
designed for a gamepad from the start. Performance budget: 60 fps at 4K on the author's laptop.

---

## 10. Program roadmap

Each sub-project runs: paired brainstorm, sub-spec, plans, autonomous execution, paired playtest.

| # | Sub-project | Contents | Notes |
|---|---|---|---|
| SP1 | Art and sound direction | Model validation cycle; a bake-off on a Nexus Prime set (one dock district, one frame with six parts, one portrait, one sky); the canonical view; pixel bible v2; the Blender rig, pixel pass, and normal maps; sound direction | Parallel with SP2 |
| SP2 | Foundation | The Python work in 9.3; the new repo from Everember; `SimRoot` skeleton; data loader; parity harness; sandbox launcher | Parallel with SP1 |
| SP3 | Logic port | Wave A is what the slice needs: player, market and economy, galaxy, encounters, combat engine, dialogue, missions and flags, crew, progression. Wave B is the rest | Autonomous, alongside SP4 to SP6 |
| SP4 | The Ship | Parts model and mounting standard; re-map of the 314 parts and modules; garage and test range; combat staging at parity; then the extensions (stagger, power pips, ammo and heat, boarding hook) | Two or three plans |
| SP5 | Space | Two-scale living map, traffic from the sim, encounter ecology and scenes, jumps, the galaxy map as an instrument | |
| SP6 | Stations and UI | Station cutaways, panels in place, dock bar, HUD, dialogue, trading panel, input grammar, onboarding rails, ship interior, venue table, Guild credit | |
| SP7 | Nexus Prime slice (M1) | Garage and test range, a trade loop between Nexus Prime and one neighbor, a visible encounter, a fully staged fight, the dock boss, the first 30 minutes of Act I | A paired playtest decides go or no-go on the direction |
| SP8 | Careers | One sub-spec per career under the Charter. Merchant and Mercenary first; then the away-team layer built with the Salvager; then Surveyor, Prospector, Smuggler, Fabricator | |
| SP9 | Breadth | All 12 systems and their stations at full quality; port wave B | |
| SP10 | Act I | Campaign re-staging, companions, keepsakes, cutscenes, the collapse. M2: a public demo of the first two hours. M3: Act I complete, Python retired | |
| SP11 | Act II | Designed after M3. M4: the full game | |

**Milestones.** M0: this document approved. M1: the Nexus Prime slice at target quality. M2: the public
demo. M3: Act I complete in Godot. M4: the full game.

**Order of paired design sessions:** SP1 and SP2, then SP4, SP5, and SP6, while port wave A runs
autonomously.

**Sizing.** The port alone was estimated at 60 to 85 sprints before the new design existed; the Ship,
Space, careers, and planets add design work on top. No total is quoted here. Each sub-spec sizes
itself and this roadmap is updated as they land.

**The stranded Station Anchors sprints.** The 16 todo sprints blocked behind SA-F2 since 2026-09-01 are
not executed in Python. Their intent moves: the finance sprints to the Merchant career (SP8), the venue
interaction work to the venue table (SP6), and the cross-station threading (SA-X1, X5, X6, X8) to Act I
(SP10).

---

## 11. Process and canon rules

- **Paired and autonomous.** Design, spend caps, and the first push to any new remote are paired with
  the author. Plans run autonomously on the Everember runbook: subagent-driven development, a review on
  every task, a final review, the full gate, then a merge. Implementers commit as soon as their tests
  pass, so a reboot cannot cost work. Ralph retires.
- **Parity first, then extend.** No subsystem is redesigned while its port is being verified.
- **Wire it or delete it.** Nothing merges without a call site and a test proving it is wired.
- **The canon scanner.** Every place, character, faction, and manufacturer is tagged with its galaxy. A
  compliance test fails on any Act II reference to Act I cast or places, apart from an explicit
  allowlist: the crew (Elena Reeves, Marcus Jin, Dr. Priya Osei, Tomas Drifter), the perpetrators
  (Aldric Senn and the Ledger leadership), and the keepsakes.
- **Writing gates carry over:** the em-dash, banned-name, and "no X, no Y" checks, and the writing
  bible.
- **Findings get fixed or ruled on.** Every playtest finding is fixed in the next slice or deferred by
  an explicit ruling in a findings register. None are routed to a spec that does not exist yet.
- **Art provenance.** Every generated asset carries a sidecar and stays provisional until the author
  approves it on a contact sheet.
- **A line cap per file**, so no new god objects grow.

---

## 12. Open items handed to sub-specs

| Item | Owner |
|---|---|
| Canonical part view: side profile or three-quarter | SP1 |
| Internal resolution confirmation (960x540 proposed) | SP1 |
| Per-class model and tool winners after the validation cycle | SP1 |
| Final slot set, stat mapping for the build-to-fight contract, part and frame counts | SP4 |
| Stagger, power pip, and ammo tuning | SP4 |
| Whether stations ever get a walking avatar | SP6 |
| Career roster confirmation, and homes for the Smuggler and Surveyor | SP8 |
| Port then redesign, or rebuild, for mining, salvage, and ground | SP8 career sub-specs |
| Whether SA-F2's partial futures implementation is ported | SP8 (Merchant) |
| Act II's galaxy count and ending form | SP11 |

---

## Appendix A: Retired and not ported

- Pixel-canvas builder: `models/ship_build.py` (1,077 lines) and its shape, material, and placed-pixel
  data (`data/ships/shapes.json`, `materials.json`, `module_materials.json`, the pixel masks in
  `modules.json`).
- Pixel physics: `models/ship_physics.py` (368 lines).
- The numpy compositor: `engine/ship_composite.py` (1,190 lines).
- Act II v1 modules and data (Appendix B).
- The old tutorial manager (`tutorial_manager.py`), replaced by the Guide rails.
- Every pygame view and the pygame engine layer.

## Appendix B: Act II v1, kept as source material

Tagged `act2-v1-archive` in SP2. Not ported as code or content.

**Kept for the Act II sub-spec to draw on:**
- Spec F (`2026-08-27-act-two-ambition-design.md`): dilemmas with permanent closure; ambition as
  identity; the "world moves without the player" principle.
- The eight dilemma texts and their companion telegraph lines, after a canon check.
- The Truth against Vengeance tension and the perpetrators-as-only-witnesses insight.

**Discarded:** the 16-lens breadth, the 11 scar NPCs placed at Act I stations, the lens hooks on Act I
actions, and the post-capstone templates.

## Appendix C: The overhaul corpus's role now

`requirements/overhaul/` (17 documents) becomes reference input, not binding design:
- `10_programmatic_generation_framework.md` and `11_pygame_capability_audit.md` are superseded by the
  engine change.
- `20_aesthetic_bible.md` is superseded by the pixel style bible v2; its palette and identity
  architecture (Bible section 10) carry forward.
- `30` to `38` (per-system overhauls) are inputs to the matching sub-specs: their touchstones,
  problem statements, and content budgets are useful; their pygame implementation plans are not.
- `40` to `42` (audio, VFX, UI chrome) are inputs to SP1 and SP6.

## Appendix D: Evidence sources

The three surveys of 2026-09-25 read, among others: `spacegame/config.py` (GameState),
`spacegame/engine/game.py`, `spacegame/views/`, `data/economy/balance.json`, `data/missions/missions.json`,
`data/dialogue/dialogues.json`, `data/ships/*.json`, `requirements/playtest_roadmap.md`,
`requirements/findings_register.md`, `requirements/roadmap/ROADMAP.md`, `STATUS.md`,
`requirements/overhaul/*`, `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md`, and
Everember's `tools/gate.py`, `core/sim_root.gd`, `test/sim/baseline_test.gd`, and `tools/art/`. Line
counts were taken with PowerShell and Python one-liners; test counts with `rg "def test_"`.
