"""Shared helpers for QA Pass 3 integration scenarios.

Scenarios exercise full player journeys across multiple subsystems with real
models. Rendering and UI are bypassed; all business logic is real.

Design notes:
  - DataLoader is the real singleton (cached between tests).
  - Player is constructed fresh per scenario.
  - No god-object Scenario class; just factory functions + helpers.
  - When a scenario needs combat state, it calls the real
    ``build_player_combat_state`` — no mocks.
"""

from __future__ import annotations

import json

from spacegame.data_loader import get_data_loader
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType
from spacegame.save_manager import SaveManager


def real_ship_type(ship_type_id: str = "shuttle") -> ShipType:
    """Return a real ShipType from DataLoader.

    Defaults to the starting shuttle. Other useful IDs: ``frigate``,
    ``cruiser``, ``hauler``. See ``data/ships/ship_types.json``.
    """
    dl = get_data_loader()
    dl.load_all()
    if ship_type_id not in dl.ship_types:
        raise ValueError(f"ship_type '{ship_type_id}' not found")
    return dl.ship_types[ship_type_id]


def fresh_player(
    *,
    name: str = "TestPilot",
    credits: int = 10000,
    system_id: str = "nexus_prime",
    ship_type_id: str = "shuttle",
    fuel: int = 40,
) -> Player:
    """Create a realistic starting Player with a ShipType-only ship (legacy path).

    For the ShipBuild path, call :func:`attach_build` on the returned player.
    """
    ship_type = real_ship_type(ship_type_id)
    ship = Ship(ship_type=ship_type, current_fuel=fuel)
    return Player(
        name=name,
        credits=credits,
        current_system_id=system_id,
        ship=ship,
    )


def attach_build(player: Player, *, weight_class: str = "small") -> None:
    """Attach a minimal ShipBuild to ``player.ship`` — forces the build-derived
    combat path. ``player.ship.computed_stats`` will become non-None.

    The build is deliberately tiny (a few pixels + no slots). Scenarios that
    need combat-capable builds should construct richer builds inline.
    """
    from spacegame.models.ship_build import PlacedPixel, ShipBuild

    build = ShipBuild(
        weight_class=weight_class,
        pixels=[PlacedPixel(x, y, "module_hull_rk") for x in range(4) for y in range(4)],
    )
    player.ship.set_build(build, full_heal=True)


def round_trip_save(player: Player) -> Player:
    """Serialize + deserialize a Player through SaveManager, returning the restored instance.

    Uses the private ``_serialize_player`` / ``_deserialize_player`` hooks so
    scenarios can exercise save/load fidelity without writing disk files.
    """
    mgr = SaveManager()
    data = mgr._serialize_player(player)
    json_str = json.dumps(data)  # Catches set/tuple issues the raw dict hides
    restored = json.loads(json_str)
    return mgr._deserialize_player(restored)


def real_enemy(template_id: str):
    """Return a real EnemyShip instance from a template (runtime combat state ready).

    See ``data/combat/enemies.json`` for template IDs. Useful ones:
      - pirate_scout (small, subs=[engine, sensor_array])
      - pirate_raider (medium, subs=[weapon_array, engine])
      - guild_dreadnought (mid-boss, subs=[weapon_array, engine, reactor])
      - pirate_lord (legendary, subs=[weapon_array, engine, reactor, cockpit])
    """
    from spacegame.models.combat import EnemyShip

    dl = get_data_loader()
    dl.load_all()
    template = dl.enemy_templates.get(template_id)
    if template is None:
        raise ValueError(f"enemy template '{template_id}' not found")
    return EnemyShip.from_template(template)
