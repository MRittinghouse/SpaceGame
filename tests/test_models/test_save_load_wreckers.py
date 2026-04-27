"""Save/load round-trip coverage for SA-1 Wreckers' Guild state.

Verifies:
  - A populated WreckersGuildState round-trips byte-clean (acceptance #9).
  - Sub-rep value lives on Player.sub_reputation (carried through the
    existing path — regression guard for SA-B-EXT-1 wiring).
  - A legacy save with no `wreckers_guild_state` key loads as unjoined.
  - Mission state (an active wreckers contract) round-trips.
"""

from __future__ import annotations

import json

from spacegame.data_loader import get_data_loader
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.models.wreckers_guild import (
    WRECKERS_CONTRACT_TEMPLATES,
    WreckersGuildState,
)
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


class TestWreckersSaveLoad:
    def test_default_state_round_trips(self) -> None:
        # Default Player has no wreckers_guild_state attribute set —
        # behaves like a freshly-created game.
        player = Player(name="Tester", credits=500, current_system_id="nexus_prime", ship=_shuttle())
        restored = _round_trip(player)
        assert restored.wreckers_guild_state is None

    def test_populated_state_round_trip(self) -> None:
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="crimson_reach",
            ship=_shuttle(),
        )
        player.sub_reputation["wreckers_guild"] = 35
        player.wreckers_guild_state = WreckersGuildState(
            enrolled=True,
            lockout_until_day=12,
            active_contract_ids=["wreckers_contract_recovery_rare_parts_2_0"],
            slot_seed_window=2,
            slot_offers=[t.id for t in WRECKERS_CONTRACT_TEMPLATES[:3]],
            promoted_tiers={"journeyman"},
            completed_contract_count=4,
        )
        restored = _round_trip(player)
        assert restored.sub_reputation.get("wreckers_guild") == 35
        assert restored.wreckers_guild_state is not None
        assert restored.wreckers_guild_state.enrolled is True
        assert restored.wreckers_guild_state.lockout_until_day == 12
        assert restored.wreckers_guild_state.active_contract_ids == [
            "wreckers_contract_recovery_rare_parts_2_0"
        ]
        assert restored.wreckers_guild_state.slot_seed_window == 2
        assert restored.wreckers_guild_state.slot_offers == [
            t.id for t in WRECKERS_CONTRACT_TEMPLATES[:3]
        ]
        assert restored.wreckers_guild_state.promoted_tiers == {"journeyman"}
        assert restored.wreckers_guild_state.completed_contract_count == 4

    def test_legacy_save_no_wreckers_key_loads_as_unjoined(self) -> None:
        """Acceptance #9 (latter half): saves predating SA-1 must load."""
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="nexus_prime",
            ship=_shuttle(),
        )
        mgr = SaveManager()
        data = mgr._serialize_player(player)
        # Strip the SA-1 key as an old save would have it.
        data.pop("wreckers_guild_state", None)
        # And strip the sub_reputation key entirely — early SA-B-EXT-1
        # saves had this absent before the field went universal.
        data.pop("sub_reputation", None)
        restored = mgr._deserialize_player(json.loads(json.dumps(data)))
        assert restored.wreckers_guild_state is None
        assert restored.sub_reputation == {}
