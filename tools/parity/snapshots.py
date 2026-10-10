"""The player state goldens compare (SP3 spec 6.2, ruling R9).

Python keeps no Player.to_dict(); the save manager's serializer is the full state. Its keys
fall into three groups: wave A keys the port holds and the goldens compare; keys owned by a
manager with its own goldens (missions, crew, social, attributes), which game.py copies onto
the player only at save time; and wave B or Act II keys the port does not hold yet. The
classification test fails on any key in none of the groups.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.save_manager import SaveManager

WAVE_A_PLAYER_KEYS: tuple[str, ...] = (
    "name",
    "ship_name",
    "pronouns",
    "credits",
    "current_system_id",
    "previous_system_id",
    "game_day",
    "ship",
    "progression",
    "upgrades",
    "trades_completed",
    "total_profit",
    "systems_visited",
    "credits_earned_lifetime",
    "credits_spent_lifetime",
    "largest_single_profit",
    "jumps_traveled",
    "fuel_consumed",
    "max_credits_held",
    "faction_reputation",
    "faction_assignments",
    "dialogue_flags",
    "captain_memory",
    "trade_permits",
    "black_market_access",
    "criminal_heat",
    "times_caught_smuggling",
    "combats_won",
    "combats_fled",
    "combats_negotiated",
    "combats_bribed",
    "side_missions_completed",
    "crew_quests_completed",
    "encounters_survived",
    "trade_profit_total",
    "price_memory",
)
MANAGER_OWNED_PLAYER_KEYS: tuple[str, ...] = (
    "mission_state",
    "crew_state",
    "social_state",
    "attribute_state",
)
EXCLUDED_PLAYER_KEYS: tuple[str, ...] = (
    "ore_mined",
    "items_salvaged",
    "items_refined",
    "unlocked_achievements",
    "max_mining_depth",
    "total_chains_triggered",
    "rare_ores_mined",
    "salvage_sessions_completed",
    "corrupted_items_extracted",
    "refining_jobs_completed",
    "batch_jobs_queued",
    "recipes_crafted",
    "investments_owned",
    "s_ranks_earned",
    "best_mining_session_ore",
    "best_mining_depth",
    "best_trade_profit",
    "best_salvage_haul",
    "best_refining_output",
    "drone_fleet",
    "sub_reputation",
    "lens_investment",
    "dilemma_state",
    "capstones_reached",
    "wreckers_guild_state",
    "deep_shafts_state",
    "okafor_research_state",
    "auction_state",
    "futures_state",
    "timed_thread_state",
    "last_interaction_day",
    "journal_state",
    "ground_equipment",
    "parts_inventory",
    "hidden_compartment",
    "smuggling_contract_state",
    "ground_contract_state",
    "political_state",
    "politics_dispute_state",
    "goods_smuggled",
    "smuggling_contracts_completed",
    "inspections_passed_with_contraband",
    "max_criminal_heat_reached",
    "ground_missions_completed",
    "ground_missions_failed",
    "ground_enemies_defeated",
    "ground_enemies_talked",
    "ground_tiles_explored",
    "ground_undetected_completions",
    "ground_campaign_missions_completed",
    "strata_tokens",
    "mining_prestige_level",
    "deep_core_upgrades",
    "ore_silo_manager",
    "mining_depth_per_system",
    "prestige_hint_shown",
    "salvage_intel",
    "salvage_prestige_level",
    "wreck_upgrades",
    "salvage_hold_manager",
    "max_salvage_deck",
    "forge_tokens",
    "forge_upgrades",
    "forge_buffer_manager",
    "recipe_mastery",
    "discovered_recipes",
    "discovered_combos",
    "unlocked_shapes",
    "unlocked_materials",
    "unlocked_weight_classes",
    "unlocked_modules",
    "player_presets",
    "build_drafts",
)
_SET_BACKED = ("systems_visited", "trade_permits", "black_market_access")


def fresh_player(
    *,
    name: str = "ParityPilot",
    credits: int = 10000,
    system_id: str = "nexus_prime",
    ship_type_id: str = "shuttle",
    fuel: int = 40,
) -> Player:
    """A starting Player on the ship-type path (twin of tests/test_scenarios/_helpers)."""
    dl = get_data_loader()
    ship = Ship(ship_type=dl.ship_types[ship_type_id], current_fuel=fuel)
    return Player(name=name, credits=credits, current_system_id=system_id, ship=ship)


def player_snapshot(player: Player) -> dict[str, object]:
    """The wave A part of the player's save data, with set-backed lists sorted."""
    raw = SaveManager()._serialize_player(player)
    snap = {key: raw[key] for key in WAVE_A_PLAYER_KEYS}
    for key in _SET_BACKED:
        snap[key] = sorted(snap[key])  # type: ignore[call-overload]
    return snap
