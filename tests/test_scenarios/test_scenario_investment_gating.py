"""SL-2 scenario: investment-card gating at the station hub.

Exercises the full filter path:
  Player state (lifetime credits + dialogue flags)
  → is_investment_unlocked
  → station_hub_view location filter
  → final visible-locations list

Per requirements/station_legibility.md, gating is two OR'd gates:
  1. Lifetime credits ≥ 25,000 CR (default threshold)
  2. dialogue_flags["investment_introduced"] is True

A fresh save with a starting shuttle player should see zero investment
cards across all 11 systems with investment locations.
"""

from __future__ import annotations

import pygame
import pygame_gui
import pytest

from spacegame.constants.flags import investment_introduced
from spacegame.data_loader import get_data_loader
from spacegame.models.location import Location
from spacegame.models.station_salience import (
    INVESTMENT_UNLOCK_CREDIT_THRESHOLD,
    is_investment_unlocked,
)
from spacegame.views.station_hub_view import StationHubView
from tests.test_scenarios._helpers import fresh_player


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    """station_hub_view requires pygame fonts and a UIManager."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    yield
    pygame.quit()


def _real_locations(system_id: str) -> list[Location]:
    """Pull the actual locations.json entries for a system."""
    dl = get_data_loader()
    dl.load_all()
    return list(dl.locations.get(system_id, []))


def _real_system(system_id: str):
    """Pull the actual system from data."""
    dl = get_data_loader()
    dl.load_all()
    return dl.systems[system_id]


def _make_hub_view(player, system_id: str) -> StationHubView:
    """Construct a StationHubView with real data for the given system."""
    ui_mgr = pygame_gui.UIManager((1280, 800))
    locations = _real_locations(system_id)
    return StationHubView(
        ui_manager=ui_mgr,
        player=player,
        system=_real_system(system_id),
        locations=locations,
        activity_registry=None,
        data_loader=get_data_loader(),
    )


# Systems that have an investment-typed location per locations.json.
# Crimson Reach has no investment card and is excluded — the gate is a
# no-op there (handled gracefully).
_SYSTEMS_WITH_INVESTMENT: list[str] = [
    "nexus_prime",
    "stellaris_port",
    "breakstone",
    "iron_depths",
    "forgeworks",
    "axiom_labs",
    "nova_research",
    "havens_rest",
    "verdant",
    "crimson_reach",
]


def _has_investment_card(view: StationHubView) -> bool:
    """Did the post-filter location list contain an investment card?"""
    return any(loc.location_type == "investment" for loc in view.locations)


class TestFreshSaveLocksInvestment:
    """A fresh save (zero lifetime credits, no flag) sees zero investment cards."""

    def test_starting_player_has_no_investment_unlocked(self) -> None:
        player = fresh_player()
        assert player.credits_earned_lifetime == 0
        assert is_investment_unlocked(player) is False

    @pytest.mark.parametrize("system_id", _SYSTEMS_WITH_INVESTMENT)
    def test_no_investment_cards_visible_at_any_system(self, system_id: str) -> None:
        """SL-2 acceptance: fresh save → zero investment cards across all 11 systems."""
        player = fresh_player()
        view = _make_hub_view(player, system_id)
        assert not _has_investment_card(view), (
            f"Fresh-save player should not see investment cards at {system_id}"
        )


class TestThresholdUnlock:
    """Crossing the lifetime-credit threshold unlocks investment cards everywhere."""

    @pytest.mark.parametrize("system_id", _SYSTEMS_WITH_INVESTMENT[:3])
    def test_at_threshold_unlocks_investment(self, system_id: str) -> None:
        """Exactly 25,000 lifetime credits is the threshold — boundary inclusive."""
        player = fresh_player()
        player.credits_earned_lifetime = INVESTMENT_UNLOCK_CREDIT_THRESHOLD
        view = _make_hub_view(player, system_id)
        # Investment may or may not exist at this system (Crimson Reach: no);
        # but if it does in source data, filter should keep it after threshold.
        source_has_investment = any(
            loc.location_type == "investment" for loc in _real_locations(system_id)
        )
        assert _has_investment_card(view) is source_has_investment

    def test_below_threshold_still_locked(self) -> None:
        """24,999 lifetime credits is one short of the threshold — still locked."""
        player = fresh_player()
        player.credits_earned_lifetime = INVESTMENT_UNLOCK_CREDIT_THRESHOLD - 1
        view = _make_hub_view(player, "nexus_prime")
        assert not _has_investment_card(view)


class TestFlagUnlock:
    """The investment_introduced flag unlocks regardless of credit balance."""

    def test_flag_set_unlocks_with_low_credits(self) -> None:
        """Cargo-Broker mission fires before the player has 25k → cards unlock."""
        player = fresh_player()
        player.credits_earned_lifetime = 1_000  # Far below threshold
        player.dialogue_flags[investment_introduced()] = True
        view = _make_hub_view(player, "nexus_prime")
        assert _has_investment_card(view), (
            "Flag-set player should see investment cards regardless of credits"
        )

    def test_flag_set_to_false_does_not_unlock(self) -> None:
        """A flag explicitly set False does not unlock (only True does)."""
        player = fresh_player()
        player.credits_earned_lifetime = 1_000
        player.dialogue_flags[investment_introduced()] = False
        view = _make_hub_view(player, "nexus_prime")
        assert not _has_investment_card(view)


class TestFulcrumNoInvestment:
    """The Fulcrum has no investment card in source data — the gate is a no-op.

    Per the SL doc's open-question audit (corrected here): the one system
    without an investment-typed location is `the_fulcrum`, not Crimson
    Reach. The gate must handle this gracefully — no card appears
    regardless of player state, and non-investment cards still render.
    """

    def test_fulcrum_locked_state(self) -> None:
        player = fresh_player()
        view = _make_hub_view(player, "the_fulcrum")
        assert not _has_investment_card(view)
        # Sanity check: other location types still present.
        types = {loc.location_type for loc in view.locations}
        assert "market" in types

    def test_fulcrum_unlocked_state(self) -> None:
        """Even with investment unlocked, no investment card exists at the Fulcrum."""
        player = fresh_player()
        player.credits_earned_lifetime = 100_000
        view = _make_hub_view(player, "the_fulcrum")
        assert not _has_investment_card(view)
        types = {loc.location_type for loc in view.locations}
        assert "market" in types
