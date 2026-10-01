"""BB-74: the faction map is content, from the cultural guide, the same in every game."""

from __future__ import annotations

from pathlib import Path

from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.faction import generate_faction_assignments
from spacegame.models.mission import MissionManager
from tools.parity.snapshots import fresh_player

# requirements/cultural_guide.md, "System Profiles", with the author's two calls: Forgeworks
# ("Guild-aligned economically") and the Fulcrum (its content says Commerce Guild) go to the
# Guild, and nobody holds Heron's Mark. The crimson_reach faction holds nothing. In
# systems.json order.
GUIDE_MAP = {
    "nexus_prime": "commerce_guild",
    "verdant": "frontier_alliance",
    "forgeworks": "commerce_guild",
    "breakstone": "miners_union",
    "axiom_labs": "science_collective",
    "havens_rest": "frontier_alliance",
    "crimson_reach": "frontier_alliance",
    "stellaris_port": "commerce_guild",
    "iron_depths": "miners_union",
    "nova_research": "science_collective",
    "the_fulcrum": "commerce_guild",
}
UNHELD = {"herons_mark"}


def _dl() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


class TestTheMap:
    def test_every_system_names_its_holder(self) -> None:
        systems = _dl().get_all_systems()
        assert {s.id: s.faction_id for s in systems if s.faction_id} == GUIDE_MAP
        assert {s.id for s in systems if not s.faction_id} == UNHELD

    def test_every_holder_is_a_faction(self) -> None:
        assert set(GUIDE_MAP.values()) <= set(_dl().factions)

    def test_the_crimson_reach_faction_keeps_its_standing_and_holds_nothing(self) -> None:
        dl = _dl()
        assert "crimson_reach" in dl.factions
        assert "crimson_reach" not in {s.faction_id for s in dl.get_all_systems()}

    def test_the_assignments_are_the_map_in_content_order(self) -> None:
        assignments = generate_faction_assignments(_dl().get_all_systems())
        assert assignments == GUIDE_MAP
        assert list(assignments) == list(GUIDE_MAP)


class TestPermits:
    """The bill of landing opens every held port but the Union's; Union Territory opens those."""

    def _permits_after(self, *mission_ids: str) -> set[str]:
        dl = _dl()
        manager = MissionManager(dl.missions)
        player = fresh_player()
        for mission_id in mission_ids:
            manager.complete_mission(mission_id, player, faction_ids=list(dl.factions))
        return set(player.trade_permits)

    def test_the_bill_leaves_out_the_union(self) -> None:
        assert self._permits_after("bill_of_landing") == {
            "commerce_guild",
            "science_collective",
            "frontier_alliance",
        }

    def test_union_territory_adds_the_union(self) -> None:
        assert "miners_union" in self._permits_after("bill_of_landing", "union_territory")

    def test_every_holder_has_a_permit_source(self) -> None:
        permits = self._permits_after("bill_of_landing", "union_territory")
        assert set(GUIDE_MAP.values()) <= permits

    def test_the_refusal_names_the_permit(self) -> None:
        from spacegame.views import trading_view

        source = Path(trading_view.__file__).read_text(encoding="utf-8")
        assert trading_view.NO_PERMIT == "You need a trade permit to trade here"
        assert "bill of landing to trade" not in source
        assert source.count("_show_message(NO_PERMIT)") == 4
