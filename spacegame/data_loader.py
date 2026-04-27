"""
Data loading system for game content.

Loads JSON data files and converts them to game model instances.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from spacegame.models.achievement import Achievement
from spacegame.models.ambient_dialogue import AmbientLine
from spacegame.models.combat import (
    BossPhase,
    CombatMove,
    EnemyBehavior,
    EnemyShipTemplate,
)
from spacegame.models.commodity import Commodity, CommodityCategory, Legality
from spacegame.models.crew import CrewAbility, CrewTemplate
from spacegame.models.dialogue import (
    NPC,
    DialogueNode,
    DialogueResponse,
    DialogueState,
    DialogueTree,
    SkillCheck,
)
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterDefinition,
    EncounterOutcome,
)
from spacegame.models.faction import Faction
from spacegame.models.investment import InvestmentTemplate, InvestmentTier
from spacegame.models.journal import JournalEntry
from spacegame.models.location import Location
from spacegame.models.mining import MiningConfig
from spacegame.models.mission import (
    AcceptCargo,
    ForcedEncounter,
    Mission,
    MissionObjective,
    MissionReward,
    ObjectiveType,
)
from spacegame.models.momentum import ShipUltimate
from spacegame.models.refining import Recipe
from spacegame.models.salvage import SalvageConfig
from spacegame.models.ship import ShipType
from spacegame.models.ship_build import HullMaterial, HullShape
from spacegame.models.system import Coordinates, Economy, StarSystem, Station
from spacegame.models.upgrades import ShipUpgrade
from spacegame.utils.logger import logger


class DataLoader:
    """
    Loads and manages game data from JSON files.

    Provides centralized access to all game content.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize data loader.

        Args:
            data_dir: Path to data directory (defaults to project data/ folder)
        """
        if data_dir is None:
            # Default to data/ directory relative to project root
            from spacegame.config import PROJECT_ROOT

            data_dir = PROJECT_ROOT / "data"

        self.data_dir = data_dir
        self.systems: Dict[str, StarSystem] = {}
        self.commodities: Dict[str, Commodity] = {}
        self.ship_types: Dict[str, ShipType] = {}
        self.mining_configs: Dict[str, MiningConfig] = {}
        self.salvage_configs: Dict[str, SalvageConfig] = {}
        self.recipes: List[Recipe] = []
        self.upgrades: Dict[str, ShipUpgrade] = {}
        self.achievements: List[Achievement] = []
        self.factions: Dict[str, Faction] = {}
        self.npcs: Dict[str, NPC] = {}
        self.dialogue_trees: Dict[str, DialogueTree] = {}
        self.missions: List[Mission] = []
        self.crew_templates: Dict[str, CrewTemplate] = {}
        self.ambient_lines: List[AmbientLine] = []
        self.enemy_templates: Dict[str, EnemyShipTemplate] = {}
        self.captains: Dict[str, "EnemyCaptain"] = {}
        self.complications: Dict[str, "CombatComplication"] = {}
        self.crew_interjections: List["CrewInterjection"] = []
        # RC-3: keyed lookup for captain dialogue variants. Built by
        # load_captain_variants() so EncounterView / CombatView can
        # resolve effective dialogue in O(1).
        self.captain_variants: Dict[tuple, "CaptainVariant"] = {}
        # TW: loaded timed thread definitions, keyed by thread id.
        self.timed_threads: Dict[str, "TimedThread"] = {}
        self.journal_entries: List[JournalEntry] = []
        self.encounter_definitions: List[EncounterDefinition] = []
        self.ground_equipment: Dict[str, "GroundEquipment"] = {}
        self.contract_templates: Dict[str, dict] = {}
        self.campaign_ground_maps: Dict[str, dict] = {}
        self.faction_laws: Dict[str, "FactionLaw"] = {}
        self.locations: Dict[str, List[Location]] = {}
        self.investment_templates: Dict[str, InvestmentTemplate] = {}
        self.faction_relationships: list = []
        # SA-P2 venue dispute templates, keyed by template id. Empty
        # when no SA-P3/P4/P5 content is installed (the default).
        self.politics_disputes: Dict[str, "PoliticsDisputeTemplate"] = {}
        self.faction_perks: Dict[str, Dict[str, list]] = {}
        self.galaxy_event_templates: List[Dict] = []
        self.galaxy_event_chains: List[Dict] = []
        self.station_chatter_lines: list = []
        self.news_templates: list = []
        self.travel_log_templates: dict = {}
        self.balance_config: Dict = {}  # Economy/balance overrides from balance.json
        self.deep_core_upgrades: Dict[str, "DeepCoreUpgrade"] = {}
        self.wreck_upgrades: Dict[str, "WreckUpgrade"] = {}
        self.forge_upgrades: Dict[str, "ForgeUpgrade"] = {}
        self.ship_ultimates: Dict[str, "ShipUltimate"] = {}  # category → ultimate
        self.hull_shapes: Dict[str, "HullShape"] = {}
        self.hull_materials: Dict[str, "HullMaterial"] = {}
        self.ship_modules: Dict[str, "ShipModule"] = {}
        self.slot_definitions: Dict[str, "SlotDefinition"] = {}
        self.ship_parts: Dict[str, "ShipPart"] = {}
        self.drydock_catalogs: Dict[str, dict] = {}

    def _safe_load(self, loader_name: str, loader_fn) -> None:
        """Call a loader function with error handling and context.

        Args:
            loader_name: Human-readable name for error messages.
            loader_fn: The load_*() method to call.
        """
        try:
            loader_fn()
        except FileNotFoundError as e:
            logger.error(f"Data file not found for {loader_name}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {loader_name}: {e}")
            raise
        except KeyError as e:
            logger.error(f"Missing required field in {loader_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load {loader_name}: {type(e).__name__}: {e}")
            raise

    def load_all(self) -> None:
        """Load all game data from JSON files."""
        logger.info("Loading game data...")
        self._safe_load("systems", self.load_systems)
        self._safe_load("commodities", self.load_commodities)
        self._safe_load("ship_types", self.load_ship_types)
        self._safe_load("mining_configs", self.load_mining_configs)
        self._safe_load("deep_core_upgrades", self.load_deep_core_upgrades)
        self._safe_load("wreck_upgrades", self.load_wreck_upgrades)
        self._safe_load("forge_upgrades", self.load_forge_upgrades)
        self._safe_load("salvage_configs", self.load_salvage_configs)
        self._safe_load("recipes", self.load_recipes)
        self._safe_load("upgrades", self.load_upgrades)
        self._safe_load("achievements", self.load_achievements)
        self._safe_load("factions", self.load_factions)
        self._safe_load("npcs", self.load_npcs)
        self._safe_load("dialogues", self.load_dialogues)
        self._safe_load("missions", self.load_missions)
        self._safe_load("crew_templates", self.load_crew_templates)
        self._safe_load("ambient_dialogue", self.load_ambient_dialogue)
        self._safe_load("enemy_templates", self.load_enemy_templates)
        self._safe_load("captains", self.load_captains)
        self._safe_load("complications", self.load_complications)
        self._safe_load("crew_interjections", self.load_crew_interjections)
        self._safe_load("captain_variants", self.load_captain_variants)
        self._safe_load("timed_threads", self.load_timed_threads)
        self._safe_load("ship_ultimates", self.load_ship_ultimates)
        self._safe_load("hull_shapes", self.load_hull_shapes)
        self._safe_load("hull_materials", self.load_hull_materials)
        self._safe_load("ship_modules", self.load_ship_modules)
        self._safe_load("slot_definitions", self.load_slot_definitions)
        self._safe_load("ship_parts", self.load_ship_parts)
        self._safe_load("module_materials", self.load_module_materials)
        self._safe_load("drydock_catalogs", self.load_drydock_catalogs)
        self._safe_load("journal_entries", self.load_journal_entries)
        self._safe_load("encounter_definitions", self.load_encounter_definitions)
        self._safe_load("ground_equipment", self.load_ground_equipment)
        self._safe_load("contract_templates", self.load_contract_templates)
        self._safe_load("campaign_maps", self.load_campaign_maps)
        self._safe_load("faction_laws", self.load_faction_laws)
        self._safe_load("locations", self.load_locations)
        self._safe_load("investment_configs", self.load_investment_configs)
        self._safe_load("politics", self.load_politics)
        self._safe_load("politics_disputes", self.load_politics_disputes)
        self._safe_load("faction_perks", self.load_faction_perks)
        self._safe_load("galaxy_events", self.load_galaxy_events)
        self._safe_load("station_chatter", self.load_station_chatter)
        self._safe_load("news_templates", self.load_news_templates)
        self._safe_load("travel_log_templates", self.load_travel_log_templates)
        self._safe_load("balance_config", self.load_balance_config)
        logger.info(
            f"Data loaded: {len(self.systems)} systems, "
            f"{len(self.commodities)} commodities, "
            f"{len(self.ship_types)} ship types, "
            f"{len(self.mining_configs)} mining configs, "
            f"{len(self.salvage_configs)} salvage configs, "
            f"{len(self.recipes)} recipes, "
            f"{len(self.upgrades)} upgrades, "
            f"{len(self.achievements)} achievements, "
            f"{len(self.crew_templates)} crew templates, "
            f"{len(self.enemy_templates)} enemy templates, "
            f"{len(self.journal_entries)} journal entries"
        )

    def validate(self) -> list[str]:
        """Cross-reference all loaded data and log warnings for mismatches.

        Non-fatal: the game continues regardless. Call after load_all().

        Returns:
            List of warning messages (also logged).
        """
        warnings: list[str] = []
        commodity_ids = set(self.commodities.keys())
        system_ids = set(self.systems.keys())
        npc_ids = set(self.npcs.keys())
        faction_ids = set(self.factions.keys())
        tree_ids = set(self.dialogue_trees.keys())
        mission_ids = {m.id for m in self.missions}

        for mission in self.missions:
            # Commodity references
            for obj in mission.objectives:
                if obj.type == ObjectiveType.COLLECT_CARGO:
                    if obj.target_id not in commodity_ids:
                        warnings.append(
                            f"Mission '{mission.id}': collect_cargo target "
                            f"'{obj.target_id}' not in commodities"
                        )
                if obj.type == ObjectiveType.REACH_SYSTEM:
                    if obj.target_id not in system_ids:
                        warnings.append(
                            f"Mission '{mission.id}': reach_system target "
                            f"'{obj.target_id}' not in systems"
                        )
                if obj.type == ObjectiveType.TALK_TO_NPC:
                    if obj.target_id not in npc_ids:
                        warnings.append(
                            f"Mission '{mission.id}': talk_to_npc target "
                            f"'{obj.target_id}' not in NPCs"
                        )
            for cargo in mission.on_accept_cargo:
                if cargo.commodity_id not in commodity_ids:
                    warnings.append(
                        f"Mission '{mission.id}': on_accept_cargo "
                        f"'{cargo.commodity_id}' not in commodities"
                    )
            # Mission chain references
            for prereq in mission.prerequisites:
                if prereq not in mission_ids:
                    warnings.append(
                        f"Mission '{mission.id}': prerequisite '{prereq}' not in missions"
                    )
            if mission.available_after and mission.available_after not in mission_ids:
                warnings.append(
                    f"Mission '{mission.id}': available_after "
                    f"'{mission.available_after}' not in missions"
                )
            # Reputation reward targets
            for reward in mission.rewards:
                if reward.reward_type == "modify_reputation":
                    if reward.target_id not in faction_ids:
                        warnings.append(
                            f"Mission '{mission.id}': modify_reputation "
                            f"target '{reward.target_id}' not in factions"
                        )

        # NPC references
        for npc in self.npcs.values():
            if npc.dialogue_id and npc.dialogue_id not in tree_ids:
                warnings.append(
                    f"NPC '{npc.id}': dialogue_id '{npc.dialogue_id}' not in dialogue trees"
                )
            if npc.home_system_id and npc.home_system_id not in system_ids:
                warnings.append(
                    f"NPC '{npc.id}': home_system_id '{npc.home_system_id}' not in systems"
                )
            if npc.faction_id and npc.faction_id not in faction_ids:
                warnings.append(f"NPC '{npc.id}': faction_id '{npc.faction_id}' not in factions")

        # Dialogue node references
        for tree in self.dialogue_trees.values():
            if tree.start_node_id not in tree.nodes:
                warnings.append(
                    f"Dialogue '{tree.id}': start_node_id '{tree.start_node_id}' not in nodes"
                )
            for node in tree.nodes.values():
                for resp in node.responses:
                    if resp.next_node_id and resp.next_node_id not in tree.nodes:
                        warnings.append(
                            f"Dialogue '{tree.id}' node '{node.id}': "
                            f"next_node_id '{resp.next_node_id}' not in nodes"
                        )

        for w in warnings:
            logger.warning(f"Data validation: {w}")
        if not warnings:
            logger.info("Data validation: all cross-references OK")
        else:
            logger.warning(f"Data validation: {len(warnings)} issue(s) found")
        return warnings

    def load_systems(self) -> Dict[str, StarSystem]:
        """
        Load star systems from JSON.

        Returns:
            Dict mapping system_id to StarSystem
        """
        file_path = self.data_dir / "galaxy" / "systems.json"
        logger.debug(f"Loading systems from {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.systems.clear()
        for system_data in data["systems"]:
            system = self._parse_system(system_data)
            self.systems[system.id] = system

        logger.info(f"Loaded {len(self.systems)} star systems")
        return self.systems

    def _parse_system(self, data: dict) -> StarSystem:
        """Parse system data dict into StarSystem object."""
        coordinates = Coordinates(x=data["coordinates"]["x"], y=data["coordinates"]["y"])

        stations = [
            Station(
                id=s["id"],
                name=s["name"],
                type=s["type"],
                description=s["description"],
                docking_fee=s["docking_fee"],
                market_variety=s["market_variety"],
            )
            for s in data["stations"]
        ]

        econ_data = data["economy"]
        economy = Economy(
            production_tags=econ_data["production_tags"],
            consumption_tags=econ_data["consumption_tags"],
            tariff_rate=econ_data["tariff_rate"],
            available_commodities=econ_data.get("available_commodities"),
            specialty_exports=econ_data.get("specialty_exports", []),
            specialty_imports=econ_data.get("specialty_imports", []),
        )

        return StarSystem(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            description=data["description"],
            coordinates=coordinates,
            danger_level=data["danger_level"],
            faction=data["faction"],
            stations=stations,
            economy=economy,
            rest_cost=data["rest_cost"],
        )

    def load_commodities(self) -> Dict[str, Commodity]:
        """
        Load commodities from JSON.

        Returns:
            Dict mapping commodity_id to Commodity
        """
        file_path = self.data_dir / "economy" / "commodities.json"
        logger.debug(f"Loading commodities from {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.commodities.clear()
        for commodity_data in data["commodities"]:
            commodity = self._parse_commodity(commodity_data)
            self.commodities[commodity.id] = commodity

        logger.info(f"Loaded {len(self.commodities)} commodities")
        return self.commodities

    def _parse_commodity(self, data: dict) -> Commodity:
        """Parse commodity data dict into Commodity object."""
        return Commodity(
            id=data["id"],
            name=data["name"],
            category=CommodityCategory(data["category"]),
            description=data["description"],
            base_price=data["base_price"],
            variance_min=data["variance_min"],
            variance_max=data["variance_max"],
            volume_per_unit=data["volume_per_unit"],
            legality=Legality(data["legality"]),
            production_tags=data["production_tags"],
            consumption_tags=data["consumption_tags"],
        )

    def load_ship_types(self) -> Dict[str, ShipType]:
        """
        Load ship types from JSON.

        Returns:
            Dict mapping ship_id to ShipType
        """
        file_path = self.data_dir / "ships" / "ship_types.json"
        logger.debug(f"Loading ship types from {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.ship_types.clear()
        for ship_data in data["ship_types"]:
            ship_type = self._parse_ship_type(ship_data)
            self.ship_types[ship_type.id] = ship_type

        logger.info(f"Loaded {len(self.ship_types)} ship types")
        return self.ship_types

    def _parse_ship_type(self, data: dict) -> ShipType:
        """Parse ship type data dict into ShipType object."""
        return ShipType(
            id=data["id"],
            name=data["name"],
            ship_class=data["class"],
            ship_class_category=data.get("ship_class_category", ""),
            defensive_identity=data.get("defensive_identity", ""),
            combat_armor=data.get("combat_armor", 0),
            combat_shield_regen=data.get("combat_shield_regen", 0),
            description=data["description"],
            cargo_capacity=data["cargo_capacity"],
            fuel_capacity=data["fuel_capacity"],
            fuel_efficiency=data["fuel_efficiency"],
            speed_multiplier=data["speed_multiplier"],
            purchase_price=data["purchase_price"],
            resale_value=data["resale_value"],
            crew_slots=data["crew_slots"],
            special_abilities=data["special_abilities"],
            availability=data["availability"],
            combat_hull=data.get("combat_hull", 0),
            combat_shields=data.get("combat_shields", 0),
            combat_energy=data.get("combat_energy", 0),
            combat_energy_regen=data.get("combat_energy_regen", 0),
            combat_speed=data.get("combat_speed", 0),
            combat_evasion=data.get("combat_evasion", 0),
            combat_accuracy=data.get("combat_accuracy", 0),
            weapon_slots=data.get("weapon_slots", 0),
            defense_slots=data.get("defense_slots", 0),
            utility_slots=data.get("utility_slots", 3),
            frame_requirements=data.get("frame_requirements", {}),
            faction_required=data.get("faction_required"),
            faction_rep_required=data.get("faction_rep_required", 0),
            unlock_condition=data.get("unlock_condition"),
        )

    def load_mining_configs(self) -> Dict[str, MiningConfig]:
        """Load mining configurations from JSON."""
        file_path = self.data_dir / "economy" / "mining_configs.json"
        if not file_path.exists():
            logger.warning(f"Mining configs not found: {file_path}")
            return self.mining_configs

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.mining_configs.clear()
        for config_data in data.get("mining_configs", []):
            config = MiningConfig(
                system_id=config_data["system_id"],
                grid_width=config_data.get("grid_width", 6),
                grid_height=config_data.get("grid_height", 4),
                max_energy=config_data.get("max_energy", 20),
                energy_regen_seconds=config_data.get("energy_regen_seconds", 3.0),
                base_click_power=config_data.get("base_click_power", 0.12),
                base_passive_rate=config_data.get("base_passive_rate", 0.05),
                rock_distribution=config_data.get("rock_distribution", {}),
            )
            self.mining_configs[config.system_id] = config

        logger.info(f"Loaded {len(self.mining_configs)} mining configs")
        return self.mining_configs

    def load_deep_core_upgrades(self) -> Dict[str, "DeepCoreUpgrade"]:
        """Load deep core mining upgrade definitions from JSON."""
        from spacegame.models.deep_core import DeepCoreUpgrade

        file_path = self.data_dir / "economy" / "mining_upgrades.json"
        if not file_path.exists():
            logger.warning(f"Mining upgrades not found: {file_path}")
            return self.deep_core_upgrades

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.deep_core_upgrades.clear()
        for entry in data.get("mining_upgrades", []):
            upgrade = DeepCoreUpgrade(
                id=entry["id"],
                name=entry["name"],
                description=entry["description"],
                max_level=entry["max_level"],
                costs=entry["costs"],
                effect_type=entry["effect_type"],
                effect_per_level=entry["effect_per_level"],
            )
            self.deep_core_upgrades[upgrade.id] = upgrade

        logger.info(f"Loaded {len(self.deep_core_upgrades)} deep core upgrades")
        return self.deep_core_upgrades

    def load_wreck_upgrades(self) -> Dict[str, "WreckUpgrade"]:
        """Load wreck salvage upgrade definitions from JSON."""
        from spacegame.models.wreck_upgrade import WreckUpgrade

        file_path = self.data_dir / "economy" / "salvage_upgrades.json"
        if not file_path.exists():
            logger.warning(f"Salvage upgrades not found: {file_path}")
            return self.wreck_upgrades

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.wreck_upgrades.clear()
        for entry in data.get("salvage_upgrades", []):
            upgrade = WreckUpgrade(
                id=entry["id"],
                name=entry["name"],
                description=entry["description"],
                max_level=entry["max_level"],
                costs=entry["costs"],
                effect_type=entry["effect_type"],
                effect_per_level=entry["effect_per_level"],
            )
            self.wreck_upgrades[upgrade.id] = upgrade

        logger.info(f"Loaded {len(self.wreck_upgrades)} wreck upgrades")
        return self.wreck_upgrades

    def load_forge_upgrades(self) -> Dict[str, "ForgeUpgrade"]:
        """Load forge upgrade definitions from JSON."""
        from spacegame.models.forge_upgrade import ForgeUpgrade

        file_path = self.data_dir / "economy" / "forge_upgrades.json"
        if not file_path.exists():
            logger.warning(f"Forge upgrades not found: {file_path}")
            return self.forge_upgrades

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.forge_upgrades.clear()
        for entry in data.get("forge_upgrades", []):
            upgrade = ForgeUpgrade(
                id=entry["id"],
                name=entry["name"],
                description=entry["description"],
                max_level=entry["max_level"],
                costs=entry["costs"],
                effect_type=entry["effect_type"],
                effect_per_level=entry["effect_per_level"],
            )
            self.forge_upgrades[upgrade.id] = upgrade

        logger.info(f"Loaded {len(self.forge_upgrades)} forge upgrades")
        return self.forge_upgrades

    def load_salvage_configs(self) -> Dict[str, SalvageConfig]:
        """Load salvage configurations from JSON."""
        file_path = self.data_dir / "economy" / "salvage_configs.json"
        if not file_path.exists():
            logger.warning(f"Salvage configs not found: {file_path}")
            return self.salvage_configs

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.salvage_configs.clear()
        for config_data in data.get("salvage_configs", []):
            config = SalvageConfig(
                system_id=config_data["system_id"],
                grid_size=config_data.get("grid_size", 5),
                max_charges=config_data.get("max_charges", 10),
                charge_regen_seconds=config_data.get("charge_regen_seconds", 5.0),
                item_density=config_data.get("item_density", 0.4),
                item_distribution=config_data.get("item_distribution", {}),
            )
            self.salvage_configs[config.system_id] = config

        logger.info(f"Loaded {len(self.salvage_configs)} salvage configs")
        return self.salvage_configs

    def load_recipes(self) -> List[Recipe]:
        """Load refining recipes from JSON."""
        file_path = self.data_dir / "economy" / "recipes.json"
        if not file_path.exists():
            logger.warning(f"Recipes not found: {file_path}")
            return self.recipes

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.recipes.clear()
        for recipe_data in data.get("recipes", []):
            recipe = Recipe(
                id=recipe_data["id"],
                name=recipe_data["name"],
                description=recipe_data["description"],
                inputs=recipe_data["inputs"],
                outputs=recipe_data["outputs"],
                processing_time=recipe_data["processing_time"],
                location_ids=recipe_data["location_ids"],
                requires_skill=recipe_data.get("requires_skill"),
                category=recipe_data.get("category", "commodity"),
                tier=recipe_data.get("tier", 1),
                discoverable=recipe_data.get("discoverable", False),
                discovery_hint=recipe_data.get("discovery_hint", ""),
                discovery_prerequisite=recipe_data.get("discovery_prerequisite", ""),
                schematic_cost=recipe_data.get("schematic_cost", 0),
            )
            self.recipes.append(recipe)

        logger.info(f"Loaded {len(self.recipes)} recipes")
        return self.recipes

    def load_upgrades(self) -> Dict[str, ShipUpgrade]:
        """Load ship upgrades from JSON."""
        file_path = self.data_dir / "ships" / "upgrades.json"
        if not file_path.exists():
            logger.warning(f"Upgrades not found: {file_path}")
            return self.upgrades

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.upgrades.clear()
        for upgrade_data in data.get("upgrades", []):
            upgrade = ShipUpgrade(
                id=upgrade_data["id"],
                name=upgrade_data["name"],
                description=upgrade_data["description"],
                price=upgrade_data["price"],
                slot_type=upgrade_data["slot_type"],
                bonus_type=upgrade_data.get("bonus_type", ""),
                bonus_value=upgrade_data.get("bonus_value", 0.0),
                combat_move=upgrade_data.get("combat_move"),
                requires_black_market=upgrade_data.get("requires_black_market", False),
                max_mark=upgrade_data.get("max_mark", 3),
                tuning_options=upgrade_data.get("tuning_options", []),
                faction_required=upgrade_data.get("faction_required"),
                faction_rep_required=upgrade_data.get("faction_rep_required", 0),
                unlock_condition=upgrade_data.get("unlock_condition"),
                tier=upgrade_data.get("tier", 1),
                available_systems=upgrade_data.get("available_systems", []),
            )
            self.upgrades[upgrade.id] = upgrade

        logger.info(f"Loaded {len(self.upgrades)} upgrades")
        return self.upgrades

    def load_achievements(self) -> List[Achievement]:
        """Load achievements from JSON."""
        file_path = self.data_dir / "progression" / "achievements.json"
        if not file_path.exists():
            logger.warning(f"Achievements not found: {file_path}")
            return self.achievements

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.achievements.clear()
        for ach_data in data.get("achievements", []):
            achievement = self._parse_achievement(ach_data)
            self.achievements.append(achievement)

        logger.info(f"Loaded {len(self.achievements)} achievements")
        return self.achievements

    def _parse_achievement(self, data: dict) -> Achievement:
        """Parse achievement data dict into Achievement object."""
        return Achievement(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            category=data["category"],
            stat_key=data["stat_key"],
            threshold=data["threshold"],
            reward_type=data["reward_type"],
            reward_value=data["reward_value"],
            hidden=data.get("hidden", False),
        )

    def load_factions(self) -> Dict[str, Faction]:
        """Load faction definitions from JSON."""
        file_path = self.data_dir / "factions.json"
        if not file_path.exists():
            logger.warning(f"Factions not found: {file_path}")
            return self.factions

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.factions.clear()
        for faction_data in data.get("factions", []):
            faction = Faction(
                id=faction_data["id"],
                name=faction_data["name"],
                description=faction_data["description"],
                color=tuple(faction_data["color"]),
                rivalry=faction_data["rivalry"],
            )
            self.factions[faction.id] = faction

        logger.info(f"Loaded {len(self.factions)} factions")
        return self.factions

    def get_faction(self, faction_id: str) -> Optional[Faction]:
        """Get a faction by ID, or None if not found."""
        return self.factions.get(faction_id)

    def get_all_factions(self) -> List[Faction]:
        """Get list of all factions."""
        return list(self.factions.values())

    def load_politics(self) -> list:
        """Load faction relationship data from JSON."""
        from spacegame.models.politics import FactionRelationship

        file_path = self.data_dir / "politics" / "faction_relationships.json"
        if not file_path.exists():
            logger.warning(f"Faction relationships not found: {file_path}")
            return self.faction_relationships

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.faction_relationships = [
            FactionRelationship.from_dict(rel_data) for rel_data in data.get("relationships", [])
        ]
        logger.info(f"Loaded {len(self.faction_relationships)} faction relationships")
        return self.faction_relationships

    def load_politics_disputes(self) -> Dict[str, "PoliticsDisputeTemplate"]:
        """Load SA-P2 venue-dispute templates from ``data/politics/*.json``.

        Reads every ``*.json`` file under ``data/politics/`` other than
        the existing ``faction_relationships.json`` file (which
        :meth:`load_politics` consumes). Each file may contain a
        top-level ``"disputes": [...]`` list of template dicts.

        SA-P3 / P4 / P5 author the content; SA-P2 ships the loader.
        Empty / missing directory returns ``{}`` without error.

        Returns:
            ``{template_id: PoliticsDisputeTemplate}``.
        """
        from spacegame.models.politics_dispute import PoliticsDisputeTemplate  # noqa: F401

        politics_dir = self.data_dir / "politics"
        self.politics_disputes = {}
        if not politics_dir.exists():
            logger.debug("No data/politics/ directory; skipping dispute templates")
            return self.politics_disputes

        for path in sorted(politics_dir.glob("*.json")):
            if path.name == "faction_relationships.json":
                continue
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for entry in raw.get("disputes", []):
                template = self._parse_politics_dispute_template(entry)
                self.politics_disputes[template.id] = template

        if self.politics_disputes:
            logger.info(
                f"Loaded {len(self.politics_disputes)} politics dispute templates"
            )
        return self.politics_disputes

    def _parse_politics_dispute_template(
        self, data: dict
    ) -> "PoliticsDisputeTemplate":
        """Parse a single dispute template dict (from ``data/politics/*.json``)."""
        from spacegame.models.politics_dispute import (
            DelegateTemplate,
            OutcomeRow,
            PoliticsDisputeTemplate,
            PoliticsMarketShift,
        )

        delegates = tuple(
            DelegateTemplate(
                delegate_id=d["delegate_id"],
                name=d.get("name", d["delegate_id"]),
                starting_visible_state=d.get("starting_visible_state", "wavering"),
                position_vector=dict(d.get("position_vector", {})),
                faction_loyalty=float(d.get("faction_loyalty", 0.0)),
                prior_dispute_memory=int(d.get("prior_dispute_memory", -1)),
                sub_faction_id=d.get("sub_faction_id", ""),
            )
            for d in data.get("delegates", [])
        )

        outcome_matrix: Dict[str, OutcomeRow] = {}
        for category, row in data.get("outcome_matrix", {}).items():
            shifts = tuple(
                PoliticsMarketShift(
                    commodity_id=s["commodity_id"],
                    system_id=s["system_id"],
                    magnitude=float(s["magnitude"]),
                    duration_days=int(s.get("duration_days", 30)),
                )
                for s in row.get("market_shifts", [])
            )
            outcome_matrix[category] = OutcomeRow(
                rep_deltas=dict(row.get("rep_deltas", {})),
                market_shifts=shifts,
                mission_unlocks=tuple(row.get("mission_unlocks", [])),
                mission_locks=tuple(row.get("mission_locks", [])),
                news_headline=row.get("news_headline"),
            )

        return PoliticsDisputeTemplate(
            id=data["id"],
            headline=data["headline"],
            factions_affected=tuple(data.get("factions_affected", ())),
            base_difficulty=int(data.get("base_difficulty", 4)),
            round_count=int(data.get("round_count", 3)),
            deadline_days=int(data.get("deadline_days", 10)),
            delegates=delegates,
            eligible_framings=tuple(data.get("eligible_framings", ())),
            eligible_evidence=tuple(data.get("eligible_evidence", ())),
            framing_modifiers=dict(data.get("framing_modifiers", {})),
            framing_target_dimensions=dict(
                data.get("framing_target_dimensions", {})
            ),
            outcome_matrix=outcome_matrix,
            is_campaign_arc=bool(data.get("is_campaign_arc", False)),
            required_flags=tuple(data.get("required_flags", ())),
        )

    def load_faction_perks(self) -> Dict[str, Dict[str, list]]:
        """Load faction perks from JSON."""
        from spacegame.models.faction_perks import FactionPerk

        file_path = self.data_dir / "progression" / "faction_perks.json"
        if not file_path.exists():
            logger.warning(f"Faction perks not found: {file_path}")
            return self.faction_perks

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.faction_perks.clear()
        perk_count = 0
        for faction_id, tiers in data.get("faction_perks", {}).items():
            self.faction_perks[faction_id] = {}
            for tier_name, perk_list in tiers.items():
                perks = []
                for perk_data in perk_list:
                    perk = FactionPerk(
                        id=perk_data["id"],
                        perk_type=perk_data["type"],
                        value=perk_data["value"],
                        name=perk_data["name"],
                        description=perk_data["description"],
                        faction_id=faction_id,
                        required_tier=tier_name,
                    )
                    perks.append(perk)
                    perk_count += 1
                self.faction_perks[faction_id][tier_name] = perks

        logger.info(f"Loaded {perk_count} faction perks for {len(self.faction_perks)} factions")
        return self.faction_perks

    def load_galaxy_events(self) -> List[Dict]:
        """Load galaxy event templates and chains from JSON."""
        file_path = self.data_dir / "economy" / "galaxy_events.json"
        if not file_path.exists():
            logger.warning(f"Galaxy events not found: {file_path}")
            return self.galaxy_event_templates

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.galaxy_event_templates = data.get("galaxy_events", [])
        self.galaxy_event_chains = data.get("event_chains", [])
        logger.info(
            f"Loaded {len(self.galaxy_event_templates)} galaxy event templates, "
            f"{len(self.galaxy_event_chains)} event chains"
        )
        return self.galaxy_event_templates

    def load_station_chatter(self) -> list:
        """Load station chatter lines from JSON."""
        from spacegame.models.station_chatter import ChatterLine

        file_path = self.data_dir / "crew" / "station_chatter.json"
        if not file_path.exists():
            logger.warning(f"Station chatter not found: {file_path}")
            return self.station_chatter_lines

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.station_chatter_lines = []
        for entry in data.get("chatter_lines", []):
            self.station_chatter_lines.append(
                ChatterLine(
                    id=entry["id"],
                    system_id=entry["system_id"],
                    text=entry["text"],
                    category=entry["category"],
                    faction_id=entry.get("faction_id", ""),
                    min_reputation=entry.get("min_reputation", -100),
                    max_reputation=entry.get("max_reputation", 100),
                    requires_event_type=entry.get("requires_event_type", ""),
                    weight=entry.get("weight", 10),
                    required_flags=entry.get("required_flags", []),
                    excluded_flags=entry.get("excluded_flags", []),
                    one_shot=entry.get("one_shot", False),
                )
            )
        logger.info(f"Loaded {len(self.station_chatter_lines)} station chatter lines")
        return self.station_chatter_lines

    def load_news_templates(self) -> list:
        """Load news ticker headline templates from JSON."""
        from spacegame.models.news_ticker import HeadlineTemplate

        file_path = self.data_dir / "economy" / "news_templates.json"
        if not file_path.exists():
            logger.warning(f"News templates not found: {file_path}")
            return self.news_templates

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.news_templates = []
        for entry in data.get("news_templates", []):
            self.news_templates.append(
                HeadlineTemplate(
                    id=entry["id"],
                    template=entry["template"],
                    trigger=entry["trigger"],
                    priority=entry.get("priority", 5),
                    faction_id=entry.get("faction_id", ""),
                )
            )
        logger.info(f"Loaded {len(self.news_templates)} news headline templates")
        return self.news_templates

    def load_travel_log_templates(self) -> dict:
        """Load travel log templates from JSON."""
        file_path = self.data_dir / "journal" / "travel_log_templates.json"
        if not file_path.exists():
            logger.warning(f"Travel log templates not found: {file_path}")
            return self.travel_log_templates

        with open(file_path, "r", encoding="utf-8") as f:
            self.travel_log_templates = json.load(f)

        first_visit_count = len(self.travel_log_templates.get("first_visit", {}))
        logger.info(f"Loaded travel log templates ({first_visit_count} first-visit entries)")
        return self.travel_log_templates

    def load_balance_config(self) -> Dict:
        """Load economy/balance configuration from JSON.

        Values in balance.json override defaults in config.py. This allows
        tuning game difficulty without modifying code, and enables difficulty
        presets (Easy/Normal/Hard) by swapping config files.
        """
        file_path = self.data_dir / "economy" / "balance.json"
        if not file_path.exists():
            logger.info("No balance.json found, using config.py defaults")
            return self.balance_config

        with open(file_path, "r", encoding="utf-8") as f:
            self.balance_config = json.load(f)

        # Apply overrides to config.py constants
        import spacegame.config as cfg

        sc = self.balance_config.get("starting_conditions", {})
        if "credits" in sc:
            cfg.STARTING_CREDITS = sc["credits"]
        if "fuel" in sc:
            cfg.STARTING_FUEL = sc["fuel"]

        xp = self.balance_config.get("xp_rates", {})
        if "per_trade" in xp:
            cfg.XP_PER_TRADE = xp["per_trade"]
        if "per_mining" in xp:
            cfg.XP_PER_MINING = xp["per_mining"]
        if "per_salvage" in xp:
            cfg.XP_PER_SALVAGE = xp["per_salvage"]
        if "per_refine" in xp:
            cfg.XP_PER_REFINE = xp["per_refine"]
        if "per_travel" in xp:
            cfg.XP_PER_TRAVEL = xp["per_travel"]

        prog = self.balance_config.get("progression", {})
        if "attribute_cap_level" in prog:
            cfg.ATTRIBUTE_CAP_LEVEL = prog["attribute_cap_level"]

        enc = self.balance_config.get("encounter_chances", {})
        from spacegame.models import encounter as enc_mod

        if "safe" in enc:
            enc_mod.ENCOUNTER_CHANCE_SAFE = enc["safe"]
        if "moderate" in enc:
            enc_mod.ENCOUNTER_CHANCE_MODERATE = enc["moderate"]
        if "dangerous" in enc:
            enc_mod.ENCOUNTER_CHANCE_DANGEROUS = enc["dangerous"]

        early = self.balance_config.get("early_game_protection", {})
        if "level_threshold" in early:
            enc_mod.EARLY_GAME_LEVEL = early["level_threshold"]
        if "non_hostile_chance" in early:
            enc_mod.EARLY_GAME_NON_HOSTILE_CHANCE = early["non_hostile_chance"]
        if "flee_bonus" in early:
            enc_mod.EARLY_GAME_FLEE_BONUS = early["flee_bonus"]

        logger.info("Loaded balance config from balance.json")
        return self.balance_config

    def get_balance_value(self, *keys: str, default: object = None) -> object:
        """Get a nested value from balance config.

        Args:
            *keys: Path of keys, e.g. ("economy", "rest_cost_per_day").
            default: Default if path not found.

        Returns:
            The value, or default.
        """
        current = self.balance_config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def get_mining_config(self, system_id: str) -> Optional[MiningConfig]:
        """Get mining config for a system, or None if not a mining system."""
        return self.mining_configs.get(system_id)

    def get_salvage_config(self, system_id: str) -> Optional[SalvageConfig]:
        """Get salvage config for a system, or None."""
        return self.salvage_configs.get(system_id)

    def get_system(self, system_id: str) -> StarSystem:
        """
        Get a specific star system by ID.

        Args:
            system_id: System ID to retrieve

        Returns:
            StarSystem instance

        Raises:
            KeyError: If system not found
        """
        return self.systems[system_id]

    def get_commodity(self, commodity_id: str) -> Commodity:
        """
        Get a specific commodity by ID.

        Args:
            commodity_id: Commodity ID to retrieve

        Returns:
            Commodity instance

        Raises:
            KeyError: If commodity not found
        """
        return self.commodities[commodity_id]

    def get_ship_type(self, ship_id: str) -> ShipType:
        """
        Get a specific ship type by ID.

        Args:
            ship_id: Ship type ID to retrieve

        Returns:
            ShipType instance

        Raises:
            KeyError: If ship type not found
        """
        return self.ship_types[ship_id]

    def get_all_systems(self) -> List[StarSystem]:
        """Get list of all star systems."""
        return list(self.systems.values())

    def get_all_commodities(self) -> List[Commodity]:
        """Get list of all commodities."""
        return list(self.commodities.values())

    def get_all_ship_types(self) -> List[ShipType]:
        """Get list of all ship types."""
        return list(self.ship_types.values())

    def load_npcs(self) -> Dict[str, NPC]:
        """Load NPC definitions from JSON."""
        file_path = self.data_dir / "characters" / "npcs.json"
        if not file_path.exists():
            logger.warning(f"NPCs not found: {file_path}")
            return self.npcs

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.npcs.clear()
        for npc_data in data.get("npcs", []):
            # Parse dialogue states (multi-state NPC system)
            states: list[DialogueState] = []
            for sd in npc_data.get("dialogue_states", []):
                states.append(
                    DialogueState(
                        state_id=sd["state_id"],
                        dialogue_id=sd["dialogue_id"],
                        required_flags=sd.get("required_flags", []),
                        excluded_flags=sd.get("excluded_flags", []),
                    )
                )
            npc = NPC(
                id=npc_data["id"],
                name=npc_data["name"],
                title=npc_data["title"],
                portrait_color=tuple(npc_data["portrait_color"]),
                home_system_id=npc_data["home_system_id"],
                dialogue_id=npc_data["dialogue_id"],
                faction_id=npc_data.get("faction_id", ""),
                auto_trigger_gate_flag=npc_data.get("auto_trigger_gate_flag", ""),
                auto_trigger_prerequisites=npc_data.get("auto_trigger_prerequisites", []),
                hide_after_flag=npc_data.get("hide_after_flag", ""),
                dialogue_music=npc_data.get("dialogue_music", ""),
                dialogue_states=states,
            )
            self.npcs[npc.id] = npc

        logger.info(f"Loaded {len(self.npcs)} NPCs")
        return self.npcs

    def load_dialogues(self) -> Dict[str, DialogueTree]:
        """Load dialogue trees from JSON files."""
        dialogue_dir = self.data_dir / "dialogue"
        self.dialogue_trees.clear()

        for filename in ["dialogues.json", "crew_quest_dialogues.json"]:
            file_path = dialogue_dir / filename
            if not file_path.exists():
                if filename == "dialogues.json":
                    logger.warning(f"Dialogues not found: {file_path}")
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for tree_data in data.get("dialogues", []):
                tree = self._parse_dialogue_tree(tree_data)
                self.dialogue_trees[tree.id] = tree

        logger.info(f"Loaded {len(self.dialogue_trees)} dialogue trees")
        return self.dialogue_trees

    def _parse_dialogue_tree(self, data: dict) -> DialogueTree:
        """Parse dialogue tree data dict into DialogueTree object."""
        nodes: Dict[str, DialogueNode] = {}
        for node_data in data.get("nodes", []):
            responses = []
            for r in node_data.get("responses", []):
                skill_check = None
                if "skill_check" in r:
                    sc = r["skill_check"]
                    skill_check = SkillCheck(
                        skill=sc["skill"],
                        difficulty=sc["difficulty"],
                        success_node_id=sc["success_node_id"],
                        failure_node_id=sc["failure_node_id"],
                        set_flag_on_success=sc.get("set_flag_on_success"),
                        set_flag_on_failure=sc.get("set_flag_on_failure"),
                    )
                responses.append(
                    DialogueResponse(
                        text=r["text"],
                        next_node_id=r.get("next_node_id"),
                        set_flag=r.get("set_flag"),
                        skill_check=skill_check,
                        disposition_change=r.get("disposition_change", 0),
                        required_flags=r.get("required_flags", []),
                        excluded_flags=r.get("excluded_flags", []),
                        faction_reputation_changes=r.get("faction_reputation_changes", []),
                        crew_loyalty_changes=r.get("crew_loyalty_changes", {}),
                    )
                )
            node = DialogueNode(
                id=node_data["id"],
                speaker_id=node_data["speaker_id"],
                text=node_data["text"],
                responses=responses,
                expression=node_data.get("expression"),
                subtext=node_data.get("subtext", ""),
            )
            nodes[node.id] = node

        return DialogueTree(
            id=data["id"],
            start_node_id=data["start_node_id"],
            nodes=nodes,
        )

    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """Get an NPC by ID, or None if not found."""
        return self.npcs.get(npc_id)

    def get_npcs_at_system(self, system_id: str) -> List[NPC]:
        """Get all NPCs located at a given system."""
        return [npc for npc in self.npcs.values() if npc.home_system_id == system_id]

    def get_dialogue(self, dialogue_id: str) -> Optional[DialogueTree]:
        """Get a dialogue tree by ID, or None if not found."""
        return self.dialogue_trees.get(dialogue_id)

    def load_missions(self) -> List[Mission]:
        """Load mission definitions from JSON.

        Loads campaign missions from missions.json and side missions from
        side_missions.json if it exists.
        """
        missions_dir = self.data_dir / "missions"
        self.missions.clear()

        for filename in [
            "missions.json",
            "side_missions.json",
            "crew_quests.json",
            "sa_2_pilgrimage.json",
            "sa_v_investment_intro.json",
        ]:
            file_path = missions_dir / filename
            if not file_path.exists():
                if filename == "missions.json":
                    logger.warning(f"Missions not found: {file_path}")
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for mission_data in data.get("missions", []):
                mission = self._parse_mission(mission_data)
                self.missions.append(mission)

        logger.info(f"Loaded {len(self.missions)} missions")
        return self.missions

    def _parse_mission(self, data: dict) -> Mission:
        """Parse mission data dict into Mission object."""
        objectives = [
            MissionObjective(
                type=ObjectiveType(obj["type"]),
                target_id=obj["target_id"],
                target_quantity=obj.get("target_quantity", 1),
                description=obj.get("description", ""),
            )
            for obj in data.get("objectives", [])
        ]
        rewards = [
            MissionReward(
                reward_type=r["reward_type"],
                amount=r["amount"],
                target_id=r.get("target_id", ""),
            )
            for r in data.get("rewards", [])
        ]
        on_accept_cargo = [
            AcceptCargo(commodity_id=c["commodity_id"], quantity=c["quantity"])
            for c in data.get("on_accept_cargo", [])
        ]
        forced_encounter = None
        if "forced_encounter" in data:
            forced_encounter = ForcedEncounter.from_dict(data["forced_encounter"])
        # TW-4: optional soft_deadline
        soft_deadline = None
        if "soft_deadline" in data:
            from spacegame.models.soft_deadline import SoftDeadline

            soft_deadline = SoftDeadline.from_dict(data["soft_deadline"])
        return Mission(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            objectives=objectives,
            rewards=rewards,
            prerequisites=data.get("prerequisites", []),
            on_accept_cargo=on_accept_cargo,
            required_flags=data.get("required_flags", []),
            forced_encounter=forced_encounter,
            auto_accept=data.get("auto_accept", False),
            hint=data.get("hint", ""),
            ground_mission_id=data.get("ground_mission_id", ""),
            ground_mission_system_id=data.get("ground_mission_system_id", ""),
            ground_mission_complete_flag=data.get("ground_mission_complete_flag", ""),
            mission_type=data.get("mission_type", "campaign"),
            available_at=data.get("available_at", []),
            available_after=data.get("available_after", ""),
            available_before=data.get("available_before", ""),
            repeatable=data.get("repeatable", False),
            discovery_method=data.get("discovery_method", ""),
            crew_member_id=data.get("crew_member_id", ""),
            required_reputation=data.get("required_reputation", []),
            soft_deadline=soft_deadline,
            timeliness_comments=dict(data.get("timeliness_comments", {})),
        )

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get a mission definition by ID, or None if not found."""
        for m in self.missions:
            if m.id == mission_id:
                return m
        return None

    def load_crew_templates(self) -> Dict[str, CrewTemplate]:
        """Load crew template definitions from JSON."""
        file_path = self.data_dir / "crew" / "crew_members.json"
        if not file_path.exists():
            logger.warning(f"Crew templates not found: {file_path}")
            return self.crew_templates

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.crew_templates.clear()
        for crew_data in data.get("crew_templates", []):
            template = self._parse_crew_template(crew_data)
            self.crew_templates[template.id] = template

        logger.info(f"Loaded {len(self.crew_templates)} crew templates")
        return self.crew_templates

    def _parse_crew_template(self, data: dict) -> CrewTemplate:
        """Parse a crew template from raw JSON data."""
        abilities = [
            CrewAbility(
                bonus_type=a["bonus_type"],
                bonus_value=a["bonus_value"],
                description=a["description"],
                unlock_level=a.get("unlock_level", 1),
            )
            for a in data.get("abilities", [])
        ]
        default_attrs = {"com": 1, "acu": 1, "res": 1, "ing": 1, "syn": 1}
        return CrewTemplate(
            id=data["id"],
            name=data["name"],
            role=data["role"],
            description=data["description"],
            portrait_color=data["portrait_color"],
            abilities=abilities,
            max_level=data.get("max_level", 5),
            xp_thresholds=data.get("xp_thresholds", [0, 50, 150, 350, 700]),
            base_attributes=data.get("base_attributes", default_attrs),
            faction_id=data.get("faction_id", ""),
            home_system_id=data.get("home_system_id", ""),
            combat_move=data.get("combat_move"),
            combat_moves=data.get("combat_moves", []),
            is_companion=data.get("is_companion", False),
        )

    def get_crew_template(self, template_id: str) -> Optional[CrewTemplate]:
        """Get a crew template by ID, or None if not found."""
        return self.crew_templates.get(template_id)

    def load_ambient_dialogue(self) -> List[AmbientLine]:
        """Load ambient crew dialogue lines from JSON."""
        file_path = self.data_dir / "crew" / "ambient_dialogue.json"
        if not file_path.exists():
            logger.warning(f"Ambient dialogue not found: {file_path}")
            return self.ambient_lines

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.ambient_lines.clear()
        for line_data in data.get("ambient_lines", []):
            self.ambient_lines.append(
                AmbientLine(
                    crew_id=line_data["crew_id"],
                    text=line_data["text"],
                    context=line_data["context"],
                    system_id=line_data.get("system_id", ""),
                    faction_id=line_data.get("faction_id", ""),
                    required_crew=line_data.get("required_crew", ""),
                    min_loyalty=line_data.get("min_loyalty", 0),
                    action_type=line_data.get("action_type", ""),
                )
            )

        logger.info(f"Loaded {len(self.ambient_lines)} ambient dialogue lines")
        return self.ambient_lines

    def load_enemy_templates(self) -> Dict[str, EnemyShipTemplate]:
        """Load enemy ship templates from JSON."""
        file_path = self.data_dir / "combat" / "enemies.json"
        if not file_path.exists():
            logger.warning(f"Enemy templates not found: {file_path}")
            return self.enemy_templates

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.enemy_templates.clear()
        for enemy_data in data.get("enemy_templates", []):
            template = self._parse_enemy_template(enemy_data)
            self.enemy_templates[template.id] = template

        logger.info(f"Loaded {len(self.enemy_templates)} enemy templates")
        return self.enemy_templates

    def load_captains(self) -> Dict[str, "EnemyCaptain"]:
        """Load named combat captains from ``data/combat/captains.json``.

        CE-1 ships with a stub roster (~2 captains). CE-2 will expand to
        the full flavor-tier roster (15-20). RC flips specific captains
        to ``is_recurring=True`` when rival infrastructure lands.
        """
        from spacegame.models.enemy_captain import EnemyCaptain

        file_path = self.data_dir / "combat" / "captains.json"
        if not file_path.exists():
            logger.warning(f"Captains file not found: {file_path}")
            return self.captains

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.captains.clear()
        for cap_data in data.get("captains", []):
            captain = EnemyCaptain.from_dict(cap_data)
            self.captains[captain.id] = captain

        logger.info(f"Loaded {len(self.captains)} captains")
        return self.captains

    def load_complications(self) -> Dict[str, "CombatComplication"]:
        """Load combat complication definitions (CE-3).

        Each complication is a scripted mid-combat event that fires when
        its trigger condition is met. Effects mutate the combat state
        (spawning reinforcements, applying environmental modifiers) or
        produce narration. Encounters reference complications by id
        via ``EncounterDefinition.complication_ids``.
        """
        from spacegame.models.combat_complication import CombatComplication

        file_path = self.data_dir / "combat" / "complications.json"
        if not file_path.exists():
            logger.warning(f"Complications file not found: {file_path}")
            return self.complications

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.complications.clear()
        for comp_data in data.get("complications", []):
            comp = CombatComplication.from_dict(comp_data)
            self.complications[comp.id] = comp

        logger.info(f"Loaded {len(self.complications)} combat complications")
        return self.complications

    def load_timed_threads(self) -> Dict[str, "TimedThread"]:
        """Load TimedThread definitions (TW-2).

        Each thread drifts through one or more ``DriftState`` entries when
        untouched for longer than the threshold. Empty file is fine.
        """
        from spacegame.models.timed_thread import TimedThread

        file_path = self.data_dir / "progression" / "timed_threads.json"
        if not file_path.exists():
            logger.warning(f"Timed threads file not found: {file_path}")
            return self.timed_threads

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.timed_threads.clear()
        for raw in data.get("threads", []):
            thread = TimedThread.from_dict(raw)
            self.timed_threads[thread.id] = thread

        logger.info(f"Loaded {len(self.timed_threads)} timed threads")
        return self.timed_threads

    def load_captain_variants(self) -> Dict[tuple, "CaptainVariant"]:
        """Load per-meeting-state captain dialogue variants (RC-3).

        Builds a (captain_id, meeting_state) -> CaptainVariant lookup
        for O(1) resolution. Empty file is fine: no variants is a valid
        starting state (RC-4 authors content).
        """
        from spacegame.models.captain_variant import CaptainVariant

        file_path = self.data_dir / "combat" / "captain_variants.json"
        if not file_path.exists():
            logger.warning(f"Captain variants file not found: {file_path}")
            return self.captain_variants

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.captain_variants.clear()
        for raw in data.get("variants", []):
            variant = CaptainVariant.from_dict(raw)
            key = (variant.captain_id, variant.meeting_state)
            self.captain_variants[key] = variant

        logger.info(f"Loaded {len(self.captain_variants)} captain dialogue variants")
        return self.captain_variants

    def load_crew_interjections(self) -> List["CrewInterjection"]:
        """Load crew combat interjections (CE-5).

        Each entry binds one (crew_id, trigger) pair to a bank of
        interchangeable lines. The combat view's CrewInterjectionResolver
        picks one line per fire and throttles display.
        """
        from spacegame.models.crew_interjection import CrewInterjection

        file_path = self.data_dir / "combat" / "crew_interjections.json"
        if not file_path.exists():
            logger.warning(f"Crew interjections file not found: {file_path}")
            return self.crew_interjections

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.crew_interjections.clear()
        for raw in data.get("interjections", []):
            self.crew_interjections.append(CrewInterjection.from_dict(raw))

        logger.info(f"Loaded {len(self.crew_interjections)} crew interjections")
        return self.crew_interjections

    def load_ship_ultimates(self) -> Dict[str, ShipUltimate]:
        """Load ship class ultimate abilities from JSON."""
        file_path = self.data_dir / "combat" / "ultimates.json"
        if not file_path.exists():
            logger.warning(f"Ultimates file not found: {file_path}")
            return self.ship_ultimates
        with open(file_path, "r") as f:
            data = json.load(f)

        self.ship_ultimates.clear()
        for ult_data in data.get("ultimates", []):
            ultimate = ShipUltimate.from_dict(ult_data)
            self.ship_ultimates[ultimate.ship_class_category] = ultimate

        logger.info(f"Loaded {len(self.ship_ultimates)} ship ultimates")
        return self.ship_ultimates

    def load_hull_shapes(self) -> Dict[str, HullShape]:
        """Load hull shape templates from JSON."""
        file_path = self.data_dir / "ships" / "shapes.json"
        if not file_path.exists():
            logger.warning(f"Shapes file not found: {file_path}")
            return self.hull_shapes
        with open(file_path, "r") as f:
            data = json.load(f)

        self.hull_shapes.clear()
        for shape_data in data.get("shapes", []):
            shape = HullShape.from_dict(shape_data)
            self.hull_shapes[shape.id] = shape

        logger.info(f"Loaded {len(self.hull_shapes)} hull shapes")
        return self.hull_shapes

    def load_hull_materials(self) -> Dict[str, HullMaterial]:
        """Load hull material definitions from JSON."""
        file_path = self.data_dir / "ships" / "materials.json"
        if not file_path.exists():
            logger.warning(f"Materials file not found: {file_path}")
            return self.hull_materials
        with open(file_path, "r") as f:
            data = json.load(f)

        self.hull_materials.clear()
        for mat_data in data.get("materials", []):
            material = HullMaterial.from_dict(mat_data)
            self.hull_materials[material.id] = material

        logger.info(f"Loaded {len(self.hull_materials)} hull materials")
        return self.hull_materials

    def load_ship_modules(self) -> Dict[str, "ShipModule"]:
        """Load ship module blueprints from JSON."""
        from spacegame.models.ship_module import ShipModule

        file_path = self.data_dir / "ships" / "modules.json"
        if not file_path.exists():
            logger.warning(f"Modules file not found: {file_path}")
            return self.ship_modules
        with open(file_path, "r") as f:
            data = json.load(f)

        self.ship_modules.clear()
        for mod_data in data.get("modules", []):
            module = ShipModule.from_dict(mod_data)
            self.ship_modules[module.id] = module

        logger.info(f"Loaded {len(self.ship_modules)} ship modules")
        return self.ship_modules

    def load_slot_definitions(self) -> Dict[str, "SlotDefinition"]:
        """Load slot definitions (type+size templates) from JSON."""
        from spacegame.models.slot_definition import SlotDefinition

        file_path = self.data_dir / "ships" / "slot_definitions.json"
        if not file_path.exists():
            logger.warning(f"Slot definitions file not found: {file_path}")
            return self.slot_definitions
        with open(file_path, "r") as f:
            data = json.load(f)

        self.slot_definitions.clear()
        for entry in data.get("slot_definitions", []):
            slot_def = SlotDefinition.from_dict(entry)
            self.slot_definitions[slot_def.id] = slot_def

        logger.info(f"Loaded {len(self.slot_definitions)} slot definitions")
        return self.slot_definitions

    def load_ship_parts(self) -> Dict[str, "ShipPart"]:
        """Load ship parts (equippable items for slots) from JSON."""
        from spacegame.models.ship_part import ShipPart

        file_path = self.data_dir / "ships" / "parts.json"
        if not file_path.exists():
            # Parts file is optional during migration — not all installs have it yet
            logger.info("Ship parts file not found (optional during migration)")
            return self.ship_parts
        with open(file_path, "r") as f:
            data = json.load(f)

        self.ship_parts.clear()
        for entry in data.get("parts", []):
            part = ShipPart.from_dict(entry)
            self.ship_parts[part.id] = part

        logger.info(f"Loaded {len(self.ship_parts)} ship parts")
        return self.ship_parts

    def load_module_materials(self) -> Dict[str, HullMaterial]:
        """Load module-specific visual materials and merge into hull_materials."""
        file_path = self.data_dir / "ships" / "module_materials.json"
        if not file_path.exists():
            logger.warning(f"Module materials file not found: {file_path}")
            return self.hull_materials
        with open(file_path, "r") as f:
            data = json.load(f)

        count = 0
        for mat_data in data.get("module_materials", []):
            material = HullMaterial.from_dict(mat_data)
            self.hull_materials[material.id] = material
            count += 1

        logger.info(f"Loaded {count} module materials (merged into hull_materials)")
        return self.hull_materials

    def load_drydock_catalogs(self) -> Dict[str, dict]:
        """Load per-system drydock content catalogs from JSON."""
        file_path = self.data_dir / "ships" / "drydock_catalogs.json"
        if not file_path.exists():
            logger.warning(f"Drydock catalogs not found: {file_path}")
            return self.drydock_catalogs
        with open(file_path, "r") as f:
            data = json.load(f)
        self.drydock_catalogs = data.get("drydock_catalogs", {})
        logger.info(f"Loaded drydock catalogs for {len(self.drydock_catalogs)} systems")
        return self.drydock_catalogs

    def _parse_enemy_template(self, data: dict) -> EnemyShipTemplate:
        """Parse an enemy ship template from raw JSON data."""
        moves = [self._parse_combat_move(m) for m in data.get("moves", [])]
        return EnemyShipTemplate(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            behavior=EnemyBehavior(data["behavior"]),
            hull=data["hull"],
            shields=data["shields"],
            energy=data["energy"],
            energy_regen=data["energy_regen"],
            speed=data["speed"],
            evasion=data["evasion"],
            accuracy=data["accuracy"],
            moves=moves,
            loot_table=data.get("loot_table", []),
            negotiate_difficulty=data.get("negotiate_difficulty", 3),
            flee_threshold=data.get("flee_threshold", 0.4),
            xp_reward=data.get("xp_reward", 20),
            faction_id=data.get("faction_id", ""),
            danger_tier=data.get("danger_tier", "moderate"),
            bribe_cost=data.get("bribe_cost", 0),
            credit_reward=data.get("credit_reward", 0),
            rare_loot=data.get("rare_loot", []),
            combat_armor=data.get("combat_armor", 0),
            is_boss=data.get("is_boss", False),
            boss_hp_multiplier=data.get("boss_hp_multiplier", 1),
            phases=[BossPhase.from_dict(p) for p in data.get("phases", [])],
            immune_to=data.get("immune_to", []),
            max_suppressed_stacks=data.get("max_suppressed_stacks", 3),
            sprite_rotation=data.get("sprite_rotation", 0),
            trophy_drop=data.get("trophy_drop", ""),
            composite_build=data.get("composite_build"),
            targetable_subsystems=data.get("targetable_subsystems", []),
        )

    def _parse_combat_move(self, data: dict) -> CombatMove:
        """Parse a combat move from raw JSON data."""
        return CombatMove.from_dict(data)

    def get_commodity_volumes(self) -> Dict[str, int]:
        """
        Get mapping of commodity IDs to their volumes.

        Useful for cargo calculations.

        Returns:
            Dict mapping commodity_id to volume_per_unit
        """
        return {c.id: c.volume_per_unit for c in self.commodities.values()}

    def load_journal_entries(self) -> List[JournalEntry]:
        """Load journal auto-entry templates from JSON.

        Returns:
            List of loaded journal entries.
        """
        file_path = self.data_dir / "journal" / "entries.json"
        if not file_path.exists():
            logger.warning(f"Journal entries not found: {file_path}")
            return self.journal_entries

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.journal_entries.clear()
        for entry_data in data.get("journal_entries", []):
            entry = self._parse_journal_entry(entry_data)
            self.journal_entries.append(entry)

        logger.info(f"Loaded {len(self.journal_entries)} journal entries")
        return self.journal_entries

    def _parse_journal_entry(self, data: dict) -> JournalEntry:
        """Parse a journal entry template from raw JSON data.

        Args:
            data: Raw JSON dict for one journal entry.

        Returns:
            JournalEntry instance.
        """
        return JournalEntry(
            entry_id=data["entry_id"],
            text=data["text"],
            game_day=0,
            system_id=data.get("system_id", ""),
            source="auto",
            trigger_flag=data.get("trigger_flag", ""),
            mission_id=data.get("mission_id", ""),
        )

    def load_encounter_definitions(self) -> List[EncounterDefinition]:
        """Load encounter definitions from all JSON files in the encounters directory.

        Returns:
            List of loaded encounter definitions.
        """
        enc_dir = self.data_dir / "encounters"
        if not enc_dir.exists():
            logger.warning(f"Encounters directory not found: {enc_dir}")
            return self.encounter_definitions

        self.encounter_definitions.clear()
        for file_path in sorted(enc_dir.glob("*.json")):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for enc_data in data.get("encounters", []):
                defn = self._parse_encounter_definition(enc_data)
                self.encounter_definitions.append(defn)

        logger.info(f"Loaded {len(self.encounter_definitions)} encounter definitions")
        return self.encounter_definitions

    def _parse_encounter_definition(self, data: dict) -> EncounterDefinition:
        """Parse encounter definition dict into EncounterDefinition object.

        Args:
            data: Raw JSON dict for one encounter definition.

        Returns:
            EncounterDefinition instance.
        """
        from spacegame.models.encounter import EncounterSkillCheck

        def _parse_outcome(raw: dict) -> EncounterOutcome:
            rewards = [
                MissionReward(
                    reward_type=r["reward_type"],
                    amount=r["amount"],
                    target_id=r.get("target_id", ""),
                )
                for r in raw.get("rewards", [])
            ]
            return EncounterOutcome(
                description=raw.get("description", ""),
                rewards=rewards,
                leads_to_combat=raw.get("leads_to_combat", False),
                enemy_template_ids=raw.get("enemy_template_ids", []),
            )

        choices = []
        for choice_data in data.get("choices", []):
            outcome = _parse_outcome(choice_data.get("outcome", {}))
            failure_outcome = (
                _parse_outcome(choice_data["failure_outcome"])
                if "failure_outcome" in choice_data
                else None
            )
            skill_check_raw = choice_data.get("skill_check")
            skill_check = (
                EncounterSkillCheck(
                    skill=skill_check_raw["skill"],
                    difficulty=int(skill_check_raw["difficulty"]),
                    set_flag_on_success=skill_check_raw.get("set_flag_on_success"),
                    set_flag_on_failure=skill_check_raw.get("set_flag_on_failure"),
                )
                if skill_check_raw
                else None
            )
            choices.append(
                EncounterChoice(
                    id=choice_data["id"],
                    label=choice_data["label"],
                    description=choice_data.get("description", ""),
                    outcome=outcome,
                    skill_check=skill_check,
                    failure_outcome=failure_outcome,
                    requires_credits=int(choice_data.get("requires_credits", 0)),
                )
            )

        icon_color_raw = data.get("icon_color", [200, 200, 200])
        icon_color = tuple(icon_color_raw) if isinstance(icon_color_raw, list) else icon_color_raw

        return EncounterDefinition(
            id=data["id"],
            encounter_type=data["encounter_type"],
            name=data["name"],
            description=data["description"],
            choices=choices,
            weight=data.get("weight", 10),
            danger_levels=data.get("danger_levels", ["moderate", "dangerous"]),
            icon_color=icon_color,
            only_systems=data.get("only_systems", []),
            excluded_systems=data.get("excluded_systems", []),
            required_faction=data.get("required_faction", ""),
            requires_flags=data.get("requires_flags", []),
            excludes_flags=data.get("excludes_flags", []),
            unique=data.get("unique", False),
            min_level=data.get("min_level", 0),
            max_level=data.get("max_level", 0),
            tone=data.get("tone", ""),
            category=data.get("category", ""),
            captain_id=data.get("captain_id", ""),
            complication_ids=list(data.get("complication_ids", [])),
        )

    def load_ground_equipment(self) -> Dict[str, "GroundEquipment"]:
        """Load ground equipment definitions from JSON.

        Returns:
            Dict mapping equipment ID to GroundEquipment.
        """
        from spacegame.models.ground_equipment import GroundEquipment

        file_path = self.data_dir / "ground" / "equipment.json"
        if not file_path.exists():
            logger.warning(f"Ground equipment data not found: {file_path}")
            return self.ground_equipment

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.ground_equipment.clear()
        for eq_data in data.get("ground_equipment", []):
            eq = GroundEquipment.from_dict(eq_data)
            self.ground_equipment[eq.id] = eq

        logger.info(f"Loaded {len(self.ground_equipment)} ground equipment")
        return self.ground_equipment

    def load_contract_templates(self) -> Dict[str, dict]:
        """Load ground contract briefing templates from JSON.

        Returns:
            Dict mapping mission type key to template dict.
        """
        file_path = self.data_dir / "ground" / "contract_templates.json"
        if not file_path.exists():
            logger.warning(f"Contract templates not found: {file_path}")
            return self.contract_templates

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.contract_templates = data.get("contract_templates", {})
        logger.info(f"Loaded {len(self.contract_templates)} contract templates")
        return self.contract_templates

    def load_campaign_maps(self) -> Dict[str, dict]:
        """Load hand-authored campaign ground maps from JSON files.

        Returns:
            Dict mapping campaign map ID to raw JSON dict.
        """
        campaign_dir = self.data_dir / "ground" / "campaign"
        self.campaign_ground_maps = {}
        if not campaign_dir.exists():
            logger.debug("No campaign maps directory found")
            return self.campaign_ground_maps

        for path in sorted(campaign_dir.glob("*.json")):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            map_id = data.get("id", path.stem)
            self.campaign_ground_maps[map_id] = data

        logger.info(f"Loaded {len(self.campaign_ground_maps)} campaign ground maps")
        return self.campaign_ground_maps

    def load_faction_laws(self) -> Dict[str, "FactionLaw"]:
        """Load faction law enforcement rules from JSON.

        Returns:
            Dict mapping faction_id to FactionLaw.
        """
        from spacegame.models.smuggling import FactionLaw

        file_path = self.data_dir / "economy" / "faction_laws.json"
        self.faction_laws = {}
        if not file_path.exists():
            logger.debug("No faction_laws.json found")
            return self.faction_laws

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for law_data in data.get("faction_laws", []):
            law = FactionLaw.from_dict(law_data)
            self.faction_laws[law.faction_id] = law

        logger.info(f"Loaded {len(self.faction_laws)} faction laws")
        return self.faction_laws

    def load_locations(self) -> Dict[str, List[Location]]:
        """Load station locations from JSON.

        Returns:
            Dict mapping system_id to list of Location objects.
        """
        file_path = self.data_dir / "galaxy" / "locations.json"
        self.locations = {}
        if not file_path.exists():
            logger.debug("No locations.json found")
            return self.locations

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for system_id, loc_list in data.get("locations", {}).items():
            locations = []
            for loc_data in loc_list:
                loc_data["system_id"] = system_id
                locations.append(Location.from_dict(loc_data))
            self.locations[system_id] = locations

        logger.info(f"Loaded locations for {len(self.locations)} systems")
        return self.locations

    def get_locations_for_system(self, system_id: str) -> List[Location]:
        """Get all locations at a given system.

        Args:
            system_id: The system to query.

        Returns:
            List of Location objects, empty if system not found.
        """
        return self.locations.get(system_id, [])

    def load_investment_configs(self) -> Dict[str, InvestmentTemplate]:
        """Load per-system investment configurations from JSON.

        Returns:
            Dict mapping system_id to InvestmentTemplate objects.
        """
        file_path = self.data_dir / "economy" / "investment_configs.json"
        self.investment_templates = {}
        if not file_path.exists():
            logger.debug("No investment_configs.json found")
            return self.investment_templates

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for config in data.get("investment_configs", []):
            tiers = [InvestmentTier.from_dict(t) for t in config.get("tiers", [])]
            template = InvestmentTemplate(
                system_id=config["system_id"],
                investment_type=config["investment_type"],
                name=config["name"],
                description=config.get("description", ""),
                tiers=tiers,
            )
            self.investment_templates[template.system_id] = template

        logger.info(f"Loaded investment configs for {len(self.investment_templates)} systems")
        return self.investment_templates

    def get_investment_template(self, system_id: str) -> Optional[InvestmentTemplate]:
        """Get investment template for a system.

        Args:
            system_id: The system to query.

        Returns:
            InvestmentTemplate or None if not found.
        """
        return self.investment_templates.get(system_id)


# Global data loader instance
_data_loader: DataLoader = None


def get_data_loader() -> DataLoader:
    """
    Get the global DataLoader instance.

    Initializes and loads data on first call.

    Returns:
        Initialized DataLoader
    """
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader()
        _data_loader.load_all()
        _data_loader.validate()
    return _data_loader
