"""The return scenes: a kept one-shot NPC remembers the captain (polish design 6, choice 11).

A kept NPC opens a return state keyed on talked_to_<npc> and the flag its mission waits on, so a
second visit never replays the first. Each return is short: one reply reaches the awaited flag
without a check, one leaves and changes nothing, and every change sits on a reply that sets the
awaited flag. The tier 2 echoes remember a refusal (writing-discipline spec 9.2 row 6).
"""

from __future__ import annotations

from typing import Optional

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.dialogue import DialogueManager
from spacegame.models.social import SocialManager


def _dl() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


def _walk(
    tree_id: str,
    npc_id: str,
    prefixes: list[str],
    flags: Optional[dict[str, bool]] = None,
    social: Optional[SocialManager] = None,
) -> DialogueManager:
    """Play a tree through the replies whose texts start with each prefix, in order.

    With a SocialManager every check fails (a fresh one holds every skill at 0) and
    dispositions land on it; without one, every check passes.
    """
    manager = DialogueManager()
    if social is not None:
        manager.set_social_manager(social)
    manager.load_flags(dict(flags or {}))
    manager.start_dialogue(_dl().dialogue_trees[tree_id], npc_id=npc_id)
    for prefix in prefixes:
        texts = [r.text for r in manager.get_available_responses()]
        picks = [i for i, text in enumerate(texts) if text.startswith(prefix)]
        assert picks, f"{tree_id}: no reply starts {prefix!r} among {texts}"
        manager.select_response(picks[0])
    return manager


def _tree_for(npc_id: str, flags: dict[str, bool]) -> str:
    return _dl().npcs[npc_id].get_active_dialogue_id(flags)


def _base(npc_id: str) -> int:
    return SocialManager().get_disposition(npc_id)


class TestElena:
    WALK_AWAY = ["Mind your own business.", "I'll figure it out myself."]

    def test_the_walk_away_is_remembered(self) -> None:
        flags = _walk("elena_cantina", "elena_reeves", self.WALK_AWAY).get_flags()
        assert flags == {"elena_walked_away": True}

    def test_a_second_visit_opens_the_return_and_the_lesson_retires_it(self) -> None:
        assert _tree_for("elena_reeves", {}) == "elena_cantina"
        met = {"talked_to_elena_reeves": True}
        assert _tree_for("elena_reeves", met) == "elena_return"
        taught = {**met, "elena_gave_trading_tips": True}
        assert _tree_for("elena_reeves", taught) == "elena_cantina"

    def test_the_short_version_teaches_the_lesson(self) -> None:
        social = SocialManager()
        flags = _walk(
            "elena_return", "elena_reeves", ["Go ahead.", "Understood.", "Thanks"], social=social
        ).get_flags()
        assert flags == {"elena_gave_trading_tips": True}
        assert social.get_disposition("elena_reeves") == _base("elena_reeves")

    def test_an_honest_admission_earns_three(self) -> None:
        social = SocialManager()
        manager = _walk(
            "elena_return",
            "elena_reeves",
            ["I said I'd figure it out.", "[Sit down]", "Understood.", "Thanks"],
            social=social,
        )
        assert manager.get_flags() == {"elena_gave_trading_tips": True}
        assert social.get_disposition("elena_reeves") == _base("elena_reeves") + 3

    def test_not_yet_changes_nothing(self) -> None:
        social = SocialManager()
        manager = _walk("elena_return", "elena_reeves", ["Still working on it."], social=social)
        assert manager.get_flags() == {}
        assert not manager.is_active
        assert social.get_disposition("elena_reeves") == _base("elena_reeves")

    def test_her_lesson_names_no_price_the_boards_cannot_show(self) -> None:
        lesson = _dl().dialogue_trees["elena_cantina"].nodes["lesson"].text
        assert "80" not in lesson and "140" not in lesson
        assert "fifteen percent" in lesson

    def test_the_walk_away_has_a_log_entry_and_a_crew_line(self) -> None:
        triggers = {e.trigger_flag for e in _dl().journal_entries}
        assert "elena_walked_away" in triggers
        lines = [
            line
            for line in _dl().ambient_lines
            if line.crew_id == "elena_reeves" and line.required_flags == ["elena_walked_away"]
        ]
        assert len(lines) == 1
        assert lines[0].text.startswith('"Mind your own business."')


class TestGlyn:
    DECLINE = [
        "Who are you?",
        "What kind of information?",
        "What does that have to do",
        "What's on the chip?",
        "I don't want to get involved.",
        "[Leave]",
    ]

    def test_the_decline_is_remembered(self) -> None:
        flags = _walk("dex_cantina", "dex_halloran", self.DECLINE).get_flags()
        assert flags == {"dex_favor_declined": True}

    def test_a_second_visit_opens_the_return(self) -> None:
        met = {"talked_to_dex_halloran": True}
        assert _tree_for("dex_halloran", met) == "dex_return"
        assert _tree_for("dex_halloran", {**met, "dex_favor_accepted": True}) == "dex_cantina"

    def test_the_second_ask_draws_the_straight_answer_and_a_yes_pays_three(self) -> None:
        social = SocialManager()
        manager = _walk(
            "dex_return",
            "dex_halloran",
            ["Why did you wait", "I asked you a question.", "So. The job.", "I'll do it."],
            social=social,
        )
        assert manager.get_flags() == {"dex_favor_accepted": True}
        assert social.get_disposition("dex_halloran") == _base("dex_halloran") + 3

    def test_the_push_sets_and_pays_nothing(self) -> None:
        straight = _dl().dialogue_trees["dex_return"].nodes["straight"]
        asked = [
            r
            for r in _dl().dialogue_trees["dex_return"].nodes["priced"].responses
            if r.next_node_id == "straight"
        ]
        for r in [*asked, *straight.responses]:
            assert not r.set_flag and not r.disposition_change and not r.faction_reputation_changes

    def test_still_no_changes_nothing(self) -> None:
        social = SocialManager()
        manager = _walk(
            "dex_return",
            "dex_halloran",
            ["Is the job still open?", "Still no.", "[Leave]"],
            social=social,
        )
        assert manager.get_flags() == {}
        assert social.get_disposition("dex_halloran") == _base("dex_halloran")

    def test_why_me_follows_reva_sato(self) -> None:
        for flags, target in (({"helped_reva_sato": True}, "why_me"), ({}, "why_me_watched")):
            manager = _walk("dex_cantina", "dex_halloran", [], flags)
            whys = [
                r.next_node_id
                for r in manager.get_available_responses()
                if r.text == "Why are you talking to me?"
            ]
            assert whys == [target], flags

    def test_malia_heard_about_the_no(self) -> None:
        for flags, shown in (({"dex_favor_declined": True}, True), ({}, False)):
            manager = _walk("torres_underground", "malia_torres", ["[Follow her]"], flags)
            texts = [r.text for r in manager.get_available_responses()]
            assert ("Glyn tell you anything about me?" in texts) is shown

    def test_whispers_names_what_the_captain_agrees_to(self) -> None:
        whispers = next(m for m in _dl().missions if m.id == "whispers_at_the_bar")
        assert whispers.objectives[0].description == "Agree to carry Glyn's chip"

    def test_the_decline_has_a_log_entry(self) -> None:
        assert "dex_favor_declined" in {e.trigger_flag for e in _dl().journal_entries}
