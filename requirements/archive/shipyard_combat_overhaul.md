# Shipyard & Combat Overhaul -- Follow-Up Roadmap

Post-implementation review document for the Per-Frame Requirements system
and Combat system deep review. Items below are recommended improvements
discovered during the review pass (2026-03-27).

---

## Shipyard Follow-Up Items

### S-1: Undersized Slot Tooltip
When a player hovers over a dimmed slot in the drydock palette, show why
it's dimmed (e.g., "This frame requires medium+ engines"). Currently it
just appears grayed out with no explanation.

### S-2: Frame Comparison Delta in Shop
Show a delta comparison between the player's current frame_requirements
and the prospective frame, similar to stat deltas. Example:
"Weapon: +2 max, Utility: -1 max."

### S-3: Min Count Display in Drydock
The requirements checklist shows `count/max` but doesn't explicitly show
the minimum in the number column. Consider `2/2-5` (count/min-max) for
required infrastructure slots, so the player understands what the
checkmark threshold represents.

### S-4: Rejection Feedback Differentiation
When a slot placement is rejected for min_size violation vs overlap vs
weight, use distinct rejection sounds and/or message colors to help the
player understand what went wrong.

### S-5: Per-Frame Total Slot Cap
Currently all large ships share the same max_slots=14 budget. Consider
whether frame_requirements should also specify a total slot cap per
frame to further differentiate combat vs trade frames.

### S-6: XLarge Ship Data
No ships currently use xlarge weight class. The infrastructure template
is ready in _INFRA_MINS but untested with real ship data. Needed for
capital ships in Campaign Act Two or Fleet Management.

---

## Combat Bugs Fixed (This Pass)

### CB-1: Tutorial Overlay Blocking Combat Input (FIXED)
**Root cause**: Combat tutorial hints (e.g., "combat_defensive_identity")
triggered during the INTRO phase (0.8s dark screen). The hint panel
appeared on top of an already-dark screen, confusing or invisible to
the player. While the overlay was active, game.py's event loop consumed
all events before they reached combat_view (line 4514 `continue`).

**Three fixes applied:**
1. `tutorial_overlay.show()` now validates `get_current_step()` before
   setting `active=True` -- prevents invisible overlay from step mode.
2. `tutorial_overlay.render()` auto-hides if active but nothing to
   display (hint_data=None or no valid step) -- safety net.
3. `game.py _check_tutorial_triggers()` now gates combat hints behind
   `CombatPhase.PLAYER_INPUT` -- hints only appear after the intro
   banner completes and the player can interact.

**Tests**: 7 new tests in `tests/test_views/test_tutorial_overlay.py`.

### CB-2: War Frigate Description Mismatch (FIXED)
Description said "Four weapon slots and three defense slots" but actual
data was weapon_slots=5, defense_slots=4. Updated to match.

---

## Combat Follow-Up Items

### C-1: Combat Hint Timing Polish
Combat hints currently trigger on the first frame of PLAYER_INPUT. This
means the player sees a hint overlay before they've had a chance to look
at the combat arena. Consider adding a 1-2 second delay after INTRO
completes before showing the first combat hint.

### C-2: No-Weapon Build Edge Case
If a player enters combat with zero equipment moves (no weapons installed
in any slot), they can only use crew moves and special actions. This is
technically valid but confusing. Consider:
- Warning in the drydock if confirming a build with no weapons
- Fallback "Basic Attack" move for weaponless ships
- Tutorial hint explaining the situation

### C-3: Combat Log Visibility During Queue Phase
When the action queue panel is visible (PLAYER_INPUT), the combat log is
hidden. Players lose context of what happened last round. Consider a
compact "last round summary" at the top of the queue panel or a toggle.

### C-4: Module-Targeted Damage Feedback
Module damage is calculated and applied, but the visual feedback for
which specific module was hit is subtle. Consider:
- Flash the hit module's pixel region on the ship sprite
- Show module name in the floating damage text ("Engine hit! -12 HP")
- Color-code damage by module type

### C-5: Defensive Identity Passive Feedback
Ghost counterstrike stacks, Sentinel shield regen, and Juggernaut armor
reduction are all passive effects that happen silently. Consider adding
subtle visual indicators when these activate:
- Ghost: brief afterimage on dodge
- Sentinel: shield shimmer on regen tick
- Juggernaut: armor flash on damage reduction

### C-6: Enemy AI Behavior Variety
The four AI behaviors (aggressive, defensive, evasive, cowardly) are
well-implemented but enemies within the same behavior type always act
identically. Consider:
- Per-enemy personality variance (some aggressive enemies target weakest
  module, others target highest-threat module)
- Adaptive behavior shifts (defensive enemies that become aggressive
  when player is low HP)
- Boss phase-specific flavor text for move selection

### C-7: Elemental Synergy Feedback
Elemental effects (Burn, Chill, Suppressed) stack and interact, but the
player may not understand the synergies. Consider:
- Tooltip on enemy status effects showing stack count and effect
- Visual distinction between 1-stack and 3-stack (Frozen) Chill
- Combo notification when Frozen + Burn interact

### C-8: Combat Escape/Flee Polish
The flee mechanic exists but success/failure feedback is minimal.
Consider:
- Flee attempt animation (ship turning, engines flaring)
- Failure consequence feedback ("Engines blocked! Lost your turn.")
- Speed stat influence on flee chance (shown in tooltip)

### C-9: Action Queue UX
The multi-action queue system allows queuing several attacks per turn.
Potential improvements:
- Drag to reorder queued actions
- Preview total damage/energy cost before executing
- Undo individual actions (not just clear all)

### C-10: Post-Combat Summary
The COMBAT_OVER screen shows results but could be richer:
- Module damage report (which modules were damaged/disabled)
- Elemental effect summary (total burn damage dealt, etc.)
- XP breakdown (base + bonus from overkill, boss, etc.)

---

---

## Combat Action System Overhaul (CRITICAL)

These issues were discovered during playtesting with a fully-equipped
large ship (6 utility + 3 defense + 2 weapon = 11 combat moves).

### CA-1: Scrollable/Categorized Action Panel
**Problem**: The 2x2 grid action panel maxes at 4 visible moves. A
player with 11+ combat moves can only see 4 at a time with no scroll
or pagination. Weapons may be completely hidden.

**Design Options**:
- **Option A (FF-style categories)**: Replace flat grid with category
  tabs: ATTACK | DEFEND | UTILITY. Each tab shows only its moves.
  Player clicks tab, then selects move. Familiar RPG pattern.
- **Option B (Scrollable list)**: Keep flat grid but add vertical
  scroll with mouse wheel. Simple but less organized.
- **Option C (Compact list)**: Replace 2-column grid with single-column
  list (smaller buttons, more rows visible). Add scroll if needed.

**Recommendation**: Option A. It scales cleanly to any loadout size,
gives clear tactical categories, and matches the genre convention.
Implementation: filter `equipment_moves` by slot_type when rendering
the action panel, with 3 tab buttons above the move grid.

### CA-2: Per-Slot Individual Cooldowns
**Problem**: Using one Phantom Cloak puts ALL 6 on cooldown because
cooldowns are tracked by `move.id` (not by slot index). All copies of
the same part share one cooldown.

**Root cause**: `ActionQueue` tracks `cooldowns: dict[str, int]` keyed
by move ID. All 6 Phantom Cloaks have `id="phantom_cloak"`, so using
one sets `cooldowns["phantom_cloak"] = 3`, blocking all 6.

**Fix**: Change cooldown tracking to use `{move_id}_{slot_idx}` as the
key. Each placed slot gets its own independent cooldown. This means
6 Phantom Cloaks can be used in rotation (use 1, wait, use next).

**Impact**: Major gameplay change — duplicate equipment becomes
strategically meaningful instead of wasteful. Need to also update:
- `_build_move_buttons()` in combat_view.py (one button per slot, not
  per move name)
- `ActionQueue.add()` validation (once-per-slot-per-turn, not once-per-
  move-per-turn)
- Cooldown display on buttons
- The action queue panel (show slot index in queued action)

### CA-3: Enemy Sprite Orientation
**Problem**: Some enemy ships face the wrong direction (UP instead of
LEFT). This is a per-sprite issue from generation — the prompt said
"facing LEFT" but the AI produced upward-facing ships.

**Fix**: For sprites that face wrong, apply a 90-degree rotation in
post-processing, or regenerate with stronger orientation language.
Could also add a per-template `rotation_offset` field to apply at
load time.

---

## Priority Ordering

**Critical** (blocks gameplay):
- CA-1: Action panel categorization/scrolling
- CA-2: Per-slot individual cooldowns

**High** (improve core UX):
- CA-3: Enemy sprite orientation fix
- C-1: Combat hint timing delay
- C-2: No-weapon build warning
- S-1: Undersized slot tooltip
- S-3: Min count display in drydock

**Medium** (deepen engagement):
- C-4: Module-targeted damage feedback
- C-5: Defensive identity passive feedback
- C-9: Action queue UX
- S-2: Frame comparison delta in shop
- S-4: Rejection feedback differentiation

**Low** (nice to have):
- C-3: Combat log during queue phase
- C-6: Enemy AI behavior variety
- C-7: Elemental synergy feedback
- C-8: Flee polish
- C-10: Post-combat summary
- S-5: Per-frame total slot cap
- S-6: XLarge ship data

---

## Major Feature: Enemy Ship Builds (Build-Based Enemy Ships)

**Vision**: Replace sprite-sheet-based enemy ships with ShipBuild-based
composites, making enemy ships follow the same pixel-hull + placed-slot
system as the player's ship. The ship builder becomes the universal ship
design tool for both player and AI ships.

### Why
- Visual consistency: enemies render as composite ships, not flat sprites
  or triangle fallbacks
- Gameplay depth: module-targeted damage becomes meaningful for enemies
  (disable their engines, weapons, reactors)
- Content pipeline: new enemies can be authored as ShipBuild presets
  instead of requiring hand-drawn sprite sheets
- Foundation for fleet management: captured/salvaged ships use the same
  system

### Phases

**Phase E-1: Enemy ShipBuild Presets**
- Add `ship_build` field to EnemyShipTemplate (JSON + model)
- Create a `generate_enemy_preset()` function similar to
  `generate_preset_from_ship_type()` that produces ShipBuild from
  enemy template stats (hull, shields, weapon_count, etc.)
- Each enemy template gets a deterministic preset build generated from
  its stats + a seed derived from the template ID
- Store as cached ShipComposite surfaces (generated once on load)

**Phase E-2: Enemy Composite Rendering in Combat**
- Combat view renders enemy ships via ShipComposite instead of sprite
  sheets, falling back to the preset-generated build
- Enemy ship scale based on danger_tier (low=small, moderate=medium,
  dangerous=large, boss=xlarge)
- Slot indicators visible on enemy ships (shows the player what modules
  the enemy has)

**Phase E-3: Enemy Module-Targeted Damage**
- Enemy ships have module_states derived from their ShipBuild
- Player attacks can target/disable enemy modules (currently only player
  modules are targetable)
- Disabling an enemy engine reduces their speed/evasion
- Disabling an enemy weapon removes that combat move
- Visual feedback: damaged enemy modules flash/darken on sprite

**Phase E-4: Data Migration**
- Convert existing EnemyShipTemplate data to include weight_class and
  slot counts, or generate them from existing stats
- Retire sprite sheet pipeline for enemies (keep as optional override
  for hand-crafted boss visuals)
- Update encounter system to work with build-based enemies

### Dependencies
- Requires stable ShipBuild + PlacedSlot + ShipComposite pipeline (done)
- Requires FrameRequirements system (done)
- Benefits from per-frame slot limits for enemy balance
