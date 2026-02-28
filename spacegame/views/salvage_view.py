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
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import ParticlePool, SCAN_PULSE, SPARK_BURST, COLLECT_SPARKLE


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
        self.title_font = pygame.font.Font(None, 36)
        self.info_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
        self.cell_font = pygame.font.Font(None, 18)

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

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered salvage operations")

        extract_bonus = 1.0
        extra_charges = 0
        if self.progression:
            extract_bonus += self.progression.get_bonus("extract_speed")
            extra_charges = int(self.progression.get_bonus("extra_scan_charges"))

        self.session = SalvageSession(
            self.salvage_config,
            extract_speed_bonus=extract_bonus,
            extra_charges=extra_charges,
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
        if (
            self.session
            and 0 <= gx < self.salvage_config.grid_size
            and 0 <= gy < self.salvage_config.grid_size
        ):
            return (gx, gy)
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._get_grid_cell(event.pos)
            if cell:
                self._click_cell(cell[0], cell[1])

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                if self.session and self.progression:
                    total = sum(self.session.total_salvaged.values())
                    if total > 0:
                        from spacegame.config import XP_PER_SALVAGE

                        xp = total * XP_PER_SALVAGE
                        msgs = self.progression.add_xp(xp)
                        for m in msgs:
                            logger.info(m)
                self.next_state = GameState.TRADING
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
                self.particles.emit(fx, fy, SCAN_PULSE)
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
            if not success:
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

            result = self.session.update(dt)
            if result:
                self._handle_extract_result(result)

    def _handle_extract_result(self, result: SalvageResult) -> None:
        self.player.ship.add_cargo(result.commodity_id, result.quantity, price_per_unit=0)
        self.player.items_salvaged += result.quantity
        commodity = self.commodities.get(result.commodity_id)
        name = commodity.name if commodity else result.commodity_id

        fx = WINDOW_WIDTH // 2
        fy = WINDOW_HEIGHT // 2
        self.particles.emit(fx, fy, COLLECT_SPARKLE)
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

        tip = self.small_font.render(
            "Scan cells to find items, then switch to Extract mode to collect them.",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(tip, (self.GRID_OFFSET_X, 80))

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
                        name = cell.item_type.value.replace("_", " ").title()
                        label = self.cell_font.render(name[:12], True, Colors.TEXT)
                        screen.blit(label, label.get_rect(center=rect.center))
                else:
                    dark = int(25 * reveal_t)
                    pygame.draw.rect(screen, (dark, dark, dark + 5), rect)
                    if reveal_t > 0.5:
                        label = self.cell_font.render("Empty", True, (50, 52, 60))
                        screen.blit(label, label.get_rect(center=rect.center))

            elif cell.state == CellState.EXTRACTING:
                color = cell.config.color if cell.config else (100, 100, 100)
                pygame.draw.rect(screen, color, rect)
                # Progress bar with glow
                bar_y = rect.bottom - 14
                bar_rect = pygame.Rect(x + 4, bar_y, w - 8, 10)
                pygame.draw.rect(screen, (30, 30, 30), bar_rect)
                fill_w = int((w - 8) * cell.extract_progress)
                pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, (x + 4, bar_y, fill_w, 10))
                # Bright leading edge
                if fill_w > 2:
                    pygame.draw.rect(screen, (200, 240, 255), (x + 4 + fill_w - 2, bar_y, 2, 10))
                label = self.cell_font.render("Extracting...", True, Colors.TEXT)
                screen.blit(label, label.get_rect(center=(rect.centerx, rect.centery - 8)))

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
        pygame.draw.rect(screen, (30, 30, 40), (panel_x, y, bar_w, bar_h))
        fill_w = int(bar_w * charge_pct)
        pygame.draw.rect(screen, Colors.BLUE, (panel_x, y, fill_w, bar_h))
        pygame.draw.rect(screen, Colors.TEXT_SECONDARY, (panel_x, y, bar_w, bar_h), 1)

        regen = self.small_font.render(
            f"Regen: 1 per {self.session.charge_regen_rate:.1f}s", True, Colors.TEXT_SECONDARY
        )
        screen.blit(regen, (panel_x, y + bar_h + 4))

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
