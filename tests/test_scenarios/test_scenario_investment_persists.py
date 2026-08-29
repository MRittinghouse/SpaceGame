"""A2-4 scenario coverage for LensInvestment persistence and consumption.

Two mechanisms are proven here:

  - **Persistence.** Investment survives a real SaveManager round-trip; a
    legacy save without a ``lens_investment`` key loads with an empty
    state and never crashes.
  - **Mechanism proof for oblique readout.** A test-local stub consumer
    reads investment via the public query API and returns different
    strings for a player above vs below a threshold. This is *only* proof
    that the API is consumable by an oblique-readout system — the real
    NPC-address / offered-work reactor is the scope of the sibling sprint
    A2-4A.
"""

from __future__ import annotations

import json

from spacegame.models.lens_investment import LensInvestment
from spacegame.models.player import Player
from spacegame.save_manager import SaveManager
from tests.test_scenarios._helpers import fresh_player, round_trip_save


class TestInvestmentSaveLoadRoundTrip:
    def test_raised_values_survive_save_and_load(self) -> None:
        player = fresh_player()
        player.lens_investment.add_investment("wealth", 12, source="scenario")
        player.lens_investment.add_investment("vengeance", 4, source="scenario")
        player.lens_investment.add_investment("legacy", 27, source="scenario")

        restored = round_trip_save(player)

        assert restored.lens_investment.get_investment("wealth") == 12
        assert restored.lens_investment.get_investment("vengeance") == 4
        assert restored.lens_investment.get_investment("legacy") == 27

    def test_default_player_has_empty_lens_investment(self) -> None:
        """A brand-new Player has an empty LensInvestment, not None."""
        player = fresh_player()
        assert isinstance(player.lens_investment, LensInvestment)
        assert player.lens_investment.get_investment("any") == 0

    def test_default_player_round_trips_with_no_investment_recorded(self) -> None:
        player = fresh_player()
        restored = round_trip_save(player)
        assert restored.lens_investment.get_investment("wealth") == 0

    def test_legacy_save_without_lens_investment_key_loads_with_empty_state(
        self,
    ) -> None:
        """AC3: an older save with no ``lens_investment`` key must load cleanly."""
        player = fresh_player()
        mgr = SaveManager()
        payload = mgr._serialize_player(player)
        # Simulate a save produced before A2-4 shipped.
        payload.pop("lens_investment", None)
        json_str = json.dumps(payload)
        restored = mgr._deserialize_player(json.loads(json_str))

        assert isinstance(restored.lens_investment, LensInvestment)
        assert restored.lens_investment.get_investment("wealth") == 0
        assert restored.lens_investment.get_investment("vengeance") == 0

    def test_malformed_lens_investment_payload_loads_as_empty(self) -> None:
        """Corrupted or unexpected shapes must not crash load."""
        player = fresh_player()
        mgr = SaveManager()
        payload = mgr._serialize_player(player)
        payload["lens_investment"] = {"values": {"wealth": "corrupt", "legacy": -3}}
        json_str = json.dumps(payload)
        restored = mgr._deserialize_player(json.loads(json_str))

        assert restored.lens_investment.get_investment("wealth") == 0
        assert restored.lens_investment.get_investment("legacy") == 0


def _select_line(
    player: Player,
    lens_id: str,
    threshold: int,
    low_line: str,
    high_line: str,
) -> str:
    """Test-local stub for an oblique NPC-line selector.

    A2-4 owns the query API; A2-4A owns the real reactor surface. This
    stub exists only to prove the API is *consumable* by a caller that
    picks content based on investment thresholds — the shape a real
    reactor is expected to take.
    """
    if player.lens_investment.is_at_or_above(lens_id, threshold):
        return high_line
    return low_line


class TestObliqueReadoutMechanism:
    def test_stub_consumer_picks_different_line_based_on_investment_threshold(
        self,
    ) -> None:
        """AC5 (mechanism proof): the query API drives an oblique selector."""
        low_line = "Rough season."
        high_line = "You've made your name."

        low_player = fresh_player(name="LowInvestment")
        high_player = fresh_player(name="HighInvestment")
        high_player.lens_investment.add_investment("wealth", 50, source="scenario")

        threshold = 25
        assert _select_line(low_player, "wealth", threshold, low_line, high_line) == low_line
        assert _select_line(high_player, "wealth", threshold, low_line, high_line) == high_line
        assert _select_line(low_player, "wealth", threshold, low_line, high_line) != _select_line(
            high_player, "wealth", threshold, low_line, high_line
        )

    def test_stub_consumer_reads_via_public_query_only(self) -> None:
        """The stub never touches ``_values`` directly — proves API sufficiency."""
        import inspect

        source = inspect.getsource(_select_line)
        assert "_values" not in source, (
            "The mechanism stub must consume LensInvestment through its public "
            "methods, not by reading the underscore-prefixed dict."
        )
