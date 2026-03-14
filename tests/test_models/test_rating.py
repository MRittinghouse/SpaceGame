"""Tests for session rating system — S/A/B/C/D performance grades."""

from spacegame.models.rating import (
    calculate_rating,
    MINING_THRESHOLDS,
    SALVAGE_THRESHOLDS,
    REFINING_THRESHOLDS,
    RATING_COLORS,
)


class TestCalculateRating:
    def test_s_rank(self) -> None:
        assert calculate_rating(15.0, MINING_THRESHOLDS) == "S"

    def test_s_rank_above_threshold(self) -> None:
        assert calculate_rating(20.0, MINING_THRESHOLDS) == "S"

    def test_a_rank(self) -> None:
        assert calculate_rating(10.0, MINING_THRESHOLDS) == "A"

    def test_b_rank(self) -> None:
        assert calculate_rating(6.0, MINING_THRESHOLDS) == "B"

    def test_c_rank(self) -> None:
        assert calculate_rating(3.0, MINING_THRESHOLDS) == "C"

    def test_d_rank(self) -> None:
        assert calculate_rating(2.9, MINING_THRESHOLDS) == "D"

    def test_zero_value(self) -> None:
        assert calculate_rating(0.0, MINING_THRESHOLDS) == "D"

    def test_negative_value(self) -> None:
        assert calculate_rating(-5.0, MINING_THRESHOLDS) == "D"


class TestSalvageThresholds:
    def test_s_rank(self) -> None:
        assert calculate_rating(0.80, SALVAGE_THRESHOLDS) == "S"

    def test_a_rank(self) -> None:
        assert calculate_rating(0.60, SALVAGE_THRESHOLDS) == "A"

    def test_b_rank(self) -> None:
        assert calculate_rating(0.40, SALVAGE_THRESHOLDS) == "B"

    def test_c_rank(self) -> None:
        assert calculate_rating(0.20, SALVAGE_THRESHOLDS) == "C"

    def test_d_rank(self) -> None:
        assert calculate_rating(0.19, SALVAGE_THRESHOLDS) == "D"


class TestRefiningThresholds:
    def test_s_rank(self) -> None:
        assert calculate_rating(10.0, REFINING_THRESHOLDS) == "S"

    def test_d_rank(self) -> None:
        assert calculate_rating(1.0, REFINING_THRESHOLDS) == "D"


class TestRatingColors:
    def test_all_ratings_have_colors(self) -> None:
        for rating in ["S", "A", "B", "C", "D"]:
            assert rating in RATING_COLORS
            assert len(RATING_COLORS[rating]) == 3

    def test_s_is_gold(self) -> None:
        assert RATING_COLORS["S"] == (255, 215, 0)
