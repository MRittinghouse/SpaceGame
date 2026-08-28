"""Content data must not name asset files. Loading is the engine's job.

## Why this exists

A graphics and systems overhaul is coming, and it will likely change how
assets are produced, named, and organised. What decides whether that is a
one-file change or a content-wide migration is a single property: whether
authored content refers to assets by *logical identity* or by *file path*.

Measured when this test was written: **zero** file-path asset references
across all 75 JSON files under `data/`. Every `pygame.image.load` call lives
in `spacegame/engine/sprites.py`. The seam already exists and is clean.

This test protects it. Seven days of unattended agent authoring is exactly
when a `"portrait": "assets/npc/kallio.png"` slips in and nobody notices,
because it would work perfectly until the day the pipeline changes and then
break everywhere at once.

Content says `"portrait_id": "kallio"`. The engine decides what that means.
A future pipeline swaps its own resolution logic and touches no content.

Same enforcement shape as `test_prose_anti_patterns.py`: schema-agnostic,
walks every string in every data file, so new content types are covered the
day they are created.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

# Media extensions, and directory-ish prefixes that imply a filesystem layout.
_ASSET_EXTENSION = re.compile(r"\.(png|jpe?g|webp|gif|bmp|ogg|wav|mp3|ttf|otf)\b", re.I)
_ASSET_DIRECTORY = re.compile(r"\b(assets?|images?|sprites?|textures?|sounds?|fonts?)/", re.I)


def _strings(obj: object, path: str = "") -> Iterator[tuple[str, str]]:
    """Yield (json_path, value) for every string anywhere in a decoded document."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from _strings(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _strings(value, f"{path}[{index}]")


def _data_files() -> list[Path]:
    return sorted(DATA_DIR.rglob("*.json"))


def _violations(pattern: re.Pattern[str]) -> list[str]:
    errors: list[str] = []
    for path in _data_files():
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue  # test_prose_anti_patterns owns unreadable-file reporting
        for json_path, value in _strings(document):
            if pattern.search(value):
                errors.append(f"{path.relative_to(PROJECT_ROOT)}{json_path}: {value[:90]}")
    return errors


def test_data_corpus_is_present() -> None:
    """Guard the guard: both checks below pass vacuously on an empty glob."""
    assert len(_data_files()) >= 50, f"expected the full data corpus, found {len(_data_files())}"


def test_content_does_not_name_asset_files() -> None:
    """No `.png`, `.ogg`, `.ttf` and so on in authored content.

    Content references assets by logical id; the engine resolves ids to files.
    A file extension in content couples authored data to one pipeline layout.
    """
    errors = _violations(_ASSET_EXTENSION)
    assert not errors, (
        "content names asset FILES, which couples it to the current asset pipeline "
        "and would force a content-wide migration when that pipeline changes. Use a "
        "logical id and let the engine resolve it:\n" + "\n".join(errors)
    )


def test_content_does_not_encode_asset_directory_layout() -> None:
    """No `assets/`, `sprites/`, `sounds/` paths in authored content.

    Directory layout is a pipeline decision. Content that encodes it has to be
    rewritten whenever the layout moves.
    """
    errors = _violations(_ASSET_DIRECTORY)
    assert not errors, (
        "content encodes the asset DIRECTORY layout, which a pipeline change would "
        "invalidate everywhere at once:\n" + "\n".join(errors)
    )
