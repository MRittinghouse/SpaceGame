"""Injected SimRng makes each former global-stream site reproducible."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.event import EventGenerator
from spacegame.models.legendary_effects import process_chain_fire
from spacegame.sim_rng import SimRng, seed_entropy
from tests.sim_rng_helpers import ScriptedRng


class TestEventGenerator:
    def test_roll_below_chance_generates(self) -> None:
        gen = EventGenerator(["food", "fuel"], ["nexus_prime"], rng=ScriptedRng([0.0]))
        assert gen.try_generate_event(5, {"food": "Food", "fuel": "Fuel"}) is not None

    def test_roll_above_chance_skips(self) -> None:
        gen = EventGenerator(["food"], ["nexus_prime"], rng=ScriptedRng([1.0]))
        assert gen.try_generate_event(5, {"food": "Food"}) is None


class TestChainFire:
    def test_scripted_roll_triggers(self) -> None:
        from spacegame.models.legendary_effects import LegendaryState

        state = LegendaryState()
        state.chain_fire_chance = 0.5
        state.chain_fire_damage_mult = 0.4
        assert process_chain_fire(state, 10.0, rng=ScriptedRng([0.1])) == (True, 0.4)
        assert process_chain_fire(state, 10.0, rng=ScriptedRng([0.9])) == (False, 0.0)


class TestMiningField:
    def test_same_stream_same_field(self) -> None:
        from spacegame.models.mining import MiningSession

        config = next(iter(get_data_loader().mining_configs.values()))
        a = MiningSession(config, rng=SimRng.from_key("mine", 1))
        b = MiningSession(config, rng=SimRng.from_key("mine", 1))
        assert [(r.grid_x, r.grid_y, r.rock_type) for r in a.rocks] == [
            (r.grid_x, r.grid_y, r.rock_type) for r in b.rocks
        ]


class TestEntropyDefault:
    def test_seeded_entropy_reproduces_default_streams(self) -> None:
        seed_entropy(3)
        first = SimRng.from_entropy().next_u32()
        seed_entropy(3)
        second = SimRng.from_entropy().next_u32()
        seed_entropy(None)
        assert first == second
