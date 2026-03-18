"""
Character screen view.

Displays protagonist attributes, progression summary, and social skills.
Links to Skill Trees and Crew views.
"""

import pygame
import pygame_gui
from typing import Optional

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.views.base_view import BaseView
from spacegame.models.player import Player
from spacegame.models.attributes import (
    AttributeId,
    AttributeSheet,
    ATTRIBUTE_DEFINITIONS,
)
from spacegame.models.social import SocialManager
from spacegame.models.progression import SkillTreeType
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_bar
from spacegame.engine.fonts import FontCache
from spacegame.engine.sprites import get_sprite_manager
from spacegame.utils.logger import logger

# Map tree types to their governing attribute for display
_TREE_ATTRIBUTE_MAP = {
    SkillTreeType.TRADING: "Commerce",
    SkillTreeType.GATHERING: "Acuity",
    SkillTreeType.MINING: "Resolve",
    SkillTreeType.LEADERSHIP: "Ingenuity",
    SkillTreeType.SOCIAL: "Synergy",
    SkillTreeType.GROUND: "Resolve",
    SkillTreeType.COMBAT: "Combat",
    SkillTreeType.EXPLORATION: "Acuity",
    SkillTreeType.SMUGGLING: "Ingenuity",
}


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

        # Fonts
        self.title_font = FontCache.get(36)
        self.header_font = FontCache.get(28)
        self.info_font = FontCache.get(22)
        self.small_font = FontCache.get(18)
        self.value_font = FontCache.get(26)

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

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        btn_width = 160
        btn_height = 40
        bottom_y = WINDOW_HEIGHT - 60

        # Navigation buttons at bottom
        self.skills_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH // 2 - btn_width - 100, bottom_y, btn_width, btn_height
            ),
            text="Skill Trees",
            manager=self.ui_manager,
        )
        self.crew_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                WINDOW_WIDTH // 2 - btn_width // 2, bottom_y, btn_width, btn_height
            ),
            text="Crew Roster",
            manager=self.ui_manager,
        )
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH // 2 + 100, bottom_y, btn_width, btn_height),
            text="Back",
            manager=self.ui_manager,
        )

        # Attribute allocation buttons (only if unspent points)
        if self.attribute_sheet.unspent_points > 0:
            start_y = 190
            row_h = 40
            for i, attr in enumerate(AttributeId):
                y = start_y + i * row_h
                self.plus_buttons[attr.value] = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(310, y, 28, 28),
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

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.skills_button:
                self.next_state = GameState.SKILL_TREE
            elif event.ui_element == self.crew_button:
                self.next_state = GameState.CREW_ROSTER
            elif event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP
            else:
                # Check plus buttons
                for attr_id, btn in self.plus_buttons.items():
                    if event.ui_element == btn:
                        success, msg = self.attribute_sheet.allocate_point(attr_id)
                        if success:
                            self._show_message(msg)
                            # Rebuild UI if no more points
                            if self.attribute_sheet.unspent_points == 0:
                                for b in self.plus_buttons.values():
                                    b.kill()
                                self.plus_buttons.clear()
                        else:
                            self._show_message(msg)
                        return

    def update(self, dt: float) -> None:
        self.background.update(dt)
        if self.message_timer > 0:
            self.message_timer -= dt

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title = self.title_font.render("CHARACTER", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        # Left panel: Attributes
        self._render_attributes_panel(screen, 30, 70)

        # Right panel: Progression & Skills
        self._render_progression_panel(screen, 400, 70)

        # Bottom: Faction Perks
        self._render_faction_perks(screen, 30, 440)

        # Message
        if self.message_timer > 0:
            msg_surf = self.info_font.render(self.message, True, Colors.SUCCESS)
            screen.blit(
                msg_surf,
                msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 100)),
            )

    def _render_attributes_panel(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Render the attributes panel on the left side."""
        # Panel background
        panel_w = 350
        panel_h = 360
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((15, 18, 30, 200))
        screen.blit(panel_surf, (x, y))
        pygame.draw.rect(screen, Colors.UI_BORDER, (x, y, panel_w, panel_h), 1)

        # Header — player name + title
        header = self.header_font.render(f"{self.player.name}", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (x + 15, y + 10))

        # Title and playstyle
        title_text = f"{self.player.title}  |  {self.player.playstyle_label}"
        title_surf = self.small_font.render(title_text, True, Colors.GOLD)
        screen.blit(title_surf, (x + 15, y + 34))

        # Ship name
        ship_display = f"Ship: {self.player.display_ship_name}"
        ship_surf = self.small_font.render(ship_display, True, Colors.TEXT_SECONDARY)
        screen.blit(ship_surf, (x + 15 + title_surf.get_width() + 20, y + 34))

        # Level and XP
        prog = self.player.progression
        xp_next = prog.get_xp_for_next_level()
        xp_str = f"{prog.xp}/{xp_next}"
        level_surf = self.info_font.render(
            f"Level {prog.level}  |  XP: {xp_str}", True, Colors.TEXT
        )
        screen.blit(level_surf, (x + 15, y + 54))

        # XP progress bar
        bar_x = x + 15
        bar_y = y + 76
        bar_w = panel_w - 30
        bar_h = 8
        progress = prog.get_xp_progress()
        draw_bar(
            screen,
            bar_x,
            bar_y,
            bar_w,
            bar_h,
            progress,
            1.0,
            Colors.TEXT_HIGHLIGHT,
            show_value=False,
            border_color=Colors.TEXT_SECONDARY,
        )

        # Unspent points indicator
        pts = self.attribute_sheet.unspent_points
        if pts > 0:
            pts_surf = self.info_font.render(f"Attribute Points: {pts}", True, Colors.YELLOW)
            screen.blit(pts_surf, (x + 15, y + 78))

        # Attributes
        attr_start_y = y + 100
        row_h = 40
        for i, attr in enumerate(AttributeId):
            ay = attr_start_y + i * row_h
            defn = ATTRIBUTE_DEFINITIONS[attr.value]
            val = self.attribute_sheet.get_value(attr.value)

            # Name
            name_surf = self.info_font.render(defn["name"], True, Colors.ATTR_HIGHLIGHT)
            screen.blit(name_surf, (x + 15, ay))

            # Description
            desc_surf = self.small_font.render(defn["description"], True, Colors.TEXT_SECONDARY)
            screen.blit(desc_surf, (x + 15, ay + 18))

            # Value
            val_color = Colors.TEXT if val <= 1 else Colors.SUCCESS
            val_surf = self.value_font.render(str(val), True, val_color)
            screen.blit(val_surf, (x + panel_w - 50, ay + 4))

        # Milestones
        milestone_y = attr_start_y + 5 * row_h + 10
        milestone_header = self.small_font.render("MILESTONES", True, Colors.TEXT_SECONDARY)
        screen.blit(milestone_header, (x + 15, milestone_y))

        from spacegame.models.attributes import MILESTONE_DEFINITIONS

        for j, (mid, desc) in enumerate(MILESTONE_DEFINITIONS.items()):
            my = milestone_y + 18 + j * 16
            awarded = self.attribute_sheet.has_milestone(mid)
            mark = "[X]" if awarded else "[ ]"
            color = Colors.SUCCESS if awarded else Colors.TEXT_SECONDARY
            m_surf = self.small_font.render(f"{mark} {desc}", True, color)
            screen.blit(m_surf, (x + 15, my))

    def _render_progression_panel(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Render the progression/skills overview on the right side."""
        panel_w = WINDOW_WIDTH - x - 30
        panel_h = 360
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((15, 18, 30, 200))
        screen.blit(panel_surf, (x, y))
        pygame.draw.rect(screen, Colors.UI_BORDER, (x, y, panel_w, panel_h), 1)

        # Skill Trees summary
        header = self.header_font.render("SKILL TREES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (x + 15, y + 10))

        prog = self.player.progression
        tree_y = y + 40
        tree_colors = {
            SkillTreeType.TRADING: Colors.FACTION_COMMERCE,
            SkillTreeType.GATHERING: Colors.FACTION_FRONTIER,
            SkillTreeType.MINING: Colors.GLOW_ORANGE,
            SkillTreeType.LEADERSHIP: Colors.FACTION_SCIENCE,
            SkillTreeType.SOCIAL: Colors.ATTR_HIGHLIGHT,
            SkillTreeType.GROUND: Colors.RED,
            SkillTreeType.COMBAT: Colors.RED,
            SkillTreeType.EXPLORATION: Colors.FACTION_FRONTIER,
            SkillTreeType.SMUGGLING: Colors.GLOW_ORANGE,
        }

        for tree_type in SkillTreeType:
            skills = prog.get_skill_tree(tree_type)
            invested = sum(s.current_level for s in skills)
            total_max = sum(s.max_level for s in skills)
            color = tree_colors.get(tree_type, Colors.TEXT)
            attr_name = _TREE_ATTRIBUTE_MAP.get(tree_type, "")

            tree_text = f"{tree_type.value.title()} ({attr_name})"
            t_surf = self.info_font.render(tree_text, True, color)
            screen.blit(t_surf, (x + 15, tree_y))

            inv_surf = self.small_font.render(
                f"{invested}/{total_max} invested", True, Colors.TEXT_SECONDARY
            )
            screen.blit(inv_surf, (x + 250, tree_y + 2))

            tree_y += 26

        # Available skill points
        avail = prog.get_available_skill_points()
        sp_color = Colors.YELLOW if avail > 0 else Colors.TEXT_SECONDARY
        sp_surf = self.info_font.render(f"Skill Points Available: {avail}", True, sp_color)
        screen.blit(sp_surf, (x + 15, tree_y + 10))

        # Social skills
        social_y = tree_y + 45
        social_header = self.header_font.render("SOCIAL SKILLS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(social_header, (x + 15, social_y))

        if self.social_manager:
            social_y += 28
            for skill in self.social_manager.get_all_skills():
                s_surf = self.info_font.render(
                    f"{skill.name}: Level {skill.level} (XP: {skill.xp})",
                    True,
                    Colors.TEXT,
                )
                screen.blit(s_surf, (x + 15, social_y))
                social_y += 22

        # Quick stats
        stats_y = social_y + 20
        stats_header = self.header_font.render("STATISTICS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(stats_header, (x + 15, stats_y))
        stats_y += 28

        stat_lines = [
            f"Credits: {self.player.credits:,} CR",
            f"Net Worth: {self.player.get_net_worth():,} CR",
            f"Trades: {self.player.trades_completed}",
            f"Systems Visited: {len(self.player.systems_visited)}",
            f"Day: {self.player.game_day}",
        ]
        for line in stat_lines:
            s = self.info_font.render(line, True, Colors.TEXT_SECONDARY)
            screen.blit(s, (x + 15, stats_y))
            stats_y += 20

    def _render_faction_perks(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Render faction reputation and active perks."""
        if not self.politics_manager or not self.player:
            return

        header = self.header_font.render("FACTION STANDING", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (x, y))
        y += 28

        faction_rep = getattr(self.player, "faction_reputation", {})
        if not faction_rep:
            return

        from spacegame.models.faction import ReputationTier, get_reputation_tier

        for faction_id, rep_value in faction_rep.items():
            tier = get_reputation_tier(rep_value)
            tier_name = tier.value.title()
            faction_name = faction_id.replace("_", " ").title()

            # Faction name + tier
            tier_color = {
                ReputationTier.ALLIED: Colors.GREEN,
                ReputationTier.FRIENDLY: (100, 200, 130),
                ReputationTier.NEUTRAL: Colors.TEXT_SECONDARY,
                ReputationTier.HOSTILE: Colors.RED,
            }.get(tier, Colors.TEXT_SECONDARY)

            # Faction emblem + name + tier
            emblem = self._sprite_mgr.get_faction_emblem(faction_id, scale=1)
            text_x = x
            if emblem:
                screen.blit(emblem, (x, y - 1))
                text_x = x + emblem.get_width() + 4

            line = f"{faction_name}: {tier_name} ({rep_value:+d})"
            surf = self.info_font.render(line, True, tier_color)
            screen.blit(surf, (text_x, y))

            # Show active perks inline
            from spacegame.models.faction_perks import get_active_perks as _get_perks

            faction_perks_data = getattr(self.politics_manager, "_faction_perks", {})
            perks = _get_perks(faction_perks_data, faction_id, tier)
            if perks:
                perk_names = [p.name for p in perks]
                perk_text = "  " + ", ".join(perk_names)
                perk_surf = self.small_font.render(perk_text, True, Colors.SUCCESS)
                screen.blit(perk_surf, (text_x + surf.get_width() + 5, y + 3))
            y += 22

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
