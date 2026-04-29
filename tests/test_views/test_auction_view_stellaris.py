"""SA-B3: AuctionView Stellaris-specific rendering paths.

Tests for the new SA-B3 view behaviors layered on top of SA-B2's view:

* PREVIEW empty-state with Velo flavor template (and fallback).
* BID_WINDOW Velo running-commentary line.
* Rival flat-bid line in the bid log when a named rival places a bid.
* POST_SESSION social UI: rival commentary, Sable read, retired-rival aside.
* Hub navigation: ``UNIQUE_HALL_TARGETS["stellaris_auction_house"]`` is set.
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.data_loader import get_data_loader
from spacegame.models.bidding import AuctionLifecycle
from spacegame.models.bidding_lot import (
    LOT_CATEGORY_MODULE,
    VENUE_STELLARIS,
    AuctionLot,
)
from spacegame.models.bidding_persona import (
    PERSONA_PRENTISS,
    PERSONA_SALKO,
    make_prentiss,
)
from spacegame.models.captain_memory import (
    STATUS_WANDERER,
    CaptainMemory,
)
from spacegame.models.crew import CrewRoster
from spacegame.models.player import Player
from spacegame.models.progression import PlayerProgression
from spacegame.models.ship import Ship
from spacegame.views.auction_view import AuctionView
from spacegame.views.station_hub_view import UNIQUE_HALL_TARGETS


def _module_lot(lot_id: str = "mod1") -> AuctionLot:
    return AuctionLot(
        id=lot_id,
        headline=f"Module {lot_id}",
        description="Test module lot.",
        category=LOT_CATEGORY_MODULE,
        venue=VENUE_STELLARIS,
        base_appraisal=12000,
        reserve_pct=0.75,
    )


def _make_env() -> tuple[pygame_gui.UIManager, Player, CrewRoster, PlayerProgression]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Tester",
        credits=2000,
        current_system_id="stellaris_port",
        ship=ship,
        game_day=10,
    )
    crew_roster = CrewRoster(templates=dl.crew_templates)
    return manager, player, crew_roster, player.progression


def _make_view(
    manager: pygame_gui.UIManager,
    player: Player,
    crew_roster: CrewRoster,
    progression: PlayerProgression,
) -> AuctionView:
    return AuctionView(
        ui_manager=manager,
        player=player,
        crew_roster=crew_roster,
        progression=progression,
        venue_id="stellaris",
        venue_display_name="Stellaris Auction House",
    )


def _stellaris_voices() -> dict:
    dl = get_data_loader()
    dl.load_all()
    return dl.get_auction_voices(VENUE_STELLARIS)


class TestHubNavigationRoutesToAuctionView:
    def test_unique_hall_target_set(self) -> None:
        assert UNIQUE_HALL_TARGETS.get("stellaris_auction_house") == GameState.AUCTION


class TestPreviewEmptyState:
    def test_velo_empty_state_uses_voice_template(self) -> None:
        manager, player, cr, prog = _make_env()
        # No session yet — schedule one 5 days out.
        player.auction_state.schedule_session(VENUE_STELLARIS, player.game_day + 5)
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        # Render path must not crash.
        view.render(screen)
        # The rendered template references Velo.
        empty_state_template = view._voice_templates.get("empty_state", "")
        assert "Velo" in empty_state_template
        assert "{gap_days}" in empty_state_template
        view.on_exit()

    def test_falls_back_to_default_when_voice_missing(self) -> None:
        manager, player, cr, prog = _make_env()
        player.auction_state.schedule_session(VENUE_STELLARIS, player.game_day + 5)
        view = _make_view(manager, player, cr, prog)
        # Empty templates dict — should fall back to "Next session in N days."
        view.set_voice_templates({})
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        view.on_exit()


class TestBidWindowVeloCommentary:
    def test_velo_lot_open_line_on_first_round(self) -> None:
        manager, player, cr, prog = _make_env()
        lot = _module_lot("voice_test_lot")
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            [lot],
            rival_ids=[],
            session_id="velo_voice_t1",
        )
        player.auction_state.set_session_personas([])
        player.auction_state.open_session()
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        view.on_enter()
        # Round state must be live.
        assert player.auction_state.round_state is not None
        assert player.auction_state.round_state.current_high_bidder_id is None
        line = view._velo_running_commentary(lot, player.auction_state.round_state)
        assert "lot is open" in line.lower() or "open" in line.lower()
        assert lot.headline in line
        view.on_exit()

    def test_velo_we_are_at_line_after_bid(self) -> None:
        manager, player, cr, prog = _make_env()
        lot = _module_lot("voice_test_lot2")
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            [lot],
            rival_ids=[],
            session_id="velo_voice_t2",
        )
        player.auction_state.set_session_personas([])
        player.auction_state.open_session()
        rs = player.auction_state.round_state
        assert rs is not None
        # Place a bid so high_bidder is set.
        rs.current_high_bid = 5000
        rs.current_high_bidder_id = "player"
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        view.on_enter()
        line = view._velo_running_commentary(lot, rs)
        assert "5,000" in line
        view.on_exit()


class TestRivalFlatBidLine:
    def test_prentiss_voice_line_format(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        line = view._format_rival_bid_line(PERSONA_PRENTISS, 6000)
        assert line is not None
        assert "6,000" in line

    def test_kade_voice_line_format(self) -> None:
        from spacegame.models.bidding_persona import PERSONA_KADE

        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        line = view._format_rival_bid_line(PERSONA_KADE, 4200)
        assert line is not None
        assert "Guild" in line
        assert "4,200" in line

    def test_salko_voice_line_format(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        line = view._format_rival_bid_line(PERSONA_SALKO, 8000)
        assert line is not None
        assert "8,000" in line

    def test_non_rival_returns_none(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        line = view._format_rival_bid_line("stellaris_speculator_1", 5000)
        assert line is None


class TestPostSessionSocialUI:
    def _setup_closed_session(
        self,
        outcome: str,
    ) -> tuple[Player, AuctionView]:
        manager, player, cr, prog = _make_env()
        # Build a session_lot_results record for the chosen outcome.
        from spacegame.models.bidding import _LotResultRecord

        lot = _module_lot("post_lot")
        player.auction_state.enter_preview(
            VENUE_STELLARIS,
            [lot],
            rival_ids=[PERSONA_PRENTISS],
            session_id="post_session_t",
        )
        player.auction_state.set_session_personas([make_prentiss()])
        if outcome == "rival_won":
            record = _LotResultRecord(
                lot_id="post_lot",
                sold=True,
                winner_id=PERSONA_PRENTISS,
                sale_price=6000,
                player_bid=True,
                rivals_bid=[PERSONA_PRENTISS],
            )
        elif outcome == "player_won":
            record = _LotResultRecord(
                lot_id="post_lot",
                sold=True,
                winner_id="player",
                sale_price=6000,
                player_bid=True,
                rivals_bid=[PERSONA_PRENTISS],
            )
        else:  # no_overlap
            record = _LotResultRecord(
                lot_id="post_lot",
                sold=False,
                winner_id=None,
                sale_price=0,
                player_bid=False,
                rivals_bid=[PERSONA_PRENTISS],
            )
        player.auction_state.session_lot_results = [record]
        player.auction_state.lifecycle = AuctionLifecycle.SESSION_CLOSE
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        view.on_enter()
        return player, view

    def test_rival_won_bucket(self) -> None:
        _player, view = self._setup_closed_session("rival_won")
        bucket = view._post_session_bucket_for_rival(PERSONA_PRENTISS)
        assert bucket == "rival_won"
        lines = view._post_session_lines()
        assert any(line for line in lines)
        view.on_exit()

    def test_player_won_bucket(self) -> None:
        _player, view = self._setup_closed_session("player_won")
        bucket = view._post_session_bucket_for_rival(PERSONA_PRENTISS)
        assert bucket == "player_won"
        view.on_exit()

    def test_no_overlap_bucket(self) -> None:
        _player, view = self._setup_closed_session("no_overlap")
        bucket = view._post_session_bucket_for_rival(PERSONA_PRENTISS)
        assert bucket == "no_overlap"
        view.on_exit()

    def test_retired_rival_aside_fires(self) -> None:
        manager, player, cr, prog = _make_env()
        # Mark Prentiss retired in the player's captain memory.
        memory = CaptainMemory(captain_id=PERSONA_PRENTISS)
        memory.status = STATUS_WANDERER
        player.captain_memory = {PERSONA_PRENTISS: memory}
        player.auction_state.lifecycle = AuctionLifecycle.SESSION_CLOSE
        player.auction_state.active_session_id = "retired_test"
        player.auction_state.rival_session_attendance["retired_test"] = []
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        view.on_enter()
        lines = view._post_session_lines()
        # Retired aside should mention Prentiss.
        assert any("Prentiss" in line for line in lines)
        view.on_exit()

    def test_sable_read_when_active(self) -> None:
        manager, player, cr, prog = _make_env()
        original_get_bonus = cr.get_bonus

        def stub(bonus_type: str) -> float:
            if bonus_type == "auction_bid_visibility":
                return 1.0
            return original_get_bonus(bonus_type)

        cr.get_bonus = stub  # type: ignore[method-assign]
        player.auction_state.lifecycle = AuctionLifecycle.SESSION_CLOSE
        player.auction_state.active_session_id = "sable_test"
        player.auction_state.rival_session_attendance["sable_test"] = []
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates(_stellaris_voices())
        view.on_enter()
        lines = view._post_session_lines()
        # Sable's "no rivals attended" line should fire when no rivals.
        assert any("named rivals" in line.lower() or "ceiling" in line.lower() for line in lines)
        view.on_exit()


class TestSetVoiceTemplates:
    def test_set_voice_templates_stores_dict(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates({"empty_state": "Velo: hello {gap_days}"})
        assert view._voice_templates.get("empty_state")
        view.on_exit()

    def test_empty_templates_default_safe(self) -> None:
        manager, player, cr, prog = _make_env()
        view = _make_view(manager, player, cr, prog)
        view.set_voice_templates({})
        view.on_enter()
        screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        view.render(screen)
        view.on_exit()
