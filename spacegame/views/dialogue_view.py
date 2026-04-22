"""
Dialogue view for NPC conversations.

Displays NPC portrait placeholder, dialogue text with typewriter effect,
and clickable player response options. Supports skill check indicators
and pass/fail feedback for social skill checks.
"""

from typing import Optional

import pygame

from spacegame.config import (
    DIALOGUE_PORTRAIT_SIZE,
    DIALOGUE_TEXT_SPEED,
    DISPOSITION_FEEDBACK_DURATION,
    DISPOSITION_TIERS,
    SOCIAL_CHECK_FEEDBACK_DURATION,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_x,
    scale_y,
)
from spacegame.data_loader import DataLoader
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_DISPLAY,
    FONT_HEADING,
    FONT_LG,
    FONT_XL2,
    get_font,
)
from spacegame.engine.sprites import AnimatedSprite, get_sprite_manager, res_scale
from spacegame.models.dialogue import NPC, DialogueManager
from spacegame.models.social import SocialManager
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView


class _ResponseButton:
    """Manually-rendered response button for the dialogue view."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        check_info: Optional[dict] = None,
        disposition_preview: int = 0,
    ) -> None:
        self.rect = rect
        self.text = text
        self.font = font
        self.hovered = False
        self.check_info = check_info  # {skill, difficulty, effective, can_pass}
        self.disposition_preview = disposition_preview  # read_the_room: predicted change

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        """Update hover state from current mouse position."""
        self.hovered = self.rect.collidepoint(mouse_pos)

    def render(self, screen: pygame.Surface) -> None:
        """Draw the response button."""
        bg_color = (40, 50, 80) if self.hovered else (25, 32, 55)
        border_color = Colors.TEXT_HIGHLIGHT if self.hovered else Colors.UI_BORDER
        text_color = Colors.TEXT_PRIMARY if self.hovered else Colors.TEXT_SECONDARY

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=4)
        pygame.draw.rect(screen, border_color, self.rect, 1, border_radius=4)

        # Skill check stripe and prefix
        if self.check_info:
            self._render_check_indicator(screen)

        # Arrow prefix — clip text to button width
        prefix = "\u25b8 " if self.hovered else "  "
        display_text = self.text
        max_text_w = self.rect.width - 24  # 12px padding each side
        text_surf = self.font.render(prefix + display_text, True, text_color)
        if text_surf.get_width() > max_text_w:
            while len(display_text) > 3 and text_surf.get_width() > max_text_w:
                display_text = display_text[:-1]
            display_text = display_text.rstrip() + ".."
            text_surf = self.font.render(prefix + display_text, True, text_color)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 12, self.rect.centery))
        screen.blit(text_surf, text_rect)

        # read_the_room: show disposition change preview on the right side
        if self.disposition_preview != 0:
            sign = "+" if self.disposition_preview > 0 else ""
            preview_color = (80, 200, 80) if self.disposition_preview > 0 else (200, 80, 80)
            preview_surf = self.font.render(
                f"{sign}{self.disposition_preview}", True, preview_color
            )
            preview_rect = preview_surf.get_rect(midright=(self.rect.right - 12, self.rect.centery))
            screen.blit(preview_surf, preview_rect)

    def _render_check_indicator(self, screen: pygame.Surface) -> None:
        """Render the color-coded skill check stripe on the left edge."""
        info = self.check_info
        if not info:
            return

        effective = info["effective"]
        difficulty = info["difficulty"]

        if effective >= difficulty:
            color = Colors.CHECK_PASS
        elif effective == difficulty - 1:
            color = Colors.CHECK_MARGINAL
        else:
            color = Colors.CHECK_FAIL

        # Left stripe
        stripe_rect = pygame.Rect(self.rect.x, self.rect.y, 4, self.rect.height)
        pygame.draw.rect(screen, color, stripe_rect, border_radius=2)

    def was_clicked(self, event: pygame.event.Event) -> bool:
        """Check if this button was clicked."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class DialogueView(BaseView):
    """View for NPC dialogue conversations."""

    # Layout constants
    PANEL_WIDTH = scale_x(800)
    PANEL_HEIGHT = scale_y(480)
    PORTRAIT_W, PORTRAIT_H = DIALOGUE_PORTRAIT_SIZE
    TEXT_LEFT_MARGIN = scale_x(150)  # Left edge of text area (after portrait)
    TEXT_TOP = scale_y(80)  # Top of text area within panel
    RESPONSE_TOP_OFFSET = scale_y(30)  # Gap between text area and responses
    RESPONSE_HEIGHT = scale_y(36)
    RESPONSE_GAP = 6

    def __init__(
        self,
        ui_manager: object,
        dialogue_manager: DialogueManager,
        data_loader: DataLoader,
        social_manager: Optional[SocialManager] = None,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.dialogue_manager = dialogue_manager
        self.data_loader = data_loader
        self.social_manager = social_manager
        self.next_state: Optional[GameState] = None

        # Fonts
        self.name_font = get_font("header", FONT_XL2)
        self.title_font = get_font("label", FONT_BODY)
        self.body_font = get_font("dialogue", FONT_LG)
        self.response_font = get_font("dialogue", FONT_BODY)
        self.initial_font = get_font("header", FONT_DISPLAY)
        self.feedback_font = get_font("machine", FONT_HEADING)

        # Panel geometry
        self.panel_x = (WINDOW_WIDTH - self.PANEL_WIDTH) // 2
        self.panel_y = (WINDOW_HEIGHT - self.PANEL_HEIGHT) // 2

        # Background
        self.background = AnimatedBackground("dialogue", WINDOW_WIDTH, WINDOW_HEIGHT, seed=77)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(140)

        # Typewriter state
        self._full_text = ""
        self._revealed_chars = 0
        self._text_timer = 0.0
        self._text_complete = False

        # Response buttons (created dynamically)
        self._response_buttons: list[_ResponseButton] = []

        # Current speaker NPC (for portrait/name rendering; None for narration)
        self._current_npc: Optional[NPC] = None

        # Return state when dialogue ends (configurable per dialogue)
        self._return_state: GameState = GameState.TRADING

        # Skill check feedback overlay
        self._check_feedback: Optional[dict] = None  # {text, timer, success}

        # Disposition UI state
        self._disposition_feedbacks: list[dict] = []  # [{text, timer, color, y_offset}]
        self._cached_disposition: int = 50  # Snapshot for change detection

        # Subtext font (italic-style for Empathic Read hints)
        self._subtext_font = get_font("narration", FONT_BODY)

        # Sprite manager for NPC portraits
        self._sprite_mgr = get_sprite_manager()
        self._portrait_cache: dict[str, Optional[AnimatedSprite]] = {}

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered dialogue view")
        self._check_feedback = None
        self._disposition_feedbacks.clear()
        self._load_current_node()

    def on_exit(self) -> None:
        super().on_exit()
        self._response_buttons.clear()

    def _load_current_node(self) -> None:
        """Load display state from the current dialogue node."""
        node = self.dialogue_manager.get_current_node()
        if not node:
            # Dialogue ended or invalid — return to trading
            self.next_state = GameState.TRADING
            return

        # Look up speaker NPC (None for narrator mode)
        if node.speaker_id == "narrator":
            self._current_npc = None
        else:
            self._current_npc = self.data_loader.get_npc(node.speaker_id)

        # Start typewriter effect
        self._full_text = node.text
        self._revealed_chars = 0
        self._text_timer = 0.0
        self._text_complete = DIALOGUE_TEXT_SPEED <= 0

        # Keep portrait on idle — expression frame swaps are too jarring
        if self._current_npc:
            portrait = self._get_portrait(self._current_npc.id)
            if portrait is not None:
                portrait.play("idle")

        # Cache current disposition for change detection
        npc_id = self.dialogue_manager._current_npc_id or ""
        if self.social_manager and npc_id:
            self._cached_disposition = self.social_manager.get_disposition(npc_id)
        else:
            self._cached_disposition = 50

        # Build response buttons (only shown when text is complete)
        self._build_response_buttons()

    def _build_response_buttons(self) -> None:
        """Create response buttons for the current node."""
        self._response_buttons.clear()
        node = self.dialogue_manager.get_current_node()
        if not node:
            return

        # read_the_room skill: preview disposition changes on responses
        has_read_the_room = False
        player = self.dialogue_manager._player
        if player and hasattr(player, "progression"):
            has_read_the_room = player.progression.get_bonus("read_the_room") > 0

        responses = self.dialogue_manager.get_available_responses()
        if not responses:
            # Terminal node — show a "[Continue]" button to end
            responses_text = ["[Continue]"]
            check_infos: list[Optional[dict]] = [None]
            disposition_previews: list[int] = [0]
        else:
            responses_text = []
            check_infos = []
            disposition_previews = []
            for r in responses:
                if r.skill_check and self.social_manager:
                    sc = r.skill_check
                    npc_id = self.dialogue_manager._current_npc_id or ""
                    effective = self.social_manager.get_effective_level(sc.skill, npc_id)
                    can_pass = self.social_manager.can_pass_check(sc.skill, sc.difficulty, npc_id)
                    skill_name = sc.skill.capitalize()
                    display_text = f"[{skill_name}: {effective}/{sc.difficulty}] {r.text}"
                    responses_text.append(display_text)
                    check_infos.append(
                        {
                            "skill": sc.skill,
                            "difficulty": sc.difficulty,
                            "effective": effective,
                            "can_pass": can_pass,
                        }
                    )
                else:
                    responses_text.append(r.text)
                    check_infos.append(None)
                # read_the_room: track disposition change for this response
                disposition_previews.append(r.disposition_change if has_read_the_room else 0)

        # Calculate vertical position for responses
        text_area_bottom = self.panel_y + self.PANEL_HEIGHT - 20
        total_response_height = len(responses_text) * (self.RESPONSE_HEIGHT + self.RESPONSE_GAP)
        response_start_y = text_area_bottom - total_response_height

        btn_x = self.panel_x + 30
        btn_width = self.PANEL_WIDTH - 60

        for i, text in enumerate(responses_text):
            btn_y = response_start_y + i * (self.RESPONSE_HEIGHT + self.RESPONSE_GAP)
            rect = pygame.Rect(btn_x, btn_y, btn_width, self.RESPONSE_HEIGHT)
            btn = _ResponseButton(
                rect, text, self.response_font, check_infos[i], disposition_previews[i]
            )
            self._response_buttons.append(btn)

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.active:
            return

        # Click to reveal text instantly
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self._text_complete:
                self._revealed_chars = len(self._full_text)
                self._text_complete = True
                return

        # Response button clicks (only when text is complete)
        if self._text_complete:
            for i, btn in enumerate(self._response_buttons):
                if btn.was_clicked(event):
                    self._on_response_selected(i)
                    return

        # Consume all clicks to prevent leaking
        if event.type == pygame.MOUSEBUTTONDOWN:
            return

    def _on_response_selected(self, index: int) -> None:
        """Handle a response button click."""
        get_audio_manager().play_sfx("ui_confirm")
        node = self.dialogue_manager.get_current_node()
        if not node:
            return

        available = self.dialogue_manager.get_available_responses()
        if not available:
            # Terminal node — "[Continue]" was clicked
            self.dialogue_manager.end_dialogue()
            self.next_state = self._return_state
            logger.info("Dialogue ended (terminal node)")
            return

        next_node = self.dialogue_manager.select_response(index)

        # Detect disposition changes (always visible, even without Empathic Read)
        npc_id = self.dialogue_manager._current_npc_id or ""
        if self.social_manager and npc_id:
            new_disp = self.social_manager.get_disposition(npc_id)
            delta = new_disp - self._cached_disposition
            if delta != 0:
                sign = "+" if delta > 0 else ""
                color = (80, 200, 80) if delta > 0 else (200, 80, 80)
                self._disposition_feedbacks.append(
                    {
                        "text": f"{sign}{delta} Trust",
                        "timer": DISPOSITION_FEEDBACK_DURATION,
                        "color": color,
                        "y_offset": 0.0,
                    }
                )
                self._cached_disposition = new_disp

        # Check for skill check result feedback
        check_result = self.dialogue_manager.get_last_check_result()
        if check_result is not None:
            success, msg = check_result
            self._check_feedback = {
                "text": "Check Passed!" if success else "Check Failed.",
                "timer": SOCIAL_CHECK_FEEDBACK_DURATION,
                "success": success,
            }
            logger.info(f"Skill check: {msg}")

        if next_node is None:
            # Dialogue ended via response
            self.next_state = self._return_state
            logger.info("Dialogue ended (end response)")
        else:
            # Advance to next node
            get_audio_manager().play_sfx("ui_click")
            self._load_current_node()

    def update(self, dt: float) -> None:
        self.background.update(dt)

        # Typewriter effect
        if not self._text_complete and DIALOGUE_TEXT_SPEED > 0:
            self._text_timer += dt
            chars_to_show = int(self._text_timer * DIALOGUE_TEXT_SPEED)
            if chars_to_show >= len(self._full_text):
                self._revealed_chars = len(self._full_text)
                self._text_complete = True
            else:
                self._revealed_chars = chars_to_show

        # Update portrait animation
        if self._current_npc:
            portrait = self._get_portrait(self._current_npc.id)
            if portrait is not None:
                portrait.update(dt)

        # Skill check feedback timer
        if self._check_feedback:
            self._check_feedback["timer"] -= dt
            if self._check_feedback["timer"] <= 0:
                self._check_feedback = None

        # Disposition feedback timers (float upward and fade)
        for fb in self._disposition_feedbacks:
            fb["timer"] -= dt
            fb["y_offset"] -= 30 * dt  # Float upward
        self._disposition_feedbacks = [fb for fb in self._disposition_feedbacks if fb["timer"] > 0]

    def render(self, screen: pygame.Surface) -> None:
        # Background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Panel
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.PANEL_WIDTH, self.PANEL_HEIGHT)
        draw_panel(screen, panel_rect, alpha=230, bg_color=Colors.PANEL, border_radius=4)

        if self._current_npc:
            # NPC dialogue mode
            self._render_portrait(screen)
            self._render_speaker_info(screen)
            self._render_disposition_indicator(screen)
            self._render_dialogue_text(screen)
            self._render_subtext(screen)
        else:
            # Narrator/monologue mode — full-width text, no portrait
            self._render_narration_text(screen)

        # Separator line above responses
        if self._text_complete:
            sep_y = self._get_response_area_top() - 12
            pygame.draw.line(
                screen,
                Colors.UI_BORDER,
                (self.panel_x + 30, sep_y),
                (self.panel_x + self.PANEL_WIDTH - 30, sep_y),
                1,
            )

        # Response buttons (only when text is fully revealed)
        if self._text_complete:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self._response_buttons:
                btn.update_hover(mouse_pos)
                btn.render(screen)

        # Skill check feedback overlay
        if self._check_feedback:
            self._render_check_feedback(screen)

        # Disposition change floating feedback
        self._render_disposition_feedback(screen)

    def _get_portrait(self, npc_id: str) -> Optional[AnimatedSprite]:
        """Get a cached animated portrait for an NPC."""
        if npc_id not in self._portrait_cache:
            self._portrait_cache[npc_id] = self._sprite_mgr.get_portrait_animated(
                npc_id, scale=res_scale(2)
            )
        return self._portrait_cache[npc_id]

    def _render_portrait(self, screen: pygame.Surface) -> None:
        """Render the NPC portrait (sprite with colored fallback)."""
        npc = self._current_npc
        if not npc:
            return

        px = self.panel_x + 25
        py = self.panel_y + 25
        portrait_rect = pygame.Rect(px, py, self.PORTRAIT_W, self.PORTRAIT_H)

        # Try sprite first
        anim = self._get_portrait(npc.id)
        sprite = anim.get_surface() if anim else None
        if sprite:
            # Scale sprite to fit portrait area
            scaled = pygame.transform.scale(sprite, (self.PORTRAIT_W, self.PORTRAIT_H))
            screen.blit(scaled, (px, py))
        else:
            # Fallback: colored rectangle with initials
            portrait_surf = pygame.Surface((self.PORTRAIT_W, self.PORTRAIT_H), pygame.SRCALPHA)
            portrait_surf.fill((*npc.portrait_color, 180))
            screen.blit(portrait_surf, (px, py))
            initials = "".join(word[0].upper() for word in npc.name.split() if word)
            initials_surf = self.initial_font.render(initials, True, Colors.WHITE)
            initials_rect = initials_surf.get_rect(center=portrait_rect.center)
            screen.blit(initials_surf, initials_rect)

        # Border
        border_color = tuple(min(c + 60, 255) for c in npc.portrait_color)
        pygame.draw.rect(screen, border_color, portrait_rect, 2)

    def _render_speaker_info(self, screen: pygame.Surface) -> None:
        """Render NPC name and title next to portrait."""
        npc = self._current_npc
        if not npc:
            return

        text_x = self.panel_x + self.TEXT_LEFT_MARGIN
        name_y = self.panel_y + 28

        # Name in highlight color
        name_surf = self.name_font.render(npc.name, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(name_surf, (text_x, name_y))

        # Title in secondary color
        if npc.title:
            title_surf = self.title_font.render(npc.title, True, Colors.TEXT_SECONDARY)
            screen.blit(title_surf, (text_x, name_y + 28))

    def _render_dialogue_text(self, screen: pygame.Surface) -> None:
        """Render the dialogue text with typewriter effect."""
        text_x = self.panel_x + self.TEXT_LEFT_MARGIN
        text_y = self.panel_y + self.TEXT_TOP
        max_width = self.PANEL_WIDTH - self.TEXT_LEFT_MARGIN - 30

        # Get the revealed portion of text
        visible_text = self._full_text[: self._revealed_chars]
        if not visible_text:
            return

        self._render_wrapped_text(screen, visible_text, text_x, text_y, max_width)

    def _render_narration_text(self, screen: pygame.Surface) -> None:
        """Render narrator/monologue text — full-width, no portrait."""
        text_x = self.panel_x + 40
        text_y = self.panel_y + 50
        max_width = self.PANEL_WIDTH - 80

        visible_text = self._full_text[: self._revealed_chars]
        if not visible_text:
            return

        self._render_wrapped_text(
            screen, visible_text, text_x, text_y, max_width, Colors.TEXT_SECONDARY
        )

    def _render_wrapped_text(
        self,
        screen: pygame.Surface,
        text: str,
        x: int,
        y: int,
        max_width: int,
        color: tuple[int, int, int] = Colors.TEXT_PRIMARY,
    ) -> None:
        """Render multi-line text with word wrapping."""
        lines = text.split("\n")
        current_y = y

        for line in lines:
            if not line.strip():
                current_y += 12
                continue

            words = line.split(" ")
            current_line = ""

            for word in words:
                test_line = f"{current_line} {word}".strip()
                test_surf = self.body_font.render(test_line, True, color)
                if test_surf.get_width() > max_width and current_line:
                    surf = self.body_font.render(current_line, True, color)
                    screen.blit(surf, (x, current_y))
                    current_y += 24
                    current_line = word
                else:
                    current_line = test_line

            if current_line:
                surf = self.body_font.render(current_line, True, color)
                screen.blit(surf, (x, current_y))
                current_y += 24

    def _render_check_feedback(self, screen: pygame.Surface) -> None:
        """Render skill check result feedback overlay."""
        feedback = self._check_feedback
        if not feedback:
            return

        # Fade based on remaining time
        alpha = min(255, int(255 * feedback["timer"] / SOCIAL_CHECK_FEEDBACK_DURATION * 2))
        color = Colors.CHECK_PASS if feedback["success"] else Colors.CHECK_FAIL

        text_surf = self.feedback_font.render(feedback["text"], True, color)
        text_surf.set_alpha(alpha)

        # Center above the panel
        text_rect = text_surf.get_rect(
            centerx=self.panel_x + self.PANEL_WIDTH // 2,
            bottom=self.panel_y - 10,
        )
        screen.blit(text_surf, text_rect)

    def _render_disposition_indicator(self, screen: pygame.Surface) -> None:
        """Render disposition tier below portrait. Gated on Empathic Read."""
        if not self.dialogue_manager.get_flag("empathic_read_active"):
            return
        npc_id = self.dialogue_manager._current_npc_id or ""
        if not self.social_manager or not npc_id:
            return

        disposition = self.social_manager.get_disposition(npc_id)
        tier = DISPOSITION_TIERS[0]  # Default: Wary
        for t in DISPOSITION_TIERS:
            if t["min"] <= disposition <= t["max"]:
                tier = t
                break

        # Position below portrait
        px = self.panel_x + 25
        py = self.panel_y + 25 + self.PORTRAIT_H + 8

        # Tier label
        label = self.response_font.render(tier["name"], True, tier["color"])
        label_rect = label.get_rect(centerx=px + self.PORTRAIT_W // 2, top=py)
        screen.blit(label, label_rect)

        # Thin bar showing position within 0-100 range
        bar_y = py + 20
        bar_w = self.PORTRAIT_W
        bar_h = 4
        bar_x = px

        # Background
        pygame.draw.rect(screen, (40, 40, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
        # Fill
        fill_w = max(2, int(bar_w * disposition / 100))
        pygame.draw.rect(screen, tier["color"], (bar_x, bar_y, fill_w, bar_h), border_radius=2)

    def _render_subtext(self, screen: pygame.Surface) -> None:
        """Render Empathic Read subtext hint below dialogue text."""
        if not self.dialogue_manager.get_flag("empathic_read_active"):
            return
        node = self.dialogue_manager.get_current_node()
        if not node or not node.subtext or not self._text_complete:
            return

        text_x = self.panel_x + self.TEXT_LEFT_MARGIN
        # Position below the main text area, above the response separator
        response_top = self._get_response_area_top()
        subtext_y = response_top - 30

        # Render in muted italic color
        color = (140, 160, 180)
        surf = self._subtext_font.render(f"* {node.subtext}", True, color)
        # Truncate if too wide
        max_w = self.PANEL_WIDTH - self.TEXT_LEFT_MARGIN - 30
        if surf.get_width() > max_w:
            # Word-wrap into up to 2 lines
            words = f"* {node.subtext}".split()
            line1 = ""
            line2 = ""
            for word in words:
                test = f"{line1} {word}".strip()
                if self._subtext_font.size(test)[0] > max_w and line1:
                    line2 = word
                    continue
                if line2:
                    line2 = f"{line2} {word}"
                else:
                    line1 = test
            if line2:
                s1 = self._subtext_font.render(line1, True, color)
                s2 = self._subtext_font.render(line2, True, color)
                screen.blit(s1, (text_x, subtext_y - 16))
                screen.blit(s2, (text_x, subtext_y))
            else:
                screen.blit(surf, (text_x, subtext_y))
        else:
            screen.blit(surf, (text_x, subtext_y))

    def _render_disposition_feedback(self, screen: pygame.Surface) -> None:
        """Render floating disposition change text near portrait."""
        if not self._disposition_feedbacks:
            return
        for fb in self._disposition_feedbacks:
            alpha = min(255, int(255 * fb["timer"] / DISPOSITION_FEEDBACK_DURATION * 2))
            surf = self.response_font.render(fb["text"], True, fb["color"])
            surf.set_alpha(alpha)
            # Float upward from below the portrait
            base_x = self.panel_x + 25 + self.PORTRAIT_W // 2
            base_y = self.panel_y + 25 + self.PORTRAIT_H + 40
            rect = surf.get_rect(centerx=base_x, top=int(base_y + fb["y_offset"]))
            screen.blit(surf, rect)

    def _get_response_area_top(self) -> int:
        """Get the Y coordinate where response buttons start."""
        if self._response_buttons:
            return self._response_buttons[0].rect.y
        return self.panel_y + self.PANEL_HEIGHT - 60

    def get_next_state(self) -> Optional[GameState]:
        """Return the requested next state."""
        return self.next_state
