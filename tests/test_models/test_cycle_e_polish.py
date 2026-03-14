"""Tests for Cycle E Phase D — particle configs and new achievements."""

from spacegame.engine.particles import (
    ParticleConfig,
    MINING_CHAIN,
    ENERGY_REGEN,
    SALVAGE_SCAN,
    SALVAGE_CORRUPT,
    REFINE_COMPLETE,
)


class TestNewParticleConfigs:
    def test_mining_chain_config(self) -> None:
        assert isinstance(MINING_CHAIN, ParticleConfig)
        assert MINING_CHAIN.count > 0
        assert MINING_CHAIN.glow is True

    def test_energy_regen_config(self) -> None:
        assert isinstance(ENERGY_REGEN, ParticleConfig)
        assert ENERGY_REGEN.gravity < 0  # Float upward

    def test_salvage_scan_config(self) -> None:
        assert isinstance(SALVAGE_SCAN, ParticleConfig)
        assert SALVAGE_SCAN.spread == 360.0

    def test_salvage_corrupt_config(self) -> None:
        assert isinstance(SALVAGE_CORRUPT, ParticleConfig)
        assert SALVAGE_CORRUPT.gravity > 0  # Fall downward

    def test_refine_complete_config(self) -> None:
        assert isinstance(REFINE_COMPLETE, ParticleConfig)
        assert REFINE_COMPLETE.glow is True


class TestNewAchievements:
    def test_investor_achievement_loaded(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        achievement = next(
            (a for a in loader.achievements if a.id == "investor"), None
        )
        assert achievement is not None
        assert achievement.stat_key == "investments_owned"
        assert achievement.threshold == 5

    def test_efficiency_expert_achievement_loaded(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        achievement = next(
            (a for a in loader.achievements if a.id == "efficiency_expert"), None
        )
        assert achievement is not None
        assert achievement.stat_key == "s_ranks_earned"
        assert achievement.threshold == 1

    def test_total_achievements_count(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        assert len(loader.achievements) == 43  # 40 + 3 smuggling
