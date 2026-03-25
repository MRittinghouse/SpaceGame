"""Sprite sheet and animation system for pixel art assets.

Provides SpriteSheet for frame extraction with nearest-neighbor scaling,
AnimationDef for defining named frame sequences, AnimatedSprite for
managing frame-based animation playback, SpriteManager for asset loading
and caching, and scale_pixel_art for safe nearest-neighbor scaling.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import pygame

from spacegame.utils.logger import logger


def res_scale(base_scale: int) -> int:
    """Compute a resolution-aware sprite scale factor.

    Scales the base factor proportionally to the active WINDOW_HEIGHT
    relative to the 720p reference. At 720p returns the base unchanged;
    at 1080p returns base * 1.5 (rounded).

    Use this for explicit ``scale=`` arguments that override SpriteManager
    defaults. The convenience methods (get_commodity_icon, etc.) already
    apply this internally when ``scale=None``.

    Args:
        base_scale: Scale factor designed for 720p resolution.

    Returns:
        Proportionally scaled integer factor for the current resolution.
    """
    from spacegame.config import WINDOW_HEIGHT

    return max(1, round(base_scale * WINDOW_HEIGHT / 720))


# Keep private alias for internal use in SpriteManager defaults
_res_scale = res_scale


class SpriteSheet:
    """Extracts and scales frames from a horizontal sprite strip.

    Frames are pre-extracted and pre-scaled on construction to avoid
    per-frame allocation in the game loop.

    Attributes:
        frame_count: Number of frames in the sheet.
    """

    def __init__(
        self,
        surface: pygame.Surface,
        frame_width: int,
        frame_height: int,
        scale: int = 1,
    ) -> None:
        """Initialize sprite sheet and extract all frames.

        Args:
            surface: Source surface containing the horizontal strip.
            frame_width: Width of each frame in native pixels.
            frame_height: Height of each frame in native pixels.
            scale: Integer scale factor (nearest-neighbor).
        """
        self._frame_width = frame_width
        self._frame_height = frame_height
        self._scale = scale
        self.frame_count = surface.get_width() // frame_width

        self._frames: list[pygame.Surface] = []
        for i in range(self.frame_count):
            rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
            frame = surface.subsurface(rect).copy()
            if scale != 1:
                scaled_size = (frame_width * scale, frame_height * scale)
                frame = pygame.transform.scale(frame, scaled_size)
            self._frames.append(frame)

    def get_frame(self, index: int) -> pygame.Surface:
        """Get a frame by index, wrapping with modulo.

        Args:
            index: Frame index (wraps around).

        Returns:
            The frame surface at the given index.
        """
        return self._frames[index % self.frame_count]


@dataclass
class AnimationDef:
    """Defines a named animation as a sequence of frame indices.

    Attributes:
        name: Animation name (e.g. "idle", "hit", "destroy").
        frames: List of frame indices into the SpriteSheet.
        frame_duration: Seconds each frame is displayed.
        loop: Whether the animation loops. Defaults to True.
    """

    name: str
    frames: list[int]
    frame_duration: float
    loop: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "AnimationDef":
        """Create an AnimationDef from a dictionary.

        Args:
            data: Dict with 'name', 'frames', 'frame_duration',
                  and optional 'loop' keys.

        Returns:
            New AnimationDef instance.
        """
        return cls(
            name=data["name"],
            frames=data["frames"],
            frame_duration=data["frame_duration"],
            loop=data.get("loop", True),
        )


class AnimatedSprite:
    """Manages frame-based animation playback on a SpriteSheet.

    Lightweight controller that tracks current animation, frame index,
    and elapsed time. Multiple AnimatedSprites can share one SpriteSheet.
    """

    def __init__(
        self,
        sheet: SpriteSheet,
        animations: dict[str, AnimationDef],
    ) -> None:
        """Initialize with a sprite sheet and animation definitions.

        Args:
            sheet: The SpriteSheet to draw frames from.
            animations: Map of animation name to AnimationDef.
        """
        self._sheet = sheet
        self._animations = animations
        self._current_anim: Optional[AnimationDef] = None
        self._frame_index: int = 0
        self._elapsed: float = 0.0
        self._finished: bool = False
        self._on_complete: Optional[Callable[[], None]] = None
        self._callback_fired: bool = False

    @property
    def current_animation(self) -> Optional[str]:
        """Name of the currently playing animation, or None."""
        if self._current_anim is None:
            return None
        return self._current_anim.name

    def play(
        self,
        name: str,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        """Start playing a named animation from the beginning.

        If the animation name doesn't exist, this is a no-op.

        Args:
            name: Animation name to play.
            on_complete: Optional callback fired when a non-looping
                         animation finishes.
        """
        anim = self._animations.get(name)
        if anim is None:
            return
        self._current_anim = anim
        self._frame_index = 0
        self._elapsed = 0.0
        self._finished = False
        self._on_complete = on_complete
        self._callback_fired = False

    def update(self, dt: float) -> None:
        """Advance the animation by dt seconds.

        Args:
            dt: Time elapsed since last update, in seconds.
        """
        if self._current_anim is None or self._finished:
            return

        self._elapsed += dt
        anim = self._current_anim
        frames_advanced = int(self._elapsed / anim.frame_duration)

        if frames_advanced > 0:
            self._elapsed -= frames_advanced * anim.frame_duration
            self._frame_index += frames_advanced

            if anim.loop:
                self._frame_index %= len(anim.frames)
            elif self._frame_index >= len(anim.frames):
                self._frame_index = len(anim.frames) - 1
                self._finished = True
                if self._on_complete and not self._callback_fired:
                    self._callback_fired = True
                    self._on_complete()

    def get_surface(self) -> Optional[pygame.Surface]:
        """Get the current frame surface.

        Returns:
            The current frame's Surface, or None if no animation is playing.
        """
        if self._current_anim is None:
            return None
        sheet_frame_index = self._current_anim.frames[self._frame_index]
        return self._sheet.get_frame(sheet_frame_index)

    def is_finished(self) -> bool:
        """Check if the current animation has finished.

        Returns:
            True if a non-looping animation has completed, False otherwise.
        """
        return self._finished


# ============================================================================
# Scaling Utility
# ============================================================================


def scale_pixel_art(surface: pygame.Surface, factor: int) -> pygame.Surface:
    """Scale a surface using nearest-neighbor interpolation.

    Always uses pygame.transform.scale (NOT smoothscale) to preserve
    hard pixel edges required for pixel art.

    Args:
        surface: Source surface to scale.
        factor: Integer scale multiplier.

    Returns:
        Scaled surface.
    """
    new_size = (surface.get_width() * factor, surface.get_height() * factor)
    return pygame.transform.scale(surface, new_size)


# ============================================================================
# SpriteManager
# ============================================================================


class SpriteManager:
    """Loads, caches, and provides access to sprite assets.

    Caches SpriteSheets (heavy, shared) and static surfaces.
    Creates fresh AnimatedSprites (lightweight, per-entity) on demand.
    All methods return Optional types — None means the asset is missing
    and the caller should fall back to procedural rendering.

    Expected directory layout under assets_dir:
        sprites/<category>/<id>.png          (static sprites)
        sprites/<category>/<id>_sheet.png    (sprite sheets)
        animations/<config>.json             (animation definitions)
    """

    def __init__(self, assets_dir: str | Path) -> None:
        """Initialize SpriteManager.

        Args:
            assets_dir: Root directory for sprite assets.
        """
        self._assets_dir = Path(assets_dir)
        self._sheet_cache: dict[str, Optional[SpriteSheet]] = {}
        self._static_cache: dict[str, Optional[pygame.Surface]] = {}
        self._anim_cache: dict[str, dict[str, AnimationDef]] = {}

    # --- Low-level API ---

    def get_sheet(
        self,
        category: str,
        sprite_id: str,
        frame_width: int,
        frame_height: int,
        scale: int = 1,
    ) -> Optional[SpriteSheet]:
        """Load or retrieve a cached SpriteSheet.

        Looks for: sprites/<category>/<sprite_id>_sheet.png

        Args:
            category: Subdirectory under sprites/ (e.g. "ships/player").
            sprite_id: Base name of the sprite (without _sheet.png).
            frame_width: Width of each frame in native pixels.
            frame_height: Height of each frame in native pixels.
            scale: Integer scale factor for nearest-neighbor scaling.

        Returns:
            SpriteSheet if the file exists, None otherwise.
        """
        cache_key = f"{category}/{sprite_id}_{scale}"
        if cache_key in self._sheet_cache:
            return self._sheet_cache[cache_key]

        path = self._assets_dir / "sprites" / category / f"{sprite_id}_sheet.png"
        if not path.exists():
            self._sheet_cache[cache_key] = None
            return None

        try:
            surface = pygame.image.load(str(path))
            if pygame.display.get_surface() is not None:
                surface = surface.convert_alpha()
            sheet = SpriteSheet(surface, frame_width, frame_height, scale)
            self._sheet_cache[cache_key] = sheet
            logger.debug(f"Loaded sprite sheet: {path} ({sheet.frame_count} frames)")
            return sheet
        except Exception as e:
            logger.error(f"Failed to load sprite sheet {path}: {e}")
            self._sheet_cache[cache_key] = None
            return None

    def get_sprite(
        self,
        category: str,
        sprite_id: str,
        frame_width: int,
        frame_height: int,
        scale: int = 1,
        animations: Optional[dict[str, AnimationDef]] = None,
    ) -> Optional[AnimatedSprite]:
        """Create an AnimatedSprite backed by a cached SpriteSheet.

        Each call returns a new AnimatedSprite instance (lightweight).
        The underlying SpriteSheet is shared and cached.

        Args:
            category: Subdirectory under sprites/.
            sprite_id: Base name of the sprite.
            frame_width: Width of each frame in native pixels.
            frame_height: Height of each frame in native pixels.
            scale: Integer scale factor.
            animations: Animation definitions. If None, a default
                        single-frame "idle" animation is created.

        Returns:
            AnimatedSprite if the sheet file exists, None otherwise.
        """
        sheet = self.get_sheet(category, sprite_id, frame_width, frame_height, scale)
        if sheet is None:
            return None

        if animations is None:
            # Default: use all frames as a looping idle
            animations = {
                "idle": AnimationDef(
                    name="idle",
                    frames=list(range(sheet.frame_count)),
                    frame_duration=0.5,
                    loop=True,
                ),
            }

        return AnimatedSprite(sheet=sheet, animations=animations)

    def get_static_sprite(
        self,
        category: str,
        sprite_id: str,
        scale: int = 1,
    ) -> Optional[pygame.Surface]:
        """Load a static (non-animated) sprite image.

        Looks for: sprites/<category>/<sprite_id>.png

        Args:
            category: Subdirectory under sprites/.
            sprite_id: Base name of the sprite (without .png).
            scale: Integer scale factor for nearest-neighbor scaling.

        Returns:
            Scaled pygame.Surface if the file exists, None otherwise.
        """
        cache_key = f"static:{category}/{sprite_id}_{scale}"
        if cache_key in self._static_cache:
            return self._static_cache[cache_key]

        path = self._assets_dir / "sprites" / category / f"{sprite_id}.png"
        if not path.exists():
            self._static_cache[cache_key] = None
            return None

        try:
            surface = pygame.image.load(str(path))
            if pygame.display.get_surface() is not None:
                surface = surface.convert_alpha()
            if scale != 1:
                surface = scale_pixel_art(surface, scale)
            self._static_cache[cache_key] = surface
            logger.debug(f"Loaded static sprite: {path}")
            return surface
        except Exception as e:
            logger.error(f"Failed to load static sprite {path}: {e}")
            self._static_cache[cache_key] = None
            return None

    def load_animation_config(self, config_filename: str) -> dict[str, AnimationDef]:
        """Load animation definitions from a JSON config file.

        Looks for: animations/<config_filename>

        The JSON format is a dict of animation name to definition:
        {
            "idle": {"name": "idle", "frames": [0, 1], "frame_duration": 0.3, "loop": true},
            "hit": {"name": "hit", "frames": [2, 3, 2], "frame_duration": 0.08, "loop": false}
        }

        Args:
            config_filename: Filename within the animations/ directory.

        Returns:
            Dict of animation name to AnimationDef. Empty dict if
            the config file is missing or invalid.
        """
        if config_filename in self._anim_cache:
            return self._anim_cache[config_filename]

        path = self._assets_dir / "animations" / config_filename
        if not path.exists():
            self._anim_cache[config_filename] = {}
            return {}

        try:
            with open(path, "r") as f:
                raw = json.load(f)
            defs: dict[str, AnimationDef] = {}
            for name, data in raw.items():
                defs[name] = AnimationDef.from_dict(data)
            self._anim_cache[config_filename] = defs
            logger.debug(f"Loaded animation config: {path} ({len(defs)} animations)")
            return defs
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to load animation config {path}: {e}")
            self._anim_cache[config_filename] = {}
            return {}

    def clear_cache(self) -> None:
        """Clear all cached sheets, surfaces, and animation configs."""
        self._sheet_cache.clear()
        self._static_cache.clear()
        self._anim_cache.clear()

    # --- Convenience API ---

    def get_ship_sprite(
        self, ship_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get a player ship sprite surface.

        Tries animated sheet first (sprites/ships/player/<ship_id>_sheet.png),
        falls back to static sprite (sprites/ships/player/<ship_id>.png).
        Native size: 32x32.

        Args:
            ship_id: Ship type identifier (e.g. "shuttle").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            pygame.Surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        anims = self.load_animation_config("ship_anims.json") or None
        animated = self.get_sprite("ships/player", ship_id, 32, 32, scale, anims)
        if animated is not None:
            animated.play("idle")
            return animated.get_surface()
        return self.get_static_sprite("ships/player", ship_id, scale)

    def get_enemy_sprite(
        self, enemy_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get an enemy ship sprite surface.

        Tries animated sheet first (sprites/ships/enemies/<enemy_id>_sheet.png),
        falls back to static sprite (sprites/ships/enemies/<enemy_id>.png).
        Native size: 32x32.

        Args:
            enemy_id: Enemy template identifier (e.g. "pirate_scout").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            pygame.Surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        anims = self.load_animation_config("ship_anims.json") or None
        animated = self.get_sprite("ships/enemies", enemy_id, 32, 32, scale, anims)
        if animated is not None:
            animated.play("idle")
            return animated.get_surface()
        return self.get_static_sprite("ships/enemies", enemy_id, scale)

    def get_portrait_sprite(
        self, npc_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get an NPC portrait sprite surface.

        Tries animated sheet first (sprites/portraits/<npc_id>_sheet.png),
        falls back to static sprite (sprites/portraits/<npc_id>.png).
        Native size: 50x60.

        Args:
            npc_id: NPC identifier (e.g. "officer_larsen").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            pygame.Surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        anims = self.load_animation_config("portrait_anims.json") or None
        animated = self.get_sprite("portraits", npc_id, 50, 60, scale, anims)
        if animated is not None:
            animated.play("idle")
            return animated.get_surface()
        return self.get_static_sprite("portraits", npc_id, scale)

    def get_commodity_icon(
        self, commodity_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get a commodity icon surface.

        Loads from sprites/commodities/<commodity_id>.png (16x16 native).

        Args:
            commodity_id: Commodity identifier (e.g. "iron_ore").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        return self.get_static_sprite("commodities", commodity_id, scale)

    def get_faction_emblem(
        self, faction_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get a faction emblem surface.

        Loads from sprites/factions/<faction_id>.png (24x24 native).

        Args:
            faction_id: Faction identifier (e.g. "commerce_guild").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        return self.get_static_sprite("factions", faction_id, scale)

    def get_ground_tile(
        self,
        tile_type: str,
        faction_id: str = "neutral",
        scale: Optional[int] = None,
    ) -> Optional[pygame.Surface]:
        """Get a ground tile surface.

        Loads from sprites/ground_tiles/<faction_id>/<tile_type>.png
        (16x16 native).

        Args:
            tile_type: Tile type name (e.g. "floor", "wall").
            faction_id: Faction tileset to use. Defaults to "neutral".
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(3)
        category = f"ground_tiles/{faction_id}"
        return self.get_static_sprite(category, tile_type, scale)

    def get_ground_tile_animated(
        self,
        tile_type: str,
        faction_id: str = "neutral",
        scale: Optional[int] = None,
    ) -> Optional["AnimatedSprite"]:
        """Get an animated ground tile sprite if a sheet exists.

        Loads from sprites/ground_tiles/<faction_id>/<tile_type>_sheet.png
        with animation config from ground_tile_anims.json.

        Args:
            tile_type: Tile type name (e.g. "noisy_floor").
            faction_id: Faction tileset to use. Defaults to "neutral".
            scale: Display scale factor. Defaults to 3 (48x48 display).

        Returns:
            AnimatedSprite if the sheet exists, None otherwise.
        """
        category = f"ground_tiles/{faction_id}"
        anims = self.load_animation_config("ground_tile_anims.json")
        if not anims:
            return None
        if scale is None:
            scale = _res_scale(3)
        return self.get_sprite(category, tile_type, 16, 16, scale, anims)

    def get_system_portrait(
        self, system_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get a star system portrait surface.

        Loads from sprites/systems/<system_id>.png (80x60 native).

        Args:
            system_id: System identifier (e.g. "nexus_prime").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(1)
        return self.get_static_sprite("systems", system_id, scale)

    def get_upgrade_icon(
        self, upgrade_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get an upgrade icon surface.

        Loads from sprites/upgrades/<upgrade_id>.png (16x16 native).

        Args:
            upgrade_id: Upgrade identifier (e.g. "cargo_bay_ext").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        return self.get_static_sprite("upgrades", upgrade_id, scale)

    def get_ground_player_sprite(self, scale: Optional[int] = None) -> Optional[pygame.Surface]:
        """Get the ground player character sprite.

        Loads from sprites/ground_tiles/player.png (16x16 native).

        Args:
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(3)
        return self.get_static_sprite("ground_tiles", "player", scale)

    def get_ship_animated(
        self, ship_id: str, category: str = "player", scale: Optional[int] = None
    ) -> Optional[AnimatedSprite]:
        """Get an AnimatedSprite for a ship (player or enemy).

        Returns an AnimatedSprite with idle animation if a sprite sheet exists,
        or a single-frame AnimatedSprite from a static PNG. Returns None if
        neither exists.

        Args:
            ship_id: Ship type identifier (e.g. "shuttle").
            category: "player" or "enemies".
            scale: Display scale factor.

        Returns:
            AnimatedSprite if any asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        subdir = f"ships/{category}"
        anims = self.load_animation_config("ship_anims.json") or None
        animated = self.get_sprite(subdir, ship_id, 32, 32, scale, anims)
        if animated is not None:
            animated.play("idle")
            return animated
        # Try static sprite as single-frame animation
        static = self.get_static_sprite(subdir, ship_id, scale)
        if static is None:
            return None
        # Wrap static surface in a single-frame SpriteSheet + AnimatedSprite
        sheet = SpriteSheet(static, static.get_width(), static.get_height(), 1)
        anim = AnimatedSprite(
            sheet=sheet,
            animations={"idle": AnimationDef("idle", [0], 1.0, loop=True)},
        )
        anim.play("idle")
        return anim

    def get_portrait_animated(
        self, npc_id: str, scale: Optional[int] = None
    ) -> Optional[AnimatedSprite]:
        """Get an AnimatedSprite for an NPC portrait.

        Returns an AnimatedSprite with idle animation if a sprite sheet exists,
        or a single-frame AnimatedSprite from a static PNG. Returns None if
        neither exists.

        Args:
            npc_id: NPC identifier (e.g. "officer_larsen").
            scale: Display scale factor.

        Returns:
            AnimatedSprite if any asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        anims = self.load_animation_config("portrait_anims.json") or None
        animated = self.get_sprite("portraits", npc_id, 50, 60, scale, anims)
        if animated is not None:
            animated.play("idle")
            return animated
        static = self.get_static_sprite("portraits", npc_id, scale)
        if static is None:
            return None
        sheet = SpriteSheet(static, static.get_width(), static.get_height(), 1)
        anim = AnimatedSprite(
            sheet=sheet,
            animations={"idle": AnimationDef("idle", [0], 1.0, loop=True)},
        )
        anim.play("idle")
        return anim

    def get_skill_icon(
        self, skill_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get a skill tree icon surface.

        Loads from sprites/ui/skills/<skill_id>.png (16x16 native).

        Args:
            skill_id: Skill identifier (e.g. "negotiator").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        return self.get_static_sprite("ui/skills", skill_id, scale)

    def get_location_icon(
        self, type_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get a station hub location type icon surface.

        Loads from sprites/ui/location_types/<type_id>.png (16x16 native).

        Args:
            type_id: Location type identifier (e.g. "market", "cantina").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(2)
        return self.get_static_sprite("ui/location_types", type_id, scale)

    def get_ground_enemy_sprite(
        self, template_id: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get a ground enemy sprite by template ID.

        Loads from sprites/ground_tiles/enemies/<template_id>.png (16x16 native).

        Args:
            template_id: Enemy template identifier (e.g. "guild_security").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled surface if the asset exists, None otherwise.
        """
        if scale is None:
            scale = _res_scale(3)
        return self.get_static_sprite("ground_tiles/enemies", template_id, scale)

    # Icon order must match tools/generate_status_icons.py EFFECT_ORDER
    _STATUS_ICON_ORDER = [
        "damage",
        "shield_restore",
        "hull_restore",
        "evasion_mod",
        "accuracy_mod",
        "shield_drain",
        "damage_reduction",
        "energy_drain",
    ]

    def get_status_icon(
        self, effect_type: str, scale: Optional[int] = None
    ) -> Optional[pygame.Surface]:
        """Get a status effect icon surface by effect type ID.

        Loads from sprites/ui/status_icons.png (96x12 sheet, 8 icons).

        Args:
            effect_type: EffectType value string (e.g. "evasion_mod").
            scale: Display scale factor. None uses resolution-aware default.

        Returns:
            Scaled icon surface if available, None otherwise.
        """
        if scale is None:
            scale = _res_scale(1)
        cache_key = f"status_icon:{effect_type}_{scale}"
        if cache_key in self._static_cache:
            return self._static_cache[cache_key]

        if effect_type not in self._STATUS_ICON_ORDER:
            self._static_cache[cache_key] = None
            return None

        idx = self._STATUS_ICON_ORDER.index(effect_type)

        # Load full sheet (cached)
        sheet_key = f"status_icon_sheet:{scale}"
        if sheet_key not in self._static_cache:
            path = self._assets_dir / "sprites" / "ui" / "status_icons.png"
            if not path.exists():
                self._static_cache[sheet_key] = None
                self._static_cache[cache_key] = None
                return None
            try:
                surface = pygame.image.load(str(path))
                if pygame.display.get_surface() is not None:
                    surface = surface.convert_alpha()
                if scale != 1:
                    surface = scale_pixel_art(surface, scale)
                self._static_cache[sheet_key] = surface
            except Exception as e:
                logger.error(f"Failed to load status icons: {e}")
                self._static_cache[sheet_key] = None
                self._static_cache[cache_key] = None
                return None

        sheet_surf = self._static_cache.get(sheet_key)
        if sheet_surf is None:
            self._static_cache[cache_key] = None
            return None

        icon_size = 12 * scale
        icon = sheet_surf.subsurface(pygame.Rect(idx * icon_size, 0, icon_size, icon_size)).copy()
        self._static_cache[cache_key] = icon
        return icon


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_sprite_manager: Optional[SpriteManager] = None


def get_sprite_manager() -> SpriteManager:
    """Get the global SpriteManager singleton.

    Creates the instance on first call using ASSETS_DIR from config.
    """
    global _sprite_manager
    if _sprite_manager is None:
        from spacegame.config import ASSETS_DIR

        _sprite_manager = SpriteManager(ASSETS_DIR)
    return _sprite_manager
