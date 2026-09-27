"""The schema tells Godot loaders which JSON numbers are ints (SP2 spec 7.5)."""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Optional

import pytest

from tools.parity.export_schema import build_schema, type_name


class TestSchema:
    def test_commodity_fields(self) -> None:
        commodity = build_schema()["types"]["Commodity"]  # type: ignore[index]
        assert commodity["base_price"] == "int"
        assert commodity["variance_min"] == "float"
        assert commodity["volume_per_unit"] == "int"
        assert commodity["category"] == "enum"
        assert commodity["production_tags"] == "list<str>"

    def test_nested_types(self) -> None:
        types = build_schema()["types"]  # type: ignore[index]
        assert types["StarSystem"]["economy"] == "Economy"
        assert types["StarSystem"]["stations"] == "list<Station>"
        assert types["StarSystem"]["rest_cost"] == "int"
        assert types["Economy"]["available_commodities"] == "optional<list<str>>"
        assert types["Coordinates"]["x"] == "float"

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError):
            type_name(complex)

    def test_optional_form(self) -> None:
        assert type_name(Optional[int]) == "optional<int>"


class _Tier(IntEnum):
    LOW = 1
    HIGH = 2


class _Colour(Enum):
    RED = "red"


class TestEnumKinds:
    def test_intenum_is_its_own_kind(self) -> None:
        assert type_name(_Tier) == "intenum"

    def test_string_enum_stays_enum(self) -> None:
        assert type_name(_Colour) == "enum"

    def test_commodity_category_is_still_enum(self) -> None:
        assert build_schema()["types"]["Commodity"]["category"] == "enum"  # type: ignore[index]
