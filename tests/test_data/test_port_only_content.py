"""Content only the Godot port reads (SpaceGame register F-014; bug bash BB-27, BB-3).

Python keeps its own rules: the first sale's 1.5x bonus (game.py, trading_view.py) and
Emergency Reserves' 1-fuel floor (``travel.fuel_after_jump``). The port reads the
new-market premium's numbers, the stations' first-sale lines, a skill text that
describes its sealed reserve cell, and the crew's ``opened_market`` and ``sold_back``
barks, whose two action types Python never fires.
"""

from __future__ import annotations

import json
from pathlib import Path

from spacegame.data_loader import get_data_loader
from spacegame.models.travel import fuel_after_jump

ROOT = Path(__file__).resolve().parents[2]
PREMIUM = {
    "base_percent": 8,
    "percent_per_commerce_level": 2,
    "percent_per_commerce_point": 1,
    "max_percent": 50,
    "cap_per_level": 500,
    "min_margin_percent": 10,
}
NO_LINE = {"the_fulcrum", "herons_mark"}


def _lines() -> list[dict[str, str]]:
    path = ROOT / "data" / "economy" / "first_sale_lines.json"
    return json.loads(path.read_text(encoding="utf-8"))["first_sale_lines"]


def test_the_premium_block_holds_the_approved_numbers() -> None:
    balance = json.loads((ROOT / "data" / "economy" / "balance.json").read_text("utf-8"))
    block = balance["economy"]["new_market_premium"]
    assert block == PREMIUM
    assert all(type(value) is int for value in block.values())


def test_every_market_but_two_has_one_first_sale_line() -> None:
    systems = list(get_data_loader().systems)
    assert [line["system_id"] for line in _lines()] == [s for s in systems if s not in NO_LINE]


def test_each_line_has_a_speaker_and_text() -> None:
    for line in _lines():
        assert set(line) == {"system_id", "speaker", "text"}, line
        assert line["speaker"].strip() and line["text"].strip(), line


def test_emergency_reserves_names_the_ports_cell_and_python_keeps_its_floor() -> None:
    skills = json.loads((ROOT / "data" / "progression" / "skills.json").read_text("utf-8"))
    reserves = next(s for s in skills["skills"] if s["id"] == "emergency_reserves")
    assert reserves["description"] == (
        "A sealed reserve cell covers the jump out when stranded; the next refuel pays for it"
    )
    assert fuel_after_jump(0, 1.0) == 1


def test_python_reads_neither_file_section() -> None:
    """If Python starts reading them, F-014 and deviations D-23 and D-25 change too."""
    for path in (ROOT / "spacegame").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "new_market_premium" not in text, path
        assert "first_sale_lines" not in text, path


def test_python_never_fires_the_ports_bark_actions() -> None:
    """The opened_market and sold_back barks are the port's (writing plan W3b; F-014)."""
    for path in (ROOT / "spacegame").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "opened_market" not in text and "sold_back" not in text, path
    lines = json.loads((ROOT / "data" / "crew" / "ambient_dialogue.json").read_text("utf-8"))
    actions = [line.get("action_type") for line in lines["ambient_lines"]]
    assert actions.count("opened_market") == 5 and actions.count("sold_back") == 4
