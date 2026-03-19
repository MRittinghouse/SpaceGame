"""
Skill tree view — two-mode interface.

Mode 1 (Selector): 3x3 grid of skill tree cards showing investment progress.
Mode 2 (Detail): Individual tree with horizontal node layout by depth.
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

# Tree metadata for display
_TREE_INFO: Dict[SkillTreeType, dict] = {
    SkillTreeType.TRADING: {
        "name": "Trading Mastery", "attr": "Commerce",
        "desc": "Market prices, bulk trading, trade networks",
        "color": Colors.FACTION_COMMERCE,
    },
    SkillTreeType.GATHERING: {
        "name": "Resource Gathering", "attr": "Acuity",
        "desc": "Drill efficiency, scanning, refining knowledge",
        "color": Colors.FACTION_FRONTIER,
    },
    SkillTreeType.MINING: {
        "name": "Mining Mastery", "attr": "Resolve",
        "desc": "Click power, drones, deep scanning, chain reactions",
        "color": Colors.GLOW_ORANGE,
    },
    SkillTreeType.LEADERSHIP: {
        "name": "Leadership", "attr": "Ingenuity",
        "desc": "Crew management, diplomacy, fleet coordination",
        "color": Colors.FACTION_SCIENCE,
    },
    SkillTreeType.SOCIAL: {
        "name": "Social Arts", "attr": "Synergy",
        "desc": "Persuasion, insight, faction diplomacy",
        "color": Colors.ATTR_HIGHLIGHT,
    },
    SkillTreeType.GROUND: {
        "name": "Ground Combat", "attr": "Resolve",
        "desc": "Melee skills, toughness, field tactics",
        "color": Colors.RED,
    },
    SkillTreeType.COMBAT: {
        "name": "Combat & Tactics", "attr": "Combat",
        "desc": "Weapons, evasion, shields, ship combat",
        "color": Colors.RED,
    },
    SkillTreeType.EXPLORATION: {
        "name": "Exploration", "attr": "Acuity",
        "desc": "Fuel efficiency, scanning, hazard detection",
        "color": Colors.FACTION_FRONTIER,
    },
    SkillTreeType.SMUGGLING: {
        "name": "Smuggling", "attr": "Ingenuity",
        "desc": "Hidden cargo, bribes, scan jamming",
        "color": Colors.GLOW_ORANGE,
    },
}

# Selector layout
CARD_W = 380
CARD_H = 155
CARD_PAD = 14
CARDS_PER_ROW = 3
GRID_W = CARDS_PER_ROW * CARD_W + (CARDS_PER_ROW - 1) * CARD_PAD
GRID_X = (WINDOW_WIDTH - GRID_W) // 2
GRID_Y = 105

# Detail node layout
NODE_RADIUS = 32
DETAIL_TOP = 100
DETAIL_BOTTOM = WINDOW_HEIGHT - 80
DETAIL_LEFT = 100
DETAIL_RIGHT = WINDOW_WIDTH - 100


class SkillTreeView(BaseView):
    """Skill tree selector + individual tree detail view."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        progression: PlayerProgression,
        player: Optional["Player"] = None,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.progression = progression
        self._player = player
        self.next_state: Optional[GameState] = None
        self.hovered_skill: Optional[str] = None

        # View mode
        self._selected_tree: Optional[SkillTreeType] = None  # None = selector mode

        # Fonts
        self.title_font = FontCache.get(32)
        self.header_font = FontCache.get(24)
        self.info_font = FontCache.get(20)
        self.small_font = FontCache.get(16)
        self.node_font = FontCache.get(14)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.respec_button: Optional[pygame_gui.elements.UIButton] = None
        self._card_rects: list[tuple[pygame.Rect, SkillTreeType]] = []
        self._hovered_card: Optional[int] = None

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

        # Detail mode: computed node positions (skill_id -> (x, y))
        self._detail_positions: Dict[str, tuple[int, int]] = {}

    def on_enter(self) -> None:
        super().on_enter()
        self._build_node_cache()
        self._selected_tree = None
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    # === UI lifecycle ===

    def _create_ui(self) -> None:
        self._destroy_ui()

        if self._selected_tree is None:
            self._create_selector_ui()
        else:
            self._create_detail_ui()

    def _create_selector_ui(self) -> None:
        """Create the 3x3 tree selector grid (manual click rects, not buttons)."""
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH // 2 - 75, WINDOW_HEIGHT - 55, 150, 38
            ),
            text="Back",
            manager=self.ui_manager,
        )

        self._card_rects = []
        for i, tree_type in enumerate(SkillTreeType):
            row = i // CARDS_PER_ROW
            col = i % CARDS_PER_ROW
            x = GRID_X + col * (CARD_W + CARD_PAD)
            y = GRID_Y + row * (CARD_H + CARD_PAD)
            self._card_rects.append((pygame.Rect(x, y, CARD_W, CARD_H), tree_type))

    def _create_detail_ui(self) -> None:
        """Create UI for the individual tree detail view."""
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20, WINDOW_HEIGHT - 55, 120, 38),
            text="Back",
            manager=self.ui_manager,
        )
        self.respec_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH - 170, WINDOW_HEIGHT - 55, 150, 38),
            text="Respec Skills",
            manager=self.ui_manager,
        )
        self._compute_detail_positions()

    def _destroy_ui(self) -> None:
        for elem in [self.back_button, self.respec_button]:
            if elem:
                elem.kill()
        self.back_button = None
        self.respec_button = None
        self._card_rects = []
        self._hovered_card = None

    # === Node position computation for detail mode ===

    def _compute_detail_positions(self) -> None:
        """Compute horizontal layout positions for the selected tree's nodes."""
        self._detail_positions.clear()
        if not self._selected_tree:
            return

        skills = self.progression.get_skill_tree(self._selected_tree)
        if not skills:
            return

        # Build depth map: depth = 0 for roots, depth(prereq) + 1 otherwise
        skill_map = {s.id: s for s in skills}
        depths: Dict[str, int] = {}

        def get_depth(sid: str) -> int:
            if sid in depths:
                return depths[sid]
            skill = skill_map.get(sid)
            if not skill or not skill.prerequisite_id or skill.prerequisite_id not in skill_map:
                depths[sid] = 0
                return 0
            d = get_depth(skill.prerequisite_id) + 1
            depths[sid] = d
            return d

        for s in skills:
            get_depth(s.id)

        # Group by depth
        by_depth: Dict[int, list[str]] = {}
        for sid, d in depths.items():
            by_depth.setdefault(d, []).append(sid)

        max_depth = max(by_depth.keys()) if by_depth else 0

        # Layout: columns left-to-right by depth, rows top-to-bottom per column
        available_w = DETAIL_RIGHT - DETAIL_LEFT
        available_h = DETAIL_BOTTOM - DETAIL_TOP
        col_spacing = available_w / max(1, max_depth) if max_depth > 0 else available_w

        for depth, sids in by_depth.items():
            x = DETAIL_LEFT + int(depth * col_spacing)
            count = len(sids)
            row_spacing = available_h / (count + 1)
            for j, sid in enumerate(sids):
                y = DETAIL_TOP + int((j + 1) * row_spacing)
                self._detail_positions[sid] = (x, y)

    # === Event handling ===

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._selected_tree is not None:
                self._selected_tree = None
                self._create_ui()
            else:
                self.next_state = GameState.CHARACTER
            return

        if event.type == pygame.MOUSEMOTION:
            if self._selected_tree is not None:
                self.hovered_skill = self._get_skill_at_pos(event.pos)
            else:
                # Track hovered card for highlight
                self._hovered_card = None
                for i, (rect, _) in enumerate(self._card_rects):
                    if rect.collidepoint(event.pos):
                        self._hovered_card = i
                        break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._selected_tree is not None:
                skill_id = self._get_skill_at_pos(event.pos)
                if skill_id:
                    success, msg = self.progression.level_up_skill(skill_id)
                    self._show_message(msg)
                    if success:
                        get_audio_manager().play_sfx("skill_unlock")
                        pos = self._detail_positions.get(skill_id)
                        if pos:
                            self.particles.emit(pos[0], pos[1], COLLECT_SPARKLE)
            else:
                # Check card clicks in selector mode
                for rect, tree_type in self._card_rects:
                    if rect.collidepoint(event.pos):
                        self._selected_tree = tree_type
                        self._create_ui()
                        return

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                if self._selected_tree is not None:
                    self._selected_tree = None
                    self.hovered_skill = None
                    self._create_ui()
                else:
                    self.next_state = GameState.CHARACTER
            elif self.respec_button and event.ui_element == self.respec_button:
                if self.progression.skill_points_spent == 0:
                    self._show_message("No skills invested to reset")
                else:
                    level = self.progression.level
                    credits = self._player.credits if self._player else 0
                    success, msg = self.progression.respec_skills(
                        player_level=level, player_credits=credits,
                    )
                    self._show_message(msg)
                    if success and self._player:
                        from spacegame.models.progression import RESPEC_COST_PER_LEVEL
                        self._player.deduct_credits(RESPEC_COST_PER_LEVEL * level)
                        self._node_surface_cache.clear()
                        self._build_node_cache()

    def _get_skill_at_pos(self, pos: tuple) -> Optional[str]:
        mx, my = pos
        for skill_id, (sx, sy) in self._detail_positions.items():
            dist = ((mx - sx) ** 2 + (my - sy) ** 2) ** 0.5
            if dist <= NODE_RADIUS:
                return skill_id
        return None

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 3.0

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt
        self._energy_dot_offset += dt * 0.3
        if self.message_timer > 0:
            self.message_timer -= dt

    # === Rendering ===

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        if self._selected_tree is None:
            self._render_selector(screen)
        else:
            self._render_detail(screen)

        # Message
        if self.message_timer > 0:
            color = Colors.SUCCESS if "leveled" in self.message.lower() else Colors.YELLOW
            msg_surf = self.info_font.render(self.message, True, color)
            screen.blit(
                msg_surf, msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 70))
            )

    # === Selector mode rendering ===

    def _render_selector(self, screen: pygame.Surface) -> None:
        """Render the 3x3 tree selector grid."""
        # Title
        title = self.title_font.render("SKILL TREES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        # Stats bar
        sp = self.progression.get_available_skill_points()
        sp_color = Colors.YELLOW if sp > 0 else Colors.TEXT_SECONDARY
        stats_text = (
            f"Level {self.progression.level}  |  "
            f"Skill Points: {sp}"
        )
        stats = self.info_font.render(stats_text, True, sp_color)
        screen.blit(stats, stats.get_rect(center=(WINDOW_WIDTH // 2, 60)))

        # XP bar
        bar_w = 300
        draw_bar(
            screen, WINDOW_WIDTH // 2 - bar_w // 2, 76, bar_w, 8,
            self.progression.get_xp_progress(), 1.0,
            Colors.TEXT_HIGHLIGHT, show_value=False,
            border_color=Colors.TEXT_SECONDARY,
        )

        # Render tree cards (draw_panel + content, no pygame_gui buttons)
        for i, (rect, tree_type) in enumerate(self._card_rects):
            is_hovered = self._hovered_card == i
            border = _TREE_INFO[tree_type]["color"] if is_hovered else Colors.UI_BORDER
            draw_panel(screen, rect, alpha=200 if is_hovered else 180, border_color=border)
            self._render_tree_card(screen, tree_type, rect.x, rect.y)

    def _render_tree_card(
        self, screen: pygame.Surface, tree_type: SkillTreeType, x: int, y: int
    ) -> None:
        """Render content overlay for a tree selector card."""
        info = _TREE_INFO[tree_type]
        color = info["color"]
        skills = self.progression.get_skill_tree(tree_type)
        invested = sum(s.current_level for s in skills)
        total_max = sum(s.max_level for s in skills)
        unlocked = sum(1 for s in skills if s.is_unlocked)

        # Accent line at top
        pygame.draw.rect(screen, color, (x, y, CARD_W, 3))

        # Tree name
        name_surf = self.header_font.render(info["name"], True, color)
        screen.blit(name_surf, (x + 12, y + 12))

        # Attribute badge
        attr_surf = self.small_font.render(info["attr"], True, Colors.TEXT_SECONDARY)
        screen.blit(attr_surf, (x + CARD_W - attr_surf.get_width() - 12, y + 16))

        # Description
        desc_surf = self.small_font.render(info["desc"], True, Colors.TEXT_SECONDARY)
        screen.blit(desc_surf, (x + 12, y + 42))

        # Progress bar
        bar_y = y + 65
        bar_w = CARD_W - 24
        progress = invested / max(1, total_max)
        draw_bar(
            screen, x + 12, bar_y, bar_w, 12,
            invested, total_max, color,
            show_value=False, border_color=Colors.UI_BORDER,
        )

        # Investment text
        inv_surf = self.small_font.render(
            f"{invested}/{total_max} points invested", True, Colors.TEXT_SECONDARY
        )
        screen.blit(inv_surf, (x + 12, bar_y + 18))

        # Skills unlocked
        unlocked_surf = self.small_font.render(
            f"{unlocked}/{len(skills)} skills unlocked", True, Colors.TEXT_SECONDARY
        )
        screen.blit(unlocked_surf, (x + 12, bar_y + 36))

        # Skill icons row (show first few skill icons)
        icon_x = x + 12
        icon_y = bar_y + 56
        shown = 0
        for s in skills:
            if shown >= 8:
                break
            icon = self._sprite_mgr.get_skill_icon(s.id, scale=1)
            if icon:
                # Dim locked icons
                if not s.is_unlocked:
                    icon = icon.copy()
                    icon.set_alpha(60)
                screen.blit(icon, (icon_x, icon_y))
                icon_x += icon.get_width() + 4
                shown += 1

    # === Detail mode rendering ===

    def _render_detail(self, screen: pygame.Surface) -> None:
        """Render the individual tree detail view."""
        info = _TREE_INFO[self._selected_tree]
        color = info["color"]

        # Title
        title = self.title_font.render(info["name"].upper(), True, color)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 25)))

        # Attribute + skill points
        sp = self.progression.get_available_skill_points()
        sp_color = Colors.YELLOW if sp > 0 else Colors.TEXT_SECONDARY
        sub = self.info_font.render(
            f"{info['attr']}  |  Skill Points: {sp}", True, sp_color
        )
        screen.blit(sub, sub.get_rect(center=(WINDOW_WIDTH // 2, 55)))

        # Description
        desc = self.small_font.render(info["desc"], True, Colors.TEXT_SECONDARY)
        screen.blit(desc, desc.get_rect(center=(WINDOW_WIDTH // 2, 78)))

        # Connection lines first
        self._draw_detail_connections(screen)

        # Nodes
        for skill_id, (sx, sy) in self._detail_positions.items():
            self._draw_node(screen, skill_id, sx, sy)

        # Particles
        self.particles.render(screen)

        # Tooltip
        if self.hovered_skill:
            self._draw_tooltip(screen)

    def _draw_detail_connections(self, screen: pygame.Surface) -> None:
        """Draw prerequisite connection lines for the detail view."""
        skills = self.progression.get_skill_tree(self._selected_tree)
        skill_map = {s.id: s for s in skills}

        for skill in skills:
            if skill.prerequisite_id and skill.prerequisite_id in self._detail_positions:
                start_pos = self._detail_positions.get(skill.prerequisite_id)
                end_pos = self._detail_positions.get(skill.id)
                if not start_pos or not end_pos:
                    continue

                prereq = skill_map.get(skill.prerequisite_id)
                is_unlocked = prereq and prereq.is_unlocked

                if is_unlocked:
                    pygame.draw.line(screen, (60, 180, 80), start_pos, end_pos, 2)
                    # Energy flow dot
                    dot_t = self._energy_dot_offset % 1.0
                    dot_x = int(start_pos[0] + (end_pos[0] - start_pos[0]) * dot_t)
                    dot_y = int(start_pos[1] + (end_pos[1] - start_pos[1]) * dot_t)
                    dot_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
                    pygame.draw.circle(dot_surf, (100, 255, 150, 200), (4, 4), 3)
                    screen.blit(dot_surf, (dot_x - 4, dot_y - 4))
                else:
                    self._draw_dashed_line(screen, start_pos, end_pos, (35, 35, 45))

    def _draw_dashed_line(
        self, screen: pygame.Surface, start: tuple, end: tuple,
        color: tuple, dash_len: int = 6, gap: int = 4,
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

    # === Shared node rendering ===

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
        node_surf = pygame.Surface((NODE_RADIUS * 2 + 4, NODE_RADIUS * 2 + 4), pygame.SRCALPHA)
        center = NODE_RADIUS + 2
        for r in range(NODE_RADIUS, 0, -1):
            t = 1.0 - (r / NODE_RADIUS)
            gr = int(fill_color[0] + (min(255, fill_color[0] + 40) - fill_color[0]) * t)
            gg = int(fill_color[1] + (min(255, fill_color[1] + 40) - fill_color[1]) * t)
            gb = int(fill_color[2] + (min(255, fill_color[2] + 40) - fill_color[2]) * t)
            pygame.draw.circle(node_surf, (gr, gg, gb, 255), (center, center), r)
        return node_surf

    def _draw_node(self, screen: pygame.Surface, skill_id: str, x: int, y: int) -> None:
        skill = self.progression.skills.get(skill_id)
        if not skill:
            return

        is_hovered = self.hovered_skill == skill_id
        unlocked = {sid: s for sid, s in self.progression.skills.items() if s.is_unlocked}
        can_level = skill.can_level_up(self.progression.get_available_skill_points(), unlocked)

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

        node_surf = self._node_surface_cache.get(state_key)
        if node_surf:
            center = NODE_RADIUS + 2
            screen.blit(node_surf, (x - center, y - center))

        # Maxed glow halo
        if skill.is_maxed:
            glow_alpha = int(40 + 20 * math.sin(self._glow_time * 2))
            halo_surf = pygame.Surface((NODE_RADIUS * 3, NODE_RADIUS * 3), pygame.SRCALPHA)
            hc = NODE_RADIUS * 3 // 2
            pygame.draw.circle(
                halo_surf, (*Colors.SUCCESS, glow_alpha), (hc, hc), NODE_RADIUS + 8, 3
            )
            screen.blit(halo_surf, (x - hc, y - hc))

        # Available pulsing border
        if can_level and not skill.is_maxed:
            pulse_alpha = int(150 + 80 * math.sin(self._glow_time * 4))
            pulse_color = (*Colors.YELLOW[:3], pulse_alpha)
            pulse_surf = pygame.Surface((NODE_RADIUS * 2 + 8, NODE_RADIUS * 2 + 8), pygame.SRCALPHA)
            pc = NODE_RADIUS + 4
            pygame.draw.circle(pulse_surf, pulse_color, (pc, pc), NODE_RADIUS + 2, 2)
            screen.blit(pulse_surf, (x - pc, y - pc))
        else:
            pygame.draw.circle(screen, border_color, (x, y), NODE_RADIUS, 2)

        # Skill icon
        icon = self._sprite_mgr.get_skill_icon(skill_id, scale=2)
        if icon:
            icon_rect = icon.get_rect(center=(x, y - 4))
            screen.blit(icon, icon_rect)
            name_surf = self.node_font.render(skill.name, True, Colors.TEXT)
            screen.blit(name_surf, name_surf.get_rect(center=(x, y + 16)))
        else:
            words = skill.name.split()
            if len(words) > 1:
                line1 = self.node_font.render(words[0], True, Colors.TEXT)
                line2 = self.node_font.render(" ".join(words[1:]), True, Colors.TEXT)
                screen.blit(line1, line1.get_rect(center=(x, y - 6)))
                screen.blit(line2, line2.get_rect(center=(x, y + 8)))
            else:
                name_surf = self.node_font.render(skill.name, True, Colors.TEXT)
                screen.blit(name_surf, name_surf.get_rect(center=(x, y)))

        # Level indicator
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

        draw_panel(
            screen, pygame.Rect(tx, ty, tw, th),
            alpha=230, bg_color=(12, 12, 28),
            border_color=Colors.TEXT_HIGHLIGHT, border_radius=4,
        )

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
                True, Colors.SUCCESS,
            )
            screen.blit(bonus, (tx + 8, ty + 80))

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
