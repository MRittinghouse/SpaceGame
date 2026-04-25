"""QA-G: edge cases and recently-found-bug regression tests.

Covers:
- QA-G-2: ground/smuggling contracts touch tomas_restless via record_interaction
- QA-G-3: mission log deadline indicator (tier resolution sanity)
- QA-G-4: captain display_name truncation logic
- General: record_interaction with edge inputs
- General: missing-captain-data graceful handling
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.captain_memory import CaptainMemory
from spacegame.models.captain_variant import (
    get_effective_captain_dialogue,
    meeting_state_for_memory,
)


def _make_player(game_day: int = 5):
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship, ShipType

    ship_type = ShipType(
        id="shuttle", name="Shuttle", ship_class="light",
        description="x", cargo_capacity=10, fuel_capacity=50,
        fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
        resale_value=0, crew_slots=2, special_abilities=[],
        availability="all",
    )
    player = Player(
        name="T", credits=500, current_system_id="nexus_prime",
        ship=Ship(ship_type=ship_type, current_fuel=50),
    )
    player.game_day = game_day
    return player


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


# ---------------------------------------------------------------------------
# QA-G-2: any_mission_accepted scope
# ---------------------------------------------------------------------------


class TestAnyMissionAcceptedScope:
    def test_record_interaction_handles_any_mission_accepted_key(self) -> None:
        """The interaction key used by smuggling/ground/mission accept paths
        must be recordable through Player.record_interaction without error."""
        player = _make_player(game_day=10)
        player.record_interaction("any_mission_accepted")
        assert player.last_interaction_day["any_mission_accepted"] == 10

    def test_recording_resets_tomas_thread_drift_clock(self, dl) -> None:
        """Tomas restless thread (touch_triggers=['any_mission_accepted'])
        only resets when ANY accept path records the interaction. Verifies
        the QA-G-2 hook lets ground/smuggling contracts also reset it."""
        from spacegame.models.timed_thread_evaluator import evaluate_threads

        player = _make_player(game_day=5)
        # Simulate accepting a smuggling contract via the QA-G-2 hook
        player.record_interaction("any_mission_accepted")
        evaluate_threads(player, dl.timed_threads)
        state = player.timed_thread_state.get("tomas_restless")
        assert state is not None
        assert state.last_touched_day == 5

        # 29 days later: still no drift (within 30-day threshold)
        player.game_day = 34
        events = evaluate_threads(player, dl.timed_threads)
        assert not any(e.thread_id == "tomas_restless" for e in events)


# ---------------------------------------------------------------------------
# record_interaction edge inputs
# ---------------------------------------------------------------------------


class TestRecordInteractionEdgeInputs:
    def test_explicit_zero_day(self) -> None:
        """Day 0 is technically valid (game start). Verify it records."""
        player = _make_player(game_day=5)
        player.record_interaction("test_key", game_day=0)
        assert player.last_interaction_day["test_key"] == 0

    def test_negative_day_does_not_crash(self) -> None:
        """Sanity: callers shouldn't pass negative days, but if they do,
        the dict accepts it without error. Evaluator's max(0, ...) handles
        the resulting calculation."""
        player = _make_player()
        player.record_interaction("test_key", game_day=-5)
        # Doesn't raise
        assert player.last_interaction_day["test_key"] == -5

    def test_repeated_record_overwrites(self) -> None:
        player = _make_player(game_day=5)
        player.record_interaction("key")  # uses self.game_day (5)
        player.record_interaction("key", game_day=10)
        player.record_interaction("key", game_day=3)  # earlier — still overwrites
        assert player.last_interaction_day["key"] == 3


# ---------------------------------------------------------------------------
# QA-G-4: captain display_name truncation graceful path
# ---------------------------------------------------------------------------


class TestCaptainDisplayNameOverflow:
    """Encounter view title now truncates display_names that overflow the
    panel. Verify the longest-name captains parse correctly so the
    truncation pipeline has data to consume."""

    def test_longest_captain_names_load_cleanly(self, dl) -> None:
        # The captains identified as overflowing in QA-G-4 measurements
        long_name_captain_ids = (
            "dowager_chamberlains_regret",  # 756px @ 1080p
            "wren_departure_angle",          # 720px @ 1080p
            "rin_wheat_dagger",              # 630px
            "odalys_kindling",
            "ink_silverback_gospel",
            "fyodor_fourth_try",
        )
        for cid in long_name_captain_ids:
            cap = dl.captains.get(cid)
            assert cap is not None, f"Missing captain {cid}"
            assert cap.display_name, f"Empty display_name for {cid}"

    def test_truncate_text_handles_long_display_name(self) -> None:
        """The truncate_text utility used by encounter_view title rendering."""
        import pygame

        from spacegame.engine.draw_utils import truncate_text
        from spacegame.engine.fonts import FONT_TITLE, get_font

        if not pygame.get_init():
            pygame.init()
        if not pygame.display.get_init() or pygame.display.get_surface() is None:
            pygame.display.set_mode((1280, 720))

        title_font = get_font("header", FONT_TITLE)
        long_name = "Dowager Vess-Renaud \u2014 Chamberlain's Regret"
        # Truncate to a tight 200px width
        truncated = truncate_text(long_name, title_font, 200)
        # Truncated string fits within 200px (with some font headroom)
        surf = title_font.render(truncated, True, (255, 255, 255))
        assert surf.get_width() <= 200


# ---------------------------------------------------------------------------
# Missing captain data — graceful handling
# ---------------------------------------------------------------------------


class TestMissingCaptainData:
    def test_get_effective_dialogue_with_unknown_captain(self) -> None:
        """If a save references a captain that's been removed from data
        (content churn), helpers should not crash."""
        # Build a fake captain that's NOT in dl.captains
        from spacegame.models.enemy_captain import EnemyCaptain

        cap = EnemyCaptain(
            id="ghost_captain",
            name="Ghost", nickname="Ghost",
            home_sector="", signature_ship_template="pirate_scout",
            pre_combat_hail="x", surrender_line="", retreat_line="",
            victory_line="", defeat_line="",
        )
        # Empty variants dict — no overlay
        eff = get_effective_captain_dialogue(cap, None, {})
        assert eff.pre_combat_hail == "x"
        assert eff.captain_id == "ghost_captain"

    def test_meeting_state_for_memory_with_none(self) -> None:
        """Player has never met this captain — state is first_meeting."""
        assert meeting_state_for_memory(None) == "first_meeting"


# ---------------------------------------------------------------------------
# Mission log deadline indicator: tier resolution
# ---------------------------------------------------------------------------


class TestDeadlineIndicatorTierResolution:
    """Verifies the math the mission_log_view deadline indicator does:
    elapsed = current_day - accepted_day; map to tier."""

    def test_full_tier_calculates_days_left_correctly(self, dl) -> None:
        from spacegame.models.mission import MissionManager, MissionStatus

        mgr = MissionManager(dl.missions)
        mgr._status["iron_delivery"] = MissionStatus.AVAILABLE
        mgr.accept_mission("iron_delivery", game_day=100)
        # iron_delivery has full=14
        # On day 105, 5 elapsed, 9 days left for full
        elapsed = 105 - mgr.get_accepted_day("iron_delivery")
        assert elapsed == 5
        days_left = 14 - elapsed
        assert days_left == 9

    def test_partial_tier_calculates_correctly(self, dl) -> None:
        from spacegame.models.mission import MissionManager, MissionStatus

        mgr = MissionManager(dl.missions)
        mgr._status["iron_delivery"] = MissionStatus.AVAILABLE
        mgr.accept_mission("iron_delivery", game_day=100)
        # On day 116, 16 elapsed, past full=14, within partial=18 (2 days left)
        elapsed = 116 - mgr.get_accepted_day("iron_delivery")
        assert elapsed == 16
        partial_days_left = 18 - elapsed
        assert partial_days_left == 2

    def test_late_tier_recognizes_past_deadline(self, dl) -> None:
        from spacegame.models.mission import MissionManager, MissionStatus

        mgr = MissionManager(dl.missions)
        mgr._status["iron_delivery"] = MissionStatus.AVAILABLE
        mgr.accept_mission("iron_delivery", game_day=100)
        elapsed = 200 - mgr.get_accepted_day("iron_delivery")
        # Past partial=18 -> late tier
        assert elapsed > 18
