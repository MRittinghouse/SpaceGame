"""Tests for the EncounterView — phase state machine, choices, outcomes."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for EncounterView tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required for EncounterView tests")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState  # noqa: E402
from spacegame.models.encounter import (  # noqa: E402
    EncounterChoice,
    EncounterDefinition,
    EncounterOutcome,
    EncounterRef,
)
from spacegame.models.captain_tokens import Pronouns  # noqa: E402
from spacegame.models.mission import MissionReward  # noqa: E402
from spacegame.views.encounter_view import EncounterPhase, EncounterView  # noqa: E402
from tools.parity.snapshots import fresh_player  # noqa: E402


# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for all view tests in this module."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_outcome(
    description: str = "Something happened.",
    rewards: list[MissionReward] | None = None,
    leads_to_combat: bool = False,
) -> EncounterOutcome:
    return EncounterOutcome(
        description=description,
        rewards=rewards or [],
        leads_to_combat=leads_to_combat,
    )


def _make_choice(
    choice_id: str = "help",
    label: str = "Help",
    description: str = "Help them out.",
    outcome: EncounterOutcome | None = None,
) -> EncounterChoice:
    return EncounterChoice(
        id=choice_id,
        label=label,
        description=description,
        outcome=outcome or _make_outcome(),
    )


def _make_definition(
    def_id: str = "test_distress_01",
    encounter_type: str = "distress_signal",
    name: str = "Test Distress",
    description: str = "A test distress signal.",
    choices: list[EncounterChoice] | None = None,
) -> EncounterDefinition:
    return EncounterDefinition(
        id=def_id,
        encounter_type=encounter_type,
        name=name,
        description=description,
        choices=choices
        or [
            _make_choice(
                "help",
                "Help",
                "Provide aid.",
                _make_outcome("You helped.", [MissionReward("credits", 100)]),
            ),
            _make_choice("ignore", "Ignore", "Leave them.", _make_outcome("You left.")),
        ],
    )


def _make_encounter_ref(
    encounter_type: str = "distress_signal",
    shakedown_demand: int = 0,
) -> EncounterRef:
    return EncounterRef(
        enemy_template_ids=[],
        encounter_seed=12345,
        encounter_type=encounter_type,
        shakedown_demand=shakedown_demand,
    )


def _make_view(
    definition: EncounterDefinition | None = None,
    encounter_ref: EncounterRef | None = None,
) -> EncounterView:
    ui = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    defn = definition or _make_definition()
    ref = encounter_ref or _make_encounter_ref()
    view = EncounterView(ui_manager=ui, encounter_def=defn, encounter_ref=ref)
    view.on_enter()
    return view


# ============================================================================
# Construction
# ============================================================================


class TestEncounterViewConstruction:
    """Test view initializes correctly."""

    def test_stores_definition(self) -> None:
        view = _make_view()
        assert view.encounter_def.id == "test_distress_01"
        view.on_exit()

    def test_stores_encounter_ref(self) -> None:
        view = _make_view()
        assert view.encounter_ref.encounter_seed == 12345
        view.on_exit()


# ============================================================================
# Choosing Phase
# ============================================================================


class TestChoosingPhase:
    """Test the initial choosing phase."""

    def test_starts_in_choosing_phase(self) -> None:
        view = _make_view()
        assert view.phase == EncounterPhase.CHOOSING
        view.on_exit()

    def test_choice_buttons_created(self) -> None:
        view = _make_view()
        assert len(view.choice_buttons) == 2
        view.on_exit()

    def test_keyboard_selection_1(self) -> None:
        """Pressing '1' selects the first choice."""
        view = _make_view()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
        view.handle_event(event)
        assert view.phase == EncounterPhase.OUTCOME
        assert view.chosen_outcome is not None
        view.on_exit()

    def test_keyboard_selection_2(self) -> None:
        """Pressing '2' selects the second choice."""
        view = _make_view()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2)
        view.handle_event(event)
        assert view.phase == EncounterPhase.OUTCOME
        view.on_exit()

    def test_advances_to_outcome(self) -> None:
        """Selecting a choice advances to OUTCOME phase."""
        view = _make_view()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
        view.handle_event(event)
        assert view.phase == EncounterPhase.OUTCOME
        assert view.chosen_outcome.description == "You helped."
        view.on_exit()


# ============================================================================
# Outcome Phase
# ============================================================================


class TestOutcomePhase:
    """Test the outcome phase after a choice is made."""

    def _advance_to_outcome(self, view: EncounterView) -> None:
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
        view.handle_event(event)

    def test_shows_outcome_rewards(self) -> None:
        view = _make_view()
        self._advance_to_outcome(view)
        assert len(view.chosen_outcome.rewards) == 1
        assert view.chosen_outcome.rewards[0].reward_type == "credits"
        view.on_exit()

    def test_enter_advances_to_done(self) -> None:
        view = _make_view()
        self._advance_to_outcome(view)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        view.handle_event(event)
        assert view.phase == EncounterPhase.DONE
        view.on_exit()

    def test_combat_outcome_sets_pending(self) -> None:
        combat_choice = _make_choice(
            "fight",
            "Fight",
            "Fight them.",
            _make_outcome("Combat begins.", leads_to_combat=True),
        )
        defn = _make_definition(choices=[combat_choice])
        view = _make_view(definition=defn)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
        view.handle_event(event)
        assert view.pending_combat is True
        view.on_exit()

    def test_non_combat_outcome_no_pending(self) -> None:
        view = _make_view()
        self._advance_to_outcome(view)
        assert view.pending_combat is False
        view.on_exit()


# ============================================================================
# Done Phase
# ============================================================================


class TestDonePhase:
    """Test the done phase and state transitions."""

    def _advance_to_done(self, view: EncounterView) -> None:
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
        view.handle_event(event)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        view.handle_event(event)

    def test_get_next_state_returns_trading(self) -> None:
        view = _make_view()
        self._advance_to_done(view)
        assert view.get_next_state() == GameState.TRADING
        view.on_exit()

    def test_combat_outcome_returns_combat(self) -> None:
        combat_choice = _make_choice(
            "fight",
            "Fight",
            "Fight them.",
            _make_outcome("Combat!", leads_to_combat=True),
        )
        defn = _make_definition(choices=[combat_choice])
        view = _make_view(definition=defn)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
        view.handle_event(event)
        # In outcome phase with pending_combat, Enter goes to DONE
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        view.handle_event(event)
        assert view.get_next_state() == GameState.COMBAT
        view.on_exit()


# ============================================================================
# Shakedown Substitution
# ============================================================================


class TestShakedownSubstitution:
    """Test shakedown demand template substitution."""

    def test_demand_replaced_in_description(self) -> None:
        defn = _make_definition(
            encounter_type="shakedown",
            description="Pay {shakedown_demand} credits or else.",
        )
        ref = _make_encounter_ref(encounter_type="shakedown", shakedown_demand=150)
        view = _make_view(definition=defn, encounter_ref=ref)
        assert "150" in view.display_description
        assert "{shakedown_demand}" not in view.display_description
        view.on_exit()

    def test_sentinel_resolved_in_rewards(self) -> None:
        pay_choice = _make_choice(
            "pay",
            "Pay",
            "Pay them.",
            _make_outcome(
                "Paid.",
                [MissionReward("deduct_credits", -1)],
            ),
        )
        defn = _make_definition(
            encounter_type="shakedown",
            choices=[pay_choice],
        )
        ref = _make_encounter_ref(encounter_type="shakedown", shakedown_demand=200)
        view = _make_view(definition=defn, encounter_ref=ref)
        # Select pay choice
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1)
        view.handle_event(event)
        # The resolved reward amount should be the actual demand
        assert view.chosen_outcome.rewards[0].amount == 200
        view.on_exit()

    def test_demand_replaced_in_choice_labels(self) -> None:
        choice = _make_choice(
            "pay",
            "Pay {shakedown_demand} CR",
            "Hand over credits.",
            _make_outcome("Done."),
        )
        defn = _make_definition(
            encounter_type="shakedown",
            choices=[choice],
        )
        ref = _make_encounter_ref(encounter_type="shakedown", shakedown_demand=175)
        view = _make_view(definition=defn, encounter_ref=ref)
        # Check the displayed choice label has been substituted
        assert "175" in view.display_choices[0].label
        view.on_exit()


class TestCaptainTokens:
    """Writing discipline spec 2.6: Szabo's {Son} and every token render for the choice."""

    def _view(
        self, choice: Pronouns, definition: EncounterDefinition, demand: int = 0
    ) -> EncounterView:
        player = fresh_player()
        player.pronouns = choice
        ref = _make_encounter_ref(
            encounter_type="shakedown" if demand else "distress_signal", shakedown_demand=demand
        )
        view = EncounterView(
            ui_manager=pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT)),
            encounter_def=definition,
            encounter_ref=ref,
            player=player,
        )
        view.on_enter()
        return view

    @pytest.mark.parametrize(
        ("choice", "word"), [(Pronouns.HE, "Son"), (Pronouns.SHE, "Girl"), (Pronouns.THEY, "Kid")]
    )
    def test_an_outcome_renders_the_address(self, choice: Pronouns, word: str) -> None:
        outcome = _make_outcome("'{Son}, I been running this route.'")
        report = _make_choice("report", "Report it", "Report it.", outcome)
        view = self._view(choice, _make_definition(choices=[report]))
        expected = f"'{word}, I been running this route.'"
        assert view.display_choices[0].outcome.description == expected
        view.on_exit()

    def test_name_description_label_and_hint_render(self) -> None:
        choice = _make_choice(
            "log",
            "Log it under {their} name",
            "{They} {v:keeps|keep} the channel open.",
            _make_outcome("Done."),
        )
        definition = _make_definition(
            name="{Their} Hail", description="The hauler hails {them}.", choices=[choice]
        )
        view = self._view(Pronouns.HE, definition)
        assert view.display_name == "His Hail"
        assert view.display_description == "The hauler hails him."
        assert view.display_choices[0].label == "Log it under his name"
        assert view.display_choices[0].description == "He keeps the channel open."
        view.on_exit()

    def test_a_verb_token_beside_the_shakedown_demand(self) -> None:
        """The tokens render before the demand's format_map, which a verb token would break."""
        definition = _make_definition(
            encounter_type="shakedown",
            description="{They} {v:owes|owe} {shakedown_demand} credits.",
        )
        view = self._view(Pronouns.THEY, definition, demand=150)
        assert view.display_description == "They owe 150 credits."
        view.on_exit()

    def test_the_chosen_outcome_keeps_the_rendered_text(self) -> None:
        outcome = _make_outcome("'{Son}, go home.'")
        report = _make_choice("report", "Report it", "Report it.", outcome)
        view = self._view(Pronouns.SHE, _make_definition(choices=[report]))
        view.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        assert view.chosen_outcome.description == "'Girl, go home.'"
        view.on_exit()
