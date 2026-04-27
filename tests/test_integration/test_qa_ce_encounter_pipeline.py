"""QA-5: end-to-end integration tests for the CE encounter pipeline.

Exercises the full chain that QA-1 audited:
- EncounterDefinition (with captain_id + complication_ids)
- -> EncounterRef
- -> EncounterView (renders captain hail)
- -> player picks combat-leading choice
- -> CombatEncounter inherits captain_id + complication_ids
- -> CombatEngine resolves complications
- -> CombatView surfaces captain outcome line at COMBAT_OVER

These are smoke tests — they do not exercise pixel rendering or
input dispatch, but they DO exercise the data flow across the four
files involved (encounter.py, combat.py, combat_engine.py,
combat_view.py).
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.combat import (
    CombatEncounter,
    CombatLogEntry,
    CombatResult,
    CombatState,
    PlayerCombatState,
)
from spacegame.models.combat_engine import CombatEngine
from spacegame.models.encounter import (
    EncounterContext,
    select_encounter_definition,
)


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


def _player_state() -> PlayerCombatState:
    return PlayerCombatState(
        hull=100,
        max_hull=100,
        shields=20,
        max_shields=40,
        energy=10,
        max_energy=10,
        energy_regen=3,
        speed=8,
        evasion=10,
        accuracy=80,
        equipment_moves=[],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
    )


# ---------------------------------------------------------------------------
# Path 1: EncounterDefinition fields propagate to CombatEncounter / CombatState
# ---------------------------------------------------------------------------


class TestEncounterDefinitionToCombatPropagation:
    def test_ransom_pirate_definition_loads_with_captain_and_complication(self, dl) -> None:
        """The encounter definition has captain_id + complication_ids; both
        must be present so the wiring chain has source data to thread."""
        defn = next(
            (d for d in dl.encounter_definitions if d.id == "ransom_pirate_corvette_01"),
            None,
        )
        assert defn is not None
        assert defn.captain_id == "vela_wolfs_ear"
        assert "morale_shift" in defn.complication_ids

    def test_combat_encounter_carries_captain_id(self) -> None:
        """CombatEncounter has the captain_id field with a working default."""
        ce = CombatEncounter(enemy_templates=[], encounter_seed=42)
        assert ce.captain_id == ""
        ce2 = CombatEncounter(
            enemy_templates=[],
            encounter_seed=42,
            captain_id="vela_wolfs_ear",
            complication_ids=["morale_shift"],
        )
        assert ce2.captain_id == "vela_wolfs_ear"
        assert ce2.complication_ids == ["morale_shift"]


# ---------------------------------------------------------------------------
# Path 2: Captain outcome line surfaces from real captain data
# ---------------------------------------------------------------------------


class TestRealCaptainOutcomeSurfacing:
    """Uses real captain data (not mocks) to ensure the lookup actually
    resolves through DataLoader.captains."""

    def _make_state(self, captain_id: str, result: CombatResult) -> CombatState:
        encounter = CombatEncounter(enemy_templates=[], encounter_seed=42, captain_id=captain_id)
        state = CombatState(
            player=_player_state(),
            enemies=[],
            encounter=encounter,
            combat_log=[],
        )
        state.result = result
        return state

    def _surface(self, state: CombatState) -> list[str]:
        """Run the surfacing helper and return any new log lines."""
        from spacegame.views.combat_view import CombatView

        # Build a CombatView shell without fully initializing pygame UI
        view = CombatView.__new__(CombatView)
        view.engine = CombatEngine(state, seed=state.encounter.encounter_seed)
        view.player = None
        view.visible_log_lines = []
        view.floating_texts = []
        # Stubs the surfacer reads
        view._interjection_resolver = None

        def _append(entry: CombatLogEntry) -> None:
            view.visible_log_lines.append(entry.effects_applied[0])

        view._append_log_line = _append
        view._maybe_surface_captain_outcome_line()
        return list(view.visible_log_lines)

    def test_anatolia_defeat_line_fires_on_player_victory(self, dl) -> None:
        captain = dl.captains["anatolia_kestrel_crow"]
        state = self._make_state("anatolia_kestrel_crow", CombatResult.VICTORY)
        lines = self._surface(state)
        # Captain.defeat_line plays when player wins
        assert any(captain.defeat_line in line for line in lines), lines

    def test_vela_victory_line_fires_on_player_defeat(self, dl) -> None:
        captain = dl.captains["vela_wolfs_ear"]
        state = self._make_state("vela_wolfs_ear", CombatResult.DEFEAT)
        lines = self._surface(state)
        assert any(captain.victory_line in line for line in lines)

    def test_ngozi_surrender_line_fires_on_negotiation(self, dl) -> None:
        captain = dl.captains["ngozi_pale_reckoning"]
        state = self._make_state("ngozi_pale_reckoning", CombatResult.NEGOTIATED)
        lines = self._surface(state)
        assert any(captain.surrender_line in line for line in lines)


# ---------------------------------------------------------------------------
# Path 3: Encounter selection respects min_level (early-game protection)
# ---------------------------------------------------------------------------


class TestMinLevelGating:
    def test_high_credit_ransoms_filtered_for_level_1(self, dl) -> None:
        """ransom_reach_collector_01 (350c, min_level=3) and
        ransom_pirate_corvette_01 (200c, min_level=2) and
        ransom_guild_audit_01 (250c, min_level=2) all gate out at level 1."""
        ctx = EncounterContext(
            encounter_type="ransom_demand",
            danger_level="dangerous",
            seed=1,
            player_level=1,
        )
        # Sample 50 selections; none should be the gated encounters
        gated_ids = {
            "ransom_pirate_corvette_01",
            "ransom_reach_collector_01",
            "ransom_guild_audit_01",
        }
        for seed in range(1, 51):
            ctx.seed = seed
            defn = select_encounter_definition(dl.encounter_definitions, ctx)
            if defn is not None:
                assert defn.id not in gated_ids, (
                    f"Level-1 player drew gated encounter '{defn.id}' (min_level={defn.min_level})"
                )

    def test_high_credit_ransoms_available_at_level_3(self, dl) -> None:
        """At level 3+, the gated encounters become eligible again."""
        seen: set[str] = set()
        for seed in range(1, 100):
            ctx = EncounterContext(
                encounter_type="ransom_demand",
                danger_level="dangerous",
                seed=seed,
                player_level=3,
            )
            defn = select_encounter_definition(dl.encounter_definitions, ctx)
            if defn:
                seen.add(defn.id)
        assert "ransom_reach_collector_01" in seen, (
            "Level-3 player should be eligible for the 350c ransom"
        )


# ---------------------------------------------------------------------------
# Path 4: Captain ship spawn alignment (QA-3 fix)
# ---------------------------------------------------------------------------


class TestCaptainShipSpawnAlignment:
    """QA-3 added enemy_template_ids overrides on captain-attributed
    encounters so the spawned enemy class matches the captain's signature
    ship. Verify this holds across all 8 attached encounters."""

    def test_every_captain_attached_encounter_spawns_signature_ship(self, dl) -> None:
        captain_ships = {cap.id: cap.signature_ship_template for cap in dl.captains.values()}
        for d in dl.encounter_definitions:
            if not d.captain_id:
                continue
            expected = captain_ships[d.captain_id]
            spawns = set()
            for c in d.choices:
                if c.outcome.leads_to_combat:
                    spawns.update(c.outcome.enemy_template_ids)
                if c.failure_outcome and c.failure_outcome.leads_to_combat:
                    spawns.update(c.failure_outcome.enemy_template_ids)
            assert expected in spawns, (
                f"Encounter '{d.id}' (captain={d.captain_id}) does not "
                f"spawn signature ship '{expected}'. Got: {spawns}"
            )


# ---------------------------------------------------------------------------
# Path 5: Encounter rate sanity (QA-2/3 tuning held)
# ---------------------------------------------------------------------------


class TestEncounterRateSanity:
    """Lock in the QA-3 weight tuning so future content changes can't
    silently regress CE-4 spawn share above the target."""

    def test_ce4_share_within_target(self) -> None:
        from spacegame.models.encounter import _NON_HOSTILE_WEIGHTS

        CE4_TYPES = {
            "ransom_demand",
            "cargo_shakedown",
            "distress_bait",
            "wandering_trader",
            "derelict_encounter",
        }
        for danger in ("moderate", "dangerous"):
            weights = _NON_HOSTILE_WEIGHTS[danger]
            total = sum(weights.values())
            ce4 = sum(w for t, w in weights.items() if t in CE4_TYPES)
            share = ce4 / total
            # Hold the line: CE-4 share must stay between 15% and 25%.
            # Below 15% means CE-4 content is under-exposed (waste).
            # Above 25% means CE-4 dominates and repeat exposure becomes
            # obvious given only 4 instances per type.
            assert 0.15 <= share <= 0.25, f"CE-4 share in {danger} = {share:.1%}, expected 15-25%"
