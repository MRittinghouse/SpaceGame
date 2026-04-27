"""Tutorial ship parts shop — first experience after character creation.

PT-N rewrite (2026-04-23): the shop now sells real parts (scrapyard-tier)
rather than slot-definition placeholders. Parts land in the player's
parts_inventory via Player.add_part() on purchase, matching the real-game
shipyard shop flow. The builder reads parts_inventory in Phase C (equip).

Three parts are mandatory (thruster, reactor, fuel cell — all scrapyard-
grade) and one is a choice (cargo hold or pulse emitter). Cockpit is
self-fulfilling per commit d9cf3d3 (placed as a slot, no part needed).

After purchasing all required + one choice, transitions to the ship
builder in tutorial mode for a three-phase guided assembly (slots, hull,
equip).
"""

from dataclasses import dataclass
from typing import Optional

import pygame
import pygame_gui

from spacegame.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Colors,
    GameState,
    scale_x,
    scale_y,
)
from spacegame.constants.flags import tutorial_bought_part
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.backgrounds import AnimatedBackground
from spacegame.engine.draw_utils import draw_panel
from spacegame.engine.fonts import (
    FONT_BODY,
    FONT_LG,
    FONT_MD,
    FONT_SECTION,
    FONT_XL,
    get_font,
)
from spacegame.utils.logger import logger
from spacegame.views.base_view import BaseView


@dataclass(frozen=True)
class TutorialPart:
    """Schema for the static TUTORIAL_PARTS table.

    SI-1b migration: replaces ``list[dict]`` so MyPy catches key-access
    mistakes (the ``p['slot_def_id']`` class of crash) at import time
    rather than at runtime in rarely-exercised code paths. Frozen so
    accidental mutation of shared content is impossible.
    """

    part_id: str
    name: str
    description: str
    cost: int
    narration: str
    tag: str


# Mandatory parts — required for flight. Cockpit omitted because cockpit
# slots are self-fulfilling (commit d9cf3d3). Placed as a slot in the
# builder, no part needed. Narration in Phase A handles that beat.
TUTORIAL_MANDATORY: list[TutorialPart] = [
    TutorialPart(
        part_id="scrapyard_thruster",
        name="Scrapyard Thruster",
        description="Pulled from a decommissioned freighter. Coolant lines patched twice.",
        cost=600,
        narration="Thruster. Mounts into the engine slot you'll place on the grid.",
        tag="REQUIRED",
    ),
    TutorialPart(
        part_id="scrapyard_reactor",
        name="Scrapyard Reactor",
        description="Second-hand plasma core. Dented casing. Holds power.",
        cost=1500,
        narration="Reactor. Junk-grade, but it's what fits the wallet today.",
        tag="REQUIRED",
    ),
    TutorialPart(
        part_id="scrapyard_fuel_cell",
        name="Scrapyard Fuel Cell",
        description="Reconditioned tank. Previous owner drained it at a bad dock-rate.",
        cost=500,
        narration="Fuel cell. Holds enough for a few jumps. Upgrade when you can.",
        tag="REQUIRED",
    ),
]

# Choice parts — player picks one, defines early playstyle
TUTORIAL_CHOICES: list[TutorialPart] = [
    TutorialPart(
        part_id="scrapyard_hold",
        name="Scrapyard Hold",
        description="Rust-flecked cargo box. Door latches twice. Dry goods only.",
        cost=800,
        narration="Cargo hold. You'll haul goods, find margins, make a living.",
        tag="CHOOSE ONE",
    ),
    TutorialPart(
        part_id="salvaged_pulse_emitter",
        name="Salvaged Pulse Emitter",
        description="Jury-rigged energy weapon pulled from scrap. Weak but it shoots.",
        cost=500,
        narration="Weapon mount. Space isn't friendly. This gives you teeth.",
        tag="CHOOSE ONE",
    ),
]

# Combined for display: mandatory first, then choices
TUTORIAL_PARTS: list[TutorialPart] = TUTORIAL_MANDATORY + TUTORIAL_CHOICES


class TutorialShopView(BaseView):
    """Simplified parts shop for the new-game tutorial."""

    def __init__(
        self,
        ui_manager: object,
        player: object,
        data_loader: object,
    ) -> None:
        super().__init__()
        self.ui_manager = ui_manager
        self.player = player
        self.data_loader = data_loader
        self.next_state: Optional[GameState] = None

        # Track which parts have been purchased
        self._purchased: list[bool] = [False] * len(TUTORIAL_PARTS)
        self._choice_made: bool = False  # Has the player chosen cargo or weapon?
        self._num_mandatory: int = len(TUTORIAL_MANDATORY)
        self._current_step: int = 0  # Which part to highlight next

        # Fonts
        self._title_font = get_font("header", FONT_SECTION)
        self._name_font = get_font("dialogue", FONT_XL)
        self._desc_font = get_font("dialogue", FONT_MD)
        self._cost_font = get_font("stats", FONT_LG)
        self._narration_font = get_font("narration", FONT_BODY)
        self._credit_font = get_font("stats", FONT_LG)

        # Background
        self.background = AnimatedBackground("station", WINDOW_WIDTH, WINDOW_HEIGHT, seed=42)
        self._bg_dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self._bg_dim.fill((0, 0, 0))
        self._bg_dim.set_alpha(160)

        # Buy buttons (created in _create_ui)
        self._buy_buttons: list[pygame_gui.elements.UIButton] = []

    def on_enter(self) -> None:
        super().on_enter()
        self._purchased = [False] * len(TUTORIAL_PARTS)
        self._choice_made = False
        self._current_step = 0
        self._create_ui()
        logger.info("Entered tutorial ship parts shop")

    def on_exit(self) -> None:
        super().on_exit()
        self._destroy_ui()

    def _create_ui(self) -> None:
        self._destroy_ui()
        self._buy_buttons = []

        card_w = scale_x(260)
        card_h = scale_y(120)
        gap = scale_x(14)

        # Mandatory row (4 cards)
        num_m = self._num_mandatory
        mand_total_w = num_m * card_w + (num_m - 1) * gap
        mand_start_x = (WINDOW_WIDTH - mand_total_w) // 2
        mand_y = scale_y(150)

        for i in range(num_m):
            part = TUTORIAL_PARTS[i]
            btn_x = mand_start_x + i * (card_w + gap) + card_w // 2 - scale_x(50)
            btn_y = mand_y + card_h - scale_y(38)
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(btn_x, btn_y, scale_x(100), scale_y(28)),
                text=f"BUY ({part.cost} CR)",
                manager=self.ui_manager,
            )
            self._buy_buttons.append(btn)

        # Choice row (2 cards, centered)
        num_c = len(TUTORIAL_CHOICES)
        choice_total_w = num_c * card_w + (num_c - 1) * gap
        choice_start_x = (WINDOW_WIDTH - choice_total_w) // 2
        choice_y = mand_y + card_h + scale_y(50)

        for i in range(num_c):
            part = TUTORIAL_CHOICES[i]
            btn_x = choice_start_x + i * (card_w + gap) + card_w // 2 - scale_x(50)
            btn_y = choice_y + card_h - scale_y(38)
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(btn_x, btn_y, scale_x(100), scale_y(28)),
                text=f"BUY ({part.cost} CR)",
                manager=self.ui_manager,
            )
            self._buy_buttons.append(btn)

    def _destroy_ui(self) -> None:
        for btn in self._buy_buttons:
            btn.kill()
        self._buy_buttons.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            for i, btn in enumerate(self._buy_buttons):
                if event.ui_element == btn and not self._purchased[i]:
                    self._buy_part(i)
                    return

    def _buy_part(self, index: int) -> None:
        """Purchase a tutorial part."""
        part = TUTORIAL_PARTS[index]
        if self.player.credits < part.cost:
            return

        # If this is a choice part, check if a choice was already made
        is_choice = index >= self._num_mandatory
        if is_choice and self._choice_made:
            return

        self.player.credits -= part.cost
        self._purchased[index] = True
        self._buy_buttons[index].disable()
        # PT-N: land the part in the player's inventory (same path as real
        # shipyard shop purchases). The builder's Phase C reads inventory
        # to show equippable parts. SI-1a: flag goes through the registry
        # helper so readers can't drift from setters.
        if hasattr(self.player, "add_part"):
            self.player.add_part(part.part_id)
        self.player.dialogue_flags[tutorial_bought_part(part.part_id)] = True
        get_audio_manager().play_sfx("trade_buy")
        logger.info(f"Tutorial: purchased {part.name} for {part.cost} CR")

        # If a choice was made, disable the other choice
        if is_choice:
            self._choice_made = True
            for j in range(self._num_mandatory, len(TUTORIAL_PARTS)):
                if j != index and not self._purchased[j]:
                    self._buy_buttons[j].disable()

        # Advance narration step
        self._current_step = sum(self._purchased)

        # All mandatory + one choice = done
        mandatory_done = all(self._purchased[: self._num_mandatory])
        if mandatory_done and self._choice_made:
            self.next_state = GameState.TUTORIAL_BUILDER

    def update(self, dt: float) -> None:
        self.background.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        self.background.render(screen)
        screen.blit(self._bg_dim, (0, 0))

        # Title
        title = self._title_font.render("SCRAPYARD DRYDOCK", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, scale_y(20)))

        # Subtitle — PT-N: frame the three-phase flow that follows so the
        # player has a mental map before buying.
        subtitle = self._desc_font.render(
            "Buy parts here. In the drydock you'll place slots, paint the hull, and equip what you bought.",
            True,
            Colors.TEXT_SECONDARY,
        )
        screen.blit(subtitle, (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, scale_y(55)))

        # Credits display
        cr_text = f"Credits: {self.player.credits:,} CR"
        cr_surf = self._credit_font.render(cr_text, True, Colors.YELLOW)
        screen.blit(cr_surf, (WINDOW_WIDTH // 2 - cr_surf.get_width() // 2, scale_y(80)))

        card_w = scale_x(260)
        card_h = scale_y(120)
        gap = scale_x(14)

        # --- Mandatory row ---
        num_m = self._num_mandatory
        mand_total_w = num_m * card_w + (num_m - 1) * gap
        mand_start_x = (WINDOW_WIDTH - mand_total_w) // 2
        mand_y = scale_y(150)

        # Section label
        req_label = self._desc_font.render("REQUIRED", True, Colors.RED)
        screen.blit(req_label, (mand_start_x, mand_y - 18))

        for i in range(num_m):
            part = TUTORIAL_PARTS[i]
            cx = mand_start_x + i * (card_w + gap)
            self._render_part_card(screen, i, part, cx, mand_y, card_w, card_h)

        # --- Choice row ---
        num_c = len(TUTORIAL_CHOICES)
        choice_total_w = num_c * card_w + (num_c - 1) * gap
        choice_start_x = (WINDOW_WIDTH - choice_total_w) // 2
        choice_y = mand_y + card_h + scale_y(50)

        # Section label
        choice_label = self._desc_font.render("CHOOSE ONE", True, Colors.TEXT_HIGHLIGHT)
        screen.blit(
            choice_label,
            (WINDOW_WIDTH // 2 - choice_label.get_width() // 2, choice_y - 20),
        )

        for i in range(num_c):
            part = TUTORIAL_CHOICES[i]
            cx = choice_start_x + i * (card_w + gap)
            self._render_part_card(
                screen, self._num_mandatory + i, part, cx, choice_y, card_w, card_h
            )

        # Mechanic narration panel at bottom
        narration_y = choice_y + card_h + scale_y(20)
        narration_w = WINDOW_WIDTH - scale_x(160)
        narration_x = (WINDOW_WIDTH - narration_w) // 2
        draw_panel(screen, (narration_x, narration_y, narration_w, scale_y(60)), alpha=200)

        # Narration text
        mandatory_done = all(self._purchased[: self._num_mandatory])
        if not mandatory_done and self._current_step < self._num_mandatory:
            narration = TUTORIAL_PARTS[self._current_step].narration
        elif mandatory_done and not self._choice_made:
            narration = (
                "Essentials sorted. Now pick your edge: cargo for trading, or a weapon for trouble."
            )
        elif mandatory_done and self._choice_made:
            # Closing line carries a small emotional beat from the neighbor-
            # mechanic (see intro_narration where a maintenance neighbor
            # helps source an engine). Reinforces the father thread without
            # exposition. PT-N: references the three-phase drydock so the
            # player has an ordering model for what comes next.
            narration = (
                "That'll do. In the drydock you'll place slots first, paint the hull around them, "
                "then mount these parts. Your old man would have liked this build. Careful kid. "
                "Too careful, maybe. That's how he was when I knew him."
            )
        else:
            # Still buying mandatory parts, show next one
            for j in range(self._num_mandatory):
                if not self._purchased[j]:
                    narration = TUTORIAL_PARTS[j].narration
                    break
            else:
                # Fallback if state gets weird — mechanic's voice, no
                # rank title (the player isn't Captain-of-anything yet).
                narration = "Grab the rest of the essentials. We're not done."

        speaker = "Mechanic: "
        speaker_surf = self._narration_font.render(speaker, True, Colors.TEXT_HIGHLIGHT)
        screen.blit(speaker_surf, (narration_x + 20, narration_y + 12))
        narr_surf = self._narration_font.render(narration, True, Colors.TEXT_PRIMARY)
        screen.blit(narr_surf, (narration_x + 20 + speaker_surf.get_width(), narration_y + 12))

    def _render_part_card(
        self,
        screen: pygame.Surface,
        index: int,
        part: TutorialPart,
        cx: int,
        cy: int,
        card_w: int,
        card_h: int,
    ) -> None:
        """Render a single part card."""
        from spacegame.engine.draw_utils import word_wrap

        purchased = self._purchased[index]
        is_choice = index >= self._num_mandatory
        # Highlight: mandatory → next unpurchased; choice → after mandatory done
        mandatory_done = all(self._purchased[: self._num_mandatory])
        if is_choice:
            is_active = mandatory_done and not self._choice_made and not purchased
        else:
            is_active = not purchased and all(self._purchased[j] for j in range(index))

        if purchased:
            bg_color = (20, 40, 25)
            border_color = Colors.GREEN
        elif is_active:
            bg_color = (25, 30, 50)
            border_color = Colors.TEXT_HIGHLIGHT
        else:
            bg_color = (18, 22, 38)
            border_color = Colors.UI_BORDER

        draw_panel(screen, (cx, cy, card_w, card_h), alpha=200, bg_color=bg_color)
        pygame.draw.rect(screen, border_color, (cx, cy, card_w, card_h), 2, border_radius=4)

        # Note: per-card REQUIRED/CHOOSE ONE tag was previously rendered here
        # at the top-right, but it collided with the card title on wider names
        # (Compact Reactor Core, Light Engine Array). The section header above
        # each row carries the same information cleanly. Card status is
        # communicated via border color (active/purchased/inactive).

        # Part name — truncate if it overflows the card. Long names like
        # "Salvaged Pulse Emitter" were spilling past the card border at
        # standard widths.
        from spacegame.engine.draw_utils import truncate_text

        name_text = truncate_text(part.name, self._name_font, card_w - 20)
        name_surf = self._name_font.render(name_text, True, Colors.TEXT_PRIMARY)
        screen.blit(name_surf, (cx + 10, cy + 6))

        # Description — PT-008: word-wrap so longer descriptions render fully
        # across two lines instead of truncating with an ellipsis. Card height
        # (120px at 720p base) has room; single-line truncation was hiding the
        # back half of every description.
        max_w = card_w - 20
        lines = word_wrap(part.description, self._desc_font, max_w)
        line_h = self._desc_font.get_linesize()
        for i, line in enumerate(lines[:2]):  # cap at 2 lines to reserve room for cost
            line_surf = self._desc_font.render(line, True, Colors.TEXT_SECONDARY)
            screen.blit(line_surf, (cx + 10, cy + 30 + i * line_h))

        # Cost — pinned to the card bottom so the wrapped description above
        # has room to breathe without pushing cost off the card.
        cost_text = f"{part.cost} CR" if not purchased else "PURCHASED"
        cost_color = Colors.YELLOW if not purchased else Colors.GREEN
        cost_surf = self._cost_font.render(cost_text, True, cost_color)
        screen.blit(cost_surf, (cx + 10, cy + card_h - cost_surf.get_height() - 6))

    def get_next_state(self) -> Optional[GameState]:
        return self.next_state
