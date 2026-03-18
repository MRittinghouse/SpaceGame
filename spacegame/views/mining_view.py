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
    HazardType,
    ROCK_TYPE_CONFIGS,
)
from spacegame.models.drone import MiningDroneFleet
from spacegame.models.ore_silo import OreSilo
from spacegame.models.rating import calculate_rating, MINING_THRESHOLDS, RATING_COLORS
from spacegame.engine.draw_utils import draw_bar, draw_summary_overlay, draw_nine_slice_panel
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import (
    ParticlePool,
    SPARK_BURST,
    COLLECT_SPARKLE,
    CLICK_HIT,
    DRONE_SPARK,
    ENERGY_REGEN,
    ROCK_BREAK,
    CHAIN_SHOCKWAVE,
    EMPOWERED_BURST,
    DEPTH_TRANSITION,
)
from spacegame.engine.sprites import get_sprite_manager
from spacegame.engine.fonts import FontCache
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.floating_text import FloatingItemManager
from spacegame.engine.tooltip import TooltipState

# System-specific asteroid field descriptions and bonuses
FIELD_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    # system_id -> (field_name, flavor_description)
    "breakstone": (
        "Breakstone Belt",
        "Standard composition. Reliable yields, steady work.",
    ),
    "iron_depths": (
        "Iron Depths Shafts",
        "Rich iron veins run deep. Larger field, faster drilling.",
    ),
    "forgeworks": (
        "Forgeworks Debris Ring",
        "Tight quarters, low energy. Common ore dominates the field.",
    ),
    "verdant": (
        "Verdant Crystal Caves",
        "Crystal formations glitter in the dark. Small field, rich pickings.",
    ),
    "the_fulcrum": (
        "Fulcrum Asteroid Corridor",
        "Military-surveyed field. Balanced composition, above-average yields.",
    ),
}


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

        # Ore silo for this system (decouples mining from ship cargo)
        self._silo: OreSilo = player.ore_silo_manager.get_silo(
            mining_config.system_id if mining_config else player.current_system_id
        )

        # Strata tokens earned this session (for summary)
        self._session_strata: int = 0

        # Fonts
        self.title_font = FontCache.get(36)
        self.info_font = FontCache.get(24)
        self.small_font = FontCache.get(20)
        self.cell_font = FontCache.get(18)

        # UI buttons
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.regen_button: Optional[pygame_gui.elements.UIButton] = None

        # Upgrade panel rects (for click detection, populated in render)
        self._upgrade_rects: Dict[str, pygame.Rect] = {}

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

        # White flash overlay for rock break (pre-allocated)
        self._flash_alpha = 0.0
        self._flash_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._flash_surface.fill((255, 255, 255))

        # Drill leading-edge glow surface (pre-allocated, reused per rock)
        self._drill_glow_surf = pygame.Surface((6, 12), pygame.SRCALPHA)

        # Procedural rock shapes (cached per-cell, used as fallback)
        self._rock_shapes: Dict[tuple, list] = {}

        # Sprite manager
        self._sprite_mgr = get_sprite_manager()

        # Rock type sprites: RockType -> list[Surface] (variants, 32x32 native @ 2x = 64x64)
        self._rock_sprites: Dict[RockType, list[pygame.Surface]] = {}
        self._load_rock_sprites()

        # Hazard sprites: HazardType -> list[Surface]
        self._hazard_sprites: Dict[str, list[pygame.Surface]] = {}
        self._load_hazard_sprites()

        # Drone tier sprites: tier (1-3) -> Surface (16x16 native @ 2x = 32x32)
        self._drone_sprites: Dict[int, Optional[pygame.Surface]] = {}
        for tier in (1, 2, 3):
            self._drone_sprites[tier] = self._sprite_mgr.get_static_sprite(
                "mining", f"drone_tier{tier}", scale=2
            )

        # Ore icon sprites (commodity_id -> Surface at 3x scale = 48x48)
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
        self._transfer_count: int = 0
        self._summary_font = FontCache.get(32)
        self._summary_title_font = FontCache.get(44)
        self._rating_font = FontCache.get(72)

        # Floating icon manager for ore-to-silo animations
        self._floats = FloatingItemManager()

        # Rock hit compress animation: (gx, gy) -> compress_timer (0.0 to 0.15)
        self._rock_compress: Dict[tuple, float] = {}

        # Glow time for pulsing effects
        self._glow_time: float = 0.0

        # Chain cascade pending visual: list of (gx, gy, delay_remaining)
        self._chain_pending: List[list] = []

        # Tooltip for upgrade descriptions
        self._tooltip = TooltipState(delay=0.3, fade_in=0.15)

        # Exit confirmation state
        self._confirm_exit: bool = False

        # Crew commentary (set by Game class after construction)
        self._get_crew_line = lambda action_type: None
        self._crew_comment: str = ""
        self._crew_comment_name: str = ""
        self._crew_comment_timer: float = 0.0

    # RockType -> sprite base ID mapping
    ROCK_SPRITE_MAP: Dict[RockType, str] = {
        RockType.COMMON: "rock_raw_ore",
        RockType.IRON: "rock_iron_ore",
        RockType.CRYSTAL: "rock_crystal_ore",
        RockType.RARE: "rock_rare_ore",
        RockType.DENSE: "rock_common_metals",
        RockType.VOLATILE: "rock_unstable",
    }

    # Number of visual variants per rock type
    ROCK_VARIANT_COUNTS: Dict[RockType, int] = {
        RockType.COMMON: 3,
        RockType.IRON: 3,
        RockType.CRYSTAL: 3,
        RockType.RARE: 3,
        RockType.DENSE: 2,
        RockType.VOLATILE: 2,
    }

    def _load_rock_sprites(self) -> None:
        """Load rock type sprite variants from sprites/mining/."""
        for rock_type, base_id in self.ROCK_SPRITE_MAP.items():
            variants: list[pygame.Surface] = []
            count = self.ROCK_VARIANT_COUNTS.get(rock_type, 1)
            for v in range(1, count + 1):
                sprite_id = f"{base_id}_v{v}"
                surf = self._sprite_mgr.get_static_sprite("mining", sprite_id, scale=2)
                if surf is not None:
                    variants.append(surf)
            # Try base (no variant suffix) as fallback
            if not variants:
                surf = self._sprite_mgr.get_static_sprite("mining", base_id, scale=2)
                if surf is not None:
                    variants.append(surf)
            if variants:
                self._rock_sprites[rock_type] = variants

    def _load_hazard_sprites(self) -> None:
        """Load hazard cell sprite variants from sprites/mining/."""
        # Unstable cells
        unstable_variants: list[pygame.Surface] = []
        for v in (1, 2):
            surf = self._sprite_mgr.get_static_sprite("mining", f"rock_unstable_v{v}", scale=2)
            if surf is not None:
                unstable_variants.append(surf)
        if unstable_variants:
            self._hazard_sprites["unstable"] = unstable_variants

        # Pressure vent cells
        vent_variants: list[pygame.Surface] = []
        for v in (1, 2):
            surf = self._sprite_mgr.get_static_sprite("mining", f"rock_vent_v{v}", scale=2)
            if surf is not None:
                vent_variants.append(surf)
        if vent_variants:
            self._hazard_sprites["vent"] = vent_variants

    def _get_rock_sprite(self, rock_type: RockType, gx: int, gy: int) -> Optional[pygame.Surface]:
        """Get a rock sprite variant seeded by grid position for visual variety.

        Args:
            rock_type: The rock type to get a sprite for.
            gx: Grid x coordinate (used for variant selection).
            gy: Grid y coordinate (used for variant selection).

        Returns:
            A sprite Surface, or None if no sprite is available.
        """
        variants = self._rock_sprites.get(rock_type)
        if not variants:
            return None
        # Deterministic variant selection based on grid position
        variant_index = (gx * 7 + gy * 13 + hash(rock_type)) % len(variants)
        return variants[variant_index]

    def _get_hazard_sprite(
        self, hazard_type: HazardType, gx: int, gy: int
    ) -> Optional[pygame.Surface]:
        """Get a hazard cell sprite variant.

        Args:
            hazard_type: The hazard type.
            gx: Grid x coordinate.
            gy: Grid y coordinate.

        Returns:
            A sprite Surface, or None if no sprite is available.
        """
        key = "unstable" if hazard_type == HazardType.UNSTABLE_CELL else "vent"
        variants = self._hazard_sprites.get(key)
        if not variants:
            return None
        variant_index = (gx * 7 + gy * 13) % len(variants)
        return variants[variant_index]

    def _generate_rock_shape(self, gx: int, gy: int, w: int, h: int) -> list:
        """Generate irregular polygon points for a rock shape (fallback)."""
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

        # Pull bonuses from progression (skill tree)
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

        # Apply ship upgrade bonuses (stacks with skill tree)
        click_power_bonus += self.player.upgrade_manager.get_bonus("drill_speed_bonus")
        rare_chance_bonus += self.player.upgrade_manager.get_bonus("rare_ore_bonus")
        chain_chance_bonus += self.player.upgrade_manager.get_bonus("chain_chance_bonus")

        # Apply Deep Core upgrade bonuses (stacks with skill tree)
        from spacegame.data_loader import get_data_loader

        dc_upgrades = get_data_loader().deep_core_upgrades
        dc_state = self.player.deep_core_upgrades
        click_power_bonus += dc_state.get_effect("core_resonance", dc_upgrades)
        energy_bonus = int(dc_state.get_effect("energy_conduit", dc_upgrades))
        chain_chance_bonus += dc_state.get_effect("seismic_pulse", dc_upgrades)
        drone_speed_bonus += dc_state.get_effect("automaton_core", dc_upgrades)
        starting_depth = 1 + int(dc_state.get_effect("depth_scanner", dc_upgrades))
        # Seismic Pulse level 3 grants +1 max chain depth
        seismic_level = dc_state.get_level("seismic_pulse")
        max_chain_depth_bonus = 1 if seismic_level >= 3 else 0

        # Get active drones
        active_drones = self.drone_fleet.get_active_drones() if self.drone_fleet else []

        self.session = MiningSession(
            self.mining_config,
            click_power_bonus=click_power_bonus,
            passive_drill_bonus=passive_drill_bonus,
            drone_speed_bonus=drone_speed_bonus,
            rare_chance_bonus=rare_chance_bonus,
            chain_chance_bonus=chain_chance_bonus,
            max_chain_depth_bonus=max_chain_depth_bonus,
            starting_depth=starting_depth,
            drones=active_drones,
            prestige_level=self.player.mining_prestige_level,
        )

        # Apply energy conduit bonus
        if energy_bonus > 0:
            self.session.max_energy += energy_bonus
            self.session.energy = self.session.max_energy
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

    def _get_instruction_text(self) -> str:
        """Get contextual instruction text based on current game state."""
        if not self.session:
            return ""
        if self.session.get_undepleted_count() == 0:
            return "All rocks mined! Click Regenerate Field to go deeper."
        if self.session.energy == 0:
            return "No energy! Wait for regen or click normally (free, slower)."
        if self._silo.is_full():
            return "Silo full! Stop mining to transfer ore to your ship."
        return "Click: mine  |  Right-click / E: empowered (3x, uses energy)  |  Drones auto-mine"

    def _end_session(self) -> None:
        """End the mining session: transfer, calculate XP, show summary."""
        # Update personal records
        if self.session:
            total_ore = sum(self.session.total_mined.values())
            if total_ore > self.player.best_mining_session_ore:
                self.player.best_mining_session_ore = total_ore
            if self.session.depth > self.player.best_mining_depth:
                self.player.best_mining_depth = self.session.depth

        self._transfer_count = self._transfer_silo_to_cargo()
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

    def handle_event(self, event: pygame.event.Event) -> None:
        # Summary dismiss: click or key
        if self._show_summary:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.next_state = GameState.TRADING
            elif event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN,
                pygame.K_ESCAPE,
                pygame.K_SPACE,
            ):
                self.next_state = GameState.TRADING
            return

        # Exit confirmation
        if self._confirm_exit:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_y, pygame.K_RETURN):
                    self._confirm_exit = False
                    self._end_session()
                elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                    self._confirm_exit = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._confirm_exit = False
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            cell = self._get_grid_cell(event.pos)
            if cell:
                empowered = event.button == 3  # Right-click = empowered
                self._click_rock(cell[0], cell[1], empowered=empowered)
            elif event.button == 1:
                # Check upgrade button clicks
                self._handle_upgrade_click(event.pos)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._confirm_exit = True
            # E for empowered click on hovered cell
            elif event.key == pygame.K_e:
                mouse_pos = pygame.mouse.get_pos()
                cell = self._get_grid_cell(mouse_pos)
                if cell:
                    self._click_rock(cell[0], cell[1], empowered=True)

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self._confirm_exit = True
            elif event.ui_element == self.regen_button:
                if self.session:
                    advance = self.session.regenerate_field()
                    self.player.max_mining_depth = max(
                        self.player.max_mining_depth, self.session.depth
                    )
                    # Award strata tokens
                    if advance.strata_earned > 0:
                        self.player.add_strata_tokens(advance.strata_earned)
                        self._session_strata += advance.strata_earned
                        bonus_text = " (full clear!)" if advance.was_full_clear else ""
                        self._add_feedback(
                            f"+{advance.strata_earned} Strata{bonus_text}",
                            WINDOW_WIDTH // 2,
                            80,
                            (180, 140, 255),
                        )
                    self._rock_shapes.clear()
                    # Depth transition particles across the grid
                    for gx in range(self.mining_config.grid_width):
                        fx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
                        fy = self.GRID_OFFSET_Y + 10
                        self.particles.emit(fx, fy, DEPTH_TRANSITION)
                    self._show_message(
                        f"Depth {self.session.depth}! +{advance.strata_earned} Strata"
                    )

    def _click_rock(self, gx: int, gy: int, empowered: bool = False) -> None:
        if not self.session:
            return

        # Check silo capacity instead of cargo
        if self._silo.is_full():
            self._show_message("Ore silo full!")
            return

        success, msg, result = self.session.click_rock(gx, gy, empowered=empowered)

        if success:
            # Click hit particles at rock position
            fx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
            fy = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_SIZE // 2
            if empowered:
                self.particles.emit(fx, fy, EMPOWERED_BURST)
            else:
                self.particles.emit(fx, fy, CLICK_HIT)
            get_audio_manager().play_sfx("mine_click")

            # Rock compress-on-hit visual
            self._rock_compress[(gx, gy)] = 0.0

            if result:
                self._handle_mine_result(result, gx, gy)
            self._process_chain_results()
            self._process_milestones()
        else:
            self._show_message(msg)

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 2.0

    def _transfer_silo_to_cargo(self) -> int:
        """Transfer as much silo ore as possible into ship cargo.

        Returns:
            Total units transferred.
        """
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        total_transferred = 0
        for commodity_id in list(self._silo.contents.keys()):
            stored = self._silo.contents.get(commodity_id, 0)
            if stored <= 0:
                continue
            available_space = self.player.ship.get_available_cargo(commodity_volumes)
            volume = commodity_volumes.get(commodity_id, 1)
            can_fit = available_space // volume if volume > 0 else stored
            transfer = min(stored, can_fit)
            if transfer > 0:
                self._silo.remove_ore(commodity_id, transfer)
                self.player.ship.add_cargo(commodity_id, transfer, price_per_unit=0)
                total_transferred += transfer
        return total_transferred

    def _handle_upgrade_click(self, pos: tuple) -> None:
        """Check if click hit an upgrade button and attempt purchase."""
        from spacegame.data_loader import get_data_loader

        dc_upgrades = get_data_loader().deep_core_upgrades
        for uid, rect in self._upgrade_rects.items():
            if rect.collidepoint(pos):
                success, msg, cost = self.player.deep_core_upgrades.purchase(
                    uid, dc_upgrades, self.player.strata_tokens
                )
                if success:
                    self.player.spend_strata_tokens(cost)
                    self._show_message(msg)
                    get_audio_manager().play_sfx("mine_collect")
                    # Apply upgrade effects immediately where possible
                    if uid == "silo_expansion":
                        silo_bonus = int(dc_upgrades[uid].effect_per_level)
                        self.player.ore_silo_manager.upgrade_all_capacity(silo_bonus)
                    elif uid == "energy_conduit" and self.session:
                        energy_add = int(dc_upgrades[uid].effect_per_level)
                        self.session.max_energy += energy_add
                        self.session.energy = min(
                            self.session.energy + energy_add, self.session.max_energy
                        )
                    elif uid == "seismic_pulse" and self.session:
                        self.session.chain_chance_bonus += dc_upgrades[uid].effect_per_level
                        # Level 3 grants +1 max chain depth
                        if self.player.deep_core_upgrades.get_level(uid) >= 3:
                            from spacegame.models.mining import CHAIN_MAX_DEPTH

                            self.session.max_chain_depth = CHAIN_MAX_DEPTH + 1
                    elif uid == "automaton_core" and self.session:
                        self.session.drone_speed_bonus += dc_upgrades[uid].effect_per_level
                else:
                    self._show_message(msg)
                break

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

        # Floating icon animations
        self._floats.update(dt)

        # Glow time
        self._glow_time += dt

        # Tooltip update
        self._update_upgrade_tooltip()
        self._tooltip.update(dt)

        # Crew comment timer
        if self._crew_comment_timer > 0:
            self._crew_comment_timer -= dt

        # Rock compress animation decay
        for key in list(self._rock_compress):
            self._rock_compress[key] += dt
            if self._rock_compress[key] >= 0.15:
                del self._rock_compress[key]

        # Chain cascade pending visual (staggered particle emission)
        for entry in list(self._chain_pending):
            entry[2] -= dt
            if entry[2] <= 0:
                fx = self.GRID_OFFSET_X + entry[0] * self.CELL_SIZE + self.CELL_SIZE // 2
                fy = self.GRID_OFFSET_Y + entry[1] * self.CELL_SIZE + self.CELL_SIZE // 2
                self.particles.emit(fx, fy, CHAIN_SHOCKWAVE)
                get_audio_manager().play_sfx("mine_chain")
                self._chain_pending.remove(entry)

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
            silo_full = self._silo.is_full()
            results = self.session.update(dt, cargo_full=silo_full)
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
        self._silo.add_ore(result.commodity_id, result.quantity)
        self.player.ore_mined += result.quantity
        if result.commodity_id == "rare_ore":
            self.player.rare_ores_mined += result.quantity

        commodity = self.commodities.get(result.commodity_id)
        name = commodity.name if commodity else result.commodity_id

        fx = self.GRID_OFFSET_X + gx * self.CELL_SIZE + self.CELL_SIZE // 2
        fy = self.GRID_OFFSET_Y + gy * self.CELL_SIZE + self.CELL_SIZE // 2

        self.particles.emit(fx, fy, ROCK_BREAK)
        self.particles.emit(fx, fy, COLLECT_SPARKLE)
        self._flash_alpha = 80.0
        self._rock_shakes.pop((gx, gy), None)
        get_audio_manager().play_sfx("mine_break")
        get_audio_manager().play_sfx("mine_collect")

        self._add_feedback(f"+{result.quantity} {name}", fx, fy)
        self._apply_ingredient_drops(result.ingredient_drops, fx, fy)

        # Float ore icon from rock to silo bar
        silo_bar_y = self.GRID_OFFSET_Y + self.mining_config.grid_height * self.CELL_SIZE + 40
        self._floats.add_icon_float(
            text=f"+{result.quantity}",
            origin=(float(fx), float(fy)),
            target=(float(self.GRID_OFFSET_X + 60), float(silo_bar_y)),
            icon_key=result.commodity_id,
            duration=0.7,
        )
        logger.debug(f"Mined {result.quantity} {name}")

        # Crew commentary (20% chance on rock break)
        if random.random() < 0.20:
            line = self._get_crew_line("mining_break")
            if line:
                self._crew_comment_name, self._crew_comment = line[0], line[1]
                self._crew_comment_timer = 4.0

    def _apply_ingredient_drops(self, drops: dict[str, int], fx: int, fy: int) -> None:
        """Add ingredient drops to silo and show feedback."""
        for ingredient_id, qty in drops.items():
            self._silo.add_ore(ingredient_id, qty)
            commodity = self.commodities.get(ingredient_id)
            iname = commodity.name if commodity else ingredient_id
            self._add_feedback(f"+{qty} {iname}!", fx, fy - 20, Colors.YELLOW)
            self.particles.emit(fx, fy, COLLECT_SPARKLE)

    def _process_chain_results(self) -> None:
        """Handle chain-broken rocks: add cargo, emit particles, show feedback."""
        if not self.session:
            return
        self.player.total_chains_triggered += len(self.session.chain_results)
        for i, chain in enumerate(self.session.chain_results):
            self._silo.add_ore(chain.commodity_id, chain.quantity)
            self.player.ore_mined += chain.quantity
            if chain.commodity_id == "rare_ore":
                self.player.rare_ores_mined += chain.quantity
            fx = self.GRID_OFFSET_X + chain.grid_x * self.CELL_SIZE + self.CELL_SIZE // 2
            fy = self.GRID_OFFSET_Y + chain.grid_y * self.CELL_SIZE + self.CELL_SIZE // 2

            # Staggered cascade: 100ms delay per chain step
            delay = i * 0.10
            if delay > 0:
                self._chain_pending.append([chain.grid_x, chain.grid_y, delay])
            else:
                self.particles.emit(fx, fy, CHAIN_SHOCKWAVE)
                get_audio_manager().play_sfx("mine_chain")

            commodity = self.commodities.get(chain.commodity_id)
            name = commodity.name if commodity else chain.commodity_id
            self._add_feedback(f"+{chain.quantity} {name}", fx, fy, Colors.YELLOW)
            self._apply_ingredient_drops(chain.ingredient_drops, fx, fy)
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
        self._silo.add_ore(result.commodity_id, result.quantity)
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

        self.particles.emit(fx, fy, ROCK_BREAK)
        self.particles.emit(fx, fy, COLLECT_SPARKLE)
        self._flash_alpha = 60.0
        get_audio_manager().play_sfx("mine_break")
        get_audio_manager().play_sfx("mine_collect")

        self._add_feedback(f"+{result.quantity} {name}", fx, fy)
        self._apply_ingredient_drops(result.ingredient_drops, fx, fy)
        logger.debug(f"Mined {result.quantity} {name} (auto)")

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title with field name
        field_info = FIELD_DESCRIPTIONS.get(self.mining_config.system_id)
        field_name = field_info[0] if field_info else "ASTEROID MINING"
        title = self.title_font.render(field_name.upper(), True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 25))
        screen.blit(title, title_rect)

        # Field flavor description
        if field_info:
            flavor = self.small_font.render(field_info[1], True, Colors.TEXT_SECONDARY)
            screen.blit(flavor, flavor.get_rect(center=(WINDOW_WIDTH // 2, 48)))

        if not self.session:
            return

        # Contextual instructions
        instr = self.small_font.render(self._get_instruction_text(), True, Colors.TEXT_SECONDARY)
        screen.blit(instr, (self.GRID_OFFSET_X, 65))

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

        # Draw upgrade panel (below milestones, left side)
        self._render_upgrade_panel(screen)

        # Draw silo bar below energy bar
        self._render_silo_bar(screen)

        # Particles on top
        self.particles.render(screen)

        # Floating ore icons (rock to silo)
        for item in self._floats.items:
            alpha = int(255 * item.alpha)
            if alpha <= 0:
                continue
            scale = item.scale
            text_surf = self.small_font.render(item.text, True, Colors.SUCCESS)
            text_surf.set_alpha(alpha)
            screen.blit(text_surf, (int(item.x) - text_surf.get_width() // 2, int(item.y)))

        # White flash overlay (pre-allocated surface)
        if self._flash_alpha > 0:
            self._flash_surface.set_alpha(int(self._flash_alpha))
            screen.blit(self._flash_surface, (0, 0))

        # Feedback messages
        for fb in self.feedback_messages:
            surf = self.info_font.render(fb["text"], True, fb["color"])
            screen.blit(surf, (int(fb["x"]) - surf.get_width() // 2, int(fb["y"])))

        # Status message
        if self.message_timer > 0:
            msg_surf = self.info_font.render(self.message, True, Colors.YELLOW)
            msg_rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 90))
            screen.blit(msg_surf, msg_rect)

        # Crew commentary
        if self._crew_comment_timer > 0 and self._crew_comment:
            alpha = min(int(self._crew_comment_timer / 0.5 * 255), 220)
            crew_text = f'{self._crew_comment_name}: "{self._crew_comment}"'
            crew_surf = self.small_font.render(crew_text, True, (180, 200, 220))
            crew_surf.set_alpha(alpha)
            screen.blit(
                crew_surf,
                crew_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 130)),
            )

        # Tooltip (above everything except overlays)
        self._render_tooltip(screen)

        # Exit confirmation overlay
        if self._confirm_exit:
            self._render_confirm_exit(screen)

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

            # Rock compress-on-hit: shrink sprite 1-2px then spring back
            compress = 0
            compress_key = (rock.grid_x, rock.grid_y)
            if compress_key in self._rock_compress:
                t = self._rock_compress[compress_key] / 0.15  # 0 -> 1
                # Compress in first 40%, spring back in remaining 60%
                if t < 0.4:
                    compress = int(2 * (t / 0.4))
                else:
                    compress = int(2 * (1.0 - (t - 0.4) / 0.6))

            if rock.depleted:
                # Empty cell — 9-slice panel
                draw_nine_slice_panel(
                    screen,
                    rect,
                    alpha=120,
                    bg_color=(18, 20, 28),
                    border_color=(35, 38, 48),
                )
            else:
                color = rock.config.color
                is_hovered = (
                    hover_cell and hover_cell[0] == rock.grid_x and hover_cell[1] == rock.grid_y
                )

                # Try rock-type sprite first, then commodity icon, then procedural
                rock_sprite = self._get_rock_sprite(rock.rock_type, rock.grid_x, rock.grid_y)

                if rock_sprite is not None:
                    # 9-slice cell background
                    bg_color = (color[0] // 5, color[1] // 5, color[2] // 5)
                    border_color = (
                        Colors.TEXT_HIGHLIGHT
                        if is_hovered
                        else (color[0] // 3, color[1] // 3, color[2] // 3)
                    )
                    draw_nine_slice_panel(
                        screen,
                        rect,
                        alpha=200,
                        bg_color=bg_color,
                        border_color=border_color,
                    )

                    # Center the rock sprite (with compress offset)
                    sprite_x = rect.centerx - rock_sprite.get_width() // 2
                    sprite_y = rect.centery - rock_sprite.get_height() // 2 - 4 + compress
                    screen.blit(rock_sprite, (sprite_x, sprite_y))
                else:
                    # Fallback: procedural polygon (no sprite available)
                    rock_points = self._generate_rock_shape(rock.grid_x, rock.grid_y, w, h)
                    offset_points = [(p[0] + sx, p[1] + sy) for p in rock_points]
                    pygame.draw.polygon(screen, color, offset_points)
                    if is_hovered:
                        pygame.draw.polygon(screen, Colors.TEXT_HIGHLIGHT, offset_points, 2)
                    else:
                        pygame.draw.polygon(screen, (180, 180, 180), offset_points, 1)

                # Drill progress bar with leading-edge glow
                if rock.drilling or rock.drill_progress > 0:
                    bar_y = rect.bottom - 12
                    bar_w = w - 8
                    # Orange for player, blue for drone
                    is_drone_target = (rock.grid_x, rock.grid_y) in drone_target_positions
                    bar_color = (80, 160, 255) if is_drone_target else Colors.TEXT_HIGHLIGHT
                    draw_bar(
                        screen,
                        sx + 4,
                        bar_y,
                        bar_w,
                        8,
                        rock.drill_progress * 100,
                        100,
                        bar_color,
                        show_value=False,
                    )
                    # Leading-edge additive glow (pre-allocated surface)
                    if rock.drill_progress > 0.02 and rock.drill_progress < 1.0:
                        edge_x = sx + 4 + int(bar_w * rock.drill_progress)
                        glow_alpha = int(120 + 60 * math.sin(self._glow_time * 8))
                        self._drill_glow_surf.fill((*bar_color, glow_alpha))
                        screen.blit(
                            self._drill_glow_surf,
                            (edge_x - 3, bar_y - 2),
                            special_flags=pygame.BLEND_ADD,
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

                # Monolith strata reward indicator
                if rock.rock_type == RockType.MONOLITH and rock.strata_reward > 0:
                    strata_text = self.cell_font.render(
                        f"+{rock.strata_reward} ST", True, (180, 120, 255)
                    )
                    screen.blit(
                        strata_text,
                        strata_text.get_rect(center=(rect.centerx, rect.top + 12)),
                    )

        # Draw environmental hazards
        for hazard in self.session.hazards:
            x = self.GRID_OFFSET_X + hazard.grid_x * self.CELL_SIZE + self.CELL_PADDING
            y = self.GRID_OFFSET_Y + hazard.grid_y * self.CELL_SIZE + self.CELL_PADDING
            w = self.CELL_SIZE - self.CELL_PADDING * 2
            h = self.CELL_SIZE - self.CELL_PADDING * 2
            rect = pygame.Rect(x, y, w, h)

            hazard_sprite = self._get_hazard_sprite(
                hazard.hazard_type, hazard.grid_x, hazard.grid_y
            )

            if hazard.hazard_type == HazardType.UNSTABLE_CELL:
                pygame.draw.rect(screen, (40, 15, 10), rect)
                if hazard_sprite is not None:
                    sprite_x = rect.centerx - hazard_sprite.get_width() // 2
                    sprite_y = rect.centery - hazard_sprite.get_height() // 2 - 4
                    screen.blit(hazard_sprite, (sprite_x, sprite_y))
                # Pulsing red sine-wave border
                pulse = int(abs(math.sin(self._glow_time * 5)) * 80) + 140
                pygame.draw.rect(screen, (pulse, 60, 30), rect, 2)
                label = self.cell_font.render("UNSTABLE", True, (255, 120, 60))
                screen.blit(label, label.get_rect(center=(rect.centerx, rect.bottom - 10)))
            elif hazard.hazard_type == HazardType.PRESSURE_VENT:
                pygame.draw.rect(screen, (10, 25, 35), rect)
                if hazard_sprite is not None:
                    sprite_x = rect.centerx - hazard_sprite.get_width() // 2
                    sprite_y = rect.centery - hazard_sprite.get_height() // 2 - 8
                    screen.blit(hazard_sprite, (sprite_x, sprite_y))
                # Pulsing teal border
                pulse = int(abs(math.sin(self._glow_time * 3)) * 40) + 60
                pygame.draw.rect(screen, (pulse, 180, 160), rect, 2)
                label = self.cell_font.render("VENT", True, (80, 220, 200))
                screen.blit(label, label.get_rect(center=(rect.centerx, rect.centery + 14)))
                from spacegame.models.mining import VENT_PULSE_INTERVAL

                remaining = VENT_PULSE_INTERVAL - hazard.pulse_timer
                timer_text = self.cell_font.render(f"{remaining:.0f}s", True, (60, 160, 140))
                screen.blit(
                    timer_text, timer_text.get_rect(center=(rect.centerx, rect.centery + 28))
                )

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

            # Drone tier sprite or fallback circle
            drone_sprite = self._drone_sprites.get(tier_val)
            if drone_sprite is not None:
                screen.blit(drone_sprite, (panel_x - 2, y - 6))
            else:
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

        stats = [
            f"Clicks: {self.session.total_clicks}",
            f"Rocks remaining: {self.session.get_undepleted_count()}/{self.session.get_total_rocks()}",
            f"Silo: {self._silo.get_total_stored()}/{self._silo.capacity}",
            f"Strata Tokens: {self.player.strata_tokens}",
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
            screen,
            bar_x,
            bar_y,
            bar_width,
            bar_height,
            self.session.energy,
            self.session.max_energy,
            bar_color,
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
        panel_y = self.GRID_OFFSET_Y + self.mining_config.grid_height * self.CELL_SIZE + 40

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
                screen,
                bar_x,
                bar_y_pos,
                bar_w,
                bar_h,
                value,
                ms.threshold,
                color,
                show_value=False,
                bg_color=Colors.BAR_BG_LIGHT,
            )

            y += 28

    def _render_silo_bar(self, screen: pygame.Surface) -> None:
        """Render silo capacity bar below the energy bar."""
        if not self.session:
            return
        energy_bar_y = self.GRID_OFFSET_Y + self.mining_config.grid_height * self.CELL_SIZE + 10
        bar_y = energy_bar_y + 28
        bar_width = self.mining_config.grid_width * self.CELL_SIZE
        bar_height = 16
        bar_x = self.GRID_OFFSET_X

        stored = self._silo.get_total_stored()
        capacity = self._silo.capacity
        ratio = stored / max(1, capacity)
        if ratio > 0.9:
            bar_color = Colors.RED
        elif ratio > 0.7:
            bar_color = Colors.YELLOW
        else:
            bar_color = (180, 140, 255)  # Purple for silo
        draw_bar(
            screen,
            bar_x,
            bar_y,
            bar_width,
            bar_height,
            stored,
            capacity,
            bar_color,
            show_value=False,
        )
        label = f"SILO: {stored}/{capacity}"
        surf = self.small_font.render(label, True, Colors.TEXT)
        screen.blit(surf, (bar_x + 8, bar_y))

    def _render_upgrade_panel(self, screen: pygame.Surface) -> None:
        """Render deep core upgrade purchase panel."""
        from spacegame.data_loader import get_data_loader

        dc_upgrades = get_data_loader().deep_core_upgrades
        if not dc_upgrades:
            return

        dc_state = self.player.deep_core_upgrades

        # Position below milestones
        milestone_count = len(self.session.milestones) if self.session else 0
        panel_x = self.GRID_OFFSET_X
        panel_y = (
            self.GRID_OFFSET_Y
            + self.mining_config.grid_height * self.CELL_SIZE
            + 40
            + milestone_count * 28
            + 30
        )

        # Check if we have room
        if panel_y > WINDOW_HEIGHT - 120:
            return

        header = self.small_font.render("DEEP CORE UPGRADES", True, (180, 140, 255))
        screen.blit(header, (panel_x, panel_y))

        strata_surf = self.small_font.render(
            f"Strata: {self.player.strata_tokens}", True, (180, 140, 255)
        )
        screen.blit(strata_surf, (panel_x + 180, panel_y))

        y = panel_y + 22
        mouse_pos = pygame.mouse.get_pos()
        self._upgrade_rects.clear()

        for uid, definition in dc_upgrades.items():
            if y > WINDOW_HEIGHT - 70:
                break
            level = dc_state.get_level(uid)
            next_cost = definition.get_cost(level + 1)

            # Button rect
            btn_rect = pygame.Rect(panel_x, y, 320, 22)
            self._upgrade_rects[uid] = btn_rect

            # Hover highlight
            is_hover = btn_rect.collidepoint(mouse_pos)
            if is_hover:
                pygame.draw.rect(screen, (40, 35, 60), btn_rect)

            # Level pips
            pip_str = ""
            for i in range(definition.max_level):
                pip_str += "[X]" if i < level else "[ ]"

            if next_cost is not None:
                can_buy = self.player.strata_tokens >= next_cost
                cost_color = Colors.TEXT if can_buy else Colors.RED
                text = f"{definition.name} {pip_str}  ({next_cost} ST)"
                surf = self.small_font.render(text, True, cost_color)
            else:
                text = f"{definition.name} {pip_str}  MAX"
                surf = self.small_font.render(text, True, Colors.TEXT_SECONDARY)

            screen.blit(surf, (panel_x + 4, y + 2))
            y += 24

    def _update_upgrade_tooltip(self) -> None:
        """Check if mouse is hovering over an upgrade row and update tooltip."""
        mouse_pos = pygame.mouse.get_pos()
        from spacegame.data_loader import get_data_loader

        dc_upgrades = get_data_loader().deep_core_upgrades
        for uid, rect in self._upgrade_rects.items():
            if rect.collidepoint(mouse_pos):
                definition = dc_upgrades.get(uid)
                if definition:
                    level = self.player.deep_core_upgrades.get_level(uid)
                    effect = definition.get_effect(level)
                    tip = f"{definition.description}"
                    if level > 0:
                        tip += f" (current: {effect:.2g})"
                    self._tooltip.set_hover(uid, mouse_pos)
                return
        self._tooltip.clear()

    def _render_tooltip(self, screen: pygame.Surface) -> None:
        """Render the upgrade tooltip if visible."""
        if not self._tooltip.visible or self._tooltip.content is None:
            return
        from spacegame.data_loader import get_data_loader

        dc_upgrades = get_data_loader().deep_core_upgrades
        definition = dc_upgrades.get(self._tooltip.content)
        if not definition:
            return

        level = self.player.deep_core_upgrades.get_level(self._tooltip.content)
        effect = definition.get_effect(level)
        lines = [definition.name, definition.description]
        if level > 0:
            lines.append(f"Current effect: {effect:.2g}")

        # Measure tooltip size
        font = self.small_font
        line_surfaces = [font.render(line, True, Colors.TEXT) for line in lines]
        tip_w = max(s.get_width() for s in line_surfaces) + 20
        tip_h = len(line_surfaces) * 20 + 12
        alpha = int(255 * self._tooltip.alpha)

        tx, ty = self._tooltip.get_screen_position(tip_w, tip_h, WINDOW_WIDTH, WINDOW_HEIGHT)

        # Background panel
        tip_surf = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
        tip_surf.fill((15, 18, 30, min(alpha, 230)))
        pygame.draw.rect(tip_surf, (60, 70, 100, alpha), tip_surf.get_rect(), 1)
        screen.blit(tip_surf, (tx, ty))

        # Text
        for i, surf in enumerate(line_surfaces):
            surf.set_alpha(alpha)
            screen.blit(surf, (tx + 10, ty + 6 + i * 20))

    def _render_confirm_exit(self, screen: pygame.Surface) -> None:
        """Render exit confirmation overlay."""
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        screen.blit(dim, (0, 0))

        prompt = self.info_font.render("End mining session?", True, Colors.TEXT)
        screen.blit(prompt, prompt.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 15)))

        hint = self.small_font.render(
            "Y / Enter = Yes    N / Esc = Cancel", True, Colors.TEXT_SECONDARY
        )
        screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 15)))

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
                ("Strata Earned", str(self._session_strata)),
                ("Loaded to Ship", str(self._transfer_count)),
            ]
            silo_remaining = self._silo.get_total_stored()
            if silo_remaining > 0:
                stats.append(("Left in Silo", str(silo_remaining)))
            # Skill bonus indicators
            if self.session.click_power_bonus > 0:
                stats.append(("Drill Power Bonus", f"+{self.session.click_power_bonus * 100:.0f}%"))
            if self.session.rare_chance_bonus > 0:
                stats.append(("Rare Ore Bonus", f"+{self.session.rare_chance_bonus * 100:.0f}%"))
            if self.session.chain_chance_bonus > 0:
                stats.append(("Chain Bonus", f"+{self.session.chain_chance_bonus * 100:.0f}%"))
        # Add per-commodity breakdown with icons
        if self.session and self.session.total_mined:
            for cid, qty in self.session.total_mined.items():
                commodity = self.commodities.get(cid)
                cname = commodity.name if commodity else cid
                stats.append((f"  {cname}", str(qty)))

        draw_summary_overlay(
            screen,
            title="MINING COMPLETE",
            stats=stats,
            xp_earned=self._summary_xp,
            rating_letter=self._session_rating,
            rating_color=RATING_COLORS.get(self._session_rating, Colors.TEXT_SECONDARY),
            panel_height=480,
        )

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
