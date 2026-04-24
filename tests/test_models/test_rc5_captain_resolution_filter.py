"""RC-5: resolved-captain encounter filter tests.

Once a captain reaches a terminal status (defeated/truce/bribed_off/
wanderer), encounters attached to them drop out of the random pool so
the player's choices stick. Scripted encounters bypass the filter.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.captain_memory import (
    OUTCOME_FLED,
    OUTCOME_NEGOTIATED,
    OUTCOME_VICTORY,
    STATUS_ACTIVE,
    STATUS_DEFEATED,
    STATUS_TRUCE,
    CaptainMemory,
)
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterContext,
    EncounterDefinition,
    EncounterOutcome,
    _is_eligible,
    lookup_encounter_definition,
    select_encounter_definition,
)


def _make_defn(
    id: str,
    encounter_type: str = "ransom_demand",
    captain_id: str = "",
    weight: int = 10,
) -> EncounterDefinition:
    return EncounterDefinition(
        id=id,
        encounter_type=encounter_type,
        name=f"Test {id}",
        description="d",
        choices=[
            EncounterChoice(
                id="x",
                label="x",
                description="",
                outcome=EncounterOutcome(description="d", rewards=[]),
            )
        ],
        weight=weight,
        captain_id=captain_id,
    )


# ---------------------------------------------------------------------------
# _is_eligible filter
# ---------------------------------------------------------------------------


class TestIsEligibleCaptainFilter:
    def test_resolved_captain_filters_out_encounter(self) -> None:
        defn = _make_defn("e1", captain_id="vela_wolfs_ear")
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="moderate",
            seed=1,
            resolved_captain_ids={"vela_wolfs_ear"},
        )
        assert _is_eligible(defn, ctx) is False

    def test_active_captain_passes_filter(self) -> None:
        defn = _make_defn("e1", captain_id="vela_wolfs_ear")
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="moderate",
            seed=1,
            resolved_captain_ids=set(),  # nothing resolved
        )
        assert _is_eligible(defn, ctx) is True

    def test_no_captain_encounter_unaffected(self) -> None:
        """Encounters without captain_id are never filtered by RC-5."""
        defn = _make_defn("e1", captain_id="")
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="moderate",
            seed=1,
            resolved_captain_ids={"vela_wolfs_ear", "calder_cold_read"},
        )
        assert _is_eligible(defn, ctx) is True

    def test_other_captain_resolved_does_not_affect_this(self) -> None:
        defn = _make_defn("e1", captain_id="ngozi_pale_reckoning")
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="moderate",
            seed=1,
            resolved_captain_ids={"vela_wolfs_ear"},  # different captain
        )
        assert _is_eligible(defn, ctx) is True


# ---------------------------------------------------------------------------
# select_encounter_definition with resolved captains
# ---------------------------------------------------------------------------


class TestSelectionWithResolvedCaptains:
    def test_resolved_captain_never_selected(self) -> None:
        defs = [
            _make_defn("vela_enc", captain_id="vela_wolfs_ear", weight=100),
            _make_defn("calder_enc", captain_id="calder_cold_read", weight=100),
        ]
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="moderate",
            seed=1,
            resolved_captain_ids={"vela_wolfs_ear"},
        )
        # Sample many seeds — vela should never be picked
        for seed in range(1, 100):
            ctx.seed = seed
            picked = select_encounter_definition(defs, ctx)
            assert picked is not None
            assert picked.id == "calder_enc"

    def test_all_resolved_returns_none(self) -> None:
        """If every candidate's captain is resolved, no encounter selects."""
        defs = [
            _make_defn("vela_enc", captain_id="vela_wolfs_ear"),
            _make_defn("calder_enc", captain_id="calder_cold_read"),
        ]
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="moderate",
            seed=1,
            resolved_captain_ids={"vela_wolfs_ear", "calder_cold_read"},
        )
        assert select_encounter_definition(defs, ctx) is None


# ---------------------------------------------------------------------------
# Scripted encounters bypass filter
# ---------------------------------------------------------------------------


class TestScriptedBypass:
    def test_direct_lookup_works_for_resolved_captain(self) -> None:
        """Scripted re-encounters via lookup_encounter_definition don't go
        through _is_eligible — they always resolve. This lets future TW or
        story content force re-encounters with resolved captains."""
        defs = [_make_defn("vela_enc", captain_id="vela_wolfs_ear")]
        # Simulating a scripted re-encounter — lookup ignores filter
        result = lookup_encounter_definition(defs, "vela_enc")
        assert result is not None
        assert result.id == "vela_enc"


# ---------------------------------------------------------------------------
# End-to-end with real data + CaptainMemory
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


class TestEndToEndWithRealData:
    def test_defeated_captain_filters_real_encounter(self, dl) -> None:
        """vela_wolfs_ear is attached to ransom_pirate_corvette_01.
        After resolution, the encounter drops from random selection."""
        # First, sanity check vela's encounter exists in the pool
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="dangerous",
            seed=42,
            player_level=5,  # past min_level gates
        )
        # Without resolution, the encounter is selectable
        seen_unrestricted = set()
        for seed in range(1, 200):
            ctx.seed = seed
            picked = select_encounter_definition(dl.encounter_definitions, ctx)
            if picked:
                seen_unrestricted.add(picked.id)
        assert "ransom_pirate_corvette_01" in seen_unrestricted, (
            "Sanity: vela's encounter should be reachable without resolution"
        )

        # With vela resolved, it should never appear
        ctx.resolved_captain_ids = {"vela_wolfs_ear"}
        seen_after_resolution = set()
        for seed in range(1, 200):
            ctx.seed = seed
            picked = select_encounter_definition(dl.encounter_definitions, ctx)
            if picked:
                seen_after_resolution.add(picked.id)
        assert "ransom_pirate_corvette_01" not in seen_after_resolution, (
            "vela's encounter should be filtered out after resolution"
        )

    def test_captain_memory_drives_resolution_set(self) -> None:
        """The set passed to EncounterContext is built from
        player.captain_memory by checking is_resolved."""
        memories = {
            "vela_wolfs_ear": CaptainMemory(
                captain_id="vela_wolfs_ear",
                encounter_count=1,
                status=STATUS_DEFEATED,
                last_outcome=OUTCOME_VICTORY,
            ),
            "calder_cold_read": CaptainMemory(
                captain_id="calder_cold_read",
                encounter_count=1,
                status=STATUS_TRUCE,
                last_outcome=OUTCOME_NEGOTIATED,
            ),
            "ngozi_pale_reckoning": CaptainMemory(
                captain_id="ngozi_pale_reckoning",
                encounter_count=1,
                status=STATUS_ACTIVE,  # met but not resolved
                last_outcome=OUTCOME_FLED,
            ),
        }
        resolved = {cid for cid, m in memories.items() if m.is_resolved}
        # Vela (defeated) and Calder (truce) are resolved; Ngozi (fled) is not
        assert resolved == {"vela_wolfs_ear", "calder_cold_read"}


class TestMultipleResolutionPathsAllFilter:
    """All four resolution statuses (defeated/truce/bribed_off/wanderer)
    cause encounter filtering, not just defeat."""

    @pytest.mark.parametrize(
        "status",
        [
            "defeated",
            "truce",
            "bribed_off",
            "wanderer",
        ],
    )
    def test_each_resolved_status_filters(self, status) -> None:
        # Build a memory in each resolved status
        memory = CaptainMemory(
            captain_id="vela_wolfs_ear",
            encounter_count=1,
            status=status,
        )
        assert memory.is_resolved
        # Filter excludes the encounter
        defn = _make_defn("e1", captain_id="vela_wolfs_ear")
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="moderate",
            seed=1,
            resolved_captain_ids={"vela_wolfs_ear"},
        )
        assert _is_eligible(defn, ctx) is False
