"""A2-4A scenario: oblique readout -- lens investment changes Malia's greeting.

Exercises the full production path:
  Player accumulates lens investment via lens_investment.record_action
  -> LensReactor.choose_variant reads the investment state
  -> WreckersGuildView._greeting_lines returns a lens-specific line
  -> The greeting differs from the fresh-player default

This is the AC5 assertion A2-4 originally targeted. The view is real;
the DataLoader is real; the LensReactor is real. No stubs.

Note: A2-4B (record_lens_action facade) is not yet merged. Investment is
driven here via player.lens_investment.record_action(tag, amount, lenses)
directly -- a legal path from test code since the compliance scanner does not
scan tests/. When A2-4B lands, the facade call can replace the direct call;
the assertions remain unchanged.
"""

from __future__ import annotations

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.data_loader import get_data_loader
from spacegame.models.mission import MissionManager
from spacegame.views.wreckers_guild_view import WreckersGuildView
from tests.test_scenarios._helpers import fresh_player

_DEFAULT_LINE = (
    "Heard you do real work. Guild takes a cut, you take the rest. "
    "Standing builds with completed contracts. Say the word."
)

_WEALTH_MID_LINES = {
    "Heard you moved thirty tonnes last week. Guild takes a cut of contract work, same as anyone. Say the word.",
    "You know the numbers. Guild route work runs fifteen percent above standard rates at Journeyman. Think on it.",
    "Contract pays on delivery. Better margin than spot runs. You know how the math goes.",
}
_WEALTH_HIGH_LINES = {
    "At your volume, Guild affiliation pays back inside one job. What you get beyond that is access to contracts that never post open.",
    "Thirty percent of Guild-exclusive contracts don't hit the open market. You've been trading on what's left.",
    "Running at scale, the Guild cut's noise. The standing is what matters. Opens the board to you.",
}
_COMMUNITY_MID_LINES = {
    "You know how many families run on what the Guild moves? Contract work keeps supply lines honest. Say the word.",
    "Guild routes keep three dock crews employed through the dry season. Real work, real people. You in?",
    "Salvage work you'd be running keeps parts flowing to settlements that can't buy new. Counts for something.",
}
_VENGEANCE_MID_LINES = {
    "Guild contracts put you in places. If you're working something, access is worth more than it looks.",
    "You're patient. That counts. Contract work builds access. Access turns up things people don't expect to turn up.",
    "Guild routes cover eleven systems in the Reach. If you've got a list, that's likely useful.",
}


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.HIDDEN)
    yield
    pygame.quit()


def _make_view(player) -> WreckersGuildView:
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    mm = MissionManager(missions=[])
    return WreckersGuildView(
        ui_manager=ui_manager,
        player=player,
        mission_manager=mm,
    )


def _add_investment(player, action_tag: str, amount: int) -> None:
    """Drive lens investment via the real record_action path (A2-4B fallback)."""
    dl = get_data_loader()
    dl.load_all()
    player.lens_investment.record_action(action_tag, amount, dl.lenses)


class TestObliqueReadout:
    def test_default_greeting_for_fresh_player_unchanged(self) -> None:
        """A fresh player with zero investment sees the unmodified default greeting."""
        player = fresh_player(name="FreshPilot")
        view = _make_view(player)
        lines = view._greeting_lines()
        spoken = lines[1]  # Stage direction is lines[0]; spoken line is lines[1]
        assert spoken == _DEFAULT_LINE, (
            f"Fresh player should see unmodified default.\n"
            f"Expected: {_DEFAULT_LINE!r}\n"
            f"Got:      {spoken!r}"
        )

    def test_full_production_path_wealth_lens_varies_greeting(self) -> None:
        """Real Player + real DataLoader + real WreckersGuildView; wealth investment changes Malia."""
        player = fresh_player(name="WealthPilot")
        _add_investment(player, "sold_cargo", 45)  # Wealth crosses threshold=40
        view = _make_view(player)
        lines = view._greeting_lines()
        spoken = lines[1]
        assert spoken in _WEALTH_MID_LINES, (
            f"Expected a wealth-mid variant after investment=45.\nGot: {spoken!r}"
        )
        assert spoken != _DEFAULT_LINE, "Wealth-invested player must not see the default"

    def test_full_production_path_vengeance_lens_varies_greeting(self) -> None:
        """Vengeance lens works independently -- reactor is lens-general, not Wealth-specific."""
        player = fresh_player(name="VengeancePilot")
        # combat_victory_named_target is in vengeance.investment_from per lenses.json
        _add_investment(player, "combat_victory_named_target", 45)
        view = _make_view(player)
        lines = view._greeting_lines()
        spoken = lines[1]
        assert spoken in _VENGEANCE_MID_LINES, (
            f"Expected a vengeance-mid variant after investment=45.\nGot: {spoken!r}"
        )
        assert spoken != _DEFAULT_LINE, "Vengeance-invested player must not see the default"

    def test_full_production_path_community_lens_varies_greeting(self) -> None:
        """Community lens works -- the venue-aligned lens proves alignment is not hard-coded."""
        player = fresh_player(name="CommunityPilot")
        # wreckers_guild_contract_completed is in community.investment_from per lenses.json
        _add_investment(player, "wreckers_guild_contract_completed", 45)
        view = _make_view(player)
        lines = view._greeting_lines()
        spoken = lines[1]
        assert spoken in _COMMUNITY_MID_LINES, (
            f"Expected a community-mid variant after investment=45.\nGot: {spoken!r}"
        )
        assert spoken != _DEFAULT_LINE, "Community-invested player must not see the default"

    def test_wealth_investment_changes_malia_greeting(self) -> None:
        """AC4 wire-in: scenario drives wealth investment and asserts the greeting changes."""
        player = fresh_player(name="TestPilot")
        _add_investment(player, "sold_cargo", 50)
        view = _make_view(player)
        lines = view._greeting_lines()
        assert len(lines) >= 2, "Must return at least 2 lines (stage direction + spoken)"
        spoken = lines[1]
        all_wealth = _WEALTH_MID_LINES | _WEALTH_HIGH_LINES
        assert spoken in all_wealth, (
            f"With wealth=50, expected a wealth pool variant.\nGot: {spoken!r}"
        )

    def test_high_wealth_returns_high_tier_line(self) -> None:
        """Investment at 85 qualifies both mid and high tiers; high tier must win."""
        player = fresh_player(name="HighWealthPilot")
        _add_investment(player, "sold_cargo", 85)
        view = _make_view(player)
        lines = view._greeting_lines()
        spoken = lines[1]
        assert spoken in _WEALTH_HIGH_LINES, (
            f"With wealth=85, expected a high-tier variant.\nGot: {spoken!r}"
        )

    def test_stage_direction_line_is_always_fixed(self) -> None:
        """The stage-direction first line is never replaced by the reactor."""
        expected_stage = "Malia Torres, Wrench, looks up from a stripped reactor housing."
        for name, tag, amount in [
            ("FreshPilot", None, 0),
            ("WealthPilot", "sold_cargo", 60),
            ("VengeancePilot", "combat_victory_named_target", 60),
        ]:
            player = fresh_player(name=name)
            if tag:
                _add_investment(player, tag, amount)
            view = _make_view(player)
            lines = view._greeting_lines()
            assert lines[0] == expected_stage, (
                f"Stage direction must be fixed for {name}.\nGot: {lines[0]!r}"
            )
