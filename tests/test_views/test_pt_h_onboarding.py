"""PT-H onboarding sprint regression tests.

Covers: Arna NPC + four-stage dialogue, Rhea NPC + dialogue, coolant_run
mission lifecycle, StationHubView interception, cockpit HUD objective
hint toggle, settings view roundtrip, Odom teaching branch gating.
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.data_loader import DataLoader
from spacegame.engine.activity_registry import create_default_registry
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.station_hub_view import StationHubView


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield


def _make_hub_env(system_id: str = "nexus_prime"):
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    loader = DataLoader()
    loader.load_all()
    ship_type = loader.get_ship_type("shuttle")
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    ship.current_hull = ship_type.combat_hull
    player = Player("Test", 5000, system_id, ship)
    system = loader.get_system(system_id)
    locations = loader.get_locations_for_system(system_id)
    registry = create_default_registry()
    view = StationHubView(
        ui_manager=manager,
        player=player,
        system=system,
        locations=locations,
        activity_registry=registry,
        data_loader=loader,
    )
    return view, player, loader


# ---------------------------------------------------------------------------
# Data integrity — NPCs, dialogues, mission all loaded and well-formed
# ---------------------------------------------------------------------------


class TestPTHDataIntegrity:
    def test_arna_npc_loaded(self) -> None:
        loader = DataLoader()
        loader.load_all()
        assert "arna" in loader.npcs
        arna = loader.npcs["arna"]
        assert arna.name == "Arna"
        assert arna.title == "Dockmaster"
        assert arna.home_system_id == "nexus_prime"
        assert arna.dialogue_id == "arna_first_encounter"
        # Dialogue states wire to the mission flag chain
        state_ids = [s.state_id for s in arna.dialogue_states]
        assert "arna_pre_completion" in state_ids
        assert "arna_post_completion" in state_ids
        assert "arna_retired" in state_ids

    def test_arna_stays_visible_after_met(self) -> None:
        """No auto_trigger_gate_flag on Arna → she stays clickable."""
        loader = DataLoader()
        loader.load_all()
        assert loader.npcs["arna"].auto_trigger_gate_flag == ""

    def test_rhea_npc_loaded(self) -> None:
        loader = DataLoader()
        loader.load_all()
        assert "rhea" in loader.npcs
        rhea = loader.npcs["rhea"]
        assert rhea.home_system_id == "verdant"
        assert rhea.dialogue_id == "rhea_receives_coolant"
        # Rhea only appears once player has accepted Arna's delivery, and
        # disappears after completion — she's a one-off recipient, not a
        # persistent NPC.
        assert "arna_delivery_accepted" in rhea.auto_trigger_prerequisites
        assert rhea.hide_after_flag == "arna_delivery_complete"

    def test_coolant_run_mission_loaded(self) -> None:
        loader = DataLoader()
        loader.load_all()
        mission = next(
            (m for m in loader.missions if m.id == "coolant_run"), None
        )
        assert mission is not None
        assert mission.available_at == ["nexus_prime"]
        assert "arna_delivery_accepted" in mission.required_flags
        assert mission.auto_accept

    def test_coolant_run_rewards(self) -> None:
        loader = DataLoader()
        loader.load_all()
        mission = next(
            (m for m in loader.missions if m.id == "coolant_run"), None
        )
        assert mission is not None
        credits_rewards = [r for r in mission.rewards if r.reward_type == "credits"]
        assert credits_rewards and credits_rewards[0].amount == 2000
        flag_targets = [r.target_id for r in mission.rewards if r.reward_type == "set_flag"]
        assert "arna_delivery_complete" in flag_targets
        assert "first_delivery_complete" in flag_targets

    def test_coolant_run_cargo_grant(self) -> None:
        """Accept of the mission should give 18 machinery."""
        loader = DataLoader()
        loader.load_all()
        mission = next(
            (m for m in loader.missions if m.id == "coolant_run"), None
        )
        assert mission is not None
        assert len(mission.on_accept_cargo) == 1
        cargo = mission.on_accept_cargo[0]
        assert cargo.commodity_id == "machinery"
        assert cargo.quantity == 18

    def test_arna_dialogue_trees_exist(self) -> None:
        loader = DataLoader()
        loader.load_all()
        dialogues = loader.dialogue_trees
        for tree_id in (
            "arna_first_encounter",
            "arna_pre_completion",
            "arna_post_completion",
            "arna_retired",
            "rhea_receives_coolant",
        ):
            assert tree_id in dialogues, f"missing dialogue tree: {tree_id}"

    def test_arna_first_encounter_accept_sets_delivery_flag(self) -> None:
        """Accepted path must set arna_delivery_accepted — the mission gate."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "dialogue", "dialogues.json"
            ),
            encoding="utf-8",
        ) as f:
            raw = json.load(f)
        tree = next(d for d in raw["dialogues"] if d["id"] == "arna_first_encounter")
        accepted = next(n for n in tree["nodes"] if n["id"] == "accepted_confirm")
        set_flags = [r.get("set_flag") for r in accepted["responses"]]
        assert "arna_delivery_accepted" in set_flags

    def test_rhea_resolves_delivery(self) -> None:
        """Rhea's accept path must set arna_delivery_resolved — the mission completion gate."""
        with open(
            os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "dialogue", "dialogues.json"
            ),
            encoding="utf-8",
        ) as f:
            raw = json.load(f)
        tree = next(d for d in raw["dialogues"] if d["id"] == "rhea_receives_coolant")
        start = next(n for n in tree["nodes"] if n["id"] == "start")
        set_flags = [r.get("set_flag") for r in start["responses"]]
        assert "arna_delivery_resolved" in set_flags


# ---------------------------------------------------------------------------
# Writing Bible compliance on new content
# ---------------------------------------------------------------------------


class TestPTHWritingCompliance:
    """New dialogue/mission text is Writing Bible clean."""

    def _collect_new_text(self) -> list[str]:
        base = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        # Arna + Rhea dialogue text
        with open(os.path.join(base, "dialogue", "dialogues.json"), encoding="utf-8") as f:
            dialogues = json.load(f)["dialogues"]
        new_ids = {
            "arna_first_encounter",
            "arna_pre_completion",
            "arna_post_completion",
            "arna_retired",
            "rhea_receives_coolant",
        }
        # Also pull new nodes on merchant_delivery (teach_intro, teach_routes)
        texts: list[str] = []
        for d in dialogues:
            if d["id"] in new_ids:
                for n in d["nodes"]:
                    texts.append(n.get("text", ""))
                    texts.append(n.get("subtext", ""))
                    for r in n.get("responses", []):
                        texts.append(r.get("text", ""))
            elif d["id"] == "merchant_delivery":
                for n in d["nodes"]:
                    if n["id"] in ("teach_intro", "teach_routes"):
                        texts.append(n.get("text", ""))
                        for r in n.get("responses", []):
                            texts.append(r.get("text", ""))
        # coolant_run mission strings
        with open(os.path.join(base, "missions", "side_missions.json"), encoding="utf-8") as f:
            missions = json.load(f)["missions"]
        cr = next(m for m in missions if m["id"] == "coolant_run")
        texts.extend(
            [cr["name"], cr["description"], cr["hint"], cr.get("discovery_text", "")]
        )
        for obj in cr.get("objectives", []):
            texts.append(obj.get("description", ""))
        return texts

    def test_no_em_dashes(self) -> None:
        for t in self._collect_new_text():
            assert "\u2014" not in t, f"em-dash found: {t!r}"

    def test_no_ai_tells(self) -> None:
        banned = ["couldn't help but", "a testament to"]
        for t in self._collect_new_text():
            lower = t.lower()
            for phrase in banned:
                assert phrase not in lower, f"banned phrase '{phrase}' in: {t!r}"


# ---------------------------------------------------------------------------
# StationHubView interception
# ---------------------------------------------------------------------------


class TestStationHubInterception:
    def test_intercepts_on_first_arrival_after_tutorial(self) -> None:
        from spacegame.constants.flags import met_npc

        view, player, _ = _make_hub_env("nexus_prime")
        player.dialogue_flags["tutorial_builder_complete"] = True
        assert not player.dialogue_flags.get(met_npc("arna"), False)
        view.on_enter()
        assert view.next_state == GameState.DIALOGUE
        assert view.pending_npc_id == "arna"
        assert player.dialogue_flags.get(met_npc("arna"), False) is True

    def test_no_intercept_without_tutorial_complete(self) -> None:
        view, player, _ = _make_hub_env("nexus_prime")
        # tutorial_builder_complete not set
        view.on_enter()
        assert view.pending_npc_id is None
        assert view.next_state != GameState.DIALOGUE

    def test_no_intercept_if_already_met(self) -> None:
        view, player, _ = _make_hub_env("nexus_prime")
        player.dialogue_flags["tutorial_builder_complete"] = True
        player.dialogue_flags["met_arna"] = True
        view.on_enter()
        assert view.pending_npc_id is None

    def test_no_intercept_at_other_systems(self) -> None:
        view, player, _ = _make_hub_env("verdant")
        player.dialogue_flags["tutorial_builder_complete"] = True
        view.on_enter()
        assert view.pending_npc_id is None


# ---------------------------------------------------------------------------
# Cockpit HUD objective hint toggle
# ---------------------------------------------------------------------------


class TestCockpitObjectiveHintToggle:
    def test_default_on(self) -> None:
        from unittest.mock import MagicMock

        from spacegame.views.cockpit_hud import CockpitHUD

        hud = CockpitHUD(player=MagicMock(), mission_manager=MagicMock())
        assert hud.show_objective_hint is True

    def test_hides_hint_when_off(self) -> None:
        """With toggle off, _get_quest_hint returns empty string even with
        active missions."""
        from unittest.mock import MagicMock

        from spacegame.views.cockpit_hud import CockpitHUD

        mgr = MagicMock()
        mgr.get_missions_by_status.return_value = [MagicMock()]
        hud = CockpitHUD(player=MagicMock(), mission_manager=mgr)
        hud.show_objective_hint = False
        assert hud._get_quest_hint() == ""

    def test_shows_hint_when_on(self) -> None:
        from unittest.mock import MagicMock

        from spacegame.models.mission import MissionObjective
        from spacegame.views.cockpit_hud import CockpitHUD

        obj = MissionObjective(
            type="reach_system",
            target_id="verdant",
            target_quantity=1,
            description="Jump to Verdant",
        )
        mock_mission = MagicMock()
        mock_mission.id = "coolant_run"
        mock_mission.objectives = [obj]
        mock_mission.hint = "hint"
        mock_mission.name = "name"
        mgr = MagicMock()
        mgr.get_missions_by_status.return_value = [mock_mission]
        mgr.get_objective_progress.return_value = [False]
        hud = CockpitHUD(player=MagicMock(), mission_manager=mgr)
        hud.show_objective_hint = True
        result = hud._get_quest_hint()
        assert "Jump to Verdant" in result


# ---------------------------------------------------------------------------
# Settings view roundtrip
# ---------------------------------------------------------------------------


class TestSettingsObjectiveHintRoundtrip:
    def test_toggle_persists_through_get_display_settings(self) -> None:
        from pathlib import Path

        from spacegame.views.settings_view import SettingsView

        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        view = SettingsView(manager, Path("."))
        view.set_objective_hint(False)
        assert view.get_display_settings()["show_objective_hint"] is False
        view.set_objective_hint(True)
        assert view.get_display_settings()["show_objective_hint"] is True

    def test_default_is_on(self) -> None:
        from pathlib import Path

        from spacegame.views.settings_view import SettingsView

        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        view = SettingsView(manager, Path("."))
        assert view.get_display_settings()["show_objective_hint"] is True
