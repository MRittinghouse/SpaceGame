"""Cantina view — social hub for NPC dialogue, crew hire, and contracts.

After selecting the cantina/social location from the station hub, players
see available NPCs to talk to, crew for hire, and station board contracts.
"""

import pygame
import pygame_gui
from typing import Optional

from spacegame.config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    Colors,
    GameState,
)
from spacegame.views.base_view import BaseView
from spacegame.models.player import Player
from spacegame.models.system import StarSystem
from spacegame.models.location import Location
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import FontCache
from spacegame.utils.logger import logger
from spacegame.engine.audio_manager import get_audio_manager

# Layout constants
HEADER_CARD_Y = 10
HEADER_CARD_H = 70
HEADER_CARD_MARGIN_X = 80

CONTENT_X = 80
CONTENT_W = WINDOW_WIDTH - 160
SECTION_PAD = 14

BUTTON_W = 400
BUTTON_H = 38
BUTTON_PAD = 6

BACK_BUTTON_W = 140
BACK_BUTTON_H = 40


class CantinaView(BaseView):
    """Social hub view for NPC dialogue, crew hire, and station board contracts.

    Replaces the inline cantina expansion on the station hub, giving
    social locations their own dedicated screen with room for multiple
    NPC interactions.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        system: StarSystem,
        location: Location,
        data_loader: object,
        crew_roster: object = None,
        mission_manager: object = None,
    ) -> None:
        """Initialize cantina view.

        Args:
            ui_manager: pygame_gui UI manager.
            player: Current player.
            system: Star system the player is docked at.
            location: Cantina location data (name, description, flavor).
            data_loader: DataLoader for NPC lookups.
            crew_roster: Optional CrewRoster for crew hire/re-recruit.
            mission_manager: Optional MissionManager for station board contracts.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.system = system
        self.location = location
        self.data_loader = data_loader
        self.crew_roster = crew_roster
        self.mission_manager = mission_manager
        self.next_state: Optional[GameState] = None

        # Pending actions for game.py to process
        self.pending_npc_id: Optional[str] = None
        self.pending_rerecruit_id: Optional[str] = None
        self.pending_hire_id: Optional[str] = None
        self.pending_contract_id: Optional[str] = None

        # Fonts
        self.title_font = FontCache.get(32)
        self.subtitle_font = FontCache.get(22)
        self.label_font = FontCache.get(20)
        self.desc_font = FontCache.get(18)
        # UI element refs
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self._npc_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._rerecruit_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._hire_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._contract_buttons: dict[str, pygame_gui.elements.UIButton] = {}

        # Background
        self.background = AnimatedBackground(
            "station", WINDOW_WIDTH, WINDOW_HEIGHT, seed=hash(system.id) % 10000
        )
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(150)

    def on_enter(self) -> None:
        """Activate view and create UI."""
        super().on_enter()
        logger.info(f"Entered cantina: {self.location.name} at {self.system.name}")
        self.next_state = None
        self.pending_npc_id = None
        self.pending_rerecruit_id = None
        self.pending_hire_id = None
        self.pending_contract_id = None
        self._create_ui()

    def on_exit(self) -> None:
        """Deactivate view, clean up UI."""
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create all UI elements."""
        self._destroy_ui()

        # Back button (bottom-left)
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                20, WINDOW_HEIGHT - BACK_BUTTON_H - 20, BACK_BUTTON_W, BACK_BUTTON_H
            ),
            text="BACK",
            manager=self.ui_manager,
        )

        # Build content buttons
        btn_x = WINDOW_WIDTH // 2 - BUTTON_W // 2
        btn_y = HEADER_CARD_Y + HEADER_CARD_H + SECTION_PAD + 30

        # NPC talk buttons with name | title
        npcs = self._get_available_npcs()
        if npcs:
            btn_y += 24  # Space for section label
            for npc in npcs:
                label = f"{npc.name}  |  {npc.title}" if npc.title else npc.name
                btn = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(btn_x, btn_y, BUTTON_W, BUTTON_H),
                    text=label,
                    manager=self.ui_manager,
                )
                self._npc_buttons[npc.id] = btn
                btn_y += BUTTON_H + BUTTON_PAD

        # Dismissed crew for re-recruitment
        if self.crew_roster and hasattr(self.crew_roster, "get_dismissed_at_system"):
            dismissed = self.crew_roster.get_dismissed_at_system(self.system.id)
            if dismissed:
                btn_y += SECTION_PAD + 24  # Gap + label space
                for template, _state in dismissed:
                    cost = self.crew_roster.get_recruit_cost(template.id)
                    cost_text = f"{cost:,} cr" if cost > 0 else "Free"
                    btn = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect(btn_x, btn_y, BUTTON_W, BUTTON_H),
                        text=f"Re-recruit: {template.name} ({cost_text})",
                        manager=self.ui_manager,
                    )
                    crew_slots = self._get_crew_slots()
                    current_crew = self._get_current_crew_count()
                    if self.player.credits < cost or current_crew >= crew_slots:
                        btn.disable()
                    self._rerecruit_buttons[template.id] = btn
                    btn_y += BUTTON_H + BUTTON_PAD

        # Available crew for first-time hire
        if self.crew_roster and hasattr(self.crew_roster, "get_available_crew_at_system"):
            available = self.crew_roster.get_available_crew_at_system(self.system.id)
            if available:
                if not self._rerecruit_buttons:
                    btn_y += SECTION_PAD + 24
                else:
                    btn_y += SECTION_PAD
                crew_slots = self._get_crew_slots()
                current_crew = self._get_current_crew_count()
                for template in available:
                    role_label = template.role.title()
                    btn = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect(btn_x, btn_y, BUTTON_W, BUTTON_H),
                        text=f"Hire: {template.name} ({role_label})",
                        manager=self.ui_manager,
                    )
                    if current_crew >= crew_slots:
                        btn.disable()
                    self._hire_buttons[template.id] = btn
                    btn_y += BUTTON_H + BUTTON_PAD

        # Station board contracts
        if self.mission_manager and hasattr(self.mission_manager, "get_available_at_system"):
            board_missions = [
                m
                for m in self.mission_manager.get_available_at_system(self.system.id)
                if m.discovery_method == "station_board"
            ]
            if board_missions:
                btn_y += SECTION_PAD + 24
                for mission in board_missions[:5]:
                    reward_text = ""
                    for r in mission.rewards:
                        if r.reward_type == "credits":
                            reward_text = f" \u2014 {r.amount:,} CR"
                            break
                    btn = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect(btn_x, btn_y, BUTTON_W, BUTTON_H),
                        text=f"Contract: {mission.name}{reward_text}",
                        manager=self.ui_manager,
                    )
                    self._contract_buttons[mission.id] = btn
                    btn_y += BUTTON_H + BUTTON_PAD

    def _destroy_ui(self) -> None:
        """Kill all UI elements."""
        if self.back_button:
            self.back_button.kill()
            self.back_button = None
        for btn in self._npc_buttons.values():
            btn.kill()
        self._npc_buttons = {}
        for btn in self._rerecruit_buttons.values():
            btn.kill()
        self._rerecruit_buttons = {}
        for btn in self._hire_buttons.values():
            btn.kill()
        self._hire_buttons = {}
        for btn in self._contract_buttons.values():
            btn.kill()
        self._contract_buttons = {}

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle button clicks and keyboard input."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.next_state = GameState.STATION_HUB
                return

        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return

        if event.ui_element == self.back_button:
            self.next_state = GameState.STATION_HUB
            return

        # NPC talk buttons
        for npc_id, btn in self._npc_buttons.items():
            if event.ui_element == btn:
                self.pending_npc_id = npc_id
                self.next_state = GameState.DIALOGUE
                return

        # Re-recruit buttons
        for crew_id, btn in self._rerecruit_buttons.items():
            if event.ui_element == btn:
                self._handle_rerecruit(crew_id)
                return

        # Hire buttons
        for crew_id, btn in self._hire_buttons.items():
            if event.ui_element == btn:
                self._handle_hire(crew_id)
                return

        # Contract buttons
        for mission_id, btn in self._contract_buttons.items():
            if event.ui_element == btn:
                self._handle_accept_contract(mission_id)
                return

    def update(self, dt: float) -> None:
        """Update background animation."""
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """Render cantina view."""
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Header card
        self._render_header(screen)

        # Section labels
        self._render_section_labels(screen)

    def _render_header(self, screen: pygame.Surface) -> None:
        """Render header card with cantina name and description."""
        card_x = HEADER_CARD_MARGIN_X
        card_y = HEADER_CARD_Y
        card_w = WINDOW_WIDTH - HEADER_CARD_MARGIN_X * 2
        card_h = HEADER_CARD_H

        draw_panel(screen, (card_x, card_y, card_w, card_h), alpha=180)

        # Accent line
        accent = (255, 200, 50)  # Cantina yellow
        pygame.draw.rect(screen, accent, (card_x, card_y, card_w, 2))

        # Cantina name
        title = self.title_font.render(self.location.name.upper(), True, accent)
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, card_y + 8))

        # Description
        desc = self.desc_font.render(self.location.description, True, Colors.TEXT_SECONDARY)
        screen.blit(desc, (WINDOW_WIDTH // 2 - desc.get_width() // 2, card_y + 40))

    def _render_section_labels(self, screen: pygame.Surface) -> None:
        """Render section labels above button groups."""
        label_x = WINDOW_WIDTH // 2 - BUTTON_W // 2
        btn_y = HEADER_CARD_Y + HEADER_CARD_H + SECTION_PAD + 30

        if self._npc_buttons:
            label = self.label_font.render("Contacts", True, Colors.TEXT_HIGHLIGHT)
            screen.blit(label, (label_x, btn_y - 2))
            btn_y += 24 + len(self._npc_buttons) * (BUTTON_H + BUTTON_PAD)

        has_crew_section = self._rerecruit_buttons or self._hire_buttons
        if has_crew_section:
            btn_y += SECTION_PAD
            label = self.label_font.render("Crew", True, Colors.TEXT_HIGHLIGHT)
            screen.blit(label, (label_x, btn_y - 2))
            # Show slot count
            if self.crew_roster:
                current = self._get_current_crew_count()
                total = self._get_crew_slots()
                slot_text = f"{current}/{total} Slots"
                slot_color = Colors.TEXT_SECONDARY if current < total else Colors.RED
                slot_surf = self.desc_font.render(slot_text, True, slot_color)
                screen.blit(slot_surf, (label_x + BUTTON_W - slot_surf.get_width(), btn_y))
            btn_y += 24 + (
                len(self._rerecruit_buttons) + len(self._hire_buttons)
            ) * (BUTTON_H + BUTTON_PAD)
            if self._rerecruit_buttons and self._hire_buttons:
                btn_y += SECTION_PAD  # Extra pad between re-recruit and hire

        if self._contract_buttons:
            btn_y += SECTION_PAD
            label = self.label_font.render("Station Board", True, Colors.TEXT_HIGHLIGHT)
            screen.blit(label, (label_x, btn_y - 2))

    # === Action handlers ===

    def _handle_rerecruit(self, crew_id: str) -> None:
        """Process re-recruitment of a dismissed crew member."""
        if not self.crew_roster:
            return
        cost = self.crew_roster.get_recruit_cost(crew_id)
        if self.player.credits < cost:
            return
        crew_slots = self._get_crew_slots()
        self.player.credits -= cost
        success, msg = self.crew_roster.recruit(crew_id, crew_slots)
        if success:
            self.pending_rerecruit_id = crew_id
            get_audio_manager().play_sfx("ui_confirm")
            self._create_ui()
        else:
            self.player.credits += cost

    def _handle_hire(self, crew_id: str) -> None:
        """Process first-time hire of a crew member."""
        if not self.crew_roster:
            return
        crew_slots = self._get_crew_slots()
        success, msg = self.crew_roster.recruit(crew_id, crew_slots)
        if success:
            self.pending_hire_id = crew_id
            get_audio_manager().play_sfx("ui_confirm")
            self._create_ui()

    def _handle_accept_contract(self, mission_id: str) -> None:
        """Accept a station board contract mission."""
        if not self.mission_manager:
            return
        success, msg = self.mission_manager.accept_mission(mission_id)
        if success:
            self.pending_contract_id = mission_id
            mission = self.mission_manager.get_mission(mission_id)
            if mission and mission.on_accept_cargo:
                for cargo in mission.on_accept_cargo:
                    self.player.ship.add_cargo(cargo.commodity_id, cargo.quantity, 0)
            get_audio_manager().play_sfx("ui_confirm")
            self._create_ui()

    # === NPC filtering ===

    def _get_available_npcs(self) -> list:
        """Get NPCs available at the current system, filtered by story flags."""
        if not hasattr(self.data_loader, "get_npcs_at_system"):
            return []
        all_npcs = self.data_loader.get_npcs_at_system(self.system.id)
        return [npc for npc in all_npcs if self._is_npc_available(npc)]

    def _is_npc_available(self, npc: object) -> bool:
        """Check if an NPC should appear in the cantina."""
        flags = self.player.dialogue_flags
        if npc.hide_after_flag and flags.get(npc.hide_after_flag, False):
            return False
        if npc.auto_trigger_gate_flag and flags.get(npc.auto_trigger_gate_flag, False):
            return False
        if npc.auto_trigger_prerequisites:
            if not all(flags.get(f, False) for f in npc.auto_trigger_prerequisites):
                return False
        return True

    # === Crew helpers ===

    def _get_crew_slots(self) -> int:
        """Get total crew slots including skill bonuses."""
        return self.player.ship.ship_type.crew_slots + int(
            self.player.progression.get_bonus("crew_slot_bonus")
        )

    def _get_current_crew_count(self) -> int:
        """Get number of currently recruited crew members."""
        if self.crew_roster and hasattr(self.crew_roster, "_recruited"):
            return len(self.crew_roster._recruited)
        return 0

    def get_next_state(self) -> Optional[GameState]:
        """Return pending state transition."""
        return self.next_state
