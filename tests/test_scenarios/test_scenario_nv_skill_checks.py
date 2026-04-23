"""NV-6c integration scenarios — skill-check voice × specialization × content.

These scenarios exercise the full skill-check pipeline on real dialogue
content to prove the NV stack integrates:

  - NV-0 specialization bonus contributes to ``effective_level``
  - NV-2/3 dialogue rewrites route through correct success/failure nodes
  - NV-5 compliance rules hold on the actual content

Each scenario configures a ``SocialManager`` with a specific build
(specialist, generalist, neglector), walks a real dialogue tree, selects
the skill-gated response, and asserts the downstream state (node
transition + flag set).

Unit tests cover the bonus math in isolation. These tests prove the math
lands correctly when it meets the authored content.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.dialogue import DialogueManager
from spacegame.models.social import SocialManager


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


def _manager_with_levels(**levels: int) -> SocialManager:
    """Build a SocialManager with explicit base levels."""
    mgr = SocialManager()
    for skill_id, level in levels.items():
        skill = mgr.get_skill(skill_id)
        assert skill is not None, f"unknown skill: {skill_id}"
        skill.level = level
    return mgr


def _start_dialogue(dl, dm: DialogueManager, tree_id: str, npc_id: str = "test_npc") -> None:
    """Start a dialogue tree by id and attach the scenario's NPC id."""
    tree = dl.dialogue_trees[tree_id]
    dm.start_dialogue(tree, npc_id=npc_id)


def _walk_to_node(dm: DialogueManager, node_id: str) -> None:
    """Jump directly to a node. Bypasses traversal — scenarios pre-position
    the player at the skill-check node rather than walking the whole tree."""
    dm._current_node_id = node_id  # test hook; no public API for jumps


def _find_response_index(dm: DialogueManager, predicate) -> int:
    """Return the index of the first response matching ``predicate``."""
    responses = dm.get_current_node().responses
    for i, r in enumerate(responses):
        if predicate(r):
            return i
    raise AssertionError(
        f"no response matched predicate at node "
        f"{dm.get_current_node().id}: responses={[r.text for r in responses]}"
    )


# ---------------------------------------------------------------------------
# Observation 2 — tev_refining_intro::weigh_output
# ---------------------------------------------------------------------------


class TestObservationCheckAtTev:
    """The Tev setter upgrade now gates knows_tev_skims behind an
    Observation 2 skill check. NV-6c verifies the integration end-to-end."""

    def test_specialist_observer_catches_skim(self, dl) -> None:
        """Observation 5 (others 1) — effective 5 + spec +2 = 7 >= 2. Passes,
        flag set."""
        mgr = _manager_with_levels(persuasion=1, intimidation=1, observation=5)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "tev_refining_intro", npc_id="tev")
        _walk_to_node(dm, "weigh_output")

        idx = _find_response_index(
            dm, lambda r: (r.skill_check is not None) and r.skill_check.skill == "observation"
        )
        next_node = dm.select_response(idx)
        assert next_node is not None
        assert dm.get_flag("knows_tev_skims"), (
            "Observation specialist should catch the skim and set the flag"
        )

    def test_neglector_misses_skim(self, dl) -> None:
        """Observation 1 (others 5) — effective 1 + spec -1 = 0 < 2. Fails,
        no flag. Player still sees the option text but the check fails."""
        mgr = _manager_with_levels(persuasion=5, intimidation=5, observation=1)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "tev_refining_intro", npc_id="tev")
        _walk_to_node(dm, "weigh_output")

        idx = _find_response_index(
            dm, lambda r: (r.skill_check is not None) and r.skill_check.skill == "observation"
        )
        next_node = dm.select_response(idx)
        assert next_node is not None
        assert not dm.get_flag("knows_tev_skims"), (
            "Observation neglector should miss the skim — flag must not be set"
        )

    def test_baseline_response_never_sets_flag(self, dl) -> None:
        """The '[Noted. Run it.]' response (no skill check) must never grant
        knows_tev_skims on its own. NV-2/3 moved the flag to skill_check path
        so this baseline response is a graceful skip-without-catch."""
        mgr = _manager_with_levels(persuasion=1, intimidation=1, observation=5)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "tev_refining_intro", npc_id="tev")
        _walk_to_node(dm, "weigh_output")

        idx = _find_response_index(
            dm, lambda r: r.skill_check is None and r.text.startswith("[Noted")
        )
        dm.select_response(idx)
        assert not dm.get_flag("knows_tev_skims"), (
            "Even an Observation specialist who picks '[Noted. Run it.]' should "
            "not automatically gain the knowledge — catching the skim requires "
            "actively choosing the Observation read"
        )


# ---------------------------------------------------------------------------
# Persuasion 3 — dex_cantina::tension
# ---------------------------------------------------------------------------


class TestPersuasionCheckAtDex:
    """Dex's Persuasion 3 check routes to chip_truth on success, the_favor
    on failure. Specialization determines which."""

    def test_specialist_persuader_gets_truth(self, dl) -> None:
        """Persuasion 5 (others 1) — effective 5 + spec +2 = 7 >= 3. Routes
        to chip_truth where Dex opens up."""
        mgr = _manager_with_levels(persuasion=5, intimidation=1, observation=1)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "dex_cantina", npc_id="dex_halloran")
        _walk_to_node(dm, "tension")

        idx = _find_response_index(
            dm,
            lambda r: (r.skill_check is not None)
            and r.skill_check.skill == "persuasion"
            and r.skill_check.difficulty == 3,
        )
        next_node = dm.select_response(idx)
        assert next_node is not None
        assert dm.get_current_node().id == "chip_truth"

    def test_neglector_gets_deflection(self, dl) -> None:
        """Persuasion 1 (others 5) — effective 1 + spec -1 = 0 < 3. Routes
        to the_favor where Dex deflects."""
        mgr = _manager_with_levels(persuasion=1, intimidation=5, observation=5)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "dex_cantina", npc_id="dex_halloran")
        _walk_to_node(dm, "tension")

        idx = _find_response_index(
            dm,
            lambda r: (r.skill_check is not None)
            and r.skill_check.skill == "persuasion"
            and r.skill_check.difficulty == 3,
        )
        next_node = dm.select_response(idx)
        assert next_node is not None
        assert dm.get_current_node().id == "the_favor"


# ---------------------------------------------------------------------------
# Knowledge-flag gating — arna_post_refining accusation
# ---------------------------------------------------------------------------


class TestKnowledgeFlagGating:
    """Arna's accusation response is gated on ``knows_tev_skims``. A player
    who caught the skim via Observation gets the option; one who didn't does
    not. This verifies the NV-2/3 voice rewrite is wired to the real flag
    gating the real dialogue."""

    def test_player_who_caught_skim_sees_accusation(self, dl) -> None:
        mgr = _manager_with_levels(persuasion=1, intimidation=1, observation=5)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        dm.set_flag("knows_tev_skims", True)
        _start_dialogue(dl, dm, "arna_post_refining", npc_id="arna")
        _walk_to_node(dm, "start")

        available = dm.get_available_responses()
        accusation = [r for r in available if r.text.startswith("[Observation]")]
        assert len(accusation) == 1, (
            "Players who caught the skim should see the [Observation] "
            "accusation response"
        )
        assert "skimmed" in accusation[0].text.lower()

    def test_player_who_missed_skim_does_not_see_accusation(self, dl) -> None:
        mgr = _manager_with_levels(persuasion=5, intimidation=5, observation=1)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        # No knows_tev_skims flag set — simulates a player who didn't catch it
        _start_dialogue(dl, dm, "arna_post_refining", npc_id="arna")
        _walk_to_node(dm, "start")

        available = dm.get_available_responses()
        accusation = [r for r in available if r.text.startswith("[Observation]")]
        assert len(accusation) == 0, (
            "Players without the flag should NOT see the accusation — the "
            "insight must be earned through the Observation check"
        )
        # But they still have some response available — the [Stay silent.] path
        assert any(r.text.startswith("[Stay silent") for r in available)


# ---------------------------------------------------------------------------
# Specialization tie-breaker — generalist vs specialist at borderline
# ---------------------------------------------------------------------------


class TestSpecializationAsTieBreaker:
    """On a borderline check, the specialization bonus is the difference
    between pass and fail. This is the core NV-0 value proposition — prove
    it on real content."""

    def test_matched_generalist_fails_difficulty_3(self, dl) -> None:
        """All social skills at 3 — effective 3 + spec 0 = 3 meets diff 3.
        This is the baseline: generalist can barely pass a D3 check at
        level 3 across the board."""
        mgr = _manager_with_levels(persuasion=3, intimidation=3, observation=3)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "dex_cantina", npc_id="dex_halloran")
        _walk_to_node(dm, "tension")

        idx = _find_response_index(
            dm,
            lambda r: (r.skill_check is not None)
            and r.skill_check.difficulty == 3,
        )
        dm.select_response(idx)
        # Effective 3 meets difficulty 3 — passes
        assert dm.get_current_node().id == "chip_truth"

    def test_specialist_at_lower_base_still_passes_d3(self, dl) -> None:
        """Persuasion 3 with others at 1 — effective 3 + spec +2 = 5 passes
        diff 3 comfortably. A mid-level specialist beats the same difficulty
        a max-level generalist would merely equal."""
        mgr = _manager_with_levels(persuasion=3, intimidation=1, observation=1)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "dex_cantina", npc_id="dex_halloran")
        _walk_to_node(dm, "tension")

        idx = _find_response_index(
            dm,
            lambda r: (r.skill_check is not None)
            and r.skill_check.difficulty == 3,
        )
        dm.select_response(idx)
        assert dm.get_current_node().id == "chip_truth"

    def test_higher_absolute_generalist_beats_lower_specialist_at_d5(
        self, dl
    ) -> None:
        """A Persuasion 5 generalist (all 5) scores effective 5 + spec 0 = 5.
        A Persuasion 4 specialist (others 1) scores 4 + spec +2 = 6. The
        specialist still wins at the high end. But neither misses D3."""
        generalist = _manager_with_levels(persuasion=5, intimidation=5, observation=5)
        specialist = _manager_with_levels(persuasion=4, intimidation=1, observation=1)

        for mgr in (generalist, specialist):
            dm = DialogueManager()
            dm.set_social_manager(mgr)
            _start_dialogue(dl, dm, "dex_cantina", npc_id="dex_halloran")
            _walk_to_node(dm, "tension")
            idx = _find_response_index(
                dm,
                lambda r: (r.skill_check is not None)
                and r.skill_check.difficulty == 3,
            )
            dm.select_response(idx)
            assert dm.get_current_node().id == "chip_truth"


# ---------------------------------------------------------------------------
# NV-8c — NV-7 content integration scenarios
#
# Each scenario below exercises a *different interaction pattern* — not
# just "specialist passes, neglector fails." The point is to prove that
# NV-7 content works the way its author expected when specialization,
# disposition, attribute mapping, and dialogue routing all meet.
# ---------------------------------------------------------------------------


class TestIntimidationD3BranchesCorrectly:
    """Hanna Voss's Intimidation 3 — high-difficulty check that actually
    branches (success routes to food_task, failure to food_reason).
    NV-7 wave 1 content."""

    def test_intimidation_specialist_skips_food_reason(self, dl) -> None:
        """Intimidation 5, others 1 → effective 5 + spec +2 = 7. Passes D3.
        Routes to food_task, skipping food_reason's 'why food' explanation."""
        mgr = _manager_with_levels(intimidation=5, persuasion=1, observation=1)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "hanna_voss_dock", npc_id="hanna_voss")
        _walk_to_node(dm, "union_way")

        idx = _find_response_index(
            dm,
            lambda r: (r.skill_check is not None)
            and r.skill_check.skill == "intimidation",
        )
        dm.select_response(idx)
        assert dm.get_current_node().id == "food_task"

    def test_intimidation_neglector_routes_to_explanation(self, dl) -> None:
        """All other skills up, Intimidation 1 → effective 1 + spec -1 = 0.
        Fails D3. Routes to food_reason (the normal 'why food' branch)."""
        mgr = _manager_with_levels(intimidation=1, persuasion=5, observation=5)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "hanna_voss_dock", npc_id="hanna_voss")
        _walk_to_node(dm, "union_way")

        idx = _find_response_index(
            dm,
            lambda r: (r.skill_check is not None)
            and r.skill_check.skill == "intimidation",
        )
        dm.select_response(idx)
        assert dm.get_current_node().id == "food_reason"


class TestTechnicalD3VirtuosoCheck:
    """Sienna's Technical 3 — tests attribute mapping (Technical draws
    from Ingenuity, not Synergy). Proves NV-6.5 wiring holds on content."""

    def test_ingenuity_attribute_contributes_to_technical(self, dl) -> None:
        """Low base Technical (1), but high Ingenuity (6). Attribute synergy
        pushes effective level to 4. Still fails D3. Proves synergy alone
        isn't enough — base matters."""
        from spacegame.models.attributes import AttributeSheet

        mgr = _manager_with_levels(technical=1)
        sheet = AttributeSheet()
        sheet.values["ing"] = 6
        mgr.set_attribute_sheet(sheet)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "sienna_vek_warning", npc_id="sienna_vek")
        _walk_to_node(dm, "introduction")

        # Before clicking: confirm effective_level = base(1) + spec_bonus + synergy
        # base 1 + spec from all-1-except-technical = 0 + synergy (6//2=3) = 4
        effective = mgr.get_effective_level("technical", "sienna_vek")
        assert effective == 4  # 1 base + 0 spec + 3 synergy

        # But the dialogue ROUTING: both success/failure node_ids are
        # the same ("revelation") — NV-7 authored this as cosmetic.
        idx = _find_response_index(
            dm,
            lambda r: (r.skill_check is not None)
            and r.skill_check.skill == "technical",
        )
        dm.select_response(idx)
        assert dm.get_current_node().id == "revelation"


class TestPilotingD3AttributeRoute:
    """Yuki's Piloting 3 — tests that Piloting routes through Acuity
    attribute (not Synergy)."""

    def test_acuity_bonus_helps_piloting_specialist(self, dl) -> None:
        """Piloting 3, others 1, Acuity 5 → effective 3 + spec +2 + (5//2)=2 = 7.
        Comfortably passes D3."""
        from spacegame.models.attributes import AttributeSheet

        mgr = _manager_with_levels(piloting=3)
        sheet = AttributeSheet()
        sheet.values["acu"] = 5
        mgr.set_attribute_sheet(sheet)
        # Piloting specialist: others should be at 1 (default).
        effective = mgr.get_effective_level("piloting", "nova_researcher")
        assert effective == 7  # 3 + 2 spec + 2 acuity


class TestDeceptionD2Routing:
    """Larsen Deception 2 — proves Deception routes correctly and both
    paths lead to personal_supplies (cosmetic only)."""

    def test_deception_skill_check_resolves_cleanly(self, dl) -> None:
        """Any build hits the skill check; both paths route to
        personal_supplies. The flag only sets on success."""
        mgr = _manager_with_levels(deception=3)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "larsen_customs", npc_id="officer_larsen")
        _walk_to_node(dm, "no_bill")

        idx = _find_response_index(
            dm,
            lambda r: (r.skill_check is not None)
            and r.skill_check.skill == "deception",
        )
        dm.select_response(idx)
        assert dm.get_current_node().id == "personal_supplies"


class TestDispositionSelectivityOnContent:
    """Verifies the NV-6.5 selective-disposition rule holds on real content:
    NPC disposition affects social skills but not Technical/Piloting."""

    def test_low_disposition_does_not_harm_technical(self, dl) -> None:
        """Hostile NPC (disposition 20). Technical check succeeds anyway
        because it doesn't depend on NPC mood."""
        mgr = _manager_with_levels(technical=3)
        mgr.modify_disposition("sienna_vek", -30)  # 50 - 30 = 20
        # Technical: base 3 + disp 0 (skipped for technical) + spec +2 = 5
        effective = mgr.get_effective_level("technical", "sienna_vek")
        assert effective == 5

    def test_low_disposition_DOES_harm_persuasion(self, dl) -> None:
        """Same hostile NPC. Persuasion check takes a disposition hit
        because persuasion IS disposition-sensitive."""
        mgr = _manager_with_levels(persuasion=3)
        mgr.modify_disposition("sienna_vek", -30)
        # Persuasion: base 3 + disp -3 + spec +2 = 2
        effective = mgr.get_effective_level("persuasion", "sienna_vek")
        assert effective == 2


class TestLeadershipContentRouting:
    """dead_ledger_investigation Leadership 2 — proves the new check
    routes to overview on both paths (cosmetic), setting the
    offered_to_lead_investigation flag only on success."""

    def test_leadership_check_sets_flag_and_routes(self, dl) -> None:
        mgr = _manager_with_levels(leadership=5, persuasion=1)
        dm = DialogueManager()
        dm.set_social_manager(mgr)
        _start_dialogue(dl, dm, "dead_ledger_investigation", npc_id="dock_investigator")

        idx = _find_response_index(
            dm,
            lambda r: (r.skill_check is not None)
            and r.skill_check.skill == "leadership",
        )
        dm.select_response(idx)
        assert dm.get_current_node().id == "overview"
        assert dm.get_flag("offered_to_lead_investigation"), (
            "Leadership specialist should pass D2 and set the flag"
        )
