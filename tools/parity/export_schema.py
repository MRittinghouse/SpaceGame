"""Field types for the model types Godot loaders build (SP2 spec Section 7.5).

Godot parses every JSON number as a float; loaders cast by this schema.
SP3 extends ``TYPES`` as it ports more models.
"""

from __future__ import annotations

import dataclasses
import json
import types
from enum import Enum
from pathlib import Path
from typing import Union, get_args, get_origin, get_type_hints

from spacegame.models.commodity import Commodity
from spacegame.models.system import Coordinates, Economy, StarSystem, Station

TYPES: dict[str, type] = {
    "Commodity": Commodity,
    "Coordinates": Coordinates,
    "Economy": Economy,
    "StarSystem": StarSystem,
    "Station": Station,
}

_SCALARS: dict[object, str] = {int: "int", float: "float", str: "str", bool: "bool"}


def type_name(tp: object) -> str:
    """Render one annotation as a schema type string.

    Raises:
        TypeError: For annotations the schema cannot express.
    """
    if tp in _SCALARS:
        return _SCALARS[tp]
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is list:
        return f"list<{type_name(args[0])}>"
    if origin is dict:
        return f"dict<{type_name(args[0])},{type_name(args[1])}>"
    if origin in (Union, types.UnionType):
        members = [a for a in args if a is not type(None)]
        if len(members) == 1 and len(args) == 2:
            return f"optional<{type_name(members[0])}>"
    if isinstance(tp, type) and issubclass(tp, Enum):
        return "enum"
    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        return tp.__name__
    raise TypeError(f"schema cannot express {tp!r}")


def build_schema() -> dict[str, object]:
    """The schema document for every registered type."""
    out: dict[str, dict[str, str]] = {}
    for name, cls in TYPES.items():
        hints = get_type_hints(cls)
        out[name] = {f.name: type_name(hints[f.name]) for f in dataclasses.fields(cls)}
    return {"format": 1, "types": out}


def write_schema(path: Path) -> None:
    """Write the schema as sorted, two-space JSON with an LF ending."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(build_schema(), indent=2, sort_keys=True) + "\n")
