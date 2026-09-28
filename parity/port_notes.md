# Port notes for SP3

Facts about the Python reference that a GDScript port must honor. Each entry
names the site so the porting task can find it.

## Rounding with ndigits

Python rounds a binary float's decimal representation, which `PyMath` does not
reproduce. None of these touch credits, prices, or quantities. Port them by
switching to integer math first, or record a deviation.

- `spacegame/models/build_rating.py:152, 187, 224, 257`: `round(score, 3)` (ship
  builder rating, retired scope per master spec Appendix A).
- `spacegame/models/salvage.py:347`: `round(self._rng.uniform(quality_min, 1.5), 2)`
  (salvage quality; the career sub-spec decides port or rebuild).

## Floor division and modulo on negative operands

Python floors; GDScript truncates. Use `PyMath.floor_div` and `PyMath.floor_mod`.

- `spacegame/models/social.py:275`
- `spacegame/models/politics_dispute.py:411`

## JSON number types

27 data keys mix ints and floats across files (`weight`, `variance_min`,
`variance_max`, `value`, `bonus_value`, and others). Cast by `parity/schema.json`.
These sites branch on `isinstance(x, int)` and need the cast before the check:
`capstone.py:128`, `lens_investment.py:174`, `bidding.py:722`, `build_sharing.py:253`.

## Derived seeds

Seeds computed from stream keys that later feed other streams. A port must build them the same way.

- Travel encounters: `EncounterRef.encounter_seed = stable_seed("encounter", game_day, system_id)`
  (`encounter.py`, `check_travel_encounter`). It feeds the combat, crew interjection,
  encounter selection, and loot seeds.
- The name `"customs"` is both a stream (`smuggling.py`, the inspection roll) and a
  `stable_seed` namespace (`game.py`, the customs `encounter_seed`). Consumers re-hash the seed,
  so the overlap is harmless, but the port's key registry must keep both uses.
- Travel protection roll: `SimRng.from_key("protection", game_day, system_id).randint(0, 99) < protection_chance`
  (`travel.post_process_encounter`). Replaced an md5 of `f"{day}_{system}_protection"` in SP3-a.
- Combat loot: `SimRng.from_key("loot", encounter_seed, template_id)` and
  `SimRng.from_key("rare_loot", encounter_seed, template_id)` (`combat_rewards.loot_rng`), drawn by
  `roll_loot` (`random()` against `chance`, then `randint(min_qty, max_qty)` per entry). Replaced
  `random.Random(encounter_seed + stable_seed("enemy", id) [+ 7919])` in SP3-a.

## Procedural mission IDs

`ProceduralMissionGenerator._mission_id` builds `proc_{type}_{system}_{day}_{base_seed}`,
keyed like the mission's content. A board holds at most one mission of each type, so the
ID is unique, and a board regenerated after a same-day load collides with the restored
missions in `MissionManager.add_mission` instead of offering copies. A port must not add a
counter or any other per-process part to the ID.

## SP3 must cover

- The module-hit path (`resolve_module_hit`, `process_overkill_chain`) reads the target's pixel
  `ShipBuild` and cannot run without the retired builder. It moves to SP4 with the parts model
  (SP3 spec R1). SP3's combat goldens run on the ship-type path.
- The engine's `except Exception: pass` guards are not ported (SP3 spec R2). The combat driver
  test proves no guarded dual-tech helper raises during a recorded fight.
- COMPLETED runtime missions stay in `MissionManager._runtime_ids` (`remove_mission`
  refuses ACTIVE and COMPLETED), and `get_state` saves each in full, so saves grow over a
  long career. The Godot save format should prune or compact them.
- `parity/golden/encounters/select.json` (SP3-a) records `select_encounter_definition`
  with the setup's `system_id` `''`, `player_level` 3, empty `dialogue_flags`, and no
  resolved captains. Over the 166 definitions, `_is_eligible` (`encounter.py`) takes both
  branches of `encounter_type`, `danger_levels`, `required_faction`, and `min_level` (the 3
  definitions gated at level 2 or 3 pass, the 6 gated at level 15 fail). It takes only the
  reject branch of `only_systems` (all 25 such definitions are rejected, 17 of them at that
  check) and of `requires_flags` (12 definitions). It takes only the pass branch of `unique`
  (15 of the 33 unique definitions reach the check, none seen yet) and of the RC-5
  resolved-captain filter (8 definitions). No definition carries `excluded_systems`,
  `excludes_flags`, or `max_level`, so those checks never run. The golden never records the
  `only_systems` accept, the `requires_flags` pass, the `unique` seen reject, or the
  resolved-captain reject; a port checking them needs a golden case with a matching
  `system_id`, set flags, a seen flag, or resolved captains.
- `parity/golden/missions/lifecycle_*.json` and `soft_deadline_*.json` (SP3-a) replay from
  `setup` alone: build the player from `setup["player"]`, recruit `setup["crew"]` with
  `setup["crew_slots"]`, load `setup["mission_state"]` through `MissionManager.load_state`,
  and replay `accept_mission`. Then set `player.game_day` to `setup["complete_on_day"]`
  before the first `check_objectives` step. Before each `check_objectives` step, apply
  `objectives[args[0]]` by these seven rules: `reach_system` sets `current_system_id` to
  the target; `talk_to_npc` sets the `talked_to_npc(target)` flag True; `have_credits`
  raises credits to at least the quantity; `collect_cargo` adds the quantity of the target
  at price 0; `has_flag` sets the target flag True; `complete_trade` raises
  `trades_completed` to at least the quantity; `win_combat` raises `combats_won` to at
  least the quantity. Pass the roster's recruited ids to `check_objectives`.
  `complete_mission` runs with the case roster, every synced faction id, and no
  reputation hook.
- `parity/golden/dialogue/*.json` (SP3-a) replay from `setup` alone. Each `tree_<id>` step
  builds fresh managers for profile `args[0]`: load `setup["profiles"][profile]["social"]`
  through `SocialManager.load_state`, recruit each `setup["crew"]` entry with
  `setup["crew_slots"]` and apply its `loyalty_delta`, load the profile's `flags`, start
  `setup["tree_id"]` with `setup["npc_id"]`, move the current node to `args[1]` (Python
  writes `DialogueManager._current_node_id`, which has no public setter), and select
  `args[2]`. The tree cases build `SocialManager` without a progression or an attribute
  sheet, so the tree bonus and the synergy bonus in `get_effective_level` are 0, and build
  `DialogueManager` without a player, so the `crew_whisperer` loyalty bonus in
  `select_response` is 0; the adapter must not attach the player's progression or
  attributes. `ambient` and `chatter` run one manager on `SimRng.from_key(*setup["rng_key"])`
  and pass the setup's fixed arguments to every call; an empty `player_flags` dict, unlike
  `None`, turns the ambient flag filter on. `interjections` keeps one resolver per fight
  label, seeded with `setup["seeds"][label]` over `setup["crew_aboard"]`: `evaluate_round`
  reads a combat state built from `args[1]` (round number, player hull and max hull, and
  each enemy's template, current hull and fled flag), `evaluate_outcome` reads no state,
  and each `commit` step names the offered event by crew id and trigger. Seven skill checks
  in six crew-quest trees name attribute ids (`acu`, `com`, `ing`, `res`, `syn`), which
  `SocialManager.resolve_check` fails as `Unknown skill: <id>`; the goldens record that
  failure for both profiles. Python bug, owner SP3-e: SP3-e's plan registers it at the next
  free id. Seven responses are recorded only as filtered out of available and are never
  selected: `merchant_delivery` greet #6, `reva_distress` greet #0, #1 and #3,
  `cassiel_maren_forgery` start #3, and `dead_ledger_investigation` greet #2 and #3. Novice
  lacks their required flags, and a flag expert loads trips their excluded flags. Each only
  moves to its `next_node_id` (none sets a flag, runs a check, or changes disposition,
  reputation, or loyalty), so a port checking those seven moves needs a golden case with a
  per-response flag set.

## SP3-a extractions

Rules lifted out of game.py and the views, each now a model function the game calls:
`trade_pricing` (buy, sell, black-market, refuel, trade reputation), `travel` (fuel, reserve
floor, encounter post-processing, hull restore), `encounter` (choice resolution, skill check,
outcome application, unique-encounter flag), `combat_rewards.loot_rng` and `roll_loot` (the loot
roll that replaced `combat_view._roll_loot`; the view's preview and both payouts call it, see
Derived seeds), `Player.apply_combat_victory` and `apply_combat_negotiated`,
`MissionManager.complete_mission`, `CrewRoster.on_trades`, `on_jumps`, `apply_leadership`, and
`GalaxyEventGenerator.advance_day`.

- Encounter credits go through `add_credits`, so `max_credits_held` tracks them (SP3-a ruling P3).
- Dialogue reputation changes need a PoliticsManager (wave B); the dialogue goldens run without
  one and record none (P5). SimRoot applies them directly until politics is ported.
  The extracted formulas take other wave B inputs too: `trade_pricing.buy_price` and
  `sell_price` take `perk_bonus` (`get_perk_bonus`), `refuel_price` takes `free_fuel`
  (`has_perk`), `travel.post_process_encounter` takes `enc_mods` (`get_encounter_modifier`)
  and `safe_passage` (`has_perk`), and the trade, mission, and encounter reputation changes go
  through `apply_reputation_with_spillover` when a manager exists. The goldens pass each as
  an explicit argument or run without a manager. Until politics is ported, SimRoot passes the
  no-politics values: 0.0, False, `{}`, False, and direct reputation.
- Reward kinds for SP3 spec 5.3's `RewardBundle`, the union of what the extracted functions
  apply. Encounter outcomes (`encounter.apply_encounter_outcome`): `credits`,
  `deduct_credits`, `xp`, `set_flag`, `add_criminal_heat`, `modify_reputation`,
  `confiscate_cargo`, `reduce_criminal_heat`, `bounty_immunity`, `start_bounty_combat`.
  Mission completion (`MissionManager.apply_rewards` and `complete_mission`): `credits`,
  `xp`, `deduct_credits`, `remove_cargo`, `set_flag`, `black_market_access`,
  `kweon_relationship`, `crew`, `trade_permit`, `reputation`, `modify_reputation`. Combat
  victory (`Player.apply_combat_victory`): XP, credits, and loot cargo; a negotiated end
  (`Player.apply_combat_negotiated`) adds loot cargo only, when enhanced negotiation earned
  it: half of each common-table roll, rounded down, at least 1.
- Encounter-definition selection goldens run with empty flags and no resolved captains.
- Golden-only key namespaces (never used by the game): `parity_fight`, `parity_complication`,
  `parity_ultimate`, `parity_dual_tech`, `parity_resolve`, `parity_ambient`, `parity_chatter`,
  `parity_interjection`.
- Player goldens compare the save manager's serializer output on the keys in `WAVE_A_PLAYER_KEYS`
  (`tools/parity/snapshots.py`); manager-owned state (missions, crew, social, attributes) is
  compared by those managers' goldens.
- Content numbers: every float literal in `data/` fits the exact decimal fast path (mantissa at
  most 2^53, decimal exponent within 22), so a literal-preserving JSON reader loads content with
  Python's types exactly (SP3 spec amendment A1).

## Act II v1

Off behind `ACT_TWO_V1_ENABLED` (tag `act2-v1-archive`). Not ported.

## Orchestration findings

Bugs in `game.py` and the views are design inputs, not parity deviations. They
are listed for the owning sub-projects in the aurelia repo's
`docs/findings_register.md` (SP2 spec Section 6).
