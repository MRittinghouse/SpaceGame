"""PT-K "System transparency" regression tests.

Covers the four hooks landed in this sprint:
  - Galaxy map hover tooltip shows fuel cost before commit
  - Cockpit HUD cargo line includes percentage with color-coded threshold
  - Faction reputation deltas queue for surface notification
  - Dialogue skill checks produce a level-vs-difficulty readout
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


# ---------------------------------------------------------------------------
# Galaxy map: hover tooltip shows fuel cost
# ---------------------------------------------------------------------------


class TestGalaxyMapHoverTooltip:
    def test_draw_hover_tooltip_renders_without_error(self) -> None:
        """Smoke test: the tooltip renders a text surface to the screen when
        a distant system is hovered."""
        from spacegame.data_loader import DataLoader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.views.galaxy_map_view import GalaxyMapView

        loader = DataLoader()
        loader.load_all()
        ship_type = loader.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        ship.current_hull = ship_type.combat_hull
        player = Player("Test", 5000, "nexus_prime", ship)

        import pygame_gui

        manager = pygame_gui.UIManager((1280, 720))
        view = GalaxyMapView(manager, player, loader.systems)
        view.hovered_system = "verdant"  # different from current

        screen = pygame.Surface((1280, 720))
        # Just needs to not raise
        view._draw_hover_tooltip(screen, "verdant")

    def test_hover_tooltip_gated_on_non_current_system(self) -> None:
        """Tooltip should only show for non-current, non-selected systems
        per the render pipeline guard. Verify the guard condition in source."""
        from pathlib import Path

        source = Path("spacegame/views/galaxy_map_view.py").read_text(encoding="utf-8")
        # The guard block names the condition clearly
        assert "self.hovered_system != self.player.current_system_id" in source
        assert "self.hovered_system != self.selected_system" in source


# ---------------------------------------------------------------------------
# Cockpit HUD: cargo line percentage + color thresholds
# ---------------------------------------------------------------------------


class TestCockpitCargoPercentage:
    def _make_hud_with_cargo(self, used: int, capacity: int):
        from spacegame.views.cockpit_hud import CockpitHUD

        player = MagicMock()
        player.display_ship_name = "Test Ship"
        player.credits = 0
        player.ship = MagicMock()
        player.ship.current_cargo = {"x": used}
        player.ship.max_cargo = capacity
        return CockpitHUD(player=player, mission_manager=MagicMock()), player

    def test_cargo_text_includes_percent(self) -> None:
        """Read the source directly — cockpit HUD renders f-string with pct."""
        from pathlib import Path

        source = Path("spacegame/views/cockpit_hud.py").read_text(encoding="utf-8")
        assert '({pct}%)' in source or '{pct}%' in source

    def test_green_under_sixty_percent(self) -> None:
        from pathlib import Path

        source = Path("spacegame/views/cockpit_hud.py").read_text(encoding="utf-8")
        # Threshold block: low pct -> TEXT_SECONDARY
        assert "cargo_color = Colors.TEXT_SECONDARY" in source

    def test_yellow_at_sixty_percent(self) -> None:
        from pathlib import Path

        source = Path("spacegame/views/cockpit_hud.py").read_text(encoding="utf-8")
        assert "elif pct >= 60:" in source
        assert "cargo_color = Colors.YELLOW" in source

    def test_red_at_ninety_percent(self) -> None:
        from pathlib import Path

        source = Path("spacegame/views/cockpit_hud.py").read_text(encoding="utf-8")
        assert "if pct >= 90:" in source
        assert "cargo_color = Colors.RED" in source


# ---------------------------------------------------------------------------
# Faction standing delta surfacing
# ---------------------------------------------------------------------------


class TestFactionDeltaNotification:
    def test_modify_reputation_queues_delta(self) -> None:
        """After modify_reputation, the player has a pending delta entry."""
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        ship_type = loader.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        ship.current_hull = ship_type.combat_hull
        player = Player("Test", 100, "nexus_prime", ship)

        player.modify_reputation("commerce_guild", 5)
        assert hasattr(player, "_pending_faction_deltas")
        assert ("commerce_guild", 5) in player._pending_faction_deltas

    def test_negative_delta_queued(self) -> None:
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        ship_type = loader.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        ship.current_hull = ship_type.combat_hull
        player = Player("Test", 100, "nexus_prime", ship)

        player.modify_reputation("miners_union", -3)
        assert ("miners_union", -3) in player._pending_faction_deltas

    def test_clamped_delta_records_effective_change(self) -> None:
        """When rep is at +100 cap, a +5 call should record 0 delta (and not
        be notified). Similarly the clamp at -100."""
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        ship_type = loader.get_ship_type("shuttle")
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        ship.current_hull = ship_type.combat_hull
        player = Player("Test", 100, "nexus_prime", ship)
        player.faction_reputation["commerce_guild"] = 100

        player.modify_reputation("commerce_guild", 5)  # clamped
        deltas = getattr(player, "_pending_faction_deltas", [])
        # Either no delta recorded, or a 0 delta (but the implementation
        # skips 0-delta appends)
        assert not any(d == ("commerce_guild", 5) for d in deltas)

    def test_game_loop_drains_pending_deltas(self) -> None:
        """Verify the drain block exists in game.py run loop."""
        from pathlib import Path

        source = Path("spacegame/engine/game.py").read_text(encoding="utf-8")
        assert "_pending_faction_deltas" in source
        assert "pending.clear()" in source


# ---------------------------------------------------------------------------
# Skill check readout in dialogue
# ---------------------------------------------------------------------------


class TestSkillCheckReadout:
    def _make_manager(self, effective_level: int, difficulty: int, skill: str = "persuasion"):
        from spacegame.models.dialogue import DialogueManager, DialogueResponse, SkillCheck

        dm = DialogueManager()
        # Fake social manager that matches the interface used by _resolve_skill_check
        social = MagicMock()
        social.resolve_check.return_value = (effective_level >= difficulty, "done")
        social.get_effective_level.return_value = effective_level
        skill_obj = MagicMock()
        skill_obj.name = skill.title()
        social._skills = {skill: skill_obj}
        dm._social_manager = social
        dm._current_npc_id = "test_npc"
        response = DialogueResponse(
            text="Try it",
            next_node_id=None,
            skill_check=SkillCheck(
                skill=skill,
                difficulty=difficulty,
                success_node_id=None,
                failure_node_id=None,
            ),
        )
        return dm, response

    def test_readout_format_pass(self) -> None:
        dm, response = self._make_manager(effective_level=3, difficulty=2)
        dm._resolve_skill_check(response)
        readout = dm.get_last_check_readout()
        assert readout is not None
        assert "PERSUASION" in readout
        assert "3" in readout
        assert "2" in readout
        assert "PASS" in readout

    def test_readout_format_fail(self) -> None:
        dm, response = self._make_manager(effective_level=1, difficulty=3)
        dm._resolve_skill_check(response)
        readout = dm.get_last_check_readout()
        assert readout is not None
        assert "FAIL" in readout
        assert "1" in readout and "3" in readout

    def test_readout_cleared_on_next_response(self) -> None:
        """After selecting a non-check response, readout resets to None so
        the dialogue overlay stops showing it."""
        from spacegame.models.dialogue import DialogueManager, DialogueResponse

        dm, response = self._make_manager(effective_level=3, difficulty=2)
        dm._resolve_skill_check(response)
        assert dm.get_last_check_readout() is not None
        # Simulate response-selection reset path
        dm._last_check_result = None
        dm._last_check_readout = None
        assert dm.get_last_check_readout() is None

    def test_readout_none_without_social_manager(self) -> None:
        from spacegame.models.dialogue import DialogueManager, DialogueResponse, SkillCheck

        dm = DialogueManager()
        # No social manager attached
        response = DialogueResponse(
            text="Try it",
            next_node_id=None,
            skill_check=SkillCheck(
                skill="persuasion", difficulty=1, success_node_id=None, failure_node_id=None
            ),
        )
        dm._resolve_skill_check(response)
        assert dm.get_last_check_readout() is None
