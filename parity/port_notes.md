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
  `setup["crew_slots"]`, load `setup["mission_state"]` through `MissionManager.load_state`
  into a manager built with `produced_flags=content_flag_producers(<dialogue trees>,
  <encounter definitions>, <NPCs>)` (the missions driver's `_manager`, since the bug bash),
  and replay `accept_mission`. Then set `player.game_day` to `setup["complete_on_day"]`
  before the first `check_objectives` step. Before each `check_objectives` step, apply
  `objectives[args[0]]` by these seven rules: `reach_system` sets `current_system_id` to
  the target; `talk_to_npc` sets the `talked_to_npc(target)` flag True and calls
  `MissionManager.record_conversation(target)`; `have_credits`
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
  free id. Eight responses are recorded only as filtered out of available and are never
  selected: `merchant_delivery` greet #6 and #8, `reva_distress` greet #0, #1 and #3,
  `cassiel_maren_forgery` start #3, and `dead_ledger_investigation` greet #2 and #3. Novice
  lacks their required flags, and a flag expert loads trips their excluded flags. Each only
  moves to its `next_node_id` (none sets a flag, runs a check, or changes disposition,
  reputation, or loyalty), so a port checking those eight moves needs a golden case with a
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

## Bug bash A1 (2026-09-30)

Model rules the Godot port mirrors after syncing this branch (plan A2). The goldens pin
each one; the missions' run state is not in any golden, so its unit tests are the spec.

- Missions (`mission.py`): `MissionObjective.after_departure` (content and runtime, written
  only when true) and `Mission.ordered_final` (runtime, written only when true, last key).
  An accept with a player records the accept system and the `combats_won` and
  `trades_completed` baselines; the first check after an accept without one records the
  system. Each check first marks a mission departed when the ship stands elsewhere, then
  evaluates in index order: an ordered final leg only when every earlier objective is met
  this check, never locked; an `after_departure` leg only when departed and every earlier
  non-has_flag objective is met; a talk objective after index 0 only when its NPC is in
  the conversations recorded since the accept (`record_conversation`, called at a dialogue's
  exit before the availability pass, notes an NPC only for an active mission with a talk
  objective after index 0 targeting it) and every earlier non-has_flag objective is met, a
  conversation recorded while one is open being dropped; a talk objective at index 0 by
  the sticky `talked_to_<npc>` flag; counters as the difference from the baseline (0 when
  none). A run's state goes when the mission leaves ACTIVE. Saved as `accept_system`,
  `departed` (sorted), `baselines`, `talked_since_accept` (sorted, non-empty only).
- The side-mission auto-resolve sets only flags no content produces:
  `content_flag_producers` (dialogue set flags and check flags, encounter outcome set_flag
  rewards and check flags, NPC gate flags) plus forced-encounter trigger flags and other
  missions' set_flag rewards. Ground-complete flags are not producers.
- Board generator: bounty, survey, and salvage returns `after_departure`; delivery and
  smuggling `ordered_final`; smuggling's `COLLECT_CARGO` leg ("Keep the N <name> aboard");
  the delivery fallback over legal, priced, listed goods; "Clear 1 Hostile"; the smuggling
  description's comma.
- Social: `resolve_check(..., game_day)` pays XP once per `"<npc>|<skill>"` a day
  (`check_xp_days` in `get_state`, sorted); npc id "" moves and reads no disposition; the
  dialogue readout reads the level before the check; the day comes from
  `DialogueManager.start_dialogue(game_day=)` and from the encounter's player.
- Game (`game.py`): every availability pass (the new game, a dialogue's exit, a load, the
  check) loads the `on_accept_cargo` of each mission it auto-accepted, with a
  `Cargo Loaded: <n> <commodity>` line (`_load_auto_accept_cargo`, F-37). The pass's
  `Mission Accepted` and `New Mission(s) Available` lines are still `check_missions`' alone.
- Combat: an enemy plays its telegraph when it still can, and the telegraph clears at its
  turn; the Volley repeat refusal `"<Move> cannot fire twice (cooldown N)"` for a cooldown
  weapon, unless its first copy was queued after Fire at Will (the cover is a Fire at Will
  still in the queue when the weapon's first copy is added, so an undone Fire at Will covers
  nothing, although F-19 keeps its half price), and Volley Commander's extra
  action is spent only by a repeat that passes every check; Counterstrike's
  cap 3 plus the skill level and the log `round(per_stack * stacks * 100)`; Mayday Burst's
  "The burst breaks contact. You are clear."; the captain outcome `fled_captain` and
  `outcome_line`; `CombatEngine.was_fought`.
- Templates: `random_pool` (filtered from random pools) and `bribable` (content marker).
- Player: `get_crew_slots` (Legend of the Expanse adds 2), `get_effective_reputations`;
  `apply_combat_defeat` takes nothing from a stack whose commodity category is `quest`,
  and the golden `player/defeat_quest_cargo` pins it, so a lost fight cannot strand a chip
  delivery. The port must add the skip: its `CombatRewards.apply_defeat` (aurelia
  `core/combat/combat_rewards.gd:154-156`) takes cargo from every stack today, so it must
  pass over a stack whose `Commodity.category` is `quest`, and plan A2's BB-53 rewrite of
  `apply_defeat` (its Task 5 Step 4) must keep that skip. `player/defeat_quest_cargo` is
  the sixth new golden, which A2's Task 1 sync list does not name: Step 2 should expect it,
  the player parity suite belongs among Step 3's expected failures, and aurelia's
  `test/parity/player_parity_test.gd` `PLAYER_CASES` goes from 4 to 5.
- Progression: `add_xp` loops only while `1 <= level < LEVEL_CAP` (10,000).
- Galaxy (`system.py`, `faction.py`, `game.py`): `StarSystem.faction_id` (content key
  `faction_id`, now in `parity/schema.json`) is the cultural guide's map. The Guild holds
  Nexus Prime, Stellaris Port, Forgeworks, and the Fulcrum; the Union holds Breakstone and
  Iron Depths; the Collective holds Axiom Labs and Nova Research; the Frontier holds
  Verdant, Haven's Rest, and Crimson Reach; Heron's Mark is "" (unheld). The crimson_reach
  faction holds nothing and keeps its standing. `generate_faction_assignments(systems)`
  returns each held system's `faction_id` in content order and leaves an unheld system
  out; the new game and a load without saved assignments take it, and no stream is drawn.
  A save's own assignments load as saved. `StarSystem.faction` stays display text.
- Permits (content): the bill of landing grants commerce_guild, science_collective, and
  frontier_alliance (three "Trade Permit Acquired: <faction>" notices); Union Territory
  alone grants miners_union. The "all" target and its "Universal Bill of Landing" notice
  stay in the code, unused by content. The no-permit refusal reads "You need a trade
  permit to trade here" (`trading_view.NO_PERMIT`).
- Combat builder (`build_player_combat_state`, both paths): Shield Mastery adds
  `int(<the hull's shields> * get_bonus("shield_bonus"))` to `max_shields` and to the
  opening `shields`, which are capped at `max_shields`. On the ship-type path the hull's
  shields are `combat_shields`, and the upgrades' `shield_bonus` sits beside the share.
  The golden `combat/skill_shield_mastery` is the only setup with a `skill_levels` key
  (`{"shield_mastery": 3}`); a replay sets those levels on the progression before it
  builds the player.
- Code-built text: the em-dash replacements in `attributes.py`, `combat_engine.py`,
  `enemy_subsystems.py`, `dialogue.py` (`"<name> (<title>)"`, since ten titles hold a
  comma), `enemy_captain.py` (`"<name> (<nickname>)"`), `dual_tech_dialogue.py`,
  `procedural_missions.py`, and `game.py`'s notices.

### Records for plan A2

Consequences of this branch that plan A2 writes into the register, the deviations, or the
hand-offs; none is a model rule to port.

- BB-12: the `bribable: false` marker on `ledger_raider`, `ledger_striker`, and
  `ledger_vanguard` takes the bribe away from the scripted Ledger ambushes (under_fire:
  raider and striker; the_collapse: vanguard, raider, and striker). With BB-8 (a lost
  ambush arms again) and the striker pinning flee at the 10% floor, those fights become
  fight-or-flee for whatever ship SP8 brings: the ship needs SP4's weapons or an SP8 retune
  before those missions are reachable (D-17's reason, and an SP4 and SP8 hand-off).
- BB-28: with Hull Brace on cooldown 2, the armored transport's cannon fires again after
  round 4, but a brace that leaves it 2 energy after the round's regen (+2) against the
  3-energy cannon makes it idle ("No Action") the next round. In a fight where the player
  never fires (TestArmoredTransportKeepsFiring's setup), it settles from round 5 into Hull
  Brace, No Action, Transport Cannon, Transport Cannon, so SP4's retune starts from a
  transport that sits out about one round in four. The golden
  `combat/fight_armored_transport` reads Transport Cannon four times, Hull Brace, No Action,
  Transport Cannon, Hull Brace, Transport Cannon: its second brace is made at 3 energy and
  leaves 3 after regen, so the cannon fires the round after. Those No Action rounds are the
  new pattern, not a regression.
- BB-17: the hold-back flag is `held_back_until_sp10`. Holding back The Silent Shaft leaves
  `attended_silent_shaft` unset until SP10, which also silences the three ambient lines
  gated on it (two of Marcus Jin's, one of Tomas Drifter's) (F-60).
- BB-82: the four availability passes mirror (`Player.get_effective_reputations`), and
  Python's hub reputation teaser (`get_reputation_locked_teaser`, which the port does not
  have) passes the same effective standing. The station hub's chatter does not: Python
  reads a display name (D-12 and F-38), and the port's `ArrivalActions._hub` reads the
  holder's stored standing, so the hub's chatter counts Frontier Reputation in neither
  build while the four availability passes do. D-12's Godot cell records it.
- F-37: every availability pass now loads an auto-accepted mission's cargo, so D-8's cargo
  clause matches Python; plan A2 trims that clause (the announcements stay port-only).
- Python's `DataLoader._parse_mission` never reads `discovery_text`, so every mission-discovery
  journal line in Python falls back to "Heard word of new work: <name>.", and the rewritten
  coolant_run and arna_02_ore_tip discovery texts show only in a build that reads the field
  (found while checking Task 7's test).
- BB-2: SpaceGame's `check_gated_flags` ignores the awaiting mission's own reward and a
  dependent mission's reward, as `producer_cycles` does, while plan A2's `_check_free`
  counts every non-dialogue producer as free. A2's twin should filter producers the way its
  `_open_producers` does (its stale comment says A1 leaves the SpaceGame twin to the later
  plan); the twins check the same synced content.
- BB-15: a captain who holds the coolant pallet past the day-one jobs can load cargo_lost's
  5 electronics to 52 of 50, which refuses every purchase until a delivery, because neither
  build checks capacity on accept-cargo loads (Python: `Ship.add_cargo` and the board
  accept in `game.py`; port: `PlayerShip.add_cargo`). The real fix is a capacity check at
  accept or load, in both builds, for A2 or SP4.
- BB-6: a save made before this branch that holds an active authored return-leg mission
  accepted at its giver's station keeps the old early payout once (Blight Season at Axiom
  Labs, Lab Rat at Forgeworks), because the old rule locked the return leg and `load_state`
  keeps a met leg met. A board contract accepted before this branch keeps its saved
  definition too (`runtime_missions` are saved whole and win over a regenerated board), so
  it pays the old way once: smuggling with an empty hold, a return leg locked early, or a
  delivery's destination counted before the goods. Under the alpha stance neither is
  migrated; a release-time migration would reset each `after_departure` leg of an active
  mission with no saved run state, and re-mark or drop active board contracts with no run
  state. BB-19 has the same seam: a save made before this branch whose Arna talk leg the
  old sticky rule locked True keeps it (`load_state` keeps a met leg met), so arna_02 saved
  as [F,F,T] completes at Breakstone once the ore is aboard, and arna_03 saved as
  [F,F,F,T] completes at Forgeworks once `tev_refining_complete` is set, each once and
  with no Arna conversation. arna_04, arna_05a, and arna_05b also hold their Nexus Prime
  return leg, which the same check locked at the accept, so they pay early as above
  (arna_04 after Keren at Heron's Mark, arna_05a on landing at Heron's Mark, arna_05b at
  Haven's Rest once the scrap is aboard). A release-time migration would also reset every
  met `talk_to_npc` leg after index 0 of an active mission when `talked_since_accept` is
  absent.
- BB-7: a collect leg tests at least N aboard per contract, so two board contracts
  (smuggling or delivery) with the same commodity and destination share one load. One
  landing pays both while the overlap is sold, and the second `remove_cargo` fails
  silently. Closing it needs per-contract cargo reservation in both builds, with BB-7's SP8
  and SP9 hand-off.
- BB-7: the port has no trade screen yet, and its `TradeActions.sell` sells any held good at
  `sell_price`'s floor of 1 CR, quest goods included. SP6's trade screen must leave
  quest-category goods out of its sell list and Sell All, as Python's trade view does, or
  `TradeActions.sell` must refuse them. Otherwise a captain who sells Dex's data chip or the
  sealed audit chip strands the_crimson_run (campaign, blocks embassy_visit) or
  the_price_of_information.
- BB-29: SP6's skill screen must wrap skill descriptions. Python's tooltip draws them on one
  300 px line, and at FONT_XS 31 of the 89 overrun it (the longest, cultural_savant, is 509
  px; counterstrike 367, insurance 482), measured at 1280x720 with the game's label font.
- BB-88: undoing a Volley repeat does not restore the extra action and drops the slot's keys
  while the first copy stays queued, so the repeat cannot move to another weapon, and
  undoing past the first copy spends the skill for the turn, in both builds. SP6's screen
  should restore the extra action and keep the keys when another copy of the slot remains.
- BB-88: a repeat of a once-per-combat move with cooldown 0 (Crew Sync) passes the queue
  and spends Volley Commander's extra action, then the engine refuses it ("Crew Sync
  already used this combat"), in both builds; SP6's queue should refuse it too.
- BB-86: `attempt_flee` draws a fresh enemy move for each parting shot and ignores
  `telegraphed_move`, so a flee can be hit by a move other than the one shown, in both
  builds (SP4).
- BB-91: Python's ghost passive readout (`spacegame/views/combat_view.py:3192`,
  "Counterstrike: +{stacks*10}%") disagrees with the engine's applied percent, 12% plus 5%
  per Counterstrike level, per stack, which the combat log and the repaired skill text both
  state: at Counterstrike 1 with four stacks the panel reads +40% and the log +68%. SP6's
  fight HUD should read the engine's per-stack value.
- BB-87: `captain_ship_fled` takes any fled enemy on the captain's `signature_ship_template`
  for the captain's ship, so a roster with a second ship on that template (an escort, or a
  reinforcement on it) would play the retreat line and record `fled_captain` after the
  captain's own ship was destroyed. No content reaches it: each of the eight reachable
  captain encounters fields one ship on the signature template, none carries a spawning
  complication, and the one reinforcement move (union_behemoth's `call_reinforcement`)
  spawns union_picket. Content that gives a captain an escort on its own template needs a
  captain mark on the enemy ship in both builds.
- BB-87: a passed pre-fight check still records a captain meeting as negotiated, a truce
  that resolves the rivalry, in both builds (Python
  `EncounterView._maybe_record_captain_encounter`, the port's
  `EncounterOutcomes.captain_outcome`). The same act inside a fight that sends the captain's
  ship away records `fled_captain` and keeps the captain active. Wren's pre-fight
  intimidation ("Then peels off without another word") and deception ("breaks off") are the
  reachable cases. Whether a captain who leaves before the fight stays in the rotation is a
  design call for a later plan; the two builds agree.
- BB-87: a persuasion surrender pays half of each loot roll, and the roll can come up empty,
  so four rewritten surrender lines can offer cargo that never arrives. Across encounter
  seeds 0 to 999 the signature ship's roll is empty for Odalys (reach_bulwark, "Yohan will
  float the crates over") 53% of the time, Anatolia (guild_revenue_cutter, "Take the
  settlement from my hold") 24%, Ink (mercenary_ace, "Take what you need from my hold") 14%,
  and Wren (smuggler, "Take what's loose in my hold") 13%. The writing pass, which holds all
  eleven lines, should weigh it; a surrender that always pays would be a rule change in
  both builds.
- BB-19: the conversation that completes arna_02, arna_05a, or arna_05b opens that job's
  pending tree (its line reads true before and after the errand), and the full return
  scene plays on the next conversation. The two-talk seam goes to SP7's paired pass.
- BB-19: Python's talk-receiver hints flag any incomplete talk objective
  (`CantinaView._npc_is_quest_receiver` at `spacegame/views/cantina_view.py:599`,
  `station_salience._has_talk_to_npc_objective_at`, and
  `MissionManager.get_active_target_systems`). So right after arna_02, arna_03, arna_04,
  arna_05a, or arna_05b is accepted, Arna shows "(Active Quest)", the hub marks her cantina
  as a mission objective, and Nexus Prime is a target, although the talk rule drops that
  conversation (her pending line reads true, so the harm is cosmetic). A port of these
  queries for SP5's and SP6's screens should flag a talk receiver only once every earlier
  leg that is not has_flag is met.
- BB-19: `record_conversation` notes an NPC only for an active mission with a talk
  objective after index 0 targeting it, where plan A2's draft `MissionManager.note_talk`
  notes the conversation for every active mission. The missions play the same, since only
  such an objective reads the note, but the saved `talked_since_accept` differs, so A2
  should narrow `note_talk` to Python's rule.
- BB-15: Rhea's `[Hand over the pallet.]` sets `arna_delivery_resolved` and thanks the
  captain for a clean pallet whether or not one is aboard; the mission waits for the
  pallet, the scene does not (SP10).
- BB-89: the item `point_defense_system` is renamed "Point Defense Screen" (move
  `point_defense_screen`); the display-name pairs SP4 still renames are "Ion Disruptor" and
  "Arc Emitter".
- BB-74: both builds now take the content's map, so D-7's deal clause no longer describes
  a difference (its display-name clause stays: Python still writes the holder's name into
  `StarSystem.faction`). The port's `FactionAssignments.generate` and
  `NewGame._assign_factions` read `faction_id` and draw no `[FACTION_ASSIGNMENT,
  world_seed]` stream, and every port test pinned to a seed's deal re-pins to the map.
- BB-74: Python's random encounter selection and the campaign ground mission now read
  `StarSystem.faction_id` (the two `getattr` sites of F-12), so F-12 closes in Python for
  both, and D-10's Python cell no longer describes a difference for the 48 faction
  definitions. Under the fixed map 36 of them can play in every game: the Guild's 12
  (through Forgeworks and the Fulcrum), the Union's 12, 8 of the Collective's, and 4 of
  the Frontier's. The Collective's other four are three anomaly definitions that play only
  with Anomaly Detector, and collective_medevac_01 (dangerous only), which never plays,
  since the Collective holds only moderate space. The Frontier's other 8 are safe-tagged
  and wait for BB-94's peaceful-only roll in safe space (SP5).
- BB-74: the campaign ground mission's faction reaches Python's procedural ground fallback.
  The two ground missions with no authored map, the_long_shift (Breakstone, a Union mine
  rescue gated on Union standing 15) and deep_core_whispers (Iron Depths), now draw the
  Union's ground pool (`ground_mapgen._FACTION_ENEMIES["miners_union"]`: union_worker twice,
  alliance_scrapper, pirate_thug) in every game, so the rescue fights Union workers. SP8
  decides whether a rescue should when it rebuilds the away team.
- BB-74: under the cultural guide's map the Collective's two dangerous-tier ships,
  `science_sentinel` and `collective_jammer_prime`, join no random pool: the Collective
  holds no dangerous system (Axiom Labs and Nova Research are moderate), and
  `filter_enemies_for_system` admits a dangerous-tier template only in dangerous space.
  Nothing else in `data/` names them, so they can never be met, where the deal gave the
  Collective dangerous space in many games (F-68's row, SP4 with SP5 for danger
  signposting).
- BB-74: until Union Territory completes, Breakstone and Iron Depths refuse trade in both
  builds. The port's scripted playthrough sells at Iron Depths on the bill alone, and its
  tests count five permits after the bill and pin "Universal Bill of Landing". No good is
  sold only in Union space, so no mission soft-locks: Union Territory's food, Miners'
  Plight's medicine, and arna_02_ore_tip's rare metals all sell elsewhere. The wallet can
  still strand a captain there: refuel and rest need no permit and the sale now does, so
  before Union Territory a captain who lands at Breakstone or Iron Depths with cargo, too
  few credits to refuel, and less fuel than the cheapest jump out cannot sell the cargo to
  get away, which the universal bill allowed. It is BB-3's dead end with a new entrance,
  for BB-3's later plan and SP6's Guild credit. Elena's cantina lesson ("Buy here, sell
  there", food to Breakstone) and Python's trading-view tutorial narration ("Five units of
  food. ... Buy it here, bring it to Breakstone.", `spacegame/views/trading_view.py:1617`)
  now run ahead of Hanna's permit. The narration shows on every trade screen while
  `trading_tutorial_buy_pending` is set, so at Breakstone and Iron Depths it asks for a
  purchase that the bill now refuses with "You need a trade permit to trade here". Both are
  left as written under the voice guard, true once the permit is held, for SP6's trade
  screen and SP7's paired pass.
- BB-75: Shield Mastery is wired, so its row of the 44-row table closes (43 stay open), and
  shield_regen, armor_expertise, and hull_reinforcement lose their dead prerequisite. A
  fight can end with shields above the hull's base, which the write-back keeps until
  docking restores the base (the shield twin of BB-23's hull record). Battle Commander
  stays unwired (SP8).
  "+10% max shields per level" is exact on Python's build path, where
  `computed_stats.shields` already holds the parts' shields. On the ship-type path, which
  is the port's only path, an upgrade's `shield_bonus` sits outside the share, so Shield
  Mastery 3 with the Auxiliary Shield Battery opens at 26 of 36 (+20% of the maximum, not
  +30%). The writing pass, which holds `shield_mastery` on the voice list, should weigh it.
- The voice guard: every player-facing line this branch changes, by content id, for the
  hand-off to the writing pass. Each is a repair; "(new)" marks a line a fix needed.
  - `data/combat/enemies.json`: the descriptions of `guild_revenue_cutter`,
    `science_surveyor`, `reach_wrecker`, `bounty_ace`, and `ledger_striker`, and
    `reach_dreadwreck`'s move `dreadwreck_barrage`. `data/ships/upgrades.json` and
    `parts.json`: `point_defense_system`'s name and move name.
  - `data/progression/skills.json`: `insurance`, `faction_ambassador`, `peacemaker`,
    `underworld_contacts`, `smugglers_eye`, `crew_whisperer`, `cultural_savant`,
    `diplomatic_relations`, `tariff_negotiation`, `juggernaut_capstone`, `counterstrike`,
    `shield_mastery`.
  - `data/dialogue/dialogues.json`: `arna_refining_pending`, `arna_buyer_pending`,
    `arna_payback_pending`, `arna_walkaway_pending` (new); `arna_ore_tip_pending.start`;
    `arna_first_encounter.the_offer` (subtext); `rhea_receives_coolant.start`;
    `arna_post_completion.ore_pitch` and `catch_unread` (new); `elena_cantina`
    `about_elena_deflect` (new); `cassiel_maren_forgery.caught` (replies 1 and 2) and
    `blackmail`; `priya_stranded.decline` and `agree_transport`; `larsen_customs.advice`;
    `merchant_delivery.teach_routes`; `callum_rhee_informant` (`start` and its reply 3,
    `deflect_destination`'s reply 0, and `deflect_smooth`).
  - `data/dialogue/crew_quest_dialogues.json`: `priya_peer_review_dialogue` (`start`, the
    Communication reply, `witness_fail`); `marcus_inspector_dialogue.bribe_accept` (the
    line and its reply).
  - `data/missions/missions.json`: `point_of_no_return` (objective 2 removed),
    `the_crimson_run` (a new objective), `recruit_navigator` (description, hint). `side_missions.json`: `the_price_of_information` and
    `coolant_run` (a new objective each), `coolant_run` and `arna_02_ore_tip`
    (`discovery_text`), `miners_plight` (description), `arna_05b_clean_pull` (description,
    hint, objective 0). `data/characters/npcs.json`: `amara_okonkwo` (name).
    `data/journal/entries.json`: `auto_arna_branch_b`.
  - `data/combat/captains.json`: the `surrender_line` of `ngozi_pale_reckoning`,
    `wren_departure_angle`, `odalys_kindling`, `ink_silverback_gospel`,
    `anatolia_kestrel_crow`, `rin_wheat_dagger`, `dowager_chamberlains_regret`,
    `thayer_clear_signal`, `dusty_slow_star`, `rhiannon_deep_veil`, `marat_old_friend`.
    `data/combat/complications.json`: `shield_harmonic` (description, narration).
  - `data/encounters/ce4_pressure.json`: `shakedown_ore_holdup_01` (the `appeal` and
    `stand_off` failure outcomes), `shakedown_contraband_intercept_01` (description).
    `ce4_variety.json`: `bait_civilian_lure_01`, `bait_mining_rig_01`, `bait_comm_relay_01`,
    `bait_patrol_officer_01`, `derelict_civilian_wreck_01`.
  - The 290 splice repairs, in 120 encounters. `campaign.json`: campaign_sato_returns_01,
    campaign_sato_ghost_01, campaign_torres_tip_01, campaign_ledger_courier_01,
    campaign_larsen_warning_01, campaign_pirate_weapons_01, campaign_guild_shadow_01,
    campaign_anomaly_deepens_01, campaign_black_market_intel_01,
    campaign_refugee_testimony_01, campaign_final_warning_01, campaign_old_allies_01.
    `commerce_guild.json`: guild_tariff_01, guild_blackmail_01, guild_merger_01,
    guild_distress_luxury_01, guild_signal_encoded_01. `frontier_alliance.json`:
    alliance_harvest_01, alliance_refugee_family_01, alliance_wrecker_01,
    alliance_moonshine_01, alliance_barter_01, alliance_community_01,
    alliance_patrol_volunteer_01, alliance_distress_crop_01, alliance_storyteller_01,
    alliance_smuggler_medicine_01, alliance_salvage_claim_01, alliance_festival_01.
    `generic.json`: distress_engine_01, derelict_freighter_01, derelict_wreck_01,
    merchant_convoy_01, debris_cargo_01, debris_ghost_01, anomaly_energy_01,
    shakedown_pirate_01, shakedown_enforcer_01, cargo_lost_distress, patrol_routine_01,
    comm_intercept_static_01, debris_minefield_01, derelict_station_01, anomaly_gravity_01,
    wildlife_swarm_01, distress_pirate_attack_01, debris_escape_pod_01,
    comm_intercept_music_01, patrol_warning_01, distress_cold_signal_01,
    distress_witness_01, distress_already_saved_01, derelict_micro_story_01,
    derelict_cargo_log_01, comm_ghost_signal_01, debris_graveyard_01. `humor.json`:
    humor_ai_existential_01, humor_space_cat_01, humor_cooking_show_01,
    humor_ghost_pirate_01, humor_wrong_number_01, humor_space_junk_art_01,
    humor_retirement_01. `lore.json`: lore_aurelia_beacon_01, lore_earth_broadcast_01,
    lore_charter_fragment_01, lore_first_miners_01, lore_pre_colony_probe_01,
    lore_generation_ship_01, lore_earth_song_01, lore_forgotten_station_01,
    lore_time_capsule_01, lore_star_map_01. `miners_union.json`: union_cave_in_01,
    union_picket_01, union_mutual_aid_01, union_derelict_drill_01, union_scab_01,
    union_ore_spill_01, union_folk_song_01, union_strike_fund_01, union_lost_miner_01,
    union_equipment_swap_01, union_memorial_01. `science_collective.json`:
    collective_specimen_01, collective_experiment_01, collective_data_buy_01,
    collective_quarantine_01, collective_ethics_01, collective_calibration_01,
    collective_peer_review_01, collective_artifact_01, collective_radiation_01,
    collective_grant_01, collective_nova_test_01. `system_specific.json`:
    sys_nexus_market_panic_01, sys_nexus_board_meeting_01, sys_stellaris_art_dealer_01,
    sys_stellaris_tourist_01, sys_verdant_crop_run_01, sys_verdant_tariff_protest_01,
    sys_haven_supply_run_01, sys_haven_newcomer_01, sys_forge_factory_fire_01,
    sys_forge_smuggle_parts_01, sys_forge_union_guild_01, sys_axiom_field_test_01,
    sys_axiom_containment_01, sys_nova_prototype_01, sys_nova_whistleblower_01,
    sys_breakstone_cave_in_02, sys_breakstone_ore_heist_01, sys_iron_deep_signal_01,
    sys_iron_dcmc_patrol_01, sys_crimson_wreck_claim_01, sys_crimson_outlaw_offer_01,
    sys_crimson_ghost_ship_01, sys_fulcrum_encrypted_01, sys_fulcrum_patrol_01,
    sys_fulcrum_weapons_test_01.
  - `data/economy/galaxy_events.json`: `guild_embargo_ore` and `alliance_embargo_food`
    (flavor text); `union_founders_day`, `alliance_harvest_festival`, `breakstone_strike`,
    `medical_breakthrough`, `frontier_pirate_surge`, `forgeworks_shortage` (descriptions).
    `data/ships/ship_types.json`: `prospector`, `consortium_merchantman`.
    `data/crew/crew_members.json`: `leah_chen`. `data/economy/commodities.json`:
    `combat_stims`.
  - Writing-pass notes on the 290 splice repairs. The parallel-negation forms left on
    purpose, inside the 290 strings: campaign_sato_ghost_01, derelict_freighter_01 and
    sys_crimson_ghost_ship_01 (descriptions), campaign_refugee_testimony_01 ("Without
    compensation. Without a timeline."), sys_iron_deep_signal_01 ("isn't magma, isn't...")
    and campaign_larsen_warning_01 ("I can't tell you who. I can't tell you why."). Outside
    them and unchanged by this branch: campaign_sato_ghost_01 choice 0 outcome,
    humor_wrong_number_01 choice 2, sys_nova_prototype_01 choice 2 outcome, and
    sys_crimson_outlaw_offer_01 choice 1 description. The code gate `_NO_X_NO_Y`
    (`[Nn]o \w+,\s*no \w+`) catches only one-word items, so these forms pass it; the
    writing pass owns them. Three sign-offs lost their dash in the old rewrite and now read
    as signatures: campaign_torres_tip_01 ("drop. Wrench"), humor_space_junk_art_01
    ("someone. T.W.") and sys_nova_whistleblower_01 ("everything here. A concerned
    researcher."). `generic.json` also gains distress_oxygen_01 (its rescue outcome), which
    is not among the 290 ids above.
  - Code-built lines: `procedural_missions.py` (the bounty name, the smuggling
    description, and its objective "Keep the {qty} {name} aboard" (new));
    `action_queue.py` ("<Move> cannot fire twice (cooldown N)" (new));
    `combat_engine.py` (Mayday Burst's "The burst breaks contact. You are clear." (new),
    and the dash lines); `dual_tech.py` (`focused_barrage`); `trading_view.py`
    (`NO_PERMIT`); and the dash lines in `attributes.py`, `game.py`, `enemy_subsystems.py`,
    `dialogue.py` (every NPC display name with a title), `enemy_captain.py` (every captain's
    display name), `dual_tech_dialogue.py`, `energy_economy.py`, `futures.py`, `ground.py`,
    `smuggling.py`, `mining_vfx.py`, and `salvage_vfx.py`.
  - Existing lines that now play in new places: the bill of landing's three "Trade Permit
    Acquired: <faction>" notices (where "Universal Bill of Landing" played), every
    captain's `retreat_line`, "Cargo Loaded" on the dialogue, load, and new-game passes, and
    "Fuel tank is full" for an over-full tank (BB-22).

## Bug bash B1 (2026-09-30)

Model rules the Godot port mirrors after syncing this branch (plan B2). The goldens pin
the first four; unit tests are the spec for the rest. Every item below landed, Hanna's
gate and Tomas's two missions included (polish design 6.3, in the author's scope).

- Missions (`mission.py`): the reward `deliver_cargo` (`amount`, `target_id`) takes
  `min(free units of its own mission, amount)` and, only when short, pays every `credits`
  reward `int(amount * credit_mult * delivered / named)` (that operand order); messages
  "+420 Credits (7 of 10 delivered)", "+315 Credits (late, 75% of 600, 7 of 10
  delivered)", and "Delivered <n> <id>" (a full load prints what `remove_cargo` printed).
  `iron_delivery`, `cargo_lost`, `drifters_delivery` and `coolant_run` (4 machinery) hand
  over through it. A mission carries at most one `deliver_cargo`
  (`test_each_hand_over_names_the_accept_cargo` pins authored content, and the board
  generator writes one a delivery); Python reads that one's share for every credits
  reward, so a second hand-over is unsupported in both builds. `check_objectives` returns
  at most one id a call, the first completed in content order; Python's per-frame check
  completes the next one a frame later, and the port loops. The reward `route_fuel` pays
  at most once per landing (game day and system), "+<n> Credits (route fuel)", saved as
  `route_fuel_landing` (`[day, system]`, `[]` for none).
- Board generator (`procedural_missions.py`): a delivery draws one of the origin's legal
  specialty exports (none: no delivery, and `generate_for_system` skips it), keeps the
  draw order (destination, good, quantity), clamps the quantity to `50 //
  volume_per_unit`, pays `max(int(int(base * qty * 1.0) * danger), 150)` with XP `30 + 5
  * qty`, and hands over through `deliver_cargo`. Surveys and salvage add `route_fuel`:
  the shortest round trip through their stops at `jump_fuel_cost(a, b, 10, 0.0)` per leg,
  times fuel's base price. Nexus Prime's day-one contract for the playthrough captain
  stays manufactured goods x3 and pays 360.
- Talk list (`npc_availability.py`, golden `dialogue/npcs_here`): listed when home, not a
  crew member aboard, every prerequisite set, the hide flag unset, and the gate unset or
  `needed_by` naming a mission (the first open mission in content order with an unset
  has_flag objective one of the NPC's trees can set, or an active mission with an unmet
  talk objective naming it). Python lists the twelve Act II v1 NPCs, and the golden holds
  them; leaving them out is the port's clause alone (D-21). Opening an NPC sets its unset
  gate first (`game.py start_dialogue`).
- Content: `tomas_havens`' accept reply sets `drifter_deal_resolved`, and six sub-node
  replies exclude the other deal flag; `the_drifters_deal` and `drifters_delivery`
  auto-accept, the delivery's objectives are `collect_cargo textiles 5` then
  `reach_system stellaris_port`, and `tomas_friendship` moves from the delivery to
  `recruit_trader`; Reva waits for `cargo_lost_accepted`, Dex for `cargo_lost_complete`,
  Hanna for `elena_gave_trading_tips`; `iron_delivery` sets `iron_delivery_moved_on`;
  `merchant_delivery`'s "About that iron ore..." excludes `iron_ore_delivered`, so a
  finished delivery never offers the betrayal (design 2.9) now that the sale sensor's
  `broker_ore_sold` outlives a sale the captain covers; neither golden profile selects
  it, so it joins the unselected responses as `merchant_delivery` greet #8 (golden
  `dialogue/tree_merchant_delivery`: the expert profile's greet steps go from seven to
  six); Emergency Reserves' description (`skills/catalog`).
- Iron job (`iron_consignment.py`; no golden): `on_clock` at a landing and a rest sets
  `iron_delivery_moved_on` from accept day + 19 (`partial_reward_day_count + 1`; day 1
  when no accept day was recorded) for an open job, and from day 20 for a permit holder
  who never took it. An open job with no accept day is ordinary play in Python and not
  only an edge case: a captain who hears Odom's offer at the Nexus Prime hub before
  Larsen's landing trigger has the job accepted by `check_missions`' availability pass,
  which passes no day (aurelia F-32, closed in the port by D-8), so Python moves the
  campaign on from day 20 and pays that job without the soft deadline's decay, where the
  port records the day, waits for accept + 19 and decays the pay. A settled job is left
  to the flag its ending set, and no branch handles a save from before this rule (the
  port mirrors none); `close_on_exit` fails an open job when `iron_delivery_failed` is
  set and sets the flag; `note_sale` sets `broker_ore_sold` when a sale of iron ore draws
  below the reserved count, hidden units counted as held, while the job is open. Python
  runs the clock at the arrival before `_check_auto_triggers`, so Elena can appear on the
  landing the clock fires; the design's DOCKED placement shows her one arrival or
  departure later (plan B2 decides whether to match). The count test at Odom's opening is
  gone in Python.
- Consignment (Python counts; the port's `CargoLots` owns lots): every active mission's
  accept cargo is reserved for it (`reserved_units`, `free_units`, `free_cargo`), counted
  as loaded, not as left: after a loss draws a consignment and the captain buys back,
  Python holds the whole load back where the port's lot holds only what is left (Odom's
  ten, three lost, four bought: Python frees 1 unit, the port 4), so Sell All, Sell Max,
  refining, auctions and other collect legs see fewer free units in Python; the seal and
  the sale sensor read the same loaded count, so after a loss and a top-up a named Sell
  of units the captain bought can be sealed or recorded in Python where the port's lots
  draw the captain's own first (Odom's ten, three lost, five bought: a Sell of 3 sets
  `broker_ore_sold` in Python and records nothing in the port; a board contract's three,
  two lost, four bought: Python seals a Sell of 3 or 4, the port allows up to 4), which
  design 2.2 rule 2's count form ("a sale ... that leaves fewer than ten aboard")
  defines; a board contract's accept cargo is sealed (`sealed_units`; "That cargo is
  sealed under your contract."); collect legs and hand-overs count only the mission's own
  and the captain's units; Sell All, Sell Max, refining, the auction house and the
  Wreckers' Guild leave reserved units aboard. An explicit Sell draws a campaign or
  authored mission's reserved units without a confirm (plan B1 ruling: the prompt would
  be a new line); the port's `sell(..., include_owned)` stands for SP6's confirm, and
  deviation D-22 records the difference. Hiding is allowed and the hidden compartment
  counts as aboard (`held_units`): the reserved count, the seal and the sensor read both
  holds, the captain's own units first, so hiding never makes a sale of the captain's own
  look like a sale of a consignment (plan B1 ruling; the port has no hidden compartment).
  None of `MissionManager`'s new methods (`reserved_units`, `sealed_units`, `free_units`,
  `sale_draws_sealed`, `free_cargo`, `open_missions`) is a port interface: the port's
  `MissionManager` sits at 24 public methods.
- Flag stores (SpaceGame F-C09): Python's save now lays the player's flag store over the
  dialogue manager's copy, in place (`DialogueManager.merged_flags`), so a flag written
  outside a conversation survives the save and a running combat's reference stays live; a
  new game reloads the copy; and the crew loyalty threshold flags now reach the player's
  store too. The port keeps one `FlagStore`; nothing to port.

### Records for plan B2

Consequences of this branch that plan B2 writes into the register, the deviations, the
hand-offs and the writing pass's list. The ids are plan B2's, which follow plan A2's
D-20, F-74 and A12 (polish design 8.1).

- Deviations: D-21 (BB-38: Python's `start_dialogue` trusts its two views and lists the
  twelve Act II v1 NPCs; the port refuses an unlisted NPC, opens a raw tree only for
  `intro_narration`, and excludes the twelve); D-22 (Python's cell: counts with a
  reserved count, the reserved count read as loaded (a loss shrinks no lot) and read by
  the seal and the sale sensor too, an explicit Sell drawing a campaign or authored
  mission's reserved units without a confirm, and the hidden compartment allowed and
  counted as aboard, per the Consignment bullet above); D-23 (BB-27: Python keeps the
  first sale's 1.5x; the port pays the premium from `economy.new_market_premium`, which
  Python ignores); D-25 (BB-3: Emergency Reserves' text names the port's cell while
  Python keeps its 1-fuel floor). No deviation for `deliver_cargo`, one completion a
  check, route fuel, the board generator, the keep rule, the gate set on open, or the
  iron clock, close and sensor: both builds change. If the author ever rules choice 6
  port-only, only the sale sensor moves: the port's sensor takes D-26, and Python keeps
  its count test at Odom's opening.
- BB-9 (plan A2's D-15 note): Python keeps counts, so loaded contract cargo has no
  purchase record here; the port's accept-cargo lot should record the loading station,
  the accept day and the base price as unit price and the loading station's price that
  day as market price, with a mark that it was not bought, so the premium still excludes
  it.
- Dialogue parity: the port's F-33 pin (`dialogue_manager_test.gd`,
  `test_the_seven_unselected_responses_move_to_their_next_node`) gains
  `["merchant_delivery", "greet", 8, 2, "betrayal"]` (available index 2 with its one
  required flag set; B2 confirms it) and counts eight.
- Register: BB-4 closes (F-75); BB-1's false accusation and Sell All close, its scenes
  stay open (F-75); BB-38, BB-67, BB-68, BB-71, BB-72 close and BB-69 stays open for
  Oren's fail-forward (F-76); F-4's closure note (the Talk list now has one filter).
- The writing pass, each a line this branch wrote or moved (N new, F a false fact
  repaired): "That cargo is sealed under your contract." (N); "+420 Credits (7 of 10
  delivered)" and its late form (N); "+<n> Credits (route fuel)" in the notice, the
  mission log and the cantina's board (N); Footing the Bill's hint (F); Drifter's
  Delivery's hint and its objective "Keep Tomas's textiles aboard: 5 Textiles" (F, N; its
  description's "Sell the goods" now reads loosely); Emergency Reserves' description (F);
  the ten first-sale lines (N, choice 17; Crimson Reach's orients only, its lore waits).
  Existing lines in new places: "No cargo to sell" from Sell Max and Sell All over
  consigned cargo, and from Sell All over a hold of quest goods alone, where the press
  was silent before; refining's "Missing: ..." and "Need ..., have ..." and the auction's
  "You do not have 1 of '<id>' in inventory." over free units; "Delivered <n> <id>" from
  `deliver_cargo`; "Progress: iron_delivery_moved_on" in the iron delivery's Mission
  Complete notice (the set_flag reward's existing "Progress: <flag>" form, which shows
  the player a raw flag id beside "Progress: iron_ore_delivered"); "Progress:
  tomas_friendship" moved from Drifter's Delivery's Mission Complete notice to Recruit
  Trader's (the set_flag reward's existing "Progress: <flag>" form).
- Content left for the writing session: the return scenes (`AWAITING_RETURN_SCENES` in
  `tests/test_data/test_one_shot_scenes.py`: Dex, Elena, Oren; `CHECK_GATED_RETURNS`:
  Oren; A1's `PENDING_CHECK_GATED_FLAGS` keeps `oren_intel_received`); the iron scenes,
  states and sensors of design 2.6; the ten crew barks; `data/endings/endings.json`; the
  journal's `auto_m13_oren`, whose trigger `oren_revealed_base` nothing sets and whose
  text (unmarked ships, Guild-class hulls) does not match Oren's scene, to be re-keyed to
  `oren_intel_received` and rewritten to what every route learns (design 6.3);
  `tomas_havens`' start reply "Thanks. I'm Tomas?", where the captain speaks his name
  before he gives it, to become a thank-you and a question about whom they owe for the
  stew (design 6.3); the Forgeworks Compact lore behind the first-sale lines (choice 17).
- Observations: a captain holding The Heirloom Seeds' three food needs five more of their
  own for Union Territory until the seeds' job ends, since the seeds are never handed
  over (A1's SP10 record); Wren is marked needed while the iron job's talk objective is
  open; Drifter's Delivery, once its arrival is locked, finishes wherever five bales are
  next aboard (the collect-then-reach edge A1 accepted); Python's hidden compartment can
  take consigned ore out of the main hold without a sale or a loss, so the later
  iron-scenes plan, whose state table assumes an open job never holds fewer than ten
  without S or L (design 2.2), must either guard `_execute_hide_cargo` or read H as
  `held_units`; route fuel pays once per landing but once per contract origin, so the
  approved "once a trip" overstates it: two surveys or salvages to one distant target,
  accepted at neighboring origins, each pay their own round trip, about 2(d1 + d2) for a
  tour that burns about 2(c + d2) (d1 and d2 the origins' distances to the target, c the
  hop between the origins), an overpayment the board's own contracts allow (SP5 and SP8,
  which own route pricing and the career). Until the iron scenes land, a captain who sold
  Odom's ore and bought back to ten (O4) is offered only the betrayal for the ore at
  Odom's greet while the job is open ("Any word on the ore shipment?" excludes
  `broker_ore_sold`). Its text ("Your hold's empty", "your bay is reading zero") is false
  for that captain, and after the delivery they hear `thanks` ("you don't skim"). Design
  2.6's `waiting_count` and `thanks_replaced` (`iron_job_replaced`,
  `iron_job_done_replaced`) are the writing session's, and the port meets the same
  content once B2 ports the sensor.

## Act II v1

Off behind `ACT_TWO_V1_ENABLED` (tag `act2-v1-archive`). Not ported.

## Orchestration findings

Bugs in `game.py` and the views are design inputs, not parity deviations. They
are listed for the owning sub-projects in the aurelia repo's
`docs/findings_register.md` (SP2 spec Section 6).
