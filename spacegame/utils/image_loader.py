"""
Image asset loader for Space Trader.

Handles loading, caching, and scaling of image assets with graceful fallback.
"""

import pygame
from pathlib import Path
from typing import Optional, Dict
from spacegame.utils.logger import logger


class ImageLoader:
    """
    Centralized image loading and caching system.

    Loads images from disk, caches them in memory, and provides
    fallback handling for missing assets.
    """

    def __init__(self, base_path: Path):
        """
        Initialize image loader.

        Args:
            base_path: Base directory for image assets
        """
        self.base_path = base_path
        self._cache: Dict[str, Optional[pygame.Surface]] = {}

    def load_image(
        self,
        relative_path: str,
        scale_to: Optional[tuple[int, int]] = None,
        convert_alpha: bool = True,
    ) -> Optional[pygame.Surface]:
        """
        Load an image from disk with optional scaling and caching.

        Args:
            relative_path: Path relative to base_path (e.g., "systems/nexus_prime.png")
            scale_to: Optional (width, height) tuple to scale image
            convert_alpha: Whether to convert image with alpha channel (default True)

        Returns:
            pygame.Surface if successful, None if image not found
        """
        # Create cache key including scale info
        cache_key = f"{relative_path}_{scale_to}"

        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Build full path
        full_path = self.base_path / relative_path

        # Try to load image
        try:
            if not full_path.exists():
                logger.warning(f"Image not found: {full_path}")
                self._cache[cache_key] = None
                return None

            # Load image
            image = pygame.image.load(str(full_path))

            # Convert for performance
            if convert_alpha:
                image = image.convert_alpha()
            else:
                image = image.convert()

            # Scale if requested
            if scale_to:
                image = pygame.transform.smoothscale(image, scale_to)

            # Cache and return
            self._cache[cache_key] = image
            logger.debug(f"Loaded image: {relative_path} (scaled to {scale_to})")
            return image

        except Exception as e:
            logger.error(f"Failed to load image {relative_path}: {e}")
            self._cache[cache_key] = None
            return None

    def load_system_image(self, system_id: str, size: tuple[int, int]) -> Optional[pygame.Surface]:
        """
        Load a system/planet image by system ID.

        Args:
            system_id: System identifier (e.g., "nexus_prime")
            size: Target (width, height) for scaling

        Returns:
            pygame.Surface if found, None otherwise
        """
        return self.load_image(f"systems/{system_id}.png", scale_to=size)

    def load_background(
        self, background_name: str, size: tuple[int, int]
    ) -> Optional[pygame.Surface]:
        """
        Load a space background image.

        Args:
            background_name: Background file name without extension (e.g., "starfield")
            size: Target (width, height) for scaling

        Returns:
            pygame.Surface if found, None otherwise
        """
        return self.load_image(f"backgrounds/{background_name}.png", scale_to=size)

    def preload_all_systems(self, system_ids: list[str], size: tuple[int, int]) -> None:
        """
        Preload all system images at startup for better performance.

        Args:
            system_ids: List of system IDs to preload
            size: Target size for all images
        """
        logger.info(f"Preloading {len(system_ids)} system images...")
        for system_id in system_ids:
            self.load_system_image(system_id, size)

    def preload_all_backgrounds(self, background_names: list[str], size: tuple[int, int]) -> None:
        """
        Preload all background images at startup.

        Args:
            background_names: List of background names to preload
            size: Target size for all images
        """
        logger.info(f"Preloading {len(background_names)} background images...")
        for bg_name in background_names:
            self.load_background(bg_name, size)

    def clear_cache(self) -> None:
        """Clear the image cache to free memory."""
        self._cache.clear()
        logger.info("Image cache cleared")
