"""Settings/configuration view.

Allows player to configure save directory, audio volume, and other settings.
"""

import pygame
import pygame_gui
from typing import Optional
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors
from spacegame.views.base_view import BaseView
from spacegame.engine.audio_manager import AudioConfig, get_audio_manager
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FontCache


class SettingsView(BaseView):
    """Settings configuration view with audio volume sliders and save directory."""

    def __init__(
        self, ui_manager: pygame_gui.UIManager, current_save_dir: Path, tutorial_manager=None
    ):
        """Initialize settings view.

        Args:
            ui_manager: pygame_gui UI manager.
            current_save_dir: Current save directory path.
            tutorial_manager: Optional tutorial manager for replay.
        """
        super().__init__()
        self.ui_manager = ui_manager

        self.current_save_dir = current_save_dir
        self.tutorial_manager = tutorial_manager
        self.new_save_dir: Optional[Path] = None
        self.should_close = False
        self.settings_changed = False

        # Snapshot original audio config for revert on cancel
        self._original_audio_config = get_audio_manager().get_config()
        self._audio_changed = False

        # Fonts
        self.title_font = FontCache.get(48)
        self.header_font = FontCache.get(28)
        self.info_font = FontCache.get(22)
        self.small_font = FontCache.get(18)

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=96)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(120)

        # UI Elements — save directory
        self.save_dir_label: Optional[pygame_gui.elements.UILabel] = None
        self.save_dir_display: Optional[pygame_gui.elements.UITextBox] = None
        self.browse_button: Optional[pygame_gui.elements.UIButton] = None
        self.reset_button: Optional[pygame_gui.elements.UIButton] = None
        self.replay_tutorial_button: Optional[pygame_gui.elements.UIButton] = None
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.apply_button: Optional[pygame_gui.elements.UIButton] = None

        # UI Elements — audio volume sliders
        self._master_slider: Optional[pygame_gui.elements.UIHorizontalSlider] = None
        self._music_slider: Optional[pygame_gui.elements.UIHorizontalSlider] = None
        self._sfx_slider: Optional[pygame_gui.elements.UIHorizontalSlider] = None
        self._ambient_slider: Optional[pygame_gui.elements.UIHorizontalSlider] = None
        self._master_label: Optional[pygame_gui.elements.UILabel] = None
        self._music_label: Optional[pygame_gui.elements.UILabel] = None
        self._sfx_label: Optional[pygame_gui.elements.UILabel] = None
        self._ambient_label: Optional[pygame_gui.elements.UILabel] = None

    def on_enter(self) -> None:
        """Create UI when entering settings view."""
        super().on_enter()
        logger.info("Opened settings")
        self._create_ui()

    def on_exit(self) -> None:
        """Clean up UI when exiting."""
        self._destroy_ui()
        super().on_exit()

    def _create_ui(self) -> None:
        """Create settings UI."""
        panel_width = 800
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        y = 100

        # === Audio Section ===
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(panel_x, y, panel_width, 30),
            text="Audio",
            manager=self.ui_manager,
        )
        y += 35

        audio_cfg = get_audio_manager().get_config()
        label_w = 140
        slider_w = panel_width - label_w - 70
        slider_h = 25
        val_w = 50

        slider_defs = [
            ("Master", audio_cfg.master_volume, "_master"),
            ("Music", audio_cfg.music_volume, "_music"),
            ("SFX", audio_cfg.sfx_volume, "_sfx"),
            ("Ambient", audio_cfg.ambient_volume, "_ambient"),
        ]

        for display_name, value, attr_prefix in slider_defs:
            pct = int(value * 100)
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(panel_x, y, label_w, slider_h),
                text=f"{display_name}:",
                manager=self.ui_manager,
            )
            setattr(self, f"{attr_prefix}_label", label)

            slider = pygame_gui.elements.UIHorizontalSlider(
                relative_rect=pygame.Rect(panel_x + label_w, y, slider_w, slider_h),
                start_value=pct,
                value_range=(0, 100),
                manager=self.ui_manager,
            )
            setattr(self, f"{attr_prefix}_slider", slider)

            # Percentage display
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(
                    panel_x + label_w + slider_w + 5, y, val_w, slider_h
                ),
                text=f"{pct}%",
                manager=self.ui_manager,
                object_id=pygame_gui.core.ObjectID(
                    f"#{attr_prefix}_pct", "@volume_pct"
                ),
            )
            y += slider_h + 8

        y += 15

        # === Save Directory Section ===
        self.save_dir_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(panel_x, y, panel_width, 30),
            text="Save Directory:",
            manager=self.ui_manager,
        )
        y += 35

        save_dir_str = str(self.current_save_dir)
        self.save_dir_display = pygame_gui.elements.UITextBox(
            html_text=f"<font size=4>{save_dir_str}</font>",
            relative_rect=pygame.Rect(panel_x, y, panel_width - 160, 50),
            manager=self.ui_manager,
        )

        self.browse_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x + panel_width - 140, y, 140, 50),
            text="BROWSE",
            manager=self.ui_manager,
        )
        y += 60

        self.reset_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x, y, 200, 40),
            text="RESET TO DEFAULT",
            manager=self.ui_manager,
        )
        y += 55

        # Info text
        info_lines = [
            "Save files will be stored in this directory.",
            "Changing this will not move existing save files.",
        ]
        for line in info_lines:
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(panel_x, y, panel_width, 22),
                text=line,
                manager=self.ui_manager,
            )
            y += 22
        y += 20

        # === Tutorial Section ===
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(panel_x, y, panel_width, 30),
            text="Tutorial:",
            manager=self.ui_manager,
        )
        y += 35
        self.replay_tutorial_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x, y, 200, 40),
            text="REPLAY TUTORIAL",
            manager=self.ui_manager,
        )

        # === Bottom buttons ===
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x, WINDOW_HEIGHT - 80, 150, 50),
            text="BACK",
            manager=self.ui_manager,
        )

        self.apply_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x + panel_width - 150, WINDOW_HEIGHT - 80, 150, 50),
            text="APPLY",
            manager=self.ui_manager,
        )
        self.apply_button.disable()

    def _destroy_ui(self) -> None:
        """Destroy all UI elements."""
        for elem in [
            self.save_dir_label, self.save_dir_display,
            self.browse_button, self.reset_button,
            self.replay_tutorial_button, self.back_button, self.apply_button,
            self._master_slider, self._music_slider,
            self._sfx_slider, self._ambient_slider,
            self._master_label, self._music_label,
            self._sfx_label, self._ambient_label,
        ]:
            if elem:
                elem.kill()
        # Kill percentage labels and section headers created without refs
        # (pygame_gui manager handles orphaned elements on view exit)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle settings view events."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.browse_button:
                self._browse_save_directory()

            elif event.ui_element == self.reset_button:
                self._reset_to_default()

            elif event.ui_element == self.replay_tutorial_button:
                self._replay_tutorial()

            elif event.ui_element == self.back_button:
                # Revert audio changes on cancel
                if self._audio_changed:
                    get_audio_manager().set_config(self._original_audio_config)
                    logger.info("Audio settings reverted")
                self.should_close = True

            elif event.ui_element == self.apply_button:
                logger.info("Apply settings changes")
                self.settings_changed = True
                self._audio_changed = False  # Committed — don't revert
                self.should_close = True

        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            self._handle_volume_slider(event)

    def _handle_volume_slider(self, event: pygame.event.Event) -> None:
        """Handle volume slider changes — live preview."""
        audio = get_audio_manager()
        slider_map = {
            id(self._master_slider): ("master", audio.set_master_volume, "#_master_pct"),
            id(self._music_slider): ("music", audio.set_music_volume, "#_music_pct"),
            id(self._sfx_slider): ("sfx", audio.set_sfx_volume, "#_sfx_pct"),
            id(self._ambient_slider): ("ambient", audio.set_ambient_volume, "#_ambient_pct"),
        }

        elem_id = id(event.ui_element)
        if elem_id in slider_map:
            name, setter, pct_obj_id = slider_map[elem_id]
            value = event.value / 100.0
            setter(value)
            self._audio_changed = True
            self.apply_button.enable()

            # Update percentage label
            pct_text = f"{int(event.value)}%"
            for elem in self.ui_manager.get_sprite_group():
                if (
                    hasattr(elem, "object_ids")
                    and pct_obj_id in [str(oid) for oid in elem.object_ids]
                ):
                    elem.set_text(pct_text)
                    break

    def get_audio_config(self) -> Optional[AudioConfig]:
        """Get the current audio config if audio settings were changed."""
        if self._audio_changed or self.settings_changed:
            return get_audio_manager().get_config()
        return None

    def _browse_save_directory(self) -> None:
        """Open directory browser to select save directory."""
        try:
            # Use tkinter file dialog (cross-platform)
            root = tk.Tk()
            root.withdraw()  # Hide main window

            selected_dir = filedialog.askdirectory(
                title="Select Save Directory", initialdir=str(self.current_save_dir)
            )

            if selected_dir:
                self.new_save_dir = Path(selected_dir)
                logger.info(f"Selected new save directory: {self.new_save_dir}")

                # Update display
                self.save_dir_display.kill()
                self.save_dir_display = pygame_gui.elements.UITextBox(
                    html_text=f"<font size=4>{str(self.new_save_dir)}</font>",
                    relative_rect=pygame.Rect((WINDOW_WIDTH - 800) // 2, 160, 640, 60),
                    manager=self.ui_manager,
                )

                # Enable apply button
                self.apply_button.enable()

        except Exception as e:
            logger.error(f"Failed to open directory browser: {e}")

    def _replay_tutorial(self) -> None:
        """Reset and replay the tutorial."""
        if self.tutorial_manager:
            self.tutorial_manager.reset_tutorial()
            logger.info("Tutorial reset for replay")

    def _reset_to_default(self) -> None:
        """Reset save directory to default."""
        import os

        # Calculate default directory
        if os.name == "nt":  # Windows
            appdata = os.getenv("APPDATA")
            default_dir = Path(appdata) / "SpaceGame" / "saves"
        else:  # Unix/Mac
            home = Path.home()
            default_dir = home / ".spacegame" / "saves"

        self.new_save_dir = default_dir
        logger.info(f"Reset to default save directory: {self.new_save_dir}")

        # Update display
        panel_x = (WINDOW_WIDTH - 800) // 2
        self.save_dir_display.kill()
        self.save_dir_display = pygame_gui.elements.UITextBox(
            html_text=f"<font size=4>{str(self.new_save_dir)}</font>",
            relative_rect=pygame.Rect(panel_x, 160, 640, 60),
            manager=self.ui_manager,
        )

        # Enable apply button
        self.apply_button.enable()

    def update(self, dt: float) -> None:
        """Update settings view."""
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """Render settings view."""
        # Animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title = self.title_font.render("SETTINGS", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 50))
        screen.blit(title, title_rect)

    def should_close_dialog(self) -> bool:
        """Check if settings dialog should close."""
        result = self.should_close
        self.should_close = False
        return result

    def has_changes(self) -> bool:
        """Check if settings were changed and applied."""
        return self.settings_changed

    def get_new_save_directory(self) -> Optional[Path]:
        """Get the new save directory if changed."""
        return self.new_save_dir
