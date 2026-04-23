"""Tests for smuggling polish (PK-1/PK-2/PK-3) deferred from the Arna arc.

Covers three sub-items:

1. Hidden compartment install flow in ``ShipyardView`` actually creates the
   ``HiddenCompartment`` object on the player (bug prior to this sprint:
   only the ``upgrade_manager`` knew about the install). First install
   shows a first-time tip. Uninstall merges hidden cargo back to main.

2. First customs inspection encounter shows a ``TutorialNarrationModal``
   explaining the comply/persuade/bribe/intimidate choices. Subsequent
   inspections don't re-fire the tip.

3. ``TradingView`` renders a disabled black-market button with a reason
   tooltip when a black market exists at the station but the player
   lacks access. Toggling into the black market fires a one-time tip.
   Regression test for the pre-existing on_enter bug where ``_create_ui``
   only ran inside the first-time-tip dismissal path.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui
import pytest


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


# ============================================================================
# PK-1: Hidden compartment install in shipyard
# ============================================================================


def _make_shipyard_with_player():
    """Construct a ShipyardView bypassing __init__, with a mock player.

    Using ``spec=Player`` on the mock means accessing an attribute that
    isn't defined on the real class raises — so the previous ``max_cargo``
    bug (where ``player.max_cargo`` silently fabricated a value) would
    have failed at test time.
    """
    from spacegame.models.player import Player
    from spacegame.views.shipyard_view import ShipyardView

    view = ShipyardView.__new__(ShipyardView)
    view.player = MagicMock(spec=Player)
    view.player.dialogue_flags = {}
    view.player.progression = MagicMock()
    view.player.progression.get_bonus.return_value = 0.0
    view.player.hidden_compartment = None
    view.player.ship = MagicMock()
    view.player.ship.max_cargo = 20
    view.player.ship.current_cargo = {}
    view.player.ship.add_cargo = MagicMock(
        side_effect=lambda cid, qty, price=0: view.player.ship.current_cargo.update(
            {cid: view.player.ship.current_cargo.get(cid, 0) + qty}
        )
    )
    view._first_time_tip = None
    view.message = ""
    view.message_timer = 0.0
    # _show_message
    view._show_message = lambda msg: setattr(view, "message", msg)
    return view


class TestHiddenCompartmentInstall:
    """_install_hidden_compartment wires the compartment object and tip."""

    def test_install_creates_compartment_on_player(self) -> None:
        from spacegame.models.smuggling import HiddenCompartment

        view = _make_shipyard_with_player()
        view._install_hidden_compartment()

        assert isinstance(view.player.hidden_compartment, HiddenCompartment)
        assert view.player.hidden_compartment.total_cargo_capacity == 20

    def test_install_shows_first_time_tip_once(self) -> None:
        view = _make_shipyard_with_player()
        view._install_hidden_compartment()
        assert view._first_time_tip is not None

        # Dismiss the tip (simulates player clicking "Got it.")
        view._first_time_tip.on_dismiss()
        assert view.player.dialogue_flags.get("seen_tip_hidden_compartment") is True

    def test_install_second_time_skips_tip(self) -> None:
        view = _make_shipyard_with_player()
        view.player.dialogue_flags["seen_tip_hidden_compartment"] = True

        view._install_hidden_compartment()
        assert view._first_time_tip is None

    def test_install_is_idempotent_when_compartment_exists(self) -> None:
        """Guard against double-install replacing cargo."""
        from spacegame.models.smuggling import HiddenCompartment

        view = _make_shipyard_with_player()
        existing = HiddenCompartment(total_cargo_capacity=20)
        existing.hidden_cargo = {"contraband_medicine": 2}
        view.player.hidden_compartment = existing

        view._install_hidden_compartment()
        assert view.player.hidden_compartment is existing
        assert view.player.hidden_compartment.hidden_cargo == {"contraband_medicine": 2}


class TestHiddenCompartmentUninstall:
    """_uninstall_hidden_compartment merges cargo and clears the object."""

    def test_uninstall_clears_compartment(self) -> None:
        from spacegame.models.smuggling import HiddenCompartment

        view = _make_shipyard_with_player()
        view.player.hidden_compartment = HiddenCompartment(total_cargo_capacity=20)

        view._uninstall_hidden_compartment()
        assert view.player.hidden_compartment is None

    def test_uninstall_merges_hidden_cargo_to_main(self) -> None:
        from spacegame.models.smuggling import HiddenCompartment

        view = _make_shipyard_with_player()
        hc = HiddenCompartment(total_cargo_capacity=20)
        hc.hidden_cargo = {"contraband_medicine": 3, "weapons_components": 2}
        view.player.hidden_compartment = hc

        view._uninstall_hidden_compartment()
        # add_cargo was called for each commodity
        assert view.player.ship.current_cargo.get("contraband_medicine") == 3
        assert view.player.ship.current_cargo.get("weapons_components") == 2

    def test_uninstall_with_empty_compartment_is_silent(self) -> None:
        from spacegame.models.smuggling import HiddenCompartment

        view = _make_shipyard_with_player()
        view.player.hidden_compartment = HiddenCompartment(total_cargo_capacity=20)
        view.message = "previous status"

        view._uninstall_hidden_compartment()
        # No status message when there's nothing to move
        assert view.message == "previous status"

    def test_uninstall_without_compartment_no_op(self) -> None:
        view = _make_shipyard_with_player()
        view.player.hidden_compartment = None
        # Should not raise
        view._uninstall_hidden_compartment()


class TestHiddenCompartmentSaveLoadMigration:
    """Pre-AR-PK saves: upgrade installed, no HC object. Load must backfill."""

    def test_old_save_with_upgrade_but_no_hc_gets_hc_on_load(self) -> None:
        """A save created before AR-PK had the upgrade installed but no
        HiddenCompartment object on the player (trading view's hide/retrieve
        silently no-op'd). Load path must detect the gap and create one."""
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.save_manager import SaveManager

        dl = get_data_loader()
        if not dl.commodities:
            dl.load_all()
        ship_type = next(iter(dl.ship_types.values()))
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        player = Player(name="T", current_system_id="nexus_prime", credits=0, ship=ship)

        # Pre-fix state: upgrade installed, no player.hidden_compartment
        upgrade = dl.upgrades["hidden_compartment"]
        player.upgrade_manager.install(upgrade)
        assert player.hidden_compartment is None

        mgr = SaveManager()
        payload = mgr._serialize_player(player)
        # Force the old shape: no hidden_compartment key, even though upgrade is on
        payload["hidden_compartment"] = None

        loaded = mgr._deserialize_player(payload)
        assert loaded.hidden_compartment is not None, (
            "old-save migration should backfill a HiddenCompartment"
        )
        assert loaded.hidden_compartment.total_cargo_capacity == loaded.ship.max_cargo

    def test_new_save_with_existing_hc_round_trips(self) -> None:
        """Regression guard: the backward-compat branch must not clobber
        an existing compartment on fresh saves."""
        from spacegame.data_loader import get_data_loader
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship
        from spacegame.models.smuggling import HiddenCompartment
        from spacegame.save_manager import SaveManager

        dl = get_data_loader()
        if not dl.commodities:
            dl.load_all()
        ship_type = next(iter(dl.ship_types.values()))
        ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
        player = Player(name="T", current_system_id="nexus_prime", credits=0, ship=ship)

        upgrade = dl.upgrades["hidden_compartment"]
        player.upgrade_manager.install(upgrade)
        player.hidden_compartment = HiddenCompartment(total_cargo_capacity=ship.max_cargo)
        player.hidden_compartment.hidden_cargo = {"contraband_medicine": 2}

        mgr = SaveManager()
        payload = mgr._serialize_player(player)
        loaded = mgr._deserialize_player(payload)

        assert loaded.hidden_compartment is not None
        assert loaded.hidden_compartment.hidden_cargo == {"contraband_medicine": 2}


# ============================================================================
# PK-2: Customs inspection first-time tutorial in EncounterView
# ============================================================================


def _make_encounter_view(encounter_type: str = "customs_inspection"):
    """Build an EncounterView with a mock player."""
    from spacegame.models.encounter import EncounterDefinition, EncounterRef
    from spacegame.views.encounter_view import EncounterView

    encounter_def = EncounterDefinition(
        id="test",
        encounter_type=encounter_type,
        name="Test Encounter",
        description="Test description",
        choices=[],
        icon_color=(100, 100, 100),
    )
    encounter_ref = EncounterRef(
        enemy_template_ids=[],
        encounter_seed=1234,
        encounter_type=encounter_type,
    )
    ui = pygame_gui.UIManager((1280, 720))
    player = MagicMock()
    player.dialogue_flags = {}
    return EncounterView(ui, encounter_def, encounter_ref, player=player), player


class TestCustomsInspectionTip:
    """EncounterView fires a tutorial modal on first customs inspection."""

    def test_first_customs_inspection_shows_tip(self) -> None:
        view, _ = _make_encounter_view("customs_inspection")
        view._maybe_show_tip()
        assert view._first_time_tip is not None

    def test_tip_dismissal_sets_flag(self) -> None:
        view, player = _make_encounter_view("customs_inspection")
        view._maybe_show_tip()
        assert view._first_time_tip is not None
        view._first_time_tip.on_dismiss()
        assert player.dialogue_flags.get("seen_tip_customs_inspection") is True

    def test_second_customs_inspection_skips_tip(self) -> None:
        view, player = _make_encounter_view("customs_inspection")
        player.dialogue_flags["seen_tip_customs_inspection"] = True
        view._maybe_show_tip()
        assert view._first_time_tip is None

    def test_non_customs_encounter_skips_tip(self) -> None:
        """Pirate/shakedown/etc encounters shouldn't fire the customs tip."""
        view, _ = _make_encounter_view("shakedown")
        view._maybe_show_tip()
        assert view._first_time_tip is None

    def test_no_player_skips_tip(self) -> None:
        """Legacy constructor (no player) never crashes."""
        from spacegame.models.encounter import EncounterDefinition, EncounterRef
        from spacegame.views.encounter_view import EncounterView

        encounter_def = EncounterDefinition(
            id="test",
            encounter_type="customs_inspection",
            name="Test",
            description="Test",
            choices=[],
            icon_color=(100, 100, 100),
        )
        encounter_ref = EncounterRef(
            enemy_template_ids=[],
            encounter_seed=1234,
            encounter_type="customs_inspection",
        )
        ui = pygame_gui.UIManager((1280, 720))
        view = EncounterView(ui, encounter_def, encounter_ref, player=None)
        view._maybe_show_tip()
        assert view._first_time_tip is None


# ============================================================================
# PK-3: Black market denial surface + first-time tip
# ============================================================================


def _make_trading_view(*, system_id: str = "nexus_prime", seen_tip: bool = True):
    """Build a real TradingView on top of the live data loader."""
    from spacegame.data_loader import get_data_loader
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship
    from spacegame.views.trading_view import TradingView

    dl = get_data_loader()
    if not dl.commodities:
        dl.load_all()
    ship_type = next(iter(dl.ship_types.values()))
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(name="Test", current_system_id=system_id, credits=5000, ship=ship)
    if seen_tip:
        player.dialogue_flags["seen_tip_trading"] = True
    ui = pygame_gui.UIManager((1280, 720))
    view = TradingView(ui, player, dl.systems, dl.commodities)
    return view, player


class TestTradingViewReturnVisit:
    """Pre-existing bug: _create_ui only ran via tip-dismiss path. Regression."""

    def test_return_visit_creates_market_and_ui(self) -> None:
        view, _ = _make_trading_view(seen_tip=True)
        view.on_enter()
        assert view.market is not None, "market should be initialized on return visit"
        assert view.market_table is not None, "market table UI should be created"
        view.on_exit()


class TestBlackMarketDenialSurface:
    """Disabled button with tooltip when market exists but access denied."""

    def test_market_exists_but_denied_shows_disabled_button(self) -> None:
        # nexus_prime has a black market rule (dex_heat); fresh player has no access
        view, _ = _make_trading_view(system_id="nexus_prime", seen_tip=True)
        view.on_enter()
        assert view._black_market_exists is True
        assert view._has_black_market is False
        assert view._black_market_denial_reason != ""
        assert view.black_market_button is not None
        assert not view.black_market_button.is_enabled
        view.on_exit()

    def test_market_does_not_exist_no_button(self) -> None:
        # stellaris_port DOES have a rule; use axiom_labs which doesn't
        view, _ = _make_trading_view(system_id="axiom_labs", seen_tip=True)
        view.on_enter()
        assert view._black_market_exists is False
        assert view.black_market_button is None
        view.on_exit()

    def test_access_granted_enables_button_clears_reason(self) -> None:
        view, player = _make_trading_view(system_id="nexus_prime", seen_tip=True)
        player.grant_black_market_access("nexus_prime")
        view.on_enter()
        assert view._has_black_market is True
        assert view._black_market_denial_reason == ""
        assert view.black_market_button is not None
        assert view.black_market_button.is_enabled
        view.on_exit()


class TestBlackMarketFirstTimeTip:
    """Entering black market mode for the first time shows a tip."""

    def test_first_toggle_into_black_market_shows_tip(self) -> None:
        view, player = _make_trading_view(system_id="nexus_prime", seen_tip=True)
        player.grant_black_market_access("nexus_prime")
        view.on_enter()
        assert view._first_time_tip is None

        view._toggle_black_market_mode()
        assert view._first_time_tip is not None
        view.on_exit()

    def test_dismiss_sets_flag(self) -> None:
        view, player = _make_trading_view(system_id="nexus_prime", seen_tip=True)
        player.grant_black_market_access("nexus_prime")
        view.on_enter()
        view._toggle_black_market_mode()
        assert view._first_time_tip is not None
        view._first_time_tip.on_dismiss()
        assert player.dialogue_flags.get("seen_tip_black_market") is True
        view.on_exit()

    def test_second_toggle_does_not_reshow_tip(self) -> None:
        view, player = _make_trading_view(system_id="nexus_prime", seen_tip=True)
        player.grant_black_market_access("nexus_prime")
        player.dialogue_flags["seen_tip_black_market"] = True
        view.on_enter()

        view._toggle_black_market_mode()  # enter
        assert view._first_time_tip is None
        view.on_exit()

    def test_toggle_out_of_black_market_does_not_show_tip(self) -> None:
        """The tip only fires on entry, not exit."""
        view, player = _make_trading_view(system_id="nexus_prime", seen_tip=True)
        player.grant_black_market_access("nexus_prime")
        view.on_enter()
        view._toggle_black_market_mode()  # enter — fires tip
        view._first_time_tip = None  # clear

        view._toggle_black_market_mode()  # exit — should NOT fire tip
        assert view._first_time_tip is None
        view.on_exit()
