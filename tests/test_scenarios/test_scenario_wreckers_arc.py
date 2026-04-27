"""SA-1 scenario: Wreckers' Guild Hall apprentice → master arc.

Walks the player through the full advancement path end-to-end:

  enroll → first contract → journeyman promotion → master promotion → save round-trip

Plus a failure path:

  apprentice → contract turn-in → simulate missed deadline → make-up beat

The test exercises real models (Player, Mission, MissionManager) but
substitutes the view with the WreckersGuildView under a real pygame_gui
manager. No rendering is required — only logic-level assertions.
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.constants.flags import (
    enrolled_wreckers_guild,
    wreckers_contract_completed,
    wreckers_made_up_apology,
    wreckers_made_up_journal,
    wreckers_promoted_tier,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.journal import Journal
from spacegame.models.mission import MissionManager
from spacegame.models.wreckers_guild import (
    LOCKOUT_DAYS,
    SUB_REP_FAILURE_PENALTY,
    WreckersGuildState,
    get_template,
)
from spacegame.views.wreckers_guild_view import WreckersGuildView
from tests.test_scenarios._helpers import fresh_player


def _make_view(player, mm):
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    return manager, WreckersGuildView(
        ui_manager=manager,
        player=player,
        mission_manager=mm,
    )


def _stock_cargo_for_active(player, view, mm):
    """Stock the player's hold with whatever the active contract demands."""
    state = player.wreckers_guild_state
    assert state is not None
    for mission_id in state.active_contract_ids:
        mission = mm.get_mission(mission_id)
        if mission is None:
            continue
        for obj in mission.objectives:
            player.ship.add_cargo(obj.target_id, obj.target_quantity)


def test_apprentice_to_master_full_arc() -> None:
    """End-to-end: enroll → completions → tier promotions through master."""
    player = fresh_player(system_id="crimson_reach", credits=1000)
    mm = MissionManager(missions=[])
    _, view = _make_view(player, mm)
    view.on_enter()

    # Step 1: enroll
    assert player.wreckers_guild_state is None or not player.wreckers_guild_state.enrolled
    view._enroll_player()
    assert player.dialogue_flags.get(enrolled_wreckers_guild()) is True
    assert player.sub_reputation["wreckers_guild"] == 1

    # Apprentice contract turn-in to seed completed_contract_count
    offers = view.get_offered_template_ids()
    assert offers, "apprentice must see contract offers"
    accepted = view._accept_contract(offers[0])
    assert accepted
    _stock_cargo_for_active(player, view, mm)
    success, _ = view._turn_in_active_contract()
    assert success
    assert player.dialogue_flags.get(wreckers_contract_completed()) is True

    # Step 2: jump rep to 30 (journeyman). Use the modify path so the
    # promotion delta queues + the view drains it on next entry.
    view._refresh_offers()
    success, _ = player.modify_sub_reputation(
        "wreckers_guild", 30 - player.sub_reputation["wreckers_guild"], _config()
    )
    assert success
    view._drain_promotion_queue()
    assert player.dialogue_flags.get(wreckers_promoted_tier("journeyman")) is True
    # Journeyman can now see the recovery + escort pools.
    view._refresh_offers()
    j_offers = view.get_offered_template_ids()
    j_categories = {get_template(o).category for o in j_offers if get_template(o)}  # type: ignore[union-attr]
    assert any(c in j_categories for c in ("recovery", "escort_salvage", "cleanup"))

    # Step 3: bump to master.
    success, _ = player.modify_sub_reputation(
        "wreckers_guild", 70 - player.sub_reputation["wreckers_guild"], _config()
    )
    assert success
    view._drain_promotion_queue()
    assert player.dialogue_flags.get(wreckers_promoted_tier("master")) is True
    view._refresh_offers()
    m_offers = view.get_offered_template_ids()
    # Master sees deep_derelict eventually — across enough seeds at least.
    # Here we only verify any card; the model-level test exercises the
    # deep-derelict reachability across windows.
    assert m_offers
    view.on_exit()


def test_failure_then_make_up_path() -> None:
    """Failure → lockout → make-up sequence (acceptance #5)."""
    player = fresh_player(system_id="crimson_reach", credits=1000)
    player.game_day = 30
    player.wreckers_guild_state = WreckersGuildState(enrolled=True)
    player.sub_reputation["wreckers_guild"] = 12
    mm = MissionManager(missions=[])
    _, view = _make_view(player, mm)
    view.on_enter()

    starting_rep = player.sub_reputation["wreckers_guild"]
    view._fail_active_contract_with_penalty(mission_id="missing_mission_id")
    assert player.sub_reputation["wreckers_guild"] == max(0, starting_rep - SUB_REP_FAILURE_PENALTY)
    assert player.wreckers_guild_state.lockout_until_day == 30 + LOCKOUT_DAYS
    assert view.is_locked_out()

    # Advance past the lockout window.
    player.game_day = 30 + LOCKOUT_DAYS + 1
    assert not view.is_locked_out()

    # Make-up beat fires once.
    view._make_up_with_malia()
    assert player.dialogue_flags.get(wreckers_made_up_apology()) is True
    assert player.dialogue_flags.get(wreckers_made_up_journal()) is True
    assert player.wreckers_guild_state.lockout_until_day == 0

    # Re-firing make-up after the apology flag is set is a no-op.
    pre_count = sum(1 for v in player.dialogue_flags.values() if v)
    view._make_up_with_malia()
    assert sum(1 for v in player.dialogue_flags.values() if v) == pre_count
    view.on_exit()


def test_journal_entries_fire_on_flags() -> None:
    """All four SA-1 journal entries trigger on their respective flags."""
    dl = get_data_loader()
    dl.load_all()
    journal = Journal(auto_templates=dl.journal_entries)

    triggered_ids = set()
    for flag in [
        wreckers_contract_completed(),
        wreckers_promoted_tier("journeyman"),
        wreckers_promoted_tier("master"),
        wreckers_made_up_journal(),
    ]:
        entry = journal.trigger_auto_entry(flag, game_day=42, system_id="crimson_reach")
        assert entry is not None, f"no journal entry registered for flag '{flag}'"
        triggered_ids.add(entry.entry_id)
    expected_ids = {
        "auto_wreckers_first_contract",
        "auto_wreckers_promoted_journeyman",
        "auto_wreckers_promoted_master",
        "auto_wreckers_made_up",
    }
    assert triggered_ids == expected_ids


def _config():
    """Convenience accessor for the Wreckers' Guild OrganizationConfig."""
    from spacegame.models.wreckers_guild import WRECKERS_GUILD_CONFIG

    return WRECKERS_GUILD_CONFIG


# ---------------------------------------------------------------------------
# Secondary contacts arc (R1)
# ---------------------------------------------------------------------------


def test_secondary_contacts_walk_full_dialogues_after_enrollment() -> None:
    """End-to-end: enroll, then exercise each contact's full 3-node tree.

    Acceptance criterion 12 requires each secondary contact to be a real
    interactive speaker carrying a distinct register. This walks the
    full greeting → craft → signoff path for Paz, Daro, and Ife and
    asserts every node passes the Writing Bible scanner inline.
    """
    player = fresh_player(system_id="crimson_reach", credits=1000)
    mm = MissionManager(missions=[])
    _, view = _make_view(player, mm)
    view.on_enter()
    view._enroll_player()
    contacts = view.get_contact_speaker_ids()
    assert set(contacts) == {"paz_reina", "daro_teck", "ife_obi"}

    forbidden_dashes = {"—", "–", " -- "}
    banned_phrases = ("couldn't help but", "a testament to")
    seen_texts: set[str] = set()

    for contact_id in contacts:
        view._open_contact_dialogue(contact_id)
        node_ids_visited = []
        for _ in range(4):  # safety bound — every tree should close inside 3 steps
            node = view.get_active_dialogue_node()
            if node is None:
                break
            node_ids_visited.append(node.id)
            assert node.speaker_id == contact_id
            # Per-node Writing Bible compliance.
            assert not any(d in node.text for d in forbidden_dashes), (
                f"em-dash in {contact_id}/{node.id}: {node.text!r}"
            )
            for phrase in banned_phrases:
                assert phrase not in node.text.lower(), (
                    f"banned phrase '{phrase}' in {contact_id}/{node.id}"
                )
            seen_texts.add(node.text)
            view._advance_dialogue()
        # Each tree must walk all three authored nodes before closing.
        assert node_ids_visited == ["greeting", "craft", "signoff"], (
            f"{contact_id} tree did not walk greeting → craft → signoff: {node_ids_visited}"
        )
        assert view.get_active_dialogue_node() is None

    # Distinctness: 3 contacts × 3 nodes = 9 unique authored texts.
    assert len(seen_texts) == 9, "secondary contact dialogue texts collapsed onto each other"
    view.on_exit()
