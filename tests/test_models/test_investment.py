"""Tests for Investment system — passive income from per-system investments."""

import pytest
from spacegame.models.investment import (
    InvestmentTier,
    InvestmentTemplate,
    Investment,
    InvestmentManager,
)


def _make_tier(
    tier: int = 1,
    cost: int = 1000,
    daily: int = 10,
    returns_type: str = "credits",
    commodity: str | None = None,
) -> InvestmentTier:
    return InvestmentTier(
        tier=tier,
        cost=cost,
        daily_return_amount=daily,
        returns_type=returns_type,
        returns_commodity=commodity,
    )


def _make_template(
    system_id: str = "nexus_prime",
    investment_type: str = "trade_office",
    name: str = "Trade Office",
    description: str = "Invest in trade.",
    tiers: list[InvestmentTier] | None = None,
) -> InvestmentTemplate:
    if tiers is None:
        tiers = [
            _make_tier(1, 1000, 10),
            _make_tier(2, 5000, 50),
            _make_tier(3, 15000, 200),
        ]
    return InvestmentTemplate(
        system_id=system_id,
        investment_type=investment_type,
        name=name,
        description=description,
        tiers=tiers,
    )


def _make_commodity_template(
    system_id: str = "breakstone",
) -> InvestmentTemplate:
    return _make_template(
        system_id=system_id,
        investment_type="mining_rig",
        name="Mining Rig",
        tiers=[
            _make_tier(1, 1000, 5, "commodity", "raw_ore"),
            _make_tier(2, 5000, 25, "commodity", "raw_ore"),
            _make_tier(3, 15000, 100, "commodity", "raw_ore"),
        ],
    )


def _make_manager(
    templates: dict[str, InvestmentTemplate] | None = None,
) -> InvestmentManager:
    if templates is None:
        templates = {
            "nexus_prime": _make_template("nexus_prime"),
            "breakstone": _make_commodity_template("breakstone"),
        }
    return InvestmentManager(templates=templates)


class TestInvestmentTierConstruction:
    def test_create_tier(self) -> None:
        tier = _make_tier()
        assert tier.tier == 1
        assert tier.cost == 1000
        assert tier.daily_return_amount == 10
        assert tier.returns_type == "credits"

    def test_commodity_tier(self) -> None:
        tier = _make_tier(returns_type="commodity", commodity="raw_ore")
        assert tier.returns_commodity == "raw_ore"


class TestInvestmentTemplateSerialization:
    def test_to_dict(self) -> None:
        template = _make_template()
        d = template.to_dict()
        assert d["system_id"] == "nexus_prime"
        assert len(d["tiers"]) == 3

    def test_round_trip(self) -> None:
        template = _make_template()
        d = template.to_dict()
        restored = InvestmentTemplate.from_dict(d)
        assert restored.system_id == template.system_id
        assert len(restored.tiers) == len(template.tiers)
        assert restored.tiers[0].cost == template.tiers[0].cost


class TestInvestmentSerialization:
    def test_to_dict(self) -> None:
        inv = Investment(
            system_id="nexus_prime", tier=2, accumulated_returns=150, last_processed_day=10
        )
        d = inv.to_dict()
        assert d["system_id"] == "nexus_prime"
        assert d["tier"] == 2
        assert d["accumulated_returns"] == 150

    def test_round_trip(self) -> None:
        inv = Investment(
            system_id="nexus_prime",
            tier=1,
            accumulated_returns=50,
            last_processed_day=5,
            halted_until_day=8,
        )
        d = inv.to_dict()
        restored = Investment.from_dict(d)
        assert restored.system_id == inv.system_id
        assert restored.tier == inv.tier
        assert restored.accumulated_returns == inv.accumulated_returns
        assert restored.halted_until_day == inv.halted_until_day

    def test_defaults(self) -> None:
        inv = Investment(system_id="nexus_prime", tier=1)
        assert inv.accumulated_returns == 0
        assert inv.last_processed_day == 0
        assert inv.halted_until_day == 0


class TestInvestmentManagerInvest:
    def test_invest_success(self) -> None:
        mgr = _make_manager()
        success, msg = mgr.invest(5000, "nexus_prime", current_day=1)
        assert success, msg
        assert mgr.get_investment("nexus_prime") is not None
        assert mgr.get_investment("nexus_prime").tier == 1

    def test_invest_returns_cost(self) -> None:
        mgr = _make_manager()
        success, msg = mgr.invest(5000, "nexus_prime", current_day=1)
        assert "1,000" in msg

    def test_invest_insufficient_credits(self) -> None:
        mgr = _make_manager()
        success, msg = mgr.invest(500, "nexus_prime", current_day=1)
        assert not success
        assert mgr.get_investment("nexus_prime") is None

    def test_invest_already_owned(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        success, msg = mgr.invest(5000, "nexus_prime", current_day=2)
        assert not success

    def test_invest_no_template(self) -> None:
        mgr = _make_manager()
        success, msg = mgr.invest(5000, "unknown_system", current_day=1)
        assert not success


class TestInvestmentManagerUpgrade:
    def test_upgrade_success(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        success, msg = mgr.upgrade(10000, "nexus_prime")
        assert success
        assert mgr.get_investment("nexus_prime").tier == 2

    def test_upgrade_max_tier(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        mgr.upgrade(10000, "nexus_prime")  # tier 2
        mgr.upgrade(20000, "nexus_prime")  # tier 3
        success, msg = mgr.upgrade(50000, "nexus_prime")  # already max
        assert not success

    def test_upgrade_insufficient_credits(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        success, msg = mgr.upgrade(1000, "nexus_prime")
        assert not success

    def test_upgrade_not_owned(self) -> None:
        mgr = _make_manager()
        success, msg = mgr.upgrade(10000, "nexus_prime")
        assert not success


class TestInvestmentManagerAdvanceDay:
    def test_accumulates_returns(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        mgr.advance_day(2, active_events={}, danger_levels={})
        inv = mgr.get_investment("nexus_prime")
        assert inv.accumulated_returns == 10  # 1 day * 10/day
        assert inv.last_processed_day == 2

    def test_accumulates_multiple_days(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        mgr.advance_day(6, active_events={}, danger_levels={})
        inv = mgr.get_investment("nexus_prime")
        assert inv.accumulated_returns == 50  # 5 days * 10/day

    def test_disaster_halts_returns(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)

        class FakeEvent:
            def is_active(self, day: int) -> bool:
                return True

            event_type: str = "disaster"

        events = {"nexus_prime": FakeEvent()}
        mgr.advance_day(2, active_events=events, danger_levels={})
        inv = mgr.get_investment("nexus_prime")
        assert inv.accumulated_returns == 0
        assert inv.halted_until_day > 0

    def test_pirate_reduction_dangerous(self) -> None:
        """Dangerous systems have 10% chance per day of halving returns.
        Use deterministic seed to verify the mechanic exists."""
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        # Run 100 days to statistically guarantee at least one reduction
        total = 0
        for day in range(2, 102):
            mgr.active["nexus_prime"].last_processed_day = day - 1
            mgr.active["nexus_prime"].accumulated_returns = 0
            mgr.advance_day(day, active_events={}, danger_levels={"nexus_prime": "dangerous"})
            total += mgr.active["nexus_prime"].accumulated_returns
        # If no reductions ever happened, total would be 1000 (100 * 10)
        # With 10% halving, expect ~950 on average
        assert total < 1000, "Expected some pirate reductions over 100 days"


class TestInvestmentManagerCollect:
    def test_collect_credits(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        mgr.advance_day(6, active_events={}, danger_levels={})
        success, msg, credits, commodity, qty = mgr.collect_returns("nexus_prime")
        assert success
        assert credits == 50
        assert commodity is None
        assert mgr.get_investment("nexus_prime").accumulated_returns == 0

    def test_collect_commodity(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "breakstone", current_day=1)
        mgr.advance_day(6, active_events={}, danger_levels={})
        success, msg, credits, commodity, qty = mgr.collect_returns("breakstone")
        assert success
        assert credits == 0
        assert commodity == "raw_ore"
        assert qty == 25  # 5 days * 5/day

    def test_collect_nothing(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        success, msg, credits, commodity, qty = mgr.collect_returns("nexus_prime")
        assert not success
        assert credits == 0

    def test_collect_no_investment(self) -> None:
        mgr = _make_manager()
        success, msg, credits, commodity, qty = mgr.collect_returns("nexus_prime")
        assert not success


class TestInvestmentManagerSerialization:
    def test_round_trip(self) -> None:
        mgr = _make_manager()
        mgr.invest(5000, "nexus_prime", current_day=1)
        mgr.advance_day(3, active_events={}, danger_levels={})
        d = mgr.to_dict()
        restored = InvestmentManager.from_dict(d, mgr.templates)
        assert "nexus_prime" in restored.active
        assert restored.active["nexus_prime"].accumulated_returns == 20

    def test_empty_round_trip(self) -> None:
        mgr = _make_manager()
        d = mgr.to_dict()
        restored = InvestmentManager.from_dict(d, mgr.templates)
        assert len(restored.active) == 0


class TestInvestmentDataLoading:
    """Tests that investment configs load correctly from JSON."""

    def test_load_investment_configs(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_investment_configs()
        assert len(loader.investment_templates) == 10

    def test_all_systems_have_templates(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_investment_configs()
        expected = [
            "nexus_prime",
            "stellaris_port",
            "axiom_labs",
            "nova_research",
            "forgeworks",
            "breakstone",
            "iron_depths",
            "verdant",
            "havens_rest",
            "crimson_reach",
        ]
        for sys_id in expected:
            assert sys_id in loader.investment_templates, f"Missing template for {sys_id}"

    def test_each_template_has_three_tiers(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_investment_configs()
        for sys_id, template in loader.investment_templates.items():
            assert len(template.tiers) == 3, f"{sys_id} should have 3 tiers"

    def test_get_investment_template(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_investment_configs()
        t = loader.get_investment_template("nexus_prime")
        assert t is not None
        assert t.name == "Meridian Trade Office"

    def test_get_investment_template_missing(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_investment_configs()
        assert loader.get_investment_template("nonexistent") is None
