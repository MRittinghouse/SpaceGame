# SA-PREP-2: Existing-Data Audit Findings

**Sprint**: SA-PREP-2 (Existing-data audit)
**Produced**: 2026-04-26
**Scope**: 10 unique-typed Station Anchor locations plus the Cargo Broker character (11 subjects total)

This document catalogs existing references to the ten Station Anchor locations and the Cargo Broker character across Aurelia's current content surfaces. It establishes the asymmetric content baseline that downstream SA sprints inherit. It provides per-anchor reference inventories, NPC lists, gap analyses, a regression checklist, and a save-state baseline for post-arc comparison.

---

## Methodology

Content surfaces searched:

- `data/galaxy/locations.json` for the 10 unique-typed anchor location cards
- `data/characters/npcs.json` for NPCs with `home_system_id` matching each anchor's host system
- `data/dialogue/dialogues.json` for dialogue trees (7,630 lines; 396 KB; audited for direct location_id string matches via grep and for NPC dialogue tree IDs via npcs.json cross-reference)
- `data/missions/missions.json`, `data/missions/side_missions.json`, `data/missions/crew_quests.json` for mission references
- `data/journal/entries.json`, `data/journal/travel_log_templates.json` for journal references
- `data/economy/news_templates.json` for anchor-specific news templates
- `data/encounters/` (11 files, approximately 523 KB total) for anchor location ID and system references
- `data/crew/station_chatter.json` (1,238 lines) and `data/crew/ambient_dialogue.json` (1,326 lines) for crew/chatter references
- `requirements/character_voices.md` for named NPC voice-sheet cross-reference (SA-PREP-1 deliverable)
- `spacegame/` codebase for sub-faction, membership, and reputation model structures

**Key finding (affects all 11 subjects):** No unique anchor location_id string (e.g., `nexus_financial_exchange`, `crimson_wreckers_guild`) appears in any encounter file, dialogue tree node, news template, station chatter line, or ambient dialogue line. All indirect references reach anchors via the host system_id or via NPCs whose `home_system_id` matches the anchor's system. The unique location cards are currently cosmetic: they exist in `locations.json` but are not mechanically referenced from any other data source.

---

## Cross-Cutting Summary Table

Reference counts include indirect linkages (speaker home, system_id match). Direct location_id references in non-location sources: zero for all 11 subjects.

| Subject | Location ID | System | Dialogue (NPC speaker home) | Missions | Journal | Encounter | Chatter/Ambient | News | Content State |
|---|---|---|---|---|---|---|---|---|---|
| Meridian Financial Exchange | nexus_financial_exchange | nexus_prime | 7 NPCs | 0 anchor-level | 0 | 0 | Yes (system) | 0 | Lore-only |
| Stellaris Auction House | stellaris_auction_house | stellaris_port | 4 NPCs | 1 side | 0 | 0 | Yes (system) | 0 | Lore-only |
| The Deep Shafts | breakstone_deep_mines | breakstone | 4 NPCs | 2 main + 1 side | 2 | 0 | Yes (system) | 0 | Has content (system-level) |
| Restricted Sector 7 | iron_depths_restricted_zone | iron_depths | 3 NPCs | 2 main + 1 side + 1 crew | 1 | 0 | Yes (system) | 0 | Has campaign content |
| Okafor Institute Medical Wing | axiom_research_wing | axiom_labs | 3 NPCs | 3 main + 2 side + 1 crew | 2 | 0 | Yes (system) | 0 | Has campaign content |
| Restricted Research Wing | nova_restricted_labs | nova_research | 3 NPCs | 1 main + 2 side + 1 crew | 0 | 0 | Yes (system) | 0 | Has campaign content |
| Alliance Congress Hall | havens_congress_hall | havens_rest | 4 NPCs | 2 side | 1 | 0 | Yes (system) | 0 | Lore-only |
| Mayors' Council Chamber | verdant_mayors_council | verdant | 5 NPCs | 2 side | 0 | 0 | Yes (system) | 0 | Lore-only |
| Wreckers' Guild Hall | crimson_wreckers_guild | crimson_reach | 2 NPCs | 1 main + 2 side | 1 | 0 | Yes (system) | 0 | Has content (system-level) |
| Assembly Core | fulcrum_core | the_fulcrum | 3 NPCs | 2 main + 3 side | 1 | 0 | Yes (system) | 0 | Has campaign content |
| Cargo Broker (SA-V) | delivery_merchant | nexus_prime | 1 NPC | 1 main | 1 | 0 | N/A | 0 | Has content |

**Notes on linkage types used in this table:**

- *Speaker home*: NPC has `home_system_id` matching the anchor's host system; the NPC has a dialogue tree, but the tree does not reference the anchor's `location_id` by string.
- *System_id match*: A mission, journal entry, or other source uses the host system's `id` (e.g., `axiom_labs`) to reference the anchor's location. The specific unique location_id does not appear.
- *In-text name match*: The anchor's common name (e.g., "Iron Depths," "Malia Torres," "Breakstone") appears as a literal string in content text.
- *Flag chain*: A dialogue flag gates content associated with the anchor.
- *Encounter note*: All 11 encounter files searched. Zero references to any unique location_id. The file `data/encounters/system_specific.json` (81 KB) likely contains system-level encounter content for several anchor host systems, but uses system_id references.
- *News note*: `data/economy/news_templates.json` uses `{faction}` and `{system}` placeholder syntax. No anchor-specific templates exist; news is dynamically filled from game state.

---

## Anchor Sections

---

### 1. Meridian Financial Exchange

**Location ID**: `nexus_financial_exchange` | **System**: `nexus_prime` | **Content state**: Lore-only

The location card exists in `data/galaxy/locations.json`. No other content source references this card by its `id`. All nexus_prime content links to the system, not the Exchange specifically. The Cargo Broker character (SA-V) resides at nexus_prime and is cataloged separately in Section 11.

#### Existing References

**`data/galaxy/locations.json#nexus_financial_exchange`** (location card; linkage type: location definition):
Description: "The Expanse's financial heart. Commodity futures, shipping contracts, and insurance policies change hands by the second." Flavor text: "Numbers scroll across floor-to-ceiling displays. Fortunes are made and lost between lunch and dinner." No mechanical linkage beyond the card itself.

**`data/characters/npcs.json` (speaker home at nexus_prime; linkage type: speaker home):**
- `data/characters/npcs.json#delivery_merchant` (Cargo Broker, Trade Courier; audited separately in Section 11) dialogue_id: `merchant_delivery`
- `data/characters/npcs.json#dex_halloran` and variants (Information Broker; dialogue trees present)
- `data/characters/npcs.json#elena_reeves` (Navigator; core crew character)
- `data/characters/npcs.json#officer_larsen` (Customs Officer)
- `data/characters/npcs.json#sgt_mossa` (Dock Security; title: dock_investigator)
- `data/characters/npcs.json#neve_osei` (Data Broker)
- `data/characters/npcs.json#arna` (Dockmaster)

**`data/crew/station_chatter.json`** (linkage type: system_id match; 16+ lines at nexus_prime):
Themes: commodity futures activity ("futures on purified crystal are up three points"), customs irregularities, Commerce Exchange atmosphere ("holographic price tickers streaming overhead"). The Exchange is not named directly; chatter establishes nexus_prime's financial district feel.

#### Named NPCs Operating Here

Cargo Broker (delivery_merchant), Dex Halloran (+ dex_tunnel_contact / dex_final_lead variants), Elena Reeves (crew), Officer Larsen, Sgt. Mossa / dock_investigator, Neve Osei, Arna.

Note: Dr. Priya Osei (`dr_priya_osei`) also has `home_system_id: nexus_prime` in `data/characters/npcs.json`, but is cataloged under Section 5 (Okafor Institute / axiom_labs) as her narrative operating context.

The Meridian Financial Exchange itself has no named resident NPC assigned in current data. The Cargo Broker is thematically adjacent but is not framed as an Exchange employee.

#### Gaps for Downstream Sprints

**What exists:** A lore-only location card with atmosphere text. Several system-level nexus_prime NPCs and chatter establish the financial district feel without touching the Exchange specifically.

**What SA-F1 and SA-F3 must add:** A named, voiced Meridian Broker NPC (distinct from the Cargo Broker) with dialogue trees. A futures contract terminal UI. Recurring market-specialist contacts. The Cargo Broker graduation moment connecting SA-V to SA-F.

**What must be preserved:** All existing nexus_prime NPCs and chatter lines. The Cargo Broker (`delivery_merchant`) NPC entry and `iron_delivery` mission flow (see Section 11). The `nexus_financial_exchange` location card's description and flavor text as the atmospheric baseline.

---

### 2. Stellaris Auction House

**Location ID**: `stellaris_auction_house` | **System**: `stellaris_port` | **Content state**: Lore-only

The location card exists. No content references this location_id directly. One side mission (`the_forgery`) is set at stellaris_port and involves an art-dealing NPC, providing the only indirect anchor-adjacent content at this system.

#### Existing References

**`data/galaxy/locations.json#stellaris_auction_house`** (location card; linkage type: location definition):
Description: "Rare goods, antiquities, and items of uncertain provenance find new owners here. Cash only, no questions asked." Flavor text: "A Core System painting goes for 50,000 credits. The buyer doesn't blink."

**`data/missions/side_missions.json#the_forgery`** (linkage type: system_id match):
Available at stellaris_port. Involves Cassiel Maren (Art Dealer) and an artifact appraisal plot. Does not reference the Auction House location_id. Thematically adjacent.

**`data/characters/npcs.json` (speaker home at stellaris_port; linkage type: speaker home):**
- `data/characters/npcs.json#cassiel_maren` (Cassiel Maren, Art Dealer; dialogue_id: `cassiel_maren_forgery`)
- `data/characters/npcs.json#rudo_kamara` (Rudo Kamara, Art Appraiser)
- `data/characters/npcs.json#suki_tannenbaum` (Suki Tannenbaum, Maintenance Chief)
- `data/characters/npcs.json#elena_archives_npc` (Elena Reeves variant, Navigator)

**`data/crew/station_chatter.json`** (linkage type: system_id match; 15+ lines at stellaris_port):
Themes: art auction results ("The Kerensky collection sold for eight thousand. The buyer didn't even inspect in person"), luxury goods scarcity, promenade atmosphere with sandalwood scent. One line references a historical auction. The Auction House is not named.

#### Named NPCs Operating Here

Cassiel Maren (Art Dealer), Rudo Kamara (Art Appraiser), Suki Tannenbaum (Maintenance Chief). Elena Reeves appears as a context variant at stellaris_port.

No Auctioneer NPC exists in data. SA-B3 must create one from scratch.

#### Gaps for Downstream Sprints

**What exists:** A lore-only auction house card. An art-forgery side mission and art-adjacent NPCs at stellaris_port that establish the aesthetic of wealth and provenance disputes. Station chatter reinforces the auction-culture atmosphere.

**What SA-B1 and SA-B3 must add:** A named Auctioneer NPC with full voice sheet, scheduled auction events every 5-7 game-days, 6-8 lot categories, 3-5 recurring rival bidder NPCs, pre-auction preview, post-auction social moments.

**What must be preserved:** The forgery side mission and Cassiel Maren's dialogue (`cassiel_maren_forgery`). Rudo Kamara and the other stellaris_port NPCs. The chatter lines establishing luxury and art-market atmosphere.

---

### 3. The Deep Shafts

**Location ID**: `breakstone_deep_mines` | **System**: `breakstone` | **Content state**: Has content (system-level)

The location card exists. No content references this location_id directly. Breakstone system has substantial mission and NPC coverage including Marcus Jin (core crew) and Oren Tak. The Uprising history and Sora Takahashi are referenced in the location card's flavor text and in station chatter, making this the most historically seeded lore-only location.

#### Existing References

**`data/galaxy/locations.json#breakstone_deep_mines`** (location card; linkage type: location definition + in-text name match):
Description: "The oldest mining tunnels in Breakstone. Section 3 preserves the cargo bay where the Uprising began." Flavor text: "The walls here are scarred with a century of drill marks. A bronze plaque marks where Sora Takahashi spoke. Miners still leave flowers." (In-text name match: Sora Takahashi, the Uprising.)

**`data/missions/missions.json#the_favor_returned`** (linkage type: system_id match):
References Breakstone tunnels. Ground mission objective: "Navigate the Breakstone tunnels." `ground_mission_id: mission_13_breakstone_tunnels`; `ground_mission_system_id: breakstone`.

**`data/missions/side_missions.json#the_long_shift`** (linkage type: system_id match):
Available at breakstone. Ground mission in breakstone tunnels (`side_long_shift`). Narrative involves a cave-in on Level 14.

**`data/characters/npcs.json` (speaker home at breakstone; linkage type: speaker home):**
- `data/characters/npcs.json#marcus_jin` (Marcus Jin, Mining Foreman; core crew character)
- `data/characters/npcs.json#hanna_voss` (Hanna Voss, Dock Boss)
- `data/characters/npcs.json#oren_tak` (Oren Tak, Retired Miner)
- `data/characters/npcs.json#britt_vasara` (Britt Vasara, Miner)
- `data/characters/npcs.json#lira_feng` (Lira Feng, Union Safety Inspector)

**`data/journal/entries.json#auto_m05_marcus`** (linkage type: flag chain):
Trigger flag: `met_marcus_jin`. System: breakstone. Records meeting Marcus Jin.

**`data/journal/entries.json#auto_m13_oren`** (linkage type: flag chain + in-text name match):
Trigger flag: `oren_revealed_base`. Text: "Oren Tak in Breakstone's mining tunnels." (In-text name match: Breakstone.)

**`data/crew/station_chatter.json`** (linkage type: system_id match + in-text name match; 16+ lines at breakstone):
Themes: shift culture ("Second shift just clocked in. Someone's whistling the old Shaft 7 ballad"), union safety regulations, historical resonance. Key line: "Someone's chalked 'SORA WAS RIGHT' on the bulkhead near Shaft 12. Again." (In-text name match: Sora.)

#### Named NPCs Operating Here

Marcus Jin (Mining Foreman, core crew), Hanna Voss (Dock Boss), Oren Tak (Retired Miner), Britt Vasara (Miner).

Note: The audit originally listed Lira Feng (Union Safety Inspector) here, but her `home_system_id` in `data/characters/npcs.json` is `forgeworks`, not `breakstone`. She is a Forgeworks-based contact and does not operate at this anchor.

No Deep Shafts caretaker or pilgrim NPC exists. SA-2 must author the caretaker ("Old Sten" or equivalent) from scratch. Marcus Jin's connection to his father at the Deep Shafts is referenced in the arc vision but not in current NPC data or dialogue.

#### Gaps for Downstream Sprints

**What exists:** A breakstone system with two mission references (tunnels, cave-in), a retired miner NPC, and atmospheric chatter that references Sora Takahashi and the Uprising. The location card's flavor text establishes the memorial character of the Deep Shafts.

**What SA-2 must add:** A first-visit scripted scene specific to the breakstone_deep_mines card. Sora Takahashi historical journal entries (multi-entry arc). A voiced caretaker NPC (voice sheet required). Marcus Jin dialogue gated on visiting this specific location. Faction reputation grant on first visit. Recurring miner's blessing mechanic.

**What must be preserved:** Marcus Jin NPC and all crew dialogue. Oren Tak NPC and his current mission involvement. All chatter lines referencing Sora Takahashi and the Uprising (especially "SORA WAS RIGHT"). Journal entries `auto_m05_marcus` and `auto_m13_oren` and their flag gates.

---

### 4. Restricted Sector 7

**Location ID**: `iron_depths_restricted_zone` | **System**: `iron_depths` | **Content state**: Has campaign content

The location card exists. The iron_depths system has direct campaign mission content including `iron_depths_investigation`. This is one of the better-integrated non-Fulcrum anchors, with in-text system-name matches across multiple missions.

#### Existing References

**`data/galaxy/locations.json#iron_depths_restricted_zone`** (location card; linkage type: location definition):
Description: "DCMC has quietly increased patrols around this sector. The official reason is 'geological instability.'" Flavor text: "Warning beacons flash at the perimeter. Whatever's in there, DCMC doesn't want you seeing it."

**`data/missions/missions.json#the_favor_returned`** (linkage type: in-text name match + system_id match):
"deep tunnels near Iron Depths: a sealed facility running Guild freight codes." References iron_depths by name. Reward flag: `hidden_facility_discovered`.

**`data/missions/missions.json#iron_depths_investigation`** (linkage type: system_id match + in-text name match):
"Travel to Iron Depths and infiltrate the hidden Guild facility." `ground_mission_system_id: iron_depths`. Reward flag: `singularity_weapon_discovered`.

**`data/missions/side_missions.json#deep_core_whispers`** (linkage type: system_id match + in-text name match):
Available at iron_depths. "The night shift at Iron Depths has been hearing things." `ground_mission_id: side_deep_core`; `ground_mission_system_id: iron_depths`. Reward flag: `ancient_chamber_discovered`.

**`data/missions/crew_quests.json#elena_wreck_meridian`** (linkage type: system_id match):
"Travel to Iron Depths and investigate the Meridian wreck site." `target_id: iron_depths`.

**`data/characters/npcs.json` (speaker home at iron_depths; linkage type: speaker home):**
- `data/characters/npcs.json#sienna_vek` (Sienna Vek, Systems Engineer)
- `data/characters/npcs.json#jez_okafor` (Jez Okafor, Shift Supervisor)
- `data/characters/npcs.json#naveen_prakash` (Naveen Prakash, Compliance Auditor)

**`data/journal/entries.json#auto_m14_scan`** (linkage type: flag chain + in-text name match):
Trigger flag: `pirate_base_confirmed`. Text: "Located a pirate command base near Iron Depths." (In-text name match: Iron Depths.)

**`data/crew/station_chatter.json`** (linkage type: system_id match; 16+ lines at iron_depths):
Themes: DCMC extraction target revisions, safety board dismissals of worker concerns, Sora echoes ("Someone's chalked 'SORA WAS RIGHT' on the bulkhead near Shaft 12"). Directly supports the restricted-zone secrecy narrative.

#### Named NPCs Operating Here

Sienna Vek (Systems Engineer), Jez Okafor (Shift Supervisor), Naveen Prakash (Compliance Auditor).

These three are supporting-cast roles in campaign missions, not recurring SA anchor contacts. None appear in SA-PREP-1's primary voice-sheet registry as arc characters.

#### Gaps for Downstream Sprints

**What exists:** Active campaign mission content involving iron_depths. DCMC tension and restricted-zone atmosphere in chatter. Three local NPCs. Flags `hidden_facility_discovered`, `singularity_weapon_discovered`, `ancient_chamber_discovered`.

**What SA-0 must add:** Verification that SL-1 conditional demotion and SL-3 mission-objective elevation surface Restricted Sector 7 correctly during campaign beats. An optional depth tier for between-campaign-beat visits (intelligence opportunities, faction-specific narrative beats, espionage flavor).

**What must be preserved:** All three existing missions (`the_favor_returned`, `iron_depths_investigation`, `deep_core_whispers`) and their flag chains. The `elena_wreck_meridian` crew quest. All three local NPCs. The chatter atmosphere establishing DCMC secrecy.

---

### 5. Okafor Institute Medical Wing

**Location ID**: `axiom_research_wing` | **System**: `axiom_labs` | **Content state**: Has campaign content

The location card exists. Axiom Labs is the most mission-integrated anchor, with six total references across main missions, side missions, and crew quests. Dr. Priya Osei (core crew) homes here, making this the best-seeded anchor for SA downstream work.

#### Existing References

**`data/galaxy/locations.json#axiom_research_wing`** (location card; linkage type: location definition + in-text name match):
Description: "Dr. Okafor's legacy: 'Knowledge that does not heal is knowledge wasted.'" Flavor text references the bronze plaque and active research. (In-text name match: Dr. Okafor.)

**`data/missions/missions.json#the_scholars_errand`** (linkage type: system_id match):
"Transport Dr. Priya Osei to Axiom Labs." `target_id: axiom_labs`. Reward flag: `visited_axiom_labs`.

**`data/missions/missions.json#embassy_visit`** (linkage type: system_id match):
"Travel to Axiom Labs to attend the faction summit." `target_id: axiom_labs`. Reward flag: `attended_embassy_summit`.

**`data/missions/missions.json#the_ledger`** (linkage type: system_id match):
"Bring the Convergence data to Dr. Osei at Axiom Labs for verification." `target_id: axiom_labs`.

**`data/missions/side_missions.json#blight_season`** (linkage type: system_id match):
`target_id: axiom_labs` (acquire restricted pesticide).

**`data/missions/side_missions.json#the_scholars_dilemma`** (linkage type: system_id match):
Available at axiom_labs.

**`data/missions/side_missions.json#lab_rat`** (linkage type: system_id match):
Available at axiom_labs. `available_after: recruit_scientist` (flag chain).

**`data/missions/crew_quests.json#priya_retracted_paper`** (linkage type: system_id match):
"Travel to Axiom Labs and help Priya retrieve her research paper." `target_id: axiom_labs`. Crew member: `dr_priya_osei`.

**`data/characters/npcs.json` (speaker home at axiom_labs; linkage type: speaker home):**
- `data/characters/npcs.json#priya_analyst` and `data/characters/npcs.json#embassy_summit_host` (Dr. Priya Osei, Research Director / Summit Chairperson; core crew)
- `data/characters/npcs.json#axiom_researcher` (Dr. Senn Hadid, Junior Researcher)
- `data/characters/npcs.json#axiom_test_coordinator` (Lani Okoro, Field Testing Coordinator)

**`data/journal/entries.json#auto_m06_priya`** (linkage type: flag chain):
"Transported Dr. Priya Osei to Axiom Labs." Trigger: `the_scholars_errand` completion.

**`data/journal/entries.json#auto_m11_summit`** (linkage type: flag chain):
"Attended faction summit at Axiom Labs." Trigger: `attended_embassy_summit` flag.

**`data/crew/station_chatter.json`** (linkage type: system_id match; 15+ lines at axiom_labs):
Themes: grant review season pressure, citation competition between departments, intellectual territorial dynamics.

#### Named NPCs Operating Here

Dr. Priya Osei (Research Director / core crew), Dr. Senn Hadid (Junior Researcher), Lani Okoro (Field Testing Coordinator).

"Dr. Okafor" is named in the location card but has no NPC entry in `data/characters/npcs.json`. The SA-R arc's "Dr. Okafor's successor" is a new character to be authored.

#### Gaps for Downstream Sprints

**What exists:** The most mission-seeded anchor. Flags `visited_axiom_labs` and `attended_embassy_summit` set by existing content. Core crew member Priya homes here. Okafor name-check in the location card.

**What SA-R1 and SA-R2 must add:** A named, voiced successor to Dr. Okafor (new NPC, voice sheet required). 8-12 active research project templates with rotating availability. A researcher sub-cast (3-5 NPCs). Collaboration and risk systems. The ethics arc from SA-R2.

**What must be preserved:** All six existing mission references and their flag chains. Dr. Priya Osei NPC entries and crew quest. The location card description including the Okafor quote. The `visited_axiom_labs` and `attended_embassy_summit` flags and all content that gates on them.

---

### 6. Restricted Research Wing

**Location ID**: `nova_restricted_labs` | **System**: `nova_research` | **Content state**: Has campaign content

The location card exists. Nova Research has four mission references and three local NPCs, all in supporting campaign roles. Unlike Restricted Sector 7, none of these missions use the restricted-wing card as a primary narrative goal.

#### Existing References

**`data/galaxy/locations.json#nova_restricted_labs`** (location card; linkage type: location definition):
Description: "Entire sections of Nova are off-limits. Armed guards, biometric locks, and persistent rumors about what's inside." Flavor text: "A researcher hurries past with a sealed container. She doesn't make eye contact. The guard watches you watch her."

**`data/missions/missions.json#cargo_lost`** (linkage type: system_id match + in-text name match):
"The last three Guild convoys to Nova Research never arrived." `target_id: nova_research`. `forced_encounter: cargo_lost_distress`.

**`data/missions/side_missions.json#the_scholars_dilemma`** (linkage type: system_id match):
`target_id: nova_research`. "Deliver the data to Nova Research for verification."

**`data/missions/side_missions.json#signal_from_the_deep`** (linkage type: system_id match):
Available at nova_research. Signal amplifier deployment mission.

**`data/missions/crew_quests.json#priya_peer_review`** (linkage type: system_id match):
"Travel to Nova Research for the review board hearing." `target_id: nova_research`. Crew member: `dr_priya_osei`.

**`data/characters/npcs.json` (speaker home at nova_research; linkage type: speaker home):**
- `data/characters/npcs.json#reva_sato` (Captain Reva Sato, Guild Convoy Escort)
- `data/characters/npcs.json#nova_researcher` (Dr. Yuki Tanaka, Signal Analyst)
- `data/characters/npcs.json#amara_okonkwo` (Dr. Amara Okonkwo, Collective Research Partner)

**`data/crew/station_chatter.json`** (linkage type: system_id match; 15+ lines at nova_research):
Themes: intellectual property quarantine, badge revocations ("A researcher was escorted out yesterday. Badge revoked on the spot. Nobody knows what she found. Nobody's asking."), access code changes. Secrecy culture well-established.

#### Named NPCs Operating Here

Captain Reva Sato (Guild Convoy Escort), Dr. Yuki Tanaka (Signal Analyst), Dr. Amara Okonkwo (Collective Research Partner).

#### Gaps for Downstream Sprints

**What exists:** Campaign-adjacent mission content at nova_research. Three supporting-cast NPCs. Chatter establishing pervasive secrecy culture.

**What SA-0 must add:** Verification that the Restricted Research Wing surfaces correctly during campaign beats per SL-1 and SL-3. An optional depth tier for between-campaign-beat visits (NAS intelligence opportunities, espionage flavor).

**What must be preserved:** `cargo_lost` and its forced encounter. `priya_peer_review` crew quest. `signal_from_the_deep` side mission. All three local NPCs.

---

### 7. Alliance Congress Hall

**Location ID**: `havens_congress_hall` | **System**: `havens_rest` | **Content state**: Lore-only

The location card exists. Haven's Rest has the lowest anchor-specific integration of the non-Cluster-A anchors. Two side missions are set at havens_rest but neither references the Congress Hall specifically. The four local NPCs are frontier and settlement characters, not political figures. One station chatter line references a "community council" in a way that loosely mirrors the Congress Hall's function.

#### Existing References

**`data/galaxy/locations.json#havens_congress_hall`** (location card; linkage type: location definition):
Description: "Where the Annual Congress meets. Delegates from every Alliance community come to argue, negotiate, and share meals." Flavor text: "The walls are covered in banners from every Alliance settlement. The table seats two hundred. The arguments can last longer than the dinners."

**`data/missions/side_missions.json#two_calls`** (linkage type: system_id match):
Available at havens_rest. No Congress Hall reference in objectives.

**`data/missions/side_missions.json#the_lost_registry`** (linkage type: system_id match):
Available at and target: havens_rest. No Congress Hall reference.

**`data/characters/npcs.json` (speaker home at havens_rest; linkage type: speaker home):**
- `data/characters/npcs.json#tomas_drifter` (Tomas Drifter, Frontier Scout; core crew)
- `data/characters/npcs.json#haven_refugee` (Soren Hadik, Refugee)
- `data/characters/npcs.json#dimi_torr` (Dimi Torr, Fishmonger)
- `data/characters/npcs.json#issa_kadeer` (Issa Kadeer, Refugee Coordinator)

**`data/journal/entries.json` (linkage type: flag chain)**:
`auto_m07_tomas_accepted` / `auto_m07_tomas_declined` reference meeting Tomas Drifter at Haven's Rest. No Congress Hall reference.

**`data/crew/station_chatter.json`** (linkage type: system_id match + in-text thematic match; 15+ lines at havens_rest):
Themes: community council debates about surplus allocation ("someone on the community council is already arguing about surplus allocation"), trading post activity, hydroponics bay atmosphere. The council reference is the closest existing thematic seed to political deliberation.

#### Named NPCs Operating Here

Tomas Drifter (Frontier Scout, core crew), Soren Hadik (Refugee), Dimi Torr (Fishmonger), Issa Kadeer (Refugee Coordinator).

No delegate NPCs, council representatives, or political figures currently exist in data for havens_rest. SA-P4 must author the full delegate cast from scratch.

#### Gaps for Downstream Sprints

**What exists:** A lore-only Congress Hall card. Two location-only side missions. Tomas Drifter (core crew) homes here. One community-council chatter line as a thin thematic seed.

**What SA-P1 and SA-P4 must add:** Named representatives from each Alliance settlement (voice sheets required), dispute templates for inter-settlement conflicts, annual Congress event structure with multi-session arcs, coalition-building gameplay, and integration with the broader Politics system built in SA-P2.

**What must be preserved:** Tomas Drifter NPC and all current mission involvement. `haven_refugee`, `dimi_torr`, `issa_kadeer` NPCs. The community character of Haven's Rest chatter. Both existing side missions.

---

### 8. Mayors' Council Chamber

**Location ID**: `verdant_mayors_council` | **System**: `verdant` | **Content state**: Lore-only

The location card exists. Verdant has no mission references specific to the Council Chamber. Two side missions are set at verdant but involve farmers and botanists. Station chatter contains one line that mirrors the Council Chamber's modernization-debate flavor text, making it the closest existing thematic seed for this anchor.

#### Existing References

**`data/galaxy/locations.json#verdant_mayors_council`** (location card; linkage type: location definition + in-text detail):
Description: "The most organized governing body in the Alliance. Where Verdant's uncomfortable success gets debated." Flavor text: "Minutes from the last session are posted on the wall. The agenda item 'modernization proposal' has been tabled for the fourth time." (In-text detail: modernization proposal, fourth tabling.)

**`data/missions/side_missions.json#blight_season`** (linkage type: system_id match):
`target_id: verdant` (return restricted pesticide to farmer). No Council reference.

**`data/missions/side_missions.json#the_heirloom_seeds`** (linkage type: system_id match):
`target_id: verdant` (deliver seeds). No Council reference.

**`data/characters/npcs.json` (speaker home at verdant; linkage type: speaker home):**
- `data/characters/npcs.json#verdant_farmer` (Orin Halstead, Farmer)
- `data/characters/npcs.json#verdant_botanist` (Dr. Amara Okonkwo, Botanist)
- `data/characters/npcs.json#bren_solvay` (Bren Solvay, Grain Trader)
- `data/characters/npcs.json#chandra_osei` (Chandra Osei, Field Researcher)
- `data/characters/npcs.json#rhea` (Rhea, Agri Hub Receiver)

**`data/crew/station_chatter.json`** (linkage type: system_id match + in-text thematic match; 15+ lines at verdant):
Themes: yield records, modernization debates. Key line: "The modernization debate is heating up again. Half the council wants automated planters, the other half wants tradition." (In-text thematic match: modernization debate, council.) This line directly echoes the Council Chamber flavor text.

#### Named NPCs Operating Here

Orin Halstead (Farmer), Dr. Amara Okonkwo (Botanist), Bren Solvay (Grain Trader), Chandra Osei (Field Researcher), Rhea (Agri Hub Receiver).

No Mayor NPC or named council delegate currently exists in data. The chatter's "council" mention is atmospheric with no linked NPC. SA-P3 must author the Mayor and delegate cast from scratch.

#### Gaps for Downstream Sprints

**What exists:** A lore-only Council Chamber card. Five agricultural NPCs with no political roles. One chatter line mirroring the modernization debate. Two side missions anchored in farming disputes that could serve as political dispute source material.

**What SA-P1 and SA-P3 must add:** A Mayor NPC (council chair; voice sheet required), 3-5 named delegate NPCs (voice sheets required), 8-12 dispute templates, multi-session arc structure, and integration with the Politics system from SA-P2.

**What must be preserved:** All five existing Verdant NPCs and their current mission roles. `blight_season` and `the_heirloom_seeds` side missions. The specific chatter line about the modernization debate (preserve wording as a continuity anchor for SA-P3 delegate dialogue).

---

### 9. Wreckers' Guild Hall

**Location ID**: `crimson_wreckers_guild` | **System**: `crimson_reach` | **Content state**: Has content (system-level)

The location card exists. Malia Torres is named in the location card's flavor text and is present in NPC data at crimson_reach. The main campaign mission `the_crimson_run` delivers the player to Malia Torres specifically, making this the best-seeded Cluster B anchor for named-NPC-to-location linkage.

#### Existing References

**`data/galaxy/locations.json#crimson_wreckers_guild`** (location card; linkage type: location definition + in-text name match):
Description: "The only structure resembling authority in Crimson Reach. Safety standards, dispute mediation, and a shared database of derelict locations." Flavor text: "Malia Torres's reputation keeps the peace better than any law could. The derelict map on the wall is worth more than most ships." (In-text name match: Malia Torres.)

**`data/missions/missions.json#the_crimson_run`** (linkage type: system_id match + in-text name match):
"Deliver Dex's data chip to Malia Torres." `target_id: crimson_reach`. `ground_mission_system_id: crimson_reach`. (In-text name match: Malia Torres.)

**`data/missions/side_missions.json#wrenchs_request`** (linkage type: system_id match + in-text name match):
Available at crimson_reach. "Torres doesn't ask for much. This time she's asking for three ship components." (In-text name match: Torres.)

**`data/missions/side_missions.json#honor_among_thieves`** (linkage type: system_id match):
Available at crimson_reach. Pirate captain retrieval mission.

**`data/characters/npcs.json` (speaker home at crimson_reach; linkage type: speaker home):**
- `data/characters/npcs.json#malia_torres` (Malia Torres, Salvage Boss; dialogue trees present)
- `data/characters/npcs.json#torres_memorial` (Malia Torres memorial variant, Salvage Specialist)
- `data/characters/npcs.json#pirate_captain` (Rook Salvai, Salvage Captain)

**`data/journal/entries.json#auto_m10_crimson`** (linkage type: flag chain + in-text name match):
"Delivered a package to Malia Torres at Crimson Reach." (In-text name match: Malia Torres, Crimson Reach.)

**`data/crew/station_chatter.json`** (linkage type: system_id match; 16+ lines at crimson_reach):
Themes: outlaw-hub atmosphere ("Don't ask names. Don't ask origins. Don't ask what's in the crates. You'll do fine here."), weapons prohibition, ambient suspicion, bartender evasiveness.

**`data/crew/ambient_dialogue.json`** (linkage type: in-text thematic mention):
One line: "The Wrecker's Guild fixed the atmospheric processor." Casual atmospheric mention; no mechanics.

#### Named NPCs Operating Here

Malia Torres (Salvage Boss / Salvage Specialist), Rook Salvai (Salvage Captain).

The `torres_memorial` NPC variant suggests a memorial or post-campaign state for Malia Torres. SA-1 should clarify whether this is a plot-endpoint state before designing her relationship arc to ensure continuity.

#### Gaps for Downstream Sprints

**What exists:** A well-seeded anchor. Malia Torres is named in the location card and present in NPC data. One main campaign mission delivers the player to her directly. Two additional side missions involve her or the crimson_reach system. One ambient line mentions the Guild by name.

**What SA-1 must add:** A salvage contract board (cleanup, recovery, escort-salvage, deep-derelict tiers). Wreckers' Guild membership tiers (apprentice, journeyman, master, separate from Crimson Reach faction rep). 2-3 secondary Wrecker NPCs as recurring contacts (wreck navigator, salvage engineer, debris-field cartographer). Failed contract consequences. Guild-member-only contract tier. Guild membership badge with mechanical implications. Full Malia Torres relationship arc with multiple dialogue gates.

**What must be preserved:** `the_crimson_run` mission and its delivery to Malia Torres. `wrenchs_request` side mission. Both Malia Torres NPC entries (`malia_torres` and `torres_memorial`). `auto_m10_crimson` journal entry and its flag gate.

---

### 10. Assembly Core

**Location ID**: `fulcrum_core` | **System**: `the_fulcrum` | **Content state**: Has campaign content

The location card exists. The Fulcrum is the campaign's climactic endpoint with two main missions and three side missions. It is the highest mission-count anchor and is categorically different from all others: it is a narrative endpoint rather than a recurring venue. SA-0 work here is a verification pass, not a content build.

#### Existing References

**`data/galaxy/locations.json#fulcrum_core`** (location card; linkage type: location definition + in-text detail):
Description: "The heart of The Fulcrum. Massive gravitational lensing arrays hang in zero-gravity assembly cradles, their curved surfaces gleaming under industrial floodlights. A warp gate frame dominates the far wall." Flavor text: "The scale is breathtaking. Each array is larger than your ship. And the warp gate behind them glows with a faint blue light, already powered, already waiting."

**`data/missions/missions.json#point_of_no_return`** (linkage type: system_id match + in-text name match):
"The Fulcrum. A decommissioned station in deep space where the Commerce Guild's Inner Ledger is assembling sixteen gravitational lensing arrays." `target_id: the_fulcrum`. `ground_mission_system_id: the_fulcrum`. Flags: `warp_gate_discovered`, `convergence_active`. (In-text name match: The Fulcrum.)

**`data/missions/missions.json#the_collapse`** (linkage type: system_id match):
"Fight through the Ledger blockade and escape through the warp gate." Flags: `escape_combat_survived`, `expanse_collapsed`.

**`data/missions/side_missions.json#counterfeit_concerns`** (linkage type: system_id match):
`target_id: the_fulcrum`.

**`data/missions/side_missions.json#the_informant`** (linkage type: system_id match):
Available at the_fulcrum.

**`data/missions/side_missions.json#honor_among_thieves`** (linkage type: system_id match):
`target_id: the_fulcrum`.

**`data/characters/npcs.json` (speaker home at the_fulcrum; linkage type: speaker home):**
- `data/characters/npcs.json#ren_castillo` (Ren Castillo, Freight Broker)
- `data/characters/npcs.json#callum_rhee` (Callum Rhee, Traveler)
- `data/characters/npcs.json#collapse_witness` (the_collapse_sequence dialogue NPC)

**`data/journal/entries.json#auto_m16_ledger`** (linkage type: flag chain + in-text name match):
"The pirate operation is funded by a rogue faction within the Commerce Guild. They call themselves The Ledger."

**`data/crew/station_chatter.json`** (linkage type: system_id match; 15+ lines at the_fulcrum):
Themes: military-grade security scanners at every junction, civilian unease, surveillance culture ("The corridors are too clean. Too quiet. Whatever happens here, they don't want witnesses.").

#### Named NPCs Operating Here

Ren Castillo (Freight Broker), Callum Rhee (Traveler), collapse_witness (endpoint NPC with `the_collapse_sequence` dialogue).

#### Gaps for Downstream Sprints

**What exists:** The most mission-integrated anchor, serving as the campaign's climactic endpoint. Five missions plus critical flag chains for the narrative's conclusion.

**What SA-0 must add:** Verification that SL-1 conditional demotion and SL-3 mission-objective elevation surface the Assembly Core correctly during its campaign beats. An optional depth tier for between-campaign-beat visits (intelligence opportunities, espionage potential).

**What must be preserved:** `point_of_no_return` and `the_collapse` missions and their full flag chains (`warp_gate_discovered`, `convergence_active`, `escape_combat_survived`, `expanse_collapsed`). All three side missions. Ren Castillo, Callum Rhee, and the collapse_witness NPCs. `auto_m16_ledger` journal entry.

---

### 11. Cargo Broker (SA-V)

**NPC ID**: `delivery_merchant` | **Character name**: Cargo Broker | **System**: `nexus_prime` | **Content state**: Has content

The Cargo Broker is a character anchor, not a location anchor. Unlike the ten unique location cards, the Broker is a recurring NPC whose SA-V arc connects to Meridian in SA-F. The Broker currently has one mission, one journal entry, and a hide-after flag. They have no personal name in current data.

#### Existing References

**`data/characters/npcs.json#delivery_merchant`** (linkage type: direct NPC):
Name: "Cargo Broker." Title: "Trade Courier." `home_system_id: nexus_prime`. `dialogue_id: merchant_delivery`. `hide_after_flag: iron_delivery_failed`. The hide flag removes the Broker from the world if the player fails the delivery mission.

**`data/dialogue/dialogues.json#merchant_delivery`** (linkage type: direct NPC dialogue):
The Broker's dialogue tree ID is `merchant_delivery`. Tree content was not audited due to file size constraints (396 KB); confirmed by `npcs.json` reference.

**`data/missions/missions.json#iron_delivery`** (linkage type: direct NPC + in-text name match):
"A cargo broker at Nexus Prime needs ten units of iron ore moved to Forgeworks." Objective flag: `talked_to_cargo_broker`. Reward flag: `iron_ore_delivered`. (In-text name match: cargo broker, Nexus Prime.)

**`data/missions/side_missions.json#coolant_run` (arna_01)** (linkage type: system_id match):
Arna (Nexus Prime dockmaster) provides a similar cargo mission. Thematically adjacent; a distinct NPC, not the Broker.

**`data/journal/entries.json#auto_m02_delivery`** (linkage type: flag chain + in-text name match):
"Delivered 10 units of iron ore to Forgeworks for a cargo broker at Nexus Prime." Trigger flag: `talked_to_cargo_broker`. (In-text name match: cargo broker, Nexus Prime.)

**`data/characters/npcs.json#forgeworks_clerk`** (linkage type: mission chain):
Deshi Wren, "Intake Clerk, Cargo Broker" at forgeworks. The delivery destination for `iron_delivery`.

#### Named NPCs Operating Here

The Cargo Broker (delivery_merchant) at nexus_prime. Deshi Wren (forgeworks_clerk) is the receiving end of the Broker's current mission.

The Broker has no personal name in current data. SA-V must assign a canonical name (subject to the banned-names list from `requirements/character_voices.md`) and author a full voice sheet per SA-PREP-1 standards.

#### Gaps for Downstream Sprints

**What exists:** A functional introduction mission (`iron_delivery`) and NPC entry. One journal entry. One hide-after flag. The Broker is currently a single-encounter character whose name is a job title.

**What SA-V must add:** A personal name, voice sheet, and character history. Three-plus dialogue trees (introduction, ongoing, graduation). An investment introduction mission that sets `investment_introduced`. A narrative thread connecting the Broker to Meridian without destroying the existing `iron_delivery` mission flow.

**What must be preserved:** The `iron_delivery` mission and its flag chain (`talked_to_cargo_broker`, `iron_ore_delivered`, `iron_delivery_failed`). The `merchant_delivery` dialogue tree. The `auto_m02_delivery` journal entry. The `deshi_wren` intake clerk NPC at Forgeworks.

The `delivery_merchant` to `odom_broker` ID reconciliation is owned by SA-V. This audit flags it but does not act on it.

---

## Sub-Faction and Organization References

This section catalogs what currently exists in code and data for the membership and sub-faction concepts that SA-B-EXT-1 will extend. Catalog only; SA-B-EXT-1 owns the design.

### Wreckers' Guild Membership

**In data:**
The `crimson_wreckers_guild` location card and `wrenchs_request` side mission reference the Wreckers' Guild by name. One line in `data/crew/ambient_dialogue.json` (line 1229) reads: "The Wrecker's Guild fixed the atmospheric processor." Casual atmospheric mention; no mechanical definition.

**In code:**
A search across `spacegame/` returned zero classes, models, or methods related to guild membership, tier tracking, or organization standing for the Wreckers' Guild.

**Verdict:** The concept exists as lore only. SA-1 must build the membership system from scratch. SA-B-EXT-1 must provide the sub-reputation infrastructure that SA-1's membership tiers depend on. Design order: SA-B-EXT-1 before SA-1.

---

### Stellaris Auctioneer Relationship

**In data:**
The `stellaris_auction_house` location card and station chatter reference the auction house atmospherically. One chatter line mentions a historical auction result. No NPC with the title "Auctioneer" exists in `data/characters/npcs.json`. No relationship model, standing tracker, or bidder history exists anywhere in data.

**In code:**
Zero auction-related classes, relationship trackers, or standing models exist in `spacegame/models/`.

**Verdict:** Nothing exists. SA-B3 authors the Auctioneer NPC and SA-B2 implements the bidding core mechanics. Whether SA-B-EXT-1 is required for the Auctioneer relationship depends on whether SA-B2's bidding core carries rivalry state natively. Confirm during SA-B1 design.

---

### Meridian Broker Relationships

**In data:**
The `nexus_financial_exchange` location card describes Meridian as the Expanse's financial heart. The Cargo Broker (`delivery_merchant`) is at nexus_prime and is the narrative precursor to Meridian, but is not tagged as a Meridian employee or affiliate in current data.

**In code:**
`spacegame/models/investment.py` contains an investment system with 3 economic tiers per system. These tiers are not faction-standing-based; they are purely economic (credit/commodity return increments). No Meridian-specific classes exist. No futures contract stubs. No broker relationship model.

**Verdict:** The investment tier system exists but is not Meridian-linked. SA-F1 and SA-F2 must build the futures system from scratch. Whether to extend or replace the existing investment tiers is a design decision for SA-F1.

---

### Current Reputation Architecture

**`spacegame/models/faction.py`: `ReputationTier` enum:**
Five tiers: HOSTILE (below -50), UNFRIENDLY (-50 to -19), NEUTRAL (-19 to 19), FRIENDLY (20 to 49), ALLIED (50 and above). Tariff modifiers: +30% at HOSTILE, -20% at ALLIED.

**`spacegame/models/player.py`: `Player.faction_reputation`:**
A dict keyed by `faction_id` with numeric standing values. Methods: `modify_reputation()`, `get_reputation()`, `get_reputation_tier()`. One level of organization, one reputation value per faction. No sub-tiers, no per-organization layers, no membership hierarchy.

**`spacegame/models/player.py`: `Player.trade_permits`:**
A `set` of `faction_id` strings. Boolean access: a permit is held or it is not. No graduated access levels.

**`spacegame/models/social.py`: `SocialManager`:**
Per-NPC disposition (0 to 100, default 50). Used in dialogue skill checks. Operates independently of faction reputation. Could serve as a per-NPC relationship proxy but is not framed as organizational standing.

**Verdict for SA-B-EXT-1:** No sub-reputation infrastructure exists. The system must be designed and built from zero. The existing `faction_reputation` dict, `trade_permits` set, and `SocialManager` are the integration points SA-B-EXT-1 will extend or sit alongside. Save-load chain must be extended to persist sub-reputation state.

---

## Regression Checklist

The following six player-facing behaviors must survive all SA arc changes. Each is observable from normal play without log inspection or save-file editing.

**Behavior 1 (Cargo Broker / nexus_prime):**
A player who has completed `iron_delivery` (flags `talked_to_cargo_broker=True` and `iron_ore_delivered=True` set) should, on loading an existing save, see the Cargo Broker's post-delivery dialogue state rather than the initial delivery offer. The NPC should remain visible (hide_after_flag `iron_delivery_failed` was not triggered). The `auto_m02_delivery` journal entry should be present.

**Behavior 2 (Malia Torres / crimson_reach / Wreckers' Guild Hall):**
A player who has completed `the_crimson_run` (flag `met_malia_torres=True` set) should, on loading an existing save, see Malia Torres's post-meeting dialogue rather than her introductory state. The `auto_m10_crimson` journal entry should be present.

**Behavior 3 (Dr. Priya Osei / axiom_labs / Okafor Institute):**
A player who has completed `the_scholars_errand` (flag `visited_axiom_labs=True` set) should, on loading a save, find Dr. Priya Osei at Axiom Labs in the post-transport state. The `auto_m06_priya` journal entry should be present. If `attended_embassy_summit=True` is also set, `auto_m11_summit` should be present.

**Behavior 4 (Marcus Jin / breakstone / The Deep Shafts):**
A player who has met Marcus Jin (flag `met_marcus_jin=True` set) should, on loading a save, see the `auto_m05_marcus` journal entry recorded. On visiting Breakstone, Marcus Jin should be in his post-meeting state, not re-triggering his introduction.

**Behavior 5 (Restricted Sector 7 / iron_depths investigation):**
A player who has completed `iron_depths_investigation` (flag `singularity_weapon_discovered=True` set) should, on loading a save, find the investigation in its completed state. Subsequent visits to Iron Depths should not re-offer the investigation mission.

**Behavior 6 (Assembly Core / the_fulcrum campaign endpoint):**
A player who has completed `point_of_no_return` and `the_collapse` (flags `warp_gate_discovered=True`, `expanse_collapsed=True`, `escape_combat_survived=True` set) should, on loading a save, find the campaign in its post-collapse state. The Assembly Core should not re-offer resolved campaign objectives.

These six behaviors span five anchor locations (nexus_prime, crimson_reach, axiom_labs, breakstone, iron_depths, the_fulcrum) and three content types: NPC dialogue state, journal entry persistence, and mission completion state.

---

## Save-State Baseline

A procedural smoke-test recipe. Run this sequence before SA-1 begins and again after SA-1 is merged to verify no regression. Use a clean build from the last commit on `master` before SA-1 work starts. Note the build commit hash before testing.

### Prerequisites

- Fresh game install or `git clean` build
- At least 6 save slots available (slots 1 through 6 used)
- Note build commit hash

### Procedure

**Step 1: New game and Cargo Broker delivery (Checkpoint A)**

Start a new game in slot 1. Navigate to Nexus Prime. Locate the Cargo Broker NPC. Accept `iron_delivery`. Acquire 10 units of iron ore. Deliver to Deshi Wren (intake clerk) at Forgeworks. Return to Nexus Prime. Confirm the Cargo Broker shows a post-delivery dialogue state, not the initial delivery offer. Save to slot 2.

Expected flags set: `talked_to_cargo_broker`, `iron_ore_delivered`. Expected journal: `auto_m02_delivery`.

**Step 2: Breakstone and Marcus Jin (Checkpoint B)**

Continue from slot 2. Travel to Breakstone. Find and speak to Marcus Jin. Confirm the `auto_m05_marcus` journal entry appears. Save to slot 3.

Expected flag set: `met_marcus_jin`. Expected journal: `auto_m05_marcus`.

**Step 3: Axiom Labs transport (Checkpoint C)**

Continue from slot 3. Accept and complete `the_scholars_errand` (transport Dr. Priya Osei to Axiom Labs). Confirm `auto_m06_priya` journal entry appears. Confirm Dr. Priya Osei is present at Axiom Labs in the post-transport state. Save to slot 4.

Expected flag set: `visited_axiom_labs`. Expected journal: `auto_m06_priya`.

**Step 4: Crimson Reach and Malia Torres (Checkpoint D)**

Continue from slot 4. Accept and complete `the_crimson_run`. Speak to Malia Torres. Confirm `auto_m10_crimson` journal entry appears. Confirm Malia Torres shows post-meeting dialogue on subsequent interaction. Save to slot 5.

Expected flag set: `met_malia_torres`. Expected journal: `auto_m10_crimson`.

**Step 5: Reload and verify state persistence**

Quit the game entirely. Relaunch. Load slot 2 (Cargo Broker checkpoint). Verify: Cargo Broker shows post-delivery dialogue state (not initial offer). Load slot 3 (Breakstone checkpoint). Verify: Marcus Jin in post-meeting state, `auto_m05_marcus` journal entry present. Load slot 4 (Axiom Labs checkpoint). Verify: Dr. Priya Osei at Axiom Labs, `auto_m06_priya` journal entry present. Load slot 5 (Crimson Reach checkpoint). Verify: Malia Torres in post-meeting state, `auto_m10_crimson` journal entry present.

### Pass Criteria

All four load-and-verify steps above show the expected state without regression. If any NPC reverts to its initial state or any journal entry is absent after reload, the regression test fails. Record the slot number and the failing NPC or journal entry.

### Iron Depths and Fulcrum

Regression items 5 and 6 (iron_depths and the_fulcrum) require campaign progression to reach. Test these by loading a save with the relevant flags already set, then verifying NPC states and mission availability match the expected post-completion states. Do not run these as part of the quick smoke-test pass; reserve for full-campaign regression runs or targeted flag-injection tests.

---

*End of SA-PREP-2 audit findings.*
