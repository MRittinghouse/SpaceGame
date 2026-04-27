"""Tests for the dual tech cinematic timeline primitive (Combat C5 §4.3).

Validates phase boundaries, per-phase factor envelopes, element-role
resolution, impact-triggered one-shot semantics, ultimate variant,
and lifecycle (reset + negative-dt guard). No pygame dependency.
"""

from __future__ import annotations

import pytest

from spacegame.engine.dual_tech_cinematic import (
    DARKEN_PEAK_ALPHA,
    STANDARD_TOTAL,
    ULTIMATE_TOTAL,
    DualTechCinematic,
    DualTechPhase,
    resolve_emissive_role,
    resolve_trail_role,
)

# ---------------------------------------------------------------------------
# Element palette resolution
# ---------------------------------------------------------------------------


class TestElementResolution:
    @pytest.mark.parametrize(
        "element,expected",
        [
            ("kinetic", "glow_warm"),
            ("plasma", "plasma_core"),
            ("ion", "ion_arc"),
            ("cryo", "cryo_fractal"),
            ("voltaic", "voltaic_strike"),
        ],
    )
    def test_emissive_role_per_element(self, element: str, expected: str) -> None:
        assert resolve_emissive_role(element) == expected

    @pytest.mark.parametrize(
        "element,expected",
        [
            ("plasma", "plasma_hot"),
            ("ion", "glow_cool"),
            ("cryo", "glow_cool"),
            ("voltaic", "voltaic_strike"),
        ],
    )
    def test_trail_role_per_element(self, element: str, expected: str) -> None:
        assert resolve_trail_role(element) == expected

    def test_unknown_element_falls_back_to_plasma(self) -> None:
        assert resolve_emissive_role("made_up") == "plasma_core"

    def test_none_element_falls_back_to_plasma(self) -> None:
        assert resolve_emissive_role(None) == "plasma_core"

    def test_kinetic_uses_warm_glow_not_plasma(self) -> None:
        """Spec §4.3 kinetic row: 'neutral, no emissive; uses glow_warm for muzzle'."""
        assert resolve_emissive_role("kinetic") == "glow_warm"

    def test_every_resolved_role_is_canonical(self) -> None:
        from spacegame.engine.material_palette import is_valid_role

        for element in ("kinetic", "plasma", "ion", "cryo", "voltaic", None):
            assert is_valid_role(resolve_emissive_role(element))
            assert is_valid_role(resolve_trail_role(element))


# ---------------------------------------------------------------------------
# Construction + resolved roles
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_defaults_are_sensible(self) -> None:
        c = DualTechCinematic(tech_name="TEST")
        assert c.elapsed == 0.0
        assert c.is_ultimate is False
        assert c.total_duration == STANDARD_TOTAL
        assert c.phase == DualTechPhase.CAMERA_ZOOM

    def test_dominant_role_resolves(self) -> None:
        c = DualTechCinematic(tech_name="ICE SPEAR", dominant_element="cryo")
        assert c.dominant_role == "cryo_fractal"

    def test_secondary_role_resolves(self) -> None:
        c = DualTechCinematic(
            tech_name="STORM BARRAGE", dominant_element="ion", secondary_element="voltaic"
        )
        assert c.secondary_role == "voltaic_strike"

    def test_trail_role_uses_secondary_when_present(self) -> None:
        c = DualTechCinematic(tech_name="X", dominant_element="ion", secondary_element="cryo")
        assert c.trail_role == "glow_cool"  # cryo's trail role

    def test_trail_role_falls_back_to_dominant(self) -> None:
        c = DualTechCinematic(tech_name="X", dominant_element="plasma")
        assert c.trail_role == "plasma_hot"  # plasma's trail role

    def test_palette_valid_flag(self) -> None:
        c = DualTechCinematic(tech_name="X", dominant_element="plasma", secondary_element="cryo")
        assert c.is_palette_valid

    def test_ultimate_total_is_longer_than_standard(self) -> None:
        c = DualTechCinematic(tech_name="X", is_ultimate=True)
        assert c.total_duration == ULTIMATE_TOTAL
        assert ULTIMATE_TOTAL > STANDARD_TOTAL


# ---------------------------------------------------------------------------
# Phase boundaries — standard variant
# ---------------------------------------------------------------------------


class TestStandardPhases:
    def _tl(self) -> DualTechCinematic:
        return DualTechCinematic(tech_name="TEST", dominant_element="plasma")

    def test_starts_in_camera_zoom(self) -> None:
        c = self._tl()
        assert c.phase == DualTechPhase.CAMERA_ZOOM

    def test_darken_phase_begins_at_0_6(self) -> None:
        c = self._tl()
        c.update(0.6)
        assert c.phase == DualTechPhase.DARKEN_PORTRAITS

    def test_name_hold_begins_at_0_9(self) -> None:
        c = self._tl()
        c.update(0.9)
        assert c.phase == DualTechPhase.NAME_HOLD

    def test_combined_resolve_begins_at_1_5(self) -> None:
        c = self._tl()
        c.update(1.5)
        assert c.phase == DualTechPhase.COMBINED_RESOLVE

    def test_impact_begins_at_2_7(self) -> None:
        c = self._tl()
        c.update(2.7)
        assert c.phase == DualTechPhase.IMPACT

    def test_completes_at_3_2(self) -> None:
        c = self._tl()
        c.update(STANDARD_TOTAL)
        assert c.phase == DualTechPhase.COMPLETE
        assert c.is_complete

    def test_standard_never_enters_charge_phase(self) -> None:
        c = self._tl()
        # Sweep the whole timeline; CHARGE must not appear.
        for _ in range(40):
            c.update(0.1)
            assert c.phase != DualTechPhase.CHARGE


# ---------------------------------------------------------------------------
# Phase boundaries — ultimate variant
# ---------------------------------------------------------------------------


class TestUltimatePhases:
    def _tl(self) -> DualTechCinematic:
        return DualTechCinematic(tech_name="ULT", dominant_element="plasma", is_ultimate=True)

    def test_charge_replaces_combined_resolve(self) -> None:
        c = self._tl()
        c.update(1.6)  # Just past t=1.5 (name_hold end)
        assert c.phase == DualTechPhase.CHARGE

    def test_ultimate_impact_starts_at_3_0(self) -> None:
        c = self._tl()
        c.update(3.0)
        assert c.phase == DualTechPhase.IMPACT

    def test_ultimate_completes_at_4_5(self) -> None:
        c = self._tl()
        c.update(ULTIMATE_TOTAL)
        assert c.phase == DualTechPhase.COMPLETE


# ---------------------------------------------------------------------------
# Factor envelopes
# ---------------------------------------------------------------------------


class TestFactorEnvelopes:
    def _tl(self) -> DualTechCinematic:
        return DualTechCinematic(tech_name="T", dominant_element="plasma")

    def test_camera_zoom_is_zero_at_start(self) -> None:
        c = self._tl()
        assert c.camera_zoom_factor == 0.0

    def test_camera_zoom_mid_is_half(self) -> None:
        c = self._tl()
        c.update(0.3)
        assert c.camera_zoom_factor == pytest.approx(0.5, abs=0.02)

    def test_camera_zoom_fully_engaged_after_0_6(self) -> None:
        c = self._tl()
        c.update(0.7)
        assert c.camera_zoom_factor == 1.0

    def test_camera_zoom_stays_engaged(self) -> None:
        c = self._tl()
        c.update(2.0)
        assert c.camera_zoom_factor == 1.0

    def test_darken_is_zero_before_portrait_phase(self) -> None:
        c = self._tl()
        c.update(0.5)
        assert c.darken_alpha == 0

    def test_darken_peaks_during_name_hold(self) -> None:
        c = self._tl()
        c.update(1.0)  # mid-name-hold
        assert c.darken_alpha == DARKEN_PEAK_ALPHA

    def test_darken_fades_during_impact(self) -> None:
        c = self._tl()
        c.update(2.7)
        peak_alpha = c.darken_alpha
        c.update(0.4)  # late-impact — un-darken has started
        assert c.darken_alpha < peak_alpha

    def test_darken_complete_is_zero(self) -> None:
        c = self._tl()
        c.update(STANDARD_TOTAL)
        assert c.darken_alpha == 0

    def test_portrait_slide_zero_before_phase(self) -> None:
        c = self._tl()
        c.update(0.4)
        assert c.portrait_slide_factor == 0.0

    def test_portrait_slide_half_mid(self) -> None:
        c = self._tl()
        c.update(0.6 + 0.15)  # mid-slide
        assert c.portrait_slide_factor == pytest.approx(0.5, abs=0.02)

    def test_portrait_slide_full_after_phase(self) -> None:
        c = self._tl()
        c.update(1.0)
        assert c.portrait_slide_factor == 1.0

    def test_portrait_alpha_full_during_hold(self) -> None:
        c = self._tl()
        c.update(1.2)
        assert c.portrait_alpha == 255

    def test_portrait_alpha_fades_to_zero_at_complete(self) -> None:
        c = self._tl()
        c.update(STANDARD_TOTAL)
        assert c.portrait_alpha == 0

    def test_tech_name_alpha_zero_before_name_hold(self) -> None:
        c = self._tl()
        c.update(0.7)
        assert c.tech_name_alpha == 0

    def test_tech_name_alpha_full_during_hold(self) -> None:
        c = self._tl()
        c.update(1.0)
        assert c.tech_name_alpha == 255

    def test_tech_name_fades_after_hold(self) -> None:
        c = self._tl()
        c.update(1.5 + 0.1)  # just after name-hold end
        assert 0 < c.tech_name_alpha < 255

    def test_combined_resolve_progress_at_phase_bounds(self) -> None:
        c = self._tl()
        c.update(1.5)
        assert c.combined_resolve_progress == 0.0
        c.update(1.2)  # now at t=2.7 (end of resolve)
        assert c.combined_resolve_progress == 1.0

    def test_impact_shake_peaks_at_impact_start(self) -> None:
        c = self._tl()
        c.update(2.7 + 0.01)
        assert c.impact_shake_factor > 0.9

    def test_impact_shake_decays_to_zero(self) -> None:
        c = self._tl()
        c.update(STANDARD_TOTAL)
        assert c.impact_shake_factor == 0.0


# ---------------------------------------------------------------------------
# Impact one-shot semantics
# ---------------------------------------------------------------------------


class TestImpactTrigger:
    def test_impact_not_fired_before_impact_phase(self) -> None:
        c = DualTechCinematic(tech_name="T")
        c.update(2.0)  # still in COMBINED_RESOLVE
        assert c.consume_impact_trigger() is False

    def test_impact_fires_once_entering_impact_phase(self) -> None:
        c = DualTechCinematic(tech_name="T")
        c.update(2.7)  # entering IMPACT
        assert c.consume_impact_trigger() is True

    def test_impact_cannot_fire_twice(self) -> None:
        c = DualTechCinematic(tech_name="T")
        c.update(2.7)
        c.consume_impact_trigger()
        # Second call returns False — one-shot semantics.
        assert c.consume_impact_trigger() is False

    def test_reset_restores_one_shot(self) -> None:
        c = DualTechCinematic(tech_name="T")
        c.update(2.7)
        c.consume_impact_trigger()
        c.reset()
        c.update(2.7)
        assert c.consume_impact_trigger() is True

    def test_ultimate_impact_fires_at_3_0(self) -> None:
        c = DualTechCinematic(tech_name="U", is_ultimate=True)
        c.update(3.0)
        assert c.consume_impact_trigger() is True


# ---------------------------------------------------------------------------
# Charge (ultimate)
# ---------------------------------------------------------------------------


class TestCharge:
    def test_charge_intensity_zero_for_standard(self) -> None:
        c = DualTechCinematic(tech_name="T")
        c.update(2.0)
        assert c.charge_intensity == 0.0

    def test_charge_intensity_ramps_during_ultimate_charge(self) -> None:
        c = DualTechCinematic(tech_name="U", is_ultimate=True)
        c.update(1.5 + 0.75)  # halfway through charge
        assert c.charge_intensity == pytest.approx(0.5, abs=0.02)

    def test_charge_intensity_full_at_charge_end(self) -> None:
        c = DualTechCinematic(tech_name="U", is_ultimate=True)
        c.update(3.0)
        assert c.charge_intensity == 1.0


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_negative_dt_ignored(self) -> None:
        c = DualTechCinematic(tech_name="T")
        c.update(-0.5)
        assert c.elapsed == 0.0

    def test_zero_dt_is_noop(self) -> None:
        c = DualTechCinematic(tech_name="T")
        c.update(0.0)
        assert c.elapsed == 0.0

    def test_update_clamps_at_total_duration(self) -> None:
        c = DualTechCinematic(tech_name="T")
        c.update(10.0)
        assert c.elapsed == STANDARD_TOTAL
        assert c.is_complete

    def test_reset_rewinds_timeline(self) -> None:
        c = DualTechCinematic(tech_name="T")
        c.update(1.5)
        c.reset()
        assert c.elapsed == 0.0
        assert c.phase == DualTechPhase.CAMERA_ZOOM

    def test_many_small_updates_equal_one_large(self) -> None:
        a = DualTechCinematic(tech_name="A")
        b = DualTechCinematic(tech_name="B")
        for _ in range(10):
            a.update(0.1)
        b.update(1.0)
        assert a.elapsed == pytest.approx(b.elapsed)


# ---------------------------------------------------------------------------
# Canonical tech examples (spec §4.3)
# ---------------------------------------------------------------------------


class TestCanonicalTechs:
    def test_ion_cryo_dual_tech_roles(self) -> None:
        """Spec example: 'ion-cryo dual tech starts with violet trail,
        arcs into cyan crystallization'."""
        c = DualTechCinematic(
            tech_name="FROST LANCE",
            dominant_element="ion",
            secondary_element="cryo",
        )
        assert c.dominant_role == "ion_arc"  # violet
        assert c.secondary_role == "cryo_fractal"  # cyan

    def test_plasma_voltaic_dual_tech_roles(self) -> None:
        c = DualTechCinematic(
            tech_name="STORM BURST",
            dominant_element="plasma",
            secondary_element="voltaic",
        )
        assert c.dominant_role == "plasma_core"
        assert c.secondary_role == "voltaic_strike"

    def test_single_element_ultimate(self) -> None:
        """Single-element ultimate: dominant == secondary."""
        c = DualTechCinematic(
            tech_name="INFERNO",
            dominant_element="plasma",
            secondary_element="plasma",
            is_ultimate=True,
        )
        assert c.dominant_role == c.secondary_role == "plasma_core"
        assert c.is_ultimate
