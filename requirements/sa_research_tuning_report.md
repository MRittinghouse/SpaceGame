# SA-R3 Research Patronage Tuning Report

**Sprint:** SA-R3 — Research Patronage polish  
**Date:** 2026-04-29  
**Author:** SA-R3 implementation agent

---

## 1. Methodology

All 10 `OkaforProjectTemplate` instances were audited against locked numeric ranges
enforced by `tests/test_models/test_okafor_template_balance.py` (126 parametric tests).
The audit checks:

- `risk_tier` ∈ `{"low", "mid", "high"}`
- `base_cost_credits` within tier-locked band
- `base_duration_days` within tier-locked band
- `base_success_payout / base_cost_credits` ∈ `[1.5, 4.5]`
- `base_failure_odds` == `FAILURE_ODDS[risk_tier]` (deterministic constant)
- `faction` ∈ `{"science_collective", "frontier_alliance", "miners_union"}`
- `outcome_unlock_type` ∈ `{"", "module", "upgrade", "commodity"}`
- Ethics keyset matches `OKAFOR_PROJECT_TEMPLATES` keyset
- Ethics tally: `{"heal": 3, "profit": 4, "neutral": 3}`
- Tier tally: `{"low": 4, "mid": 4, "high": 2}`

Expected value formula used below:

```
EV = (1 - failure_odds) × payout + failure_odds × (cost × refund_rate) − cost
```

Refund rates after SA-R3 Decision 1: low=0.50, mid=0.30, high=0.20.

---

## 2. Per-Template Audit Table

| ID | Tier | Cost (CR) | Dur (d) | Payout (CR) | P/C ratio | Fail% | Refund% | EV (CR) | Ethics | Faction |
|----|------|-----------|---------|-------------|-----------|-------|---------|---------|--------|---------|
| low_protein_folding_replication | low | 8,000 | 6 | 14,000 | 1.75 | 5% | 50% | 5,500 | neutral | sci |
| low_archive_recovery | low | 10,000 | 8 | 18,000 | 1.80 | 5% | 50% | 7,350 | neutral | sci |
| low_meta_analysis_pediatric | low | 12,000 | 7 | 20,000 | 1.67 | 5% | 50% | 7,300 | heal | frt |
| low_industrial_dust_filtration | low | 9,000 | 6 | 16,000 | 1.78 | 5% | 50% | 6,425 | profit | mnu |
| mid_neural_synthesis_protocol | mid | 28,000 | 12 | 70,000 | 2.50 | 18% | 30% | 30,912 | neutral | sci |
| mid_orbital_propulsion_efficiency | mid | 32,000 | 14 | 80,000 | 2.50 | 18% | 30% | 35,328 | profit | sci |
| mid_field_clinic_supply_chain | mid | 24,000 | 10 | 60,000 | 2.50 | 18% | 30% | 26,496 | heal | frt |
| mid_alloy_corrosion_mining_belt | mid | 26,000 | 11 | 65,000 | 2.50 | 18% | 30% | 28,704 | profit | mnu |
| high_quantum_sensor_capstone | high | 85,000 | 22 | 240,000 | 2.82 | 35% | 20% | 76,950 | profit | sci |
| high_post_outbreak_vaccine_synthesis | high | 120,000 | 28 | 320,000 | 2.67 | 35% | 20% | 96,400 | heal | frt |

Faction abbreviations: sci = science_collective, frt = frontier_alliance, mnu = miners_union.

All 10 templates pass the locked-range checks. No adjustments required.

---

## 3. Applied Changes (SA-R3)

### 3.1 Tier-aware failure refund (Decision 1)

**Before:** flat `FAILURE_REFUND_RATE = 0.30` for all tiers.

**After:**
```python
FAILURE_REFUND_RATES: dict[str, float] = {"low": 0.50, "mid": 0.30, "high": 0.20}
```

Rationale: low-risk projects rarely fail; a larger refund keeps early-game players
solvent. High-risk projects carry a larger expected margin; a smaller refund maintains
stakes and discourages treat-high-tier-as-a-hedge behaviour.

EV impact vs. flat 30% refund:

| Tier | Old refund% | New refund% | EV delta per 1 CR cost |
|------|------------|------------|----------------------|
| low  | 30% | 50% | +0.05 × fail_odds = +0.0025 CR / CR |
| mid  | 30% | 30% | 0 (unchanged) |
| high | 30% | 20% | −0.10 × fail_odds = −0.035 CR / CR |

For the highest-cost high template (120,000 CR, 35% fail):
old refund = 12,600 CR; new refund = 8,400 CR; loss on failure increases by 4,200 CR.
This is intentional — high risk should sting.

### 3.2 `kweon_relationship` mission reward type

Added `resolve_mission_rewards` branch in `spacegame/models/mission.py`.
Reward is a no-op when `player.okafor_research_state is None` (SA-R3 Decision 7).
Wired to `okafor_legacy_clinic_run` (fourth reward, `amount: 1`).

### 3.3 Kweon post-clinic-run callback dialogue tree

New tree `kweon_legacy_post_clinic_run` (4 nodes) in `data/dialogue/dialogues.json`.
Register: `flags.okafor_legacy_clinic_callback_seen()`.
Priority chain in `_kweon_dialogue_id()`: failure_debrief > post_clinic_run >
pending_legacy_beat > ambient.
Register fires in `_close_active_dialogue()` via `_LEGACY_ARC_TREE_TO_FLAG`.

Voice register: institutional-fatigue (not rare-warmth — reserved for heal-ending).
No em-dashes. No banned phrases.

### 3.4 Team-fund collaborator picker modal (SA-R1-FOLLOW-2 closure)

Replaces `self._fund_project(tid, collaborators=["dr_iris_navarro"])` stub.
Picker: checkbox rows for each docked researcher (3 permanent + Nuri when crewed),
cap enforced at 2 collaborators (`TEAM_FUND_MAX_COLLABORATORS`), live math display
(cost / duration update per toggle), Confirm/Cancel buttons.
Confirm with 0 selections = solo fund (SA-R3 Decision 5).

---

## 4. Royalty Break-Even Math

```
Royalty per interval = ROYALTY_RATE × payout = 0.05 × payout
Royalty interval     = ROYALTY_INTERVAL_DAYS = 10 days
Sell lump sum        = SELL_LUMP_SUM_RATE × payout = 0.60 × payout

Break-even intervals = 0.60 / 0.05 = 12 intervals = 120 days
```

Licensing beats selling at any payout if the player holds the patent for more than
120 days after success. The break-even is payout-independent.

Concrete examples:

| Template | Payout | Royalty / 10d | Sell lump | Break-even |
|----------|--------|---------------|-----------|-----------|
| low_protein_folding_replication | 14,000 | 700 CR | 8,400 CR | 120 d |
| mid_neural_synthesis_protocol | 70,000 | 3,500 CR | 42,000 CR | 120 d |
| high_quantum_sensor_capstone | 240,000 | 12,000 CR | 144,000 CR | 120 d |

Player guidance (implicit in game): sell for immediate liquidity; license for
passive income if game-time horizon exceeds ~4 months in-game.

---

## 5. Skip List

### 5.1 Numeric categories examined, no adjustments made

| Category | Decision | Rationale |
|----------|----------|-----------|
| Project costs (`base_cost_credits`) | Locked at SA-R1 ranges; no change | All 10 templates within locked bands ([5k–15k] / [20k–35k] / [70k–125k]); SA-X2 owns the cross-anchor balance pass. |
| Duration days (`base_duration_days`) | Locked; no change | Deterministic resolution math (slot-window length, royalty cadence) depends on these values; changing them without a coordinated balance pass would shift the whole passive-income curve. |
| Royalty rate / interval (`ROYALTY_RATE = 0.05`, `ROYALTY_INTERVAL_DAYS = 10`) | Locked; no change | Passive-income economy is intentionally slow (120-day break-even vs. lump-sum). SA-X2 owns any deeper royalty tuning. |
| Sell lump-sum rate (`SELL_LUMP_SUM_RATE = 0.60`) | Locked; no change | Matches the "immediate cash vs. patient income" intentional curve; lump-sum at 60% payout preserves the trade-off without a playtest signal to justify movement. |
| Team-fund cost / duration multipliers (`TEAM_FUND_COST_PER_COLLABORATOR = 0.50`, `TEAM_FUND_DURATION_PER_COLLABORATOR = 0.70`) | Locked at SA-R1 values; no change | The picker UI delivered this sprint exposes the previously-unreachable 2-collaborator math; the multipliers are now reachable and can be playtested before SA-X2 considers adjustment. |

**Hand-off to SA-X2.** Cross-anchor reputation balance, including any global review of the Research Patronage numeric ranges in the context of all other anchors (Politics, Bidding, Wreckers' Guild, Deep Shafts), is owned by SA-X2.

### 5.2 Test coverage deferred

| Item | Affected templates | Blocking reason |
|------|-------------------|-----------------|
| `outcome_unlock_id` data-existence check | mid_neural_synthesis_protocol, mid_orbital_propulsion_efficiency, mid_field_clinic_supply_chain, mid_alloy_corrosion_mining_belt, high_quantum_sensor_capstone, high_post_outbreak_vaccine_synthesis | SA-R1 stub IDs (advanced_sensor_array, efficient_thrusters, medical_supplies, alloy_composite) do not yet exist in data files. Test would check `get_data_loader().modules`, `.upgrades`, `.commodities` — none of those registries have been populated for these IDs. |

All 10 templates are within locked ranges as shipped; no numeric adjustments were made beyond the tier-aware failure-refund map (section 3.1).
