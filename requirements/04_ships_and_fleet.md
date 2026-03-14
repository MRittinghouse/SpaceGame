# Ship & Fleet Requirements

> **Implementation Status** (Updated 2026-02-27): PARTIALLY IMPLEMENTED
>
> - **Ship types**: COMPLETE — 6 classes (Shuttle through Luxury Yacht) with cargo, fuel, efficiency, speed, crew slots, special abilities — `data/ships/ship_types.json`, `models/ship.py`
> - **Ship purchase**: COMPLETE — buy/compare ships at the shipyard, trade-in value system — `views/shipyard_view.py`
> - **Ship upgrades**: COMPLETE — 5 upgrades with 3-slot limit, flat bonuses (simplified from the 15+ tiered upgrades in this spec) — `data/ships/upgrades.json`, `models/upgrades.py`
> - **Cargo management**: COMPLETE — volume-based cargo with capacity limits
> - **Fleet management**: NOT IMPLEMENTED — deferred to Campaign Act Two (Cycle 5.3.1), single ship only during Act One
> - **Crew slots**: Defined in ship data but non-functional — crew system is Phase 2+
> - **Spec note**: The upgrade system was simplified to 5 flat-bonus upgrades with a 3-slot cap, rather than the tiered percentage-based upgrades in this document.

## 1. Overview

Ships are the player's primary asset, mobile warehouse, and means of traversal. Ship selection and upgrades provide key strategic decisions and progression milestones.

## 2. Core Ship Systems

### 2.1 Essential Ship Attributes

Every ship has the following properties:

#### Cargo Capacity
- **Definition**: Maximum units of cargo the ship can carry
- **Range**: 50 (starter) to 1000+ (late-game freighters)
- **Impact**: Directly affects profit potential per trip

#### Fuel Capacity
- **Definition**: Maximum fuel units the ship can store
- **Range**: 50 to 500 units
- **Impact**: Determines travel range before refueling

#### Fuel Efficiency
- **Definition**: Fuel consumed per jump
- **Range**: 5 (efficient) to 50 (inefficient) units per jump
- **Impact**: Operating costs and route viability

#### Speed (Optional - if real-time travel)
- **Definition**: How fast the ship travels between systems
- **Range**: 1x (slow) to 3x (fast) multiplier
- **Impact**: Time efficiency, event exposure

#### Defensive Capability (Optional - future feature)
- **Definition**: Armor, shields, or evasion rating
- **Impact**: Survivability during pirate encounters

#### Purchase Price
- **Definition**: Cost to buy the ship
- **Range**: 5,000 CR (starter) to 5,000,000+ CR (capital ships)

#### Resale Value
- **Definition**: 50-70% of purchase price when sold
- **Impact**: Allows players to switch ship types

### 2.2 Ship Data Structure

```
Ship {
    id: string
    name: string
    class: enum (Shuttle, Freighter, Hauler, Tanker, Corvette)
    cargo_capacity: int
    fuel_capacity: int
    fuel_efficiency: int (units per jump)
    speed_multiplier: float (optional)
    defense_rating: int (optional)
    purchase_price: int
    resale_value: int
    upgrade_slots: int
    special_abilities: list[string] (optional)
}
```

## 3. Ship Classes

### 3.1 Starter Ships

#### Shuttle (Starting Ship)
- **Cargo**: 50-75 units
- **Fuel Capacity**: 100 units
- **Fuel Efficiency**: 10 units/jump
- **Price**: 5,000 CR (or provided free at start)
- **Role**: Learn the game, limited profit potential
- **Upgrade Path**: Quick transition to Freighter

#### Light Freighter
- **Cargo**: 150 units
- **Fuel Capacity**: 150 units
- **Fuel Efficiency**: 15 units/jump
- **Price**: 25,000 CR
- **Role**: Early-game workhorse, balanced stats
- **Upgrade Path**: First major upgrade goal

### 3.2 Mid-Game Ships

#### Medium Freighter
- **Cargo**: 300 units
- **Fuel Capacity**: 200 units
- **Fuel Efficiency**: 20 units/jump
- **Price**: 100,000 CR
- **Role**: Efficient mid-game trader
- **Upgrade Path**: Specialist branches (hauler vs. tanker)

#### Fast Courier
- **Cargo**: 100 units
- **Fuel Capacity**: 250 units
- **Fuel Efficiency**: 8 units/jump
- **Speed**: 2x multiplier
- **Price**: 150,000 CR
- **Role**: Speed over capacity, time-sensitive goods
- **Upgrade Path**: Rare goods specialist

### 3.3 Late-Game Ships

#### Heavy Hauler
- **Cargo**: 600 units
- **Fuel Capacity**: 300 units
- **Fuel Efficiency**: 35 units/jump
- **Price**: 500,000 CR
- **Role**: Maximum cargo, bulk commodities
- **Trade-off**: High fuel costs, slower

#### Bulk Tanker
- **Cargo**: 800 units
- **Fuel Capacity**: 400 units
- **Fuel Efficiency**: 40 units/jump
- **Price**: 1,000,000 CR
- **Role**: Endgame capacity king
- **Trade-off**: Expensive to operate, requires big trades

#### Corvette (Combat-Capable)
- **Cargo**: 200 units
- **Fuel Capacity**: 250 units
- **Fuel Efficiency**: 18 units/jump
- **Defense**: High armor/shields
- **Price**: 750,000 CR
- **Role**: Dangerous route specialist, pirate resistance
- **Trade-off**: Lower cargo for safety

### 3.4 Special/Luxury Ships (Post-MVP)

#### Luxury Yacht
- **Cargo**: 50 units (luxury goods only)
- **Special**: +20% profit on luxury goods
- **Price**: 2,000,000 CR
- **Role**: Niche high-value trading

#### Survey Vessel
- **Cargo**: 150 units
- **Special**: Exploration bonuses, reveals system data
- **Price**: 500,000 CR
- **Role**: Discovery and cartography

## 4. Ship Progression

### 4.1 Upgrade Timeline

**Recommended player progression:**
1. **Start**: Shuttle (provided or 5K CR)
2. **2-3 hours**: Light Freighter (25K CR)
3. **5-8 hours**: Medium Freighter (100K CR)
4. **10-15 hours**: Specialist ship (150-500K CR)
5. **20+ hours**: Heavy Hauler or Tanker (500K-1M CR)
6. **Endgame**: Fleet management (multiple ships)

### 4.2 Ship Purchase Mechanics

#### Shipyards
- Only certain stations sell ships
- Major stations and trade hubs have shipyards
- Selection varies by location (3-8 ship types available)

#### Purchase Flow
1. Visit shipyard at eligible station
2. View available ships with stats comparison
3. See trade-in value of current ship (if applicable)
4. Purchase new ship:
   - **Trade-In**: Sell current ship, apply value to new ship
   - **Direct Purchase**: Buy second ship (fleet management)
5. Transfer cargo from old ship to new (if applicable)

#### Ship Storage
- Player can own multiple ships (fleet management)
- Inactive ships remain docked at station where purchased/parked
- Switch between ships at station where stored

## 5. Ship Upgrades and Modifications

### 5.1 Upgrade Categories

#### Cargo Expansion
- **Effect**: +10-20% cargo capacity
- **Cost**: 10-20% of ship's base price
- **Limit**: 1-2 upgrades per ship
- **Example**: Medium Freighter 300 → 360 units

#### Fuel Tank Upgrade
- **Effect**: +20-30% fuel capacity
- **Cost**: 5-10% of ship's base price
- **Limit**: 1-2 upgrades per ship

#### Engine Efficiency Upgrade
- **Effect**: -10-20% fuel consumption per jump
- **Cost**: 15-25% of ship's base price
- **Limit**: 1-2 upgrades per ship

#### Navigation Computer
- **Effect**: Improved autopilot, route planning
- **Cost**: 10,000-50,000 CR
- **Limit**: One-time upgrade

#### Scanner Upgrade
- **Effect**: Reveal system info before visiting
- **Cost**: 25,000-100,000 CR
- **Limit**: Multiple tiers (Basic, Advanced, Elite)

#### Defensive Upgrades (Post-MVP)
- Shields, armor plating, point defense
- Reduce damage from pirate attacks
- Cost: 50,000-500,000 CR

### 5.2 Upgrade Slots

- Each ship class has fixed upgrade slots (2-5 slots)
- Players choose which upgrades to install
- Upgrades can be removed/replaced (at cost)
- Some upgrades are mutually exclusive

### 5.3 Upgrade Data Structure

```
Upgrade {
    id: string
    name: string
    type: enum (Cargo, Fuel, Efficiency, Navigation, Scanner, Defense)
    effect: {attribute: string, modifier: float}
    cost: int
    compatible_classes: list[enum] (or "all")
    requires_slot: bool
}
```

## 6. Fleet Management (Campaign Act Two)

> **Design Note**: Fleet management is deferred to Campaign Act Two (Cycle 5.3.1). Narratively, the player's growing influence and expanded operations in Act Two justify acquiring and managing multiple ships. Single-ship gameplay throughout Act One keeps the early experience focused.

### 6.1 Multiple Ship Ownership

- Player can own 2-5 ships simultaneously
- Each ship operates independently
- Ships can be stationed at different systems

### 6.2 Fleet Operations

#### Manual Control
- Player directly controls one ship at a time
- Other ships remain docked/idle

#### Automated Routes (Advanced Feature)
- Assign AI to run automated trade routes
- Set buy/sell parameters
- Ship generates passive income
- Requires "Fleet Manager" upgrade or skill

### 6.3 Fleet Progression

- **Solo Trader** (0-10 hours): One ship, hands-on
- **Small Fleet** (10-20 hours): 2-3 ships, starting delegation
- **Trade Empire** (20+ hours): 5+ ships, passive income focus

## 7. Ship Maintenance and Repair

### 7.1 Wear and Tear (Optional Feature)

- Ships degrade over time/jumps
- Reduces efficiency (higher fuel costs)
- Requires periodic maintenance

### 7.2 Repair Mechanics

- **Routine Maintenance**: 1-5% of ship value, performed at stations
- **Damage Repair**: After combat or accidents
- **Prevents**: Ship breakdown or performance loss

### 7.3 Ship Insurance (Optional)

- Pay premium for insurance coverage
- Reduces loss if ship is destroyed
- Premium based on ship value and risk

## 8. Special Ship Abilities

### 8.1 Class-Specific Perks

- **Courier**: 20% faster travel time
- **Hauler**: -10% tariff fees
- **Tanker**: Can refuel other ships (fleet support)
- **Corvette**: Can fight pirates, escort missions

### 8.2 Named Ships / Unique Variants

- Rare ships with enhanced stats
- Found at specific locations or through quests
- Collectible aspect for dedicated players

## 9. Ship Comparison and Analysis

### 9.1 Player Tools

#### Ship Statistics Screen
- View all owned ships and their stats
- Compare ships side-by-side
- See current location of each ship

#### Profitability Calculator
- Input route parameters (distance, cargo type)
- Compare profit potential across ships
- Factor in fuel costs and capacity

### 9.2 Decision Factors

When choosing a ship, players consider:
- **Cargo capacity** vs. **fuel efficiency**
- **Purchase price** vs. **long-term ROI**
- **Operating costs** (fuel per jump)
- **Route suitability** (range, danger level)
- **Future upgrade potential**

## 10. Balance Considerations

### 10.1 Ship Viability

- Every ship class should have a viable use case
- No single "best" ship for all scenarios
- Trade-offs should feel meaningful

### 10.2 Upgrade ROI

- Upgrades should pay for themselves within 5-10 trade runs
- Not strictly necessary but provide clear advantage
- Allow customization based on playstyle

### 10.3 Progression Pacing

- Ship upgrades should feel achievable but rewarding
- Time between upgrades: 2-5 hours of gameplay
- Avoid dead-end ships (all should lead somewhere)

## 11. Technical Requirements

### 11.1 Ship Registry System

- Track all player-owned ships
- Persist ship locations and cargo
- Support ship transfer between saves (optional)

### 11.2 Ship Instance Data

```
PlayerShip {
    ship_id: string (references Ship definition)
    custom_name: string (player-assigned)
    current_system: string
    current_station: string
    cargo_hold: list[{commodity_id: string, quantity: int}]
    fuel_current: int
    upgrades_installed: list[string]
    condition: float (1.0 = pristine, 0.0 = broken)
    total_jumps: int (statistics)
    total_profit: int (statistics)
}
```

### 11.3 Save Data Integration

- Player ship configurations saved per game
- Ship market availability can be procedural or fixed
- Upgrade installation is persistent

## 12. UI/UX Considerations

### 12.1 Ship Management Interface

- Clear display of current ship stats
- Easy access to ship switching (if fleet)
- Visual representation of cargo fill level
- Fuel gauge always visible

### 12.2 Purchase/Upgrade Flow

- Comparison tables for decision-making
- Tooltips explaining each stat
- Confirmation prompts for major purchases
- Undo option for accidental trades (optional)

## 13. Open Questions

- Should ships have unique names assigned by players?
- Can ships be destroyed, or just damaged?
- Should there be ship rental options for new players?
- How deep should ship customization go (cosmetics)?
- Should NPC traders use the same ship types?
- Multi-crew ships (larger ships need hired crew)?

---

**Document Status**: Draft v1.0
**Last Updated**: 2025-10-18
**Dependencies**: Economic system (cargo/fuel as commodities), Galaxy map (fuel consumption per jump)
