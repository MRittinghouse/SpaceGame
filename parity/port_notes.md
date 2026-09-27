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

- A combat golden that exercises the engine's module-hit path: `resolve_module_hit` and
  `process_overkill_chain` in `CombatEngine` (`combat_engine.py`, about lines 2134-2232),
  both drawing from `rng=self._rng`. No SP2 golden reaches it, so "combat reproduces from
  its seed" is untested there.
- The `except Exception: pass` around that block (`combat_engine.py`, about line 2231)
  hides runtime failures: an exception anywhere in the module hit silently abandons the
  rest of it while the hull damage still lands. Decide whether the port keeps the guard
  before recording the golden.
- COMPLETED runtime missions stay in `MissionManager._runtime_ids` (`remove_mission`
  refuses ACTIVE and COMPLETED), and `get_state` saves each in full, so saves grow over a
  long career. The Godot save format should prune or compact them.
- `parity/golden/encounters/select.json` (SP3-a) records `select_encounter_definition`
  with every `EncounterContext` at its default `dialogue_flags={}` and
  `resolved_captain_ids=set()`. So the golden never exercises `EncounterDefinition.unique`,
  `requires_flags`, `excludes_flags`, or the RC-5 resolved-captain filter inside
  `_is_eligible` (`encounter.py`); it covers only `encounter_type`, `danger_levels`,
  `only_systems`/`excluded_systems`, `required_faction`, and level gates. A port checking
  those flag-gated branches needs a golden case that sets them.
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
  `args[2]`. `ambient` and `chatter` run one manager on `SimRng.from_key(*setup["rng_key"])`
  and pass the setup's fixed arguments to every call; an empty `player_flags` dict, unlike
  `None`, turns the ambient flag filter on. `interjections` keeps one resolver per fight
  label, seeded with `setup["seeds"][label]` over `setup["crew_aboard"]`: `evaluate_round`
  reads a combat state built from `args[1]` (round number, player hull and max hull, and
  each enemy's template, current hull and fled flag), `evaluate_outcome` reads no state,
  and each `commit` step names the offered event by crew id and trigger. Seven skill checks
  in six crew-quest trees name attribute ids (`acu`, `com`, `ing`, `res`, `syn`), which
  `SocialManager.resolve_check` fails as `Unknown skill: <id>`; the goldens record that
  failure for both profiles.

## Act II v1

Off behind `ACT_TWO_V1_ENABLED` (tag `act2-v1-archive`). Not ported.

## Orchestration findings

Bugs in `game.py` and the views are design inputs, not parity deviations. They
are listed for the owning sub-projects in the aurelia repo's
`docs/findings_register.md` (SP2 spec Section 6).
