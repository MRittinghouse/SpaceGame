"""Known-answer and edge-case tests for SimRng (SP2 spec Section 3)."""

from __future__ import annotations

import pytest

from spacegame.sim_rng import SimRng, build_key, seed_entropy, stable_seed
from tests.sim_rng_helpers import ScriptedRng


class _ScriptedU32(SimRng):
    """Feeds randint a fixed sequence of raw 32-bit draws."""

    def __init__(self, draws: list[int]) -> None:
        super().__init__(1, 2, 3, 4)
        self._draws = list(draws)

    def next_u32(self) -> int:
        return self._draws.pop(0)


class TestAlgorithm:
    def test_reference_sequence_from_state_1_2_3_4(self) -> None:
        rng = SimRng(1, 2, 3, 4)
        got = [rng.next_u32() for _ in range(4)]
        assert got == [11520, 0, 5927040, 70819200], f"xoshiro128** reference mismatch: {got}"

    def test_md5_seeding_of_key_a(self) -> None:
        # md5("a") = 0cc175b9 c0f1b6a8 31c399e2 69772661, read as little-endian words.
        assert SimRng.from_key("a").state() == (0xB975C10C, 0xA8B6F1C0, 0xE299C331, 0x61267769)

    def test_all_zero_state_uses_fallback_word(self) -> None:
        assert SimRng(0, 0, 0, 0).state() == (0x9E3779B9, 0, 0, 0)

    def test_randf_is_top_24_bits(self) -> None:
        a = SimRng.from_key("k")
        b = SimRng.from_key("k")
        assert a.randf() == (b.next_u32() >> 8) / 16777216.0


class TestKeys:
    def test_parts_join_with_pipe(self) -> None:
        assert build_key("market", 1, "iron_ore") == "market|1|iron_ore"

    def test_negative_int_and_empty_string_are_valid(self) -> None:
        assert build_key("neg", -5, "") == "neg|-5|"

    @pytest.mark.parametrize("bad", [True, 1.5, None])
    def test_bool_float_none_are_rejected(self, bad: object) -> None:
        with pytest.raises(TypeError, match="str or int"):
            build_key("x", bad)  # type: ignore[arg-type]

    def test_same_key_same_stream(self) -> None:
        a = SimRng.from_key("market", 3, "food", "verdant")
        b = SimRng.from_key("market", 3, "food", "verdant")
        assert [a.next_u32() for _ in range(8)] == [b.next_u32() for _ in range(8)]

    def test_stable_seed_is_first_state_word(self) -> None:
        assert stable_seed("player", "Ada") == SimRng.from_key("player", "Ada").state()[0]


class TestRandint:
    def test_bounds_inclusive(self) -> None:
        rng = SimRng.from_key("randint")
        values = {rng.randint(1, 6) for _ in range(500)}
        assert values == {1, 2, 3, 4, 5, 6}

    def test_rejection_skips_values_at_or_above_limit(self) -> None:
        # n = 3, limit = (2**32 // 3) * 3 = 4294967295: that draw is rejected.
        rng = _ScriptedU32([4294967295, 7])
        assert rng.randint(0, 2) == 1

    def test_full_32_bit_span_is_allowed(self) -> None:
        assert SimRng.from_key("span").randint(0, 2**32 - 1) >= 0

    @pytest.mark.parametrize(("lo", "hi"), [(5, 4), (0, 2**32)])
    def test_invalid_spans_raise(self, lo: int, hi: int) -> None:
        with pytest.raises(ValueError):
            SimRng.from_key("bad").randint(lo, hi)


class TestUniformAndChance:
    def test_uniform_matches_formula_symmetric_range(self) -> None:
        a = SimRng.from_key("uniform")
        b = SimRng.from_key("uniform")
        assert a.uniform(-0.1, 0.1) == -0.1 + (0.1 - -0.1) * b.randf()

    def test_uniform_matches_formula_nonsymmetric_range(self) -> None:
        a = SimRng.from_key("uniform2")
        b = SimRng.from_key("uniform2")
        assert a.uniform(2.0, 5.0) == 2.0 + (5.0 - 2.0) * b.randf()

    @pytest.mark.parametrize("p", [0.1, 0.5, 0.9])
    def test_chance_matches_formula(self, p: float) -> None:
        a = SimRng.from_key("chance", str(p))
        b = SimRng.from_key("chance", str(p))
        assert a.chance(p) == (b.randf() < p)

    def test_chance_zero_is_always_false(self) -> None:
        assert SimRng.from_key("chance0").chance(0.0) is False

    def test_chance_one_is_always_true(self) -> None:
        assert SimRng.from_key("chance1").chance(1.0) is True

    def test_uniform_and_chance_do_not_consume_scripted_random(self) -> None:
        rng = ScriptedRng([0.0])
        rng.uniform(0.0, 1.0)
        rng.chance(0.5)
        assert rng.random() == 0.0


class TestSequences:
    def test_choice_empty_raises(self) -> None:
        with pytest.raises(IndexError):
            SimRng.from_key("c").choice([])

    def test_sample_bounds(self) -> None:
        rng = SimRng.from_key("s")
        assert rng.sample([1, 2, 3], 0) == []
        with pytest.raises(ValueError):
            rng.sample([1, 2, 3], 4)
        with pytest.raises(ValueError):
            rng.sample([1, 2, 3], -1)

    def test_sample_returns_distinct_members(self) -> None:
        got = SimRng.from_key("s").sample(list(range(10)), 4)
        assert len(set(got)) == 4 and set(got) <= set(range(10))

    def test_shuffle_is_a_permutation(self) -> None:
        items = list(range(10))
        SimRng.from_key("sh").shuffle(items)
        assert sorted(items) == list(range(10))

    def test_weighted_index_never_picks_zero_weight(self) -> None:
        rng = SimRng.from_key("w")
        picks = {rng.weighted_index([1.0, 0.0, 3.5]) for _ in range(300)}
        assert picks == {0, 2}

    @pytest.mark.parametrize("weights", [[], [0.0, 0.0]])
    def test_weighted_index_degenerate_raises(self, weights: list[float]) -> None:
        with pytest.raises(ValueError):
            SimRng.from_key("w").weighted_index(weights)

    def test_choices_with_mismatched_weights_raises(self) -> None:
        with pytest.raises(ValueError):
            SimRng.from_key("c").choices(["a", "b"], weights=[1.0], k=1)

    def test_choices_matches_weighted_index(self) -> None:
        a = SimRng.from_key("cw")
        b = SimRng.from_key("cw")
        assert (
            a.choices(["x", "y", "z"], weights=[1, 2, 3], k=1)[0]
            == ["x", "y", "z"][b.weighted_index([1, 2, 3])]
        )


class TestStateAndEntropy:
    def test_serialize_round_trip(self) -> None:
        rng = SimRng.from_key("state")
        rng.next_u32()
        clone = SimRng.deserialize(rng.serialize())
        assert clone.state() == rng.state()
        assert all(isinstance(w, str) for w in rng.serialize())

    def test_deserialize_needs_four_words(self) -> None:
        with pytest.raises(ValueError):
            SimRng.deserialize(["1", "2", "3"])

    def test_seeded_entropy_is_reproducible(self) -> None:
        seed_entropy(7)
        first = [SimRng.from_entropy().next_u32() for _ in range(3)]
        seed_entropy(7)
        second = [SimRng.from_entropy().next_u32() for _ in range(3)]
        seed_entropy(None)
        assert first == second

    def test_unseeded_entropy_differs(self) -> None:
        seed_entropy(None)
        assert SimRng.from_entropy().state() != SimRng.from_entropy().state()


class TestScriptedRng:
    def test_random_returns_scripted_values_then_fails(self) -> None:
        rng = ScriptedRng([0.25, 0.75])
        assert rng.random() == 0.25
        assert rng.random() == 0.75
        with pytest.raises(AssertionError, match="ran out"):
            rng.random()

    def test_other_draws_are_real(self) -> None:
        assert ScriptedRng([0.0]).randint(0, 9) == SimRng.from_key("scripted").randint(0, 9)
