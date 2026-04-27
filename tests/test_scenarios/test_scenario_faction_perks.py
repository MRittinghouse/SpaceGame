"""Scenario F: Faction reputation gates perks.

Walks the full perk pipeline:
  reputation shift → rep tier crossing → active perks → bonus calculation

Verifies that a player reaching FRIENDLY (rep >= 20) gains friendly-tier
perks, reaching ALLIED (rep >= 50) stacks allied-tier on top, and that the
numeric/boolean bonuses actually flow to the query API that gameplay reads.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.faction import ReputationTier
from spacegame.models.politics import PoliticsManager
from tests.test_scenarios._helpers import fresh_player


def _politics() -> PoliticsManager:
    dl = get_data_loader()
    dl.load_all()
    mgr = PoliticsManager(
        relationships=dl.faction_relationships,
        factions=dl.factions,
    )
    mgr.set_faction_perks(dl.faction_perks)
    return mgr


class TestReputationTierTransitions:
    def test_neutral_has_no_perks(self) -> None:
        player = fresh_player()
        mgr = _politics()

        # Assign nexus_prime to commerce_guild
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        assert player.get_reputation("commerce_guild") == 0

        active = mgr.get_active_perks(player, "nexus_prime")
        assert active == [], "Neutral reputation should grant no perks"

    def test_friendly_grants_friendly_perks(self) -> None:
        player = fresh_player()
        mgr = _politics()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.faction_reputation["commerce_guild"] = 25  # FRIENDLY tier

        assert player.get_reputation_tier("commerce_guild") == ReputationTier.FRIENDLY

        active = mgr.get_active_perks(player, "nexus_prime")
        # commerce_guild has friendly-tier perks authored
        assert len(active) > 0, "Friendly rep must unlock friendly-tier perks"
        # Sanity: every returned perk is for commerce_guild at friendly tier
        for perk in active:
            assert perk.faction_id == "commerce_guild"
            assert perk.required_tier == "friendly"

    def test_allied_stacks_both_friendly_and_allied_perks(self) -> None:
        """Reaching ALLIED should grant BOTH friendly AND allied perks
        (allied is additive, not a replacement)."""
        player = fresh_player()
        mgr = _politics()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.faction_reputation["commerce_guild"] = 60  # ALLIED

        assert player.get_reputation_tier("commerce_guild") == ReputationTier.ALLIED

        active = mgr.get_active_perks(player, "nexus_prime")
        tiers_present = {perk.required_tier for perk in active}
        assert "friendly" in tiers_present, "ALLIED must include friendly perks"
        assert "allied" in tiers_present, "ALLIED must include allied perks"


class TestPerkBonusFlowsToQueryAPI:
    """The bonus is only useful if the query API actually returns it.
    Verifies that gameplay's typical call — ``get_perk_bonus(player, system,
    'buy_price_bonus')`` — returns a positive number when perks are active.
    """

    def test_buy_price_bonus_accumulates_from_active_perks(self) -> None:
        player = fresh_player()
        mgr = _politics()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.faction_reputation["commerce_guild"] = 60  # ALLIED

        # Commerce Guild perks include buy_price_bonus at both tiers.
        bonus = mgr.get_perk_bonus(player, "nexus_prime", "buy_price_bonus")
        # Could be positive or negative depending on perk values;
        # just assert it's non-zero at ALLIED with commerce_guild.
        assert bonus != 0.0, (
            f"ALLIED with commerce_guild should give a non-zero buy_price_bonus. Got {bonus}."
        )

    def test_unrelated_perk_type_returns_zero(self) -> None:
        player = fresh_player()
        mgr = _politics()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.faction_reputation["commerce_guild"] = 60

        # commerce_guild doesn't grant mining perks
        bonus = mgr.get_perk_bonus(player, "nexus_prime", "mining_yield_bonus")
        assert bonus == 0.0

    def test_no_perks_in_unassigned_system(self) -> None:
        player = fresh_player()
        mgr = _politics()
        player.faction_reputation["commerce_guild"] = 60  # max rep

        # No faction_assignment for 'nexus_prime' → no perks
        bonus = mgr.get_perk_bonus(player, "nexus_prime", "buy_price_bonus")
        assert bonus == 0.0


class TestPerkGatingByCurrentSystem:
    """Perks only apply IN the controlling faction's systems. A player with
    max commerce_guild rep in a miners_union system shouldn't get commerce
    perks."""

    def test_perks_not_active_in_other_factions_system(self) -> None:
        player = fresh_player()
        mgr = _politics()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.faction_assignments["breakstone"] = "miners_union"
        player.faction_reputation["commerce_guild"] = 60  # allied
        player.faction_reputation["miners_union"] = 0

        # In nexus_prime (commerce): perks active
        cg_perks = mgr.get_active_perks(player, "nexus_prime")
        assert len(cg_perks) > 0

        # In breakstone (miners): no commerce_guild perks
        mu_perks = mgr.get_active_perks(player, "breakstone")
        assert all(p.faction_id != "commerce_guild" for p in mu_perks), (
            "Commerce Guild perks must NOT fire in a Miners Union system"
        )


class TestRepShiftUnlocksPerksLive:
    """A single reputation increase that crosses a tier threshold should
    make the matching perks immediately queryable."""

    def test_crossing_friendly_threshold_unlocks_perks(self) -> None:
        player = fresh_player()
        mgr = _politics()
        player.faction_assignments["nexus_prime"] = "commerce_guild"

        # Below threshold (neutral)
        player.faction_reputation["commerce_guild"] = 19
        assert len(mgr.get_active_perks(player, "nexus_prime")) == 0

        # Cross the line (20 = friendly start)
        player.modify_reputation("commerce_guild", 1)
        assert player.faction_reputation["commerce_guild"] == 20
        active_after = mgr.get_active_perks(player, "nexus_prime")
        assert len(active_after) > 0, (
            "Crossing the FRIENDLY threshold should unlock perks immediately"
        )

    def test_losing_rep_drops_perks(self) -> None:
        """Equally important: rep drop must retire the perks so exploits can't
        persist benefits."""
        player = fresh_player()
        mgr = _politics()
        player.faction_assignments["nexus_prime"] = "commerce_guild"
        player.faction_reputation["commerce_guild"] = 25

        active_before = mgr.get_active_perks(player, "nexus_prime")
        assert len(active_before) > 0

        # Drop below friendly
        player.modify_reputation("commerce_guild", -10)  # 25 → 15 (neutral)
        active_after = mgr.get_active_perks(player, "nexus_prime")
        assert len(active_after) == 0, (
            "Losing FRIENDLY tier must retire the perks — no leftover bonuses"
        )
