"""Every save field of Player is classified, and snapshots sort set-backed lists (R9)."""

from __future__ import annotations

from spacegame.save_manager import SaveManager
from tools.parity.snapshots import (
    EXCLUDED_PLAYER_KEYS,
    MANAGER_OWNED_PLAYER_KEYS,
    WAVE_A_PLAYER_KEYS,
    fresh_player,
    player_snapshot,
)


def test_every_save_key_is_classified_once() -> None:
    keys = set(SaveManager()._serialize_player(fresh_player()))
    groups = [set(WAVE_A_PLAYER_KEYS), set(MANAGER_OWNED_PLAYER_KEYS), set(EXCLUDED_PLAYER_KEYS)]
    assert not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])
    unclassified = keys - set().union(*groups)
    stale = set().union(*groups) - keys
    assert not unclassified, f"classify these new Player save keys: {sorted(unclassified)}"
    assert not stale, f"these classified keys no longer exist: {sorted(stale)}"


def test_snapshot_sorts_set_backed_lists() -> None:
    player = fresh_player()
    for system_id in ("verdant", "axiom_labs", "nexus_prime"):
        player.systems_visited.add(system_id)
    snap = player_snapshot(player)
    assert snap["systems_visited"] == sorted(snap["systems_visited"])
    assert set(snap) == set(WAVE_A_PLAYER_KEYS)
