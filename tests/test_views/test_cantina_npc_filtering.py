"""Tests for NPC filtering in station hub cantina.

Verifies that NPCs are properly filtered based on their auto_trigger_prerequisites
and auto_trigger_gate_flag, preventing story-sequence-breaking dialogue options.
"""

import ast
from pathlib import Path

from spacegame.constants.flags import met_npc
from spacegame.models.dialogue import NPC
from spacegame.models.npc_availability import is_listed


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
        """The shared Talk filter, with no mission waiting on anyone."""
        return is_listed(npc, npc.home_system_id, dialogue_flags, None, set(), frozenset())

    def test_npc_without_auto_trigger_always_visible(self) -> None:
        """NPCs without auto_trigger fields appear regardless of flags."""
        npc = _make_npc(npc_id="odom_broker")
        assert self._check_available(npc, {})
        assert self._check_available(npc, {"some_flag": True})

    def test_npc_hidden_when_prerequisites_not_met(self) -> None:
        """NPCs with unmet prerequisites should not appear."""
        npc = _make_npc(
            npc_id="dex_halloran",
            auto_trigger_gate_flag=met_npc("dex_halloran"),
            auto_trigger_prerequisites=["cargo_lost_resolved"],
        )
        # No flags set - prerequisites not met
        assert not self._check_available(npc, {})

    def test_npc_visible_when_prerequisites_met_and_gate_not_set(self) -> None:
        """NPCs appear when prerequisites are met and gate flag not yet set."""
        npc = _make_npc(
            npc_id="dex_halloran",
            auto_trigger_gate_flag=met_npc("dex_halloran"),
            auto_trigger_prerequisites=["cargo_lost_resolved"],
        )
        flags = {"cargo_lost_resolved": True}
        assert self._check_available(npc, flags)

    def test_npc_hidden_after_gate_flag_set(self) -> None:
        """NPCs hidden once their gate flag is set (dialogue already happened)."""
        npc = _make_npc(
            npc_id="dex_halloran",
            auto_trigger_gate_flag=met_npc("dex_halloran"),
            auto_trigger_prerequisites=["cargo_lost_resolved"],
        )
        flags = {"cargo_lost_resolved": True, met_npc("dex_halloran"): True}
        assert not self._check_available(npc, flags)

    def test_multiple_dex_entries_only_one_visible(self) -> None:
        """Only the Dex Halloran NPC whose prereqs are met should appear."""
        dex1 = _make_npc(
            npc_id="dex_halloran",
            auto_trigger_gate_flag=met_npc("dex_halloran"),
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
            auto_trigger_gate_flag=met_npc("dex_halloran"),
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
        flags = {"cargo_lost_resolved": True, met_npc("dex_halloran"): True}
        visible = [n for n in all_dex if self._check_available(n, flags)]
        assert len(visible) == 0, (
            "No Dex is listed between story beats while no mission waits on one"
        )

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


class TestBothViewsShareTheFilter:
    """BB-38: the station hub, the cantina and the quest marker read one module."""

    def _function(self, path: str, name: str) -> ast.FunctionDef:
        root = Path(__file__).resolve().parents[2]
        tree = ast.parse((root / path).read_text(encoding="utf-8"))
        return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)

    def _calls(self, node: ast.AST) -> set[str]:
        return {
            c.func.id
            for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
        }

    def test_both_lists_call_is_listed(self) -> None:
        for path in ("spacegame/views/station_hub_view.py", "spacegame/views/cantina_view.py"):
            assert "is_listed" in self._calls(self._function(path, "_is_npc_available")), path

    def test_the_quest_marker_calls_needed_by(self) -> None:
        marker = self._function("spacegame/views/cantina_view.py", "_npc_is_quest_receiver")
        assert "needed_by" in self._calls(marker)
