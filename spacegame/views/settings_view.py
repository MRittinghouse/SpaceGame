"""Settings/configuration view.

Allows player to configure save directory, audio volume, and other settings.
"""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import pygame
import pygame_gui

from spacegame.config import (
    FULLSCREEN,
    SUPPORTED_RESOLUTIONS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    scale_x,
    scale_y,
)
from spacegame.engine.audio_manager import AudioConfig, get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FONT_BODY, FONT_DISPLAY, FONT_SM, FONT_XL, get_font
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView


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
        # Settings uses its own UIManager so its elements don't mix with
        # the game's main ui_manager. This prevents button overlap when
        # settings is opened from any context (main menu, pause, in-game).
        self._own_ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.ui_manager = self._own_ui_manager
        self._game_ui_manager = ui_manager  # Keep reference for theme compat

        self.current_save_dir = current_save_dir
        self.tutorial_manager = tutorial_manager
        self.new_save_dir: Optional[Path] = None
        self.should_close = False
        self.settings_changed = False

        # Snapshot original audio config for revert on cancel
        self._original_audio_config = get_audio_manager().get_config()
        self._audio_changed = False

        # Fonts
        self.title_font = get_font("header", FONT_DISPLAY)
        self.header_font = get_font("header", FONT_XL)
        self.info_font = get_font("dialogue", FONT_BODY)
        self.small_font = get_font("dialogue", FONT_SM)

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=96)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(255)  # Fully opaque — covers all underlying UI

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

        # UI Elements — display settings
        self._resolution_buttons: list[pygame_gui.elements.UIButton] = []
        self._fullscreen_button: Optional[pygame_gui.elements.UIButton] = None
        self._selected_resolution: tuple[int, int] = (WINDOW_WIDTH, WINDOW_HEIGHT)
        self._selected_fullscreen: bool = FULLSCREEN
        self._restart_label: Optional[pygame_gui.elements.UILabel] = None

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
        self._misc_labels: list[pygame_gui.elements.UILabel] = []
        panel_width = scale_x(800)
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        y = scale_y(100)

        # === Audio Section ===
        self._misc_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(panel_x, y, panel_width, 30),
                text="Audio",
                manager=self.ui_manager,
            )
        )
        y += 35

        audio_cfg = get_audio_manager().get_config()
        label_w = scale_x(140)
        slider_w = panel_width - label_w - scale_x(70)
        slider_h = scale_y(25)
        val_w = scale_x(50)

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
            self._misc_labels.append(
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(panel_x + label_w + slider_w + 5, y, val_w, slider_h),
                    text=f"{pct}%",
                    manager=self.ui_manager,
                    object_id=pygame_gui.core.ObjectID(f"#{attr_prefix}_pct", "@volume_pct"),
                )
            )
            y += slider_h + 8

        y += 15

        # === Display Section ===
        self._misc_labels.append(
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(panel_x, y, panel_width, 30),
                text="Display",
                manager=self.ui_manager,
            )
        )
        y += 35

        # Resolution buttons
        current_res = (WINDOW_WIDTH, WINDOW_HEIGHT)
        btn_w = (panel_width - 20) // len(SUPPORTED_RESOLUTIONS)
        for i, (w, h) in enumerate(SUPPORTED_RESOLUTIONS):
            label = f"{w}x{h}"
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(panel_x + i * (btn_w + 10), y, btn_w, 35),
                text=label,
                manager=self.ui_manager,
            )
            if (w, h) == current_res:
                btn.disable()
            self._resolution_buttons.append(btn)
        y += 45

        # Fullscreen toggle
        fs_label = "Fullscreen: ON" if self._selected_fullscreen else "Fullscreen: OFF"
        self._fullscreen_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x, y, scale_x(200), scale_y(35)),
            text=fs_label,
            manager=self.ui_manager,
        )
        y += 45

        # Restart required label (hidden until display setting changes)
        self._restart_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(panel_x, y, panel_width, 22),
            text="",
            manager=self.ui_manager,
        )
        y += 30

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
            relative_rect=pygame.Rect(panel_x, y, panel_width - scale_x(160), scale_y(50)),
            manager=self.ui_manager,
        )

        self.browse_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                panel_x + panel_width - scale_x(140), y, scale_x(140), scale_y(50)
            ),
            text="BROWSE",
            manager=self.ui_manager,
        )
        y += 60

        self.reset_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x, y, scale_x(200), scale_y(40)),
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
            self._misc_labels.append(
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(panel_x, y, panel_width, 22),
                    text=line,
                    manager=self.ui_manager,
                )
            )
            y += 22
        y += 20

        # === Bottom buttons ===
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                panel_x, WINDOW_HEIGHT - scale_y(110), scale_x(150), scale_y(44)
            ),
            text="BACK",
            manager=self.ui_manager,
        )

        self.apply_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                panel_x + panel_width - scale_x(150),
                WINDOW_HEIGHT - scale_y(110),
                scale_x(150),
                scale_y(44),
            ),
            text="APPLY",
            manager=self.ui_manager,
        )
        self.apply_button.disable()

    def _destroy_ui(self) -> None:
        """Destroy all UI elements."""
        for elem in [
            self.save_dir_label,
            self.save_dir_display,
            self.browse_button,
            self.reset_button,
            self.back_button,
            self.apply_button,
            self._master_slider,
            self._music_slider,
            self._sfx_slider,
            self._ambient_slider,
            self._master_label,
            self._music_label,
            self._sfx_label,
            self._ambient_label,
            self._fullscreen_button,
            self._restart_label,
        ]:
            if elem:
                elem.kill()
        for btn in self._resolution_buttons:
            btn.kill()
        self._resolution_buttons = []
        for label in getattr(self, "_misc_labels", []):
            label.kill()
        self._misc_labels = []

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle settings view events."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.browse_button:
                self._browse_save_directory()

            elif event.ui_element == self.reset_button:
                self._reset_to_default()

            elif event.ui_element == self._fullscreen_button:
                self._selected_fullscreen = not self._selected_fullscreen
                fs_label = "Fullscreen: ON" if self._selected_fullscreen else "Fullscreen: OFF"
                self._fullscreen_button.set_text(fs_label)
                self.apply_button.enable()
                if self._restart_label:
                    self._restart_label.set_text("Restart required to apply display changes")

            elif event.ui_element in self._resolution_buttons:
                idx = self._resolution_buttons.index(event.ui_element)
                self._selected_resolution = SUPPORTED_RESOLUTIONS[idx]
                # Update button states
                for i, btn in enumerate(self._resolution_buttons):
                    if i == idx:
                        btn.disable()
                    else:
                        btn.enable()
                self.apply_button.enable()
                if self._restart_label:
                    self._restart_label.set_text("Restart required to apply display changes")

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
            _name, setter, pct_obj_id = slider_map[elem_id]
            # Apply logarithmic curve so volume changes feel perceptually linear.
            # Linear sliders sound wrong because human hearing is logarithmic.
            linear = event.value / 100.0
            value = linear * linear  # Quadratic curve: gentle at top, steep near zero
            setter(value)
            self._audio_changed = True
            self.apply_button.enable()

            # Update percentage label
            pct_text = f"{int(event.value)}%"
            for elem in self.ui_manager.get_sprite_group().sprites():
                if hasattr(elem, "object_ids") and pct_obj_id in [
                    str(oid) for oid in elem.object_ids
                ]:
                    elem.set_text(pct_text)
                    break

    def get_audio_config(self) -> Optional[AudioConfig]:
        """Get the current audio config if audio settings were changed."""
        if self._audio_changed or self.settings_changed:
            return get_audio_manager().get_config()
        return None

    def get_display_settings(self) -> dict:
        """Get the selected display settings for persistence.

        Returns:
            Dict with 'resolution' and 'fullscreen' keys.
        """
        return {
            "resolution": list(self._selected_resolution),
            "fullscreen": self._selected_fullscreen,
        }

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
                    html_text=f"<font size=4>{self.new_save_dir!s}</font>",
                    relative_rect=pygame.Rect(
                        (WINDOW_WIDTH - scale_x(800)) // 2, scale_y(160), scale_x(640), scale_y(60)
                    ),
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
        panel_x = (WINDOW_WIDTH - scale_x(800)) // 2
        self.save_dir_display.kill()
        self.save_dir_display = pygame_gui.elements.UITextBox(
            html_text=f"<font size=4>{self.new_save_dir!s}</font>",
            relative_rect=pygame.Rect(panel_x, scale_y(160), scale_x(640), scale_y(60)),
            manager=self.ui_manager,
        )

        # Enable apply button
        self.apply_button.enable()

    def update(self, dt: float) -> None:
        """Update settings view."""
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """Render settings view."""
        # Full-screen opaque background (covers game underneath completely)
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Settings panel background (dark card for readability)
        panel_w = scale_x(840)
        panel_h = WINDOW_HEIGHT - scale_y(40)
        panel_x = (WINDOW_WIDTH - panel_w) // 2
        panel_y = scale_y(20)
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((10, 14, 25, 240))
        screen.blit(panel_surf, (panel_x, panel_y))
        pygame.draw.rect(
            screen, (40, 50, 70), (panel_x, panel_y, panel_w, panel_h), 1, border_radius=8
        )

        # Title
        title = self.title_font.render("SETTINGS", True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, scale_y(50)))
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
