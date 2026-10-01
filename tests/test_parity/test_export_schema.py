"""The schema tells Godot loaders which JSON numbers are ints (SP2 spec 7.5)."""

from __future__ import annotations

from enum import Enum, IntEnum, IntFlag, StrEnum
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
        assert types["StarSystem"]["faction_id"] == "str"
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


class _IntValued(Enum):
    LOW = 1
    HIGH = 2


class _Mixed(int, Enum):
    LOW = 1
    HIGH = 2


class _Flags(IntFlag):
    READ = 1
    WRITE = 2


class _StrMixed(str, Enum):
    RED = "red"


class _StrTier(StrEnum):
    RED = "red"


class TestEnumKinds:
    def test_intenum_is_its_own_kind(self) -> None:
        assert type_name(_Tier) == "intenum"

    def test_string_enum_stays_enum(self) -> None:
        assert type_name(_Colour) == "enum"

    def test_commodity_category_is_still_enum(self) -> None:
        assert build_schema()["types"]["Commodity"]["category"] == "enum"  # type: ignore[index]

    def test_commodity_legality_is_still_enum(self) -> None:
        assert build_schema()["types"]["Commodity"]["legality"] == "enum"  # type: ignore[index]

    def test_plain_enum_with_int_values_raises(self) -> None:
        with pytest.raises(TypeError):
            type_name(_IntValued)

    def test_int_enum_mixin_that_is_not_intenum_raises(self) -> None:
        with pytest.raises(TypeError):
            type_name(_Mixed)

    def test_intflag_raises(self) -> None:
        # In Python 3.11+, IntFlag does not subclass IntEnum, so it falls through
        # to the generic Enum branch; its int-valued members must raise, not
        # silently become "enum" or "intenum".
        assert not issubclass(_Flags, IntEnum)
        with pytest.raises(TypeError):
            type_name(_Flags)

    def test_str_enum_mixin_stays_enum(self) -> None:
        assert type_name(_StrMixed) == "enum"

    def test_strenum_stays_enum(self) -> None:
        assert type_name(_StrTier) == "enum"
