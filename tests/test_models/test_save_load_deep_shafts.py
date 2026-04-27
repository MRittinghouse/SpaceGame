"""SA-2 save/load round-trip coverage for ``DeepShaftsState``.

Verifies (acceptance #10):
  - A populated ``DeepShaftsState`` round-trips byte-clean.
  - ``faction_reputation["miners_union"]`` carries the granted rep.
  - A legacy save with no ``deep_shafts_state`` key loads as None.
  - Pilgrimage journal flags round-trip via ``dialogue_flags``.
"""

from __future__ import annotations

import json

from spacegame.data_loader import get_data_loader
from spacegame.models.deep_shafts import DeepShaftsState
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.save_manager import SaveManager


def _shuttle() -> Ship:
    dl = get_data_loader()
    dl.load_all()
    return Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)


def _round_trip(player: Player) -> Player:
    mgr = SaveManager()
    data = mgr._serialize_player(player)
    json_str = json.dumps(data)
    return mgr._deserialize_player(json.loads(json_str))


class TestDeepShaftsSaveLoad:
    def test_default_state_round_trips_as_none(self) -> None:
        """A fresh Player has no deep_shafts_state."""
        player = Player(
            name="Tester", credits=500, current_system_id="nexus_prime", ship=_shuttle()
        )
        restored = _round_trip(player)
        assert restored.deep_shafts_state is None

    def test_populated_state_round_trip(self) -> None:
        """Acceptance #10: visit_count=4, last_pilgrimage_day=37, blessing_total=11,
        scripted_scene_played=True round-trips byte-clean."""
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="breakstone",
            ship=_shuttle(),
        )
        player.faction_reputation["miners_union"] = 11
        player.deep_shafts_state = DeepShaftsState(
            visit_count=4,
            last_pilgrimage_day=37,
            blessing_total=11,
            scripted_scene_played=True,
            last_journal_unlock_day=37,
        )
        restored = _round_trip(player)
        assert restored.faction_reputation.get("miners_union") == 11
        assert restored.deep_shafts_state is not None
        assert restored.deep_shafts_state.visit_count == 4
        assert restored.deep_shafts_state.last_pilgrimage_day == 37
        assert restored.deep_shafts_state.blessing_total == 11
        assert restored.deep_shafts_state.scripted_scene_played is True
        assert restored.deep_shafts_state.last_journal_unlock_day == 37

    def test_legacy_save_no_deep_shafts_key_loads_safely(self) -> None:
        """Saves predating SA-2 must load without exception."""
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="nexus_prime",
            ship=_shuttle(),
        )
        mgr = SaveManager()
        data = mgr._serialize_player(player)
        data.pop("deep_shafts_state", None)
        restored = mgr._deserialize_player(json.loads(json.dumps(data)))
        assert restored.deep_shafts_state is None

    def test_pilgrimage_journal_flags_persist(self) -> None:
        """Sora journal flags ride on ``dialogue_flags`` and round-trip."""
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="breakstone",
            ship=_shuttle(),
        )
        player.dialogue_flags["pilgrimage_journal_1"] = True
        player.dialogue_flags["pilgrimage_journal_2"] = True
        player.dialogue_flags["visited_deep_shafts"] = True
        restored = _round_trip(player)
        assert restored.dialogue_flags.get("pilgrimage_journal_1") is True
        assert restored.dialogue_flags.get("pilgrimage_journal_2") is True
        assert restored.dialogue_flags.get("visited_deep_shafts") is True
