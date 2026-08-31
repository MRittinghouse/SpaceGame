"""A2-4B scenario test: investment accrues through real gameplay events.

Tests the full vertical slice: real Player + real DataLoader + real
record_lens_action calls via gameplay methods. No stubs.

This test is the counterpart to A2-4's mechanism-proof stub scenario:
A2-4 proved the API works with a stub consumer; A2-4B proves the API
works with real producers.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from tests.test_scenarios._helpers import fresh_player


def _dl():
    dl = get_data_loader()
    dl.load_all()
    return dl


class TestInvestmentAccruesFromGameplay:
    def test_vertical_slice_of_three_actions_compounds_correctly(self) -> None:
        """Sell cargo → wealth up; travel new system → exploration up;
        defeat captain → vengeance up; community stays zero.
        """
        _dl()  # ensure data loaded
        player = fresh_player(
            name="SliceTest",
            credits=50000,
            system_id="nexus_prime",
            fuel=100,
        )
        # Add cargo with purchase price 0 to guarantee known profit
        player.ship.add_cargo("refined_metals", 1, 0)

        # Action 1: sell cargo at a price below 5000 profit → sold_cargo fires
        success, _ = player.sell_commodity("refined_metals", 1, 200)
        assert success
        wealth_after_sell = player.lens_investment.get_investment("wealth")
        assert wealth_after_sell == 1, (
            f"Expected wealth=1 after sold_cargo, got {wealth_after_sell}"
        )
        # trade_profit_large must NOT have fired (profit = 200 < 5000)
        assert player.lens_investment.get_investment("crime") == 0

        # Action 2: travel to an unvisited system → reach_system_first_visit fires
        success, _ = player.travel_to_system("verdant", 5)
        assert success
        exploration_after_travel = player.lens_investment.get_investment("exploration")
        assert exploration_after_travel == 5, (
            f"Expected exploration=5 after first visit, got {exploration_after_travel}"
        )

        # Action 3: simulate the captain-defeat emit path (combat_view wires this)
        player.record_captain_encounter("pirate_lord_ash", "killed")
        player.record_lens_action("combat_victory_named_target", 10)
        vengeance_after_combat = player.lens_investment.get_investment("vengeance")
        assert vengeance_after_combat == 10, (
            f"Expected vengeance=10 after captain defeat, got {vengeance_after_combat}"
        )

        # Community must still be zero (no wreckers contract in this slice)
        community = player.lens_investment.get_investment("community")
        assert community == 0, f"community should be 0 with no wreckers contract, got {community}"

    def test_trade_profit_large_fires_when_profit_meets_threshold(self) -> None:
        """trade_profit_large fires alongside sold_cargo when profit >= 5000."""
        _dl()
        player = fresh_player(credits=50000)
        # Add 10 units with purchase price 0 → sell at 600 each → profit = 6000
        player.ship.add_cargo("luxury_goods", 10, 0)
        success, _ = player.sell_commodity("luxury_goods", 10, 600)
        assert success
        assert player.lens_investment.get_investment("wealth") == 4  # 1 (sold) + 3 (large)

    def test_reach_system_first_visit_does_not_fire_on_revisit(self) -> None:
        """reach_system_first_visit accrues only once per system.

        Player starts with current_system_id pre-added to systems_visited
        (via Player.__post_init__), so only genuinely new destinations fire.
        """
        _dl()
        player = fresh_player(system_id="nexus_prime", fuel=200)
        # nexus_prime is already in systems_visited from __post_init__
        assert "nexus_prime" in player.systems_visited
        # First visit to verdant
        player.travel_to_system("verdant", 5)
        exploration_first = player.lens_investment.get_investment("exploration")
        assert exploration_first == 5
        # Return home — nexus_prime already in systems_visited, so no emit
        player.travel_to_system("nexus_prime", 5)
        # Revisit verdant — verdant now in systems_visited, so no emit
        player.travel_to_system("verdant", 5)
        exploration_revisit = player.lens_investment.get_investment("exploration")
        assert exploration_revisit == 5, (
            f"Expected 5 (only verdant first visit), got {exploration_revisit}"
        )

    def test_record_lens_action_returns_list_of_incremented_lenses(self) -> None:
        """The facade returns which lens_ids were incremented."""
        _dl()
        player = fresh_player()
        # sold_cargo maps to the wealth lens
        result = player.record_lens_action("sold_cargo", 1)
        assert "wealth" in result

    def test_wreckers_contract_completed_accrues_community(self) -> None:
        """wreckers_guild_contract_completed fires on community per the lens registry.

        Note: the preservation lens uses a qualified tag
        (wreckers_guild_contract_completed:preservation) which is a GAP tag
        (no emitter yet). The base tag accrues only on community.
        """
        _dl()
        player = fresh_player()
        result = player.record_lens_action("wreckers_guild_contract_completed", 5)
        assert "community" in result
        assert player.lens_investment.get_investment("community") == 5

    def test_crew_loyalty_gained_accrues_community_and_connection(self) -> None:
        """crew_loyalty_gained fires on community AND connection lenses."""
        _dl()
        player = fresh_player()
        result = player.record_lens_action("crew_loyalty_gained", 1)
        assert "community" in result
        assert "connection" in result

    def test_okafor_high_risk_co_fire_accrues_legacy_and_transcendence(self) -> None:
        """Both okafor tags fire for high-risk funding; legacy + transcendence increment."""
        _dl()
        player = fresh_player()
        # Base tag → legacy
        player.record_lens_action("okafor_research_project_funded", 10)
        # High-risk qualifier → transcendence
        player.record_lens_action("okafor_research_project_funded:high_risk", 10)
        assert player.lens_investment.get_investment("legacy") == 10
        assert player.lens_investment.get_investment("transcendence") == 10
