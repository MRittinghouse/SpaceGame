"""Persistent cockpit HUD bar rendered at the bottom of gameplay screens.

Displays ship status (hull, shield, fuel), quick-access navigation buttons
with notification badges, credits, cargo capacity, and active quest hint.
Visual skin adapts to context: cockpit instruments when in space, station
chrome when docked.
"""

from enum import Enum
from typing import Optional

import pygame

from spacegame.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_x,
    scale_y,
)
from spacegame.engine.fonts import (
    FONT_MD,
    FONT_SM,
    FONT_XS,
    get_font,
)
from spacegame.models.mission import MissionStatus
from spacegame.utils.logger import logger

# Height of the cockpit HUD bar (at 720p base)
HUD_BASE_HEIGHT = 90


class HUDContext(Enum):
    """Visual context for the HUD bar."""

    HIDDEN = "hidden"
    SHIP = "ship"  # In space / on the ship — cockpit instruments
    STATION = "station"  # Docked at a station — station interior chrome


# Map GameState → HUD context
_STATE_CONTEXT: dict[GameState, HUDContext] = {
    # Ship context: flying, managing ship systems
    GameState.GALAXY_MAP: HUDContext.SHIP,
    GameState.CHARACTER: HUDContext.SHIP,
    GameState.SKILL_TREE: HUDContext.SHIP,
    GameState.CREW_ROSTER: HUDContext.SHIP,
    GameState.MISSION_LOG: HUDContext.SHIP,
    GameState.JOURNAL: HUDContext.SHIP,
    GameState.STATISTICS: HUDContext.SHIP,
    GameState.ACHIEVEMENTS: HUDContext.SHIP,
    # Station context: docked, interacting with station facilities
    GameState.STATION_HUB: HUDContext.STATION,
    GameState.TRADING: HUDContext.STATION,
    GameState.CANTINA: HUDContext.STATION,
    GameState.REPAIR_BAY: HUDContext.STATION,
    GameState.SHIPYARD: HUDContext.STATION,
    GameState.INVESTMENT: HUDContext.STATION,
}

# States where the HUD is visible (union of SHIP + STATION contexts)
HUD_VISIBLE_STATES = frozenset(_STATE_CONTEXT.keys())

# --- Ship skin colors (cockpit instruments) ---
_SHIP_PANEL_BG = (18, 22, 35)
_SHIP_PANEL_BORDER = (40, 50, 75)
_SHIP_ACCENT = (60, 180, 255)  # Cyan
_SHIP_ACCENT_DIM = (30, 90, 130)
_SHIP_RIVET_COLOR = (50, 55, 70)

# --- Station skin colors (docked interior) ---
_STATION_PANEL_BG = (22, 25, 32)
_STATION_PANEL_BORDER = (55, 60, 75)
_STATION_ACCENT = (200, 180, 100)  # Warm amber (default; overridden by faction)
_STATION_ACCENT_DIM = (100, 90, 50)
_STATION_TRIM_COLOR = (60, 60, 55)

# Faction accent overrides for station skin
FACTION_ACCENTS: dict[str, tuple[int, int, int]] = {
    "commerce_guild": (80, 140, 220),  # Corporate blue
    "miners_union": (220, 170, 60),  # Industrial amber
    "science_collective": (180, 200, 240),  # Clean white-blue
    "frontier_alliance": (80, 200, 120),  # Frontier green
}

# Shared colors (used by both skins)
_ACCENT_CYAN = (60, 180, 255)
_ACCENT_CYAN_DIM = (30, 90, 130)
_BUTTON_BG = (25, 32, 52)
_BUTTON_HOVER = (35, 45, 72)
_BUTTON_BG = (25, 32, 52)
_BUTTON_HOVER = (35, 45, 72)
_BUTTON_BORDER = (55, 65, 95)
_SHIELD_COLOR = (80, 180, 255)
_FUEL_COLOR = (190, 140, 30)
_BADGE_RED = (220, 40, 40)
_CREDIT_GOLD = (255, 215, 100)

# Navigation button definitions
_NAV_BUTTONS = [
    ("CPT", "Captain", GameState.CHARACTER),
    ("SKL", "Skills", GameState.SKILL_TREE),
    ("CRW", "Crew", GameState.CREW_ROSTER),
    ("MSN", "Missions", GameState.MISSION_LOG),
    ("JRN", "Journal", GameState.JOURNAL),
]


class CockpitHUD:
    """Persistent HUD bar with contextual visual skins.

    Renders as an overlay after pygame_gui elements. Follows the
    tutorial_overlay pattern: manually rendered, event interception,
    no BaseView lifecycle.
    """

    def __init__(
        self,
        player: "Player",
        mission_manager: "MissionManager",
        crew_roster: Optional["CrewRoster"] = None,
    ) -> None:
        """Initialize the cockpit HUD.

        Args:
            player: Player instance for live data.
            mission_manager: MissionManager for quest hints.
            crew_roster: Optional crew roster for loyalty warnings.
        """
        self.player = player
        self.mission_manager = mission_manager
        self.crew_roster = crew_roster
        self.visible = False
        self._current_state: Optional[GameState] = None

        # Contextual skin tracking
        self._context: HUDContext = HUDContext.HIDDEN
        self._faction_id: str = ""  # Current system's faction (for station skin)

        # Layout dimensions
        self.height = scale_y(HUD_BASE_HEIGHT)
        self.y = WINDOW_HEIGHT - self.height
        self.width = WINDOW_WIDTH

        # Fonts
        self._label_font = get_font("label", FONT_XS)
        self._value_font = get_font("stats", FONT_SM)
        self._button_font = get_font("dialogue", FONT_SM)
        self._tooltip_font = get_font("dialogue", FONT_XS)
        self._quest_font = get_font("dialogue", FONT_SM)
        self._credit_font = get_font("dialogue", FONT_MD)

        # Button rects (computed in _build_layout)
        self._button_rects: list[pygame.Rect] = []
        self._button_defs = _NAV_BUTTONS
        self._hovered_button: int = -1

        # Quest hint click rect
        self._quest_rect = pygame.Rect(0, 0, 0, 0)

        # Pre-rendered background panels (one per context)
        self._bg_surfaces: dict[HUDContext, pygame.Surface] = {}
        self._bg_surface: Optional[pygame.Surface] = None

        # Pulse timer for shield bar glow
        self._pulse_timer: float = 0.0

        # Build layout and pre-render background skins
        self._build_layout()
        self._build_ship_background()
        self._build_station_background()

        logger.info("Cockpit HUD initialized")

    def _build_layout(self) -> None:
        """Compute button positions and section boundaries."""
        pad = scale_x(12)
        btn_w = scale_x(70)
        btn_h = scale_y(32)
        btn_gap = scale_x(8)

        # Center section: 5 buttons
        total_btn_w = len(self._button_defs) * btn_w + (len(self._button_defs) - 1) * btn_gap
        btn_start_x = (self.width - total_btn_w) // 2
        btn_y = self.y + (self.height - btn_h) // 2

        self._button_rects = []
        for i in range(len(self._button_defs)):
            x = btn_start_x + i * (btn_w + btn_gap)
            self._button_rects.append(pygame.Rect(x, btn_y, btn_w, btn_h))

        # Section boundaries
        self._left_x = pad
        self._left_w = btn_start_x - pad * 2
        self._right_x = btn_start_x + total_btn_w + pad
        self._right_w = self.width - self._right_x - pad

    def _build_ship_background(self) -> None:
        """Pre-render the ship/cockpit panel background skin."""
        bg = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Subtle vertical gradient (lighter at top, darker at bottom)
        r0, g0, b0 = _SHIP_PANEL_BG
        for row in range(self.height):
            t = row / max(1, self.height - 1)
            # Lighten top by +8, darken bottom by -4
            r = int(r0 + 8 * (1 - t) - 4 * t)
            g = int(g0 + 8 * (1 - t) - 4 * t)
            b = int(b0 + 10 * (1 - t) - 6 * t)
            pygame.draw.line(
                bg,
                (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))),
                (0, row),
                (self.width, row),
            )

        # Top accent line (cyan cockpit border)
        pygame.draw.line(bg, _SHIP_ACCENT, (0, 0), (self.width, 0), 2)
        # Inner glow line below the cyan accent (darker cyan, 1px)
        pygame.draw.line(bg, (20, 60, 100), (0, 3), (self.width, 3), 1)
        pygame.draw.line(bg, _SHIP_ACCENT_DIM, (0, 2), (self.width, 2), 1)

        # Bottom edge (dark)
        pygame.draw.line(bg, (10, 12, 20), (0, self.height - 1), (self.width, self.height - 1))

        # Subtle panel border
        pygame.draw.rect(bg, _SHIP_PANEL_BORDER, (0, 0, self.width, self.height), 1)

        # Thin vertical separator lines at section boundaries
        pad = scale_x(12)
        left_sep_x = self._left_x + self._left_w + pad
        right_sep_x = self._right_x - pad
        sep_top = scale_y(8)
        sep_bottom = self.height - scale_y(8)
        sep_color = (35, 42, 65)
        pygame.draw.line(bg, sep_color, (left_sep_x, sep_top), (left_sep_x, sep_bottom), 1)
        pygame.draw.line(bg, sep_color, (right_sep_x, sep_top), (right_sep_x, sep_bottom), 1)

        # Rivets along top edge for industrial feel
        rivet_spacing = scale_x(40)
        rivet_y = scale_y(6)
        for x in range(rivet_spacing // 2, self.width, rivet_spacing):
            pygame.draw.circle(bg, _SHIP_RIVET_COLOR, (x, rivet_y), 2)

        # Subtle horizontal panel seam line
        seam_y = self.height // 2
        pygame.draw.line(bg, (25, 30, 48), (0, seam_y), (self.width, seam_y), 1)

        self._bg_surfaces[HUDContext.SHIP] = bg

    def _build_station_background(self) -> None:
        """Pre-render the station/docked panel background skin."""
        bg = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Lighter composite panel
        bg.fill(_STATION_PANEL_BG)

        # Top accent line (warm amber default — overridden per-faction at render time)
        pygame.draw.line(bg, _STATION_ACCENT, (0, 0), (self.width, 0), 2)
        pygame.draw.line(bg, _STATION_ACCENT_DIM, (0, 2), (self.width, 2), 1)

        # Bottom edge
        pygame.draw.line(bg, (15, 16, 20), (0, self.height - 1), (self.width, self.height - 1))

        # Panel border (slightly lighter than ship skin)
        pygame.draw.rect(bg, _STATION_PANEL_BORDER, (0, 0, self.width, self.height), 1)

        # Horizontal trim lines (station interior feel, no rivets)
        trim_y = scale_y(6)
        pygame.draw.line(
            bg, _STATION_TRIM_COLOR, (scale_x(20), trim_y), (self.width - scale_x(20), trim_y), 1
        )
        seam_y = self.height // 2
        pygame.draw.line(bg, (30, 32, 40), (0, seam_y), (self.width, seam_y), 1)

        self._bg_surfaces[HUDContext.STATION] = bg

    def update(
        self,
        dt: float,
        current_state: Optional[GameState] = None,
        faction_id: str = "",
    ) -> None:
        """Update HUD state each frame.

        Args:
            dt: Delta time in seconds.
            current_state: Current game state for visibility/context control.
            faction_id: Current system's faction ID (for station skin accent).
        """
        if current_state is not None:
            self._current_state = current_state
            new_context = _STATE_CONTEXT.get(current_state, HUDContext.HIDDEN)
            self._context = new_context
            self.visible = new_context != HUDContext.HIDDEN

            # Select the background skin for the active context
            self._bg_surface = self._bg_surfaces.get(new_context)

        if faction_id and faction_id != self._faction_id:
            self._faction_id = faction_id

        self._pulse_timer += dt

    def handle_event(self, event: pygame.event.Event) -> Optional[GameState]:
        """Handle mouse events on HUD buttons.

        Args:
            event: Pygame event to process.

        Returns:
            GameState to navigate to if a button was clicked, None otherwise.
        """
        if not self.visible:
            return None

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self._hovered_button = -1
            for i, rect in enumerate(self._button_rects):
                if rect.collidepoint(mx, my):
                    self._hovered_button = i
                    break
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Check navigation buttons
            for i, rect in enumerate(self._button_rects):
                if rect.collidepoint(mx, my):
                    _, _, target_state = self._button_defs[i]
                    # Don't navigate if we're already on that screen
                    if self._current_state != target_state:
                        logger.info(f"HUD nav: {target_state.value}")
                        return target_state
                    return None

            # Check quest hint click
            if self._quest_rect.collidepoint(mx, my):
                if self._current_state != GameState.MISSION_LOG:
                    return GameState.MISSION_LOG

            # Consume clicks on the HUD bar area to prevent click-through
            if my >= self.y:
                return None  # Consumed but no navigation

        return None

    def render(self, screen: pygame.Surface) -> None:
        """Render the cockpit HUD bar.

        Args:
            screen: Surface to draw on.
        """
        if not self.visible:
            return

        # Background panel (skin-appropriate)
        if self._bg_surface:
            screen.blit(self._bg_surface, (0, self.y))

        # Station skin: overdraw faction-colored accent line on top edge
        if self._context == HUDContext.STATION and self._faction_id:
            accent = FACTION_ACCENTS.get(self._faction_id, _STATION_ACCENT)
            pygame.draw.line(screen, accent, (0, self.y), (self.width, self.y), 2)

        self._render_status_bars(screen)
        self._render_buttons(screen)
        self._render_info_panel(screen)

    def _render_status_bars(self, screen: pygame.Surface) -> None:
        """Render hull, shield, and fuel bars in the left section."""
        ship = self.player.ship
        x = self._left_x
        bar_w = self._left_w
        bar_h = scale_y(14)
        y = self.y + scale_y(10)
        spacing = scale_y(25)

        # Prefer computed_stats from custom builds, fall back to ship_type
        cs = getattr(ship, "computed_stats", None)

        # Hull bar — clamp current to max to prevent "60/58" display
        hull_max = cs.hull if cs and cs.hull > 0 else ship.ship_type.combat_hull
        hull_current = min(ship.current_hull, hull_max)
        hull_ratio = hull_current / max(1, hull_max)
        hull_color = (
            Colors.GREEN
            if hull_ratio > 0.5
            else (Colors.YELLOW if hull_ratio > 0.25 else Colors.RED)
        )
        self._draw_hud_bar(
            screen, x, y, bar_w, bar_h, hull_ratio, hull_color, "HULL", f"{hull_current}/{hull_max}"
        )

        # Shield bar
        y += spacing
        shield_max = cs.shields if cs and cs.shields > 0 else ship.ship_type.combat_shields
        shield_current = min(ship.current_shields, shield_max)
        shield_ratio = shield_current / max(1, shield_max)
        self._draw_hud_bar(
            screen,
            x,
            y,
            bar_w,
            bar_h,
            shield_ratio,
            _SHIELD_COLOR,
            "SHLD",
            f"{shield_current}/{shield_max}",
        )

        # Fuel bar
        y += spacing
        fuel_max = cs.fuel_capacity if cs and cs.fuel_capacity > 0 else ship.max_fuel
        fuel_current = min(ship.current_fuel, fuel_max)
        fuel_ratio = fuel_current / max(1, fuel_max)
        fuel_color = _FUEL_COLOR if fuel_ratio > 0.2 else Colors.RED
        self._draw_hud_bar(
            screen,
            x,
            y,
            bar_w,
            bar_h,
            fuel_ratio,
            fuel_color,
            "FUEL",
            f"{fuel_current}/{fuel_max}",
        )

    def _draw_hud_bar(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        width: int,
        height: int,
        ratio: float,
        color: tuple[int, int, int],
        label: str,
        value: str = "",
    ) -> None:
        """Render a single HUD status bar with label and inline value."""
        label_w = scale_x(38)
        bar_x = x + label_w
        bar_w = width - label_w

        # Label
        label_surf = self._label_font.render(label, True, Colors.TEXT_SECONDARY)
        screen.blit(label_surf, (x, y + (height - label_surf.get_height()) // 2))

        # Bar background
        pygame.draw.rect(screen, Colors.BAR_BG, (bar_x, y, bar_w, height))

        # Bar fill
        fill_w = max(0, int(bar_w * min(1.0, ratio)))
        if fill_w > 0:
            pygame.draw.rect(screen, color, (bar_x, y, fill_w, height))
            # Leading edge highlight
            edge_x = bar_x + fill_w - 1
            if edge_x > bar_x:
                pygame.draw.line(screen, Colors.BAR_EDGE, (edge_x, y), (edge_x, y + height - 1))

        # Border
        pygame.draw.rect(screen, _SHIP_PANEL_BORDER, (bar_x, y, bar_w, height), 1)

        # Inline value text (right-aligned, dark pill background for readability)
        if value:
            val_surf = self._label_font.render(value, True, (230, 230, 230))
            val_x = bar_x + bar_w - val_surf.get_width() - scale_x(4)
            val_y = y + (height - val_surf.get_height()) // 2
            # Dark semi-transparent pill behind the text
            pill_pad = scale_x(3)
            pill_rect = pygame.Rect(
                val_x - pill_pad,
                val_y - 1,
                val_surf.get_width() + pill_pad * 2,
                val_surf.get_height() + 2,
            )
            pill_bg = pygame.Surface((pill_rect.width, pill_rect.height), pygame.SRCALPHA)
            pill_bg.fill((0, 0, 0, 160))
            screen.blit(pill_bg, pill_rect.topleft)
            screen.blit(val_surf, (val_x, val_y))

    def _render_buttons(self, screen: pygame.Surface) -> None:
        """Render the 5 navigation buttons in the center section."""
        for i, (short_label, full_label, target_state) in enumerate(self._button_defs):
            rect = self._button_rects[i]
            is_hovered = i == self._hovered_button
            is_active = self._current_state == target_state

            # Button background
            if is_active:
                bg = _ACCENT_CYAN_DIM
                border = _ACCENT_CYAN
            elif is_hovered:
                bg = _BUTTON_HOVER
                border = Colors.TEXT_HIGHLIGHT
            else:
                bg = _BUTTON_BG
                border = _BUTTON_BORDER

            pygame.draw.rect(screen, bg, rect, border_radius=3)
            pygame.draw.rect(screen, border, rect, 1, border_radius=3)

            # Button label
            text_color = Colors.TEXT_HIGHLIGHT if is_active else Colors.TEXT_PRIMARY
            label_surf = self._button_font.render(short_label, True, text_color)
            screen.blit(
                label_surf,
                label_surf.get_rect(center=rect.center),
            )

            # Notification badge
            has_badge = self._check_badge(i)
            if has_badge:
                badge_x = rect.right - scale_x(6)
                badge_y = rect.top + scale_y(4)
                pygame.draw.circle(screen, _BADGE_RED, (badge_x, badge_y), scale_x(4))
                pygame.draw.circle(screen, (255, 100, 100), (badge_x - 1, badge_y - 1), 1)

            # Tooltip on hover
            if is_hovered:
                tooltip = self._tooltip_font.render(full_label, True, Colors.TEXT_PRIMARY)
                tip_x = rect.centerx - tooltip.get_width() // 2
                tip_y = rect.top - tooltip.get_height() - scale_y(4)
                tip_bg = pygame.Rect(
                    tip_x - 4,
                    tip_y - 2,
                    tooltip.get_width() + 8,
                    tooltip.get_height() + 4,
                )
                pygame.draw.rect(screen, _SHIP_PANEL_BG, tip_bg)
                pygame.draw.rect(screen, _SHIP_PANEL_BORDER, tip_bg, 1)
                screen.blit(tooltip, (tip_x, tip_y))

    def _check_badge(self, button_index: int) -> bool:
        """Check if a button should show a notification badge.

        Args:
            button_index: Index into _NAV_BUTTONS.

        Returns:
            True if the button has pending content.
        """
        if button_index == 1:  # Skills
            return self.player.progression.skill_points > 0
        if button_index == 3:  # Missions
            available = self.mission_manager.get_missions_by_status(MissionStatus.AVAILABLE)
            return len(available) > 0
        if button_index == 2:  # Crew
            if self.crew_roster:
                pending = self.crew_roster.pending_companion_ids
                return len(pending) > 0
        return False

    def _render_info_panel(self, screen: pygame.Surface) -> None:
        """Render credits, cargo, and quest hint in the right section."""
        x = self._right_x
        w = self._right_w
        y = self.y + scale_y(10)

        # Credits
        credits_text = f"{self.player.credits:,} CR"
        cr_surf = self._credit_font.render(credits_text, True, _CREDIT_GOLD)
        screen.blit(cr_surf, (x, y))

        # Cargo capacity
        y += scale_y(24)
        ship = self.player.ship
        used = sum(ship.current_cargo.values())
        capacity = ship.max_cargo
        cargo_text = f"Cargo: {used}/{capacity}"
        cargo_color = Colors.TEXT_SECONDARY if used < capacity else Colors.RED
        cargo_surf = self._value_font.render(cargo_text, True, cargo_color)
        screen.blit(cargo_surf, (x, y))

        # Small cargo fill bar
        cargo_bar_y = y + cargo_surf.get_height() + 2
        cargo_bar_w = min(w, scale_x(140))
        cargo_bar_h = scale_y(4)
        pygame.draw.rect(screen, Colors.BAR_BG, (x, cargo_bar_y, cargo_bar_w, cargo_bar_h))
        fill_ratio = min(1.0, used / max(1, capacity))
        fill_w = int(cargo_bar_w * fill_ratio)
        if fill_w > 0:
            fill_color = Colors.TEXT_HIGHLIGHT if fill_ratio < 0.9 else Colors.RED
            pygame.draw.rect(screen, fill_color, (x, cargo_bar_y, fill_w, cargo_bar_h))

        # Quest hint
        y = cargo_bar_y + scale_y(10)
        quest_text = self._get_quest_hint()
        if quest_text:
            quest_surf = self._quest_font.render(quest_text, True, Colors.TEXT_SECONDARY)
            # Truncate if too wide
            max_w = w - scale_x(4)
            if quest_surf.get_width() > max_w:
                while len(quest_text) > 3 and quest_surf.get_width() > max_w:
                    quest_text = quest_text[:-1]
                quest_text = quest_text.rstrip() + ".."
                quest_surf = self._quest_font.render(quest_text, True, Colors.TEXT_SECONDARY)
            screen.blit(quest_surf, (x, y))
            self._quest_rect = pygame.Rect(x, y, quest_surf.get_width(), quest_surf.get_height())
        else:
            self._quest_rect = pygame.Rect(0, 0, 0, 0)

    def _get_quest_hint(self) -> str:
        """Get a short quest hint from the first active mission.

        Returns:
            Quest hint string, or empty string if no active missions.
        """
        active = self.mission_manager.get_missions_by_status(MissionStatus.ACTIVE)
        if not active:
            return ""

        # Show the first active mission's first incomplete objective
        mission = active[0]
        progress = self.mission_manager.get_objective_progress(mission.id)
        if progress:
            for i, completed in enumerate(progress):
                if not completed and i < len(mission.objectives):
                    return f"> {mission.objectives[i].description}"
        return f"> {mission.hint}" if mission.hint else f"> {mission.name}"
