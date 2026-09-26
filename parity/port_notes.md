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

## Act II v1

Off behind `ACT_TWO_V1_ENABLED` (tag `act2-v1-archive`). Not ported.

## Orchestration findings

Bugs in `game.py` and the views are design inputs, not parity deviations. They
are listed for the owning sub-projects in the aurelia repo's
`docs/findings_register.md` (SP2 spec Section 6).
