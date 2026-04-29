# Financial Exchange Design

**Sprint**: SA-F1 | **Phase**: V | **Author**: SA-F1 implementation agent

This document is the single source of truth for the Aurelia Financial Exchange arc. SA-F2 reads sections 1 through 3, 7, 8, 9, 11 before writing a line of code. SA-F3 reads sections 1, 2, 7, 9, 11 plus the Ilse Vey voice sheet. SA-F4 reads sections 1, 4, 7, 8, 9, 11. SA-F5 reads sections 1, 5, 7, 8, 9, 11. SA-F6 reads sections 1, 6, 7, 8, 9, 11 plus the existing `galaxy_event.py`. SA-F7 reads sections 1, 2, 4, 5, 6, 7, 9, 11. SA-X1, SA-X3, SA-X5, SA-X6, and SA-X7 read section 9 only. The hand-off table at section 12 maps each downstream sprint to its relevant sections.

All decisions in section 11 are locked. SA-F2 and downstream sprints do not re-litigate locked decisions. Open items deferred to SA-F2 / SA-F4 / SA-F5 / SA-F6 / SA-F7 are explicitly named in section 10.

---

## 1. Scope and Relationship to Existing Systems

### 1.1 What the Financial Exchange arc adds

The Financial Exchange arc introduces Meridian Financial Exchange as a higher-tier capital deployment venue at Nexus Prime. Three sub-systems extend the player's economic surface: futures contracts (commodity price speculation), shipping contracts (agreed cargo delivery for profit), and insurance (hull coverage against ship loss). A fourth system adds galaxy events of type MARKET_MANIPULATION that interact with all three and are detectable and sometimes counterable by the player.

The Financial Exchange is where the player moves from running trades to structuring them. It requires operating capital, market literacy, and some tolerance for timed risk. It is accessible after the SA-V Cargo Broker arc introduces the player to Odom and his graduation pointer toward Ilse Vey at Meridian.

### 1.2 What the Financial Exchange arc does NOT touch

The per-system passive investment system (`spacegame/models/investment.py`) is unchanged. Meridian is a parallel higher-tier system, not a replacement. Per-system investment cards continue as the player's first taste of capital deployment (introduced in SA-V's `the_longer_ledger` mission); Meridian is the graduation tier where the same instinct operates at scale. **Decision locked. See Section 11, decision 5.**

`market.py` is read-only from SA-F's perspective. The futures settlement call reads `Market.get_price()` at maturity; no other market mutations are introduced by SA-F2 through SA-F6. Market manipulation events in SA-F6 apply via the existing `GalaxyEvent` infrastructure, which already modifies `Market._calculate_price()` -- not via new market-write paths.

The SA-V Odom `graduation_pointer` dialogue node at `data/dialogue/dialogues.json:1331-1340` is NOT modified by this arc. SA-F3 authors new dialogue for Ilse Vey and the Meridian contact hierarchy; Odom's existing node remains as written.

### 1.3 Module layout

| File | Sprint | Status |
|---|---|---|
| `spacegame/models/futures.py` | SA-F2 | NEW -- FuturesContract, FuturesState, PricingEngine |
| `spacegame/models/shipping_contract.py` | SA-F4 | NEW -- ShippingContract, ShippingContractState |
| `spacegame/models/insurance.py` | SA-F5 | NEW -- InsurancePolicy, InsurancePremiumEngine |
| `spacegame/models/market_manipulation.py` | SA-F6 | NEW -- extends GalaxyEvent with MARKET_MANIPULATION enum value and manipulation templates |
| `spacegame/views/meridian_view.py` | SA-F3 | NEW -- MeridianView, contract terminal UI |
| `data/galaxy/manipulation_events.json` | SA-F6 | NEW -- 8 manipulation event templates |
| `data/missions/shipping_contracts.json` | SA-F4 | NEW -- initial shipping contract pool |
| `data/missions/crisis_arc.json` | SA-F7 | NEW -- financial crisis event arc |

### 1.4 Venues and access gating

| Venue | Location | Access gate |
|---|---|---|
| Meridian Financial Exchange | Nexus Prime | Nexus Prime / Commerce Guild standing tier |
| Meridian contract terminal | Inside Meridian venue | First visit triggers Cargo Broker graduation arc (SA-F3) |

Nexus Prime standing tiers gate contract size, mirroring the Stellaris Port pattern from SA-B1 decision 8: apprentice (low max contract size), regular (mid), certified (high), patron (no cap). **Decision locked. See Section 11, decision 7.**

### 1.5 Relationship to SA-V (Cargo Broker arc)

SA-V produces Odom's `graduation_pointer` node naming Ilse Vey at Meridian. SA-F3 picks up that thread. The player's first Meridian visit should feel like a natural escalation of what the Cargo Broker arc built. Ilse Vey's voice and register are documented in `requirements/character_voices.md:1470-1511`. SA-F3 authors the graduation dialogue; SA-F1 establishes the sample lines and voice constraints in section 9 of this document.

### 1.6 Relationship to existing skill tree and crew (SA-C2, SA-A2)

The `spread_trader` Commerce Tier 2 skill (`spacegame/models/progression.py`, created by SA-C2) provides `speculator_premium_reduction` at +0.05 per level, max level 2, max contribution +0.10. Brix Tano speculator crew (`data/crew/crew_members.json:774-800`) provides `futures_intel: 1.0` and `speculator_premium_reduction: 0.10`. Combined maximum is 0.20 (additive, capped at -0.25 including future edge cases). **Decision locked. See Section 11, decision 6.**

---

## 2. Futures Contract Lifecycle

### 2.1 Five-phase lifecycle

A futures contract moves through five phases:

```
OFFER --> PREVIEW --> ACCEPT --> MATURE --> SETTLE
```

| Phase | Actor | Description |
|---|---|---|
| Offer | Meridian broker | Broker posts contracts at the contract terminal; each contract specifies commodity, quantity, direction, duration, strike price, entry cost |
| Preview | Player | Player compares strike price against current market price and recent PriceHistory; Brix Tano's futures_intel reveals probability band if active |
| Accept | Player | Player pays entry_cost (credits deducted immediately); contract enters in-flight state on Player save as part of FuturesState |
| Mature | Game-day cycle | Contract countdown ticks each `update_day()`; at maturity day, settlement is triggered automatically |
| Settle | Game engine | `Market.get_price(commodity_id)` is called at the maturity day; settlement payoff computed; credits credited/debited; rep delta applied; journal entry fires; news ticker template fires if headliner contract |

### 2.2 Contract directions

A **LONG** contract profits if the commodity price rises above the strike price at maturity:
- settlement_payoff = (Market.get_price(commodity_id) - strike_price) x quantity

A **SHORT** contract profits if the commodity price falls below the strike price at maturity:
- settlement_payoff = (strike_price - Market.get_price(commodity_id)) x quantity

A positive settlement_payoff credits the player. A negative settlement_payoff debits the player. The entry_cost is always paid at acceptance and is not returned at settlement, regardless of direction.

### 2.3 Headliner contracts

Contracts above a volume threshold (quantity x strike_price > 10,000 cr) are flagged as headliners. Headliner contract settlements fire the news ticker template stub (section 9.3). SA-F3 / SA-X5 authors the full ticker content.

### 2.4 Minimum quantity gate

The Meridian terminal does not post futures contracts below 20 units per contract. This prevents trivial fishing contracts that clutter the terminal. **Decision locked. See Section 11, decision 2.**

---

## 3. Futures Pricing Formula

### 3.1 Inputs

The pricing engine takes the following inputs at offer generation time:

| Input | Source | Notes |
|---|---|---|
| `current_price` | `Market.get_price(commodity_id)` | Current price at Nexus Prime on the offer day |
| `trend` | `PriceHistory.get_trend(system_id, commodity_id)` | "rising", "stable", or "falling" |
| `distance_hops` | Galaxy graph hop count from commodity's primary production system to Nexus Prime | Integer, 1-5 |
| `duration_days` | Player-selected at acceptance: 7, 14, or 21 game-days | Integer |
| `speculator_premium_reduction` | `progression.get_bonus("speculator_premium_reduction") + crew_roster.get_bonus("speculator_premium_reduction")` | Float, capped at 0.25 |

### 3.2 Formula

```
TREND_PREMIUM = {"rising": 0.04, "stable": 0.01, "falling": 0.00}
HOP_PENALTY = 0.01  # per hop from production system to Nexus Prime
DURATION_SPREAD = {7: 0.02, 14: 0.05, 21: 0.09}
BASE_BROKER_SPREAD = 0.04

forward_spread = TREND_PREMIUM[trend] + (distance_hops x HOP_PENALTY) + DURATION_SPREAD[duration_days]
strike_price = floor(current_price x (1 + forward_spread))
broker_spread_rate = BASE_BROKER_SPREAD x (1 - speculator_premium_reduction)
entry_cost = floor(strike_price x quantity x broker_spread_rate)
```

The forward_spread is built into the strike price. It reflects the broker's forward expectation: a rising trend pushes the strike higher (player must bet on prices rising further), a falling trend keeps the strike close to current (lower bar for a short). A longer duration widens the strike further due to greater market uncertainty.

`speculator_premium_reduction` reduces the broker's commission rate but does not change the strike price. The player saves on entry cost but still faces the same market bet.

The `_get_supply_demand_modifier` at Nexus Prime is already reflected in the `current_price` that `Market.get_price()` returns (via `Market._calculate_price()` which calls `_get_supply_demand_modifier` internally). The pricing engine reads the already-calculated price; it does not re-invoke the modifier.

### 3.3 Settlement

At the maturity game-day, the settlement engine calls `Market.get_price(commodity_id)` at Nexus Prime. No proxy, no synthetic projection. The payoff uses the actual observable price the player can verify on the trade terminal the same day.

### 3.4 Worked examples

#### Example A: common_metals, 7-day LONG, no speculator bonuses (production-tag commodity)

Context: common_metals is a raw material produced at mining systems (`production_tags: ['common_metals', 'raw_materials', 'mining']`). At Nexus Prime (a finance/trade hub that does not produce or consume common_metals in its economy), `_get_supply_demand_modifier` returns 0.0. The current price is driven by the base price plus random variance from `_get_random_variance`.

```
current_price = Market.get_price("common_metals") at Nexus Prime = 62 cr
  [base_price 60 x (1 + 0.0 [_get_supply_demand_modifier: neutral] + 0.03 [_get_random_variance]) = 61.8 -> 62]

trend = PriceHistory.get_trend("nexus_prime", "common_metals") = "rising"
  -> TREND_PREMIUM = 0.04

distance_hops = 3  [common_metals primary production at distant mining systems]
  -> HOP_PENALTY contribution = 0.03

duration_days = 7
  -> DURATION_SPREAD = 0.02

forward_spread = 0.04 + 0.03 + 0.02 = 0.09
strike_price = floor(62 x 1.09) = floor(67.58) = 67 cr

speculator_premium_reduction = 0.0  [no skill, no crew]
broker_spread_rate = 0.04 x (1 - 0.0) = 0.04
quantity = 80 units
entry_cost = floor(67 x 80 x 0.04) = floor(214.40) = 214 cr

----- 7 game-days pass -----

Market.get_price("common_metals") at maturity = 74 cr  [supply pressure from mining strike]
payoff (LONG) = (74 - 67) x 80 = 7 x 80 = 560 cr
net_result = 560 - 214 = +346 cr profit
```

Analysis: The rising trend correctly predicted direction. The 3-hop distance premium reflected genuine supply uncertainty. The 7-day DURATION_SPREAD was the minimum (lowest bar). The contract paid off cleanly.

#### Example B: medical, 14-day LONG, Brix Tano crew active (consumption-tag commodity)

Context: medical is produced at research/high_tech systems (`production_tags: ['medical', 'research', 'high_tech']`) and consumed at trade hubs (`consumption_tags: ['trade_hub', 'agricultural', 'industrial']`). At Nexus Prime (trade hub tag present in Nexus Prime's economy), `_get_supply_demand_modifier` returns +0.25, raising the price above base.

```
current_price = Market.get_price("medical") at Nexus Prime = 444 cr
  [base_price 350 x (1 + 0.25 [_get_supply_demand_modifier: consumption system] + 0.02 [_get_random_variance]) = 444.5 -> 444]

trend = PriceHistory.get_trend("nexus_prime", "medical") = "stable"
  -> TREND_PREMIUM = 0.01

distance_hops = 2  [medical produced at research systems 2 hops from Nexus Prime]
  -> HOP_PENALTY contribution = 0.02

duration_days = 14
  -> DURATION_SPREAD = 0.05

forward_spread = 0.01 + 0.02 + 0.05 = 0.08
strike_price = floor(444 x 1.08) = floor(479.52) = 479 cr

speculator_premium_reduction = 0.10  [Brix Tano crew active; no spread_trader skill]
broker_spread_rate = 0.04 x (1 - 0.10) = 0.036
quantity = 20 units
entry_cost = floor(479 x 20 x 0.036) = floor(345.12) = 345 cr

----- 14 game-days pass -----

Market.get_price("medical") at maturity = 461 cr  [modest demand uptick, not sufficient]
payoff (LONG) = (461 - 479) x 20 = -18 x 20 = -360 cr
net_result = -360 - 345 = -705 cr total loss
```

Analysis: The stable trend was accurate -- prices did not move significantly. The 14-day DURATION_SPREAD (0.05) required a +8% price move above current to exceed the strike (479 vs 444, a 7.9% bar). Medical rose only 3.8% (444 to 461). Brix's presence reduced the entry cost by 10%, partially cushioning the loss, but could not overcome an unfavorable settlement. This is the expected outcome for a long on a stable-trend commodity: the forward_spread demands movement the market didn't provide.

#### Example C: manufactured_goods, 21-day SHORT, max speculator bonuses (neutral-tag commodity, short position)

Context: manufactured_goods is produced at industrial systems (`production_tags: ['manufactured_goods', 'industrial']`) and consumed at trade hubs (`consumption_tags: ['agricultural', 'trade_hub', 'mining']`). At Nexus Prime, `_get_supply_demand_modifier` returns +0.25 (trade_hub consumption). The player takes a SHORT position betting prices will fall.

```
current_price = Market.get_price("manufactured_goods") at Nexus Prime = 152 cr
  [base_price 120 x (1 + 0.25 [_get_supply_demand_modifier: consumption system] + 0.02 [_get_random_variance]) = 152.4 -> 152]

trend = PriceHistory.get_trend("nexus_prime", "manufactured_goods") = "falling"
  -> TREND_PREMIUM = 0.00

distance_hops = 1  [industrial systems adjacent to Nexus Prime]
  -> HOP_PENALTY contribution = 0.01

duration_days = 21
  -> DURATION_SPREAD = 0.09

forward_spread = 0.00 + 0.01 + 0.09 = 0.10
strike_price = floor(152 x 1.10) = floor(167.2) = 167 cr

speculator_premium_reduction = 0.20  [spread_trader L2: 2 x 0.05 = 0.10; Brix Tano crew: 0.10; total = 0.20]
broker_spread_rate = 0.04 x (1 - 0.20) = 0.032
quantity = 50 units
entry_cost = floor(167 x 50 x 0.032) = floor(267.2) = 267 cr

----- 21 game-days pass -----

Market.get_price("manufactured_goods") at maturity = 139 cr  [supply glut from nearby industrial expansion]
payoff (SHORT) = (167 - 139) x 50 = 28 x 50 = 1,400 cr
net_result = 1,400 - 267 = +1,133 cr profit
```

Analysis: The falling trend was correctly identified; TREND_PREMIUM = 0.0 kept the strike close to the current price (167 vs 152, a 9.9% bar from current). The SHORT position required actual_price < strike; at 139 cr the market fell 22 cr below the 167 strike, producing a 28 cr/unit payoff. The 21-day DURATION_SPREAD (0.09) was the widest, but also the period over which the supply glut materialised. Max speculator bonuses (0.20) reduced the entry cost from floor(167 x 50 x 0.04) = 334 cr down to 267 cr -- a 67 cr saving that materially improved net return.

---

## 4. Shipping Contract Structure

### 4.1 Schema fields

| Field | Type | Description |
|---|---|---|
| `origin_system_id` | `str` | System where the commodity is loaded |
| `destination_system_id` | `str` | System where the commodity must be delivered |
| `commodity_id` | `str` | Commodity being shipped |
| `quantity` | `int` | Units required for delivery |
| `payout_credits` | `int` | Credits paid on successful on-time delivery |
| `deadline_day` | `int` | Game-day by which the delivery must be complete |
| `late_penalty_credits` | `int` | Credits deducted per day past deadline_day (capped at cancellation) |
| `route_waypoint_bonus_system_id` | `Optional[str]` | System to visit en route for bonus payout; None if no waypoint |
| `route_waypoint_bonus_credits` | `int` | Credits added to payout for visiting route_waypoint_bonus_system_id |
| `cancellation_penalty_credits` | `int` | Credits debited if the contract is cancelled or very-late (deadline + 5) |
| `faction_id` | `str` | Faction the contract belongs to; affects standing on completion |
| `prerequisite_standing_tier` | `str` | Minimum standing tier required to accept ("apprentice", "regular", "certified", "patron") |

### 4.2 Acceptance flow

The contract terminal displays available contracts sorted by payout. The player must meet `prerequisite_standing_tier` with the `faction_id` faction to accept. On acceptance, the contract enters the Player's `shipping_contracts` list in an `IN_FLIGHT` state. The player must then:
1. Load the commodity (commodity_id, quantity) into their cargo hold at origin_system_id.
2. Travel to destination_system_id.
3. Dock -- the game checks cargo against the contract on dock at destination.

Delivery resolution at destination dock:
- If `cargo[commodity_id] >= quantity` and `current_day <= deadline_day`: contract resolves SUCCESS. Player receives payout_credits. If the player visited route_waypoint_bonus_system_id during transit, route_waypoint_bonus_credits are added. Faction standing delta applied (`apply_reputation_with_spillover` per section 7).
- If `cargo[commodity_id] >= quantity` and `current_day > deadline_day` and `current_day <= deadline_day + 5`: contract resolves LATE. Payout reduced by `late_penalty_credits x (current_day - deadline_day)`. If adjusted payout falls below zero, player receives 0 and is additionally debited the cancellation_penalty_credits.
- If `current_day > deadline_day + 5`: contract auto-cancels. Player is debited cancellation_penalty_credits. Faction standing penalty applied.

### 4.3 Contract pool generation

The contract pool is generated against the current market simulation state at Nexus Prime / Commerce Guild faction pool. High-margin routes (where the commodity's destination price significantly exceeds its origin price) receive more contracts. Low-margin routes receive fewer. SA-F4 implements the generation algorithm; SA-F1 locks the structural schema.

### 4.4 Faction standing implications

| Contract faction | Success outcome | Late outcome | Cancellation outcome |
|---|---|---|---|
| `commerce_guild` | Commerce Guild standing +N | Commerce Guild standing +N/2 | Commerce Guild standing -N |
| `frontier_alliance` | Alliance standing +N | Alliance standing +N/2 | Alliance standing -N |
| Mixed-cargo (no faction_id) | No faction delta | No faction delta | No faction delta |

The delta N is proportional to contract payout. SA-F4 tunes the exact conversion rate; SA-F1 locks the directional rule.

### 4.5 In-flight tracking on the Player save

The Player save carries the full list of in-flight shipping contracts serialized as `ShippingContract.to_dict()`. Each contract's status field tracks: `AVAILABLE`, `IN_FLIGHT`, `COMPLETED`, `LATE_COMPLETED`, `CANCELLED`. SA-F4 authors the full ShippingContract model; section 8 of this document provides the `from_dict` migration snippet.

---

## 5. Insurance Sub-system

### 5.1 Premium formula

```
monthly_premium = ship_value x base_rate x combat_record_modifier x faction_standing_modifier
```

Where:
- `ship_value` = computed from `Ship.get_value()` (hull base value + module values)
- `base_rate` = 0.005 to 0.015 per game-month (exact tuned by SA-F5; recommended starting value 0.008)
- `combat_record_modifier` = based on ship destructions in the last 30 game-days:
  - 0 losses in last 30 days: 0.85 (clean record discount)
  - 1-2 losses in last 30 days: 1.00 (standard rate)
  - 3+ losses in last 30 days: 1.50 (high-risk surcharge)
- `faction_standing_modifier` = based on Nexus Prime / Commerce Guild standing tier:
  - Hostile: 1.50
  - Neutral (apprentice/regular): 1.00
  - Friendly (certified): 0.90
  - Patron: 0.85

Monthly premium is charged every 30 game-days. The charge triggers on the anniversary of the policy purchase date. If the player does not have enough credits on the charge day, the policy enters a 7-day grace period. If the premium remains unpaid after 7 days, the policy lapses.

### 5.2 Deductible tiers

The player selects a deductible tier at policy purchase. The tier cannot be changed mid-policy without cancelling and reacquiring:

| Tier name | Premium multiplier | Deductible (% of claim payout) |
|---|---|---|
| Low-coverage | 0.70 | 25% |
| Balanced | 1.00 | 10% |
| Full-coverage | 1.40 | 0% |

### 5.3 Claim flow (ship destruction)

When the player's ship is destroyed (`game.py` death/respawn path):
1. `game.py` checks `player.insurance_policies` for an active policy on the destroyed ship.
2. If no active policy: standard respawn (player may lose cargo, credits per existing system).
3. If active policy:
   a. Compute `claim_payout = ship_value x (1 - deductible_fraction) x recent_claims_modifier`.
   b. `recent_claims_modifier`: if the player has filed a claim in the last 60 game-days, payout is reduced by 0.15 (one prior claim) or 0.30 (two or more prior claims).
   c. Credit claim_payout to player.credits.
   d. Record the claim in the player's policy claim history.
   e. Respawn proceeds at nearest Commerce Guild station (or closest known station if no CG station accessible).

### 5.4 Lapse and reinstatement

- **Lapse trigger**: premium unpaid for 7 game-days after charge date.
- **Lapse effect**: policy transitions to LAPSED state; no claims can be filed.
- **Reinstatement**: player visits Meridian terminal and requests reinstatement. An Acumen skill check (difficulty 8) is required to pass a "clean inspection." If the player has an Acumen score >= 8 (effective_level >= difficulty, per the deterministic threshold system), reinstatement is granted and the premium is charged at the standard rate. If below threshold, reinstatement is declined; the player must wait 15 game-days and try again.

---

## 6. Market Manipulation Event Templates

### 6.1 Infrastructure decision

Manipulation events extend `GalaxyEvent` via a new `GalaxyEventType.MARKET_MANIPULATION` enum value and a `manipulation_subtype: str` field added to the `GalaxyEvent` dataclass. This keeps the existing lifecycle code (`is_active()`, `days_remaining()`, `to_dict()`, `from_dict()`, chaining via `chain_id`/`chain_step`) intact while adding the discrimination layer SA-F6 needs for per-template behaviour. **Decision locked. See Section 11, decision 9.**

The `manipulation_subtype` field is additive: `GalaxyEvent.from_dict()` reads it via `data.get("manipulation_subtype", "")`, defaulting to empty string for pre-SA-F6 saves.

### 6.2 Eight manipulation event templates

Each template is defined in `data/galaxy/manipulation_events.json` (SA-F6). SA-F1 specifies the template structure; SA-F6 authors the JSON.

**Template 1: cartel_pump**
- Trigger: GalaxyEventManager random generation; weight favors high-volume commodities; requires no active cartel_pump already in progress
- Market effect: target commodity price_modifier +0.30 at target system for 5-10 days
- Duration range: 5-10 game-days
- Faction implications: Commerce Guild standing -5 if player does not participate; +5 if player holds a long futures position on the commodity that settles during the event
- Player counter-mechanic: player with spread_trader L2 + futures_intel (Brix Tano) detects anomalous volume; can open a SHORT position before the peak; skill_check_threshold = speculator_premium_reduction total >= 0.15

**Template 2: supply_line_sabotage**
- Trigger: GalaxyEventManager chain from an existing LABOR_STRIKE event at a producing system; or standalone via weight roll
- Market effect: shutdown_tags populated with the producing system's primary production tag; affected commodities price raised by existing LABOR_STRIKE logic in Market._calculate_price()
- Duration range: 7-14 game-days
- Faction implications: Wreckers' Guild standing +3 if player holds salvage-related cargo during the event (implied contraband opportunity)
- Player counter-mechanic: player with shipping contract for the affected commodity can reroute via an alternate origin; waypoint bonus triggers if the alternate origin is visited; no skill check

**Template 3: false_news_pump**
- Trigger: GalaxyEventManager weight roll; low base weight; requires an active news ticker cycle
- Market effect: single commodity price_modifier +0.20 for 3 days, then price_modifier reverts to 0.0 (the event expires naturally)
- Duration range: 3 game-days fixed
- Faction implications: none
- Player counter-mechanic: player who waits until day 2 to open a SHORT benefits from the anticipated revert; futures_intel (Brix Tano) flags the pump as "short-duration anomaly" on day 1; skill_check_threshold = futures_intel bonus >= 1.0 (Brix Tano active)

**Template 4: short_squeeze**
- Trigger: fires when player futures volume on a single commodity exceeds 5 active contracts in the same direction; not a random event -- player behaviour triggers it
- Market effect: target commodity price_modifier +0.25 for the duration of the player's contract; if the player is SHORT, this punishes them
- Duration range: matches the player's active contract duration
- Faction implications: none
- Player counter-mechanic: player diversifies across multiple commodities to avoid triggering; detected retroactively by futures_intel on the day of the spike

**Template 5: regulatory_capture**
- Trigger: GalaxyEventManager weight roll; only fires at systems with a Commerce Guild faction presence
- Market effect: blocked_commodities populated with a single commodity; trading halted at target system for duration
- Duration range: 5-7 game-days
- Faction implications: Commerce Guild standing -10 for all players (galactic event); Frontier Alliance standing +5 if the player is not at a Commerce Guild station when it fires
- Player counter-mechanic: player who holds a futures SHORT on the blocked commodity before the event profits from the price disruption at adjacent systems; skill_check_threshold = spread_trader L1 (speculator_premium_reduction >= 0.05)

**Template 6: commodity_dumping**
- Trigger: GalaxyEventManager weight roll; targets systems with a specialty_import for the commodity
- Market effect: single commodity price_modifier -0.25 at target system for 7-10 days
- Duration range: 7-10 game-days
- Faction implications: frontier_alliance standing -5 if the dumped commodity is a frontier-produced resource
- Player counter-mechanic: player with a long shipping contract for the commodity before the event can cancel and absorb the cancellation_penalty to avoid delivering at a loss; or hold if the event ends before the shipping deadline

**Template 7: insider_leak**
- Trigger: only fires as a player-side detection event, not a market-side event; triggers when player has futures_intel bonus >= 1.0 AND there is an active cartel_pump or false_news_pump in the same system
- Market effect: none (detection only; the underlying event produces its own market effect)
- Duration range: 1 game-day (detection window)
- Faction implications: Commerce Guild standing +3 if player acts on the leak and files a "market irregularity report" at Meridian (SA-F3 authors this interaction)
- Player counter-mechanic: IS the counter-mechanic; triggers a special dialogue flag `manipulation_insider_detected` that gates Brix Tano banter in SA-X6

**Template 8: counter_manipulation**
- Trigger: player-initiated; requires active cartel_pump OR regulatory_capture in the current system; requires player credits >= 5,000 cr; requires spread_trader L1
- Market effect: player injects capital to counter the price distortion; price_modifier on the target commodity is reduced by 0.10 for 3 days
- Duration range: 3 game-days (effect window)
- Faction implications: Commerce Guild standing +8 if counter succeeds; -3 if the underlying event outlasts the counter window
- Player counter-mechanic: IS the mechanic; skill_check_threshold = speculator_premium_reduction total >= 0.10 (spread_trader L1 OR Brix Tano crew)

---

## 7. Cross-System Integration Commitments

### 7.1 Market

- SA-F2 reads `Market.get_price(commodity_id)` at settlement (`spacegame/models/market.py:311`, the `get_price()` method). No writes to Market from the futures system.
- SA-F6's manipulation events apply via `GalaxyEvent.price_modifiers` and `GalaxyEvent.blocked_commodities`, which `Market._calculate_price()` (`spacegame/models/market.py:180`) already processes in its galaxy event loop.
- No new market-write paths are introduced by SA-F2 through SA-F6.

### 7.2 Investment

- SA-F makes no reads or writes to `spacegame/models/investment.py`. Meridian is a parallel system.
- The per-system investment cards continue to operate through their existing `update_day()` hook. Meridian's futures/shipping/insurance systems use a separate update path.
- SA-F7 may reference investment portfolio state when computing financial crisis severity thresholds; SA-F7 owns that integration.

### 7.3 Game-day cycle

- Futures contract maturity ticks via the existing `update_day()` chain. SA-F2 hooks into the player's `update_day()` method to check `futures_state.active_contracts` for maturity.
- Shipping contract deadlines tick the same way. SA-F4 hooks into `update_day()` to check `shipping_contracts` for expiry.
- Insurance premium charges tick every 30 game-days per policy. SA-F5 hooks into `update_day()` to check `insurance_policies` for charge dates and lapse conditions.
- The `GalaxyEventManager` (or equivalent) already processes `galaxy_events` on `update_day()`. SA-F6's manipulation events register through the same path; SA-F6 does not introduce a separate event loop.

### 7.4 Skill tree

- `progression.get_bonus("speculator_premium_reduction")` is the read point for the spread_trader skill contribution. SA-F2's pricing engine calls this at offer generation time and at entry_cost computation time.
- No new bonus_types are introduced by SA-F2 through SA-F6. The `spread_trader` and `futures_intel` bonus_types are already wired by SA-C2 and SA-A2.

### 7.5 Crew

- `crew_roster.get_bonus("speculator_premium_reduction")` provides Brix Tano's 0.10 contribution.
- `crew_roster.get_bonus("futures_intel")` provides Brix Tano's detection flag (1.0 = active).
- Both are read by SA-F2's pricing engine and by SA-F6's manipulation detection logic.
- Stacking cap: total `speculator_premium_reduction` = skill (0-0.10) + crew (0-0.10) + any future edge-case contributions (up to 0.05), capped at 0.25. The cap is enforced in SA-F2's pricing engine.

### 7.6 Reputation

- Shipping contract delivery calls `apply_reputation_with_spillover` (or the equivalent standing update function) for the contract's `faction_id`.
- Futures settlement above a threshold payoff (> 5,000 cr profit) triggers a small Nexus Prime / Commerce Guild standing delta (+2 for the Exchange's "noteworthy client" record).
- Counter-manipulation success (template 8) triggers a Commerce Guild standing delta per section 6.2.
- SA-F4 and SA-F2 own the standing call sites; they use the existing reputation update infrastructure.

### 7.7 Combat

- Ship destruction triggers the insurance claim flow at `game.py`'s respawn path. SA-F5 inserts the claim check at the respawn handler.
- SA-F5 reads `player.insurance_policies` and the ship's `get_value()` at the time of destruction (before the ship is rebuilt/replaced).
- The existing combat record (number of losses in the last 30 game-days) is read from `player.ship_destruction_log` (or the nearest equivalent in the Player model; SA-F5 adds this field if it does not exist -- see section 8).

### 7.8 News

- Settlement payoffs above the headliner threshold fire `news_ticker.add_template_event("futures_headliner_settled", ...)`.
- Financial crisis onset (SA-F7) fires the crisis news template.
- Counter-manipulation success fires a brief market-irregularity-resolved template.
- All news template stubs are defined in section 9.3. Content is authored in SA-X5.

---

## 8. Save/Load Contract

### 8.1 New Player fields

All `from_dict()` reads use `data.get("field", default)` per CLAUDE.md migration discipline. Pre-SA-F2 saves have none of these keys; they load cleanly with safe defaults.

| Field | Type | Default | Description |
|---|---|---|---|
| `futures_state` | `FuturesState` | `FuturesState()` (empty) | Active and historical futures contracts |
| `shipping_contracts` | `list[ShippingContract]` | `[]` | In-flight and completed shipping contracts |
| `insurance_policies` | `list[InsurancePolicy]` | `[]` | Active and lapsed insurance policies |
| `ship_destruction_log` | `list[int]` | `[]` | Game-days of recent ship destructions; insurance reads last 30 entries |

### 8.2 Galaxy-level state

Manipulation events register on the existing GalaxyEventManager (or its equivalent list of active galaxy events). SA-F6 adds `manipulation_events` as a separate list on the game's event manager, or as a filtered sub-list of the existing `active_galaxy_events` -- SA-F6 decides based on GalaxyEventManager's actual structure. The save/load key is `manipulation_events`.

### 8.3 Literal from_dict snippets (paste these into Player.from_dict and GalaxyEventManager.from_dict)

```python
# In Player.from_dict() -- paste after existing field reads:
futures_data = data.get("futures_state", {})
self.futures_state = FuturesState.from_dict(futures_data)

shipping_data = data.get("shipping_contracts", [])
self.shipping_contracts = [ShippingContract.from_dict(s) for s in shipping_data]

insurance_data = data.get("insurance_policies", [])
self.insurance_policies = [InsurancePolicy.from_dict(p) for p in insurance_data]

self.ship_destruction_log = data.get("ship_destruction_log", [])
```

```python
# In GalaxyEventManager.from_dict() (or equivalent) -- paste after existing event reads:
manipulation_data = data.get("manipulation_events", [])
self.manipulation_events = [GalaxyEvent.from_dict(e) for e in manipulation_data]
```

This mirrors the pattern at `Market.load_supply_demand` (`spacegame/models/market.py:638`): `data.get("player_supply_demand", {})` with a safe dict default.

### 8.4 FuturesState fields

| Field | Type | Default | Description |
|---|---|---|---|
| `active_contracts` | `list[FuturesContract]` | `[]` | Contracts currently in-flight |
| `settled_contracts` | `list[FuturesContract]` | `[]` | Historical settled contracts |
| `total_credits_won` | `int` | `0` | Running total of profitable settlement payoffs |
| `total_credits_lost` | `int` | `0` | Running total of unprofitable settlement payoffs + entry costs |

### 8.5 ShippingContract status field

The `status` field on ShippingContract uses string values for readability in saves:
`"AVAILABLE"`, `"IN_FLIGHT"`, `"COMPLETED"`, `"LATE_COMPLETED"`, `"CANCELLED"`

Old saves that predate SA-F4 have no `shipping_contracts` key; `Player.from_dict()` handles this via `data.get("shipping_contracts", [])`.

---

## 9. Tutorial, Journal, News, Crew-Banter, and Achievement Stubs

### 9.1 First-time system tips (FirstTimeTipOverlay)

Overlays follow the onboarding design overlay style (declarative, terse, no flavor, dismiss button reads "Got it"). Reference: `requirements/onboarding_design.md` section 9a.

**Futures tip**
- Trigger flag: `futures_first_contract_previewed` (set in `spacegame/constants/flags.py` by SA-F2)
- Fires once on first preview of a futures contract at the Meridian terminal

```
"Strike price is set at offer. Spread is your entry cost.
At maturity, the market settles against the actual price.
Long = you bet it rises. Short = you bet it falls."
```

**Shipping contracts tip**
- Trigger flag: `shipping_first_contract_previewed` (set in `spacegame/constants/flags.py` by SA-F4)
- Fires once on first preview of a shipping contract

```
"Accept the contract, load the cargo, dock at destination before the deadline.
Late means reduced payout. Very late means a penalty on top.
The waypoint bonus pays if you stop there on the way."
```

**Insurance tip**
- Trigger flag: `insurance_terminal_first_opened` (set in `spacegame/constants/flags.py` by SA-F5)
- Fires once on first opening of the insurance terminal at Meridian

```
"Monthly premium covers your hull value against total loss.
Deductible comes out of any payout when you make a claim.
Seven days of missed premium lapses the policy."
```

**Market manipulation tip**
- Trigger flag: `manipulation_first_event_detected` (set in `spacegame/constants/flags.py` by SA-F6)
- Fires once when the player first observes an active manipulation event in the market view

```
"Manipulation events shift prices outside normal supply and demand.
Some are detectable early with the right crew.
Counter-manipulation requires capital and a Speculator track."
```

### 9.2 Journal entry templates

Journal entries are in the captain's-notebook register: first person, clipped, specific, no grand framing. Reference: `requirements/dialogue_writing_guide.md` and `requirements/aurelia_voice_examples.md`.

**Futures templates**

*First contract accepted*
```
Entry title: "Position Open"
Entry body:  "Opened a [LONG/SHORT] position on [COMMODITY] at [STRIKE_PRICE] cr.
              Maturity in [DURATION] days. Spread cost [ENTRY_COST] cr.
              [PRICE_HISTORY_TREND] was the read. We'll see if it holds."
```

*Contract settled -- profit*
```
Entry title: "Closed"
Entry body:  "Closed the [COMMODITY] position. Market settled at [SETTLEMENT_PRICE] cr.
              Payoff: [PAYOFF_AMOUNT] cr. Net after spread: [NET_AMOUNT] cr.
              [IF Brix active: Brix had the band right.]"
```

*Contract settled -- loss*
```
Entry title: "Closed at a Loss"
Entry body:  "Closed the [COMMODITY] position. Settled at [SETTLEMENT_PRICE] cr.
              Down [NET_AMOUNT] cr all in.
              The spread doesn't care which way it went."
```

**Shipping contract templates**

*Contract accepted*
```
Entry title: "Run Accepted"
Entry body:  "Picked up a [COMMODITY] contract for [FACTION_DISPLAY].
              [ORIGIN_SYSTEM] to [DESTINATION_SYSTEM], [QUANTITY] units, [PAYOUT_CREDITS] cr.
              Deadline: day [DEADLINE_DAY]."
```

*Delivery completed on time*
```
Entry title: "Delivered"
Entry body:  "Got the [COMMODITY] to [DESTINATION_SYSTEM] on time.
              Payout: [PAYOUT_CREDITS] cr. [FACTION_DISPLAY] standing adjusted."
```

*Delivery completed late*
```
Entry title: "Late Delivery"
Entry body:  "Got the [COMMODITY] to [DESTINATION_SYSTEM].
              Not by day [ORIGINAL_DEADLINE]. Late penalty: [LATE_PENALTY_CREDITS] cr.
              Accepted [ADJUSTED_PAYOUT] cr."
```

**Insurance templates**

*Policy purchased*
```
Entry title: "Policy Registered"
Entry body:  "Hull policy active at Meridian. Covers up to [INSURED_VALUE] cr.
              Monthly premium: [MONTHLY_PREMIUM] cr. Deductible: [DEDUCTIBLE_PCT]%."
```

*Claim filed and paid*
```
Entry title: "Claim Paid"
Entry body:  "Filed a claim. Loss confirmed. Payout after deductible: [CLAIM_PAYOUT] cr.
              Premium adjusts at next renewal."
```

*Policy lapsed*
```
Entry title: "Policy Lapsed"
Entry body:  "Seven days past due. Policy lapsed.
              Need a clean inspection to reinstate. Flying uncovered until that clears."
```

**Market manipulation templates**

*Manipulation event detected by crew (Brix Tano active)*
```
Entry title: "Anomalous Volume"
Entry body:  "Brix flagged [COMMODITY] at [SYSTEM_ID] as outside normal parameters.
              Probability band shifted. Could be a play or could be noise."
```

*Manipulation event confirmed public*
```
Entry title: "[MANIPULATION_SUBTYPE_DISPLAY] Confirmed"
Entry body:  "[COMMODITY] prices at [SYSTEM_ID] affected.
              Exchange estimates [DURATION_ESTIMATE] more days of disruption."
```

*Counter-manipulation executed*
```
Entry title: "Counter Position Taken"
Entry body:  "Put [CAPITAL_AMOUNT] cr against the [MANIPULATION_SUBTYPE_DISPLAY] at [SYSTEM_ID].
              If the event resolves on schedule, the position recovers."
```

### 9.3 News ticker headline templates

Headlines under 80 characters after substitution. Reference: `requirements/dialogue_writing_guide.md`.

**Futures templates**

```
"[COMMODITY] futures position closed at Meridian. Settlement: [AMOUNT] cr."
"Meridian logs [N] open futures positions across [N] commodities this cycle."
"Exchange headliner: [COMMODITY] contract settles at [AMOUNT] cr."
```

**Shipping contract templates**

```
"[FACTION_SHORT] shipping contracts posted. [N] routes available."
"Delivery confirmed: [COMMODITY], [ORIGIN] to [DESTINATION]."
"Late delivery penalty applied on [COMMODITY] contract. Route: [ORIGIN]-[DESTINATION]."
```

**Insurance templates**

```
"Hull policy issued at Meridian Exchange. Value: [AMOUNT] cr."
"Insurance claim processed at Meridian. Payout: [AMOUNT] cr."
"Policy lapse recorded at Meridian Exchange. Reinstatement required."
```

**Market manipulation templates**

```
"Market irregularity detected at [SYSTEM_ID]. Cause under review."
"[COMMODITY] prices at [SYSTEM_ID] shift [N]%. Exchange monitoring."
"[MANIPULATION_SUBTYPE_DISPLAY] event ends at [SYSTEM_ID]. Prices stabilising."
```

### 9.4 Crew-banter trigger flags

These flags are set by the SA-F2 / SA-F4 / SA-F5 / SA-F6 systems and read by the crew banter system (SA-X6). SA-F2/F4/F5/F6 register them in `spacegame/constants/flags.py`.

| Flag name | Set when |
|---|---|
| `futures_first_contract_accepted` | Player accepts first futures contract at Meridian |
| `futures_first_win` | Player's first profitable futures settlement |
| `futures_first_loss` | Player's first unprofitable futures settlement |
| `shipping_first_contract_accepted` | Player accepts first shipping contract |
| `shipping_first_late_delivery` | Player delivers a shipping contract past deadline |
| `insurance_policy_purchased` | Player purchases first insurance policy |
| `insurance_first_claim` | Player files first insurance claim after ship destruction |
| `manipulation_event_detected_by_crew` | Brix Tano flags anomalous price movement (futures_intel >= 1.0 active) |
| `manipulation_counter_executed` | Player executes a successful counter-manipulation trade |
| `financial_crisis_threshold_approaching` | Internal trigger for SA-F7 crisis onset; set by SA-F7's volatility monitor |

SA-X6 authors the actual banter dialogue that these flags gate.

### 9.5 Achievement stub identifiers

SA-X7 authors full achievement content. SA-F1 establishes the stub IDs that SA-F2 / SA-F4 / SA-F5 / SA-F6 register.

| Achievement ID | Condition |
|---|---|
| `achievement_futures_first_win` | First profitable futures contract settlement |
| `achievement_futures_speculator` | Close 5 profitable futures contracts |
| `achievement_futures_short_master` | Close 3 profitable SHORT contracts |
| `achievement_shipping_on_time` | Complete 10 shipping contracts without a late delivery |
| `achievement_shipping_waypoint_bonus` | Collect 5 route-quality waypoint bonuses |
| `achievement_insurance_claimed` | Recover from ship destruction via insurance payout |
| `achievement_counter_manipulator` | Execute a successful counter-manipulation trade |
| `achievement_meridian_patron` | Reach Patron standing tier with Commerce Guild |

### 9.6 Sample Ilse Vey lines (voice-checked, SA-F3 uses these as starting points)

These lines follow Ilse Vey's voice sheet (`requirements/character_voices.md:1470-1511`): institutional gatekeeping with polish, "Your record" framing, refers to the Exchange as a separate entity, formal but not cold.

*Contract terminal introduction*:
"Your record shows you've moved cargo across the Expanse. That's a foundation. What we deal in here is exposure, not delivery. You're agreeing to a position. Take your time with the terminal. The contracts aren't going anywhere."

*After first settlement (profitable)*:
"Settlement came in on the right side. Your record here has its first line. That's what the Exchange uses to calibrate what we offer you next."

*After first settlement (loss)*:
"Settlement came in on the wrong side. That happens. Your record shows you accepted a structured risk and saw it through. That's what we're looking for, actually."

---

## 10. Open Items Deferred to Downstream Sprints

The following items are explicitly deferred. Downstream sprint agents do not need human approval to resolve them; they are within each sprint's scope.

1. **Exact base insurance rate** (range 0.005-0.015 per game-month specified; exact starting value): deferred to SA-F5 tuning pass. Recommended default 0.008 per game-month.

2. **Exact financial-crisis trigger thresholds** (market-volatility threshold + active-manipulation-event count + player-futures-volume): deferred to SA-F7. SA-F7 owns the numeric constants; section 11 decision 4 locks the structural form.

3. **UI panel dimensions and layout for the Meridian contract terminal**: deferred to SA-F3. SA-F3 owns the MeridianView implementation.

4. **Secondary Meridian broker NPC voice content beyond Ilse Vey**: deferred to SA-F3. SA-F3 may introduce a junior broker and a senior partner; voice sheets for any new named characters must meet `requirements/character_voices.md` standards.

5. **Sound design for settlement-win and contract-default audio events**: deferred to SA-X9. SA-F2 wires audio hook placeholders; SA-X9 delivers audio assets.

6. **Exact wording of secondary journal entries** beyond the templates in section 9.2: deferred to the implementing sprint. Each implementing sprint voice-checks final wording against the Writing Bible scanner before commit.

7. **Recurring Meridian rival speculator NPC** (analogous to Prentiss/Kade/Salko in the auction system): deferred to SA-F3. SA-F3 decides whether to introduce a named recurring rival at the contract terminal and authors the CaptainMemory integration if so.

8. **Exact manipulation_subtype content for advanced templates** beyond the 8 defined in section 6.2: deferred to SA-F6. Section 6 defines all 8 templates; SA-F6 may add up to 2 additional templates if playtesting reveals coverage gaps.

9. **Meridian venue visual identity** (background art, lighting, signature UI elements): deferred to SA-X10. SA-F3 ships a functional venue; SA-X10 applies per-venue visual identity.

10. **Exact salvo of crew banter content for each flag** in section 9.4: deferred to SA-X6. SA-X6 authors banter content for all flags listed; no individual sprint before SA-X6 writes banter lines.

11. **Insurance claim adjudication dialogue from Ilse Vey**: deferred to SA-F5. SA-F5 authors the 2-3 dialogue lines Ilse Vey delivers when a claim is processed; these must pass voice-sheet and Writing Bible compliance.

12. **Crisis arc scripted beat content** (the tutorial-scripted first crisis): deferred to SA-F7. SA-F7 authors the full `data/missions/crisis_arc.json` content.

---

## 11. Locked Decisions

The following decisions are locked. SA-F2 and all downstream sprints do not re-litigate them.

1. **Futures settlement uses real Market.get_price() at maturity; no proxy, no projection.**
   Rationale: the SA-F1 goal explicitly requires the system to "feel honest against the existing market simulation." A simulated projection creates a parallel pricing model that drifts from what the player can verify on the trade terminal. The player would experience this as arbitrary outcomes rather than earned prediction.
   Source: `requirements/station_anchors.md:172` ("must feel honest against the existing market simulation").

2. **Contract granularity: per-(commodity, system) integer-unit with a 20-unit minimum.**
   Rationale: matches `market.py`'s per-commodity per-system integer-quantity model. Fractional units would introduce bookkeeping mismatches. The 20-unit minimum prevents trivial fishing contracts.
   Source: `spacegame/models/market.py:425` (`record_buy(commodity_id: str, quantity: int)` -- quantities are integers throughout the market trading surface).

3. **Insurance premium formula: multiplicative product of ship_value, base_rate, combat_record_modifier, faction_standing_modifier.**
   Rationale: the three-axis model reflects the three integration commitments from `requirements/station_anchors.md:180-186` ("Tied to ship value, combat record, and faction standing"). A single-axis premium would underuse the existing combat record and faction standing systems.
   Source: `requirements/station_anchors.md:186`.

4. **Financial crisis (SA-F7): generated under conditions with one tutorial-scripted first fire.**
   Rationale: a single scripted crisis reduces the late-game financial system to "wait for the scripted event." The generated form lets the player's investment in futures + insurance + shipping create real systemic exposure. The scripted first-fire teaches the crisis loop without removing emergent recurrence.
   Source: `requirements/station_anchors.md:254` (open question -- "Recommendation lockable in SA-F1").

5. **Existing per-system investment.py cards are unchanged; Meridian is the parallel higher tier.**
   Rationale: `requirements/station_anchors.md` integration commitment "Existing investment is the lower tier; Meridian is the higher tier." `requirements/investment_rewards_design.md:40` confirms Phase V supersedes the stub for Meridian only, not for per-system cards.
   Source: `requirements/investment_rewards_design.md:40`.

6. **Speculator skill + crew bonus: additive, capped at -0.25 total speculator_premium_reduction.**
   Rationale: skill max 0.10 + crew max 0.10 = 0.20 base combined; cap at 0.25 allows edge-case festival/event-driven discounts without enabling degenerate stacking with future Speculator-themed crew.
   Source: `requirements/sa_skill_design.md:92` (magnitude rationale for spread_trader, bonus_per_level 0.05, max level 2, combined max 0.20).

7. **Reputation gating: Nexus Prime / Commerce Guild standing tiers (apprentice, regular, certified, patron) gate contract sizes.**
   Rationale: mirrors the Stellaris Port pattern established in SA-B1 decision 8. The player already understands the tier shape from the auction system; Meridian applying the same shape is coherent.
   Source: `requirements/station_anchors.md:185` ("Nexus Prime standing gates contract sizes"); SA-B1 section 1.5.

8. **Settlement window range: 7 to 21 game-days; player picks at acceptance.**
   Rationale: 7 days is the lower bound matching `PriceHistory.max_days = 7`; shorter means the player has no price history to compare against. 21 days is the upper bound; longer outpaces the market simulation's meaningful drift.
   Source: `spacegame/models/market.py:29` (`PriceHistory.max_days = 7`).

9. **Market manipulation taxonomy: extend GalaxyEvent with GalaxyEventType.MARKET_MANIPULATION enum value + manipulation_subtype: str field.**
   Rationale: `GalaxyEvent` already has chaining, duration tracking, system targeting, price modifiers, and blocked commodities -- every primitive a manipulation event needs. A separate event class duplicates lifecycle code and forces `Market._calculate_price()` to handle two parallel event types. The subtype field keeps JSON content authoring clean.
   Source: `spacegame/models/galaxy_event.py:26-65` (GalaxyEventType enum and GalaxyEvent fields).

10. **investment_rewards_design.md open threads are explicitly out of SA-F scope.**
    Rationale: all five open threads in `requirements/investment_rewards_design.md` (pacing, cross-system intersection, narrative beats, risk dimension, tier visibility) concern the existing per-system investment cards. SA-F adds Meridian on top; it does not modify the lower tier. Conflating them would balloon SA-F's scope significantly.
    Source: `requirements/investment_rewards_design.md:19-25` (open threads); line 40 (sister-doc scope fence).

---

## 12. Hand-off Map

| Downstream sprint | Sections to read | Notes |
|---|---|---|
| SA-F2 (Futures Core) | 1, 2, 3, 7, 8, 9, 11 | Section 3.3 defines the exact Market.get_price() settlement call. Section 7.1 names the market read-only constraint. Section 8.3 provides the literal from_dict snippets to paste. Section 9.4 lists flags SA-F2 must register in constants/flags.py. |
| SA-F3 (Meridian Venue + Cargo Broker graduation) | 1, 2, 7, 9, 11 | Section 9.6 provides Ilse Vey sample lines as starting points. Section 1.5 names the SA-V graduation_pointer node SA-F3 must not modify. Section 9.1 provides the futures FirstTimeTipOverlay copy SA-F3 surfaces on first contract terminal visit. |
| SA-F4 (Shipping Contracts sub-system) | 1, 4, 7, 8, 9, 11 | Section 4 is SA-F4's primary input. Section 4.2 defines the full delivery resolution flow. Section 8.3 provides the shipping_contracts from_dict snippet. Section 9.4 lists the shipping banter flags SA-F4 must register. |
| SA-F5 (Insurance sub-system) | 1, 5, 7, 8, 9, 11 | Section 5 is SA-F5's primary input. Section 5.4 defines lapse and reinstatement. Section 7.7 names the game.py respawn integration point. Section 8.3 provides the insurance_policies from_dict snippet. |
| SA-F6 (Market Manipulation threats) | 1, 6, 7, 8, 9, 11 | Section 6 is SA-F6's primary input. Section 6.1 specifies the GalaxyEventType.MARKET_MANIPULATION enum extension. Section 11 decision 9 locks the taxonomy. Section 8.3 provides the manipulation_events from_dict snippet. |
| SA-F7 (Financial Crisis Event Arc) | 1, 2, 4, 5, 6, 7, 9, 11 | Section 2 (futures lifecycle) and sections 4, 5, 6 (sub-system state at crisis time) inform the crisis arc design. Section 11 decision 4 locks the generated-under-conditions structure. Section 9.4 flag `financial_crisis_threshold_approaching` is SA-F7's internal trigger. |
| SA-X1 (Cross-anchor narrative threading) | 9 | Section 9.4 (crew banter flags) and 9.6 (Ilse Vey sample lines) inform cross-anchor dialogue insertions. |
| SA-X3 (Tutorial integration) | 9 | Section 9.1 provides the four FirstTimeTipOverlay stubs SA-X3 integrates into the tutorial chain. |
| SA-X5 (News Ticker integration) | 9 | Section 9.3 provides the twelve news ticker template stubs SA-X5 expands to full ticker content. |
| SA-X6 (Crew Reactions / Anchor Banter) | 9 | Section 9.4 lists all crew banter trigger flags; SA-X6 authors banter content for each. |
| SA-X7 (Achievement Pass) | 9 | Section 9.5 lists the eight stub achievement IDs; SA-X7 authors full achievement metadata and unlock conditions. |
