"""Bug bash BB-38: who can be talked to, as one filter with the keep rule."""

from __future__ import annotations

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.dialogue import (
    NPC,
    DialogueNode,
    DialogueResponse,
    DialogueState,
    DialogueTree,
)
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.npc_availability import (
    is_listed,
    needed_by,
    npcs_here,
    settable_flags,
    settable_index,
)


def _npc(
    npc_id: str = "test_npc",
    home: str = "nexus_prime",
    gate: str = "",
    prerequisites: list[str] | None = None,
    hide: str = "",
) -> NPC:
    return NPC(
        id=npc_id,
        name="Test NPC",
        title="Test",
        portrait_color=(100, 100, 100),
        home_system_id=home,
        dialogue_id=f"{npc_id}_dialogue",
        auto_trigger_gate_flag=gate,
        auto_trigger_prerequisites=prerequisites or [],
        hide_after_flag=hide,
    )


def _mission(mission_id: str, *objectives: MissionObjective) -> Mission:
    return Mission(
        id=mission_id,
        name=mission_id,
        description="A test mission.",
        objectives=list(objectives),
        rewards=[MissionReward(reward_type="xp", amount=10)],
    )


def _waiting(status: MissionStatus, flag: str = "awaited") -> MissionManager:
    manager = MissionManager([])
    manager.add_mission(
        _mission("waits", MissionObjective(type=ObjectiveType.HAS_FLAG, target_id=flag)), status
    )
    return manager


def _dl() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


class TestClauses:
    def test_an_npc_is_listed_only_at_home(self) -> None:
        npc = _npc()
        assert is_listed(npc, "nexus_prime", {}, None, set(), frozenset())
        assert not is_listed(npc, "verdant", {}, None, set(), frozenset())

    def test_a_crew_member_aboard_is_not_listed(self) -> None:
        npc = _npc("elena_reeves")
        assert not is_listed(npc, "nexus_prime", {}, None, {"elena_reeves"}, frozenset())

    def test_an_npc_waits_for_every_prerequisite(self) -> None:
        npc = _npc(prerequisites=["a", "b"])
        assert not is_listed(npc, "nexus_prime", {"a": True}, None, set(), frozenset())
        assert is_listed(npc, "nexus_prime", {"a": True, "b": True}, None, set(), frozenset())

    def test_a_played_one_shot_scene_unlists_its_npc(self) -> None:
        npc = _npc(gate="met_test")
        assert not is_listed(npc, "nexus_prime", {"met_test": True}, None, set(), {"awaited"})

    def test_the_keep_rule_lists_a_played_npc_a_mission_still_needs(self) -> None:
        npc = _npc(gate="met_test")
        flags = {"met_test": True}
        for status in (MissionStatus.AVAILABLE, MissionStatus.ACTIVE):
            manager = _waiting(status)
            assert is_listed(npc, "nexus_prime", flags, manager, set(), {"awaited"}), status
            assert needed_by(npc.id, {"awaited"}, manager, flags) == "waits"
        for status in (
            MissionStatus.UNAVAILABLE,
            MissionStatus.COMPLETED,
            MissionStatus.FAILED,
            MissionStatus.ABANDONED,
        ):
            manager = _waiting(status)
            assert manager.open_missions() == [], status
            assert not is_listed(npc, "nexus_prime", flags, manager, set(), {"awaited"}), status
            assert needed_by(npc.id, {"awaited"}, manager, flags) == "", status
        manager = _waiting(MissionStatus.ACTIVE)
        assert not is_listed(
            npc, "nexus_prime", {**flags, "awaited": True}, manager, set(), {"awaited"}
        )
        assert not is_listed(npc, "nexus_prime", flags, manager, set(), {"other"})

    def test_a_dialogue_states_tree_feeds_the_keep_index(self) -> None:
        npc = _npc(gate="met_test")
        npc.dialogue_states = [
            DialogueState(
                state_id="return",
                dialogue_id="test_npc_return",
                required_flags=["talked_to_test_npc"],
                excluded_flags=["awaited"],
            )
        ]
        trees = {
            "test_npc_dialogue": DialogueTree(
                id="test_npc_dialogue",
                start_node_id="start",
                nodes={
                    "start": DialogueNode(
                        id="start",
                        speaker_id="test_npc",
                        text="Hello.",
                        responses=[DialogueResponse(text="Leave.", next_node_id=None)],
                    )
                },
            ),
            "test_npc_return": DialogueTree(
                id="test_npc_return",
                start_node_id="start",
                nodes={
                    "start": DialogueNode(
                        id="start",
                        speaker_id="test_npc",
                        text="Welcome back.",
                        responses=[
                            DialogueResponse(text="Done.", next_node_id=None, set_flag="awaited")
                        ],
                    )
                },
            ),
        }
        assert "awaited" not in settable_flags(_npc(gate="met_test"), trees)
        assert "awaited" in settable_flags(npc, trees)
        assert "awaited" in settable_index([npc], trees)["test_npc"]
        assert is_listed(
            npc,
            "nexus_prime",
            {"met_test": True},
            _waiting(MissionStatus.ACTIVE),
            set(),
            settable_flags(npc, trees),
        )

    def test_a_hide_flag_beats_the_keep_rule(self) -> None:
        npc = _npc(gate="met_test", hide="gone")
        flags = {"met_test": True, "gone": True}
        manager = _waiting(MissionStatus.ACTIVE)
        assert not is_listed(npc, "nexus_prime", flags, manager, set(), {"awaited"})

    def test_an_active_talk_objective_needs_its_npc_until_it_is_met(self) -> None:
        npc = _npc(gate="met_test")
        manager = MissionManager([])
        talk = _mission(
            "talk",
            MissionObjective(type=ObjectiveType.TALK_TO_NPC, target_id="test_npc"),
        )
        manager.add_mission(talk, MissionStatus.AVAILABLE)
        flags = {"met_test": True}
        assert needed_by("test_npc", frozenset(), manager, flags) == ""
        manager._status["talk"] = MissionStatus.ACTIVE
        assert is_listed(npc, "nexus_prime", flags, manager, set(), frozenset())
        manager._progress["talk"] = [True]
        assert needed_by("test_npc", frozenset(), manager, flags) == ""

    def test_needed_by_names_the_first_open_mission_in_content_order(self) -> None:
        manager = MissionManager([])
        for mission_id in ("first", "second"):
            manager.add_mission(
                _mission(mission_id, MissionObjective(type=ObjectiveType.HAS_FLAG, target_id="x")),
                MissionStatus.ACTIVE,
            )
        assert needed_by("test_npc", {"x"}, manager, {}) == "first"
        assert [m.id for m in manager.open_missions()] == ["first", "second"]


class TestTheRealContent:
    def test_elena_stays_after_a_walk_away_until_her_lesson(self) -> None:
        dl = _dl()
        elena = dl.npcs["elena_reeves"]
        manager = MissionManager(dl.missions)
        manager.load_state({"status": {"footing_the_bill": "active"}})
        flags = {"iron_delivery_moved_on": True, "talked_to_elena_cantina": True}
        settable = settable_flags(elena, dl.dialogue_trees)
        assert "elena_gave_trading_tips" in settable
        assert is_listed(elena, "nexus_prime", flags, manager, set(), settable)
        assert needed_by(elena.id, settable, manager, flags) == "footing_the_bill"
        flags["elena_gave_trading_tips"] = True
        assert not is_listed(elena, "nexus_prime", flags, manager, set(), settable)

    def test_day_one_at_nexus_prime(self) -> None:
        """Larsen is needed for the permit; Python lists the Act II v1 NPCs (D-21 is the port's)."""
        dl = _dl()
        manager = MissionManager(dl.missions)
        manager.load_state({"status": {"bill_of_landing": "active"}})
        index = settable_index(dl.npcs.values(), dl.dialogue_trees)
        listed = dict(npcs_here(dl.npcs.values(), "nexus_prime", {}, manager, set(), index))
        assert listed["officer_larsen"] == "bill_of_landing"
        assert listed["odom_broker"] == ""
        assert "noor_castellano" in listed
        assert "dex_halloran" not in listed
