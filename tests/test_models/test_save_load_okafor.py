"""Save/load round-trip coverage for SA-R1 Okafor research-patronage state.

Verifies:
  - A populated OkaforResearchState round-trips byte-clean (acceptance #10).
  - Active projects, holdings, royalty schedule, and Kweon's
    relationship value all round-trip.
  - A legacy save with no ``okafor_research_state`` key loads as None
    (no errors).
"""

from __future__ import annotations

import json

from spacegame.data_loader import get_data_loader
from spacegame.models.okafor_research import (
    ActiveProject,
    OkaforResearchState,
    PatentHolding,
)
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


class TestOkaforSaveLoad:
    def test_default_state_round_trips_as_none(self) -> None:
        # Default Player has no okafor_research_state — behaves like a
        # freshly-created game that hasn't entered the venue.
        player = Player(
            name="Tester", credits=500, current_system_id="nexus_prime", ship=_shuttle()
        )
        restored = _round_trip(player)
        assert restored.okafor_research_state is None

    def test_populated_state_round_trip(self) -> None:
        """Acceptance #10: two active, one held + one licensed, kweon=3."""
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="axiom_labs",
            ship=_shuttle(),
        )
        player.okafor_research_state = OkaforResearchState(
            active_projects={
                "mid_neural_synthesis_protocol": ActiveProject(
                    template_id="mid_neural_synthesis_protocol",
                    accept_day=10,
                    duration_days=12,
                    cost_paid=28_000,
                    collaborators=["nuri_solberg"],
                ),
                "high_quantum_sensor_capstone": ActiveProject(
                    template_id="high_quantum_sensor_capstone",
                    accept_day=15,
                    duration_days=22,
                    cost_paid=85_000,
                    collaborators=[],
                ),
            },
            holdings=[
                PatentHolding(
                    holding_id="mid_orbital_propulsion_efficiency_30",
                    template_id="mid_orbital_propulsion_efficiency",
                    state="held",
                    success_payout=80_000,
                ),
                PatentHolding(
                    holding_id="low_protein_folding_replication_5",
                    template_id="low_protein_folding_replication",
                    state="licensed",
                    success_payout=14_000,
                    license_start_day=20,
                    next_royalty_day=30,
                ),
            ],
            kweon_relationship_value=3,
            slot_seed_window=1,
            slot_offers=[
                "mid_neural_synthesis_protocol",
                "high_quantum_sensor_capstone",
                "low_protein_folding_replication",
            ],
            completed_count=2,
            failed_count=1,
        )
        restored = _round_trip(player)
        s = restored.okafor_research_state
        assert s is not None
        assert s.kweon_relationship_value == 3
        assert s.slot_seed_window == 1
        assert s.completed_count == 2
        assert s.failed_count == 1
        assert "mid_neural_synthesis_protocol" in s.active_projects
        active = s.active_projects["mid_neural_synthesis_protocol"]
        assert active.accept_day == 10
        assert active.duration_days == 12
        assert active.cost_paid == 28_000
        assert active.collaborators == ["nuri_solberg"]
        # Holdings preserved including license schedule.
        assert len(s.holdings) == 2
        held = next(h for h in s.holdings if h.state == "held")
        licensed = next(h for h in s.holdings if h.state == "licensed")
        assert held.success_payout == 80_000
        assert licensed.next_royalty_day == 30
        assert licensed.license_start_day == 20

    def test_legacy_save_with_no_okafor_key_loads_as_none(self) -> None:
        """Acceptance #10 (latter half): saves predating SA-R1 must load."""
        player = Player(
            name="Tester",
            credits=500,
            current_system_id="nexus_prime",
            ship=_shuttle(),
        )
        mgr = SaveManager()
        data = mgr._serialize_player(player)
        data.pop("okafor_research_state", None)
        restored = mgr._deserialize_player(json.loads(json.dumps(data)))
        assert restored.okafor_research_state is None
