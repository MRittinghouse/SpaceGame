"""Tests for faction reputation system."""

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
    """Tests for random faction assignment to systems."""

    def _system_ids(self) -> list[str]:
        return [
            "nexus_prime",
            "verdant",
            "forgeworks",
            "breakstone",
            "axiom_labs",
            "havens_rest",
            "crimson_reach",
            "stellaris_port",
            "iron_depths",
            "nova_research",
        ]

    def _faction_ids(self) -> list[str]:
        return ["commerce_guild", "miners_union", "science_collective", "frontier_alliance"]

    def test_covers_all_systems(self) -> None:
        assignments = generate_faction_assignments(self._system_ids(), self._faction_ids())
        assert set(assignments.keys()) == set(self._system_ids())

    def test_uses_only_valid_factions(self) -> None:
        assignments = generate_faction_assignments(self._system_ids(), self._faction_ids())
        for faction_id in assignments.values():
            assert faction_id in self._faction_ids(), f"Unexpected faction: {faction_id}"

    def test_balanced_distribution(self) -> None:
        """Each faction should get 2-3 systems for 10 systems / 4 factions."""
        assignments = generate_faction_assignments(self._system_ids(), self._faction_ids())
        counts: dict[str, int] = {}
        for faction_id in assignments.values():
            counts[faction_id] = counts.get(faction_id, 0) + 1
        for faction_id, count in counts.items():
            assert 2 <= count <= 3, f"{faction_id} got {count} systems, expected 2-3"

    def test_all_factions_represented(self) -> None:
        assignments = generate_faction_assignments(self._system_ids(), self._faction_ids())
        assigned_factions = set(assignments.values())
        assert assigned_factions == set(self._faction_ids())

    def test_different_calls_can_produce_different_results(self) -> None:
        """Multiple calls should eventually produce different assignments."""
        results = set()
        for _ in range(20):
            assignments = generate_faction_assignments(self._system_ids(), self._faction_ids())
            # Create a hashable representation
            result_tuple = tuple(sorted(assignments.items()))
            results.add(result_tuple)
        assert len(results) > 1, "20 calls should produce at least 2 different assignments"

    def test_fewer_systems_than_factions(self) -> None:
        """Edge case: fewer systems than factions."""
        assignments = generate_faction_assignments(["sys_a", "sys_b"], self._faction_ids())
        assert len(assignments) == 2
        for fid in assignments.values():
            assert fid in self._faction_ids()

    def test_equal_systems_and_factions(self) -> None:
        """Edge case: same number of systems as factions."""
        systems = ["sys_a", "sys_b", "sys_c", "sys_d"]
        assignments = generate_faction_assignments(systems, self._faction_ids())
        assert len(assignments) == 4
        # Each faction should get exactly 1
        assert set(assignments.values()) == set(self._faction_ids())
