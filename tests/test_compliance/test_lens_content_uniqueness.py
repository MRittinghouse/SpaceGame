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
