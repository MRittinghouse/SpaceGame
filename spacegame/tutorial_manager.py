"""
Tutorial system for new players.

5-step guided tutorial that auto-triggers on new game with skip and replay options.
"""

from dataclasses import dataclass
from typing import Optional

# SI-2 migration (see requirements/si2_dataclass_migration_cookbook.md):
# TUTORIAL_STEPS and MINIGAME_HINTS converted from dict-shaped content to
# frozen dataclasses. Attribute access replaces dict indexing so a typo
# (step['tittle']) becomes an AttributeError at access time rather than
# passing silently through a .get() default.


@dataclass(frozen=True)
class TutorialStep:
    """Schema for a 5-step tutorial overlay entry."""

    id: int
    title: str
    description: str
    trigger: str  # "galaxy_map" | "trading" | "after_first_trade" | "activity" | "after_first_travel"


@dataclass(frozen=True)
class MinigameHint:
    """Schema for a contextual mini-game hint shown once per mini-game."""

    title: str
    description: str


# Tutorial step definitions
# Narrative voice (QA Pass 6 pre-playtest polish, 2026-04-21). Tutorials
# build on the `intro_narration` dialogue — second-person internal voice,
# grounded in the protagonist's recent history (father's death, the
# scrapyard build, 4000 credits, leaving the colony ship). Style reference:
# requirements/dialogue_writing_guide.md §3 (writing for ordinary people)
# and §6 (AI anti-patterns). No em-dashes, no "couldn't help but", no
# "no X, no Y" constructions.

TUTORIAL_STEPS: list[TutorialStep] = [
    TutorialStep(
        id=0,
        title="The Map",
        description=(
            "Eleven systems on the nav display. Your father worked mining "
            "rigs in three of them on paper. In person he only ever saw "
            "this one. The permit clears you for the others. The fuel "
            "tank clears you for two jumps if you're careful, maybe "
            "three.\n\n"
            "Click a system to see what it is. Click Travel when you're "
            "ready to burn fuel. Nothing gets better while you're sitting "
            "here."
        ),
        trigger="galaxy_map",
    ),
    TutorialStep(
        id=1,
        title="The Markets",
        description=(
            "You've seen trading posts your whole life. This one looks "
            "the same as the ones in the colony ship. Prices run "
            "different everywhere. Food is cheap where farms are, "
            "expensive where miners are. Manufactured goods are cheap "
            "where factories are, expensive out on the frontier.\n\n"
            "Buy where they grow it. Sell where they need it. The trend "
            "arrows show which way prices are heading. The math isn't "
            "hard. The waiting is."
        ),
        trigger="trading",
    ),
    TutorialStep(
        id=2,
        title="The Fuel Bill",
        description=(
            "Your first profit. Most of it just went to fuel cells. "
            "That's trading. Every jump costs. Every day at rest costs "
            "nothing but time.\n\n"
            "Prices shift daily. Sometimes waiting IS the trade. You "
            "can REST at any system to pass time without burning fuel. "
            "Your father used to say, 'Plan twice, move once.' He "
            "didn't always follow his own advice."
        ),
        trigger="after_first_trade",
    ),
    TutorialStep(
        id=3,
        title="The Sidework",
        description=(
            "Some systems pay in ore if you're willing to pull a shift "
            "on the rocks. Some have wrecks to pick through. Some run "
            "refineries that turn raw junk into parts worth ten times "
            "what you paid. Your father pulled mining shifts his whole "
            "adult life. Loud work. Dangerous work. Honest work.\n\n"
            "Look at the trading screen for available activities in the "
            "current system. The veterans have a rule: don't turn down "
            "paying work when your hold is empty."
        ),
        trigger="activity",
    ),
    TutorialStep(
        id=4,
        title="The Long Haul",
        description=(
            "First jump made. Now you understand why the old dockhands "
            "talk about fuel like it's bread. You'll level up by trading, "
            "fighting, mining, surviving. Skills unlock. Ships get "
            "better.\n\n"
            "Every system will tell you something if you listen. Some "
            "of them might tell you who buried your father's report. "
            "That's a long way from here. First you need credits. "
            "Then you need friends. Then you need leverage."
        ),
        trigger="after_first_travel",
    ),
]


# Contextual hints shown once per mini-game (independent of the 5-step tutorial).
# Narrative voice (QA Pass 6 pre-playtest polish, 2026-04-21) — same style
# rules as TUTORIAL_STEPS above. Each hint grounds mechanical facts in the
# protagonist's voice or a working-class NPC's voice, rather than breaking
# the fourth wall.
MINIGAME_HINTS: dict[str, MinigameHint] = {
    "mining": MinigameHint(
        title="The Drill Line",
        description=(
            "Your father could read a rock face by the dust it threw. "
            "You don't have that yet. You will.\n\n"
            "LEFT-CLICK breaks a rock one swing at a time.\n"
            "RIGHT-CLICK is the empowered strike. Costs energy. Three "
            "times the damage.\n\n"
            "Energy refills while you work the lighter rocks. Drones "
            "mine the common stuff automatically once you can afford "
            "them. When your hold is full, the drill stops. Regenerate "
            "the field to dig deeper. Rarer ores are further down. So "
            "is everything harder."
        ),
    ),
    "salvage": MinigameHint(
        title="The Wreck",
        description=(
            "Everything you see here was someone's bad day. The "
            "wreckage is going to be picked clean regardless. Might as "
            "well be you.\n\n"
            "SCAN reveals what's in a cell. Costs a charge. Numbers "
            "show how many items are nearby.\n"
            "EXTRACT pulls items out. Takes time. You can run several "
            "at once.\n\n"
            "Red cells are corrupted. Once the timer starts, you lose "
            "the contents fast. The scanner flashes when it spots one. "
            "Watch the flash."
        ),
    ),
    "refining": MinigameHint(
        title="The Crucible",
        description=(
            "Raw metals pay less than finished parts. That's not "
            "philosophy, that's margin.\n\n"
            "Select a recipe. It lists what it NEEDS and what it "
            "MAKES. Queue a job with Start. Jobs process in real time "
            "and you can stack them.\n\n"
            "Some recipes want ingredients you haven't found yet. "
            "You'll trip them as you trade. The old line on the docks: "
            "miners break, refiners build, shippers get paid. Learn "
            "all three."
        ),
    ),
    # === Combat System Tutorials ===
    "combat_momentum": MinigameHint(
        title="The Momentum Bar",
        description=(
            "You feel the fight settle into rhythm. Every hit landed, "
            "every hit taken, every crew move, every status effect "
            "feeds a pool the old pilots call momentum.\n\n"
            "25% unlocks Crew Combos.\n"
            "50% doubles your weapon damage for a turn.\n"
            "75% adds +3 energy regen.\n"
            "100% fires your ship's Ultimate, whatever that is.\n\n"
            "The bar sits on your left. The bar doesn't lie."
        ),
    ),
    "combat_crew_combo": MinigameHint(
        title="Crew Combo",
        description=(
            "Two of your crew just synced on a shared move. The gold "
            "COMBO button in the crew row is the opportunity.\n\n"
            "Press it in place of the regular crew ability. Combos "
            "hit harder than solo moves. Different pairs unlock "
            "different combos.\n\n"
            "Your crew works better together than apart. That's not a "
            "metaphor, that's mechanics."
        ),
    ),
    "combat_ultimate": MinigameHint(
        title="Ultimate Ready",
        description=(
            "Full momentum. Your ship's Ultimate is live.\n\n"
            "Press [U] or click the gold ULTIMATE button. What "
            "happens depends on the ship class. Some ultimates are "
            "finishing blows. Some are tactical resets. Using one "
            "drops the bar back to zero.\n\n"
            "Pick your moment. Don't waste it on an enemy that was "
            "already going to die."
        ),
    ),
    "combat_boss": MinigameHint(
        title="Boss Contact",
        description=(
            "This enemy is different. Higher hull. Phase transitions.\n\n"
            "When their hull drops past certain thresholds, their "
            "tactics shift. They might call reinforcements. They "
            "might unleash a saved attack. They might rebuild shields.\n\n"
            "Read the telegraphs before you commit your queue. Bosses "
            "don't freeze. They resist voltaic suppression. Fight "
            "them slow. Fight them patient."
        ),
    ),
    "combat_elemental": MinigameHint(
        title="Elemental Weapons",
        description=(
            "Your weapon just applied a status effect. The element "
            "determines what happens next.\n\n"
            "Plasma: BURN ticks damage over three turns. Stacks to 3.\n"
            "Cryo: CHILL reduces evasion. Three stacks FREEZES the "
            "target for a turn.\n"
            "Voltaic: SUPPRESSED cuts enemy damage output.\n"
            "Ion: 150% vs shields, 75% vs hull.\n"
            "Kinetic: no effects, pure damage.\n\n"
            "Different fights want different tools. Pack for the "
            "fight you expect."
        ),
    ),
    # === Ship Builder Tutorials (Phase F) ===
    "builder_welcome": MinigameHint(
        title="The Drydock",
        description=(
            "This is where you build. Every pixel you lay down becomes "
            "part of your ship's hull and sprite, and flies with you "
            "from here on.\n\n"
            "LEFT panel is your shape palette. Pick a shape to stamp.\n"
            "RIGHT panel is your material selector. Pick what the "
            "shape is made of.\n"
            "CENTER is your ship grid. Click to place.\n\n"
            "The stats panel at the bottom updates in real time so "
            "you can see what your choices actually mean. Don't want "
            "to build from scratch? Click BACK and load a preset from "
            "the Shipyard."
        ),
    ),
    "builder_shapes": MinigameHint(
        title="Shapes and Materials",
        description=(
            "Shapes are your building blocks. Pick one from the left, "
            "click the grid to stamp it down.\n\n"
            "[R] rotates the shape 90 degrees.\n"
            "[Q] flips horizontally.\n"
            "[X] mirrors across the center line.\n\n"
            "Materials decide what each pixel contributes. Standard "
            "Plate is the honest middle of the road. Heavy Armor is "
            "tough and slow. Light Alloy is fast and fragile. The "
            "pixel color IS the material color. The ship shows its "
            "materials by showing its colors."
        ),
    ),
    "builder_tools": MinigameHint(
        title="Builder Tools",
        description=(
            "[S] Stamp places shapes. This is the default tool.\n"
            "[P] Pencil places single pixels for detail.\n"
            "[M] Brush repaints pixels with a different material.\n"
            "[F] Fill floods an enclosed area.\n"
            "[E] Eraser removes pixels.\n\n"
            "Right-click always erases. Ctrl+Z undoes. Ctrl+Y redoes. "
            "Press [Tab] to switch to EQUIP mode and install weapons "
            "and shields into your module slots."
        ),
    ),
    "builder_confirm": MinigameHint(
        title="Confirming the Build",
        description=(
            "Click CONFIRM BUILD when you're satisfied. The ship's "
            "sprite updates everywhere. Combat, galaxy map, HUD. "
            "All of it.\n\n"
            "Nothing is permanent. Any shipyard lets you rebuild. "
            "The weight system creates natural trade-offs. Hull "
            "materials are heavy but durable. Shields are medium and "
            "balanced. Light materials are fast but fragile.\n\n"
            "Your ship tells your story. Build the ship you want, "
            "and rebuild it when you learn more."
        ),
    ),
    # === Ship Builder Tutorials (Slot-Based System) ===
    "builder_module_welcome": MinigameHint(
        title="Drydock Intake",
        description=(
            "This is the Drydock. You design your ship by placing "
            "slots on the grid. Each slot type does a different job.\n\n"
            "SLOTS tab: weapon, defense, engine, and utility mounts.\n"
            "HULL tab: paint hull pixels for armor and character.\n\n"
            "Pick a slot type from the palette on the left. Click the "
            "grid to place it. [R] rotates. [Tab] switches modes. "
            "Right-click removes a placed slot. The grid doesn't "
            "judge. That's what the stats panel is for."
        ),
    ),
    "builder_module_engine": MinigameHint(
        title="Engine First",
        description=(
            "Your ship needs propulsion before anything else. Pick an "
            "Engine slot from the palette, click the grid to place.\n\n"
            "Ships face RIGHT in this view. Engines go toward the "
            "left (stern) so the nozzle faces the right direction.\n\n"
            "After placing the slot, buy an engine part in the Shop "
            "tab and equip it in the Loadout tab. Without an engine, "
            "you're space debris."
        ),
    ),
    "builder_module_requirements": MinigameHint(
        title="Minimum Viable Ship",
        description=(
            "Every ship needs at minimum:\n\n"
            "1. Engine slot (propulsion)\n"
            "2. Reactor slot (power)\n\n"
            "Everything else is preference. Weapons if you expect to "
            "fight. Defense if you expect to be fought. Cargo if you "
            "plan to trade. Utility for fuel and sensors. Crew "
            "quarters if you want crew aboard.\n\n"
            "Your frame caps how many of each slot type you can "
            "place. Work within the cap. That's part of the design, "
            "not a barrier to it."
        ),
    ),
    "builder_module_hull": MinigameHint(
        title="Hull Pixels",
        description=(
            "Press [Tab] to switch to Hull mode. You paint hull "
            "pixels around your slots to add hit points and armor.\n\n"
            "Four hull materials:\n"
            "Light Alloy is fast and fragile.\n"
            "Standard Plate is balanced.\n"
            "Heavy Armor is tough and slow.\n"
            "Stealth Composite is evasive.\n\n"
            "Slots define what the ship does. Hull pixels define "
            "what it looks like and how much damage it absorbs "
            "before something vital breaks. Both matter."
        ),
    ),
    "builder_module_confirm": MinigameHint(
        title="Ready to Fly",
        description=(
            "All requirements met. Your layout works.\n\n"
            "Click CONFIRM BUILD to finalize. Slot and pixel "
            "fabrication costs come out of your credits. After "
            "confirming, the Shop tab sells parts that fit your "
            "slots and the Loadout tab equips them.\n\n"
            "The overlays on the right panel show structural "
            "integrity and center of mass. Use them to find weak "
            "points in your design before you commit. A bad center "
            "of mass in the builder is a worse one in combat."
        ),
    ),
    "combat_defensive_identity": MinigameHint(
        title="Your Ship's Identity",
        description=(
            "Your build shapes how your ship fights. The ship tells "
            "you which identity it leans into.\n\n"
            "JUGGERNAUT (hull-heavy): armor reduces incoming damage. "
            "Last Stand activates below 25% hull.\n"
            "SENTINEL (shield-heavy): shields regenerate every turn. "
            "Shield Break leaves a short vulnerability window.\n"
            "GHOST (light and evasive): clean dodges build "
            "Counterstrike stacks. Hits hurt more when they land.\n\n"
            "Your identity shows on the left combat panel. Play the "
            "identity your ship actually has, not the one you wanted."
        ),
    ),
}


class TutorialManager:
    """Manages the tutorial progression and state.

    Two modes:
    - "story" (default): 5-step overlay is suppressed. Story-tied tutorials
      (P1-P5) teach through gameplay. MINIGAME_HINTS still fire on repeat visits.
    - "classic": Original 5-step overlay tutorial fires as before.
    """

    def __init__(self) -> None:
        """Initialize tutorial in not-started state."""
        self.current_step: int = 0
        self.completed: bool = False
        self.skipped: bool = False
        self.active: bool = False
        self._show_step: bool = False
        self.hints_dismissed: set[str] = set()
        self.tutorial_approach: str = "story"  # "story" or "classic"

    def should_show_step(self, trigger: str) -> bool:
        """Check if a tutorial step should show for the given trigger.

        In "story" mode, overlay steps are suppressed (story tutorials handle teaching).
        In "classic" mode, overlay steps fire normally.

        Args:
            trigger: The trigger context (e.g., "galaxy_map", "trading").

        Returns:
            True if the current step matches this trigger and should show.
        """
        if self.tutorial_approach == "story":
            return False  # Story tutorials replace overlay steps
        if self.completed or self.skipped or not self.active:
            return False
        if self.current_step >= len(TUTORIAL_STEPS):
            return False
        step = TUTORIAL_STEPS[self.current_step]
        return step.trigger == trigger and not self._show_step

    def start_step(self) -> Optional[TutorialStep]:
        """Begin showing the current step.

        Returns:
            The current TutorialStep, or None if no step to show.
        """
        if self.completed or self.skipped or not self.active:
            return None
        if self.current_step >= len(TUTORIAL_STEPS):
            self.completed = True
            return None
        self._show_step = True
        return TUTORIAL_STEPS[self.current_step]

    def advance_step(self) -> Optional[TutorialStep]:
        """Advance to the next tutorial step.

        Returns:
            The next TutorialStep, or None if tutorial is complete.
        """
        self.current_step += 1
        self._show_step = False
        if self.current_step >= len(TUTORIAL_STEPS):
            self.completed = True
            return None
        return TUTORIAL_STEPS[self.current_step]

    def skip_tutorial(self) -> None:
        """Skip the rest of the tutorial."""
        self.skipped = True
        self._show_step = False

    def reset_tutorial(self) -> None:
        """Reset tutorial for replay."""
        self.current_step = 0
        self.completed = False
        self.skipped = False
        self.active = True
        self._show_step = False

    def is_showing(self) -> bool:
        """Check if a tutorial step is currently being shown."""
        return self._show_step and self.active and not self.completed and not self.skipped

    def get_current_step(self) -> Optional[TutorialStep]:
        """Get the current step content if showing.

        Returns:
            The current TutorialStep or None.
        """
        if not self.is_showing():
            return None
        if self.current_step >= len(TUTORIAL_STEPS):
            return None
        return TUTORIAL_STEPS[self.current_step]

    def should_show_hint(self, hint_id: str) -> bool:
        """Check if a contextual hint should show.

        Args:
            hint_id: ID of the hint (e.g., 'mining', 'salvage', 'refining').

        Returns:
            True if the hint exists and hasn't been dismissed yet.
        """
        return hint_id in MINIGAME_HINTS and hint_id not in self.hints_dismissed

    def get_hint(self, hint_id: str) -> Optional[MinigameHint]:
        """Get hint content by ID.

        Args:
            hint_id: ID of the hint.

        Returns:
            MinigameHint with title/description, or None.
        """
        return MINIGAME_HINTS.get(hint_id)

    def dismiss_hint(self, hint_id: str) -> None:
        """Mark a contextual hint as dismissed.

        Args:
            hint_id: ID of the hint to dismiss.
        """
        self.hints_dismissed.add(hint_id)

    def to_dict(self) -> dict:
        """Serialize tutorial state."""
        return {
            "current_step": self.current_step,
            "completed": self.completed,
            "skipped": self.skipped,
            "active": self.active,
            "hints_dismissed": list(self.hints_dismissed),
            "tutorial_approach": self.tutorial_approach,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TutorialManager":
        """Deserialize tutorial state.

        Args:
            data: Serialized tutorial state dict.

        Returns:
            Restored TutorialManager instance.
        """
        tm = cls()
        tm.current_step = data.get("current_step", 0)
        tm.completed = data.get("completed", False)
        tm.skipped = data.get("skipped", False)
        tm.active = data.get("active", False)
        tm.hints_dismissed = set(data.get("hints_dismissed", []))
        tm.tutorial_approach = data.get("tutorial_approach", "story")
        return tm
