"""SA-B2: AI bidder persona value functions, behavior axes, archetype factories."""

from __future__ import annotations

import pytest

from spacegame.models.bidding_lot import (
    LOT_CATEGORY_ANTIQUITY,
    LOT_CATEGORY_CONTRABAND,
    LOT_CATEGORY_FACTION_COMMODITY,
    LOT_CATEGORY_MODULE,
    LOT_CATEGORY_RESTRICTED_WEAPON,
    LOT_CATEGORY_SALVAGE_LOT,
    VENUE_CRIMSON_REACH,
    VENUE_STELLARIS,
    AuctionLot,
)
from spacegame.models.bidding_persona import (
    AGGRESSION_HIGH_DELAY_MAX,
    AGGRESSION_MID_DELAY_MAX,
    AGGRESSION_MID_DELAY_MIN,
    PERSONA_KADE,
    PERSONA_PRENTISS,
    SALKO_ESCALATION_BONUS,
    SNIPE_RESPONSE_THRESHOLD,
    AIBidderPersona,
    _seeded_drift,
    make_kade,
    make_prentiss,
    make_reach_flavor,
    make_salko,
    make_stellaris_speculator,
)


def _make_antiquity_lot(base: int = 10000) -> AuctionLot:
    return AuctionLot(
        id="ant_lot",
        headline="Pre-Compact Astrolabe",
        description="Functional. Provenance documented.",
        category=LOT_CATEGORY_ANTIQUITY,
        venue=VENUE_STELLARIS,
        base_appraisal=base,
        reserve_pct=0.7,
    )


def _make_module_lot(base: int = 12000) -> AuctionLot:
    return AuctionLot(
        id="mod_lot",
        headline="Re-Issue Module",
        description="Documented re-issue.",
        category=LOT_CATEGORY_MODULE,
        venue=VENUE_STELLARIS,
        base_appraisal=base,
        reserve_pct=0.75,
    )


def _make_contraband_lot(base: int = 6000) -> AuctionLot:
    return AuctionLot(
        id="con_lot",
        headline="Unstamped Items",
        description="No paperwork.",
        category=LOT_CATEGORY_CONTRABAND,
        venue=VENUE_CRIMSON_REACH,
        base_appraisal=base,
        reserve_pct=0.65,
        contraband=True,
    )


class TestSeededDrift:
    def test_drift_in_designed_range(self) -> None:
        drift = _seeded_drift("session_a", PERSONA_PRENTISS)
        assert -0.05 <= drift <= 0.05

    def test_drift_is_deterministic(self) -> None:
        a = _seeded_drift("sess1", PERSONA_PRENTISS)
        b = _seeded_drift("sess1", PERSONA_PRENTISS)
        assert a == b

    def test_drift_varies_per_session(self) -> None:
        a = _seeded_drift("sess1", PERSONA_PRENTISS)
        b = _seeded_drift("sess2", PERSONA_PRENTISS)
        assert a != b

    def test_drift_varies_per_persona(self) -> None:
        a = _seeded_drift("sess1", PERSONA_PRENTISS)
        b = _seeded_drift("sess1", PERSONA_KADE)
        assert a != b


class TestPrentissValueFunction:
    def test_prentiss_antiquity_effective_value(self) -> None:
        """Design doc §4.5 spec: 10000 * 1.40 * (1 + drift), drift in ±0.05."""
        prentiss = make_prentiss()
        lot = _make_antiquity_lot(10000)
        ev = prentiss.compute_effective_value(lot, "session_a")
        # Effective value should be within ±5% of 14000 (1.40 * base) per drift cap.
        assert 13300 <= ev <= 14700

    def test_prentiss_ceiling_is_110_percent_of_effective(self) -> None:
        prentiss = make_prentiss()
        lot = _make_antiquity_lot(10000)
        ev = prentiss.compute_effective_value(lot, "session_a")
        ceiling = prentiss.compute_ceiling(lot, "session_a")
        assert ceiling == round(ev * 1.10)

    def test_prentiss_skips_categories_outside_profile(self) -> None:
        prentiss = make_prentiss()
        salvage = AuctionLot(
            id="salv",
            headline="Bulk Salvage",
            description="--",
            category=LOT_CATEGORY_SALVAGE_LOT,
            venue=VENUE_STELLARIS,
            base_appraisal=4000,
            reserve_pct=0.7,
        )
        # ``salvage_lot`` is not in Prentiss's desire dict — desire 0.0.
        assert prentiss.compute_effective_value(salvage, "session_a") == 0
        assert prentiss.compute_ceiling(salvage, "session_a") == 0


class TestKadeValueFunction:
    def test_kade_skips_non_list_lots(self) -> None:
        """Kade has no entry for ``antiquity`` -> desire 0.0 -> sit out."""
        kade = make_kade()
        antiq = _make_antiquity_lot()
        assert kade.compute_effective_value(antiq, "session_a") == 0

    def test_kade_bids_on_list_faction_commodity(self) -> None:
        kade = make_kade()
        fc = AuctionLot(
            id="fc",
            headline="Approved Commodity",
            description="--",
            category=LOT_CATEGORY_FACTION_COMMODITY,
            venue=VENUE_STELLARIS,
            base_appraisal=8000,
            reserve_pct=0.8,
        )
        ev = kade.compute_effective_value(fc, "session_a")
        # 8000 * 1.00 * (1 ± 0.05) -> 7600..8400.
        assert 7600 <= ev <= 8400

    def test_kade_ceiling_equals_effective_value(self) -> None:
        kade = make_kade()
        fc = AuctionLot(
            id="fc",
            headline="Approved Commodity",
            description="--",
            category=LOT_CATEGORY_FACTION_COMMODITY,
            venue=VENUE_STELLARIS,
            base_appraisal=8000,
            reserve_pct=0.8,
        )
        ev = kade.compute_effective_value(fc, "session_a")
        ceiling = kade.compute_ceiling(fc, "session_a")
        assert ceiling == ev  # ceiling_ratio = 1.00


class TestSalkoValueFunction:
    def test_salko_default_ceiling_when_player_absent(self) -> None:
        salko = make_salko()
        lot = _make_module_lot(10000)
        # default desire 0.60 * base -> ev around 6000; ceiling at 0.90.
        ev = salko.compute_effective_value(lot, "session_a")
        assert 5700 <= ev <= 6300
        ceiling = salko.compute_ceiling(lot, "session_a", vs_player=False)
        assert ceiling == round(ev * 0.90)

    def test_salko_vs_player_ceiling_uses_115_override(self) -> None:
        salko = make_salko()
        lot = _make_module_lot(10000)
        ev = salko.compute_effective_value(lot, "session_a")
        ceiling_vs_player = salko.compute_ceiling(lot, "session_a", vs_player=True)
        assert ceiling_vs_player == round(ev * 1.15)

    def test_salko_player_target_escalation_adds_bonus(self) -> None:
        salko = make_salko()
        lot = _make_module_lot(10000)
        # When player has bid on modules recently, desire becomes 0.60 + 0.70 = 1.30.
        ev_no_player = salko.compute_effective_value(lot, "session_a")
        ev_with_player = salko.compute_effective_value(
            lot, "session_a", recent_player_categories=(LOT_CATEGORY_MODULE,)
        )
        assert ev_with_player > ev_no_player
        # Roughly: ev * (1.30 / 0.60) within drift tolerance.
        assert ev_with_player == pytest.approx(ev_no_player * (1.30 / 0.60), rel=0.01)

    def test_salko_escalation_only_for_matching_category(self) -> None:
        salko = make_salko()
        lot = _make_antiquity_lot(10000)
        no_player = salko.compute_effective_value(lot, "session_a")
        with_player_module = salko.compute_effective_value(
            lot, "session_a", recent_player_categories=(LOT_CATEGORY_MODULE,)
        )
        # Module category in player history but lot is antiquity -> no escalation.
        assert with_player_module == no_player


class TestStellarisSpeculator:
    def test_elevated_category_bumped_to_1_20(self) -> None:
        spec = make_stellaris_speculator(LOT_CATEGORY_MODULE, instance_index=1)
        assert spec.desire_multipliers[LOT_CATEGORY_MODULE] == pytest.approx(1.20)

    def test_other_categories_unchanged(self) -> None:
        spec = make_stellaris_speculator(LOT_CATEGORY_MODULE, instance_index=1)
        assert spec.desire_multipliers[LOT_CATEGORY_ANTIQUITY] == pytest.approx(0.9)

    def test_ceiling_ratio_is_0_85(self) -> None:
        spec = make_stellaris_speculator(LOT_CATEGORY_MODULE, instance_index=1)
        assert spec.ceiling_ratio == pytest.approx(0.85)

    def test_speculator_is_not_named_rival(self) -> None:
        spec = make_stellaris_speculator(LOT_CATEGORY_MODULE)
        assert spec.is_named_rival is False

    def test_per_instance_id_makes_drift_deterministically_distinct(self) -> None:
        spec1 = make_stellaris_speculator(LOT_CATEGORY_MODULE, instance_index=1)
        spec2 = make_stellaris_speculator(LOT_CATEGORY_MODULE, instance_index=2)
        d1 = spec1.session_signal_drift("session_a")
        d2 = spec2.session_signal_drift("session_a")
        assert d1 != d2


class TestReachFlavor:
    def test_contraband_desire_high(self) -> None:
        rf = make_reach_flavor(instance_index=1)
        assert rf.desire_multipliers[LOT_CATEGORY_CONTRABAND] == pytest.approx(1.20)

    def test_restricted_weapon_desire_mid(self) -> None:
        rf = make_reach_flavor(instance_index=1)
        assert rf.desire_multipliers[LOT_CATEGORY_RESTRICTED_WEAPON] == pytest.approx(1.10)

    def test_reach_flavor_aggressive_axes(self) -> None:
        rf = make_reach_flavor()
        assert rf.aggression >= 0.7
        assert rf.signal_discipline <= 0.4

    def test_bids_on_reach_contraband_lot(self) -> None:
        rf = make_reach_flavor()
        lot = _make_contraband_lot(5000)
        ev = rf.compute_effective_value(lot, "session_a")
        # 5000 * 1.20 * (1 ± 0.05) -> 5700..6300.
        assert 5700 <= ev <= 6300


class TestCounterBidTimingByAggression:
    @pytest.mark.parametrize(
        "aggression,expected_max_delay",
        [
            (0.9, AGGRESSION_HIGH_DELAY_MAX),
            (0.5, AGGRESSION_MID_DELAY_MAX),
        ],
    )
    def test_high_and_mid_aggression_bounds(
        self, aggression: float, expected_max_delay: float
    ) -> None:
        persona = AIBidderPersona(
            persona_id="probe",
            display_name="Probe",
            desire_multipliers={"module": 1.0},
            aggression=aggression,
            snipe_resistance=0.5,
        )
        delay = persona.counter_bid_delay("sess", round_number=1, round_duration_seconds=30.0)
        assert 0.5 <= delay <= expected_max_delay + 0.001

    def test_high_aggression_fires_within_one_second(self) -> None:
        persona = AIBidderPersona(
            persona_id="probe",
            display_name="Probe",
            desire_multipliers={"module": 1.0},
            aggression=0.9,
            snipe_resistance=0.5,
        )
        delay = persona.counter_bid_delay("sess", round_number=1, round_duration_seconds=30.0)
        assert delay <= AGGRESSION_HIGH_DELAY_MAX + 0.001

    def test_mid_aggression_within_3_to_7_seconds(self) -> None:
        persona = AIBidderPersona(
            persona_id="probe",
            display_name="Probe",
            desire_multipliers={"module": 1.0},
            aggression=0.5,
            snipe_resistance=0.5,
        )
        delay = persona.counter_bid_delay("sess", round_number=1, round_duration_seconds=30.0)
        assert AGGRESSION_MID_DELAY_MIN <= delay <= AGGRESSION_MID_DELAY_MAX

    def test_low_aggression_lands_in_final_40_percent(self) -> None:
        persona = AIBidderPersona(
            persona_id="probe",
            display_name="Probe",
            desire_multipliers={"module": 1.0},
            aggression=0.2,
            snipe_resistance=0.5,
        )
        round_dur = 30.0
        delay = persona.counter_bid_delay("sess", round_number=1, round_duration_seconds=round_dur)
        # Final 40% -> [18.0, 30.0] minus jitter; clamp at 0.5.
        assert delay >= round_dur * 0.6
        assert delay <= round_dur

    def test_asap_compresses_with_min_spacing(self) -> None:
        persona = AIBidderPersona(
            persona_id="probe",
            display_name="Probe",
            desire_multipliers={"module": 1.0},
            aggression=0.5,
            snipe_resistance=0.5,
        )
        # Mid aggression at speed 0.1: base in [3.0, 7.0]; compressed to
        # [0.3, 0.7]; clamped to >= 0.5.
        delay = persona.counter_bid_delay(
            "sess", round_number=1, round_duration_seconds=8.0, speed_multiplier=0.1
        )
        assert delay >= 0.5

    def test_counter_delay_deterministic_across_calls(self) -> None:
        persona = make_prentiss()
        d1 = persona.counter_bid_delay("sess", round_number=1, round_duration_seconds=30.0)
        d2 = persona.counter_bid_delay("sess", round_number=1, round_duration_seconds=30.0)
        assert d1 == d2

    def test_counter_delay_changes_per_round(self) -> None:
        persona = make_prentiss()
        d1 = persona.counter_bid_delay("sess", round_number=1, round_duration_seconds=30.0)
        d2 = persona.counter_bid_delay("sess", round_number=2, round_duration_seconds=30.0)
        # Hashed seed differs by round; statistically-near-zero collision.
        assert d1 != d2


class TestSnipeResistanceGate:
    @pytest.mark.parametrize(
        "snipe_resistance,expected",
        [(0.2, False), (0.49, False), (0.5, True), (0.95, True)],
    )
    def test_will_counter_snipe_at_threshold(self, snipe_resistance: float, expected: bool) -> None:
        persona = AIBidderPersona(
            persona_id="probe",
            display_name="Probe",
            desire_multipliers={"module": 1.0},
            snipe_resistance=snipe_resistance,
        )
        assert persona.will_counter_snipe() is expected

    def test_threshold_constant_value(self) -> None:
        assert SNIPE_RESPONSE_THRESHOLD == 0.5


class TestSalkoEscalationConstants:
    def test_escalation_bonus_value(self) -> None:
        assert SALKO_ESCALATION_BONUS == 0.70

    def test_salko_factory_escalates_all_categories(self) -> None:
        salko = make_salko()
        assert "module" in salko.player_target_escalation_categories
        assert "antiquity" in salko.player_target_escalation_categories
