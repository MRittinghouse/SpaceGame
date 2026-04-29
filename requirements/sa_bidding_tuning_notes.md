# SA-B6: Bidding System Tuning Notes

**Sprint**: SA-B6 (Bidding polish + tuning)
**Date**: 2026-04-29
**Status**: Audit complete. No constant changes applied.

---

## 1. Methodology

Tuning analysis used three inputs:

1. **Static persona inspection**: read each archetype factory in `bidding_persona.py` (lines 250-380) against the design-doc §4.1 expected behavior and §4.2 behavior axes. Compared ceiling_ratio, aggression, patience, desire_multipliers, and venue-specific flags for each of the 5 personas.

2. **Scenario test review**: executed the existing scenario test suite (`pytest tests/test_scenarios/`) at INFO-level logging to observe per-lot sale prices, persona ceilings, and round counts. Tests exercise all four speed settings, two venues (stellaris, crimson_reach), and two rep tiers (regular, certified/patron).

3. **Constant range analysis**: evaluated each tuning constant against its expected behavioral range per design doc §5.2, §10.8, and §B4.4.

SA-B6 does NOT introduce new lots, new personas, new venues, or new view substates. Tuning is restricted to evaluating (and potentially editing) existing constants.

---

## 2. Observed Signal

### Persona ceiling_ratio

| Persona | ceiling_ratio | vs_player_ceiling_ratio | Assessment |
|---|---|---|---|
| Aldous Prentiss | 1.10 | n/a | Correct. Heritage collector who values acquisition over price discipline. Pays 10% above effective value on contested lots. |
| Yuna Kade | 1.00 | n/a | Correct. Commerce Guild commissioner on a budget; precise payer with no overshoot. |
| Fenn Salko | 0.90 (base) | 1.15 (vs player) | Correct. Cost-disciplined in general; escalates specifically against the player. The asymmetry creates the cold-grudge dynamic. |
| Stellaris Speculator | 0.85 | n/a | Correct. Ambient room fills at a slight discount; prevents speculators from driving prices above catalogue value. |
| Reach Buyer | 0.90 | n/a | Correct. Black market buyer; matches Salko's general discipline. The 0.90 cap keeps lots competitive without dominating. |

### Persona aggression

| Persona | aggression | Assessment |
|---|---|---|
| Prentiss | 0.30 | Correct. Measured cadence; sits out marginal lots. |
| Kade | 0.70 | Correct. Aggressive on her approved list; sits out everything else (desire_multipliers gate). |
| Salko | 0.60 | Correct. Moderate base aggression; patient=0.90 means he holds his bid longer before countering. |
| Speculator | 0.50 | Correct. Mid-room; does not dominate individual lots. |
| Reach Buyer | 0.80 | Correct. Fast cash culture; enters quickly and bids aggressively on contraband/weapons. |

### min_increment_for_appraisal

Current four-tier scale (`bidding_round.py:55-72`):
- <= 2,000 credits: 50 (2.5%)
- <= 10,000 credits: 200 (2.0%)
- <= 30,000 credits: 500 (1.7%)
- > 30,000 credits: 1,000 (~2%)

The increment percentages are consistent across tiers (1.7-2.5%). This produces appropriately tight increments on lower-value lots and wider spacing on premium lots, which matches the §5.2 design intent. No evidence of stickiness or jump-skipping in scenario runs.

### Listing fee rate

`LISTING_FEE_RATE = 0.05` (5% of declared appraisal), `LISTING_FEE_FLOOR = 100` credits.

On a 10,000-credit lot: 500-credit fee. On a 1,500-credit lot: 100-credit fee (floor). These values create meaningful cost friction for high-value consignments while protecting small-lot sellers from prohibitive fees. The 5% rate is consistent with the design doc's intent that listing should be a considered decision, not a reflex.

### Reach demand probability

`REACH_DEMAND_PROBABILITY = 0.35`, `REACH_DEMAND_MAX_GAP_DAYS = 8`.

Expected session cadence: at 35% daily probability with a 4-arrival threshold (REACH_SESSION_SIZE = 4), the expected gap is roughly 4 / 0.35 = 11.4 days. The MAX_GAP_DAYS = 8 cap forces a session to open no later than day 8 after the last close, regardless of arrival count. This produces the Reach's "irregular but not absent" feel. The cadence contrast with Stellaris (5-7 day deterministic schedule) is sharp and intentional (locked decision §B4.4).

---

## 3. Recommended Adjustments

| Category | Recommendation | Rationale |
|---|---|---|
| Persona ceiling_ratio | Skipped | All five archetypes fall within target behavioral range. See §4.1 design alignment above. |
| Persona aggression | Skipped | All five archetypes read correctly per design-doc §4.2. No session-outcome skew observed. |
| Listing fee rate | Skipped | 5% with 100-credit floor is within the intended friction range. No player-experience signal suggests the fee is a barrier. |
| Reach demand probability | Skipped | 0.35 probability produces the intended irregular-but-bounded cadence. MAX_GAP_DAYS = 8 provides the ceiling. |
| min_increment_for_appraisal | Skipped | Four-tier scale is consistent (1.7-2.5% across tiers). No evidence of increment-related gameplay friction. |

---

## 4. Applied Changes

No constants were modified in SA-B6. The three SA-B6 deliverables that touched code are:

1. **Post-session line rotation** (`auction_view.py`): `_post_session_lines()` now uses `_seed_index(session_id, rival_id, bucket) % len(options)` instead of always `options[0]`. No constants changed.

2. **Dead-code removal** (`auction_view.py`): removed the unreachable `on_session_complete` delta-detection block in `update()`. No constants changed.

3. **Reach Salko bucket expansion** (`crimson_reach_voices.json`): each of the four `post_session.fenn_salko` buckets extended from 1 line to 3 lines. No constants changed.

### Accessibility

Audit completed against `requirements/ui_design_standards.md` compliance checklist on `auction_view.py` and `sell_lot_view.py`. Findings:

**(a) Tab order through bid panel**: Raise, Hold, Fold buttons are created in that order (`auction_view.py:809-819`). pygame_gui traverses buttons in creation order by default. Tab sequence is: Raise Min → Hold → Fold → Speed buttons. This matches visual left-to-right order.

**(b) No critical information conveyed by color alone**: The high-bid display in `_render_body_bid_window` renders the bid value as text (e.g., "12,400 credits"). The active speed setting is displayed via button label text, not only by color highlight. The FirstTimeTip overlay shows its title and body as left-aligned text. Pass.

**(c) FirstTimeTipOverlay at 1280x720**: TIP_TITLE ("Auction Floor") and TIP_BODY (three sentences, ~30 words) are well within the overlay panel width at minimum resolution. Pass.

**(d) Slow mode (45s/5s) usable**: Scenario tests complete at all four speed settings. The slow mode provides substantial time for deliberate input. Pass.

**Result**: No accessibility violations found. No code changes from the audit.

---

## 5. Skip List

| Category | Decision | Rationale |
|---|---|---|
| Persona ceiling_ratio | Not adjusted | All five archetypes within target behavioral range. |
| Persona aggression | Not adjusted | All five archetypes read correctly. |
| LISTING_FEE_RATE | Not adjusted | 5% with floor is appropriate friction. |
| REACH_DEMAND_PROBABILITY | Not adjusted | 0.35 produces the intended irregular cadence. |
| REACH_DEMAND_MAX_GAP_DAYS | Not adjusted | 8-day cap provides the upper bound. Locked decision §B6.7. |
| STELLARIS_CADENCE_MIN/MAX_DAYS | Not adjusted | 5-7 day cadence is the design baseline. |
| MAX_ACTIVE_LISTINGS | Not adjusted | 3-listing cap prevents session dominance. |
| LISTING_FEE_FLOOR | Not adjusted | 100-credit floor protects small-lot sellers. |
| Pause / auto-bid affordance | Not in scope | Locked decision §B6.1; no new UI affordances in this sprint. |
| Reach player-listing variant | Permanently deferred | Locked decision §B6.2; Reach is a buyer-side experience. |
| velo_lines rename | Not executed | Locked decision §B6.6; alias is permanent infrastructure. |
