"""Tests for the sub-reputation system (SA-B-EXT-1).

Covers OrganizationTier / OrganizationConfig shape, tier lookup, validation,
Player helper APIs, notification queue, save round-trip, and orthogonality
with faction_reputation.
"""

import dataclasses

import pytest

from spacegame.models.sub_reputation import (
    OrganizationConfig,
    OrganizationTier,
    SubReputationDelta,
    get_tier_for_rep,
    is_at_least,
)

# ---------------------------------------------------------------------------
# Test fixtures — synthetic configs used throughout
# ---------------------------------------------------------------------------


def _make_1tier_config() -> OrganizationConfig:
    """1-tier minimal config: every rep value maps to 'member'."""
    return OrganizationConfig(
        id="minimal_org",
        name="Minimal Org",
        tiers=(OrganizationTier(id="member", name="Member", rank=1, min_rep=0),),
        min_rep=0,
        max_rep=50,
    )


def _make_3tier_config() -> OrganizationConfig:
    """3-tier Wreckers'-shape: apprentice / journeyman / master."""
    return OrganizationConfig(
        id="wreckers_guild",
        name="Wreckers' Guild",
        tiers=(
            OrganizationTier(id="apprentice", name="Apprentice", rank=1, min_rep=0),
            OrganizationTier(id="journeyman", name="Journeyman", rank=2, min_rep=30),
            OrganizationTier(id="master", name="Master", rank=3, min_rep=70),
        ),
        min_rep=0,
        max_rep=100,
    )


def _make_4tier_config() -> OrganizationConfig:
    """4-tier Stellaris-shape: registered / preferred / trusted / elite."""
    return OrganizationConfig(
        id="stellaris_auctioneer",
        name="Stellaris Auctioneer",
        tiers=(
            OrganizationTier(id="registered", name="Registered", rank=1, min_rep=0),
            OrganizationTier(id="preferred", name="Preferred", rank=2, min_rep=25),
            OrganizationTier(id="trusted", name="Trusted", rank=3, min_rep=55),
            OrganizationTier(id="elite", name="Elite", rank=4, min_rep=80),
        ),
        min_rep=0,
        max_rep=100,
    )


# ---------------------------------------------------------------------------
# AC-1: OrganizationConfig validation
# ---------------------------------------------------------------------------


class TestOrganizationConfigValidation:
    """AC-1: __post_init__ rejects malformed configs."""

    def test_empty_tiers_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one tier"):
            OrganizationConfig(
                id="bad",
                name="Bad",
                tiers=(),
            )

    def test_duplicate_tier_ids_rejected(self) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            OrganizationConfig(
                id="bad",
                name="Bad",
                tiers=(
                    OrganizationTier(id="tier_a", name="A", rank=1, min_rep=0),
                    OrganizationTier(id="tier_a", name="A2", rank=2, min_rep=10),
                ),
            )

    def test_non_ascending_ranks_rejected(self) -> None:
        with pytest.raises(ValueError, match="ascending"):
            OrganizationConfig(
                id="bad",
                name="Bad",
                tiers=(
                    OrganizationTier(id="tier_a", name="A", rank=2, min_rep=0),
                    OrganizationTier(id="tier_b", name="B", rank=1, min_rep=10),
                ),
            )

    def test_non_ascending_min_rep_rejected(self) -> None:
        with pytest.raises(ValueError, match="ascending"):
            OrganizationConfig(
                id="bad",
                name="Bad",
                tiers=(
                    OrganizationTier(id="tier_a", name="A", rank=1, min_rep=20),
                    OrganizationTier(id="tier_b", name="B", rank=2, min_rep=10),
                ),
            )

    def test_valid_config_constructs_cleanly(self) -> None:
        cfg = _make_3tier_config()
        assert len(cfg.tiers) == 3

    def test_equal_ranks_rejected(self) -> None:
        with pytest.raises(ValueError, match="ascending"):
            OrganizationConfig(
                id="bad",
                name="Bad",
                tiers=(
                    OrganizationTier(id="tier_a", name="A", rank=1, min_rep=0),
                    OrganizationTier(id="tier_b", name="B", rank=1, min_rep=10),
                ),
            )

    def test_equal_min_rep_rejected(self) -> None:
        with pytest.raises(ValueError, match="ascending"):
            OrganizationConfig(
                id="bad",
                name="Bad",
                tiers=(
                    OrganizationTier(id="tier_a", name="A", rank=1, min_rep=10),
                    OrganizationTier(id="tier_b", name="B", rank=2, min_rep=10),
                ),
            )


# ---------------------------------------------------------------------------
# AC-2 / AC-3: get_tier_for_rep and tier ordering
# ---------------------------------------------------------------------------


class TestGetTierForRep:
    """AC-2: get_tier_for_rep returns the correct tier at every threshold edge."""

    def test_at_min_rep_returns_lowest_tier(self) -> None:
        cfg = _make_3tier_config()
        tier = get_tier_for_rep(cfg, 0)
        assert tier.id == "apprentice"

    def test_below_second_threshold_still_first_tier(self) -> None:
        cfg = _make_3tier_config()
        tier = get_tier_for_rep(cfg, 29)
        assert tier.id == "apprentice"

    def test_at_second_threshold_returns_second_tier(self) -> None:
        cfg = _make_3tier_config()
        tier = get_tier_for_rep(cfg, 30)
        assert tier.id == "journeyman"

    def test_between_second_and_third_threshold(self) -> None:
        cfg = _make_3tier_config()
        tier = get_tier_for_rep(cfg, 50)
        assert tier.id == "journeyman"

    def test_at_third_threshold_returns_highest_tier(self) -> None:
        cfg = _make_3tier_config()
        tier = get_tier_for_rep(cfg, 70)
        assert tier.id == "master"

    def test_at_max_rep_returns_highest_tier(self) -> None:
        cfg = _make_3tier_config()
        tier = get_tier_for_rep(cfg, 100)
        assert tier.id == "master"

    def test_1tier_config_always_returns_that_tier(self) -> None:
        cfg = _make_1tier_config()
        assert get_tier_for_rep(cfg, 0).id == "member"
        assert get_tier_for_rep(cfg, 25).id == "member"
        assert get_tier_for_rep(cfg, 50).id == "member"

    def test_4tier_boundaries(self) -> None:
        cfg = _make_4tier_config()
        assert get_tier_for_rep(cfg, 0).id == "registered"
        assert get_tier_for_rep(cfg, 24).id == "registered"
        assert get_tier_for_rep(cfg, 25).id == "preferred"
        assert get_tier_for_rep(cfg, 54).id == "preferred"
        assert get_tier_for_rep(cfg, 55).id == "trusted"
        assert get_tier_for_rep(cfg, 79).id == "trusted"
        assert get_tier_for_rep(cfg, 80).id == "elite"
        assert get_tier_for_rep(cfg, 100).id == "elite"


class TestOrganizationTierOrdering:
    """AC-3: OrganizationTier supports >= / < comparison by rank."""

    def test_tier_ge_itself(self) -> None:
        cfg = _make_3tier_config()
        journeyman = cfg.tiers[1]
        assert journeyman >= journeyman

    def test_higher_tier_ge_lower(self) -> None:
        cfg = _make_3tier_config()
        apprentice, journeyman, master = cfg.tiers
        assert journeyman >= apprentice
        assert master >= journeyman
        assert master >= apprentice

    def test_lower_tier_not_ge_higher(self) -> None:
        cfg = _make_3tier_config()
        apprentice, journeyman, _ = cfg.tiers
        assert not (apprentice >= journeyman)

    def test_lt_comparison(self) -> None:
        cfg = _make_3tier_config()
        apprentice, journeyman, _ = cfg.tiers
        assert apprentice < journeyman
        assert not (journeyman < apprentice)


class TestIsAtLeast:
    """AC-3: is_at_least gates correctly and handles unknown tier IDs."""

    def test_is_at_least_returns_true_for_equal_tier(self) -> None:
        cfg = _make_3tier_config()
        assert is_at_least(cfg, 30, "journeyman") is True

    def test_is_at_least_returns_true_for_higher_tier(self) -> None:
        cfg = _make_3tier_config()
        assert is_at_least(cfg, 70, "journeyman") is True

    def test_is_at_least_returns_false_for_lower_tier(self) -> None:
        cfg = _make_3tier_config()
        assert is_at_least(cfg, 10, "journeyman") is False

    def test_unknown_tier_id_returns_false_no_raise(self) -> None:
        cfg = _make_3tier_config()
        result = is_at_least(cfg, 100, "grand_master")
        assert result is False


# ---------------------------------------------------------------------------
# Frozen dataclasses and SubReputationDelta shape
# ---------------------------------------------------------------------------


class TestDataclassProperties:
    """OrganizationTier, OrganizationConfig, and SubReputationDelta are frozen."""

    def test_organization_tier_is_frozen(self) -> None:
        tier = OrganizationTier(id="t", name="T", rank=1, min_rep=0)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            tier.rank = 99  # type: ignore[misc]

    def test_organization_config_is_frozen(self) -> None:
        cfg = _make_1tier_config()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            cfg.id = "modified"  # type: ignore[misc]

    def test_sub_reputation_delta_is_frozen(self) -> None:
        cfg = _make_3tier_config()
        apprentice, journeyman, _ = cfg.tiers
        delta = SubReputationDelta(
            org_id="wreckers_guild",
            effective_amount=30,
            old_tier=apprentice,
            new_tier=journeyman,
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            delta.effective_amount = 0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AC-4 / AC-5 / AC-6 / AC-7: Player helper APIs
# ---------------------------------------------------------------------------


class TestPlayerSubReputationHelpers:
    """Tests for Player.modify_sub_reputation and companion helpers."""

    def _make_player(self):  # type: ignore[no-untyped-def]
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship

        dl = get_data_loader()
        ship_type = dl.ship_types["shuttle"]
        ship = Ship(ship_type=ship_type, current_fuel=40)
        return Player(name="TestPilot", credits=1000, current_system_id="nexus_prime", ship=ship)

    def test_new_player_has_empty_sub_reputation(self) -> None:
        player = self._make_player()
        assert player.sub_reputation == {}

    def test_get_sub_reputation_defaults_to_zero(self) -> None:
        player = self._make_player()
        assert player.get_sub_reputation("wreckers_guild") == 0

    def test_modify_sub_reputation_sets_value(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        success, _ = player.modify_sub_reputation("wreckers_guild", 20, cfg)
        assert success is True
        assert player.get_sub_reputation("wreckers_guild") == 20

    def test_modify_sub_reputation_accumulates(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 20, cfg)
        player.modify_sub_reputation("wreckers_guild", 15, cfg)
        assert player.get_sub_reputation("wreckers_guild") == 35

    def test_modify_sub_reputation_clamps_to_max_rep(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 200, cfg)
        assert player.get_sub_reputation("wreckers_guild") == 100

    def test_modify_sub_reputation_clamps_to_min_rep(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", -50, cfg)
        assert player.get_sub_reputation("wreckers_guild") == 0

    def test_modify_sub_reputation_returns_success_message(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        success, msg = player.modify_sub_reputation("wreckers_guild", 10, cfg)
        assert success is True
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_get_sub_reputation_tier_returns_lowest_when_absent(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        tier = player.get_sub_reputation_tier("wreckers_guild", cfg)
        assert tier.id == "apprentice"

    def test_get_sub_reputation_tier_returns_correct_tier(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 30, cfg)
        tier = player.get_sub_reputation_tier("wreckers_guild", cfg)
        assert tier.id == "journeyman"

    def test_is_at_least_tier_returns_false_when_absent(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        assert player.is_at_least_tier("wreckers_guild", "journeyman", cfg) is False

    def test_is_at_least_tier_returns_true_at_threshold(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 30, cfg)
        assert player.is_at_least_tier("wreckers_guild", "journeyman", cfg) is True

    def test_is_at_least_tier_returns_true_above_threshold(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 70, cfg)
        assert player.is_at_least_tier("wreckers_guild", "master", cfg) is True

    def test_is_at_least_tier_returns_false_for_unknown_tier_id(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 100, cfg)
        assert player.is_at_least_tier("wreckers_guild", "grand_master", cfg) is False


# ---------------------------------------------------------------------------
# AC-5: Notification queue (tier-change queueing)
# ---------------------------------------------------------------------------


class TestNotificationQueue:
    """AC-5: tier-crossing appends SubReputationDelta; no-change does not."""

    def _make_player(self):  # type: ignore[no-untyped-def]
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship

        dl = get_data_loader()
        ship_type = dl.ship_types["shuttle"]
        ship = Ship(ship_type=ship_type, current_fuel=40)
        return Player(name="TestPilot", credits=1000, current_system_id="nexus_prime", ship=ship)

    def test_no_delta_queued_when_no_tier_change(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        # 10 rep: still apprentice. No queue.
        player.modify_sub_reputation("wreckers_guild", 10, cfg)
        queue = getattr(player, "_pending_sub_rep_deltas", [])
        assert queue == []

    def test_tier_up_queues_delta(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        # Crossing apprentice -> journeyman at 30
        player.modify_sub_reputation("wreckers_guild", 30, cfg)
        queue: list[SubReputationDelta] = getattr(player, "_pending_sub_rep_deltas", [])
        assert len(queue) == 1
        delta = queue[0]
        assert delta.org_id == "wreckers_guild"
        assert delta.old_tier.id == "apprentice"
        assert delta.new_tier.id == "journeyman"
        assert delta.effective_amount == 30

    def test_tier_down_queues_delta(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        # Get to journeyman first
        player.modify_sub_reputation("wreckers_guild", 30, cfg)
        # Drain the queue
        player._pending_sub_rep_deltas = []  # type: ignore[attr-defined]
        # Now drop below the threshold: 30 - 5 = 25 -> apprentice
        player.modify_sub_reputation("wreckers_guild", -5, cfg)
        queue: list[SubReputationDelta] = getattr(player, "_pending_sub_rep_deltas", [])
        assert len(queue) == 1
        delta = queue[0]
        assert delta.old_tier.id == "journeyman"
        assert delta.new_tier.id == "apprentice"

    def test_no_tier_change_no_queue_entry(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 30, cfg)
        player._pending_sub_rep_deltas = []  # type: ignore[attr-defined]
        # Still journeyman after +5 (35 < 70)
        player.modify_sub_reputation("wreckers_guild", 5, cfg)
        queue = getattr(player, "_pending_sub_rep_deltas", [])
        assert queue == []

    def test_clamped_at_max_no_duplicate_queue(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        # Push to master first
        player.modify_sub_reputation("wreckers_guild", 70, cfg)
        player._pending_sub_rep_deltas = []  # type: ignore[attr-defined]
        # Now clamp at ceiling — no tier change, no queue
        player.modify_sub_reputation("wreckers_guild", 100, cfg)
        queue = getattr(player, "_pending_sub_rep_deltas", [])
        assert queue == []

    def test_multiple_tier_skips_queue_one_delta(self) -> None:
        """Jumping 2 tiers in one call: only one delta representing the net change."""
        player = self._make_player()
        cfg = _make_3tier_config()
        # 0 -> 80 crosses both journeyman and master thresholds
        player.modify_sub_reputation("wreckers_guild", 80, cfg)
        queue: list[SubReputationDelta] = getattr(player, "_pending_sub_rep_deltas", [])
        assert len(queue) == 1
        assert queue[0].old_tier.id == "apprentice"
        assert queue[0].new_tier.id == "master"


# ---------------------------------------------------------------------------
# AC-6: Orthogonality — sub-rep and faction-rep are independent
# ---------------------------------------------------------------------------


class TestOrthogonality:
    """AC-6: modifying sub-rep doesn't touch faction_reputation and vice versa."""

    def _make_player(self):  # type: ignore[no-untyped-def]
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship

        dl = get_data_loader()
        ship_type = dl.ship_types["shuttle"]
        ship = Ship(ship_type=ship_type, current_fuel=40)
        return Player(name="TestPilot", credits=1000, current_system_id="nexus_prime", ship=ship)

    def test_modify_sub_rep_does_not_touch_faction_reputation(self) -> None:
        player = self._make_player()
        player.faction_reputation = {"commerce_guild": 20}
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 50, cfg)
        assert player.faction_reputation == {"commerce_guild": 20}

    def test_modify_sub_rep_does_not_affect_other_orgs(self) -> None:
        player = self._make_player()
        cfg_a = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 50, cfg_a)
        assert player.get_sub_reputation("stellaris_auctioneer") == 0

    def test_modify_faction_rep_does_not_touch_sub_reputation(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 40, cfg)
        player.modify_reputation("commerce_guild", 30)
        assert player.get_sub_reputation("wreckers_guild") == 40


# ---------------------------------------------------------------------------
# AC-8 / AC-9 / AC-10: Save / load round-trip
# ---------------------------------------------------------------------------


class TestSaveRoundTrip:
    """AC-8/9/10: sub_reputation survives round-trip; queue is dropped; legacy saves load."""

    def _make_player(self):  # type: ignore[no-untyped-def]
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship

        dl = get_data_loader()
        ship_type = dl.ship_types["shuttle"]
        ship = Ship(ship_type=ship_type, current_fuel=40)
        return Player(name="TestPilot", credits=1000, current_system_id="nexus_prime", ship=ship)

    def _round_trip(self, player):  # type: ignore[no-untyped-def]
        from spacegame.save_manager import SaveManager

        sm = SaveManager()
        data = sm._serialize_player(player)
        return sm._deserialize_player(data)

    def test_sub_reputation_values_survive_round_trip(self) -> None:
        player = self._make_player()
        cfg_a = _make_3tier_config()
        cfg_b = _make_4tier_config()
        cfg_c = _make_1tier_config()
        player.modify_sub_reputation("wreckers_guild", 45, cfg_a)
        player.modify_sub_reputation("stellaris_auctioneer", 60, cfg_b)
        player.modify_sub_reputation("minimal_org", 30, cfg_c)

        player2 = self._round_trip(player)

        assert player2.get_sub_reputation("wreckers_guild") == 45
        assert player2.get_sub_reputation("stellaris_auctioneer") == 60
        assert player2.get_sub_reputation("minimal_org") == 30

    def test_sub_reputation_key_serialized(self) -> None:
        player = self._make_player()
        cfg = _make_3tier_config()
        player.modify_sub_reputation("wreckers_guild", 50, cfg)

        from spacegame.save_manager import SaveManager

        sm = SaveManager()
        data = sm._serialize_player(player)
        assert "sub_reputation" in data
        assert data["sub_reputation"]["wreckers_guild"] == 50

    def test_legacy_save_missing_key_loads_empty_dict(self) -> None:
        """AC-9: saves without sub_reputation key load without crash."""
        player = self._make_player()
        from spacegame.save_manager import SaveManager

        sm = SaveManager()
        data = sm._serialize_player(player)
        data.pop("sub_reputation", None)  # simulate legacy save

        player2 = sm._deserialize_player(data)
        assert player2.sub_reputation == {}

    def test_notification_queue_not_serialized(self) -> None:
        """AC-10: pending deltas are dropped across a round-trip."""
        player = self._make_player()
        cfg = _make_3tier_config()
        # Force a tier-up to populate the queue
        player.modify_sub_reputation("wreckers_guild", 30, cfg)
        assert len(getattr(player, "_pending_sub_rep_deltas", [])) > 0

        player2 = self._round_trip(player)
        queue = getattr(player2, "_pending_sub_rep_deltas", [])
        assert queue == []


# ---------------------------------------------------------------------------
# AC-11: 3 different organization shapes exercised
# (1-tier, 3-tier, 4-tier are all tested above; this is a combined smoke test)
# ---------------------------------------------------------------------------


class TestThreeOrgShapes:
    """AC-11: explicit smoke test using all three org shapes together."""

    def _make_player(self):  # type: ignore[no-untyped-def]
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship

        dl = get_data_loader()
        ship_type = dl.ship_types["shuttle"]
        ship = Ship(ship_type=ship_type, current_fuel=40)
        return Player(name="TestPilot", credits=1000, current_system_id="nexus_prime", ship=ship)

    def test_three_independent_orgs(self) -> None:
        player = self._make_player()
        cfg1 = _make_1tier_config()
        cfg3 = _make_3tier_config()
        cfg4 = _make_4tier_config()

        player.modify_sub_reputation("minimal_org", 40, cfg1)
        player.modify_sub_reputation("wreckers_guild", 50, cfg3)
        player.modify_sub_reputation("stellaris_auctioneer", 70, cfg4)

        assert player.get_sub_reputation("minimal_org") == 40
        assert player.get_sub_reputation("wreckers_guild") == 50
        assert player.get_sub_reputation("stellaris_auctioneer") == 70

        assert player.get_sub_reputation_tier("minimal_org", cfg1).id == "member"
        assert player.get_sub_reputation_tier("wreckers_guild", cfg3).id == "journeyman"
        assert player.get_sub_reputation_tier("stellaris_auctioneer", cfg4).id == "trusted"
