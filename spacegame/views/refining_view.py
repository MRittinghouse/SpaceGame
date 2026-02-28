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
from spacegame.utils.logger import logger
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.particles import ParticlePool, COLLECT_SPARKLE


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
        self.title_font = pygame.font.Font(None, 36)
        self.info_font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)

        # UI
        self.back_button: Optional[pygame_gui.elements.UIButton] = None
        self.craft_button: Optional[pygame_gui.elements.UIButton] = None

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

    def on_enter(self) -> None:
        super().on_enter()
        logger.info("Entered refining")
        self.session = RefiningSession(self.all_recipes, self.system_id)
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
        self.craft_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(180, WINDOW_HEIGHT - 60, 150, 40),
            text="Start Recipe",
            manager=self.ui_manager,
        )

    def _destroy_ui(self) -> None:
        if self.back_button:
            self.back_button.kill()
        if self.craft_button:
            self.craft_button.kill()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                if self.session and self.progression:
                    total = sum(self.session.total_refined.values())
                    if total > 0:
                        from spacegame.config import XP_PER_REFINE

                        xp = total * XP_PER_REFINE
                        msgs = self.progression.add_xp(xp)
                        for m in msgs:
                            logger.info(m)
                self.next_state = GameState.TRADING
            elif event.ui_element == self.craft_button:
                self._start_selected_recipe()

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
        success, msg = self.session.start_job(recipe, inventory)
        self._show_message(msg)

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 3.0

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.particles.update(dt)
        self._glow_time += dt

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

        # Completion particle burst
        self.particles.emit(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, COLLECT_SPARKLE)

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
            color = Colors.SUCCESS if "Started" in self.message else Colors.YELLOW
            msg_surf = self.info_font.render(self.message, True, color)
            screen.blit(msg_surf, msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 90)))

    def _render_recipes(self, screen: pygame.Surface) -> None:
        header = self.info_font.render("AVAILABLE RECIPES", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(header, (30, 90))

        label = self.small_font.render("(Click to select, then Start)", True, Colors.TEXT_SECONDARY)
        screen.blit(label, (230, 93))

        y = 120
        inventory = self.player.ship.current_cargo

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

            # Recipe name
            name_color = Colors.TEXT if can_craft else Colors.TEXT_SECONDARY
            name_surf = self.info_font.render(recipe.name, True, name_color)
            screen.blit(name_surf, (rect.x + 10, rect.y + 5))

            # Time
            time_surf = self.small_font.render(f"{recipe.processing_time:.0f}s", True, Colors.BLUE)
            screen.blit(time_surf, (rect.right - 50, rect.y + 5))

            # Inputs
            inputs_str = "Needs: " + ", ".join(
                f"{qty} {self.commodities.get(cid, type('', (), {'name': cid})()).name}"
                for cid, qty in recipe.inputs.items()
            )
            have_color = Colors.TEXT_SECONDARY if can_craft else Colors.RED
            screen.blit(
                self.small_font.render(inputs_str, True, have_color), (rect.x + 10, rect.y + 28)
            )

            # Outputs
            outputs_str = "Makes: " + ", ".join(
                f"{qty} {self.commodities.get(cid, type('', (), {'name': cid})()).name}"
                for cid, qty in recipe.outputs.items()
            )
            screen.blit(
                self.small_font.render(outputs_str, True, Colors.SUCCESS),
                (rect.x + 10, rect.y + 48),
            )

            # Skill requirement indicator
            if recipe.requires_skill:
                skill_surf = self.small_font.render("[SKILL]", True, Colors.YELLOW)
                screen.blit(skill_surf, (rect.right - 50, rect.y + 28))

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
            name_surf = self.small_font.render(job.recipe.name, True, Colors.TEXT)
            screen.blit(name_surf, (panel_x, y))

            # Progress bar with gradient fill
            bar_y = y + 22
            bar_w = 300
            bar_h = 16
            pygame.draw.rect(screen, (30, 30, 40), (panel_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * job.progress)
            bar_color = Colors.SUCCESS if job.progress >= 0.9 else Colors.TEXT_HIGHLIGHT
            pygame.draw.rect(screen, bar_color, (panel_x, bar_y, fill_w, bar_h))

            # Bright leading edge
            if fill_w > 2:
                pygame.draw.rect(screen, (200, 240, 255), (panel_x + fill_w - 2, bar_y, 2, bar_h))

            pygame.draw.rect(screen, Colors.TEXT_SECONDARY, (panel_x, bar_y, bar_w, bar_h), 1)

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

        for cid, qty in self.player.ship.current_cargo.items():
            commodity = self.commodities.get(cid)
            name = commodity.name if commodity else cid
            line = self.small_font.render(f"  {name}: {qty}", True, Colors.TEXT_SECONDARY)
            screen.blit(line, (panel_x, y))
            y += 18

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
