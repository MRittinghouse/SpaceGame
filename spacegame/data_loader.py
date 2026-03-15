"""
Data loading system for game content.

Loads JSON data files and converts them to game model instances.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from spacegame.models.system import StarSystem, Station, Economy, Coordinates
from spacegame.models.location import Location
from spacegame.models.investment import InvestmentTemplate, InvestmentTier
from spacegame.models.commodity import Commodity, CommodityCategory, Legality
from spacegame.models.ship import ShipType
from spacegame.models.mining import MiningConfig
from spacegame.models.salvage import SalvageConfig
from spacegame.models.refining import Recipe
from spacegame.models.journal import JournalEntry
from spacegame.models.upgrades import ShipUpgrade
from spacegame.models.achievement import Achievement
from spacegame.models.faction import Faction
from spacegame.models.dialogue import (
    NPC,
    DialogueTree,
    DialogueNode,
    DialogueResponse,
    SkillCheck,
)
from spacegame.models.mission import (
    AcceptCargo,
    ForcedEncounter,
    Mission,
    MissionObjective,
    MissionReward,
    ObjectiveType,
)
from spacegame.models.crew import CrewTemplate, CrewAbility
from spacegame.models.combat import (
    CombatEffect,
    CombatMove,
    EnemyBehavior,
    EnemyShipTemplate,
)
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterDefinition,
    EncounterOutcome,
)
from spacegame.utils.logger import logger


class DataLoader:
    """
    Loads and manages game data from JSON files.

    Provides centralized access to all game content.
    """

    def __init__(self, data_dir: Path = None):
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
        self.enemy_templates: Dict[str, EnemyShipTemplate] = {}
        self.journal_entries: List[JournalEntry] = []
        self.encounter_definitions: List[EncounterDefinition] = []
        self.ground_equipment: Dict[str, "GroundEquipment"] = {}
        self.contract_templates: Dict[str, dict] = {}
        self.campaign_ground_maps: Dict[str, dict] = {}
        self.faction_laws: Dict[str, "FactionLaw"] = {}
        self.locations: Dict[str, List[Location]] = {}
        self.investment_templates: Dict[str, InvestmentTemplate] = {}
        self.faction_relationships: list = []

    def load_all(self) -> None:
        """Load all game data from JSON files."""
        logger.info("Loading game data...")
        self.load_systems()
        self.load_commodities()
        self.load_ship_types()
        self.load_mining_configs()
        self.load_salvage_configs()
        self.load_recipes()
        self.load_upgrades()
        self.load_achievements()
        self.load_factions()
        self.load_npcs()
        self.load_dialogues()
        self.load_missions()
        self.load_crew_templates()
        self.load_enemy_templates()
        self.load_journal_entries()
        self.load_encounter_definitions()
        self.load_ground_equipment()
        self.load_contract_templates()
        self.load_campaign_maps()
        self.load_faction_laws()
        self.load_locations()
        self.load_investment_configs()
        self.load_politics()
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
            FactionRelationship.from_dict(rel_data)
            for rel_data in data.get("relationships", [])
        ]
        logger.info(
            f"Loaded {len(self.faction_relationships)} faction relationships"
        )
        return self.faction_relationships

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
            )
            self.npcs[npc.id] = npc

        logger.info(f"Loaded {len(self.npcs)} NPCs")
        return self.npcs

    def load_dialogues(self) -> Dict[str, DialogueTree]:
        """Load dialogue trees from JSON."""
        file_path = self.data_dir / "dialogue" / "dialogues.json"
        if not file_path.exists():
            logger.warning(f"Dialogues not found: {file_path}")
            return self.dialogue_trees

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.dialogue_trees.clear()
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
                    )
                )
            node = DialogueNode(
                id=node_data["id"],
                speaker_id=node_data["speaker_id"],
                text=node_data["text"],
                responses=responses,
                expression=node_data.get("expression"),
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
        """Load mission definitions from JSON."""
        file_path = self.data_dir / "missions" / "missions.json"
        if not file_path.exists():
            logger.warning(f"Missions not found: {file_path}")
            return self.missions

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.missions.clear()
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
            combat_move=data.get("combat_move"),
        )

    def get_crew_template(self, template_id: str) -> Optional[CrewTemplate]:
        """Get a crew template by ID, or None if not found."""
        return self.crew_templates.get(template_id)

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

    def _parse_enemy_template(self, data: dict) -> EnemyShipTemplate:
        """Parse an enemy ship template from raw JSON data."""
        moves = [
            self._parse_combat_move(m) for m in data.get("moves", [])
        ]
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
        """Load encounter definitions from JSON.

        Returns:
            List of loaded encounter definitions.
        """
        file_path = self.data_dir / "encounters" / "encounters.json"
        if not file_path.exists():
            logger.warning(f"Encounter definitions not found: {file_path}")
            return self.encounter_definitions

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.encounter_definitions.clear()
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
        choices = []
        for choice_data in data.get("choices", []):
            outcome_data = choice_data.get("outcome", {})
            rewards = [
                MissionReward(
                    reward_type=r["reward_type"],
                    amount=r["amount"],
                    target_id=r.get("target_id", ""),
                )
                for r in outcome_data.get("rewards", [])
            ]
            outcome = EncounterOutcome(
                description=outcome_data.get("description", ""),
                rewards=rewards,
                leads_to_combat=outcome_data.get("leads_to_combat", False),
            )
            choices.append(
                EncounterChoice(
                    id=choice_data["id"],
                    label=choice_data["label"],
                    description=choice_data.get("description", ""),
                    outcome=outcome,
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
    return _data_loader
