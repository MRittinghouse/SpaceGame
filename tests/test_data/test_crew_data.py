"""Data validation tests for crew templates and ambient dialogue."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"

CREW_FILE = DATA_DIR / "crew" / "crew_members.json"
DIALOGUE_FILE = DATA_DIR / "crew" / "ambient_dialogue.json"

# All valid system IDs from the game
VALID_SYSTEMS = {
    "nexus_prime", "stellaris_port", "breakstone", "iron_depths",
    "forgeworks", "axiom_labs", "nova_research", "havens_rest",
    "verdant", "crimson_reach", "the_fulcrum",
}

VALID_FACTIONS = {
    "commerce_guild", "industrial_union", "science_collective",
    "frontier_alliance", "free_alliance", "",
}


def _load_crew_data() -> list[dict]:
    with open(CREW_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["crew_templates"]


def _load_dialogue_data() -> list[dict]:
    with open(DIALOGUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["ambient_lines"]


class TestCrewTemplateData:
    """Validate crew_members.json structure and content."""

    def test_total_crew_count(self) -> None:
        templates = _load_crew_data()
        assert len(templates) == 19  # 4 companions + 15 crew

    def test_companion_count(self) -> None:
        templates = _load_crew_data()
        companions = [t for t in templates if t.get("is_companion", False)]
        assert len(companions) == 4

    def test_crew_count(self) -> None:
        templates = _load_crew_data()
        crew = [t for t in templates if not t.get("is_companion", False)]
        assert len(crew) == 15

    def test_all_have_required_fields(self) -> None:
        required = {"id", "name", "role", "description", "portrait_color"}
        for t in _load_crew_data():
            missing = required - set(t.keys())
            assert not missing, f"{t['id']} missing fields: {missing}"

    def test_unique_ids(self) -> None:
        templates = _load_crew_data()
        ids = [t["id"] for t in templates]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[i for i in ids if ids.count(i) > 1]}"

    def test_valid_home_systems(self) -> None:
        for t in _load_crew_data():
            system = t.get("home_system_id", "")
            if system:
                assert system in VALID_SYSTEMS, f"{t['id']} has invalid home_system_id: {system}"

    def test_crew_have_max_level_1(self) -> None:
        templates = _load_crew_data()
        crew = [t for t in templates if not t.get("is_companion", False)]
        for c in crew:
            assert c.get("max_level", 5) == 1, f"{c['id']} should have max_level=1"

    def test_crew_have_no_combat_move(self) -> None:
        templates = _load_crew_data()
        crew = [t for t in templates if not t.get("is_companion", False)]
        for c in crew:
            assert c.get("combat_move") is None, f"{c['id']} should not have combat_move"

    def test_companions_have_combat_move(self) -> None:
        templates = _load_crew_data()
        companions = [t for t in templates if t.get("is_companion", False)]
        for c in companions:
            assert c.get("combat_move") is not None, f"{c['id']} should have combat_move"

    def test_crew_abilities_all_level_1(self) -> None:
        templates = _load_crew_data()
        crew = [t for t in templates if not t.get("is_companion", False)]
        for c in crew:
            for ability in c.get("abilities", []):
                assert ability.get("unlock_level", 1) == 1, (
                    f"{c['id']} ability '{ability['description']}' should be unlock_level=1"
                )

    def test_portrait_color_valid_rgb(self) -> None:
        for t in _load_crew_data():
            color = t["portrait_color"]
            assert len(color) == 3, f"{t['id']} portrait_color must be [R, G, B]"
            for val in color:
                assert 0 <= val <= 255, f"{t['id']} portrait_color value {val} out of range"

    def test_all_systems_have_crew(self) -> None:
        """Every system should have at least one crew member (companion or crew)."""
        templates = _load_crew_data()
        covered_systems = {t["home_system_id"] for t in templates if t.get("home_system_id")}
        for system in VALID_SYSTEMS:
            assert system in covered_systems, f"No crew at system: {system}"


class TestAmbientDialogueData:
    """Validate ambient_dialogue.json structure and content."""

    def test_all_crew_have_dialogue(self) -> None:
        templates = _load_crew_data()
        dialogue = _load_dialogue_data()
        crew_ids_with_lines = {line["crew_id"] for line in dialogue}
        for t in templates:
            assert t["id"] in crew_ids_with_lines, f"{t['id']} has no ambient dialogue"

    def test_new_crew_have_at_least_3_lines(self) -> None:
        templates = _load_crew_data()
        dialogue = _load_dialogue_data()
        crew = [t for t in templates if not t.get("is_companion", False)]
        for c in crew:
            lines = [d for d in dialogue if d["crew_id"] == c["id"]]
            assert len(lines) >= 3, f"{c['id']} has only {len(lines)} dialogue lines (need >= 3)"

    def test_each_crew_has_home_system_line(self) -> None:
        templates = _load_crew_data()
        dialogue = _load_dialogue_data()
        crew = [t for t in templates if not t.get("is_companion", False)]
        for c in crew:
            home_lines = [
                d for d in dialogue
                if d["crew_id"] == c["id"] and d["context"] == "home_system"
            ]
            assert len(home_lines) >= 1, f"{c['id']} has no home_system dialogue line"

    def test_dialogue_references_valid_crew(self) -> None:
        templates = _load_crew_data()
        valid_ids = {t["id"] for t in templates}
        for line in _load_dialogue_data():
            assert line["crew_id"] in valid_ids, f"Dialogue references unknown crew: {line['crew_id']}"
