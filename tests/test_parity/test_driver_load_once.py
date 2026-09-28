"""Each golden driver reloads game data at most once per build.

A full ``DataLoader.load_all`` costs about 25 ms. A reload inside a per-case or per-step
helper made the encounters, combat, and missions builds take about 25 s together, which
pushed ``test_goldens_current`` toward the 120 s per-test timeout under ``-n auto``. Each
driver resets the loader once at the top of ``build_cases`` and its helpers read the
loaded singleton.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from spacegame.data_loader import DataLoader, get_data_loader
from tools.parity import regen
from tools.parity.driver import Case


def _driver_id(build: Callable[[], list[Case]]) -> str:
    return build.__module__.rsplit(".", 1)[-1]


@pytest.mark.parametrize("build", regen.DRIVERS, ids=_driver_id)
def test_build_cases_loads_data_at_most_once(
    build: Callable[[], list[Case]], monkeypatch: pytest.MonkeyPatch
) -> None:
    get_data_loader()  # the singleton's own first load is not the driver's
    calls: list[str] = []
    original = DataLoader.load_all

    def counting(self: DataLoader) -> None:
        calls.append("load_all")
        original(self)

    monkeypatch.setattr(DataLoader, "load_all", counting)
    build()
    assert len(calls) <= 1, (
        f"{_driver_id(build)} called load_all {len(calls)} times in one build; "
        "load once in build_cases and let helpers read get_data_loader()"
    )
