"""RC-1: CaptainMemory model + Player wiring + save/load tests."""

from __future__ import annotations

import pytest

from spacegame.models.captain_memory import (
    OUTCOME_BRIBED,
    OUTCOME_DEFEAT,
    OUTCOME_FLED,
    OUTCOME_NEGOTIATED,
    OUTCOME_VICTORY,
    RESOLUTION_THRESHOLD,
    STATUS_ACTIVE,
    STATUS_BRIBED_OFF,
    STATUS_DEFEATED,
    STATUS_TRUCE,
    STATUS_WANDERER,
    VALID_STATUSES,
    CaptainMemory,
)


# ---------------------------------------------------------------------------
# Model basics
# ---------------------------------------------------------------------------


class TestCaptainMemoryDefaults:
    def test_fresh_memory_is_unmet(self) -> None:
        mem = CaptainMemory(captain_id="vela_wolfs_ear")
        assert mem.encounter_count == 0
        assert mem.last_outcome == ""
        assert mem.status == STATUS_ACTIVE
        assert mem.is_first_meeting
        assert not mem.is_resolved

    def test_status_constants_in_registry(self) -> None:
        for s in (
            STATUS_ACTIVE,
            STATUS_DEFEATED,
            STATUS_TRUCE,
            STATUS_BRIBED_OFF,
            STATUS_WANDERER,
        ):
            assert s in VALID_STATUSES

    def test_round_trip(self) -> None:
        original = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=2,
            last_outcome=OUTCOME_NEGOTIATED,
            status=STATUS_TRUCE,
            first_seen_day=10,
            last_seen_day=23,
        )
        restored = CaptainMemory.from_dict(original.to_dict())
        assert restored == original

    def test_from_dict_falls_back_to_active_for_unknown_status(self) -> None:
        mem = CaptainMemory.from_dict(
            {"captain_id": "x", "status": "garbage_status"}
        )
        assert mem.status == STATUS_ACTIVE

    def test_from_dict_handles_missing_fields(self) -> None:
        mem = CaptainMemory.from_dict({"captain_id": "x"})
        assert mem.encounter_count == 0
        assert mem.first_seen_day == 0
        assert mem.last_seen_day == 0
        assert mem.last_outcome == ""


# ---------------------------------------------------------------------------
# Resolution rules
# ---------------------------------------------------------------------------


class TestResolutionRules:
    def test_victory_resolves_to_defeated(self) -> None:
        mem = CaptainMemory(captain_id="x")
        mem.record_encounter(OUTCOME_VICTORY, game_day=5)
        assert mem.status == STATUS_DEFEATED
        assert mem.is_resolved
        assert mem.encounter_count == 1
        assert mem.first_seen_day == 5
        assert mem.last_seen_day == 5

    def test_negotiation_resolves_to_truce(self) -> None:
        mem = CaptainMemory(captain_id="x")
        mem.record_encounter(OUTCOME_NEGOTIATED, game_day=8)
        assert mem.status == STATUS_TRUCE
        assert mem.is_resolved

    def test_bribe_resolves_to_bribed_off(self) -> None:
        mem = CaptainMemory(captain_id="x")
        mem.record_encounter(OUTCOME_BRIBED, game_day=12)
        assert mem.status == STATUS_BRIBED_OFF
        assert mem.is_resolved

    def test_defeat_does_not_resolve_immediately(self) -> None:
        mem = CaptainMemory(captain_id="x")
        mem.record_encounter(OUTCOME_DEFEAT, game_day=1)
        assert mem.status == STATUS_ACTIVE
        assert mem.encounter_count == 1
        assert mem.last_outcome == OUTCOME_DEFEAT

    def test_flee_does_not_resolve_immediately(self) -> None:
        mem = CaptainMemory(captain_id="x")
        mem.record_encounter(OUTCOME_FLED, game_day=1)
        assert mem.status == STATUS_ACTIVE
        assert mem.encounter_count == 1


class TestThresholdAutoRetire:
    def test_three_unresolved_encounters_become_wanderer(self) -> None:
        mem = CaptainMemory(captain_id="x")
        mem.record_encounter(OUTCOME_FLED, game_day=1)
        mem.record_encounter(OUTCOME_DEFEAT, game_day=4)
        mem.record_encounter(OUTCOME_FLED, game_day=8)
        assert mem.encounter_count == RESOLUTION_THRESHOLD
        assert mem.status == STATUS_WANDERER
        assert mem.is_resolved

    def test_two_unresolved_stays_active(self) -> None:
        mem = CaptainMemory(captain_id="x")
        mem.record_encounter(OUTCOME_FLED, game_day=1)
        mem.record_encounter(OUTCOME_DEFEAT, game_day=4)
        assert mem.status == STATUS_ACTIVE

    def test_resolution_does_not_get_overwritten_by_later_encounter(self) -> None:
        """Once resolved, future record_encounter calls don't change status."""
        mem = CaptainMemory(captain_id="x")
        mem.record_encounter(OUTCOME_VICTORY, game_day=1)
        assert mem.status == STATUS_DEFEATED
        # Forced re-encounter (e.g. scripted) shouldn't reverse resolution
        mem.record_encounter(OUTCOME_NEGOTIATED, game_day=10)
        assert mem.status == STATUS_DEFEATED


class TestDayStamps:
    def test_first_seen_only_set_on_first_encounter(self) -> None:
        mem = CaptainMemory(captain_id="x")
        mem.record_encounter(OUTCOME_FLED, game_day=5)
        mem.record_encounter(OUTCOME_FLED, game_day=12)
        assert mem.first_seen_day == 5
        assert mem.last_seen_day == 12


# ---------------------------------------------------------------------------
# Player wiring
# ---------------------------------------------------------------------------


class TestPlayerCaptainMemoryAPI:
    def _make_player(self):
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        ship_type = ShipType(
            id="shuttle", name="Shuttle", ship_class="light",
            description="x", cargo_capacity=10, fuel_capacity=50,
            fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
            resale_value=0, crew_slots=2, special_abilities=[],
            availability="all",
        )
        ship = Ship(ship_type=ship_type, current_fuel=50)
        return Player(
            name="Test", credits=500, current_system_id="nexus_prime", ship=ship
        )

    def test_get_captain_memory_creates_on_first_access(self) -> None:
        player = self._make_player()
        assert "vela_wolfs_ear" not in player.captain_memory
        mem = player.get_captain_memory("vela_wolfs_ear")
        assert mem.captain_id == "vela_wolfs_ear"
        assert mem.encounter_count == 0
        # Subsequent access returns the same instance
        assert player.get_captain_memory("vela_wolfs_ear") is mem

    def test_record_captain_encounter_updates_state(self) -> None:
        player = self._make_player()
        player.game_day = 7
        mem = player.record_captain_encounter("ngozi_pale_reckoning", OUTCOME_VICTORY)
        assert mem.status == STATUS_DEFEATED
        assert mem.encounter_count == 1
        assert mem.first_seen_day == 7
        # Persists in player dict
        assert player.captain_memory["ngozi_pale_reckoning"] is mem


# ---------------------------------------------------------------------------
# Save/load round-trip
# ---------------------------------------------------------------------------


class TestCaptainMemorySerialization:
    """Captain memory survives the dict serialization layer used by saves.

    The full save_game() path drags in markets / events / playtime / etc;
    these tests focus on the captain_memory portion in isolation by
    exercising the to_dict / from_dict shape directly through a serialize
    + reconstruct cycle.
    """

    def test_dict_serialization_roundtrip(self) -> None:
        memory = {
            "vela_wolfs_ear": CaptainMemory(
                captain_id="vela_wolfs_ear",
                encounter_count=1,
                last_outcome=OUTCOME_NEGOTIATED,
                status=STATUS_TRUCE,
                first_seen_day=5,
                last_seen_day=5,
            ),
            "anatolia_kestrel_crow": CaptainMemory(
                captain_id="anatolia_kestrel_crow",
                encounter_count=1,
                last_outcome=OUTCOME_VICTORY,
                status=STATUS_DEFEATED,
                first_seen_day=12,
                last_seen_day=12,
            ),
        }
        # Serialize as save_manager does
        serialized = {cid: mem.to_dict() for cid, mem in memory.items()}
        # Reconstruct as load path does
        restored = {
            cid: CaptainMemory.from_dict(d) for cid, d in serialized.items()
        }
        assert restored == memory

    def test_save_manager_includes_captain_memory_in_dict(self, tmp_path) -> None:
        """The save dict written by save_game should contain a captain_memory
        key with serialized memory contents."""
        from spacegame.models.market import Market
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType
        from spacegame.save_manager import SaveManager

        ship_type = ShipType(
            id="shuttle", name="Shuttle", ship_class="light",
            description="x", cargo_capacity=10, fuel_capacity=50,
            fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
            resale_value=0, crew_slots=2, special_abilities=[],
            availability="all",
        )
        player = Player(
            name="Test", credits=500, current_system_id="nexus_prime",
            ship=Ship(ship_type=ship_type, current_fuel=50),
        )
        player.game_day = 8
        player.record_captain_encounter("vela_wolfs_ear", OUTCOME_VICTORY)

        sm = SaveManager(save_directory=tmp_path)
        ok = sm.save_game(
            slot=0,
            player=player,
            markets={},
            active_events={},
            playtime_seconds=0,
        )
        assert ok

        import json
        save_path = sm.get_save_file_path(0)
        raw = json.loads(save_path.read_text(encoding="utf-8"))
        assert "captain_memory" in raw["player"]
        cm = raw["player"]["captain_memory"]
        assert "vela_wolfs_ear" in cm
        assert cm["vela_wolfs_ear"]["status"] == STATUS_DEFEATED
        assert cm["vela_wolfs_ear"]["last_outcome"] == OUTCOME_VICTORY

    def test_load_reconstructs_captain_memory_objects(self, tmp_path) -> None:
        """Round-trip via save_manager preserves CaptainMemory state."""
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType
        from spacegame.save_manager import SaveManager

        ship_type = ShipType(
            id="shuttle", name="Shuttle", ship_class="light",
            description="x", cargo_capacity=10, fuel_capacity=50,
            fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
            resale_value=0, crew_slots=2, special_abilities=[],
            availability="all",
        )
        player = Player(
            name="Test", credits=500, current_system_id="nexus_prime",
            ship=Ship(ship_type=ship_type, current_fuel=50),
        )
        player.game_day = 8
        player.record_captain_encounter("ngozi_pale_reckoning", OUTCOME_NEGOTIATED)

        sm = SaveManager(save_directory=tmp_path)
        sm.save_game(
            slot=0, player=player, markets={}, active_events={}, playtime_seconds=0
        )
        loaded = sm.load_game(slot=0)
        assert loaded is not None
        loaded_player = loaded["player"]
        assert isinstance(loaded_player.captain_memory["ngozi_pale_reckoning"], CaptainMemory)
        assert loaded_player.captain_memory["ngozi_pale_reckoning"].status == STATUS_TRUCE

    def test_legacy_save_without_captain_memory_loads_empty(self, tmp_path) -> None:
        """Saves from before RC-1 lack the captain_memory key under
        player. Loading them should silently default to an empty dict."""
        import json

        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType
        from spacegame.save_manager import SaveManager

        ship_type = ShipType(
            id="shuttle", name="Shuttle", ship_class="light",
            description="x", cargo_capacity=10, fuel_capacity=50,
            fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
            resale_value=0, crew_slots=2, special_abilities=[],
            availability="all",
        )
        player = Player(
            name="Test", credits=500, current_system_id="nexus_prime",
            ship=Ship(ship_type=ship_type, current_fuel=50),
        )

        sm = SaveManager(save_directory=tmp_path)
        sm.save_game(
            slot=0, player=player, markets={}, active_events={}, playtime_seconds=0
        )
        save_path = sm.get_save_file_path(0)
        raw = json.loads(save_path.read_text(encoding="utf-8"))
        raw["player"].pop("captain_memory", None)
        save_path.write_text(json.dumps(raw), encoding="utf-8")

        loaded = sm.load_game(slot=0)
        assert loaded is not None
        assert loaded["player"].captain_memory == {}
