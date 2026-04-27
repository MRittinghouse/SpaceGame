"""Tests for spacegame/constants/flags.py canonical flag string helpers.

Exercises all helpers to confirm canonical string values and that each
helper is callable with the expected signature. The strings are the
single source of truth for flag names across producers and consumers;
a wrong return value here means the flag bus is broken.
"""

from __future__ import annotations

from spacegame.constants.flags import (
    campaign_mission_milestone,
    dual_tech_revealed,
    encounter_seen,
    heard_dcmc_intelligence,
    heard_nas_intelligence,
    investment_introduced,
    met_npc,
    odom_explained_investment,
    seen_faction_tip,
    seen_investment_tip,
    talked_to_npc,
    tutorial_bought_part,
)


class TestTutorialFlags:
    def test_tutorial_bought_part_returns_prefixed_string(self) -> None:
        assert tutorial_bought_part("engine_mk1") == "tutorial_bought_part_engine_mk1"

    def test_tutorial_bought_part_with_different_ids(self) -> None:
        assert tutorial_bought_part("hull_plate") == "tutorial_bought_part_hull_plate"
        assert tutorial_bought_part("weapon_laser") == "tutorial_bought_part_weapon_laser"


class TestCampaignMilestoneFlags:
    def test_campaign_milestone_5(self) -> None:
        assert campaign_mission_milestone(5) == "completed_mission_5"

    def test_campaign_milestone_10(self) -> None:
        assert campaign_mission_milestone(10) == "completed_mission_10"

    def test_campaign_milestone_20(self) -> None:
        assert campaign_mission_milestone(20) == "completed_mission_20"


class TestMetNpcFlags:
    def test_met_npc_marcus(self) -> None:
        assert met_npc("marcus_jin") == "met_marcus_jin"

    def test_met_npc_arna(self) -> None:
        assert met_npc("arna") == "met_arna"


class TestTalkedToNpcFlags:
    def test_talked_to_cargo_broker(self) -> None:
        assert talked_to_npc("cargo_broker") == "talked_to_cargo_broker"

    def test_talked_to_officer_larsen(self) -> None:
        assert talked_to_npc("officer_larsen") == "talked_to_officer_larsen"


class TestDualTechRevealedFlags:
    def test_dual_tech_revealed_suffix(self) -> None:
        assert dual_tech_revealed("warp_strike") == "dual_tech_warp_strike_revealed"


class TestInvestmentIntroducedFlag:
    def test_investment_introduced_returns_canonical_string(self) -> None:
        assert investment_introduced() == "investment_introduced"

    def test_investment_introduced_is_no_arg(self) -> None:
        # Helper takes no arguments — calling with no args must not raise.
        result = investment_introduced()
        assert isinstance(result, str)


class TestSeenFactionTipFlags:
    def test_seen_faction_tip_guild(self) -> None:
        assert seen_faction_tip("guild") == "seen_faction_tip_guild"

    def test_seen_faction_tip_union(self) -> None:
        assert seen_faction_tip("union") == "seen_faction_tip_union"


class TestEncounterSeenFlags:
    def test_encounter_seen_format(self) -> None:
        assert encounter_seen("reva_distress") == "encounter_seen_reva_distress"


class TestSA0DepthTierFlags:
    """SA-0: Canonical string verification for the two new depth-tier flags.

    These no-arg helpers guard the Cluster A depth-tier dialogue beats.
    The canonical string is the single source of truth — changing either
    value here would silently break the dialogue gate and journal trigger.
    """

    def test_heard_dcmc_intelligence_canonical_string(self) -> None:
        """heard_dcmc_intelligence() must return the exact canonical string."""
        assert heard_dcmc_intelligence() == "heard_dcmc_intelligence"

    def test_heard_nas_intelligence_canonical_string(self) -> None:
        """heard_nas_intelligence() must return the exact canonical string."""
        assert heard_nas_intelligence() == "heard_nas_intelligence"

    def test_both_flags_are_no_arg_callables(self) -> None:
        """Both helpers take no arguments — verify the signature holds."""
        dcmc = heard_dcmc_intelligence()
        nas = heard_nas_intelligence()
        assert isinstance(dcmc, str), "heard_dcmc_intelligence() should return str"
        assert isinstance(nas, str), "heard_nas_intelligence() should return str"

    def test_flags_are_distinct(self) -> None:
        """The two flag strings must not collide."""
        assert heard_dcmc_intelligence() != heard_nas_intelligence()


class TestSAVCargoBrokerFlags:
    """SA-V: canonical string verification for the two new Cargo Broker flags.

    odom_explained_investment is set by the investment_intro dialogue node
    and consumed by the_longer_ledger mission objective.
    seen_investment_tip is set by the station_hub_view PT-M dismiss callback
    and guards re-fire of the investment-card tip.
    """

    def test_odom_explained_investment_returns_canonical_string(self) -> None:
        assert odom_explained_investment() == "odom_explained_investment"

    def test_odom_explained_investment_is_no_arg_callable(self) -> None:
        result = odom_explained_investment()
        assert isinstance(result, str)

    def test_seen_investment_tip_returns_canonical_string(self) -> None:
        assert seen_investment_tip() == "seen_investment_tip"

    def test_seen_investment_tip_is_no_arg_callable(self) -> None:
        result = seen_investment_tip()
        assert isinstance(result, str)

    def test_sa_v_flags_are_distinct_from_each_other(self) -> None:
        """The two SA-V flag strings must not collide."""
        assert odom_explained_investment() != seen_investment_tip()

    def test_sa_v_flags_do_not_collide_with_investment_introduced(self) -> None:
        """SA-V helpers are distinct from the pre-existing investment_introduced flag."""
        assert odom_explained_investment() != investment_introduced()
        assert seen_investment_tip() != investment_introduced()
