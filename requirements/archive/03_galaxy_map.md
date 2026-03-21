# Space/Galaxy Map Requirements

> **Implementation Status** (Updated 2026-02-27): FULLY IMPLEMENTED
>
> - **Galaxy structure**: 10 star systems with 2D coordinates (Option B: Coordinate-Based) — `data/galaxy/systems.json`
> - **System types**: Trade hub, agricultural, industrial, mining, research, frontier — all 6 types present
> - **Travel**: Turn-based with fuel costs based on Euclidean distance — `models/player.py`
> - **Stations**: Multiple stations per system with docking fees and market variety — `models/system.py`
> - **Visual**: 2D galaxy map view with system info, hover/selection, procedural planet thumbnails — `views/galaxy_map_view.py`
> - **Economy tags**: Production/consumption tag system drives supply/demand per system

## 1. Overview

The galaxy map defines the spatial structure of the game world, travel mechanics, and how players navigate between trading locations.

## 2. Galaxy Structure

### 2.1 Hierarchy

```
Galaxy
└── Sectors (optional organizational layer)
    └── Star Systems
        └── Stations/Planets (trading locations)
```

### 2.2 Scale Options

#### Option A: Simple Network (MVP Recommendation)
- 10-20 star systems
- Systems connected in a network graph (not true coordinates)
- Each system has 2-5 connections to other systems
- Focus on connectivity over spatial realism

#### Option B: Coordinate-Based
- Systems have X,Y coordinates in 2D space
- Travel based on euclidean distance
- More realistic but complex for pathfinding

**Recommended**: Option A for MVP, migrate to Option B post-launch if desired

### 2.3 Star System Properties

Each star system contains:
- **Name**: Unique identifier (e.g., "Alpha Centauri", "New Terra")
- **Type**: Determines economic characteristics
- **Stations**: 1-3 trading stations/planets per system
- **Connections**: List of accessible neighboring systems
- **Danger Level**: Safe, Moderate, Dangerous (affects random events)
- **Faction Control**: Which faction owns/controls this system
- **Special Tags**: Production/consumption attributes for economy

### 2.4 Star System Types

#### Agricultural Systems
- **Economic Profile**: Produces food, textiles, organic goods
- **Buys**: Machinery, fuel, manufactured goods
- **Characteristics**: Lower prices for basic commodities

#### Industrial Systems
- **Economic Profile**: Produces machinery, electronics, manufactured goods
- **Buys**: Raw materials, food, fuel
- **Characteristics**: High demand for raw inputs

#### Mining Systems
- **Economic Profile**: Produces metals, rare earth elements
- **Buys**: Food, machinery, fuel
- **Characteristics**: Abundant raw materials

#### Research Systems
- **Economic Profile**: Produces electronics, medical supplies
- **Buys**: Rare materials, food
- **Characteristics**: High-tech goods availability

#### Trade Hub Systems
- **Economic Profile**: Balanced markets, high variety
- **Buys/Sells**: Everything at moderate prices
- **Characteristics**: Central locations, high traffic

#### Frontier Systems
- **Economic Profile**: Volatile, high-risk/reward
- **Buys/Sells**: Limited selection, extreme prices
- **Characteristics**: Remote, dangerous, opportunities for big profits

## 3. Stations and Trading Posts

### 3.1 Station Types

#### Major Stations
- Full commodity selection (15-20 different goods)
- High supply depth (1000+ units)
- Full ship services (repair, upgrade, purchase)
- Safe docking, low fees

#### Minor Outposts
- Limited commodity selection (5-10 goods)
- Low supply depth (100-500 units)
- Basic services only
- May have higher fees or risks

#### Black Market Stations (Post-MVP)
- Illegal goods available
- No questions asked
- Higher risk of law enforcement
- Access requires reputation or discovery

### 3.2 Station Properties

```
Station {
    id: string
    name: string
    system_id: string
    type: enum (Major, Minor, BlackMarket)
    docking_fee: int
    services: list[enum] (Trade, Repair, Upgrade, ShipPurchase)
    commodity_availability: list[string]
    reputation_required: int (0 = open to all)
}
```

## 4. Travel and Navigation

### 4.1 Travel Mechanics (Network-Based)

#### Jump System
- Travel occurs via "jumps" between connected systems
- Each jump takes time and consumes fuel
- Distance measured in jumps, not spatial units

#### Travel Time Options

**Option A: Instant Travel (Simplest)**
- Click destination, arrive instantly
- Fuel cost applied
- Random events can occur on arrival

**Option B: Turn-Based Travel**
- Each jump = 1 turn/day
- Events can occur during travel
- Time affects market prices

**Option C: Real-Time with Pause**
- Travel takes real seconds (e.g., 5-10 seconds per jump)
- Can pause anytime
- Events can interrupt travel

**Recommended**: Option A or B for MVP

### 4.2 Fuel System

#### Fuel as Resource
- Fuel is a tradeable commodity
- Required for jump travel
- Consumption based on:
  - Ship type (larger ships = more fuel)
  - Jump distance (longer = more fuel)
  - Ship upgrades (efficiency improvements)

#### Fuel Costs
- **Small Ship**: 5-10 fuel units per jump
- **Medium Ship**: 15-25 fuel units per jump
- **Large Ship**: 30-50 fuel units per jump

#### Running Out of Fuel
- Player stranded in current system
- Must buy fuel or sell cargo to afford fuel
- Emergency distress beacon (optional rescue mechanic)

### 4.3 Pathfinding

#### Manual Navigation
- Player selects next system from current system's connections
- Player plans route manually

#### Autopilot (Optional Feature)
- Input destination system
- Game calculates shortest path
- Player confirms and executes

#### Navigation Display
- Current system highlighted
- Accessible systems (1 jump away) shown clearly
- Multi-jump paths shown with waypoints
- Fuel cost preview before travel

## 5. Map Visualization

### 5.1 Galaxy Map View

#### Layout
- 2D representation of star systems
- Systems shown as nodes/icons
- Connections shown as lines between systems
- Color-coded by faction or danger level

#### Visual Elements
- **Current Location**: Distinct marker (e.g., pulsing icon)
- **Visited Systems**: Normal appearance
- **Unvisited Systems**: Grayed out or question mark (fog of war)
- **Connections**: Lines between linked systems
- **Faction Colors**: Background or border color indicates control

#### Interaction
- Click system to view details
- Click to set as destination/waypoint
- Hover for quick info tooltip
- Zoom in/out (if map is large)

### 5.2 System Detail View

When player selects a system:
- System name and type
- Stations available (list)
- Faction control
- Danger level
- Distance from current location (in jumps)
- Estimated fuel cost to reach
- Market price preview (if visited before)

### 5.3 Fog of War (Optional)

#### Discovery Mechanic
- Systems start hidden or with minimal info
- Revealed when visited or when adjacent to visited system
- Market data only available after visiting

#### Intelligence Gathering
- Buy star charts to reveal new systems
- NPC tips about profitable routes
- Exploration bonus for first visit

## 6. Galaxy Generation

### 6.1 Procedural vs. Hand-Crafted

#### Hand-Crafted (MVP Recommendation)
- Designer manually creates 10-20 systems
- Ensures balanced and interesting layout
- Easier to test and balance
- Connections designed for good gameplay flow

#### Procedural Generation (Post-MVP)
- Algorithm generates galaxy on new game
- Seed-based for reproducibility
- Ensures minimum connectivity and variety
- Replayability benefit

### 6.2 Generation Requirements

If procedural:
- Ensure all systems are reachable from start
- Balance system type distribution
- Avoid isolated dead-ends (unless intentional)
- Create meaningful trade route opportunities
- Place high-value systems at appropriate risk/distance

### 6.3 Starting Location

- Player starts in a "safe" starter system
- **Type**: Trade Hub or Agricultural (stable prices)
- **Connections**: 3-4 accessible systems nearby
- **Characteristics**: Low danger, good tutorial environment

## 7. Map Data Structure

### 7.1 System Graph

```
System {
    id: string
    name: string
    type: enum (Agricultural, Industrial, Mining, Research, TradeHub, Frontier)
    danger_level: enum (Safe, Moderate, Dangerous)
    faction_id: string
    connected_systems: list[string] (system IDs)
    stations: list[Station]
    production_tags: list[string]
    consumption_tags: list[string]
    position: {x: float, y: float} (for visualization)
    discovered: bool (player has visited)
}
```

### 7.2 Connection Metadata (Optional)

```
Connection {
    from_system: string
    to_system: string
    base_fuel_cost: int
    danger_level: enum (Safe, Moderate, Dangerous)
    controlled_by: string (faction_id, if applicable)
}
```

## 8. Exploration and Discovery

### 8.1 Exploration Incentives

- **First Discovery Bonus**: Credits for first visit to system
- **Cartography Data**: Sell exploration data to factions
- **Hidden Systems**: Secret systems accessible only via rumors/quests
- **Anomalies**: Special locations with unique opportunities

### 8.2 Navigation Tools

- **Star Charts**: Purchasable items that reveal system info
- **Scanner Upgrades**: Reveal more info about adjacent systems
- **Navigation Computer**: Improves autopilot and route planning

## 9. Dynamic Events

### 9.1 System-Level Events

- **Pirate Blockade**: Travel to/from system risky or blocked
- **Economic Boom/Bust**: Affects all prices in system
- **Natural Disaster**: Supply shortages, high demand
- **Political Change**: Faction control changes

### 9.2 Route Events

Events that can occur during travel:
- **Pirate Encounter**: Combat or bribe (future feature)
- **Distress Signal**: Rescue opportunity (reward or trap)
- **Debris Field**: Salvage opportunity
- **Navigation Hazard**: Extra fuel cost or damage

## 10. Faction Territory

### 10.1 Faction Control

- Each system controlled by one of 3-5 major factions
- Faction relationship affects:
  - Docking fees
  - Tariffs
  - Access to restricted systems
  - Random event frequency

### 10.2 Border Systems

- Systems on faction boundaries
- Higher tension, more patrol activity
- Potential for conflict events
- Trade opportunities due to tariff differences

### 10.3 Independent Systems

- Not controlled by major factions
- More freedom, less security
- Frontier opportunities

## 11. Technical Considerations

### 11.1 Performance

- Map should render smoothly (60 FPS target)
- Pathfinding should be instant for typical galaxy sizes
- Graph algorithms: Dijkstra or A* for routing

### 11.2 Data Storage

- JSON or SQLite for system/connection data
- Save player's discovered systems per save file
- Cache calculated routes for performance

### 11.3 Scalability

- Design to support 50-100 systems without refactoring
- Modular system to add new systems easily
- Support for expansion content

## 12. Open Questions

- Should systems have multiple routes between them (redundant paths)?
- How much should fog of war obscure vs. reveal?
- Real-time or turn-based travel?
- Should there be one-way connections or wormholes?
- How does player unlock new regions of the galaxy?
- Should distance affect market prices automatically?

---

**Document Status**: Draft v1.0
**Last Updated**: 2025-10-18
**Dependencies**: Integrates with economic system (production/consumption) and ship specs (fuel consumption)
