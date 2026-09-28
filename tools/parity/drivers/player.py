"""Player resource and payout goldens (SP3 spec 6.2)."""

from __future__ import annotations

from typing import Any

from spacegame.data_loader import get_data_loader
from spacegame.models.combat import EnemyShip
from spacegame.models.player import Player
from tools.parity.driver import Case
from tools.parity.snapshots import fresh_player, player_snapshot

_PILOT: dict[str, Any] = {
    "name": "ParityPilot",
    "system_id": "nexus_prime",
    "ship_type": "shuttle",
    "fuel": 40,
}


def _pilot(credits: int) -> dict[str, Any]:
    """The five fresh_player parameters, with credits set per case."""
    return {**_PILOT, "credits": credits}


def _build_player(setup: dict[str, Any]) -> Player:
    """Construct a Player from a setup dict's "player" field, plus synced data only."""
    fields = setup["player"]
    return fresh_player(
        name=fields["name"],
        credits=fields["credits"],
        system_id=fields["system_id"],
        ship_type_id=fields["ship_type"],
        fuel=fields["fuel"],
    )


def _max_skill(player: Player, bonus_type: str) -> None:
    for node in player.progression.skills.values():
        if node.bonus_type == bonus_type:
            node.current_level = node.max_level


def _plain_args(args: tuple[object, ...]) -> list[object]:
    """Replace any list of ``EnemyShip`` with plain, JSON-ready dicts.

    ``EnemyShip`` instances are not JSON: the golden holds template ids plus the
    ``dead``/``fled`` flags the Godot adapter needs to rebuild them.
    """
    out: list[object] = []
    for arg in args:
        if isinstance(arg, list) and arg and isinstance(arg[0], EnemyShip):
            out.append(
                [
                    {"template_id": e.template.id, "dead": not e.is_alive, "fled": e.is_fled}
                    for e in arg
                ]
            )
        else:
            out.append(arg)
    return out


class _Recorder:
    def __init__(self, case: Case, player: Player) -> None:
        self.case = case
        self.player = player

    def call(self, name: str, *args: object) -> object:
        result = getattr(self.player, name)(*args)
        if hasattr(result, "__dataclass_fields__"):
            import dataclasses

            result = dataclasses.asdict(result)
        self.case.record(name, _plain_args(args), result, player_snapshot(self.player))
        return result


def _volumes() -> dict[str, int]:
    return {cid: c.volume_per_unit for cid, c in get_data_loader().commodities.items()}


def _trading() -> Case:
    setup: dict[str, Any] = {"player": _pilot(2000)}
    case = Case("player", "trading", setup)
    rec = _Recorder(case, _build_player(setup))
    volumes = _volumes()
    rec.call("buy_commodity", "food", 10, 50, volumes)
    rec.call("buy_commodity", "electronics", 5, 130, volumes)
    rec.call("buy_commodity", "art", 50, 600, volumes)  # unaffordable
    rec.call("buy_commodity", "iron_ore", 100, 1, volumes)  # no room
    rec.call("sell_commodity", "food", 4, 70)
    rec.call("sell_commodity", "food", 40, 70)  # not held
    rec.call("refuel_ship", 5, 9)
    rec.call("refuel_ship", 500, 9)  # unaffordable
    rec.call("refuel_ship", 80, 9)  # tank fills first
    rec.call("add_credits", 250)
    rec.call("deduct_credits", 100)
    rec.call("deduct_credits", 1_000_000)
    rec.call("modify_reputation", "commerce_guild", 70)
    rec.call("modify_reputation", "commerce_guild", 70)  # clamps at 100
    rec.call("add_criminal_heat", 12)
    rec.call("decay_criminal_heat", 5)
    rec.call("grant_trade_permit", "frontier_alliance")
    return case


def _defeat(insured: bool) -> Case:
    name = "defeat_insured" if insured else "defeat"
    setup: dict[str, Any] = {
        "insured": insured,
        "player": _pilot(3000),
        "max_level_bonus_types": ["insurance"] if insured else [],
        "cargo": [
            {"commodity_id": "food", "quantity": 20, "price": 10},
            {"commodity_id": "electronics", "quantity": 10, "price": 10},
            {"commodity_id": "scrap_metal", "quantity": 1, "price": 10},
        ],
        "faction_assignments": {"nexus_prime": "commerce_guild"},
    }
    case = Case("player", name, setup)
    player = _build_player(setup)
    for bonus_type in setup["max_level_bonus_types"]:
        _max_skill(player, bonus_type)
    for entry in setup["cargo"]:
        player.ship.add_cargo(entry["commodity_id"], entry["quantity"], entry["price"])
    for system_id, faction in setup["faction_assignments"].items():
        player.faction_assignments[system_id] = faction
    rec = _Recorder(case, player)
    rec.call("apply_combat_defeat", "nexus_prime")
    return case


def _enemy(template_id: str, *, dead: bool = False, fled: bool = False) -> EnemyShip:
    enemy = EnemyShip.from_template(get_data_loader().enemy_templates[template_id])
    if dead:
        enemy.current_hull = 0
    enemy.is_fled = fled
    return enemy


def _payouts() -> Case:
    setup: dict[str, Any] = {"player": _pilot(0), "encounter_seed": 4242}
    case = Case("player", "payouts", setup)
    rec = _Recorder(case, _build_player(setup))
    enemies = [
        _enemy("pirate_raider", dead=True),
        _enemy("pirate_scout", fled=True),
        _enemy("pirate_heavy", dead=True),
    ]
    rec.call("apply_combat_victory", enemies, 4242)
    rec.call("apply_combat_negotiated", [_enemy("union_brawler")], 4242, True)
    rec.call("apply_combat_negotiated", [_enemy("union_brawler")], 4242, False)
    return case


def build_cases() -> list[Case]:
    """Every player case."""
    get_data_loader().load_all()
    return [_trading(), _defeat(False), _defeat(True), _payouts()]
