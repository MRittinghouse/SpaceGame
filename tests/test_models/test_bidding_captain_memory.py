"""SA-B2: OUTCOME_OUTBID + auto-retire integration with the auction lifecycle."""

from __future__ import annotations

from spacegame.models.bidding import AuctionState, _LotResultRecord
from spacegame.models.bidding_lot import (
    LOT_CATEGORY_MODULE,
    VENUE_STELLARIS,
    AuctionLot,
)
from spacegame.models.bidding_persona import (
    PERSONA_PRENTISS,
    PERSONA_SALKO,
)
from spacegame.models.captain_memory import (
    OUTCOME_OUTBID,
    RESOLUTION_THRESHOLD,
    STATUS_ACTIVE,
    STATUS_WANDERER,
    CaptainMemory,
)


def _module_lot(lot_id: str = "mod1", base: int = 10000) -> AuctionLot:
    return AuctionLot(
        id=lot_id,
        headline=f"Module {lot_id}",
        description="--",
        category=LOT_CATEGORY_MODULE,
        venue=VENUE_STELLARIS,
        base_appraisal=base,
        reserve_pct=0.7,
    )


class TestOutcomeOutbidConstant:
    def test_constant_value(self) -> None:
        assert OUTCOME_OUTBID == "outbid"

    def test_constant_distinct_from_combat_outcomes(self) -> None:
        from spacegame.models.captain_memory import OUTCOME_DEFEAT, OUTCOME_FLED

        assert OUTCOME_OUTBID != OUTCOME_DEFEAT
        assert OUTCOME_OUTBID != OUTCOME_FLED


class TestAccumulationViaCaptainMemory:
    def test_first_outbid_increments_count(self) -> None:
        mem = CaptainMemory(captain_id=PERSONA_SALKO)
        mem.record_encounter(OUTCOME_OUTBID, 5)
        assert mem.encounter_count == 1
        assert mem.last_outcome == OUTCOME_OUTBID
        assert mem.status == STATUS_ACTIVE

    def test_two_outbids_still_active(self) -> None:
        mem = CaptainMemory(captain_id=PERSONA_SALKO)
        mem.record_encounter(OUTCOME_OUTBID, 5)
        mem.record_encounter(OUTCOME_OUTBID, 6)
        assert mem.encounter_count == 2
        assert mem.status == STATUS_ACTIVE

    def test_third_outbid_auto_retires_to_wanderer(self) -> None:
        assert RESOLUTION_THRESHOLD == 3
        mem = CaptainMemory(captain_id=PERSONA_SALKO)
        for day in range(5, 8):
            mem.record_encounter(OUTCOME_OUTBID, day)
        assert mem.encounter_count == 3
        assert mem.status == STATUS_WANDERER


class TestLifecycleHandoff:
    def _state_with_rival_winning_lot(self) -> AuctionState:
        """Manually craft a session_history entry where Salko outbids the player."""
        st = AuctionState()
        st.active_auction_id = VENUE_STELLARIS
        st.active_session_id = "fixture_sess"
        # Hand-build a session_history entry as if a session just closed.
        from spacegame.models.bidding import _SessionHistoryEntry

        history = _SessionHistoryEntry(
            session_id="fixture_sess",
            venue_id=VENUE_STELLARIS,
            closed_on_day=10,
            lot_results=[
                _LotResultRecord(
                    lot_id="lot_a",
                    sold=True,
                    winner_id=PERSONA_SALKO,
                    sale_price=12000,
                    player_bid=True,
                    rivals_bid=[PERSONA_SALKO],
                ),
            ],
            rival_ids=[PERSONA_SALKO],
        )
        st.session_history.append(history)
        return st

    def test_outbid_record_fires_when_rival_wins_player_bid(self) -> None:
        st = self._state_with_rival_winning_lot()
        captain_memory: dict = {}
        retired = st.collect_outbid_records(captain_memory, game_day=10)
        assert PERSONA_SALKO in captain_memory
        assert captain_memory[PERSONA_SALKO].encounter_count == 1
        assert retired == []

    def test_three_outbids_promote_to_wanderer_via_lifecycle(self) -> None:
        captain_memory: dict = {}
        for sess in range(3):
            st = self._state_with_rival_winning_lot()
            st.collect_outbid_records(captain_memory, game_day=10 + sess)
        assert captain_memory[PERSONA_SALKO].status == STATUS_WANDERER

    def test_player_win_suppresses_record(self) -> None:
        from spacegame.models.bidding import _SessionHistoryEntry

        st = AuctionState()
        st.active_auction_id = VENUE_STELLARIS
        st.active_session_id = "p_won"
        history = _SessionHistoryEntry(
            session_id="p_won",
            venue_id=VENUE_STELLARIS,
            closed_on_day=10,
            lot_results=[
                _LotResultRecord(
                    lot_id="lot_a",
                    sold=True,
                    winner_id="player",
                    sale_price=12000,
                    player_bid=True,
                    rivals_bid=[PERSONA_SALKO],
                ),
            ],
            rival_ids=[PERSONA_SALKO],
        )
        st.session_history.append(history)
        captain_memory: dict = {}
        retired = st.collect_outbid_records(captain_memory, game_day=10)
        assert PERSONA_SALKO not in captain_memory
        assert retired == []

    def test_player_fold_suppresses_record(self) -> None:
        from spacegame.models.bidding import _SessionHistoryEntry

        st = AuctionState()
        st.active_auction_id = VENUE_STELLARIS
        st.active_session_id = "p_folded"
        history = _SessionHistoryEntry(
            session_id="p_folded",
            venue_id=VENUE_STELLARIS,
            closed_on_day=10,
            lot_results=[
                _LotResultRecord(
                    lot_id="lot_a",
                    sold=True,
                    winner_id=PERSONA_SALKO,
                    sale_price=12000,
                    player_bid=False,  # player folded -> player_bid=False
                    rivals_bid=[PERSONA_SALKO],
                ),
            ],
            rival_ids=[PERSONA_SALKO],
        )
        st.session_history.append(history)
        captain_memory: dict = {}
        st.collect_outbid_records(captain_memory, game_day=10)
        assert PERSONA_SALKO not in captain_memory

    def test_unsold_lot_suppresses_record(self) -> None:
        from spacegame.models.bidding import _SessionHistoryEntry

        st = AuctionState()
        st.active_auction_id = VENUE_STELLARIS
        st.active_session_id = "withdrawn"
        history = _SessionHistoryEntry(
            session_id="withdrawn",
            venue_id=VENUE_STELLARIS,
            closed_on_day=10,
            lot_results=[
                _LotResultRecord(
                    lot_id="lot_a",
                    sold=False,
                    winner_id=None,
                    sale_price=0,
                    player_bid=True,
                    rivals_bid=[PERSONA_SALKO],
                ),
            ],
            rival_ids=[PERSONA_SALKO],
        )
        st.session_history.append(history)
        captain_memory: dict = {}
        st.collect_outbid_records(captain_memory, game_day=10)
        assert PERSONA_SALKO not in captain_memory

    def test_procedural_persona_does_not_record(self) -> None:
        """Speculator wins are not recorded as captain memory."""
        from spacegame.models.bidding import _SessionHistoryEntry

        st = AuctionState()
        st.active_auction_id = VENUE_STELLARIS
        st.active_session_id = "spec_won"
        history = _SessionHistoryEntry(
            session_id="spec_won",
            venue_id=VENUE_STELLARIS,
            closed_on_day=10,
            lot_results=[
                _LotResultRecord(
                    lot_id="lot_a",
                    sold=True,
                    winner_id="stellaris_speculator_1",
                    sale_price=12000,
                    player_bid=True,
                    rivals_bid=["stellaris_speculator_1"],
                ),
            ],
            rival_ids=["stellaris_speculator_1"],
        )
        st.session_history.append(history)
        captain_memory: dict = {}
        retired = st.collect_outbid_records(captain_memory, game_day=10)
        assert captain_memory == {}
        assert retired == []

    def test_retire_count_tracked_for_achievement(self) -> None:
        captain_memory: dict = {}
        st = AuctionState()
        for sess in range(3):
            sub = self._state_with_rival_winning_lot()
            sub.collect_outbid_records(captain_memory, game_day=10 + sess)
            # Mirror retire bookkeeping into our state: check that the
            # third invocation actually moved status to WANDERER.
        # Drive AuctionState's retired counter via a separate fixture.
        from spacegame.models.bidding import _SessionHistoryEntry

        for sess in range(3):
            st.active_session_id = f"rsess_{sess}"
            st.active_auction_id = VENUE_STELLARIS
            history = _SessionHistoryEntry(
                session_id=f"rsess_{sess}",
                venue_id=VENUE_STELLARIS,
                closed_on_day=10 + sess,
                lot_results=[
                    _LotResultRecord(
                        lot_id=f"lot_{sess}",
                        sold=True,
                        winner_id=PERSONA_PRENTISS,
                        sale_price=12000,
                        player_bid=True,
                        rivals_bid=[PERSONA_PRENTISS],
                    ),
                ],
                rival_ids=[PERSONA_PRENTISS],
            )
            st.session_history.append(history)
            st.collect_outbid_records(captain_memory, game_day=10 + sess)
        assert st.auction_rivals_retired == 1


# ---------------------------------------------------------------------------
# SA-B6: OUTCOME_OUTCOMPETED — symmetric rivalry resolution
# ---------------------------------------------------------------------------


class TestOutcomeOutcompeted:
    """SA-B6: symmetric player-win accumulation via OUTCOME_OUTCOMPETED."""

    def test_constant_value(self) -> None:
        from spacegame.models.captain_memory import OUTCOME_OUTCOMPETED

        assert OUTCOME_OUTCOMPETED == "outcompeted"

    def test_constant_distinct_from_outbid(self) -> None:
        from spacegame.models.captain_memory import OUTCOME_OUTBID, OUTCOME_OUTCOMPETED

        assert OUTCOME_OUTCOMPETED != OUTCOME_OUTBID

    def _state_with_player_winning_lot(self, rival_id: str = PERSONA_SALKO) -> AuctionState:
        """Craft a session_history entry where the player wins a lot a rival also bid on."""
        from spacegame.models.bidding import _SessionHistoryEntry

        st = AuctionState()
        st.active_auction_id = VENUE_STELLARIS
        st.active_session_id = "player_win_sess"
        history = _SessionHistoryEntry(
            session_id="player_win_sess",
            venue_id=VENUE_STELLARIS,
            closed_on_day=10,
            lot_results=[
                _LotResultRecord(
                    lot_id="lot_p",
                    sold=True,
                    winner_id="player",
                    sale_price=12000,
                    player_bid=True,
                    rivals_bid=[rival_id],
                ),
            ],
            rival_ids=[rival_id],
        )
        st.session_history.append(history)
        return st

    def test_single_player_win_records_outcompeted(self) -> None:
        st = self._state_with_player_winning_lot()
        captain_memory: dict = {}
        st.collect_player_win_records(captain_memory, game_day=10)
        assert PERSONA_SALKO in captain_memory
        assert captain_memory[PERSONA_SALKO].encounter_count == 1
        from spacegame.models.captain_memory import OUTCOME_OUTCOMPETED

        assert captain_memory[PERSONA_SALKO].last_outcome == OUTCOME_OUTCOMPETED
        assert captain_memory[PERSONA_SALKO].status == STATUS_ACTIVE

    def test_three_wins_auto_retire_to_wanderer(self) -> None:
        captain_memory: dict = {}
        for sess in range(3):
            from spacegame.models.bidding import _SessionHistoryEntry

            st = AuctionState()
            st.active_auction_id = VENUE_STELLARIS
            st.active_session_id = f"pw_sess_{sess}"
            history = _SessionHistoryEntry(
                session_id=f"pw_sess_{sess}",
                venue_id=VENUE_STELLARIS,
                closed_on_day=10 + sess,
                lot_results=[
                    _LotResultRecord(
                        lot_id=f"lot_pw_{sess}",
                        sold=True,
                        winner_id="player",
                        sale_price=12000,
                        player_bid=True,
                        rivals_bid=[PERSONA_SALKO],
                    ),
                ],
                rival_ids=[PERSONA_SALKO],
            )
            st.session_history.append(history)
            st.collect_player_win_records(captain_memory, game_day=10 + sess)
        assert captain_memory[PERSONA_SALKO].status == STATUS_WANDERER

    def test_player_abstention_suppresses_entry(self) -> None:
        """Player did not bid (player_bid=False); entry must not fire."""
        from spacegame.models.bidding import _SessionHistoryEntry

        st = AuctionState()
        st.active_auction_id = VENUE_STELLARIS
        st.active_session_id = "abstain_sess"
        history = _SessionHistoryEntry(
            session_id="abstain_sess",
            venue_id=VENUE_STELLARIS,
            closed_on_day=10,
            lot_results=[
                _LotResultRecord(
                    lot_id="lot_abs",
                    sold=True,
                    winner_id="player",
                    sale_price=12000,
                    player_bid=False,  # player abstained
                    rivals_bid=[PERSONA_SALKO],
                ),
            ],
            rival_ids=[PERSONA_SALKO],
        )
        st.session_history.append(history)
        captain_memory: dict = {}
        st.collect_player_win_records(captain_memory, game_day=10)
        assert PERSONA_SALKO not in captain_memory

    def test_mixed_outcomes_aggregate_against_threshold(self) -> None:
        """1 OUTBID + 2 OUTCOMPETED against same rival -> STATUS_WANDERER."""
        from spacegame.models.bidding import _SessionHistoryEntry

        captain_memory: dict = {}
        # Session 1: rival wins (OUTBID)
        st1 = AuctionState()
        st1.active_auction_id = VENUE_STELLARIS
        st1.active_session_id = "mix_sess_1"
        hist1 = _SessionHistoryEntry(
            session_id="mix_sess_1",
            venue_id=VENUE_STELLARIS,
            closed_on_day=10,
            lot_results=[
                _LotResultRecord(
                    lot_id="lot_m1",
                    sold=True,
                    winner_id=PERSONA_SALKO,
                    sale_price=12000,
                    player_bid=True,
                    rivals_bid=[PERSONA_SALKO],
                ),
            ],
            rival_ids=[PERSONA_SALKO],
        )
        st1.session_history.append(hist1)
        st1.collect_outbid_records(captain_memory, game_day=10)
        assert captain_memory[PERSONA_SALKO].status == STATUS_ACTIVE

        # Sessions 2 & 3: player wins (OUTCOMPETED)
        for sess in range(2, 4):
            st = AuctionState()
            st.active_auction_id = VENUE_STELLARIS
            st.active_session_id = f"mix_sess_{sess}"
            hist = _SessionHistoryEntry(
                session_id=f"mix_sess_{sess}",
                venue_id=VENUE_STELLARIS,
                closed_on_day=10 + sess,
                lot_results=[
                    _LotResultRecord(
                        lot_id=f"lot_m{sess}",
                        sold=True,
                        winner_id="player",
                        sale_price=12000,
                        player_bid=True,
                        rivals_bid=[PERSONA_SALKO],
                    ),
                ],
                rival_ids=[PERSONA_SALKO],
            )
            st.session_history.append(hist)
            st.collect_player_win_records(captain_memory, game_day=10 + sess)
        assert captain_memory[PERSONA_SALKO].status == STATUS_WANDERER

    def test_other_rival_unaffected(self) -> None:
        """Only the rival who bid on the won lot accumulates; others are unaffected."""
        from spacegame.models.bidding import _SessionHistoryEntry

        st = AuctionState()
        st.active_auction_id = VENUE_STELLARIS
        st.active_session_id = "other_sess"
        history = _SessionHistoryEntry(
            session_id="other_sess",
            venue_id=VENUE_STELLARIS,
            closed_on_day=10,
            lot_results=[
                _LotResultRecord(
                    lot_id="lot_o",
                    sold=True,
                    winner_id="player",
                    sale_price=12000,
                    player_bid=True,
                    rivals_bid=[PERSONA_SALKO],  # only Salko bid
                ),
            ],
            rival_ids=[PERSONA_SALKO, PERSONA_PRENTISS],
        )
        st.session_history.append(history)
        captain_memory: dict = {}
        st.collect_player_win_records(captain_memory, game_day=10)
        assert PERSONA_SALKO in captain_memory
        assert PERSONA_PRENTISS not in captain_memory
