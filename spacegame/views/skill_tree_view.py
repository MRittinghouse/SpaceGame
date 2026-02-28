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

# Node positions for rendering (tree_type -> {skill_id: (x, y)})
# 4 trees distributed across 1280px: Trading, Gathering, Mining, Leadership
SKILL_POSITIONS = {
    SkillTreeType.TRADING: {
        "negotiator": (160, 200),
        "market_eye": (80, 340),
        "bulk_trader": (240, 340),
        "trade_network": (80, 480),
        "market_insider": (80, 620),
    },
    SkillTreeType.GATHERING: {
        "efficient_drills": (460, 200),
        "keen_scanner": (380, 340),
        "rich_veins": (540, 340),
        "master_extractor": (380, 480),
        "refining_knowledge": (380, 620),
    },
    SkillTreeType.MINING: {
        "click_power": (740, 200),
        "passive_drill": (660, 340),
        "deep_scan": (660, 480),
        "drone_bay_1": (820, 340),
        "drone_bay_2": (880, 480),
        "drone_bay_3": (880, 620),
        "drone_efficiency": (740, 480),
        "ore_targeting": (740, 620),
    },
    SkillTreeType.LEADERSHIP: {
        "crew_manager": (1080, 200),
        "diplomatic_relations": (1000, 340),
        "inspiring_leader": (1160, 340),
        "tariff_negotiation": (1000, 480),
        "crew_mentor": (1160, 480),
    },
}

NODE_RADIUS = 35


class SkillTreeView(BaseView):
    """Visual skill tree with two branches and enhanced visuals."""

    def __init__(self, ui_manager: pygame_gui.UIManager, progression: PlayerProgression):
        super().__init__()
        self.ui_manager = ui_manager
        self.progression = progression
        self.next_state: Optional[GameState] = None
        self.hovered_skill: Optional[str] = None

        # Fonts
        self.title_font = pygame.font.Font(None, 36)
        self.header_font = pygame.font.Font(None, 28)
        self.info_font = pygame.font.Font(None, 22)
        self.small_font = pygame.font.Font(None, 18)
        self.node_font = pygame.font.Font(None, 16)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

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

    def on_enter(self) -> None:
        super().on_enter()
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

    def _destroy_ui(self) -> None:
        if self.back_button:
            self.back_button.kill()

    def _get_skill_at_pos(self, pos: tuple) -> Optional[str]:
        mx, my = pos
        for tree_type, positions in SKILL_POSITIONS.items():
            for skill_id, (sx, sy) in positions.items():
                dist = ((mx - sx) ** 2 + (my - sy) ** 2) ** 0.5
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
                    # Level-up particle burst from node
                    for tree_type, positions in SKILL_POSITIONS.items():
                        if skill_id in positions:
                            sx, sy = positions[skill_id]
                            self.particles.emit(sx, sy, COLLECT_SPARKLE)

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 3.0

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt
        self._energy_dot_offset += dt * 0.3  # Speed of energy flow dots

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
        xp_str = f"{self.progression.xp}/{xp_next}" if xp_next else f"{self.progression.xp} (MAX)"
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
        pygame.draw.rect(screen, (30, 30, 40), (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(bar_w * progress)
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, (bar_x, bar_y, fill_w, bar_h))
        if fill_w > 2:
            pygame.draw.rect(screen, (200, 240, 255), (bar_x + fill_w - 2, bar_y, 2, bar_h))
        pygame.draw.rect(screen, Colors.TEXT_SECONDARY, (bar_x, bar_y, bar_w, bar_h), 1)

        # Tree headers
        trading_header = self.header_font.render("TRADING MASTERY", True, Colors.FACTION_COMMERCE)
        screen.blit(trading_header, trading_header.get_rect(center=(160, 150)))

        gathering_header = self.header_font.render(
            "RESOURCE GATHERING", True, Colors.FACTION_FRONTIER
        )
        screen.blit(gathering_header, gathering_header.get_rect(center=(460, 150)))

        mining_header = self.header_font.render("MINING MASTERY", True, Colors.GLOW_ORANGE)
        screen.blit(mining_header, mining_header.get_rect(center=(740, 150)))

        leadership_header = self.header_font.render("LEADERSHIP", True, Colors.FACTION_SCIENCE)
        screen.blit(leadership_header, leadership_header.get_rect(center=(1080, 150)))

        # Draw connection lines first
        self._draw_connections(screen)

        # Draw nodes
        for tree_type, positions in SKILL_POSITIONS.items():
            for skill_id, (sx, sy) in positions.items():
                self._draw_node(screen, skill_id, sx, sy)

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
        for tree_type, positions in SKILL_POSITIONS.items():
            for skill_id, (sx, sy) in positions.items():
                skill = self.progression.skills.get(skill_id)
                if skill and skill.prerequisite_id:
                    prereq_pos = positions.get(skill.prerequisite_id)
                    if prereq_pos:
                        prereq_skill = self.progression.skills.get(skill.prerequisite_id)
                        is_unlocked = prereq_skill and prereq_skill.is_unlocked

                        if is_unlocked:
                            # Glowing connection line
                            glow_alpha = int(60 + 30 * math.sin(self._glow_time * 2))
                            color = (60, 180, 80)
                            pygame.draw.line(screen, color, prereq_pos, (sx, sy), 2)

                            # Energy flow dot
                            dot_t = self._energy_dot_offset % 1.0
                            dot_x = int(prereq_pos[0] + (sx - prereq_pos[0]) * dot_t)
                            dot_y = int(prereq_pos[1] + (sy - prereq_pos[1]) * dot_t)
                            dot_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
                            pygame.draw.circle(dot_surf, (100, 255, 150, 200), (4, 4), 3)
                            pygame.draw.circle(dot_surf, (100, 255, 150, 80), (4, 4), 4)
                            screen.blit(dot_surf, (dot_x - 4, dot_y - 4))
                        else:
                            # Dashed locked line
                            self._draw_dashed_connection(screen, prereq_pos, (sx, sy), (35, 35, 45))

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

        # Determine colors
        if skill.is_maxed:
            fill_color = (50, 150, 50)
            border_color = Colors.SUCCESS
        elif skill.is_unlocked:
            fill_color = (40, 80, 140)
            border_color = Colors.TEXT_HIGHLIGHT
        elif can_level:
            fill_color = (60, 60, 30)
            border_color = Colors.YELLOW
        else:
            fill_color = (30, 30, 40)
            border_color = (60, 60, 70)

        if is_hovered:
            fill_color = tuple(min(255, c + 30) for c in fill_color)

        # Radial gradient fill (lighter center)
        node_surf = pygame.Surface((NODE_RADIUS * 2 + 4, NODE_RADIUS * 2 + 4), pygame.SRCALPHA)
        center = NODE_RADIUS + 2
        for r in range(NODE_RADIUS, 0, -1):
            t = 1.0 - (r / NODE_RADIUS)  # 0 at edge, 1 at center
            gr = int(fill_color[0] + (min(255, fill_color[0] + 40) - fill_color[0]) * t)
            gg = int(fill_color[1] + (min(255, fill_color[1] + 40) - fill_color[1]) * t)
            gb = int(fill_color[2] + (min(255, fill_color[2] + 40) - fill_color[2]) * t)
            pygame.draw.circle(node_surf, (gr, gg, gb, 255), (center, center), r)
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

        # Skill name (wrapped)
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
        tooltip_surf = pygame.Surface((tw, th), pygame.SRCALPHA)
        tooltip_surf.fill((12, 12, 28, 230))
        screen.blit(tooltip_surf, (tx, ty))
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, (tx, ty, tw, th), 1)

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
