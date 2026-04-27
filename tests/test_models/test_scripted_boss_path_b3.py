"""
Scripted-boss trigger path verification for Phase B3.

T4 bosses (pirate_lord, reach_dreadnought, union_behemoth) are intentionally
excluded from random encounter pools by ``filter_enemies_for_system``.
They must be reachable through narrative encounter choices that set
``leads_to_combat=true`` and name the boss in ``enemy_template_ids``.

The infrastructure already exists (legacy bosses corsair_king and
void_leviathan use it). These tests verify the new B2 T4 bosses work
with the same infrastructure — instantiation, boss HP multiplier,
phase data integrity — so a future narrative encounter referencing
them will Just Work.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.combat import EnemyShip
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterOutcome,
)

T4_BOSS_IDS = ["pirate_lord", "reach_dreadnought", "union_behemoth"]


@pytest.fixture(scope="module")
def enemies() -> dict:
    dl = get_data_loader()
    return dl.load_enemy_templates()


# ============================================================================
# Boss instantiation
# ============================================================================


class TestBossInstantiation:
    """Each T4 boss template must instantiate cleanly into a runtime
    EnemyShip with full HP and correct phase state."""

    @pytest.mark.parametrize("boss_id", T4_BOSS_IDS)
    def test_boss_from_template_initializes(self, enemies: dict, boss_id: str) -> None:
        template = enemies[boss_id]
        assert template.is_boss, f"{boss_id} must be is_boss=True"

        ship = EnemyShip.from_template(template)
        expected_hull = template.hull * (template.boss_hp_multiplier or 1)
        expected_shields = template.shields * (template.boss_hp_multiplier or 1)
        assert ship.current_hull == expected_hull
        assert ship.current_shields == expected_shields
        assert ship.is_alive
        assert not ship.is_fled
        assert ship.current_phase_idx == 0

    @pytest.mark.parametrize("boss_id", T4_BOSS_IDS)
    def test_boss_has_well_formed_phases(self, enemies: dict, boss_id: str) -> None:
        template = enemies[boss_id]
        assert len(template.phases) >= 2, f"{boss_id} needs at least 2 phases"
        # Phase 1: always-active opening.
        assert template.phases[0].hp_threshold == 1.0
        # Phase 2: half-HP transition.
        assert template.phases[1].hp_threshold == 0.5
        # Transition phase must have non-empty flavor text.
        assert template.phases[1].on_enter_text, (
            f"{boss_id} phase-2 transition should have on_enter_text for narrative punch"
        )

    @pytest.mark.parametrize("boss_id", T4_BOSS_IDS)
    def test_boss_phase_move_ids_all_resolve(self, enemies: dict, boss_id: str) -> None:
        """Every move_id referenced by a phase must resolve to a real move in
        the boss's moveset. Prevents silent fallthrough bugs."""
        template = enemies[boss_id]
        move_ids = {m.id for m in template.moves}
        for phase in template.phases:
            for mid in phase.move_ids:
                assert mid in move_ids, (
                    f"{boss_id} phase '{phase.name}' references unknown move '{mid}'"
                )


# ============================================================================
# Scripted encounter outcome wiring
# ============================================================================


class TestScriptedOutcomePath:
    """An EncounterOutcome with leads_to_combat + boss ID is the canonical
    scripted-boss trigger. These tests demonstrate the pattern works for
    each new T4 boss."""

    @pytest.mark.parametrize("boss_id", T4_BOSS_IDS)
    def test_outcome_carries_boss_id(self, boss_id: str) -> None:
        """An EncounterOutcome can reference a T4 boss by ID — the
        infrastructure does not restrict which template IDs are valid here."""
        outcome = EncounterOutcome(
            description=f"You engage the {boss_id}.",
            rewards=[],
            leads_to_combat=True,
            enemy_template_ids=[boss_id],
        )
        assert outcome.leads_to_combat
        assert outcome.enemy_template_ids == [boss_id]

    @pytest.mark.parametrize("boss_id", T4_BOSS_IDS)
    def test_outcome_boss_id_resolves_to_template(self, enemies: dict, boss_id: str) -> None:
        """The canonical 'leads_to_combat + enemy_template_ids' pattern: the
        ID must resolve to a real template in the data loader so the
        encounter view can instantiate combat from it."""
        outcome = EncounterOutcome(
            description="",
            rewards=[],
            leads_to_combat=True,
            enemy_template_ids=[boss_id],
        )
        for eid in outcome.enemy_template_ids:
            assert eid in enemies, f"Scripted-outcome boss {eid} not in loaded templates"
            template = enemies[eid]
            # Must be a boss-class template — scripted path is reserved for them.
            assert template.is_boss, (
                f"Scripted-outcome boss {eid} isn't flagged is_boss — "
                f"either the template is wrong or this outcome should route "
                f"through random encounters instead"
            )

    def test_choice_wraps_outcome_with_boss_id(self) -> None:
        """End-to-end: a choice in a narrative encounter wraps an outcome
        that spawns a boss. This is the exact pattern used by legacy
        encounters (see data/encounters/generic.json 'corsair_king' spawn)."""
        choice = EncounterChoice(
            id="fight",
            label="Stand and Fight",
            description="You will not flee.",
            outcome=EncounterOutcome(
                description="The dreadnought's spinal cannon pivots toward you.",
                rewards=[],
                leads_to_combat=True,
                enemy_template_ids=["reach_dreadnought"],
            ),
        )
        assert choice.outcome.leads_to_combat
        assert choice.outcome.enemy_template_ids == ["reach_dreadnought"]


# ============================================================================
# Documentation-style sanity: parity with legacy bosses
# ============================================================================


class TestParityWithLegacyBosses:
    """The legacy roster already has bosses triggered by narrative encounters
    (corsair_king, void_leviathan). New T4 bosses must support the same
    contract so they drop-in to future campaign work."""

    def test_new_bosses_match_legacy_boss_shape(self, enemies: dict) -> None:
        legacy_boss = enemies.get("corsair_king")
        assert legacy_boss is not None and legacy_boss.is_boss

        for boss_id in T4_BOSS_IDS:
            new_boss = enemies[boss_id]
            # Same structural flags
            assert new_boss.is_boss == legacy_boss.is_boss
            assert hasattr(new_boss, "phases")
            assert hasattr(new_boss, "boss_hp_multiplier")
            assert hasattr(new_boss, "max_suppressed_stacks")
