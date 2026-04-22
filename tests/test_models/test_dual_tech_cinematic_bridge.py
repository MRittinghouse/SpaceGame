"""Tests for the dual tech cinematic bridge (C5 Impl 2).

Covers element mapping, ultimate flag, inputs derivation from DualTech
registry, canonical ID coverage, unknown-id handling.
"""

from __future__ import annotations

from spacegame.models.dual_tech import PAIR_TECH_IDS, TRIAD_TECH_IDS
from spacegame.models.dual_tech_cinematic_bridge import (
    DUAL_TECH_ELEMENTS,
    ULTIMATE_TECH_IDS,
    DualTechCinematicInputs,
    get_cinematic_inputs,
    is_dual_tech_move,
)


class TestElementMapping:
    def test_every_registered_tech_has_elements(self) -> None:
        """All 6 pair techs + 1 triad mapped in the bridge."""
        for tech_id in PAIR_TECH_IDS + TRIAD_TECH_IDS:
            assert tech_id in DUAL_TECH_ELEMENTS, f"Missing elements for {tech_id}"

    def test_elements_are_canonical(self) -> None:
        """Every element in the mapping is a known WeaponElement."""
        canonical = {"kinetic", "plasma", "ion", "cryo", "voltaic"}
        for tech_id, (dom, sec) in DUAL_TECH_ELEMENTS.items():
            assert dom in canonical, f"{tech_id}: dominant {dom} not canonical"
            assert sec in canonical, f"{tech_id}: secondary {sec} not canonical"

    def test_crew_sync_is_the_only_ultimate(self) -> None:
        """Triad technique is the canonical ultimate per design doc."""
        assert ULTIMATE_TECH_IDS == frozenset({"crew_sync"})


class TestIsDualTechMove:
    def test_known_tech_is_dual_tech(self) -> None:
        assert is_dual_tech_move("fire_at_will")
        assert is_dual_tech_move("crew_sync")

    def test_unknown_move_is_not_dual_tech(self) -> None:
        assert not is_dual_tech_move("laser_shot")
        assert not is_dual_tech_move("")
        assert not is_dual_tech_move("not_a_real_move")


class TestGetCinematicInputs:
    def test_returns_none_for_unknown_id(self) -> None:
        assert get_cinematic_inputs("nonsense") is None

    def test_pair_tech_inputs_populated(self) -> None:
        inputs = get_cinematic_inputs("fire_at_will")
        assert inputs is not None
        assert isinstance(inputs, DualTechCinematicInputs)
        assert inputs.tech_id == "fire_at_will"
        assert inputs.tech_name == "FIRE AT WILL"  # uppercased
        assert len(inputs.crew_ids) == 2
        assert inputs.dominant_element == "plasma"
        assert inputs.secondary_element == "kinetic"
        assert not inputs.is_ultimate

    def test_ultimate_flag_set_for_crew_sync(self) -> None:
        inputs = get_cinematic_inputs("crew_sync")
        assert inputs is not None
        assert inputs.is_ultimate
        assert len(inputs.crew_ids) == 4  # Triad

    def test_tech_names_render_shouty(self) -> None:
        """Cinematic styling is all-caps. Bridge uppercases for consistency."""
        inputs = get_cinematic_inputs("focused_barrage")
        assert inputs is not None
        assert inputs.tech_name.isupper()

    def test_elements_narratively_coherent(self) -> None:
        """Spot-check a few elemental assignments match the intent
        captured in the bridge's top-of-file rationale."""
        # power_drift: reactor bleed + momentum → voltaic + ion
        pd = get_cinematic_inputs("power_drift")
        assert pd is not None
        assert pd.dominant_element == "voltaic"
        assert pd.secondary_element == "ion"

        # daring_gambit: cold precision + counter
        dg = get_cinematic_inputs("daring_gambit")
        assert dg is not None
        assert dg.dominant_element == "cryo"


class TestRegistryCoverage:
    def test_all_mapped_ids_exist_in_palette(self) -> None:
        """Every id in DUAL_TECH_ELEMENTS must resolve against the
        mechanical palette — bridge can't reference techs that don't exist."""
        from spacegame.models.dual_tech import DUAL_TECH_PALETTE

        for tech_id in DUAL_TECH_ELEMENTS:
            assert tech_id in DUAL_TECH_PALETTE, (
                f"Bridge references {tech_id} but palette has no such tech"
            )

    def test_pair_crew_counts_match(self) -> None:
        """Pair techs have 2 crew ids; triad has 4."""
        for tech_id in PAIR_TECH_IDS:
            inputs = get_cinematic_inputs(tech_id)
            assert inputs is not None
            assert len(inputs.crew_ids) == 2
        for tech_id in TRIAD_TECH_IDS:
            inputs = get_cinematic_inputs(tech_id)
            assert inputs is not None
            assert len(inputs.crew_ids) == 4
