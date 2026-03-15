# R2: Ships, Upgrades & Enhancement System

## Design Philosophy

Every ship should feel like a **statement of intent**. When a player docks at Nexus Prime in a War Frigate, other captains know what they're about. When someone rolls up in an Institute Vessel, you know they earned that reputation. The upgrade enhancement system turns generic parts into *your* parts — two players with the same Laser Cannon can have completely different builds.

**Core Principles:**
- Ships define your role; upgrades define your style within that role
- Every tier offers a meaningful fork — no "strictly better" ships, only trade-offs
- Enhancement rewards investment without requiring more slots
- Faction and quest gates create aspirational goals, not gatekeeping

---

## Part 1: Ship Roster (9 → 24 ships)

### Tier Philosophy

| Tier | Count | Purpose |
|------|-------|---------|
| Starter | 1 | Everyone starts here. No choice, just survival. |
| Early Game | 3 | **The First Fork.** Trade, combat, or resource gathering. |
| Mid Game | 8 | **Identity crystallizes.** Each path has 2+ options with distinct trade-offs. |
| Late Game | 8 | **Ultimate expression.** Capstone ships that reward deep commitment. |
| Faction | 4 | **Prestige ships.** Reputation-gated, unique abilities, aspirational. |

### Starter (1)

| ID | Name | Cargo | Fuel | Hull | Shields | W/D/U | Speed | Price | Identity |
|----|------|-------|------|------|---------|-------|-------|-------|----------|
| shuttle | Shuttle | 50 | 100 | 60 | 20 | 1/0/2 | 1.0x | 5,000 | Your tin can. Survive. |

### Early Game (3) — The First Fork

| ID | Name | Cargo | Fuel | Hull | Shields | W/D/U | Speed | Price | Identity |
|----|------|-------|------|------|---------|-------|-------|-------|----------|
| light_freighter | Light Freighter | 150 | 150 | 100 | 40 | 1/1/3 | 1.0x | 25,000 | Trade path. Reliable workhorse. |
| prospector | **Prospector** | 80 | 180 | 80 | 25 | 0/1/4 | 1.0x | 22,000 | Resource path. Extra utility for mining/salvage gear. |
| patrol_cutter | **Patrol Cutter** | 60 | 140 | 110 | 45 | 2/1/2 | 1.2x | 28,000 | Combat path. Punches above its weight. |

**Design notes:**
- Prospector has 4 utility slots (most at this tier) but 0 weapon slots — must avoid fights or rely on crew/evasion
- Patrol Cutter has 2 weapon slots early — a real combat advantage, but tiny cargo means combat must be the income source
- Light Freighter remains the safe, balanced choice

### Mid Game (8) — Identity Crystallizes

| ID | Name | Cargo | Fuel | Hull | Shields | W/D/U | Speed | Price | Identity |
|----|------|-------|------|------|---------|-------|-------|-------|----------|
| medium_freighter | Medium Freighter | 300 | 200 | 150 | 60 | 1/2/3 | 0.9x | 100,000 | Bulk trade. Serious cargo capacity. |
| fast_courier | Fast Courier | 100 | 250 | 80 | 30 | 2/1/2 | 2.0x | 150,000 | Speed demon. Luxury goods runner. |
| armed_trader | Armed Trader | 120 | 180 | 130 | 50 | 2/2/2 | 1.0x | 85,000 | Fight-and-trade hybrid. |
| scout_vessel | Scout Vessel | 60 | 300 | 70 | 35 | 1/1/4 | 1.5x | 65,000 | Explorer. Sees everything, carries little. |
| corsair | **Corsair** | 40 | 200 | 140 | 55 | 3/1/2 | 1.3x | 120,000 | Combat raider. 3 weapon slots. Tiny hold — you fight for your income. |
| mining_barge | **Mining Barge** | 200 | 160 | 180 | 40 | 0/2/5 | 0.7x | 90,000 | Mining specialist. 5 utility slots, 0 weapons, very slow. |
| smugglers_sloop | **Smuggler's Sloop** | 100 | 220 | 75 | 30 | 1/1/3 | 1.8x | 110,000 | Fast and sneaky. Built-in `hidden_compartment`. |
| salvage_rig | **Salvage Rig** | 180 | 170 | 160 | 35 | 1/1/4 | 0.8x | 80,000 | Salvage specialist. Built-in `salvage_bonus`. Sturdy. |

**Design notes:**
- Corsair is the pure combat ship — 3 weapon slots is unmatched at this tier, but 40 cargo means you MUST fight to earn
- Mining Barge's 5 utility slots + 0 weapon slots creates total commitment to the resource path
- Smuggler's Sloop starts with hidden_compartment ability — it's designed for the Smuggling tree
- Salvage Rig gets built-in salvage yield bonus — pairs perfectly with Exploration tree's salvage_instinct skill

### Late Game (8) — Ultimate Expression

| ID | Name | Cargo | Fuel | Hull | Shields | W/D/U | Speed | Price | Identity |
|----|------|-------|------|------|---------|-------|-------|-------|----------|
| bulk_hauler | Bulk Hauler | 600 | 300 | 250 | 80 | 2/2/4 | 0.7x | 400,000 | Max cargo. Trading empire flagship. |
| luxury_yacht | Luxury Yacht | 200 | 400 | 120 | 100 | 1/3/3 | 1.5x | 600,000 | Diplomacy/social. Crew paradise. |
| clipper | Clipper | 150 | 350 | 90 | 45 | 2/1/3 | 2.0x | 350,000 | Speed + stealth hybrid. |
| war_frigate | **War Frigate** | 60 | 250 | 280 | 120 | 4/3/2 | 0.9x | 500,000 | Dedicated warship. 4 weapon + 3 defense. Combat tree capstone. |
| deep_explorer | **Deep Explorer** | 100 | 500 | 100 | 60 | 1/2/5 | 1.3x | 450,000 | Maximum range. 500 fuel, 5 utility. Sees everything. |
| phantom | **Phantom** | 120 | 300 | 70 | 35 | 2/1/4 | 2.2x | 550,000 | Ultimate smuggler. Max evasion, built-in `ghost_mode`, `hidden_compartment`. |
| industrial_titan | **Industrial Titan** | 250 | 200 | 300 | 60 | 0/3/6 | 0.5x | 480,000 | Mining/refining mega-ship. 6 utility, 0 weapons. Built-in `refining_bonus`. |
| diplomatic_cruiser | **Diplomatic Cruiser** | 150 | 350 | 180 | 90 | 1/3/4 | 1.0x | 520,000 | Faction influence ship. Built-in `diplomatic_access`, `rep_bonus`. 6 crew slots. |

**Design notes:**
- War Frigate: 4W/3D is the most combat-oriented loadout in the game — a flying arsenal
- Deep Explorer: 500 fuel + 5 utility = reach anywhere, scan everything, carry almost nothing
- Phantom: Fastest ship (2.2x), maximum evasion, but paper-thin hull — glass cannon runner
- Industrial Titan: 6 utility slots, 0 weapons, slowest in game — total commitment to resource empire
- Diplomatic Cruiser: 6 crew slots, rep bonus, diplomatic access — the Leadership/Social tree dream

### Faction Ships (4) — Reputation-Gated

Require **Allied reputation (50+)** with the corresponding faction. Only purchasable at that faction's stations.

| ID | Name | Faction | Cargo | Fuel | Hull | Shields | W/D/U | Speed | Price | Unique Ability |
|----|------|---------|-------|------|------|---------|-------|-------|-------|----------------|
| consortium_merchantman | Consortium Merchantman | Nexus Trade Consortium | 350 | 300 | 180 | 70 | 2/2/4 | 1.1x | 700,000 | `tariff_immunity` — zero tariffs everywhere |
| syndicate_enforcer | Syndicate Enforcer | Forgeworks Industrial | 100 | 250 | 250 | 100 | 3/3/3 | 1.0x | 650,000 | `hull_regen` — repairs 5 hull per turn in combat |
| frontier_runner | Frontier Runner | Free Salvagers Union | 130 | 350 | 90 | 50 | 2/1/4 | 2.0x | 580,000 | `salvage_mastery` — double salvage yields |
| institute_vessel | Institute Vessel | Axiom Research | 80 | 400 | 110 | 130 | 1/2/5 | 1.2x | 720,000 | `quantum_sensors` — full system intel at any range |

**Design notes:**
- These are aspirational goals, not mandatory progression
- Each has a powerful unique ability that stacks with skill tree bonuses
- Price is steep — you're paying for prestige AND power
- Must travel to the faction's home system to purchase

---

## Part 2: Upgrade Enhancement System

### The Mark System

Every upgrade can be enhanced from **Mk1** (base) to **Mk3** (mastered). Enhancement happens at the shipyard on already-installed upgrades.

| Mark | Effect | Cost | Requirement |
|------|--------|------|-------------|
| Mk1 | Base stats | Purchase price | — |
| Mk2 | +25% effectiveness, pick tuning | 100% of base price + commodity | Mk1 installed |
| Mk3 | +50% effectiveness, tuning intensifies | 200% of base price + rare commodity | Mk2 installed |

**Enhancement costs scale with the upgrade's base price:**
- Mk2: `base_price × 1.0` credits + 3 units of a common commodity (varies by upgrade type)
- Mk3: `base_price × 2.0` credits + 2 units of a rare commodity (varies by upgrade type)

**Commodity requirements by upgrade slot type:**
| Slot Type | Mk2 Commodity | Mk3 Commodity |
|-----------|---------------|---------------|
| weapon | common_metals × 3 | alloy_composite × 2 |
| defense | iron_ore × 3 | alloy_composite × 2 |
| cargo/fuel | textiles × 3 | manufactured_goods × 2 |
| engine | fuel × 3 | purified_crystal × 2 |
| mining | raw_ore × 3 | rare_metals × 2 |
| scanner | electronics × 3 | purified_crystal × 2 |
| smuggling | scrap_metal × 3 | rare_parts × 2 |

### The Tuning System

At Mk2, the player **chooses one of two tuning specializations** that adds a secondary bonus. This choice defines the upgrade's personality and stacks with the mark bonus.

At Mk3, the tuning effect **doubles** (no new choice — the Mk2 decision carries forward).

**Example tunings for selected upgrades:**

#### Laser Cannon (weapon, base: 18 dmg)
- **"Overcharged"**: +4 damage (Mk3: +8) — raw damage build
- **"Precision"**: +15 accuracy (Mk3: +30) — never-miss sniper build

#### Cargo Bay Extension (utility, base: +20 cargo)
- **"Reinforced"**: +10 hull HP (Mk3: +20) — your cargo bay doubles as armor
- **"Optimized"**: +5 cargo (Mk3: +10) — pure efficiency, +30 total at Mk3

#### Basic Shield Generator (defense, base: 20 shield restore)
- **"Rapid Cycle"**: -1 energy cost (Mk3: -1 energy, minimum 1) — spam shields cheaply
- **"Overcharge"**: +10 restore (Mk3: +20) — big shield dumps

#### Mining Drill Mk2 (utility, base: 20% drill speed)
- **"Deep Core"**: +15% rare ore chance (Mk3: +30%) — quality over speed
- **"Rapid Extract"**: +10% additional drill speed (Mk3: +20%) — speed over quality

#### Hidden Compartment (smuggling, base: 30% hidden cargo)
- **"Ghost Lining"**: -5% scan detection (Mk3: -10%) — harder to detect
- **"Expanded"**: +10% hidden cargo (Mk3: +20%) — hide more stuff

### How Enhancement Affects Stats

For **numeric bonus upgrades** (cargo_bonus, fuel_bonus, etc.):
```
effective_value = base_value × mark_multiplier + tuning_bonus
```
Where mark_multiplier is: Mk1=1.0, Mk2=1.25, Mk3=1.50

For **combat move upgrades** (weapons, defenses):
```
effective_damage = base_damage × mark_multiplier
effective_accuracy = base_accuracy + tuning_accuracy_bonus
```

### Data Model: InstalledUpgrade

```python
@dataclass
class InstalledUpgrade:
    """An upgrade instance installed on a ship, with enhancement state."""
    upgrade_id: str  # Reference to base ShipUpgrade definition
    mark: int = 1  # Enhancement level (1-3)
    tuning: Optional[str] = None  # Tuning choice ID (set at Mk2)
```

Serialization stores `{upgrade_id, mark, tuning}` per installed item.
On load, the base ShipUpgrade is resolved from the data loader.

---

## Part 3: New Upgrades (24 → ~42)

### New Utility Upgrades (7)

| ID | Name | Slot | Bonus Type | Value | Price | Tunings |
|----|------|------|-----------|-------|-------|---------|
| nav_computer | Navigation Computer | engine | fuel_efficiency_bonus | 3 | 12,000 | "Predictive" (+1 fuel eff) / "Adaptive" (+5% travel speed) |
| tractor_beam | Tractor Beam | scanner | salvage_yield_bonus | 0.20 | 10,000 | "Wide Field" (+10% yield) / "Precise" (+1 scan charge) |
| refining_module | Refining Module | mining | refining_yield_bonus | 0.15 | 14,000 | "Catalyst" (+10% yield) / "Speed" (-15% refine time) |
| crew_quarters | Crew Quarters Expansion | cargo | crew_slot_bonus | 1 | 20,000 | "Comfort" (+5 loyalty) / "Training" (+1 crew XP/event) |
| sensor_array | Long-Range Sensor Array | scanner | map_reveal_bonus | 1 | 15,000 | "Deep Scan" (+1 range) / "Threat Detection" (-10% ambush chance) |
| cargo_compressor | Cargo Compressor | cargo | cargo_bonus | 35 | 18,000 | "Industrial" (+15 cargo) / "Shielded" (+15 hull) |
| hull_reinforcement | Hull Reinforcement | engine | hull_bonus | 25 | 16,000 | "Ablative" (+10% dmg reduction in combat) / "Dense" (+15 hull) |

### New Weapons (3)

| ID | Name | Price | Damage | Energy | Special | Tunings |
|----|------|-------|--------|--------|---------|---------|
| autocannon | Autocannon | 7,000 | 10 | 2 | +15 accuracy, no cooldown | "Burst Fire" (+5 dmg) / "Tracer" (+10 acc) |
| rail_gun | Rail Gun | 25,000 | 40 | 5 | Cooldown 2, +20 accuracy | "Accelerator" (+10 dmg) / "Armor Piercing" (ignore 15% shields) |
| flak_battery | Flak Battery | 20,000 | 15 | 3 | No cooldown, -5 accuracy | "Shrapnel" (+8 dmg) / "Suppressive" (-10 enemy evasion 1 turn) |

### New Defenses (2)

| ID | Name | Price | Effect | Energy | Tunings |
|----|------|-------|--------|--------|---------|
| reactive_armor | Reactive Armor | 18,000 | +20 hull (passive) + 20% dmg reduction 2 turns (active) | 3 | "Composite" (+10 hull) / "Explosive" (5 dmg to attacker) |
| ecm_suite | ECM Suite | 22,000 | +30 evasion 2 turns (active) | 3 | "Jamming" (-10 enemy accuracy) / "Ghost" (-5% scan detection) |

### Faction-Locked Upgrades (4)

| ID | Name | Faction | Rep | Price | Slot | Bonus | Tunings |
|----|------|---------|-----|-------|------|-------|---------|
| nexus_trade_beacon | Nexus Trade Beacon | nexus_trade | 20 | 25,000 | cargo | sell_price_bonus: 0.08 | "Broadcast" (+3% sell) / "Network" (see remote prices) |
| forge_plating | Forge-Hardened Plating | forgeworks_industrial | 20 | 30,000 | defense | hull_bonus: 30 | "Tempered" (+15 hull) / "Reflective" (+10% shield regen) |
| frontier_salvage_array | Frontier Salvage Array | free_salvagers | 20 | 22,000 | scanner | salvage_yield_bonus: 0.30 | "Field" (+15% yield) / "Analyzer" (+2 scan charges) |
| axiom_scanner | Axiom Quantum Scanner | axiom_research | 20 | 35,000 | scanner | scan_charge_bonus: 3 | "Quantum" (+2 charges) / "Spectral" (reveal rare resources) |

### Quest-Unlocked Upgrades (3)

| ID | Name | Unlock Condition | Price | Slot | Effect |
|----|------|------------------|-------|------|--------|
| prototype_shields | Prototype Shield Matrix | `quest_axiom_defense` | 40,000 | defense | 50 shield restore + 15% dmg reduction 3 turns |
| ancient_drive | Ancient Drive Core | `quest_deep_ruins` | 50,000 | engine | fuel_efficiency_bonus: 5 + speed_multiplier_bonus: 0.3 |
| black_sun_jammer | Black Sun Jammer | `quest_fulcrum_chain` | 35,000 | smuggling | -15% detection, -10% heat gain, -8% bounty chance |

---

## Part 4: Faction & Quest Gating

### Ship Availability

Ships gain two new optional fields:
```json
{
  "faction_required": "nexus_trade",
  "faction_rep_required": 50
}
```

Shipyard filters: only show ships where the player meets faction rep AND is at the correct system.

### Upgrade Availability

Upgrades gain:
```json
{
  "faction_required": "forgeworks_industrial",
  "faction_rep_required": 20,
  "unlock_condition": "quest_axiom_defense"
}
```

Shipyard filters:
- `faction_required` + `faction_rep_required`: must have sufficient rep
- `unlock_condition`: checks `player.flags` for the flag key
- `requires_black_market`: existing check, kept as-is

### Faction ID Mapping

| System | Faction ID |
|--------|-----------|
| Nexus Prime | `nexus_trade` |
| Forgeworks | `forgeworks_industrial` |
| Crimson Reach | `free_salvagers` |
| Axiom Labs | `axiom_research` |
| Verdant / Haven's Rest | `verdant_coop` |
| Stellaris Port | `stellaris_commerce` |

---

## Part 5: Implementation Plan

### Step 1: Data Model — InstalledUpgrade & Enhancement (TDD)

**Modify**: `spacegame/models/upgrades.py`
- Add `InstalledUpgrade` dataclass (upgrade_id, mark, tuning)
- Add fields to `ShipUpgrade`: `faction_required`, `faction_rep_required`, `unlock_condition`, `max_mark`, `tuning_options`
- Modify `ShipUpgradeManager`:
  - Store `InstalledUpgrade` list instead of raw `ShipUpgrade` list
  - `get_bonus()` applies mark multiplier + tuning bonus
  - `get_combat_moves()` applies mark multiplier to damage/effects
  - New `enhance(upgrade_id, tuning_choice) → tuple[bool, str]`
  - Updated `to_dict()` / `from_dict()` with mark/tuning data
- Add `MARK_MULTIPLIERS = {1: 1.0, 2: 1.25, 3: 1.50}`
- Add `ENHANCEMENT_COSTS` configuration
- Add tuning bonus resolution

**Modify**: `spacegame/models/ship.py`
- Add `faction_required`, `faction_rep_required`, `unlock_condition` to `ShipType`

**Tests**: ~30-40 new tests covering enhancement, tuning, mark bonuses, backward compat

### Step 2: New Ship Data (24 ships)

**Modify**: `data/ships/ship_types.json` — add 15 new ship definitions
**Modify**: `spacegame/data_loader.py` — parse new ShipType fields
**Tests**: validation tests for all ships (stats, balance, faction gates)

### Step 3: New Upgrade Data (~42 upgrades)

**Modify**: `data/ships/upgrades.json` — add ~18 new upgrades with tuning options
**Modify**: `spacegame/data_loader.py` — parse new ShipUpgrade fields
**Tests**: validation tests for all upgrades, tuning options, faction gates

### Step 4: Shipyard Filtering

**Modify**: `spacegame/views/shipyard_view.py`
- Ship list: filter by faction_required + faction_rep_required + unlock_condition
- Upgrade list: same filtering
- Show locked items as grayed-out with requirement text (aspirational visibility)

### Step 5: Enhancement UI

**Modify**: `spacegame/views/shipyard_view.py`
- New "Enhance" action on installed upgrades tab
- Enhancement flow: select upgrade → see cost → pick tuning (if Mk2) → confirm
- Visual: mark indicators (I/II/III) on installed upgrades, tuning name displayed

### Step 6: Verification

1. All tests pass
2. Game runs, shipyard shows correct filtering
3. Can purchase, install, enhance to Mk2 (pick tuning), enhance to Mk3
4. Save/load preserves enhancement state
5. Mark bonuses apply correctly to ship stats and combat

---

## Trade-Off Matrix

Every ship choice should involve trade-offs. No ship should be universally best.

| If you want... | You sacrifice... | Best ship |
|----------------|------------------|-----------|
| Maximum cargo | Speed, combat | Industrial Titan / Bulk Hauler |
| Maximum combat | Cargo, fuel | War Frigate / Corsair |
| Maximum speed | Hull, cargo | Phantom / Clipper |
| Maximum range | Cargo, combat | Deep Explorer |
| Maximum stealth | Hull, weapons | Phantom / Smuggler's Sloop |
| Maximum mining | Speed, weapons | Industrial Titan / Mining Barge |
| Maximum diplomacy | Combat, speed | Diplomatic Cruiser / Luxury Yacht |
| Maximum prestige | Credits, time | Faction ships |

---

## Skill Tree Synergies

| Skill Tree | Best Ships | Best Upgrades |
|------------|-----------|---------------|
| Trading | Bulk Hauler, Consortium Merchantman | Nexus Trade Beacon, Cargo Compressor |
| Mining | Industrial Titan, Mining Barge | Refining Module, Mining Drill |
| Gathering | Salvage Rig, Deep Explorer | Tractor Beam, Frontier Salvage Array |
| Combat | War Frigate, Syndicate Enforcer | Rail Gun, Reactive Armor |
| Exploration | Deep Explorer, Frontier Runner | Nav Computer, Sensor Array, Axiom Scanner |
| Smuggling | Phantom, Smuggler's Sloop | Black Sun Jammer, Hidden Compartment |
| Leadership | Diplomatic Cruiser, Luxury Yacht | Crew Quarters, Hull Reinforcement |
| Social | Luxury Yacht, Diplomatic Cruiser | Nexus Trade Beacon |
| Ground | Any (ground combat is ship-independent) | Hull Reinforcement (survive getting there) |
