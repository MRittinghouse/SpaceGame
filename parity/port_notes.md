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
  `xp`, `deduct_credits`, `remove_cargo`, `deliver_cargo`, `route_fuel`, `set_flag`,
  `black_market_access`, `kweon_relationship`, `crew`, `trade_permit`, `reputation`,
  `modify_reputation`. Combat victory (`Player.apply_combat_victory`): XP, credits, and
  loot cargo; a negotiated end (`Player.apply_combat_negotiated`) adds loot cargo only,
  when enhanced negotiation earned it: half of each common-table roll, rounded down, at
  least 1.
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
- BB-7 (closed by bug bash B1; see its Records for plan B2): a collect leg tests at least N
  aboard per contract, so two board contracts (smuggling or delivery) with the same
  commodity and destination share one load. One landing pays both while the overlap is
  sold, and the second `remove_cargo` fails silently. Closing it needs per-contract cargo
  reservation in both builds, with BB-7's SP8 and SP9 hand-off.
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
  Hanna for `elena_gave_trading_tips`; `iron_delivery` sets `iron_delivery_moved_on`, and
  three gates wait on that flag in place of the job (BB-4): Elena's
  `auto_trigger_prerequisites` (was `iron_ore_delivered`), Footing the Bill's
  (prerequisite `bill_of_landing`, was `iron_delivery`, plus the flag in
  `required_flags`) and The Dead Ledger's (`available_after` `bill_of_landing`, was
  `iron_delivery`, plus the flag in `required_flags`); the availability golden shows only
  the flag joining its all-flags profile, so these gates reach the port with the data
  sync; `merchant_delivery`'s "About that iron ore..." excludes `iron_ore_delivered`, so
  a finished delivery never offers the betrayal (design 2.9) now that the sale sensor's
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
- Hand-offs: BB-7's shared-load hand-off (aurelia `docs/handoffs.md`, "A collect leg
  tests at least N aboard per contract ... Closing it needs per-contract cargo
  reservation in both builds", from plan A1's port notes) closes: Python reserves each
  mission's accept cargo, rechecks collect legs on free units, hands over through
  `deliver_cargo` and completes one mission a check, so one load pays one contract
  (`test_mission_deliver_cargo.py` `test_one_load_pays_one_contract`;
  `test_mission_consignment.py`
  `test_another_missions_accept_cargo_does_not_fill_a_collect_leg`), and the port's
  `CargoLots` does the same; plan B2 deletes that hand-off bullet.
- The writing pass, each a line this branch wrote or moved (N new, F a false fact
  repaired): "That cargo is sealed under your contract." (N); "+420 Credits (7 of 10
  delivered)" and its late form (N); "+<n> Credits (route fuel)" in the notice and the
  mission log, and "<n> Credits (route fuel)" in the cantina's board detail (N); Footing
  the Bill's hint (F); Drifter's Delivery's hint and its objective "Keep Tomas's textiles
  aboard: 5 Textiles" (F, N; its description's "Sell the goods" now reads loosely);
  Emergency Reserves' description (F); the ten first-sale lines (N, choice 17; Crimson
  Reach's orients only, its lore waits). Existing lines in new places: "No cargo to sell"
  from Sell Max and Sell All over consigned cargo, and from Sell All over a hold of quest
  goods alone, where the press was silent before; refining's "Missing: ..." and "Need
  ..., have ..." and the auction's "You do not have 1 of '<id>' in inventory." over free
  units; the mission log's collect hint "→ <n>/<m> in cargo"
  (`MissionLogView._get_objective_detail`) and the auction picker's "<Name> (cargo, <n>)"
  row (`SellLotView.get_eligible_items`) over free units, so "cargo" can understate the
  hold (7 food aboard with The Heirloom Seeds' 3 reserved: "→ 4/5 in cargo" for Union
  Territory); "Delivered <n> <id>" from `deliver_cargo`; "Progress:
  iron_delivery_moved_on" in the iron delivery's Mission Complete notice (the set_flag
  reward's existing "Progress: <flag>" form, which shows the player a raw flag id beside
  "Progress: iron_ore_delivered"); "Progress: tomas_friendship" moved from Drifter's
  Delivery's Mission Complete notice to Recruit Trader's (the set_flag reward's existing
  "Progress: <flag>" form).
- Content left for the writing session, as plan W3a-S left it ("Writing W3a" below): the
  return scenes landed, and the constants with them (`AWAITING_RETURN_SCENES` and
  `CHECK_GATED_RETURNS` are gone from `tests/test_data/test_one_shot_scenes.py`, and A1's
  `PENDING_CHECK_GATED_FLAGS` from `tests/test_data/test_content_contracts.py`, whose check
  now asserts that no awaited flag is gated); the iron scenes, states and sensors of design
  2.6 landed; the journal's `auto_m13_oren` is re-keyed to `oren_intel_received` and
  rewritten to what every route learns; and `tomas_havens`' start reply reads "Thanks. Who
  do I owe for the stew?" (design 6.3). The observations below on Wren's talk objective,
  the hidden compartment and the O4 captain's greet are settled by the same plan. Still
  open: the ten crew barks and the Forgeworks Compact lore behind the first-sale lines
  (choice 17), plan W3b's (spec 9.2 row 10); and `data/endings/endings.json`, written in
  SP6's paired dialogue session (aurelia `docs/handoffs.md`, SP6).
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

## Writing W1 (2026-10-01)

The writing half's foundations (writing discipline spec, aurelia
`docs/specs/2026-10-01-writing-discipline-design.md`, 9.2 rows 0 to 3), plan W1-S. The
Godot port mirrors these after syncing this branch (plan W1-A). The goldens pin the renderer,
the pronoun key and the data rows; unit tests are the spec for the rest.

- The renderer (`spacegame/models/captain_tokens.py`; golden `dialogue/captain_tokens`).
  `Pronouns` saves as "he/him", "she/her" or "they/them", and `Pronouns.parse` reads any
  other value as they/them. `WORDS` maps each word token to its he/him, she/her and
  they/them renders: `{they}` he/she/they, `{They}` He/She/They, `{them}` him/her/them,
  `{their}` his/her/their, `{Their}` His/Her/Their, `{theirs}` his/hers/theirs,
  `{themself}` himself/herself/themself, `{sir}` sir/ma'am/Captain, `{Sir}`
  Sir/Ma'am/Captain, `{son}` son/girl/kid, `{Son}` Son/Girl/Kid (the she/her "girl" is the
  author's ruling, 2026-10-02). `fill(text, pronouns, day=None)` replaces every
  `\{v:([^|{}]*)\|([^{}]*)\}` first (the first form for he/him and she/her, the second for
  they/them), then every `\{([A-Za-z]+)\}` that names a word token, then `{day}` with the day
  when one is given; any other brace stays as written, so a surface's own fill can run after
  it. Rendering twice changes nothing. `captain_line(text, player)` reads the player's choice
  and game day (an int only) and renders they/them with no day when there is no player. The
  golden records `fill` for six probes and every shipped line that carries a token (three:
  Larsen's greeting and farewell, Szabo's outcome), for the three choices, with the day 61
  and with none (`null`).
- Where Python renders: at each surface's display edge, so every model and golden keeps the
  raw line (the smuggler outcome golden records Szabo's
  `{Son}`). The dialogue view (node text, replies, the Empathic Read line), the
  inline dialogue panels of the deep shafts, Okafor and Wreckers views, the combat view
  (interjections and captains' outcome lines, the whole formatted line), the encounter view
  (name, description, labels, hints, outcomes, before its `{shakedown_demand}` fill, since a
  verb token breaks `format_map`), the banner (`Game._next_mission_notification`, every
  queued line), the crew's mini-game commentary, station chatter, and the galaxy map's news
  ticker (`news_ticker._fill` now fills only the names its context holds and leaves every
  other brace).
- The registry (`tests/writing_gates/registry.py`): the captain's tokens may appear in
  `dialogue/*.json`, `combat/crew_interjections.json`, `combat/captains.json`,
  `combat/captain_variants.json`, `encounters/*.json`, `crew/ambient_dialogue.json`,
  `crew/station_chatter.json` and `economy/news_templates.json`, and nowhere else; each
  surface's own fill is listed beside it (news, the travel log, galaxy events, ground
  contracts, post-capstone templates, auction voices, the encounters' shakedown demand).
  `tests/test_compliance/test_captain_token_render_sites.py` names each print path. The
  port's registry test mirrors the files the port prints. `{player}`, the captain's name,
  stays the news fill's alone (spec 2.7).
- The choice: the save key `pronouns` (`SaveManager._serialize_player`, beside
  `ship_name`), wave A in `tools/parity/snapshots.py`, so every player snapshot in the
  goldens holds `"pronouns": "they/them"` (157 files). `Player.pronouns` is keyword-only,
  default they/them. `Game.initialize_new_game(..., pronouns=Pronouns.THEY)` takes the
  pick; nothing passes it until SP6's creator.
- The data: `intro_narration` has two nodes, `intro_1` (`[Continue]` to `intro_2`) and
  `intro_2` (terminal); Larsen's greeting and farewell carry `{sir}`; Elena's `first_turn`
  line 1 reads "...apply, Chief. Sorry. Captain." for every captain, with no token (the
  author's ruling, 2026-10-02); Szabo's report outcome carries
  `{Son}`; `the_foremans_son` is named "Deferred" and its description says "The one that came
  back deferred."; `bill_of_landing` says "he"; `marcus_recognition.recognition` and
  `.report_buried` and the Log's `auto_m05_marcus` carry the timeline of spec 4.3; the fixer
  is "Glyn Quintela" ("Glyn" alone) in 28 strings, the three NPC records' names among them,
  and the show "Mouthfeel" in two. No id changed.
- The gates (`tests/writing_gates/`: `surfaces.py`, `rules.py`, `registry.py`,
  `allowlist.py`, `allowlist.json`, `act_verbs.txt`) are pure Python over `data/` and the
  source text of `spacegame/views` and `spacegame/models` (the strings built in code, read
  with `ast`, and `capstone_view.py`'s `_TEMPLATE`, the capstone frame, a narration field of
  spec 5.1). The baseline held 529 rows; this branch's fixes leave 519. The three G5
  `vocative` rows left, Odalys's "sweetheart" and Tariq's "darling" (two lines), stay for
  good: a habit the speaker uses with anyone (the author's ruling, 2026-10-02).

### Records for plan W1-A

What plan W1-A ports, syncs and records. The ids it allocates (deviations, register rows,
hand-off entries) are its own.

- Port: the renderer as `CaptainTokens` with the table, the order (verb tokens, then word
  tokens, then `{day}`), the unknown-brace rule and the they/them fallback above, replaying
  `dialogue/captain_tokens`; the choice on `PlayerIdentity`, saved under `pronouns` and added
  to `PlayerSnapshot.KEYS` (`test_the_snapshot_holds_every_wave_a_key_from_its_owner` is the
  check); rendering at the port's surface exits for the surfaces it prints (dialogue,
  interjections, captains, encounters, ambient lines, station chatter), never inside a
  parity-tested model; the news templates wait for a port news surface; the port's
  per-surface brace tests extended to the captain's tokens on those surfaces
  (`test/unit/galaxy_event_test.gd` keeps `{system}` alone).
- Sync: `data/` and the goldens (the new case, the 157 snapshot goldens, `interjections`,
  `outcomes_smuggler`, `lifecycle_the_foremans_son`, `tree_intro_narration`). The gates
  package is not under `data/` or `parity/golden/`, so the cutover copies it by hand or
  widens `tools/sync_data.py`'s trees.
- Tests the sync breaks: B2's `test_the_dex_records_are_listed_one_at_a_time` filters on a
  display name beginning "Dex", which no record carries after the sync, so beats 1, 2, 4
  and 6 find no record where each expects one and the test fails: re-key it on the ids
  `dex_halloran`, `dex_tunnel_contact`, `dex_final_lead`, keeping each beat's expected
  list. No aurelia unit test pins M05's title (`test/unit/mission_manager_test.gd` uses
  only the id `the_foremans_son`, which stays); the synced golden
  `lifecycle_the_foremans_son` carries "Accepted: Deferred". A second test fails at Task 1
  Step 4: `test/unit/dialogue_content_test.gd`'s `test_every_npc_and_tree_loads` pins the
  dialogue totals (nodes, replies, skill checks, replies that set a flag, replies that end
  the conversation) at plan B2's `[742, 1160, 59, 174, 288]`, and the intro's repair
  (`intro_narration` from five nodes and four replies to two and one) makes them
  `[739, 1157, 59, 174, 288]`: re-pin the first two (742 to 739, 1160 to 1157) in the sync
  commit.
- Where plan W1-A's text no longer matches this branch, for its controller to amend before
  Task 1 runs:
  - Koren stays "he" in `data/missions/crew_quests.json` (W2's, under Deferred below), so
    Task 1's "Koren as 'she'" and Step 3's crew quests do not arrive by sync. The sync
    changes nine data files (dialogues, crew interjections, the Alliance encounters,
    missions, journal entries, NPCs, commodities, news templates, the humor encounters)
    plus `SYNC.json`, ten in all, where Step 3 expects about eleven.
  - B2's committed `test_the_dex_records_are_listed_one_at_a_time` pins each beat's exact
    list, so after the sync it fails at beats 1, 2, 4 and 6, where Step 4 expects a pass
    with nothing checked. It has no `for beat: Variant in beats:` loop or
    `is_less_equal(1)` assertion for Step 5's `seen` guard to hang on, and its exact-list
    pins already fail an empty listing, so the guard and Step 6's "no fixer record was
    listed" are unnecessary: Step 10's re-key on the ids is the whole fix.
  - G5's `token_names` (`tests/writing_gates/rules.py`) names a brace `v` only for the full
    `{v:A|B}` form, two forms around exactly one pipe; any other body that begins `v:`
    keeps its whole brace as its name and fails G5 as an unknown token. Task 6's
    `TokenRegistry.names_in` names `v` for any body that begins `v:`, looser than the
    function it cites, so Task 6 ports the full form. Nothing ships wrong meanwhile:
    aurelia's `data/` is a copy this stricter G5 has passed.
- The `change` and `romance` fields need no port code (the port reads named keys only);
  G13's disposition half reads `change` once a tree marks a node.
- `{player}` renders only in the news fill today (spec 2.7): a line that wants the
  captain's name on another surface extends `captain_line`, the port's `CaptainTokens` and
  both registries in one change across both builds.
- For `docs/handoffs.md`'s writing-pass queue (spec 9.2 row 11), every line this branch
  wrote or changed: the two intro cards; Larsen's greeting and farewell; Elena's slip;
  Szabo's `{Son}`; "Deferred" and "The one that came back deferred."; `bill_of_landing`'s
  "he"; Marcus's `recognition` and `report_buried`; `auto_m05_marcus`; the smuggling access
  reason "(Meet Glyn Quintela)".
- Open, for the hand-offs and the desk copy (row 12):
  - The narrator audit's eight `intro_narration` rows (audit.md, dialogues.json rows 1 to
    8), which this branch retired by repairing the intro in place: plan W1-A records that
    W2 skips them (the chunk map's W2 row, or `docs/handoffs.md`'s "The writing pass");
    audit.md stays as dated evidence.
  - The intro is two cards (`intro_1`, `intro_2`) after W1: spec section 8's SP7 entry
    ("replaces the five intro cards") should say two.
  - Spec 2.5's contraction forms: this plan is the renderer's, which spec 2.5 lets change
    the spelling, and it spells `{they} {v:doesn't|don't}` and `{they} {v:wasn't|weren't}`
    with a space after the pronoun; both renderers' tests use the spaced forms. Plan W1-A
    carries the spaced forms into spec 2.5's Contractions bullet and the regenerated desk
    copy, so no writer meets the unspaced ones (which render "shedoesn't").
  - F-016: 22 strings built in code, allowlisted under the gates with F-016 as their
    reason; their rewrite is outside the narrator audit (spec 9.4), and chunk W2 owns it
    (the controller's ruling, 2026-10-02).
- Deferred, each with one owner: spec 7's data rows outside W1, and the allowlist reasons
  that name a later owner.
  - `the_collapse_sequence` (SP10, which rewrites the sequence): Elena's `gate_activation`
    line retired (impact 5.1), the two G9 stage tags (`[Silence]`, `[End of Act One]`) and
    the four G11 "warp" lines, each allowlisted with an SP10 reason.
  - The other ten "warp" rows, and "naval facility" in
    `campaign_pirate_weapons_01.salvage_evidence` (impact 10.8): W2. audit.md flags neither
    word, so W2's list must name them.
  - `merchant_delivery.betrayal_rant`'s three motive questions and the Science Collective
    -5 (impact 8.8): W3, with the iron scenes (spec 9.3, choice 4).
  - `ambient_lines[176]`, replaced by the key (impact 10.14): Tomas's slice.
  - Koren's pronoun in `elena_old_charts` ("his last known position") and
    `elena_charting_stars` ("before he died"; audit.md row 858): W2, whose found-on-the-way
    list (spec 9.4) names Koren's pronoun drift beside the revenue officer in
    `ransom_guild_audit_01`; impact 6.8 files it as polish design 3.2's canon fix.
  - `the_foremans_son`'s last description sentence, "He's carrying something, and it's not
    just guilt.", narration that states Marcus's inner state: W2, though audit.md lists no
    row for it.
  - The seven G9 `observation unquoted` replies (impact 7e): W2. `dialogue_writing_guide.md`
    quotes `embassy_summit.observation_moment` in its Before/After gallery and its NV-7
    Best-of gallery, as shipped; both rows follow that line when W2 rewrites it. The NV-7
    entry's heading ("names what it means") and pattern note ("one synthesis") follow spec
    2.2's edge 6 with it, and the Before/After gallery's last row quotes
    `arna_post_refining.start`'s knowledge-gated reply (G9 `not an act`, W2), which it
    follows the same way. Missing from plan W1-A's Task 12 hand-offs text, which names the
    seven replies alone: W1-A adds the NV-7 heading and pattern note and the
    `arna_post_refining.start` gallery row to W2's list in `docs/handoffs.md`.
  - Spoken lines that pass G9 because their first word is an act verb:
    "[Take care of yourself.]" in `arna_post_payback.what_now`,
    `arna_last_freight_out_closeout.brother` and `.help_offer`, and "[Take care.]" in
    `arna_stays_closeout.check`, farewells said to Arna; and "[Leave it.]" in
    `merchant_delivery.odom_arna_branch_a` to `_c`, an act or a line beside the failing
    "[Drop it. Run it.]": W2. G9 reads a tag's first word only (spec 5.1), so no allowlist
    row carries them and audit.md lists none. Missing from plan W1-A's Task 12 hand-offs
    text: W1-A adds the seven tags to W2's list in `docs/handoffs.md`, since W2's sweep
    reads only the allowlist and audit.md.
- Observations: until SP6's creator every player sees the they/them column; the gates'
  "player-facing" set is every string under `data/` less the sprite manifest, `_` keys,
  lowercase identifiers and six lens authoring keys, plus every string built in code under
  `spacegame/views` and `spacegame/models` less docstrings, logger arguments, blank strings
  and lowercase identifiers; G4 compares person records only; G13's count is 21 trees
  because a skill check whose branches lead on is not an exit, and a reply with a skill
  check leads only to its branches (both builds ignore its next_node_id), which the port's
  gate keeps. G5's token rule checks a file against every name its renderers fill, so a
  brace one news trigger fills and another does not passes it: `news_templates.json`'s
  pm_01 to pm_03 write `{description}`, which the `player_milestone` fill (`{milestone}`
  alone) never supplies; nothing passes milestones to `generate_headlines` today, and the
  port's news surface settles it. Missing from plan W1-A's Task 12 hand-offs text: W1-A
  adds it to `docs/handoffs.md` beside the news templates' entry among the token
  registry's unported files.

## Writing W2 (2026-10-11)

Plan W2-S, the narrator audit's pass (writing discipline spec, aurelia
`docs/specs/2026-10-01-writing-discipline-design.md`, 9.2 row 4 and 9.4), rewrote the shipped
lines its worklist (`tools/writing/w2_rows.json`) names, and plan W2-A brings them to the
Godot port by sync.

### Records for plan W2-A

- What the sync brings: the outcome text of the encounters W2 rewrote, so the encounter
  goldens' content changes (up to 16 `encounters/outcomes_*` files), `dialogue/chatter.json`
  and `dialogue/captain_tokens.json`; no node, reply or record is added or removed, so
  aurelia's `test/unit/dialogue_content_test.gd` totals hold; no brace is added, so the token
  registry holds; Szabo's report keeps its opening, so `captain_surfaces_test.gd` holds; 30
  data files change. (Plan W2-S)
- What W2 fixed: 560 of the audit's 567 open rows, the lines the gates held for W2, the named
  lines and F-016's 22 strings (closed as F-C10), with a travel "warp" made "jump"
  (`ransom_pirate_corvette_01`'s description in `data/encounters/ce4_pressure.json`, 'A pirate
  corvette warps onto your tail.', keeps 'warps', because G11's whole-word match misses the
  inflection; it waits for the later writing chunk that owns the file, which makes the
  one-word 'jumps' swap: T4-29, the author's ruling of 2026-10-11), a "warp
  gate" made "the gate", "naval facility" a Guild enforcement yard, Koren "she", and the Log's
  touched lines in spec 2.4's form. (Plan W2-S)
- What W2 left, and to whom: the price rows and the figures in narration to W3 (record
  tokens, spec 3.7); `auto_m13_oren`, `auto_iron_betrayal` and `iron_delivery`'s discovery
  note to W3's scenes; the collapse sequence to SP10, which chooses its own words; the G13
  exit trees to each tree's rewrite (W3 to W8, SP10); the names to the naming pass; the Act
  II v1 archive to SP11 if it returns (the d1 and d3 capstone narration, the lens's core
  fantasy, the 8 G10 rows, the lens file's double hyphens, and `capstone_view.py`'s frame);
  the `not_rich` condition and its `RICH_THRESHOLD` to SP5; the Log lines W2 did not touch to
  the writing pass. (Plan W2-S's rulings) The reading copy tags the archive's 19
  `data/narrative/` entries "skip, archive", the owner `tools/writing/w2_audit.py` gives
  them: that owner is SP11, as the plan's review ruled. Task 11 meant to put the difference
  to the author as a flag, and none of the ruled flags carries it.
- W3's queue: the strings of plan A1's list that W2 rewrote in the six encounters whose
  parallel-negation forms "The writing pass" names, listed below; every other W2 rewrite
  inside the 120 encounters of plan A1's list is recorded by path in
  `tools/writing/w2_rows.json` and in the reading copy. Outside those encounters, W2 rewrote
  three strings plan A1 changed, listed last with their files. The pass reads them all as W2
  left them. (Plan W2-S; aurelia `docs/handoffs.md`, "The writing pass")
  - `.encounters[id=campaign_larsen_warning_01].choices[id=heed_warning].outcome.description`
  - `.encounters[id=campaign_larsen_warning_01].choices[id=ignore_warning].description`
  - `.encounters[id=campaign_larsen_warning_01].choices[id=ignore_warning].outcome.description`
  - `.encounters[id=campaign_larsen_warning_01].description`
  - `.encounters[id=campaign_refugee_testimony_01].choices[id=document].description`
  - `.encounters[id=campaign_refugee_testimony_01].choices[id=move_on].description`
  - `.encounters[id=campaign_refugee_testimony_01].choices[id=move_on].outcome.description`
  - `.encounters[id=campaign_refugee_testimony_01].choices[id=provide_aid].description`
  - `.encounters[id=campaign_refugee_testimony_01].choices[id=provide_aid].outcome.description`
  - `.encounters[id=campaign_sato_ghost_01].choices[id=ignore].description`
  - `.encounters[id=campaign_sato_ghost_01].choices[id=ignore].outcome.description`
  - `.encounters[id=campaign_sato_ghost_01].choices[id=run_diagnostics].outcome.description`
  - `.encounters[id=campaign_sato_ghost_01].description`
  - `.encounters[id=derelict_freighter_01].choices[id=pass].description`
  - `.encounters[id=derelict_freighter_01].choices[id=pass].outcome.description`
  - `.encounters[id=derelict_freighter_01].choices[id=salvage].description`
  - `.encounters[id=derelict_freighter_01].description`
  - `.encounters[id=sys_crimson_ghost_ship_01].choices[id=avoid].description`
  - `.encounters[id=sys_crimson_ghost_ship_01].choices[id=avoid].outcome.description`
  - `.encounters[id=sys_crimson_ghost_ship_01].choices[id=board].description`
  - `.encounters[id=sys_crimson_ghost_ship_01].choices[id=report].description`
  - `.encounters[id=sys_iron_deep_signal_01].choices[id=alert_union].description`
  - `.encounters[id=sys_iron_deep_signal_01].choices[id=ignore].description`
  - `.encounters[id=sys_iron_deep_signal_01].choices[id=ignore].label`
  - `.encounters[id=sys_iron_deep_signal_01].choices[id=ignore].outcome.description`
  - `.dialogues[id=arna_post_completion].nodes[id=catch_unread].responses[0].text` in `data/dialogue/dialogues.json`
  - `.dialogues[id=arna_post_completion].nodes[id=catch_unread].responses[1].text` in `data/dialogue/dialogues.json`
  - `.missions[id=miners_plight].description` in `data/missions/side_missions.json`
- After W2: `tests/test_data/test_writing_w2_audit.py` becomes the residue check in Task 12,
  so W3 to W8 and SP10 may rewrite any W2 line, but no audit excerpt may come back. (Plan
  W2-S)
- Where plan W2-A's text no longer matches this branch, for its controller to amend before
  Task 1 runs:
  - Task 2 Step 1 expects 798 `###` headings in the reading copy. It renders 799, one per
    worklist entry: Task 9's fix round added the named line
    `.complications[id=reinforcement_arrival].description` (`data/combat/complications.json`)
    to the worklist.
  - The rulings send 16 flags to aurelia's findings register (`docs/findings_register.md`),
    each with its finding under "The findings for aurelia's findings register" below, but no
    step of plan W2-A writes a register row, and Task 2's file list does not name the
    register. Its controller adds that step (one row per finding) or names the plan that
    files them.
  - Task 2 Step 3's hand-off entry says what W2 left by the plan's rulings alone. The flags
    leave work too: to W3 (66 ruled flags and the remainders the table names), the later
    writing chunks (41), SP10 (3) and the naming pass (4), and the unruled flags below go to
    the owners named beside them. The entry carries them, by theme or by pointing to this
    section's table.
  - Task 2 Step 2's word swaps and Step 3's entry say a travel "warp" became "jump";
    `ransom_pirate_corvette_01`'s description keeps "warps onto your tail" for the later
    writing chunk that owns `data/encounters/ce4_pressure.json` (T4-29), so both say that one
    waits.
  - Task 2 Step 2 asks for a bullet for "each flag the run raised": the run raised 209 ruled
    flags in 14 themes and the unruled flags listed below, so a bullet per theme, naming its
    flags, covers them.
- The author's read: the reading copy (`python -m tools.writing.w2_audit read --out <file>`)
  is the record of every line, with the twelve edge rows and the sensation flagged. The
  author read it on 2026-10-11 and approved every proposal ("I accept the changes on all
  fronts."); the rulings follow. (Chunk map; spec 11.2)
  - The edge rows (spec 11.2): all twelve accepted as drafted. Five of them then took a cut
    under a flag's ruling in Task 12: the tourist escort (T3-9), the cat's rescue (T5-1),
    the pendant's Read (T7-5), `the_drifters_deal` (T9-3) and `tomas_new_ledger` (T9-4).
    - `data/crew/crew_members.json` `.crew_templates[id=sable_trent].description`
    - `data/dialogue/dialogues.json`
      `.dialogues[id=arna_last_freight_out_closeout].nodes[id=pendant].subtext`
    - `data/encounters/campaign.json` `.encounters[id=campaign_pirate_weapons_01].description`
    - `data/encounters/humor.json`
      `.encounters[id=humor_space_cat_01].choices[id=rescue].outcome.description`
    - `data/encounters/humor.json` `.encounters[id=humor_wrong_number_01].description`
    - `data/encounters/miners_union.json`
      `.encounters[id=union_strike_fund_01].choices[id=decline].outcome.description`
    - `data/encounters/system_specific.json`
      `.encounters[id=sys_forge_factory_fire_01].choices[id=avoid].outcome.description`
    - `data/encounters/system_specific.json`
      `.encounters[id=sys_stellaris_tourist_01].choices[id=escort].outcome.description`
    - `data/missions/crew_quests.json` `.missions[id=elena_charting_stars].description`
    - `data/missions/crew_quests.json` `.missions[id=tomas_new_ledger].description`
    - `data/missions/missions.json` `.missions[id=the_drifters_deal].description`
    - `data/ships/modules.json` `.modules[id=legendary_phantom_shroud].description`
  - The sensation (spec 2.2 edge 1): refused. Spec 2.3's provisional After stands ("at a
    frequency that rattles in your teeth"), and no sensation is written back in:
    `data/encounters/campaign.json`
    `.encounters[id=campaign_anomaly_deepens_01].choices[id=approach].outcome.description`.
    Task 12's cut T4-1 then ended the line on the timestamp.
  - The plan review's rulings (the author, 2026-10-11, aurelia 869afde): the Act II v1
    archive goes to SP11; the Log takes the past tense (spec 2.4's form); the word swaps
    stand (a travel warp becomes a jump or the gate, the naval words as ruled).
  - Every other line: none was refused or redirected, so each stands as W2 wrote it, apart
    from the flag cuts below. A few of those cuts also added words, each shown old beside new
    in the final reading copy: T4-24 borrows the sibling civilian wreck's "Small finder's fee."
    to give the hulk's 60 credits a source; T5-1 adds "for the cat" to the reward notice;
    T6-9's submit outcome reflows its verbs ("scans every container and cross-references
    serial numbers"); and the words around a cut were composed for T3-3 ("Vex escorts you
    through two debris fields"), T6-6 ("Demand a higher fee."), T7-12 ("She says it too
    fast."), T8-9 ("the inside of anyone's lungs if they stayed long enough") and T9-4 ("the
    question: what kind of trader does Tomas want to be").
  - The flags for the author: 209 flags. The author ruled 208 of them at the read, in 14
    themes, taking each theme's recommended ruling, and T3-29 follows theme 1's ruling. The
    table after these notes gives each flag's theme by number and its owner; the themes
    follow, each with its ruling, then the findings the rulings send to aurelia's findings
    register. Of the 74 cuts the rulings gave Task 12, it made 71, in 94 lines; the other
    three stand under their own theme's ruling (a hint that repeats its label stands): T4-15,
    T4-16 and T6-36.
    T3-29, raised in Task 3 and parked by the ledger until the author ruled on forecasts as a
    class, follows that ruling: the final fix wave cut "Breakstone will hear about it." from
    `sys_breakstone_ore_heist_01.scavenge`'s outcome, which now ends on "says nothing.". The
    same wave cut "for now" from `auto_p5_first_salvage_rights_concession` ("The Guild field
    rights stayed unchanged."), a W2 Log line no flag named, after T4-3's ruling that "For
    now." is a forecast.
    Seven of the 71 are the ready cuts the themes 'Untouched lines in encounters W3 reads' and
    'Untouched encounter lines outside W3's queue' gave Task 12 in W2 lines: T5-7, T5-17, T6-15,
    T6-25, T6-33, T6-9 and T6-26.
    T8-4 is made in
    full: `auto_sa_v_longer_ledger` also loses "He named one person at the end: Ilse Vey at
    Meridian. Did not elaborate.". The entry fires on `investment_introduced`, and Odom names
    Meridian and Ilse Vey for the first time in `graduation_pointer`, which that flag opens
    (SA-V's design, ROADMAP item 7). The SA-V scenario test's AC-9 check now asserts that the
    entry does not name them. A Log line for the name would be a new entry on a new flag,
    outside W2.
    - The themes, each with the author's ruling and the flags inside it that went to another
      owner. Where a ruling states a rule, the chunks that next rewrite these lines keep it: a
      forecast or remark after the image goes (theme 1); a hint names the act and nothing
      more, and a hint that repeats its label stands (theme 2); the contract holds over the
      audit's choices (theme 3); a line recalls only what every path to it shows (theme 4);
      and the news ticker is the world's press (theme 13).
      - Theme 1, shipped narrator remarks kept inside lines W2 rewrote (41, with T3-29): Task 12
        makes the named cut or one-word swap in each W2 line, so it ends on the image before
        the remark, and adds no new writing. The remarks are kickers, asides, guesses at
        someone's mind and forecasts after the image.
      - Theme 2, W2 hints that carry a reason, or only repeat their label (14): a hint names
        the act and nothing more. Task 12 cuts the reason, risk or set-up from each W2 hint
        here (taking the outcome's own words where a hint has no act), and a hint that repeats
        its label stands. T2-17 goes to W3, since recasting thirteen world-fact hints as acts
        is new writing; `anomaly_gravity_01.study`'s hint alone has a ready swap.
      - Theme 3, clauses the audit passed or chose that the contract may still fail (8): hold
        these fields to the contract over the audit's choices. Task 12 cuts each named clause
        in the W2 lines, and the untouched lines inside the same flags go to their encounters'
        owners. T6-19 goes to W3, since six of its seven inner-state lines are untouched in
        encounters on plan A1's list. T7-7 goes to the later writing chunk, since the whole
        Read is a past fact and a cut would leave Arna's node without a Read.
      - Theme 4, lines that recall what the captain's path may not have shown (9): a line may
        recall only what every path to it shows. Task 12 cuts or swaps the W2 lines here, and
        the two triggers no cut can fix (T8-1, T8-3) go to the findings register. T7-2 goes to
        the later writing chunk, since both Arna Reads are untouched and belong to her trees'
        rewrite.
      - Theme 5, text that promises what the code does not do (12): each goes to the findings
        register as a defect of words against systems, and Task 12 changes only the military
        hulk's pay line (T4-24). T5-6 goes to W3, whose record tokens make the pirate's spoken
        200 credits read the real 50 CR charge.
      - Theme 6, content the game never shows, or shows with raw ids (4): each goes to the
        findings register as a code or data defect, and the wording stays as W2 drafted it;
        the port's journal and news work inherit the register's decisions.
      - Theme 7, questions for Act I's ending and the held-back missions (3): all three go to
        SP10, and no W2 text changes. The intervene hint's reason clause in
        `distress_pirate_attack_01`, "Two against two changes the odds.", goes with W3's read
        of that encounter. T2-10's choice is marked as a fight and starts none, which is
        already finding F-51.
      - Theme 8, the same name or signature used for several people, and words the gates miss
        (6): the names go to the naming pass, and the gesture and the stray "warps" to the
        chunks that rewrite those trees and `ce4_pressure.json`, with no Task 12 change. T7-8
        is open: Marcus's "without looking up", reworded as "does not look up" for Arna, Odom,
        Mossa and Wulan, waits for the author's ruling on the gesture, which each tree's
        rewrite then applies, and Arna's W2 Read needs a new observable. T4-29's one-word
        "jumps" swap waits for the later writing chunk that owns `ce4_pressure.json`.
      - Theme 9, untouched lines in encounters W3 reads (62): W3, which restyles these
        encounters under spec 9.2 row 11, takes every line, and Task 12 made only the ready
        cuts in the five W2 lines these flags also name (T5-7, T5-17, T6-15, T6-25, T6-33).
      - Theme 10, untouched encounter lines outside W3's queue (28): each goes to the later
        writing chunk for its file, and Task 12 made only the ready cuts in the two W2 lines
        T6-9 and T6-26 name.
      - Theme 11, dialogue tree lines W2 did not touch (7): each goes to the later writing
        chunk that rewrites its tree; the Observation failure branches (T7-14) need structure
        as well as words, and that chunk owns both.
      - Theme 12, Log entries outside W2 still in the old form (3): the later writing chunk
        applies spec 2.4's past-tense, acts-only Log form to them, and Task 12 changed none.
        T11-3 goes to W3, since the plan's overlaps ruling gives its three scenes to W3, whose
        rewrite spec 2.4's form binds.
      - Theme 13, records and docs plan W2-A should carry (4): the bullet "Plan W2-A's
        records" below notes each item, ruling the news ticker the world's press so its wry
        tags stand, and Task 12 changed no game text for them.
      - Theme 14, flags already fixed or answered (8): each is closed with no action.
    - The findings for aurelia's findings register (`docs/findings_register.md`): 16 flags,
      each needing a code or data decision that a text-only pass cannot make, and none has a
      register row yet. Data checked at this branch's head.
      - T3-20, `sys_crimson_wreck_claim_01`: steal_it's outcome ends "You leave with a full
        hold and two new enemies.", while the choice pays 250 CR and 15 XP and leaves the hold
        and every standing as they were. Its watch outcome also ends on the kicker "Nobody
        wins.".
      - T3-26, `sys_haven_newcomer_01.give_credits` and `sys_haven_supply_run_01.donate`: two
        gifts cost the player nothing. The care package transfers "a small credit bundle and a
        crate of nutri-packs" and deducts neither (20 XP, +10 Frontier Alliance); the donation
        hands over "a crate of supplies", takes no cargo and pays 75 CR. The give_credits
        hint's "to help them get started" reads as a reason (spec 2.2 edge 9).
      - T4-30, `ransom_pirate_corvette_01.pay`: the hint's "Your reputation does not." promises
        a lasting cost, but paying costs 200 CR, gives 5 XP and moves no standing.
      - T5-5, `humor_bureaucracy_01.bribe`: the certificate "gets you a 5% discount at Guild
        administrative offices", which no system grants; the choice costs 30 CR and gives 20
        XP.
      - T5-12, `humor_ai_existential_01.console`: the course correction "saves you an hour of
        travel time", but nothing changes; the choice gives 15 XP.
      - T5-28, outcomes in eleven humor and lore encounters (the table names them): each pays
        credits the text does not explain, such as Declan's keepsake crate paying 60 CR, or
        powering the miners' memorial buoy paying 25 CR where it would cost.
      - T6-14, `guild_contract_01.counter`: Sable offers "an improved rate on your first three
        deliveries", but the choice pays 120 CR, 10 XP and +5 Commerce Guild at once, and
        nothing sets up deliveries.
      - T6-23, `alliance_patrol_volunteer_01.intel`: the hint offers "the suspicious contacts
        in your sensor log", but the choice appears whether or not the captain has logged any.
      - T6-24, `alliance_moonshine_01.buy`, `alliance_smuggler_medicine_01.buy_some`,
        `alliance_festival_01.trade_only` and `union_mutual_aid_01.take_rations`: each outcome
        describes buying or receiving goods (coolant drums, medicine, festival cargo, rations),
        yet each pays the captain 60 to 100 CR and puts nothing in the hold.
      - T6-29, `union_strike_fund_01.donate_big`: the outcome ends "It opens doors in
        Breakstone." about a pin the game never records. The +10 Miners' Union standing is
        real and can unlock perks, so the line is half true.
      - T8-1, `auto_p3_first_dispute_attended`: the entry describes a Verdant council session,
        but its flag fires on the first dispute anywhere, so a captain whose first dispute is
        elsewhere reads a session that never happened. The same holds for
        `auto_p4_first_alliance_congress_attended`, which compares its room with Verdant's. A
        venue-neutral line would drop every delegate, so the fix is a Verdant-only trigger.
      - T8-3, `auto_arna_brother_reveal`: the brother story fires when The Buyer completes, but
        Arna tells it only if the captain asks "What about your brother?", so otherwise the Log
        tells a story the captain never heard. The trigger has to move to the brother node.
      - T8-6, `data/journal/travel_log_templates.json` and `spacegame/models/travel_log.py`:
        only first-visit Log lines are ever written. The trade, encounter and event generators
        have no caller, so 15 of the 26 templates never show, and if called, they would print
        raw ids.
      - T8-7, `first_visit.nexus_prime`: every captain starts at Nexus Prime and the visit
        count starts at one, so this rewritten line never fires; "First visit" also contradicts
        the captain's apprenticeship there.
      - T10-1, `data/economy/news_templates.json`'s ge_* and me_* templates
        (`spacegame/engine/game.py` 5874 to 5918): the news ticker fills faction and system
        names with raw ids, so headlines read "commerce_guild imposes trade embargo" or name
        "nexus_prime"; the embargo headline also repeats its description.
      - T10-2, pe_03, pe_04 and pm_03: these templates would run the event text into the next
        sentence without a full stop, but nothing feeds the ticker those events today.
      - Unruled, for the register's owner to weigh: T9-6's check found
        `data/ground/campaign/mission_16_pirate_base.json` named by no mission's
        `ground_mission_id`.
  - Plan W2-A's records, which the author's ruling of 2026-10-11 on the 'Records and docs'
    theme asks to note each item, ruling the news ticker in-world press so its wry tags stand:
    - T10-3: the news ticker (`data/economy/news_templates.json`) is the world's press, an
      in-world document in third-person bulletins, not narration. Spec 2.2 edge 5's
      narrator-joke test does not bind it, and its wry tags stand (ge_festival_04 'unpaid,
      naturally.', flavor_42 'And your reputation.', pm_02 'One more name the sector won't
      forget.', ge_embargo_03 'As usual.', ge_festival_05 'Almost works.', pe_04 'Again.').
      Plan W2-A carries the classification into the writing decisions log beside spec 5.1's
      narration-fields table.
    - T4-52: the plan's ruling on narration that decides for the player (spec 2.2 edge 8)
      fixed the audit's seven outcomes, but those were not every case. `ce4_variety.json`'s
      `bait_patrol_officer_01.decline` outcome, `bait_civilian_lure_01.scan_first`'s failure
      and `bait_comm_relay_01.decode`'s failure also decide for the player, and their lines
      carry owners in the table (T4-17, T4-18, T4-19).
    - T7-13: `requirements/dialogue_writing_guide.md` contradicts the spec and the gates
      outside NV-7. Section 8's Observation Checks GOOD example uses the filter verb 'You
      notice' (spec 2.2 edge 2) and a double hyphen. Canonical Format says to omit N on a
      knowledge-flag-gated reply, which G9 fails. It lists three valid skills where its
      infrastructure note lists seven. NV-7's other headings and several rows keep em dashes.
      The guide's next edit fixes them.
    - T10-5: `requirements/overhaul/42_ui_chrome_components.md:114` still gives the docked
      header with an em dash as its FONT_HEADING example, while the game renders 'DOCKED:
      NEXUS PRIME'. The two archive docs (`requirements/archive/journal_system.md:155`,
      `requirements/archive/shipyard_overhaul.md:507`) quote old forms as history and need
      nothing.
  - Flags the author's table does not carry, all unruled, for plan W2-A to carry to their
    owners: Task 12's own, raised after the read, and earlier ones that ledger rulings or
    reviewer minors raised but that never reached the table.
    - `data/dialogue/dialogues.json` `arna_last_freight_out_closeout.pendant_truth`: after
      T7-5's cut, Arna's "You got three of them, I think." answers the reply "I have."; the
      chunk that rewrites her tree takes it with T7-5's remainder.
    - Narrator inferences left in W2 lines outside their named cuts, each for the chunk that
      next rewrites its file: `mission_16_pirate_base` story_triggers[1] ("Someone spent a
      fortune building this place."); `mission_16_the_fulcrum` story_triggers[3] ("The system
      is ready.") and [4] ("When the star collapses, they walk through this gate ...");
      `campaign_old_allies_01` ("The pieces are falling into place.");
      `campaign_pirate_weapons_01.mark_and_leave` ("By the time anyone responds, the debris
      will be scattered ..."); `lore_star_map_01.analyze` ("The disc is either impossibly old
      or impossibly precise.").
    - `sys_crimson_ghost_ship_01.report`: the hint now opens on "Transmit its coordinates",
      and its "its" depends on the encounter text; a later pass may name the Margrave.
    - T4-7's fragment "For the last three jumps: ..." and T5-24's "your home system" stand,
      since the theme adds no new writing; the chunk that next rewrites each line reads them.
    - T3-27: `sys_haven_newcomer_01.guide`'s outcome (`data/encounters/system_specific.json`)
      keeps audit row 18's "The young voice (a teenager's) thanks you", a possessive with its
      noun left out; the ledger offered "The teenager on the comms thanks you three times
      before signing off.". Owner: W3, whose queue holds the encounter.
    - T3-28: two adopted hints repeat their labels, `sys_crimson_outlaw_offer_01.refuse`'s
      "Refuse and hold course." and `distress_already_saved_01.continue`'s "Resume your
      route.". Closed under theme 2's ruling: a hint that repeats its label stands.
    - T8-12: `first_visit.crimson_reach` (`data/journal/travel_log_templates.json`) ends "No
      questions asked here.", which can read as a generalization about the place; the ledger
      offered "No questions asked." or a cut ending on "then looked away.". Owner: the later
      writing chunk that owns the file.
    - T8-13: `auto_p5_first_reach_arbitration` (`data/journal/entries.json`) keeps "The
      delegates came in knowing what they wanted.", another character's state of mind in the
      Log (spec 2.4, 6.2). A plain cut would leave "Two of them" without an antecedent, so the
      ledger offered "Two of the delegates had been in the same room before.". Owner: the
      later writing chunk that owns the file.
    - From Task 5's review: `humor_wrong_number_01.play_along`'s outcome
      (`data/encounters/humor.json`), a W2 draft, keeps "Francine is so touched by Rodriguez's
      sudden emotional growth", the narrator reading an NPC's feeling with irony (spec 2.2
      edge 5); T5-3 covered only "(Rodriguez)". Owner: W3, whose queue holds the encounter.
    - From Task 7's review: two Observation replies W2 made into speech now meet a seam in
      their trees, and they join T7-14 with the later writing chunk that rewrites each tree.
      `keren_meet.start`'s reply fails to `inspect`, where Keren carries on as if nothing was
      said; `oren_tak_meeting.start`'s reply leads on both branches to `suspicious`, which
      answers "Glyn" though the captain never said the name on that path.
    - From Task 2's review: `comm_intercept_static_01.log`'s outcome
      (`data/encounters/generic.json`), a W2 draft, ends on the maxim "The Expanse is full of
      ghosts on dead frequencies." after the image. It is the audit's chosen end point, the
      class the author cut in T3-6. Owner: W3, whose queue holds the encounter; a cut also
      regenerates the goldens.

| Flag | Theme | Where | The author's ruling (2026-10-11) |
|---|---|---|---|
| T2-1 | 1 | `data/encounters/generic.json .encounters[id=anomaly_gravity_01].choices[id=study].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T2-2 | 9 | `data/encounters/generic.json .encounters[id=anomaly_gravity_01].choices[id=flee] (description and outcome.description)` | W3 |
| T2-3 | 9 | `data/encounters/generic.json .encounters[id=cargo_lost_distress].choices[id=press_on].outcome.description` | W3 |
| T2-4 | 10 | `data/encounters/generic.json .encounters[id=cargo_stowaway].choices[id=work].outcome.description` | the later writing chunk that owns the file |
| T2-5 | 9 | `data/encounters/generic.json .encounters[id=comm_ghost_signal_01].choices[id=trace].outcome.description` | W3 |
| T2-6 | 9 | `data/encounters/generic.json .encounters[id=derelict_cargo_log_01].choices[id=download] (description and outcome.description)` | W3 |
| T2-7 | 9 | `data/encounters/generic.json .encounters[id=debris_graveyard_01].choices[id=search].description and .choices[id=avoid].description` | W3 |
| T2-8 | 9 | `data/encounters/generic.json .encounters[id=derelict_micro_story_01].choices[id=scan].outcome.description` | W3 |
| T2-9 | 9 | `data/encounters/generic.json .encounters[id=distress_oxygen_01].choices[id=rescue].description` | W3 |
| T2-10 | 7 | `data/encounters/generic.json .encounters[id=distress_pirate_attack_01].choices[id=intervene]` | SP10; the intervene hint's reason clause, 'Two against two changes the odds.', goes to W3 |
| T2-11 | 10 | `data/encounters/generic.json .encounters[id=legendary_corsair_king].choices[id=fight].outcome.description and .choices[id=flee].outcome.description` | the later writing chunk that owns the file |
| T2-12 | 10 | `data/encounters/generic.json .encounters[id=legendary_the_collector].choices[id=fight].outcome.description and .choices[id=flee].outcome.description` | the later writing chunk that owns the file |
| T2-13 | 10 | `data/encounters/generic.json .encounters[id=legendary_void_leviathan].choices[id=flee].outcome.description; .encounters[id=escape_pod_adrift].choices[id=salvage].outcome.description` | the later writing chunk that owns the file |
| T2-14 | 9 | `data/encounters/generic.json .encounters[id=shakedown_pirate_01].choices[id=fight].outcome.description` | W3 |
| T2-15 | 1 | `data/encounters/generic.json .encounters[id=smuggler_offer_01].choices[id=buy] (outcome.description and description)` | Task 12 cut its W2 line (the outcome); the buy hint, untouched, goes to the later writing chunk that owns the file |
| T2-16 | 9 | `data/encounters/generic.json .encounters[id=wildlife_swarm_01].choices[id=observe].outcome.description` | W3 |
| T2-17 | 2 | `data/encounters/generic.json hints: cargo_stowaway.work, derelict_cargo_log_01.strip, derelict_micro_story_01.board, distress_cold_signal_01.investigate and .log_it, legendary_iron_maw.fight, merchant_trader_01.trade, patrol_warning_01.heed and .volunteer, anomaly_gravity_01.study` | W3 (`anomaly_gravity_01.study`'s hint alone has a ready swap) |
| T2-18 | 8 | `data/encounters/generic.json .encounters[id=distress_already_saved_01].choices[id=hail].outcome.description` | the naming pass |
| T3-1 | 1 | `data/encounters/system_specific.json, sys_axiom_containment_01.choices[id=hold].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T3-2 | 1 | `data/encounters/system_specific.json, sys_crimson_outlaw_offer_01.choices[id=refuse].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T3-3 | 1 | `data/encounters/system_specific.json, sys_crimson_outlaw_offer_01.choices[id=pay].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T3-4 | 1 | `data/encounters/system_specific.json, sys_fulcrum_patrol_01.choices[id=retreat].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T3-5 | 1 | `data/encounters/system_specific.json, sys_fulcrum_weapons_test_01.choices[id=scan].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T3-6 | 3 | `data/encounters/system_specific.json, sys_fulcrum_encrypted_01.choices[id=ignore].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T3-7 | 1 | `data/encounters/system_specific.json, sys_fulcrum_patrol_01.choices[id=bluff].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T3-8 | 1 | `data/encounters/system_specific.json, sys_haven_newcomer_01.choices[id=guide].outcome.description and choices[id=pass].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T3-9 | 1 | `data/encounters/system_specific.json, sys_stellaris_tourist_01.choices[id=escort].outcome.description (EDGE)` | Task 12 cuts it (a line W2 rewrote) |
| T3-10 | 3 | `data/encounters/system_specific.json, sys_stellaris_art_dealer_01.choices[id=accept_appraisal].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T3-11 | 2 | `data/encounters/system_specific.json, sys_breakstone_cave_in_02.choices[id=move_on].description and sys_crimson_ghost_ship_01.choices[id=report].description` | Task 12 cuts it (a line W2 rewrote) |
| T3-12 | 1 | `data/encounters/system_specific.json, sys_stellaris_art_dealer_01.choices[id=decline].outcome.description; also sys_axiom_field_test_01.choices[id=decline].outcome.description` | Task 12 cut its W2 line (the art dealer's decline outcome); `sys_axiom_field_test_01.decline`'s outcome, untouched, goes to the later writing chunk that owns the file |
| T3-13 | 10 | `data/encounters/system_specific.json, sys_verdant_tariff_protest_01: choices record (hint and outcome), support outcome, ignore outcome` | the later writing chunk that owns the file |
| T3-14 | 9 | `data/encounters/system_specific.json, sys_haven_supply_run_01: choices escort (hint) and decline (outcome)` | W3 |
| T3-15 | 10 | `data/encounters/system_specific.json, sys_forge_smuggle_parts_01: outcomes of buy, report, decline` | the later writing chunk that owns the file |
| T3-16 | 10 | `data/encounters/system_specific.json, sys_forge_union_guild_01: outcomes of side_union and side_guild` | the later writing chunk that owns the file |
| T3-17 | 10 | `data/encounters/system_specific.json, sys_nova_prototype_01: scan_drone hint, help_recover outcome` | the later writing chunk that owns the file |
| T3-18 | 9 | `data/encounters/system_specific.json, sys_iron_deep_signal_01.choices[id=record].outcome.description` | W3 |
| T3-19 | 9 | `data/encounters/system_specific.json, sys_iron_dcmc_patrol_01: description, negotiate outcome` | W3 |
| T3-20 | 5 | `data/encounters/system_specific.json, sys_crimson_wreck_claim_01: steal_it outcome, watch outcome` | aurelia's findings register (its finding is listed above) |
| T3-21 | 9 | `data/encounters/system_specific.json, sys_crimson_outlaw_offer_01: description, counter outcome` | W3 |
| T3-22 | 9 | `data/encounters/system_specific.json, sys_crimson_ghost_ship_01.choices[id=board].outcome.description` | W3 |
| T3-23 | 9 | `data/encounters/system_specific.json, sys_fulcrum_encrypted_01: intercept hint, intercept outcome, trace outcome` | W3 |
| T3-24 | 9 | `data/encounters/system_specific.json, sys_fulcrum_patrol_01: description, retreat hint` | W3 |
| T3-25 | 10 | `data/encounters/system_specific.json, sys_fulcrum_weapons_test_01.choices[id=scan].description` | the later writing chunk that owns the file |
| T3-26 | 5 | `data/encounters/system_specific.json, sys_haven_newcomer_01.choices[id=give_credits] (hint, outcome); sys_haven_supply_run_01.choices[id=donate].outcome` | aurelia's findings register (its finding is listed above) |
| T3-29 | 1 | `data/encounters/system_specific.json, sys_breakstone_ore_heist_01.choices[id=scavenge].outcome.description` | Task 12's final fix wave cuts it (a line W2 rewrote), under theme 1's ruling on a forecast after the image |
| T4-1 | 1 | `data/encounters/campaign.json .encounters[id=campaign_anomaly_deepens_01].choices[id=approach].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T4-2 | 1 | `data/encounters/campaign.json .encounters[id=campaign_anomaly_deepens_01].choices[id=deep_scan].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T4-3 | 1 | `data/encounters/campaign.json .encounters[id=campaign_final_warning_01].choices[id=comply].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T4-4 | 1 | `data/encounters/campaign.json .encounters[id=campaign_larsen_warning_01].choices[id=heed_warning].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T4-5 | 1 | `data/encounters/campaign.json .encounters[id=campaign_pirate_weapons_01].choices[id=mark_and_leave].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T4-6 | 1 | `data/encounters/campaign.json .encounters[id=campaign_pirate_weapons_01].choices[id=salvage_evidence].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T4-7 | 1 | `data/encounters/campaign.json .encounters[id=campaign_guild_shadow_01].description` | Task 12 cuts it (a line W2 rewrote) |
| T4-8 | 1 | `data/encounters/campaign.json .encounters[id=campaign_old_allies_01].description` | Task 12 cuts it (a line W2 rewrote) |
| T4-9 | 1 | `data/encounters/campaign.json .encounters[id=campaign_refugee_testimony_01].choices[id=move_on].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T4-10 | 1 | `data/encounters/ce4_variety.json .encounters[id=bait_mining_rig_01].choices[id=scan_drive].failure_outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T4-11 | 2 | `data/encounters/campaign.json .encounters[id=campaign_ledger_courier_01].choices[id=refuse].description` | Task 12 cuts it (a line W2 rewrote) |
| T4-12 | 2 | `data/encounters/campaign.json .encounters[id=campaign_refugee_testimony_01].choices[id=move_on].description` | Task 12 cuts it (a line W2 rewrote) |
| T4-13 | 2 | `data/encounters/campaign.json .encounters[id=campaign_old_allies_01].choices[id=hold_back].description` | Task 12 cuts it (a line W2 rewrote) |
| T4-14 | 2 | `data/encounters/campaign.json .encounters[id=campaign_final_warning_01].choices[id=comply].description` | Task 12 cuts it (a line W2 rewrote) |
| T4-15 | 2 | `data/encounters/campaign.json .encounters[id=campaign_black_market_intel_01].choices[id=decline].description` | stands: a hint that repeats its label stands (theme 2's ruling) |
| T4-16 | 2 | `data/encounters/ce4_pressure.json .encounters[id=shakedown_food_blockade_01].choices[id=refuse].description` | stands: a hint that repeats its label stands (theme 2's ruling) |
| T4-17 | 9 | `data/encounters/ce4_variety.json .encounters[id=bait_civilian_lure_01].choices[id=scan_first].failure_outcome.description` | W3 |
| T4-18 | 10 | `data/encounters/ce4_variety.json .encounters[id=bait_comm_relay_01].choices[id=decode].failure_outcome.description` | the later writing chunk that owns the file |
| T4-19 | 10 | `data/encounters/ce4_variety.json .encounters[id=bait_patrol_officer_01].choices[id=decline].outcome.description` | the later writing chunk that owns the file |
| T4-20 | 10 | `data/encounters/ce4_variety.json .encounters[id=bait_patrol_officer_01].choices[id=verify_id].description` | the later writing chunk that owns the file |
| T4-21 | 9 | `data/encounters/ce4_variety.json .encounters[id=bait_mining_rig_01].choices[id=scan_drive].description` | W3 |
| T4-22 | 10 | `data/encounters/ce4_variety.json .encounters[id=trader_contraband_01].choices[id=verify].description` | the later writing chunk that owns the file |
| T4-23 | 10 | `data/encounters/ce4_variety.json .encounters[id=derelict_military_hulk_01].choices[id=pass].description` | the later writing chunk that owns the file |
| T4-24 | 5 | `data/encounters/ce4_variety.json .encounters[id=derelict_military_hulk_01].choices[id=pass].outcome.description` | Task 12 adds the sibling civilian wreck's 'Small finder's fee.', giving the 60 credits a source (a line W2 rewrote) |
| T4-25 | 10 | `data/encounters/ce4_variety.json .encounters[id=derelict_military_hulk_01].choices[id=board_blind].outcome.description` | the later writing chunk that owns the file |
| T4-26 | 10 | `data/encounters/ce4_variety.json .encounters[id=derelict_military_hulk_01].choices[id=spot_threats].failure_outcome.description` | the later writing chunk that owns the file |
| T4-27 | 10 | `data/encounters/ce4_variety.json .encounters[id=derelict_military_hulk_01].description` | the later writing chunk that owns the file |
| T4-28 | 10 | `data/encounters/ce4_variety.json .encounters[id=trader_contraband_01].description` | the later writing chunk that owns the file |
| T4-29 | 8 | `data/encounters/ce4_pressure.json .encounters[id=ransom_pirate_corvette_01].description` | the later writing chunk that owns the file, which makes the one-word 'jumps' swap |
| T4-30 | 5 | `data/encounters/ce4_pressure.json .encounters[id=ransom_pirate_corvette_01].choices[id=pay].description` | aurelia's findings register (its finding is listed above) |
| T4-31 | 10 | `data/encounters/ce4_pressure.json .encounters[id=ransom_pirate_corvette_01].choices[id=threaten].failure_outcome.description` | the later writing chunk that owns the file |
| T4-32 | 10 | `data/encounters/ce4_pressure.json .encounters[id=shakedown_medical_strongarm_01].choices[id=give].description` | the later writing chunk that owns the file |
| T4-33 | 10 | `data/encounters/ce4_pressure.json .encounters[id=shakedown_food_blockade_01].choices[id=give].outcome.description` | the later writing chunk that owns the file |
| T4-34 | 9 | `data/encounters/campaign.json .encounters[id=campaign_sato_ghost_01].choices[id=run_diagnostics].description` | W3 |
| T4-35 | 9 | `data/encounters/campaign.json .encounters[id=campaign_sato_ghost_01].choices[id=investigate].description` | W3 |
| T4-36 | 9 | `data/encounters/campaign.json .encounters[id=campaign_sato_ghost_01].choices[id=investigate].outcome.description` | W3 |
| T4-37 | 9 | `data/encounters/campaign.json .encounters[id=campaign_pirate_weapons_01].choices[id=salvage_evidence].description` | W3 |
| T4-38 | 9 | `data/encounters/campaign.json .encounters[id=campaign_pirate_weapons_01].choices[id=strip_parts].description` | W3 |
| T4-39 | 9 | `data/encounters/campaign.json .encounters[id=campaign_pirate_weapons_01].choices[id=strip_parts].outcome.description` | W3 |
| T4-40 | 9 | `data/encounters/campaign.json .encounters[id=campaign_pirate_weapons_01].choices[id=mark_and_leave].description` | W3 |
| T4-41 | 9 | `data/encounters/campaign.json .encounters[id=campaign_guild_shadow_01].choices[id=defy].outcome.description` | W3 |
| T4-42 | 9 | `data/encounters/campaign.json .encounters[id=campaign_guild_shadow_01].choices[id=scan_shadow].outcome.description` | W3 |
| T4-43 | 9 | `data/encounters/campaign.json .encounters[id=campaign_final_warning_01].choices[id=double_down].outcome.description` | W3 |
| T4-44 | 9 | `data/encounters/campaign.json .encounters[id=campaign_final_warning_01].choices[id=set_trap].description` | W3 |
| T4-45 | 14 | `data/encounters/campaign.json .encounters[id=campaign_final_warning_01].choices[id=comply].description and choices[id=double_down].outcome.description` | closed, no action |
| T4-46 | 9 | `data/encounters/campaign.json .encounters[id=campaign_old_allies_01].choices[id=coordinate].outcome.description` | W3 |
| T4-47 | 9 | `data/encounters/campaign.json .encounters[id=campaign_old_allies_01].choices[id=hold_back].outcome.description` | W3 |
| T4-48 | 7 | `data/encounters/campaign.json .encounters[id=campaign_old_allies_01].choices[id=go_public].outcome.description and choices[id=coordinate].outcome.description` | SP10 |
| T4-49 | 9 | `data/encounters/campaign.json .encounters[id=campaign_larsen_warning_01].choices[id=trace_source].description` | W3 |
| T4-50 | 9 | `data/encounters/campaign.json .encounters[id=campaign_sato_returns_01].choices[id=warn_her].description` | W3 |
| T4-51 | 4 | `data/encounters/campaign.json .encounters[id=campaign_refugee_testimony_01].choices[id=provide_aid].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T4-52 | 13 | `data/encounters/ce4_variety.json bait_patrol_officer_01.decline, bait_civilian_lure_01.scan_first failure, bait_comm_relay_01.decode failure` | plan W2-A's records |
| T5-1 | 1 | `data/encounters/humor.json .encounters[id=humor_space_cat_01].choices[id=rescue].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T5-2 | 1 | `data/encounters/humor.json .encounters[id=humor_space_cat_01].choices[id=hail].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T5-3 | 1 | `data/encounters/humor.json .encounters[id=humor_wrong_number_01].choices[id=play_along].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T5-4 | 1 | `data/encounters/humor.json .encounters[id=humor_wrong_number_01].choices[id=disconnect].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T5-5 | 5 | `data/encounters/humor.json .encounters[id=humor_bureaucracy_01].choices[id=bribe].outcome.description` | aurelia's findings register (its finding is listed above) |
| T5-6 | 5 | `data/encounters/humor.json .encounters[id=humor_ghost_pirate_01].description (against choices[id=pay])` | W3 |
| T5-7 | 9 | `data/encounters/humor.json .encounters[id=humor_ghost_pirate_01].description and .choices[id=pay].outcome.description` | W3; Task 12 cut its W2 line (`data/encounters/humor.json .encounters[id=humor_ghost_pirate_01].choices[id=pay].outcome.description`) |
| T5-8 | 10 | `data/encounters/humor.json .encounters[id=humor_bureaucracy_01].description` | the later writing chunk that owns the file |
| T5-9 | 10 | `data/encounters/humor.json .encounters[id=humor_cooking_show_01].choices[id=tip].outcome.description` | the later writing chunk that owns the file |
| T5-10 | 9 | `data/encounters/humor.json .encounters[id=humor_retirement_01].choices[id=accept].outcome.description` | W3 |
| T5-11 | 4 | `data/encounters/humor.json .encounters[id=humor_retirement_01].choices[id=drink].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T5-12 | 5 | `data/encounters/humor.json .encounters[id=humor_ai_existential_01].choices[id=console].outcome.description` | aurelia's findings register (its finding is listed above) |
| T5-13 | 1 | `data/encounters/lore.json .encounters[id=lore_earth_broadcast_01].description` | Task 12 cuts it (a line W2 rewrote) |
| T5-14 | 10 | `data/encounters/lore.json .encounters[id=lore_charter_fragment_01].description` | the later writing chunk that owns the file |
| T5-15 | 9 | `data/encounters/lore.json .encounters[id=lore_charter_fragment_01].choices[id=recover].outcome.description` | W3 |
| T5-16 | 9 | `data/encounters/lore.json .encounters[id=lore_charter_fragment_01].choices[id=scan].outcome.description` | W3 |
| T5-17 | 9 | `data/encounters/lore.json .encounters[id=lore_first_miners_01].choices[id=pass].outcome.description and .choices[id=pass].description` | W3; Task 12 cut its W2 line (`data/encounters/lore.json .encounters[id=lore_first_miners_01].choices[id=pass].description`) |
| T5-18 | 9 | `data/encounters/lore.json .encounters[id=lore_pre_colony_probe_01].description and .encounters[id=lore_star_map_01].description` | W3 |
| T5-19 | 9 | `data/encounters/lore.json .encounters[id=lore_pre_colony_probe_01].choices[id=intercept].outcome.description` | W3 |
| T5-20 | 2 | `data/encounters/lore.json .encounters[id=lore_pre_colony_probe_01].choices[id=leave].description` | Task 12 cuts it (a line W2 rewrote) |
| T5-21 | 9 | `data/encounters/lore.json .encounters[id=lore_generation_ship_01].choices[id=scan].outcome.description` | W3 |
| T5-22 | 1 | `data/encounters/lore.json .encounters[id=lore_generation_ship_01].choices[id=leave].outcome.description and .encounters[id=lore_star_map_01].choices[id=analyze].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T5-23 | 1 | `data/encounters/lore.json .encounters[id=lore_star_map_01].choices[id=chart].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T5-24 | 1 | `data/encounters/lore.json .encounters[id=lore_star_map_01].choices[id=leave].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T5-25 | 9 | `data/encounters/lore.json .encounters[id=lore_forgotten_station_01].description, .choices[id=explore].outcome.description, .choices[id=scan].outcome.description` | W3 |
| T5-26 | 1 | `data/encounters/lore.json .encounters[id=lore_time_capsule_01].choices[id=open].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T5-27 | 9 | `data/encounters/lore.json .encounters[id=lore_aurelia_beacon_01].description and .encounters[id=lore_earth_song_01].choices[id=listen].outcome.description` | W3 |
| T5-28 | 5 | `data/encounters/humor.json and lore.json: ghost_pirate hack, retirement accept and drink, wrong_number play_along, aurelia_beacon share, charter recover, first_miners maintain, earth_song hail, forgotten_station explore, time_capsule open and deliver, star_map analyze, earth_broadcast record` | aurelia's findings register (its finding is listed above) |
| T5-29 | 8 | `data/encounters/humor.json humor_space_junk_art_01 and humor_space_cat_01; frontier_alliance.json alliance_wrecker_01; lore.json lore_first_miners_01` | the naming pass |
| T6-1 | 2 | `data/encounters/miners_union.json .encounters[id=union_derelict_drill_01].choices[id=leave_it].description` | Task 12 cuts it (a line W2 rewrote) |
| T6-2 | 1 | `data/encounters/frontier_alliance.json .encounters[id=alliance_festival_01].choices[id=join].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T6-3 | 1 | `data/encounters/science_collective.json .encounters[id=collective_nova_test_01].choices[id=ask_details].outcome.description` | Task 12 cuts it (a line W2 rewrote) |
| T6-4 | 2 | `data/encounters/frontier_alliance.json .encounters[id=alliance_wrecker_01].choices[id=side_brannick].description` | Task 12 cuts it (a line W2 rewrote) |
| T6-5 | 2 | `data/encounters/science_collective.json .encounters[id=collective_peer_review_01].choices[id=side_christensen].description` | Task 12 cuts it (a line W2 rewrote) |
| T6-6 | 2 | `data/encounters/commerce_guild.json .encounters[id=guild_escort_01].choices[id=negotiate_fee].description` | Task 12 cuts it (a line W2 rewrote) |
| T6-7 | 10 | `data/encounters/commerce_guild.json .encounters[id=guild_audit_01].choices[id=negotiate].outcome.description` | the later writing chunk that owns the file |
| T6-8 | 9 | `data/encounters/commerce_guild.json .encounters[id=guild_tariff_01].choices[id=fight].description` | W3 |
| T6-9 | 10 | `data/encounters/commerce_guild.json .encounters[id=guild_inspection_01]: .description; .choices[id=submit].outcome.description; .choices[id=bribe].outcome.description` | the later writing chunk that owns the file; Task 12 cut its W2 line (`data/encounters/commerce_guild.json .encounters[id=guild_inspection_01].choices[id=submit].outcome.description`) |
| T6-10 | 9 | `data/encounters/commerce_guild.json .encounters[id=guild_blackmail_01]: .description; .choices[id=sell_to_director].description and .outcome.description` | W3 |
| T6-11 | 10 | `data/encounters/commerce_guild.json .encounters[id=guild_escort_01]: .choices[id=escort].outcome.description; .choices[id=decline].outcome.description` | the later writing chunk that owns the file |
| T6-12 | 9 | `data/encounters/commerce_guild.json .encounters[id=guild_distress_luxury_01]: .choices[id=sell_rations].description; .choices[id=help_repair].outcome.description; .choices[id=pass_by].outcome.description` | W3 |
| T6-13 | 9 | `data/encounters/commerce_guild.json .encounters[id=guild_signal_encoded_01].choices[id=decode_further].outcome.description` | W3 |
| T6-14 | 5 | `data/encounters/commerce_guild.json .encounters[id=guild_contract_01].choices[id=counter].outcome.description` | aurelia's findings register (its finding is listed above) |
| T6-15 | 9 | `data/encounters/frontier_alliance.json outcomes of alliance_patrol_volunteer_01.refuse, alliance_barter_01.decline, alliance_storyteller_01.decline, alliance_smuggler_medicine_01.buy_some, alliance_salvage_claim_01.offer_help, alliance_community_01.decline` | W3; Task 12 cut its W2 line (`data/encounters/frontier_alliance.json .encounters[id=alliance_patrol_volunteer_01].choices[id=refuse].outcome.description`) |
| T6-16 | 9 | `data/encounters/frontier_alliance.json .encounters[id=alliance_salvage_claim_01].choices[id=contest].outcome.description` | W3 |
| T6-17 | 9 | `data/encounters/frontier_alliance.json .encounters[id=alliance_barter_01].choices[id=haggle]: .description and .outcome.description` | W3 |
| T6-18 | 3 | `frontier_alliance.json alliance_distress_crop_01.pass outcome; miners_union.json union_ore_spill_01.scoop_yourself, union_picket_01.honor_picket and union_picket_01.force_through outcomes` | Task 12 cut its two W2 lines (`alliance_distress_crop_01.pass`, `union_ore_spill_01.scoop_yourself`); `union_picket_01`'s honor_picket and force_through outcomes, untouched, go to W3 |
| T6-19 | 3 | `frontier_alliance.json outcomes of alliance_harvest_01.pass, alliance_community_01.small_help and decline, alliance_refugee_family_01.supplies, alliance_wrecker_01.split; miners_union.json union_scab_01.convince_union, union_ore_spill_01.help_recover` | W3 |
| T6-20 | 9 | `data/encounters/frontier_alliance.json .encounters[id=alliance_moonshine_01].choices[id=buy].outcome.description` | W3 |
| T6-21 | 9 | `data/encounters/frontier_alliance.json .encounters[id=alliance_festival_01].choices[id=trade_only].outcome.description` | W3 |
| T6-22 | 9 | `data/encounters/frontier_alliance.json .encounters[id=alliance_patrol_volunteer_01].choices[id=refuse].description` | W3 |
| T6-23 | 5 | `data/encounters/frontier_alliance.json .encounters[id=alliance_patrol_volunteer_01].choices[id=intel].description` | aurelia's findings register (its finding is listed above) |
| T6-24 | 5 | `frontier_alliance.json outcomes of alliance_moonshine_01.buy, alliance_smuggler_medicine_01.buy_some, alliance_festival_01.trade_only; miners_union.json union_mutual_aid_01.take_rations outcome` | aurelia's findings register (its finding is listed above) |
| T6-25 | 9 | `miners_union.json outcomes of union_lost_miner_01.rescue, union_equipment_swap_01.trade_parts, union_scab_01.help_hauler, union_derelict_drill_01.leave_it` | W3; Task 12 cut its W2 line (`data/encounters/miners_union.json .encounters[id=union_lost_miner_01].choices[id=rescue].outcome.description`) |
| T6-26 | 10 | `data/encounters/miners_union.json .encounters[id=union_safety_patrol_01]: .choices[id=bribe].outcome.description; .choices[id=refuse].description; .choices[id=comply].outcome.description` | the later writing chunk that owns the file; Task 12 cut its W2 line (`data/encounters/miners_union.json .encounters[id=union_safety_patrol_01].choices[id=bribe].outcome.description`) |
| T6-27 | 9 | `data/encounters/miners_union.json .encounters[id=union_derelict_drill_01].choices[id=salvage_drill].outcome.description` | W3 |
| T6-28 | 9 | `data/encounters/miners_union.json .encounters[id=union_ore_spill_01].choices[id=fly_around].description` | W3 |
| T6-29 | 5 | `data/encounters/miners_union.json .encounters[id=union_strike_fund_01].choices[id=donate_big].outcome.description` | aurelia's findings register (its finding is listed above) |
| T6-30 | 9 | `data/encounters/miners_union.json .encounters[id=union_folk_song_01].choices[id=listen_along].outcome.description` | W3 |
| T6-31 | 9 | `data/encounters/science_collective.json .encounters[id=collective_specimen_01]: .choices[id=collect_samples].outcome.description; .choices[id=sell_data].description; .choices[id=decline_specimen].description` | W3 |
| T6-32 | 9 | `data/encounters/science_collective.json .encounters[id=collective_quarantine_01].choices[id=push_through].outcome.description` | W3 |
| T6-33 | 9 | `data/encounters/science_collective.json .encounters[id=collective_ethics_01].choices[id=sell_nova]: .description and .outcome.description` | W3; Task 12 cut its W2 line (`data/encounters/science_collective.json .encounters[id=collective_ethics_01].choices[id=sell_nova].outcome.description`) |
| T6-34 | 9 | `data/encounters/science_collective.json .encounters[id=collective_grant_01].choices[id=negotiate_grant].outcome.description` | W3 |
| T6-35 | 9 | `data/encounters/science_collective.json .encounters[id=collective_nova_test_01].description` | W3 |
| T6-36 | 2 | `hints of frontier_alliance.json alliance_community_01.decline; miners_union.json union_folk_song_01.fly_on and union_strike_fund_01.decline; science_collective.json collective_data_buy_01.decline_data` | stands: a hint that repeats its label stands (theme 2's ruling) |
| T6-37 | 8 | `frontier_alliance.json alliance_community_01, alliance_refugee_family_01, alliance_wrecker_01; science_collective.json collective_artifact_01, collective_experiment_01; miners_union.json union_cave_in_01` | the naming pass |
| T6-38 | 14 | `spacegame/views/combat_view.py:1341` | closed, no action |
| T7-1 | 11 | `data/dialogue/dialogues.json .dialogues[id=arna_post_ore_tip].nodes[id=start].subtext` | the later writing chunk that owns the file |
| T7-2 | 4 | `data/dialogue/dialogues.json .dialogues[id=arna_betray_followthrough].nodes[id=security].subtext; .dialogues[id=arna_last_freight_out_closeout].nodes[id=brother].subtext` | the later writing chunk that owns the file |
| T7-3 | 11 | `data/dialogue/dialogues.json .dialogues[id=arna_betray_followthrough].nodes[id=reach].subtext` | the later writing chunk that owns the file |
| T7-4 | 11 | `data/dialogue/dialogues.json .dialogues[id=arna_betray_followthrough].nodes[id=ask].subtext` | the later writing chunk that owns the file |
| T7-5 | 4 | `data/dialogue/dialogues.json .dialogues[id=arna_last_freight_out_closeout].nodes[id=pendant].responses[0].text and .nodes[id=pendant_truth].text` | Task 12 cuts it (a line W2 rewrote) |
| T7-6 | 1 | `data/dialogue/dialogues.json .dialogues[id=arna_last_freight_out_closeout].nodes[id=start].subtext` | Task 12 cuts it (a line W2 rewrote) |
| T7-7 | 3 | `data/dialogue/dialogues.json .dialogues[id=arna_post_refining].nodes[id=whats_next].subtext` | the later writing chunk that owns the file |
| T7-8 | 8 | `data/dialogue/dialogues.json arna_first_encounter.start subtext; merchant_delivery.odom_arna_branch_a and .graduation_pointer text; dead_ledger_investigation.greet text; wulan_default.start subtext` | the later writing chunk that owns the file, once the author rules on the gesture (open) |
| T7-9 | 11 | `data/dialogue/dialogues.json embassy_summit nodes player_speaks, speech_fails, observation_moment, noticed_signal, missed_signal; oren_tak_meeting nodes trust_earned, farewell` | the later writing chunk that owns the file |
| T7-10 | 11 | `data/dialogue/dialogues.json .dialogues[id=oren_tak_meeting].nodes[id=farewell].text` | the later writing chunk that owns the file |
| T7-11 | 1 | `data/dialogue/dialogues.json .dialogues[id=cassiel_maren_forgery].nodes[id=start].text; .dialogues[id=priya_convergence_analysis].nodes[id=start].text` | Task 12 cut its W2 line (Priya's start text); `cassiel_maren_forgery`'s start text, untouched, goes to that tree's rewrite |
| T7-12 | 3 | `data/dialogue/dialogues.json marcus_recognition.start, neve_osei_price_of_info.start, arna_post_completion.catch (subtext and Observation reply)` | Task 12 cuts it (a line W2 rewrote) |
| T7-13 | 13 | `SpaceGame requirements/dialogue_writing_guide.md lines 342, 405 to 406, 460, 491 to 525` | plan W2-A's records |
| T7-14 | 11 | `data/dialogue/dialogues.json .dialogues[id=embassy_summit].nodes[id=observation_moment].responses[0] with missed_signal; .dialogues[id=tev_refining_intro].nodes[id=weigh_output].responses[0]` | the later writing chunk that owns the file; the unruled seams in `keren_meet` and `oren_tak_meeting` (listed above) join it |
| T7-15 | 14 | `SpaceGame tests/writing_gates/allowlist.json, the G11 'without looking up' row on .dialogues[id=the_collapse_sequence].nodes[id=priya_calibrates].text` | closed, no action |
| T7-16 | 11 | `data/dialogue/dialogues.json .dialogues[id=cassiel_maren_forgery].nodes[id=in_progress].responses[0].text` | the later writing chunk that owns the file |
| T7-17 | 14 | `SpaceGame requirements/nv_audit_findings.md rows 46 and 81` | closed, no action |
| T8-1 | 4 | `data/journal/entries.json .journal_entries[id=auto_p3_first_dispute_attended].text (and auto_p4_first_alliance_congress_attended)` | aurelia's findings register (its finding is listed above) |
| T8-2 | 4 | `data/journal/entries.json .journal_entries[id=auto_arna_branch_c].text` | Task 12 cuts it (a line W2 rewrote) |
| T8-3 | 4 | `data/journal/entries.json .journal_entries[id=auto_arna_brother_reveal].text` | aurelia's findings register (its finding is listed above) |
| T8-4 | 4 | `data/journal/entries.json .journal_entries[id=auto_sa_v_longer_ledger].text` | Task 12 cuts it (a line W2 rewrote) |
| T8-5 | 4 | `data/journal/entries.json .journal_entries[id=auto_auction_first_velo_encounter].text` | Task 12 cuts it (a line W2 rewrote) |
| T8-6 | 6 | `data/journal/travel_log_templates.json; spacegame/models/travel_log.py` | aurelia's findings register (its finding is listed above) |
| T8-7 | 6 | `data/journal/travel_log_templates.json .first_visit.nexus_prime` | aurelia's findings register (its finding is listed above) |
| T8-8 | 12 | `data/journal/travel_log_templates.json .first_visit.iron_depths, .first_visit.forgeworks, .major_trade[0], .major_trade[1]` | the later writing chunk that owns the file |
| T8-9 | 1 | `data/journal/travel_log_templates.json .first_visit.breakstone, .first_visit.crimson_reach, .first_visit.axiom_labs` | Task 12 cuts it (a line W2 rewrote) |
| T8-10 | 1 | `data/journal/entries.json .journal_entries[id=auto_m17_horizon].text` | Task 12 cuts it (a line W2 rewrote); SP10 may rewrite the entry again |
| T8-11 | 12 | `data/journal/entries.json auto_m06_priya, auto_m08_helped, auto_m10_crimson, auto_m12_attack, auto_m14_scan, auto_arna_branch_b, auto_arna_departure, auto_wreckers_first_contract, auto_okafor_first_disposed, auto_okafor_legacy_profit_ending, auto_auction_first_session, _rivalry, _listing_created, and the d1, d3 (three), d5, d7, d8 entries` | the later writing chunk that owns the file; inside it, the five campaign entries are SP10's text (F-66), the dilemma entries fire only on the archived Act II flags, and `auto_arna_branch_b` is in W3's queue |
| T9-1 | 14 | `data/combat/complications.json .complications[id=reinforcement_arrival].description` | closed, no action |
| T9-2 | 1 | `data/combat/complications.json .complications[id=reinforcement_arrival].narration` | Task 12 cuts it (a line W2 rewrote) |
| T9-3 | 1 | `data/missions/missions.json .missions[id=the_drifters_deal].description` | Task 12 cuts it (a line W2 rewrote) |
| T9-4 | 3 | `crew_quests.json elena_old_charts and tomas_new_ledger; missions.json recruit_scientist and the_scholars_errand; side_missions.json old_debts (each .description)` | Task 12 cuts it (a line W2 rewrote) |
| T9-5 | 1 | `data/missions/side_missions.json .missions[id=the_informant].description` | Task 12 cuts it (a line W2 rewrote) |
| T9-6 | 3 | `data/ground/campaign/ mission_13 interactables[1], story_triggers[4]; mission_14 story_triggers[0], [2], [4]; mission_16_pirate_base interactables[0], [3], story_triggers[1]; mission_16_the_fulcrum story_triggers[2], [3], [4]` | Task 12 cuts it (a line W2 rewrote) |
| T9-7 | 7 | `data/missions/side_missions.json .missions[id=two_calls].description` | SP10 |
| T9-8 | 8 | `side_missions.json the_forgery and Maren Holt's mission; generic.json hauler captain Maren; npcs.json, dialogues.json, station_chatter.json` | the naming pass |
| T10-1 | 6 | `data/economy/news_templates.json ge_* and me_* templates; spacegame/engine/game.py lines 5874 to 5918` | aurelia's findings register (its finding is listed above) |
| T10-2 | 6 | `data/economy/news_templates.json pe_03, pe_04, pm_03` | aurelia's findings register (its finding is listed above) |
| T10-3 | 13 | `data/economy/news_templates.json ge_festival_04, flavor_42, pm_02, ge_embargo_03, ge_festival_05, pe_04` | plan W2-A's records (ruled the world's press: its wry tags stand) |
| T10-4 | 1 | `data/economy/news_templates.json .news_templates[id=flavor_15].template` | Task 12 cuts it (a line W2 rewrote) |
| T10-5 | 13 | `SpaceGame requirements/overhaul/42_ui_chrome_components.md:114 (also requirements/archive/journal_system.md:155, requirements/archive/shipyard_overhaul.md:507)` | plan W2-A's records |
| T11-1 | 14 | `SpaceGame tests/writing_gates/allowlist.py REASONS` | closed, no action |
| T11-2 | 14 | `SpaceGame parity/port_notes.md, this section's W3-queue bullet` | closed, no action |
| T11-3 | 12 | `data/journal/entries.json auto_iron_betrayal and auto_m13_oren; data/missions/missions.json iron_delivery.discovery_text` | W3 |
| T11-4 | 14 | `SpaceGame parity/port_notes.md, this section's 'What W2 fixed' bullet` | closed, no action |

## Writing W4 (2026-10-11)

Writing plan W4-S landed the SpaceGame half of the crew quests' wiring slice (writing-discipline
spec 9.2 row 7; polish design 3.1 and 3.6): the crew-scene mechanism, the twelve crew quests
re-gated on an ask with a minimal opener each, F-34's seven checks repaired, F-45 fixed (this
register's F-015, now F-C11), the take-both walk fixed, `elena_archives_npc` deleted, the three
strangers gated, and content rules 1 to 12 held by `tests/test_data/test_crew_scene_content.py`
(spec 5.1's G12).

### Records for plan W4-A

- What the sync brings: `data/missions/crew_quests.json` (each quest's gate `["<quest>_agreed"]`
  after its stage's predecessor, and a `scenes` list of three: `<quest>_opener`,
  `<quest>_raise`, `<quest>_resolution`; `elena_old_charts`'s hint),
  `data/dialogue/crew_quest_dialogues.json` (eight new trees `<quest>_ask_dialogue`; the four
  stage 1 trees gain an ask, a decline, a deferral and the nodes `declined` and `ask_again`;
  F-34's seven check replies; the take-both replies set `elena_wreck_found`;
  `tomas_fulcrum_dialogue`'s `con_result` node deleted; `marcus_confrontation_dialogue`'s start
  line says "get there" for "get back to Breakstone", since `marcus_steel_holds_resolution`
  plays it at Breakstone) and `data/characters/npcs.json` (`elena_archives_npc` deleted;
  `lira_feng`, `amara_okonkwo` and `ren_castillo` listed only after their stage's resolution and
  hidden after it until their slice gives them an after-tree, so W4 reaches each only through
  its resolution scene). None of `lira_feng`, `amara_okonkwo` or `ren_castillo` is listed at any
  point in W4 (each one's prerequisite and hide flag are the same resolution flag), so plan
  W4-A's arc-test assertion `contains(["lira_feng"])` at Forgeworks (its plan :1673) and its
  strangers record (its plan :1744) flip to match. (plan W4-S Task 4 and its preflight
  ruling 13)
- Goldens whose content changes: twelve of the sixteen crew trees' `dialogue/tree_*` goldens,
  all but `marcus_evidence_dialogue`, `marcus_inspector_dialogue`, `priya_paper_dialogue` and
  `tomas_lead_dialogue` (F-45's `crew_loyalty_*_70` and `_85` flags in every step whose gain
  crosses a mark from the driver's 60; the stage 1 trees' new replies and nodes; F-34's checks,
  which now pass and fail on registered skills; rule 8's moved flags and loyalty;
  `elena_wreck_dialogue`'s four take-both steps now set `elena_wreck_found`;
  `tomas_fulcrum_dialogue`'s two `con_result` steps (novice and expert) gone with the node;
  `elena_archives_dialogue`'s `npc_id` null now that its NPC is gone), `dialogue/npcs_here` and
  `missions/availability`; no `missions/lifecycle_*` golden changes, since the lifecycle driver
  forces 'available' and never reads the gate. The new goldens are the eight
  `dialogue/tree_<quest>_ask_dialogue` and `crew/scenes_due`. (plan W4-S Task 5)
- What to port: `CrewScene` read beside the missions in `MissionContent` (so `Mission`, the save
  and the mission goldens never see scenes), with the record's fields and defaults as
  `spacegame/models/crew_scene.py` gives them; the gate's six rules in order (the `scenes_due`
  golden pins only rule 1 first and rule 2 before rule 5: it cannot order rules 3 and 4 before
  rule 5, or rules 2 to 5 before rule 6, and with no placed opener or middle in W4 it never sets
  the place against the pace; Python pins the rest in `tests/test_models/test_crew_scenes.py`'s
  five checked-before tests (:266-285), which `crew_scene_test.gd` should mirror) with their
  four refusals verbatim ("<Name> is not aboard.", "<Name> has nothing to say about that now.",
  "<Name> wants to talk about that at <System>.", "<Name> will bring it up at the next port."),
  the name the crew template's and the system's; the talk rows (each companion's first due
  crew-initiative scene in roster order, then every due captain topic); a place scene's hook
  announced after the crew's arrival lines as `<Name>: "<hook>"`; a scene opened at its entry
  node with its `with_npc_id` (disposition, then `talked_to_<npc>` at the close), the port's ""
  for no entry node opening at the start node (D-2: Python refuses "" as an unknown node and
  tests `is not None`, and no caller passes it, so no result differs); the companion joins the
  landing's spoken set at the close; F-45 in `DialogueManager._crew_loyalty`; the `scenes_due`
  replay; and content rules 1 to 12 in `crew_content_test.gd` with the same allowlist as
  `tests/test_data/test_crew_scene_content.py`'s `ALLOWED`, plus G12's money cap (rule 12's
  `('12', 'money')` offence: the sum, over the crew quests, of each quest's largest
  `outcome_rewards` entry in credits is at most `MONEY_CAP`, 5,900; plan W4-S's preflight
  ruling 14), which plan W4-A's rule 12 lacks and `crew_content_test.gd` mirrors; the stage 1
  openers' follow-up ask nodes also offer the decline, pinned in Python by
  `test_every_ask_of_an_opener_can_be_declined`, which `crew_content_test.gd` may mirror.
  (polish design 3.1, 8.1, 8.2 step 7.4)
- A difference with no deviation: SpaceGame keeps the spoken set on `Game`, cleared when a
  landing begins and on a new game or a load, and does not save it; the port saves
  `Visit.crew_spoke`. They differ only for a save and load in the middle of a landing. (plan
  W4-S's spoken set ruling)
- Pins the sync moves in the port: `dialogue_parity_test.gd`'s case count (161 plus the eight
  new trees), `dialogue_content_test.gd`'s NPC count (one fewer), tree count and totals,
  `crew_parity_test.gd`'s count (4 to 5), `load_gate_test.gd`'s trade that crossed 50 and
  accepted `elena_old_charts` (the quest now waits for its ask), and
  `dialogue_manager_test.gd`'s unknown-skill pin on `tomas_fulcrum_dialogue` (con_plan is
  Deception now; the pin moves to a synthetic tree). (plan W4-S Tasks 2 and 4)
- The writing pass's queue: `priya_peer_review_dialogue` start's Communication reply is F-34's
  fourth check, rewritten here as "[Persuasion 3] Ask Dr. Rautio-Mensah to tell the board what
  happened in the lab."; W3 leaves it. (plan W4-S Task 4)
- Left, each with its owner: each arc's own openers and middles, the strangers' after-trees,
  the rescaled loyalty amounts, `outcome_rewards` and the money routes, Tomas's story opening,
  and the stage 3 places (W5 to W8); the port's gates on the relationship model's tiers,
  chapters and `crew_acts` (W9). (plan W4-S rulings)
- The author's read: the twelve minimal openers and the twenty-four hooks are working text the
  author reads with the plan (polish design 3.6); the author approved writing and running W4
  overnight on 2026-10-11, the plan's review to follow. (plan W4-S rulings)
- The register: this register's F-015 closes as F-C11. aurelia's F-34 and F-45 close, and its
  new rows for BB-16 (closed at landing) and the Legend latch (a threshold flag never fires
  when Legend is learned while loyalty sits in the ten points under a mark; owner the
  relationship model, W9) take the next free ids in plan W4-A. (polish design 3.6 Records)

## Writing W3a (2026-10-13)

Plan W3a-S (aurelia `docs/plans/2026-10-12-writing-w3a-spacegame.md`) landed the SpaceGame half
of the writing-discipline spec's 9.2 rows 5 and 6: Odom's iron job truthful in every state, with
its states, sensors, clock, close and closers (polish design 2.2 and 2.6 to 2.9; spec 9.3's
choices 1, 3, 4 and 5), Joaquim Kimura's and Elena's iron scenes, and the return scenes of polish
choice 11 (polish design 6) with the Grand Bazaar's receipt. The author read every new line on
2026-10-13 and accepted the defaults; Task 9 applied the rulings and regenerated the goldens once.

### Records for plan W3a-A

- What the sync brings: six data files. `data/dialogue/dialogues.json` (Odom's `merchant_delivery`
  in every state, the clerk's `forgeworks_intake`, Elena's three iron replies and the walk-away's
  flag in `elena_cantina`, the four return trees `elena_return`, `dex_return`, `oren_return` and
  `tomas_return`, and the tier 2 echoes in `dex_cantina`, `torres_underground`,
  `oren_tak_meeting`, `tomas_havens` and `sienna_vek_warning`); `data/characters/npcs.json` (the
  four kept NPCs' return states; `forgeworks_clerk` is Joaquim Kimura, "Intake Clerk, Main
  Foundry", and loses its `hide_after_flag`); `data/missions/missions.json` (`iron_delivery`'s
  one-unit collect leg "Keep Odom's ore aboard", its hand-over flag `iron_ore_handed_over`,
  `iron_delivery_resolved` among its rewards, its hint, discovery note and timeliness lines;
  `whispers_at_the_bar`'s objective "Agree to carry Glyn's chip"; `drifters_delivery`'s
  description and `receipt`); `data/missions/sa_v_investment_intro.json` (The Longer Ledger after
  `bill_of_landing` on `odom_ledger_open`, its description and discovery note);
  `data/journal/entries.json` (`auto_m02_delivery` on `iron_ore_delivered` for `iron_delivery`,
  `auto_m13_oren` on `oren_intel_received`, `auto_iron_betrayal`, and seven new entries:
  `auto_iron_short`, `auto_iron_made_good`, `auto_iron_written_off`, `auto_iron_handed_back`,
  `auto_iron_covered`, `auto_elena_walked_away`, `auto_dex_declined`); and
  `data/crew/ambient_dialogue.json` (two crew lines: Elena's walk-away, Tomas's turned-down
  bales). (plan W3a-S Tasks 3 to 6 and 9)
- Goldens whose content changes, from the regeneration's diff: the dialogue goldens of the eight
  trees Tasks 3 to 6 changed (`dialogue/tree_merchant_delivery`, `tree_forgeworks_intake`,
  `tree_elena_cantina`, `tree_dex_cantina`, `tree_torres_underground`, `tree_oren_tak_meeting`,
  `tree_tomas_havens`, `tree_sienna_vek_warning`); four new goldens, `dialogue/tree_elena_return`,
  `tree_dex_return`, `tree_oren_return` and `tree_tomas_return`; `dialogue/npcs_here` (a new
  `tomas_thinking` step, the Forgeworks steps relabelled `intake_offered` and `intake_awaited`
  at the author's read, `intake_awaited` holding `iron_job_full`, and a new `odom_short_load`
  step that lists Odom for `iron_delivery`); `missions/lifecycle_iron_delivery` and the three
  soft-deadline cases `missions/soft_deadline_5`, `_16` and `_25`, which now pin 60, 45 and 30
  credits with "(1 of 10 delivered)", since the collect objective is one unit and the drivers
  meet it with one unit aboard (each now sets `iron_ore_handed_over` where it recorded the talk
  with the clerk, `talked_to_forgeworks_clerk`, and adds "Progress: iron_delivery_resolved");
  and
  `missions/availability`, whose every-gate flag set loses `iron_ore_delivered` and gains
  `odom_ledger_open` with The Longer Ledger's new gate. The dialogue goldens record each tree's
  structure (availability, next nodes, flags, dispositions), never its text, so the author's
  rewordings move none of them; the read's structural changes show in
  `tree_merchant_delivery` (the drifted reply's gate, `iron_delivery_late_tier`),
  `tree_dex_cantina` (the watched reply's gate; the first visit's yes pays +3) and `npcs_here`.
  The Longer Ledger's `missions/lifecycle_sa_v_investment_intro` does not change: the lifecycle
  driver forces the mission available, so its new gate and discovery note never reach it. The
  ambient case and `whispers_at_the_bar` do not move. The port's dialogue case count rises by
  four (the return trees). (plan W3a-S Task 9)
- The port's iron work (polish design 2.8, 2.2): `IronConsignment` gains the state table
  (`state_of`, `refresh_state`, run from `DialogueActions._opening_flags` after the tree is
  picked, after `at_exit` in `_close`, and after the clock), `note_defeat` (in `FightEnd`'s
  defeat branch after `apply_defeat` and guard (a), from the job's owned lot before and after),
  the close's take-back of up to ten ore through the reward path (replacing B2's
  `lots.release`), the no-fault close (`iron_delivery_closed`, "Job Closed: Iron Ore Delivery"),
  the decline's exit (`iron_delivery_resolved` with no job open moves the campaign on), the
  clock's filing (the moved state from the late tier: fail, take back, Commerce Guild -10
  applied directly under D-13, the register's notices) and `closers(flags)` in
  `NpcAvailability.needed_by`. The clock also sets `iron_delivery_late_tier` at the first
  landing or rest on or after the open job's own late-tier day (its accept day + 19), only
  while the job is open and never on the filing's tick, because the synced "Is it still six
  hundred?" reply in `merchant_delivery`'s `waiting` and `waiting_count` now requires it in
  place of `iron_delivery_moved_on`, so a captain who took the job late hears it on their own
  clock; when both fall due on one tick the notice's flags read `iron_delivery_late_tier`, then
  `iron_delivery_moved_on` (the author's read, Q4). The notices verbatim, each its own banner,
  in Task 1's constants as the read left them: `FAILED_LINE` "Mission Failed: Iron Ore
  Delivery"; `CLOSED_LINE` "Job Closed: Iron Ore Delivery"; `TAKEN_BACK_LINE` "Odom's crew took
  back {units} Iron Ore" (left out when nothing is taken); `FILING_LINE` "Nexus Prime cargo
  office, Odom's register: consigned iron ore, sold on a Guild trading floor under your
  permit." (its "ten units" and its last sentence gone at the read, Q3); the new
  `VIOLATION_LINE` "Freight violation filed.", posted after it; and `HIDE_REFUSED` "Consigned ore
  stays in the main hold.". A filing posts failed, taken back, filing, violation in that order;
  a betrayal at the exit posts failed and taken back, a no-fault close closed and taken back.
  The port has no hidden compartment, so the hide rule and `HIDE_REFUSED` are Python's alone.
  (plan W3a-S Tasks 1, 2 and 9)
- The receipt: the port reads a mission record's `receipt` beside the missions (as plan W4-A
  reads crew scenes) and `MissionFlow._complete` posts it after "Mission Complete";
  `Mission.to_dict` never writes it in Python, so no mission golden carries it. Drifter's
  Delivery's receipt reads, at the read (Q39), "Grand Bazaar, textile desk: Tomas Drifter's
  bales cleared under your license. Shares wired to Haven's Rest and to you." (118 characters).
  (plan W3a-S Task 6, polish design 6)
- Content rule 9 (a return tree pays once) is tested in SpaceGame now
  (`tests/test_data/test_one_shot_scenes.py`, `test_a_return_pays_once`), and aurelia's
  `test/unit/one_shot_content_test.gd` (its line 13 says rule 9 waits for the return trees)
  should mirror it, since polish design 6.1 mirrors every rule in the port: read an exit as a
  missing node, a node without replies or a reply without a next node; count a check's reply
  flag and its branch flag (`set_flag_on_success` or `set_flag_on_failure`); and stop a path at
  a node already on it. Plan W3a-A's row for that file adds no rule 9 yet. (plan W3a-S Task 7
  and its ledger's ruling on the reviewer's flag b)
- The port's tests the sync moves: `test/parity/dialogue_parity_test.gd` (`DIALOGUE_CASES` gains
  the four return trees); `test/unit/dialogue_content_test.gd` (the tree count, +4, and the
  totals, each read from the synced data; the NPC count holds); `test/unit/dialogue_manager_test.gd`
  (the F-33 pins of `merchant_delivery`'s unselectable greet replies, now 4, 5, 13, 14, 15 and
  18, and SpaceGame's `UNSELECTED_RESPONSES` also names `dex_cantina`'s start reply 2, the
  watched reply, which the expert profile's `helped_reva_sato` excludes and the novice's empty
  flags never open since the read gated it on `ignored_distress_signal` (Q27): with that flag
  alone it is visible reply 1 and moves to `why_me_watched`);
  `test/unit/mission_content_test.gd` (`iron_delivery`'s objectives, its six rewards and its
  timeliness lines; the receipt's text if a case pins it);
  `test/unit/mission_manager_test.gd` (the collect fall-back case takes the ore from ten to none,
  the objective being one unit); `test/unit/npc_availability_test.gd` (the clerk's `needed_by`
  holds only with an open state set); `test/unit/dialogue_actions_test.gd` (Odom's opening, what
  the new greet offers; the exit's take-back in place of the release; the accept moved from
  `offer` to `details`); `test/unit/one_shot_content_test.gd` (four kept NPCs, Elena, Glyn, Oren
  and Tomas; none awaiting a return; Tomas's deferral exit resolving nothing; Elena's settable
  pins gain `elena_walked_away`); `test/unit/story_content_test.gd` (`CHECK_GATE_ALLOWLIST`
  emptied; its suite is at 499 lines, so no line may be added);
  `test/unit/ambient_chatter_test.gd` (the ambient line count gains the two crew lines); and
  `test/playthrough/one_shot_scenes_test.gd` (the second talks open the return trees, Elena's
  `elena_return` and Glyn's `dex_return`; a first talk with Glyn by a captain who never met Reva
  Sato's distress call, both of its flags unset, now offers only "Who are you?" at his start, so
  a case that picked "Why are you talking to me?" there moves too). (plan W3a-A's sync table;
  the author's read)
- Python only, for the port's records beside deviation D-22: a sale of a top-up after a loss
  reads as a sale of Odom's ore in Python (counts) and as the captain's own in the port (lots).
  The hand-over (`deliver_cargo`, through `_delivery_share` and `apply_rewards`) and the
  take-back read both holds, the main hold first (the author's read, Q2), so a captain's own
  ore hidden beside Odom's counts on the scale, as it does in the job's state; the port has no
  hidden compartment, so nothing follows there. Kimura's advice ("Ten on the scale, Odom's stamp
  on every unit.") holds in the port only because its hand-over takes the mission's own lot
  first, which plan W3a-A states only for the take-back: W3a-A should cite
  `test/unit/cargo_lots_test.gd`'s line 40 and add one reward-path test with the captain's own
  ore aboard. Saving is refused while a conversation is open (the pause menu greys Save out,
  `PauseMenuView(save_allowed=...)`; the author's read, Q40): a Python UI rule, which the port's
  save screen needs its own form of (SP6). (plan W3a-S Task 9)
- Records in aurelia: F-75 (the iron scenes) and F-76 (the return scenes and BB-69's
  fail-forward) close; F-66's `auto_m02_delivery` and `auto_m13_oren` items are fixed; F-86 stays
  open for plan W3b (rows 10 and 11). The weigher's rename stands (the author's read, Q1:
  Joaquim Kimura, "Intake Clerk, Main Foundry") and reaches the economy design's notes on Wren
  (its 5.9 row "Wren | the Syndicate scale, Forgeworks" and the "Wren keeps the scale" note
  under it, with Wren again in 5.10, 14.7 and Appendix A, and in
  `docs/design/economy-loops/standing-people.md`) and `docs/handoffs.md`'s Wren line ("Wren keeps
  the scale while the writing spec's rename waits on the author"); spec 9.3's last bullet is
  settled by the same word. (plan W3a-S rulings)
- The author's read: 2026-10-13. The author read the reading desk (82 nodes, the 22 planning
  rulings, 42 questions with defaults and 18 flags) and replied "Reading desk reviewed, looks
  good.", accepting every recommended default and every planning ruling. The rulings file lives
  outside the repo and is never committed, so the list below is the record, one sub-bullet per
  question with the controller's picks and adjustments marked; Task 9 applied them.
  - Q1. no change: `data/characters/npcs.json`'s `forgeworks_clerk` stays Joaquim Kimura, "Intake
    Clerk, Main Foundry"; planning ruling 3 stands.
  - Q2. (controller's pick, accepted: it keeps planning ruling H, held_units over both holds, and
    changes two removals; the other fix would reverse ruling H across four readers.) Python only:
    `MissionManager._delivery_share` counts `held_units` over both holds less the reserved units
    (docstring says so; no golden moves); `apply_rewards`' `deliver_cargo` branch removes from the
    main hold first, then the rest from `hidden_compartment`; `iron_consignment.take_back` does the
    same (both docstrings follow); the REVIEWED reasons for `take_back` and `apply_rewards` in
    `tests/test_compliance/test_cargo_removal_registry.py` now say "from both holds, the main hold
    first"; two new tests, `test_a_hand_over_takes_the_hidden_compartment_too` and
    `test_the_close_takes_back_from_both_holds`.
  - Q3. Python: `iron_consignment.FILING_LINE` drops "ten units," (111 characters) and a new
    `VIOLATION_LINE`, "Freight violation filed." (24), posts after it as its own banner (`on_clock`
    returns both, so the landing and rest paths post six notice constants in all); the expected
    tuples in `test_iron_consignment.py` and `test_trading_actions.py` follow, and
    `test_the_filing_fits_the_banner` is new.
  - Q4. (controller's pick, accepted: a clock flag set only while the job is open keeps
    `waiting_drifted`'s figure-free text true for every captain who can reach it, one who took the
    job after day 20 included; a rewrite for a late taker would take the late-tier captain's real
    answer away.) New `iron_delivery_late_tier()` in `spacegame/constants/flags.py` (the moved-on
    docstring loses the drifted reply as consumer); `iron_consignment` adds it to `ENGINE_FLAGS`,
    adds `late_tier_due`, and `on_clock` writes it before `iron_delivery_moved_on` while the job is
    open; the "Is it still six hundred?" reply in `merchant_delivery`'s `waiting` and
    `waiting_count` now requires `iron_delivery_late_tier` instead of `iron_delivery_moved_on`;
    tests: the clock tests in `test_iron_consignment.py` (new
    `test_a_late_take_reaches_its_own_late_tier`), the reply gate in
    `test_iron_delivery_outcomes.py`, and the helper's name in `test_flags.py`.
  - Q5. `merchant_delivery` / `waiting_count`: "Your bay reads ten." gains "or better".
  - Q6. no change, held for the T7-8 gesture ruling: `merchant_delivery`'s `waiting_drifted`,
    `loss_closed`, `odom_arna_branch_a` and `graduation_pointer`.
  - Q7. (controller's pick, accepted: wait for SP10's hooks; the default already writes no Log line
    now, and waiting is the smallest change.) (adjusted: the note's last clause would be stale after
    the read.) No data change; `odom_caught_lie` stays in the orphan list in
    `tests/test_data/test_dialogue_integrity.py`, and its comment's last clause, "the author's Task
    8 read rules on one", becomes "the author's read (2026-10-13) leaves it to SP10".
  - Q8. `merchant_delivery` / `ongoing_greet` cuts "The Forgeworks run closed on my books. That
    counts." and folds "He taps the stack of manifests in front of him." into the first narration;
    `data/missions/sa_v_investment_intro.json`'s `discovery_text` cuts "after the iron ore job"
    (both named in the records above).
  - Q9. no change: `merchant_delivery` greet reply 18 ("Anything else you'd put in the ledger for
    me?", into `second_look`) keeps its `excluded_flags`; (adjusted: Task 8's copy was already read,
    so the note goes to the records) the SP10 note is in "What W3a leaves".
  - Q10. no change to any line; (adjusted: Task 8's copy went to the author without Odom's lines
    printed against his voice sheet) the voice-sheet check of every new or changed Odom line
    (`requirements/character_voices.md`, lines 454 to 511) moves to the final review.
  - Q11. `data/journal/entries.json`, `auto_m02_delivery`: cuts "First completed contract."
  - Q12. `auto_iron_covered`: "paid the iron run in full" becomes "paid the iron run on the count".
  - Q13. (controller's pick, accepted: the purchase premise does not stand, since combat loot,
    mining and salvage also reach the made-good state, so the three lines are ruled together and
    name the making-up, not a purchase.) `auto_iron_made_good` now reads "Made up Odom's count after
    a fight took ore from his load." and "wrote the difference" for the floor's charge;
    `merchant_delivery`'s `thanks_made_good` says "not all ten carry my stamp" and "You made up the
    difference"; `made_good_book` says "the difference, to the credit" for "what the floor charged
    you".
  - Q14. `auto_iron_betrayal`: cuts "What did not come back to his lot is in his book."
  - Q15. `forgeworks_intake` / `nothing_to_weigh`: "Nothing on the scale, nothing to sign." becomes
    "Nothing on the scale means nothing to sign."
  - Q16. `forgeworks_intake`: `accept_made_good` says "The incident report" for "The lane report"
    and the lot reader "takes a while over the stamps" for "beeps twice: Odom's stamp, and floor
    stock beside it"; `accept_floor_stock`'s reader "takes a while over the stamps" for "takes
    longer, and comes back with two stamps"; (adjusted: the recommended "the floor's stamp is on the
    count" is false for a captain who made up the count with looted, mined or salvaged ore) Odom's
    line is applied in Q13 as "not all ten carry my stamp".
  - Q17. `forgeworks_intake` / `no_sign`: cuts "It comes up empty." and "nothing on file says where
    the rest went" becomes "the file doesn't cover the gap".
  - Q18. (a) (adjusted: "The incident report is on his datapad" becomes "comes up beside it", since
    Q19 already puts the reading on his datapad) `forgeworks_intake` / `weigh_short`: "runs the load
    onto the scale" becomes "pulls the intake scale's reading onto his datapad", "The lane's
    incident report is on his datapad" becomes "The incident report comes up beside it", and "off
    that lane this month" loses "off that lane"; (b) `accept_made_good`, applied in Q16a; (c)
    `elena_cantina` / `trading_tips` reply R1 (needs `broker_ore_lost`): "I lost part of Odom's load
    on the Forgeworks lane." becomes "I lost Odom's ore in a fight."; (d) `merchant_delivery` /
    `loss_short`: "The lane incident report" becomes "The incident report" and "Forgeworks lane." is
    cut.
  - Q19. (controller's pick, accepted: the scenes read the intake scale off his datapad; it is the
    smaller change and matches crucible's "pulls the left bank's readout onto his datapad", where
    meeting him off shift would leave "runs the load onto the scale" false.) The one line it changes
    is applied in Q18a; `iron_delivery`'s objective and hint stay as they are.
  - Q20. no change, held for the T7-8 gesture ruling: `data/missions/missions.json`,
    `iron_delivery`'s `timeliness_comments.late`.
  - Q21. `elena_cantina` / `trading_tips` reply R0: "Odom paid six hundred" becomes "Odom offered
    six hundred"; `iron_carriage` stays.
  - Q22. no change, held for the T7-8 gesture ruling: `elena_return` / `start`, "She speaks before
    she looks up."; (adjusted: Task 8's copy is read, so the held list lives in these records,
    beside `waiting_drifted` and `loss_closed`).
  - Q23. (a) `elena_return` / `projections` opens "A freight projection is open on her slate now,
    for a ship registered to someone else." and cuts "and the owner wants them..."; (b)
    `elena_cantina` / `iron_lane` cuts "If we ran it, we would want... *She stops.*".
  - Q24. applied in Q23a (`elena_return` / `projections`).
  - Q25. (controller's pick, accepted: single quotes keep the line reading as the captain's quoted
    words; with no marks it reads as Elena's own order.) `data/crew/ambient_dialogue.json`, the
    `elena_reeves` line requiring `elena_walked_away`: the double quotes round "Mind your own
    business." become single quotes; `TestElena.test_the_walk_away_has_a_log_entry_and_a_crew_line`
    in `tests/test_data/test_return_scenes.py` follows.
  - Q26. no change: `elena_reeves`' `dialogue_states` keep their order, since `after_walkaway`
    cannot reach a D5 captain while `ACT_TWO_V1_ENABLED` is False.
  - Q27. `dex_cantina` / `start`, reply R2 ("Why are you talking to me?", into `why_me_watched`):
    gains `required_flags` [`ignored_distress_signal`] and keeps `excluded_flags`
    [`helped_reva_sato`]; `TestGlyn.test_why_me_follows_reva_sato` loops the three cases.
  - Q28. (a) `dex_cantina` / `why_me_watched` opens "What's that worth to you? ... Call it a sample.
    You didn't stop for Reva Sato." for "Because you didn't stop for Reva Sato."; (b) (controller's
    pick, accepted: the canon `why_me` deflects first the same way, since the voice sheet's rule
    binds both, and the parallel wording is the smallest change) `why_me` opens "What's that worth
    to you? Call it a sample. You helped Reva Sato," for "Because you helped Reva Sato,".
  - Q29. no change, held for the T7-8 gesture ruling: `dex_return` / `start`, "He doesn't turn
    around.", listed among the held lines in these records, which say the plan added the sentence
    (the design names only the stool).
  - Q30. (a) `dex_cantina` / `accept_path` reply R0 ("I'll do it.") gains `disposition_change` 3;
    (b) `dex_return` / `terms`: "You'd still have a favor" becomes "You'd have a favor" and "A
    smaller one." becomes "Smaller than a yes on the spot would have bought."; (c) (controller's
    pick, accepted: "The price moves every day you wait" claims a cost nothing applies, and the new
    line is in Glyn's information-economy voice and claims nothing about cost or time) `still_no`:
    "The price moves every day you wait. That's the market, not me." becomes "A no is information
    too, friend, and I never throw information away."; (d) new
    `TestGlyn.test_the_first_yes_pays_three_too`.
  - Q31. `oren_tak_meeting` / `refuse`: cuts "Not yet."
  - Q32. `oren_return`: (a) `start` reply R0 "Same as before." becomes "I should have led with
    that."; (b) `glyn_again`: "That name bought you thirty seconds last time." becomes "That name
    buys thirty seconds." and "It buys less now." becomes "Fewer on a second visit."
  - Q33. `oren_return` / `found`: cuts ", procurement format".
  - Q34. (a) `oren_return` / `found_not`: "Then, lower, as you stand:" becomes "Then, lower:"; (b)
    `tomas_return` / `terms`: "before you sit down" becomes "as you reach the table".
  - Q35. `data/journal/entries.json`, `auto_m13_oren`: cuts "Union pension".
  - Q36. (controller's pick, accepted: at Task 9, not W3b, since unmarked narration under Sienna's
    speaker tag is a broken stage direction in a tree this plan changed, and the fix is two pairs of
    asterisks.) `sienna_vek_warning` / `start` and `share_data`: the opening narration is wrapped in
    asterisks (to "before speaking." and to "smaller than a thumbnail.").
  - Q37. no change: `sienna_vek_warning` / `scale` reply R2 is true wherever it shows, since it
    needs `oren_full_account`.
  - Q38. `data/missions/missions.json`, `drifters_delivery.description`: "bolts" becomes "bales",
    and "Tomas can't sell there himself. He's got the wrong paperwork, the wrong reputation, and the
    wrong answers for customs." becomes "Under Tomas's name the Guild tariff eats nearly the whole
    sale."; "bill of landing" stays, the game's in-world document name in at least eight strings.
  - Q39. `drifters_delivery.receipt`: the two share sentences become "Shares wired to Haven's Rest
    and to you." (118 characters, from 150).
  - Q40. Python UI rule: `PauseMenuView(ui_manager, save_allowed=True)` greys Save out and ignores
    its press when False, and `Game._open_pause_menu` passes `save_allowed=False` in
    `GameState.DIALOGUE`; the new tests are `tests/test_views/test_pause_menu_view.py` (two) and
    `tests/test_engine/test_pause_save_gate.py`; the port's save screen needs its own rule.
  - Q41. no change: `npc_availability.needed_by` keeps asking `IronConsignment.closers`, which its
    test pins.
  - Q42. `TALK_STEPS` in `tools/parity/drivers/dialogue.py`: `wren_offered` and `wren_awaited`
    become `intake_offered` and `intake_awaited`, and `tests/test_parity/test_dialogue_driver.py`
    follows; `parity/golden/dialogue/npcs_here.json` changes only through the regeneration, the
    port's golden follows at W3a-A's sync, and `requirements/sa_audit_findings.md` stays as history.
  - Planning rulings 1 to 22: confirmed as written. (the author's read, 2026-10-13)
- What W3a leaves, and to whom:
  - Tier 3's `no_freight` and `no_freight_float` (W3b or SP10); record tokens and the price rows
    (W3b or SP10); `iron_delivery`'s description ("keeps your fuel tank full") against economy
    design 7.4 (unowned, flagged).
  - The T7-8 gesture ruling (spec 11.2) is still open and holds seven lines as they stand:
    `merchant_delivery`'s `waiting_drifted`, `loss_closed`, `odom_arna_branch_a` and
    `graduation_pointer`; `iron_delivery`'s late timeliness comment; `elena_return`'s `start`;
    and `dex_return`'s `start`, whose not-turning sentence the plan added (polish design 6.3
    names only the stool). Two more of the family were not on the desk: `oren_tak_meeting`'s
    `parting` and `sienna_vek_warning`'s `farewell` (the author's T7-8 ruling, then W3b).
  - `sienna_vek_warning`'s `refuse_data` and `farewell` keep narration unmarked under Sienna's
    speaker tag (W3b's sweep); the read marked `start` and `share_data` (Q36).
  - `odom_caught_lie` stays read by nothing until SP10's hooks (Q7; it stays in
    `KNOWN_PRODUCER_ONLY_ORPHANS`). Any amends that brings Odom back after
    `iron_delivery_failed` must add that flag to his greet's "Anything else you'd put in the
    ledger for me?" reply's `excluded_flags` (SP10, Q9).
  - The read's residuals, each for W3b's writing pass unless named: `iron_delivery`'s
    `very_late` comment keeps "Intake clerk leans on the crate" (Q19); lane mentions that name
    no lane stay in `thanks_made_good`, `thanks_short`, `auto_iron_short` and Odom's greet reply
    10 (Q18); The Longer Ledger's "Odom flagged me down" though the captain goes to him on every
    route (Q8); in the D-22 case above, the clerk's "the file doesn't cover the gap" is
    arguable (Q17); Python's collect leg still reads the main hold (`free_units`), so a captain
    whose main-hold ore is gone, with their own hidden, can be signed for but completes the run
    only once ore is back in the main hold (Python only, Q2).
  - "bill of landing" is the game's document name in at least eight strings (the mission
    `bill_of_landing`, Larsen's tree, "Universal Bill of Landing", Odom's `no_permit`,
    `tomas_havens` twice); a rename to "bill of lading" would be a ruling across those files
    (the author, unowned).
  - Glyn's first-visit yes pays +3 once only because `dex_favor_accepted` ends his keep: a later
    mission that keeps him listed after the accept needs `excluded_flags`
    `["dex_favor_accepted"]` on that reply (that mission's plan, Q30).
  - The Q40 rule meets aurelia `docs/handoffs.md`'s saves stance ("manual saves anywhere") for
    SP6, which now reads "anywhere outside a conversation" in Python.
  - The voice-sheet check of Odom's lines (`requirements/character_voices.md`, Odom's sheet)
    moves to the plan's final review (Q10); Task 9's own Odom lines (Q5, Q8a, Q13b, Q13c, Q18d)
    keep his register: counts, weights and the book, no motive read.
  - The run's other flags for the author, with owners: `iron_consignment.note_sale` and
    `note_defeat` measure against every active mission's iron-ore accept cargo
    (`MissionManager.reserved_units`), which only `iron_delivery` carries today (the plan that
    authors a second iron-ore consignment); the iron section comment in
    `spacegame/constants/flags.py` ("The iron ore delivery (bug bash BB-1, BB-4)") predates W3a
    and says nothing of the state table (unowned, nothing false); older em dashes in comments of
    `tests/test_constants/test_flags.py` (lines 88, 110, 123) and in
    `requirements/roadmap/ROADMAP.md` line 1438, which no gate scans (a later prose-cleanup
    pass); `test_known_orphan_lists_stay_meaningful`
    (`tests/test_data/test_dialogue_integrity.py`, line 1283) lacks the 300 s timeout marker its
    siblings carry and times out under load (after W3a; preflight ruling R18 covers it until
    then); `test_a_return_pays_once` carries no marker and runs in 0.05 s (leave it); Elena's
    lesson test (`tests/test_data/test_return_scenes.py`, line 103) checks "80" and "140" as
    substrings (switch to a word-bounded match if an edit trips it); the call-site test's
    `_arg(c).values[0]` (`tests/test_engine/test_game_call_sites.py`, lines 306 and 307) relies
    on narrowing mypy would not apply (leave it unless mypy covers tests); rule 9's walker
    ignores reply gates (revisit if a return tree gains a gated reply after a check); rule 6's
    `self_looping_checks` (`tests/test_data/test_content_contracts.py`, line 236) catches only a
    check that fails back to its own node (plan A1's owner); the global interpreter is Python
    3.14 while the repo names 3.13, and every gate of the run passed under 3.14 (process).
    Settled in the run and kept: the rest's notices go through `on_iron_notice` into the
    banner queue, and a filing writes its Log entry at once (`Game._after_iron_clock`), both
    Python-only departures from the plan's code (Task 2's fix round).

## Act II v1

Off behind `ACT_TWO_V1_ENABLED` (tag `act2-v1-archive`). Not ported.

## Orchestration findings

Bugs in `game.py` and the views are design inputs, not parity deviations. They
are listed for the owning sub-projects in the aurelia repo's
`docs/findings_register.md` (SP2 spec Section 6).
