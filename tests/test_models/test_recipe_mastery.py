"""Tests for recipe mastery tracking."""

from spacegame.models.recipe_mastery import (
    MASTERY_THRESHOLDS,
    RecipeMasteryEntry,
    RecipeMasteryTracker,
)


class TestRecipeMasteryEntry:
    """Tests for RecipeMasteryEntry defaults."""

    def test_default_entry(self) -> None:
        entry = RecipeMasteryEntry(recipe_id="smelt_iron")
        assert entry.times_crafted == 0
        assert entry.mastery_level == 0


class TestRecipeMasteryTracker:
    """Tests for RecipeMasteryTracker craft recording and bonuses."""

    def _make_tracker(self) -> RecipeMasteryTracker:
        return RecipeMasteryTracker()

    def test_record_craft_no_threshold(self) -> None:
        tracker = self._make_tracker()
        result = tracker.record_craft("smelt_iron")
        assert result is None, "Single craft should not cross any threshold"
        assert tracker.get_mastery("smelt_iron").times_crafted == 1

    def test_record_craft_reaches_level_1(self) -> None:
        tracker = self._make_tracker()
        for _ in range(MASTERY_THRESHOLDS[0] - 1):
            tracker.record_craft("smelt_iron")
        result = tracker.record_craft("smelt_iron")
        assert result == 1, f"Should reach mastery level 1 at {MASTERY_THRESHOLDS[0]} crafts"
        assert tracker.get_mastery("smelt_iron").mastery_level == 1

    def test_record_craft_reaches_level_2(self) -> None:
        tracker = self._make_tracker()
        for _ in range(MASTERY_THRESHOLDS[1]):
            tracker.record_craft("smelt_iron")
        assert tracker.get_mastery("smelt_iron").mastery_level == 2

    def test_record_craft_reaches_level_3(self) -> None:
        tracker = self._make_tracker()
        for _ in range(MASTERY_THRESHOLDS[2]):
            tracker.record_craft("smelt_iron")
        assert tracker.get_mastery("smelt_iron").mastery_level == 3

    def test_no_level_past_3(self) -> None:
        tracker = self._make_tracker()
        for _ in range(MASTERY_THRESHOLDS[2]):
            tracker.record_craft("smelt_iron")
        assert tracker.get_mastery("smelt_iron").mastery_level == 3
        # Additional crafts should not increase level further
        for _ in range(5):
            result = tracker.record_craft("smelt_iron")
            assert result is None, "Should not gain levels past 3"
        assert tracker.get_mastery("smelt_iron").mastery_level == 3
        assert tracker.get_mastery("smelt_iron").times_crafted == 20

    def test_get_speed_bonus_none(self) -> None:
        tracker = self._make_tracker()
        assert tracker.get_speed_bonus("smelt_iron") == 0.0

    def test_get_speed_bonus_level_1(self) -> None:
        tracker = self._make_tracker()
        for _ in range(MASTERY_THRESHOLDS[0]):
            tracker.record_craft("smelt_iron")
        assert tracker.get_speed_bonus("smelt_iron") == 0.10

    def test_get_yield_bonus_level_2(self) -> None:
        tracker = self._make_tracker()
        for _ in range(MASTERY_THRESHOLDS[1]):
            tracker.record_craft("smelt_iron")
        assert tracker.get_yield_bonus("smelt_iron") == 1

    def test_get_yield_bonus_below_2(self) -> None:
        tracker = self._make_tracker()
        assert tracker.get_yield_bonus("smelt_iron") == 0
        # Level 1 also gets no yield bonus
        for _ in range(MASTERY_THRESHOLDS[0]):
            tracker.record_craft("smelt_iron")
        assert tracker.get_yield_bonus("smelt_iron") == 0

    def test_serialization_round_trip(self) -> None:
        tracker = self._make_tracker()
        for _ in range(MASTERY_THRESHOLDS[1]):
            tracker.record_craft("smelt_iron")
        for _ in range(MASTERY_THRESHOLDS[0]):
            tracker.record_craft("refine_gold")

        data = tracker.to_dict()
        restored = RecipeMasteryTracker.from_dict(data)

        iron = restored.get_mastery("smelt_iron")
        assert iron.times_crafted == MASTERY_THRESHOLDS[1]
        assert iron.mastery_level == 2

        gold = restored.get_mastery("refine_gold")
        assert gold.times_crafted == MASTERY_THRESHOLDS[0]
        assert gold.mastery_level == 1
