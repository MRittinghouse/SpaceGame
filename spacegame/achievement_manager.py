"""
Achievement tracking and reward system.

Checks player stats against achievement thresholds and applies rewards.
"""

from typing import Optional
from spacegame.models.achievement import Achievement
from spacegame.models.player import Player
from spacegame.utils.logger import logger


class AchievementManager:
    """Manages achievement checking, unlocking, and reward application."""

    def __init__(self, achievements: list[Achievement]) -> None:
        """
        Initialize with achievement definitions.

        Args:
            achievements: All achievement definitions from data loader.
        """
        self.achievements = {a.id: a for a in achievements}

    def _get_stat_value(self, player: Player, stat_key: str) -> int:
        """Get a player stat value by key name.

        Args:
            player: Player to read stat from.
            stat_key: Name of the stat field.

        Returns:
            Current stat value.
        """
        if stat_key == "systems_discovered":
            return len(player.systems_visited)
        if stat_key == "level":
            return player.progression.level
        if stat_key == "unique_recipes_crafted":
            return len(player.recipes_crafted)
        return getattr(player, stat_key, 0)

    def check_achievements(self, player: Player) -> list[Achievement]:
        """Compare player stats against thresholds, return newly unlocked.

        Args:
            player: Player to check achievements for.

        Returns:
            List of newly unlocked achievements (not previously unlocked).
        """
        newly_unlocked: list[Achievement] = []

        for achievement in self.achievements.values():
            if achievement.id in player.unlocked_achievements:
                continue

            stat_value = self._get_stat_value(player, achievement.stat_key)
            if stat_value >= achievement.threshold:
                player.unlocked_achievements.append(achievement.id)
                newly_unlocked.append(achievement)
                logger.info(
                    f"Achievement unlocked: {achievement.name} "
                    f"({achievement.stat_key} = {stat_value} >= {achievement.threshold})"
                )

        return newly_unlocked

    def apply_reward(self, player: Player, achievement: Achievement) -> str:
        """Apply achievement reward to player.

        Args:
            player: Player to receive reward.
            achievement: Achievement whose reward to apply.

        Returns:
            Human-readable reward description.
        """
        if achievement.reward_type == "xp":
            player.progression.add_xp(achievement.reward_value)
            return f"+{achievement.reward_value} XP"
        elif achievement.reward_type == "credits":
            player.add_credits(achievement.reward_value)
            return f"+{achievement.reward_value:,} Credits"
        elif achievement.reward_type == "skill_point":
            player.progression.skill_points += achievement.reward_value
            return f"+{achievement.reward_value} Skill Point{'s' if achievement.reward_value > 1 else ''}"
        elif achievement.reward_type == "upgrade":
            # Upgrade rewards would add a specific upgrade to the player
            return f"Upgrade: {achievement.reward_value}"
        else:
            logger.warning(f"Unknown reward type: {achievement.reward_type}")
            return ""

    def get_all_achievements(self) -> list[Achievement]:
        """Get all achievement definitions."""
        return list(self.achievements.values())

    def get_unlocked(self, player: Player) -> list[str]:
        """Return list of unlocked achievement IDs.

        Args:
            player: Player to check.

        Returns:
            List of unlocked achievement IDs.
        """
        return list(player.unlocked_achievements)

    def get_progress(self, player: Player, achievement_id: str) -> float:
        """Get progress toward an achievement as 0.0-1.0.

        Args:
            player: Player to check.
            achievement_id: Achievement to check progress for.

        Returns:
            Progress fraction (clamped to 0.0-1.0).
        """
        achievement = self.achievements.get(achievement_id)
        if not achievement:
            return 0.0
        stat_value = self._get_stat_value(player, achievement.stat_key)
        if achievement.threshold <= 0:
            return 1.0
        return min(1.0, stat_value / achievement.threshold)
