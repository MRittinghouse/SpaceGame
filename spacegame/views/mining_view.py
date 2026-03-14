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
from spacegame.models.rating import calculate_rating, MINING_THRESHOLDS, RATING_COLORS
from spacegame.engine.draw_utils import draw_bar, draw_summary_overlay
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import (
    ParticlePool,
    SPARK_BURST,
    MINING_DUST,
    COLLECT_SPARKLE,
    CLICK_HIT,
    DRONE_SPARK,
    MINING_CHAIN,
    ENERGY_REGEN,
)
from spacegame.engine.sprites import get_sprite_manager
from spacegame.engine.fonts import FontCache
from spacegame.engine.audio_manager import get_audio_manager


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
        self.title_font = FontCache.get(36)
        self.info_font = FontCache.get(24)
        self.small_font = FontCache.get(20)
        self.cell_font = FontCache.get(18)

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

        # Procedural rock shapes (cached per-cell, used as fallback)
        self._rock_shapes: Dict[tuple, list] = {}

        # Ore icon sprites (commodity_id -> Surface at 3x scale = 48x48)
        self._sprite_mgr = get_sprite_manager()
        self._ore_icons: Dict[str, Optional[pygame.Surface]] = {}
        for cfg in ROCK_TYPE_CONFIGS.values():
            self._ore_icons[cfg.commodity_id] = self._sprite_mgr.get_commodity_icon(
                cfg.commodity_id, scale=3
            )

        # Session summary overlay
        self._show_summary: bool = False
        self._summary_xp: int = 0
        self._session_elapsed: float = 0.0
        self._session_rating: str = "D"
        self._summary_font = FontCache.get(32)
        self._summary_title_font = FontCache.get(44)
        self._rating_font = FontCache.get(72)

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

        chain_chance_bonus = 0.0

        if self.progression:
            click_power_bonus = self.progression.get_bonus("click_drill_power")
            passive_drill_bonus = self.progression.get_bonus("passive_drill_speed")
            drone_speed_bonus = self.progression.get_bonus("drone_mining_speed")
            rare_chance_bonus = self.progression.get_bonus("mining_rare_chance")
            rare_chance_bonus += self.progression.get_bonus("rare_ore_chance")
            chain_chance_bonus = self.progression.get_bonus("chain_chance")

        # Get active drones
        active_drones = self.drone_fleet.get_active_drones() if self.drone_fleet else []

        self.session = MiningSession(
            self.mining_config,
            click_power_bonus=click_power_bonus,
            passive_drill_bonus=passive_drill_bonus,
            drone_speed_bonus=drone_speed_bonus,
            rare_chance_bonus=rare_chance_bonus,
            chain_chance_bonus=chain_chance_bonus,
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
        # Summary dismiss: click or key
        if self._show_summary:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.next_state = GameState.TRADING
            elif event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE,
            ):
                self.next_state = GameState.TRADING
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            cell = self._get_grid_cell(event.pos)
            if cell:
                empowered = event.button == 3  # Right-click = empowered
                self._click_rock(cell[0], cell[1], empowered=empowered)

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                xp = 0
                if self.session and self.progression:
                    total = sum(self.session.total_mined.values())
                    if total > 0:
                        from spacegame.config import XP_PER_MINING

                        xp = total * XP_PER_MINING
                        msgs = self.progression.add_xp(xp)
                        for m in msgs:
                            logger.info(m)
                self._summary_xp = xp
                self._calculate_rating()
                self._show_summary = True
                self._destroy_ui()
            elif event.ui_element == self.regen_button:
                if self.session:
                    self.session.regenerate_field()
                    self.player.max_mining_depth = max(
                        self.player.max_mining_depth, self.session.depth
                    )
                    self._rock_shapes.clear()
                    self._show_message("Asteroid field regenerated!")

    def _click_rock(self, gx: int, gy: int, empowered: bool = False) -> None:
        if not self.session:
            return

        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        if self.player.ship.get_available_cargo(commodity_volumes) <= 0:
            self._show_message("Cargo hold full!")
            return

        success, msg, result = self.session.click_rock(gx, gy, empowered=empowered)

        if success:
            # Click hit particles at rock position
            fx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
            fy = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_SIZE // 2
            self.particles.emit(fx, fy, CLICK_HIT)
            get_audio_manager().play_sfx("mine_click")

            if result:
                self._handle_mine_result(result, gx, gy)
            self._process_chain_results()
            self._process_milestones()
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
        if not self._show_summary:
            self._session_elapsed += dt

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

            prev_energy = self.session.energy
            commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
            cargo_full = self.player.ship.get_available_cargo(commodity_volumes) <= 0
            results = self.session.update(dt, cargo_full=cargo_full)
            if self.session.energy > prev_energy:
                bar_x = self.GRID_OFFSET_X + 100
                bar_y = self.GRID_OFFSET_Y + self.mining_config.grid_height * self.CELL_SIZE + 25
                self.particles.emit(bar_x, bar_y, ENERGY_REGEN)
                get_audio_manager().play_sfx("mine_energy")
            for result in results:
                self._handle_mine_result_from_update(result)
            self._process_chain_results()
            self._process_milestones()

    def _handle_mine_result(self, result: MiningResult, gx: int, gy: int) -> None:
        """Handle a mining result from a player click that broke a rock."""
        self.player.ship.add_cargo(result.commodity_id, result.quantity, price_per_unit=0)
        self.player.ore_mined += result.quantity
        if result.commodity_id == "rare_ore":
            self.player.rare_ores_mined += result.quantity

        commodity = self.commodities.get(result.commodity_id)
        name = commodity.name if commodity else result.commodity_id

        fx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
        fy = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_SIZE // 2

        self.particles.emit(fx, fy, MINING_DUST)
        self.particles.emit(fx, fy, COLLECT_SPARKLE)
        self._flash_alpha = 80.0
        self._rock_shakes.pop((gx, gy), None)
        get_audio_manager().play_sfx("mine_break")
        get_audio_manager().play_sfx("mine_collect")

        self._add_feedback(f"+{result.quantity} {name}", fx, fy)
        logger.debug(f"Mined {result.quantity} {name}")

    def _process_chain_results(self) -> None:
        """Handle chain-broken rocks: add cargo, emit particles, show feedback."""
        if not self.session:
            return
        self.player.total_chains_triggered += len(self.session.chain_results)
        for chain in self.session.chain_results:
            self.player.ship.add_cargo(chain.commodity_id, chain.quantity, price_per_unit=0)
            self.player.ore_mined += chain.quantity
            if chain.commodity_id == "rare_ore":
                self.player.rare_ores_mined += chain.quantity
            fx = self.GRID_OFFSET_X + chain.grid_x * self.CELL_SIZE + self.CELL_SIZE // 2
            fy = self.GRID_OFFSET_Y + chain.grid_y * self.CELL_SIZE + self.CELL_SIZE // 2
            self.particles.emit(fx, fy, MINING_CHAIN)
            get_audio_manager().play_sfx("mine_chain")
            commodity = self.commodities.get(chain.commodity_id)
            name = commodity.name if commodity else chain.commodity_id
            self._add_feedback(f"+{chain.quantity} {name}", fx, fy, Colors.YELLOW)
            self._rock_shakes.pop((chain.grid_x, chain.grid_y), None)

    def _process_milestones(self) -> None:
        """Apply rewards for newly completed milestones."""
        if not self.session:
            return
        for ms in self.session.newly_completed_milestones:
            if ms.reward_xp > 0 and self.progression:
                msgs = self.progression.add_xp(ms.reward_xp)
                for m in msgs:
                    logger.info(m)
                self._add_feedback(f"+{ms.reward_xp} XP", WINDOW_WIDTH - 200, 80, Colors.BLUE)
            if ms.reward_credits > 0:
                self.player.credits += ms.reward_credits
                self._add_feedback(
                    f"+{ms.reward_credits} CR", WINDOW_WIDTH - 200, 100, Colors.GREEN
                )
            logger.info(f"Mining milestone complete: {ms.description}")

    def _handle_mine_result_from_update(self, result: MiningResult) -> None:
        """Handle a mining result from update() (passive drill or drone)."""
        self.player.ship.add_cargo(result.commodity_id, result.quantity, price_per_unit=0)
        self.player.ore_mined += result.quantity
        if result.commodity_id == "rare_ore":
            self.player.rare_ores_mined += result.quantity

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
        get_audio_manager().play_sfx("mine_break")
        get_audio_manager().play_sfx("mine_collect")

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
            "Left-click: mine  |  Right-click: empowered (3x, uses energy)  |  Drones mine automatically",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(instr, (self.GRID_OFFSET_X, 55))

        # Draw grid
        self._render_grid(screen)

        # Draw energy bar below grid
        self._render_energy_bar(screen)

        # Draw stats panel
        self._render_stats(screen)

        # Draw drone panel
        self._render_drone_panel(screen)

        # Draw milestone panel
        self._render_milestones(screen)

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

        # Summary overlay (drawn last, on top of everything)
        if self._show_summary:
            self._render_summary(screen)

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
                color = rock.config.color
                icon = self._ore_icons.get(rock.config.commodity_id)

                if icon is not None:
                    # Tinted cell background (rock color, dimmed)
                    bg_color = (color[0] // 4, color[1] // 4, color[2] // 4)
                    pygame.draw.rect(screen, bg_color, rect)

                    # Ore icon in upper portion of cell
                    icon_x = rect.centerx - icon.get_width() // 2
                    icon_y = rect.top + 4
                    screen.blit(icon, (icon_x, icon_y))

                    # Hover / normal border
                    if hover_cell and hover_cell[0] == rock.grid_x and hover_cell[1] == rock.grid_y:
                        pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, rect, 2)
                    else:
                        border_color = (color[0] // 2, color[1] // 2, color[2] // 2)
                        pygame.draw.rect(screen, border_color, rect, 1)
                else:
                    # Fallback: procedural polygon (no sprite available)
                    rock_points = self._generate_rock_shape(rock.grid_x, rock.grid_y, w, h)
                    offset_points = [(p[0] + sx, p[1] + sy) for p in rock_points]
                    pygame.draw.polygon(screen, color, offset_points)
                    if hover_cell and hover_cell[0] == rock.grid_x and hover_cell[1] == rock.grid_y:
                        pygame.draw.polygon(screen, Colors.TEXT_HIGHLIGHT, offset_points, 2)
                    else:
                        pygame.draw.polygon(screen, (180, 180, 180), offset_points, 1)

                # Rock type label (below icon, above hardness/bar)
                label = self.cell_font.render(rock.rock_type.value.upper(), True, Colors.TEXT)
                label_y = rect.top + 52 if icon is not None else rect.centery - 6
                screen.blit(label, label.get_rect(center=(rect.centerx, label_y)))

                # Drill progress bar (shown when drilling via click or drone)
                if rock.drilling or rock.drill_progress > 0:
                    bar_y = rect.bottom - 12
                    # Orange for player, blue for drone
                    is_drone_target = (rock.grid_x, rock.grid_y) in drone_target_positions
                    bar_color = (80, 160, 255) if is_drone_target else Colors.TEXT_HIGHLIGHT
                    draw_bar(
                        screen,
                        sx + 4,
                        bar_y,
                        w - 8,
                        8,
                        rock.drill_progress * 100,
                        100,
                        bar_color,
                        show_value=False,
                    )
                else:
                    hard_text = self.cell_font.render(
                        f"{rock.hardness:.1f}s", True, Colors.TEXT_SECONDARY
                    )
                    screen.blit(
                        hard_text, hard_text.get_rect(center=(rect.centerx, rect.bottom - 10))
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

        max_legend_y = WINDOW_HEIGHT - 80  # Leave room for buttons
        for rt, cfg in ROCK_TYPE_CONFIGS.items():
            if y >= max_legend_y:
                break
            pygame.draw.rect(screen, cfg.color, (panel_x, y + 2, 14, 14))
            pygame.draw.rect(screen, Colors.TEXT_SECONDARY, (panel_x, y + 2, 14, 14), 1)
            commodity = self.commodities.get(cfg.commodity_id)
            name = commodity.name if commodity else cfg.commodity_id
            text = f"{rt.value.title()}: {cfg.hardness}s -> {name}"
            surf = self.small_font.render(text, True, Colors.TEXT_SECONDARY)
            screen.blit(surf, (panel_x + 20, y))
            y += 20

    def _render_energy_bar(self, screen: pygame.Surface) -> None:
        """Render energy bar below the mining grid."""
        if not self.session:
            return
        bar_y = self.GRID_OFFSET_Y + self.mining_config.grid_height * self.CELL_SIZE + 10
        bar_width = self.mining_config.grid_width * self.CELL_SIZE
        bar_height = 20
        bar_x = self.GRID_OFFSET_X

        # Dynamic color based on energy ratio
        ratio = self.session.energy / max(1, self.session.max_energy)
        if ratio > 0.5:
            bar_color = Colors.BLUE
        elif ratio > 0.25:
            bar_color = Colors.YELLOW
        else:
            bar_color = Colors.RED
        draw_bar(
            screen, bar_x, bar_y, bar_width, bar_height,
            self.session.energy, self.session.max_energy, bar_color,
            show_value=False,
        )

        # Custom text with empowered click cost info
        cost = self.session.get_click_energy_cost()
        label = f"ENERGY: {self.session.energy}/{self.session.max_energy}  |  R-click: 3x ({cost} energy)"
        surf = self.small_font.render(label, True, Colors.TEXT)
        # Clip label to bar width
        if surf.get_width() > bar_width - 16:
            # Fall back to shorter label
            label = f"ENERGY: {self.session.energy}/{self.session.max_energy}"
            surf = self.small_font.render(label, True, Colors.TEXT)
        screen.blit(surf, (bar_x + 8, bar_y + 2))

        # Depth indicator right of energy bar
        depth_label = f"DEPTH {self.session.depth}"
        depth_intensity = min(255, 150 + self.session.depth * 10)
        depth_color = (depth_intensity, depth_intensity, 255)
        depth_surf = self.info_font.render(depth_label, True, depth_color)
        screen.blit(depth_surf, (bar_x + bar_width + 20, bar_y))

    def _render_milestones(self, screen: pygame.Surface) -> None:
        """Render milestone progress panel."""
        if not self.session or not self.session.milestones:
            return

        panel_x = self.GRID_OFFSET_X
        panel_y = (
            self.GRID_OFFSET_Y
            + self.mining_config.grid_height * self.CELL_SIZE
            + 40
        )

        header = self.small_font.render("MILESTONES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (panel_x, panel_y))
        y = panel_y + 20

        for ms in self.session.milestones:
            value = self.session._get_milestone_value(ms.category)
            progress = min(1.0, value / max(1, ms.threshold))

            # Checkmark or progress
            if ms.completed:
                mark = self.small_font.render("[DONE]", True, Colors.GREEN)
            else:
                mark = self.small_font.render(
                    f"[{value}/{ms.threshold}]", True, Colors.TEXT_SECONDARY
                )
            screen.blit(mark, (panel_x, y))

            # Description
            desc_surf = self.small_font.render(ms.description, True, Colors.TEXT)
            screen.blit(desc_surf, (panel_x + 80, y))

            # Small progress bar
            bar_x = panel_x + 80
            bar_y_pos = y + 16
            bar_w = 150
            bar_h = 4
            color = Colors.GREEN if ms.completed else Colors.BLUE
            draw_bar(
                screen, bar_x, bar_y_pos, bar_w, bar_h,
                value, ms.threshold, color,
                show_value=False, bg_color=Colors.BAR_BG_LIGHT,
            )

            y += 28

    def _calculate_rating(self) -> None:
        """Calculate session performance rating."""
        if self.session and self._session_elapsed > 0:
            total_ore = sum(self.session.total_mined.values())
            ore_per_min = total_ore / (self._session_elapsed / 60.0)
            self._session_rating = calculate_rating(ore_per_min, MINING_THRESHOLDS)
            if self._session_rating == "S":
                self.player.s_ranks_earned += 1
        else:
            self._session_rating = "D"

    def _render_summary(self, screen: pygame.Surface) -> None:
        """Render session summary overlay."""
        stats: list[tuple[str, str]] = []
        if self.session:
            total_ore = sum(self.session.total_mined.values())
            completed = sum(1 for ms in self.session.milestones if ms.completed)
            stats = [
                ("Rocks Mined", str(self.session.rocks_broken)),
                ("Total Ore", str(total_ore)),
                ("Rare Ores", str(self.session.rare_ores_found)),
                ("Max Depth", str(self.session.depth)),
                ("Chains Triggered", str(self.session.total_chains)),
                ("Milestones", f"{completed} / {len(self.session.milestones)}"),
            ]
        draw_summary_overlay(
            screen,
            title="MINING COMPLETE",
            stats=stats,
            xp_earned=self._summary_xp,
            rating_letter=self._session_rating,
            rating_color=RATING_COLORS.get(self._session_rating, Colors.TEXT_SECONDARY),
        )

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
