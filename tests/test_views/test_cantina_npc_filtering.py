"""Tests for NPC filtering in station hub cantina.

Verifies that NPCs are properly filtered based on their auto_trigger_prerequisites
and auto_trigger_gate_flag, preventing story-sequence-breaking dialogue options.
"""

from unittest.mock import MagicMock

from spacegame.models.dialogue import NPC


def _make_npc(
    npc_id: str = "test_npc",
    name: str = "Test NPC",
    home_system_id: str = "nexus_prime",
    auto_trigger_gate_flag: str = "",
    auto_trigger_prerequisites: list[str] | None = None,
    hide_after_flag: str = "",
) -> NPC:
    """Create a test NPC."""
    return NPC(
        id=npc_id,
        name=name,
        title="Test",
        portrait_color=(100, 100, 100),
        home_system_id=home_system_id,
        dialogue_id=f"{npc_id}_dialogue",
        auto_trigger_gate_flag=auto_trigger_gate_flag,
        auto_trigger_prerequisites=auto_trigger_prerequisites or [],
        hide_after_flag=hide_after_flag,
    )


class TestNpcAvailability:
    """Test _is_npc_available logic for cantina NPC display."""

    def _check_available(self, npc: NPC, dialogue_flags: dict[str, bool]) -> bool:
        """Replicate the filtering logic from station_hub_view._is_npc_available."""
        # Hide if hide_after_flag is set
        if npc.hide_after_flag and dialogue_flags.get(npc.hide_after_flag, False):
            return False
        # Hide if gate flag already triggered (dialogue already happened)
        if npc.auto_trigger_gate_flag and dialogue_flags.get(
            npc.auto_trigger_gate_flag, False
        ):
            return False
        # Hide if prerequisites not yet met
        if npc.auto_trigger_prerequisites:
            if not all(
                dialogue_flags.get(f, False) for f in npc.auto_trigger_prerequisites
            ):
                return False
        return True

    def test_npc_without_auto_trigger_always_visible(self) -> None:
        """NPCs without auto_trigger fields appear regardless of flags."""
        npc = _make_npc(npc_id="delivery_merchant")
        assert self._check_available(npc, {})
        assert self._check_available(npc, {"some_flag": True})

    def test_npc_hidden_when_prerequisites_not_met(self) -> None:
        """NPCs with unmet prerequisites should not appear."""
        npc = _make_npc(
            npc_id="dex_halloran",
            auto_trigger_gate_flag="met_dex_halloran",
            auto_trigger_prerequisites=["cargo_lost_resolved"],
        )
        # No flags set - prerequisites not met
        assert not self._check_available(npc, {})

    def test_npc_visible_when_prerequisites_met_and_gate_not_set(self) -> None:
        """NPCs appear when prerequisites are met and gate flag not yet set."""
        npc = _make_npc(
            npc_id="dex_halloran",
            auto_trigger_gate_flag="met_dex_halloran",
            auto_trigger_prerequisites=["cargo_lost_resolved"],
        )
        flags = {"cargo_lost_resolved": True}
        assert self._check_available(npc, flags)

    def test_npc_hidden_after_gate_flag_set(self) -> None:
        """NPCs hidden once their gate flag is set (dialogue already happened)."""
        npc = _make_npc(
            npc_id="dex_halloran",
            auto_trigger_gate_flag="met_dex_halloran",
            auto_trigger_prerequisites=["cargo_lost_resolved"],
        )
        flags = {"cargo_lost_resolved": True, "met_dex_halloran": True}
        assert not self._check_available(npc, flags)

    def test_multiple_dex_entries_only_one_visible(self) -> None:
        """Only the Dex Halloran NPC whose prereqs are met should appear."""
        dex1 = _make_npc(
            npc_id="dex_halloran",
            auto_trigger_gate_flag="met_dex_halloran",
            auto_trigger_prerequisites=["cargo_lost_resolved"],
        )
        dex2 = _make_npc(
            npc_id="dex_tunnel_contact",
            auto_trigger_gate_flag="dex_tunnel_briefing_heard",
            auto_trigger_prerequisites=["guild_hardware_discovered"],
        )
        dex3 = _make_npc(
            npc_id="dex_final_lead",
            auto_trigger_gate_flag="assembly_location_known",
            auto_trigger_prerequisites=["convergence_data_verified"],
        )

        # Early game: cargo_lost_resolved set, first Dex prereqs met
        flags = {"cargo_lost_resolved": True}
        visible = [n for n in [dex1, dex2, dex3] if self._check_available(n, flags)]
        assert len(visible) == 1
        assert visible[0].id == "dex_halloran"

    def test_sequential_dex_progression(self) -> None:
        """As story progresses, only the current Dex NPC is visible."""
        dex1 = _make_npc(
            npc_id="dex_halloran",
            auto_trigger_gate_flag="met_dex_halloran",
            auto_trigger_prerequisites=["cargo_lost_resolved"],
        )
        dex2 = _make_npc(
            npc_id="dex_tunnel_contact",
            auto_trigger_gate_flag="dex_tunnel_briefing_heard",
            auto_trigger_prerequisites=["guild_hardware_discovered"],
        )
        dex3 = _make_npc(
            npc_id="dex_final_lead",
            auto_trigger_gate_flag="assembly_location_known",
            auto_trigger_prerequisites=["convergence_data_verified"],
        )

        all_dex = [dex1, dex2, dex3]

        # After first Dex dialogue, before second prereqs
        flags = {"cargo_lost_resolved": True, "met_dex_halloran": True}
        visible = [n for n in all_dex if self._check_available(n, flags)]
        assert len(visible) == 0, "No Dex should be visible between story beats"

        # Second Dex prereqs met
        flags["guild_hardware_discovered"] = True
        visible = [n for n in all_dex if self._check_available(n, flags)]
        assert len(visible) == 1
        assert visible[0].id == "dex_tunnel_contact"

        # After second Dex, before third prereqs
        flags["dex_tunnel_briefing_heard"] = True
        visible = [n for n in all_dex if self._check_available(n, flags)]
        assert len(visible) == 0

        # Third Dex prereqs met
        flags["convergence_data_verified"] = True
        visible = [n for n in all_dex if self._check_available(n, flags)]
        assert len(visible) == 1
        assert visible[0].id == "dex_final_lead"

    def test_hide_after_flag_still_works(self) -> None:
        """NPCs with hide_after_flag are hidden when that flag is set."""
        npc = _make_npc(
            npc_id="officer_larsen",
            hide_after_flag="larsen_permit_complete",
        )
        assert self._check_available(npc, {})
        assert not self._check_available(npc, {"larsen_permit_complete": True})

    def test_multiple_prerequisites_all_required(self) -> None:
        """All prerequisites must be met, not just some."""
        npc = _make_npc(
            npc_id="test",
            auto_trigger_gate_flag="test_gate",
            auto_trigger_prerequisites=["flag_a", "flag_b"],
        )
        assert not self._check_available(npc, {"flag_a": True})
        assert not self._check_available(npc, {"flag_b": True})
        assert self._check_available(npc, {"flag_a": True, "flag_b": True})
