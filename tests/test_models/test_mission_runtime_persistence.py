"""Runtime-added (procedural) missions persist through save and load (SP2 spec Section 6)."""

from __future__ import annotations

import json

from spacegame.data_loader import get_data_loader
from spacegame.models.mission import MissionManager, MissionStatus
from spacegame.models.procedural_missions import ProceduralMissionGenerator
from tests.test_scenarios._helpers import fresh_player


def _board() -> tuple[MissionManager, list[str]]:
    dl = get_data_loader()
    manager = MissionManager(list(dl.missions))
    gen = ProceduralMissionGenerator(
        systems=dl.systems,
        commodities=dl.commodities,
        enemy_templates=dl.enemy_templates,
        seed=2024,
    )
    ids: list[str] = []
    for mission in gen.generate_for_system("nexus_prime", 3):
        ok, msg = manager.add_mission(mission)
        assert ok, msg
        ids.append(mission.id)
    assert len(ids) >= 2, "need at least two procedural missions for this test"
    return manager, ids


class TestRuntimeMissionPersistence:
    def test_accepted_and_offered_runtime_missions_survive(self) -> None:
        manager, ids = _board()
        player = fresh_player()
        ok, msg = manager.accept_mission(ids[0], player=player)
        assert ok, msg

        saved = json.loads(json.dumps(manager.get_state()))
        restored = MissionManager(list(get_data_loader().missions))
        restored.load_state(saved)

        assert restored.get_status(ids[0]) == MissionStatus.ACTIVE
        assert restored.get_status(ids[1]) == MissionStatus.AVAILABLE
        original = manager.get_mission(ids[0])
        copy = restored.get_mission(ids[0])
        assert original is not None and copy is not None
        assert copy.to_dict() == original.to_dict()

    def test_removed_runtime_missions_are_not_saved(self) -> None:
        manager, ids = _board()
        assert manager.remove_mission(ids[1])
        saved_ids = [m["id"] for m in manager.get_state()["runtime_missions"]]
        assert ids[1] not in saved_ids

    def test_legacy_state_without_runtime_missions_loads(self) -> None:
        restored = MissionManager(list(get_data_loader().missions))
        restored.load_state({"status": {}, "progress": {}})
        assert restored.get_state()["runtime_missions"] == []
