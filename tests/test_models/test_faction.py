"""Tests for faction reputation system."""

from types import SimpleNamespace

from spacegame.models.faction import (
    Faction,
    ReputationTier,
    get_reputation_tier,
    get_tariff_modifier,
    generate_faction_assignments,
)


class TestReputationTier:
    """Tests for reputation tier calculation."""

    def test_hostile_at_negative_100(self) -> None:
        assert get_reputation_tier(-100) == ReputationTier.HOSTILE

    def test_hostile_at_negative_50(self) -> None:
        assert get_reputation_tier(-50) == ReputationTier.HOSTILE

    def test_unfriendly_at_negative_49(self) -> None:
        assert get_reputation_tier(-49) == ReputationTier.UNFRIENDLY

    def test_unfriendly_at_negative_20(self) -> None:
        assert get_reputation_tier(-20) == ReputationTier.UNFRIENDLY

    def test_neutral_at_negative_19(self) -> None:
        assert get_reputation_tier(-19) == ReputationTier.NEUTRAL

    def test_neutral_at_zero(self) -> None:
        assert get_reputation_tier(0) == ReputationTier.NEUTRAL

    def test_neutral_at_positive_19(self) -> None:
        assert get_reputation_tier(19) == ReputationTier.NEUTRAL

    def test_friendly_at_positive_20(self) -> None:
        assert get_reputation_tier(20) == ReputationTier.FRIENDLY

    def test_friendly_at_positive_49(self) -> None:
        assert get_reputation_tier(49) == ReputationTier.FRIENDLY

    def test_allied_at_positive_50(self) -> None:
        assert get_reputation_tier(50) == ReputationTier.ALLIED

    def test_allied_at_positive_100(self) -> None:
        assert get_reputation_tier(100) == ReputationTier.ALLIED


class TestTariffModifier:
    """Tests for tariff modifier based on reputation."""

    def test_hostile_tariff(self) -> None:
        assert get_tariff_modifier(-75) == 0.30

    def test_unfriendly_tariff(self) -> None:
        assert get_tariff_modifier(-30) == 0.15

    def test_neutral_tariff(self) -> None:
        assert get_tariff_modifier(0) == 0.0

    def test_friendly_tariff(self) -> None:
        assert get_tariff_modifier(35) == -0.10

    def test_allied_tariff(self) -> None:
        assert get_tariff_modifier(80) == -0.20


class TestFaction:
    """Tests for Faction dataclass."""

    def test_creation(self) -> None:
        faction = Faction(
            id="commerce_guild",
            name="Commerce Guild",
            description="A trading consortium.",
            color=(100, 150, 255),
            rivalry="miners_union",
        )
        assert faction.id == "commerce_guild"
        assert faction.name == "Commerce Guild"
        assert faction.color == (100, 150, 255)
        assert faction.rivalry == "miners_union"

    def test_display_name(self) -> None:
        faction = Faction(
            id="miners_union",
            name="Miners Union",
            description="A mining alliance.",
            color=(200, 150, 50),
            rivalry="commerce_guild",
        )
        assert faction.name == "Miners Union"


class TestGenerateFactionAssignments:
    """The assignment reads each system's faction_id; it no longer deals (BB-74)."""

    def test_each_held_system_keeps_its_faction(self) -> None:
        systems = [
            SimpleNamespace(id="a", faction_id="commerce_guild"),
            SimpleNamespace(id="b", faction_id="miners_union"),
        ]
        assert generate_faction_assignments(systems) == {
            "a": "commerce_guild",
            "b": "miners_union",
        }

    def test_an_unheld_system_is_left_out(self) -> None:
        systems = [
            SimpleNamespace(id="a", faction_id="commerce_guild"),
            SimpleNamespace(id="mark", faction_id=""),
        ]
        assert generate_faction_assignments(systems) == {"a": "commerce_guild"}

    def test_every_call_gives_the_same_map(self) -> None:
        systems = [SimpleNamespace(id=f"s{i}", faction_id="frontier_alliance") for i in range(12)]
        first = generate_faction_assignments(systems)
        assert all(generate_faction_assignments(systems) == first for _ in range(20))
