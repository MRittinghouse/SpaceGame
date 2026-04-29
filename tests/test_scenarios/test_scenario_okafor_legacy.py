"""SA-R2 scenario: Kweon legacy-arc walk across four scenario paths.

Each scenario exercises the full arc-beat routing, flag propagation, and
save/load fidelity for the ethics-in-research narrative introduced in SA-R2.
Rendering and engine are bypassed; all logic is real model code.

Scenarios:
  (a) Full heal path — 1 heal → first-heal beat → 2 more → heal-pattern +
      mission offered → 3 more → heal-ending + arc terminal.
  (b) Full profit path — same shape, ending = profit, no mission offered.
  (c) Mixed 3+3 — first-heal + first-profit + heal-pattern + profit-pattern
      all fire; no ending fires; pending_legacy_beat returns None thereafter.
  (d) Save/load mid-arc — interrupt after 4 heal completions, round-trip
      through SaveManager, assert counter and next pending beat survive.
"""

from __future__ import annotations

from spacegame.constants.flags import (
    okafor_legacy_mission_completed,
    okafor_legacy_first_heal_seen,
    okafor_legacy_first_profit_seen,
    okafor_legacy_heal_ending_seen,
    okafor_legacy_heal_pattern_seen,
    okafor_legacy_mission_offered,
    okafor_legacy_profit_ending_seen,
    okafor_legacy_profit_pattern_seen,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.mission import MissionManager
from spacegame.models.okafor_research import (
    OKAFOR_PROJECT_ETHICS,
    OkaforResearchState,
    pending_legacy_beat,
)
from spacegame.models.player import Player
from tests.test_scenarios._helpers import fresh_player, round_trip_save

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_HEAL_TEMPLATES = [t for t, tag in OKAFOR_PROJECT_ETHICS.items() if tag == "heal"]
_PROFIT_TEMPLATES = [t for t, tag in OKAFOR_PROJECT_ETHICS.items() if tag == "profit"]


def _player_at_axiom() -> Player:
    p = fresh_player(name="ScenarioPilot", credits=200_000, system_id="axiom_labs")
    p.okafor_research_state = OkaforResearchState()
    return p


def _apply_ethics(state: OkaforResearchState, template_id: str) -> None:
    """Increment the ethics counter the way game._tick_okafor_projects does."""
    tag = OKAFOR_PROJECT_ETHICS.get(template_id, "neutral")
    if tag == "heal":
        state.legacy_heal_completed += 1
    elif tag == "profit":
        state.legacy_profit_completed += 1


def _complete_n_heal(state: OkaforResearchState, n: int) -> None:
    """Apply n heal completions using the first heal-tagged template."""
    tmpl = _HEAL_TEMPLATES[0]
    for _ in range(n):
        _apply_ethics(state, tmpl)


def _complete_n_profit(state: OkaforResearchState, n: int) -> None:
    """Apply n profit completions using the first profit-tagged template."""
    tmpl = _PROFIT_TEMPLATES[0]
    for _ in range(n):
        _apply_ethics(state, tmpl)


_BEAT_FLAG: dict[str, str] = {
    "kweon_legacy_first_heal": okafor_legacy_first_heal_seen(),
    "kweon_legacy_first_profit": okafor_legacy_first_profit_seen(),
    "kweon_legacy_heal_pattern": okafor_legacy_heal_pattern_seen(),
    "kweon_legacy_profit_pattern": okafor_legacy_profit_pattern_seen(),
    "kweon_legacy_heal_ending": okafor_legacy_heal_ending_seen(),
    "kweon_legacy_profit_ending": okafor_legacy_profit_ending_seen(),
}

_BEAT_ENDING: dict[str, str] = {
    "kweon_legacy_heal_ending": "heal",
    "kweon_legacy_profit_ending": "profit",
}


def _see_beat(player: Player, beat_id: str) -> None:
    """Simulate the close-handler in OkaforView: set seen-flag + ending."""
    flag = _BEAT_FLAG.get(beat_id, "")
    if flag:
        player.dialogue_flags[flag] = True
    ending = _BEAT_ENDING.get(beat_id, "")
    if ending and player.okafor_research_state is not None:
        player.okafor_research_state.legacy_ending = ending
    # heal-pattern also sets mission_offered (mirroring the dialogue node's set_flag)
    if beat_id == "kweon_legacy_heal_pattern":
        player.dialogue_flags[okafor_legacy_mission_offered()] = True


# ---------------------------------------------------------------------------
# Scenario (a): Full heal path
# ---------------------------------------------------------------------------


class TestHealArc:
    """Walk the complete heal-side arc: first-heal → heal-pattern → heal-ending."""

    def test_full_heal_arc(self) -> None:
        player = _player_at_axiom()
        state = player.okafor_research_state
        assert state is not None
        flags = player.dialogue_flags

        # ── 1 heal completion ──────────────────────────────────────────────
        _complete_n_heal(state, 1)
        assert state.legacy_heal_completed == 1

        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_first_heal", f"expected first-heal beat, got {beat!r}"

        _see_beat(player, "kweon_legacy_first_heal")
        assert flags.get(okafor_legacy_first_heal_seen()), "first-heal flag not set"
        # Pattern not yet due
        assert pending_legacy_beat(state, flags) is None

        # ── 2 more heal completions → total 3 ─────────────────────────────
        _complete_n_heal(state, 2)
        assert state.legacy_heal_completed == 3

        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_heal_pattern", f"expected heal-pattern, got {beat!r}"

        _see_beat(player, "kweon_legacy_heal_pattern")
        assert flags.get(okafor_legacy_heal_pattern_seen()), "heal-pattern flag not set"
        assert flags.get(okafor_legacy_mission_offered()), (
            "mission should be offered at heal-pattern"
        )
        assert pending_legacy_beat(state, flags) is None

        # ── 3 more heal completions → total 6, profit = 0 (spread = 6) ───
        _complete_n_heal(state, 3)
        assert state.legacy_heal_completed == 6
        assert state.legacy_profit_completed == 0

        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_heal_ending", f"expected heal-ending, got {beat!r}"

        _see_beat(player, "kweon_legacy_heal_ending")
        assert flags.get(okafor_legacy_heal_ending_seen()), "heal-ending flag not set"
        assert state.legacy_ending == "heal"

        # Arc is terminal: no further beats
        assert pending_legacy_beat(state, flags) is None, "arc should be terminal after ending"

    def test_heal_arc_ending_requires_spread_of_5(self) -> None:
        """Ending should not fire if profit side kept pace."""
        player = _player_at_axiom()
        state = player.okafor_research_state
        assert state is not None
        flags = player.dialogue_flags

        # Seen all beats up to but not including ending
        flags[okafor_legacy_first_heal_seen()] = True
        flags[okafor_legacy_first_profit_seen()] = True
        flags[okafor_legacy_heal_pattern_seen()] = True
        flags[okafor_legacy_profit_pattern_seen()] = True

        # 6 heal but only spread of 3 — ending should not fire
        state.legacy_heal_completed = 6
        state.legacy_profit_completed = 3

        assert pending_legacy_beat(state, flags) is None


# ---------------------------------------------------------------------------
# Scenario (b): Full profit path
# ---------------------------------------------------------------------------


class TestProfitArc:
    """Walk the complete profit-side arc: first-profit → profit-pattern → profit-ending."""

    def test_full_profit_arc(self) -> None:
        player = _player_at_axiom()
        state = player.okafor_research_state
        assert state is not None
        flags = player.dialogue_flags

        # ── 1 profit completion ────────────────────────────────────────────
        _complete_n_profit(state, 1)
        assert state.legacy_profit_completed == 1

        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_first_profit", f"expected first-profit beat, got {beat!r}"

        _see_beat(player, "kweon_legacy_first_profit")
        assert flags.get(okafor_legacy_first_profit_seen())
        assert pending_legacy_beat(state, flags) is None

        # ── 2 more profit completions → total 3 ───────────────────────────
        _complete_n_profit(state, 2)
        assert state.legacy_profit_completed == 3

        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_profit_pattern", f"expected profit-pattern, got {beat!r}"

        _see_beat(player, "kweon_legacy_profit_pattern")
        assert flags.get(okafor_legacy_profit_pattern_seen())
        # Profit path does NOT set mission_offered
        assert not flags.get(okafor_legacy_mission_offered()), "mission not offered on profit arc"
        assert pending_legacy_beat(state, flags) is None

        # ── 3 more profit completions → total 6, heal = 0 (spread = 6) ───
        _complete_n_profit(state, 3)
        assert state.legacy_profit_completed == 6
        assert state.legacy_heal_completed == 0

        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_profit_ending", f"expected profit-ending, got {beat!r}"

        _see_beat(player, "kweon_legacy_profit_ending")
        assert flags.get(okafor_legacy_profit_ending_seen())
        assert state.legacy_ending == "profit"
        assert pending_legacy_beat(state, flags) is None


# ---------------------------------------------------------------------------
# Scenario (c): Mixed 3+3 — no ending, both arcs advance in parallel
# ---------------------------------------------------------------------------


class TestMixedArc:
    """Alternating heal/profit completions — both firsts + patterns fire, no ending."""

    def test_mixed_arc_no_ending(self) -> None:
        player = _player_at_axiom()
        state = player.okafor_research_state
        assert state is not None
        flags = player.dialogue_flags

        # Complete heal 1 → first-heal
        _complete_n_heal(state, 1)
        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_first_heal"
        _see_beat(player, "kweon_legacy_first_heal")

        # Complete profit 1 → first-profit
        _complete_n_profit(state, 1)
        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_first_profit"
        _see_beat(player, "kweon_legacy_first_profit")

        # Complete heal 2 more → heal total 3, trigger heal-pattern
        _complete_n_heal(state, 2)
        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_heal_pattern"
        _see_beat(player, "kweon_legacy_heal_pattern")

        # Complete profit 2 more → profit total 3, trigger profit-pattern
        _complete_n_profit(state, 2)
        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_profit_pattern"
        _see_beat(player, "kweon_legacy_profit_pattern")

        # Final state: heal=3, profit=3, spread=0 → no ending fires
        assert state.legacy_heal_completed == 3
        assert state.legacy_profit_completed == 3
        assert pending_legacy_beat(state, flags) is None, "no ending expected at equal counts"
        assert state.legacy_ending == "", "ending should not be set in mixed arc"

    def test_mixed_arc_both_flags_set(self) -> None:
        """After mixed 3+3, all four non-ending seen-flags should be set."""
        player = _player_at_axiom()
        state = player.okafor_research_state
        assert state is not None
        flags = player.dialogue_flags

        _complete_n_heal(state, 1)
        _see_beat(player, pending_legacy_beat(state, flags))  # type: ignore[arg-type]
        _complete_n_profit(state, 1)
        _see_beat(player, pending_legacy_beat(state, flags))  # type: ignore[arg-type]
        _complete_n_heal(state, 2)
        _see_beat(player, pending_legacy_beat(state, flags))  # type: ignore[arg-type]
        _complete_n_profit(state, 2)
        _see_beat(player, pending_legacy_beat(state, flags))  # type: ignore[arg-type]

        assert flags.get(okafor_legacy_first_heal_seen()), "first-heal seen"
        assert flags.get(okafor_legacy_first_profit_seen()), "first-profit seen"
        assert flags.get(okafor_legacy_heal_pattern_seen()), "heal-pattern seen"
        assert flags.get(okafor_legacy_profit_pattern_seen()), "profit-pattern seen"
        assert not flags.get(okafor_legacy_heal_ending_seen()), "heal-ending NOT seen"
        assert not flags.get(okafor_legacy_profit_ending_seen()), "profit-ending NOT seen"


# ---------------------------------------------------------------------------
# Scenario (d): Save/load mid-arc
# ---------------------------------------------------------------------------


class TestMidArcSaveLoad:
    """Interrupt a heal arc mid-walk, round-trip through SaveManager, verify fidelity."""

    def test_save_load_preserves_counters_and_beat(self) -> None:
        player = _player_at_axiom()
        state = player.okafor_research_state
        assert state is not None
        flags = player.dialogue_flags

        # Advance: 1 heal → see first-heal → 3 more heals → see heal-pattern
        # = 4 total heals, heal-pattern seen, mid-arc position
        _complete_n_heal(state, 1)
        _see_beat(player, "kweon_legacy_first_heal")
        _complete_n_heal(state, 3)
        _see_beat(player, "kweon_legacy_heal_pattern")

        assert state.legacy_heal_completed == 4
        assert flags.get(okafor_legacy_first_heal_seen())
        assert flags.get(okafor_legacy_heal_pattern_seen())
        assert flags.get(okafor_legacy_mission_offered())
        # No ending yet (only 4 heals, need 6 with spread >= 5)
        assert pending_legacy_beat(state, flags) is None

        # Round-trip through SaveManager
        restored = round_trip_save(player)
        rs = restored.okafor_research_state
        assert rs is not None
        rflags = restored.dialogue_flags

        assert rs.legacy_heal_completed == 4, f"expected 4, got {rs.legacy_heal_completed}"
        assert rs.legacy_profit_completed == 0
        assert rs.legacy_ending == ""
        assert rflags.get(okafor_legacy_first_heal_seen()), "first-heal flag lost in round-trip"
        assert rflags.get(okafor_legacy_heal_pattern_seen()), "heal-pattern flag lost in round-trip"
        assert rflags.get(okafor_legacy_mission_offered()), (
            "mission-offered flag lost in round-trip"
        )

        # After restore: pending_legacy_beat should still return None
        # (heal-pattern seen, only 4 heals, ending needs 6 with spread 5)
        assert pending_legacy_beat(rs, rflags) is None

        # Advance 2 more heals to total 6 — ending should fire after restore
        _complete_n_heal(rs, 2)
        beat = pending_legacy_beat(rs, rflags)
        assert beat == "kweon_legacy_heal_ending", (
            f"expected heal-ending after restore+2, got {beat!r}"
        )

    def test_save_load_preserves_ending_state(self) -> None:
        """An arc that has reached its ending round-trips with legacy_ending intact."""
        player = _player_at_axiom()
        state = player.okafor_research_state
        assert state is not None
        flags = player.dialogue_flags

        # Fast-forward to ending: pre-set all seen flags + run counters
        flags[okafor_legacy_first_heal_seen()] = True
        flags[okafor_legacy_heal_pattern_seen()] = True
        flags[okafor_legacy_mission_offered()] = True
        state.legacy_heal_completed = 6
        state.legacy_profit_completed = 0

        beat = pending_legacy_beat(state, flags)
        assert beat == "kweon_legacy_heal_ending"
        _see_beat(player, "kweon_legacy_heal_ending")
        assert state.legacy_ending == "heal"

        restored = round_trip_save(player)
        rs = restored.okafor_research_state
        assert rs is not None
        rflags = restored.dialogue_flags

        assert rs.legacy_ending == "heal"
        assert rs.legacy_heal_completed == 6
        assert rflags.get(okafor_legacy_heal_ending_seen())
        assert pending_legacy_beat(rs, rflags) is None, "arc should be terminal after restore"


# ---------------------------------------------------------------------------
# SA-R3: Clinic-run mission kweon_relationship reward (AC #5)
# ---------------------------------------------------------------------------


class TestClinicRunMissionReward:
    """SA-R3 AC #5 — completing clinic run bumps kweon_relationship_value by 1."""

    def test_clinic_run_completion_bumps_kweon_relationship(self) -> None:
        dl = get_data_loader()
        dl.load_all()

        mission = dl.get_mission("okafor_legacy_clinic_run")
        assert mission is not None, "okafor_legacy_clinic_run must be loadable"
        # Confirm four rewards exist
        assert len(mission.rewards) == 4, (
            f"Expected 4 rewards (credits/xp/set_flag/kweon_relationship), "
            f"got {len(mission.rewards)}"
        )
        reward_types = [r.reward_type for r in mission.rewards]
        assert "kweon_relationship" in reward_types, (
            f"kweon_relationship reward not found in {reward_types}"
        )

        # Build a player with okafor_research_state already initialised.
        player = fresh_player(name="ClinicPilot", credits=50_000, system_id="havens_rest")
        player.okafor_research_state = OkaforResearchState(kweon_relationship_value=2)
        pre_value = player.okafor_research_state.kweon_relationship_value

        # Set the required flag so the mission is available.
        player.dialogue_flags["okafor_legacy_heal_pattern_seen"] = True

        mgr = MissionManager([mission])
        mgr.accept_mission("okafor_legacy_clinic_run")
        mgr.apply_rewards("okafor_legacy_clinic_run", player)

        post_value = player.okafor_research_state.kweon_relationship_value
        assert post_value == pre_value + 1, (
            f"kweon_relationship_value should increase by 1 on clinic run completion; "
            f"was {pre_value}, now {post_value}"
        )
        assert player.dialogue_flags.get(okafor_legacy_mission_completed()), (
            "okafor_legacy_mission_completed flag must be set by set_flag reward"
        )

    def test_clinic_run_relationship_clamped_if_already_at_max(self) -> None:
        dl = get_data_loader()
        dl.load_all()

        mission = dl.get_mission("okafor_legacy_clinic_run")
        assert mission is not None

        player = fresh_player(name="ClinicPilot", credits=50_000, system_id="havens_rest")
        player.okafor_research_state = OkaforResearchState(kweon_relationship_value=10)

        mgr = MissionManager([mission])
        mgr.accept_mission("okafor_legacy_clinic_run")
        mgr.apply_rewards("okafor_legacy_clinic_run", player)

        assert player.okafor_research_state.kweon_relationship_value == 10, (
            "kweon_relationship_value must stay clamped at 10"
        )
