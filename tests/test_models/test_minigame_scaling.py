"""Tests for danger-level yield scaling in mining and salvage mini-games."""

import math

from spacegame.config import DANGER_YIELD_MULTIPLIERS
from spacegame.models.mining import MiningConfig, MiningSession
from spacegame.models.salvage import SalvageConfig, SalvageSession


class TestDangerYieldConstants:
    """DANGER_YIELD_MULTIPLIERS should have correct values."""

    def test_safe_multiplier(self) -> None:
        assert DANGER_YIELD_MULTIPLIERS["safe"] == 1.0

    def test_moderate_multiplier(self) -> None:
        assert DANGER_YIELD_MULTIPLIERS["moderate"] == 1.15

    def test_dangerous_multiplier(self) -> None:
        assert DANGER_YIELD_MULTIPLIERS["dangerous"] == 1.3

    def test_unknown_defaults_to_one(self) -> None:
        assert DANGER_YIELD_MULTIPLIERS.get("unknown", 1.0) == 1.0


class TestMiningConfigDangerLevel:
    """MiningConfig should support danger_level field."""

    def test_default_danger_level(self) -> None:
        config = MiningConfig(system_id="test_system")
        assert config.danger_level == "safe"

    def test_custom_danger_level(self) -> None:
        config = MiningConfig(system_id="test_system", danger_level="dangerous")
        assert config.danger_level == "dangerous"


class TestMiningDangerYieldScaling:
    """MiningSession should scale yields by danger level."""

    def _make_session(self, danger_level: str = "safe") -> MiningSession:
        config = MiningConfig(system_id="test", danger_level=danger_level)
        return MiningSession(config=config)

    def test_safe_yields_unmodified(self) -> None:
        session = self._make_session("safe")
        result = session._apply_yield_bonus(10)
        assert result == 10

    def test_dangerous_yields_higher(self) -> None:
        session = self._make_session("dangerous")
        result = session._apply_yield_bonus(10)
        assert result == math.floor(10 * 1.3)  # 13

    def test_moderate_yields_intermediate(self) -> None:
        session = self._make_session("moderate")
        result = session._apply_yield_bonus(10)
        assert result == math.floor(10 * 1.15)  # 11

    def test_unknown_danger_level_no_scaling(self) -> None:
        session = self._make_session("unknown")
        result = session._apply_yield_bonus(10)
        assert result == 10


class TestSalvageConfigDangerLevel:
    """SalvageConfig should support danger_level field."""

    def test_default_danger_level(self) -> None:
        config = SalvageConfig(system_id="test_system")
        assert config.danger_level == "safe"

    def test_custom_danger_level(self) -> None:
        config = SalvageConfig(system_id="test_system", danger_level="dangerous")
        assert config.danger_level == "dangerous"


class TestSalvageDangerYieldScaling:
    """SalvageSession should scale yields by danger level."""

    def _make_session(self, danger_level: str = "safe") -> SalvageSession:
        config = SalvageConfig(system_id="test", danger_level=danger_level)
        return SalvageSession(config=config)

    def test_safe_yields_unmodified(self) -> None:
        session = self._make_session("safe")
        result = session._apply_danger_multiplier(10)
        assert result == 10

    def test_dangerous_yields_higher(self) -> None:
        session = self._make_session("dangerous")
        result = session._apply_danger_multiplier(10)
        assert result == math.floor(10 * 1.3)  # 13

    def test_moderate_yields_intermediate(self) -> None:
        session = self._make_session("moderate")
        result = session._apply_danger_multiplier(10)
        assert result == math.floor(10 * 1.15)  # 11

    def test_minimum_yield_is_one(self) -> None:
        """Even with scaling, yield should never be less than 1."""
        session = self._make_session("safe")
        result = session._apply_danger_multiplier(1)
        assert result >= 1
