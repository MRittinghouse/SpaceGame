"""
Salvage operations mini-game view.

Grid-based scanning and extraction puzzle.
Features scan pulse particles, cell reveal fade, metallic hidden cells, and extraction sparks.
"""

import pygame
import pygame_gui
import random
import math
from typing import Optional, Dict, List
from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.player import Player
from spacegame.models.commodity import Commodity
from spacegame.models.salvage import (
    SalvageSession,
    SalvageConfig,
    SalvageResult,
    SalvageCell,
    CellState,
    SalvageItemType,
    SALVAGE_ITEM_CONFIGS,
)
from spacegame.models.rating import calculate_rating, SALVAGE_THRESHOLDS, RATING_COLORS
from spacegame.engine.draw_utils import draw_bar, draw_summary_overlay
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import (
    ParticlePool, SCAN_PULSE, SPARK_BURST, COLLECT_SPARKLE,
    SALVAGE_SCAN, SALVAGE_CORRUPT,
)
from spacegame.engine.fonts import FontCache
from spacegame.engine.sprites import get_sprite_manager
from spacegame.engine.audio_manager import get_audio_manager


class SalvageView(BaseView):
    """Salvage operations mini-game with visual effects."""

    CELL_SIZE = 90
    CELL_PADDING = 4
    GRID_OFFSET_X = 60
    GRID_OFFSET_Y = 120

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        commodities: Dict[str, Commodity],
        salvage_config: Optional[SalvageConfig] = None,
        progression=None,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.commodities = commodities
        self.progression = progression

        if salvage_config is None:
            salvage_config = SalvageConfig(system_id=player.current_system_id)
        self.salvage_config = salvage_config

        self.session: Optional[SalvageSession] = None
        self.next_state: Optional[GameState] = None
        self.mode: str = "scan"

        # Fonts
        self.title_font = FontCache.get(36)
        self.info_font = FontCache.get(24)
        self.small_font = FontCache.get(20)
        self.cell_font = FontCache.get(18)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.scan_button: Optional[pygame_gui.elements.UIButton] = None
        self.extract_button: Optional[pygame_gui.elements.UIButton] = None
        self.regen_button: Optional[pygame_gui.elements.UIButton] = None

        # Feedback
        self.feedback_messages: List[dict] = []
        self.message: str = ""
        self.message_timer: float = 0.0

        # Animated background
        self.background = AnimatedBackground("debris", WINDOW_WIDTH, WINDOW_HEIGHT, seed=60)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(100)

        # Particles
        self.particles = ParticlePool(200)

        # Cell reveal fade-in tracking
        self._reveal_timers: Dict[tuple, float] = {}  # (gx, gy) -> timer 0.0-0.2
        self._static_time = 0.0

        # Salvage commodity sprites (commodity_id -> Surface at 3x scale = 48x48)
        self._sprite_mgr = get_sprite_manager()
        self._item_icons: Dict[str, Optional[pygame.Surface]] = {}
        for config in SALVAGE_ITEM_CONFIGS.values():
            self._item_icons[config.commodity_id] = self._sprite_mgr.get_commodity_icon(
                config.commodity_id, scale=3
            )

        # Session summary overlay
        self._show_summary: bool = False
        self._summary_xp: int = 0
        self._session_elapsed: float = 0.0
        self._session_rating: str = "D"
        self._summary_font = FontCache.get(32)
        self._summary_title_font = FontCache.get(44)
        self._rating_font = FontCache.get(72)

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered salvage operations")

        extract_bonus = 1.0
        extra_charges = 0
        extra_parallel = 0
        if self.progression:
            extract_bonus += self.progression.get_bonus("extract_speed")
            extra_charges = int(self.progression.get_bonus("extra_scan_charges"))
            # master_extractor level 3 (3 * 0.20 = 0.60) unlocks 3rd parallel slot
            if self.progression.get_bonus("extract_speed") >= 0.60:
                extra_parallel = 1

        self.session = SalvageSession(
            self.salvage_config,
            extract_speed_bonus=extract_bonus,
            extra_charges=extra_charges,
            extra_parallel=extra_parallel,
        )
        self._reveal_timers.clear()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        btn_x = WINDOW_WIDTH - 200
        self.scan_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, WINDOW_HEIGHT - 180, 170, 35),
            text="Scan Mode",
            manager=self.ui_manager,
        )
        self.extract_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, WINDOW_HEIGHT - 140, 170, 35),
            text="Extract Mode",
            manager=self.ui_manager,
        )
        self.regen_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, WINDOW_HEIGHT - 100, 170, 35),
            text="New Wreck",
            manager=self.ui_manager,
        )
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, WINDOW_HEIGHT - 60, 170, 35),
            text="Stop Salvaging",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        for btn in [self.back_button, self.scan_button, self.extract_button, self.regen_button]:
            if btn:
                btn.kill()

    def _get_grid_cell(self, mouse_pos: tuple) -> Optional[tuple]:
        mx, my = mouse_pos
        gx = (mx - self.GRID_OFFSET_X) // self.CELL_SIZE
        gy = (my - self.GRID_OFFSET_Y) // self.CELL_SIZE
        if self.session:
            grid_size = self.session.derelict_type.grid_size
            if 0 <= gx < grid_size and 0 <= gy < grid_size:
                return (gx, gy)
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        # Summary dismiss: click or key
        if self._show_summary:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.next_state = GameState.TRADING
            elif event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE,
            ):
                self.next_state = GameState.TRADING
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._get_grid_cell(event.pos)
            if cell:
                self._click_cell(cell[0], cell[1])

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                xp = 0
                if self.session and self.progression:
                    total = sum(self.session.total_salvaged.values())
                    if total > 0:
                        from spacegame.config import XP_PER_SALVAGE

                        xp = total * XP_PER_SALVAGE
                        msgs = self.progression.add_xp(xp)
                        for m in msgs:
                            logger.info(m)
                self.player.salvage_sessions_completed += 1
                self._summary_xp = xp
                self._calculate_rating()
                self._show_summary = True
                self._destroy_ui()
            elif event.ui_element == self.scan_button:
                self.mode = "scan"
                self._show_message("Scan mode: click cells to reveal contents")
            elif event.ui_element == self.extract_button:
                self.mode = "extract"
                self._show_message("Extract mode: click scanned items to extract them")
            elif event.ui_element == self.regen_button:
                if self.session:
                    self.session.regenerate_grid()
                    self._reveal_timers.clear()
                    self._show_message("Found a new derelict hull!")

    def _click_cell(self, gx: int, gy: int) -> None:
        if not self.session:
            return

        if self.mode == "scan":
            success, msg = self.session.scan_cell(gx, gy)
            if success:
                fx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
                fy = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_SIZE // 2
                # Scan pulse particles
                self.particles.emit(fx, fy, SALVAGE_SCAN)
                get_audio_manager().play_sfx("salvage_scan")
                # Start reveal fade-in
                self._reveal_timers[(gx, gy)] = 0.0
                self._add_feedback(msg, fx, fy - self.CELL_SIZE // 2)
            else:
                self._show_message(msg)
        elif self.mode == "extract":
            commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
            if self.player.ship.get_available_cargo(commodity_volumes) <= 0:
                self._show_message("Cargo hold full!")
                return
            success, msg = self.session.start_extract(gx, gy)
            if success:
                get_audio_manager().play_sfx("salvage_extract")
            else:
                self._show_message(msg)

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 2.5

    def _add_feedback(self, text: str, x: int, y: int, color=Colors.SUCCESS) -> None:
        self.feedback_messages.append({"text": text, "x": x, "y": y, "timer": 1.5, "color": color})

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._static_time += dt
        if not self._show_summary:
            self._session_elapsed += dt

        if self.message_timer > 0:
            self.message_timer -= dt

        for fb in self.feedback_messages:
            fb["timer"] -= dt
            fb["y"] -= 25 * dt
        self.feedback_messages = [fb for fb in self.feedback_messages if fb["timer"] > 0]

        # Update reveal timers
        for key in list(self._reveal_timers):
            self._reveal_timers[key] += dt
            if self._reveal_timers[key] >= 0.2:
                del self._reveal_timers[key]

        # Emit extraction sparks
        if self.session:
            for cell in self.session.grid:
                if cell.state == CellState.EXTRACTING:
                    fx = self.GRID_OFFSET_X + cell.grid_x * self.CELL_SIZE + self.CELL_SIZE // 2
                    fy = self.GRID_OFFSET_Y + cell.grid_y * self.CELL_SIZE + self.CELL_SIZE // 2
                    if random.random() < 0.2:
                        self.particles.emit(fx, fy, SPARK_BURST)

            results = self.session.update(dt)
            for result in results:
                self._handle_extract_result(result)

    def _handle_extract_result(self, result: SalvageResult) -> None:
        self.player.ship.add_cargo(result.commodity_id, result.quantity, price_per_unit=0)
        self.player.items_salvaged += result.quantity
        if result.corrupted and result.quantity > 0:
            self.player.corrupted_items_extracted += result.quantity
        commodity = self.commodities.get(result.commodity_id)
        name = commodity.name if commodity else result.commodity_id

        fx = WINDOW_WIDTH // 2
        fy = WINDOW_HEIGHT // 2
        if result.corrupted:
            self.particles.emit(fx, fy, SALVAGE_CORRUPT)
            get_audio_manager().play_sfx("salvage_corrupt")
        else:
            self.particles.emit(fx, fy, COLLECT_SPARKLE)
            get_audio_manager().play_sfx("salvage_reveal")
        self._add_feedback(f"+{result.quantity} {name}", fx, fy)

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        title = self.title_font.render("SALVAGE OPERATIONS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        if not self.session:
            return

        mode_text = f"Mode: {'SCAN' if self.mode == 'scan' else 'EXTRACT'}"
        instr = self.small_font.render(mode_text, True, Colors.YELLOW)
        screen.blit(instr, (self.GRID_OFFSET_X, 60))

        # Derelict type name
        derelict_name = self.session.derelict_type.name
        tip = self.small_font.render(
            f"Derelict: {derelict_name} — Scan cells to find items, then Extract to collect.",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(tip, (self.GRID_OFFSET_X, 80))

        self._render_corruption_timer(screen)
        self._render_grid(screen)
        self._render_stats(screen)

        # Particles
        self.particles.render(screen)

        for fb in self.feedback_messages:
            surf = self.info_font.render(fb["text"], True, fb["color"])
            screen.blit(surf, (int(fb["x"]) - surf.get_width() // 2, int(fb["y"])))

        if self.message_timer > 0:
            msg_surf = self.info_font.render(self.message, True, Colors.YELLOW)
            screen.blit(
                msg_surf, msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 200))
            )

        # Summary overlay (drawn last, on top of everything)
        if self._show_summary:
            self._render_summary(screen)

    def _render_corruption_timer(self, screen: pygame.Surface) -> None:
        """Render corruption countdown bar above the grid."""
        if not self.session.corruption_started:
            return
        grid_size = self.session.derelict_type.grid_size
        bar_x = self.GRID_OFFSET_X
        bar_y = self.GRID_OFFSET_Y - 24
        bar_w = grid_size * self.CELL_SIZE
        bar_h = 16

        pct = max(0, self.session.corruption_timer / self.session.corruption_seconds)
        if pct > 0.6:
            color = (50, 200, 50)
        elif pct > 0.3:
            color = (220, 200, 50)
        else:
            color = (220, 50, 50)

        draw_bar(
            screen, bar_x, bar_y, bar_w, bar_h,
            self.session.corruption_timer, self.session.corruption_seconds, color,
            show_value=False, border_color=Colors.TEXT_SECONDARY,
        )

        if self.session.is_corrupted:
            label = self.small_font.render("CORRUPTED", True, (255, 80, 80))
        else:
            secs = max(0, int(self.session.corruption_timer))
            label = self.small_font.render(f"Corruption: {secs}s", True, Colors.TEXT)
        screen.blit(label, label.get_rect(center=(bar_x + bar_w // 2, bar_y + bar_h // 2)))

    def _render_grid(self, screen: pygame.Surface) -> None:
        mouse_pos = pygame.mouse.get_pos()
        hover_cell = self._get_grid_cell(mouse_pos)

        for cell in self.session.grid:
            x = self.GRID_OFFSET_X + cell.grid_x * self.CELL_SIZE + self.CELL_PADDING
            y = self.GRID_OFFSET_Y + cell.grid_y * self.CELL_SIZE + self.CELL_PADDING
            w = self.CELL_SIZE - self.CELL_PADDING * 2
            h = self.CELL_SIZE - self.CELL_PADDING * 2
            rect = pygame.Rect(x, y, w, h)

            if cell.state == CellState.HIDDEN:
                # Dark metallic surface with flickering static pixels
                pygame.draw.rect(screen, (40, 42, 55), rect)
                pygame.draw.rect(screen, (65, 68, 85), rect, 1)

                # Flickering static pixels
                rng = random.Random(
                    int(self._static_time * 10) + cell.grid_x * 7 + cell.grid_y * 13
                )
                for _ in range(5):
                    px = x + rng.randint(4, w - 4)
                    py = y + rng.randint(4, h - 4)
                    brightness = rng.randint(50, 90)
                    screen.set_at((px, py), (brightness, brightness, brightness + 5))

                label = self.cell_font.render("???", True, (80, 82, 95))
                screen.blit(label, label.get_rect(center=rect.center))

            elif cell.state == CellState.CORRUPTED:
                # Dark red tint with static noise
                pygame.draw.rect(screen, (55, 25, 25), rect)
                pygame.draw.rect(screen, (90, 40, 40), rect, 1)
                rng = random.Random(
                    int(self._static_time * 8) + cell.grid_x * 11 + cell.grid_y * 17
                )
                for _ in range(8):
                    px = x + rng.randint(4, w - 4)
                    py = y + rng.randint(4, h - 4)
                    screen.set_at((px, py), (rng.randint(80, 140), 30, 30))
                label = self.cell_font.render("CORRUPT", True, (160, 60, 60))
                screen.blit(label, label.get_rect(center=rect.center))

            elif cell.state == CellState.SCANNED:
                # Check if still fading in
                reveal_key = (cell.grid_x, cell.grid_y)
                reveal_t = 1.0
                if reveal_key in self._reveal_timers:
                    reveal_t = min(1.0, self._reveal_timers[reveal_key] / 0.2)

                if cell.has_item:
                    color = cell.config.color
                    # Fade-in: lerp from dark to actual color
                    r = int(20 + (color[0] - 20) * reveal_t)
                    g = int(22 + (color[1] - 22) * reveal_t)
                    b = int(30 + (color[2] - 30) * reveal_t)
                    pygame.draw.rect(screen, (r, g, b), rect)
                    if reveal_t > 0.5:
                        # Try commodity icon, fall back to text label
                        icon = self._item_icons.get(cell.config.commodity_id) if cell.config else None
                        if icon is not None:
                            # Icon in upper portion, tier label below
                            icon_x = rect.centerx - icon.get_width() // 2
                            icon_y = rect.top + 4
                            screen.blit(icon, (icon_x, icon_y))
                        else:
                            name = cell.item_type.value.replace("_", " ").title()
                            # Truncate with ellipsis if too wide
                            display = name[:10] + ".." if len(name) > 12 else name
                            label = self.cell_font.render(display, True, Colors.TEXT)
                            screen.blit(label, label.get_rect(center=(rect.centerx, rect.top + 28)))
                        # Quality tier border
                        from spacegame.models.salvage import QualityTier
                        tier_colors = {
                            QualityTier.POOR: (80, 80, 80),
                            QualityTier.NORMAL: (140, 140, 140),
                            QualityTier.GOOD: (100, 200, 100),
                            QualityTier.EXCELLENT: (255, 220, 80),
                        }
                        border_color = tier_colors.get(cell.quality_tier, (140, 140, 140))
                        pygame.draw.rect(screen, border_color, rect, 2)
                        # Tier label below icon, above bottom edge
                        tier_label = self.cell_font.render(
                            cell.quality_tier.value.title(), True, border_color
                        )
                        tier_y = rect.top + 56 if icon is not None else rect.top + 48
                        screen.blit(
                            tier_label,
                            tier_label.get_rect(center=(rect.centerx, tier_y)),
                        )
                else:
                    dark = int(25 * reveal_t)
                    pygame.draw.rect(screen, (dark, dark, dark + 5), rect)
                    if reveal_t > 0.5:
                        # Minesweeper hint number
                        if cell.adjacent_count is not None and cell.adjacent_count > 0:
                            if cell.adjacent_count <= 2:
                                hint_color = (80, 120, 200)
                            elif cell.adjacent_count <= 4:
                                hint_color = (80, 200, 80)
                            else:
                                hint_color = (220, 200, 50)
                            hint_font = FontCache.get(28)
                            hint_surf = hint_font.render(
                                str(cell.adjacent_count), True, hint_color
                            )
                            screen.blit(hint_surf, hint_surf.get_rect(center=rect.center))
                        else:
                            label = self.cell_font.render("Empty", True, (50, 52, 60))
                            screen.blit(label, label.get_rect(center=rect.center))

            elif cell.state == CellState.EXTRACTING:
                color = cell.config.color if cell.config else (100, 100, 100)
                pygame.draw.rect(screen, color, rect)
                # Progress bar at bottom
                bar_y = rect.bottom - 14
                draw_bar(
                    screen,
                    x + 4,
                    bar_y,
                    w - 8,
                    10,
                    cell.extract_progress * 100,
                    100,
                    Colors.TEXT_HIGHLIGHT,
                    show_value=False,
                )
                # Icon in upper portion, or text label
                icon = self._item_icons.get(cell.config.commodity_id) if cell.config else None
                if icon is not None:
                    icon_x = rect.centerx - icon.get_width() // 2
                    icon_y = rect.top + 4
                    screen.blit(icon, (icon_x, icon_y))
                else:
                    label = self.cell_font.render("Extracting...", True, Colors.TEXT)
                    screen.blit(label, label.get_rect(center=(rect.centerx, rect.top + 28)))

            elif cell.state == CellState.EXTRACTED:
                pygame.draw.rect(screen, (15, 28, 15), rect)
                pygame.draw.rect(screen, (40, 65, 40), rect, 1)
                label = self.cell_font.render("Collected", True, (65, 110, 65))
                screen.blit(label, label.get_rect(center=rect.center))

            # Hover
            if hover_cell and hover_cell[0] == cell.grid_x and hover_cell[1] == cell.grid_y:
                pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, rect, 2)

    def _render_stats(self, screen: pygame.Surface) -> None:
        panel_x = WINDOW_WIDTH - 280
        panel_y = 120

        header = self.info_font.render("SALVAGE STATUS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (panel_x, panel_y))

        y = panel_y + 30
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        stats = [
            f"Scan Charges: {self.session.charges}/{self.session.max_charges}",
            f"Hidden: {self.session.get_hidden_count()}/{len(self.session.grid)}",
            f"Ready to Extract: {self.session.get_extractable_count()}",
            f"Cargo: {self.player.ship.get_used_cargo(commodity_volumes)}/{self.player.ship.max_cargo}",
        ]

        if self.session.total_salvaged:
            stats.append("")
            stats.append("Salvaged this session:")
            for cid, qty in self.session.total_salvaged.items():
                commodity = self.commodities.get(cid)
                name = commodity.name if commodity else cid
                stats.append(f"  {name}: {qty}")

        for line in stats:
            surf = self.small_font.render(line, True, Colors.TEXT)
            screen.blit(surf, (panel_x, y))
            y += 22

        # Charge regen bar
        y += 10
        bar_w = 200
        bar_h = 16
        charge_pct = (
            self.session.charges / self.session.max_charges if self.session.max_charges > 0 else 0
        )
        pygame.draw.rect(screen, Colors.BAR_BG, (panel_x, y, bar_w, bar_h))
        fill_w = int(bar_w * charge_pct)
        pygame.draw.rect(screen, Colors.BLUE, (panel_x, y, fill_w, bar_h))
        pygame.draw.rect(screen, Colors.TEXT_SECONDARY, (panel_x, y, bar_w, bar_h), 1)

        regen = self.small_font.render(
            f"Regen: 1 per {self.session.charge_regen_rate:.1f}s", True, Colors.TEXT_SECONDARY
        )
        screen.blit(regen, (panel_x, y + bar_h + 4))

    def _calculate_rating(self) -> None:
        """Calculate session performance rating."""
        if self.session:
            total_items = self.session.get_item_count()
            if total_items > 0:
                extracted = sum(self.session.total_salvaged.values())
                ratio = extracted / total_items
                self._session_rating = calculate_rating(ratio, SALVAGE_THRESHOLDS)
                if self._session_rating == "S":
                    self.player.s_ranks_earned += 1
                return
        self._session_rating = "D"

    def _render_summary(self, screen: pygame.Surface) -> None:
        """Render session summary overlay."""
        stats: list[tuple[str, str]] = []
        if self.session:
            grid_size = self.session.derelict_type.grid_size
            total_cells = grid_size * grid_size
            hidden = self.session.get_hidden_count()
            corrupted_count = sum(
                1 for c in self.session.grid if c.state == CellState.CORRUPTED
            )
            scanned = total_cells - hidden - corrupted_count
            total_items = sum(self.session.total_salvaged.values())

            if self.session.is_corrupted:
                corruption_status = "Survived"
            elif self.session.corruption_started:
                corruption_status = "Avoided"
            else:
                corruption_status = "Not started"

            stats = [
                ("Derelict Type", self.session.derelict_type.name),
                ("Cells Scanned", f"{scanned} / {total_cells}"),
                ("Items Extracted", str(total_items)),
                ("Corruption", corruption_status),
            ]
        draw_summary_overlay(
            screen,
            title="SALVAGE COMPLETE",
            stats=stats,
            xp_earned=self._summary_xp,
            rating_letter=self._session_rating,
            rating_color=RATING_COLORS.get(self._session_rating, Colors.TEXT_SECONDARY),
            panel_height=420,
        )

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
