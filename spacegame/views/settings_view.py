"""
Settings/configuration view.

Allows player to configure save directory and other game settings.
"""

import pygame
import pygame_gui
from typing import Optional
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors
from spacegame.views.base_view import BaseView
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground


class SettingsView(BaseView):
    """
    Settings configuration view.

    Currently supports:
    - Save directory configuration
    - Future: Audio, graphics, controls, etc.
    """

    def __init__(
        self, ui_manager: pygame_gui.UIManager, current_save_dir: Path, tutorial_manager=None
    ):
        """
        Initialize settings view.

        Args:
            ui_manager: pygame_gui UI manager
            current_save_dir: Current save directory path
        """
        super().__init__()
        self.ui_manager = ui_manager

        self.current_save_dir = current_save_dir
        self.tutorial_manager = tutorial_manager
        self.new_save_dir: Optional[Path] = None
        self.should_close = False
        self.settings_changed = False

        # Fonts
        self.title_font = pygame.font.Font(None, 48)
        self.header_font = pygame.font.Font(None, 28)
        self.info_font = pygame.font.Font(None, 22)
        self.small_font = pygame.font.Font(None, 18)

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=96)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(120)

        # UI Elements
        self.save_dir_label: Optional[pygame_gui.elements.UILabel] = None
        self.save_dir_display: Optional[pygame_gui.elements.UITextBox] = None
        self.browse_button: Optional[pygame_gui.elements.UIButton] = None
        self.reset_button: Optional[pygame_gui.elements.UIButton] = None
        self.replay_tutorial_button: Optional[pygame_gui.elements.UIButton] = None
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.apply_button: Optional[pygame_gui.elements.UIButton] = None

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
        start_y = 120

        # Save Directory Section
        self.save_dir_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(panel_x, start_y, panel_width, 30),
            text="Save Directory:",
            manager=self.ui_manager,
        )

        # Display current save directory
        save_dir_str = str(self.current_save_dir)
        self.save_dir_display = pygame_gui.elements.UITextBox(
            html_text=f"<font size=4>{save_dir_str}</font>",
            relative_rect=pygame.Rect(panel_x, start_y + 40, panel_width - 160, 60),
            manager=self.ui_manager,
        )

        # Browse button
        self.browse_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x + panel_width - 140, start_y + 40, 140, 60),
            text="BROWSE",
            manager=self.ui_manager,
        )

        # Reset to default button
        self.reset_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x, start_y + 120, 200, 50),
            text="RESET TO DEFAULT",
            manager=self.ui_manager,
        )

        # Info text
        info_y = start_y + 190
        info_lines = [
            "Save files will be stored in this directory.",
            "Changing this will not move existing save files.",
            "Default location: AppData/SpaceGame/saves (Windows)",
            "or ~/.spacegame/saves (Unix/Mac)",
        ]

        for i, line in enumerate(info_lines):
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(panel_x, info_y + i * 25, panel_width, 25),
                text=line,
                manager=self.ui_manager,
            )

        # Tutorial section
        tutorial_y = info_y + len(info_lines) * 25 + 30
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(panel_x, tutorial_y, panel_width, 30),
            text="Tutorial:",
            manager=self.ui_manager,
        )
        self.replay_tutorial_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(panel_x, tutorial_y + 35, 200, 50),
            text="REPLAY TUTORIAL",
            manager=self.ui_manager,
        )

        # Bottom buttons
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
        self.apply_button.disable()  # Disabled until changes made

    def _destroy_ui(self) -> None:
        """Destroy all UI elements."""
        if self.save_dir_label:
            self.save_dir_label.kill()
        if self.save_dir_display:
            self.save_dir_display.kill()
        if self.browse_button:
            self.browse_button.kill()
        if self.reset_button:
            self.reset_button.kill()
        if self.replay_tutorial_button:
            self.replay_tutorial_button.kill()
        if self.back_button:
            self.back_button.kill()
        if self.apply_button:
            self.apply_button.kill()

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
                logger.info("Close settings (no changes applied)")
                self.should_close = True

            elif event.ui_element == self.apply_button:
                logger.info("Apply settings changes")
                self.settings_changed = True
                self.should_close = True

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
