"""Player resource and payout goldens (SP3 spec 6.2)."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.combat import EnemyShip
from spacegame.models.player import Player
from tools.parity.driver import Case
from tools.parity.snapshots import fresh_player, player_snapshot


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
    case = Case("player", "trading", {"credits": 2000, "ship_type": "shuttle"})
    rec = _Recorder(case, fresh_player(credits=2000))
    volumes = _volumes()
    rec.call("buy_commodity", "food", 10, 50, volumes)
    rec.call("buy_commodity", "electronics", 5, 130, volumes)
    rec.call("buy_commodity", "art", 50, 600, volumes)  # unaffordable
    rec.call("buy_commodity", "iron_ore", 10_000, 1, volumes)  # unaffordable
    rec.call("sell_commodity", "food", 4, 70)
    rec.call("sell_commodity", "food", 40, 70)  # not held
    rec.call("refuel_ship", 5, 9)
    rec.call("refuel_ship", 500, 9)  # tank fills first
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
    case = Case("player", name, {"insured": insured})
    player = fresh_player(credits=3000)
    if insured:
        for node in player.progression.skills.values():
            if node.bonus_type == "insurance":
                node.current_level = node.max_level
    for commodity_id, qty in (("food", 20), ("electronics", 10), ("scrap_metal", 1)):
        player.ship.add_cargo(commodity_id, qty, 10)
    player.faction_assignments["nexus_prime"] = "commerce_guild"
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
    case = Case("player", "payouts", {"encounter_seed": 4242})
    rec = _Recorder(case, fresh_player(credits=0))
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
    return [_trading(), _defeat(False), _defeat(True), _payouts()]
