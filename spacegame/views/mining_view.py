"""
Mining mini-game view.

Click-to-mine asteroid field with drone automation, passive drilling,
procedural rock shapes, particle effects, and progression integration.
"""

import pygame
import pygame_gui
import math
import random
from typing import Optional, Dict, List
from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.player import Player
from spacegame.models.commodity import Commodity
from spacegame.models.mining import (
    MiningSession,
    MiningConfig,
    MiningResult,
    AsteroidRock,
    RockType,
    ROCK_TYPE_CONFIGS,
)
from spacegame.models.drone import MiningDroneFleet
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import (
    ParticlePool,
    SPARK_BURST,
    MINING_DUST,
    COLLECT_SPARKLE,
    CLICK_HIT,
    DRONE_SPARK,
)


class MiningView(BaseView):
    """Asteroid mining mini-game with click-to-mine and drone automation."""

    CELL_SIZE = 80
    CELL_PADDING = 4
    GRID_OFFSET_X = 60
    GRID_OFFSET_Y = 120

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        commodities: Dict[str, Commodity],
        mining_config: Optional[MiningConfig] = None,
        progression=None,
        drone_fleet: Optional[MiningDroneFleet] = None,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.commodities = commodities
        self.progression = progression
        self.drone_fleet = drone_fleet or player.drone_fleet

        if mining_config is None:
            mining_config = MiningConfig(system_id=player.current_system_id)
        self.mining_config = mining_config

        self.session: Optional[MiningSession] = None
        self.next_state: Optional[GameState] = None

        # Fonts
        self.title_font = pygame.font.Font(None, 36)
        self.info_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
        self.cell_font = pygame.font.Font(None, 18)

        # UI buttons
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.regen_button: Optional[pygame_gui.elements.UIButton] = None

        # Visual feedback
        self.feedback_messages: List[dict] = []
        self.message: str = ""
        self.message_timer: float = 0.0

        # Animated background
        self.background = AnimatedBackground("asteroid_field", WINDOW_WIDTH, WINDOW_HEIGHT, seed=50)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(100)

        # Particles (larger pool for click effects + drones)
        self.particles = ParticlePool(500)

        # Rock shake offsets (per rock, increases near break)
        self._rock_shakes: Dict[tuple, tuple] = {}

        # White flash overlay for rock break
        self._flash_alpha = 0.0

        # Procedural rock shapes (cached per-cell)
        self._rock_shapes: Dict[tuple, list] = {}

    def _generate_rock_shape(self, gx: int, gy: int, w: int, h: int) -> list:
        """Generate irregular polygon points for a rock shape."""
        key = (gx, gy)
        if key in self._rock_shapes:
            return self._rock_shapes[key]

        rng = random.Random(hash(key) + 42)
        cx, cy = w // 2, h // 2
        points = []
        num_vertices = rng.randint(6, 10)
        for i in range(num_vertices):
            angle = (2 * math.pi * i / num_vertices) + rng.uniform(-0.3, 0.3)
            r = min(w, h) // 2 - 2
            r_var = r * rng.uniform(0.7, 1.0)
            px = cx + int(math.cos(angle) * r_var)
            py = cy + int(math.sin(angle) * r_var)
            points.append((px, py))

        self._rock_shapes[key] = points
        return points

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered mining mini-game")

        # Pull bonuses from progression
        click_power_bonus = 0.0
        passive_drill_bonus = 0.0
        drone_speed_bonus = 0.0
        rare_chance_bonus = 0.0

        if self.progression:
            click_power_bonus = self.progression.get_bonus("click_drill_power")
            passive_drill_bonus = self.progression.get_bonus("passive_drill_speed")
            drone_speed_bonus = self.progression.get_bonus("drone_mining_speed")
            rare_chance_bonus = self.progression.get_bonus("mining_rare_chance")

        # Get active drones
        active_drones = self.drone_fleet.get_active_drones() if self.drone_fleet else []

        self.session = MiningSession(
            self.mining_config,
            click_power_bonus=click_power_bonus,
            passive_drill_bonus=passive_drill_bonus,
            drone_speed_bonus=drone_speed_bonus,
            rare_chance_bonus=rare_chance_bonus,
            drones=active_drones,
        )
        self._rock_shapes.clear()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20, WINDOW_HEIGHT - 60, 150, 40),
            text="Stop Mining",
            manager=self.ui_manager,
        )
        self.regen_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(180, WINDOW_HEIGHT - 60, 180, 40),
            text="Regenerate Field",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        if self.back_button:
            self.back_button.kill()
        if self.regen_button:
            self.regen_button.kill()

    def _get_grid_cell(self, mouse_pos: tuple) -> Optional[tuple]:
        mx, my = mouse_pos
        gx = (mx - self.GRID_OFFSET_X) // self.CELL_SIZE
        gy = (my - self.GRID_OFFSET_Y) // self.CELL_SIZE
        if (
            self.session
            and 0 <= gx < self.mining_config.grid_width
            and 0 <= gy < self.mining_config.grid_height
        ):
            return (gx, gy)
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._get_grid_cell(event.pos)
            if cell:
                self._click_rock(cell[0], cell[1])

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                if self.session and self.progression:
                    total = sum(self.session.total_mined.values())
                    if total > 0:
                        from spacegame.config import XP_PER_MINING

                        xp = total * XP_PER_MINING
                        msgs = self.progression.add_xp(xp)
                        for m in msgs:
                            logger.info(m)
                self.next_state = GameState.TRADING
            elif event.ui_element == self.regen_button:
                if self.session:
                    self.session.regenerate_field()
                    self._rock_shapes.clear()
                    self._show_message("Asteroid field regenerated!")

    def _click_rock(self, gx: int, gy: int) -> None:
        if not self.session:
            return

        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        if self.player.ship.get_available_cargo(commodity_volumes) <= 0:
            self._show_message("Cargo hold full!")
            return

        success, msg, result = self.session.click_rock(gx, gy)

        if success:
            # Click hit particles at rock position
            fx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
            fy = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_SIZE // 2
            self.particles.emit(fx, fy, CLICK_HIT)

            if result:
                self._handle_mine_result(result, gx, gy)
        else:
            self._show_message(msg)

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 2.0

    def _add_feedback(self, text: str, x: int, y: int, color=Colors.SUCCESS) -> None:
        self.feedback_messages.append({"text": text, "x": x, "y": y, "timer": 1.0, "color": color})

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)

        if self.message_timer > 0:
            self.message_timer -= dt

        for fb in self.feedback_messages:
            fb["timer"] -= dt
            fb["y"] -= 30 * dt
        self.feedback_messages = [fb for fb in self.feedback_messages if fb["timer"] > 0]

        # Flash decay
        if self._flash_alpha > 0:
            self._flash_alpha = max(0, self._flash_alpha - 600 * dt)

        if self.session:
            # Emit spark particles for actively drilling rocks (player)
            if self.session.active_rock and self.session.active_rock.drilling:
                rock = self.session.active_rock
                fx = self.GRID_OFFSET_X + rock.grid_x * self.CELL_SIZE + self.CELL_SIZE // 2
                fy = self.GRID_OFFSET_Y + rock.grid_y * self.CELL_SIZE + self.CELL_SIZE // 2
                if random.random() < 0.2:
                    self.particles.emit(fx, fy, SPARK_BURST)

                # Rock shake (increases with progress)
                shake_intensity = rock.drill_progress * 2.0
                self._rock_shakes[(rock.grid_x, rock.grid_y)] = (
                    random.uniform(-shake_intensity, shake_intensity),
                    random.uniform(-shake_intensity, shake_intensity),
                )

            # Drone spark particles on drone targets
            for idx, target in self.session.drone_targets.items():
                if target and not target.depleted:
                    fx = self.GRID_OFFSET_X + target.grid_x * self.CELL_SIZE + self.CELL_SIZE // 2
                    fy = self.GRID_OFFSET_Y + target.grid_y * self.CELL_SIZE + self.CELL_SIZE // 2
                    if random.random() < 0.10:
                        self.particles.emit(fx, fy, DRONE_SPARK)
                    # Lighter shake for drone-mined rocks
                    shake_intensity = target.drill_progress * 1.0
                    self._rock_shakes[(target.grid_x, target.grid_y)] = (
                        random.uniform(-shake_intensity, shake_intensity),
                        random.uniform(-shake_intensity, shake_intensity),
                    )

            results = self.session.update(dt)
            for result in results:
                self._handle_mine_result_from_update(result)

    def _handle_mine_result(self, result: MiningResult, gx: int, gy: int) -> None:
        """Handle a mining result from a player click that broke a rock."""
        self.player.ship.add_cargo(result.commodity_id, result.quantity, price_per_unit=0)
        self.player.ore_mined += result.quantity

        commodity = self.commodities.get(result.commodity_id)
        name = commodity.name if commodity else result.commodity_id

        fx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
        fy = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_SIZE // 2

        self.particles.emit(fx, fy, MINING_DUST)
        self.particles.emit(fx, fy, COLLECT_SPARKLE)
        self._flash_alpha = 80.0
        self._rock_shakes.pop((gx, gy), None)

        self._add_feedback(f"+{result.quantity} {name}", fx, fy)
        logger.debug(f"Mined {result.quantity} {name}")

    def _handle_mine_result_from_update(self, result: MiningResult) -> None:
        """Handle a mining result from update() (passive drill or drone)."""
        self.player.ship.add_cargo(result.commodity_id, result.quantity, price_per_unit=0)
        self.player.ore_mined += result.quantity

        commodity = self.commodities.get(result.commodity_id)
        name = commodity.name if commodity else result.commodity_id

        # Find the rock that just broke for positioning
        fx, fy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        if self.session:
            for r in self.session.rocks:
                if r.depleted and r.commodity_id == result.commodity_id:
                    fx = self.GRID_OFFSET_X + r.grid_x * self.CELL_SIZE + self.CELL_SIZE // 2
                    fy = self.GRID_OFFSET_Y + r.grid_y * self.CELL_SIZE + self.CELL_SIZE // 2
                    self._rock_shakes.pop((r.grid_x, r.grid_y), None)
                    break

        self.particles.emit(fx, fy, MINING_DUST)
        self.particles.emit(fx, fy, COLLECT_SPARKLE)
        self._flash_alpha = 60.0

        self._add_feedback(f"+{result.quantity} {name}", fx, fy)
        logger.debug(f"Mined {result.quantity} {name} (auto)")

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title = self.title_font.render("ASTEROID MINING", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 30))
        screen.blit(title, title_rect)

        if not self.session:
            return

        # Instructions
        instr = self.small_font.render(
            "Click rocks to mine! Drones mine automatically.", True, Colors.TEXT_SECONDARY
        )
        screen.blit(instr, (self.GRID_OFFSET_X, 55))

        # Draw grid
        self._render_grid(screen)

        # Draw stats panel
        self._render_stats(screen)

        # Draw drone panel
        self._render_drone_panel(screen)

        # Particles on top
        self.particles.render(screen)

        # White flash overlay
        if self._flash_alpha > 0:
            flash = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            flash.fill((255, 255, 255))
            flash.set_alpha(int(self._flash_alpha))
            screen.blit(flash, (0, 0))

        # Feedback messages
        for fb in self.feedback_messages:
            surf = self.info_font.render(fb["text"], True, fb["color"])
            screen.blit(surf, (int(fb["x"]) - surf.get_width() // 2, int(fb["y"])))

        # Status message
        if self.message_timer > 0:
            msg_surf = self.info_font.render(self.message, True, Colors.YELLOW)
            msg_rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 90))
            screen.blit(msg_surf, msg_rect)

    def _render_grid(self, screen: pygame.Surface) -> None:
        mouse_pos = pygame.mouse.get_pos()
        hover_cell = self._get_grid_cell(mouse_pos)

        # Build set of drone target rock positions for indicator rendering
        drone_target_positions = set()
        if self.session:
            for idx, target in self.session.drone_targets.items():
                if target and not target.depleted:
                    drone_target_positions.add((target.grid_x, target.grid_y))

        for rock in self.session.rocks:
            x = self.GRID_OFFSET_X + rock.grid_x * self.CELL_SIZE + self.CELL_PADDING
            y = self.GRID_OFFSET_Y + rock.grid_y * self.CELL_SIZE + self.CELL_PADDING
            w = self.CELL_SIZE - self.CELL_PADDING * 2
            h = self.CELL_SIZE - self.CELL_PADDING * 2

            # Apply rock shake offset
            shake = self._rock_shakes.get((rock.grid_x, rock.grid_y), (0, 0))
            sx = x + int(shake[0])
            sy = y + int(shake[1])

            rect = pygame.Rect(sx, sy, w, h)

            if rock.depleted:
                # Empty cell with subtle border
                pygame.draw.rect(screen, (20, 22, 30), rect)
                pygame.draw.rect(screen, (35, 38, 48), rect, 1)
                label = self.cell_font.render("empty", True, (50, 52, 60))
                screen.blit(label, label.get_rect(center=rect.center))
            else:
                # Procedural rock shape
                color = rock.config.color
                rock_points = self._generate_rock_shape(rock.grid_x, rock.grid_y, w, h)
                # Offset points to screen position
                offset_points = [(p[0] + sx, p[1] + sy) for p in rock_points]
                pygame.draw.polygon(screen, color, offset_points)

                # Crack lines (darker version of rock color)
                dark_color = (max(0, color[0] - 40), max(0, color[1] - 40), max(0, color[2] - 40))
                rng = random.Random(hash((rock.grid_x, rock.grid_y)))
                for _ in range(2):
                    i1 = rng.randint(0, len(offset_points) - 1)
                    cx, cy = rect.centerx + rng.randint(-5, 5), rect.centery + rng.randint(-5, 5)
                    pygame.draw.line(screen, dark_color, offset_points[i1], (cx, cy), 1)

                # Hover highlight
                if hover_cell and hover_cell[0] == rock.grid_x and hover_cell[1] == rock.grid_y:
                    pygame.draw.polygon(screen, Colors.TEXT_HIGHLIGHT, offset_points, 2)
                else:
                    pygame.draw.polygon(screen, (180, 180, 180), offset_points, 1)

                # Rock type label
                label = self.cell_font.render(rock.rock_type.value.upper(), True, Colors.TEXT)
                screen.blit(label, label.get_rect(center=(rect.centerx, rect.centery - 8)))

                # Drill progress bar (shown when drilling via click or drone)
                if rock.drilling or rock.drill_progress > 0:
                    bar_y = rect.bottom - 12
                    bar_rect = pygame.Rect(sx + 4, bar_y, w - 8, 8)
                    pygame.draw.rect(screen, (40, 40, 40), bar_rect)
                    fill_width = int((w - 8) * rock.drill_progress)
                    # Orange for player, blue for drone
                    is_drone_target = (rock.grid_x, rock.grid_y) in drone_target_positions
                    bar_color = (80, 160, 255) if is_drone_target else Colors.TEXT_HIGHLIGHT
                    fill_rect = pygame.Rect(sx + 4, bar_y, fill_width, 8)
                    pygame.draw.rect(screen, bar_color, fill_rect)
                    if fill_width > 2:
                        pygame.draw.rect(
                            screen, (200, 240, 255), (sx + 4 + fill_width - 2, bar_y, 2, 8)
                        )
                else:
                    hard_text = self.cell_font.render(
                        f"{rock.hardness:.1f}s", True, Colors.TEXT_SECONDARY
                    )
                    screen.blit(
                        hard_text, hard_text.get_rect(center=(rect.centerx, rect.centery + 10))
                    )

                # Drone indicator dot (blue dot top-right corner)
                if (rock.grid_x, rock.grid_y) in drone_target_positions:
                    dot_x = rect.right - 8
                    dot_y = rect.top + 8
                    pygame.draw.circle(screen, (80, 160, 255), (dot_x, dot_y), 4)
                    pygame.draw.circle(screen, (120, 200, 255), (dot_x, dot_y), 4, 1)

    def _render_drone_panel(self, screen: pygame.Surface) -> None:
        """Render drone status panel on the right side."""
        panel_x = WINDOW_WIDTH - 280
        panel_y = 120

        # Header
        header = self.info_font.render("DRONES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (panel_x, panel_y))

        y = panel_y + 28
        active_drones = self.session.drones if self.session else []

        if not active_drones:
            no_drones = self.small_font.render("No drones active", True, Colors.TEXT_SECONDARY)
            screen.blit(no_drones, (panel_x, y))
            hint = self.small_font.render("Unlock via Mining skill tree", True, (80, 80, 100))
            screen.blit(hint, (panel_x, y + 18))
            return

        tier_colors = {
            1: (120, 120, 120),  # Basic - gray
            2: (80, 160, 255),  # Advanced - blue
            3: (255, 180, 60),  # Elite - gold
        }
        tier_names = {1: "Basic", 2: "Advanced", 3: "Elite"}

        for i, drone in enumerate(active_drones):
            tier_val = drone.tier.value
            color = tier_colors.get(tier_val, (120, 120, 120))

            # Tier colored circle
            pygame.draw.circle(screen, color, (panel_x + 8, y + 8), 6)
            pygame.draw.circle(screen, (200, 200, 200), (panel_x + 8, y + 8), 6, 1)

            # Drone label
            label = f"T{tier_val} {tier_names.get(tier_val, '???')}"
            label_surf = self.small_font.render(label, True, Colors.TEXT)
            screen.blit(label_surf, (panel_x + 20, y))

            # Status: current target or idle
            target = self.session.drone_targets.get(i) if self.session else None
            if target and not target.depleted:
                status = f"Mining {target.rock_type.value}"
                status_color = Colors.TEXT_SECONDARY
            else:
                status = "Idle"
                status_color = (80, 80, 100)

            status_surf = self.small_font.render(status, True, status_color)
            screen.blit(status_surf, (panel_x + 20, y + 16))

            # Preference indicator
            if drone.target_preference:
                pref = self.small_font.render(
                    f"Pref: {drone.target_preference.value}", True, (100, 160, 100)
                )
                screen.blit(pref, (panel_x + 140, y + 8))

            y += 38

    def _render_stats(self, screen: pygame.Surface) -> None:
        panel_x = WINDOW_WIDTH - 280
        # Position below drone panel
        active_drones = self.session.drones if self.session else []
        drone_panel_height = max(65, 28 + len(active_drones) * 38 + 15)
        panel_y = 120 + drone_panel_height

        header = self.info_font.render("SESSION STATS", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (panel_x, panel_y))

        y = panel_y + 30
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}

        stats = [
            f"Clicks: {self.session.total_clicks}",
            f"Rocks remaining: {self.session.get_undepleted_count()}/{self.session.get_total_rocks()}",
            f"Cargo: {self.player.ship.get_used_cargo(commodity_volumes)}/{self.player.ship.max_cargo}",
        ]

        if self.session.total_mined:
            stats.append("")
            stats.append("Mined this session:")
            for cid, qty in self.session.total_mined.items():
                commodity = self.commodities.get(cid)
                name = commodity.name if commodity else cid
                stats.append(f"  {name}: {qty}")

        for line in stats:
            surf = self.small_font.render(line, True, Colors.TEXT)
            screen.blit(surf, (panel_x, y))
            y += 22

        # Rock type legend
        y += 15
        legend = self.info_font.render("ROCK TYPES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(legend, (panel_x, y))
        y += 25

        for rt, cfg in ROCK_TYPE_CONFIGS.items():
            pygame.draw.rect(screen, cfg.color, (panel_x, y + 2, 14, 14))
            pygame.draw.rect(screen, Colors.TEXT_SECONDARY, (panel_x, y + 2, 14, 14), 1)
            commodity = self.commodities.get(cfg.commodity_id)
            name = commodity.name if commodity else cfg.commodity_id
            text = f"{rt.value.title()}: {cfg.hardness}s -> {name}"
            surf = self.small_font.render(text, True, Colors.TEXT_SECONDARY)
            screen.blit(surf, (panel_x + 20, y))
            y += 20

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
