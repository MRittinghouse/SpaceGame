"""A2-10: Permanent closure save/load round-trip scenarios.

Verifies that dilemma resolution state (closed lenses, tier unlocks,
dialogue flags) survives save/load, and that closed lenses cannot
be reopened afterward.

Uses synthetic fixture ids so the tests do not depend on real dilemma
data landing in data/narrative/dilemmas/.
"""

from __future__ import annotations

from spacegame.constants.flags import dilemma_resolved, lens_closed
from spacegame.models.dilemma import (
    Dilemma,
    DilemmaOutcome,
    check_dilemmas,
    resolve,
)
from spacegame.models.lens_investment import LensInvestment
from tests.test_scenarios._helpers import fresh_player, round_trip_save


def _test_dilemma() -> Dilemma:
    """Synthetic two-pole dilemma for scenario tests."""
    return Dilemma(
        id="d_test_closure",
        poles=["wealth", "community"],
        collision_requires=2,
        telegraph_threshold=55,
        collision_threshold=80,
        telegraph_npc_id="priya_osei",
        telegraph_lines=["test_line"],
        outcomes=[
            DilemmaOutcome(
                winning_lens_id="wealth",
                closes=["community"],
                tier_unlocks=["tier_commerce_deep"],
                outcome_flag="outcome_chose_wealth",
                narration_summary="You chose wealth.",
            ),
            DilemmaOutcome(
                winning_lens_id="community",
                closes=["wealth"],
                tier_unlocks=["tier_social_deep"],
                outcome_flag="outcome_chose_community",
                narration_summary="You chose community.",
            ),
        ],
    )


class TestDilemmaClosureRoundTrip:
    """AC5: all closure state survives save/load."""

    def test_closed_lenses_survive_round_trip(self) -> None:
        player = fresh_player()
        dilemma = _test_dilemma()
        resolve(dilemma, "wealth", player)

        restored = round_trip_save(player)
        assert "community" in restored.dilemma_state.closed_lenses, (
            "closed_lenses must survive save/load"
        )

    def test_tier_unlocks_granted_survive_round_trip(self) -> None:
        player = fresh_player()
        dilemma = _test_dilemma()
        resolve(dilemma, "wealth", player)

        restored = round_trip_save(player)
        assert restored.dilemma_state.tier_unlocks_granted.get("wealth") == [
            "tier_commerce_deep"
        ], "tier_unlocks_granted must survive save/load"

    def test_lens_closed_flag_survives_round_trip(self) -> None:
        player = fresh_player()
        dilemma = _test_dilemma()
        resolve(dilemma, "wealth", player)

        restored = round_trip_save(player)
        assert restored.dialogue_flags.get(lens_closed("community")) is True, (
            "lens_closed flag must survive save/load"
        )

    def test_dilemma_resolved_flag_survives_round_trip(self) -> None:
        player = fresh_player()
        dilemma = _test_dilemma()
        resolve(dilemma, "wealth", player)

        restored = round_trip_save(player)
        assert restored.dialogue_flags.get(dilemma_resolved("d_test_closure")) is True, (
            "dilemma_resolved flag must survive save/load"
        )

    def test_resolved_map_survives_round_trip(self) -> None:
        player = fresh_player()
        dilemma = _test_dilemma()
        resolve(dilemma, "wealth", player)

        restored = round_trip_save(player)
        assert restored.dilemma_state.resolved.get("d_test_closure") == "wealth"


class TestClosureIrreversibilityAfterLoad:
    """AC6: post-load, closed lens cannot be reopened and coordinator does not re-fire."""

    def test_closed_lens_investment_suppressed_after_load(self) -> None:
        """AC6a: post-load investment on closed lens does not increase."""
        player = fresh_player()
        dilemma = _test_dilemma()
        resolve(dilemma, "wealth", player)
        restored = round_trip_save(player)

        before = restored.lens_investment.get_investment("community")
        # "sold_cargo" normally raises community investment — must be suppressed now.
        restored.record_lens_action("sold_cargo", 10)
        after = restored.lens_investment.get_investment("community")
        assert after == before, (
            f"Post-load: closed lens 'community' must not gain investment: "
            f"before={before}, after={after}"
        )

    def test_coordinator_skips_resolved_dilemma_after_load(self) -> None:
        """AC6b: coordinator does not re-fire a resolved dilemma after save/load."""
        player = fresh_player()
        dilemma = _test_dilemma()
        # Set investment above collision threshold for both poles.
        player.lens_investment = LensInvestment(_values={"wealth": 100, "community": 100})
        resolve(dilemma, "wealth", player)
        restored = round_trip_save(player)
        restored.lens_investment = LensInvestment(_values={"wealth": 100, "community": 100})

        result = check_dilemmas(restored, {"d_test_closure": dilemma})
        assert "d_test_closure" not in result.newly_collided, (
            "Coordinator must skip resolved dilemma after save/load"
        )
        assert "d_test_closure" not in result.newly_telegraphed
        assert "d_test_closure" not in result.re_telegraphed
