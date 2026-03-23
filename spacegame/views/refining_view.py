"""
Refining system view.

Queue-based crafting UI for processing raw materials into valuable goods.
Features styled recipe cards, active job glow, completion particles, progress bar gradients,
forge buffer output decoupling, forge token upgrades, and recipe mastery indicators.
"""

import pygame
import pygame_gui
import math
import random
from typing import Optional, Dict, List
from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState, scale_x, scale_y
from spacegame.models.player import Player
from spacegame.models.commodity import Commodity
from spacegame.models.refining import Recipe, RefiningSession, RefiningResult
from spacegame.models.forge_buffer import ForgeBuffer
from spacegame.models.rating import calculate_rating, REFINING_THRESHOLDS, RATING_COLORS
from spacegame.engine.draw_utils import draw_bar, draw_summary_overlay, draw_nine_slice_panel
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import (
    ParticlePool,
    FORGE_FLAME,
    FORGE_COMPLETE_FLASH,
)
from spacegame.engine.scrollable_panel import ScrollablePanel
from spacegame.engine.fonts import FontCache, FONT_HEADING, FONT_LG, FONT_MD, FONT_RATING, FONT_SECTION2, FONT_TITLE
from spacegame.engine.sprites import get_sprite_manager, res_scale
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.easing import Tween, ease_out_cubic
from spacegame.engine.floating_text import FloatingItemManager
from spacegame.engine.tooltip import TooltipState
from spacegame.engine.refining_vfx import ForgeAtmosphere, MasteryMomentumBar, DiscoveryHint

# Forge upgrade color theme (warm orange)
FORGE_COLOR = (255, 160, 60)


class RefiningView(BaseView):
    """Refining interface with visual enhancements."""

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        player: Player,
        commodities: Dict[str, Commodity],
        recipes: List[Recipe],
        system_id: str,
        progression=None,
    ):
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.commodities = commodities
        self.all_recipes = recipes
        self.system_id = system_id
        self.progression = progression

        self.session: Optional[RefiningSession] = None
        self.next_state: Optional[GameState] = None
        self.selected_recipe_idx: int = 0

        # Fonts
        self.title_font = FontCache.get(FONT_TITLE)
        self.info_font = FontCache.get(FONT_LG)
        self.small_font = FontCache.get(FONT_MD)

        # Batch
        self.batch_count: int = 1

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.craft_button: Optional[pygame_gui.elements.UIButton] = None
        self.batch_minus_button: Optional[pygame_gui.elements.UIButton] = None
        self.batch_plus_button: Optional[pygame_gui.elements.UIButton] = None

        # Messages
        self.message: str = ""
        self.message_timer: float = 0.0
        self.completed_messages: List[dict] = []

        # Visual
        self.background = AnimatedBackground("industrial", WINDOW_WIDTH, WINDOW_HEIGHT, seed=70)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(110)

        self.particles = ParticlePool(100)
        self._glow_time = 0.0

        # Session summary overlay
        self._show_summary: bool = False
        self._summary_xp: int = 0
        self._session_elapsed: float = 0.0
        self._session_rating: str = "D"
        self._jobs_completed_count: int = 0
        self._unique_recipes_count: int = 0
        self._summary_font = FontCache.get(FONT_HEADING)
        self._summary_title_font = FontCache.get(FONT_SECTION2)
        self._rating_font = FontCache.get(FONT_RATING)

        # Sprite manager
        self._sprite_mgr = get_sprite_manager()

        # Forge state sprites (48x48 native at 2x = 96x96)
        self._forge_sprites: Dict[str, Optional[pygame.Surface]] = {}
        for state in ("idle", "active", "complete"):
            self._forge_sprites[state] = self._sprite_mgr.get_static_sprite(
                "refining", f"forge_{state}", scale=res_scale(2)
            )

        # Mastery star sprites (8x8 native at 2x = 16x16)
        self._mastery_stars: Dict[str, Optional[pygame.Surface]] = {}
        for tier_name in ("bronze", "silver", "gold"):
            self._mastery_stars[tier_name] = self._sprite_mgr.get_static_sprite(
                "refining", f"mastery_star_{tier_name}", scale=res_scale(2)
            )

        # Recipe category icon sprites (16x16 native at 1x)
        self._category_icons: Dict[str, Optional[pygame.Surface]] = {}
        for cat_name in ("commodity", "upgrade", "equipment", "trade"):
            self._category_icons[cat_name] = self._sprite_mgr.get_static_sprite(
                "refining", f"icon_category_{cat_name}", scale=res_scale(1)
            )

        # Lock icon for locked recipes (8x8 native at 2x = 16x16)
        self._lock_icon: Optional[pygame.Surface] = self._sprite_mgr.get_static_sprite(
            "ui", "icon_lock", scale=res_scale(2)
        )

        # Forge completion flash timer (for brief "complete" sprite display)
        self._forge_flash_timer: float = 0.0

        # Floating icon manager for output "ejection" animations
        self._floats = FloatingItemManager()

        # Animated forge token counter (displayed vs actual, tweens up)
        self._displayed_tokens: float = 0.0
        self._token_tween: Optional[Tween] = None

        # Blueprint discovery banner
        self._discovery_banner: Optional[str] = None
        self._discovery_timer: float = 0.0

        # Batch hold-to-increment state
        self._batch_hold_timer: float = 0.0
        self._batch_hold_active: bool = False
        self._batch_hold_direction: int = 0  # +1 or -1
        self._batch_hold_repeats: int = 0  # How many auto-repeats have fired

        # Tooltip for upgrade descriptions
        self._tooltip = TooltipState(delay=0.3, fade_in=0.15)

        # Exit confirmation state
        self._confirm_exit: bool = False

        # Crew commentary (set by Game class after construction)
        self._get_crew_line = lambda action_type: None
        self._crew_comment: str = ""
        self._crew_comment_name: str = ""
        self._crew_comment_timer: float = 0.0

        # Pre-rendered card background surfaces (avoids per-frame allocation)
        card_w, card_h = scale_x(500), scale_y(75)
        self._card_selected = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        for row in range(card_h):
            t = row / card_h
            r = int(30 + (40 - 30) * t)
            g = int(40 + (50 - 40) * t)
            b = int(65 + (75 - 65) * t)
            pygame.draw.line(self._card_selected, (r, g, b, 220), (0, row), (card_w, row))
        self._card_unselected = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        self._card_unselected.fill((18, 22, 38, 200))

        locked_h = scale_y(55)
        self._card_locked = pygame.Surface((card_w, locked_h), pygame.SRCALPHA)
        self._card_locked.fill((12, 14, 28, 180))

        # Recipe list scroll panel (recipes start at y=140, left column 530px wide)
        self._recipe_scroll = ScrollablePanel(
            rect=pygame.Rect(scale_x(30), scale_y(140), scale_x(530), WINDOW_HEIGHT - scale_y(220)),
            content_height=0,  # Updated in on_enter when recipes are known
            scroll_speed=40,
        )

        # Category filter state
        self._active_category: str = (
            "all"  # "all", "commodity", "upgrade", "equipment", "trade_good"
        )
        self._category_tab_rects: Dict[str, pygame.Rect] = {}

        # Commodity icon sprites (scale=1 = 16x16 for inline display)
        self._commodity_icons: Dict[str, Optional[pygame.Surface]] = {}

        # Forge buffer for this system (output decoupling)
        self._buffer: ForgeBuffer = player.forge_buffer_manager.get_buffer(system_id)

        # Forge session tracking
        self._session_forge_tokens: int = 0
        self._transfer_count: int = 0
        self._mastery_levelups: List[str] = []

        # Upgrade panel click rects
        self._upgrade_rects: Dict[str, pygame.Rect] = {}

        # Forge atmosphere VFX (right-side panel where queue/forge renders)
        forge_rect = pygame.Rect(
            WINDOW_WIDTH - scale_x(350), scale_y(80), scale_x(330), scale_y(400)
        )
        self._forge_atmosphere = ForgeAtmosphere(forge_rect)
        self._mastery_bar = MasteryMomentumBar(
            x=WINDOW_WIDTH - scale_x(350),
            y=scale_y(490),
            width=scale_x(330),
        )
        self._discovery_hint = DiscoveryHint(
            x=WINDOW_WIDTH - scale_x(350),
            y=scale_y(525),
            width=scale_x(330),
        )

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered refining")

        # Skill tree bonuses
        speed_bonus = 0.0
        yield_bonus = 0.0
        if self.progression:
            speed_bonus = self.progression.get_bonus("refining_speed")
            yield_bonus = self.progression.get_bonus("gathering_yield_bonus")

        # Apply ship upgrade bonuses (stacks with skill tree)
        speed_bonus += self.player.upgrade_manager.get_bonus("refining_speed_bonus")
        yield_bonus += self.player.upgrade_manager.get_bonus("refining_yield_bonus")

        # Forge upgrade bonuses
        from spacegame.data_loader import get_data_loader

        forge_upgrades = get_data_loader().forge_upgrades
        fu_state = self.player.forge_upgrades

        forge_speed_bonus = fu_state.get_effect("thermal_efficiency", forge_upgrades)
        forge_yield_bonus = fu_state.get_effect("catalyst_resonance", forge_upgrades)
        queue_size_bonus = int(fu_state.get_effect("queue_expansion", forge_upgrades))
        token_earn_bonus = fu_state.get_effect("material_insight", forge_upgrades)
        token_earn_bonus += self.player.upgrade_manager.get_bonus("forge_token_bonus")

        # Apply buffer capacity upgrade
        buffer_bonus = int(fu_state.get_effect("forge_buffer", forge_upgrades))
        if buffer_bonus > 0:
            self.player.forge_buffer_manager.upgrade_all_capacity(buffer_bonus)
            self._buffer = self.player.forge_buffer_manager.get_buffer(self.system_id)

        self.session = RefiningSession(
            self.all_recipes,
            self.system_id,
            speed_bonus=speed_bonus,
            yield_bonus=yield_bonus,
            forge_speed_bonus=forge_speed_bonus,
            forge_yield_bonus=forge_yield_bonus,
            queue_size_bonus=queue_size_bonus,
            mastery_tracker=self.player.recipe_mastery,
            token_earn_bonus=token_earn_bonus,
            discovered_recipes=self.player.discovered_recipes,
        )
        # Locked discoverable recipes at this location (for schematic discovery UI)
        self._locked_recipes: list[Recipe] = [
            r
            for r in self.all_recipes
            if r.discoverable
            and self.system_id in r.location_ids
            and not self.player.is_recipe_discovered(r.id)
            and r.schematic_cost > 0
        ]
        self._schematic_rects: dict[str, pygame.Rect] = {}

        self._jobs_completed_count = 0
        self._session_recipes: set[str] = set()
        self._session_forge_tokens = 0
        self._mastery_levelups = []
        self._displayed_tokens = float(self.player.forge_tokens)
        self._token_tween = None
        self._discovery_banner = None
        self._discovery_timer = 0.0
        self._active_category = "all"
        self._update_recipe_scroll_height()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        btn_h = scale_y(40)
        btn_y = WINDOW_HEIGHT - scale_y(60)
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(20), btn_y, scale_x(150), btn_h),
            text="Stop Refining",
            manager=self.ui_manager,
        )
        self.batch_minus_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(180), btn_y, scale_x(35), btn_h),
            text="-",
            manager=self.ui_manager,
        )
        self.craft_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(220), btn_y, scale_x(150), btn_h),
            text="Start x1",
            manager=self.ui_manager,
        )
        self.batch_plus_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(scale_x(375), btn_y, scale_x(35), btn_h),
            text="+",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        for elem in [
            self.back_button,
            self.craft_button,
            self.batch_minus_button,
            self.batch_plus_button,
        ]:
            if elem:
                elem.kill()

    def _get_instruction_text(self) -> str:
        """Get contextual instruction text based on current game state."""
        if not self.session:
            return ""
        if self._buffer.is_full():
            return "Forge buffer full! Stop refining to transfer output to your ship."
        queue_size = self.session.get_queue_size()
        max_queue = self.session.max_queue_size
        if queue_size >= max_queue:
            return "Queue full! Wait for jobs to complete before starting more."
        filtered = self._get_filtered_recipes()
        if not filtered:
            return "No recipes in this category. Try a different filter tab."
        if queue_size == 0:
            return "Select recipe (Up/Down), Enter to craft. Jobs process in real-time."
        return f"Queue: {queue_size}/{max_queue}. Select recipe + Enter to add more jobs."

    def _end_session(self) -> None:
        """End the refining session: transfer, calculate XP, show summary."""
        # Update personal records
        if self.session:
            total_output = sum(self.session.total_refined.values())
            if total_output > self.player.best_refining_output:
                self.player.best_refining_output = total_output

        self._transfer_count = self._transfer_buffer_to_cargo()
        xp = 0
        if self.session and self.progression:
            total = sum(self.session.total_refined.values())
            if total > 0:
                from spacegame.config import XP_PER_REFINE

                xp = total * XP_PER_REFINE
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

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                self._confirm_exit = True
            elif event.ui_element == self.craft_button:
                self._start_selected_recipe()
            elif event.ui_element == self.batch_minus_button:
                self.batch_count = max(1, self.batch_count - 1)
                self._update_craft_button_text()
                self._batch_hold_active = True
                self._batch_hold_direction = -1
                self._batch_hold_timer = 0.0
                self._batch_hold_repeats = 0
            elif event.ui_element == self.batch_plus_button:
                if self.session:
                    max_batch = self.session.max_queue_size - self.session.get_queue_size()
                else:
                    max_batch = RefiningSession.MAX_QUEUE_SIZE
                if max_batch > 0:
                    self.batch_count = min(max_batch, self.batch_count + 1)
                self._update_craft_button_text()
                self._batch_hold_active = True
                self._batch_hold_direction = 1
                self._batch_hold_timer = 0.0
                self._batch_hold_repeats = 0

        elif event.type == pygame.MOUSEBUTTONUP:
            self._batch_hold_active = False

        elif event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            self._recipe_scroll.handle_event(event, mouse_pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self._handle_category_tab_click(event.pos):
                if not self._handle_schematic_click(event.pos):
                    if not self._handle_upgrade_click(event.pos):
                        self._handle_recipe_click(event.pos)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._confirm_exit = True
            elif event.key in (pygame.K_UP, pygame.K_DOWN):
                self._navigate_recipe(event.key == pygame.K_DOWN)
            elif event.key == pygame.K_RETURN:
                self._start_selected_recipe()

    def _handle_category_tab_click(self, pos: tuple) -> bool:
        """Check if click hit a category filter tab.

        Returns:
            True if a tab was clicked.
        """
        for cat, rect in self._category_tab_rects.items():
            if rect.collidepoint(pos):
                if self._active_category != cat:
                    self._active_category = cat
                    # Select first recipe in new filter
                    filtered = self._get_filtered_recipes()
                    if filtered and self.session:
                        self.selected_recipe_idx = self.session.available_recipes.index(filtered[0])
                    else:
                        self.selected_recipe_idx = 0
                    self._update_recipe_scroll_height()
                    self._recipe_scroll.scroll_to_top()
                return True
        return False

    def _handle_recipe_click(self, pos: tuple) -> None:
        if not self.session:
            return
        filtered = self._get_filtered_recipes()
        for i, recipe in enumerate(filtered):
            content_y = i * scale_y(80)
            screen_y = self._recipe_scroll.get_screen_y(content_y)
            rect = pygame.Rect(scale_x(30), screen_y, scale_x(500), scale_y(75))
            if rect.collidepoint(pos) and self._recipe_scroll.is_item_visible(content_y, scale_y(75)):
                # Map back to index in full available_recipes for craft button
                full_idx = self.session.available_recipes.index(recipe)
                self.selected_recipe_idx = full_idx
                break

    def _handle_schematic_click(self, pos: tuple) -> bool:
        """Check if click hit a locked recipe card and attempt schematic discovery.

        Returns:
            True if the click was consumed.
        """
        for recipe_id, rect in self._schematic_rects.items():
            if rect.collidepoint(pos):
                recipe = next((r for r in self._locked_recipes if r.id == recipe_id), None)
                if recipe is None:
                    return True
                cargo = self.player.ship.current_cargo
                schematic_count = cargo.get("schematic_data", 0)
                if schematic_count < recipe.schematic_cost:
                    self._show_message(
                        f"Need {recipe.schematic_cost} Schematic Data (have {schematic_count})"
                    )
                    return True
                # Spend schematic data and discover
                cargo["schematic_data"] = schematic_count - recipe.schematic_cost
                if cargo["schematic_data"] <= 0:
                    del cargo["schematic_data"]
                self.player.discover_recipe(recipe.id)
                # Add to session available recipes
                if self.session and self.system_id in recipe.location_ids:
                    self.session.available_recipes.append(recipe)
                # Remove from locked list
                self._locked_recipes = [r for r in self._locked_recipes if r.id != recipe_id]
                del self._schematic_rects[recipe_id]
                self._discovery_banner = recipe.name
                self._discovery_timer = 3.0
                self.completed_messages.append(
                    {
                        "text": f"Blueprint Discovered: {recipe.name}!",
                        "timer": 5.0,
                    }
                )
                return True
        return False

    def _handle_upgrade_click(self, pos: tuple) -> bool:
        """Check if click hit an upgrade button and attempt purchase.

        Returns:
            True if the click was consumed by an upgrade button.
        """
        from spacegame.data_loader import get_data_loader

        forge_upgrades = get_data_loader().forge_upgrades
        for uid, rect in self._upgrade_rects.items():
            if rect.collidepoint(pos):
                success, msg, cost = self.player.forge_upgrades.purchase(
                    uid, forge_upgrades, self.player.forge_tokens
                )
                if success:
                    self.player.spend_forge_tokens(cost)
                    self._show_message(msg)
                    get_audio_manager().play_sfx("refine_complete")
                    # Apply upgrade effects immediately
                    if uid == "forge_buffer":
                        bonus = int(forge_upgrades[uid].effect_per_level)
                        self.player.forge_buffer_manager.upgrade_all_capacity(bonus)
                        self._buffer = self.player.forge_buffer_manager.get_buffer(self.system_id)
                    elif uid == "queue_expansion" and self.session:
                        self.session.max_queue_size += 1
                    elif uid == "thermal_efficiency" and self.session:
                        self.session.forge_speed_bonus += forge_upgrades[uid].effect_per_level
                    elif uid == "catalyst_resonance" and self.session:
                        self.session.forge_yield_bonus += forge_upgrades[uid].effect_per_level
                    elif uid == "material_insight" and self.session:
                        self.session.token_earn_bonus += forge_upgrades[uid].effect_per_level
                else:
                    self._show_message(msg)
                return True
        return False

    def _start_selected_recipe(self) -> None:
        if not self.session:
            return
        if not self.session.available_recipes:
            self._show_message("No recipes available at this location")
            return
        if self.selected_recipe_idx >= len(self.session.available_recipes):
            return

        recipe = self.session.available_recipes[self.selected_recipe_idx]

        # Guard: if a category filter is active, ensure the selected recipe is visible
        if self._active_category != "all" and recipe.category != self._active_category:
            filtered = self._get_filtered_recipes()
            if filtered:
                recipe = filtered[0]
                self.selected_recipe_idx = self.session.available_recipes.index(recipe)
            else:
                self._show_message("No recipes in this category")
                return

        if recipe.requires_skill and self.progression:
            if not self.progression.get_bonus("advanced_recipes"):
                self._show_message(f"Requires skill: Refining Knowledge")
                return

        inventory = self.player.ship.current_cargo
        if self.batch_count > 1:
            success, msg = self.session.start_batch(recipe, inventory, self.batch_count)
        else:
            success, msg = self.session.start_job(recipe, inventory)
        self._show_message(msg)
        if success:
            get_audio_manager().play_sfx("refine_start")
            if self.batch_count > 1:
                self.player.batch_jobs_queued += self.batch_count
            self.batch_count = 1
            self._update_craft_button_text()

    def _update_craft_button_text(self) -> None:
        """Update craft button to show current batch count."""
        if self.craft_button:
            self.craft_button.set_text(f"Start x{self.batch_count}")

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 3.0

    def _navigate_recipe(self, forward: bool) -> None:
        """Navigate recipe selection within the filtered list.

        Args:
            forward: True for next recipe (Down), False for previous (Up).
        """
        if not self.session:
            return
        filtered = self._get_filtered_recipes()
        if not filtered:
            return

        # Find current recipe's position in filtered list
        current_recipe = None
        if self.selected_recipe_idx < len(self.session.available_recipes):
            current_recipe = self.session.available_recipes[self.selected_recipe_idx]

        try:
            current_filtered_idx = (
                filtered.index(current_recipe) if current_recipe in filtered else 0
            )
        except ValueError:
            current_filtered_idx = 0

        if forward:
            new_filtered_idx = min(len(filtered) - 1, current_filtered_idx + 1)
        else:
            new_filtered_idx = max(0, current_filtered_idx - 1)

        # Map back to full list index
        target_recipe = filtered[new_filtered_idx]
        self.selected_recipe_idx = self.session.available_recipes.index(target_recipe)

    def _estimate_recipe_profit(self, recipe: Recipe) -> Optional[int]:
        """Estimate profit from crafting a recipe using base commodity prices.

        Returns:
            Estimated profit in CR, or None if prices unavailable.
        """
        input_cost = 0
        for cid, qty in recipe.inputs.items():
            commodity = self.commodities.get(cid)
            if commodity:
                input_cost += commodity.base_price * qty
            else:
                return None  # Unknown commodity

        output_value = 0
        for cid, qty in recipe.outputs.items():
            commodity = self.commodities.get(cid)
            if commodity:
                output_value += commodity.base_price * qty
            else:
                return None

        return output_value - input_cost

    def _get_filtered_recipes(self) -> list[Recipe]:
        """Get recipes filtered by active category."""
        if not self.session:
            return []
        if self._active_category == "all":
            return self.session.available_recipes
        return [r for r in self.session.available_recipes if r.category == self._active_category]

    def _update_recipe_scroll_height(self) -> None:
        """Recalculate scroll content height based on filtered recipe count."""
        recipes = self._get_filtered_recipes()
        locked = self._locked_recipes if hasattr(self, "_locked_recipes") else []
        # Each recipe card is 80px tall, locked cards are 60px, header adds 25px
        content_h = len(recipes) * scale_y(80)
        if locked:
            content_h += scale_y(25) + len(locked) * scale_y(60)
        self._recipe_scroll.set_content_height(content_h)

    def _get_icon(self, commodity_id: str) -> Optional[pygame.Surface]:
        """Get a cached 16x16 commodity icon."""
        if commodity_id not in self._commodity_icons:
            self._commodity_icons[commodity_id] = self._sprite_mgr.get_commodity_icon(
                commodity_id, scale=res_scale(1)
            )
        return self._commodity_icons[commodity_id]

    def _get_forge_state(self) -> str:
        """Get current forge visual state based on queue and flash timer."""
        if self._forge_flash_timer > 0:
            return "complete"
        if self.session and self.session.job_queue:
            return "active"
        return "idle"

    def _get_mastery_star(self, level: int) -> Optional[pygame.Surface]:
        """Get mastery star sprite for a mastery level (1=bronze, 2=silver, 3=gold)."""
        if level >= 3:
            return self._mastery_stars.get("gold")
        if level >= 2:
            return self._mastery_stars.get("silver")
        if level >= 1:
            return self._mastery_stars.get("bronze")
        return None

    def _get_category_icon(self, category: str) -> Optional[pygame.Surface]:
        """Get category icon for a recipe category."""
        # Map recipe category values to sprite names
        cat_map = {
            "commodity": "commodity",
            "upgrade": "upgrade",
            "equipment": "equipment",
            "trade_good": "trade",
        }
        return self._category_icons.get(cat_map.get(category, "commodity"))

    def _transfer_buffer_to_cargo(self) -> int:
        """Transfer as much forge buffer output as possible into ship cargo.

        Returns:
            Total units transferred.
        """
        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        total_transferred = 0
        for commodity_id in list(self._buffer.contents.keys()):
            stored = self._buffer.contents.get(commodity_id, 0)
            if stored <= 0:
                continue
            available_space = self.player.ship.get_available_cargo(commodity_volumes)
            volume = commodity_volumes.get(commodity_id, 1)
            can_fit = available_space // volume if volume > 0 else stored
            transfer = min(stored, can_fit)
            if transfer > 0:
                self._buffer.remove_output(commodity_id, transfer)
                self.player.ship.add_cargo(commodity_id, transfer, price_per_unit=0)
                total_transferred += transfer
        return total_transferred

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt

        # Forge atmosphere VFX
        self._forge_atmosphere.update(dt)
        self._discovery_hint.update(dt)
        if self.session:
            active_count = len(self.session.job_queue)
            max_tier = 1
            for job in self.session.job_queue:
                max_tier = max(max_tier, job.recipe.tier)
            self._forge_atmosphere.set_intensity(active_count, max_tier)
        else:
            self._forge_atmosphere.set_intensity(0)
        self._mastery_bar.clear()
        if not self._show_summary:
            self._session_elapsed += dt

        if self.message_timer > 0:
            self.message_timer -= dt

        for cm in self.completed_messages:
            cm["timer"] -= dt
        self.completed_messages = [cm for cm in self.completed_messages if cm["timer"] > 0]

        # Forge flash timer decay
        if self._forge_flash_timer > 0:
            self._forge_flash_timer = max(0, self._forge_flash_timer - dt)

        # Floating icon animations
        self._floats.update(dt)

        # Tooltip update
        self._update_upgrade_tooltip()
        self._tooltip.update(dt)

        # Crew comment timer
        if self._crew_comment_timer > 0:
            self._crew_comment_timer -= dt

        # Animated token counter
        if self._token_tween is not None:
            self._token_tween.update(dt)
            self._displayed_tokens = self._token_tween.value
            if self._token_tween.finished:
                self._displayed_tokens = float(self.player.forge_tokens)
                self._token_tween = None

        # Discovery banner timer
        if self._discovery_timer > 0:
            self._discovery_timer -= dt
            if self._discovery_timer <= 0:
                self._discovery_banner = None

        # Batch hold-to-increment
        if self._batch_hold_active:
            self._batch_hold_timer += dt
            if self._batch_hold_timer > 0.4:  # Initial delay before repeat
                # How many repeats should have fired by now
                expected_repeats = int((self._batch_hold_timer - 0.4) / 0.1) + 1
                if expected_repeats > self._batch_hold_repeats:
                    self._batch_hold_repeats = expected_repeats
                    if self._batch_hold_direction > 0:
                        if self.session:
                            max_batch = self.session.max_queue_size - self.session.get_queue_size()
                        else:
                            max_batch = 5
                        if max_batch > 0:
                            self.batch_count = min(max_batch, self.batch_count + 1)
                    else:
                        self.batch_count = max(1, self.batch_count - 1)
                    self._update_craft_button_text()

        if self.session:
            # Forge flame particles — intensity scales with active job count
            job_count = len(self.session.job_queue)
            flame_chance = min(0.05 + job_count * 0.05, 0.30)
            if job_count > 0 and random.random() < flame_chance:
                forge_x = WINDOW_WIDTH - 350 + 48
                forge_y = 70
                self.particles.emit(forge_x, forge_y, FORGE_FLAME)

            results = self.session.update(dt)
            for result in results:
                self._handle_result(result)

    def _handle_result(self, result: RefiningResult) -> None:
        # Add outputs to forge buffer instead of ship cargo
        for cid, qty in result.outputs.items():
            added = self._buffer.add_output(cid, qty)
            self.player.items_refined += added
        self.player.refining_jobs_completed += 1
        self.player.recipes_crafted.add(result.recipe_id)
        self._jobs_completed_count += 1
        self._session_recipes.add(result.recipe_id)

        # Award forge tokens with animated counter
        if result.forge_tokens_earned > 0:
            old_tokens = self.player.forge_tokens
            self.player.add_forge_tokens(result.forge_tokens_earned)
            self._session_forge_tokens += result.forge_tokens_earned
            # Animate token display counting up
            self._token_tween = Tween(
                start=float(old_tokens),
                end=float(self.player.forge_tokens),
                duration=0.6,
                easing=ease_out_cubic,
            )

        # Set dialogue flag for craft-gated upgrades/equipment
        recipe = next((r for r in self.all_recipes if r.id == result.recipe_id), None)
        if recipe and recipe.category in ("upgrade", "equipment"):
            for output_id in recipe.outputs:
                self.player.dialogue_flags[output_id] = True
                logger.info(f"Set dialogue flag: {output_id}")
        if recipe and recipe.category == "equipment":
            for output_id in recipe.outputs:
                if output_id not in self.player.ground_equipment:
                    self.player.ground_equipment.append(output_id)
                    logger.info(f"Added ground equipment: {output_id}")

        # Check mastery level-ups (tracked via mastery_tracker in session)
        mastery = self.player.recipe_mastery.get_mastery(result.recipe_id)
        if mastery.mastery_level > 0:
            recipe_name = recipe.name if recipe else result.recipe_id
            levelup_key = f"{result.recipe_id}_{mastery.mastery_level}"
            if levelup_key not in self._mastery_levelups:
                self._mastery_levelups.append(levelup_key)

        # Mastery 3 triggers recipe discovery
        if mastery.mastery_level >= 3:
            for r in self.all_recipes:
                if r.discoverable and r.discovery_prerequisite == result.recipe_id:
                    if not self.player.is_recipe_discovered(r.id):
                        self.player.discover_recipe(r.id)
                        # Add to session available recipes
                        if self.session and r.id not in [
                            ar.id for ar in self.session.available_recipes
                        ]:
                            if self.system_id in r.location_ids:
                                self.session.available_recipes.append(r)
                        # Full-screen discovery banner
                        self._discovery_banner = r.name
                        self._discovery_timer = 3.0
                        self.completed_messages.append(
                            {
                                "text": f"Blueprint Discovered: {r.name}!",
                                "timer": 5.0,
                            }
                        )

        # Completion particle burst + forge flash + output icon float
        get_audio_manager().play_sfx("refine_complete")
        self._forge_flash_timer = 0.6
        forge_x = WINDOW_WIDTH - 350 + 48
        forge_y = 70
        self.particles.emit(forge_x, forge_y, FORGE_COMPLETE_FLASH)

        # Float output icon from forge to buffer bar area
        first_output_id = next(iter(result.outputs), None)
        if first_output_id:
            first_qty = result.outputs[first_output_id]
            cname = self.commodities.get(
                first_output_id, type("", (), {"name": first_output_id})()
            ).name
            # Buffer bar is rendered below queue — approximate target position
            buffer_target_y = forge_y + 300
            self._floats.add_icon_float(
                text=f"+{first_qty} {cname}",
                origin=(float(forge_x), float(forge_y)),
                target=(float(forge_x), float(buffer_target_y)),
                icon_key=first_output_id,
                duration=0.8,
            )

        output_str = ", ".join(
            f"{qty} {self.commodities.get(cid, type('', (), {'name': cid})()).name}"
            for cid, qty in result.outputs.items()
        )
        token_str = f" (+{result.forge_tokens_earned} FT)" if result.forge_tokens_earned > 0 else ""
        self.completed_messages.append(
            {
                "text": f"Completed: {output_str}{token_str}",
                "timer": 4.0,
            }
        )
        logger.info(f"Refining complete: {result.outputs}, tokens: {result.forge_tokens_earned}")

        # Crew commentary (25% chance on job completion)
        if random.random() < 0.25:
            line = self._get_crew_line("refine_complete")
            if line:
                self._crew_comment_name, self._crew_comment = line[0], line[1]
                self._crew_comment_timer = 4.0

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        title = self.title_font.render("REFINING", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        if not self.session:
            return

        # Forge tokens display (top right, animated counter)
        display_tokens = int(self._displayed_tokens)
        token_surf = self.info_font.render(f"Forge Tokens: {display_tokens}", True, FORGE_COLOR)
        screen.blit(token_surf, (WINDOW_WIDTH - token_surf.get_width() - 20, 20))

        instr = self.small_font.render(self._get_instruction_text(), True, Colors.TEXT_SECONDARY)
        screen.blit(instr, (30, 60))

        self._render_recipes(screen)
        self._forge_atmosphere.render(screen)
        self._render_queue(screen)
        self._mastery_bar.render(screen)
        self._discovery_hint.render(screen)

        # Particles
        self.particles.render(screen)

        # Floating output icons (ejected from forge)
        for item in self._floats.items:
            alpha = int(255 * item.alpha)
            if alpha <= 0:
                continue
            text_surf = self.small_font.render(item.text, True, FORGE_COLOR)
            text_surf.set_alpha(alpha)
            screen.blit(text_surf, (int(item.x) - text_surf.get_width() // 2, int(item.y)))

        # Discovery banner overlay
        if self._discovery_banner and self._discovery_timer > 0:
            self._render_discovery_banner(screen)

        # Completed messages
        y = WINDOW_HEIGHT - 160
        for cm in self.completed_messages:
            surf = self.info_font.render(cm["text"], True, Colors.SUCCESS)
            screen.blit(surf, (30, y))
            y -= 25

        # Status message
        if self.message_timer > 0:
            is_success = "Started" in self.message or "Queued" in self.message
            color = Colors.SUCCESS if is_success else Colors.YELLOW
            msg_surf = self.info_font.render(self.message, True, color)
            screen.blit(msg_surf, msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 90)))

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

        # Tooltip
        self._render_tooltip(screen)

        # Exit confirmation overlay
        if self._confirm_exit:
            self._render_confirm_exit(screen)

        # Summary overlay (drawn last, on top of everything)
        if self._show_summary:
            self._render_summary(screen)

    def _render_recipes(self, screen: pygame.Surface) -> None:
        header = self.info_font.render("RECIPES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (30, 90))

        # Category filter tabs
        self._render_category_tabs(screen, tab_y=92)

        filtered = self._get_filtered_recipes()
        inventory = self.player.ship.current_cargo
        # Clip rendering to scroll panel area
        old_clip = screen.get_clip()
        screen.set_clip(self._recipe_scroll.rect)

        for i, recipe in enumerate(filtered):
            content_y = i * 80
            if not self._recipe_scroll.is_item_visible(content_y, 75):
                continue
            y = self._recipe_scroll.get_screen_y(content_y)

            # Map to full index for selection tracking
            full_idx = (
                self.session.available_recipes.index(recipe)
                if recipe in self.session.available_recipes
                else i
            )
            rect = pygame.Rect(scale_x(30), y, scale_x(500), scale_y(75))
            is_selected = full_idx == self.selected_recipe_idx
            can_craft = recipe.can_craft(inventory)

            # Card background from pre-rendered cache
            screen.blit(
                self._card_selected if is_selected else self._card_unselected,
                rect.topleft,
            )

            # Border
            border_color = Colors.TEXT_HIGHLIGHT if is_selected else (45, 52, 72)
            pygame.draw.rect(screen, border_color, rect, 2 if is_selected else 1, border_radius=4)

            # Clip content to card bounds
            screen.set_clip(rect)

            # Row 1: Category icon + recipe name + mastery stars (left), time (right)
            name_x = rect.x + 10
            cat_icon = self._get_category_icon(recipe.category)
            if cat_icon is not None:
                screen.blit(cat_icon, (name_x, rect.y + 8))
                name_x += cat_icon.get_width() + 4
            name_color = Colors.TEXT if can_craft else Colors.TEXT_SECONDARY
            # Truncate name to leave room for stars and time
            max_name_w = rect.right - name_x - 80
            name_text = recipe.name
            name_surf = self.info_font.render(name_text, True, name_color)
            if name_surf.get_width() > max_name_w:
                while len(name_text) > 3 and self.info_font.size(name_text + "..")[0] > max_name_w:
                    name_text = name_text[:-1]
                name_text = name_text.rstrip() + ".."
                name_surf = self.info_font.render(name_text, True, name_color)
            screen.blit(name_surf, (name_x, rect.y + 5))

            # Mastery stars (sprite-based) — capped to available space
            mastery = self.player.recipe_mastery.get_mastery(recipe.id)
            if mastery.mastery_level > 0:
                star_x = name_x + name_surf.get_width() + 6
                star_limit = rect.right - 60  # Leave room for time
                for lvl in range(1, mastery.mastery_level + 1):
                    if star_x >= star_limit:
                        break
                    star = self._get_mastery_star(lvl)
                    if star is not None:
                        screen.blit(star, (star_x, rect.y + 6))
                        star_x += star.get_width() + 2
                    else:
                        star_color = (255, 215, 0) if lvl >= 3 else FORGE_COLOR
                        fallback = self.small_font.render("*", True, star_color)
                        screen.blit(fallback, (star_x, rect.y + 8))
                        star_x += fallback.get_width() + 1

            # Time (always far right of row 1)
            time_str = f"{recipe.processing_time:.0f}s"
            time_surf = self.small_font.render(time_str, True, Colors.BLUE)
            screen.blit(time_surf, (rect.right - time_surf.get_width() - 8, rect.y + 5))

            # Row 2: Inputs (left), tier + skill badge (right)
            input_x = rect.x + 10
            input_y = rect.y + 28
            # Right-side badges on row 2 (render first to know input cutoff)
            row2_right_x = rect.right - 8
            if recipe.requires_skill:
                skill_surf = self.small_font.render("[SKILL]", True, Colors.YELLOW)
                row2_right_x -= skill_surf.get_width()
                screen.blit(skill_surf, (row2_right_x, input_y))
                row2_right_x -= 4
            if recipe.tier > 1:
                tier_surf = self.small_font.render(f"T{recipe.tier}", True, FORGE_COLOR)
                row2_right_x -= tier_surf.get_width()
                screen.blit(tier_surf, (row2_right_x, input_y))
                row2_right_x -= 4
            input_cutoff = row2_right_x - 4

            needs_surf = self.small_font.render("Needs: ", True, Colors.TEXT_SECONDARY)
            screen.blit(needs_surf, (input_x, input_y))
            input_x += needs_surf.get_width()
            for j, (cid, qty) in enumerate(recipe.inputs.items()):
                if input_x >= input_cutoff:
                    ellipsis = self.small_font.render("...", True, Colors.TEXT_SECONDARY)
                    screen.blit(ellipsis, (input_x, input_y))
                    break
                if j > 0:
                    comma = self.small_font.render(", ", True, Colors.TEXT_SECONDARY)
                    screen.blit(comma, (input_x, input_y))
                    input_x += comma.get_width()
                have = inventory.get(cid, 0)
                has_enough = have >= qty
                indicator = self.small_font.render(
                    "+" if has_enough else "x",
                    True,
                    Colors.GREEN if has_enough else Colors.RED,
                )
                screen.blit(indicator, (input_x, input_y))
                input_x += indicator.get_width() + 1
                icon = self._get_icon(cid)
                if icon is not None:
                    screen.blit(icon, (input_x, input_y + 2))
                    input_x += icon.get_width() + 2
                cname = self.commodities.get(cid, type("", (), {"name": cid})()).name
                item_color = Colors.TEXT_SECONDARY if has_enough else Colors.RED
                txt = self.small_font.render(f"{qty} {cname}", True, item_color)
                screen.blit(txt, (input_x, input_y))
                input_x += txt.get_width()

            # Row 3: Outputs (left), profit (right)
            output_x = rect.x + 10
            output_y = rect.y + 48
            profit = self._estimate_recipe_profit(recipe)
            profit_w = 0
            if profit is not None:
                if profit > 0:
                    profit_color = Colors.GREEN
                    profit_text = f"+{profit:,} CR"
                elif profit < 0:
                    profit_color = Colors.RED
                    profit_text = f"{profit:,} CR"
                else:
                    profit_color = Colors.TEXT_SECONDARY
                    profit_text = "0 CR"
                profit_surf = self.small_font.render(profit_text, True, profit_color)
                profit_w = profit_surf.get_width() + 12
                screen.blit(
                    profit_surf,
                    profit_surf.get_rect(right=rect.right - 8, top=output_y),
                )
            output_cutoff = rect.right - 8 - profit_w - 4

            makes_surf = self.small_font.render("Makes: ", True, Colors.SUCCESS)
            screen.blit(makes_surf, (output_x, output_y))
            output_x += makes_surf.get_width()
            for j, (cid, qty) in enumerate(recipe.outputs.items()):
                if output_x >= output_cutoff:
                    ellipsis = self.small_font.render("...", True, Colors.SUCCESS)
                    screen.blit(ellipsis, (output_x, output_y))
                    break
                if j > 0:
                    comma = self.small_font.render(", ", True, Colors.SUCCESS)
                    screen.blit(comma, (output_x, output_y))
                    output_x += comma.get_width()
                icon = self._get_icon(cid)
                if icon is not None:
                    screen.blit(icon, (output_x, output_y + 2))
                    output_x += icon.get_width() + 2
                cname = self.commodities.get(cid, type("", (), {"name": cid})()).name
                txt = self.small_font.render(f"{qty} {cname}", True, Colors.SUCCESS)
                screen.blit(txt, (output_x, output_y))
                output_x += txt.get_width()

            screen.set_clip(self._recipe_scroll.rect)

        # Render locked discoverable recipes with schematic discovery option
        if self._locked_recipes:
            locked_content_y = len(filtered) * 80
            locked_screen_y = self._recipe_scroll.get_screen_y(locked_content_y)
            if self._recipe_scroll.is_item_visible(locked_content_y, 25):
                lock_header = self.small_font.render(
                    "LOCKED BLUEPRINTS (spend Schematic Data)", True, Colors.TEXT_SECONDARY
                )
                screen.blit(lock_header, (30, locked_screen_y + 5))

            schematic_count = self.player.ship.current_cargo.get("schematic_data", 0)

            for li, recipe in enumerate(self._locked_recipes):
                item_content_y = locked_content_y + 25 + li * 60
                if not self._recipe_scroll.is_item_visible(item_content_y, 55):
                    continue
                ly = self._recipe_scroll.get_screen_y(item_content_y)
                rect = pygame.Rect(scale_x(30), ly, scale_x(500), scale_y(55))
                screen.blit(self._card_locked, rect.topleft)
                pygame.draw.rect(screen, (60, 50, 30), rect, 1, border_radius=4)

                # Lock icon + recipe name (dimmed)
                lock_x = rect.x + 10
                if self._lock_icon is not None:
                    screen.blit(self._lock_icon, (lock_x, rect.y + 7))
                    lock_x += self._lock_icon.get_width() + 4
                name_surf = self.info_font.render(recipe.name, True, Colors.TEXT_SECONDARY)
                screen.blit(name_surf, (lock_x, rect.y + 5))

                # Tier
                if recipe.tier > 1:
                    tier_surf = self.small_font.render(f"T{recipe.tier}", True, FORGE_COLOR)
                    screen.blit(tier_surf, (rect.right - 50, rect.y + 5))

                # Hint + schematic cost
                hint_text = recipe.discovery_hint if recipe.discovery_hint else "Locked"
                hint_surf = self.small_font.render(hint_text, True, (120, 100, 70))
                screen.blit(hint_surf, (rect.x + 10, rect.y + 30))

                can_afford = schematic_count >= recipe.schematic_cost
                cost_color = Colors.SUCCESS if can_afford else Colors.RED
                cost_text = f"[{recipe.schematic_cost} Schematic Data]"
                cost_surf = self.small_font.render(cost_text, True, cost_color)
                cost_rect = cost_surf.get_rect(right=rect.right - 10, centery=rect.y + 38)
                screen.blit(cost_surf, cost_rect)

                self._schematic_rects[recipe.id] = rect

        # Restore clip and render scrollbar
        screen.set_clip(old_clip)
        sb = self._recipe_scroll.scrollbar_rect
        if sb is not None:
            pygame.draw.rect(screen, (60, 65, 80), sb)
            pygame.draw.rect(screen, (80, 85, 100), sb, 1)

    def _render_category_tabs(self, screen: pygame.Surface, tab_y: int) -> None:
        """Render category filter tab bar."""
        categories = [
            ("all", "All"),
            ("commodity", "Commodity"),
            ("upgrade", "Upgrade"),
            ("equipment", "Equipment"),
            ("trade_good", "Trade"),
        ]
        tab_x = scale_x(120)
        self._category_tab_rects.clear()
        for cat_id, cat_label in categories:
            is_active = self._active_category == cat_id
            color = Colors.TEXT_HIGHLIGHT if is_active else Colors.TEXT_SECONDARY
            tab_surf = self.small_font.render(cat_label, True, color)
            tab_w = tab_surf.get_width() + 12
            tab_rect = pygame.Rect(tab_x, tab_y, tab_w, 22)
            self._category_tab_rects[cat_id] = tab_rect
            if is_active:
                pygame.draw.rect(screen, (30, 40, 65), tab_rect)
                pygame.draw.rect(screen, Colors.TEXT_HIGHLIGHT, tab_rect, 1)
            screen.blit(tab_surf, (tab_x + 6, tab_y + 2))
            tab_x += tab_w + 4

    def _render_queue(self, screen: pygame.Surface) -> None:
        panel_x = WINDOW_WIDTH - scale_x(350)
        panel_y = scale_y(90)

        # Forge sprite (above queue header)
        forge_state = self._get_forge_state()
        forge_sprite = self._forge_sprites.get(forge_state)
        if forge_sprite is not None:
            fx = panel_x + 260  # Right-aligned in panel
            fy = panel_y - 20
            screen.blit(forge_sprite, (fx, fy))

        max_queue = self.session.max_queue_size if self.session else RefiningSession.MAX_QUEUE_SIZE
        header = self.info_font.render(
            f"JOB QUEUE ({self.session.get_queue_size()}/{max_queue})",
            True,
            Colors.TEXT_HIGHLIGHT,
        )
        screen.blit(header, (panel_x, panel_y))

        y = panel_y + 30
        if not self.session.job_queue:
            empty = self.small_font.render("No active jobs", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (panel_x, y))
            y += 30
        else:
            for job in self.session.job_queue:
                # Job name with output icon (truncate to fit panel)
                first_output_id = next(iter(job.recipe.outputs), None)
                job_icon = self._get_icon(first_output_id) if first_output_id else None
                jx = panel_x
                if job_icon is not None:
                    screen.blit(job_icon, (jx, y + 2))
                    jx += job_icon.get_width() + 4
                display_name = job.recipe.name
                name_surf = self.small_font.render(display_name, True, Colors.TEXT)
                # Truncate if name overflows panel width
                max_name_w = scale_x(300) - (jx - panel_x)
                if name_surf.get_width() > max_name_w:
                    while len(display_name) > 3 and self.small_font.size(display_name + "..")[0] > max_name_w:
                        display_name = display_name[:-1]
                    display_name = display_name.rstrip() + ".."
                    name_surf = self.small_font.render(display_name, True, Colors.TEXT)
                screen.blit(name_surf, (jx, y))

                # Progress bar with gradient fill
                bar_y = y + 22
                bar_w = scale_x(300)
                bar_h = scale_y(16)
                bar_color = Colors.SUCCESS if job.progress >= 0.9 else Colors.TEXT_HIGHLIGHT
                draw_bar(
                    screen,
                    panel_x,
                    bar_y,
                    bar_w,
                    bar_h,
                    current=job.progress,
                    maximum=1.0,
                    color=bar_color,
                    show_value=False,
                )

                # Pulsing glow border for active job
                glow_alpha = int(30 + 20 * math.sin(self._glow_time * 4))
                glow_surf = pygame.Surface((bar_w + 4, bar_h + 4), pygame.SRCALPHA)
                pygame.draw.rect(
                    glow_surf, (*Colors.TEXT_HIGHLIGHT, glow_alpha), glow_surf.get_rect(), 1
                )
                screen.blit(glow_surf, (panel_x - 2, bar_y - 2))

                remaining = job.remaining_time
                time_str = f"{remaining:.1f}s" if remaining > 0 else "Done!"
                time_surf = self.small_font.render(time_str, True, Colors.TEXT_SECONDARY)
                screen.blit(time_surf, (panel_x + bar_w + 5, bar_y))

                y += 50

        # Empty queue slot outlines
        current_jobs = self.session.get_queue_size() if self.session else 0
        empty_slots = max_queue - current_jobs
        for _ in range(empty_slots):
            slot_rect = pygame.Rect(panel_x, y + 22, scale_x(300), scale_y(16))
            pygame.draw.rect(screen, (25, 28, 40), slot_rect)
            pygame.draw.rect(screen, (40, 44, 60), slot_rect, 1)
            y += 50

        # Forge buffer bar
        y += 10
        self._render_buffer_bar(screen, panel_x, y)
        y += 40

        # Forge upgrade panel
        self._render_upgrade_panel(screen, panel_x, y)

    def _render_buffer_bar(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Render forge buffer capacity bar with overflow warning."""
        stored = self._buffer.get_total_stored()
        capacity = self._buffer.capacity
        ratio = stored / max(1, capacity)

        if ratio > 0.9:
            bar_color = Colors.RED
        elif ratio > 0.7:
            bar_color = Colors.YELLOW
        else:
            bar_color = FORGE_COLOR

        bar_w = scale_x(300)
        bar_h = scale_y(16)
        draw_bar(
            screen,
            x,
            y,
            bar_w,
            bar_h,
            stored,
            capacity,
            bar_color,
            show_value=False,
        )
        label = f"FORGE BUFFER: {stored}/{capacity}"
        surf = self.small_font.render(label, True, Colors.TEXT)
        screen.blit(surf, (x + 8, y))

        # Pulsing red border when nearly full
        if ratio > 0.9:
            pulse = int(abs(math.sin(self._glow_time * 4)) * 80) + 80
            pygame.draw.rect(
                screen,
                (pulse, 30, 30),
                (x - 1, y - 1, bar_w + 2, bar_h + 2),
                1,
            )

    def _render_upgrade_panel(self, screen: pygame.Surface, panel_x: int, panel_y: int) -> None:
        """Render forge upgrade purchase panel."""
        from spacegame.data_loader import get_data_loader

        forge_upgrades = get_data_loader().forge_upgrades
        if not forge_upgrades:
            return

        fu_state = self.player.forge_upgrades

        if panel_y > WINDOW_HEIGHT - 80:
            return

        header = self.small_font.render("FURNACE UPGRADES", True, FORGE_COLOR)
        screen.blit(header, (panel_x, panel_y))

        token_surf = self.small_font.render(f"FT: {self.player.forge_tokens}", True, FORGE_COLOR)
        screen.blit(token_surf, (panel_x + 160, panel_y))

        y = panel_y + 22
        mouse_pos = pygame.mouse.get_pos()
        self._upgrade_rects.clear()

        for uid, definition in forge_upgrades.items():
            if y > WINDOW_HEIGHT - 70:
                break
            level = fu_state.get_level(uid)
            next_cost = definition.get_cost(level + 1)

            btn_rect = pygame.Rect(panel_x, y, scale_x(320), scale_y(22))
            self._upgrade_rects[uid] = btn_rect

            is_hover = btn_rect.collidepoint(mouse_pos)
            if is_hover:
                pygame.draw.rect(screen, (50, 35, 20), btn_rect)

            pip_str = ""
            for i in range(definition.max_level):
                pip_str += "[X]" if i < level else "[ ]"

            if next_cost is not None:
                can_buy = self.player.forge_tokens >= next_cost
                cost_color = Colors.TEXT if can_buy else Colors.RED
                text = f"{definition.name} {pip_str}  ({next_cost} FT)"
                surf = self.small_font.render(text, True, cost_color)
            else:
                text = f"{definition.name} {pip_str}  MAX"
                surf = self.small_font.render(text, True, Colors.TEXT_SECONDARY)

            screen.blit(surf, (panel_x + 4, y + 2))
            y += 24

    def _calculate_rating(self) -> None:
        """Calculate session performance rating."""
        if self.session and self._session_elapsed > 0:
            total_output = sum(self.session.total_refined.values())
            output_per_min = total_output / (self._session_elapsed / 60.0)
            self._session_rating = calculate_rating(output_per_min, REFINING_THRESHOLDS)
            if self._session_rating == "S":
                self.player.s_ranks_earned += 1
        else:
            self._session_rating = "D"

    def _update_upgrade_tooltip(self) -> None:
        """Check if mouse is hovering over an upgrade row and update tooltip."""
        mouse_pos = pygame.mouse.get_pos()
        from spacegame.data_loader import get_data_loader

        forge_upgrades = get_data_loader().forge_upgrades
        for uid, rect in self._upgrade_rects.items():
            if rect.collidepoint(mouse_pos):
                definition = forge_upgrades.get(uid)
                if definition:
                    level = self.player.forge_upgrades.get_level(uid)
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

        forge_upgrades = get_data_loader().forge_upgrades
        definition = forge_upgrades.get(self._tooltip.content)
        if not definition:
            return

        level = self.player.forge_upgrades.get_level(self._tooltip.content)
        effect = definition.get_effect(level)
        lines = [definition.name, definition.description]
        if level > 0:
            lines.append(f"Current effect: {effect:.2g}")

        font = self.small_font
        line_surfaces = [font.render(line, True, Colors.TEXT) for line in lines]
        tip_w = max(s.get_width() for s in line_surfaces) + 20
        tip_h = len(line_surfaces) * 20 + 12
        alpha = int(255 * self._tooltip.alpha)

        tx, ty = self._tooltip.get_screen_position(tip_w, tip_h, WINDOW_WIDTH, WINDOW_HEIGHT)

        tip_surf = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
        tip_surf.fill((15, 18, 30, min(alpha, 230)))
        pygame.draw.rect(tip_surf, (60, 70, 100, alpha), tip_surf.get_rect(), 1)
        screen.blit(tip_surf, (tx, ty))

        for i, surf in enumerate(line_surfaces):
            surf.set_alpha(alpha)
            screen.blit(surf, (tx + 10, ty + 6 + i * 20))

    def _render_confirm_exit(self, screen: pygame.Surface) -> None:
        """Render exit confirmation overlay."""
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        screen.blit(dim, (0, 0))

        prompt = self.info_font.render("End refining session?", True, Colors.TEXT)
        screen.blit(prompt, prompt.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 15)))

        hint = self.small_font.render(
            "Y / Enter = Yes    N / Esc = Cancel", True, Colors.TEXT_SECONDARY
        )
        screen.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 15)))

    def _render_discovery_banner(self, screen: pygame.Surface) -> None:
        """Render full-screen blueprint discovery banner."""
        # Fade alpha: full for first 2s, fade out in last 1s
        if self._discovery_timer > 1.0:
            alpha = 255
        else:
            alpha = int(255 * self._discovery_timer)

        # Dim background
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, min(alpha, 120)))
        screen.blit(dim, (0, 0))

        # Banner text
        banner_font = FontCache.get(FONT_SECTION2)
        title = banner_font.render("BLUEPRINT DISCOVERED", True, FORGE_COLOR)
        title.set_alpha(alpha)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 25))
        screen.blit(title, title_rect)

        name_font = FontCache.get(FONT_HEADING)
        name = name_font.render(self._discovery_banner, True, Colors.TEXT)
        name.set_alpha(alpha)
        name_rect = name.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 15))
        screen.blit(name, name_rect)

        # Decorative line
        line_w = max(title.get_width(), name.get_width()) + 40
        line_x = WINDOW_WIDTH // 2 - line_w // 2
        line_color = (FORGE_COLOR[0], FORGE_COLOR[1], FORGE_COLOR[2], alpha)
        line_surf = pygame.Surface((line_w, 2), pygame.SRCALPHA)
        line_surf.fill(line_color)
        screen.blit(line_surf, (line_x, WINDOW_HEIGHT // 2 - 5))

    def _render_summary(self, screen: pygame.Surface) -> None:
        """Render session summary overlay with forge sprite."""
        stats: list[tuple[str, str]] = []
        if self.session:
            total_output = sum(self.session.total_refined.values())
            speed_pct = f"{self.session.speed_bonus * 100:.0f}%"
            yield_pct = f"{self.session.yield_bonus * 100:.0f}%"
            stats = [
                ("Jobs Completed", str(self._jobs_completed_count)),
                ("Total Output", str(total_output)),
                ("Unique Recipes", str(len(self._session_recipes))),
                ("Speed Bonus", speed_pct),
                ("Yield Bonus", yield_pct),
                ("Forge Tokens Earned", str(self._session_forge_tokens)),
                ("Loaded to Ship", str(self._transfer_count)),
            ]
            buffer_remaining = self._buffer.get_total_stored()
            if buffer_remaining > 0:
                stats.append(("Left in Buffer", str(buffer_remaining)))
            if self._mastery_levelups:
                stats.append(("Mastery Level-Ups", str(len(self._mastery_levelups))))
            if self.session.forge_speed_bonus > 0:
                stats.append(("Forge Speed Bonus", f"+{self.session.forge_speed_bonus * 100:.0f}%"))
            if self.session.forge_yield_bonus > 0:
                stats.append(("Forge Yield Bonus", f"+{self.session.forge_yield_bonus * 100:.0f}%"))
        draw_summary_overlay(
            screen,
            title="REFINING COMPLETE",
            stats=stats,
            xp_earned=self._summary_xp,
            rating_letter=self._session_rating,
            rating_color=RATING_COLORS.get(self._session_rating, Colors.TEXT_SECONDARY),
        )
        # Forge sprite in summary background (dimmed, centered below title area)
        forge_sprite = self._forge_sprites.get("idle")
        if forge_sprite is not None:
            fx = WINDOW_WIDTH // 2 - forge_sprite.get_width() // 2
            fy = WINDOW_HEIGHT // 2 - 180
            dimmed = forge_sprite.copy()
            dimmed.set_alpha(80)
            screen.blit(dimmed, (fx, fy))

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
