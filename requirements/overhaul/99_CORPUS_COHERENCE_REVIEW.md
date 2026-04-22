# Corpus Coherence Review

> **Status:** v1 — conducted after the complete design corpus landed (17 design docs + 3 spike findings + prototype code). Reviews alignment across systems, identifies cross-cutting primitives, documents the identity architecture, catalogs integration opportunities, acknowledges gaps, and records the coherence edits applied.
>
> This doc is **not** a design doc. It's a consistency audit. When the Tier 2 docs disagree or the architecture is implicit, this doc makes the corrections explicit.

---

## Table of Contents

1. The identity architecture — the five-mapping pattern
2. Shared-primitive map
3. Cross-system integration opportunities
4. Consolidated implementation sequence
5. Content authoring budget
6. Voice coherence audit
7. Coherence edits applied
8. Acknowledged gaps (explicit out-of-scope)
9. Scope realism check
10. Recommendations for next phase

---

## 1. The identity architecture — the five-mapping pattern

The corpus's strongest accidental structure: **five factions × five activity systems × five identities** fall into a clean pattern.

| Faction | Activity system | Identity | Voice pivot from warm-industrial base |
|---|---|---|---|
| Commerce Guild | Trading (34) | **The Merchant** | + data-dense brutalism |
| Crimson Reach | Combat (30) | **The Captain** | + cinematic weight |
| Miners Union | Mining (32) | **The Prospector** | + solidarity labor |
| Frontier Alliance | Salvage (36) | **The Salvager** | + haunted archaeology |
| Science Collective | Refining (37) | **The Fabricator** | + craft precision |

**This is now canon** — formalized in Aesthetic Bible §10 v1.1.

### Three implications

**1. Identity depth asymmetry is deliberate, not accidental.** Combat and Trading are *primary* gameplay systems everyone engages with — they carry identity through UX/palette/encounters rather than authored campaigns. Mining, Salvage, Refining are *optional deep pools* — a player CHOOSES to specialize, earning authored narrative in exchange for that commitment.

**2. Pivot discipline is testable.** Future content additions can be tested: *does this pivot from, or contradict, the base warm-industrial voice?* The Bible §10.4 documents the limits per pivot direction.

**3. Cultural geography by work.** A player who inhabits all three optional identities has traversed Aurelia's cultural space — union-labor → frontier-archaeology → collective-craft. The game is not a linear story; it's a cultural space explored through chosen work.

### Coherence opportunity: cross-identity acknowledgment

Currently each identity exists in isolation. A Prospector master (Mining Ch5) gets no acknowledgment from NPCs outside mining. This is a 30-40 line authoring opportunity (discipline documented in Bible §10.3) that adds cross-identity tissue without scope expansion.

---

## 2. Shared-primitive map

Primitives defined in one doc and consumed across many. Making dependencies explicit prevents implementation drift.

### 2.1 Rendering primitives

| Primitive | Defined in | Consumed by |
|---|---|---|
| **SceneCamera** (renamed from ArenaCamera v1) | Combat §4.4 | Combat, Builder preview (§4.2), Builder test flight (§4.7), Galaxy jump cinematic (§4.1), Mining prestige cinematic (§8.4), Salvage module recovery (§4.7), Salvage cycle cinematic (§4.8), Station Hub docking cinematic (§4.10), Ground deployment/extraction (§6.6) — **9 consumers** |
| **ShipComposite** (rebuilt) | Framework §2 | Combat runtime (§4.1), Builder preview (§4.2), Builder test flight (§4.7), Salvage module recovery (§4.7), Station Hub docked-ship glimpse (§4.6) — **5 consumers** |
| **Hangar environment system** | Builder §4.1 | Builder (4 variants), Station Hub (5 faction variants — §4.1), Salvage (5 broker dockside environments — §8.6) — **3 systems, 14 variants total** |
| **Faction color overlay** | Bible §4.8 | Combat (enemy coding), Galaxy dominion overlay (§4.3), Trading glyphs (§4.3), Station Hub chrome (§4.6), Salvage broker affiliations (§7.2) — **5 consumers** |
| **Palette bands + role table** | Bible §2 | Every render across all 9 Tier 2 systems |
| **Material system with shade bands** | Bible §3 + Framework §4 | Every ship render, every module render |

### 2.2 UI primitives

| Primitive | Defined in | Consumed by |
|---|---|---|
| **Skill voice corner region** | UI Chrome §5.7 (canonicalized post-coherence) | Mining (§5.2), Salvage (§5.2), Refining (§5.2) — **3 identities, 15 distinct voices total** |
| **Journal surface family** | UI Chrome §5.6 (canonicalized post-coherence) | Mining Claim Ledger, Salvage Wrecker's Log, Refining Fabricator's Register, Ground Expedition Log — **4 surfaces** |
| **Thought cabinet** | Mining §5.3 (implicit pattern) | Mining (6 thoughts), Salvage (6 thoughts), Refining (4 thoughts) — **3 realizations, 16 total entries** |
| **News ticker** | Existing `news_ticker` model | Trading (§4.2), Station Hub (§4.4) — **2 systems** |
| **Badge / stamp / glyph system** | UI Chrome §7 | ~40 distinct badges introduced across 9 Tier 2 docs |
| **9-slice panel + card anatomy** | UI Chrome §5 | Every Tier 2 view |

### 2.3 Audio primitives

| Primitive | Defined in | Consumed by |
|---|---|---|
| **AudioManager** | Existing engine code | All SFX triggers across 15 active views |
| **9 SFX category taxonomy** | Audio §3.1 | All SFX emissions across Tier 2 systems |
| **Music orchestration rules** | Audio §5.1 | Every gameplay state transition |
| **Ambient scene mapping** | Audio §5.2 | Every scene (including 5 new faction-specific ambient variants) |
| **Per-Tier-2 audio cue catalog** | Audio §6 | Every audio integration point across 9 systems |

### 2.4 VFX primitives

| Primitive | Defined in | Consumed by |
|---|---|---|
| **ParticlePool + Particle** | Existing `particles.py` | All particle emission |
| **25-preset shared catalog** | VFX §3 | Every system's particle emission (no duplication) |
| **11 new proposed presets** | VFX §3.5 | Specific Tier 2 features (JUMP_STREAK, MODULE_RECOVERY_LIFT, etc.) |
| **Elemental particle vocabulary** | VFX §5 | Combat (5 elements) + Dual tech combinations (7 techs) |

---

## 3. Cross-system integration opportunities

Places where two or more Tier 2 systems naturally connect. Not all implemented in v1 — flagged for phasing decisions.

### 3.1 Economic chain (already alive in existing game; make visual)

```
Mining → Raw materials → Refining → Components → Ship Builder → Module install → Combat
                                                                                    ↓
                                                                                 Salvage → Recovered modules (circles back)
```

**Opportunity:** visually surface this chain. A crafted component in the Fabricator's Register shows its source ingredients (traceable back to mining session if applicable). A recovered module's origin wreck is tagged. An installed module's build history becomes part of the ship's story.

**Not v1 scope** — flagged for future polish.

### 3.2 Named character cross-references

| Character | Source system | Cross-reference opportunities |
|---|---|---|
| Augustyn Voss (mining mentor) | Mining §6.2 | Could mention Named Wrecks he worked years ago — bridges to Salvage §7.1 |
| Mattsen Holt (salvage broker) | Salvage §6.2 | Could reference Fabricator peers buying salvage — bridges to Refining §6.3 |
| Marta Beleń (Union organizer) | Mining §6.2 | Could appear at Union Hall in station hub — bridges to Station Hub §4.8 |
| Adisa Lark (refining commission client) | Refining §6.3 | Her firm might buy specific salvage types — bridges to Salvage §7.2 |
| Cesarine Marrot (salvage broker) | Salvage §7.2 | Military-grade specialist; could cross-reference Combat mission rewards |

**Each cross-reference is 1-3 lines of dialogue.** Total: ~30-40 lines added for cross-identity tissue across the whole corpus.

### 3.3 Faction event resonance

Galaxy map (§4.5 living-galaxy breathing) registers faction events. These should resonate across systems:

- Faction territory shift → station hub faction chrome updates (§35)
- Faction at war → combat encounters more frequent in contested space (§30)
- Faction embargo → trading market constraints (§34)
- Faction member death / dialogue → mini-game peer correspondence may reference (Fabricator correspondence archive)

**Most already implicitly supported by existing faction / event / news_ticker systems.** Surfacing them visually is where the integration opportunity lives.

### 3.4 Temporal event synchronization

**Unaddressed across docs.** Each system defines its own time-based events:

- Mining: prestige thresholds (internal clock)
- Salvage: Wrecker Cycles (~accumulated Standing)
- Refining: quarterly Expositions / Commissions / Rediscoveries (~90 in-game days)
- Station Hub: Union Convocation (quarterly; mentioned in mining doc)
- Galaxy Map: event tick (per game day)

**Coherence need:** a unified event calendar or at least a scheduling discipline to prevent all events clumping in the same week. Flagged for implementation-phase coordination; not scoped here.

### 3.5 Combat → Salvage bridge

Ground §5.2 and Salvage §7.4 both reference Hostile Recoveries — salvage sessions on combat wreckage. This is genuine cross-system integration:

- Combat destruction sequence leaves persistent debris
- Salvage system accepts "Hostile Recovery" initiation from that debris
- Recovered items include weapon-grade components unavailable elsewhere

**Implementation coordination required** between Combat Phase C1-C5 and Salvage Phase S5-S6.

### 3.6 Mining → Salvage via abandoned operations

Mining's optional Lost Claims (§7.3) reference abandoned mining operations. Salvage's Named Wrecks (§7.1) include an Old Mine entry. These are **the same fictional space** — a mining operation that failed becomes a salvage target.

**Coordination:** Salvage content authoring (~Phase S4-S5) can reference mining narratives from the same author pass, with names/dates consistent.

---

## 4. Consolidated implementation sequence

Dependency order extracted across all Tier 2 docs. The must-land-first list determines what blocks what.

### 4.1 Foundation phase (must ship before parallelizable work)

**Tier 1 foundation:**
1. Palette + material bands implementation (Bible §2) — blocks all render work
2. SceneCamera primitive (Combat §4.4, reused by 9 systems) — blocks Combat C1, Builder B1, Galaxy G2, Mining M2, Salvage S5, Station Hub H5, Ground GR3
3. ShipComposite rebuild (Framework §2) — blocks Combat C4, Builder B1, Salvage S5, Station Hub H5

**Tier 3 foundation:**
4. 11 new VFX presets (VFX §3.5) — blocks specific Tier 2 features (dual tech visuals, jump sequence, module recovery cinematic, mastery celebrations)
5. UI Chrome badge/stamp primitives (UI §7.3) — blocks trading stamps, mining mastery badges, ground afflictions, galaxy landmarks, etc.
6. Audio music/ambient orchestration wiring (Audio §5.1) — unlocks atmospheric gameplay feel across all systems

**Foundation phase total:** ~4-6 weeks concentrated engineering effort.

### 4.2 Visual-overhaul phase (parallelizable after foundation)

Once foundation is in place, most Tier 2 visual phases can proceed in parallel:

| Phase | Duration | Why parallelizable |
|---|---|---|
| Combat C1-C3 | ~3 weeks | Camera, VFX palette, arena entry — no cross-blocking |
| Builder B1-B3 | ~5 weeks | Hangar + preview + catalog + placement ghost |
| Galaxy G1-G3 | ~5 weeks | Zoom + jump cinematic + backdrop |
| Trading T1-T4 | ~6 weeks | Commodity rows + ticker + Market Intel Panel + stamps |
| Station Hub H1-H3 | ~5 weeks | Service badges + backdrops + faction chrome |

### 4.3 Identity-content phase (sequential authoring — narrative-heavy)

Narrative content is the big time consumer. Mining / Salvage / Refining mini-campaigns + Ground exploration content + cross-identity references.

| System | Duration | Content load |
|---|---|---|
| Mining M3-M5 (Prospector's Road + optional) | ~12-14 weeks | ~17.7k words authored |
| Salvage S3-S6 (Wrecker's Log + Brokers) | ~14-16 weeks | ~26.6k words authored |
| Refining F4 (Seasonal events + commissions) | ~3-4 weeks | ~24.5k words authored |
| Ground GR4-GR5 (NPC encounters + named) | ~7-8 weeks | ~26.5k words authored |

**Content phase total:** ~36-42 weeks if sequential; ~18-24 weeks if parallelized across multiple agents.

### 4.4 Polish phase

Combat C6 (background atmospheric), Builder B6, Galaxy G5 (landmarks), Station Hub H6 (neon-district), Mining M6, Salvage S7, Ground GR7. Several weeks of polish after identity content lands.

### 4.5 Total estimate

**~40-60 weeks of focused work**, depending on parallelization. Foundation is ~10% of total; visual-overhaul ~20%; content ~55%; polish ~15%. Content is the long pole.

---

## 5. Content authoring budget

### 5.1 Total word count commitment

| System | Words | Notes |
|---|---|---|
| Mining | 17,700 | 6 chapters + 5 skill voices + rivals + legendary seams + anomalies + thought cabinet |
| Salvage | 26,600 | 6 chapters + 5 brokers + 5 skill voices + named wrecks + artifacts + thought cabinet |
| Refining | 24,500 | Seasonal events + 48 commissions + correspondence + 5 skill voices + thought cabinet |
| Ground Exploration | 26,500 | Chapter encounters + 5 named encounters + expedition voice + terminals + afflictions |
| Combat | 2,000 | Dual tech names, element beats, cinematic scripts |
| Galaxy Map | 2,000 | Landmark labels, system descriptions, nebula region names |
| Station Hub | 3,000 | 150 additional chatter lines for visit-state + faction-specific |
| Ship Builder | 1,500 | Briefing text, confirm flavor, test flight script |
| Trading | 3,000 | Event flavor, permit text, Market Intel Panel copy |
| **Total** | **~106,800** | Novel's length |

### 5.2 Authoring constraints

All content must respect:
- `requirements/cultural_guide.md` — Aurelia's 2335 setting, faction voices
- `requirements/dialogue_writing_guide.md` — Writing Bible
- Banned NPC names: Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose
- GenAI-trope avoidance: no em-dashes, no "no X, no Y" constructions, no "testament to", no "couldn't help but"
- Voice-per-faction discipline

### 5.3 Pacing recommendation

At agent-assisted pace with user review, target **~2,000-4,000 words per week** sustained. That puts content completion at **6-14 months** if authored sequentially. Parallelizing across multiple agent workstreams (one agent per identity) could compress to **3-6 months**.

### 5.4 Content priority

If content must be cut or deferred:
1. **Core campaign chapters** (mining Ch1-5, salvage Ch1-5, ground chapter encounters) — essential
2. **Skill voices across 3 mini-games** — high ROI per line, preserves identity
3. **Named encounters and characters** — essential for identity
4. **Thought cabinet entries** — essential but small volume (~2,000 words total)
5. **Commission / rival / broker variants** — can scale per time available
6. **Optional tracks (legendary seams, anomalies)** — deferrable to post-launch
7. **Cross-identity acknowledgment lines** — small (~30-40 lines); ship with core content if possible
8. **Refining correspondence** — can scale incrementally
9. **Chapter 6 lore chapters** (mining, salvage) — highest deferrability

---

## 6. Voice coherence audit

Audited every Tier 2 doc against Bible §1 base voice ("warm-industrial grounded sci-fi with chunky palette-banded lighting, visible seams and wear, and legible faction identity — lived-in, hand-built, analog-future").

**Result: every Tier 2 doc serves the base voice.** Specific pivots per identity (Bible §10.4) inflect the register without contradicting it.

### Subtle tensions caught and documented:

**1. Refining's Fabricator** leans cleaner than warm-industrial baseline (postwar Japanese swordsmith / Bauhaus / Bell Labs references). Resolved by Bible §10.4 constraint: "Do not drift into sterile clean-room or minimalist-Apple; Aurelia's precision is craft-precision, not corporate-pristine." Current refining content satisfies this.

**2. Trading's brutalist-density** could drift toward cyberpunk if implementation isn't careful. Resolved by Bible §10.4 constraint: "Do not drift into cyberpunk-neon or hedge-fund-finance; Aurelia's commerce is data-dense but industrial-honest, not synthwave." Trading §2.3 explicitly rejects neon.

**3. Salvage's Ghost Channel skill voice** could drift toward Lovecraftian horror if lines aren't disciplined. Resolved by Bible §10.4 constraint: "Do not drift into gothic horror or Lovecraftian dread; Aurelia is weighted-industrial, not cosmic-alien." Salvage's content authoring (Phase S4-S5) must hold this line.

**4. Ground's Darkest Dungeon influence** is structurally imported (formation, resolve, afflictions); voice was deliberately NOT imported. Bible §10.4 Captain pivot: "cinematic weight comes from grounded consequence, not theatrical staging." Ground §2.2 tonal adjustments explicitly reject DD despair; current ground content satisfies.

---

## 7. Coherence edits applied

Targeted edits to existing docs to make implicit alignment explicit:

### 7.1 Bible §10 added (v1.1)

New section formalizing the five-identity architecture. Previously implicit across Tier 2 docs; now canonical.

### 7.2 Framework §2 ship_composite consumer enumeration

Five consumers listed explicitly (Combat, Builder ×2, Salvage, Station Hub) with API implications noted. Previously implicit.

### 7.3 Combat §4.4 SceneCamera rename

`ArenaCamera` renamed to `SceneCamera` with 9-system consumer list. Arena-specific states preserved as one flavor of the shared primitive. Previously implied combat-specific.

### 7.4 UI Chrome §5.6 journal surface family canonicalized

Four journal surfaces (Claim Ledger, Wrecker's Log, Fabricator's Register, Expedition Log) documented with shared anatomy + aesthetic differentiation. Previously each system reinvented.

### 7.5 UI Chrome §5.7 skill voice corner region canonicalized

Shared inner-voice UI component documented. Three mini-game identities consume same primitive with different voice content. Previously implied across three docs.

### 7.6 This document (99) created

Corpus coherence review as permanent record. Future design additions have a place to check alignment against the whole corpus.

---

## 8. Acknowledged gaps (explicit out-of-scope)

Honest call-outs of what is NOT integrated, and why:

### 8.1 No Trading or Combat mini-campaign

Combat and Trading don't get identity-treatment mini-campaigns. Conscious choice: they're primary gameplay, not optional deep pools. Identity accumulates through UX/palette/encounter content instead of authored campaigns.

### 8.2 No cross-game meta-campaign

Each identity's arc concludes within its own system. There is no grand cross-identity narrative ("complete all three mastery paths to unlock the secret ending"). This is deliberate — Aurelia's main campaign (Act One + future Acts) is the cross-system story; mini-game identities are parallel to it, not dependent on it.

### 8.3 No procedural identity content

All chaptered content is hand-authored. No procgen chapter generation. Contracts/procedural encounters use template systems with authored content.

### 8.4 No audio voiceover

Dialogue is text. Audio framework reserves voiceover channel for future; not in v1.

### 8.5 No shared temporal calendar

Mining's prestige, salvage's cycles, refining's expositions, ground's recovery, station hub's Union Convocation, galaxy events — unsynchronized. Flagged for implementation-phase coordination.

### 8.6 No cross-identity meta-progression

Completing Prospector + Salvager + Fabricator doesn't unlock anything mechanical. Worldbuilding reward only (accumulated character identity). Mechanical cross-reward deliberately excluded to avoid FOMO pressure.

### 8.7 No multiplayer consideration

Single-player throughout. No shared state, no co-op expeditions, no leaderboards.

### 8.8 Partial accessibility

§42 UI Chrome documents colorblind / keyboard / motion-reduction hooks. Implementation deferred. Full accessibility audit is post-v1.

---

## 9. Scope realism check

**Total implementation estimate: ~40-60 weeks** focused work, plus ~6-14 months content authoring (can parallelize).

For solo + agent development, this is **ambitious but not unrealistic**. The path:

1. **Foundation phase (~4-6 weeks)** lands SceneCamera + ShipComposite rebuild + palette + UI primitives. Single biggest unlock.
2. **Visual-overhaul phase (~14-20 weeks)** lands combat / builder / galaxy / trading / station hub polish. Parallelizable.
3. **Content phase (~24-40 weeks)** authors mini-game narratives. Can parallelize across multiple agent workstreams.
4. **Polish phase (~6-12 weeks)** lands legendary seams, anomalies, optional content.

**Risk areas:**

- **Content authoring discipline** — voice consistency across 100,000+ words is the single biggest risk. Requires close user review and possibly a dedicated content pipeline with voice-per-faction agents.
- **Cross-system integration coordination** — the more systems integrate, the more coordination overhead. Flagged throughout this doc.
- **Playtest-driven calibration** — many balance targets are proposals (quality variance probabilities, Resolve thresholds, etc.). Budget for playtest-and-tune cycles in each phase.

**Risk mitigation:**

- Ship foundation (Phase 1) and validate via a single Tier 2 implementation (e.g., Combat C1-C3) before committing to parallel phases
- Author ONE mini-campaign chapter in isolation first (e.g., Mining Chapter 1 "First Claim") to prove the content pipeline before scaling
- Content priorities (§5.4) provide a cut list if schedule compresses

---

## 10. Recommendations for next phase

### 10.1 Immediate next step

**Ship Combat Phase C1 (SceneCamera + pacing beats) as the foundation validation.** It's ~1 week of focused work, it unlocks 9 downstream systems, and it provides the first tangible proof that the design corpus produces real gameplay improvement. Low-risk, high-payoff, builds implementation momentum.

### 10.2 After C1 succeeds

**Phase foundation in earnest:**

1. Week 2-3: SceneCamera in production + pacing beats (Combat C1 extended)
2. Week 3-5: ShipComposite rebuild (Framework §2) with all five consumer APIs
3. Week 5-7: Palette + material band infrastructure (Bible §2 implementation)
4. Week 7-9: Core UI primitives (UI §7 badges + §5.6 journal + §5.7 skill voice)
5. Week 9-10: Audio orchestration wiring (Audio §5.1)

After Week 10, visual-overhaul phases can proceed in parallel across multiple systems.

### 10.3 After foundation

**Pilot content authoring with Mining Chapter 1.** ~2,000 words of the highest-priority content. Validates:
- Voice consistency under agent-assisted authoring
- Content pipeline (dialogue system integration, save persistence, journal entry rendering)
- User review cadence
- Estimated time-per-chapter

Use this pilot's data to calibrate the full content phase schedule.

### 10.4 Ongoing

**Keep this coherence review current.** When a Tier 2 phase ships, update the status here. When a new integration opportunity emerges, document it. When a gap is closed or deferred, mark it.

The design corpus is now static; the implementation will reveal drift; coherence review is a living document that prevents the drift from compounding.

---

*Revision history:*
- *v1 — corpus coherence review completed after all 17 Tier 0-3 docs landed. Five-identity architecture named; five targeted edits applied; cross-system primitive map documented.*
