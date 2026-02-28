"""
Save/Load system for SpaceGame.

Handles saving and loading game state to/from JSON files.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import asdict

from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.models.market import Market
from spacegame.models.event import MarketEvent
from spacegame.utils.logger import logger


class SaveManager:
    """
    Manages save/load operations for the game.

    Save files are stored as JSON in the configured save directory.
    Supports multiple save slots with metadata.
    """

    SAVE_VERSION = "1.0"
    DEFAULT_NUM_SLOTS = 12

    def __init__(self, save_directory: Optional[Path] = None):
        """
        Initialize the save manager.

        Args:
            save_directory: Custom save directory path. If None, uses AppData default.
        """
        if save_directory:
            self.save_dir = Path(save_directory)
        else:
            # Default to AppData on Windows, ~/.spacegame on Unix
            if os.name == "nt":  # Windows
                appdata = os.getenv("APPDATA")
                self.save_dir = Path(appdata) / "SpaceGame" / "saves"
            else:  # Unix/Mac
                home = Path.home()
                self.save_dir = home / ".spacegame" / "saves"

        # Create save directory if it doesn't exist
        self.save_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Save directory: {self.save_dir}")

    def get_save_file_path(self, slot: int) -> Path:
        """Get the file path for a save slot."""
        return self.save_dir / f"save_slot_{slot}.json"

    def save_game(
        self,
        slot: int,
        player: Player,
        markets: Dict[str, Market],
        active_events: Dict[str, MarketEvent],
        playtime_seconds: int,
        save_name: Optional[str] = None,
        event_log: Optional[List[Dict[str, Any]]] = None,
        tutorial_state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save the current game state to a slot.

        Args:
            slot: Save slot number (0-11)
            player: Player object
            markets: Dictionary of system_id -> Market
            active_events: Dictionary of system_id -> MarketEvent
            playtime_seconds: Total playtime in seconds
            save_name: Optional custom name for the save

        Returns:
            True if save successful, False otherwise
        """
        try:
            save_data = self._serialize_game_state(
                player,
                markets,
                active_events,
                playtime_seconds,
                save_name,
                event_log=event_log,
                tutorial_state=tutorial_state,
            )

            save_path = self.get_save_file_path(slot)
            with open(save_path, "w") as f:
                json.dump(save_data, f, indent=2)

            logger.info(f"Game saved to slot {slot}: {save_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save game to slot {slot}: {e}")
            return False

    def load_game(self, slot: int) -> Optional[Dict[str, Any]]:
        """
        Load game state from a slot.

        Args:
            slot: Save slot number (0-11)

        Returns:
            Dictionary containing deserialized game state, or None if load fails
        """
        try:
            save_path = self.get_save_file_path(slot)

            if not save_path.exists():
                logger.warning(f"Save file not found: {save_path}")
                return None

            with open(save_path, "r") as f:
                save_data = json.load(f)

            # Validate save version
            if save_data.get("version") != self.SAVE_VERSION:
                logger.warning(
                    f"Save file version mismatch: {save_data.get('version')} != {self.SAVE_VERSION}"
                )
                # TODO: Implement save migration in future

            deserialized = self._deserialize_game_state(save_data)
            logger.info(f"Game loaded from slot {slot}: {save_path}")
            return deserialized

        except Exception as e:
            logger.error(f"Failed to load game from slot {slot}: {e}")
            return None

    def get_save_metadata(self, slot: int) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a save slot without loading the full game state.

        Args:
            slot: Save slot number

        Returns:
            Dictionary with metadata (name, timestamp, credits, location, playtime)
            or None if slot is empty
        """
        try:
            save_path = self.get_save_file_path(slot)

            if not save_path.exists():
                return None

            with open(save_path, "r") as f:
                save_data = json.load(f)

            return save_data.get("metadata", {})

        except Exception as e:
            logger.error(f"Failed to read save metadata for slot {slot}: {e}")
            return None

    def get_all_save_metadata(self) -> List[Optional[Dict[str, Any]]]:
        """
        Get metadata for all save slots.

        Returns:
            List of metadata dictionaries (None for empty slots)
        """
        return [self.get_save_metadata(i) for i in range(self.DEFAULT_NUM_SLOTS)]

    def delete_save(self, slot: int) -> bool:
        """
        Delete a save file.

        Args:
            slot: Save slot number

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            save_path = self.get_save_file_path(slot)

            if save_path.exists():
                save_path.unlink()
                logger.info(f"Deleted save in slot {slot}")
                return True
            else:
                logger.warning(f"No save file to delete in slot {slot}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete save in slot {slot}: {e}")
            return False

    def get_most_recent_save_slot(self) -> Optional[int]:
        """
        Find the most recently saved slot.

        Returns:
            Slot number of most recent save, or None if no saves exist
        """
        most_recent_slot = None
        most_recent_time = None

        for slot in range(self.DEFAULT_NUM_SLOTS):
            metadata = self.get_save_metadata(slot)
            if metadata:
                timestamp_str = metadata.get("timestamp")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if most_recent_time is None or timestamp > most_recent_time:
                        most_recent_time = timestamp
                        most_recent_slot = slot

        return most_recent_slot

    def _serialize_game_state(
        self,
        player: Player,
        markets: Dict[str, Market],
        active_events: Dict[str, MarketEvent],
        playtime_seconds: int,
        save_name: Optional[str],
        event_log: Optional[List[Dict[str, Any]]] = None,
        tutorial_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Serialize game state to dictionary for JSON saving."""
        # Get current system name for metadata
        from spacegame.data_loader import get_data_loader

        data_loader = get_data_loader()
        current_system = data_loader.get_system(player.current_system_id)
        current_system_name = current_system.name if current_system else player.current_system_id

        timestamp = datetime.now().isoformat()

        return {
            "version": self.SAVE_VERSION,
            "metadata": {
                "name": save_name or f"Save {timestamp}",
                "timestamp": timestamp,
                "credits": player.credits,
                "location": current_system_name,
                "playtime_seconds": playtime_seconds,
                "game_day": player.game_day,
            },
            "player": self._serialize_player(player),
            "markets": self._serialize_markets(markets),
            "active_events": self._serialize_events(active_events),
            "event_log": event_log or [],
            "tutorial": tutorial_state or {},
            "playtime_seconds": playtime_seconds,
        }

    def _deserialize_game_state(self, save_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize game state from loaded JSON."""
        return {
            "player": self._deserialize_player(save_data["player"]),
            "markets": self._deserialize_markets(save_data["markets"]),
            "active_events": self._deserialize_events(save_data.get("active_events", {})),
            "event_log": save_data.get("event_log", []),
            "tutorial": save_data.get("tutorial", {}),
            "playtime_seconds": save_data.get("playtime_seconds", 0),
            "metadata": save_data.get("metadata", {}),
        }

    def _serialize_player(self, player: Player) -> Dict[str, Any]:
        """Serialize Player object."""
        result = {
            "name": player.name,
            "credits": player.credits,
            "current_system_id": player.current_system_id,
            "game_day": player.game_day,
            "ship": self._serialize_ship(player.ship),
            "progression": player.progression.to_dict(),
            "upgrades": player.upgrade_manager.to_dict(),
            "trades_completed": player.trades_completed,
            "total_profit": player.total_profit,
            "systems_visited": list(player.systems_visited),
            "credits_earned_lifetime": player.credits_earned_lifetime,
            "credits_spent_lifetime": player.credits_spent_lifetime,
            "largest_single_profit": player.largest_single_profit,
            "jumps_traveled": player.jumps_traveled,
            "fuel_consumed": player.fuel_consumed,
            "ore_mined": player.ore_mined,
            "items_salvaged": player.items_salvaged,
            "items_refined": player.items_refined,
            "unlocked_achievements": player.unlocked_achievements,
            "drone_fleet": player.drone_fleet.to_dict(),
            "faction_reputation": player.faction_reputation,
            "faction_assignments": player.faction_assignments,
            "dialogue_flags": player.dialogue_flags,
            "trade_permits": list(player.trade_permits),
            "mission_state": player.mission_state,
            "crew_state": player.crew_state,
        }
        return result

    def _deserialize_player(self, data: Dict[str, Any]) -> Player:
        """Deserialize Player object."""
        from spacegame.models.progression import PlayerProgression
        from spacegame.models.upgrades import ShipUpgradeManager
        from spacegame.data_loader import get_data_loader

        ship = self._deserialize_ship(data["ship"])

        player = Player(
            name=data["name"],
            credits=data["credits"],
            current_system_id=data["current_system_id"],
            game_day=data["game_day"],
            ship=ship,
        )

        # Restore progression
        if "progression" in data:
            player.progression = PlayerProgression.from_dict(data["progression"])

        # Restore upgrades
        if "upgrades" in data:
            dl = get_data_loader()
            player.upgrade_manager = ShipUpgradeManager.from_dict(data["upgrades"], dl.upgrades)
            # Re-link upgrade manager to ship after restoring
            player.ship.set_upgrade_manager(player.upgrade_manager)

        # Restore lifetime stats
        player.trades_completed = data.get("trades_completed", 0)
        player.total_profit = data.get("total_profit", 0)
        player.systems_visited = set(data.get("systems_visited", [player.current_system_id]))
        player.credits_earned_lifetime = data.get("credits_earned_lifetime", 0)
        player.credits_spent_lifetime = data.get("credits_spent_lifetime", 0)
        player.largest_single_profit = data.get("largest_single_profit", 0)
        player.jumps_traveled = data.get("jumps_traveled", 0)
        player.fuel_consumed = data.get("fuel_consumed", 0)
        player.ore_mined = data.get("ore_mined", 0)
        player.items_salvaged = data.get("items_salvaged", 0)
        player.items_refined = data.get("items_refined", 0)
        player.unlocked_achievements = data.get("unlocked_achievements", [])

        # Restore drone fleet
        if "drone_fleet" in data:
            from spacegame.models.drone import MiningDroneFleet

            player.drone_fleet = MiningDroneFleet.from_dict(data["drone_fleet"])

        # Restore faction data
        player.faction_reputation = data.get("faction_reputation", {})
        player.faction_assignments = data.get("faction_assignments", {})

        # Restore dialogue flags
        player.dialogue_flags = data.get("dialogue_flags", {})

        # Restore trade permits (bills of landing)
        trade_permits_data = data.get("trade_permits")
        if trade_permits_data is not None:
            player.trade_permits = set(trade_permits_data)
        else:
            # Legacy save: grant all permits for backward compatibility
            player.trade_permits = set(player.faction_reputation.keys())

        # Restore mission state
        player.mission_state = data.get("mission_state", {})

        # Restore crew state
        player.crew_state = data.get("crew_state", {})

        return player

    def _serialize_ship(self, ship: Ship) -> Dict[str, Any]:
        """Serialize Ship object."""
        # Get ship type data
        from spacegame.data_loader import get_data_loader

        data_loader = get_data_loader()

        return {
            "ship_type_id": ship.ship_type.id,
            "current_fuel": ship.current_fuel,
            "current_cargo": ship.current_cargo,
            "cargo_purchase_prices": ship.cargo_purchase_prices,
        }

    def _deserialize_ship(self, data: Dict[str, Any]) -> Ship:
        """Deserialize Ship object."""
        from spacegame.data_loader import get_data_loader

        data_loader = get_data_loader()

        ship_type = data_loader.get_ship_type(data["ship_type_id"])

        return Ship(
            ship_type=ship_type,
            current_fuel=data["current_fuel"],
            current_cargo=data.get("current_cargo", {}),
            cargo_purchase_prices=data.get("cargo_purchase_prices", {}),
        )

    def _serialize_markets(self, markets: Dict[str, Market]) -> Dict[str, Any]:
        """Serialize markets dictionary."""
        serialized = {}

        for system_id, market in markets.items():
            serialized[system_id] = {
                "current_prices": market.current_prices,
                "last_update_day": market.last_update_day,
            }

        return serialized

    def _deserialize_markets(self, data: Dict[str, Any]) -> Dict[str, Market]:
        """Deserialize markets dictionary."""
        # Markets will be recreated by the game engine using saved state
        # Return the raw data for now
        return data

    def _serialize_events(self, events: Dict[str, MarketEvent]) -> Dict[str, Any]:
        """Serialize active events dictionary."""
        serialized = {}

        for system_id, event in events.items():
            serialized[system_id] = {
                "event_type": event.event_type.value,
                "commodity_id": event.commodity_id,
                "system_id": event.system_id,
                "day_started": event.day_started,
                "duration_days": event.duration_days,
                "price_multiplier": event.price_multiplier,
                "description": event.description,
            }

        return serialized

    def _deserialize_events(self, data: Dict[str, Any]) -> Dict[str, MarketEvent]:
        """Deserialize active events dictionary."""
        from spacegame.models.event import MarketEvent, EventType

        events = {}

        for system_id, event_data in data.items():
            # Support both old "start_day" and new "day_started" key names
            day_started = event_data.get("day_started", event_data.get("start_day", 0))
            event = MarketEvent(
                event_type=EventType(event_data["event_type"]),
                commodity_id=event_data["commodity_id"],
                system_id=event_data["system_id"],
                day_started=day_started,
                duration_days=event_data["duration_days"],
                price_multiplier=event_data["price_multiplier"],
                description=event_data["description"],
            )
            events[system_id] = event

        return events
