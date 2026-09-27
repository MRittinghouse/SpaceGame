"""Combat victory rewards and loot rolls (SP3 spec 6.1)."""

from __future__ import annotations

from spacegame.models.combat_rewards import loot_rng, roll_loot
from spacegame.sim_rng import SimRng
from tests.test_scenarios._helpers import fresh_player, real_enemy

TABLE = [
    {"commodity_id": "scrap_metal", "min_qty": 2, "max_qty": 6, "chance": 1.0},
    {"commodity_id": "electronics", "min_qty": 1, "max_qty": 3, "chance": 0.0},
]


class TestRollLoot:
    def test_guaranteed_and_impossible_drops(self) -> None:
        loot = roll_loot(TABLE, SimRng.from_key("t", 1))
        assert "electronics" not in loot
        assert 2 <= loot["scrap_metal"] <= 6

    def test_same_key_same_loot(self) -> None:
        a = roll_loot(TABLE, loot_rng(42, "pirate_scout", rare=False))
        b = roll_loot(TABLE, loot_rng(42, "pirate_scout", rare=False))
        assert a == b

    def test_rare_stream_differs_from_common(self) -> None:
        common = loot_rng(42, "pirate_scout", rare=False).state()
        rare = loot_rng(42, "pirate_scout", rare=True).state()
        assert common != rare


class TestVictory:
    def test_xp_counts_every_enemy_credits_and_loot_only_the_dead(self) -> None:
        player = fresh_player(credits=0)
        dead, fled = real_enemy("pirate_scout"), real_enemy("pirate_scout")
        dead.current_hull = 0
        fled.is_fled = True
        victory = player.apply_combat_victory([dead, fled], encounter_seed=9)
        assert victory.xp == dead.template.xp_reward * 2
        assert victory.credits == dead.template.credit_reward
        assert player.credits == dead.template.credit_reward
        assert player.combats_won == 1
        assert victory.loot, "the dead scout must roll loot at seed 9"
        for cid, qty in victory.loot.items():
            assert player.ship.get_cargo_quantity(cid) == qty

    def test_negotiated_halves_loot_and_counts(self) -> None:
        player = fresh_player()
        enemy = real_enemy("pirate_raider")
        loot = player.apply_combat_negotiated([enemy], encounter_seed=9, partial_loot=True)
        full = roll_loot(enemy.template.loot_table, loot_rng(9, enemy.template.id, rare=False))
        assert full, "seed 9 must roll pirate_raider loot, or the halving check proves nothing"
        assert loot == {cid: max(1, qty // 2) for cid, qty in full.items()}
        for cid, qty in loot.items():
            assert player.ship.get_cargo_quantity(cid) == qty, (
                f"negotiated {cid} must reach the hold"
            )
        assert (player.combats_won, player.combats_negotiated) == (1, 1)

    def test_plain_negotiation_counts_but_pays_no_loot(self) -> None:
        player = fresh_player()
        enemy = real_enemy("pirate_raider")
        # The same fight with partial loot would pay out, so an empty result here is the
        # partial_loot guard and not an empty roll.
        assert roll_loot(enemy.template.loot_table, loot_rng(9, enemy.template.id, rare=False))
        loot = player.apply_combat_negotiated([enemy], encounter_seed=9, partial_loot=False)
        assert loot == {}
        for entry in enemy.template.loot_table:
            assert player.ship.get_cargo_quantity(entry["commodity_id"]) == 0
        assert (player.combats_won, player.combats_negotiated) == (1, 1)

    def test_preview_and_payout_draw_the_same_loot(self) -> None:
        enemy = real_enemy("pirate_raider")
        enemy.current_hull = 0
        preview = roll_loot(enemy.template.loot_table, loot_rng(77, enemy.template.id, False))
        player = fresh_player()
        victory = player.apply_combat_victory([enemy], encounter_seed=77)
        rare = roll_loot(enemy.template.rare_loot, loot_rng(77, enemy.template.id, True))
        expected = dict(preview)
        for cid, qty in rare.items():
            expected[cid] = expected.get(cid, 0) + qty
        assert victory.loot == expected
