"""
Save/Load slot selection view.

Displays 12 save slots with metadata and allows player to save or load.
"""

import pygame
import pygame_gui
from typing import Optional, List, Dict, Any
from datetime import datetime

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, scale_x, scale_y
from spacegame.views.base_view import BaseView
from spacegame.save_manager import SaveManager
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.fonts import FontCache, FONT_DISPLAY, FONT_LG, FONT_MD, FONT_SM


class SaveLoadView(BaseView):
    """
    Save/Load slot selection view.

    Shows 12 save slots with metadata (name, date, credits, location, playtime).
    In save mode: Click slot to save
    In load mode: Click slot to load
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        save_manager: SaveManager,
        mode: str = "save",  # "save" or "load"
    ):
        """
        Initialize save/load view.

        Args:
            ui_manager: pygame_gui UI manager
            save_manager: SaveManager instance
            mode: "save" or "load"
        """
        super().__init__()
        self.ui_manager = ui_manager

        self.save_manager = save_manager
        self.mode = mode  # "save" or "load"
        self.selected_slot: Optional[int] = None
        self.should_close = False
        self.should_execute = False  # True when save/load should happen

        # Fonts
        self.title_font = FontCache.get(FONT_DISPLAY)
        self.header_font = FontCache.get(FONT_LG)
        self.info_font = FontCache.get(FONT_MD)
        self.small_font = FontCache.get(FONT_SM)

        # UI Elements
        self.slot_buttons: List[pygame_gui.elements.UIButton] = []
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.confirm_button: Optional[pygame_gui.elements.UIButton] = None
        self.delete_button: Optional[pygame_gui.elements.UIButton] = None

        # Slot metadata cache
        self.slot_metadata: List[Optional[Dict[str, Any]]] = []

        # Background
        self.background = AnimatedBackground("deep_space", WINDOW_WIDTH, WINDOW_HEIGHT, seed=95)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(120)

    def on_enter(self) -> None:
        """Create UI when entering save/load view."""
        super().on_enter()
        logger.info(f"Opened {self.mode} dialog")
        self._load_slot_metadata()
        self._create_ui()

    def on_exit(self) -> None:
        """Clean up UI when exiting."""
        self._destroy_ui()
        super().on_exit()

    def _load_slot_metadata(self) -> None:
        """Load metadata for all save slots."""
        self.slot_metadata = self.save_manager.get_all_save_metadata()

    def _create_ui(self) -> None:
        """Create save/load slot UI."""
        # Create 12 slot buttons in a grid (4 rows x 3 columns)
        slot_width = scale_x(350)
        slot_height = scale_y(100)
        start_x = scale_x(50)
        start_y = scale_y(100)
        spacing_x = scale_x(370)
        spacing_y = scale_y(120)

        for i in range(12):
            row = i // 3
            col = i % 3

            x = start_x + col * spacing_x
            y = start_y + row * spacing_y

            # Create slot button with metadata text
            metadata = self.slot_metadata[i]
            if metadata:
                # Slot has save data
                slot_text = self._format_slot_text(i, metadata)
            else:
                # Empty slot
                label = "Autosave" if i == 0 else f"Slot {i}"
                slot_text = f"{label}\n(Empty)"

            button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(x, y, slot_width, slot_height),
                text=slot_text,
                manager=self.ui_manager,
            )
            self.slot_buttons.append(button)

        # Back button (above HUD bar)
        from spacegame.views.cockpit_hud import HUD_BASE_HEIGHT

        hud_h = scale_y(HUD_BASE_HEIGHT)
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                scale_x(50), WINDOW_HEIGHT - hud_h - scale_y(60),
                scale_x(150), scale_y(45),
            ),
            text="BACK",
            manager=self.ui_manager,
        )

        # Confirm button (only visible when slot selected)
        if self.mode == "save":
            confirm_text = "SAVE"
        else:
            confirm_text = "LOAD"

        self.confirm_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH - scale_x(350), WINDOW_HEIGHT - scale_y(70), scale_x(150), scale_y(50)),
            text=confirm_text,
            manager=self.ui_manager,
        )
        self.confirm_button.disable()  # Disabled until slot selected

        # Delete button (only in load mode, only when slot selected)
        if self.mode == "load":
            self.delete_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(WINDOW_WIDTH - scale_x(180), WINDOW_HEIGHT - scale_y(70), scale_x(150), scale_y(50)),
                text="DELETE",
                manager=self.ui_manager,
            )
            self.delete_button.disable()

    def _destroy_ui(self) -> None:
        """Destroy all UI elements."""
        for button in self.slot_buttons:
            button.kill()
        self.slot_buttons.clear()

        if self.back_button:
            self.back_button.kill()
        if self.confirm_button:
            self.confirm_button.kill()
        if self.delete_button:
            self.delete_button.kill()

    def _format_slot_text(self, slot: int, metadata: Dict[str, Any]) -> str:
        """Format slot metadata as display text."""
        name = metadata.get("name", f"Slot {slot + 1}")
        timestamp_str = metadata.get("timestamp", "")
        credits = metadata.get("credits", 0)
        location = metadata.get("location", "Unknown")
        playtime_seconds = metadata.get("playtime_seconds", 0)

        # Format timestamp
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            date_str = timestamp.strftime("%Y-%m-%d %H:%M")
        except:
            date_str = "Unknown"

        # Format playtime
        hours = playtime_seconds // 3600
        minutes = (playtime_seconds % 3600) // 60
        playtime_str = f"{hours}h {minutes}m"

        # Build display text (limited by button size)
        slot_label = "Autosave" if slot == 0 else f"Slot {slot}"
        lines = [
            f"{slot_label}: {name[:20]}",
            f"{date_str}",
            f"{credits:,} CR | {location[:15]} | {playtime_str}",
        ]

        return "\n".join(lines)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle save/load view events."""
        # ESC to close
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.should_close = True
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            # Check if slot button pressed
            for i, button in enumerate(self.slot_buttons):
                if event.ui_element == button:
                    self._select_slot(i)
                    return

            if event.ui_element == self.back_button:
                logger.info("Cancel save/load")
                self.should_close = True

            elif event.ui_element == self.confirm_button:
                if self.selected_slot is not None:
                    logger.info(f"{self.mode.capitalize()} to slot {self.selected_slot}")
                    self.should_execute = True
                    self.should_close = True

            elif event.ui_element == self.delete_button:
                if self.selected_slot is not None:
                    self._delete_slot(self.selected_slot)

    def _select_slot(self, slot: int) -> None:
        """Select a save slot."""
        self.selected_slot = slot
        logger.info(f"Selected slot {slot}")

        # Enable confirm button
        self.confirm_button.enable()

        # Enable delete button if slot has data (load mode only)
        if self.mode == "load" and self.delete_button:
            if self.slot_metadata[slot]:
                self.delete_button.enable()
            else:
                self.delete_button.disable()

    def _delete_slot(self, slot: int) -> None:
        """Delete a save slot."""
        logger.info(f"Deleting slot {slot}")
        success = self.save_manager.delete_save(slot)

        if success:
            # Reload metadata and recreate UI
            self._load_slot_metadata()
            self._destroy_ui()
            self._create_ui()
            self.selected_slot = None

    def update(self, dt: float) -> None:
        """Update save/load view."""
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        """Render save/load view."""
        # Animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        if self.mode == "save":
            title_text = "SAVE GAME"
        else:
            title_text = "LOAD GAME"

        title = self.title_font.render(title_text, True, Colors.TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 40))
        screen.blit(title, title_rect)

        # Instructions
        if self.mode == "save":
            instr_text = "Select a slot to save your game"
        else:
            instr_text = "Select a slot to load"

        instr = self.info_font.render(instr_text, True, Colors.TEXT_SECONDARY)
        instr_rect = instr.get_rect(center=(WINDOW_WIDTH // 2, 70))
        screen.blit(instr, instr_rect)

        # Highlight selected slot
        if self.selected_slot is not None:
            button = self.slot_buttons[self.selected_slot]
            pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, button.relative_rect, 3)

    def get_selected_slot(self) -> Optional[int]:
        """Get the selected slot number."""
        return self.selected_slot

    def should_close_dialog(self) -> bool:
        """Check if dialog should close."""
        result = self.should_close
        self.should_close = False
        return result

    def should_execute_action(self) -> bool:
        """Check if save/load action should execute."""
        result = self.should_execute
        self.should_execute = False
        return result
