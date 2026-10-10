"""Each surface that may carry the captain's tokens renders them where it prints its lines.

The registry (``tests/writing_gates/registry.py``) lets a data file carry the captain's tokens
only where the code that prints its lines fills them (writing discipline spec 2.7). This test
names that code: each function below calls ``captain_line``, and every registry entry that
allows the captain's tokens lists its functions here. Each surface's behavior is tested with its
view or model; this test keeps a renamed or rewritten print path from dropping the call unseen.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.writing_gates.registry import CAPTAIN_TOKENS, REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[2]

# Registry file glob -> (module, "Class.method" or "function") of every print path.
SURFACE_SITES: dict[str, tuple[tuple[str, str], ...]] = {
    "data/dialogue/*.json": (
        ("spacegame/views/dialogue_view.py", "DialogueView._load_current_node"),
        ("spacegame/views/dialogue_view.py", "DialogueView._build_response_buttons"),
        ("spacegame/views/dialogue_view.py", "DialogueView._subtext_line"),
        ("spacegame/views/deep_shafts_view.py", "DeepShaftsView._render_dialogue_panel"),
        ("spacegame/views/okafor_view.py", "OkaforView._render_dialogue_panel"),
        ("spacegame/views/wreckers_guild_view.py", "WreckersGuildView._render_contact_dialogue"),
    ),
    "data/combat/crew_interjections.json": (
        ("spacegame/views/combat_view.py", "CombatView._surface_interjection"),
    ),
    "data/combat/captains.json": (
        ("spacegame/views/encounter_view.py", "EncounterView.__init__"),
        ("spacegame/views/combat_view.py", "CombatView._maybe_surface_captain_outcome_line"),
    ),
    "data/combat/captain_variants.json": (
        ("spacegame/views/encounter_view.py", "EncounterView.__init__"),
        ("spacegame/views/combat_view.py", "CombatView._maybe_surface_captain_outcome_line"),
    ),
    "data/encounters/*.json": (
        ("spacegame/views/encounter_view.py", "EncounterView.__init__"),
        ("spacegame/views/encounter_view.py", "_substitute_choices"),
    ),
    "data/crew/ambient_dialogue.json": (
        ("spacegame/engine/game.py", "Game._next_mission_notification"),
        ("spacegame/engine/game.py", "Game._make_crew_commentary_fn"),
    ),
    "data/crew/station_chatter.json": (
        ("spacegame/views/station_hub_view.py", "StationHubView.on_enter"),
    ),
    "data/economy/news_templates.json": (
        ("spacegame/views/galaxy_map_view.py", "GalaxyMapView._ticker_headlines"),
    ),
}


def _function(file: str, dotted: str) -> ast.FunctionDef | None:
    """The definition of ``Class.method`` (or a module-level function) in a module."""
    scope = ast.parse((REPO_ROOT / file).read_text(encoding="utf-8")).body
    *classes, name = dotted.split(".")
    for class_name in classes:
        found = [
            node for node in scope if isinstance(node, ast.ClassDef) and node.name == class_name
        ]
        if not found:
            return None
        scope = found[0].body
    for node in scope:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _calls_captain_line(function: ast.FunctionDef) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "captain_line"
        for node in ast.walk(function)
    )


def test_every_print_path_renders_the_captains_tokens() -> None:
    missing: list[str] = []
    for sites in SURFACE_SITES.values():
        for file, dotted in sites:
            function = _function(file, dotted)
            if function is None:
                missing.append(f"{file}: no {dotted}")
            elif not _calls_captain_line(function):
                missing.append(f"{file}: {dotted} does not call captain_line")
    assert not missing, "\n".join(missing)


def test_every_captain_token_surface_names_its_print_paths() -> None:
    surfaces = {entry.files for entry in REGISTRY if CAPTAIN_TOKENS <= entry.tokens}
    assert surfaces == set(SURFACE_SITES)
