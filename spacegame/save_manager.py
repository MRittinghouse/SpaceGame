"""
Save/Load system for SpaceGame.

Handles saving and loading game state to/from JSON files.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from spacegame.models.event import MarketEvent
from spacegame.models.market import Market
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.utils.logger import logger


class SaveManager:
    """
    Manages save/load operations for the game.

    Save files are stored as JSON in the configured save directory.
    Supports multiple save slots with metadata.
    """

    SAVE_VERSION = "1.0"
    DEFAULT_NUM_SLOTS = 5

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

    @property
    def _settings_path(self) -> Path:
        """Path to the global settings file."""
        return self.save_dir / "settings.json"

    def save_settings(self, settings: Dict[str, Any]) -> None:
        """Save global settings (audio, etc.) to settings.json.

        Args:
            settings: Settings dict to persist.
        """
        try:
            with open(self._settings_path, "w") as f:
                json.dump(settings, f, indent=2)
            logger.info("Settings saved")
        except OSError as e:
            logger.error(f"Failed to save settings: {e}")

    def load_settings(self) -> Dict[str, Any]:
        """Load global settings from settings.json.

        Returns:
            Settings dict, or empty dict if file doesn't exist.
        """
        if not self._settings_path.exists():
            return {}
        try:
            with open(self._settings_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load settings: {e}")
            return {}

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
        price_history: Optional[Any] = None,
        trade_routes: Optional[Any] = None,
        trade_contracts: Optional[Any] = None,
        investment_manager: Optional[Any] = None,
        ambient_dialogue: Optional[Any] = None,
        galaxy_events: Optional[Dict[str, Any]] = None,
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
            price_history: Optional PriceHistory tracker.
            trade_routes: Optional TradeRouteTracker.
            trade_contracts: Optional TradeContractManager.
            ambient_dialogue: Optional AmbientDialogueManager.
            galaxy_events: Optional serialized galaxy events dict.

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
                price_history=price_history,
                trade_routes=trade_routes,
                trade_contracts=trade_contracts,
                investment_manager=investment_manager,
                ambient_dialogue=ambient_dialogue,
                galaxy_events=galaxy_events,
            )

            save_path = self.get_save_file_path(slot)
            tmp_path = save_path.with_suffix(".tmp")

            # Write to temp file first, then atomic rename
            with open(tmp_path, "w") as f:
                json.dump(save_data, f, indent=2)
            import os

            os.replace(str(tmp_path), str(save_path))

            logger.info(f"Game saved to slot {slot}: {save_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save game to slot {slot}: {e}")
            # Clean up temp file if it exists
            try:
                tmp_path = self.get_save_file_path(slot).with_suffix(".tmp")
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
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
                # Save migration: ShipBuild.from_dict handles missing module
                # fields via .get() defaults. Full version migration (schema
                # transforms) deferred until a breaking format change is needed.

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
        price_history: Optional[Any] = None,
        trade_routes: Optional[Any] = None,
        trade_contracts: Optional[Any] = None,
        investment_manager: Optional[Any] = None,
        ambient_dialogue: Optional[Any] = None,
        galaxy_events: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Serialize game state to dictionary for JSON saving."""
        # Get current system name for metadata
        from spacegame.data_loader import get_data_loader

        data_loader = get_data_loader()
        current_system = data_loader.get_system(player.current_system_id)
        current_system_name = current_system.name if current_system else player.current_system_id

        timestamp = datetime.now().isoformat()

        result = {
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

        # Phase 3 trading data (optional, backward-compatible)
        if price_history:
            result["price_history"] = price_history.to_dict()
        if trade_routes:
            result["trade_routes"] = trade_routes.to_dict()
        if trade_contracts:
            result["trade_contracts"] = trade_contracts.to_dict()
        if investment_manager:
            result["investment_state"] = investment_manager.to_dict()
        if ambient_dialogue:
            result["ambient_dialogue"] = ambient_dialogue.to_dict()
        if galaxy_events:
            result["galaxy_events"] = galaxy_events

        # Market supply/demand modifiers
        market_supply_demand = {}
        for system_id, market in markets.items():
            sd = getattr(market, "_player_supply_demand", {})
            if sd:
                market_supply_demand[system_id] = dict(sd)
        if market_supply_demand:
            result["market_supply_demand"] = market_supply_demand

        return result

    def _deserialize_game_state(self, save_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize game state from loaded JSON."""
        result = {
            "player": self._deserialize_player(save_data["player"]),
            "markets": self._deserialize_markets(save_data["markets"]),
            "active_events": self._deserialize_events(save_data.get("active_events", {})),
            "event_log": save_data.get("event_log", []),
            "tutorial": save_data.get("tutorial", {}),
            "playtime_seconds": save_data.get("playtime_seconds", 0),
            "metadata": save_data.get("metadata", {}),
        }

        # Phase 3 trading data (optional, backward-compatible defaults)
        if "price_history" in save_data:
            from spacegame.models.market import PriceHistory

            result["price_history"] = PriceHistory.from_dict(save_data["price_history"])
        else:
            result["price_history"] = None

        if "trade_routes" in save_data:
            from spacegame.models.trade_route import TradeRouteTracker

            result["trade_routes"] = TradeRouteTracker.from_dict(save_data["trade_routes"])
        else:
            result["trade_routes"] = None

        if "trade_contracts" in save_data:
            from spacegame.models.trade_contract import TradeContractManager

            result["trade_contracts"] = TradeContractManager.from_dict(save_data["trade_contracts"])
        else:
            result["trade_contracts"] = None

        result["investment_state"] = save_data.get("investment_state", None)

        result["market_supply_demand"] = save_data.get("market_supply_demand", {})

        result["ambient_dialogue"] = save_data.get("ambient_dialogue", None)

        # Galaxy events (backward-compatible, defaults to empty)
        result["galaxy_events"] = save_data.get("galaxy_events", {})

        return result

    def _serialize_player(self, player: Player) -> Dict[str, Any]:
        """Serialize Player object."""
        result = {
            "name": player.name,
            "ship_name": player.ship_name,
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
            "max_mining_depth": player.max_mining_depth,
            "total_chains_triggered": player.total_chains_triggered,
            "rare_ores_mined": player.rare_ores_mined,
            "salvage_sessions_completed": player.salvage_sessions_completed,
            "corrupted_items_extracted": player.corrupted_items_extracted,
            "refining_jobs_completed": player.refining_jobs_completed,
            "batch_jobs_queued": player.batch_jobs_queued,
            "recipes_crafted": list(player.recipes_crafted),
            "investments_owned": player.investments_owned,
            "s_ranks_earned": player.s_ranks_earned,
            "best_mining_session_ore": player.best_mining_session_ore,
            "best_mining_depth": player.best_mining_depth,
            "best_trade_profit": player.best_trade_profit,
            "best_salvage_haul": player.best_salvage_haul,
            "best_refining_output": player.best_refining_output,
            "max_credits_held": player.max_credits_held,
            "drone_fleet": player.drone_fleet.to_dict(),
            "faction_reputation": player.faction_reputation,
            "faction_assignments": player.faction_assignments,
            "sub_reputation": player.sub_reputation,
            "wreckers_guild_state": (
                player.wreckers_guild_state.to_dict()
                if player.wreckers_guild_state is not None
                else None
            ),
            "deep_shafts_state": (
                player.deep_shafts_state.to_dict() if player.deep_shafts_state is not None else None
            ),
            # SA-B2: bidding system state. Always serialized (default
            # AuctionState() is the empty state). Additive — no
            # SAVE_VERSION bump per locked decision §SA-B2.3.
            "auction_state": player.auction_state.to_dict(),
            "dialogue_flags": player.dialogue_flags,
            "captain_memory": {cid: mem.to_dict() for cid, mem in player.captain_memory.items()},
            "timed_thread_state": {
                tid: st.to_dict() for tid, st in player.timed_thread_state.items()
            },
            "last_interaction_day": dict(player.last_interaction_day),
            "trade_permits": list(player.trade_permits),
            "black_market_access": list(player.black_market_access),
            "mission_state": player.mission_state,
            "crew_state": player.crew_state,
            "social_state": player.social_state,
            "attribute_state": player.attribute_state,
            "journal_state": player.journal_state,
            "ground_equipment": list(player.ground_equipment),
            "parts_inventory": dict(player.parts_inventory),
            "hidden_compartment": (
                player.hidden_compartment.to_dict() if player.hidden_compartment else None
            ),
            "smuggling_contract_state": player.smuggling_contract_state,
            "ground_contract_state": player.ground_contract_state,
            "political_state": player.political_state,
            "politics_dispute_state": player.politics_dispute_state,
            "criminal_heat": player.criminal_heat,
            "goods_smuggled": player.goods_smuggled,
            "smuggling_contracts_completed": player.smuggling_contracts_completed,
            "times_caught_smuggling": player.times_caught_smuggling,
            "inspections_passed_with_contraband": player.inspections_passed_with_contraband,
            "max_criminal_heat_reached": player.max_criminal_heat_reached,
            "ground_missions_completed": player.ground_missions_completed,
            "ground_missions_failed": player.ground_missions_failed,
            "ground_enemies_defeated": player.ground_enemies_defeated,
            "ground_enemies_talked": player.ground_enemies_talked,
            "ground_tiles_explored": player.ground_tiles_explored,
            "ground_undetected_completions": player.ground_undetected_completions,
            "ground_campaign_missions_completed": player.ground_campaign_missions_completed,
            "previous_system_id": player.previous_system_id,
            "combats_won": player.combats_won,
            "combats_fled": player.combats_fled,
            "combats_negotiated": player.combats_negotiated,
            "combats_bribed": player.combats_bribed,
            "side_missions_completed": player.side_missions_completed,
            "crew_quests_completed": player.crew_quests_completed,
            "encounters_survived": player.encounters_survived,
            # Deep Core mining progression
            "strata_tokens": player.strata_tokens,
            "mining_prestige_level": player.mining_prestige_level,
            "deep_core_upgrades": player.deep_core_upgrades.to_dict(),
            "ore_silo_manager": player.ore_silo_manager.to_dict(),
            "mining_depth_per_system": dict(player.mining_depth_per_system),
            "prestige_hint_shown": player.prestige_hint_shown,
            "salvage_intel": player.salvage_intel,
            "salvage_prestige_level": player.salvage_prestige_level,
            "wreck_upgrades": player.wreck_upgrades.to_dict(),
            "salvage_hold_manager": player.salvage_hold_manager.to_dict(),
            "max_salvage_deck": player.max_salvage_deck,
            # Forge (Catalyst Protocol) progression
            "forge_tokens": player.forge_tokens,
            "forge_upgrades": player.forge_upgrades.to_dict(),
            "forge_buffer_manager": player.forge_buffer_manager.to_dict(),
            "recipe_mastery": player.recipe_mastery.to_dict(),
            "discovered_recipes": sorted(player.discovered_recipes),
            "discovered_combos": sorted(player.discovered_combos),
            "unlocked_shapes": sorted(player.unlocked_shapes),
            "unlocked_materials": sorted(player.unlocked_materials),
            "unlocked_weight_classes": sorted(player.unlocked_weight_classes),
            "unlocked_modules": sorted(player.unlocked_modules),
            "player_presets": player.player_presets,
            "build_drafts": player.build_drafts,
            "trade_profit_total": player.trade_profit_total,
            # Tier 3.F: per-system commodity price memory (gated by skill).
            "price_memory": player.price_memory.to_dict(),
        }
        return result

    def _deserialize_player(self, data: Dict[str, Any]) -> Player:
        """Deserialize Player object."""
        from spacegame.data_loader import get_data_loader
        from spacegame.models.progression import PlayerProgression
        from spacegame.models.upgrades import ShipUpgradeManager

        ship = self._deserialize_ship(data["ship"])

        player = Player(
            name=data["name"],
            credits=data["credits"],
            current_system_id=data["current_system_id"],
            ship=ship,
            ship_name=data.get("ship_name", ""),
            game_day=data["game_day"],
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

        # Restore minigame stats
        player.max_mining_depth = data.get("max_mining_depth", 0)
        player.total_chains_triggered = data.get("total_chains_triggered", 0)
        player.rare_ores_mined = data.get("rare_ores_mined", 0)
        player.salvage_sessions_completed = data.get("salvage_sessions_completed", 0)
        player.corrupted_items_extracted = data.get("corrupted_items_extracted", 0)
        player.refining_jobs_completed = data.get("refining_jobs_completed", 0)
        player.batch_jobs_queued = data.get("batch_jobs_queued", 0)
        player.recipes_crafted = set(data.get("recipes_crafted", []))
        player.investments_owned = data.get("investments_owned", 0)
        player.s_ranks_earned = data.get("s_ranks_earned", 0)
        player.best_mining_session_ore = data.get("best_mining_session_ore", 0)
        player.best_mining_depth = data.get("best_mining_depth", 0)
        player.best_trade_profit = data.get("best_trade_profit", 0)
        player.best_salvage_haul = data.get("best_salvage_haul", 0)
        player.best_refining_output = data.get("best_refining_output", 0)
        player.max_credits_held = data.get("max_credits_held", 0)

        # Restore combat + mission stats
        player.combats_won = data.get("combats_won", 0)
        player.combats_fled = data.get("combats_fled", 0)
        player.combats_negotiated = data.get("combats_negotiated", 0)
        player.combats_bribed = data.get("combats_bribed", 0)
        player.side_missions_completed = data.get("side_missions_completed", 0)
        player.crew_quests_completed = data.get("crew_quests_completed", 0)
        player.encounters_survived = data.get("encounters_survived", 0)

        # Restore drone fleet
        if "drone_fleet" in data:
            from spacegame.models.drone import MiningDroneFleet

            player.drone_fleet = MiningDroneFleet.from_dict(data["drone_fleet"])

        # Restore faction data
        player.faction_reputation = data.get("faction_reputation", {})
        player.faction_assignments = data.get("faction_assignments", {})
        player.sub_reputation = data.get("sub_reputation", {})

        # SA-1: Wreckers' Guild Hall runtime state (None for legacy saves
        # and for players who never docked at the Hall).
        wreckers_data = data.get("wreckers_guild_state")
        if wreckers_data:
            from spacegame.models.wreckers_guild import WreckersGuildState

            player.wreckers_guild_state = WreckersGuildState.from_dict(wreckers_data)
        else:
            player.wreckers_guild_state = None

        # SA-2: Deep Shafts memorial pilgrimage state (None for legacy
        # saves and for players who have not yet entered the venue).
        deep_shafts_data = data.get("deep_shafts_state")
        if deep_shafts_data:
            from spacegame.models.deep_shafts import DeepShaftsState

            player.deep_shafts_state = DeepShaftsState.from_dict(deep_shafts_data)
        else:
            player.deep_shafts_state = None

        # SA-B2: bidding system state. Legacy saves predating SA-B2 have
        # no ``auction_state`` key and load with the default empty state.
        auction_data = data.get("auction_state")
        if auction_data:
            from spacegame.models.bidding import AuctionState

            player.auction_state = AuctionState.from_dict(auction_data)
        else:
            from spacegame.models.bidding import AuctionState

            player.auction_state = AuctionState()

        # Restore dialogue flags
        player.dialogue_flags = data.get("dialogue_flags", {})

        # Restore captain memory (RC). Empty dict for legacy saves.
        from spacegame.models.captain_memory import CaptainMemory

        captain_mem_raw = data.get("captain_memory", {})
        player.captain_memory = {
            cid: CaptainMemory.from_dict(mem_data) for cid, mem_data in captain_mem_raw.items()
        }

        # Restore TW timed thread state. Empty dict for legacy saves.
        from spacegame.models.timed_thread import TimedThreadState

        thread_raw = data.get("timed_thread_state", {})
        player.timed_thread_state = {
            tid: TimedThreadState.from_dict(st) for tid, st in thread_raw.items()
        }
        # Restore interaction-day map (QA-F-1 fix). Empty for legacy.
        player.last_interaction_day = {
            k: int(v) for k, v in data.get("last_interaction_day", {}).items()
        }

        # Restore trade permits (bills of landing)
        trade_permits_data = data.get("trade_permits")
        if trade_permits_data is not None:
            player.trade_permits = set(trade_permits_data)
        else:
            # Legacy save: grant all permits for backward compatibility
            player.trade_permits = set(player.faction_reputation.keys())

        # Restore black market access permits
        player.black_market_access = set(data.get("black_market_access", []))

        # Restore mission state
        player.mission_state = data.get("mission_state", {})

        # Restore crew state (with capacity validation)
        player.crew_state = data.get("crew_state", {})
        crew_count = len(player.crew_state)
        crew_slots = player.ship.ship_type.crew_slots if player.ship else 0
        if crew_count > crew_slots:
            logger.warning(
                "Crew count (%d) exceeds ship capacity (%d). Crew preserved but may cause issues.",
                crew_count,
                crew_slots,
            )

        # Restore social state
        player.social_state = data.get("social_state", {})

        # Restore attribute state
        player.attribute_state = data.get("attribute_state", {})

        # Restore journal state
        player.journal_state = data.get("journal_state", {})

        # Restore ground equipment inventory
        player.ground_equipment = data.get("ground_equipment", [])
        player.parts_inventory = data.get("parts_inventory", {})

        # Restore hidden compartment
        hidden_data = data.get("hidden_compartment")
        if hidden_data:
            from spacegame.models.smuggling import HiddenCompartment

            player.hidden_compartment = HiddenCompartment.from_dict(hidden_data)
            player.hidden_compartment.set_progression(player.progression)
        else:
            player.hidden_compartment = None

        # Backward-compat migration: players with the hidden_compartment
        # upgrade from before AR-PK's install-flow fix have no
        # HiddenCompartment object on the save. Create one now so trading
        # view's hide/retrieve actually works on old saves.
        if player.hidden_compartment is None and player.upgrade_manager.has_upgrade(
            "hidden_compartment"
        ):
            from spacegame.models.smuggling import HiddenCompartment

            player.hidden_compartment = HiddenCompartment(
                total_cargo_capacity=player.ship.max_cargo,
            )
            player.hidden_compartment.set_progression(player.progression)

        # Restore ground contract state
        player.ground_contract_state = data.get("ground_contract_state", {})

        # Restore smuggling contract state
        player.smuggling_contract_state = data.get("smuggling_contract_state", {})

        # Restore political state
        player.political_state = data.get("political_state", {})
        # SA-P2: restore venue dispute state. Older saves default to
        # empty per the additive-field rule (CLAUDE.md save migration).
        player.politics_dispute_state = data.get("politics_dispute_state", {})

        # Restore smuggling stats
        player.criminal_heat = data.get("criminal_heat", 0)
        player.goods_smuggled = data.get("goods_smuggled", 0)
        player.smuggling_contracts_completed = data.get("smuggling_contracts_completed", 0)
        player.times_caught_smuggling = data.get("times_caught_smuggling", 0)
        player.inspections_passed_with_contraband = data.get(
            "inspections_passed_with_contraband", 0
        )
        player.max_criminal_heat_reached = data.get("max_criminal_heat_reached", 0)

        # Restore ground exploration stats
        player.ground_missions_completed = data.get("ground_missions_completed", 0)
        player.ground_missions_failed = data.get("ground_missions_failed", 0)
        player.ground_enemies_defeated = data.get("ground_enemies_defeated", 0)
        player.ground_enemies_talked = data.get("ground_enemies_talked", 0)
        player.ground_tiles_explored = data.get("ground_tiles_explored", 0)
        player.ground_undetected_completions = data.get("ground_undetected_completions", 0)
        player.ground_campaign_missions_completed = data.get(
            "ground_campaign_missions_completed", 0
        )

        # Restore previous system ID (for trade route tracking)
        player.previous_system_id = data.get("previous_system_id", "")

        # Restore Deep Core mining progression
        player.strata_tokens = data.get("strata_tokens", 0)
        player.mining_prestige_level = data.get("mining_prestige_level", 0)
        if "deep_core_upgrades" in data:
            from spacegame.models.deep_core import DeepCoreUpgradeState

            player.deep_core_upgrades = DeepCoreUpgradeState.from_dict(data["deep_core_upgrades"])
        if "ore_silo_manager" in data:
            from spacegame.models.ore_silo import OreSiloManager

            player.ore_silo_manager = OreSiloManager.from_dict(data["ore_silo_manager"])
        player.mining_depth_per_system = data.get("mining_depth_per_system", {})
        player.prestige_hint_shown = data.get("prestige_hint_shown", False)

        # Restore Deep Salvage progression
        player.salvage_intel = data.get("salvage_intel", 0)
        player.salvage_prestige_level = data.get("salvage_prestige_level", 0)
        player.max_salvage_deck = data.get("max_salvage_deck", 0)
        if "wreck_upgrades" in data:
            from spacegame.models.wreck_upgrade import WreckUpgradeState

            player.wreck_upgrades = WreckUpgradeState.from_dict(data["wreck_upgrades"])
        if "salvage_hold_manager" in data:
            from spacegame.models.salvage_hold import SalvageHoldManager

            player.salvage_hold_manager = SalvageHoldManager.from_dict(data["salvage_hold_manager"])

        # Restore Forge (Catalyst Protocol) progression
        player.forge_tokens = data.get("forge_tokens", 0)
        if "forge_upgrades" in data:
            from spacegame.models.forge_upgrade import ForgeUpgradeState

            player.forge_upgrades = ForgeUpgradeState.from_dict(data["forge_upgrades"])
        if "forge_buffer_manager" in data:
            from spacegame.models.forge_buffer import ForgeBufferManager

            player.forge_buffer_manager = ForgeBufferManager.from_dict(data["forge_buffer_manager"])
        if "recipe_mastery" in data:
            from spacegame.models.recipe_mastery import RecipeMasteryTracker

            player.recipe_mastery = RecipeMasteryTracker.from_dict(data["recipe_mastery"])
        if "discovered_recipes" in data:
            player.discovered_recipes = set(data["discovered_recipes"])
        if "discovered_combos" in data:
            player.discovered_combos = set(data["discovered_combos"])
        if "unlocked_shapes" in data:
            player.unlocked_shapes = set(data["unlocked_shapes"])
        if "unlocked_materials" in data:
            player.unlocked_materials = set(data["unlocked_materials"])
        if "unlocked_weight_classes" in data:
            player.unlocked_weight_classes = set(data["unlocked_weight_classes"])
        if "unlocked_modules" in data:
            player.unlocked_modules = set(data["unlocked_modules"])
        if "player_presets" in data:
            player.player_presets = data["player_presets"]
        if "build_drafts" in data:
            player.build_drafts = data["build_drafts"]
        if "trade_profit_total" in data:
            player.trade_profit_total = data["trade_profit_total"]
        # Tier 3.F: restore per-system price memory.
        if "price_memory" in data:
            from spacegame.models.trade_route import PriceMemory

            player.price_memory = PriceMemory.from_dict(data["price_memory"])

        return player

    def _serialize_ship(self, ship: Ship) -> Dict[str, Any]:
        """Serialize Ship object."""
        # Get ship type data
        result = {
            "ship_type_id": ship.ship_type.id,
            "current_fuel": ship.current_fuel,
            "current_cargo": ship.current_cargo,
            "cargo_purchase_prices": ship.cargo_purchase_prices,
            "current_hull": ship.current_hull,
            "current_shields": ship.current_shields,
        }
        # Serialize ShipBuild if present (Shipyard Overhaul Phase G)
        if hasattr(ship, "_build") and ship._build is not None:
            result["build"] = ship._build.to_dict()
        return result

    def _deserialize_ship(self, data: Dict[str, Any]) -> Ship:
        """Deserialize Ship object."""
        from spacegame.data_loader import get_data_loader

        data_loader = get_data_loader()

        ship_type = data_loader.get_ship_type(data["ship_type_id"])

        ship = Ship(
            ship_type=ship_type,
            current_fuel=data["current_fuel"],
            current_cargo=data.get("current_cargo", {}),
            cargo_purchase_prices=data.get("cargo_purchase_prices", {}),
        )
        # Restore hull/shields if saved (backward compat: defaults from __post_init__)
        if "current_hull" in data:
            ship.current_hull = data["current_hull"]
        if "current_shields" in data:
            ship.current_shields = data["current_shields"]

        # Restore ShipBuild if present (Shipyard Overhaul Phase G)
        if "build" in data:
            from spacegame.models.ship_build import ShipBuild

            build = ShipBuild.from_dict(data["build"])
            # Migration: backfill ship_type_id on legacy builds
            if not build.ship_type_id:
                build.ship_type_id = ship_type.id
            ship.set_build(build)
        elif data.get("ship_type_id"):
            # Old save without build: generate preset for migration
            from spacegame.models.ship_presets import get_preset_for_ship_type

            preset = get_preset_for_ship_type(data["ship_type_id"])
            if preset:
                try:
                    ship.set_build(preset)
                except Exception:
                    ship._build = preset  # Fallback if set_build fails

        return ship

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
        from spacegame.models.event import EventType, MarketEvent

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
