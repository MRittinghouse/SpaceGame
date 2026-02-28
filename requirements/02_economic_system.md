# Economic System Requirements

> **Implementation Status** (Updated 2026-02-27): FULLY IMPLEMENTED
>
> - **Currency**: Credits (integer-based), starting capital 5,000 CR — implemented in `models/player.py`
> - **Commodities**: 19 tradeable goods across basic, industrial, and luxury categories (exceeds the 8-12 spec) — `data/economy/commodities.json`
> - **Pricing**: Dynamic with base prices, variance ranges, and supply/demand tags — `models/market.py`
> - **Market events**: Shortage, surplus, disaster, boom — `models/event.py`
> - **Trade mechanics**: Buy/sell with cargo volume management — `views/trading_view.py`
> - **Mining/Salvage/Refining economy**: 4 ore types, 3 salvage types, 6 refining recipes feed into the commodity market

## 1. Overview

The economic system is the core mechanic of the space trading game. It must provide depth, variability, and strategic decision-making while remaining understandable to new players.

## 2. Currency System

### 2.1 Primary Currency
- **Credits (CR)**: Universal currency accepted across all systems
- **Integer-based**: No decimal values to simplify UI and calculations
- **Starting Capital**: 1,000 - 5,000 CR (to be balanced during testing)

### 2.2 Currency Display
- Formatted with thousand separators (e.g., "1,234,567 CR")
- Color-coded: Green for gains, Red for losses, White for neutral
- Always visible in main UI header

### 2.3 Bankruptcy Protection
- Player cannot go into negative credits
- Minimum emergency loan system (optional feature for later)
- If stuck: ability to sell cargo or ship components to recover

## 3. Commodity System

### 3.1 Commodity Categories

#### Basic Goods (Low Risk, Low Margin)
- **Food & Water**: Stable demand, small price fluctuations
- **Textiles**: Common trade good
- **Common Metals**: Iron, Copper, Aluminum
- **Fuel**: Used by ships, moderate demand

#### Industrial Goods (Medium Risk, Medium Margin)
- **Machinery**: Manufacturing equipment
- **Electronics**: Computer components, sensors
- **Rare Metals**: Platinum, Titanium, Rare Earth Elements
- **Manufactured Goods**: Consumer products

#### Luxury Goods (High Risk, High Margin)
- **Precious Metals**: Gold, Silver
- **Art & Antiquities**: Cultural items
- **Exotic Goods**: Alien artifacts, rare specimens
- **Medical Supplies**: Advanced pharmaceuticals

### 3.2 Commodity Properties

Each commodity has:
- **Base Price**: Starting reference price (in credits per unit)
- **Price Variance Range**: Min/Max percentage deviation (e.g., ±20% for stable goods, ±60% for volatile)
- **Volume**: Cargo space per unit (e.g., 1, 5, 10, 20 units)
- **Legality Status**: Legal, Restricted, Illegal (by system)
- **Supply/Demand Factors**: Production vs consumption attributes

### 3.3 Commodity Data Structure

```
Commodity {
    id: string
    name: string
    category: enum (Basic, Industrial, Luxury)
    base_price: int
    variance_min: float (-1.0 to 0.0)
    variance_max: float (0.0 to 1.0)
    volume_per_unit: int
    legality: enum (Legal, Restricted, Illegal)
    production_tags: list[string] (e.g., ["agricultural", "mining"])
    consumption_tags: list[string] (e.g., ["industrial", "luxury_demand"])
}
```

## 4. Pricing Model

### 4.1 Base Pricing Formula

```
current_price = base_price × (1 + supply_demand_modifier + random_variance + event_modifier)
```

### 4.2 Supply and Demand Modifiers

#### Production Bonus (Reduces Price)
- Systems with production tags matching commodity reduce price by 15-30%
- Example: Agricultural systems sell Food cheap

#### Consumption Bonus (Increases Price)
- Systems with consumption tags matching commodity increase price by 15-30%
- Example: Industrial systems buy Machinery at premium

#### Distance Premium
- Goods far from production source cost more
- Optional feature: +5% per jump from nearest production system

### 4.3 Random Variance
- Small random fluctuation applied each game cycle/day
- Range: ±5-10% for stable goods, ±15-25% for volatile goods
- Changes gradually (not instant jumps) to prevent exploit

### 4.4 Event Modifiers
- **Shortage**: +30-60% price increase
- **Surplus**: -20-40% price decrease
- **Blockade**: Prevents trade entirely or extreme price spike
- **Economic Boom**: +10-20% to all luxury goods
- **Recession**: -10-20% to all luxury goods

## 5. Market Mechanics

### 5.1 Market Information Display

Players should see:
- Current price per unit
- Comparison to galactic average (e.g., "15% below avg")
- Recent trend indicator (rising/falling/stable)
- Quantity available (supply limit)
- Your cargo quantity of this commodity

### 5.2 Supply Limits

#### Limited Market Depth
- Each system has finite quantity of each commodity available
- High-volume stations: 1000-5000 units
- Small stations: 100-500 units
- Prevents infinite money exploits

#### Restocking
- Markets restock over time (per game day/cycle)
- Production systems restock faster
- Player purchases reduce available supply
- Player sales increase available supply (with diminishing returns)

### 5.3 Transaction Mechanics

#### Buying
1. Select commodity from market list
2. Input desired quantity (limited by cargo space and funds)
3. See total cost calculation
4. Confirm purchase
5. Credits deducted, cargo added

#### Selling
1. Select commodity from cargo hold
2. Input quantity to sell (or "Sell All" option)
3. See total revenue calculation
4. Confirm sale
5. Credits added, cargo removed

### 5.4 Transaction Fees
- **Tariffs**: 0-5% fee on transactions (varies by system)
- **Docking Fee**: Flat fee per station visit (100-500 CR)
- **Illegal Goods Fine**: Risk of confiscation and heavy fine if caught

## 6. Trade Route Optimization

### 6.1 Profit Calculation
```
profit = (sell_price - buy_price) × quantity - fuel_cost - fees - risk_cost
profit_margin = profit / total_investment
```

### 6.2 Player Tools
- **Price History**: View recent price trends (last 5-10 data points)
- **Route Planner**: Calculate potential profit between systems (optional feature)
- **Market Reports**: Rumors/news about shortages and surpluses

### 6.3 Risk Factors
- **Distance**: More jumps = more fuel cost
- **Danger Zones**: Pirate-controlled systems (future feature)
- **Volatility**: Prices may change during travel
- **Cargo Capacity**: Opportunity cost of carrying one good vs another

## 7. Economic Balance

### 7.1 Profit Margins

**Target profit margins by game stage:**
- **Early Game**: 10-25% per round trip (safe routes)
- **Mid Game**: 25-50% per round trip (optimized routes)
- **Late Game**: 30-60% per trip (high-risk routes or rare goods)

### 7.2 Earning Curves

**Expected credits per hour of play:**
- **Hour 1**: 1,000-3,000 CR
- **Hour 5**: 10,000-25,000 CR
- **Hour 10**: 50,000-100,000 CR
- **Hour 20+**: 200,000+ CR

### 7.3 Anti-Exploit Measures

#### Price Dampening
- Repeated trades on same route cause diminishing returns
- Buying large quantities increases local price
- Selling large quantities decreases local price

#### Market Memory
- Systems "remember" recent player transactions
- Prevents infinite buy-low-sell-high loops
- Markets take time to reset (3-5 game cycles)

#### Supply Exhaustion
- Can't buy infinite quantities
- Must wait for restocking or find new sources

## 8. Advanced Economic Features (Post-MVP)

### 8.1 Supply Chain Simulation
- Refined goods require raw materials
- Production systems consume inputs, produce outputs
- Player can identify and profit from supply chain gaps

### 8.2 Economic Events
- **Famine**: Food prices spike in affected region
- **War**: Weapons/Military goods in high demand
- **Discovery**: New commodity unlocked, initially rare
- **Trade Agreement**: Tariffs removed between faction systems

### 8.3 Speculation
- Forward contracts: Buy futures at locked price
- Commodity warehousing: Store goods to sell later
- Arbitrage opportunities across distant systems

### 8.4 Black Markets
- Hidden markets for illegal goods
- Higher risk, higher reward
- Requires reputation or special access

## 9. Data Requirements

### 9.1 Persistent Data
- Current market prices per system per commodity
- Market supply levels
- Player transaction history
- Active economic events

### 9.2 Configuration Data
- Commodity definitions
- Base price tables
- System production/consumption tags
- Event trigger conditions

## 10. Testing and Balancing

### 10.1 Key Metrics to Monitor
- Average profit per trade route
- Time to reach first ship upgrade
- Price volatility range
- Exploit opportunities (if any)

### 10.2 Balance Levers
- Adjust base prices
- Modify variance ranges
- Change supply/demand multipliers
- Tune event frequency and impact

## 11. Open Questions

- Should there be a stock market/investment system?
- How much should player actions affect the broader economy?
- Should NPC traders compete with the player?
- Real-time price updates or turn-based?
- Should certain goods be seasonally available?

---

**Document Status**: Draft v1.0
**Last Updated**: 2025-10-18
**Dependencies**: Requires galaxy map structure and ship cargo definitions
