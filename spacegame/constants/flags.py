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
