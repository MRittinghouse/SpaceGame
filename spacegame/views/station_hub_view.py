"""Station hub view — location selection screen.

After arriving at a system, players see available locations (market, repair bay,
cantina, activities, shipyard, unique POIs) and choose where to go. This replaces
the direct galaxy-map-to-trading transition.
"""

import random
from typing import Optional

import pygame
import pygame_gui

from spacegame.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_x,
    scale_y,
)
from spacegame.engine.activity_registry import ActivityRegistry
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_LG,
    FONT_MD,
    FONT_SM2,
    FONT_TITLE,
    FONT_XL,
    FONT_XL2,
    FONT_XS,
    get_font,
)
from spacegame.engine.sprites import get_sprite_manager, res_scale
from spacegame.models.location import Location
from spacegame.models.player import Player
from spacegame.models.system import StarSystem
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.station_layouts import create_station_layout

# Location type → GameState mapping
_LOCATION_STATE_MAP: dict[str, GameState] = {
    "market": GameState.TRADING,
    "repair_bay": GameState.REPAIR_BAY,
    "cantina": GameState.CANTINA,
    "mining": GameState.MINING,
    "salvaging": GameState.SALVAGING,
    "refining": GameState.REFINING,
    "shipyard": GameState.SHIPYARD,
    "investment": GameState.INVESTMENT,
}

# Location type → accent color for card rendering
_LOCATION_COLORS: dict[str, tuple[int, int, int]] = {
    "market": (100, 200, 255),  # Blue — commerce
    "repair_bay": (50, 200, 100),  # Green — repair
    "cantina": (255, 200, 50),  # Yellow — social
    "mining": (180, 80, 30),  # Rust — mining
    "salvaging": (140, 170, 200),  # Steel — salvage
    "refining": (255, 160, 40),  # Orange — industrial
    "shipyard": (100, 180, 240),  # Sky blue — upgrades
    "unique": (200, 160, 255),  # Purple — special
    "investment": (200, 180, 80),  # Gold — investment
}

# Location type → short label for card rendering
_LOCATION_LABELS: dict[str, str] = {
    "market": "TRADE",
    "repair_bay": "REPAIR",
    "cantina": "SOCIAL",
    "mining": "MINING",
    "salvaging": "SALVAGE",
    "refining": "REFINE",
    "shipyard": "SHIPS",
    "unique": "EXPLORE",
    "investment": "INVEST",
}

# Faction name → color
_FACTION_COLORS: dict[str, tuple[int, int, int]] = {
    "commerce_guild": Colors.FACTION_COMMERCE,
    "miners_union": Colors.FACTION_MINERS,
    "science_collective": Colors.FACTION_SCIENCE,
    "frontier_alliance": Colors.FACTION_FRONTIER,
}

# Layout constants
HEADER_CARD_Y = 10
HEADER_CARD_H = scale_y(105)
HEADER_CARD_MARGIN_X = scale_x(80)

CARD_W = scale_x(370)
CARD_H = scale_y(80)
CARD_PAD = 10
CARDS_PER_ROW = 3
CARD_AREA_X = (WINDOW_WIDTH - (CARDS_PER_ROW * CARD_W + (CARDS_PER_ROW - 1) * CARD_PAD)) // 2

CHATTER_CARD_X = scale_x(80)
CHATTER_CARD_Y = WINDOW_HEIGHT - scale_y(185)
CHATTER_CARD_W = scale_x(960)
CHATTER_CARD_H = scale_y(75)

BACK_BUTTON_W = scale_x(140)
BACK_BUTTON_H = scale_y(40)
DETAIL_PANEL_X = scale_x(60)
DETAIL_PANEL_W = WINDOW_WIDTH - scale_x(120)
FLAVOR_ROTATION_INTERVAL = 10.0  # Seconds between flavor text changes

# Station atmosphere descriptions — evocative one-liners per system
STATION_ATMOSPHERE: dict[str, str] = {
    "nexus_prime": "The hum of commerce never stops. Credits change hands faster than handshakes.",
    "forgeworks": "Soot-stained corridors and the constant clang of metal on metal. This place builds things.",
    "breakstone": "Dust in the air, ore in the holds. Miners drink hard and work harder.",
    "stellaris_port": "Polished floors and curated art. Everything here costs more than it should.",
    "iron_depths": "Deep below the surface, where the lights flicker and the walls groan.",
    "verdant": "Green spaces and open skies on the observation deck. A breath of something real.",
    "havens_rest": "Quiet corridors, warm lights. The frontier's idea of civilization.",
    "axiom_labs": "Sterile halls and sealed doors. Whatever they're researching, it's not for you.",
    "nova_research": "Screens glow in every corner. The people here talk in equations.",
    "crimson_reach": "Keep your hand on your wallet and your back to the wall.",
    "the_fulcrum": "Military checkpoints and the distant thrum of patrol engines. Eyes everywhere.",
}


class StationHubView(BaseView):
    """Location selection screen for a docked station.

    Displays available locations as clickable cards. Cantina expands
    to show NPC talk buttons inline. Unique locations show a lore panel.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        system: StarSystem,
        locations: list[Location],
        activity_registry: ActivityRegistry,
        data_loader: object,
        politics_manager: object = None,
        crew_roster: object = None,
        station_chatter: object = None,
        mission_manager: object = None,
    ) -> None:
        """Initialize station hub view.

        Args:
            ui_manager: pygame_gui UI manager.
            player: Current player.
            system: Star system the player is docked at.
            locations: Available locations at this system.
            activity_registry: For resolving activity availability.
            data_loader: DataLoader instance for NPC lookups.
            politics_manager: Optional PoliticsManager for docking checks.
            crew_roster: Optional CrewRoster for re-recruitment at cantina.
            station_chatter: Optional StationChatterManager for ambient text.
            mission_manager: Optional MissionManager for station board contracts.
        """
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.system = system
        self.locations = locations
        self.activity_registry = activity_registry
        self.data_loader = data_loader
        self.politics_manager = politics_manager
        self.crew_roster = crew_roster
        self.station_chatter = station_chatter
        self.mission_manager = mission_manager
        self.next_state: Optional[GameState] = None
        self.docking_denied = False
        self._docking_denied_msg = ""

        # Cantina state
        self.cantina_expanded = False
        self.pending_npc_id: Optional[str] = None
        self.pending_rerecruit_id: Optional[str] = None
        self.pending_hire_id: Optional[str] = None

        # Detail panel (for unique locations)
        self._detail_location: Optional[Location] = None

        # Faction color for header accent
        self._faction_color = _FACTION_COLORS.get(system.faction, Colors.TEXT_HIGHLIGHT)

        # Flavor text rotation
        self._flavor_texts = [loc.flavor_text for loc in locations if loc.flavor_text]
        self._flavor_index = 0
        self._flavor_timer = 0.0
        if self._flavor_texts:
            rng = random.Random(hash(system.id))
            rng.shuffle(self._flavor_texts)

        # Fonts — role-based for narrative immersion
        self.title_font = get_font("header", FONT_TITLE)  # "DOCKED — NEXUS PRIME"
        self.subtitle_font = get_font("narration", FONT_LG)  # Station description
        self.flavor_font = get_font("narration", FONT_MD)  # Atmosphere text
        self.card_name_font = get_font("dialogue", FONT_XL)  # Location names
        self.card_desc_font = get_font("dialogue", FONT_BODY)  # Location descriptions
        self.card_detail_font = get_font("label", FONT_SM2)  # Card detail labels
        self.card_label_font = get_font("label", FONT_XS)  # "TRADE", "REPAIR" badges
        self.detail_title_font = get_font("header", FONT_XL2)  # Detail panel headers
        self.detail_font = get_font("dialogue", FONT_BODY)  # Detail panel body
        self.npc_font = get_font("dialogue", FONT_BODY)  # NPC names and speech
        self.chatter_font = get_font("narration", FONT_BODY)  # Station ambient chatter

        # UI element refs
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self._npc_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._rerecruit_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._hire_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self._contract_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self.pending_contract_id: Optional[str] = None
        self._detail_close_button: Optional[pygame_gui.elements.UIButton] = None

        # Sprite manager for faction emblems
        self._sprite_mgr = get_sprite_manager()
        self._faction_emblem: Optional[pygame.Surface] = self._sprite_mgr.get_faction_emblem(
            system.faction, scale=res_scale(2)
        )

        # Faction-specific station layout (created in _create_ui)
        self._station_layout: Optional[object] = None

        # Background
        self.background = AnimatedBackground(
            "station", WINDOW_WIDTH, WINDOW_HEIGHT, seed=hash(system.id) % 10000
        )
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        """Activate view, restore shields, create UI."""
        super().on_enter()
        logger.info(f"Entered station hub at {self.system.name}")

        # Check docking permission (HOSTILE faction denies access)
        self.docking_denied = False
        self._docking_denied_msg = ""
        if self.politics_manager:
            allowed, msg = self.politics_manager.get_docking_allowed(self.player, self.system.id)
            if not allowed:
                self.docking_denied = True
                self._docking_denied_msg = msg
                logger.info(f"Docking denied at {self.system.name}: {msg}")
                self._create_denied_ui()
                return

        # Docking restores shields
        self.player.ship.restore_shields()

        # Inject station chatter into flavor text pool
        if self.station_chatter:
            try:
                rep = 0
                if hasattr(self.player, "faction_reputation"):
                    rep = self.player.faction_reputation.get(self.system.faction, 0)
                chatter_lines = self.station_chatter.get_chatter(self.system.id, rep, [], count=3)
                if chatter_lines:
                    self._flavor_texts = chatter_lines + self._flavor_texts
                    self._flavor_index = 0
            except Exception:
                pass  # Chatter is non-critical ambient flavor

        self.cantina_expanded = False
        self.pending_npc_id = None
        self._detail_location = None
        self._create_ui()

    def on_exit(self) -> None:
        """Deactivate view, clean up UI."""
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create location card buttons and back button."""
        self._destroy_ui()

        # Back button (bottom-left, above HUD bar)
        from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT

        hud_h = scale_y(HUD_BASE_HEIGHT)
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                20,
                WINDOW_HEIGHT - hud_h - BACK_BUTTON_H - scale_y(15),
                BACK_BUTTON_W,
                BACK_BUTTON_H,
            ),
            text="UNDOCK",
            manager=self.ui_manager,
        )

        # Create faction-specific station layout (replaces card buttons)
        self._station_layout = create_station_layout(
            self.locations, self.system.id, self._sprite_mgr
        )

    def _create_denied_ui(self) -> None:
        """Create minimal UI for docking denial — only a Leave button."""
        self._destroy_ui()
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH // 2 - 70,
                WINDOW_HEIGHT // 2 + 60,
                140,
                BACK_BUTTON_H,
            ),
            text="LEAVE",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        """Kill all UI elements."""
        if self.back_button:
            self.back_button.kill()
            self.back_button = None
        self._station_layout = None
        self._destroy_npc_buttons()
        if self._detail_close_button:
            self._detail_close_button.kill()
            self._detail_close_button = None

    def _destroy_npc_buttons(self) -> None:
        """Kill cantina NPC, re-recruit, hire, and contract buttons."""
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

    def _create_npc_buttons(self) -> None:
        """Create NPC talk, re-recruit, and hire buttons for expanded cantina."""
        self._destroy_npc_buttons()
        npcs = self._get_cantina_npcs()
        # Position below the station layout zones
        if self._station_layout and self._station_layout.zones:
            base_y = max(z.rect.bottom for z in self._station_layout.zones) + scale_y(10)
        else:
            base_y = CHATTER_CARD_Y - scale_y(100)
        btn_index = 0
        for npc in npcs:
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    CARD_AREA_X,
                    base_y + btn_index * 38,
                    300,
                    34,
                ),
                text=f"Talk: {npc.name}",
                manager=self.ui_manager,
            )
            self._npc_buttons[npc.id] = btn
            btn_index += 1

        # Dismissed crew available for re-recruitment at this system
        if self.crew_roster and hasattr(self.crew_roster, "get_dismissed_at_system"):
            dismissed = self.crew_roster.get_dismissed_at_system(self.system.id)
            for template, _state in dismissed:
                cost = self.crew_roster.get_recruit_cost(template.id)
                cost_text = f"{cost:,} cr" if cost > 0 else "Free"
                btn = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(
                        CARD_AREA_X,
                        base_y + btn_index * 38,
                        300,
                        34,
                    ),
                    text=f"Re-recruit: {template.name} ({cost_text})",
                    manager=self.ui_manager,
                )
                # Disable if can't afford or no crew slots
                crew_slots = self._get_crew_slots()
                current_crew = self._get_current_crew_count()
                if self.player.credits < cost or current_crew >= crew_slots:
                    btn.disable()
                self._rerecruit_buttons[template.id] = btn
                btn_index += 1

        # Available crew for first-time hire at this system
        if self.crew_roster and hasattr(self.crew_roster, "get_available_crew_at_system"):
            available = self.crew_roster.get_available_crew_at_system(self.system.id)
            if available:
                crew_slots = self._get_crew_slots()
                current_crew = self._get_current_crew_count()
                for template in available:
                    role_label = template.role.title()
                    btn = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect(
                            CARD_AREA_X,
                            base_y + btn_index * 38,
                            300,
                            34,
                        ),
                        text=f"Hire: {template.name} ({role_label})",
                        manager=self.ui_manager,
                    )
                    if current_crew >= crew_slots:
                        btn.disable()
                    self._hire_buttons[template.id] = btn
                    btn_index += 1

        # Station board contracts (procedural missions)
        if self.mission_manager and hasattr(self.mission_manager, "get_available_at_system"):
            board_missions = [
                m
                for m in self.mission_manager.get_available_at_system(self.system.id)
                if m.discovery_method == "station_board"
            ]
            if board_missions:
                btn_index += 1  # Gap before contracts section
                for mission in board_missions[:5]:  # Cap at 5 visible
                    reward_text = ""
                    for r in mission.rewards:
                        if r.reward_type == "credits":
                            reward_text = f" — {r.amount:,} CR"
                            break
                    btn = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect(
                            CARD_AREA_X,
                            base_y + btn_index * 38,
                            300,
                            34,
                        ),
                        text=f"Contract: {mission.name[:30]}{reward_text}",
                        manager=self.ui_manager,
                    )
                    self._contract_buttons[mission.id] = btn
                    btn_index += 1

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle card clicks and navigation."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self._request_back()
                return

            if event.ui_element == self._detail_close_button:
                self._detail_location = None
                if self._detail_close_button:
                    self._detail_close_button.kill()
                    self._detail_close_button = None
                return

            # Check NPC buttons
            for npc_id, btn in self._npc_buttons.items():
                if event.ui_element == btn:
                    self._select_npc(npc_id)
                    return

            # Check re-recruit buttons
            for crew_id, btn in self._rerecruit_buttons.items():
                if event.ui_element == btn:
                    self._handle_rerecruit(crew_id)
                    return

            # Check hire buttons
            for crew_id, btn in self._hire_buttons.items():
                if event.ui_element == btn:
                    self._handle_hire(crew_id)
                    return

            # Check contract buttons (station board)
            for mission_id, btn in self._contract_buttons.items():
                if event.ui_element == btn:
                    self._handle_accept_contract(mission_id)
                    return

        # Check station layout zone clicks
        if self._station_layout and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            zone = self._station_layout.get_clicked_zone(event.pos)
            if zone:
                get_audio_manager().play_sfx("ui_confirm")
                self._select_location_type(zone.location.location_type)
                if zone.location.location_type == "unique":
                    self._detail_location = zone.location
                return

        # Keyboard: Escape to undock
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._request_back()

    def update(self, dt: float) -> None:
        """Update background animation, layout hover, and flavor text rotation."""
        self.background.update(dt)
        if self._station_layout:
            self._station_layout.handle_hover(pygame.mouse.get_pos())
            self._station_layout.update(dt)
        if self._flavor_texts:
            self._flavor_timer += dt
            if self._flavor_timer >= FLAVOR_ROTATION_INTERVAL:
                self._flavor_timer = 0.0
                self._flavor_index = (self._flavor_index + 1) % len(self._flavor_texts)

    def render(self, screen: pygame.Surface) -> None:
        """Render station hub."""
        # Background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Docking denied overlay
        if self.docking_denied:
            self._render_denied(screen)
            return

        # Header: system name + description
        self._render_header(screen)

        # Faction-specific station layout zones
        if self._station_layout:
            self._station_layout.render_background(screen)
            self._station_layout.render_zones(screen)
            self._station_layout.render_atmosphere(screen)

        # Station chatter (bottom card)
        self._render_chatter(screen)

        # Detail panel for unique locations
        if self._detail_location:
            self._render_detail_panel(screen)

        # Status bar removed — HUD bar now handles credits, hull, shields, fuel

    def _render_denied(self, screen: pygame.Surface) -> None:
        """Render docking denial overlay."""
        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2

        # System name
        title = self.title_font.render(self.system.name.upper(), True, Colors.RED)
        screen.blit(title, (cx - title.get_width() // 2, cy - 80))

        # Denial message
        msg = self.subtitle_font.render(self._docking_denied_msg, True, Colors.TEXT)
        screen.blit(msg, (cx - msg.get_width() // 2, cy - 30))

        # Help text
        help_text = self.card_desc_font.render(
            "Your reputation is too low to dock here.",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(help_text, (cx - help_text.get_width() // 2, cy + 10))

    def _render_header(self, screen: pygame.Surface) -> None:
        """Render header card with system name, description, atmosphere, and faction."""
        fc = self._faction_color
        card_x = HEADER_CARD_MARGIN_X
        card_y = HEADER_CARD_Y
        card_w = WINDOW_WIDTH - HEADER_CARD_MARGIN_X * 2
        card_h = HEADER_CARD_H

        # Semi-transparent header card
        draw_panel(screen, (card_x, card_y, card_w, card_h), alpha=180)

        # Faction accent line at top of card
        pygame.draw.rect(screen, fc, (card_x, card_y, card_w, 2))

        # System name in faction color
        title = self.title_font.render(f"DOCKED \u2014 {self.system.name.upper()}", True, fc)
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, card_y + 8))

        # Station description
        station = self.system.get_main_station()
        if station:
            desc = self.subtitle_font.render(station.description, True, Colors.TEXT_SECONDARY)
            screen.blit(desc, (WINDOW_WIDTH // 2 - desc.get_width() // 2, card_y + 38))

        # Atmosphere description
        atmosphere = STATION_ATMOSPHERE.get(self.system.id, "")
        if atmosphere:
            atmo_surf = self.card_desc_font.render(atmosphere, True, fc)
            atmo_surf.set_alpha(160)
            screen.blit(
                atmo_surf,
                (WINDOW_WIDTH // 2 - atmo_surf.get_width() // 2, card_y + 58),
            )

        # Faction + danger with faction color dot
        faction_name = self.system.faction.replace("_", " ").title()
        info_text = f"{faction_name}  |  Danger: {self.system.danger_level.title()}"
        info = self.card_desc_font.render(info_text, True, Colors.TEXT_SECONDARY)
        info_x = WINDOW_WIDTH // 2 - info.get_width() // 2
        screen.blit(info, (info_x, card_y + 78))
        # Faction emblem or small color dot before faction name
        if self._faction_emblem:
            emblem_rect = self._faction_emblem.get_rect(midright=(info_x - 6, card_y + 78 + 10))
            screen.blit(self._faction_emblem, emblem_rect)
        else:
            pygame.draw.circle(screen, fc, (info_x - 10, card_y + 78 + 10), 4)

    def _render_detail_panel(self, screen: pygame.Surface) -> None:
        """Render detail panel for unique/expanded locations."""
        loc = self._detail_location
        if not loc:
            return

        # Pre-calculate content height for dynamic panel sizing
        content_w = DETAIL_PANEL_W - 40
        header_h = 52  # Title + divider
        desc_lines = self._count_wrapped_lines(loc.description, self.detail_font, content_w)
        flavor_lines = 0
        if loc.flavor_text:
            flavor_lines = self._count_wrapped_lines(
                f'"{loc.flavor_text}"', self.detail_font, content_w - 24
            ) + 1  # +1 for gap
        line_h = self.detail_font.get_linesize()
        panel_h = header_h + (desc_lines + flavor_lines) * line_h + 70  # 70 for padding + close btn
        panel_h = max(180, min(panel_h, 450))  # Allow taller panels for long flavor text
        panel_y = WINDOW_HEIGHT - panel_h - 60
        accent = _LOCATION_COLORS.get(loc.location_type, Colors.UI_BORDER)

        # Semi-transparent panel
        draw_panel(
            screen,
            (DETAIL_PANEL_X, panel_y, DETAIL_PANEL_W, panel_h),
            alpha=230,
            border_color=accent,
        )
        # Top accent bar
        pygame.draw.rect(screen, accent, (DETAIL_PANEL_X, panel_y, DETAIL_PANEL_W, 3))

        # Title in accent color
        title = self.detail_title_font.render(loc.name, True, accent)
        screen.blit(title, (DETAIL_PANEL_X + 20, panel_y + 14))

        # Divider line
        div_y = panel_y + 42
        pygame.draw.line(
            screen,
            Colors.UI_BORDER,
            (DETAIL_PANEL_X + 20, div_y),
            (DETAIL_PANEL_X + DETAIL_PANEL_W - 20, div_y),
        )

        # Word-wrapped description
        content_x = DETAIL_PANEL_X + 20
        content_w = DETAIL_PANEL_W - 40
        y_cursor = div_y + 10
        y_cursor = self._render_wrapped_text(
            screen,
            loc.description,
            self.detail_font,
            Colors.TEXT_PRIMARY,
            content_x,
            y_cursor,
            content_w,
        )

        # Flavor text (italic feel via secondary color + indent)
        if loc.flavor_text:
            y_cursor += 8
            self._render_wrapped_text(
                screen,
                f'"{loc.flavor_text}"',
                self.detail_font,
                Colors.TEXT_SECONDARY,
                content_x + 12,
                y_cursor,
                content_w - 24,
            )

        # Close button
        if not self._detail_close_button:
            self._detail_close_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    DETAIL_PANEL_X + DETAIL_PANEL_W - 90,
                    panel_y + panel_h - 40,
                    70,
                    30,
                ),
                text="Close",
                manager=self.ui_manager,
            )

    def _render_wrapped_text(
        self,
        screen: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        x: int,
        y: int,
        max_width: int,
    ) -> int:
        """Render word-wrapped text. Returns y position after last line."""
        words = text.split()
        line = ""
        line_y = y
        for word in words:
            test = f"{line} {word}".strip()
            if font.size(test)[0] > max_width and line:
                surf = font.render(line, True, color)
                screen.blit(surf, (x, line_y))
                line_y += font.get_linesize()
                line = word
            else:
                line = test
        if line:
            surf = font.render(line, True, color)
            screen.blit(surf, (x, line_y))
            line_y += font.get_linesize()
        return line_y

    def _count_wrapped_lines(self, text: str, font: pygame.font.Font, max_width: int) -> int:
        """Count how many lines word-wrapped text will take."""
        words = text.split()
        line = ""
        count = 0
        for word in words:
            test = f"{line} {word}".strip()
            if font.size(test)[0] > max_width and line:
                count += 1
                line = word
            else:
                line = test
        if line:
            count += 1
        return max(1, count)

    def _render_chatter(self, screen: pygame.Surface) -> None:
        """Render station chatter in a card at the bottom of the screen."""
        if not self._flavor_texts:
            return

        card_x = CHATTER_CARD_X
        card_y = CHATTER_CARD_Y
        card_w = CHATTER_CARD_W
        card_h = CHATTER_CARD_H

        draw_panel(screen, (card_x, card_y, card_w, card_h), alpha=160)

        flavor = self._flavor_texts[self._flavor_index]

        # Fade effect on rotation
        alpha = 255
        if self._flavor_timer < 0.5:
            alpha = int(255 * (self._flavor_timer / 0.5))
        elif self._flavor_timer > FLAVOR_ROTATION_INTERVAL - 0.5:
            alpha = int(255 * ((FLAVOR_ROTATION_INTERVAL - self._flavor_timer) / 0.5))

        # Word-wrap chatter text into up to 3 lines
        words = flavor.split()
        lines: list[str] = []
        line = ""
        max_w = card_w - 32
        for word in words:
            test = f"{line} {word}".strip()
            if self.chatter_font.size(test)[0] > max_w and line:
                lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)

        y = card_y + 10
        for text_line in lines[:3]:
            surf = self.chatter_font.render(text_line, True, Colors.TEXT_SECONDARY)
            surf.set_alpha(alpha)
            screen.blit(surf, (card_x + 16, y))
            y += self.chatter_font.get_linesize()

    def _render_status_bar(self, screen: pygame.Surface) -> None:
        """Render ship status readout at bottom-right."""
        ship = self.player.ship
        max_hull = ship.ship_type.combat_hull
        max_shields = ship.ship_type.combat_shields

        # Status items: (label, value, color)
        hull_ratio = ship.current_hull / max_hull if max_hull > 0 else 1.0
        hull_color = (
            Colors.GREEN
            if hull_ratio > 0.5
            else (Colors.YELLOW if hull_ratio > 0.25 else Colors.RED)
        )
        items = [
            ("Credits", f"{self.player.credits:,} CR", Colors.TEXT_HIGHLIGHT),
            ("Hull", f"{ship.current_hull}/{max_hull}", hull_color),
            ("Shields", f"{ship.current_shields}/{max_shields}", Colors.BLUE),
            ("Fuel", f"{ship.current_fuel}/{ship.ship_type.fuel_capacity}", Colors.TEXT_SECONDARY),
        ]

        # Criminal heat indicator (only shown when > 0)
        from spacegame.config import get_heat_display_color

        heat_color = get_heat_display_color(self.player.criminal_heat)
        if heat_color:
            items.append(("Heat", str(self.player.criminal_heat), heat_color))

        # Background strip
        bar_h = len(items) * 20 + 12
        bar_y = WINDOW_HEIGHT - bar_h - 10
        bar_w = 200
        bar_x = WINDOW_WIDTH - bar_w - 12
        bg = pygame.Surface((bar_w, bar_h))
        bg.fill((10, 12, 25))
        bg.set_alpha(180)
        screen.blit(bg, (bar_x, bar_y))
        pygame.draw.rect(screen, Colors.UI_BORDER, (bar_x, bar_y, bar_w, bar_h), 1)

        y = bar_y + 6
        for label, value, color in items:
            lbl = self.card_desc_font.render(f"{label}:", True, Colors.TEXT_SECONDARY)
            val = self.card_desc_font.render(value, True, color)
            screen.blit(lbl, (bar_x + 8, y))
            screen.blit(val, (bar_x + bar_w - val.get_width() - 8, y))
            y += 20

    # === Navigation helpers ===

    def _request_back(self) -> None:
        """Navigate back to galaxy map."""
        self.next_state = GameState.GALAXY_MAP

    def _select_location_type(self, location_type: str) -> None:
        """Handle selection of a location type.

        Args:
            location_type: The type of location selected.
        """
        # Unique locations show detail panel (no state transition)
        if location_type == "unique":
            return

        # Everything else transitions to the appropriate GameState
        target = _LOCATION_STATE_MAP.get(location_type)
        if target:
            self.next_state = target

    def _select_npc(self, npc_id: str) -> None:
        """Select an NPC to talk to from the cantina.

        Args:
            npc_id: ID of the NPC to initiate dialogue with.
        """
        self.pending_npc_id = npc_id
        self.next_state = GameState.DIALOGUE

    def _handle_rerecruit(self, crew_id: str) -> None:
        """Process re-recruitment of a dismissed crew member.

        Args:
            crew_id: Template ID of the crew member to re-recruit.
        """
        if not self.crew_roster:
            return
        cost = self.crew_roster.get_recruit_cost(crew_id)
        if self.player.credits < cost:
            return
        crew_slots = self._get_crew_slots()
        self.player.credits -= cost
        success, _msg = self.crew_roster.recruit(crew_id, crew_slots)
        if success:
            self.pending_rerecruit_id = crew_id
            get_audio_manager().play_sfx("ui_confirm")
            # Refresh cantina buttons to remove the re-recruited crew
            self._create_npc_buttons()
        else:
            # Refund if recruit failed
            self.player.credits += cost

    def _handle_hire(self, crew_id: str) -> None:
        """Process first-time hire of a crew member.

        Args:
            crew_id: Template ID of the crew member to hire.
        """
        if not self.crew_roster:
            return
        crew_slots = self._get_crew_slots()
        success, _msg = self.crew_roster.recruit(crew_id, crew_slots)
        if success:
            self.pending_hire_id = crew_id
            get_audio_manager().play_sfx("ui_confirm")
            # Refresh cantina buttons to remove the hired crew
            self._create_npc_buttons()

    def _handle_accept_contract(self, mission_id: str) -> None:
        """Accept a station board contract mission.

        Args:
            mission_id: ID of the procedural mission to accept.
        """
        if not self.mission_manager:
            return
        success, _msg = self.mission_manager.accept_mission(mission_id)
        if success:
            self.pending_contract_id = mission_id
            # Set accepted flag so NPCs gated on this mission can appear
            self.player.dialogue_flags[f"{mission_id}_accepted"] = True
            # Grant on_accept_cargo if any
            mission = self.mission_manager.get_mission(mission_id)
            if mission and mission.on_accept_cargo:
                for cargo in mission.on_accept_cargo:
                    self.player.ship.add_cargo(cargo.commodity_id, cargo.quantity, 0)
            get_audio_manager().play_sfx("ui_confirm")
            # Refresh buttons to remove the accepted contract
            self._create_npc_buttons()

    def _get_cantina_npcs(self) -> list:
        """Get NPCs available at the current system.

        Filters NPCs based on story progression:
        - hide_after_flag set → hidden (e.g., Officer Larsen after permit)
        - auto_trigger_gate_flag set → hidden (dialogue already happened)
        - auto_trigger_prerequisites not met → hidden (story not reached)

        Returns:
            List of NPC objects at this system.
        """
        if not hasattr(self.data_loader, "get_npcs_at_system"):
            return []
        all_npcs = self.data_loader.get_npcs_at_system(self.system.id)
        return [npc for npc in all_npcs if self._is_npc_available(npc)]

    def _is_npc_available(self, npc: object) -> bool:
        """Check if an NPC should appear in the cantina.

        Args:
            npc: NPC object with dialogue flag fields.

        Returns:
            True if the NPC should be visible.
        """
        flags = self.player.dialogue_flags
        # Hide if hide_after_flag is set
        if npc.hide_after_flag and flags.get(npc.hide_after_flag, False):
            return False
        # Hide if gate flag already triggered (dialogue already happened)
        if npc.auto_trigger_gate_flag and flags.get(npc.auto_trigger_gate_flag, False):
            return False
        # Hide if prerequisites not yet met
        if npc.auto_trigger_prerequisites:
            if not all(flags.get(f, False) for f in npc.auto_trigger_prerequisites):
                return False
        return True

    def get_next_state(self) -> Optional[GameState]:
        """Return pending state transition."""
        return self.next_state
