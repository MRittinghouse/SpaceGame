"""End-to-end scenario: dilemma scar mechanism (A2-11).

This test proves the scar-category ChatterLine mechanism is testable without
importing the dilemma resolution view or any collision/engine machinery.

Symbols this test deliberately does NOT import (anti-backslide anchor):
  - DilemmaResolutionView
  - check_collision

The scar mechanism depends only on:
  1. flags.lens_closed() producing the correct flag string.
  2. player.dialogue_flags accepting that flag.
  3. StationChatterManager.get_chatter filtering by required_flags.
  4. reset_shown allowing the scar line to recur (one_shot=False semantics).

No real dilemma data, no engine tick, no view layer.
"""

from spacegame.constants import flags
from spacegame.models.station_chatter import ChatterLine, StationChatterManager

_TEST_LENS_ID = "test_lens"
_SYSTEM_ID = "nexus_prime"


def _make_scar_chatter_manager() -> tuple[StationChatterManager, ChatterLine]:
    """Return a manager with a single scar line gated on the test lens flag."""
    scar_line = ChatterLine(
        id="np_scar_fixture_01",
        system_id=_SYSTEM_ID,
        text="The contract broker is still running the freight route. Same as before.",
        category="scar",
        weight=7,
        required_flags=[flags.lens_closed(_TEST_LENS_ID)],
        one_shot=False,
    )
    return StationChatterManager([scar_line]), scar_line


class TestDilemmaScarsEndToEnd:
    """Scar lines surface when a lens closes, and recur on subsequent dock visits."""

    def test_scar_excluded_before_lens_closes(self) -> None:
        """Before the lens closes, the scar line is invisible."""
        manager, _ = _make_scar_chatter_manager()
        player_flags: dict[str, bool] = {}

        results = manager.get_chatter(
            _SYSTEM_ID, player_rep=0, active_event_types=[], count=3, player_flags=player_flags
        )
        assert results == [], "Scar line must be hidden before the lens closes"

    def test_scar_included_after_lens_closes(self) -> None:
        """After the lens closes, the scar line becomes eligible."""
        manager, scar_line = _make_scar_chatter_manager()

        # Simulate dilemma resolution closing the lens by setting the flag directly.
        # No DilemmaResolutionView, no check_collision — just the flag.
        player_flags = {flags.lens_closed(_TEST_LENS_ID): True}

        results = manager.get_chatter(
            _SYSTEM_ID, player_rep=0, active_event_types=[], count=3, player_flags=player_flags
        )
        assert len(results) == 1, "Scar line must surface after lens closes"
        assert scar_line.text in results, "Scar line text must match"

    def test_scar_recurs_across_dock_visits(self) -> None:
        """Scar line appears on a second dock visit after reset_shown (not retired)."""
        manager, _scar_line = _make_scar_chatter_manager()
        player_flags = {flags.lens_closed(_TEST_LENS_ID): True}

        first = manager.get_chatter(
            _SYSTEM_ID, player_rep=0, active_event_types=[], count=1, player_flags=player_flags
        )
        assert len(first) == 1, "Scar line must appear on first dock"

        # Simulate leaving and returning to the station (new dock resets shown tracking)
        manager.reset_shown(_SYSTEM_ID)

        second = manager.get_chatter(
            _SYSTEM_ID, player_rep=0, active_event_types=[], count=1, player_flags=player_flags
        )
        assert len(second) == 1, "Scar line must recur on second dock visit (one_shot=False)"
        assert second[0] == first[0], "Same scar line text should appear both visits"

    def test_scar_flag_string_matches_lens_closed_helper(self) -> None:
        """The flag string used in required_flags must match flags.lens_closed()."""
        flag_string = flags.lens_closed(_TEST_LENS_ID)
        assert flag_string == "lens_closed_test_lens", (
            f"flags.lens_closed('{_TEST_LENS_ID}') produced '{flag_string}'; "
            "expected 'lens_closed_test_lens'. The helper and the data file must agree."
        )
