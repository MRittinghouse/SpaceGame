# SA-P6 Politics Tuning Report

**Sprint:** SA-P6 — Politics polish + tuning  
**Date:** 2026-04-27  
**Author:** Implementation agent  
**Scope:** All 21 dispute templates across three venues (Verdant Mayors' Council, Haven's Rest Congress Hall, Crimson Reach Wreckers' Guild)

---

## 1. Per-Template Audit Table

| Template ID | Venue | D | R | Arc | Difficulty | Deadline | Win Rep (primary) | Loss Rep (primary) | Mkt Durations (win) | Max Mag |
|---|---|---|---|---|---|---|---|---|---|---|
| water_rights_phasing | Verdant | 4 | 3 | No | 4 | 10 | +5 (frontier_alliance) | -2 | 30, 30 | 0.10 |
| aquifer_concession_renewal | Verdant | 4 | 3 | No | 5 | 12 | +4 (frontier_alliance) | -3 | 30, 20 | 0.12 |
| infrastructure_co_op_vote | Verdant | 4 | 5 | Yes | 4 | 18 | +4 (frontier_alliance) | -2 | 30, 25 | 0.10 |
| forgeworks_partnership_extension | Verdant | 4 | 3 | No | 4 | 12 | +3 (frontier_alliance) | -1 | 25, 20 | 0.08 |
| co_op_dividend_distribution | Verdant | 4 | 3 | No | 3 | 10 | +3 (frontier_alliance) | -2 | 28 | 0.10 |
| hydroponics_yield_quota | Verdant | 4 | 3 | No | 4 | 11 | +3 (frontier_alliance) | -2 | 30, 20 | 0.12 |
| settler_food_credit_dispute | Verdant | 4 | 3 | No | 3 | 9 | +3 (frontier_alliance) | -2 | 25, 18 | 0.08 |
| frontier_trade_route_levy | Verdant | 4 | 5 | Yes | 4 | 20 | +4 (frontier_alliance) | -2 | 30, 25 | 0.10 |
| cross_settlement_tariff_review | Alliance | 4 | 3 | No | 4 | 12 | +4 (frontier_alliance) | -2 | 30, 25 | 0.10 |
| frontier_trade_unification_act | Alliance | 4 | 5 | Yes | 5 | 24 | +6 (frontier_alliance) | -3 | 30, 30, 25 | 0.12 |
| crimson_response_protocol_review | Alliance | 4 | 3 | No | 4 | 12 | +4 (frontier_alliance) | -2 | 25, 20 | 0.08 |
| frontier_security_compact | Alliance | 4 | 5 | Yes | 5 | 22 | +5 (frontier_alliance) | -3 | 30, 25, 20 | 0.10 |
| infrastructure_capital_pool | Alliance | 4 | 3 | No | 4 | 14 | +4 (frontier_alliance) | -2 | 30, 25 | 0.10 |
| cross_settlement_logistics_overhaul | Alliance | 4 | 3 | No | 4 | 12 | +3 (frontier_alliance) | -2 | 22, 22 | 0.06 |
| cross_settlement_water_compact | Alliance | 4 | 3 | No | 4 | 14 | +5 (frontier_alliance) | -2 | 30, 28, 25 | 0.10 |
| annual_alliance_congress | Alliance | 4 | 5 | Yes (annual) | 5 | 28 | +8 (frontier_alliance) | -4 | 40, 30, 30 | 0.12 |
| salvage_rights_phasing | Reach | 4 | 3 | No | 4 | 10 | +4 (crimson_reach) | -3 | 28, 25 | 0.10 |
| outsider_salvage_concession | Reach | 4 | 3 | No | 3 | 12 | +5 (crimson_reach) | -3 | 30, 20 | 0.08 |
| wrecker_loyalty_oath_dispute | Reach | 4 | 3 | No | 4 | 8 | +4 (crimson_reach) | -3 | 25, 20 | 0.08 |
| debris_field_territory_claim | Reach | 4 | 5 | Yes | 5 | 14 | +5 (crimson_reach) | -4 | 35, 30 | 0.12 |
| gray_market_goods_provenance | Reach | 4 | 3 | No | 3 | 7 | +4 (crimson_reach) | -3 | 28, 20 | 0.09 |

**Column key:** D = delegates, R = rounds, Arc = campaign arc, Deadline = deadline_days, Win Rep = win outcome primary faction rep delta, Max Mag = highest absolute market shift magnitude across all outcome rows.

---

## 2. Out-of-Range Findings

Three values exceeded the initial spec ranges. All three are intentional design decisions locked before SA-P6 began. They are documented here so future tuners have an audit trail.

### 2a. Annual Alliance Congress — Win Rep Delta = +8

**Spec expectation (AC 8 draft):** win-row rep_delta abs ≤ 6 for all templates.  
**Observed:** `annual_alliance_congress` win row: `frontier_alliance = +8`.  
**Ruling:** Intentional. Annual Congress is a once-per-year event with 5 rounds and a 28-day deadline. The +8 cap is the high-water mark for any template in the game and is explicitly locked in the ROADMAP locked-decisions block. The balance test cap for campaign arcs is 8 (not 6).

### 2b. Annual Alliance Congress — Win Market Shift Duration = 40 days

**Spec expectation (AC 8 draft):** every market_shift duration ≤ 30.  
**Observed:** `annual_alliance_congress` win row: first shift duration = 40 days.  
**Ruling:** Intentional. Annual Congress win triggers a major market realignment lasting approximately two in-game weeks past the longest standard template. The global duration cap in the balance test is 42 (not 30), with this value as the validated maximum.

### 2c. debris_field_territory_claim — Campaign Arc Deadline = 14 days

**Spec expectation:** campaign arcs should have "extended" deadlines vs standard templates.  
**Observed:** `debris_field_territory_claim` deadline_days = 14, matching the upper bound of standard templates (7–14).  
**Ruling:** Intentional pressure mechanic. A 5-round arc with a tight 14-day deadline forces the player to prioritize corridor work. This is the Reach's defining tension: high stakes, short window, Guild tier gates compound the pressure. Balance test accepts arcs in [5, 35].

---

## 3. Locked Balance Baseline

**Design §6.3 worked-example math (canonical fairness baseline):**

> Persuasion 3 + framing-match (+1) + neutral disposition (0) + no crew bonus (0) + no skill bonus (0)
> = `floor(3 + 1 + 0 + 0 + 0) = 4`
> A base_difficulty-4 argument passes exactly at threshold.

**Operational acceptance metric:** A Persuasion-3 / no-crew player with a framing-match must be able to pass a base_difficulty-4 argument under neutral disposition. No template may ship with base_difficulty > 5 unless at least one framing in `eligible_framings` offers a +1 modifier path for the primary framing dimension.

The following ranges are the validated baseline after SA-P6. Any value outside these ranges introduced by future content must be called out in a new tuning report entry.

| Property | Standard templates | Campaign arcs | Annual Congress |
|---|---|---|---|
| Delegate count | 3–6 | 3–6 | 3–6 |
| Round count | 3 | 5 | 5 |
| Deadline days | 5–20 | 5–35 | 28 (locked) |
| Base difficulty | 1–7 | 1–7 | 5 (locked) |
| Win rep primary (abs) | 1–6 | 1–8 | 8 (locked) |
| Loss rep primary (abs) | 1–5 | 1–6 | 4 |
| Market shift duration | 14–32 | 14–42 | 40 max (locked) |
| Market shift magnitude abs | 0.01–0.15 | 0.01–0.15 | 0.12 |

Ordinal rep invariant: `win ≥ partial_win_off_record ≥ partial_win_coalition_thin` for the primary faction in every template. Verified across all 21 templates.

All three venues have at least one campaign arc. Verdant has two (infrastructure_co_op_vote, frontier_trade_route_levy). Alliance has four (including the Annual Congress). Reach has one (debris_field_territory_claim).

---

## 4. Next-Tuning-Pass Criteria

The following issues are noted but deferred to a future pass (SA-X10 or a dedicated balance sprint).

### 4a. forgeworks_partnership_extension — partial_win_coalition_thin has no market shifts

The `forgeworks_partnership_extension` template has an empty market_shifts tuple for the `partial_win_coalition_thin` row. This is the only template where a partial win outcome has no market consequence. The balance test permits empty market_shifts for partial-win rows but requires at least one shift for the win and loss rows. Flag for authoring review: add at least one modest shift (magnitude 0.03–0.05, duration 14–18) to the partial_win_coalition_thin row.

### 4b. Reach deadline cluster tightness

Three of five Reach templates have deadlines of 7–10 days (gray_market: 7, wrecker_loyalty: 8, salvage_rights: 10). Combined with the tier gate for apprentice players (all buttons disabled) this creates a very punishing first-session experience. Consider raising gray_market to 10 and wrecker_loyalty to 11 in a future pass.

### 4c. Alliance difficulty uniformity

Eight of eight Alliance standard templates have `base_difficulty = 4`. While this gives consistent challenge, it removes meaningful difficulty differentiation. A future pass should vary difficulty in the range [3, 5] across the non-arc templates (cross_settlement_logistics_overhaul would be a natural candidate for difficulty 3 given its cooperative framing).

### 4d. Counter-framing coverage at Reach

`debris_field_territory_claim` counter_framing for `field_drosa` has only one element: `["salvage_precedent"]`. Other delegates with betrayal conditions have two or more. Consider adding a second counter-framing dimension for field_drosa to give the player more options to preempt the betrayal.
