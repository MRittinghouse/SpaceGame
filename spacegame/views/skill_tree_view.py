"""
Skill tree view.

Visual skill tree with clickable nodes for investing skill points.
Features radial gradient nodes, glow halos, pulsing borders, animated connections.
"""

import pygame
import pygame_gui
import math
from typing import Optional, Dict, List
from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.progression import PlayerProgression, SkillNode, SkillTreeType
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import ParticlePool, COLLECT_SPARKLE
from spacegame.engine.draw_utils import draw_bar, draw_panel
from spacegame.engine.fonts import FontCache
from spacegame.engine.sprites import get_sprite_manager
from spacegame.engine.audio_manager import get_audio_manager

# Node positions for rendering (tree_type -> {skill_id: (x, y)})
# 6 trees distributed across 1280px
SKILL_POSITIONS = {
    SkillTreeType.TRADING: {
        "negotiator": (100, 200),
        "market_eye": (40, 340),
        "bulk_trader": (160, 340),
        "trade_network": (40, 480),
        "market_insider": (40, 620),
        "commodity_specialist": (100, 620),
        "smuggler_contacts": (160, 480),
        "market_manipulation": (100, 750),
    },
    SkillTreeType.GATHERING: {
        "efficient_drills": (310, 200),
        "keen_scanner": (250, 340),
        "rich_veins": (370, 340),
        "master_extractor": (250, 480),
        "refining_knowledge": (250, 620),
        "efficient_refining": (185, 620),
        "yield_mastery": (310, 620),
    },
    SkillTreeType.MINING: {
        "click_power": (530, 200),
        "passive_drill": (460, 340),
        "deep_scan": (460, 480),
        "drone_bay_1": (600, 340),
        "drone_bay_2": (635, 480),
        "drone_bay_3": (635, 620),
        "drone_efficiency": (530, 480),
        "ore_targeting": (530, 620),
        "chain_reaction": (460, 620),
    },
    SkillTreeType.LEADERSHIP: {
        "crew_manager": (730, 200),
        "diplomatic_relations": (670, 340),
        "inspiring_leader": (790, 340),
        "tariff_negotiation": (670, 480),
        "crew_mentor": (790, 480),
        "veteran_command": (730, 340),
        "crisis_management": (670, 620),
        "fleet_coordinator": (790, 620),
    },
    SkillTreeType.SOCIAL: {
        "silver_tongue": (920, 200),
        "commanding_presence": (860, 340),
        "keen_insight": (980, 340),
        "master_negotiator": (860, 480),
        "streetwise": (980, 480),
        "empathic_read": (1040, 480),
        "silver_lining": (860, 620),
        "faction_diplomat": (920, 620),
    },
    SkillTreeType.GROUND: {
        "scrapper": (1080, 200),
        "tough_hide": (1180, 200),
        "quick_reflexes": (1080, 340),
        "last_stand": (1180, 340),
        "intimidating_presence": (1080, 480),
        "veteran": (1130, 620),
    },
    SkillTreeType.COMBAT: {
        "weapons_training": (1360, 200),
        "evasive_maneuvers": (1480, 200),
        "precision_targeting": (1300, 340),
        "combat_veteran": (1420, 340),
        "shield_mastery": (1540, 340),
        "tactical_retreat": (1540, 480),
        "broadside": (1300, 480),
    },
    SkillTreeType.EXPLORATION: {
        "fuel_efficiency": (1700, 200),
        "stellar_cartography": (1820, 200),
        "efficient_routing": (1640, 340),
        "salvage_instinct": (1760, 340),
        "hazard_scanner": (1820, 340),
        "long_range_scanner": (1880, 340),
        "explorer_reputation": (1880, 480),
    },
    SkillTreeType.SMUGGLING: {
        "hidden_compartments": (2060, 200),
        "bribe_mastery": (2000, 340),
        "scan_jamming": (2120, 340),
        "black_market_access": (2000, 480),
        "heat_management": (2120, 480),
        "ghost_runner": (2060, 620),
    },
}

NODE_RADIUS = 35

# Total content width (rightmost node + padding)
SCROLL_MAX = 1000  # Maximum scroll offset (content extends to ~2200px)
SCROLL_SPEED = 300  # Pixels per second for smooth scrolling


class SkillTreeView(BaseView):
    """Visual skill tree with scrollable branches and enhanced visuals."""

    def __init__(self, ui_manager: pygame_gui.UIManager, progression: PlayerProgression):
        super().__init__()
        self.ui_manager = ui_manager
        self.progression = progression
        self.next_state: Optional[GameState] = None
        self.hovered_skill: Optional[str] = None

        # Horizontal scroll
        self._scroll_x: float = 0.0
        self._scroll_target: float = 0.0

        # Fonts
        self.title_font = FontCache.get(36)
        self.header_font = FontCache.get(28)
        self.info_font = FontCache.get(22)
        self.small_font = FontCache.get(18)
        self.node_font = FontCache.get(16)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.scroll_left_btn: Optional[pygame_gui.elements.UIButton] = None
        self.scroll_right_btn: Optional[pygame_gui.elements.UIButton] = None

        # Sprites
        self._sprite_mgr = get_sprite_manager()

        # Message
        self.message: str = ""
        self.message_timer: float = 0.0

        # Visual
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=80)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(80)

        self.particles = ParticlePool(100)
        self._glow_time = 0.0
        self._energy_dot_offset = 0.0
        self._node_surface_cache: Dict[str, pygame.Surface] = {}

    def on_enter(self) -> None:
        super().on_enter()
        self._build_node_cache()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH // 2 - 75, WINDOW_HEIGHT - 60, 150, 40),
            text="Back",
            manager=self.ui_manager,
        )
        self.scroll_left_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(10, WINDOW_HEIGHT // 2 - 20, 40, 40),
            text="<",
            manager=self.ui_manager,
        )
        self.scroll_right_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH - 50, WINDOW_HEIGHT // 2 - 20, 40, 40),
            text=">",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        for elem in [self.back_button, self.scroll_left_btn, self.scroll_right_btn]:
            if elem:
                elem.kill()

    def _build_node_cache(self) -> None:
        """Pre-render radial gradient node surfaces for each visual state."""
        states = {
            "maxed": (50, 150, 50),
            "unlocked": (40, 80, 140),
            "available": (60, 60, 30),
            "locked": Colors.BAR_BG,
        }
        self._node_surface_cache.clear()
        for state_name, color in states.items():
            self._node_surface_cache[state_name] = self._make_node_surface(color)
            hover_color = tuple(min(255, c + 30) for c in color)
            self._node_surface_cache[f"{state_name}_hover"] = self._make_node_surface(hover_color)

    def _make_node_surface(self, fill_color: tuple) -> pygame.Surface:
        """Create a radial gradient circle surface for a node."""
        node_surf = pygame.Surface((NODE_RADIUS * 2 + 4, NODE_RADIUS * 2 + 4), pygame.SRCALPHA)
        center = NODE_RADIUS + 2
        for r in range(NODE_RADIUS, 0, -1):
            t = 1.0 - (r / NODE_RADIUS)
            gr = int(fill_color[0] + (min(255, fill_color[0] + 40) - fill_color[0]) * t)
            gg = int(fill_color[1] + (min(255, fill_color[1] + 40) - fill_color[1]) * t)
            gb = int(fill_color[2] + (min(255, fill_color[2] + 40) - fill_color[2]) * t)
            pygame.draw.circle(node_surf, (gr, gg, gb, 255), (center, center), r)
        return node_surf

    def _get_skill_at_pos(self, pos: tuple) -> Optional[str]:
        mx, my = pos
        offset = int(self._scroll_x)
        for tree_type, positions in SKILL_POSITIONS.items():
            for skill_id, (sx, sy) in positions.items():
                screen_x = sx - offset
                dist = ((mx - screen_x) ** 2 + (my - sy) ** 2) ** 0.5
                if dist <= NODE_RADIUS:
                    return skill_id
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hovered_skill = self._get_skill_at_pos(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            skill_id = self._get_skill_at_pos(event.pos)
            if skill_id:
                success, msg = self.progression.level_up_skill(skill_id)
                self._show_message(msg)
                if success:
                    get_audio_manager().play_sfx("skill_unlock")
                    # Level-up particle burst from node
                    for tree_type, positions in SKILL_POSITIONS.items():
                        if skill_id in positions:
                            sx, sy = positions[skill_id]
                            self.particles.emit(sx, sy, COLLECT_SPARKLE)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self._scroll_target = max(0, self._scroll_target - 400)
            elif event.key == pygame.K_RIGHT:
                self._scroll_target = min(SCROLL_MAX, self._scroll_target + 400)

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.scroll_left_btn:
                self._scroll_target = max(0, self._scroll_target - 400)
            elif event.ui_element == self.scroll_right_btn:
                self._scroll_target = min(SCROLL_MAX, self._scroll_target + 400)
            elif event.ui_element == self.back_button:
                self.next_state = GameState.CHARACTER

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 3.0

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt
        self._energy_dot_offset += dt * 0.3  # Speed of energy flow dots

        # Smooth scroll toward target
        diff = self._scroll_target - self._scroll_x
        if abs(diff) > 1:
            self._scroll_x += diff * min(1.0, dt * 8.0)
        else:
            self._scroll_x = self._scroll_target

        if self.message_timer > 0:
            self.message_timer -= dt

    def render(self, screen: pygame.Surface) -> None:
        # Background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title = self.title_font.render("SKILL TREES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        # Player stats bar
        xp_next = self.progression.get_xp_for_next_level()
        xp_str = f"{self.progression.xp}/{xp_next}"
        stats = self.info_font.render(
            f"Level {self.progression.level}  |  XP: {xp_str}  |  "
            f"Skill Points: {self.progression.get_available_skill_points()}",
            True,
            Colors.TEXT,
        )
        screen.blit(stats, stats.get_rect(center=(WINDOW_WIDTH // 2, 65)))

        # XP progress bar
        bar_x = WINDOW_WIDTH // 2 - 200
        bar_y = 82
        bar_w = 400
        bar_h = 12
        progress = self.progression.get_xp_progress()
        xp_max = xp_next
        xp_current_in_level = int(xp_max * progress)
        draw_bar(
            screen, bar_x, bar_y, bar_w, bar_h,
            xp_current_in_level, xp_max,
            Colors.TEXT_HIGHLIGHT,
            show_value=False,
            border_color=Colors.TEXT_SECONDARY,
        )

        # Tree headers with attribute subtitles
        offset = int(self._scroll_x)
        _headers = [
            ("TRADING MASTERY", "Commerce", 100, Colors.FACTION_COMMERCE),
            ("RESOURCE GATHERING", "Acuity", 310, Colors.FACTION_FRONTIER),
            ("MINING MASTERY", "Resolve", 530, Colors.GLOW_ORANGE),
            ("LEADERSHIP", "Ingenuity", 730, Colors.FACTION_SCIENCE),
            ("SOCIAL ARTS", "Synergy", 920, Colors.ATTR_HIGHLIGHT),
            ("GROUND COMBAT", "Resolve", 1130, Colors.RED),
            ("COMBAT & TACTICS", "Combat", 1420, Colors.RED),
            ("EXPLORATION", "Acuity", 1760, Colors.FACTION_FRONTIER),
            ("SMUGGLING", "Ingenuity", 2060, Colors.GLOW_ORANGE),
        ]
        for header_text, attr_name, hx, color in _headers:
            screen_hx = hx - offset
            if -200 < screen_hx < WINDOW_WIDTH + 200:
                h_surf = self.header_font.render(header_text, True, color)
                screen.blit(h_surf, h_surf.get_rect(center=(screen_hx, 140)))
                a_surf = self.small_font.render(attr_name, True, Colors.TEXT_SECONDARY)
                screen.blit(a_surf, a_surf.get_rect(center=(screen_hx, 162)))

        # Scroll indicator
        if self._scroll_target < SCROLL_MAX:
            hint = self.small_font.render("Arrow keys or < > to scroll", True, Colors.TEXT_SECONDARY)
            screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 85)))

        # Draw connection lines first
        self._draw_connections(screen)

        # Draw nodes
        for tree_type, positions in SKILL_POSITIONS.items():
            for skill_id, (sx, sy) in positions.items():
                screen_x = sx - offset
                if -NODE_RADIUS < screen_x < WINDOW_WIDTH + NODE_RADIUS:
                    self._draw_node(screen, skill_id, screen_x, sy)

        # Particles on top
        self.particles.render(screen)

        # Draw tooltip for hovered skill
        if self.hovered_skill:
            self._draw_tooltip(screen)

        # Message
        if self.message_timer > 0:
            color = Colors.SUCCESS if "leveled" in self.message.lower() else Colors.YELLOW
            msg_surf = self.info_font.render(self.message, True, color)
            screen.blit(
                msg_surf, msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 100))
            )

    def _draw_connections(self, screen: pygame.Surface) -> None:
        offset = int(self._scroll_x)
        for tree_type, positions in SKILL_POSITIONS.items():
            for skill_id, (sx, sy) in positions.items():
                skill = self.progression.skills.get(skill_id)
                if skill and skill.prerequisite_id:
                    prereq_pos = positions.get(skill.prerequisite_id)
                    if prereq_pos:
                        # Apply scroll offset to both endpoints
                        screen_sx = sx - offset
                        screen_px = prereq_pos[0] - offset
                        # Cull off-screen connections
                        if max(screen_sx, screen_px) < -50 or min(screen_sx, screen_px) > WINDOW_WIDTH + 50:
                            continue

                        prereq_skill = self.progression.skills.get(skill.prerequisite_id)
                        is_unlocked = prereq_skill and prereq_skill.is_unlocked

                        start = (screen_px, prereq_pos[1])
                        end = (screen_sx, sy)

                        if is_unlocked:
                            color = (60, 180, 80)
                            pygame.draw.line(screen, color, start, end, 2)

                            # Energy flow dot
                            dot_t = self._energy_dot_offset % 1.0
                            dot_x = int(start[0] + (end[0] - start[0]) * dot_t)
                            dot_y = int(start[1] + (end[1] - start[1]) * dot_t)
                            dot_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
                            pygame.draw.circle(dot_surf, (100, 255, 150, 200), (4, 4), 3)
                            pygame.draw.circle(dot_surf, (100, 255, 150, 80), (4, 4), 4)
                            screen.blit(dot_surf, (dot_x - 4, dot_y - 4))
                        else:
                            self._draw_dashed_connection(screen, start, end, (35, 35, 45))

    def _draw_dashed_connection(
        self,
        screen: pygame.Surface,
        start: tuple,
        end: tuple,
        color: tuple,
        dash_len: int = 6,
        gap: int = 4,
    ) -> None:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = max(1, math.sqrt(dx * dx + dy * dy))
        nx, ny = dx / dist, dy / dist
        pos = 0.0
        while pos < dist:
            seg_end = min(dist, pos + dash_len)
            if seg_end > pos:
                sx = int(start[0] + nx * pos)
                sy = int(start[1] + ny * pos)
                ex = int(start[0] + nx * seg_end)
                ey = int(start[1] + ny * seg_end)
                pygame.draw.line(screen, color, (sx, sy), (ex, ey), 1)
            pos += dash_len + gap

    def _draw_node(self, screen: pygame.Surface, skill_id: str, x: int, y: int) -> None:
        skill = self.progression.skills.get(skill_id)
        if not skill:
            return

        is_hovered = self.hovered_skill == skill_id
        unlocked = {sid: s for sid, s in self.progression.skills.items() if s.is_unlocked}
        can_level = skill.can_level_up(self.progression.get_available_skill_points(), unlocked)

        # Determine state key and border color
        if skill.is_maxed:
            state_key = "maxed"
            border_color = Colors.SUCCESS
        elif skill.is_unlocked:
            state_key = "unlocked"
            border_color = Colors.TEXT_HIGHLIGHT
        elif can_level:
            state_key = "available"
            border_color = Colors.YELLOW
        else:
            state_key = "locked"
            border_color = (60, 60, 70)

        if is_hovered:
            state_key += "_hover"

        # Use pre-rendered radial gradient surface
        node_surf = self._node_surface_cache.get(state_key)
        if node_surf:
            center = NODE_RADIUS + 2
            screen.blit(node_surf, (x - center, y - center))

        # Maxed nodes: persistent glow halo
        if skill.is_maxed:
            glow_alpha = int(40 + 20 * math.sin(self._glow_time * 2))
            halo_surf = pygame.Surface((NODE_RADIUS * 3, NODE_RADIUS * 3), pygame.SRCALPHA)
            hc = NODE_RADIUS * 3 // 2
            pygame.draw.circle(
                halo_surf, (*Colors.SUCCESS, glow_alpha), (hc, hc), NODE_RADIUS + 8, 3
            )
            screen.blit(halo_surf, (x - hc, y - hc))

        # Available nodes: pulsing border
        if can_level and not skill.is_maxed:
            pulse_alpha = int(150 + 80 * math.sin(self._glow_time * 4))
            pulse_color = (*Colors.YELLOW[:3], pulse_alpha)
            pulse_surf = pygame.Surface((NODE_RADIUS * 2 + 8, NODE_RADIUS * 2 + 8), pygame.SRCALPHA)
            pc = NODE_RADIUS + 4
            pygame.draw.circle(pulse_surf, pulse_color, (pc, pc), NODE_RADIUS + 2, 2)
            screen.blit(pulse_surf, (x - pc, y - pc))
        else:
            # Standard border
            pygame.draw.circle(screen, border_color, (x, y), NODE_RADIUS, 2)

        # Skill icon (centered in node, text shifts below)
        icon = self._sprite_mgr.get_skill_icon(skill_id, scale=2)
        if icon:
            icon_rect = icon.get_rect(center=(x, y - 6))
            screen.blit(icon, icon_rect)
            # Compact name below icon
            name_surf = self.node_font.render(skill.name, True, Colors.TEXT)
            screen.blit(name_surf, name_surf.get_rect(center=(x, y + 18)))
        else:
            # Fallback: text-only layout
            words = skill.name.split()
            if len(words) > 1:
                line1 = self.node_font.render(words[0], True, Colors.TEXT)
                line2 = self.node_font.render(" ".join(words[1:]), True, Colors.TEXT)
                screen.blit(line1, line1.get_rect(center=(x, y - 8)))
                screen.blit(line2, line2.get_rect(center=(x, y + 8)))
            else:
                name_surf = self.node_font.render(skill.name, True, Colors.TEXT)
                screen.blit(name_surf, name_surf.get_rect(center=(x, y)))

        # Level indicator below
        level_str = f"{skill.current_level}/{skill.max_level}"
        level_surf = self.small_font.render(level_str, True, Colors.TEXT_SECONDARY)
        screen.blit(level_surf, level_surf.get_rect(center=(x, y + NODE_RADIUS + 12)))

    def _draw_tooltip(self, screen: pygame.Surface) -> None:
        skill = self.progression.skills.get(self.hovered_skill)
        if not skill:
            return

        mx, my = pygame.mouse.get_pos()
        tw, th = 280, 100
        tx = min(mx + 15, WINDOW_WIDTH - tw - 10)
        ty = min(my + 15, WINDOW_HEIGHT - th - 10)

        # Background
        draw_panel(
            screen,
            pygame.Rect(tx, ty, tw, th),
            alpha=230,
            bg_color=(12, 12, 28),
            border_color=Colors.TEXT_HIGHLIGHT,
            border_radius=4,
        )

        # Content
        name = self.info_font.render(skill.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name, (tx + 8, ty + 5))

        desc = self.small_font.render(skill.description, True, Colors.TEXT)
        screen.blit(desc, (tx + 8, ty + 28))

        level = self.small_font.render(
            f"Level: {skill.current_level}/{skill.max_level}", True, Colors.TEXT_SECONDARY
        )
        screen.blit(level, (tx + 8, ty + 48))

        if skill.prerequisite_id:
            prereq = self.progression.skills.get(skill.prerequisite_id)
            prereq_name = prereq.name if prereq else skill.prerequisite_id
            prereq_text = self.small_font.render(f"Requires: {prereq_name}", True, Colors.YELLOW)
            screen.blit(prereq_text, (tx + 8, ty + 68))

        if skill.is_unlocked and skill.bonus_per_level > 0:
            bonus = self.small_font.render(
                (
                    f"Current bonus: {skill.get_bonus():.0%}"
                    if skill.bonus_per_level < 1
                    else f"Current bonus: {skill.get_bonus():.0f}"
                ),
                True,
                Colors.SUCCESS,
            )
            screen.blit(bonus, (tx + 8, ty + 80))

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
