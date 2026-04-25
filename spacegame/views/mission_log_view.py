"""
Mission log view.

Displays active, available, and completed missions with objectives
and rewards. Allows accepting available missions.
"""

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, Colors, GameState, scale_x, scale_y
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_LG,
    FONT_MD,
    FONT_SECTION,
    FONT_XL,
    FONT_XS,
    get_font,
)
from spacegame.models.mission import Mission, MissionManager, MissionStatus, ObjectiveType
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

TAB_HEIGHT = scale_y(36)
TAB_WIDTH = scale_x(130)


class _TabButton:
    """Manually-rendered tab button."""

    def __init__(self, rect: pygame.Rect, label: str, font: pygame.font.Font) -> None:
        self.rect = rect
        self.label = label
        self.font = font
        self.active = False
        self.hovered = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        self.hovered = self.rect.collidepoint(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        if self.active:
            bg = Colors.ROW_HIGHLIGHT
            border = Colors.TEXT_HIGHLIGHT
            text_color = Colors.TEXT_HIGHLIGHT
        elif self.hovered:
            bg = Colors.ROW_BG
            border = Colors.UI_BORDER
            text_color = Colors.TEXT_PRIMARY
        else:
            bg = Colors.CARD_BG
            border = Colors.UI_BORDER
            text_color = Colors.TEXT_SECONDARY

        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=4)
        text_surf = self.font.render(self.label, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


_SIDE_BADGE_COLOR = (80, 140, 180)
_CAMPAIGN_BADGE_COLOR = (180, 140, 60)


class _MissionItem:
    """Clickable mission list entry."""

    def __init__(
        self,
        rect: pygame.Rect,
        mission: Mission,
        font: pygame.font.Font,
        badge_font: pygame.font.Font,
        status: Optional[MissionStatus] = None,
    ) -> None:
        self.rect = rect
        self.mission = mission
        self.font = font
        self.badge_font = badge_font
        self.status = status
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
        text_surf = self.font.render(self.mission.name, True, text_color)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 14, self.rect.centery))
        screen.blit(text_surf, text_rect)

        # Status/type badge on the right
        if self.status == MissionStatus.ABANDONED:
            badge_text = "ABANDONED"
            badge_color = (160, 80, 80)
        elif self.status == MissionStatus.FAILED:
            badge_text = "FAILED"
            badge_color = (200, 60, 60)
        elif self.mission.mission_type == "side":
            badge_text = "SIDE"
            badge_color = _SIDE_BADGE_COLOR
        else:
            badge_text = "MAIN"
            badge_color = _CAMPAIGN_BADGE_COLOR
        badge_surf = self.badge_font.render(badge_text, True, badge_color)
        badge_rect = badge_surf.get_rect(midright=(self.rect.right - 10, self.rect.centery))
        screen.blit(badge_surf, badge_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class _AcceptButton:
    """Accept mission button shown in detail panel."""

    def __init__(self, rect: pygame.Rect, font: pygame.font.Font) -> None:
        self.rect = rect
        self.font = font
        self.hovered = False
        self.visible = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        if self.visible:
            self.hovered = self.rect.collidepoint(mouse_pos)
        else:
            self.hovered = False

    def render(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return
        bg = (40, 80, 50) if self.hovered else (30, 60, 40)
        border = Colors.GREEN if self.hovered else (60, 100, 70)
        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=4)
        text_surf = self.font.render("ACCEPT", True, Colors.GREEN)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class _AbandonButton:
    """Abandon mission button shown in detail panel for active side missions."""

    def __init__(self, rect: pygame.Rect, font: pygame.font.Font) -> None:
        self.rect = rect
        self.font = font
        self.hovered = False
        self.visible = False

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        if self.visible:
            self.hovered = self.rect.collidepoint(mouse_pos)
        else:
            self.hovered = False

    def render(self, screen: pygame.Surface) -> None:
        if not self.visible:
            return
        bg = (80, 30, 30) if self.hovered else (50, 25, 25)
        border = (200, 60, 60) if self.hovered else (120, 50, 50)
        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=4)
        text_surf = self.font.render("ABANDON", True, (200, 80, 80))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class MissionLogView(BaseView):
    """Mission log showing active, available, and completed missions."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        mission_manager: Optional[MissionManager],
        data_loader: Optional[object] = None,
        player: Optional[object] = None,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.mission_manager = mission_manager
        self._data_loader = data_loader
        self._player = player
        self.next_state: Optional[GameState] = None

        # Tab state
        self._current_tab: str = "active"
        self._selected_mission_id: Optional[str] = None
        self.pending_accept_id: Optional[str] = None
        self.pending_abandon_id: Optional[str] = None
        self._abandon_confirm_active: bool = False
        self._abandon_confirm_mission_id: Optional[str] = None

        # Scroll
        self._scroll_offset: int = 0

        # Fonts
        self._title_font = get_font("header", FONT_SECTION)
        self._tab_font = get_font("label", FONT_BODY)
        self._name_font = get_font("dialogue", FONT_LG)
        self._desc_font = get_font("dialogue", FONT_MD)
        self._detail_title_font = get_font("header", FONT_XL)
        self._label_font = get_font("dialogue", FONT_BODY)
        self._badge_font = get_font("label", FONT_XS)
        self._small_font = get_font("dialogue", FONT_XS)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None

        # PT-M: first-time tip overlay (None unless unseen on this entry)
        from spacegame.views.first_time_tip import FirstTimeTipOverlay

        self._first_time_tip: Optional[FirstTimeTipOverlay] = None

        # Tab buttons
        self._tabs: list[_TabButton] = []
        self._mission_items: list[_MissionItem] = []
        self._accept_btn: Optional[_AcceptButton] = None

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=77)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

    def on_enter(self) -> None:
        super().on_enter()
        self._create_ui()
        self._build_tabs()
        self._refresh_list()
        self._maybe_show_tip()
        logger.info("Entered mission log view")

    def _maybe_show_tip(self) -> None:
        """PT-M: show the first-time mission log tip if the player hasn't
        dismissed it yet. Literal flag strings stay in this file so the
        dialogue-integrity scanner sees both the read and the write."""
        if self._player is None:
            return
        if self._player.dialogue_flags.get("seen_tip_mission_log", False):
            return
        from spacegame.views.first_time_tip import FirstTimeTipOverlay

        self._first_time_tip = FirstTimeTipOverlay(
            title="Mission Log",
            body=(
                "Active contracts, available work, and completed history in one place. "
                "Select a mission to see objectives and rewards. The cockpit hint line "
                "tracks the top active mission if you want it to."
            ),
            on_dismiss=self._mark_mission_log_tip_seen,
        )

    def _mark_mission_log_tip_seen(self) -> None:
        if self._player is not None:
            self._player.dialogue_flags["seen_tip_mission_log"] = True

    def on_exit(self) -> None:
        self._destroy_ui()
        super().on_exit()
        logger.info("Exited mission log view")

    def _create_ui(self) -> None:
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                PANEL_LEFT, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - scale_y(60), 120, 40
            ),
            text="BACK",
            manager=self.ui_manager,
        )

        # Accept button in detail panel area
        detail_x = PANEL_LEFT + LIST_WIDTH + 30
        self._accept_btn = _AcceptButton(
            pygame.Rect(detail_x + 20, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 140, 140, 38),
            self._label_font,
        )
        # Abandon button (same position, different tab)
        self._abandon_btn = _AbandonButton(
            pygame.Rect(detail_x + 20, WINDOW_HEIGHT - scale_y(HUD_BASE_HEIGHT) - 140, 140, 38),
            self._label_font,
        )

    def _destroy_ui(self) -> None:
        if self.back_button:
            self.back_button.kill()
            self.back_button = None

    def _build_tabs(self) -> None:
        self._tabs.clear()
        tab_labels = [("active", "Active"), ("available", "Available"), ("completed", "Completed")]
        for i, (key, label) in enumerate(tab_labels):
            rect = pygame.Rect(
                PANEL_LEFT + i * (TAB_WIDTH + 8), PANEL_TOP - TAB_HEIGHT - 6, TAB_WIDTH, TAB_HEIGHT
            )
            tab = _TabButton(rect, label, self._tab_font)
            tab.active = key == self._current_tab
            self._tabs.append(tab)

    def _refresh_list(self) -> None:
        """Rebuild the mission item list for the current tab."""
        self._mission_items.clear()
        self._scroll_offset = 0

        if not self.mission_manager:
            return

        status_map = {
            "active": MissionStatus.ACTIVE,
            "available": MissionStatus.AVAILABLE,
            "completed": MissionStatus.COMPLETED,
        }
        status = status_map.get(self._current_tab, MissionStatus.ACTIVE)
        missions = self.mission_manager.get_missions_by_status(status)
        # Completed tab also shows abandoned and failed missions
        if self._current_tab == "completed":
            missions.extend(self.mission_manager.get_missions_by_status(MissionStatus.ABANDONED))
            missions.extend(self.mission_manager.get_missions_by_status(MissionStatus.FAILED))
        # PT-J: Available tab hides missions that surface through other channels.
        # NPC-initiated missions appear when the player accepts them in dialogue;
        # encounter missions appear when the player triggers the encounter.
        # Surfacing them here before that happens breaks the "jobs come from
        # people, not menus" framing (playtest finding PT-013). Station-board
        # and campaign missions stay visible because they're meant to be
        # discovered at this surface.
        if self._current_tab == "available":
            missions = [m for m in missions if m.discovery_method not in ("npc", "encounter")]
        # Sort: campaign missions first, then side missions
        missions.sort(key=lambda m: (0 if m.mission_type == "campaign" else 1, m.name))

        for i, mission in enumerate(missions):
            rect = pygame.Rect(
                PANEL_LEFT + 4,
                PANEL_TOP + 4 + i * (ITEM_HEIGHT + 4),
                LIST_WIDTH - 8,
                ITEM_HEIGHT,
            )
            mission_status = (
                self.mission_manager.get_status(mission.id) if self.mission_manager else None
            )
            item = _MissionItem(
                rect, mission, self._name_font, self._badge_font, status=mission_status
            )
            self._mission_items.append(item)

        # Auto-select first if available
        if self._mission_items:
            self._mission_items[0].selected = True
            self._selected_mission_id = self._mission_items[0].mission.id
        else:
            self._selected_mission_id = None

        # Show accept button only on available tab
        if self._accept_btn:
            self._accept_btn.visible = (
                self._current_tab == "available" and self._selected_mission_id is not None
            )
        self._update_abandon_visibility()

    def _update_abandon_visibility(self) -> None:
        """Show abandon button only for active side missions."""
        if not self._abandon_btn:
            return
        if self._current_tab != "active" or not self._selected_mission_id:
            self._abandon_btn.visible = False
            return
        # Only side missions can be abandoned
        mission = (
            self.mission_manager.get_mission(self._selected_mission_id)
            if self.mission_manager
            else None
        )
        self._abandon_btn.visible = mission is not None and mission.mission_type == "side"

    def _select_mission(self, mission_id: str) -> None:
        self._selected_mission_id = mission_id
        for item in self._mission_items:
            item.selected = item.mission.id == mission_id
        if self._accept_btn:
            self._accept_btn.visible = (
                self._current_tab == "available" and self._selected_mission_id is not None
            )
        self._update_abandon_visibility()

    def handle_event(self, event: pygame.event.Event) -> None:
        # PT-M: tip overlay consumes events while active
        if self._first_time_tip is not None and not self._first_time_tip.dismissed:
            if self._first_time_tip.handle_event(event):
                return
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self.next_state = GameState.GALAXY_MAP

        # Tab clicks
        for i, tab in enumerate(self._tabs):
            if tab.was_clicked(event):
                tab_keys = ["active", "available", "completed"]
                self._current_tab = tab_keys[i]
                for t in self._tabs:
                    t.active = False
                tab.active = True
                self._refresh_list()
                return

        # Mission item clicks
        for item in self._mission_items:
            if item.was_clicked(event):
                self._select_mission(item.mission.id)
                return

        # Confirmation overlay intercepts all clicks when active
        if self._abandon_confirm_active:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Yes/No button hit detection (centered overlay)
                cx = WINDOW_WIDTH // 2
                cy = WINDOW_HEIGHT // 2
                yes_rect = pygame.Rect(cx - 120, cy + 20, 100, 36)
                no_rect = pygame.Rect(cx + 20, cy + 20, 100, 36)
                if yes_rect.collidepoint(mx, my):
                    self.pending_abandon_id = self._abandon_confirm_mission_id
                    self._abandon_confirm_active = False
                    self._abandon_confirm_mission_id = None
                    self.next_state = GameState.GALAXY_MAP
                elif no_rect.collidepoint(mx, my):
                    self._abandon_confirm_active = False
                    self._abandon_confirm_mission_id = None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_n:
                    self._abandon_confirm_active = False
                    self._abandon_confirm_mission_id = None
                elif event.key == pygame.K_y or event.key == pygame.K_RETURN:
                    self.pending_abandon_id = self._abandon_confirm_mission_id
                    self._abandon_confirm_active = False
                    self._abandon_confirm_mission_id = None
                    self.next_state = GameState.GALAXY_MAP
            return  # Consume all events while confirm is open

        # Accept button
        if self._accept_btn and self._accept_btn.was_clicked(event):
            if self._selected_mission_id:
                self.pending_accept_id = self._selected_mission_id
                self.next_state = GameState.GALAXY_MAP
                return

        # Abandon button
        if self._abandon_btn and self._abandon_btn.was_clicked(event):
            if self._selected_mission_id:
                self._abandon_confirm_active = True
                self._abandon_confirm_mission_id = self._selected_mission_id
                return

        # Scroll
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_offset = max(0, self._scroll_offset - event.y * 20)

    def update(self, dt: float) -> None:
        # PT-M: tick tip overlay; clear once dismissed
        if self._first_time_tip is not None:
            self._first_time_tip.update(dt)
            if self._first_time_tip.dismissed:
                self._first_time_tip = None
        self.background.update(dt)
        mouse_pos = pygame.mouse.get_pos()
        for tab in self._tabs:
            tab.update_hover(mouse_pos)
        for item in self._mission_items:
            item.update_hover(mouse_pos)
        if self._accept_btn:
            self._accept_btn.update_hover(mouse_pos)
        if self._abandon_btn:
            self._abandon_btn.update_hover(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title_surf = self._title_font.render("MISSION LOG", True, Colors.TEXT_PRIMARY)
        screen.blit(title_surf, (PANEL_LEFT, 30))

        # Tabs
        for tab in self._tabs:
            tab.render(screen)

        # List panel background
        list_rect = pygame.Rect(PANEL_LEFT, PANEL_TOP, LIST_WIDTH, LIST_HEIGHT)
        draw_panel(screen, list_rect, alpha=255)

        # Mission items (clipped to list panel)
        clip_prev = screen.get_clip()
        screen.set_clip(list_rect)
        if not self._mission_items:
            # Empty-state copy varies per tab so the player knows whether
            # the absence is "nothing accepted yet" vs "none pending" vs
            # "nothing finished yet."
            _TAB_EMPTY_COPY = {
                "active": "Nothing active. Pick something up from Available.",
                "available": "Nothing on the board yet.",
                "completed": "Nothing finished yet.",
            }
            empty_text = _TAB_EMPTY_COPY.get(
                self._current_tab, "Nothing here yet."
            )
            empty_surf = self._desc_font.render(empty_text, True, Colors.TEXT_SECONDARY)
            screen.blit(
                empty_surf,
                (
                    list_rect.x + (list_rect.width - empty_surf.get_width()) // 2,
                    list_rect.y + scale_y(40),
                ),
            )
        else:
            for item in self._mission_items:
                # Apply scroll offset
                shifted_rect = item.rect.move(0, -self._scroll_offset)
                if shifted_rect.bottom < list_rect.top or shifted_rect.top > list_rect.bottom:
                    continue
                orig_rect = item.rect
                item.rect = shifted_rect
                item.render(screen)
                item.rect = orig_rect
        screen.set_clip(clip_prev)

        # Detail panel
        detail_x = PANEL_LEFT + LIST_WIDTH + 30
        detail_rect = pygame.Rect(detail_x, PANEL_TOP, DETAIL_WIDTH, LIST_HEIGHT)
        draw_panel(screen, detail_rect, alpha=255)

        self._render_detail_panel(screen, detail_x, PANEL_TOP)

        # Accept button
        if self._accept_btn:
            self._accept_btn.render(screen)

        # Abandon button
        if self._abandon_btn:
            self._abandon_btn.render(screen)

        # Abandon confirmation overlay
        if self._abandon_confirm_active:
            self._render_abandon_confirm(screen)

    def _render_abandon_confirm(self, screen: pygame.Surface) -> None:
        """Render the 'Are you sure?' confirmation overlay."""
        # Dim background
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        # Panel
        pw, ph = scale_x(360), scale_y(140)
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        px, py = cx - pw // 2, cy - ph // 2
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((14, 18, 32, 240))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (200, 80, 80), (px, py, pw, ph), 2, border_radius=6)

        # Title
        title = self._detail_title_font.render("Abandon Mission?", True, (220, 100, 100))
        screen.blit(title, title.get_rect(centerx=cx, top=py + scale_y(14)))

        # Mission name
        mission = (
            self.mission_manager.get_mission(self._abandon_confirm_mission_id)
            if self.mission_manager and self._abandon_confirm_mission_id
            else None
        )
        if mission:
            name_surf = self._desc_font.render(mission.name, True, Colors.TEXT_SECONDARY)
            screen.blit(name_surf, name_surf.get_rect(centerx=cx, top=py + scale_y(50)))

        # Subtitle
        sub = self._desc_font.render("No rewards will be given.", True, Colors.TEXT_SECONDARY)
        screen.blit(sub, sub.get_rect(centerx=cx, top=py + scale_y(70)))

        # Yes / No buttons
        yes_rect = pygame.Rect(cx - 120, cy + 20, 100, 36)
        no_rect = pygame.Rect(cx + 20, cy + 20, 100, 36)
        mouse = pygame.mouse.get_pos()

        for rect, label, base_bg, hover_bg, border_c, text_c in [
            (yes_rect, "YES", (60, 25, 25), (100, 35, 35), (200, 60, 60), (220, 80, 80)),
            (no_rect, "NO", (25, 35, 50), (35, 50, 70), (80, 120, 180), Colors.TEXT_PRIMARY),
        ]:
            hovered = rect.collidepoint(mouse)
            bg = hover_bg if hovered else base_bg
            pygame.draw.rect(screen, bg, rect, border_radius=4)
            pygame.draw.rect(screen, border_c, rect, 1, border_radius=4)
            t = self._label_font.render(label, True, text_c)
            screen.blit(t, t.get_rect(center=rect.center))

    def _render_detail_panel(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Render the selected mission's details."""
        if not self._selected_mission_id or not self.mission_manager:
            # Empty state
            no_sel = self._desc_font.render(
                "Select a mission to view details.", True, Colors.TEXT_SECONDARY
            )
            screen.blit(no_sel, (x + 20, y + 30))
            return

        mission = self.mission_manager.get_mission(self._selected_mission_id)
        if not mission:
            return

        pad_x = x + 20
        cur_y = y + 18

        # Mission type label
        if mission.mission_type == "side":
            type_label = "SIDE MISSION"
            type_color = _SIDE_BADGE_COLOR
        else:
            type_label = "CAMPAIGN MISSION"
            type_color = _CAMPAIGN_BADGE_COLOR
        type_surf = self._badge_font.render(type_label, True, type_color)
        screen.blit(type_surf, (pad_x, cur_y))
        cur_y += 18

        # Mission name
        name_surf = self._detail_title_font.render(mission.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name_surf, (pad_x, cur_y))
        cur_y += 34

        # Description (word-wrapped)
        cur_y = self._render_wrapped(
            screen,
            mission.description,
            self._desc_font,
            Colors.TEXT_SECONDARY,
            pad_x,
            cur_y,
            DETAIL_WIDTH - 40,
        )
        cur_y += 20

        # Objectives header
        obj_header = self._label_font.render("Objectives:", True, Colors.TEXT_PRIMARY)
        screen.blit(obj_header, (pad_x, cur_y))
        cur_y += 26

        # Objective checklist with location details
        progress = self.mission_manager.get_objective_progress(self._selected_mission_id)
        for i, obj in enumerate(mission.objectives):
            completed = progress[i] if i < len(progress) else False
            check = "\u2611" if completed else "\u2610"
            color = Colors.GREEN if completed else Colors.TEXT_SECONDARY
            obj_text = f"{check} {obj.description}"
            obj_surf = self._desc_font.render(obj_text, True, color)
            screen.blit(obj_surf, (pad_x + 10, cur_y))
            cur_y += 20

            # Show location hint for incomplete objectives
            if not completed:
                detail = self._get_objective_detail(obj)
                if detail:
                    detail_surf = self._small_font.render(detail, True, (120, 140, 170))
                    screen.blit(detail_surf, (pad_x + 30, cur_y))
                    cur_y += 16
            cur_y += 4

        # Hint (actionable guidance)
        if mission.hint:
            cur_y += 12
            hint_header = self._label_font.render("Hint:", True, Colors.TEXT_PRIMARY)
            screen.blit(hint_header, (pad_x, cur_y))
            cur_y += 24
            cur_y = self._render_wrapped(
                screen,
                mission.hint,
                self._desc_font,
                (180, 200, 220),
                pad_x + 10,
                cur_y,
                DETAIL_WIDTH - 50,
            )

        cur_y += 16

        # Rewards header
        rew_header = self._label_font.render("Rewards:", True, Colors.TEXT_PRIMARY)
        screen.blit(rew_header, (pad_x, cur_y))
        cur_y += 26

        for reward in mission.rewards:
            if reward.reward_type == "credits":
                rew_text = f"+{reward.amount:,} Credits"
                color = Colors.YELLOW
            elif reward.reward_type == "xp":
                rew_text = f"+{reward.amount} XP"
                color = Colors.BLUE
            elif reward.reward_type == "modify_reputation":
                sign = "+" if reward.amount > 0 else ""
                rew_text = f"{sign}{reward.amount} {reward.target_id} rep"
                color = Colors.GREEN if reward.amount > 0 else Colors.RED
            elif reward.reward_type in ("set_flag", "remove_cargo", "deduct_credits"):
                continue  # Don't show internal flags or deductions in UI
            else:
                rew_text = f"+{reward.amount} {reward.reward_type}"
                color = Colors.TEXT_SECONDARY
            rew_surf = self._desc_font.render(rew_text, True, color)
            screen.blit(rew_surf, (pad_x + 10, cur_y))
            cur_y += 22

        # QA-G-3: Soft-deadline indicator (TW). Only meaningful for active
        # missions where we have an accept_day to compare against. Three
        # tier colors so the player can see at a glance whether they're
        # still in the full-reward window.
        if (
            mission.soft_deadline is not None
            and self._current_tab == "active"
            and self._player is not None
            and self.mission_manager is not None
        ):
            cur_y += 12
            accepted = self.mission_manager.get_accepted_day(mission.id)
            if accepted is not None:
                elapsed = max(0, self._player.game_day - accepted)
                full = mission.soft_deadline.full_reward_day_count
                partial = mission.soft_deadline.partial_reward_day_count
                if elapsed <= full:
                    days_left = full - elapsed
                    text = f"Deadline: {days_left} day{'s' if days_left != 1 else ''} left for full reward."
                    color = Colors.GREEN
                elif elapsed <= partial:
                    days_left = partial - elapsed
                    pct = int(mission.soft_deadline.partial_reward_multiplier * 100)
                    text = f"Late. Partial reward ({pct}%). {days_left} day{'s' if days_left != 1 else ''} before reward floors."
                    color = Colors.YELLOW
                else:
                    pct = int(mission.soft_deadline.late_multiplier * 100)
                    text = f"Past deadline. Reward at {pct}%."
                    color = Colors.RED
                deadline_surf = self._desc_font.render(text, True, color)
                screen.blit(deadline_surf, (pad_x, cur_y))

        # Prerequisites (if any and on available tab)
        if mission.prerequisites and self._current_tab == "available":
            cur_y += 12
            prereq_surf = self._desc_font.render(
                f"Requires: {', '.join(mission.prerequisites)}",
                True,
                Colors.TEXT_SECONDARY,
            )
            screen.blit(prereq_surf, (pad_x, cur_y))

    def _get_objective_detail(self, obj: "MissionObjective") -> str:
        """Get a location/quantity hint for an objective, or empty string."""
        if obj.type == ObjectiveType.REACH_SYSTEM and self._data_loader:
            system = self._data_loader.get_system(obj.target_id)
            if system:
                return f"\u2192 {system.name}"
        if obj.type == ObjectiveType.TALK_TO_NPC and self._data_loader:
            npc = self._data_loader.get_npc(obj.target_id)
            if npc:
                system = self._data_loader.get_system(npc.home_system_id)
                loc = system.name if system else npc.home_system_id
                return f"\u2192 {npc.name} at {loc}"
        if obj.type == ObjectiveType.COLLECT_CARGO and self._player:
            current = self._player.ship.get_cargo_quantity(obj.target_id)
            return f"\u2192 {current}/{obj.target_quantity} in cargo"
        return ""

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

    def render_top(self, screen: pygame.Surface) -> None:
        """PT-M: draw the first-time tip above pygame_gui elements."""
        if self._first_time_tip is not None:
            self._first_time_tip.render(screen)

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
