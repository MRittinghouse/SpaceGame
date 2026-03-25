"""Ground mission briefing view.

Pre-mission screen showing mission details, objectives, intel hints,
and crew selection. The player reviews the mission and chooses which
crew members to bring before launching ground exploration.
"""

from typing import Any, Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FONT_BODY, FONT_MD, FONT_MD2, FONT_SECTION, FONT_XL, get_font
from spacegame.models.crew import CrewRoster, CrewTemplate
from spacegame.models.ground_mission import GroundMissionConfig, IntelHint
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

# Ground ability descriptions per crew member (matches GroundCrewBonuses.compute)
_GROUND_ABILITIES: dict[str, list[str]] = {
    "elena_reeves": ["Vision +1", "Reveal patrols", "Retreat +2"],
    "marcus_jin": ["Silent doors"],
    "dr_priya_osei": ["Analyze weakness"],
    "tomas_drifter": ["Noise -1", "Talk +2"],
}

# Difficulty tier display colors
_DIFFICULTY_COLORS: dict[str, tuple[int, int, int]] = {
    "low": Colors.GREEN,
    "moderate": Colors.YELLOW,
    "high": (255, 140, 40),
    "extreme": Colors.RED,
}


class GroundBriefingView(BaseView):
    """Pre-mission briefing screen for ground exploration.

    Displays mission name, atmospheric description, objectives, intel
    hints (filtered by player skill), and a crew selection panel.
    The player can select crew members (up to max_crew) and either
    launch the mission or cancel to return.
    """

    # Layout constants
    PANEL_X = scale_x(100)
    PANEL_Y = scale_y(60)
    PANEL_W = WINDOW_WIDTH - scale_x(200)
    PANEL_H = WINDOW_HEIGHT - scale_y(120)
    CREW_SECTION_Y = scale_y(520)
    CREW_CARD_W = scale_x(180)
    CREW_CARD_H = scale_y(120)
    CREW_CARD_GAP = scale_x(16)
    BUTTON_W = scale_x(180)
    BUTTON_H = scale_y(44)

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        mission_config: GroundMissionConfig,
        crew_roster: CrewRoster,
        skill_levels: dict[str, int],
    ) -> None:
        """Initialize the briefing view.

        Args:
            ui_manager: pygame_gui UI manager.
            mission_config: Configuration for the ground mission.
            crew_roster: Player's crew roster for crew selection.
            skill_levels: Player's skill levels for intel hint filtering.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.mission_config = mission_config
        self.crew_roster = crew_roster
        self.skill_levels = skill_levels
        self.next_state: Optional[GameState] = None
        self.return_state: GameState = GameState.GALAXY_MAP

        # Crew selection state
        self.selected_crew: list[str] = []
        self.available_crew: list[tuple[CrewTemplate, dict[str, Any]]] = []
        self.revealed_hints: list[IntelHint] = []

        # UI element refs (created in _create_ui)
        self.launch_button: Optional[pygame_gui.elements.UIButton] = None
        self.cancel_button: Optional[pygame_gui.elements.UIButton] = None
        self.crew_buttons: dict[str, pygame_gui.elements.UIButton] = {}

        # Fonts
        self.title_font = get_font("header", FONT_SECTION)
        self.subtitle_font = get_font("header", FONT_XL)
        self.body_font = get_font("dialogue", FONT_BODY)
        self.small_font = get_font("dialogue", FONT_MD)
        self.hint_font = get_font("machine", FONT_MD2)

        # Visual
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=77)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        """Initialize view state and UI elements."""
        super().on_enter()
        logger.info(
            "Entered ground briefing: %s (%s)",
            self.mission_config.name,
            self.mission_config.difficulty.value,
        )
        self.next_state = None
        self.selected_crew = []

        # Compute available crew and revealed intel
        self.available_crew = self.crew_roster.get_recruited_members()
        self.revealed_hints = self.mission_config.get_revealed_hints(self.skill_levels)

        self._create_ui()

    def on_exit(self) -> None:
        """Clean up UI elements."""
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create all pygame_gui elements."""
        btn_y = self.PANEL_Y + self.PANEL_H - self.BUTTON_H - 20
        cx = WINDOW_WIDTH // 2

        # Launch button
        self.launch_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(cx + 20, btn_y, self.BUTTON_W, self.BUTTON_H),
            text="LAUNCH MISSION",
            manager=self.ui_manager,
        )

        # Cancel button
        self.cancel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(cx - self.BUTTON_W - 20, btn_y, self.BUTTON_W, self.BUTTON_H),
            text="CANCEL",
            manager=self.ui_manager,
        )

        # Crew selection buttons
        self.crew_buttons = {}
        crew_start_x = self.PANEL_X + 30
        for i, (template, _state) in enumerate(self.available_crew):
            btn_x = crew_start_x + i * (self.CREW_CARD_W + self.CREW_CARD_GAP)
            self.crew_buttons[template.id] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    btn_x, self.CREW_SECTION_Y + 30, self.CREW_CARD_W, self.CREW_CARD_H
                ),
                text=template.name,
                manager=self.ui_manager,
            )

    def _destroy_ui(self) -> None:
        """Kill all pygame_gui elements."""
        for elem in [self.launch_button, self.cancel_button]:
            if elem:
                elem.kill()
        for btn in self.crew_buttons.values():
            btn.kill()
        self.launch_button = None
        self.cancel_button = None
        self.crew_buttons.clear()

    def toggle_crew_selection(self, crew_id: str) -> None:
        """Toggle a crew member's selection state.

        Args:
            crew_id: Template ID of the crew member.
        """
        # Only allow recruited crew
        recruited_ids = {t.id for t, _ in self.available_crew}
        if crew_id not in recruited_ids:
            return

        if crew_id in self.selected_crew:
            self.selected_crew.remove(crew_id)
        elif len(self.selected_crew) < self.mission_config.max_crew:
            self.selected_crew.append(crew_id)

    def get_crew_ground_abilities(self, crew_id: str) -> list[str]:
        """Get ground ability descriptions for a crew member.

        Args:
            crew_id: Template ID of the crew member.

        Returns:
            List of human-readable ability descriptions.
        """
        return list(_GROUND_ABILITIES.get(crew_id, []))

    def get_next_state(self) -> Optional[GameState]:
        """Return pending state transition."""
        return self.next_state

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle button presses and keyboard input."""
        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.next_state = self.return_state
                return

        # pygame_gui button presses
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.launch_button:
                self.next_state = GameState.GROUND_EXPLORATION
                return
            if event.ui_element == self.cancel_button:
                self.next_state = self.return_state
                return

            # Crew selection buttons
            for crew_id, btn in self.crew_buttons.items():
                if event.ui_element == btn:
                    self.toggle_crew_selection(crew_id)
                    return

    def update(self, dt: float) -> None:
        """Update background animation."""
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """Render the briefing screen."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Main panel background
        panel_rect = pygame.Rect(self.PANEL_X, self.PANEL_Y, self.PANEL_W, self.PANEL_H)
        pygame.draw.rect(screen, Colors.UI_PANEL, panel_rect, border_radius=8)
        pygame.draw.rect(screen, Colors.UI_BORDER, panel_rect, 1, border_radius=8)

        self._render_header(screen)
        self._render_description(screen)
        self._render_objectives(screen)
        self._render_intel(screen)
        self._render_crew_section(screen)

    def _render_header(self, screen: pygame.Surface) -> None:
        """Render mission title and difficulty badge."""
        # Title
        title_surf = self.title_font.render(self.mission_config.name, True, Colors.TEXT_PRIMARY)
        screen.blit(title_surf, (self.PANEL_X + 30, self.PANEL_Y + 20))

        # "GROUND MISSION BRIEFING" label
        label_surf = self.small_font.render("GROUND MISSION BRIEFING", True, Colors.TEXT_SECONDARY)
        screen.blit(label_surf, (self.PANEL_X + 30, self.PANEL_Y + 58))

        # Difficulty badge
        diff = self.mission_config.difficulty
        diff_color = _DIFFICULTY_COLORS.get(diff.value, Colors.TEXT_SECONDARY)
        diff_surf = self.subtitle_font.render(diff.value.upper(), True, diff_color)
        diff_x = self.PANEL_X + self.PANEL_W - diff_surf.get_width() - 30
        screen.blit(diff_surf, (diff_x, self.PANEL_Y + 24))

        # Separator
        sep_y = self.PANEL_Y + 80
        pygame.draw.line(
            screen,
            Colors.UI_BORDER,
            (self.PANEL_X + 20, sep_y),
            (self.PANEL_X + self.PANEL_W - 20, sep_y),
        )

    def _render_description(self, screen: pygame.Surface) -> None:
        """Render atmospheric mission description."""
        y = self.PANEL_Y + 95
        text = self.mission_config.description
        # Simple word-wrap
        max_width = self.PANEL_W - 60
        words = text.split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if self.body_font.size(test)[0] <= max_width:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for line in lines:
            surf = self.body_font.render(line, True, Colors.TEXT_SECONDARY)
            screen.blit(surf, (self.PANEL_X + 30, y))
            y += 22

    def _render_objectives(self, screen: pygame.Surface) -> None:
        """Render mission objectives list."""
        y = self.PANEL_Y + 180
        header = self.subtitle_font.render("OBJECTIVES", True, Colors.TEXT_PRIMARY)
        screen.blit(header, (self.PANEL_X + 30, y))
        y += 30

        for obj in self.mission_config.objectives:
            bullet = self.body_font.render(f"\u2022 {obj}", True, Colors.TEXT_SECONDARY)
            screen.blit(bullet, (self.PANEL_X + 40, y))
            y += 24

    def _render_intel(self, screen: pygame.Surface) -> None:
        """Render revealed intel hints."""
        if not self.revealed_hints:
            return

        y = self.PANEL_Y + 300
        header = self.subtitle_font.render("INTEL", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (self.PANEL_X + 30, y))
        y += 30

        for hint in self.revealed_hints:
            # Diamond prefix for intel items
            text = f"\u25c6 {hint.text}"
            surf = self.hint_font.render(text, True, Colors.TEXT_HIGHLIGHT)
            screen.blit(surf, (self.PANEL_X + 40, y))
            y += 22

    def _render_crew_section(self, screen: pygame.Surface) -> None:
        """Render crew selection area with ability summaries."""
        y = self.CREW_SECTION_Y

        # Section header with selection count
        max_crew = self.mission_config.max_crew
        count = len(self.selected_crew)
        header_text = f"CREW ({count}/{max_crew})"
        header = self.subtitle_font.render(header_text, True, Colors.TEXT_PRIMARY)
        screen.blit(header, (self.PANEL_X + 30, y))

        if not self.available_crew:
            no_crew = self.body_font.render("No crew recruited.", True, Colors.TEXT_SECONDARY)
            screen.blit(no_crew, (self.PANEL_X + 30, y + 35))
            return

        # Draw ability summaries below each crew button
        crew_start_x = self.PANEL_X + 30
        for i, (template, _state) in enumerate(self.available_crew):
            card_x = crew_start_x + i * (self.CREW_CARD_W + self.CREW_CARD_GAP)
            abilities_y = self.CREW_SECTION_Y + 30 + self.CREW_CARD_H + 8

            # Selection indicator
            is_selected = template.id in self.selected_crew
            if is_selected:
                sel_rect = pygame.Rect(
                    card_x - 2,
                    self.CREW_SECTION_Y + 28,
                    self.CREW_CARD_W + 4,
                    self.CREW_CARD_H + 4,
                )
                pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, sel_rect, 2, border_radius=4)

            # Ground abilities text
            abilities = self.get_crew_ground_abilities(template.id)
            for j, ability in enumerate(abilities):
                color = Colors.TEXT_HIGHLIGHT if is_selected else Colors.TEXT_SECONDARY
                surf = self.small_font.render(ability, True, color)
                screen.blit(surf, (card_x + 4, abilities_y + j * 18))
