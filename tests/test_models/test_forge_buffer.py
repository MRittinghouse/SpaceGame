"""Tests for ForgeBuffer and ForgeBufferManager models."""

from spacegame.models.forge_buffer import (
    BASE_FORGE_BUFFER_CAPACITY,
    ForgeBuffer,
    ForgeBufferManager,
)


class TestForgeBuffer:
    """Tests for the ForgeBuffer dataclass."""

    def test_new_buffer_is_empty_with_default_capacity(self) -> None:
        buf = ForgeBuffer(system_id="sys_01")
        assert buf.get_total_stored() == 0
        assert buf.capacity == 50
        assert buf.capacity == BASE_FORGE_BUFFER_CAPACITY

    def test_custom_capacity(self) -> None:
        buf = ForgeBuffer(system_id="sys_01", capacity=120)
        assert buf.capacity == 120
        assert buf.available_space() == 120

    def test_add_output_basic(self) -> None:
        buf = ForgeBuffer(system_id="sys_01")
        added = buf.add_output("refined_iron", 10)
        assert added == 10
        assert buf.contents["refined_iron"] == 10
        assert buf.get_total_stored() == 10

    def test_add_output_multiple_types(self) -> None:
        buf = ForgeBuffer(system_id="sys_01")
        buf.add_output("refined_iron", 10)
        buf.add_output("copper_alloy", 5)
        assert buf.get_total_stored() == 15
        assert buf.contents["refined_iron"] == 10
        assert buf.contents["copper_alloy"] == 5

    def test_add_output_capped_at_capacity(self) -> None:
        buf = ForgeBuffer(system_id="sys_01", capacity=20)
        added = buf.add_output("refined_iron", 25)
        assert added == 20, "Should cap at capacity"
        assert buf.get_total_stored() == 20
        assert buf.is_full()

    def test_add_output_partial_when_nearly_full(self) -> None:
        buf = ForgeBuffer(system_id="sys_01", capacity=20)
        buf.add_output("refined_iron", 15)
        added = buf.add_output("copper_alloy", 10)
        assert added == 5, "Only 5 space remaining"
        assert buf.get_total_stored() == 20

    def test_is_full_boundary(self) -> None:
        buf = ForgeBuffer(system_id="sys_01", capacity=10)
        assert not buf.is_full()
        buf.add_output("refined_iron", 9)
        assert not buf.is_full()
        buf.add_output("refined_iron", 1)
        assert buf.is_full()

    def test_remove_output_basic(self) -> None:
        buf = ForgeBuffer(system_id="sys_01")
        buf.add_output("refined_iron", 20)
        removed = buf.remove_output("refined_iron", 10)
        assert removed == 10
        assert buf.contents["refined_iron"] == 10

    def test_remove_output_more_than_stored(self) -> None:
        buf = ForgeBuffer(system_id="sys_01")
        buf.add_output("refined_iron", 5)
        removed = buf.remove_output("refined_iron", 20)
        assert removed == 5, "Can only remove what is stored"
        assert "refined_iron" not in buf.contents, "Empty entry should be cleaned up"

    def test_remove_output_nonexistent_commodity(self) -> None:
        buf = ForgeBuffer(system_id="sys_01")
        removed = buf.remove_output("unobtanium", 10)
        assert removed == 0

    def test_serialization_round_trip(self) -> None:
        buf = ForgeBuffer(system_id="sys_01", capacity=80)
        buf.add_output("refined_iron", 30)
        buf.add_output("copper_alloy", 10)

        data = buf.to_dict()
        restored = ForgeBuffer.from_dict(data)

        assert restored.system_id == "sys_01"
        assert restored.capacity == 80
        assert restored.contents == {"refined_iron": 30, "copper_alloy": 10}


class TestForgeBufferManager:
    """Tests for the ForgeBufferManager."""

    def test_creates_buffer_on_demand(self) -> None:
        mgr = ForgeBufferManager()
        buf = mgr.get_buffer("sys_01")
        assert buf.system_id == "sys_01"
        assert buf.capacity == BASE_FORGE_BUFFER_CAPACITY

    def test_returns_same_buffer_on_repeat_access(self) -> None:
        mgr = ForgeBufferManager()
        buf1 = mgr.get_buffer("sys_01")
        buf1.add_output("refined_iron", 5)
        buf2 = mgr.get_buffer("sys_01")
        assert buf2.contents["refined_iron"] == 5

    def test_upgrade_all_capacity(self) -> None:
        mgr = ForgeBufferManager()
        mgr.get_buffer("sys_01")
        mgr.get_buffer("sys_02")
        mgr.upgrade_all_capacity(25)

        assert mgr.get_buffer("sys_01").capacity == BASE_FORGE_BUFFER_CAPACITY + 25
        assert mgr.get_buffer("sys_02").capacity == BASE_FORGE_BUFFER_CAPACITY + 25
        # New buffers also get the bonus
        assert mgr.get_buffer("sys_03").capacity == BASE_FORGE_BUFFER_CAPACITY + 25

    def test_serialization_round_trip(self) -> None:
        mgr = ForgeBufferManager()
        mgr.get_buffer("sys_01").add_output("refined_iron", 10)
        mgr.upgrade_all_capacity(20)

        data = mgr.to_dict()
        restored = ForgeBufferManager.from_dict(data)

        assert restored.capacity_bonus == 20
        buf = restored.get_buffer("sys_01")
        assert buf.contents["refined_iron"] == 10
        assert buf.capacity == BASE_FORGE_BUFFER_CAPACITY + 20
