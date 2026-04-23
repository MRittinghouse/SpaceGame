"""
Character screen view.

Displays protagonist attributes, progression summary, faction standing,
and key statistics. Links to Skill Trees and Crew views.
"""

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_bar, draw_panel
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_LG,
    FONT_MD,
    FONT_SM,
    FONT_XL2,
    FONT_XS,
    get_font,
)
from spacegame.engine.sprites import get_sprite_manager, res_scale
from spacegame.models.attributes import (
    ATTRIBUTE_DEFINITIONS,
    AttributeId,
    AttributeSheet,
)
from spacegame.models.player import Player
from spacegame.models.progression import SkillTreeType
from spacegame.models.social import SocialManager
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT

# Map tree types to their governing attribute for display
_TREE_ATTRIBUTE_MAP = {
    SkillTreeType.COMMERCE: "Commerce",
    SkillTreeType.COMBAT: "Combat",
    SkillTreeType.EXPLORATION: "Acuity",
    SkillTreeType.LEADERSHIP: "Ingenuity",
    SkillTreeType.SOCIAL: "Synergy",
    SkillTreeType.INDUSTRY: "Resolve",
}

# Layout constants
HEADER_X = scale_x(80)
HEADER_Y = 10
HEADER_W = WINDOW_WIDTH - scale_x(160)
HEADER_H = scale_y(75)

LEFT_X = scale_x(30)
LEFT_Y = scale_y(100)
LEFT_W = scale_x(480)
LEFT_H = scale_y(530)

RIGHT_X = LEFT_X + LEFT_W + scale_x(20)
RIGHT_Y = scale_y(100)
RIGHT_W = WINDOW_WIDTH - RIGHT_X - scale_x(30)
RIGHT_TOP_H = scale_y(270)
RIGHT_BOT_Y = RIGHT_Y + RIGHT_TOP_H + 10
RIGHT_BOT_H = LEFT_H - RIGHT_TOP_H - 10

BTN_Y = WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(55)
BTN_W = scale_x(150)
BTN_H = scale_y(38)


class CharacterView(BaseView):
    """Main character screen showing attributes, progression, and navigation."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        attribute_sheet: AttributeSheet,
        social_manager: Optional[SocialManager] = None,
        politics_manager: object = None,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.attribute_sheet = attribute_sheet
        self.social_manager = social_manager
        self.politics_manager = politics_manager
        self.next_state: Optional[GameState] = None

        # PT-M: first-time tip overlay
        from spacegame.views.first_time_tip import FirstTimeTipOverlay

        self._first_time_tip: Optional[FirstTimeTipOverlay] = None

        # Fonts
        self.title_font = get_font("header", FONT_XL2)
        self.header_font = get_font("header", FONT_BODY)
        self.info_font = get_font("dialogue", FONT_MD)
        self.small_font = get_font("label", FONT_XS)
        self.value_font = get_font("stats", FONT_LG)
        self.section_font = get_font("label", FONT_SM)

        # UI elements
        self.skills_button: Optional[pygame_gui.elements.UIButton] = None
        self.crew_button: Optional[pygame_gui.elements.UIButton] = None
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.plus_buttons: dict[str, pygame_gui.elements.UIButton] = {}

        # Message
        self.message: str = ""
        self.message_timer: float = 0.0

        # Sprites
        self._sprite_mgr = get_sprite_manager()

        # Visual
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=55)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(100)

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered character view")
        self._create_ui()
        self._maybe_show_tip()

    def _maybe_show_tip(self) -> None:
        """PT-M: first-time character sheet tip."""
        if self.player is None:
            return
        if self.player.dialogue_flags.get("seen_tip_character", False):
            return
        from spacegame.views.first_time_tip import FirstTimeTipOverlay

        self._first_time_tip = FirstTimeTipOverlay(
            title="Character Sheet",
            body=(
                "Your attributes, level, and milestones. Attribute points "
                "come from specific level thresholds. Milestones are one-time "
                "rewards tied to specific achievements."
            ),
            on_dismiss=self._mark_character_tip_seen,
        )

    def _mark_character_tip_seen(self) -> None:
        if self.player is not None:
            self.player.dialogue_flags["seen_tip_character"] = True

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        # Navigation buttons at bottom center
        total_btn_w = BTN_W * 3 + 20 * 2
        start_x = WINDOW_WIDTH // 2 - total_btn_w // 2

        self.skills_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(start_x, BTN_Y, BTN_W, BTN_H),
            text="Skill Trees",
            manager=self.ui_manager,
        )
        self.crew_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(start_x + BTN_W + 20, BTN_Y, BTN_W, BTN_H),
            text="Crew Roster",
            manager=self.ui_manager,
        )
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(start_x + (BTN_W + 20) * 2, BTN_Y, BTN_W, BTN_H),
            text="Back",
            manager=self.ui_manager,
        )

        # Attribute allocation buttons (only if unspent points)
        if self.attribute_sheet.unspent_points > 0:
            attr_start_y = LEFT_Y + 44
            row_h = 48
            for i, attr in enumerate(AttributeId):
                y = attr_start_y + i * row_h
                self.plus_buttons[attr.value] = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(LEFT_X + LEFT_W - 50, y + 6, 30, 30),
                    text="+",
                    manager=self.ui_manager,
                )

    def _destroy_ui(self) -> None:
        for elem in [self.skills_button, self.crew_button, self.back_button]:
            if elem:
                elem.kill()
        for btn in self.plus_buttons.values():
            btn.kill()
        self.plus_buttons.clear()
        self.skills_button = None
        self.crew_button = None
        self.back_button = None

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 3.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return

        # PT-M: first-time tip consumes events while active
        if self._first_time_tip is not None and not self._first_time_tip.dismissed:
            if self._first_time_tip.handle_event(event):
                return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.next_state = GameState.GALAXY_MAP
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.skills_button:
                self.next_state = GameState.SKILL_TREE
            elif event.ui_element == self.crew_button:
                self.next_state = GameState.CREW_ROSTER
            elif event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP
            else:
                for attr_id, btn in self.plus_buttons.items():
                    if event.ui_element == btn:
                        success, msg = self.attribute_sheet.allocate_point(attr_id)
                        if success:
                            self._show_message(msg)
                            if self.attribute_sheet.unspent_points == 0:
                                for b in self.plus_buttons.values():
                                    b.kill()
                                self.plus_buttons.clear()
                        else:
                            self._show_message(msg)
                        return

    def update(self, dt: float) -> None:
        # PT-M: tick tip overlay; clear once dismissed
        if self._first_time_tip is not None:
            self._first_time_tip.update(dt)
            if self._first_time_tip.dismissed:
                self._first_time_tip = None
        self.background.update(dt)
        if self.message_timer > 0:
            self.message_timer -= dt

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        self._render_header(screen)
        self._render_attributes_panel(screen)
        self._render_skill_trees_panel(screen)
        self._render_stats_faction_panel(screen)

        # Message feedback
        if self.message_timer > 0:
            msg_surf = self.info_font.render(self.message, True, Colors.SUCCESS)
            screen.blit(
                msg_surf,
                msg_surf.get_rect(center=(WINDOW_WIDTH // 2, BTN_Y - 20)),
            )

    # === Header card ===

    def _render_header(self, screen: pygame.Surface) -> None:
        """Render player identity header card."""
        draw_panel(screen, (HEADER_X, HEADER_Y, HEADER_W, HEADER_H), alpha=190)
        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, (HEADER_X, HEADER_Y, HEADER_W, 2))

        cx = WINDOW_WIDTH // 2

        # Name + title
        name_surf = self.title_font.render(self.player.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name_surf, (cx - name_surf.get_width() // 2, HEADER_Y + 6))

        # Title | Playstyle | Ship
        parts = []
        if self.player.title:
            parts.append(self.player.title)
        if self.player.playstyle_label:
            parts.append(self.player.playstyle_label)
        parts.append(f"Ship: {self.player.display_ship_name}")
        subtitle = "  |  ".join(parts)
        sub_surf = self.small_font.render(subtitle, True, Colors.TEXT_SECONDARY)
        screen.blit(sub_surf, (cx - sub_surf.get_width() // 2, HEADER_Y + 32))

        # Level + XP bar
        prog = self.player.progression
        xp_next = prog.get_xp_for_next_level()
        level_text = f"Level {prog.level}  |  XP: {prog.xp}/{xp_next}"
        level_surf = self.small_font.render(level_text, True, Colors.TEXT)
        screen.blit(level_surf, (cx - level_surf.get_width() // 2, HEADER_Y + 50))

        # XP progress bar
        bar_w = 300
        draw_bar(
            screen,
            cx - bar_w // 2,
            HEADER_Y + 66,
            bar_w,
            6,
            prog.get_xp_progress(),
            1.0,
            Colors.TEXT_HIGHLIGHT,
            show_value=False,
            border_color=Colors.TEXT_SECONDARY,
        )

    # === Left panel: Attributes + Milestones ===

    def _render_attributes_panel(self, screen: pygame.Surface) -> None:
        """Render attributes and milestones in the left card."""
        draw_panel(screen, (LEFT_X, LEFT_Y, LEFT_W, LEFT_H), alpha=190)

        x = LEFT_X + 15
        y = LEFT_Y + 10

        # Section header with unspent points
        header = self.header_font.render("ATTRIBUTES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (x, y))

        pts = self.attribute_sheet.unspent_points
        if pts > 0:
            pts_surf = self.section_font.render(
                f"{pts} point{'s' if pts != 1 else ''} available", True, Colors.YELLOW
            )
            screen.blit(pts_surf, (x + LEFT_W - 170, y + 4))

        y += 34

        # Attributes
        row_h = 48
        for i, attr in enumerate(AttributeId):
            ay = y + i * row_h
            defn = ATTRIBUTE_DEFINITIONS[attr.value]
            val = self.attribute_sheet.get_value(attr.value)

            # Name
            name_surf = self.info_font.render(defn["name"], True, Colors.ATTR_HIGHLIGHT)
            screen.blit(name_surf, (x, ay))

            # Description
            desc_surf = self.small_font.render(defn["description"], True, Colors.TEXT_SECONDARY)
            screen.blit(desc_surf, (x, ay + 22))

            # Value (right-aligned, inside card boundary before + button)
            val_color = Colors.TEXT if val <= 1 else Colors.SUCCESS
            val_surf = self.value_font.render(str(val), True, val_color)
            screen.blit(val_surf, (LEFT_X + LEFT_W - 85, ay + 6))

        # Divider before milestones
        div_y = y + 5 * row_h + 6
        pygame.draw.line(
            screen,
            Colors.UI_BORDER,
            (x, div_y),
            (LEFT_X + LEFT_W - 15, div_y),
        )

        # Milestones
        milestone_y = div_y + 12
        milestone_header = self.section_font.render("MILESTONES", True, Colors.TEXT_SECONDARY)
        screen.blit(milestone_header, (x, milestone_y))
        milestone_y += 22

        from spacegame.models.attributes import MILESTONE_DEFINITIONS

        for mid, desc in MILESTONE_DEFINITIONS.items():
            awarded = self.attribute_sheet.has_milestone(mid)
            mark = "[X]" if awarded else "[ ]"
            color = Colors.SUCCESS if awarded else Colors.TEXT_SECONDARY
            m_surf = self.small_font.render(f"{mark} {desc}", True, color)
            screen.blit(m_surf, (x, milestone_y))
            milestone_y += 20

    # === Right top panel: Skill Trees overview ===

    def _render_skill_trees_panel(self, screen: pygame.Surface) -> None:
        """Render skill tree investment summary."""
        draw_panel(screen, (RIGHT_X, RIGHT_Y, RIGHT_W, RIGHT_TOP_H), alpha=190)

        x = RIGHT_X + 15
        y = RIGHT_Y + 10

        header = self.header_font.render("SKILL TREES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (x, y))
        y += 30

        prog = self.player.progression
        tree_colors = {
            SkillTreeType.COMMERCE: Colors.FACTION_COMMERCE,
            SkillTreeType.COMBAT: Colors.RED,
            SkillTreeType.EXPLORATION: Colors.FACTION_FRONTIER,
            SkillTreeType.LEADERSHIP: Colors.FACTION_SCIENCE,
            SkillTreeType.SOCIAL: Colors.ATTR_HIGHLIGHT,
            SkillTreeType.INDUSTRY: Colors.GLOW_ORANGE,
        }

        for tree_type in SkillTreeType:
            skills = prog.get_skill_tree(tree_type)
            invested = sum(s.current_level for s in skills)
            total_max = sum(s.max_level for s in skills)
            color = tree_colors.get(tree_type, Colors.TEXT)

            tree_text = tree_type.value.title()
            t_surf = self.info_font.render(tree_text, True, color)
            screen.blit(t_surf, (x, y))

            inv_surf = self.small_font.render(
                f"{invested}/{total_max}", True, Colors.TEXT_SECONDARY
            )
            screen.blit(inv_surf, (x + RIGHT_W - 80, y + 2))
            y += 24

        # Skill points available
        y += 6
        avail = prog.get_available_skill_points()
        sp_color = Colors.YELLOW if avail > 0 else Colors.TEXT_SECONDARY
        sp_surf = self.info_font.render(f"Skill Points: {avail}", True, sp_color)
        screen.blit(sp_surf, (x, y))

    # === Right bottom panel: Statistics + Faction Standing ===

    def _render_stats_faction_panel(self, screen: pygame.Surface) -> None:
        """Render statistics and faction standing side by side."""
        draw_panel(screen, (RIGHT_X, RIGHT_BOT_Y, RIGHT_W, RIGHT_BOT_H), alpha=190)

        # Left column: Statistics
        sx = RIGHT_X + 15
        sy = RIGHT_BOT_Y + 10

        stats_header = self.header_font.render("STATISTICS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(stats_header, (sx, sy))
        sy += 28

        stat_lines = [
            ("Credits", f"{self.player.credits:,} CR"),
            ("Net Worth", f"{self.player.get_net_worth():,} CR"),
            ("Trades", str(self.player.trades_completed)),
            ("Systems", f"{len(self.player.systems_visited)} visited"),
            ("Day", str(self.player.game_day)),
            (
                "Missions",
                str(
                    self.player.side_missions_completed
                    + len(
                        [m for m in (self.player.mission_state or {}).values() if m == "completed"]
                    )
                ),
            ),
        ]
        for label, value in stat_lines:
            lbl_surf = self.small_font.render(f"{label}:", True, Colors.TEXT_SECONDARY)
            val_surf = self.small_font.render(value, True, Colors.TEXT)
            screen.blit(lbl_surf, (sx, sy))
            screen.blit(val_surf, (sx + 90, sy))
            sy += 20

        # Right column: Faction Standing
        fx = RIGHT_X + RIGHT_W // 2 + 10
        fy = RIGHT_BOT_Y + 10

        faction_header = self.header_font.render("FACTIONS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(faction_header, (fx, fy))
        fy += 28

        if not self.politics_manager or not self.player:
            return

        faction_rep = getattr(self.player, "faction_reputation", {})
        if not faction_rep:
            return

        from spacegame.models.faction import ReputationTier, get_reputation_tier

        tier_colors = {
            ReputationTier.ALLIED: Colors.GREEN,
            ReputationTier.FRIENDLY: (100, 200, 130),
            ReputationTier.NEUTRAL: Colors.TEXT_SECONDARY,
            ReputationTier.HOSTILE: Colors.RED,
        }

        for faction_id, rep_value in faction_rep.items():
            tier = get_reputation_tier(rep_value)
            tier_name = tier.value.title()
            tier_color = tier_colors.get(tier, Colors.TEXT_SECONDARY)
            faction_name = faction_id.replace("_", " ").title()

            # Faction emblem
            emblem = self._sprite_mgr.get_faction_emblem(faction_id, scale=res_scale(1))
            text_x = fx
            if emblem:
                screen.blit(emblem, (fx, fy - 1))
                text_x = fx + emblem.get_width() + 4

            # Name + rep
            name_surf = self.small_font.render(faction_name, True, tier_color)
            screen.blit(name_surf, (text_x, fy))

            rep_surf = self.small_font.render(
                f"{tier_name} ({rep_value:+d})", True, Colors.TEXT_SECONDARY
            )
            screen.blit(rep_surf, (text_x + name_surf.get_width() + 6, fy))
            fy += 22

    def render_top(self, screen: pygame.Surface) -> None:
        """PT-M: draw the first-time tip above pygame_gui elements."""
        if self._first_time_tip is not None:
            self._first_time_tip.render(screen)

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
