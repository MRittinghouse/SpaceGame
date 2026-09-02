"""SA-F2: Save/load round-trip coverage for ``Player.futures_state``.

Verifies:
  - A default player serializes / deserializes with an empty FuturesState.
  - A populated FuturesState (mix of active + settled contracts, non-zero
    running totals, advanced contract-sequence counter) round-trips
    losslessly through save + load.
  - A legacy save predating SA-F2 (no ``futures_state`` key) loads with
    a default FuturesState (acceptance criterion 9c).
  - A malformed payload also loads to a default FuturesState (defensive
    migration per CLAUDE.md).
"""

from __future__ import annotations

import json

from spacegame.data_loader import get_data_loader
from spacegame.models.futures import FuturesContract, FuturesState
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


def _make_contract(**overrides: object) -> FuturesContract:
    defaults: dict[str, object] = {
        "contract_id": "futures_1_common_metals_001",
        "commodity_id": "common_metals",
        "direction": "LONG",
        "strike_price": 67,
        "quantity": 80,
        "duration_days": 7,
        "entry_cost": 214,
        "accept_day": 1,
        "maturity_day": 8,
    }
    defaults.update(overrides)
    return FuturesContract(**defaults)  # type: ignore[arg-type]


class TestFuturesStateSaveLoad:
    def test_default_state_round_trips(self) -> None:
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="nexus_prime",
            ship=_shuttle(),
        )
        restored = _round_trip(player)
        assert isinstance(restored.futures_state, FuturesState)
        assert restored.futures_state.active_contracts == []
        assert restored.futures_state.settled_contracts == []
        assert restored.futures_state.total_credits_won == 0
        assert restored.futures_state.total_credits_lost == 0

    def test_populated_state_round_trips_including_seq_counter(self) -> None:
        player = Player(
            name="Tester",
            credits=5_000,
            current_system_id="nexus_prime",
            ship=_shuttle(),
        )
        active = _make_contract(contract_id="futures_1_common_metals_001")
        settled = _make_contract(
            contract_id="futures_1_medical_002",
            commodity_id="medical",
            direction="LONG",
            strike_price=479,
            quantity=20,
            duration_days=14,
            entry_cost=344,
            accept_day=1,
            maturity_day=15,
            settled=True,
            payoff=-360,
            settlement_day=15,
            settlement_price=461,
        )
        player.futures_state.active_contracts.append(active)
        player.futures_state.settled_contracts.append(settled)
        player.futures_state.total_credits_won = 560
        player.futures_state.total_credits_lost = 360
        # Advance seq twice so the counter is persisted at 2.
        player.futures_state.next_sequence()
        player.futures_state.next_sequence()

        restored = _round_trip(player)
        assert restored.futures_state.active_contracts == [active]
        assert restored.futures_state.settled_contracts == [settled]
        assert restored.futures_state.total_credits_won == 560
        assert restored.futures_state.total_credits_lost == 360
        # Sequence resumes at 3, not 1.
        assert restored.futures_state.next_sequence() == 3

    def test_pre_sa_f2_save_loads_with_empty_futures_state(self) -> None:
        """Legacy save with no ``futures_state`` key loads cleanly."""
        player = Player(
            name="Legacy",
            credits=300,
            current_system_id="nexus_prime",
            ship=_shuttle(),
        )
        mgr = SaveManager()
        payload = mgr._serialize_player(player)
        # Strip the SA-F2 key to simulate a pre-SA-F2 save file.
        payload.pop("futures_state", None)

        restored = mgr._deserialize_player(json.loads(json.dumps(payload)))
        assert isinstance(restored.futures_state, FuturesState)
        assert restored.futures_state.active_contracts == []
        assert restored.futures_state.settled_contracts == []

    def test_malformed_futures_state_loads_as_empty(self) -> None:
        """A non-dict payload for ``futures_state`` migrates to empty."""
        player = Player(
            name="Malformed",
            credits=100,
            current_system_id="nexus_prime",
            ship=_shuttle(),
        )
        mgr = SaveManager()
        payload = mgr._serialize_player(player)
        payload["futures_state"] = "not-a-dict"

        restored = mgr._deserialize_player(json.loads(json.dumps(payload)))
        assert isinstance(restored.futures_state, FuturesState)
        assert restored.futures_state.active_contracts == []
