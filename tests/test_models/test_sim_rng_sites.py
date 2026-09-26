"""Keyed SimRng sites and cross-process determinism (SP2 spec Section 4)."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from spacegame.data_loader import get_data_loader
from spacegame.models.market import Market
from spacegame.sim_rng import SimRng

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_in_fresh_process(snippet: str, hash_seed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    done = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(snippet)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return done.stdout


class TestMarketKey:
    def test_variance_uses_the_market_stream(self) -> None:
        loader = get_data_loader()
        system = loader.systems["nexus_prime"]
        market = Market(system, list(loader.commodities.values()), game_day=4)
        commodity = next(iter(market.commodities.values()))
        span = abs(commodity.variance_max - commodity.variance_min)
        max_random = min(0.10, span * 0.2)
        expected = SimRng.from_key("market", 4, commodity.id, "nexus_prime").uniform(
            -max_random, max_random
        )
        assert market._get_random_variance(commodity) == expected


class TestCrossProcess:
    def test_procedural_missions_identical_across_hash_seeds(self) -> None:
        snippet = """
            import logging
            logging.disable(logging.CRITICAL)  # keep timestamped log lines out of stdout
            from spacegame.data_loader import get_data_loader
            from spacegame.models.procedural_missions import ProceduralMissionGenerator
            dl = get_data_loader()
            gen = ProceduralMissionGenerator(
                systems=dl.systems, commodities=dl.commodities,
                enemy_templates=dl.enemy_templates, seed=12345,
            )
            for m in gen.generate_for_system("nexus_prime", 7):
                print(m.id, m.name)
        """
        first = _run_in_fresh_process(snippet, "1")
        second = _run_in_fresh_process(snippet, "2")
        assert first, "the generator should produce missions for nexus_prime on day 7"
        assert first == second, "procedural missions must not depend on PYTHONHASHSEED"

    def test_stable_seed_identical_across_hash_seeds(self) -> None:
        snippet = """
            from spacegame.sim_rng import stable_seed
            print(stable_seed("player", "Ada"), stable_seed("enemy", "pirate_raider"))
        """
        assert _run_in_fresh_process(snippet, "1") == _run_in_fresh_process(snippet, "2")
