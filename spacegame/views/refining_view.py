"""
Refining system view.

Queue-based crafting UI for processing raw materials into valuable goods.
Features styled recipe cards, active job glow, completion particles, and progress bar gradients.
"""

import pygame
import pygame_gui
import math
from typing import Optional, Dict, List
from spacegame.views.base_view import BaseView
from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, Colors, GameState
from spacegame.models.player import Player
from spacegame.models.commodity import Commodity
from spacegame.models.refining import Recipe, RefiningSession, RefiningResult
from spacegame.models.rating import calculate_rating, REFINING_THRESHOLDS, RATING_COLORS
from spacegame.engine.draw_utils import draw_bar, draw_summary_overlay
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import ParticlePool, COLLECT_SPARKLE, REFINE_COMPLETE
from spacegame.engine.fonts import FontCache
from spacegame.engine.sprites import get_sprite_manager
from spacegame.engine.audio_manager import get_audio_manager


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
        self.title_font = FontCache.get(36)
        self.info_font = FontCache.get(24)
        self.small_font = FontCache.get(20)

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
        self._summary_font = FontCache.get(32)
        self._summary_title_font = FontCache.get(44)
        self._rating_font = FontCache.get(72)

        # Commodity icon sprites (scale=1 = 16x16 for inline display)
        self._sprite_mgr = get_sprite_manager()
        self._commodity_icons: Dict[str, Optional[pygame.Surface]] = {}

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered refining")
        speed_bonus = 0.0
        yield_bonus = 0.0
        if self.progression:
            speed_bonus = self.progression.get_bonus("refine_speed")
            yield_bonus = self.progression.get_bonus("refine_yield")
        self.session = RefiningSession(
            self.all_recipes, self.system_id,
            speed_bonus=speed_bonus, yield_bonus=yield_bonus,
        )
        self._jobs_completed_count = 0
        self._session_recipes: set[str] = set()
        self._create_ui()

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(20, WINDOW_HEIGHT - 60, 150, 40),
            text="Stop Refining",
            manager=self.ui_manager,
        )
        self.batch_minus_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(180, WINDOW_HEIGHT - 60, 35, 40),
            text="-",
            manager=self.ui_manager,
        )
        self.craft_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(220, WINDOW_HEIGHT - 60, 150, 40),
            text="Start x1",
            manager=self.ui_manager,
        )
        self.batch_plus_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(375, WINDOW_HEIGHT - 60, 35, 40),
            text="+",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        for elem in [
            self.back_button, self.craft_button,
            self.batch_minus_button, self.batch_plus_button,
        ]:
            if elem:
                elem.kill()

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

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
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
            elif event.ui_element == self.craft_button:
                self._start_selected_recipe()
            elif event.ui_element == self.batch_minus_button:
                self.batch_count = max(1, self.batch_count - 1)
                self._update_craft_button_text()
            elif event.ui_element == self.batch_plus_button:
                max_batch = RefiningSession.MAX_QUEUE_SIZE
                if self.session:
                    max_batch = RefiningSession.MAX_QUEUE_SIZE - self.session.get_queue_size()
                self.batch_count = min(max(1, max_batch), self.batch_count + 1)
                self._update_craft_button_text()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_recipe_click(event.pos)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_recipe_idx = max(0, self.selected_recipe_idx - 1)
            elif event.key == pygame.K_DOWN:
                if self.session:
                    max_idx = len(self.session.available_recipes) - 1
                    self.selected_recipe_idx = min(max_idx, self.selected_recipe_idx + 1)

    def _handle_recipe_click(self, pos: tuple) -> None:
        if not self.session:
            return
        recipe_y_start = 140
        for i, recipe in enumerate(self.session.available_recipes):
            rect = pygame.Rect(30, recipe_y_start + i * 80, 500, 75)
            if rect.collidepoint(pos):
                self.selected_recipe_idx = i
                break

    def _start_selected_recipe(self) -> None:
        if not self.session:
            return
        if not self.session.available_recipes:
            self._show_message("No recipes available at this location")
            return
        if self.selected_recipe_idx >= len(self.session.available_recipes):
            return

        recipe = self.session.available_recipes[self.selected_recipe_idx]

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

    def _get_icon(self, commodity_id: str) -> Optional[pygame.Surface]:
        """Get a cached 16x16 commodity icon."""
        if commodity_id not in self._commodity_icons:
            self._commodity_icons[commodity_id] = self._sprite_mgr.get_commodity_icon(
                commodity_id, scale=1
            )
        return self._commodity_icons[commodity_id]

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt
        if not self._show_summary:
            self._session_elapsed += dt

        if self.message_timer > 0:
            self.message_timer -= dt

        for cm in self.completed_messages:
            cm["timer"] -= dt
        self.completed_messages = [cm for cm in self.completed_messages if cm["timer"] > 0]

        if self.session:
            results = self.session.update(dt)
            for result in results:
                self._handle_result(result)

    def _handle_result(self, result: RefiningResult) -> None:
        for cid, qty in result.outputs.items():
            self.player.ship.add_cargo(cid, qty, price_per_unit=0)
            self.player.items_refined += qty
        self.player.refining_jobs_completed += 1
        self.player.recipes_crafted.add(result.recipe_id)
        self._jobs_completed_count += 1
        self._session_recipes.add(result.recipe_id)

        # Completion particle burst
        get_audio_manager().play_sfx("refine_complete")
        self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, REFINE_COMPLETE)

        output_str = ", ".join(
            f"{qty} {self.commodities.get(cid, type('', (), {'name': cid})()).name}"
            for cid, qty in result.outputs.items()
        )
        self.completed_messages.append(
            {
                "text": f"Completed: {output_str}",
                "timer": 4.0,
            }
        )
        logger.info(f"Refining complete: {result.outputs}")

    def render(self, screen: pygame.Surface) -> None:
        # Animated background
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        title = self.title_font.render("REFINING", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        if not self.session:
            return

        instr = self.small_font.render(
            "Select a recipe and click Start. Jobs process in real-time.",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(instr, (30, 60))

        self._render_recipes(screen)
        self._render_queue(screen)

        # Particles
        self.particles.render(screen)

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

        # Summary overlay (drawn last, on top of everything)
        if self._show_summary:
            self._render_summary(screen)

    def _render_recipes(self, screen: pygame.Surface) -> None:
        header = self.info_font.render("AVAILABLE RECIPES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (30, 90))

        label = self.small_font.render("(Click to select, then Start)", True, Colors.TEXT_SECONDARY)
        screen.blit(label, (230, 93))

        y = 120
        inventory = self.player.ship.current_cargo
        max_text_x = 30 + 490  # Right edge of card minus padding

        for i, recipe in enumerate(self.session.available_recipes):
            rect = pygame.Rect(30, y, 500, 75)
            is_selected = i == self.selected_recipe_idx
            can_craft = recipe.can_craft(inventory)

            # Rounded card background with gradient fill
            card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            if is_selected:
                # Gradient: lighter at top
                for row in range(rect.height):
                    t = row / rect.height
                    r = int(30 + (40 - 30) * t)
                    g = int(40 + (50 - 40) * t)
                    b = int(65 + (75 - 65) * t)
                    pygame.draw.line(card_surf, (r, g, b, 220), (0, row), (rect.width, row))
            else:
                card_surf.fill((18, 22, 38, 200))
            screen.blit(card_surf, rect.topleft)

            # Border
            border_color = Colors.TEXT_HIGHLIGHT if is_selected else (45, 52, 72)
            pygame.draw.rect(screen, border_color, rect, 2 if is_selected else 1, border_radius=4)

            # Clip content to card bounds
            old_clip = screen.get_clip()
            screen.set_clip(rect)

            # Recipe name
            name_color = Colors.TEXT if can_craft else Colors.TEXT_SECONDARY
            name_surf = self.info_font.render(recipe.name, True, name_color)
            screen.blit(name_surf, (rect.x + 10, rect.y + 5))

            # Time
            time_surf = self.small_font.render(f"{recipe.processing_time:.0f}s", True, Colors.BLUE)
            screen.blit(time_surf, (rect.right - 50, rect.y + 5))

            # Inputs with inline icons
            have_color = Colors.TEXT_SECONDARY if can_craft else Colors.RED
            input_x = rect.x + 10
            input_y = rect.y + 28
            needs_surf = self.small_font.render("Needs: ", True, have_color)
            screen.blit(needs_surf, (input_x, input_y))
            input_x += needs_surf.get_width()
            for j, (cid, qty) in enumerate(recipe.inputs.items()):
                if input_x >= max_text_x:
                    break
                if j > 0:
                    comma = self.small_font.render(", ", True, have_color)
                    screen.blit(comma, (input_x, input_y))
                    input_x += comma.get_width()
                icon = self._get_icon(cid)
                if icon is not None:
                    screen.blit(icon, (input_x, input_y + 2))
                    input_x += icon.get_width() + 2
                cname = self.commodities.get(cid, type('', (), {'name': cid})()).name
                txt = self.small_font.render(f"{qty} {cname}", True, have_color)
                screen.blit(txt, (input_x, input_y))
                input_x += txt.get_width()

            # Outputs with inline icons
            output_x = rect.x + 10
            output_y = rect.y + 48
            makes_surf = self.small_font.render("Makes: ", True, Colors.SUCCESS)
            screen.blit(makes_surf, (output_x, output_y))
            output_x += makes_surf.get_width()
            for j, (cid, qty) in enumerate(recipe.outputs.items()):
                if output_x >= max_text_x:
                    break
                if j > 0:
                    comma = self.small_font.render(", ", True, Colors.SUCCESS)
                    screen.blit(comma, (output_x, output_y))
                    output_x += comma.get_width()
                icon = self._get_icon(cid)
                if icon is not None:
                    screen.blit(icon, (output_x, output_y + 2))
                    output_x += icon.get_width() + 2
                cname = self.commodities.get(cid, type('', (), {'name': cid})()).name
                txt = self.small_font.render(f"{qty} {cname}", True, Colors.SUCCESS)
                screen.blit(txt, (output_x, output_y))
                output_x += txt.get_width()

            # Skill requirement indicator
            if recipe.requires_skill:
                skill_surf = self.small_font.render("[SKILL]", True, Colors.YELLOW)
                screen.blit(skill_surf, (rect.right - 50, rect.y + 28))

            screen.set_clip(old_clip)

            y += 80

    def _render_queue(self, screen: pygame.Surface) -> None:
        panel_x = WINDOW_WIDTH - 350
        panel_y = 90

        header = self.info_font.render(
            f"JOB QUEUE ({self.session.get_queue_size()}/{RefiningSession.MAX_QUEUE_SIZE})",
            True,
            Colors.TEXT_HIGHLIGHT,
        )
        screen.blit(header, (panel_x, panel_y))

        y = panel_y + 30
        if not self.session.job_queue:
            empty = self.small_font.render("No active jobs", True, Colors.TEXT_SECONDARY)
            screen.blit(empty, (panel_x, y))
            return

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
            max_name_w = 300 - (jx - panel_x)
            if name_surf.get_width() > max_name_w:
                while len(display_name) > 3 and name_surf.get_width() > max_name_w:
                    display_name = display_name[:-1]
                display_name = display_name.rstrip() + ".."
                name_surf = self.small_font.render(display_name, True, Colors.TEXT)
            screen.blit(name_surf, (jx, y))

            # Progress bar with gradient fill
            bar_y = y + 22
            bar_w = 300
            bar_h = 16
            bar_color = Colors.SUCCESS if job.progress >= 0.9 else Colors.TEXT_HIGHLIGHT
            draw_bar(
                screen, panel_x, bar_y, bar_w, bar_h,
                current=job.progress, maximum=1.0, color=bar_color,
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

        # Cargo summary
        y += 20
        cargo_header = self.info_font.render("CARGO HOLD", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(cargo_header, (panel_x, y))
        y += 25

        commodity_volumes = {c.id: c.volume_per_unit for c in self.commodities.values()}
        used = self.player.ship.get_used_cargo(commodity_volumes)
        total = self.player.ship.max_cargo
        cargo_text = self.small_font.render(f"Space: {used}/{total}", True, Colors.TEXT)
        screen.blit(cargo_text, (panel_x, y))
        y += 20

        max_cargo_y = WINDOW_HEIGHT - 80  # Leave room for buttons
        for cid, qty in self.player.ship.current_cargo.items():
            if y >= max_cargo_y:
                more = self.small_font.render("  ...", True, Colors.TEXT_SECONDARY)
                screen.blit(more, (panel_x, y))
                break
            commodity = self.commodities.get(cid)
            name = commodity.name if commodity else cid
            line = self.small_font.render(f"  {name}: {qty}", True, Colors.TEXT_SECONDARY)
            screen.blit(line, (panel_x, y))
            y += 18

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

    def _render_summary(self, screen: pygame.Surface) -> None:
        """Render session summary overlay."""
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
            ]
        draw_summary_overlay(
            screen,
            title="REFINING COMPLETE",
            stats=stats,
            xp_earned=self._summary_xp,
            rating_letter=self._session_rating,
            rating_color=RATING_COLORS.get(self._session_rating, Colors.TEXT_SECONDARY),
        )

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
