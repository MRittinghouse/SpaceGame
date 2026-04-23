# Living Universe Arc

**Status:** Staged. Not yet implemented. Approved for sequential execution starting with Phase 1 (NV).

**Thesis:** Aurelia has breadth. What it needs next is *specificity* — dialogue that carries voice, combat that carries memory, time that carries weight, enemies that carry grudges, crew that carry conversation. Each phase targets one of those. Together they deliver on a single promise: the universe is alive, reactive, and specific — not just populated.

**Scope at a glance:**

| Phase | Name | Estimated effort | Risk |
|-------|------|------------------|------|
| NV | Narrative Voice (Skill Check Pass + Expansion) | 10-14 days | Low |
| CE | Combat Encounters Non-Generic | 13-19 days | Moderate |
| TW | Time Weight (Moderate) | 8-12 days | High (balance) |
| RC | Recurring Rival Captains | 15-20 days | Moderate (scope) |
| CB | Crew Banter During Travel | 11-15 days | Low |
| **Total** | | **~57-80 days** | |

**Sequence:** `NV → CE → TW → RC → CB` — matches user preference and respects technical dependencies (NV first so later content inherits the voice standard; CE before RC so rivals reuse captain infrastructure; TW before RC so "days since last encounter" is a concept; CB last because it benefits from rival state, time signals, and post-NV voice discipline).

**Principles governing all five phases:**
- **No hard fails.** Nothing in this arc introduces a punishment state. Drift changes *what* happens, never locks progression.
- **Test-driven.** Every new model ships with round-trip save/load tests and model-level unit tests written first.
- **Writing Bible discipline.** Every new content file enters the compliance scanner before shipping.
- **Cross-reference integrity.** Every id referenced across systems must resolve; enforced by existing integrity tests.
- **Small polish sub-sprint at the end of every phase.** Non-negotiable.
- **Each phase is a shipping unit.** You could stop after any phase and have a meaningfully-better game. No phase leaves the game in a broken state.

---

## Phase 1 — NV: Narrative Voice (Skill Check Pass)

### Goal

Every skill-gated dialogue response is a moment of narrative insight — the skill IS the observation, not a prefix-plus-unlock. Produces a permanent voice guideline that governs all future content. NV also expands the skill check footprint so the player's build is felt across more of the game, not just in the eight places it currently fires.

### Design philosophy

A skill-gated response should answer: *"What does this character see, say, or do because of this skill that the baseline character wouldn't?"*

The existing text prefix format `[Persuasion 2]` (skill + difficulty) is preserved unchanged — NV is a content pass, not infrastructure work.

**Dual-voice convention (loose guideline, not rigid rule):**

Default voice per skill category, with freedom to mix when narrative demands:

- **Speech skills** (Persuasion, Intimidation, Deception) — default to in-quote spoken dialogue
  `[Persuasion 2] "You want out of this. I can help you find it."`
- **Observation skills** (Perception, Observation) — default to internal-observation statement
  `[Perception] His second tap was for him, not the scale.`
- **Hybrid skills** (Technical, Piloting, Leadership) — author's choice per line

**Mix formats when the line serves both.** Examples:
- Observation setting up speech: `[Persuasion 2] His shoulders are down. "I can help you find the exit."`
- Internal self-direction: `[Perception] You already know the answer. You just want permission to say it out loud.`

The rule under the guideline: **skill should produce insight.** Whether that insight is voiced out loud or lands internally is a craft call per line.

**Ladder of quality:**
- **D:** `[Persuasion 2] I disagree.` — skill is a gate, response is empty
- **C:** `[Persuasion 2] You're not wrong, but there's an angle.` — skill colors tone
- **B:** `[Persuasion 2] "You want to be talked out of this. I can help."` — skill reads the NPC
- **A:** `[Perception] His second tap was for him, not the scale.` — skill IS the insight

Target: every skill-gated response at grade A or B. Zero at grade D.

**Scope contract (scope-explosion handling):** if the NV-1 audit finds significantly more existing skill-gated responses than anticipated (current estimate ~70-140), prioritize rewrites by dialogue traffic — rewrite high-traffic first (Arna arc, companion onboarding, faction introductions, starter NPCs), defer lower-traffic rewrites to a follow-up pass. Calendar is held; coverage is phased.

### Architecture

**No new models.** Dialogue system already supports the mechanic via `required_flags` and (where applicable) attribute/skill checks on response options. This phase is editorial + compliance-tooling.

**Optional enhancement (recommended):** add an optional `skill_tag` field to response entries:

```json
{
  "text": "His second tap was for him, not the scale.",
  "skill_tag": "perception",
  "required_flags": ["knows_tev_skims"]
}
```

This:
1. Lets the compliance scanner identify skill-gated responses explicitly (current identification via required_flags is heuristic and brittle).
2. Lets the UI render the `[PERCEPTION]` prefix consistently with theme color per skill type.
3. Lets tests verify every `skill_tag` response meets voice standards.

### Sub-sprint breakdown

**NV-0: Specialization soft modifier** (~1 day) — mechanic infrastructure that governs both existing checks and NV-7 expansion.
- Add `get_specialization_ratio(skill_id)` and `get_specialization_bonus(skill_id)` on `SocialManager`.
- Formula: `ratio = skill_base / mean(all_social_base_levels)`; `bonus = int((ratio - 1.0) * 2)` clamped `[-2, +2]`.
- Integrate bonus into `get_effective_level`.
- Tests: balanced (bonus 0), specialist (bonus +1/+2), neglector (bonus -1/-2), edge cases.
- Rewards focused investment over passive level-grinding across the entire game.

**NV-7: Skill check expansion** (~3-5 days) — **FIRST WAVE SHIPPED 2026-04-23**

21 new skill checks authored across 14 high-traffic dialogue trees. All 7 skill types registered by NV-6.5 now have gameplay presence; four of them (Intimidation, Deception, Technical, Piloting, Leadership) went from zero existing checks to active coverage.

**Distribution (checks added in this wave):**
| Skill | Added | After |
|-------|-------|-------|
| Persuasion | +2 | 9 |
| Intimidation | +3 | 3 |
| Observation | +6 | 9 |
| Deception | +2 | 2 |
| Technical | +4 | 4 |
| Piloting | +1 | 1 |
| Leadership | +3 | 3 |
| **Total** | **+21** | **31** |

**Dialogues enriched:**
- **Arna arc** (4): `arna_post_completion::catch` (Observation 2, catches her contact-hedge), `arna_post_ore_tip::start` (Observation 2, catches double-weigh), `keren_meet::start` (Observation 3, catches the hands-in-pockets tell), `arna_post_ambush::okay` (Leadership 2, take command while she's bleeding).
- **Companions** (7): Elena gets Piloting (reads her routes-math) and Persuasion (presses past "between contracts"). Marcus gets Observation (catches his name-recognition) and Technical (reads the air-recycler-report depth). Priya gets Technical (isotope decay insight) and Leadership (captain-claims-father-by-name). Tomas gets Deception (manifest-splitting bluff).
- **Starter NPCs** (3): Larsen gets Deception (personal-kit bluff at customs), Forgeworks clerk gets Technical (flags the hot crucible), Odom has no check this wave (deferred to NV-7 continuation).
- **Faction** (7): Hanna gets Leadership (real-load offer) AND Intimidation (reads her understaffed dock). Reva gets Intimidation (cold-path pressure for names). Dex gets Observation (spots the Guild auditor's cover). Torres gets Intimidation (threaten before handing over chip). Oren gets Observation (spots his holdout hand). Sienna gets Technical (names the gravitational lensing array).
- **Tev** (1): Persuasion 2 on fee breakdown (forces the real total out of him).

**"Insight flags" introduced:** 17 new producer-only flags (e.g., `read_arna_weighing`, `read_marcus_engineer`, `spotted_auditor_cover`, `intimidated_ambush_squad` — removed during the keren_meet fix). All flags catalogued in `KNOWN_PRODUCER_ONLY_ORPHANS` with a note explaining they're "insight flags" that preserve narrative memory for future content to consume.

**Compliance:** all 21 new checks pass NV-5 gating (bracket prefix, skill registered, skill/difficulty match, ≥6 words body, no bare declaratives). Writing Bible compliance verified across the full dialogue corpus.

**Balance fix:** `test_dex_persuasion_branching` updated to filter for the Persuasion check specifically (NV-7 added an Observation check at the same node).

**Integrity fix:** discovered that `skill_check.success_node_id` / `failure_node_id` must be non-null; removed one planned Intimidation check at `keren_meet::inspect` that required null node refs (scripted ambush terminal response).

**What's deferred to NV-7 continuation / NV-8:**
- Distribution target (43) only 49% hit — wave two can expand Deception, Intimidation, Persuasion (still under target).
- Ground mission NPCs (14 dialogue trees, 0 checks) untouched this wave. Quick-win target for continuation.
- Odom's `merchant_delivery` (25 responses) skipped. Good Persuasion/Observation target.
- NV-8 will playthrough-verify the content in context.

Tests: 7,711 passing, zero regressions.

---

**NV-6.5: Skill registry expansion** (~1-2 days) — **SHIPPED 2026-04-23**

Infrastructure sprint before NV-7 content. Registered four new skills so the authoring palette goes from 3 to 7.

- Added `deception`, `technical`, `piloting`, `leadership` to `SOCIAL_SKILL_DEFINITIONS`. Same XP thresholds, same max level 5, same ±2 growth on success/failure.
- New `SKILL_TO_ATTRIBUTE` map routes synergy per skill: socials → SYN, Technical → ING, Piloting → ACU. New `AttributeSheet.get_attribute_check_bonus(attr_id)` method.
- New `SKILLS_USING_DISPOSITION` set selectively applies disposition modifier — only social-interaction skills respond to NPC mood; Technical/Piloting ignore it (NPC opinion doesn't change whether you can read a circuit).
- `faction_social_bonus` (Cultural Savant) also now correctly scoped to social skills only.
- Tree skills added (4 base + 3 variants):
  - Base (Tier 1, +1 to checks, max_level 2): `poker_face` (Social→Deception), `tool_sense` (Industry→Technical), `steady_stick` (Exploration→Piloting), `give_the_word` (Leadership→Leadership).
  - Variants (Tier 2, narrowly-scoped, prerequisites the base): `ghost_protocol` (Deception+contraband), `engineer_insight` (Technical+refining), `command_presence` (Leadership+crew).
- XP growth hooks outside dialogue (proactive — addresses "new skills stagnate if NV-7 dialogue is sparse"):
  - `refining_view._handle_result` grants Technical +2 XP per successful refine.
  - `game._grant_piloting_xp_on_combat_win` grants Piloting +2 XP per true VICTORY (not negotiated).
- Downstream wiring: `tests/test_data/test_skill_check_voice.py` VALID_SKILLS expanded; `tools/nv_audit.py` skill inference updated with heuristics for all 7; `dialogue_writing_guide.md` infrastructure note rewritten with attribute mapping, disposition rules, XP growth, and per-skill authoring notes with GOOD/BAD examples for each new skill.
- Back-compat: `SocialManager.load_state` existing behavior handles old 3-skill saves cleanly (new skills default to level 1); test coverage confirms.
- Total new tests: +29 in `tests/test_models/test_nv_skill_registry.py` covering registry, attribute mapping, selective disposition, tree bonuses, save/load, XP hook wiring.

Total skill count: 75 → 82. Total max levels: 132 → 146.

---

**NV-0.5: Long-response tooltip UI** (~1-2 days) — UI infrastructure for voice-rich skill-gated responses.
- `_ResponseButton` gains `is_truncated` flag, detected at init from font+rect+text.
- Truncation indicator switched from `..` to styled `…` in highlight color.
- `DialogueView._render_response_tooltip` draws full wrapped text near the hovered truncated button.
- Tooltip auto-positions right of button; flips left if it would clip; clamps to screen edges.
- Layout remains stable (no button height changes, no stack re-flow).
- Tests cover truncation detection, tooltip positioning (right/flip/clamp), visibility logic.

**NV-1: Audit + tooling** (~1 day)
- Write `tools/nv_audit.py`: scans `data/dialogue/dialogues.json`, identifies response options with skill-derived `required_flags`, outputs a CSV + markdown catalog.
- Generate `requirements/nv_audit_findings.md` with the complete catalog grouped by skill type, current quality grade (manually tagged), and rewrite priority.
- Identify 3 "reference quality" examples already in the codebase to anchor the voice guide.

**NV-2: Social skill rewrite pass** (~2-3 days)
- Target skills: Persuasion, Intimidation, Perception, Observation, Deception.
- Estimated volume: 40-60 lines (confirmed by NV-1).
- Each rewrite: preserves mechanical effect, adds voice. Side-by-side before/after tracked in audit findings doc.
- Rewrites committed in small batches of 10-15 lines per commit for reviewability.

**NV-3: Knowledge skill rewrite pass** (~1-2 days)
- Target skills: Technical, Piloting, Leadership.
- Estimated volume: 20-30 lines.
- Technical: engineering-insight voice ("[TECHNICAL] That relay's been patched twice. Third time it fails.").
- Piloting: pilot-intuition voice.
- Leadership: people-reading voice.

**NV-4: Writing Bible update** (~0.5 day)
- Add section to `requirements/dialogue_writing_guide.md`: "Skill Check as Voice."
- Before/after gallery (pull 8-10 from NV-2/3).
- Anti-patterns gallery.
- Canonical format spec: `[SKILL] observation-as-narrative.`

**NV-5: Compliance tests** (~0.5 day)
- New file: `tests/test_data/test_skill_check_voice.py`.
- Tests:
  - No bare declarative unlocks (regex: `\[[A-Z]+\]\s+(I agree|I disagree|Yes|No|Sure|OK)\.$`).
  - Minimum length: skill-tagged responses ≥ 6 words.
  - No AI tells within skill-tagged responses (extends existing Writing Bible scanner to apply to this subset explicitly).

**NV-6: Integration polish** (~1-2 days) — **SHIPPED 2026-04-23**

Five sub-sprints:
- **NV-6a**: Narrative flow verification. Read every downstream NPC node for each of the 10 rewrites — ~14 nodes total. Verify each NPC's next beat still lands with the new player voice. Finding: all paths align; an unexpected win at summit where the new `[Observation 2]` text primes the `noticed_signal` reveal as a genuine callback.
- **NV-6b**: Character voice verification. Cross-check rewrites against `character_voices.md` for Reva, Dex, Oren, Priya. Each rewrite provokes exactly the NPC register the sheet calls for: Reva drops briefing tone, Dex drops the mask, Oren's jaw works chewing bitter.
- **NV-6c**: Playthrough integration tests. New `tests/test_scenarios/test_scenario_nv_skill_checks.py` with 10 scenarios exercising NV-0 + NV-2/3 + NV-5 on real content. Specialist vs generalist vs neglector at Observation 2 (Tev), Persuasion 3 (Dex), and specialization-as-tie-breaker at borderline D3.
- **NV-6d**: Critical re-read. One tightening applied: summit Observation changed "runs out today" → "ends today" (more concrete, ties to summit situation). Nine others at A/strong-B, no adjustment.
- **NV-6e**: Arc closeout documentation (this section).

Tests after NV-6: 7,682 passing (+10 integration scenarios, +0 regressions). Full suite still green on parallel run.

**NV-7: Skill check expansion** (~3-5 days)
- **Contract:** never gate plot progression. Every mission outcome reachable without any skill check. New checks only change FLAVOR (richer beat, unique line, NPC color), EFFICIENCY (skip 2 dialogue nodes, unlock a shortcut response), or UNLOCK DETAIL (set a knowledge flag that colors later scenes).
- **Variety target:** every skill type (Persuasion, Intimidation, Deception, Perception, Observation, Technical, Piloting, Leadership) gets new checks. Weighted toward currently under-used skills.
- **Focus:** high-traffic dialogue surface first — Arna arc, 4 companion trees, faction introductions, Odom/Larsen/Broker starters, cantina recruit NPCs.
- **Target volume:** 40-60 new skill checks across ~15-20 dialogue trees. 2-3 checks per dialogue average.
- **Difficulty distribution:** mixed. Tier 1 (frequent, low-investment hit) through Tier 3 (high-investment payoff). Nobody locked out; everybody's build matters somewhere.
- **Authoring discipline:** each new check follows the NV voice standard from NV-2/3. Compliance tests from NV-5 catch violations.
- **Never breaks the dialogue graph.** New responses added as additional options, not replacements. Existing flow preserved.

**NV-8: Expansion polish, tests, integrity** (~1-2 days)
- Cross-reference integrity: every new skill_check resolves (skill name valid, success/failure nodes exist, flags resolve).
- Writing Bible compliance scan on all new content.
- Playthrough test: walk a full dialogue tour, verify all new checks trigger correctly.
- Distribution audit: confirm skill variety target met (no skill over-represented).
- Update `dialogue_writing_guide.md` with the NV-7 examples as a "skill check authoring" section.

### Acceptance criteria

- [ ] All skill-gated responses in `dialogues.json` rewritten to grade A or B (NV-2/3).
- [ ] `requirements/dialogue_writing_guide.md` has a "Skill Check as Voice" section with examples (NV-4).
- [ ] `test_skill_check_voice.py` has at least 5 compliance tests, all passing (NV-5).
- [ ] Zero bare declaratives on skill-gated responses.
- [ ] Audit findings doc committed for permanent reference (NV-1).
- [ ] 40-60 new skill checks authored across high-traffic dialogues, covering all 8 skill types (NV-7).
- [ ] Distribution audit confirms no skill over-represented (NV-8).
- [ ] All new checks preserve existing dialogue flow — every mission outcome still reachable without any skill check (NV-8 verified via playthrough test).
- [ ] `dialogue_writing_guide.md` gains an authoring section with examples drawn from NV-7 (NV-8).

### Risks

- **Editorial drift.** Rewriter might introduce new AI tells. → Compliance tests run on every commit.
- **Mechanical regression.** Rewriting a response could accidentally change its required_flags. → Audit tool + diff review pre-commit.

---

## Phase 2 — CE: Combat Encounters Non-Generic

### Goal

Combat encounters carry specificity — named captains, situational complications, varied encounter types. Regular fights feel authored even when procedurally generated.

### Design philosophy

Combat is currently mechanically rich but narratively thin. This phase adds CONTENT layers to the existing combat engine. It does NOT rebuild combat. It gives it story.

Four CE pillars:
1. **Captains over templates.** Notable enemy ships have a captain with a name and voice.
2. **Encounter complications.** Fights can change shape mid-turn.
3. **Non-combat encounter variety.** Not every encounter is a fight — expand the lexicon.
4. **Crew speaks during combat.** The ship feels inhabited.

### Architecture

**New models:**

`EnemyCaptain` (`spacegame/models/enemy_captain.py`):
```python
@dataclass
class EnemyCaptain:
    id: str
    name: str
    nickname: str  # e.g., "Wolf's Ear"
    home_sector: str  # system_id or region
    signature_ship_template: str  # enemy_template_id
    pre_combat_hail_id: str  # dialogue_id from combat_hails.json
    surrender_line: str
    retreat_line: str
    victory_line: str
    defeat_line: str  # when defeated (can be same as retreat if captain always flees)
    is_recurring: bool = False  # True if this captain is a rival (RC reads this)
```

Note: `is_recurring` flag prepares RC integration. CE-phase captains are `is_recurring=False`. RC promotes some captains to recurring in a later phase.

`CombatComplication` (`spacegame/models/combat_complication.py`):
```python
@dataclass
class CombatComplication:
    id: str
    name: str
    trigger_type: str  # "turn_counter" | "hp_threshold" | "player_action" | "random"
    trigger_params: dict  # e.g., {"turn": 3} or {"hp_pct": 0.3}
    effect_type: str  # "spawn_reinforcement" | "environmental" | "choice_prompt" | "iff_change"
    effect_params: dict
    description: str  # player-facing
    narration: str  # displayed when fires
```

**New content files:**
- `data/combat/captains.json` — captain roster
- `data/combat/complications.json` — complication templates
- `data/dialogue/combat_hails.json` — compact dialogue trees for captains
  - Short single-node trees in most cases (one hail + player response)

**Extended models:**
- `EncounterDefinition` gains: `captain_id: Optional[str]`, `complication_ids: list[str]`, `pre_combat_dialogue_id: Optional[str]`, `post_combat_dialogue_id: Optional[str]`.
- `EnemyTemplate` adds: `default_captain_id: Optional[str]` — for templates that represent a specific captain's ship.

**Extended behavior:**
- `spacegame/engine/game.py`: encounter resolution flow gains pre-combat dialogue phase, complication registration, post-combat dialogue phase.
- `spacegame/views/combat_view.py`: turn-counter hook for complications, complication narration display.
- `spacegame/models/combat.py`: complication trigger evaluation in turn resolution.

### Sub-sprint breakdown

**CE-1: Captain model + dialogue hook infrastructure** (~2-3 days)
- Define `EnemyCaptain` + `CombatComplication` models.
- Extend `EncounterDefinition`.
- Add pre/post-combat dialogue hooks in game.py encounter flow.
- Save/load tests on new models.
- Back-compat: encounters without captain fields fall through unchanged.

**CE-2: Captain roster authoring (non-recurring flavor)** (~3-4 days)
- Author 15-20 captain entries, distributed across sectors and factions.
- Each with: name, nickname, ship template link, 5-line hail dialogue tree, 3-4 combat-phase lines (surrender/retreat/victory/defeat).
- Examples:
  - Captain Vela "Wolf's Ear" — Haven's Rest pirate
  - Deckhand Soren — Guild-aligned mercenary
  - The Twin Stars (Inez + Rafa) — Crimson Reach duo, appear together
  - Calder the Reader — reads player's ship for weakness before fight
  - Captain Hadrian — an honorable pirate who always offers surrender at low HP
- Each captain is **non-recurring** at this phase. RC will promote specific captains (or add new ones) as rivals later.

**CE-3: Complication system** (~3-4 days)
- Implement 6-8 complication types:
  1. `reinforcement_arrival` — at turn N, spawn additional enemies
  2. `civilian_in_crossfire` — non-combat freighter takes collateral; player can break off to defend (reputation effect on ignore)
  3. `distress_nearby` — mid-fight distress signal; choice to pivot to rescue or continue
  4. `shield_harmonic` — environmental: all shields regenerate 50% slower
  5. `enemy_surrender` — captain offers surrender at low HP
  6. `third_party_ambush` — a third faction ship appears, attacks one side
  7. `asteroid_closure` — playing field shrinks each turn
  8. `comms_hijack` — enemy fakes distress in your IFF, heat-like fallout
- Each wired to combat turn resolution.
- Each has an existing encounter template demonstrating usage.

**CE-4: Non-combat encounter variety** (~2-3 days)
- 4-5 new encounter types beyond the current pirate-attack template:
  1. `ransom_demand` — skill check or pay (no combat if resolved cleanly)
  2. `cargo_shakedown` — persuasion / intimidation / pay / fight
  3. `distress_bait` — distress signal that reveals as ambush if you approach
  4. `wandering_trader` — one-off NPC merchant, rare good at premium
  5. `derelict_encounter` — salvage with potential complication (hostile drones inside)

**CE-5: Crew combat interjections** (~2-3 days)
- ~30-40 short crew lines triggered during combat by:
  - First turn (crew greeting / acknowledgment)
  - Player health threshold (concerned line at 30% hull)
  - Enemy health threshold (confidence line at enemy 20% hull)
  - Specific enemy type (crew reacts to seeing their nemesis-tier enemies)
  - Combat outcome (post-fight line)
- Per companion, voiced consistent with existing character voice sheets.
- Displayed as subtitle / speech bubble, non-blocking.

**CE-6: Content scale audit + polish** (~2-3 days)
- Audit existing encounter pool; identify generic encounters for enrichment.
- Goal: every faction has 3+ distinctive encounter types.
- Zero "unflavored pirate_scout" encounters without at least flavor text or captain attribution.
- Polish pass: re-read all captain dialogue in context, tighten.

### Testing strategy

- **Unit:** `EnemyCaptain`, `CombatComplication` round-trip tests.
- **Integration:** encounter fires with captain → pre-combat dialogue shows → combat proceeds → appropriate post-combat dialogue.
- **Integration:** each complication fires at correct trigger condition.
- **Content integrity:** every `captain_id` / `complication_id` / `combat_hail_id` referenced in encounter definitions resolves.
- **Writing Bible:** captains.json + combat_hails.json added to compliance scanner.
- **Dialogue integrity:** new combat_hail dialogues pass existing integrity test (no orphan flags, no broken references).

### Acceptance criteria

- [ ] 15-20 captains authored, each with complete dialogue.
- [ ] 6-8 complication types implemented and demoable.
- [ ] 4-5 new non-combat encounter types added.
- [ ] ~30-40 crew combat lines authored.
- [ ] All new content in Writing Bible compliance.
- [ ] Test count growth: +~50 tests estimated.
- [ ] Zero regressions in existing combat tests.

### Risks

- **Scope creep into RC territory.** CE captains are flavor; RC captains are rivals. → Mandatory: `is_recurring=False` for all CE captains.
- **Complication balance.** Some complications could dominate encounters. → Each complication tuned in isolation; encounter pool controls frequency.
- **Dialogue combinatorial explosion.** Crew × captain × outcome could produce too much content. → Start with trigger types, not combinations. Crew lines are generic to situation, not per-captain.

---

## Phase 3 — TW: Time Weight (Moderate)

### Goal

Time feels like it moves. The player notices. No hard fails, no punishment states. Selected narrative threads drift if ignored. Soft deadlines modulate reward. The galaxy emits world-moved signals.

### Design philosophy

**"Moderate" is the load-bearing constraint.** Implementation choices should always fall on the lighter side. If a design decision COULD punish, it MUST not.

Pillars:
1. **Drift, not fail.** NPC states CHANGE if ignored, but the arc continues. Different content, not locked content.
2. **Soft deadlines.** Some missions reward MORE for promptness, but never reward NOTHING for late completion.
3. **World signals.** News, journal, and environmental dialogue drift over time — the player hears the galaxy moving.
4. **Selective.** 5-8 threads get time weight. Not every thread, not every NPC, not every mission.

### Architecture

**New models:**

`TimedThread` (`spacegame/models/timed_thread.py`):
```python
@dataclass
class TimedThread:
    id: str
    last_touched_day: int  # set by game_day when thread is "touched"
    drift_states: list[DriftState]  # ordered by threshold_days ascending
    current_state_id: str
    touch_triggers: list[str]  # dialogue_flags that "touch" this thread when set

@dataclass
class DriftState:
    id: str  # state identifier
    threshold_days: int  # drift happens at game_day >= last_touched_day + threshold
    journal_entry_on_enter: Optional[str]  # journal entry to auto-add
    flag_to_set_on_enter: Optional[str]  # dialogue flag to set
    narration: Optional[str]  # short news/ticker line
```

`SoftDeadline` (`spacegame/models/soft_deadline.py`):
```python
@dataclass
class SoftDeadline:
    mission_id: str
    full_reward_day_count: int  # days from accept for 100% reward
    partial_reward_day_count: int  # days from accept for reduced reward
    partial_reward_multiplier: float  # e.g., 0.7
```

**New content files:**
- `data/progression/timed_threads.json` — 5-8 thread definitions
- Soft deadlines embedded in mission definitions (new optional field on Mission)

**Extended models:**
- `Player` gains `timed_thread_state: dict[str, dict]` — per-thread state
- Mission reward resolution: check for `soft_deadline` field, apply multiplier

**New system hooks:**
- On `game_day` tick: evaluate all TimedThreads, fire drift transitions
- On `dialogue_flags` set: check if flag is a touch_trigger for any thread, update last_touched_day
- On mission complete: evaluate soft_deadline, apply multiplier to reward

### Sub-sprint breakdown

**TW-1: Model + persistence** (~2 days)
- Define `TimedThread`, `DriftState`, `SoftDeadline` models.
- Save/load round-trip tests.
- Player model extension for timed_thread_state.

**TW-2: Thread authoring** (~2-3 days)
- Author 5-8 threads:
  1. **`arna_post_arc`** — 60 days untouched after Arna's branch closeout → journal adds "Heard Arna left Nexus after all."
  2. **`marcus_lead_cold`** — 30 days since accepting Marcus's quest without progress → journal "Marcus's lead went cold. He's less talkative now."
  3. **`summit_restless`** — 60 days summit unprogressed → news fires "Factions holding second summit, this time without [player]"
  4. **`priya_impatience`** — 20 days between delivery accept and complete → Priya delivers mission with edge
  5. **`elena_unspoken`** — 45 days without Elena dialogue → next Elena conversation acknowledges absence
  6. **`tomas_restless`** — 30 days aboard without a mission → Tomas suggests work
  7. **`crimson_reach_watching`** — after Branch A betrayal + 30 days → news entry "Reach put a bounty on a captain matching your signature"
  8. **`oren_tak_drifted`** — 45 days since Oren's info without return → Oren's next dialogue drifts toward distrust
- Each thread: define drift states, touch triggers, journal/news/dialogue wiring.

**TW-3: Soft deadlines** (~1-2 days)
- Mission model extension for `soft_deadline` field.
- Reward multiplier logic.
- 6 missions get soft deadlines:
  1. Coolant run (M1): 10 days full, 15 days partial (0.75×)
  2. Iron delivery (M2): 14 full, 18 partial
  3. Priya delivery: 20 full, 25 partial
  4. Iron Depths anomaly scan: 30 full, 40 partial
  5. Marcus tunnel survey: 25 full, 35 partial
  6. Evidence delivery (M15): 40 full, 60 partial
- UI indicator: mission log shows "X days left for full reward" when deadline approaches.

**TW-4: World-moved signals** (~2-3 days)
- Passive news generation: every 7 in-game days of inactivity on main campaign, a news entry fires from an "in-between" pool.
- Author ~20 in-between news templates.
- Journal entries gain `created_day` field (backfill for existing entries via migration).
- Relative-time formatting: "12 days ago" in journal view.

**TW-5: Cockpit HUD date polish** (~1 day)
- Clean date indicator in cockpit: `"Day 47 — Year 2335"`.
- Optional counters (behind a setting): "days without port," "days without combat."

**TW-6: Balance + QA** (~1-2 days)
- Deliberate slow-playthrough scenario test: verify no progression locks.
- Deliberate rush scenario test: verify deadlines aren't too generous (full reward still meaningful).
- Playtest gate: a full arc run with each playstyle, noting any friction.

### Testing strategy

- **Unit:** `TimedThread` drift progression (state X on day Y).
- **Unit:** `SoftDeadline` reward tiers.
- **Integration:** thread touched → last_touched_day updates → drift NOT fires on that day.
- **Integration:** thread untouched for threshold → drift fires → journal entry auto-added.
- **Save/load:** timed_thread_state round-trips.
- **Scenario:** automated slow-playthrough doesn't lock any arc.

### Acceptance criteria

- [ ] 5-8 TimedThreads defined and wired.
- [ ] 6 missions have soft deadlines.
- [ ] ~20 in-between news templates authored.
- [ ] Cockpit shows clean date.
- [ ] Slow-playthrough scenario passes (no locks).
- [ ] Rush-playthrough scenario shows rewards intact.
- [ ] All drift transitions reversible by reading journal (player understands what changed).

### Risks

- **"Moderate" violation.** Easy to over-engineer. → Mandatory balance-review checkpoint mid-phase. Every drift state reviewed against "does this punish?"
- **Touch trigger gaps.** A thread might not have a touch trigger players naturally hit. → Each thread defined with 2+ touch triggers; audit.
- **News churn.** Passive news could feel spammy. → Rate limit: max 1 passive news entry per 7 days.

---

## Phase 4 — RC: Recurring Rival Captains

### Goal

8-12 named enemy captains who persist across a playthrough. Each has history, grudge, and evolving ship. Crew recognizes them. Journal tracks them. News mentions them. Combat tells stories.

### Design philosophy

This is a system, not a sub-feature. Every rival is a CHARACTER with a named ship, a voice, an operating region, and a story arc implicit in their encounter history. Rivals never die in first contact — they flee. Lieutenants inherit on death. Grudge persists through save/load.

Pillars:
1. **Named rivals, not templates.** 8-12 at launch, authored individually.
2. **Retreat before death.** Rivals flee at low HP until final confrontation.
3. **Ship evolution.** Grudge drives loadout escalation.
4. **Crew recognition.** Companions speak when rivals appear.
5. **Lieutenants inherit.** Killing a rival spawns their lieutenant with inherited grudge.
6. **Journal + news integration.** Rival history is visible and re-readable.

### Architecture

**New models:**

`RivalCaptain` (`spacegame/models/rival_captain.py`):
```python
@dataclass
class RivalCaptain:
    id: str
    name: str
    nickname: str
    home_sector: str
    operating_systems: list[str]  # spawn-eligible systems
    ship_evolution: dict[int, str]  # grudge_level → enemy_template_id
    lieutenant_id: Optional[str]  # rival_id that inherits on death
    dialogue_id_prefix: str  # e.g., "rival_vela" resolves to rival_vela_pre, _during, _retreat, etc.
    lore: str  # backstory for journal
```

`RivalState` (persistent, per-player):
```python
@dataclass
class RivalState:
    rival_id: str
    grudge_level: int  # 0-5
    encounters_survived: int  # player failed to defeat them
    encounters_defeated: int  # player "won" (rival retreated or died)
    first_encountered_day: int
    last_encountered_day: int
    status: str  # "not_met" | "active" | "dead" | "lieutenant_inherited"
    lieutenant_active: bool
```

`RivalEncounterEntry`:
```python
@dataclass
class RivalEncounterEntry:
    rival_id: str
    game_day: int
    system_id: str
    outcome: str  # "rival_retreated" | "rival_killed" | "player_killed" | "standoff"
    grudge_delta: int
```

**New content files:**
- `data/combat/rivals.json` — full rival roster
- Rival dialogue trees added to `data/dialogue/dialogues.json` under `rival_<id>` prefix

**Extended models:**
- `EnemyCaptain` (from CE) gains optional `rival_id` — if set, promotes this captain to a rival
- `Player` gains `rival_states: dict[str, RivalState]` and `rival_history: list[RivalEncounterEntry]`

**New behavior:**
- `RivalSpawnManager`: when an encounter rolls, check if any rival is eligible in this system (operating_systems + grudge_level + cooldown). Weight their spawn against generic encounters.
- `RivalRetreatBehavior`: rival ships flee at 20% hull (configurable per rival). Combat ends with rival-retreated outcome.
- `LieutenantInheritance`: on rival death with lieutenant_id, lieutenant transitions to active with grudge_level=2 (inherited anger).

### Sub-sprint breakdown

**RC-1: Rival model + state machine** (~2 days)
- Models, save/load, state transitions.
- Player extension for rival_states + rival_history.

**RC-2: Retreat mechanic** (~2 days)
- Combat engine extension: detect rival at low HP, trigger retreat sequence.
- Visual: rival ship warps out / smokescreens / signature exit.
- Encounter outcome handler: rival retreat → grudge increments, encounter logged.

**RC-3: Spawn manager + weighting** (~2 days)
- System-level spawn eligibility check.
- Weight against generic encounter pool.
- Cooldown enforcement (rivals don't spawn back-to-back in consecutive encounters).
- TW integration: "days since last seen" gates minimum recovery time.

**RC-4: Ship evolution tables** (~2 days)
- Per-rival tier progression (3 tiers typical).
- Tier 1: baseline ship. Tier 3: boss-tier with lieutenants escorting.
- Author ship loadouts per tier per rival.

**RC-5: Dialogue authoring** (~3-4 days)
- Per rival, author 6-10 dialogue lines:
  - Pre-combat hail (varies by grudge level)
  - During-combat taunts (1-2 per grudge level)
  - Retreat line ("I'm out. You'll see me again.")
  - Post-combat defeat line (if caught at low HP and defeated)
  - Death line (final confrontation)
  - Lieutenant-inheriting line (their final message)
- Total: ~60-100 dialogue lines.

**RC-6: Crew recognition** (~1-2 days)
- Per-crew × per-rival affinity map.
- Author ~30-40 short recognition lines.
- Triggered on rival encounter start.

**RC-7: Journal + news integration** (~1-2 days)
- Auto-journal entries on: first encounter, every 2nd encounter, death, lieutenant inheritance.
- News ticker templates: "Rumor: the Red Knife was seen near Iron Depths last week."
- "Rival tracker" sub-view in journal (optional sub-sprint).

**RC-8: Initial rival roster authoring** (~3-4 days)
- 8-12 rivals, each with:
  - Name + nickname
  - Home sector + operating systems
  - 3-tier ship evolution
  - Lieutenant definition
  - Lore entry
  - Full dialogue tree
- Roster should cover variety:
  - Early-game pirate (Vela "Wolf's Ear")
  - Ex-arc antagonist (Keren Ortiz — promotes from Arna arc)
  - Escaped Ledger captain (main campaign tie-in)
  - Faction-aligned rogue (Commodore Halden — Guild-adjacent)
  - Mirror-style mercenary (Sash Vey "The Mirror" — scales with player)
  - Legendary (Red Knife — rare, escalating)
  - Crew-tied (Priya's old rival — ties to companion quest)
  - Anti-faction zealot (Thorne)
  - Late-game queen (Old Berna)
  - Speed runner (Kaz Dramin — always outpaces, never stays to die)
  - Opportunist (The Collector — appears when player carries premium cargo)
  - Endgame tier (Boss Ashkeeper — spawns at grudge 5 on others)

**RC-9: Death + lieutenant handling** (~1 day)
- On rival death with lieutenant_id: transition rival to dead, lieutenant to active (grudge=2).
- Journal entry: "You killed [X]. [Y] took the ship."
- Grace period: lieutenant doesn't spawn for N days.

**RC-10: Tests + cross-ref integrity** (~1-2 days)
- Rival state transitions (unit).
- Save/load with various rival states (integration).
- Spawn weighting distribution (statistical test over N rolls).
- Cross-reference: every rival_id in dialogue resolves; every lieutenant_id resolves.

### Testing strategy

- **Unit:** RivalCaptain, RivalState, RivalEncounterEntry round-trips.
- **Unit:** state transitions (not_met → active → dead → lieutenant_inherited).
- **Integration:** encounter resolution with rival spawn → dialogue → combat → retreat → grudge increment.
- **Integration:** lieutenant inheritance on rival death.
- **Statistical:** spawn weighting distribution over 1000 rolls matches design target.
- **Save/load:** rival state survives across saves.
- **Content integrity:** dialogue ids resolve, ship templates resolve, lieutenant chain is acyclic.

### Acceptance criteria

- [ ] 8-12 rivals authored with complete dialogue + ship evolution.
- [ ] Retreat mechanic works reliably at 20% hull.
- [ ] Grudge increments on every rival-survived encounter.
- [ ] Ship evolves across grudge tiers.
- [ ] Lieutenant inheritance works on rival death.
- [ ] Crew recognition fires on rival appearance.
- [ ] Journal auto-logs encounters.
- [ ] News ticker fires rival activity entries.
- [ ] All rivals pass Writing Bible + integrity scans.
- [ ] Test count growth: +~80-100 tests estimated.

### Risks

- **Ship balance.** Grudged rival might be unbeatable or trivial. → Tier progression scales with player level, not just grudge count.
- **Save/load edge cases.** Long playthroughs with many rivals in various states. → Dedicated RC save/load test suite covering all state combinations.
- **Spawn cadence.** Rivals could over-saturate encounters. → Hard caps: max 1 rival per encounter, max 1 rival encounter per N system jumps.
- **Content authoring fatigue.** 12 rivals × 8 lines = 96+ lines of combat dialogue. → Phase the authoring: 4 rivals per sub-batch, ship each batch separately.

---

## Phase 5 — CB: Crew Banter During Travel

### Goal

Crew speaks during travel in short, non-blocking exchanges. Banter is contextual to destination, recent events, crew composition, and rival state. 40-60 entries at launch, scalable.

### Design philosophy

Banter is ambient character. It is never required. It never blocks. It is precious — low frequency keeps it fresh. Every line is in-voice per the character voice sheets (Elena, Marcus, Priya, Tomas).

Pillars:
1. **Non-blocking, low-frequency.** One banter per ~3 jumps on average.
2. **Contextual.** Triggered by destination, recent events, crew pairs, rival state.
3. **In-voice.** Per-crew consistency with `character_voices.md`.
4. **Re-readable.** Ship log menu preserves all heard banter.
5. **Scalable.** Trigger system accommodates future authoring.

### Architecture

**New models:**

`BanterEntry` (`spacegame/models/banter_entry.py`):
```python
@dataclass
class BanterEntry:
    id: str
    trigger_conditions: BanterTrigger
    speakers: list[str]  # crew_ids in order
    lines: list[str]  # alternating speakers
    weight: int  # selection weight when multiple eligible
    cooldown_days: int  # minimum days before can re-fire
```

`BanterTrigger`:
```python
@dataclass
class BanterTrigger:
    trigger_type: str  # "destination" | "crew_pair" | "flag" | "combat_after" | "rival_seen" | "idle"
    destination_id: Optional[str]  # required system
    required_crew: list[str]  # crew_ids that must be aboard
    required_flags: list[str]  # dialogue_flags
    excluded_flags: list[str]
    recent_combat_within_days: Optional[int]  # trigger after combat in last N days
    rival_id: Optional[str]  # trigger on entering rival territory
    min_jump_count: int = 0  # prevents very-early banter
```

**New system: `BanterEngine`** (`spacegame/engine/banter_engine.py`):
- `evaluate_eligible(game_state) → list[BanterEntry]`
- `select_banter(eligible) → BanterEntry` (weighted random)
- `fire_banter(banter) → displays + marks in history`

**New content files:**
- `data/dialogue/banter.json` — all banter entries

**Extended models:**
- `Player` gains `banter_history: list[dict]` (banter_id + game_day)

**Display layer:**
- `spacegame/views/banter_overlay.py` — non-blocking subtitle during warp/jump transition
- Animated fade in → 4-6s hold → fade out
- Player can dismiss with any key (but auto-advances anyway)

**Integration points:**
- Warp transition hook (in `spacegame/engine/transitions.py` or equivalent) fires banter engine
- Banter engine checks eligibility, selects, displays
- History logged to Player state

### Sub-sprint breakdown

**CB-1: Trigger engine + model** (~2 days)
- Define models.
- BanterEngine eligibility + selection logic.
- Save/load of banter_history.

**CB-2: Display layer** (~1-2 days)
- Subtitle renderer during warp.
- Speaker color from portrait.
- Fade animation + dismiss handling.
- Integration into warp transition.

**CB-3: Destination banter authoring** (~2 days)
- ~20 destination-specific entries.
- Per companion × per significant destination (Haven's Rest, Breakstone, Axiom Labs, Nexus Prime, Crimson Reach).
- Each entry 2-4 lines.

**CB-4: Crew pair banter** (~2 days)
- ~15 crew-pair entries.
- 6 pairs (Tomas×Marcus, Tomas×Priya, Tomas×Elena, Marcus×Priya, Marcus×Elena, Priya×Elena).
- 2-3 entries per pair.

**CB-5: Flag-triggered banter** (~1-2 days)
- ~10 entries triggered by specific events:
  - Post Act-One completion (crew reflects)
  - Post Arna arc (each branch gets appropriate reaction)
  - Post first customs inspection
  - Post first black market trade
  - etc.

**CB-6: Combat-aftermath + idle banter** (~1-2 days)
- ~5 combat-after entries (first fight with companion, heavy damage, easy win, etc.)
- ~10 idle-chatter entries (random eligible, low weight)

**CB-7: RC integration** (~1 day)
- ~10 rival-aware entries (CB × RC).
- Triggered on entering rival territory or just-escaped-rival.

**CB-8: Ship log menu** (~1 day)
- New menu entry: "Ship Log"
- Lists all heard banter chronologically.
- Filterable by speaker.

**CB-9: Tests + polish** (~1 day)
- Model round-trips.
- Eligibility test cases.
- Writing Bible compliance on all banter.
- Playtest pass: tune frequency, catch any tonal misfires.

### Testing strategy

- **Unit:** BanterEntry + BanterTrigger round-trips.
- **Unit:** eligibility evaluation for various game states.
- **Integration:** banter fires during warp transition.
- **Integration:** cooldown prevents repeat within window.
- **Content integrity:** every speaker_id resolves to a known crew member.
- **Writing Bible:** banter.json in compliance scanner.
- **Character voice:** per-speaker tests verify voice consistency (tone keywords per character).

### Acceptance criteria

- [ ] BanterEngine selects correctly per game state.
- [ ] ~50+ banter entries authored across all trigger types.
- [ ] Display is non-blocking, auto-dismissing.
- [ ] Ship log menu shows history.
- [ ] All banter passes Writing Bible + voice compliance.
- [ ] Frequency tuned to ~1 per 3 jumps average (player playtest).
- [ ] Test count growth: +~40-60 tests estimated.

### Risks

- **Frequency tuning.** Too frequent = noise, too rare = forgotten. → Start at 1-in-3, adjust from playtest. Banter engine exposes frequency config.
- **Voice drift.** Authoring 50+ entries invites tonal inconsistency. → Per-character test: banter flagged against voice sheet keywords.
- **Trigger overlap.** Multiple banters eligible could fire repeatedly. → Weighted selection + cooldown enforced per entry.

---

## Cross-cutting concerns

### Writing Bible scanner extension

New content files added to `tests/test_writing_bible_compliance.py` scan list:
- `data/combat/captains.json`
- `data/combat/rivals.json`
- `data/combat/complications.json`
- `data/dialogue/combat_hails.json`
- `data/dialogue/banter.json`
- `data/progression/timed_threads.json`

Each addition must pass:
- No em-dashes
- No AI tells ("couldn't help but," "a testament to," parallel-negation cadence)
- Per-character voice consistency (for banter)

### Dialogue integrity scanner extension

`tests/test_data/test_dialogue_integrity.py` existing tests extend to cover:
- Captain dialogue ids resolve.
- Rival dialogue prefixes resolve.
- Banter speaker_ids resolve.
- Timed thread touch_triggers are valid flags.
- No orphan flags introduced by new content.

Any flag set by a new phase goes to its phase's `KNOWN_PRODUCER_ONLY_ORPHANS` contribution if applicable.

### Save/load compatibility

Each phase introduces new models with save state:
- NV: none (editorial only).
- CE: encounter definitions extended — back-compat via optional fields.
- TW: timed_thread_state — new Player field, default `{}` for old saves.
- RC: rival_states, rival_history — new Player fields, default `{}` / `[]` for old saves.
- CB: banter_history — new Player field, default `[]` for old saves.

Save version bump at start of RC (first major schema change). Migrations in `save_manager.from_dict` where needed.

Full save/load round-trip test for each new model.

### Test discipline

TDD cadence per sub-sprint:
1. Write failing test(s) for the feature.
2. Implement minimum code to pass.
3. Refactor for clarity.
4. Add integration test at sub-sprint completion.
5. Full suite green before commit.

Test count targets per phase:
- NV: +15-25 tests (compliance + expansion cross-refs)
- CE: +40-50 tests
- TW: +20-30 tests
- RC: +80-100 tests
- CB: +40-60 tests

Arc total test growth: ~195-265 tests.

### Achievements + progression integration

Opportunity to add achievements that thread through the arc:
- **"Nemesis"** — defeat a rival at grudge 5.
- **"Negotiator"** — resolve 5 encounters via non-combat choices (CE).
- **"Slow and Steady"** — complete a run where every soft deadline is beaten.
- **"Ship Comfortable"** — hear 50 banter entries.
- **"They Called You By Name"** — trigger a captain's defeat-line five times with different captains.

Add to `data/progression/achievements.json` at phase completion, not in-phase (avoids scope creep).

---

## Risks + mitigations summary

| Risk | Phase | Mitigation |
|------|-------|------------|
| Editorial voice drift | NV | Compliance tests run on every commit |
| Scope creep CE → RC | CE | Mandatory `is_recurring=False` for CE captains |
| "Moderate" violation | TW | Balance checkpoint mid-phase; every drift state reviewed |
| Ship balance in grudged rivals | RC | Tier scales with player level, not grudge count alone |
| Save/load edge cases | RC | Dedicated state-combination test suite |
| Banter frequency | CB | Configurable, tuned from playtest |
| Content authoring fatigue | RC, CB | Phased authoring (4 rivals per batch, 10 banter entries per batch) |
| Cross-phase integration bugs | All | Integration tests at phase boundaries |

---

## Timeline + milestones

```
Week 1-2     [NV-1 ... NV-8]                  →  NV SHIP
Week 3-5     [CE-1 CE-2 CE-3 CE-4 CE-5 CE-6]  →  CE SHIP
Week 6-7     [TW-1 TW-2 TW-3 TW-4 TW-5 TW-6]  →  TW SHIP
Week 8-10    [RC-1 ... RC-10]                 →  RC SHIP
Week 11-13   [CB-1 ... CB-9]                  →  CB SHIP
```

**After each SHIP milestone:** arc is in a committable, shippable state. Stop here if priorities shift.

**Dist regeneration:** after each phase ships.

---

## Implementation sequence — Day 1

The first concrete step when execution begins:

1. Create `tools/nv_audit.py`:
   ```python
   # Walk data/dialogue/dialogues.json
   # For each response option, identify if it's skill-gated
   #   - required_flags contains a skill-derived flag (e.g., knows_*, _revealed)
   #   - or has explicit skill_tag field
   # Emit CSV: dialogue_id, node_id, response_text, inferred_skill, current_grade (manual), word_count
   ```
2. Run the audit, commit the output as `requirements/nv_audit_findings.md`.
3. Grade the catalog manually (A/B/C/D per response).
4. NV-2 rewrite sprint begins on the D-graded lines first, C next.

This approach means we start with DATA before we start rewriting. We never guess the scope.

---

## Definition of "arc complete"

- [ ] All 5 phases shipped to criteria above.
- [ ] Full test suite green (target: ~7,820+ tests after all phases).
- [ ] Writing Bible compliance clean across all new content.
- [ ] Dialogue + data integrity clean.
- [ ] Save/load round-trip tested for all new models.
- [ ] Dist regenerated and verified post-arc.
- [ ] `requirements/living_universe_arc.md` closing addendum documenting what shipped vs. plan.

---

## Closing note

This arc is where Aurelia graduates from "content-complete narrative space RPG" to "universe that breathes." Each phase is smaller than the Shipbuilder Upgrade or Skill Tree Overhaul arcs, but together they change the game's texture. The game won't have more features after this arc — it'll have more *presence*.

Ship quality over speed. No phase merges until its acceptance criteria are fully met.
