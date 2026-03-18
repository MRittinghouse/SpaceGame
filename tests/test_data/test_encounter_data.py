"""Tests for encounter definition data loading and validation."""

from pathlib import Path

from spacegame.data_loader import DataLoader
from spacegame.models.encounter import EncounterDefinition


# Valid encounter types that the system supports
VALID_ENCOUNTER_TYPES = {
    "distress_signal",
    "derelict",
    "merchant",
    "debris",
    "anomaly",
    "shakedown",
    "patrol",
    "smuggler",
    "refugee",
    "comm_intercept",
    "wildlife",
}

VALID_DANGER_LEVELS = {"safe", "moderate", "dangerous"}

VALID_REWARD_TYPES = {
    "credits",
    "deduct_credits",
    "xp",
    "set_flag",
    "trade_permit",
    "remove_cargo",
    "modify_reputation",
    "add_criminal_heat",
    "confiscate_cargo",
    "reduce_criminal_heat",
    "bounty_immunity",
    "start_bounty_combat",
}

VALID_TONES = {"", "neutral", "humorous", "mysterious", "aggressive", "dark_humor"}

VALID_CATEGORIES = {
    "",
    "generic",
    "faction",
    "system",
    "campaign",
    "lore",
    "easter_egg",
}

VALID_FACTION_IDS = {
    "",
    "commerce_guild",
    "miners_union",
    "science_collective",
    "frontier_alliance",
}

VALID_SYSTEM_IDS = {
    "nexus_prime",
    "stellaris_port",
    "verdant",
    "havens_rest",
    "forgeworks",
    "axiom_labs",
    "nova_research",
    "breakstone",
    "iron_depths",
    "crimson_reach",
    "the_fulcrum",
}


class TestEncounterDataLoading:
    """Tests that encounter definitions load correctly from JSON."""

    def _load(self) -> list[EncounterDefinition]:
        """Load encounter definitions via DataLoader."""
        project_root = Path(__file__).parent.parent.parent
        loader = DataLoader(data_dir=project_root / "data")
        loader.load_encounter_definitions()
        return loader.encounter_definitions

    def test_file_loads_without_error(self) -> None:
        """Encounter definitions JSON loads successfully."""
        definitions = self._load()
        assert definitions is not None

    def test_minimum_encounter_count(self) -> None:
        """At least 120 encounter definitions are loaded."""
        definitions = self._load()
        assert len(definitions) >= 120, f"Expected >= 120, got {len(definitions)}"

    def test_multi_file_loading(self) -> None:
        """Encounters load from multiple JSON files in the encounters directory."""
        definitions = self._load()
        # Should have encounters from various categories
        categories = {d.category for d in definitions if d.category}
        assert len(categories) >= 4, (
            f"Expected encounters from >= 4 categories, got {categories}"
        )

    def test_no_duplicate_ids(self) -> None:
        """All encounter IDs are unique across all files."""
        definitions = self._load()
        ids = [d.id for d in definitions]
        duplicates = [eid for eid in ids if ids.count(eid) > 1]
        assert len(duplicates) == 0, f"Duplicate encounter IDs: {set(duplicates)}"

    def test_all_types_covered(self) -> None:
        """All encounter types in weight tables have at least one definition."""
        definitions = self._load()
        types_found = {d.encounter_type for d in definitions}
        # At minimum, the original 6 types plus new ones should have definitions
        required_types = {
            "distress_signal", "derelict", "merchant", "debris",
            "anomaly", "shakedown",
        }
        for enc_type in required_types:
            assert enc_type in types_found, f"Missing encounter type: {enc_type}"

    def test_all_definitions_have_choices(self) -> None:
        """Every encounter definition has at least one choice."""
        definitions = self._load()
        for defn in definitions:
            assert len(defn.choices) >= 1, (
                f"Encounter {defn.id} has no choices"
            )

    def test_choice_count_range(self) -> None:
        """Every encounter has 2-3 choices (except campaign weight-0)."""
        definitions = self._load()
        for defn in definitions:
            assert 2 <= len(defn.choices) <= 3, (
                f"Encounter {defn.id} has {len(defn.choices)} choices, expected 2-3"
            )

    def test_all_choices_have_outcomes(self) -> None:
        """Every choice has a non-empty outcome description."""
        definitions = self._load()
        for defn in definitions:
            for choice in defn.choices:
                assert choice.outcome.description, (
                    f"Empty outcome in encounter {defn.id}, choice {choice.id}"
                )

    def test_all_reward_types_valid(self) -> None:
        """All rewards in encounter definitions use valid reward types."""
        definitions = self._load()
        for defn in definitions:
            for choice in defn.choices:
                for reward in choice.outcome.rewards:
                    assert reward.reward_type in VALID_REWARD_TYPES, (
                        f"Invalid reward_type '{reward.reward_type}' in "
                        f"encounter {defn.id}, choice {choice.id}"
                    )

    def test_danger_levels_valid(self) -> None:
        """All danger_levels in definitions are valid values."""
        definitions = self._load()
        for defn in definitions:
            for level in defn.danger_levels:
                assert level in VALID_DANGER_LEVELS, (
                    f"Invalid danger level '{level}' in encounter {defn.id}"
                )

    def test_encounter_types_valid(self) -> None:
        """All encounter_type values are from the valid set."""
        definitions = self._load()
        for defn in definitions:
            assert defn.encounter_type in VALID_ENCOUNTER_TYPES, (
                f"Invalid encounter type '{defn.encounter_type}' in {defn.id}"
            )

    def test_shakedown_uses_sentinel_amount(self) -> None:
        """Shakedown encounters use amount=-1 sentinel for deduct_credits."""
        definitions = self._load()
        shakedowns = [d for d in definitions if d.encounter_type == "shakedown"]
        assert len(shakedowns) >= 1, "Need at least one shakedown definition"
        for defn in shakedowns:
            pay_choices = [
                c for c in defn.choices
                if any(r.reward_type == "deduct_credits" for r in c.outcome.rewards)
            ]
            for choice in pay_choices:
                for reward in choice.outcome.rewards:
                    if reward.reward_type == "deduct_credits":
                        assert reward.amount == -1, (
                            f"Shakedown {defn.id} pay choice should use "
                            f"sentinel amount=-1, got {reward.amount}"
                        )

    def test_tone_values_valid(self) -> None:
        """All tone values are from the known set."""
        definitions = self._load()
        for defn in definitions:
            assert defn.tone in VALID_TONES, (
                f"Invalid tone '{defn.tone}' in encounter {defn.id}"
            )

    def test_category_values_valid(self) -> None:
        """All category values are from the known set."""
        definitions = self._load()
        for defn in definitions:
            assert defn.category in VALID_CATEGORIES, (
                f"Invalid category '{defn.category}' in encounter {defn.id}"
            )

    def test_only_systems_reference_valid_systems(self) -> None:
        """All system IDs in only_systems exist in the known set."""
        definitions = self._load()
        for defn in definitions:
            for sys_id in defn.only_systems:
                assert sys_id in VALID_SYSTEM_IDS, (
                    f"Invalid system '{sys_id}' in only_systems of {defn.id}"
                )

    def test_excluded_systems_reference_valid_systems(self) -> None:
        """All system IDs in excluded_systems exist in the known set."""
        definitions = self._load()
        for defn in definitions:
            for sys_id in defn.excluded_systems:
                assert sys_id in VALID_SYSTEM_IDS, (
                    f"Invalid system '{sys_id}' in excluded_systems of {defn.id}"
                )

    def test_required_factions_valid(self) -> None:
        """All required_faction values are known faction IDs."""
        definitions = self._load()
        for defn in definitions:
            assert defn.required_faction in VALID_FACTION_IDS, (
                f"Invalid faction '{defn.required_faction}' in {defn.id}"
            )

    def test_faction_encounter_distribution(self) -> None:
        """Each faction has at least 8 encounters."""
        definitions = self._load()
        for faction_id in ["commerce_guild", "miners_union", "science_collective", "frontier_alliance"]:
            count = sum(1 for d in definitions if d.required_faction == faction_id)
            assert count >= 8, (
                f"Faction {faction_id} has only {count} encounters, expected >= 8"
            )

    def test_unique_encounters_exist(self) -> None:
        """At least 10 unique (one-time) encounters are defined."""
        definitions = self._load()
        unique_count = sum(1 for d in definitions if d.unique)
        assert unique_count >= 10, (
            f"Expected >= 10 unique encounters, got {unique_count}"
        )

    def test_new_encounter_types_have_definitions(self) -> None:
        """New encounter types (patrol, comm_intercept, refugee) have definitions."""
        definitions = self._load()
        types_found = {d.encounter_type for d in definitions}
        new_types = {"patrol", "comm_intercept", "refugee"}
        for enc_type in new_types:
            assert enc_type in types_found, (
                f"New encounter type '{enc_type}' has no definitions"
            )
