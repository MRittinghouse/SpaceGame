"""Tests for the attribute system model."""

from spacegame.models.attributes import (
    AttributeId,
    AttributeSheet,
    ATTRIBUTE_DEFINITIONS,
    ATTRIBUTE_MAX,
    MILESTONE_DEFINITIONS,
)


class TestAttributeId:
    """Tests for the AttributeId enum."""

    def test_five_attributes_exist(self) -> None:
        assert len(AttributeId) == 5

    def test_attribute_ids(self) -> None:
        assert AttributeId.COM.value == "com"
        assert AttributeId.ACU.value == "acu"
        assert AttributeId.RES.value == "res"
        assert AttributeId.ING.value == "ing"
        assert AttributeId.SYN.value == "syn"

    def test_all_attributes_have_definitions(self) -> None:
        for attr in AttributeId:
            assert attr.value in ATTRIBUTE_DEFINITIONS, f"{attr} missing from definitions"
            defn = ATTRIBUTE_DEFINITIONS[attr.value]
            assert "name" in defn
            assert "description" in defn


class TestAttributeSheetCreation:
    """Tests for AttributeSheet initialization."""

    def test_default_creation(self) -> None:
        sheet = AttributeSheet()
        for attr in AttributeId:
            assert sheet.get_value(attr.value) == 1, f"{attr} should default to 1"
        assert sheet.unspent_points == 0

    def test_creation_with_points(self) -> None:
        sheet = AttributeSheet(unspent_points=5)
        assert sheet.unspent_points == 5
        for attr in AttributeId:
            assert sheet.get_value(attr.value) == 1

    def test_creation_with_custom_values(self) -> None:
        values = {"com": 3, "acu": 2, "res": 1, "ing": 1, "syn": 1}
        sheet = AttributeSheet(values=values)
        assert sheet.get_value("com") == 3
        assert sheet.get_value("acu") == 2

    def test_unknown_attribute_returns_zero(self) -> None:
        sheet = AttributeSheet()
        assert sheet.get_value("nonexistent") == 0


class TestAttributeAllocation:
    """Tests for allocating attribute points."""

    def test_allocate_point_success(self) -> None:
        sheet = AttributeSheet(unspent_points=3)
        success, msg = sheet.allocate_point("com")
        assert success, f"Allocation should succeed: {msg}"
        assert sheet.get_value("com") == 2
        assert sheet.unspent_points == 2

    def test_allocate_multiple_to_same(self) -> None:
        sheet = AttributeSheet(unspent_points=3)
        sheet.allocate_point("com")
        sheet.allocate_point("com")
        sheet.allocate_point("com")
        assert sheet.get_value("com") == 4
        assert sheet.unspent_points == 0

    def test_allocate_no_points_available(self) -> None:
        sheet = AttributeSheet(unspent_points=0)
        success, msg = sheet.allocate_point("com")
        assert not success
        assert sheet.get_value("com") == 1

    def test_allocate_at_max(self) -> None:
        values = {"com": ATTRIBUTE_MAX, "acu": 1, "res": 1, "ing": 1, "syn": 1}
        sheet = AttributeSheet(values=values, unspent_points=5)
        success, msg = sheet.allocate_point("com")
        assert not success
        assert sheet.get_value("com") == ATTRIBUTE_MAX

    def test_allocate_unknown_attribute(self) -> None:
        sheet = AttributeSheet(unspent_points=5)
        success, msg = sheet.allocate_point("nonexistent")
        assert not success

    def test_deallocate_point_success(self) -> None:
        values = {"com": 3, "acu": 1, "res": 1, "ing": 1, "syn": 1}
        sheet = AttributeSheet(values=values, unspent_points=0)
        success, msg = sheet.deallocate_point("com")
        assert success
        assert sheet.get_value("com") == 2
        assert sheet.unspent_points == 1

    def test_deallocate_at_minimum(self) -> None:
        sheet = AttributeSheet(unspent_points=0)
        success, msg = sheet.deallocate_point("com")
        assert not success
        assert sheet.get_value("com") == 1


class TestAttributePoints:
    """Tests for adding points and milestones."""

    def test_add_points(self) -> None:
        sheet = AttributeSheet()
        sheet.add_points(3)
        assert sheet.unspent_points == 3

    def test_award_milestone_success(self) -> None:
        sheet = AttributeSheet()
        success, msg = sheet.award_milestone("first_trade")
        assert success
        assert sheet.unspent_points == 1

    def test_award_milestone_only_once(self) -> None:
        sheet = AttributeSheet()
        sheet.award_milestone("first_trade")
        success, msg = sheet.award_milestone("first_trade")
        assert not success
        assert sheet.unspent_points == 1  # Still 1, not 2

    def test_award_unknown_milestone(self) -> None:
        sheet = AttributeSheet()
        success, msg = sheet.award_milestone("nonexistent_milestone")
        assert not success
        assert sheet.unspent_points == 0

    def test_all_milestones_can_be_awarded(self) -> None:
        sheet = AttributeSheet()
        for milestone_id in MILESTONE_DEFINITIONS:
            success, msg = sheet.award_milestone(milestone_id)
            assert success, f"Milestone {milestone_id} should be awardable"
        assert sheet.unspent_points == len(MILESTONE_DEFINITIONS)

    def test_milestone_tracking(self) -> None:
        sheet = AttributeSheet()
        assert not sheet.has_milestone("first_trade")
        sheet.award_milestone("first_trade")
        assert sheet.has_milestone("first_trade")


class TestAttributeModifiers:
    """Tests for attribute modifiers and bonuses."""

    def test_get_modifier_base(self) -> None:
        sheet = AttributeSheet()
        # All at 1, modifier = value - 1 = 0
        assert sheet.get_modifier("com") == 0

    def test_get_modifier_higher(self) -> None:
        values = {"com": 4, "acu": 1, "res": 1, "ing": 1, "syn": 1}
        sheet = AttributeSheet(values=values)
        assert sheet.get_modifier("com") == 3

    def test_synergy_social_bonus_low(self) -> None:
        sheet = AttributeSheet()
        # SYN = 1, bonus = 1 // 2 = 0
        assert sheet.get_synergy_social_bonus() == 0

    def test_synergy_social_bonus_mid(self) -> None:
        values = {"com": 1, "acu": 1, "res": 1, "ing": 1, "syn": 3}
        sheet = AttributeSheet(values=values)
        # SYN = 3, bonus = 3 // 2 = 1
        assert sheet.get_synergy_social_bonus() == 1

    def test_synergy_social_bonus_high(self) -> None:
        values = {"com": 1, "acu": 1, "res": 1, "ing": 1, "syn": 6}
        sheet = AttributeSheet(values=values)
        # SYN = 6, bonus = 6 // 2 = 3
        assert sheet.get_synergy_social_bonus() == 3

    def test_get_bonus_buy_price(self) -> None:
        values = {"com": 3, "acu": 1, "res": 1, "ing": 1, "syn": 1}
        sheet = AttributeSheet(values=values)
        # COM = 3, modifier = 2, bonus = 2 * 0.005 = 0.01
        bonus = sheet.get_bonus("buy_price_attr_reduction")
        assert abs(bonus - 0.01) < 1e-9

    def test_get_bonus_sell_price(self) -> None:
        values = {"com": 3, "acu": 1, "res": 1, "ing": 1, "syn": 1}
        sheet = AttributeSheet(values=values)
        bonus = sheet.get_bonus("sell_price_attr_bonus")
        assert abs(bonus - 0.01) < 1e-9

    def test_get_bonus_unknown_type(self) -> None:
        sheet = AttributeSheet()
        assert sheet.get_bonus("nonexistent_bonus") == 0.0

    def test_get_bonus_at_base(self) -> None:
        sheet = AttributeSheet()
        # All at 1, modifier = 0, all bonuses = 0
        assert sheet.get_bonus("buy_price_attr_reduction") == 0.0
        assert sheet.get_bonus("mining_power_attr") == 0.0


class TestAttributeSheetSerialization:
    """Tests for to_dict / from_dict."""

    def test_to_dict(self) -> None:
        values = {"com": 3, "acu": 2, "res": 1, "ing": 1, "syn": 4}
        sheet = AttributeSheet(values=values, unspent_points=2)
        sheet.award_milestone("first_trade")
        data = sheet.to_dict()

        assert data["values"]["com"] == 3
        assert data["values"]["syn"] == 4
        assert data["unspent_points"] == 3  # 2 + 1 from milestone
        assert "first_trade" in data["awarded_milestones"]

    def test_from_dict(self) -> None:
        data = {
            "values": {"com": 3, "acu": 2, "res": 1, "ing": 1, "syn": 4},
            "unspent_points": 2,
            "awarded_milestones": ["first_trade"],
        }
        sheet = AttributeSheet.from_dict(data)
        assert sheet.get_value("com") == 3
        assert sheet.get_value("syn") == 4
        assert sheet.unspent_points == 2
        assert sheet.has_milestone("first_trade")

    def test_round_trip(self) -> None:
        sheet = AttributeSheet(unspent_points=5)
        sheet.allocate_point("com")
        sheet.allocate_point("syn")
        sheet.allocate_point("syn")
        sheet.award_milestone("first_trade")

        data = sheet.to_dict()
        restored = AttributeSheet.from_dict(data)

        assert restored.get_value("com") == sheet.get_value("com")
        assert restored.get_value("syn") == sheet.get_value("syn")
        assert restored.unspent_points == sheet.unspent_points
        assert restored.has_milestone("first_trade")

    def test_from_dict_empty(self) -> None:
        sheet = AttributeSheet.from_dict({})
        for attr in AttributeId:
            assert sheet.get_value(attr.value) == 1
        assert sheet.unspent_points == 0

    def test_from_dict_partial(self) -> None:
        data = {"values": {"com": 5}}
        sheet = AttributeSheet.from_dict(data)
        assert sheet.get_value("com") == 5
        assert sheet.get_value("acu") == 1  # Default


class TestAttributeSheetGetAllValues:
    """Tests for getting all attribute values."""

    def test_get_all_values(self) -> None:
        values = {"com": 3, "acu": 2, "res": 1, "ing": 1, "syn": 4}
        sheet = AttributeSheet(values=values)
        all_vals = sheet.get_all_values()
        assert all_vals == values
        # Returned dict should be a copy
        all_vals["com"] = 99
        assert sheet.get_value("com") == 3
