"""Tests for LensInvestment — the per-lens accrual store (A2-4).

Covers the model surface: accrual, query, threshold predicate, action-tag
walking, and serialization. See ``requirements/roadmap/ROADMAP.md`` sprint
A2-4 for scope. NPC-address / offered-work reactions are the scope of the
sibling sprint A2-4A; A2-4 owns state and query only.
"""

from __future__ import annotations

import pytest

from spacegame.models.lens import Lens
from spacegame.models.lens_investment import LensInvestment


def _lens(lens_id: str, investment_from: tuple[str, ...] = ()) -> Lens:
    """Build a minimal Lens for tests (all narrative text is placeholder)."""
    return Lens(
        lens_id=lens_id,
        name=lens_id.replace("_", " ").title(),
        core_fantasy="unused",
        question="unused",
        sees="unused",
        wants="unused",
        trades="unused",
        investment_from=investment_from,
        minigame_shape="deduction",
        voice="unused",
        tier_unlocks=(),
    )


class TestLensInvestmentBasics:
    def test_get_investment_defaults_to_zero_for_unknown_lens(self) -> None:
        inv = LensInvestment()
        assert inv.get_investment("vengeance") == 0

    def test_add_investment_accrues(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 5, source="test")
        assert inv.get_investment("wealth") == 5

    def test_add_investment_multiple_calls_sum(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 5, source="test")
        inv.add_investment("wealth", 3, source="test")
        inv.add_investment("wealth", 2, source="test")
        assert inv.get_investment("wealth") == 10

    def test_add_investment_zero_is_accepted_no_change(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 5, source="test")
        inv.add_investment("wealth", 0, source="test")
        assert inv.get_investment("wealth") == 5

    def test_add_investment_rejects_negative_amount_with_valueerror(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 5, source="test")
        with pytest.raises(ValueError):
            inv.add_investment("wealth", -3, source="closure_attempt")
        # Value unchanged.
        assert inv.get_investment("wealth") == 5

    def test_add_investment_rejects_negative_on_unraised_lens(self) -> None:
        inv = LensInvestment()
        with pytest.raises(ValueError):
            inv.add_investment("wealth", -1, source="test")
        assert inv.get_investment("wealth") == 0

    def test_add_investment_stores_unknown_lens_id_verbatim(self) -> None:
        """Validation is A2-1's job; the model records any string key."""
        inv = LensInvestment()
        inv.add_investment("not_a_real_lens", 7, source="test")
        assert inv.get_investment("not_a_real_lens") == 7

    def test_is_at_or_above_returns_true_at_boundary(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 25, source="test")
        assert inv.is_at_or_above("wealth", 25) is True

    def test_is_at_or_above_returns_true_above_boundary(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 30, source="test")
        assert inv.is_at_or_above("wealth", 25) is True

    def test_is_at_or_above_returns_false_below_boundary(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 24, source="test")
        assert inv.is_at_or_above("wealth", 25) is False

    def test_is_at_or_above_on_unraised_lens_returns_false_for_positive_threshold(
        self,
    ) -> None:
        inv = LensInvestment()
        assert inv.is_at_or_above("vengeance", 1) is False

    def test_is_at_or_above_on_unraised_lens_returns_true_for_zero_threshold(
        self,
    ) -> None:
        inv = LensInvestment()
        assert inv.is_at_or_above("vengeance", 0) is True

    def test_per_lens_isolation_verified_across_three_lens_fixture(self) -> None:
        """AC1: per-lens accrual verified with a synthetic 3-lens fixture."""
        inv = LensInvestment()
        inv.add_investment("vengeance", 7, source="test")
        inv.add_investment("wealth", 12, source="test")
        inv.add_investment("legacy", 3, source="test")
        assert inv.get_investment("vengeance") == 7
        assert inv.get_investment("wealth") == 12
        assert inv.get_investment("legacy") == 3


class TestRecordAction:
    def test_walks_registry_and_increments_matching_lenses(self) -> None:
        inv = LensInvestment()
        lenses = {
            "vengeance": _lens("vengeance", ("combat_victory_named_target",)),
            "wealth": _lens("wealth", ("sold_cargo",)),
        }
        inv.record_action("combat_victory_named_target", 5, lenses)
        assert inv.get_investment("vengeance") == 5
        assert inv.get_investment("wealth") == 0

    def test_ignores_lens_whose_investment_from_does_not_contain_tag(self) -> None:
        inv = LensInvestment()
        lenses = {
            "wealth": _lens("wealth", ("sold_cargo",)),
        }
        inv.record_action("combat_victory_named_target", 5, lenses)
        assert inv.get_investment("wealth") == 0

    def test_returns_list_of_incremented_lens_ids(self) -> None:
        inv = LensInvestment()
        lenses = {
            "vengeance": _lens("vengeance", ("combat_victory_named_target",)),
            "legacy": _lens("legacy", ("combat_victory_named_target",)),
            "wealth": _lens("wealth", ("sold_cargo",)),
        }
        incremented = inv.record_action("combat_victory_named_target", 3, lenses)
        assert incremented == ["vengeance", "legacy"]

    def test_with_empty_registry_returns_empty_list(self) -> None:
        inv = LensInvestment()
        incremented = inv.record_action("combat_victory_named_target", 5, {})
        assert incremented == []

    def test_tag_match_is_exact_not_substring(self) -> None:
        """A lens listing ``combat_victory`` must NOT match ``combat_victory_named_target``."""
        inv = LensInvestment()
        lenses = {
            "wealth": _lens("wealth", ("combat_victory",)),
        }
        inv.record_action("combat_victory_named_target", 5, lenses)
        assert inv.get_investment("wealth") == 0

    def test_multiple_tags_on_one_lens_all_match(self) -> None:
        inv = LensInvestment()
        lenses = {
            "wealth": _lens("wealth", ("sold_cargo", "auction_won")),
        }
        inv.record_action("sold_cargo", 4, lenses)
        inv.record_action("auction_won", 6, lenses)
        assert inv.get_investment("wealth") == 10

    def test_seventeenth_lens_added_purely_via_fixture_is_still_matched(self) -> None:
        """AC8: adding a new lens requires no change to lens_investment.py."""
        inv = LensInvestment()
        lenses = {
            "wealth": _lens("wealth", ("sold_cargo",)),
            "seventeenth_novel_lens": _lens("seventeenth_novel_lens", ("novel_action_tag",)),
        }
        incremented = inv.record_action("novel_action_tag", 4, lenses)
        assert incremented == ["seventeenth_novel_lens"]
        assert inv.get_investment("seventeenth_novel_lens") == 4

    def test_record_action_propagates_negative_amount_rejection(self) -> None:
        """A negative amount into record_action still raises ValueError (via add)."""
        inv = LensInvestment()
        lenses = {
            "wealth": _lens("wealth", ("sold_cargo",)),
        }
        with pytest.raises(ValueError):
            inv.record_action("sold_cargo", -1, lenses)

    def test_record_action_with_no_matching_lens_leaves_others_alone(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 9, source="prior")
        lenses = {
            "vengeance": _lens("vengeance", ("combat_victory_named_target",)),
        }
        inv.record_action("sold_cargo", 5, lenses)
        assert inv.get_investment("wealth") == 9
        assert inv.get_investment("vengeance") == 0


class TestLensInvestmentSerialization:
    def test_to_dict_emits_current_values_wrapped(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 12, source="test")
        inv.add_investment("vengeance", 3, source="test")
        payload = inv.to_dict()
        assert payload == {"values": {"wealth": 12, "vengeance": 3}}

    def test_to_dict_on_empty_state_returns_wrapped_empty_dict(self) -> None:
        inv = LensInvestment()
        assert inv.to_dict() == {"values": {}}

    def test_from_dict_missing_key_returns_empty_state(self) -> None:
        inv = LensInvestment.from_dict({})
        assert inv.get_investment("wealth") == 0

    def test_from_dict_round_trip_preserves_values(self) -> None:
        inv = LensInvestment()
        inv.add_investment("wealth", 12, source="test")
        inv.add_investment("vengeance", 3, source="test")
        restored = LensInvestment.from_dict(inv.to_dict())
        assert restored.get_investment("wealth") == 12
        assert restored.get_investment("vengeance") == 3

    def test_from_dict_accepts_bare_dict_of_int(self) -> None:
        """Defensive: partial rollouts may have emitted the bare dict shape."""
        restored = LensInvestment.from_dict({"wealth": 8, "legacy": 4})
        assert restored.get_investment("wealth") == 8
        assert restored.get_investment("legacy") == 4

    def test_from_dict_drops_non_int_values_without_crashing(self) -> None:
        payload = {"values": {"wealth": 8, "corrupt": "not_an_int", "also_bad": None}}
        restored = LensInvestment.from_dict(payload)
        assert restored.get_investment("wealth") == 8
        assert restored.get_investment("corrupt") == 0
        assert restored.get_investment("also_bad") == 0

    def test_from_dict_drops_negative_values_without_crashing(self) -> None:
        """A malformed save must not violate the monotonic-rise invariant."""
        payload = {"values": {"wealth": -5, "legacy": 3}}
        restored = LensInvestment.from_dict(payload)
        assert restored.get_investment("wealth") == 0
        assert restored.get_investment("legacy") == 3

    def test_from_dict_rejects_non_dict_input_gracefully(self) -> None:
        """A truly malformed value (list, string) yields empty state."""
        assert LensInvestment.from_dict([]).get_investment("wealth") == 0  # type: ignore[arg-type]
        assert LensInvestment.from_dict("nope").get_investment("wealth") == 0  # type: ignore[arg-type]
