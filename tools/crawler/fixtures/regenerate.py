"""Regenerate the three committed checkpoint save fixtures.

Run this whenever the save format changes (e.g. a save-schema refactor
lands under a Populist-B ticket). Produces three JSON files under
``tools/crawler/fixtures/``:

    save_slot_1.json  — "early"  (no ship built, in tutorial shop)
    save_slot_2.json  — "mid"    (mid-tier ship, ~50k credits, 3 systems)
    save_slot_3.json  — "late"   (end-tier ship, ~500k credits, all systems)

The crawler CLI's ``--checkpoint {early|mid|late}`` flag loads slot 1/2/3
respectively.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Headless SDL so pygame initialization is silent.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Ensure repo root is on sys.path when run directly.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from spacegame.data_loader import get_data_loader  # noqa: E402
from spacegame.models.player import Player  # noqa: E402
from spacegame.models.ship import Ship  # noqa: E402
from spacegame.save_manager import SaveManager  # noqa: E402


FIXTURES_DIR = _HERE


def _build_early_player() -> Player:
    dl = get_data_loader()
    dl.load_all()
    ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)
    player = Player(
        name="Crawler_Early",
        credits=250,
        current_system_id="nexus_prime",
        ship=ship,
        ship_name="Aurelia's Chance",
    )
    player.systems_visited = {"nexus_prime"}
    player.game_day = 1
    return player


def _build_mid_player() -> Player:
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types.get("medium_freighter") or dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Crawler_Mid",
        credits=50_000,
        current_system_id="nexus_prime",
        ship=ship,
        ship_name="Longhaul",
    )
    player.systems_visited = {"nexus_prime", "verdant", "forgeworks"}
    player.game_day = 40
    player.dialogue_flags["met_shift_supervisor"] = True
    player.dialogue_flags["completed_tutorial"] = True
    return player


def _build_late_player() -> Player:
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types.get("industrial_titan") or dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Crawler_Late",
        credits=500_000,
        current_system_id="nexus_prime",
        ship=ship,
        ship_name="Registrar",
    )
    all_systems = {s.id for s in dl.get_all_systems()}
    player.systems_visited = all_systems
    player.game_day = 220
    player.dialogue_flags["met_shift_supervisor"] = True
    player.dialogue_flags["completed_tutorial"] = True
    return player


def regenerate(output_dir: Path | None = None) -> list[Path]:
    """Write the three checkpoint save files.

    Args:
        output_dir: Optional override. Defaults to ``tools/crawler/fixtures``.

    Returns:
        List of Paths written.
    """
    target = output_dir or FIXTURES_DIR
    target.mkdir(parents=True, exist_ok=True)

    save_manager = SaveManager(save_directory=target)
    written: list[Path] = []

    for slot, factory, label in (
        (1, _build_early_player, "early"),
        (2, _build_mid_player, "mid"),
        (3, _build_late_player, "late"),
    ):
        player = factory()
        ok = save_manager.save_game(
            slot=slot,
            player=player,
            markets={},
            active_events={},
            playtime_seconds=0,
            save_name=f"crawler_{label}",
        )
        if not ok:
            raise RuntimeError(f"Failed to write checkpoint slot {slot} ({label})")
        written.append(save_manager.get_save_file_path(slot))

    return written


if __name__ == "__main__":
    paths = regenerate()
    for p in paths:
        print(f"Wrote {p}")
