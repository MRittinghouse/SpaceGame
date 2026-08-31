"""Content-uniqueness and structural integrity guards for the lens registry.

Checks that:
(a) No two lenses share a ``minigame_shape`` string (case-insensitive).
(b) Every ``investment_from`` tag matches the canonical snake_case pattern.
(c) Exploration and Discovery are textually distinct on ``question``, ``sees``, and ``wants``.
(d) Political Power and Revolution are textually distinct on ``question`` and ``minigame_shape``.

Tests skip cleanly when the referenced lens_id is absent from the registry, so A2-6
(running before A2-5 in a race) does not fail this file's absent-lens assertions.
The empty-registry case is guarded against: if no lenses load the test skips with a
reason rather than silently passing.
"""

from __future__ import annotations

import re

import pytest

_TAG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(:[a-z][a-z0-9_]*)?$")


def _load() -> dict:
    """Return the loaded lens registry (lazy import, keyed by lens_id)."""
    from spacegame.data_loader import get_data_loader

    loader = get_data_loader()
    return loader.lenses


class TestMinigameShapeUniqueness:
    def test_minigame_shape_is_unique_across_registry(self) -> None:
        """No two lenses in the registry may share a ``minigame_shape`` string.

        Case-insensitive, exact match after ``.strip().lower()``. Guards against
        the reskin failure mode Spec F names explicitly.
        """
        lenses = _load()
        if not lenses:
            pytest.skip(
                "Lens registry is empty -- uniqueness check would scan nothing. "
                "Expected while A2-5/A2-6 have not yet landed."
            )

        seen: dict[str, str] = {}
        duplicates: list[str] = []
        for lens_id, lens in lenses.items():
            key = lens.minigame_shape.strip().lower()
            if key in seen:
                duplicates.append(
                    f"'{lens_id}' and '{seen[key]}' share minigame_shape: {lens.minigame_shape!r}"
                )
            else:
                seen[key] = lens_id

        assert not duplicates, (
            "Duplicate minigame_shape values detected across lens registry:\n"
            + "\n".join(duplicates)
        )


class TestInvestmentFromTags:
    def test_investment_from_tags_match_pattern(self) -> None:
        """Every ``investment_from`` tag must match ``^[a-z][a-z0-9_]*(:[a-z][a-z0-9_]*)?$``.

        Snake_case, optional single colon-qualifier. No hyphens, no uppercase,
        no spaces, at most one colon.
        """
        lenses = _load()
        if not lenses:
            pytest.skip(
                "Lens registry is empty -- tag pattern check would scan nothing. "
                "Expected while A2-5/A2-6 have not yet landed."
            )

        violations: list[str] = []
        for lens_id, lens in lenses.items():
            for tag in lens.investment_from:
                if not _TAG_PATTERN.match(tag):
                    violations.append(
                        f"lens '{lens_id}': tag {tag!r} does not match "
                        r"^[a-z][a-z0-9_]*(:[a-z][a-z0-9_]*)?$"
                    )

        assert not violations, "Malformed investment_from tags in lens registry:\n" + "\n".join(
            violations
        )


class TestExplorationDiscoveryDistinctness:
    """Exploration and Discovery must not collapse to the same reading.

    Spec F names this as the most common easy-collapse pair.
    Tests skip cleanly when either lens is absent, so concurrent A2-5/A2-6
    runs do not cross-fail.
    """

    def _get_pair(self) -> tuple | None:
        lenses = _load()
        expl = lenses.get("exploration")
        disc = lenses.get("discovery")
        if expl is None or disc is None:
            return None
        return expl, disc

    def test_exploration_and_discovery_question_distinct(self) -> None:
        """Exploration and Discovery must not share the same ``question`` text."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'exploration' or 'discovery' not yet in registry.")
        expl, disc = pair
        assert expl.question != disc.question, (
            "Exploration and Discovery share the same 'question' -- they must be distinct."
        )

    def test_exploration_and_discovery_sees_distinct(self) -> None:
        """Exploration and Discovery must not share the same ``sees`` text."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'exploration' or 'discovery' not yet in registry.")
        expl, disc = pair
        assert expl.sees != disc.sees, (
            "Exploration and Discovery share the same 'sees' -- they must be distinct."
        )

    def test_exploration_and_discovery_wants_distinct(self) -> None:
        """Exploration and Discovery must not share the same ``wants`` text."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'exploration' or 'discovery' not yet in registry.")
        expl, disc = pair
        assert expl.wants != disc.wants, (
            "Exploration and Discovery share the same 'wants' -- they must be distinct."
        )


class TestPoliticalPowerRevolutionDistinctness:
    """Political Power and Revolution must not collapse -- Spec F names this trio explicitly.

    Tests skip cleanly when either lens is absent.
    """

    def _get_pair(self) -> tuple | None:
        lenses = _load()
        pp = lenses.get("political_power")
        rev = lenses.get("revolution")
        if pp is None or rev is None:
            return None
        return pp, rev

    def test_political_power_and_revolution_question_distinct(self) -> None:
        """Political Power and Revolution must not share the same ``question`` text."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'political_power' or 'revolution' not yet in registry.")
        pp, rev = pair
        assert pp.question != rev.question, (
            "Political Power and Revolution share the same 'question' -- they must be distinct."
        )

    def test_political_power_and_revolution_minigame_shape_distinct(self) -> None:
        """Political Power and Revolution must not share the same ``minigame_shape``."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'political_power' or 'revolution' not yet in registry.")
        pp, rev = pair
        assert pp.minigame_shape.strip().lower() != rev.minigame_shape.strip().lower(), (
            "Political Power and Revolution share the same 'minigame_shape' -- "
            "they must be mechanically distinct."
        )


class TestEmpireTrioDistinctness:
    """Empire, Political Power, and Revolution must not collapse to the same reading.

    Spec F names this trio explicitly: master the system, break it, or become it.
    Extends TestPoliticalPowerRevolutionDistinctness by adding the Empire leg.
    Tests skip cleanly when any lens of the trio is absent.
    """

    def _get_trio(self) -> tuple | None:
        lenses = _load()
        emp = lenses.get("empire")
        pp = lenses.get("political_power")
        rev = lenses.get("revolution")
        if emp is None or pp is None or rev is None:
            return None
        return emp, pp, rev

    def test_empire_political_power_question_distinct(self) -> None:
        """Empire and Political Power must not share the same ``question`` text."""
        trio = self._get_trio()
        if trio is None:
            pytest.skip("'empire', 'political_power', or 'revolution' not yet in registry.")
        emp, pp, _rev = trio
        assert emp.question != pp.question, (
            "Empire and Political Power share the same 'question' -- they must be distinct."
        )

    def test_empire_political_power_minigame_shape_distinct(self) -> None:
        """Empire and Political Power must not share the same ``minigame_shape``."""
        trio = self._get_trio()
        if trio is None:
            pytest.skip("'empire', 'political_power', or 'revolution' not yet in registry.")
        emp, pp, _rev = trio
        assert emp.minigame_shape.strip().lower() != pp.minigame_shape.strip().lower(), (
            "Empire and Political Power share the same 'minigame_shape' -- "
            "they must be mechanically distinct."
        )

    def test_empire_revolution_question_distinct(self) -> None:
        """Empire and Revolution must not share the same ``question`` text."""
        trio = self._get_trio()
        if trio is None:
            pytest.skip("'empire', 'political_power', or 'revolution' not yet in registry.")
        emp, _pp, rev = trio
        assert emp.question != rev.question, (
            "Empire and Revolution share the same 'question' -- they must be distinct."
        )

    def test_empire_revolution_minigame_shape_distinct(self) -> None:
        """Empire and Revolution must not share the same ``minigame_shape``."""
        trio = self._get_trio()
        if trio is None:
            pytest.skip("'empire', 'political_power', or 'revolution' not yet in registry.")
        emp, _pp, rev = trio
        assert emp.minigame_shape.strip().lower() != rev.minigame_shape.strip().lower(), (
            "Empire and Revolution share the same 'minigame_shape' -- "
            "they must be mechanically distinct."
        )


class TestCommunityWealthSameWound:
    """Community and Wealth must read as 'the same wound, opposite conclusion'.

    Spec F's 'Wealth vs Community' note: the same childhood produces both ambitions.
    Asserts their ``sees`` fields are distinct and each anchored to its own discriminant
    word set (people-focused vs market-focused). Tests skip cleanly when either lens absent.
    """

    _COMMUNITY_DISCRIMINANTS: frozenset[str] = frozenset(
        {"survivors", "cryo", "families", "housing", "shelter", "people"}
    )
    _WEALTH_DISCRIMINANTS: frozenset[str] = frozenset(
        {"supply", "gap", "route", "margin", "tonnage", "price"}
    )

    def _get_pair(self) -> tuple | None:
        lenses = _load()
        comm = lenses.get("community")
        wlth = lenses.get("wealth")
        if comm is None or wlth is None:
            return None
        return comm, wlth

    def test_community_and_wealth_sees_distinct(self) -> None:
        """Community and Wealth must not share the same ``sees`` text."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'community' or 'wealth' not yet in registry.")
        comm, wlth = pair
        assert comm.sees != wlth.sees, (
            "Community and Wealth share the same 'sees' -- "
            "they must read the world from opposite sides of the same wound."
        )

    def test_community_sees_contains_person_discriminant(self) -> None:
        """Community's ``sees`` must contain at least one person-focused discriminant word."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'community' or 'wealth' not yet in registry.")
        comm, _wlth = pair
        sees_lower = comm.sees.lower()
        found = any(word in sees_lower for word in self._COMMUNITY_DISCRIMINANTS)
        assert found, (
            f"Community 'sees' does not contain a person discriminant from "
            f"{sorted(self._COMMUNITY_DISCRIMINANTS)!r}: {comm.sees!r}"
        )

    def test_wealth_sees_contains_market_discriminant(self) -> None:
        """Wealth's ``sees`` must contain at least one market-focused discriminant word."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'community' or 'wealth' not yet in registry.")
        _comm, wlth = pair
        sees_lower = wlth.sees.lower()
        found = any(word in sees_lower for word in self._WEALTH_DISCRIMINANTS)
        assert found, (
            f"Wealth 'sees' does not contain a market discriminant from "
            f"{sorted(self._WEALTH_DISCRIMINANTS)!r}: {wlth.sees!r}"
        )


class TestTruthVengeanceCompatibility:
    """Truth and Vengeance must be compatible-until-they-are-not, not covertly identical.

    Truth reaches for comprehension (explanation, evidence, coherent account), not
    confirmation of a target. Neither truth.wants nor truth.voice may use pursuit vocabulary.
    Tests skip cleanly when either lens is absent.
    """

    _COMPREHENSION_WORDS: frozenset[str] = frozenset(
        {"understanding", "explanation", "coherent", "evidence", "source", "record"}
    )
    _PURSUIT_WORDS: frozenset[str] = frozenset({"hunt", "pursue", "target", "revenge", "punish"})

    def _get_pair(self) -> tuple | None:
        lenses = _load()
        tr = lenses.get("truth")
        vg = lenses.get("vengeance")
        if tr is None or vg is None:
            return None
        return tr, vg

    def test_truth_and_vengeance_wants_distinct(self) -> None:
        """Truth and Vengeance must not share the same ``wants`` text."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'truth' or 'vengeance' not yet in registry.")
        tr, vg = pair
        assert tr.wants != vg.wants, (
            "Truth and Vengeance share the same 'wants' -- "
            "they must diverge on method and end-state."
        )

    def test_truth_reaches_for_comprehension(self) -> None:
        """Truth's ``wants + voice`` (concatenated) must contain at least one comprehension word."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'truth' or 'vengeance' not yet in registry.")
        tr, _vg = pair
        combined = (tr.wants + " " + tr.voice).lower()
        found = any(word in combined for word in self._COMPREHENSION_WORDS)
        assert found, (
            f"Truth 'wants'+'voice' combined does not contain a comprehension word from "
            f"{sorted(self._COMPREHENSION_WORDS)!r}. "
            f"truth.wants={tr.wants!r}, truth.voice={tr.voice!r}"
        )

    def test_truth_avoids_pursuit_vocabulary(self) -> None:
        """Neither truth.wants nor truth.voice may contain pursuit vocabulary."""
        pair = self._get_pair()
        if pair is None:
            pytest.skip("'truth' or 'vengeance' not yet in registry.")
        tr, _vg = pair
        wants_lower = tr.wants.lower()
        voice_lower = tr.voice.lower()
        pursuit_in_wants = sorted(w for w in self._PURSUIT_WORDS if w in wants_lower)
        pursuit_in_voice = sorted(w for w in self._PURSUIT_WORDS if w in voice_lower)
        assert not pursuit_in_wants, (
            f"Pursuit vocabulary {pursuit_in_wants!r} found in truth.wants: {tr.wants!r}"
        )
        assert not pursuit_in_voice, (
            f"Pursuit vocabulary {pursuit_in_voice!r} found in truth.voice: {tr.voice!r}"
        )
