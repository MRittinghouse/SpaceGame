"""Tests for encounter definition data loading."""

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
}

VALID_DANGER_LEVELS = {"safe", "moderate", "dangerous"}

VALID_REWARD_TYPES = {
    "credits",
    "deduct_credits",
    "xp",
    "set_flag",
    "trade_permit",
    "remove_cargo",
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

    def test_definitions_not_empty(self) -> None:
        """At least 10 encounter definitions are loaded."""
        definitions = self._load()
        assert len(definitions) >= 10, f"Expected >= 10, got {len(definitions)}"

    def test_all_types_covered(self) -> None:
        """All 6 encounter types have at least one definition."""
        definitions = self._load()
        types_found = {d.encounter_type for d in definitions}
        for enc_type in VALID_ENCOUNTER_TYPES:
            assert enc_type in types_found, f"Missing encounter type: {enc_type}"

    def test_all_definitions_have_choices(self) -> None:
        """Every encounter definition has at least one choice."""
        definitions = self._load()
        for defn in definitions:
            assert len(defn.choices) >= 1, (
                f"Encounter {defn.id} has no choices"
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
