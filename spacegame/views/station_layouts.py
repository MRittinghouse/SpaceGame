"""Faction-specific station hub layouts.

Each faction has a distinct visual layout for their stations, creating
immediate visual identity when docking. The player knows whose space
they're in from the visual language alone.

- Commerce Guild: Deck-by-deck vertical (corporate, hierarchical)
- Miners' Union: Cross-section blueprint (industrial, functional)
- Science Collective: Radial command display (clean, futuristic)
- Frontier Alliance: Freeform scattered (improvised, colorful)
- Crimson Reach: Dark minimal (dangerous, sparse)
"""

import math
from dataclasses import dataclass
from typing import Optional

import pygame

from spacegame.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    scale_x,
    scale_y,
)
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_SM,
    FONT_XS,
    get_font,
)
from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT

# Location type accent colors (shared across all layouts)
LOCATION_COLORS: dict[str, tuple[int, int, int]] = {
    "market": (100, 200, 255),
    "repair_bay": (50, 200, 100),
    "cantina": (255, 200, 50),
    "mining": (180, 80, 30),
    "salvaging": (140, 170, 200),
    "refining": (255, 160, 40),
    "shipyard": (100, 180, 240),
    "unique": (200, 160, 255),
    "investment": (200, 180, 80),
}

LOCATION_LABELS: dict[str, str] = {
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

# System → layout type mapping (based on controlling faction)
SYSTEM_LAYOUT_MAP: dict[str, str] = {
    # Commerce Guild systems
    "nexus_prime": "guild",
    "stellaris_port": "guild",
    "the_fulcrum": "guild",
    # Miners' Union systems
    "forgeworks": "union",
    "breakstone": "union",
    "iron_depths": "union",
    # Science Collective systems
    "axiom_labs": "collective",
    "nova_research": "collective",
    # Frontier Alliance systems
    "havens_rest": "frontier",
    "verdant": "frontier",
    # Crimson Reach (lawless)
    "crimson_reach": "reach",
}

# HUD height for layout area calculation
_HUD_H = scale_y(HUD_BASE_HEIGHT)
_LAYOUT_TOP = scale_y(125)  # Below header card (HEADER_CARD_Y=10 + HEADER_CARD_H=105 + margin)
_LAYOUT_BOTTOM = WINDOW_HEIGHT - _HUD_H - scale_y(90)  # Above chatter + HUD
_LAYOUT_H = _LAYOUT_BOTTOM - _LAYOUT_TOP


@dataclass
class StationZone:
    """A clickable zone in the station layout."""

    location: object  # Location dataclass
    rect: pygame.Rect
    label: str
    accent_color: tuple[int, int, int]
    hovered: bool = False
    icon: Optional[pygame.Surface] = None


class StationLayout:
    """Base class for faction-specific station hub layouts."""

    # Faction visual properties (override in subclasses)
    accent_color: tuple[int, int, int] = Colors.TEXT_HIGHLIGHT
    bg_tint: Optional[tuple[int, int, int, int]] = None
    label_prefix: str = ""
    faction_tagline: str = ""  # Atmospheric motto displayed in layout

    def __init__(self, locations: list, system_id: str) -> None:
        self.locations = locations
        self.system_id = system_id
        self.zones: list[StationZone] = []
        self._label_font = get_font("label", FONT_XS)
        self._name_font = get_font("dialogue", FONT_BODY)
        self._section_font = get_font("label", FONT_SM)
        self._tooltip_font = get_font("dialogue", FONT_XS)
        self._tagline_font = get_font("narration", FONT_SM)
        self._elapsed: float = 0.0
        self._entrance_timer: float = 0.0  # Fade-in on dock

        # Ambient particles
        self._ambient_particles: list[dict] = []
        self._ambient_emit_timer: float = 0.0

    def build_zones(self, sprite_mgr: object) -> list[StationZone]:
        """Build zone rects for all locations. Override in subclasses."""
        self.zones = []
        return self.zones

    def update(self, dt: float) -> None:
        """Update animations, entrance fade, and ambient particles."""
        self._elapsed += dt
        if self._entrance_timer < 1.0:
            self._entrance_timer = min(1.0, self._entrance_timer + dt * 2.0)

        # Update ambient particles
        for p in self._ambient_particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self._ambient_particles = [p for p in self._ambient_particles if p["life"] > 0]

    def handle_hover(self, pos: tuple[int, int]) -> None:
        """Update hover state on zones."""
        for zone in self.zones:
            zone.hovered = zone.rect.collidepoint(pos)

    def get_clicked_zone(self, pos: tuple[int, int]) -> Optional[StationZone]:
        """Return the zone at the click position, or None."""
        for zone in self.zones:
            if zone.rect.collidepoint(pos):
                return zone
        return None

    def render_background(self, screen: pygame.Surface) -> None:
        """Render faction-specific background elements."""
        if self.bg_tint:
            tint = pygame.Surface((WINDOW_WIDTH, _LAYOUT_H), pygame.SRCALPHA)
            tint.fill(self.bg_tint)
            screen.blit(tint, (0, _LAYOUT_TOP))

    def render_zones(self, screen: pygame.Surface) -> None:
        """Render all zones with entrance fade. Override for custom styling."""
        alpha_mult = self._entrance_timer  # 0→1 over 0.5s
        for zone in self.zones:
            self._render_default_zone(screen, zone, alpha_mult)

    def render_atmosphere(self, screen: pygame.Surface) -> None:
        """Render ambient particles, tagline, and hover tooltips."""
        # Ambient particles
        for p in self._ambient_particles:
            t = p["life"] / p["max_life"]
            alpha = int(p["alpha"] * t * self._entrance_timer)
            if alpha <= 0:
                continue
            size = max(1, int(p.get("size", 2)))
            color = p["color"]
            ps = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*color, alpha), (size, size), size)
            screen.blit(ps, (int(p["x"]) - size, int(p["y"]) - size))

        # Faction tagline (bottom of layout area, subtle)
        if self.faction_tagline and self._entrance_timer >= 0.8:
            tag_alpha = int(60 * min(1.0, (self._entrance_timer - 0.8) / 0.2))
            tag_surf = self._tagline_font.render(self.faction_tagline, True, self.accent_color)
            tag_surf.set_alpha(tag_alpha)
            tag_x = WINDOW_WIDTH // 2 - tag_surf.get_width() // 2
            tag_y = _LAYOUT_BOTTOM - scale_y(15)
            screen.blit(tag_surf, (tag_x, tag_y))

        # Hover tooltip for the hovered zone
        for zone in self.zones:
            if zone.hovered:
                self._render_zone_tooltip(screen, zone)
                break

    def _render_zone_tooltip(self, screen: pygame.Surface, zone: StationZone) -> None:
        """Render a detailed tooltip above/below the hovered zone."""
        loc = zone.location
        lines: list[tuple[str, tuple[int, int, int]]] = []

        lines.append((loc.name, Colors.TEXT_HIGHLIGHT))
        if loc.description:
            # Word-wrap description
            desc = loc.description
            if len(desc) > 60:
                # Simple split at ~60 chars
                mid = desc.rfind(" ", 0, 60)
                if mid > 20:
                    lines.append((desc[:mid], Colors.TEXT_PRIMARY))
                    lines.append((desc[mid + 1 :], Colors.TEXT_PRIMARY))
                else:
                    lines.append((desc, Colors.TEXT_PRIMARY))
            else:
                lines.append((desc, Colors.TEXT_PRIMARY))
        if hasattr(loc, "flavor_text") and loc.flavor_text:
            flavor = loc.flavor_text
            if len(flavor) > 65:
                flavor = flavor[:62] + "..."
            lines.append((f'"{flavor}"', Colors.TEXT_SECONDARY))

        if not lines:
            return

        font = self._tooltip_font
        line_h = font.get_linesize() + 2
        pad = 8
        tip_w = max(font.size(text)[0] for text, _ in lines) + pad * 2
        tip_h = len(lines) * line_h + pad * 2
        tip_w = min(tip_w, scale_x(350))

        # Position: above the zone if space, below if not
        tip_x = zone.rect.centerx - tip_w // 2
        tip_y = zone.rect.top - tip_h - 6
        if tip_y < _LAYOUT_TOP:
            tip_y = zone.rect.bottom + 6
        # Keep on screen horizontally
        tip_x = max(4, min(tip_x, WINDOW_WIDTH - tip_w - 4))

        # Background
        tip_surf = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
        tip_surf.fill((10, 14, 25, 230))
        screen.blit(tip_surf, (tip_x, tip_y))

        # Accent top border
        pygame.draw.line(screen, zone.accent_color, (tip_x, tip_y), (tip_x + tip_w, tip_y), 2)
        pygame.draw.rect(screen, Colors.UI_BORDER, (tip_x, tip_y, tip_w, tip_h), 1)

        # Text
        ty = tip_y + pad
        for text, color in lines:
            surf = font.render(text, True, color)
            # Clip if too wide
            if surf.get_width() > tip_w - pad * 2:
                clip_rect = pygame.Rect(0, 0, tip_w - pad * 2, surf.get_height())
                screen.blit(surf, (tip_x + pad, ty), clip_rect)
            else:
                screen.blit(surf, (tip_x + pad, ty))
            ty += line_h

    def _render_default_zone(
        self, screen: pygame.Surface, zone: StationZone, alpha_mult: float = 1.0
    ) -> None:
        """Render a single zone with standard styling."""
        r = zone.rect
        # Background (with entrance fade)
        bg_alpha = int((200 if zone.hovered else 160) * alpha_mult)
        bg_color = (25, 30, 50) if zone.hovered else (18, 22, 38)
        zone_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        zone_surf.fill((*bg_color, bg_alpha))
        screen.blit(zone_surf, r.topleft)

        # Accent border
        border_color = zone.accent_color if zone.hovered else Colors.UI_BORDER
        pygame.draw.rect(screen, border_color, r, 2 if zone.hovered else 1, border_radius=4)

        # Left accent stripe
        stripe_rect = pygame.Rect(r.x, r.y, 4, r.height)
        pygame.draw.rect(screen, zone.accent_color, stripe_rect)

        # Location icon
        if zone.icon:
            icon_y = r.y + (r.height - zone.icon.get_height()) // 2
            screen.blit(zone.icon, (r.x + 10, icon_y))
            text_x = r.x + 10 + zone.icon.get_width() + 8
        else:
            text_x = r.x + 18

        # Name
        name_surf = self._name_font.render(zone.location.name, True, Colors.TEXT_PRIMARY)
        screen.blit(name_surf, (text_x, r.y + scale_y(8)))

        # Type label (top-right)
        type_label = LOCATION_LABELS.get(zone.location.location_type, "")
        if type_label:
            label_surf = self._label_font.render(type_label, True, zone.accent_color)
            screen.blit(label_surf, (r.right - label_surf.get_width() - 8, r.y + 6))

        # Description (below name, with word wrapping for taller cards)
        if r.height >= scale_y(50):
            desc = zone.location.description or ""
            max_desc_w = r.right - text_x - 10
            desc_y = r.y + scale_y(28)
            line_h = self._label_font.get_linesize()
            max_lines = max(1, (r.height - scale_y(32)) // line_h)

            # Word-wrap description into lines that fit the available width
            words = desc.split()
            lines: list[str] = []
            current_line = ""
            for word in words:
                test = f"{current_line} {word}".strip() if current_line else word
                if self._label_font.size(test)[0] <= max_desc_w:
                    current_line = test
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            for i, line in enumerate(lines[:max_lines]):
                if i == max_lines - 1 and len(lines) > max_lines:
                    line = line[: len(line) - 3] + "..." if len(line) > 3 else line
                desc_surf = self._label_font.render(line, True, Colors.TEXT_SECONDARY)
                screen.blit(desc_surf, (text_x, desc_y + i * line_h))

    def _categorize_locations(self) -> dict[str, list]:
        """Sort locations into upper/service/industrial categories."""
        upper = []  # Commerce: market, shipyard, investment
        service = []  # Services: cantina, repair, unique
        industrial = []  # Industrial: mining, salvaging, refining

        for loc in self.locations:
            lt = loc.location_type
            if lt in ("market", "shipyard", "investment"):
                upper.append(loc)
            elif lt in ("mining", "salvaging", "refining"):
                industrial.append(loc)
            else:
                service.append(loc)
        return {"upper": upper, "service": service, "industrial": industrial}


# ==========================================================================
# Commerce Guild — Deck-by-Deck Vertical
# ==========================================================================


class GuildDeckLayout(StationLayout):
    """Corporate deck-by-deck layout. Clean, hierarchical, blue accents."""

    accent_color = (80, 140, 220)
    bg_tint = (10, 15, 30, 15)
    faction_tagline = "Commerce. Order. Prosperity."

    def build_zones(self, sprite_mgr: object) -> list[StationZone]:
        from spacegame.engine.sprites import res_scale

        cats = self._categorize_locations()
        self.zones = []

        margin_x = scale_x(60)
        deck_w = WINDOW_WIDTH - margin_x * 2
        zone_h = scale_y(90)
        zone_gap = scale_x(12)
        deck_gap = scale_y(18)
        deck_label_h = scale_y(22)

        y = _LAYOUT_TOP + scale_y(10)
        deck_labels = [
            ("UPPER DECK", cats["upper"]),
            ("SERVICE DECK", cats["service"]),
            ("INDUSTRIAL DECK", cats["industrial"]),
        ]

        for deck_name, locations in deck_labels:
            if not locations:
                continue

            # Deck label
            self._deck_labels = getattr(self, "_deck_labels", [])
            self._deck_labels.append((deck_name, margin_x, y))
            y += deck_label_h

            # Zones within deck
            num = len(locations)
            zone_w = (deck_w - (num - 1) * zone_gap) // max(1, num)
            zone_w = min(zone_w, scale_x(380))

            total_w = num * zone_w + (num - 1) * zone_gap
            start_x = (WINDOW_WIDTH - total_w) // 2

            for i, loc in enumerate(locations):
                x = start_x + i * (zone_w + zone_gap)
                rect = pygame.Rect(x, y, zone_w, zone_h)
                color = LOCATION_COLORS.get(loc.location_type, Colors.TEXT_HIGHLIGHT)
                icon = sprite_mgr.get_location_icon(loc.location_type, scale=res_scale(2))
                self.zones.append(
                    StationZone(
                        location=loc,
                        rect=rect,
                        label=loc.name,
                        accent_color=color,
                        icon=icon,
                    )
                )
            y += zone_h + deck_gap

        return self.zones

    def update(self, dt: float) -> None:
        super().update(dt)
        # Holographic data motes (blue floating points)
        import random as _rng

        self._ambient_emit_timer += dt
        if self._ambient_emit_timer >= 0.4:
            self._ambient_emit_timer -= 0.4
            self._ambient_particles.append(
                {
                    "x": _rng.uniform(scale_x(100), WINDOW_WIDTH - scale_x(100)),
                    "y": _rng.uniform(_LAYOUT_TOP, _LAYOUT_BOTTOM),
                    "vx": _rng.uniform(-5, 5),
                    "vy": _rng.uniform(-15, -5),
                    "life": _rng.uniform(1.5, 3.0),
                    "max_life": 3.0,
                    "alpha": _rng.randint(25, 50),
                    "color": self.accent_color,
                    "size": _rng.uniform(1, 2),
                }
            )

    def render_background(self, screen: pygame.Surface) -> None:
        super().render_background(screen)

        # Deck separator lines
        for label, lx, ly in getattr(self, "_deck_labels", []):
            label_surf = self._section_font.render(label, True, self.accent_color)
            screen.blit(label_surf, (lx, ly + 2))
            # Horizontal rule after label
            line_y = ly + scale_y(18)
            pygame.draw.line(
                screen,
                (*self.accent_color, 60),
                (lx + label_surf.get_width() + 10, line_y),
                (WINDOW_WIDTH - lx, line_y),
            )


# ==========================================================================
# Miners' Union — Cross-Section Blueprint
# ==========================================================================


class UnionBlueprintLayout(StationLayout):
    """Industrial blueprint layout. Rust accents, technical labels."""

    accent_color = (220, 170, 60)
    bg_tint = (15, 10, 5, 12)
    faction_tagline = "Built by hands, not contracts."

    def build_zones(self, sprite_mgr: object) -> list[StationZone]:
        from spacegame.engine.sprites import res_scale

        self.zones = []
        margin_x = scale_x(60)
        zone_w = scale_x(200)
        zone_h = scale_y(90)
        gap_x = scale_x(15)
        gap_y = scale_y(20)
        cols = min(4, max(2, (WINDOW_WIDTH - margin_x * 2 + gap_x) // (zone_w + gap_x)))

        total_w = cols * zone_w + (cols - 1) * gap_x
        start_x = (WINDOW_WIDTH - total_w) // 2
        y = _LAYOUT_TOP + scale_y(15)

        for i, loc in enumerate(self.locations):
            col = i % cols
            row = i // cols
            x = start_x + col * (zone_w + gap_x)
            zy = y + row * (zone_h + gap_y)
            rect = pygame.Rect(x, zy, zone_w, zone_h)
            color = LOCATION_COLORS.get(loc.location_type, Colors.TEXT_HIGHLIGHT)
            icon = sprite_mgr.get_location_icon(loc.location_type, scale=res_scale(2))

            # Technical label prefix
            bay_num = f"BAY {i + 1:02d}"
            self.zones.append(
                StationZone(
                    location=loc,
                    rect=rect,
                    label=f"{bay_num}: {loc.name}",
                    accent_color=color,
                    icon=icon,
                )
            )
        return self.zones

    def update(self, dt: float) -> None:
        super().update(dt)
        # Industrial sparks (amber, falling with gravity)
        import random as _rng

        self._ambient_emit_timer += dt
        if self._ambient_emit_timer >= 0.6:
            self._ambient_emit_timer -= 0.6
            if self.zones:
                zone = _rng.choice(self.zones)
                self._ambient_particles.append(
                    {
                        "x": _rng.uniform(zone.rect.left, zone.rect.right),
                        "y": float(zone.rect.top),
                        "vx": _rng.uniform(-10, 10),
                        "vy": _rng.uniform(15, 35),
                        "life": _rng.uniform(0.5, 1.2),
                        "max_life": 1.2,
                        "alpha": _rng.randint(60, 120),
                        "color": (255, _rng.randint(150, 200), 40),
                        "size": 1.5,
                    }
                )

    def render_background(self, screen: pygame.Surface) -> None:
        super().render_background(screen)

        # Blueprint grid lines
        grid_color = (40, 55, 50, 30)
        grid_spacing = scale_x(40)
        for x in range(0, WINDOW_WIDTH, grid_spacing):
            pygame.draw.line(screen, grid_color, (x, _LAYOUT_TOP), (x, _LAYOUT_BOTTOM))
        for y in range(_LAYOUT_TOP, _LAYOUT_BOTTOM, grid_spacing):
            pygame.draw.line(screen, grid_color, (0, y), (WINDOW_WIDTH, y))

    def _render_default_zone(
        self, screen: pygame.Surface, zone: StationZone, alpha_mult: float = 1.0
    ) -> None:
        """Override: add riveted panel feel and technical labels."""
        r = zone.rect
        # Darker, more industrial background
        bg_alpha = 210 if zone.hovered else 170
        bg_color = (28, 24, 18) if zone.hovered else (20, 18, 14)
        zone_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        zone_surf.fill((*bg_color, bg_alpha))
        screen.blit(zone_surf, r.topleft)

        # Double border (industrial feel)
        outer_color = zone.accent_color if zone.hovered else (80, 70, 50)
        pygame.draw.rect(screen, outer_color, r, 2)
        inner = pygame.Rect(r.x + 3, r.y + 3, r.width - 6, r.height - 6)
        pygame.draw.rect(screen, (50, 45, 35), inner, 1)

        # Rivets at corners
        rivet_color = (70, 65, 50)
        for cx, cy in [
            (r.x + 6, r.y + 6),
            (r.right - 6, r.y + 6),
            (r.x + 6, r.bottom - 6),
            (r.right - 6, r.bottom - 6),
        ]:
            pygame.draw.circle(screen, rivet_color, (cx, cy), 2)

        # Bay number (top-left, small, amber)
        bay_surf = self._label_font.render(zone.label.split(":")[0], True, self.accent_color)
        screen.blit(bay_surf, (r.x + 12, r.y + 5))

        # Location name
        name = zone.location.name
        name_surf = self._name_font.render(name, True, Colors.TEXT_PRIMARY)
        screen.blit(name_surf, (r.x + 12, r.y + scale_y(18)))

        # Description (word-wrapped)
        desc = zone.location.description or ""
        if desc and r.height >= scale_y(60):
            text_x = r.x + 12
            max_w = r.width - 24
            desc_y = r.y + scale_y(38)
            line_h = self._label_font.get_linesize()
            words = desc.split()
            line = ""
            lines_drawn = 0
            for word in words:
                test = f"{line} {word}".strip() if line else word
                if self._label_font.size(test)[0] <= max_w:
                    line = test
                else:
                    if line and lines_drawn < 2:
                        d_surf = self._label_font.render(line, True, Colors.TEXT_SECONDARY)
                        screen.blit(d_surf, (text_x, desc_y + lines_drawn * line_h))
                        lines_drawn += 1
                    line = word
            if line and lines_drawn < 2:
                d_surf = self._label_font.render(line, True, Colors.TEXT_SECONDARY)
                screen.blit(d_surf, (text_x, desc_y + lines_drawn * line_h))

        # Type label (top-right)
        type_label = LOCATION_LABELS.get(zone.location.location_type, "")
        if type_label:
            tl_surf = self._label_font.render(type_label, True, zone.accent_color)
            screen.blit(tl_surf, (r.right - tl_surf.get_width() - 10, r.y + 6))


# ==========================================================================
# Science Collective — Radial Command Display
# ==========================================================================


class CollectiveRadialLayout(StationLayout):
    """Radial command display. Clean, holographic, data-driven."""

    accent_color = (160, 200, 240)
    bg_tint = (5, 8, 18, 10)
    faction_tagline = "Through knowledge, understanding."

    def build_zones(self, sprite_mgr: object) -> list[StationZone]:
        from spacegame.engine.sprites import res_scale

        self.zones = []
        cx = WINDOW_WIDTH // 2
        cy = _LAYOUT_TOP + _LAYOUT_H // 2
        radius = min(scale_x(280), _LAYOUT_H // 2 - scale_y(40))
        zone_w = scale_x(160)
        zone_h = scale_y(85)

        n = len(self.locations)
        for i, loc in enumerate(self.locations):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            zx = cx + int(radius * math.cos(angle)) - zone_w // 2
            zy = cy + int(radius * math.sin(angle)) - zone_h // 2
            rect = pygame.Rect(zx, zy, zone_w, zone_h)
            color = LOCATION_COLORS.get(loc.location_type, Colors.TEXT_HIGHLIGHT)
            icon = sprite_mgr.get_location_icon(loc.location_type, scale=res_scale(2))
            self.zones.append(
                StationZone(
                    location=loc,
                    rect=rect,
                    label=loc.name,
                    accent_color=color,
                    icon=icon,
                )
            )
        self._center = (cx, cy)
        self._radius = radius
        return self.zones

    def update(self, dt: float) -> None:
        super().update(dt)
        # Orbiting data nodes (small white-blue dots circling the center)
        import random as _rng

        self._ambient_emit_timer += dt
        if self._ambient_emit_timer >= 0.3:
            self._ambient_emit_timer -= 0.3
            cx, cy = getattr(self, "_center", (WINDOW_WIDTH // 2, _LAYOUT_TOP + _LAYOUT_H // 2))
            angle = self._elapsed * 0.8 + _rng.uniform(0, math.pi * 2)
            r = getattr(self, "_radius", scale_x(200)) * _rng.uniform(0.3, 0.9)
            self._ambient_particles.append(
                {
                    "x": cx + math.cos(angle) * r,
                    "y": cy + math.sin(angle) * r,
                    "vx": math.cos(angle + 1.57) * 12,
                    "vy": math.sin(angle + 1.57) * 12,
                    "life": _rng.uniform(1.0, 2.5),
                    "max_life": 2.5,
                    "alpha": _rng.randint(30, 60),
                    "color": (180, 210, 255),
                    "size": _rng.uniform(1, 2),
                }
            )

    def render_background(self, screen: pygame.Surface) -> None:
        super().render_background(screen)
        cx, cy = self._center

        # Central ring
        ring_alpha = 40 + int(15 * math.sin(self._elapsed * 1.5))
        ring_surf = pygame.Surface((self._radius * 2 + 20, self._radius * 2 + 20), pygame.SRCALPHA)
        rc = self._radius + 10
        pygame.draw.circle(ring_surf, (*self.accent_color, ring_alpha), (rc, rc), self._radius, 1)
        pygame.draw.circle(
            ring_surf,
            (*self.accent_color, ring_alpha // 2),
            (rc, rc),
            self._radius - scale_x(15),
            1,
        )
        screen.blit(ring_surf, (cx - rc, cy - rc))

        # Connecting lines from center to each zone
        for zone in self.zones:
            zx = zone.rect.centerx
            zy = zone.rect.centery
            line_color = zone.accent_color if zone.hovered else (*self.accent_color[:3],)
            line_alpha = 80 if zone.hovered else 30
            # Draw semi-transparent line
            pygame.draw.line(screen, (*line_color[:3], line_alpha), (cx, cy), (zx, zy))

        # Central station dot
        pygame.draw.circle(screen, self.accent_color, (cx, cy), scale_x(6))
        pygame.draw.circle(screen, Colors.TEXT_PRIMARY, (cx, cy), scale_x(3))

    def _render_default_zone(
        self, screen: pygame.Surface, zone: StationZone, alpha_mult: float = 1.0
    ) -> None:
        """Override: holographic node feel."""
        r = zone.rect
        # Subtle translucent background
        bg_alpha = 180 if zone.hovered else 120
        zone_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        zone_surf.fill((12, 18, 35, bg_alpha))
        screen.blit(zone_surf, r.topleft)

        # Thin bright border
        border_color = zone.accent_color if zone.hovered else self.accent_color
        border_w = 2 if zone.hovered else 1
        pygame.draw.rect(screen, border_color, r, border_w, border_radius=6)

        # Icon + name centered
        text_x = r.x + 8
        if zone.icon:
            icon_y = r.y + (r.height - zone.icon.get_height()) // 2
            screen.blit(zone.icon, (r.x + 6, icon_y))
            text_x = r.x + 6 + zone.icon.get_width() + 6
        name_surf = self._name_font.render(zone.location.name, True, Colors.TEXT_PRIMARY)
        screen.blit(name_surf, (text_x, r.y + (r.height - name_surf.get_height()) // 2))


# ==========================================================================
# Frontier Alliance — Freeform Scattered
# ==========================================================================


class FrontierScatteredLayout(StationLayout):
    """Freeform scattered layout. Organic, improvised, colorful."""

    accent_color = (80, 200, 120)
    bg_tint = (8, 15, 8, 10)
    faction_tagline = "The frontier takes care of its own."

    def build_zones(self, sprite_mgr: object) -> list[StationZone]:
        import random as _random

        from spacegame.engine.sprites import res_scale

        self.zones = []
        rng = _random.Random(hash(self.system_id) + 42)

        # Scatter zones with controlled randomness (no overlap)
        zone_w = scale_x(190)
        zone_h = scale_y(85)
        margin = scale_x(50)

        placed: list[pygame.Rect] = []
        for loc in self.locations:
            # Try random positions, avoid overlap
            for _ in range(50):
                x = rng.randint(margin, WINDOW_WIDTH - margin - zone_w)
                y = rng.randint(_LAYOUT_TOP + scale_y(10), _LAYOUT_BOTTOM - zone_h)
                rect = pygame.Rect(x, y, zone_w, zone_h)
                # Check overlap with placed zones
                if not any(rect.inflate(10, 10).colliderect(p) for p in placed):
                    placed.append(rect)
                    break
            else:
                # Fallback: place in a grid-like position
                idx = len(placed)
                x = margin + (idx % 3) * (zone_w + scale_x(20))
                y = _LAYOUT_TOP + scale_y(10) + (idx // 3) * (zone_h + scale_y(15))
                rect = pygame.Rect(x, y, zone_w, zone_h)
                placed.append(rect)

            color = LOCATION_COLORS.get(loc.location_type, Colors.TEXT_HIGHLIGHT)
            icon = sprite_mgr.get_location_icon(loc.location_type, scale=res_scale(2))
            self.zones.append(
                StationZone(
                    location=loc,
                    rect=rect,
                    label=loc.name,
                    accent_color=color,
                    icon=icon,
                )
            )
        return self.zones

    def update(self, dt: float) -> None:
        super().update(dt)
        # Floating dust/pollen (warm green, drifting upward)
        import random as _rng

        self._ambient_emit_timer += dt
        if self._ambient_emit_timer >= 0.5:
            self._ambient_emit_timer -= 0.5
            self._ambient_particles.append(
                {
                    "x": _rng.uniform(scale_x(40), WINDOW_WIDTH - scale_x(40)),
                    "y": float(_LAYOUT_BOTTOM),
                    "vx": _rng.uniform(-8, 8),
                    "vy": _rng.uniform(-20, -8),
                    "life": _rng.uniform(2.0, 4.0),
                    "max_life": 4.0,
                    "alpha": _rng.randint(20, 45),
                    "color": (
                        _rng.randint(100, 160),
                        _rng.randint(180, 220),
                        _rng.randint(80, 120),
                    ),
                    "size": _rng.uniform(1, 2.5),
                }
            )

    def render_background(self, screen: pygame.Surface) -> None:
        super().render_background(screen)

        # Dashed connecting corridors between zones
        if len(self.zones) >= 2:
            for i in range(len(self.zones) - 1):
                z1 = self.zones[i]
                z2 = self.zones[i + 1]
                x1, y1 = z1.rect.centerx, z1.rect.centery
                x2, y2 = z2.rect.centerx, z2.rect.centery
                # Dashed line
                dx = x2 - x1
                dy = y2 - y1
                dist = max(1, int(math.sqrt(dx * dx + dy * dy)))
                dash_len = 8
                for d in range(0, dist, dash_len * 2):
                    t1 = d / dist
                    t2 = min(1.0, (d + dash_len) / dist)
                    px1 = int(x1 + dx * t1)
                    py1 = int(y1 + dy * t1)
                    px2 = int(x1 + dx * t2)
                    py2 = int(y1 + dy * t2)
                    pygame.draw.line(screen, (60, 80, 60), (px1, py1), (px2, py2))

    def _render_default_zone(
        self, screen: pygame.Surface, zone: StationZone, alpha_mult: float = 1.0
    ) -> None:
        """Override: varied panel styles, slightly rough edges."""
        r = zone.rect
        bg_alpha = 190 if zone.hovered else 150
        bg_color = (22, 30, 22) if zone.hovered else (16, 22, 16)
        zone_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        zone_surf.fill((*bg_color, bg_alpha))
        screen.blit(zone_surf, r.topleft)

        # Colorful accent border (each zone gets its location color)
        border_w = 2 if zone.hovered else 1
        pygame.draw.rect(screen, zone.accent_color, r, border_w, border_radius=3)

        # Icon + name
        text_x = r.x + 10
        if zone.icon:
            icon_y = r.y + (r.height - zone.icon.get_height()) // 2
            screen.blit(zone.icon, (r.x + 8, icon_y))
            text_x = r.x + 8 + zone.icon.get_width() + 6
        name_surf = self._name_font.render(zone.location.name, True, Colors.TEXT_PRIMARY)
        screen.blit(name_surf, (text_x, r.y + scale_y(6)))

        # Flavor text (small, below name)
        if zone.location.flavor_text:
            flavor = zone.location.flavor_text
            if len(flavor) > 45:
                flavor = flavor[:42] + "..."
            fl_surf = self._label_font.render(flavor, True, Colors.TEXT_SECONDARY)
            screen.blit(fl_surf, (text_x, r.y + scale_y(28)))


# ==========================================================================
# Crimson Reach — Dark Minimal
# ==========================================================================


class ReachDarkLayout(StationLayout):
    """Dark minimal layout. Dangerous, sparse, barely visible."""

    accent_color = (180, 50, 40)
    bg_tint = (20, 5, 5, 15)
    faction_tagline = "No laws. No mercy. No refunds."

    def build_zones(self, sprite_mgr: object) -> list[StationZone]:
        from spacegame.engine.sprites import res_scale

        self.zones = []
        zone_w = scale_x(220)
        zone_h = scale_y(85)
        gap = scale_y(12)
        # Single column, centered, sparse
        total_h = len(self.locations) * zone_h + (len(self.locations) - 1) * gap
        start_y = _LAYOUT_TOP + (_LAYOUT_H - total_h) // 2

        for i, loc in enumerate(self.locations):
            # Alternate left/right offset for asymmetry
            offset = scale_x(30) if i % 2 == 0 else scale_x(-30)
            x = (WINDOW_WIDTH - zone_w) // 2 + offset
            y = start_y + i * (zone_h + gap)
            rect = pygame.Rect(x, y, zone_w, zone_h)
            color = LOCATION_COLORS.get(loc.location_type, self.accent_color)
            icon = sprite_mgr.get_location_icon(loc.location_type, scale=res_scale(2))
            self.zones.append(
                StationZone(
                    location=loc,
                    rect=rect,
                    label=loc.name,
                    accent_color=color,
                    icon=icon,
                )
            )
        return self.zones

    def update(self, dt: float) -> None:
        super().update(dt)
        # Dim flickering embers (red, sparse, slow)
        import random as _rng

        self._ambient_emit_timer += dt
        if self._ambient_emit_timer >= 1.2:
            self._ambient_emit_timer -= 1.2
            self._ambient_particles.append(
                {
                    "x": _rng.uniform(scale_x(80), WINDOW_WIDTH - scale_x(80)),
                    "y": _rng.uniform(_LAYOUT_TOP + scale_y(20), _LAYOUT_BOTTOM - scale_y(20)),
                    "vx": _rng.uniform(-3, 3),
                    "vy": _rng.uniform(-8, -2),
                    "life": _rng.uniform(1.5, 3.0),
                    "max_life": 3.0,
                    "alpha": _rng.randint(15, 35),
                    "color": (_rng.randint(140, 180), _rng.randint(30, 60), _rng.randint(20, 40)),
                    "size": _rng.uniform(1, 2),
                }
            )

    def _render_default_zone(
        self, screen: pygame.Surface, zone: StationZone, alpha_mult: float = 1.0
    ) -> None:
        """Override: zones barely visible until hovered."""
        r = zone.rect

        if zone.hovered:
            # Revealed: zone lights up
            zone_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            zone_surf.fill((25, 12, 12, 200))
            screen.blit(zone_surf, r.topleft)
            pygame.draw.rect(screen, self.accent_color, r, 2, border_radius=3)

            # Full content
            text_x = r.x + 12
            if zone.icon:
                screen.blit(zone.icon, (r.x + 8, r.y + (r.height - zone.icon.get_height()) // 2))
                text_x = r.x + 8 + zone.icon.get_width() + 6
            name_surf = self._name_font.render(zone.location.name, True, Colors.TEXT_PRIMARY)
            screen.blit(name_surf, (text_x, r.y + (r.height - name_surf.get_height()) // 2))
        else:
            # Hidden: faint outline, dim text
            zone_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            zone_surf.fill((12, 8, 8, 80))
            screen.blit(zone_surf, r.topleft)
            pygame.draw.rect(screen, (50, 25, 25), r, 1, border_radius=3)

            # Dim name only
            name_surf = self._name_font.render(zone.location.name, True, (80, 60, 60))
            screen.blit(name_surf, (r.x + 12, r.y + (r.height - name_surf.get_height()) // 2))

    def render_atmosphere(self, screen: pygame.Surface) -> None:
        """Flickering ambient effect."""
        # Random flicker on one zone
        if int(self._elapsed * 8) % 13 == 0 and self.zones:
            idx = int(self._elapsed * 3) % len(self.zones)
            r = self.zones[idx].rect
            flicker = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            flicker.fill((180, 50, 40, 15))
            screen.blit(flicker, r.topleft)


# ==========================================================================
# Layout Factory
# ==========================================================================

_LAYOUT_CLASSES: dict[str, type[StationLayout]] = {
    "guild": GuildDeckLayout,
    "union": UnionBlueprintLayout,
    "collective": CollectiveRadialLayout,
    "frontier": FrontierScatteredLayout,
    "reach": ReachDarkLayout,
}


def create_station_layout(
    locations: list,
    system_id: str,
    sprite_mgr: object,
) -> StationLayout:
    """Factory: create the appropriate layout for a system.

    Args:
        locations: List of Location objects at this system.
        system_id: System identifier for faction lookup.
        sprite_mgr: SpriteManager for loading icons.

    Returns:
        Initialized StationLayout with zones built.
    """
    layout_key = SYSTEM_LAYOUT_MAP.get(system_id, "reach")
    layout_cls = _LAYOUT_CLASSES.get(layout_key, ReachDarkLayout)
    layout = layout_cls(locations, system_id)
    layout.build_zones(sprite_mgr)
    return layout
