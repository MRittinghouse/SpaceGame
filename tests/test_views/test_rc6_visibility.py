"""RC-6: visibility tests — non-combat recording, journal entries,
and the 'met before' badge.
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.models.captain_memory import (
    OUTCOME_BRIBED,
    OUTCOME_NEGOTIATED,
    OUTCOME_VICTORY,
    STATUS_BRIBED_OFF,
    STATUS_TRUCE,
    CaptainMemory,
)
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterDefinition,
    EncounterOutcome,
    EncounterRef,
    EncounterSkillCheck,
)
from spacegame.models.journal import Journal
from spacegame.models.mission import MissionReward
from spacegame.models.social import SocialManager
from spacegame.views.encounter_view import EncounterView


def _init_pygame() -> None:
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def _ui_manager() -> pygame_gui.UIManager:
    _init_pygame()
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


class _FakePlayer:
    """Minimal player shim — exposes the surface CaptainMemory needs."""

    def __init__(self, credits: int = 1000) -> None:
        self.credits = credits
        self.dialogue_flags: dict[str, bool] = {}
        self.captain_memory: dict[str, CaptainMemory] = {}
        self.game_day: int = 7
        self.current_system_id: str = "havens_rest"

    def get_captain_memory(self, captain_id: str) -> CaptainMemory:
        if captain_id not in self.captain_memory:
            self.captain_memory[captain_id] = CaptainMemory(captain_id=captain_id)
        return self.captain_memory[captain_id]

    def record_captain_encounter(self, captain_id: str, outcome: str) -> CaptainMemory:
        mem = self.get_captain_memory(captain_id)
        mem.record_encounter(outcome, self.game_day)
        return mem


def _make_captain_encounter(
    choices: list[EncounterChoice], captain_id: str = "vela_wolfs_ear"
) -> EncounterDefinition:
    return EncounterDefinition(
        id="ce4_test",
        encounter_type="ransom_demand",
        name="Test Encounter",
        description="Pay or fight.",
        choices=choices,
        captain_id=captain_id,
    )


def _make_view(
    encounter_def: EncounterDefinition,
    player: _FakePlayer | None = None,
    social: SocialManager | None = None,
    journal: Journal | None = None,
) -> EncounterView:
    return EncounterView(
        ui_manager=_ui_manager(),
        encounter_def=encounter_def,
        encounter_ref=EncounterRef(enemy_template_ids=[], encounter_seed=42),
        player=player,
        social_manager=social,
        journal=journal,
    )


# ---------------------------------------------------------------------------
# RC-6a: non-combat recording
# ---------------------------------------------------------------------------


class TestNonCombatCaptainRecording:
    def test_pay_choice_records_bribed(self) -> None:
        choice = EncounterChoice(
            id="pay",
            label="Pay",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            requires_credits=200,
        )
        defn = _make_captain_encounter([choice])
        player = _FakePlayer()
        view = _make_view(defn, player=player)
        view.on_enter()
        view._select_choice(0)
        mem = player.captain_memory["vela_wolfs_ear"]
        assert mem.encounter_count == 1
        assert mem.last_outcome == OUTCOME_BRIBED
        assert mem.status == STATUS_BRIBED_OFF
        view.on_exit()

    def test_skill_check_success_records_negotiated(self) -> None:
        social = SocialManager()
        social._skills["persuasion"].level = 5
        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            skill_check=EncounterSkillCheck("persuasion", 3),
        )
        defn = _make_captain_encounter([choice])
        player = _FakePlayer()
        view = _make_view(defn, player=player, social=social)
        view.on_enter()
        view._select_choice(0)
        mem = player.captain_memory["vela_wolfs_ear"]
        assert mem.last_outcome == OUTCOME_NEGOTIATED
        assert mem.status == STATUS_TRUCE
        view.on_exit()

    def test_skill_check_failure_does_not_record_via_encounter_view(self) -> None:
        """Failure leads to combat — CombatView is responsible for recording."""
        social = SocialManager()
        # No skills leveled → fails the check
        choice = EncounterChoice(
            id="talk",
            label="Talk",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            failure_outcome=EncounterOutcome(
                description="combat", rewards=[], leads_to_combat=True
            ),
            skill_check=EncounterSkillCheck("persuasion", 5),
        )
        defn = _make_captain_encounter([choice])
        player = _FakePlayer()
        view = _make_view(defn, player=player, social=social)
        view.on_enter()
        view._select_choice(0)
        # EncounterView did not record — combat-bound outcome
        assert "vela_wolfs_ear" not in player.captain_memory
        view.on_exit()

    def test_walk_away_does_not_record(self) -> None:
        """Plain refuse / pass with no engagement gets no record."""
        choice = EncounterChoice(
            id="pass",
            label="Pass",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
        )
        defn = _make_captain_encounter([choice])
        player = _FakePlayer()
        view = _make_view(defn, player=player)
        view.on_enter()
        view._select_choice(0)
        assert "vela_wolfs_ear" not in player.captain_memory
        view.on_exit()

    def test_no_captain_attached_does_not_record(self) -> None:
        choice = EncounterChoice(
            id="pay",
            label="Pay",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            requires_credits=100,
        )
        defn = _make_captain_encounter([choice], captain_id="")  # no captain
        player = _FakePlayer()
        view = _make_view(defn, player=player)
        view.on_enter()
        view._select_choice(0)
        assert player.captain_memory == {}
        view.on_exit()


# ---------------------------------------------------------------------------
# RC-6b: journal entries on first meeting
# ---------------------------------------------------------------------------


class TestJournalEntryOnFirstMeeting:
    def test_first_meeting_adds_journal_entry(self) -> None:
        choice = EncounterChoice(
            id="pay",
            label="Pay",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            requires_credits=100,
        )
        defn = _make_captain_encounter([choice])
        player = _FakePlayer()
        journal = Journal()
        view = _make_view(defn, player=player, journal=journal)
        view.on_enter()
        view._select_choice(0)
        entries = journal.get_entries()
        assert len(entries) == 1
        assert "Captain Vela" in entries[0].text
        assert entries[0].tag == "people"
        view.on_exit()

    def test_second_meeting_does_not_add_duplicate_journal_entry(self) -> None:
        """Even though the recording fires every meeting, the journal entry
        only fires on FIRST meeting (memory.is_first_meeting == True)."""
        choice = EncounterChoice(
            id="pay",
            label="Pay",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            requires_credits=100,
        )
        defn = _make_captain_encounter([choice])
        player = _FakePlayer()
        # Pre-existing memory: already met once
        player.captain_memory["vela_wolfs_ear"] = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=1,
            first_seen_day=2,
            last_seen_day=2,
        )
        journal = Journal()
        view = _make_view(defn, player=player, journal=journal)
        view.on_enter()
        view._select_choice(0)
        # No journal entry — second meeting
        assert journal.get_entries() == []
        view.on_exit()

    def test_no_journal_wired_does_not_crash(self) -> None:
        """Backward compat: if Game doesn't pass a journal, recording still works."""
        choice = EncounterChoice(
            id="pay",
            label="Pay",
            description="d",
            outcome=EncounterOutcome(description="ok", rewards=[]),
            requires_credits=100,
        )
        defn = _make_captain_encounter([choice])
        player = _FakePlayer()
        view = _make_view(defn, player=player, journal=None)
        view.on_enter()
        view._select_choice(0)
        # Recording still happened
        assert "vela_wolfs_ear" in player.captain_memory
        view.on_exit()


# ---------------------------------------------------------------------------
# RC-6c: met-before badge
# ---------------------------------------------------------------------------


class TestMetBeforeBadge:
    def test_no_badge_for_first_meeting(self) -> None:
        defn = _make_captain_encounter(
            [
                EncounterChoice(
                    id="x",
                    label="x",
                    description="",
                    outcome=EncounterOutcome(description="d", rewards=[]),
                )
            ]
        )
        player = _FakePlayer()
        view = _make_view(defn, player=player)
        view.on_enter()
        assert view._met_before_badge_text() == ""
        view.on_exit()

    def test_badge_for_one_prior_meeting(self) -> None:
        defn = _make_captain_encounter(
            [
                EncounterChoice(
                    id="x",
                    label="x",
                    description="",
                    outcome=EncounterOutcome(description="d", rewards=[]),
                )
            ]
        )
        player = _FakePlayer()
        player.captain_memory["vela_wolfs_ear"] = CaptainMemory(
            captain_id="vela_wolfs_ear", encounter_count=1
        )
        view = _make_view(defn, player=player)
        view.on_enter()
        assert "1 time" in view._met_before_badge_text()
        view.on_exit()

    def test_badge_pluralization_for_multiple_meetings(self) -> None:
        defn = _make_captain_encounter(
            [
                EncounterChoice(
                    id="x",
                    label="x",
                    description="",
                    outcome=EncounterOutcome(description="d", rewards=[]),
                )
            ]
        )
        player = _FakePlayer()
        player.captain_memory["vela_wolfs_ear"] = CaptainMemory(
            captain_id="vela_wolfs_ear", encounter_count=3
        )
        view = _make_view(defn, player=player)
        view.on_enter()
        assert "3 times" in view._met_before_badge_text()
        view.on_exit()

    def test_no_badge_for_no_captain(self) -> None:
        defn = _make_captain_encounter(
            [
                EncounterChoice(
                    id="x",
                    label="x",
                    description="",
                    outcome=EncounterOutcome(description="d", rewards=[]),
                )
            ],
            captain_id="",
        )
        player = _FakePlayer()
        view = _make_view(defn, player=player)
        view.on_enter()
        assert view._met_before_badge_text() == ""
        view.on_exit()
