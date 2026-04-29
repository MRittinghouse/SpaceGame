"""Centralized dialogue-flag name helpers.

Stability Initiative SI-1a. Prevents the "shop sets X, builder reads Y"
string-drift bug class (see requirements/stability_initiative.md).
Callers that touch these flags MUST import from this module instead of
building the strings inline.

Current scope: tutorial flags (the surface that caused the SI origin
bugs). SI-2 will backfill broader dialogue_flag usage with the same
pattern, gradually tightening the ``tests/test_compliance/`` flag
scanner as we go.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Tutorial
# ---------------------------------------------------------------------------


_TUTORIAL_BOUGHT_PART_PREFIX = "tutorial_bought_part_"


def tutorial_bought_part(part_id: str) -> str:
    """Flag set by ``tutorial_shop_view`` when the player buys a part.

    Read by ``ship_builder_view`` to know which tutorial parts are
    available for placement. The single source of truth for the flag
    name — prior drift (shop wrote ``tutorial_bought_part_X`` while
    builder read ``tutorial_bought_X``) caused two game-breaking
    crashes before this registry existed.
    """
    return f"{_TUTORIAL_BOUGHT_PART_PREFIX}{part_id}"


def extract_tutorial_bought_part_id(flag_name: str) -> Optional[str]:
    """Inverse of :func:`tutorial_bought_part`.

    Returns the ``part_id`` when ``flag_name`` is a tutorial-purchase
    flag, else ``None``. Consumers that iterate
    ``player.dialogue_flags`` looking for tutorial purchases go through
    this helper so the prefix lives in exactly one module.
    """
    if flag_name.startswith(_TUTORIAL_BOUGHT_PART_PREFIX):
        return flag_name[len(_TUTORIAL_BOUGHT_PART_PREFIX) :]
    return None


# ---------------------------------------------------------------------------
# Campaign mission milestones
# ---------------------------------------------------------------------------
#
# SI-3 Pass 3.3 (see requirements/si3_flag_registry_cookbook.md).
# Set in ``engine/game.py``'s mission-completion handler when the
# player crosses N total campaign-mission completions (N ∈ {5, 10,
# 15, 20}). Read by ``data/encounters/campaign.json`` via
# ``requires_flags`` to gate Act One milestone encounters.


def campaign_mission_milestone(n: int) -> str:
    """Flag set when the player crosses ``n`` total campaign completions.

    Producer: ``engine/game.py`` mission-completion handler.
    Consumers: ``data/encounters/campaign.json`` (multiple gates).
    Valid milestones today: 5, 10, 15, 20.
    """
    return f"completed_mission_{n}"


# ---------------------------------------------------------------------------
# NPC introductions ("met X")
# ---------------------------------------------------------------------------
#
# SI-3 Pass 3.3. Set when the player first encounters a named NPC, in
# either a dialogue choice (``set_flag`` in ``data/dialogue/dialogues.json``)
# or a view-side handshake (e.g., ``StationHubView`` for Arna).
# Consumed by mission ``requires_flags``, journal ``trigger_flag``,
# station chatter ``required_flags``, and a small number of code-side
# gates that branch on whether the player has met someone.


def met_npc(npc_id: str) -> str:
    """Flag set on first introduction to a named NPC.

    Producer: dialogue ``set_flag`` actions and a few view-side
    handshakes (e.g., :mod:`spacegame.views.station_hub_view`).
    Consumers: mission gates, journal triggers, station chatter, and
    code-side branches that vary content based on prior introductions.

    ``npc_id`` is the canonical NPC identifier, e.g. ``"marcus_jin"``,
    ``"arna"``, ``"malia_torres"``.
    """
    return f"met_{npc_id}"


# ---------------------------------------------------------------------------
# Conversation gates ("talked to X")
# ---------------------------------------------------------------------------
#
# SI-3 Pass 3.5. Set after a player completes a specific dialogue
# encounter. Distinct from ``met_npc`` — "met" fires on first contact,
# "talked_to" fires on a specific dialogue beat (e.g., the briefing
# the player needs to take before a mission unlocks). Some flags use
# the full NPC name (``talked_to_officer_larsen``) and others use a
# short alias (``talked_to_voss``); the helper accepts whatever id the
# producer site chose.


def talked_to_npc(npc_id: str) -> str:
    """Flag set after a player completes a specific dialogue beat with an NPC.

    Producer: ``engine/game.py`` (after dialogue completion handlers),
    plus dialogue ``set_flag`` actions in ``data/dialogue/dialogues.json``.
    Consumers: mission ``required_flags``, journal ``trigger_flag``,
    timed-thread ``touch_triggers``, and various code-side gates.

    ``npc_id`` is the conversation gate identifier — frequently the
    NPC id, but sometimes a short alias (e.g. ``"voss"``,
    ``"officer_larsen"``, ``"cargo_broker"``).
    """
    return f"talked_to_{npc_id}"


# ---------------------------------------------------------------------------
# Dual tech reveal flags
# ---------------------------------------------------------------------------
#
# SI-3 Pass 3.5. Set on first activation of a dual tech in combat to
# record that the cinematic reveal scene has played; subsequent
# activations skip it. ``models/dual_tech_dialogue.reveal_flag_key``
# now delegates to this helper to keep one canonical source of truth.


def dual_tech_revealed(tech_id: str) -> str:
    """Flag set when a dual tech's first-use cinematic has played.

    Producer: ``models/dual_tech_dialogue.check_and_mark_reveal``.
    Consumers: combat engine (gates whether to emit the scene), tests.
    """
    return f"dual_tech_{tech_id}_revealed"


# ---------------------------------------------------------------------------
# Investment introduction
# ---------------------------------------------------------------------------
#
# SL-2 (requirements/station_legibility.md). Set when the Cargo Broker
# introduces investment to the player. Read by
# ``models/station_salience.is_investment_unlocked`` to decide whether
# investment-typed location cards render in the station hub. The flag
# is one of two OR'd gates — the other is a credit threshold
# (``INVESTMENT_UNLOCK_CREDIT_THRESHOLD``). Either gate unlocks the cards.


def investment_introduced() -> str:
    """Flag set when the Cargo Broker introduces investment to the player.

    Producer: SL-2 introduction mission (Cargo-Broker dialogue beat,
    sets the flag via ``set_flag`` action). Threshold-only unlocks do
    NOT set this flag — a player who unlocks via credits never gets
    the introduction beat unless the mission also fires.

    Consumer: :func:`spacegame.models.station_salience.is_investment_unlocked`.
    """
    return "investment_introduced"


# ---------------------------------------------------------------------------
# Faction-first-dock orientation tip
# ---------------------------------------------------------------------------
#
# SL-5 (requirements/station_legibility.md). Set on first dock at each
# faction's territory after the player dismisses the orientation tip.
# Read by :class:`spacegame.views.station_hub_view.StationHubView` to
# decide whether to fire the tip on the current dock.
#
# Layout keys are the stable identifiers (guild / union / collective /
# frontier / reach) per ``SYSTEM_LAYOUT_MAP`` in
# ``spacegame.views.station_layouts``.


def seen_faction_tip(layout_key: str) -> str:
    """Flag set when the player has dismissed a faction's orientation tip.

    Producer: :class:`spacegame.views.station_hub_view.StationHubView`'s
    on-dismiss callback for the faction-first-dock tip overlay.

    Consumer: the same view's ``_maybe_show_faction_tip`` (gates the
    next-dock fire).

    ``layout_key`` is the canonical faction layout id (``"guild"``,
    ``"union"``, ``"collective"``, ``"frontier"``, ``"reach"``).
    """
    return f"seen_faction_tip_{layout_key}"


# ---------------------------------------------------------------------------
# Encounter "seen" markers (unique encounters fire once per playthrough)
# ---------------------------------------------------------------------------
#
# SI-3 Pass 3.5. Set after a unique encounter resolves so the random-
# selection pool drops it on subsequent travel rolls.


def encounter_seen(encounter_id: str) -> str:
    """Flag set after a unique encounter resolves.

    Producer: ``engine/game.py._apply_encounter_result`` (unique branch).
    Consumer: ``models/encounter._is_eligible`` (drops the encounter
    from the weighted-random pool once the flag is present).
    """
    return f"encounter_seen_{encounter_id}"


# ---------------------------------------------------------------------------
# SA-0 depth-tier intelligence beats (Cluster A anchors)
# ---------------------------------------------------------------------------
#
# SA-0 (requirements/roadmap/ROADMAP.md). One-shot per save: set when
# the player hears an insider intelligence beat at a Cluster A anchor
# during a between-campaign-visit. The flag gates re-display of the
# branch so the NPC does not repeat themselves on subsequent docks.
#
# Producers: ``data/dialogue/dialogues.json`` — response ``set_flag``
#   on the final node of the depth-tier branch.
# Consumers: ``data/dialogue/dialogues.json`` — ``excluded_flags`` on
#   the response that offers the branch, preventing re-entry once heard.
#   Also consumed by ``data/journal/entries.json`` via ``trigger_flag``
#   to auto-add the corresponding journal entry.


def heard_dcmc_intelligence() -> str:
    """Flag set when player hears Naveen Prakash's DCMC depth-tier beat.

    One-shot per save. Offered at iron_depths between campaign beats;
    suppressed once heard and whenever iron_depths_investigation is active.

    Producer: ``naveen_prakash_dialogue`` (dcmc_intelligence_reveal branch).
    Consumer: ``naveen_prakash_dialogue`` (excluded_flag gate on greet response),
        ``data/journal/entries.json`` (trigger_flag for auto_dcmc_intelligence).
    """
    return "heard_dcmc_intelligence"


def heard_nas_intelligence() -> str:
    """Flag set when player hears Yuki Tanaka's NAS depth-tier beat.

    One-shot per save. Offered at nova_research between campaign beats;
    suppressed once heard and whenever cargo_lost is active.

    Producer: ``yuki_signal_deep`` (nas_intelligence_reveal branch).
    Consumer: ``yuki_signal_deep`` (excluded_flag gate on start response),
        ``data/journal/entries.json`` (trigger_flag for auto_nas_intelligence).
    """
    return "heard_nas_intelligence"


# ---------------------------------------------------------------------------
# Wreckers' Guild Hall (SA-1)
# ---------------------------------------------------------------------------
#
# SA-1 (requirements/roadmap/ROADMAP.md). Flags scoped to the Wreckers'
# Guild Hall venue at Crimson Reach. Producers and consumers all live
# inside the SA-1 surface (view, dialogue, journal triggers); this
# section keeps the strings centralized so the SI-3 dialogue-integrity
# scanner can pair them without missing a typo.


def enrolled_wreckers_guild() -> str:
    """Flag set when the player joins the Wreckers' Guild at apprentice tier.

    Producer: :class:`spacegame.views.wreckers_guild_view.WreckersGuildView`
    on first conversation with Malia Torres at the Hall (also seeds
    ``Player.sub_reputation["wreckers_guild"] = 1``).
    Consumers: dialogue gates (greet vs enrollment branch),
    :func:`spacegame.engine.game.Game._drain_wreckers_sub_rep_queue`,
    journal ``trigger_flag`` for the apprentice arc.
    """
    return "enrolled_wreckers_guild"


def wreckers_promoted_tier(tier_id: str) -> str:
    """Flag set when the player crosses into a new Wreckers' Guild tier.

    Producer: :func:`spacegame.engine.game.Game._drain_wreckers_sub_rep_queue`
    after a :class:`spacegame.models.sub_reputation.SubReputationDelta`
    pushes the player into ``tier_id``. Set once per tier per save.
    Consumers: ``data/journal/entries.json`` (trigger_flag for the
    journeyman / master journal entries),
    :class:`spacegame.views.wreckers_guild_view.WreckersGuildView`
    (suppresses repeat promotion banners).

    ``tier_id`` is the snake_case identifier from
    :data:`spacegame.models.wreckers_guild.WRECKERS_GUILD_CONFIG`
    (e.g. ``"journeyman"``, ``"master"``).
    """
    return f"wreckers_promoted_{tier_id}"


def wreckers_made_up_apology() -> str:
    """Flag set after Malia's post-lockout make-up beat plays.

    Producer: :class:`spacegame.views.wreckers_guild_view.WreckersGuildView`
    when the player accepts Malia's make-up branch following a
    contract-failure lockout (see
    :class:`spacegame.models.wreckers_guild.WreckersGuildState`).
    Consumer: same view, gates re-enabling contract accepts. The flag
    fires once per save; subsequent failures rerun the lockout but do
    not re-fire the make-up beat.
    """
    return "wreckers_made_up_apology"


def seen_wreckers_guild_tip() -> str:
    """Flag set after the player dismisses the first-visit tip overlay.

    Producer: :class:`spacegame.views.wreckers_guild_view.WreckersGuildView`'s
    on-dismiss callback for the
    :class:`spacegame.views.first_time_tip.FirstTimeTipOverlay`.
    Consumer: the same view's first-entry guard. The PT-M overlay never
    re-fires once this flag is set.
    """
    return "seen_wreckers_guild_tip"


def wreckers_contract_completed() -> str:
    """Flag set the first time the player turns in a Wreckers' contract.

    Producer: :class:`spacegame.views.wreckers_guild_view.WreckersGuildView`
    contract turn-in flow.
    Consumer: ``data/journal/entries.json`` (trigger_flag for the
    first-completion entry). Subsequent completions never refire the
    journal entry because the journal manager dedupes by trigger_flag.
    """
    return "wreckers_contract_completed"


def wreckers_made_up_journal() -> str:
    """Flag set after the make-up beat resolves; gates the recovery journal entry.

    Producer: :class:`spacegame.views.wreckers_guild_view.WreckersGuildView`
    on the same code path as :func:`wreckers_made_up_apology`. Kept
    distinct so the journal entry can fire once even if the apology
    flag is loaded from a save written mid-beat.
    Consumer: ``data/journal/entries.json`` (trigger_flag for the
    failure-recovery entry).
    """
    return "wreckers_made_up_journal"


# ---------------------------------------------------------------------------
# Deep Shafts Memorial (SA-2)
# ---------------------------------------------------------------------------
#
# SA-2 (requirements/roadmap/ROADMAP.md). Flags scoped to the Deep Shafts
# memorial / pilgrimage venue at Breakstone. Producers and consumers all
# live inside the SA-2 surface (view, dialogue tree, mission, journal
# triggers); centralizing the strings here keeps the SI-3 dialogue-
# integrity scanner stable across producer / consumer pairs.


def visited_deep_shafts() -> str:
    """Flag set on first entry to the Deep Shafts memorial.

    Producer: :class:`spacegame.views.deep_shafts_view.DeepShaftsView`
    on first ``on_enter`` per save (also marks the scripted scene as
    played).
    Consumer: ``the_silent_shaft`` mission objective (``has_flag``);
    journal trigger gate; subsequent venue entries (visit-count math).
    """
    return "visited_deep_shafts"


def received_miners_blessing_first() -> str:
    """Flag set when the first-visit +5 Miners' Union rep grant fires.

    One-shot per save. Producer: :class:`spacegame.views.deep_shafts_view.DeepShaftsView`
    on first entry. Consumer: same view's pilgrimage-tick gate (the
    first-visit grant fires only when this flag is unset).
    """
    return "received_miners_blessing_first"


def talked_to_sten_brygaard() -> str:
    """Flag set after the player's first Sten Brygaard dialogue at the venue.

    Producer: ``data/dialogue/dialogues.json`` (``set_flag`` on Sten's
    first-meeting greeting node).
    Consumer: Marcus venue branches B and C (gating); subsequent Sten
    dialogue beats (``required_flags`` / ``forbidden_flags`` for the
    return greeting).
    """
    return "talked_to_sten_brygaard"


def seen_deep_shafts_tip() -> str:
    """Flag set after the player dismisses the first-visit tip overlay.

    Producer: :class:`spacegame.views.deep_shafts_view.DeepShaftsView`'s
    on-dismiss callback for the
    :class:`spacegame.views.first_time_tip.FirstTimeTipOverlay`.
    Consumer: the same view's first-entry guard. The PT-M overlay never
    re-fires once this flag is set.
    """
    return "seen_deep_shafts_tip"


# ---------------------------------------------------------------------------
# Okafor Institute (SA-R1)
# ---------------------------------------------------------------------------
#
# SA-R1 (requirements/roadmap/ROADMAP.md). Flags scoped to the Okafor
# Institute Medical Wing venue at Axiom Labs. Producers and consumers
# all live inside the SA-R1 surface (view, dialogue, journal triggers);
# centralizing the strings here keeps the SI-3 dialogue-integrity
# scanner stable across producer / consumer pairs.


def seen_okafor_tip() -> str:
    """Flag set after the player dismisses the first-visit tip overlay.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s
    on-dismiss callback for the
    :class:`spacegame.views.first_time_tip.FirstTimeTipOverlay`.
    Consumer: the same view's first-entry guard. The PT-M overlay never
    re-fires once this flag is set.
    """
    return "seen_okafor_tip"


def okafor_project_funded_first() -> str:
    """Flag set the first time the player funds an Okafor research project.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s fund flow.
    Consumer: ``data/journal/entries.json`` (trigger_flag for the
    first-funding entry). Subsequent fund actions never refire the
    journal entry because the journal manager dedupes by trigger_flag.
    """
    return "okafor_project_funded_first"


def okafor_project_completed_first() -> str:
    """Flag set the first time an Okafor project resolves to success.

    Producer: :func:`spacegame.engine.game.Game._tick_okafor_projects`
    when a project reaches its completion day with a successful roll.
    Consumer: ``data/journal/entries.json`` (trigger_flag for the
    first-completion entry).
    """
    return "okafor_project_completed_first"


def okafor_project_failed_first() -> str:
    """Flag set the first time an Okafor project resolves to failure.

    Producer: :func:`spacegame.engine.game.Game._tick_okafor_projects`
    when a project reaches its completion day with a failure roll.
    Consumer: ``data/journal/entries.json`` (trigger_flag for the
    first-failure entry).
    """
    return "okafor_project_failed_first"


def okafor_patent_disposed_first() -> str:
    """Flag set the first time the player licenses or sells a patent.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s IP
    disposition flow (fires on either license OR sell on the first
    disposition only).
    Consumer: ``data/journal/entries.json`` (trigger_flag for the
    first-disposition entry; one body covers either path).
    """
    return "okafor_patent_disposed_first"


def okafor_first_failure_seen() -> str:
    """Flag set after Kweon's first-failure debrief plays.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s failure
    debrief flow on the first failure encountered. Subsequent failures
    do not re-trigger the debrief.
    Consumer: same view's failure-debrief gate.
    """
    return "okafor_first_failure_seen"


def okafor_failure_debrief_shown() -> str:
    """Flag set after the player dismisses Kweon's first-failure debrief tree.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s Kweon
    dialogue dismiss handler — set when the failure-debrief branch ends.
    Consumer: same view's Kweon-routing guard. Once set, Kweon's button
    routes back to the ambient ``kweon_okafor_intro`` tree.
    """
    return "okafor_failure_debrief_shown"


def okafor_collaborator_share(researcher_id: str) -> str:
    """Flag set per researcher when the player team-funds with their slot.

    Producer: :class:`spacegame.views.okafor_view.OkaforView` when a
    project is accepted with that researcher in a collaborator slot.
    Consumer: SA-R2 narrative arc (Kweon's dialogue references which
    Institute staff the player has worked with). Listed in
    :data:`KNOWN_PRODUCER_ONLY_ORPHANS` until SA-R2 wires consumers.

    ``researcher_id`` is the snake_case speaker_id of the collaborator.
    """
    return f"okafor_collaborator_share_{researcher_id}"


# ---------------------------------------------------------------------------
# Cargo Broker (SA-V)
# ---------------------------------------------------------------------------
#
# SA-V (requirements/roadmap/ROADMAP.md). Flags scoped to Odom's investment-
# introduction arc at Nexus Prime. The speaker_id was renamed to odom_broker
# in this sprint; these helpers carry the producer/consumer documentation
# for the two new flags SA-V introduces.


def odom_explained_investment() -> str:
    """Flag set when the player exhausts Odom's investment_intro dialogue node.

    Producer: ``data/dialogue/dialogues.json`` — ``set_flag`` on the
    response that closes the ``investment_intro`` node in the
    ``merchant_delivery`` dialogue tree.
    Consumer: ``the_longer_ledger`` mission objective (``has_flag`` check
    against this flag fires the mission-complete reward, which sets
    ``investment_introduced``).
    """
    return "odom_explained_investment"


def seen_investment_tip() -> str:
    """Flag set when the player dismisses the first investment-card tip overlay.

    Producer: :class:`spacegame.views.station_hub_view.StationHubView`'s
    on-dismiss callback for the PT-M
    :class:`spacegame.views.first_time_tip.FirstTimeTipOverlay` fired on
    first click of any ``investment``-typed location card after
    ``investment_introduced`` is set.
    Consumer: the same view's first-click guard — the overlay never
    re-fires across the playthrough once this flag is set.
    """
    return "seen_investment_tip"


def pilgrimage_journal(n: int) -> str:
    """Flag set when the ``n``th Sora Takahashi journal entry unlocks.

    Producer: :class:`spacegame.views.deep_shafts_view.DeepShaftsView`
    on visit thresholds [1, 3, 5, 8, 12] with a ≥3-game-day spacing
    rule between consecutive unlocks.
    Consumer: ``data/journal/entries.json`` (``trigger_flag`` for
    ``pilgrimage_journal_<n>``).
    """
    return f"pilgrimage_journal_{n}"


def attended_silent_shaft() -> str:
    """Flag set on completion of ``the_silent_shaft`` mission.

    Producer: ``the_silent_shaft`` mission reward (``set_flag``).
    Consumer: future Act Two cascade (SA-X1 cross-anchor threading).
    Listed in :data:`KNOWN_PRODUCER_ONLY_ORPHANS` until SA-X1 wires a
    consumer.
    """
    return "attended_silent_shaft"


def marcus_silent_vigil_seen() -> str:
    """Flag set after Marcus's first-visit silent-vigil branch plays.

    Producer: ``data/dialogue/dialogues.json`` (``set_flag`` on the
    Marcus branch-A node).
    Consumer: Marcus branches B and C (gates the next-visit father-
    connection node so the silent vigil always lands first).
    """
    return "marcus_silent_vigil_seen"


def marcus_father_connection_seen() -> str:
    """Flag set after Marcus's father-as-Union-collegial branch plays.

    Producer: ``data/dialogue/dialogues.json`` (``set_flag`` on the
    Marcus branch-B node).
    Consumer: Marcus branch C (the Uprising-inheritance node gates on
    this flag so the arc lands in order).
    """
    return "marcus_father_connection_seen"


def marcus_uprising_inheritance_seen() -> str:
    """Flag set after Marcus's Uprising-inheritance branch plays.

    Producer: ``data/dialogue/dialogues.json`` (``set_flag`` on the
    Marcus branch-C node).
    Consumer: future Act Two cascade (SA-X1) and crew-banter (SA-X6).
    Listed in :data:`KNOWN_PRODUCER_ONLY_ORPHANS` until those land.
    """
    return "marcus_uprising_inheritance_seen"


# ---------------------------------------------------------------------------
# Politics venue (SA-P2)
# ---------------------------------------------------------------------------
#
# SA-P2 (requirements/sa_politics_design.md, sections 7.3 + 9.1). Outcome
# and tutorial flags for the venue-based dispute system. SA-P2 ships
# only the flag helpers; SA-P3 wires the FirstTimeTipOverlay calls and
# authors dispute templates that consume the outcome flags via
# ``required_flags`` / ``set_flag`` plumbing.


def dispute_resolved(dispute_id: str) -> str:
    """Flag set when a dispute reaches any final resolution.

    Fires for every outcome category (``win``,
    ``partial_win_coalition_thin``, ``partial_win_off_record``, ``loss``).
    Producer: :class:`spacegame.models.politics_dispute.PoliticsDisputeManager`
    when a dispute resolves.
    Consumers: SA-P3/P4/P5 mission ``required_flags`` / journal
    ``trigger_flag`` entries; future cross-anchor narrative threading.
    """
    return f"dispute_resolved_{dispute_id}"


def coalition_won(dispute_id: str) -> str:
    """Flag set when a dispute resolves as the full ``win`` outcome.

    Indicates a passing vote with at least 60 percent of the delegate
    roster pre-committed via corridor coalition-building. Distinguishes
    a coalition-built win from a thin-margin victory.
    Producer: :class:`spacegame.models.politics_dispute.PoliticsDisputeManager`.
    Consumers: SA-P3/P4/P5 mission and journal gates that key off a
    decisive coalition win specifically.
    """
    return f"coalition_won_{dispute_id}"


def dispute_mediated(dispute_id: str) -> str:
    """Flag set when a dispute resolves as ``partial_win_off_record``.

    Off-record concessions saved a failed vote: at least one delegate
    carried a ``conceded`` flag from a successful mediation when the
    final tally fell short.
    Producer: :class:`spacegame.models.politics_dispute.PoliticsDisputeManager`.
    Consumers: SA-P3/P4/P5 mission gates that depend on a mediated
    settlement; SA-X7 ``Council Mediator`` achievement seed.
    """
    return f"dispute_mediated_{dispute_id}"


def seen_politics_venue_tip() -> str:
    """Flag set after the player dismisses the politics-venue tip overlay.

    One-shot per save. Producer (SA-P3): the venue view's on-dismiss
    callback for the :class:`spacegame.views.first_time_tip.FirstTimeTipOverlay`
    fired on first venue entry. Consumer (SA-P3): the same view's
    first-entry guard. SA-P2 ships the helper so the SI-3 scanner can
    pair the producer / consumer when SA-P3 wires the overlay.
    """
    return "seen_politics_venue_tip"


def seen_argument_composer_tip() -> str:
    """Flag set after the player dismisses the argument-composer tip overlay.

    One-shot per save. Producer (SA-P3): the dispute view's on-dismiss
    callback for the composer-substate
    :class:`spacegame.views.first_time_tip.FirstTimeTipOverlay`. Consumer
    (SA-P3): the same view's composer-open guard. SA-P2 ships the helper
    so the SI-3 scanner can pair the producer / consumer when SA-P3
    wires the overlay.
    """
    return "seen_argument_composer_tip"


def seen_annual_congress_tip() -> str:
    """Flag set after the player dismisses the Annual Congress tip overlay.

    One-shot per save. Producer (SA-P4): the dispute view's on-dismiss
    callback for the Annual Congress tutorial overlay, fired only when
    the player enters the Haven's Rest dispute view for the first time.
    Consumer (SA-P4): the same view's Annual-Congress entry guard. The
    overlay explains that Congress meets once per game-year and that the
    coalition built before the floor opens determines the outcome —
    mechanic-essential rather than flavor.
    """
    return "seen_annual_congress_tip"


def seen_gray_market_arbitration_tip() -> str:
    """Flag set after the player dismisses the gray-market arbitration tip overlay.

    One-shot per save. Producer (SA-P5): the dispute view's on-dismiss
    callback for the Crimson Reach arbitration tutorial overlay, fired
    only when the player enters the Crimson Reach dispute view for the
    first time. Consumer (SA-P5): the same view's Reach-entry guard.
    The overlay explains the tier-based access model for the Guild floor.
    Read in two places (overlay gate AND dismissal callback) per the
    SA-P3/P4 LOCKED convention for tutorial flags.
    """
    return "seen_gray_market_arbitration_tip"


# ---------------------------------------------------------------------------
# Bidding venues (SA-B2)
# ---------------------------------------------------------------------------
#
# SA-B2 (requirements/sa_bidding_design.md, sections 9.1 + 9.4). Tutorial
# tip flag and crew-banter trigger flags for the auction system. SA-B2
# both produces and consumes the tip flag; the banter flags are produced
# by the auction lifecycle and consumed by SA-X6 crew banter content.


def seen_auction_first_session_tip() -> str:
    """Flag set after the player dismisses the first-auction tip overlay.

    One-shot per save. Producer: :class:`spacegame.views.auction_view.AuctionView`
    on-dismiss callback for the
    :class:`spacegame.views.first_time_tip.FirstTimeTipOverlay` fired on
    first entry to either auction venue. Consumer: the same view's
    first-entry guard. The overlay explains the ascending-bid format and
    the reserve-not-met outcome (see design doc §9.1).
    """
    return "seen_auction_first_session_tip"


def auction_first_session_complete() -> str:
    """Banter trigger: player completed their first auction session.

    Producer: :class:`spacegame.models.bidding.AuctionState` on
    SESSION_CLOSE for the first session in any venue. Consumer: SA-X6
    crew-banter content (not authored in SA-B2).
    """
    return "auction_first_session_complete"


def auction_first_win() -> str:
    """Banter trigger: player won their first lot at any auction venue.

    Producer: :class:`spacegame.models.bidding.AuctionState` on the first
    LOT_RESOLUTION where the player is the winning bidder. Consumer:
    SA-X6 crew-banter content; SA-X7 ``auction_first_win`` achievement.
    """
    return "auction_first_win"


def auction_rival_encountered(rival_id: str) -> str:
    """Banter trigger: a named rival appeared in the same session as the player.

    Fires once per rival per save. Producer:
    :class:`spacegame.models.bidding.AuctionState` on SESSION_OPEN for
    each named rival in the roster (Prentiss, Kade, Salko). Consumer:
    SA-X6 crew-banter content.

    ``rival_id`` is the canonical persona identifier (``"aldous_prentiss"``,
    ``"yuna_kade"``, ``"fenn_salko"``).
    """
    return f"auction_rival_{rival_id}_encountered"


def auction_first_rivalry_formed() -> str:
    """Banter trigger: first OUTCOME_OUTBID recorded against any named rival.

    Producer: :class:`spacegame.models.bidding.AuctionState` on the first
    LOT_RESOLUTION where a named rival outbids the player. Consumer:
    SA-X6 crew-banter content; SA-B2 journal trigger for the
    "[rival] Was There" entry.
    """
    return "auction_first_rivalry_formed"


def seen_first_velo_encounter() -> str:
    """Flag set the first time the player exchanges dialogue with Cassian Velo.

    SA-B3 (decision §B3.13). Producer: Velo's dialogue tree
    (``cassian_velo_main`` in ``data/dialogue/dialogues.json``) sets the
    flag via ``set_flag`` on the greeting node response.
    Consumer: ``data/journal/entries.json``
    (``trigger_flag`` for the ``auto_auction_first_velo_encounter``
    auto-entry). Subsequent dialogue exchanges do not re-fire the entry.
    """
    return "seen_first_velo_encounter"


def auction_sable_ceiling_correct() -> str:
    """Banter trigger: Sable's ceiling estimate was within 5% of the actual.

    Producer: :class:`spacegame.models.bidding.AuctionState` on
    SESSION_CLOSE when Sable is active and the per-rival ceiling estimate
    error is at or below 5% averaged across the session. Consumer: SA-X6
    crew-banter content.
    """
    return "auction_sable_ceiling_correct"


# ---------------------------------------------------------------------------
# Bidding venue: Crimson Reach Black Market (SA-B4)
# ---------------------------------------------------------------------------
#
# SA-B4 (requirements/sa_bidding_design.md, sections 1.4 + 4.5 + 9.4 + 9.5).
# One first-encounter flag for the Reach Floor Manager (Vex Tarn) and two
# banter trigger flags for the Reach session-and-contraband milestones.
# Producer locations: Floor Manager dialogue tree (set_flag actions) and
# the auction-state lifecycle hooks wired in ``engine/game.py``.
# Consumers: ``data/journal/entries.json`` auto-entries (today) and
# SA-X6 crew-banter content (later sprint).


def seen_first_floor_manager_encounter() -> str:
    """Flag set the first time the player exchanges dialogue with Vex Tarn.

    SA-B4 (decision §B4.5). Producer: the Floor Manager dialogue tree
    (``reach_floor_manager_main`` in ``data/dialogue/dialogues.json``)
    sets the flag via ``set_flag`` on the greeting node responses.
    Consumer: ``data/journal/entries.json``
    (``trigger_flag`` for the
    ``auto_auction_first_floor_manager_encounter`` auto-entry).
    Subsequent dialogue exchanges do not re-fire the entry.
    """
    return "seen_first_floor_manager_encounter"


def auction_first_reach_session() -> str:
    """Banter trigger: player completed (or entered) their first Reach session.

    Producer: :class:`spacegame.models.bidding.AuctionState` on
    SESSION_OPEN at the Reach venue, surfaced by the engine's
    ``_prepare_reach_session`` helper. Consumers: SA-X6 crew-banter
    content (later sprint) and the
    ``auto_auction_first_reach_session`` journal auto-entry.
    """
    return "auction_first_reach_session"


def auction_first_contraband_win() -> str:
    """Banter trigger: player won their first contraband lot at any Reach session.

    Producer: ``engine/game.py``'s ``on_lot_won`` callback when
    ``venue_id == "crimson_reach"`` and ``lot.category == "contraband"``.
    The flag is set after the legality penalty is applied so the journal
    auto-entry sees the post-penalty rep value.
    Consumers: SA-X6 crew-banter content (later sprint) and the
    ``auto_auction_first_contraband_lesson`` journal auto-entry.
    """
    return "auction_first_contraband_win"


# ---------------------------------------------------------------------------
# Player-initiated auctions (SA-B5)
# ---------------------------------------------------------------------------
#
# SA-B5 (requirements/sa_bidding_design.md, §11.11 same-engine commitment).
# One first-time tip flag and three banter trigger / journal trigger flags
# for the player-as-seller side of the Stellaris Auction House. Producers
# and consumers all live inside the SA-B5 surface (sell_lot_view,
# auction_state, engine/game callbacks); centralizing the strings keeps
# the SI-3 dialogue-integrity scanner stable across producer/consumer
# pairs even when the surface spans model + view + engine.


def seen_first_listing_tip() -> str:
    """Flag set after the player dismisses the first SellLotView tip overlay.

    One-shot per save. Producer:
    :class:`spacegame.views.sell_lot_view.SellLotView` on-dismiss callback
    for the :class:`spacegame.views.first_time_tip.FirstTimeTipOverlay`
    fired on first entry to the consignment screen. Consumer: the same
    view's first-entry guard — the tip explains that the listing fee is
    non-refundable and that the reserve is the player's "no thanks"
    floor (see locked decision §B5.11).
    """
    return "seen_first_listing_tip"


def auction_first_listing_created() -> str:
    """Banter / journal trigger: player consigned their first lot.

    Producer: :func:`spacegame.engine.game.Game._ensure_sell_lot_view`'s
    on-confirm callback (or the SellLotView's confirm path when running
    standalone). Set once per save on the first successful
    ``AuctionState.create_listing`` call. Consumers:
    ``data/journal/entries.json`` (``trigger_flag`` for the
    ``auto_auction_first_listing_created`` auto-entry) and SA-X6
    crew-banter content.
    """
    return "auction_first_listing_created"


def auction_first_sale() -> str:
    """Banter / journal trigger: a player-listed lot sold for the first time.

    Producer: :func:`spacegame.engine.game.Game._ensure_auction_view`'s
    ``on_player_lot_sold`` callback. Set once per save on the first
    player-seller resolution where the lot resolves with
    ``outcome="sold"``. Consumers: ``data/journal/entries.json``
    (``trigger_flag`` for the ``auto_auction_first_sale`` auto-entry)
    and SA-X6 crew-banter content.
    """
    return "auction_first_sale"


def auction_first_listing_withdrawn() -> str:
    """Banter / journal trigger: a player-listed lot was withdrawn at session.

    Producer: :func:`spacegame.engine.game.Game._ensure_auction_view`'s
    ``on_player_lot_withdrawn`` callback. Set once per save on the first
    player-seller resolution where the reserve is not met. Consumers:
    ``data/journal/entries.json`` (``trigger_flag`` for the
    ``auto_auction_first_listing_withdrawn`` auto-entry) and SA-X6
    crew-banter content.
    """
    return "auction_first_listing_withdrawn"


# ---------------------------------------------------------------------------
# Okafor legacy arc (SA-R2) — Dr. Okafor's Legacy Narrative Arc
# ---------------------------------------------------------------------------
#
# SA-R2 (requirements/roadmap/ROADMAP.md). Flags scoped to the ethics-in-
# research narrative thread that Dr. Kweon carries on top of SA-R1's project-
# patronage venue. Each flag is produced when the matching Kweon arc-beat
# dialogue tree closes in OkaforView; consumers are the view's routing guard,
# journal trigger_flag entries, and the optional mission gate.


def okafor_legacy_first_heal_seen() -> str:
    """Flag set when the player dismisses the first-heal arc-beat tree.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s
    ``_close_active_dialogue`` handler when the ``kweon_legacy_first_heal``
    tree closes.
    Consumers: ``OkaforView._kweon_dialogue_id()`` routing guard (beat
    must not repeat); ``data/journal/entries.json`` trigger_flag for the
    ``auto_okafor_legacy_first_heal`` entry.
    """
    return "okafor_legacy_first_heal_seen"


def okafor_legacy_first_profit_seen() -> str:
    """Flag set when the player dismisses the first-profit arc-beat tree.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s
    ``_close_active_dialogue`` handler when the ``kweon_legacy_first_profit``
    tree closes.
    Consumers: ``OkaforView._kweon_dialogue_id()`` routing guard (beat
    must not repeat); ``data/journal/entries.json`` trigger_flag for the
    ``auto_okafor_legacy_first_profit`` entry.
    """
    return "okafor_legacy_first_profit_seen"


def okafor_legacy_heal_pattern_seen() -> str:
    """Flag set when the player dismisses the heal-pattern arc-beat tree.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s
    ``_close_active_dialogue`` handler when the ``kweon_legacy_heal_pattern``
    tree closes.
    Consumers: ``OkaforView._kweon_dialogue_id()`` routing guard; mission
    ``required_flags`` gate for ``okafor_legacy_clinic_run`` (the optional
    heal-side delivery mission that becomes available after this beat).
    """
    return "okafor_legacy_heal_pattern_seen"


def okafor_legacy_profit_pattern_seen() -> str:
    """Flag set when the player dismisses the profit-pattern arc-beat tree.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s
    ``_close_active_dialogue`` handler when the ``kweon_legacy_profit_pattern``
    tree closes.
    Consumer: ``OkaforView._kweon_dialogue_id()`` routing guard (beat must
    not repeat). No mission consumer on the profit side per Decision 6.
    """
    return "okafor_legacy_profit_pattern_seen"


def okafor_legacy_heal_ending_seen() -> str:
    """Flag set when the player dismisses the heal-ending arc-beat tree.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s
    ``_close_active_dialogue`` handler when the ``kweon_legacy_heal_ending``
    tree closes. Also triggers setting ``OkaforResearchState.legacy_ending``
    to ``"heal"`` (terminal arc state).
    Consumers: ``OkaforView._kweon_dialogue_id()`` routing guard (arc
    terminal — all subsequent beats return None); ``data/journal/entries.json``
    trigger_flag for the ``auto_okafor_legacy_heal_ending`` entry.
    """
    return "okafor_legacy_heal_ending_seen"


def okafor_legacy_profit_ending_seen() -> str:
    """Flag set when the player dismisses the profit-ending arc-beat tree.

    Producer: :class:`spacegame.views.okafor_view.OkaforView`'s
    ``_close_active_dialogue`` handler when the ``kweon_legacy_profit_ending``
    tree closes. Also triggers setting ``OkaforResearchState.legacy_ending``
    to ``"profit"`` (terminal arc state).
    Consumers: ``OkaforView._kweon_dialogue_id()`` routing guard (arc
    terminal); ``data/journal/entries.json`` trigger_flag for the
    ``auto_okafor_legacy_profit_ending`` entry.
    """
    return "okafor_legacy_profit_ending_seen"


def okafor_legacy_mission_offered() -> str:
    """Flag set when Kweon offers the optional clinic-run mission in the heal-pattern beat.

    Producer: ``kweon_legacy_heal_pattern`` dialogue tree — a response
    ``set_flag`` on the node that names the destination system; set when the
    player advances through that response in OkaforView.
    Consumer: mission system (``okafor_legacy_clinic_run`` uses this flag
    for one-shot gating so the offer line never repeats).
    """
    return "okafor_legacy_mission_offered"


def okafor_legacy_mission_completed() -> str:
    """Flag set when the player completes the optional clinic-run mission.

    Producer: mission reward chain for ``okafor_legacy_clinic_run``
    (``reward_type: set_flag`` entry in ``data/missions/sa_r2_okafor_legacy.json``).
    Consumer: ``OkaforView._kweon_dialogue_id()`` post-clinic-run callback
    routing guard (SA-R3). Removed from KNOWN_PRODUCER_ONLY_ORPHANS in SA-R3.
    """
    return "okafor_legacy_mission_completed"


def okafor_legacy_clinic_callback_seen() -> str:
    """Flag set when the post-clinic-run Kweon callback dialogue is dismissed.

    Producer: ``OkaforView._close_active_dialogue()`` via the
    ``_LEGACY_ARC_TREE_TO_FLAG`` mapping when the
    ``kweon_legacy_post_clinic_run`` tree closes.
    Consumer: ``OkaforView._kweon_dialogue_id()`` routing guard — once set,
    the callback beat no longer surfaces and normal arc routing resumes.
    Both producer and consumer land in SA-R3 — no KNOWN_PRODUCER_ONLY_ORPHANS
    registration needed.
    """
    return "okafor_legacy_clinic_callback_seen"
