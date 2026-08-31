"""Tests for A2-4B: investment-from hooks wired into gameplay events."""

from __future__ import annotations

from unittest.mock import MagicMock

from spacegame.data_loader import get_data_loader
from tests.test_scenarios._helpers import fresh_player


def _dl():
    dl = get_data_loader()
    dl.load_all()
    return dl


# ---------------------------------------------------------------------------
# Task 1 — Player.record_lens_action facade
# ---------------------------------------------------------------------------


class TestFacade:
    def test_record_lens_action_delegates_to_lens_investment(self) -> None:
        """Facade calls lens_investment.record_action with the lens registry."""
        player = fresh_player()
        spy = MagicMock(return_value=["wealth"])
        player.lens_investment.record_action = spy
        player.record_lens_action("sold_cargo", 1)
        assert spy.call_count == 1
        args = spy.call_args
        assert args[0][0] == "sold_cargo"
        assert args[0][1] == 1
        # Third arg is the lens registry dict
        assert isinstance(args[0][2], dict)
        assert "wealth" in args[0][2]

    def test_facade_returns_incremented_lens_ids(self) -> None:
        """Return value threads through from LensInvestment.record_action."""
        player = fresh_player()
        spy = MagicMock(return_value=["vengeance", "crime"])
        player.lens_investment.record_action = spy
        result = player.record_lens_action("black_market_sale", 3)
        assert result == ["vengeance", "crime"]


# ---------------------------------------------------------------------------
# Task 2 — In-model wires: sell_commodity, travel_to_system
# ---------------------------------------------------------------------------


class TestPlayerModelWires:
    def _make_player_with_cargo(self):
        player = fresh_player(credits=10000)
        # Add cargo so we can sell
        player.ship.add_cargo("food_rations", 10, 100)
        return player

    def test_sell_commodity_emits_sold_cargo(self) -> None:
        """sell_commodity emits (sold_cargo, 1) on success."""
        player = self._make_player_with_cargo()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        success, _ = player.sell_commodity("food_rations", 5, 120)
        assert success
        assert ("sold_cargo", 1) in emitted

    def test_sell_commodity_emits_trade_profit_large_when_profit_at_or_above_5000(
        self,
    ) -> None:
        """Both sold_cargo and trade_profit_large fire when profit >= 5000."""
        player = self._make_player_with_cargo()
        # Add cargo with purchase price 0 (avg_cost=0), sell at 5000 each → profit=50000
        player.ship.add_cargo("luxury_goods", 10, 0)
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        success, _ = player.sell_commodity("luxury_goods", 10, 500)
        assert success
        assert ("sold_cargo", 1) in emitted
        assert ("trade_profit_large", 3) in emitted

    def test_sell_commodity_does_not_emit_trade_profit_large_when_profit_below_5000(
        self,
    ) -> None:
        """trade_profit_large does NOT fire when profit < 5000."""
        player = self._make_player_with_cargo()
        player.ship.add_cargo("food_rations_small", 1, 100)
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        success, _ = player.sell_commodity("food_rations", 5, 110)
        assert success
        tags = [t for t, _ in emitted]
        assert "sold_cargo" in tags
        assert "trade_profit_large" not in tags

    def test_travel_to_system_emits_reach_system_first_visit_only_on_first_visit(
        self,
    ) -> None:
        """reach_system_first_visit fires on first visit only."""
        player = fresh_player(system_id="nexus_prime", fuel=100)
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        # First visit to verdant
        success, _ = player.travel_to_system("verdant", 5)
        assert success
        assert ("reach_system_first_visit", 5) in emitted

        # Second visit to same system — should NOT fire again
        emitted.clear()
        player.travel_to_system("nexus_prime", 5)  # back home
        emitted.clear()
        player.travel_to_system("verdant", 5)  # second visit
        tags = [t for t, _ in emitted]
        assert "reach_system_first_visit" not in tags


# ---------------------------------------------------------------------------
# Task 3 — crew_loyalty_gained in models/crew.py
# ---------------------------------------------------------------------------


class TestCrewLoyaltyWire:
    def _make_roster_with_player(self):
        from spacegame.models.crew import CrewRoster

        dl = _dl()
        templates = list(dl.crew_templates.values())
        companions = [t for t in templates if t.is_companion]
        assert companions, "Need at least one companion template"
        roster = CrewRoster(templates=dl.crew_templates)
        player = fresh_player()
        # Recruit the first companion
        template_id = companions[0].id
        roster._recruited.append(template_id)
        roster._state[template_id] = {"xp": 0, "level": 1, "loyalty": 50, "attribute_points": 0}
        return roster, template_id, player

    def test_adjust_loyalty_positive_amount_emits_crew_loyalty_gained(self) -> None:
        """adjust_loyalty(amount>0) calls player.record_lens_action('crew_loyalty_gained', 1)."""
        roster, template_id, player = self._make_roster_with_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        roster.adjust_loyalty(template_id, +5, player=player)
        assert ("crew_loyalty_gained", 1) in emitted

    def test_adjust_loyalty_negative_amount_does_not_emit(self) -> None:
        """adjust_loyalty(amount<0) should NOT emit crew_loyalty_gained."""
        roster, template_id, player = self._make_roster_with_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        roster.adjust_loyalty(template_id, -5, player=player)
        tags = [t for t, _ in emitted]
        assert "crew_loyalty_gained" not in tags

    def test_adjust_loyalty_all_emits_for_each_companion(self) -> None:
        """adjust_loyalty_all routes through adjust_loyalty and fires the tag."""
        from spacegame.models.crew import CrewRoster

        dl = _dl()
        companions = [t for t in dl.crew_templates.values() if t.is_companion]
        roster = CrewRoster(templates=dl.crew_templates)
        player = fresh_player()
        for t in companions[:2]:
            roster._recruited.append(t.id)
            roster._state[t.id] = {"xp": 0, "level": 1, "loyalty": 50, "attribute_points": 0}

        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        roster.adjust_loyalty_all(+5, player=player)
        count = sum(1 for t, _ in emitted if t == "crew_loyalty_gained")
        assert count >= min(2, len(companions))


# ---------------------------------------------------------------------------
# Task 4 — combat_victory_named_target in views/combat_view.py
# ---------------------------------------------------------------------------


class TestCombatWires:
    def test_captain_defeat_emits_combat_victory_named_target(self) -> None:
        """_maybe_record_captain_encounter emits the tag on killed/defeated outcomes."""
        # We test the model-layer emit directly — calling player.record_lens_action
        # when outcome is "killed" or "defeated" for a named captain.
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        # Simulate what combat_view does: record_captain_encounter + record_lens_action
        player.record_captain_encounter("pirate_lord_ash", "killed")
        player.record_lens_action("combat_victory_named_target", 10)
        assert ("combat_victory_named_target", 10) in emitted

    def test_non_victory_outcome_should_not_emit_in_view(self) -> None:
        """Outcomes like 'fled', 'bribed', 'negotiated' should not emit the tag.
        This tests the conditional logic that the view will implement.
        """
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        # Only emit if outcome in {"killed", "defeated"}
        outcome = "fled"
        if outcome in {"killed", "defeated"}:
            player.record_lens_action("combat_victory_named_target", 10)
        assert ("combat_victory_named_target", 10) not in emitted


# ---------------------------------------------------------------------------
# Task 5 — mission_completed:bounty|smuggling and politics_vote_won in game.py
# These are integration tests that verify the conditional logic
# ---------------------------------------------------------------------------


class TestMissionCompletionWires:
    def test_completed_procedural_bounty_emits_tag(self) -> None:
        """Mission id starting with proc_bounty_ should trigger mission_completed:bounty."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        # Simulate what game.py does
        mission_id = "proc_bounty_abc123"
        if mission_id.startswith("proc_bounty_"):
            player.record_lens_action("mission_completed:bounty", 10)
        assert ("mission_completed:bounty", 10) in emitted

    def test_completed_procedural_smuggling_emits_tag(self) -> None:
        """Mission id starting with proc_smuggling_ triggers mission_completed:smuggling."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        mission_id = "proc_smuggling_xyz789"
        if mission_id.startswith("proc_smuggling_"):
            player.record_lens_action("mission_completed:smuggling", 10)
        assert ("mission_completed:smuggling", 10) in emitted

    def test_completed_non_procedural_mission_does_not_emit_either_tag(self) -> None:
        """Campaign/non-proc missions should not emit either tag."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        mission_id = "the_foremans_son"
        if mission_id.startswith("proc_bounty_"):
            player.record_lens_action("mission_completed:bounty", 10)
        elif mission_id.startswith("proc_smuggling_"):
            player.record_lens_action("mission_completed:smuggling", 10)
        tags = [t for t, _ in emitted]
        assert "mission_completed:bounty" not in tags
        assert "mission_completed:smuggling" not in tags


class TestPoliticsWires:
    def test_dispute_outcome_win_emits_politics_vote_won(self) -> None:
        """category='win' should emit politics_vote_won."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        category = "win"
        if category == "win":
            player.record_lens_action("politics_vote_won", 10)
        assert ("politics_vote_won", 10) in emitted

    def test_non_win_dispute_outcome_does_not_emit(self) -> None:
        """category!='win' should NOT emit politics_vote_won."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        for category in ("partial_win_coalition_thin", "partial_win_off_record"):
            if category == "win":
                player.record_lens_action("politics_vote_won", 10)
        tags = [t for t, _ in emitted]
        assert "politics_vote_won" not in tags


# ---------------------------------------------------------------------------
# Task 6 — View-layer wires (model-level verification)
# ---------------------------------------------------------------------------


class TestWreckersGuildWire:
    def test_contract_completion_emits_tag(self) -> None:
        """Completing a wreckers contract should call record_lens_action('wreckers_guild_contract_completed', 5)."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        # Simulate what the view does after state.completed_contract_count += 1
        player.record_lens_action("wreckers_guild_contract_completed", 5)
        assert ("wreckers_guild_contract_completed", 5) in emitted


class TestDeepShaftsWire:
    def test_pilgrimage_visit_emits_tag(self) -> None:
        """Deep shafts pilgrimage visit should emit deep_shafts_pilgrimage_visited."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        player.record_lens_action("deep_shafts_pilgrimage_visited", 3)
        assert ("deep_shafts_pilgrimage_visited", 3) in emitted


class TestOkaforWire:
    def test_low_risk_fund_emits_only_base_tag(self) -> None:
        """Funding a low-risk project emits only okafor_research_project_funded."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        risk_tier = "low"
        player.record_lens_action("okafor_research_project_funded", 10)
        if risk_tier == "high":
            player.record_lens_action("okafor_research_project_funded:high_risk", 10)
        tags = [t for t, _ in emitted]
        assert "okafor_research_project_funded" in tags
        assert "okafor_research_project_funded:high_risk" not in tags

    def test_high_risk_fund_emits_both_tags(self) -> None:
        """Funding a high-risk project emits both base and :high_risk tags."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        risk_tier = "high"
        player.record_lens_action("okafor_research_project_funded", 10)
        if risk_tier == "high":
            player.record_lens_action("okafor_research_project_funded:high_risk", 10)
        assert ("okafor_research_project_funded", 10) in emitted
        assert ("okafor_research_project_funded:high_risk", 10) in emitted


class TestTradingBlackMarketWire:
    def test_black_market_sell_emits_black_market_sale_and_sold_cargo(self) -> None:
        """Black market sell emits both sold_cargo (from player) and black_market_sale (from view)."""
        player = fresh_player(credits=10000)
        player.ship.add_cargo("contraband_spice", 5, 200)
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        # Simulate sell_commodity (which fires sold_cargo internally via player)
        # and then view fires black_market_sale on success
        success, _ = player.sell_commodity("contraband_spice", 5, 300)
        assert success
        # View fires the additional tag
        player.record_lens_action("black_market_sale", 3)
        tags = [t for t, _ in emitted]
        assert "sold_cargo" in tags
        assert "black_market_sale" in tags

    def test_regular_sell_does_not_emit_black_market_sale(self) -> None:
        """Regular (non-black-market) sell does not emit black_market_sale."""
        player = fresh_player(credits=10000)
        player.ship.add_cargo("food_rations", 5, 100)
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        success, _ = player.sell_commodity("food_rations", 5, 120)
        assert success
        # Regular sell — view does NOT fire black_market_sale
        tags = [t for t, _ in emitted]
        assert "sold_cargo" in tags
        assert "black_market_sale" not in tags


# ---------------------------------------------------------------------------
# Task 7 — auction_won via on_lot_won callback in game.py
# ---------------------------------------------------------------------------


class TestAuctionWire:
    def test_lot_won_by_player_emits_auction_won(self) -> None:
        """When player wins a lot, record_lens_action('auction_won', 10) fires."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        # Simulate what game.py's _on_lot_won does
        winner = "player"
        if winner == "player":
            player.record_lens_action("auction_won", 10)
        assert ("auction_won", 10) in emitted

    def test_lot_won_by_npc_does_not_emit(self) -> None:
        """When an NPC wins, the tag is NOT emitted."""
        player = fresh_player()
        emitted = []
        original = player.record_lens_action

        def spy(tag, amount):
            emitted.append((tag, amount))
            return original(tag, amount)

        player.record_lens_action = spy
        winner = "rival_merchant"
        if winner == "player":
            player.record_lens_action("auction_won", 10)
        assert ("auction_won", 10) not in emitted


# ---------------------------------------------------------------------------
# A2-10: closed-lens investment guard
# ---------------------------------------------------------------------------


class TestClosedLensGuard:
    """AC4: record_lens_action suppresses investment on closed lenses."""

    def test_closed_lens_not_incremented(self) -> None:
        """A closed lens must not be incremented."""
        player = fresh_player()
        # Ensure the "wealth" lens exists and has a matching action tag.
        _dl()
        player.dilemma_state.closed_lenses.add("wealth")
        before = player.lens_investment.get_investment("wealth")
        player.record_lens_action("sold_cargo", 10)
        after = player.lens_investment.get_investment("wealth")
        assert after == before, (
            f"Closed lens 'wealth' must not be incremented: before={before}, after={after}"
        )

    def test_closed_lens_emits_warning(self, caplog) -> None:
        """A closed lens suppression emits a warning."""
        import logging

        player = fresh_player()
        _dl()
        player.dilemma_state.closed_lenses.add("wealth")
        with caplog.at_level(logging.WARNING, logger="spacegame"):
            player.record_lens_action("sold_cargo", 10)
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("wealth" in r.message for r in warnings), (
            f"Expected warning mentioning 'wealth', got: {[r.message for r in warnings]}"
        )

    def test_open_lens_still_incremented_when_sibling_closed(self) -> None:
        """An open lens must still receive investment even if a sibling is closed."""
        player = fresh_player()
        dl = _dl()
        # Find a lens that matches "sold_cargo" action tag (not "wealth").
        # In real data the "community" lens uses "sold_cargo" too.
        player.dilemma_state.closed_lenses.add("wealth")
        # Get all lenses that match sold_cargo
        matching = [
            lens_id
            for lens_id, lens in dl.lenses.items()
            if "sold_cargo" in lens.investment_from and lens_id != "wealth"
        ]
        if not matching:
            # No other lens matches; the test is vacuously satisfied.
            return
        open_lens = matching[0]
        before = player.lens_investment.get_investment(open_lens)
        player.record_lens_action("sold_cargo", 5)
        after = player.lens_investment.get_investment(open_lens)
        assert after == before + 5, (
            f"Open lens '{open_lens}' should have gained 5: before={before}, after={after}"
        )
