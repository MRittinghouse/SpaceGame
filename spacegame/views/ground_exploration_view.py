"""Ground exploration view.

Turn-based grid exploration with scrolling viewport, fog of war,
player movement, enemy rendering, stealth system integration,
and ground combat overlay panel.
"""

import random
from typing import TYPE_CHECKING, Optional

import pygame
import pygame_gui

from spacegame.config import (
    GROUND_CAMERA_LERP_SPEED,
    GROUND_COMBAT_PANEL_HEIGHT,
    GROUND_TILE_SIZE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_y,
)
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.draw_utils import draw_bar
from spacegame.engine.fonts import FONT_BODY, FONT_LG, FONT_MD, FONT_SECTION, FONT_XL, get_font
from spacegame.engine.sprites import AnimatedSprite, get_sprite_manager
from spacegame.models.ground import (
    FogState,
    GroundMap,
    GroundPlayerState,
    TileType,
)
from spacegame.models.ground_combat import (
    CombatOutcome,
    GroundCombatState,
    SocialSkillType,
    build_player_ground_combat_stats,
    make_enemy_from_template,
)
from spacegame.models.ground_enemy import (
    AlertLevel,
    Direction,
    GroundMissionState,
    NoiseEvent,
)
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView

if TYPE_CHECKING:
    from spacegame.models.ground_mission import (
        GroundMissionConfig,
        GroundMissionResult,
        MissionOutcome,
    )


# Minimap constants
MINIMAP_SIZE = scale_y(150)  # Pixels (square)
MINIMAP_MARGIN = 10  # From top-right corner
MINIMAP_BG_COLOR = (10, 10, 15, 200)  # Semi-transparent background
MINIMAP_INTERACTABLE_COLOR = (100, 220, 220)  # Cyan for loot containers

# Tile type to placeholder color mapping
_TILE_COLORS: dict[TileType, tuple[int, int, int]] = {
    TileType.FLOOR: Colors.GROUND_FLOOR,
    TileType.WALL: Colors.GROUND_WALL,
    TileType.DOOR_CLOSED: Colors.GROUND_DOOR_CLOSED,
    TileType.DOOR_OPEN: Colors.GROUND_DOOR_OPEN,
    TileType.EXIT: Colors.GROUND_EXIT,
    TileType.ENTRANCE: Colors.GROUND_ENTRANCE,
    TileType.NOISY_FLOOR: Colors.GROUND_NOISY_FLOOR,
    TileType.TERMINAL: Colors.GROUND_TERMINAL,
    TileType.HAZARD: Colors.GROUND_HAZARD,
    TileType.VENT: Colors.GROUND_VENT,
}

# Alert level to color mapping for HUD indicator
_ALERT_COLORS: dict[AlertLevel, tuple[int, int, int]] = {
    AlertLevel.UNDETECTED: Colors.GREEN,
    AlertLevel.SUSPICIOUS: Colors.YELLOW,
    AlertLevel.ALERT: Colors.RED,
    AlertLevel.COMBAT: Colors.RED,
}

# Movement key mapping: key -> (dx, dy)
_MOVE_KEYS: dict[int, tuple[int, int]] = {
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
}

# Direction to facing indicator offset (small triangle pointing in direction)
_FACING_OFFSETS: dict[Direction, tuple[int, int, int, int, int, int]] = {
    # (x1, y1, x2, y2, x3, y3) — triangle vertices relative to tile center
    Direction.RIGHT: (4, -3, 4, 3, 8, 0),
    Direction.LEFT: (-4, -3, -4, 3, -8, 0),
    Direction.DOWN: (-3, 4, 3, 4, 0, 8),
    Direction.UP: (-3, -4, 3, -4, 0, -8),
}

# Social skill cycle order for talk attempts
_SOCIAL_SKILL_ORDER = [
    SocialSkillType.PERSUASION,
    SocialSkillType.INTIMIDATION,
    SocialSkillType.OBSERVATION,
]


class GroundExplorationView(BaseView):
    """Turn-based grid exploration with scrolling viewport and fog of war."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        ground_map: GroundMap,
        player_state: GroundPlayerState,
        mission_state: Optional[GroundMissionState] = None,
        mission_config: Optional["GroundMissionConfig"] = None,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.ground_map = ground_map
        self.player_state = player_state
        self.mission_state = mission_state
        self.mission_config = mission_config
        self.next_state: Optional[GameState] = None

        # === Mission-wide tracking (for result building) ===
        self.total_loot_credits: int = 0
        self.total_loot_commodities: dict[str, int] = {}
        self.total_enemies_defeated: int = 0
        self.total_enemies_talked: int = 0
        self.was_detected: bool = False
        self._crew_ids: list[str] = []
        self._mission_outcome: Optional["MissionOutcome"] = None

        # Camera position in pixel coords (lerps toward player)
        px = player_state.x * GROUND_TILE_SIZE + GROUND_TILE_SIZE // 2
        py = player_state.y * GROUND_TILE_SIZE + GROUND_TILE_SIZE // 2
        self._camera_x: float = float(px)
        self._camera_y: float = float(py)
        self._target_camera_x: float = float(px)
        self._target_camera_y: float = float(py)

        # Fonts
        self._hud_font = get_font("machine", FONT_BODY)
        self._msg_font = get_font("dialogue", FONT_LG)
        self._combat_font = get_font("header", FONT_XL)
        self._dice_font = get_font("stats", FONT_SECTION)
        self._combat_label_font = get_font("dialogue", FONT_MD)

        # Sprite manager for ground tiles
        self._sprite_mgr = get_sprite_manager()
        # Pre-cache tile sprites (GROUND_TILE_SIZE / 16 = scale factor)
        tile_scale = GROUND_TILE_SIZE // 16
        tile_faction = self.mission_config.faction_id if self.mission_config else "neutral"
        self._tile_sprites: dict[str, Optional[pygame.Surface]] = {}
        self._animated_tile_sprites: dict[str, AnimatedSprite] = {}
        for tt in TileType:
            # Try animated sprite sheet first, fall back to static
            anim = self._sprite_mgr.get_ground_tile_animated(
                tt.value, tile_faction, scale=tile_scale
            )
            if anim is not None:
                self._animated_tile_sprites[tt.value] = anim
            self._tile_sprites[tt.value] = self._sprite_mgr.get_ground_tile(
                tt.value, tile_faction, scale=tile_scale
            )

        # Ground character sprites
        self._player_sprite = self._sprite_mgr.get_ground_player_sprite(scale=tile_scale)
        self._enemy_sprites: dict[str, Optional[pygame.Surface]] = {}

        # Fog overlay tile (reused for explored tiles)
        self._fog_overlay = pygame.Surface((GROUND_TILE_SIZE, GROUND_TILE_SIZE), pygame.SRCALPHA)
        self._fog_overlay.fill((0, 0, 0, Colors.GROUND_FOG_EXPLORED_ALPHA))

        # Combat panel background (reused)
        self._combat_panel_bg = pygame.Surface(
            (WINDOW_WIDTH, GROUND_COMBAT_PANEL_HEIGHT), pygame.SRCALPHA
        )
        self._combat_panel_bg.fill((15, 15, 25, 230))

        # Minimap surface and positioning
        self._minimap_surface = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE), pygame.SRCALPHA)
        self._minimap_scale = MINIMAP_SIZE / max(self.ground_map.width, self.ground_map.height)
        self._minimap_x = WINDOW_WIDTH - MINIMAP_SIZE - MINIMAP_MARGIN
        self._minimap_y = MINIMAP_MARGIN

        # UI elements
        self._back_button: Optional[pygame_gui.elements.UIButton] = None

        # Status message
        self._message: str = ""
        self._message_timer: float = 0.0

        # Track last direction for interact
        self._last_dx: int = 1
        self._last_dy: int = 0

        # === Combat overlay state ===
        self._combat_state: Optional[GroundCombatState] = None
        self._combat_message: str = ""
        self._last_player_roll: int = 0
        self._last_enemy_roll: int = 0
        self._analyze_bonus: int = 0  # Pending attack bonus from Priya's analyze
        self._loot_earned: int = 0  # Credits earned from last combat victory

    # === Lifecycle ===

    def on_enter(self) -> None:
        """Initialize view and reveal starting area."""
        super().on_enter()
        logger.info("Entered ground exploration")
        self._create_ui()

        # Initial fog reveal at player position
        self.ground_map.update_fog_of_war(
            self.player_state.x,
            self.player_state.y,
            self._effective_vision_radius(),
        )

    def _create_ui(self) -> None:
        """Create pygame_gui elements."""
        # Place below minimap to avoid overlap
        btn_y = MINIMAP_MARGIN + MINIMAP_SIZE + 5
        self._back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((WINDOW_WIDTH - 120, btn_y), (110, 35)),
            text="Exit (Esc)",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        """Kill all UI elements."""
        if self._back_button:
            self._back_button.kill()
            self._back_button = None

    def on_exit(self) -> None:
        """Clean up on exit."""
        self._combat_state = None
        self._destroy_ui()
        super().on_exit()

    def get_next_state(self) -> Optional[GameState]:
        """Return pending state transition."""
        return self.next_state

    # === Mission Tracking ===

    def _check_detection(self) -> None:
        """Update detection flag from current alert level (sticky)."""
        if self.mission_state and not self.was_detected:
            if self.mission_state.alert_level in (AlertLevel.ALERT, AlertLevel.COMBAT):
                self.was_detected = True

    def _accumulate_combat_loot(self, credits: int) -> None:
        """Add loot credits to mission-wide total."""
        self.total_loot_credits += credits

    def _accumulate_enemies_defeated(self, count: int) -> None:
        """Add to mission-wide enemies defeated count."""
        self.total_enemies_defeated += count

    def _accumulate_enemies_talked(self, count: int) -> None:
        """Add to mission-wide enemies talked count."""
        self.total_enemies_talked += count

    def _check_exit_tile(self) -> None:
        """Check if player is standing on exit tile and end mission."""
        tile = self.ground_map.get_tile(self.player_state.x, self.player_state.y)
        if tile and tile.tile_type == TileType.EXIT:
            if self.mission_config:
                from spacegame.models.ground_mission import MissionOutcome

                self._end_mission(MissionOutcome.SUCCESS)
            else:
                self.next_state = GameState.GALAXY_MAP

    def _end_mission(self, outcome: "MissionOutcome") -> None:
        """End the ground mission and transition to result screen.

        Args:
            outcome: The mission outcome.
        """
        self._mission_outcome = outcome
        self.next_state = GameState.GROUND_RESULT

    def get_mission_result(self, outcome: "MissionOutcome") -> Optional["GroundMissionResult"]:
        """Build a GroundMissionResult from tracked mission state.

        Args:
            outcome: The mission outcome to record.

        Returns:
            GroundMissionResult, or None if no mission config.
        """
        if not self.mission_config:
            return None

        from spacegame.models.ground_mission import GroundMissionResult

        objectives_total = len(self.mission_config.objectives)
        # For success, all objectives completed; otherwise estimate from progress
        if outcome.is_success:
            objectives_completed = objectives_total
        else:
            objectives_completed = 0

        # Estimate progress percent from player position relative to exit
        progress = 0.0
        if self.ground_map.exit_pos:
            ex, ey = self.ground_map.exit_pos
            ix, iy = self.ground_map.entrance_pos
            total_dist = abs(ex - ix) + abs(ey - iy)
            if total_dist > 0:
                player_dist = abs(self.player_state.x - ix) + abs(self.player_state.y - iy)
                progress = min(1.0, player_dist / total_dist)
        if outcome.is_success:
            progress = 1.0

        return GroundMissionResult(
            config=self.mission_config,
            outcome=outcome,
            objectives_completed=objectives_completed,
            objectives_total=objectives_total,
            turns_taken=self.player_state.turn_number,
            enemies_defeated=self.total_enemies_defeated,
            enemies_talked=self.total_enemies_talked,
            loot_credits=self.total_loot_credits,
            loot_items=[],
            loot_commodities=dict(self.total_loot_commodities),
            progress_percent=progress,
            crew_ids=list(self._crew_ids),
            detected=self.was_detected,
        )

    # === Update ===

    def update(self, dt: float) -> None:
        """Update camera position and message timers."""
        if not self.active:
            return

        # Lerp camera toward target
        lerp = min(1.0, GROUND_CAMERA_LERP_SPEED * dt)
        self._camera_x += (self._target_camera_x - self._camera_x) * lerp
        self._camera_y += (self._target_camera_y - self._camera_y) * lerp

        # Decay status message
        if self._message_timer > 0:
            self._message_timer -= dt
            if self._message_timer <= 0:
                self._message = ""

        # Update animated tile sprites
        for anim in self._animated_tile_sprites.values():
            anim.update(dt)

    # === Rendering ===

    def render(self, screen: pygame.Surface) -> None:
        """Render the ground map, enemies, player, and HUD."""
        screen.fill(Colors.BLACK)

        ts = GROUND_TILE_SIZE
        # Calculate viewport offset (center camera on screen)
        offset_x = WINDOW_WIDTH // 2 - self._camera_x
        offset_y = WINDOW_HEIGHT // 2 - self._camera_y

        # Clamp camera so we don't show beyond map edges
        map_pixel_w = self.ground_map.width * ts
        map_pixel_h = self.ground_map.height * ts
        offset_x = min(0, max(WINDOW_WIDTH - map_pixel_w, offset_x))
        offset_y = min(0, max(WINDOW_HEIGHT - map_pixel_h, offset_y))

        # Determine visible tile range for culling
        start_x = max(0, int(-offset_x // ts))
        start_y = max(0, int(-offset_y // ts))
        end_x = min(self.ground_map.width, start_x + (WINDOW_WIDTH // ts) + 2)
        end_y = min(self.ground_map.height, start_y + (WINDOW_HEIGHT // ts) + 2)

        # Render tiles
        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                tile = self.ground_map.get_tile(tx, ty)
                if tile is None:
                    continue

                screen_x = int(tx * ts + offset_x)
                screen_y = int(ty * ts + offset_y)
                tile_rect = pygame.Rect(screen_x, screen_y, ts, ts)

                if tile.fog_state == FogState.UNEXPLORED:
                    continue

                # Try animated sprite, then static sprite, then colored rectangle
                anim_tile = self._animated_tile_sprites.get(tile.tile_type.value)
                if anim_tile:
                    surf = anim_tile.get_surface()
                    if surf:
                        screen.blit(surf, (screen_x, screen_y))
                    else:
                        tile_sprite = self._tile_sprites.get(tile.tile_type.value)
                        if tile_sprite:
                            screen.blit(tile_sprite, (screen_x, screen_y))
                elif tile_sprite := self._tile_sprites.get(tile.tile_type.value):
                    screen.blit(tile_sprite, (screen_x, screen_y))
                else:
                    color = _TILE_COLORS.get(tile.tile_type, Colors.GROUND_FLOOR)
                    pygame.draw.rect(screen, color, tile_rect)

                if tile.fog_state == FogState.EXPLORED:
                    screen.blit(self._fog_overlay, (screen_x, screen_y))

                # Tile border for grid visibility
                pygame.draw.rect(screen, Colors.UI_BORDER, tile_rect, 1)

        # Render patrol route markers (Elena's reveal)
        if self.mission_state and self.mission_state.crew_bonuses.reveal_patrol_routes:
            self._render_patrol_routes(screen, offset_x, offset_y, ts)

        # Render enemies (only on visible tiles)
        if self.mission_state:
            self._render_enemies(screen, offset_x, offset_y, ts)

        # Render player (rotated to face last movement direction)
        if self._player_sprite is not None:
            # Determine rotation from last direction (sprite default = facing down)
            if self._last_dx == 1 and self._last_dy == 0:
                angle = 90  # Right
            elif self._last_dx == -1 and self._last_dy == 0:
                angle = -90  # Left
            elif self._last_dy == -1:
                angle = 180  # Up
            else:
                angle = 0  # Down (default)
            rotated = pygame.transform.rotate(self._player_sprite, angle)
            ppx = int(self.player_state.x * ts + offset_x + (ts - rotated.get_width()) // 2)
            ppy = int(self.player_state.y * ts + offset_y + (ts - rotated.get_height()) // 2)
            screen.blit(rotated, (ppx, ppy))
        else:
            ppx = int(self.player_state.x * ts + offset_x + ts * 0.2)
            ppy = int(self.player_state.y * ts + offset_y + ts * 0.2)
            player_size = int(ts * 0.6)
            pygame.draw.rect(screen, Colors.GROUND_PLAYER, (ppx, ppy, player_size, player_size))

        # HUD overlay
        self._render_hud(screen)

        # Minimap
        self._render_minimap(screen)

        # Combat panel overlay
        if self._combat_state is not None:
            self._render_combat_panel(screen)

    def _render_patrol_routes(
        self,
        screen: pygame.Surface,
        offset_x: float,
        offset_y: float,
        ts: int,
    ) -> None:
        """Render patrol route markers as small diamonds on explored tiles."""
        if not self.mission_state:
            return
        patrol_tiles = self.mission_state.get_revealed_patrol_tiles()
        for px, py in patrol_tiles:
            tile = self.ground_map.get_tile(px, py)
            if tile is None or tile.fog_state == FogState.UNEXPLORED:
                continue
            cx = int(px * ts + offset_x + ts // 2)
            cy = int(py * ts + offset_y + ts // 2)
            # Small diamond marker
            size = 4
            points = [
                (cx, cy - size),
                (cx + size, cy),
                (cx, cy + size),
                (cx - size, cy),
            ]
            color = (
                (255, 180, 50, 160) if tile.fog_state == FogState.VISIBLE else (255, 180, 50, 80)
            )
            pygame.draw.polygon(screen, color[:3], points)

    def _render_enemies(
        self,
        screen: pygame.Surface,
        offset_x: float,
        offset_y: float,
        ts: int,
    ) -> None:
        """Render visible enemies as colored circles with facing indicators."""
        if not self.mission_state:
            return

        for enemy in self.mission_state.enemies:
            tile = self.ground_map.get_tile(enemy.x, enemy.y)
            if tile is None or tile.fog_state != FogState.VISIBLE:
                continue

            # Try sprite for this enemy
            if enemy.template_id not in self._enemy_sprites:
                self._enemy_sprites[enemy.template_id] = self._sprite_mgr.get_ground_enemy_sprite(
                    enemy.template_id
                )
            enemy_sprite = self._enemy_sprites.get(enemy.template_id)

            if enemy_sprite is not None:
                # Rotate sprite to match facing direction
                facing_angles = {
                    Direction.RIGHT: 90,
                    Direction.LEFT: -90,
                    Direction.UP: 180,
                    Direction.DOWN: 0,
                }
                angle = facing_angles.get(enemy.facing, 0)
                rotated_enemy = pygame.transform.rotate(enemy_sprite, angle)
                ex = int(enemy.x * ts + offset_x + (ts - rotated_enemy.get_width()) // 2)
                ey = int(enemy.y * ts + offset_y + (ts - rotated_enemy.get_height()) // 2)
                screen.blit(rotated_enemy, (ex, ey))
                # Alert level indicator dot
                color = _ALERT_COLORS.get(self.mission_state.alert_level, Colors.GROUND_ENEMY)
                dot_x = int(enemy.x * ts + offset_x + ts - 8)
                dot_y = int(enemy.y * ts + offset_y + 4)
                pygame.draw.circle(screen, color, (dot_x, dot_y), 4)
            else:
                # Fallback: circle + triangle
                cx = int(enemy.x * ts + offset_x + ts // 2)
                cy = int(enemy.y * ts + offset_y + ts // 2)
                radius = int(ts * 0.25)
                color = _ALERT_COLORS.get(self.mission_state.alert_level, Colors.GROUND_ENEMY)
                pygame.draw.circle(screen, color, (cx, cy), radius)
                tri = _FACING_OFFSETS.get(enemy.facing)
                if tri:
                    points = [
                        (cx + tri[0], cy + tri[1]),
                        (cx + tri[2], cy + tri[3]),
                        (cx + tri[4], cy + tri[5]),
                    ]
                    pygame.draw.polygon(screen, color, points)

    def _render_hud(self, screen: pygame.Surface) -> None:
        """Render heads-up display with turn counter, position, and alert."""
        # Turn counter
        turn_text = self._hud_font.render(
            f"Turn: {self.player_state.turn_number}",
            True,
            Colors.TEXT_PRIMARY,
        )
        screen.blit(turn_text, (10, 10))

        # Position
        pos_text = self._hud_font.render(
            f"Pos: ({self.player_state.x}, {self.player_state.y})",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(pos_text, (10, 32))

        # Alert level indicator
        if self.mission_state:
            alert = self.mission_state.alert_level
            alert_color = _ALERT_COLORS.get(alert, Colors.TEXT_SECONDARY)
            alert_text = self._hud_font.render(f"Alert: {alert.value.upper()}", True, alert_color)
            screen.blit(alert_text, (10, 54))

        # Status message (only when NOT in combat — combat has its own messages)
        if self._combat_state is None and self._message and self._message_timer > 0:
            msg_surface = self._msg_font.render(self._message, True, Colors.YELLOW)
            msg_x = (WINDOW_WIDTH - msg_surface.get_width()) // 2
            screen.blit(msg_surface, (msg_x, WINDOW_HEIGHT - 40))

    # === Minimap Rendering ===

    def _update_minimap(self) -> None:
        """Redraw the minimap surface from current map state."""
        self._minimap_surface.fill(MINIMAP_BG_COLOR)
        scale = self._minimap_scale

        # Draw tiles
        for ty in range(self.ground_map.height):
            for tx in range(self.ground_map.width):
                tile = self.ground_map.get_tile(tx, ty)
                if tile is None or tile.fog_state == FogState.UNEXPLORED:
                    continue

                color = _TILE_COLORS.get(tile.tile_type, Colors.GROUND_FLOOR)
                if tile.fog_state == FogState.EXPLORED:
                    # Darken explored tiles
                    color = (color[0] // 2, color[1] // 2, color[2] // 2)

                px = int(tx * scale)
                py = int(ty * scale)
                pw = max(1, int(scale))
                ph = max(1, int(scale))
                pygame.draw.rect(self._minimap_surface, color, (px, py, pw, ph))

        # Draw interactable markers (un-looted, visible)
        if self.mission_state:
            for obj in self.mission_state.interactables:
                if obj.looted:
                    continue
                tile = self.ground_map.get_tile(obj.x, obj.y)
                if tile and tile.fog_state == FogState.VISIBLE:
                    cx = int(obj.x * scale + scale / 2)
                    cy = int(obj.y * scale + scale / 2)
                    r = max(2, int(scale / 2))
                    pygame.draw.circle(
                        self._minimap_surface,
                        MINIMAP_INTERACTABLE_COLOR,
                        (cx, cy),
                        r,
                    )

        # Draw visible enemies
        if self.mission_state:
            for enemy in self.mission_state.enemies:
                tile = self.ground_map.get_tile(enemy.x, enemy.y)
                if tile and tile.fog_state == FogState.VISIBLE:
                    cx = int(enemy.x * scale + scale / 2)
                    cy = int(enemy.y * scale + scale / 2)
                    r = max(2, int(scale / 2))
                    pygame.draw.circle(
                        self._minimap_surface,
                        Colors.GROUND_ENEMY,
                        (cx, cy),
                        r,
                    )

        # Draw player dot (always visible, on top)
        px = int(self.player_state.x * scale + scale / 2)
        py = int(self.player_state.y * scale + scale / 2)
        r = max(2, int(scale / 2) + 1)
        pygame.draw.circle(
            self._minimap_surface,
            Colors.GROUND_PLAYER,
            (px, py),
            r,
        )

    def _render_minimap(self, screen: pygame.Surface) -> None:
        """Update and blit the minimap to the screen."""
        self._update_minimap()
        screen.blit(self._minimap_surface, (self._minimap_x, self._minimap_y))
        # Border
        pygame.draw.rect(
            screen,
            Colors.UI_BORDER,
            (self._minimap_x, self._minimap_y, MINIMAP_SIZE, MINIMAP_SIZE),
            1,
        )

    # === Combat Panel Rendering ===

    def _render_combat_panel(self, screen: pygame.Surface) -> None:
        """Render the combat overlay panel at the bottom of the screen."""
        if self._combat_state is None:
            return

        panel_y = WINDOW_HEIGHT - GROUND_COMBAT_PANEL_HEIGHT
        cs = self._combat_state

        # Panel background
        screen.blit(self._combat_panel_bg, (0, panel_y))

        # Urgent top border
        pygame.draw.line(screen, Colors.RED, (0, panel_y), (WINDOW_WIDTH, panel_y), 2)

        # === Left section: Player stats ===
        self._render_combat_player_stats(screen, 20, panel_y + 12, cs)

        # === Center section: Dice and result ===
        self._render_combat_dice(screen, WINDOW_WIDTH // 2, panel_y + 20, cs)

        # === Right section: Enemy info ===
        self._render_combat_enemy_info(screen, WINDOW_WIDTH - 280, panel_y + 12, cs)

        # === Bottom strip: Action hints ===
        self._render_combat_actions(screen, panel_y + GROUND_COMBAT_PANEL_HEIGHT - 35, cs)

    def _render_combat_player_stats(
        self, screen: pygame.Surface, x: int, y: int, cs: GroundCombatState
    ) -> None:
        """Render player HP and stats in combat panel."""
        label = self._combat_label_font.render("YOU", True, Colors.GROUND_PLAYER)
        screen.blit(label, (x, y))

        # HP bar
        self._render_hp_bar(screen, x, y + 20, 200, cs.player.hp, cs.player.max_hp, Colors.GREEN)

        # Shield if any
        if cs.player.shield > 0:
            shield_text = self._combat_label_font.render(
                f"Shield: {cs.player.shield}", True, (100, 180, 255)
            )
            screen.blit(shield_text, (x, y + 44))

        # Re-rolls
        if cs.player.rerolls > 0:
            reroll_text = self._combat_label_font.render(
                f"Re-rolls: {cs.player.rerolls}", True, Colors.YELLOW
            )
            screen.blit(reroll_text, (x, y + 62))

        # Momentum
        if cs.consecutive_wins >= 2:
            mom_text = self._combat_label_font.render("MOMENTUM +2!", True, (255, 200, 50))
            screen.blit(mom_text, (x, y + 80))

        # Round counter
        round_text = self._combat_label_font.render(
            f"Round {cs.round_number + 1}", True, Colors.TEXT_SECONDARY
        )
        screen.blit(round_text, (x, y + 120))

    def _render_combat_dice(
        self, screen: pygame.Surface, center_x: int, y: int, cs: GroundCombatState
    ) -> None:
        """Render dice values and exchange result."""
        if self._last_player_roll > 0:
            # Player die
            p_color = Colors.GOLD if self._last_player_roll == 6 else Colors.TEXT_PRIMARY
            p_text = self._dice_font.render(f"[{self._last_player_roll}]", True, p_color)
            screen.blit(p_text, p_text.get_rect(center=(center_x - 60, y + 30)))

            # VS label
            vs_text = self._combat_label_font.render("vs", True, Colors.TEXT_SECONDARY)
            screen.blit(vs_text, vs_text.get_rect(center=(center_x, y + 30)))

            # Enemy die
            e_color = (255, 60, 60) if self._last_enemy_roll == 6 else Colors.TEXT_PRIMARY
            e_text = self._dice_font.render(f"[{self._last_enemy_roll}]", True, e_color)
            screen.blit(e_text, e_text.get_rect(center=(center_x + 60, y + 30)))

        # Combat message
        if self._combat_message:
            msg_color = Colors.RED if "damage" in self._combat_message.lower() else Colors.YELLOW
            if "CRIT" in self._combat_message:
                msg_color = Colors.GOLD
            if "Victory" in self._combat_message or "escaped" in self._combat_message:
                msg_color = Colors.GREEN
            msg_surf = self._combat_font.render(self._combat_message, True, msg_color)
            screen.blit(msg_surf, msg_surf.get_rect(center=(center_x, y + 80)))

    def _render_combat_enemy_info(
        self, screen: pygame.Surface, x: int, y: int, cs: GroundCombatState
    ) -> None:
        """Render targeted enemy info in combat panel."""
        alive = [e for e in cs.enemies if not e.is_defeated]
        if not alive:
            return

        target = cs.enemies[cs.target_index]

        # Target indicator
        target_label = self._combat_label_font.render(f"TARGET: {target.name}", True, Colors.RED)
        screen.blit(target_label, (x, y))

        # Enemy HP bar
        hp_color = Colors.RED if target.hp <= target.max_hp * 0.25 else (220, 60, 60)
        self._render_hp_bar(screen, x, y + 20, 200, target.hp, target.max_hp, hp_color)

        # Enemy count
        if len(alive) > 1:
            count_text = self._combat_label_font.render(
                f"{len(alive)} enemies engaged (Tab to cycle)",
                True,
                Colors.TEXT_SECONDARY,
            )
            screen.blit(count_text, (x, y + 44))

        # Talk difficulty
        if target.is_automated:
            talk_text = self._combat_label_font.render(
                "Cannot talk (automated)", True, (120, 120, 120)
            )
        elif target.talk_difficulty is not None:
            talk_text = self._combat_label_font.render(
                f"Talk DC: {target.talk_difficulty}", True, Colors.TEXT_SECONDARY
            )
        else:
            talk_text = None
        if talk_text:
            screen.blit(talk_text, (x, y + 62))

    def _render_combat_actions(self, screen: pygame.Surface, y: int, cs: GroundCombatState) -> None:
        """Render action key hints at bottom of combat panel."""
        if cs.outcome != CombatOutcome.IN_PROGRESS:
            hint = self._combat_font.render("Press SPACE to continue", True, Colors.TEXT_PRIMARY)
            screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, y)))
            return

        hints: list[str] = ["[F] Fight"]
        if cs.can_analyze_weakness:
            hints.append("[A] Analyze")
        if cs.can_retreat:
            hints.append("[R] Retreat")
        # Check if talk is possible
        can_talk = not all(e.is_automated for e in cs.enemies if not e.is_defeated)
        if can_talk:
            hints.append("[T] Talk")
        hints.append("[Tab] Cycle Target")

        hint_text = "    ".join(hints)
        hint_surf = self._combat_label_font.render(hint_text, True, Colors.TEXT_PRIMARY)
        screen.blit(hint_surf, hint_surf.get_rect(center=(WINDOW_WIDTH // 2, y)))

    def _render_hp_bar(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        width: int,
        current: int,
        maximum: int,
        color: tuple[int, int, int],
    ) -> None:
        """Render a horizontal HP bar with text."""
        bar_h = scale_y(16)
        draw_bar(
            screen,
            x,
            y,
            width,
            bar_h,
            current,
            maximum,
            color,
            font=self._combat_label_font,
            border_color=Colors.TEXT_SECONDARY,
        )

    # === Input Handling ===

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle keyboard input for movement and interaction."""
        if not self.active:
            return

        # Combat mode gates all normal input
        if self._combat_state is not None:
            self._handle_combat_event(event)
            return

        # pygame_gui button events
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self._back_button:
                if self.mission_config:
                    from spacegame.models.ground_mission import MissionOutcome

                    self._end_mission(MissionOutcome.FLED)
                else:
                    self.next_state = GameState.GALAXY_MAP
                return

        if event.type != pygame.KEYDOWN:
            return

        # Escape — exit exploration
        if event.key == pygame.K_ESCAPE:
            if self.mission_config:
                from spacegame.models.ground_mission import MissionOutcome

                self._end_mission(MissionOutcome.FLED)
            else:
                self.next_state = GameState.GALAXY_MAP
            return

        # Movement keys
        if event.key in _MOVE_KEYS:
            dx, dy = _MOVE_KEYS[event.key]
            self._last_dx = dx
            self._last_dy = dy
            success, msg = self.player_state.move(dx, dy, self.ground_map)
            if success:
                self._update_camera_target()
                self._on_player_moved()
                get_audio_manager().play_sfx("ground_step")
                if "hazard" in msg.lower():
                    self._show_message(msg)
                    get_audio_manager().play_sfx("ground_alert")
            else:
                self._show_message(msg)
            return

        # Interact (E key) — interact with tile in last movement direction
        if event.key == pygame.K_e:
            target_x = self.player_state.x + self._last_dx
            target_y = self.player_state.y + self._last_dy

            # Check tile type BEFORE interaction to detect door opens
            tile_before = self.ground_map.get_tile(target_x, target_y)
            was_closed_door = (
                tile_before is not None and tile_before.tile_type == TileType.DOOR_CLOSED
            )

            # Check for un-looted interactable at target (before interact mutates)
            looted_obj = None
            if self.mission_state:
                for ia in self.mission_state.interactables:
                    if ia.x == target_x and ia.y == target_y and not ia.looted:
                        looted_obj = ia
                        break

            interactables = self.mission_state.interactables if self.mission_state else []
            success, msg = self.player_state.interact(
                self.ground_map,
                target_x,
                target_y,
                interactables=interactables,
            )
            if success:
                # Track loot from containers (check object, not message)
                if looted_obj is not None and looted_obj.looted:
                    self.total_loot_credits += looted_obj.loot_credits
                    # Track commodity drops
                    for cid, qty in looted_obj.loot_commodities.items():
                        self.total_loot_commodities[cid] = (
                            self.total_loot_commodities.get(cid, 0) + qty
                        )
                    if looted_obj.description:
                        msg = f"{looted_obj.description} (+{looted_obj.loot_credits} CR)"
                    get_audio_manager().play_sfx("ground_pickup")
                if was_closed_door:
                    get_audio_manager().play_sfx("ground_door")
                self._on_player_acted(door_opened=was_closed_door)
            self._show_message(msg)
            return

        # Wait (Space) — skip turn
        if event.key == pygame.K_SPACE:
            self.player_state.wait()
            self._on_player_acted()
            return

    # === Combat Input ===

    def _handle_combat_event(self, event: pygame.event.Event) -> None:
        """Handle input during combat mode."""
        if event.type != pygame.KEYDOWN:
            return

        cs = self._combat_state
        if cs is None:
            return

        # Combat over — Space/Enter to dismiss
        if cs.outcome != CombatOutcome.IN_PROGRESS:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._end_combat(cs.outcome)
            return

        # Fight
        if event.key == pygame.K_f:
            self._execute_fight()
            return

        # Retreat
        if event.key == pygame.K_r:
            self._execute_retreat()
            return

        # Talk
        if event.key == pygame.K_t:
            self._execute_talk()
            return

        # Analyze weakness (Priya)
        if event.key == pygame.K_a:
            self._execute_analyze()
            return

        # Cycle target
        if event.key == pygame.K_TAB:
            cs.cycle_target()
            return

    # === Combat Actions ===

    def _execute_fight(self) -> None:
        """Execute a fight exchange with dice rolls."""
        cs = self._combat_state
        if cs is None or cs.outcome != CombatOutcome.IN_PROGRESS:
            return

        player_roll = random.randint(1, 6)
        enemy_roll = random.randint(1, 6)
        self._last_player_roll = player_roll
        self._last_enemy_roll = enemy_roll

        # Apply and consume analyze weakness bonus
        extra_mod = self._analyze_bonus
        self._analyze_bonus = 0
        result = cs.execute_fight(player_roll, enemy_roll, extra_attack_mod=extra_mod)

        # Build result message
        parts: list[str] = []
        if result.player_crit:
            parts.append("CRIT!")
        if result.enemy_damage > 0:
            parts.append(f"You deal {result.enemy_damage} damage!")
        if result.player_damage > 0:
            parts.append(f"You take {result.player_damage} damage!")
        if result.player_damage == 0 and result.enemy_damage == 0:
            parts.append("Glancing blow!")
        if result.enemy_staggers:
            parts.append("Enemy staggers!")
        self._combat_message = " ".join(parts)

        self._check_combat_over()

    def _execute_retreat(self) -> None:
        """Attempt to retreat from combat."""
        cs = self._combat_state
        if cs is None or cs.outcome != CombatOutcome.IN_PROGRESS:
            return

        roll = random.randint(1, 6)
        self._last_player_roll = roll
        self._last_enemy_roll = 0

        # Generate free attack rolls for all living enemies
        alive = [e for e in cs.enemies if not e.is_defeated]
        free_attacks = [random.randint(1, 6) for _ in alive]

        retreat_mod = 0
        if self.mission_state:
            retreat_mod = self.mission_state.crew_bonuses.retreat_bonus
        success = cs.attempt_retreat(roll, retreat_mod=retreat_mod, free_attack_rolls=free_attacks)

        if success:
            self._combat_message = "You escaped!"
        else:
            self._combat_message = f"Retreat failed! (rolled {roll})"

        self._check_combat_over()

    def _execute_talk(self) -> None:
        """Attempt to talk your way out of combat."""
        cs = self._combat_state
        if cs is None or cs.outcome != CombatOutcome.IN_PROGRESS:
            return

        # Check if all enemies are automated
        alive = [e for e in cs.enemies if not e.is_defeated]
        if all(e.is_automated for e in alive):
            self._combat_message = "Can't reason with machines!"
            return

        # Pick best available social skill
        skill = None
        for s in _SOCIAL_SKILL_ORDER:
            if cs.can_use_social_skill(s):
                skill = s
                break

        if skill is None:
            self._combat_message = "No social skills left to try!"
            return

        roll = random.randint(1, 6)
        self._last_player_roll = roll
        self._last_enemy_roll = 0

        # Social modifier from crew bonuses (Tomas + SYN attribute)
        social_mod = 0
        if self.mission_state:
            social_mod = self.mission_state.crew_bonuses.talk_bonus
        free_attacks = [random.randint(1, 6) for e in alive]

        success = cs.attempt_talk(roll, social_mod, skill, free_attack_rolls=free_attacks)

        if success:
            self._combat_message = f"Talked your way out! ({skill.value})"
        else:
            self._combat_message = f"{skill.value.title()} failed! (rolled {roll})"

        self._check_combat_over()

    def _execute_analyze(self) -> None:
        """Use Priya's analyze weakness for +3 on next attack."""
        cs = self._combat_state
        if cs is None or cs.outcome != CombatOutcome.IN_PROGRESS:
            return

        if not cs.can_analyze_weakness:
            self._combat_message = "Analyze weakness not available!"
            return

        bonus = cs.use_analyze_weakness()
        self._analyze_bonus = bonus
        self._combat_message = f"Weakness found! +{bonus} to next attack."

    # === Combat Lifecycle ===

    def _start_combat(self) -> None:
        """Initialize combat state from nearby enemies."""
        if self._combat_state is not None or self.mission_state is None:
            return

        engaged = self.mission_state.get_engaged_enemies()
        if not engaged:
            return

        # Build player stats from attributes, progression, and crew bonuses
        crew_bonuses = self.mission_state.crew_bonuses
        player_stats = build_player_ground_combat_stats(
            attributes=self.mission_state.attributes,
            progression=self.mission_state.progression,
            crew_bonuses=crew_bonuses,
        )

        # Build enemy stats from templates stored on each enemy
        enemy_stats = []
        for enemy in engaged:
            try:
                stats = make_enemy_from_template(enemy.template_id)
            except KeyError:
                stats = make_enemy_from_template("guild_security")
            enemy_stats.append(stats)

        # Determine ambush / disadvantaged
        is_ambush = False
        is_disadvantaged = False

        # Check if player has adjacent cover (non-wall non-floor tiles count)
        has_cover = False
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            adj_tile = self.ground_map.get_tile(self.player_state.x + dx, self.player_state.y + dy)
            if adj_tile and adj_tile.tile_type == TileType.WALL:
                has_cover = True
                break
        if not has_cover:
            is_disadvantaged = True

        # Check retreat possibility (needs at least one open adjacent tile)
        can_retreat = False
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            ax = self.player_state.x + dx
            ay = self.player_state.y + dy
            if self.ground_map.is_walkable(ax, ay):
                can_retreat = True
                break

        self._combat_state = GroundCombatState(
            player=player_stats,
            enemies=enemy_stats,
            is_ambush=is_ambush,
            is_disadvantaged=is_disadvantaged,
            can_retreat=can_retreat,
            has_analyze_weakness=crew_bonuses.analyze_weakness_available,
        )
        self._combat_message = "COMBAT! Choose your action."
        self._last_player_roll = 0
        self._last_enemy_roll = 0
        self._analyze_bonus = 0

        get_audio_manager().play_sfx("ground_combat")
        logger.info(
            "Ground combat started: %d enemies engaged",
            len(enemy_stats),
        )

    def _end_combat(self, outcome: CombatOutcome) -> None:
        """Clean up after combat ends and apply outcome effects."""
        if self.mission_state is None:
            self._combat_state = None
            return

        engaged = self.mission_state.get_engaged_enemies()

        if outcome == CombatOutcome.VICTORY:
            # Collect loot from defeated enemies
            self._loot_earned = self.mission_state.collect_enemy_loot(engaged)

            # Accumulate mission-wide stats
            self._accumulate_combat_loot(self._loot_earned)
            self._accumulate_enemies_defeated(len(engaged))

            # Remove defeated enemies from mission state
            for enemy in engaged:
                if enemy in self.mission_state.enemies:
                    self.mission_state.enemies.remove(enemy)
            self.mission_state.alert_level = AlertLevel.ALERT
            if self._loot_earned > 0:
                self._show_message(f"Enemies defeated! Looted {self._loot_earned} CR")
            else:
                self._show_message("Enemies defeated!")

        elif outcome == CombatOutcome.DEFEAT:
            self.mission_state.alert_level = AlertLevel.ALERT
            self.was_detected = True  # Defeat implies detection
            self._show_message("You've been knocked out...")
            # End mission on defeat
            if self.mission_config:
                from spacegame.models.ground_mission import MissionOutcome

                self._end_mission(MissionOutcome.DEFEATED)

        elif outcome == CombatOutcome.RETREATED:
            self.mission_state.alert_level = AlertLevel.ALERT
            self._show_message("You escaped!")

        elif outcome == CombatOutcome.TALKED:
            self.mission_state.alert_level = AlertLevel.ALERT
            self._show_message("You talked your way out!")
            self._accumulate_enemies_talked(len(engaged))

        self._combat_state = None
        self._combat_message = ""
        logger.info("Ground combat ended: %s", outcome.value)

    def _check_combat_over(self) -> None:
        """Update combat message if combat has ended.

        Does NOT auto-end — the player must press Space to dismiss.
        Called from tests to process deferred outcomes.
        """
        if self._combat_state is None:
            return
        if self._combat_state.outcome == CombatOutcome.IN_PROGRESS:
            return

        outcome = self._combat_state.outcome
        if outcome == CombatOutcome.VICTORY:
            self._combat_message = "Victory! All enemies defeated. [SPACE]"
        elif outcome == CombatOutcome.DEFEAT:
            self._combat_message = "Defeated... You black out. [SPACE]"
        elif outcome == CombatOutcome.RETREATED:
            self._combat_message = "You escaped! [SPACE]"
        elif outcome == CombatOutcome.TALKED:
            self._combat_message = "You talked your way out! [SPACE]"

    # === Post-Action Processing ===

    def _on_player_moved(self) -> None:
        """Handle post-movement updates: fog, noise, enemy turns, exit check."""
        # Check exit tile before anything else
        self._check_exit_tile()
        if self.next_state is not None:
            return

        # Check for story triggers at player position
        self._check_story_triggers()

        # Update fog of war
        self.ground_map.update_fog_of_war(
            self.player_state.x,
            self.player_state.y,
            self._effective_vision_radius(),
        )

        # Check for tile noise
        if self.mission_state:
            noise = self.mission_state.check_tile_noise(self.player_state.x, self.player_state.y)
            if noise:
                self.mission_state.add_noise(noise)

        # Process enemy turns
        self._process_enemy_phase()

        # Track detection status
        self._check_detection()

    def _check_story_triggers(self) -> None:
        """Fire story trigger at player position if one exists."""
        if not self.mission_state:
            return
        trigger = self.mission_state.get_story_trigger_at(self.player_state.x, self.player_state.y)
        if trigger:
            text = trigger.fire()
            if text:
                self._show_story_message(text)

    def _on_player_acted(self, door_opened: bool = False) -> None:
        """Handle post-action updates: fog, noise from door, enemy turns."""
        # Update fog of war
        self.ground_map.update_fog_of_war(
            self.player_state.x,
            self.player_state.y,
            self._effective_vision_radius(),
        )

        # Door noise (reduced by Marcus's silent doors / crew bonuses)
        if door_opened and self.mission_state:
            door_radius = self.mission_state.get_door_noise_radius()
            if door_radius > 0:
                self.mission_state.add_noise(
                    NoiseEvent(
                        x=self.player_state.x,
                        y=self.player_state.y,
                        radius=door_radius,
                    )
                )

        # Process enemy turns
        self._process_enemy_phase()

    def _process_enemy_phase(self) -> None:
        """Process noise events, enemy movement, and vision checks."""
        if not self.mission_state:
            return

        self.mission_state.process_noise()
        self.mission_state.process_enemy_turns(self.player_state.turn_number)

        # Check for combat trigger
        if self.mission_state.alert_level == AlertLevel.COMBAT and self._combat_state is None:
            self._start_combat()
            return

        # Show alert level changes
        if self.mission_state.alert_level == AlertLevel.ALERT:
            self._show_message("ALERT! You've been spotted!")
            get_audio_manager().play_sfx("ground_alert")
        elif self.mission_state.alert_level == AlertLevel.SUSPICIOUS:
            self._show_message("Something alerted the guards...")
            get_audio_manager().play_sfx("ground_alert")

    def _effective_vision_radius(self) -> int:
        """Return vision radius including crew/attribute bonuses."""
        if self.mission_state:
            return self.mission_state.effective_vision_radius
        return self.player_state.vision_radius

    def _update_camera_target(self) -> None:
        """Set camera target to center on player position."""
        self._target_camera_x = float(
            self.player_state.x * GROUND_TILE_SIZE + GROUND_TILE_SIZE // 2
        )
        self._target_camera_y = float(
            self.player_state.y * GROUND_TILE_SIZE + GROUND_TILE_SIZE // 2
        )

    def _show_message(self, msg: str) -> None:
        """Display a timed status message."""
        self._message = msg
        self._message_timer = 2.0

    def _show_story_message(self, msg: str) -> None:
        """Display a story trigger message with extended duration."""
        self._message = msg
        self._message_timer = 4.0
