"""Every save field of Player is classified, and snapshots sort set-backed lists (R9)."""

from __future__ import annotations

import dataclasses

from spacegame.models.player import Player
from spacegame.save_manager import SaveManager
from tools.parity.snapshots import (
    EXCLUDED_PLAYER_KEYS,
    MANAGER_OWNED_PLAYER_KEYS,
    WAVE_A_PLAYER_KEYS,
    _SET_BACKED,
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
    for permit in (
        "zulu_permit",
        "yankee_permit",
        "xray_permit",
        "whiskey_permit",
        "victor_permit",
    ):
        player.trade_permits.add(permit)
    for system_id in (
        "zulu_market",
        "yankee_market",
        "xray_market",
        "whiskey_market",
        "victor_market",
    ):
        player.black_market_access.add(system_id)
    snap = player_snapshot(player)
    assert snap["systems_visited"] == sorted(snap["systems_visited"])
    assert snap["trade_permits"] == sorted(snap["trade_permits"])
    assert snap["black_market_access"] == sorted(snap["black_market_access"])
    assert set(snap) == set(WAVE_A_PLAYER_KEYS)


def test_set_backed_fields_are_declared_and_sorted() -> None:
    """Every set-typed Player field in wave A is sorted by player_snapshot (R9)."""
    set_fields = {
        f.name
        for f in dataclasses.fields(Player)
        if isinstance(getattr(fresh_player(), f.name), (set, frozenset))
    }
    assert set_fields & set(WAVE_A_PLAYER_KEYS) == set(_SET_BACKED)
