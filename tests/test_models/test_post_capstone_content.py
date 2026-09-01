"""A2-21: PostCapstoneContentGenerator unit tests.

Covers acceptance criteria 1-5 from ROADMAP.md's A2-21 sprint section:

- AC1: empire lens returns a mission with a HAS_FLAG objective on the
  correct outcome_flag AND a REACH_SYSTEM objective targeting a valid
  system id.
- AC2: community lens returns a mission whose id begins with
  ``post_capstone_community_`` and whose description contains a
  community-specific marker distinguishing it from generic
  procedural output.
- AC3: vengeance lens returns a mission with a HAS_FLAG objective on
  the resolved outcome_flag and a description that names a specific
  narrative element from the resolution.
- AC4: unimplemented lens (e.g. ``faith``) returns [] without raising;
  same when the ``{lens_id}_capstone_reached`` flag is absent.
- AC5: determinism -- two calls with same seed/day/state return equal
  output; different game_day produces different output.

Fixtures build a minimal ``Player`` inline; a full ``Game`` is never
constructed. Templates are loaded from the real data file so the
scanner catches drift between the templates JSON and the generator.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.dilemma import DilemmaRuntimeState
from spacegame.models.lens_investment import LensInvestment
from spacegame.models.mission import ObjectiveType
from spacegame.models.player import Player
from spacegame.models.post_capstone_content import PostCapstoneContentGenerator
from spacegame.models.ship import Ship


def _make_player(system_id: str = "nexus_prime") -> Player:
    """Minimal player fixture. Not a Game."""
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    p = Player("Tester", 1000, system_id, ship)
    # Ensure the sub-models are fresh (some tests share a data loader).
    p.lens_investment = LensInvestment()
    p.dilemma_state = DilemmaRuntimeState()
    p.capstones_reached = set()
    p.dialogue_flags = {}
    return p


def _make_generator() -> PostCapstoneContentGenerator:
    dl = get_data_loader()
    dl.load_all()
    return PostCapstoneContentGenerator(
        systems=dl.systems,
        commodities=dl.commodities,
        enemy_templates=dl.enemy_templates,
        templates=dl.post_capstone_templates,
        seed=12345,
    )


class TestEmpireLensGeneration:
    """AC1 -- empire lens returns a mission gated on the resolved outcome flag."""

    def test_empire_capstone_yields_mission_with_has_flag_and_reach_system(self) -> None:
        gen = _make_generator()
        player = _make_player()
        player.dialogue_flags["empire_capstone_reached"] = True
        player.dilemma_state.resolved = {"d6_preservation_empire": "empire"}
        player.dialogue_flags["d6_empire_won"] = True

        missions = gen.generate_for_lens("empire", game_day=10, player=player)

        assert missions, "empire capstone must yield at least one mission"
        # At least one mission has both a HAS_FLAG and REACH_SYSTEM objective
        for m in missions:
            has_flag_objs = [o for o in m.objectives if o.type == ObjectiveType.HAS_FLAG]
            reach_objs = [o for o in m.objectives if o.type == ObjectiveType.REACH_SYSTEM]
            if has_flag_objs and reach_objs:
                # Flag target must be one of the recognized outcome flags
                flag_targets = {o.target_id for o in has_flag_objs}
                assert flag_targets & {"d6_empire_won", "d3_empire_won"}, (
                    f"expected an empire outcome_flag on HAS_FLAG objective, got {flag_targets}"
                )
                # Reach system target must be in the systems registry
                dl = get_data_loader()
                for obj in reach_objs:
                    assert obj.target_id in dl.systems, (
                        f"REACH_SYSTEM target '{obj.target_id}' not in systems"
                    )
                return
        raise AssertionError("no mission had both HAS_FLAG and REACH_SYSTEM objectives")

    def test_empire_mission_id_prefix(self) -> None:
        gen = _make_generator()
        player = _make_player()
        player.dialogue_flags["empire_capstone_reached"] = True
        player.dilemma_state.resolved = {"d6_preservation_empire": "empire"}
        player.dialogue_flags["d6_empire_won"] = True

        missions = gen.generate_for_lens("empire", game_day=10, player=player)

        assert missions
        for m in missions:
            assert m.id.startswith("post_capstone_empire_"), (
                f"empire mission id must start with 'post_capstone_empire_', got {m.id!r}"
            )


class TestCommunityLensGeneration:
    """AC2 -- community lens has its own id prefix and specific description marker."""

    def test_community_capstone_yields_prefix_and_description(self) -> None:
        gen = _make_generator()
        player = _make_player()
        player.dialogue_flags["community_capstone_reached"] = True
        player.dilemma_state.resolved = {"d2_wealth_community": "community"}
        player.dialogue_flags["d2_community_won"] = True

        missions = gen.generate_for_lens("community", game_day=25, player=player)

        assert missions, "community capstone must yield at least one mission"
        for m in missions:
            assert m.id.startswith("post_capstone_community_"), (
                f"community mission id prefix wrong: {m.id!r}"
            )
        # At least one description contains a community/settlement marker
        joined = " ".join(m.description.lower() for m in missions)
        markers = ("settlement", "cradlepoint", "kallio", "scarcity", "list", "clinic")
        assert any(marker in joined for marker in markers), (
            f"expected a settlement/scarcity marker in community descriptions; "
            f"got: {joined[:200]!r}"
        )

    def test_community_uses_collect_cargo_objective(self) -> None:
        gen = _make_generator()
        player = _make_player()
        player.dialogue_flags["community_capstone_reached"] = True
        player.dilemma_state.resolved = {"d8_crime_community": "community"}
        player.dialogue_flags["d8_community_won"] = True

        missions = gen.generate_for_lens("community", game_day=25, player=player)

        assert missions
        found_collect = False
        for m in missions:
            for obj in m.objectives:
                if obj.type == ObjectiveType.COLLECT_CARGO:
                    found_collect = True
                    dl = get_data_loader()
                    assert obj.target_id in dl.commodities, (
                        f"COLLECT_CARGO target '{obj.target_id}' not in commodities"
                    )
        assert found_collect, "community mission must include a COLLECT_CARGO objective"


class TestVengeanceLensGeneration:
    """AC3 -- vengeance mission names specific narrative elements."""

    def test_vengeance_names_foss_or_vert_from_d1(self) -> None:
        gen = _make_generator()
        player = _make_player()
        player.dialogue_flags["vengeance_capstone_reached"] = True
        player.dilemma_state.resolved = {"d1_vengeance_justice": "vengeance"}
        player.dialogue_flags["d1_vengeance_won"] = True

        missions = gen.generate_for_lens("vengeance", game_day=7, player=player)

        assert missions
        # At least one mission references a D1 name
        joined = " ".join(m.description for m in missions)
        assert "Rendik Foss" in joined or "Callan Vert" in joined, (
            f"expected D1 narrative names (Foss/Vert) in vengeance descriptions; "
            f"got: {joined[:250]!r}"
        )
        # HAS_FLAG objective on d1_vengeance_won
        found = False
        for m in missions:
            for obj in m.objectives:
                if obj.type == ObjectiveType.HAS_FLAG and obj.target_id == "d1_vengeance_won":
                    found = True
        assert found, "expected a HAS_FLAG objective referencing d1_vengeance_won"

    def test_vengeance_names_senn_or_ledger_from_d4(self) -> None:
        gen = _make_generator()
        player = _make_player()
        player.dialogue_flags["vengeance_capstone_reached"] = True
        player.dilemma_state.resolved = {"d4_truth_vengeance": "vengeance"}
        player.dialogue_flags["d4_vengeance_won"] = True

        missions = gen.generate_for_lens("vengeance", game_day=7, player=player)

        assert missions
        joined = " ".join(m.description for m in missions)
        assert "Senn" in joined or "Ledger" in joined, (
            f"expected D4 narrative names (Senn/Ledger) in vengeance descriptions; "
            f"got: {joined[:250]!r}"
        )
        found = False
        for m in missions:
            for obj in m.objectives:
                if obj.type == ObjectiveType.HAS_FLAG and obj.target_id == "d4_vengeance_won":
                    found = True
        assert found, "expected a HAS_FLAG objective referencing d4_vengeance_won"


class TestUnimplementedLensReturnsEmpty:
    """AC4 -- unimplemented lens or missing capstone_reached flag returns []."""

    def test_faith_lens_with_flag_returns_empty(self) -> None:
        gen = _make_generator()
        player = _make_player()
        player.dialogue_flags["faith_capstone_reached"] = True

        assert gen.generate_for_lens("faith", game_day=10, player=player) == []

    def test_missing_capstone_flag_returns_empty(self) -> None:
        gen = _make_generator()
        player = _make_player()
        # No capstone_reached flag set for empire
        assert gen.generate_for_lens("empire", game_day=10, player=player) == []

    def test_unknown_lens_returns_empty_without_flag(self) -> None:
        gen = _make_generator()
        player = _make_player()
        assert gen.generate_for_lens("not_a_lens", game_day=10, player=player) == []

    def test_empire_without_gate_flag_returns_empty(self) -> None:
        """Empire capstone_reached is set but no matching resolved outcome_flag."""
        gen = _make_generator()
        player = _make_player()
        player.dialogue_flags["empire_capstone_reached"] = True
        # No d3_empire_won or d6_empire_won in dialogue_flags
        assert gen.generate_for_lens("empire", game_day=10, player=player) == []


class TestDeterminism:
    """AC5 -- same inputs produce equal output; different day produces different output."""

    def _make_empire_player(self) -> Player:
        player = _make_player()
        player.dialogue_flags["empire_capstone_reached"] = True
        player.dilemma_state.resolved = {"d6_preservation_empire": "empire"}
        player.dialogue_flags["d6_empire_won"] = True
        return player

    def test_two_calls_same_day_produce_equal_output(self) -> None:
        gen_a = _make_generator()
        gen_b = _make_generator()
        pa = self._make_empire_player()
        pb = self._make_empire_player()

        out_a = gen_a.generate_for_lens("empire", game_day=10, player=pa)
        out_b = gen_b.generate_for_lens("empire", game_day=10, player=pb)

        assert len(out_a) == len(out_b) and len(out_a) > 0
        for m_a, m_b in zip(out_a, out_b, strict=True):
            assert m_a.id == m_b.id
            assert m_a.description == m_b.description
            assert [(o.type, o.target_id) for o in m_a.objectives] == [
                (o.type, o.target_id) for o in m_b.objectives
            ]

    def test_different_game_day_produces_different_output(self) -> None:
        gen_a = _make_generator()
        gen_b = _make_generator()
        pa = self._make_empire_player()
        pb = self._make_empire_player()

        out_a = gen_a.generate_for_lens("empire", game_day=10, player=pa)
        out_b = gen_b.generate_for_lens("empire", game_day=99, player=pb)

        # Something must differ -- ids at minimum since they include day
        ids_a = [m.id for m in out_a]
        ids_b = [m.id for m in out_b]
        assert ids_a != ids_b, (
            f"different game_day must produce different mission ids (got {ids_a} vs {ids_b})"
        )


class TestNoLensInvestmentReads:
    """AC8 -- the generator does not read player.lens_investment.

    The generator lives in ``spacegame/models/`` which the compliance
    scanner does NOT forbid, but this sprint's engine wiring reads only
    ``dialogue_flags`` / ``dilemma_state`` / ``capstones_reached``. This
    test proves the generator itself doesn't require investment either,
    so a caller that never populates lens_investment still gets output.
    """

    def test_generator_works_without_lens_investment_populated(self) -> None:
        gen = _make_generator()
        player = _make_player()
        # Do NOT touch player.lens_investment.
        player.dialogue_flags["empire_capstone_reached"] = True
        player.dilemma_state.resolved = {"d6_preservation_empire": "empire"}
        player.dialogue_flags["d6_empire_won"] = True

        missions = gen.generate_for_lens("empire", game_day=10, player=player)

        assert missions, "generator must work without any lens_investment reads"
