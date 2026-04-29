"""
Crew roster view.

Displays recruited crew members with their stats, abilities, and loyalty.
Allows dismissing crew members from the roster.
"""

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_bar, draw_panel
from spacegame.engine.fonts import FONT_BODY, FONT_LG, FONT_SECTION, FONT_XL, get_font
from spacegame.engine.sprites import AnimatedSprite, get_sprite_manager, res_scale
from spacegame.models.attributes import ATTRIBUTE_DEFINITIONS, AttributeId
from spacegame.models.crew import CrewRoster, CrewTemplate
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView
from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT

# Layout constants (shared source: layout.py)
from spacegame.views.layout import (
    DETAIL_WIDTH,
    LIST_HEIGHT,
    LIST_WIDTH,
)
from spacegame.views.layout import (
    LIST_DETAIL_LEFT as PANEL_LEFT,
)
from spacegame.views.layout import (
    LIST_DETAIL_TOP as PANEL_TOP,
)
from spacegame.views.layout import (
    LIST_ITEM_HEIGHT as ITEM_HEIGHT,
)


class _CrewItem:
    """Clickable crew list entry showing name and level."""

    def __init__(
        self,
        rect: pygame.Rect,
        template: CrewTemplate,
        state: dict,
        font: pygame.font.Font,
    ) -> None:
        self.rect = rect
        self.template = template
        self.state = state
        self.font = font
        self.selected = False
        self.hovered = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        self.hovered = self.rect.collidepoint(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        if self.selected:
            bg = Colors.ROW_HIGHLIGHT
            text_color = Colors.TEXT_HIGHLIGHT
        elif self.hovered:
            bg = Colors.ROW_BG
            text_color = Colors.TEXT_PRIMARY
        else:
            bg = Colors.ROW_DETAIL
            text_color = Colors.TEXT_SECONDARY

        pygame.draw.rect(screen, bg, self.rect, border_radius=3)

        # Crew name on left
        name_surf = self.font.render(self.template.name, True, text_color)
        name_rect = name_surf.get_rect(midleft=(self.rect.x + 14, self.rect.centery))
        screen.blit(name_surf, name_rect)

        # Level on right (companions show level, crew show "Crew")
        if self.template.is_companion:
            level = self.state.get("level", 1)
            badge_text = f"Lv {level}"
        else:
            badge_text = "Crew"
        badge_surf = self.font.render(badge_text, True, Colors.TEXT_SECONDARY)
        badge_rect = badge_surf.get_rect(midright=(self.rect.right - 14, self.rect.centery))
        screen.blit(badge_surf, badge_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class _DismissButton:
    """Dismiss crew button shown in detail panel."""

    def __init__(self, rect: pygame.Rect, font: pygame.font.Font) -> None:
        self.rect = rect
        self.font = font
        self.hovered = False
        self.visible = False
        self.disabled = False
        self.disabled_reason = ""

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        if self.visible and not self.disabled:
            self.hovered = self.rect.collidepoint(mouse_pos)
        else:
            self.hovered = False

    def render(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return
        if self.disabled:
            bg = (40, 40, 40)
            border = (80, 80, 80)
            text_color = (100, 100, 100)
        elif self.hovered:
            bg = (80, 40, 40)
            border = Colors.RED
            text_color = Colors.RED
        else:
            bg = (60, 30, 30)
            border = (100, 50, 50)
            text_color = Colors.RED
        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=4)
        text_surf = self.font.render("DISMISS", True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if not self.visible or self.disabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class CrewRosterView(BaseView):
    """Crew roster showing recruited members with stats and abilities."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        crew_roster: Optional[CrewRoster],
        crew_slots: int,
        active_mission_ids: Optional[list[str]] = None,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.crew_roster = crew_roster
        self.crew_slots = crew_slots
        self._active_mission_ids: list[str] = active_mission_ids or []
        self.next_state: Optional[GameState] = None

        # Selection state
        self._selected_crew_id: Optional[str] = None
        self.pending_dismiss_id: Optional[str] = None

        # Scroll
        self._scroll_offset: int = 0

        # Fonts
        self._title_font = get_font("header", FONT_SECTION)
        self._name_font = get_font("dialogue", FONT_LG)
        # Crew descriptions read more cleanly in Silver — see
        # station_hub_view.py for the canonical font swap rationale.
        self._desc_font = get_font("narration", FONT_LG)
        self._detail_title_font = get_font("header", FONT_XL)
        self._label_font = get_font("dialogue", FONT_BODY)
        self._slot_font = get_font("stats", FONT_LG)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

        # Manual widgets
        self._crew_items: list[_CrewItem] = []
        self._dismiss_btn: Optional[_DismissButton] = None
        self._attr_plus_rects: dict[str, pygame.Rect] = {}

        # Sprite manager for crew portraits
        self._sprite_mgr = get_sprite_manager()
        self._portrait_cache: dict[str, Optional[AnimatedSprite]] = {}

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=88)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        super().on_enter()
        self._create_ui()
        self._refresh_list()
        logger.info("Entered crew roster view")

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()
        logger.info("Exited crew roster view")

    def _create_ui(self) -> None:
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_LEFT, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(60), 120, 40
            ),
            text="BACK",
            manager=self.ui_manager,
        )

        # Dismiss button below detail panel, aligned with back button row
        detail_x = PANEL_LEFT + LIST_WIDTH + 30
        dismiss_y = WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(60)
        self._dismiss_btn = _DismissButton(
            pygame.Rect(detail_x + 20, dismiss_y, 140, 40),
            self._label_font,
        )

    def _destroy_ui(self) -> None:
        if self.back_button:
            self.back_button.kill()
            self.back_button = None

    def _refresh_list(self) -> None:
        """Rebuild the crew item list from the roster."""
        self._crew_items.clear()
        self._scroll_offset = 0

        if not self.crew_roster:
            self._selected_crew_id = None
            if self._dismiss_btn:
                self._dismiss_btn.visible = False
            return

        members = self.crew_roster.get_recruited_members()

        for i, (template, state) in enumerate(members):
            rect = pygame.Rect(
                PANEL_LEFT + 4,
                PANEL_TOP + 4 + i * (ITEM_HEIGHT + 4),
                LIST_WIDTH - 8,
                ITEM_HEIGHT,
            )
            item = _CrewItem(rect, template, state, self._name_font)
            self._crew_items.append(item)

        # Auto-select first if available
        if self._crew_items:
            self._crew_items[0].selected = True
            self._selected_crew_id = self._crew_items[0].template.id
        else:
            self._selected_crew_id = None

        # Show dismiss button when crew is selected
        if self._dismiss_btn:
            self._dismiss_btn.visible = self._selected_crew_id is not None

    def _select_crew(self, crew_id: str) -> None:
        """Select a crew member by template ID."""
        self._selected_crew_id = crew_id
        for item in self._crew_items:
            item.selected = item.template.id == crew_id
        if self._dismiss_btn:
            self._dismiss_btn.visible = self._selected_crew_id is not None
            # Check dismiss blocking
            if self.crew_roster and self._selected_crew_id:
                can, reason = self.crew_roster.can_dismiss(
                    self._selected_crew_id, self._active_mission_ids
                )
                self._dismiss_btn.disabled = not can
                self._dismiss_btn.disabled_reason = reason
            else:
                self._dismiss_btn.disabled = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP

        # Crew item clicks
        for item in self._crew_items:
            if item.was_clicked(event):
                self._select_crew(item.template.id)
                return

        # Dismiss button
        if self._dismiss_btn and self._dismiss_btn.was_clicked(event):
            if self._selected_crew_id and self.crew_roster:
                can, _reason = self.crew_roster.can_dismiss(
                    self._selected_crew_id, self._active_mission_ids
                )
                if can:
                    self.pending_dismiss_id = self._selected_crew_id
                    self.next_state = GameState.GALAXY_MAP
                return

        # Attribute allocation buttons
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for attr_id, rect in self._attr_plus_rects.items():
                if rect.collidepoint(event.pos) and self._selected_crew_id:
                    success, _msg = self.crew_roster.allocate_crew_attribute(
                        self._selected_crew_id, attr_id
                    )
                    if success:
                        self._refresh_list()
                        self._select_crew(self._selected_crew_id)
                    return

        # Scroll
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_offset = max(0, self._scroll_offset - event.y * 20)

    def update(self, dt: float) -> None:
        self.background.update(dt)

        # Update portrait animations
        for portrait in self._portrait_cache.values():
            if portrait is not None:
                portrait.update(dt)

        mouse_pos = pygame.mouse.get_pos()
        for item in self._crew_items:
            item.update_hover(mouse_pos)
        if self._dismiss_btn:
            self._dismiss_btn.update_hover(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title_surf = self._title_font.render("CREW ROSTER", True, Colors.TEXT_PRIMARY)
        screen.blit(title_surf, (PANEL_LEFT, 30))

        # Slot counter (top right area)
        recruited_count = len(self._crew_items)
        slot_text = f"Slots: {recruited_count}/{self.crew_slots}"
        slot_surf = self._slot_font.render(slot_text, True, Colors.TEXT_SECONDARY)
        slot_rect = slot_surf.get_rect(topright=(WINDOW_WIDTH - PANEL_LEFT, 34))
        screen.blit(slot_surf, slot_rect)

        # List panel background
        list_rect = pygame.Rect(PANEL_LEFT, PANEL_TOP, LIST_WIDTH, LIST_HEIGHT)
        draw_panel(screen, list_rect, alpha=255)

        # Crew items (clipped to list panel)
        clip_prev = screen.get_clip()
        screen.set_clip(list_rect)
        if self._crew_items:
            for item in self._crew_items:
                # Apply scroll offset
                shifted_rect = item.rect.move(0, -self._scroll_offset)
                if shifted_rect.bottom < list_rect.top or shifted_rect.top > list_rect.bottom:
                    continue
                orig_rect = item.rect
                item.rect = shifted_rect
                item.render(screen)
                item.rect = orig_rect
        else:
            # Empty state inside the list panel
            empty_surf = self._desc_font.render(
                "No crew members recruited yet.", True, Colors.TEXT_SECONDARY
            )
            empty_rect = empty_surf.get_rect(center=(list_rect.centerx, list_rect.top + 40))
            screen.blit(empty_surf, empty_rect)
        screen.set_clip(clip_prev)

        # Detail panel
        detail_x = PANEL_LEFT + LIST_WIDTH + 30
        detail_rect = pygame.Rect(detail_x, PANEL_TOP, DETAIL_WIDTH, LIST_HEIGHT)
        draw_panel(screen, detail_rect, alpha=255)

        self._render_detail_panel(screen, detail_x, PANEL_TOP)

        # Dismiss button
        if self._dismiss_btn:
            self._dismiss_btn.render(screen)

    def _render_detail_panel(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Render the selected crew member's details."""
        if not self._selected_crew_id or not self.crew_roster:
            self._attr_plus_rects.clear()
            self._render_dual_tech_overview(screen, x, y)
            return

        template = self.crew_roster.get_template(self._selected_crew_id)
        state = self.crew_roster.get_member_state(self._selected_crew_id)
        if not template or not state:
            return

        pad_x = x + 20
        cur_y = y + 18

        # Portrait: sprite with colored fallback
        portrait_size = 40
        portrait_rect = pygame.Rect(pad_x, cur_y, portrait_size, portrait_size)
        portrait_color = (
            tuple(template.portrait_color) if template.portrait_color else (80, 80, 120)
        )

        # Try sprite
        if template.id not in self._portrait_cache:
            self._portrait_cache[template.id] = self._sprite_mgr.get_portrait_animated(
                template.id, scale=res_scale(1)
            )
        anim = self._portrait_cache[template.id]
        sprite = anim.get_surface() if anim else None
        if sprite:
            scaled = pygame.transform.scale(sprite, (portrait_size, portrait_size))
            screen.blit(scaled, (pad_x, cur_y))
        else:
            pygame.draw.rect(screen, portrait_color, portrait_rect, border_radius=4)
            initial_surf = self._detail_title_font.render(
                template.name[0].upper(), True, Colors.TEXT_PRIMARY
            )
            initial_rect = initial_surf.get_rect(center=portrait_rect.center)
            screen.blit(initial_surf, initial_rect)
        pygame.draw.rect(screen, Colors.UI_BORDER, portrait_rect, 1, border_radius=4)

        # Name (to the right of portrait)
        name_surf = self._detail_title_font.render(template.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name_surf, (pad_x + 54, cur_y + 2))

        # Role subtitle with companion/crew label
        type_label = "Companion" if template.is_companion else "Crew"
        role_text = f"{template.role}  ({type_label})"
        role_surf = self._label_font.render(role_text, True, Colors.TEXT_SECONDARY)
        screen.blit(role_surf, (pad_x + 54, cur_y + 24))
        cur_y += 56

        # Description (word-wrapped)
        cur_y = self._render_wrapped(
            screen,
            template.description,
            self._desc_font,
            Colors.TEXT_SECONDARY,
            pad_x,
            cur_y,
            DETAIL_WIDTH - 40,
        )
        cur_y += 20

        # Level and XP (companions only — crew are level 1 with no XP)
        level = state.get("level", 1)
        if template.is_companion:
            xp = state.get("xp", 0)
            if level < template.max_level and level < len(template.xp_thresholds):
                xp_threshold = template.xp_thresholds[level]
                xp_text = f"Level: {level}  XP: {xp}/{xp_threshold}"
            else:
                xp_text = f"Level: {level}  XP: MAX"
            xp_surf = self._label_font.render(xp_text, True, Colors.TEXT_PRIMARY)
            screen.blit(xp_surf, (pad_x, cur_y))
            cur_y += 28

        # Loyalty (companions get a bar with tiers; crew show "Reliable")
        if template.is_companion:
            loyalty = state.get("loyalty", 50)
            loyalty_label = self._label_font.render("Loyalty:", True, Colors.TEXT_PRIMARY)
            screen.blit(loyalty_label, (pad_x, cur_y))

            tier = self.crew_roster.get_loyalty_tier(template.id)
            if tier:
                from spacegame.models.crew import LoyaltyTier

                tier_names = {
                    LoyaltyTier.DISCONTENTED: ("Discontented", Colors.RED),
                    LoyaltyTier.WARY: ("Wary", Colors.YELLOW),
                    LoyaltyTier.NEUTRAL: ("Neutral", Colors.TEXT_SECONDARY),
                    LoyaltyTier.WARM: ("Warm", Colors.YELLOW),
                    LoyaltyTier.LOYAL: ("Loyal", Colors.GREEN),
                    LoyaltyTier.DEVOTED: ("Devoted", Colors.GREEN),
                }
                tier_name, bar_color = tier_names.get(tier, ("", Colors.TEXT_SECONDARY))
            else:
                bar_color = Colors.TEXT_SECONDARY
                tier_name = ""

            draw_bar(
                screen,
                pad_x + 70,
                cur_y + 3,
                140,
                14,
                current=loyalty,
                maximum=100,
                color=bar_color,
                font=self._desc_font,
                show_value=True,
            )
            if tier_name:
                tier_surf = self._desc_font.render(tier_name, True, bar_color)
                screen.blit(tier_surf, (pad_x + 218, cur_y + 3))
            cur_y += 32
        else:
            # Crew: static "Reliable" label instead of loyalty bar
            reliable_surf = self._label_font.render("Status: Reliable", True, Colors.GREEN)
            screen.blit(reliable_surf, (pad_x, cur_y))
            cur_y += 28

        # Abilities section
        abilities_header = self._label_font.render("Abilities:", True, Colors.TEXT_PRIMARY)
        screen.blit(abilities_header, (pad_x, cur_y))
        cur_y += 26

        for ability in template.abilities:
            if ability.unlock_level <= level:
                # Unlocked
                bonus_sign = "+" if ability.bonus_value >= 0 else ""
                bonus_display = ability.bonus_value
                if bonus_display == int(bonus_display):
                    bonus_display = int(bonus_display)
                ability_text = f"\u2713 {ability.description} ({bonus_sign}{bonus_display})"
                color = Colors.GREEN
            else:
                # Locked
                ability_text = f"\U0001f512 {ability.description} (Lv {ability.unlock_level})"
                color = Colors.TEXT_SECONDARY
            ability_surf = self._desc_font.render(ability_text, True, color)
            screen.blit(ability_surf, (pad_x + 10, cur_y))
            cur_y += 22

        # Bonus abilities from quest rewards
        bonus_abilities = state.get("bonus_abilities", [])
        if bonus_abilities:
            for ba in bonus_abilities:
                bonus_sign = "+" if ba.get("bonus_value", 0) >= 0 else ""
                bv = ba.get("bonus_value", 0)
                if bv == int(bv):
                    bv = int(bv)
                ba_text = f"\u2605 {ba.get('description', '?')} ({bonus_sign}{bv})"
                ba_surf = self._desc_font.render(ba_text, True, (255, 215, 0))
                screen.blit(ba_surf, (pad_x + 10, cur_y))
                cur_y += 22

        # Attributes section (companions only — crew don't level or allocate)
        self._attr_plus_rects.clear()
        if template.is_companion:
            cur_y += 10
            attr_header = self._label_font.render("Attributes:", True, Colors.TEXT_PRIMARY)
            screen.blit(attr_header, (pad_x, cur_y))
            cur_y += 24

            attrs = self.crew_roster.get_member_attributes(self._selected_crew_id)
            attr_points = self.crew_roster.get_member_attribute_points(self._selected_crew_id)

            if attr_points > 0:
                pts_surf = self._desc_font.render(
                    f"Points Available: {attr_points}", True, Colors.YELLOW
                )
                screen.blit(pts_surf, (pad_x, cur_y))
                cur_y += 20

            mouse_pos = pygame.mouse.get_pos()
            for attr in AttributeId:
                defn = ATTRIBUTE_DEFINITIONS[attr.value]
                val = attrs.get(attr.value, 1)
                attr_surf = self._desc_font.render(f"{defn['name']}: {val}", True, Colors.TEXT)
                screen.blit(attr_surf, (pad_x + 10, cur_y))

                if attr_points > 0:
                    plus_rect = pygame.Rect(pad_x + 180, cur_y - 2, 22, 20)
                    self._attr_plus_rects[attr.value] = plus_rect
                    hovered = plus_rect.collidepoint(mouse_pos)
                    bg = (50, 80, 50) if hovered else (40, 60, 40)
                    pygame.draw.rect(screen, bg, plus_rect, border_radius=2)
                    pygame.draw.rect(screen, Colors.GREEN, plus_rect, 1, border_radius=2)
                    plus_surf = self._desc_font.render("+", True, Colors.GREEN)
                    screen.blit(plus_surf, plus_surf.get_rect(center=plus_rect.center))

                cur_y += 20

    def _render_dual_tech_overview(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Render the dual tech status list when no crew is selected.

        Shows every tech in the palette with its participating crew,
        loyalty requirement, and availability — a discovery point that
        tells the player "unlock Elena + Marcus at Loyalty 2 to get
        Fire at Will" without them having to read the code.
        """
        from spacegame.models.dual_tech import describe_all_dual_techs

        pad_x = x + 20
        cur_y = y + 18

        title = self._detail_title_font.render("COORDINATED ABILITIES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (pad_x, cur_y))
        cur_y += title.get_height() + 6

        hint = self._label_font.render(
            "Crew pairings that unlock when loyalty is earned.",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(hint, (pad_x, cur_y))
        cur_y += hint.get_height() + 12

        statuses = describe_all_dual_techs(self.crew_roster)

        # Build quick display-name lookup from templates.
        name_of: dict[str, str] = {}
        if self.crew_roster is not None:
            for cid, _ in [(c, None) for s in statuses for c, _ in s.crew_loyalties]:
                tmpl = self.crew_roster.get_template(cid)
                if tmpl is not None:
                    # Display first name only for compactness.
                    name_of[cid] = tmpl.name.split()[0]

        available_color = (120, 220, 160)
        locked_color = (200, 150, 150)
        dim_color = (140, 140, 150)

        for status in statuses:
            if cur_y + 46 > y + LIST_HEIGHT - 20:
                # Out of room — ellipsize.
                more = self._label_font.render(
                    f"(+{len(statuses) - statuses.index(status)} more)",
                    True,
                    dim_color,
                )
                screen.blit(more, (pad_x, cur_y))
                break

            # Header: name + status badge
            color = available_color if status.is_available else locked_color
            name_surf = self._label_font.render(status.tech.name, True, color)
            screen.blit(name_surf, (pad_x, cur_y))
            badge_text = "AVAILABLE" if status.is_available else "LOCKED"
            badge = self._label_font.render(badge_text, True, color)
            screen.blit(
                badge,
                (x + DETAIL_WIDTH - 40 - badge.get_width(), cur_y),
            )
            cur_y += name_surf.get_height() + 2

            # Participating crew + loyalty state
            parts: list[str] = []
            for cid, loy in status.crew_loyalties:
                label = name_of.get(cid, cid)
                if loy is None:
                    parts.append(f"{label} (not recruited)")
                else:
                    bar = (
                        "OK"
                        if loy >= status.tech.loyalty_req
                        else f"{loy}/{status.tech.loyalty_req}"
                    )
                    parts.append(f"{label} {bar}")
            crew_line = " + ".join(parts)
            crew_surf = self._label_font.render(crew_line, True, Colors.TEXT_SECONDARY)
            screen.blit(crew_surf, (pad_x + 8, cur_y))
            cur_y += crew_surf.get_height() + 10

    def _render_wrapped(
        self,
        screen: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        x: int,
        y: int,
        max_width: int,
    ) -> int:
        """Render word-wrapped text, return y position after last line."""
        words = text.split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if font.size(test)[0] <= max_width:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for line in lines:
            surf = font.render(line, True, color)
            screen.blit(surf, (x, y))
            y += font.get_linesize()
        return y

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
