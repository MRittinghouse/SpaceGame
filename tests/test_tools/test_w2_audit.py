"""Plan W2-S's worklist tool (writing-discipline spec 9.4): parsing the audit, composing the
audit's mechanical rewrites, swapping a JSON string in place, and checking and reading entries."""

from __future__ import annotations

import json
from pathlib import Path

from tools.writing import w2_audit
from tools.writing.w2_audit import ADOPT, DRAFT, SKIP, Entry, Row

AUDIT_SAMPLE = """# Narrator audit

### `../SpaceGame/data/encounters/generic.json` (2)

| # | Path | Class | Excerpt | Suggested rewrite | Note |
|---|---|---|---|---|---|
| 1 | `a_01/choices/go/description` | motive | Worth a look. | Fly closer. (end there) |  |
| 2 | `a_01/choices/go/outcome/description` | thought | Someone else can deal with it. | (cut; end on "You leave.") | edge: a note |

### `../SpaceGame/data/dialogue/dialogues.json` (1)

| # | Path | Class | Excerpt | Suggested rewrite | Note |
|---|---|---|---|---|---|
| 1 | `intro_narration/nodes/intro_1/text` | thought | Old intro. | New intro. |  |
"""


def test_parse_audit_reads_every_row_with_its_file_and_path() -> None:
    found = w2_audit.parse_audit(AUDIT_SAMPLE)
    assert [(file, path, row.row) for file, path, row in found] == [
        ("data/encounters/generic.json", "a_01/choices/go/description", 1),
        ("data/encounters/generic.json", "a_01/choices/go/outcome/description", 2),
        ("data/dialogue/dialogues.json", "intro_narration/nodes/intro_1/text", 1),
    ]
    assert found[1][2].note == "edge: a note"


def test_compose_applies_each_mechanical_form() -> None:
    line = "Drift past. Worth a look. The lights blink."
    assert w2_audit.compose(line, "Worth a look.", "Fly closer.") == (
        "Drift past. Fly closer. The lights blink."
    )
    assert w2_audit.compose(line, "Worth a look.", "Fly closer. (end there)") == (
        "Drift past. Fly closer."
    )
    cut = "You leave. Someone else can deal with it."
    assert w2_audit.compose(
        cut, "Someone else can deal with it.", '(cut; end on "You leave.")'
    ) == ("You leave.")
    opening = "Discretion wins out. You alter course."
    assert w2_audit.compose(
        opening, "Discretion wins out.", '(cut; open on "You alter course")'
    ) == ("You alter course.")


def test_compose_replaces_only_whole_sentences() -> None:
    assert w2_audit.compose("Worth a look, they say. Stay.", "Worth a look,", "Fly.") is None
    assert w2_audit.compose("Stay. Worth a look", "Worth a look", "Fly.") is None
    assert (
        w2_audit.compose("Stay. 'Worth a look.' Go.", "'Worth a look.'", "Fly.") == "Stay. Fly. Go."
    )


def test_a_hint_adopts_only_a_whole_replacement() -> None:
    path = ".encounters[id=a].choices[id=b].description"
    rows = [Row(1, "motive", "Worth a look.", "Fly closer.", "")]
    partial = Entry("data/x.json", path, "Dock. Worth a look.", rows=rows)
    w2_audit.decide(partial)
    assert (partial.disposition, partial.new) == (DRAFT, "")
    whole = Entry("data/x.json", path, "Worth a look.", rows=rows)
    w2_audit.decide(whole)
    assert (whole.disposition, whole.new) == (ADOPT, "Fly closer.")


def test_a_composition_that_adds_a_figure_needs_a_writer() -> None:
    rows = [Row(1, "motive", "Worth it.", "Pay the 800 and take the coil.", "")]
    entry = Entry("data/x.json", ".a", "Buy the coil. Worth it.", rows=rows)
    w2_audit.decide(entry)
    assert (entry.disposition, entry.new) == (DRAFT, "")


def test_an_awkward_composition_needs_a_writer() -> None:
    assert w2_audit._awkward("Twenty minutes, recording. the Collective would kill for.")
    assert w2_audit._awkward("Open a channel. Open a channel and answer them.")
    assert not w2_audit._awkward("Open a channel. Answer them. 'Fine.'")


def test_compose_leaves_anything_else_to_a_writer() -> None:
    line = "You log the coordinates and give it a respectful berth. Some things are best left."
    excerpt = "give it a respectful berth. Some things are best left."
    assert w2_audit.compose(line, excerpt, "You log the coordinates. (end there)") is None
    assert w2_audit.compose("A. B.", "B.", "Say C. (alone)") is None
    assert w2_audit.compose("A. B.", "B.", "(cut; end on the crew chief's cap)") is None
    assert w2_audit.compose("B. A.", "B.", '(cut; end on "A.")') is None


def test_compose_keeps_the_closing_quote_of_the_speech_it_ends_on() -> None:
    line = "'Either way, deck seven thanks you.' You feel good about this one."
    excerpt = "You feel good about this one."
    suggestion = '(cut; end on "deck seven thanks you.")'
    assert w2_audit.compose(line, excerpt, suggestion) == "'Either way, deck seven thanks you.'"


def test_compose_will_not_restate_the_line() -> None:
    line = "You dump the data. Maybe later."
    assert w2_audit.compose(line, "Maybe later.", "You dump the data.") is None
    wall = "Below, arrays. But your eyes go to the wall -- a gate frame, thirty meters across."
    suggestion = "On the wall: a gate frame, thirty meters across."
    assert w2_audit.compose(wall, "But your eyes go to the wall", suggestion) is None
    rows = [
        Row(1, "thought", "Maybe later.", "Keep it.", ""),
        Row(2, "thought", "Who knows?", "Keep it.", ""),
    ]
    entry = Entry("data/x.json", ".a", "Maybe later. Who knows?", rows=rows)
    w2_audit.decide(entry)
    assert (entry.disposition, entry.new) == (DRAFT, "")


def test_compose_cleans_the_join() -> None:
    assert w2_audit.compose("Go.  Not now. Stay.", "Not now.", "Wait.") == "Go. Wait. Stay."
    assert w2_audit.compose("Go now. Not today.", "Not today.", "Decline .") == "Go now. Decline."


def test_rows_on_one_string_compose_in_order() -> None:
    rows = [
        Row(1, "motive", "Worth a look.", "Fly closer.", ""),
        Row(2, "thought", "Who knows?", '(cut; end on "Fly closer.")', ""),
    ]
    entry = Entry("data/x.json", ".a", "Worth a look. Who knows?", rows=rows)
    w2_audit.decide(entry)
    assert (entry.disposition, entry.new) == (ADOPT, "Fly closer.")


def test_a_flag_that_needs_a_writer_makes_a_draft() -> None:
    rows = [Row(1, "thought", "Who knows?", "Fly on.", "")]
    entry = Entry(
        "data/journal/entries.json", ".journal_entries[id=x].text", "Who knows?", rows=rows
    )
    entry.flags = ["LOG"]
    w2_audit.decide(entry)
    assert (entry.disposition, entry.new) == (DRAFT, "")
    dashed = Entry(
        "data/x.json", ".a", "Go -- now. Who knows?", rows=rows, gates=["G1:double hyphen"]
    )
    w2_audit.decide(dashed)
    assert (dashed.disposition, dashed.new) == (DRAFT, "")


def test_a_bracketed_spoken_line_loses_its_brackets() -> None:
    entry = Entry("data/dialogue/dialogues.json", ".r", "[Your brother?]", gates=["G9:not an act"])
    w2_audit.decide(entry)
    assert (entry.disposition, entry.new) == (ADOPT, "Your brother?")


def test_swap_keeps_the_file_escaping_and_line_endings() -> None:
    raw = '{\r\n  "a": "Caf\\u00e9 \\"open\\".",\r\n  "b": "Plain."\r\n}\r\n'
    swapped = w2_audit.swap(raw, 'Café "open".', "Café shut.")
    assert swapped == '{\r\n  "a": "Caf\\u00e9 shut.",\r\n  "b": "Plain."\r\n}\r\n'
    assert json.loads(swapped)["a"] == "Café shut."


def test_swap_replaces_only_the_occurrence_its_path_names(tmp_path: Path) -> None:
    raw = '{"a": "[Yes.]", "b": "[Yes.]"}'
    assert w2_audit.swap(raw, "[Yes.]", "Yes.", 1, 2) == '{"a": "[Yes.]", "b": "Yes."}'
    data = tmp_path / "data"
    data.mkdir()
    (data / "f.json").write_text(raw, encoding="utf-8")
    entry = Entry("data/f.json", ".b", "[Yes.]", new="Yes.", disposition=ADOPT)
    assert w2_audit.apply_file([entry], "data/f.json", tmp_path) == 1
    assert json.loads((data / "f.json").read_text(encoding="utf-8")) == {"a": "[Yes.]", "b": "Yes."}


def _workspace(tmp_path: Path, text: str) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    (data / "f.json").write_text(json.dumps({"a": text}, indent=2) + "\n", encoding="utf-8")
    return tmp_path


def test_apply_and_check(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "You wait. Who knows? {they} stay.")
    rows = [Row(1, "thought", "Who knows?", "(cut)", "")]
    entry = Entry("data/f.json", ".a", "You wait. Who knows? {they} stay.", rows=rows)
    entry.new = "You wait. {they} stay."
    assert w2_audit.check([entry], {"data/f.json"}, root) == [
        "data/f.json|.a: the data does not hold the new line"
    ]
    assert w2_audit.apply_file([entry], "data/f.json", root) == 1
    assert w2_audit.check([entry], {"data/f.json"}, root) == []


def test_check_fails_a_lost_brace(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "{They} wait. Who knows?")
    rows = [Row(1, "thought", "Who knows?", "(cut)", "")]
    entry = Entry("data/f.json", ".a", "{They} wait. Who knows?", rows=rows)
    entry.new = "They wait."
    w2_audit.apply_file([entry], "data/f.json", root)
    assert w2_audit.check([entry], {"data/f.json"}, root) == ["data/f.json|.a: the braces changed"]


def test_check_holds_a_skipped_line_unchanged(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "Left for W3.")
    entry = Entry("data/f.json", ".a", "Left for W3.", disposition=SKIP, owner="W3")
    assert w2_audit.check([entry], {"data/f.json"}, root) == []
    (root / "data" / "f.json").write_text('{"a": "Changed."}\n', encoding="utf-8")
    assert w2_audit.check([entry], {"data/f.json"}, root) == [
        "data/f.json|.a: a skipped line changed"
    ]


def test_apply_takes_a_redraft(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "Old line.")
    entry = Entry("data/f.json", ".a", "Old line.", new="New line.", disposition=ADOPT)
    assert w2_audit.apply_file([entry], "data/f.json", root) == 1
    w2_audit.merge_drafts([entry], {entry.id: "Better line."})
    assert w2_audit.apply_file([entry], "data/f.json", root) == 1
    assert w2_audit.check([entry], {"data/f.json"}, root) == []
    assert w2_audit.apply_file([entry], "data/f.json", root) == 0


def test_residue_reports_an_excerpt_that_came_back(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "You wait. Who knows?")
    rows = [Row(1, "thought", "Who knows?", "(cut)", "")]
    entry = Entry("data/f.json", ".a", "You wait. Who knows?", new="You wait.", rows=rows)
    assert w2_audit.residue([entry], {"data/f.json"}, root) == [
        "data/f.json|.a: row 1's excerpt is back"
    ]
    w2_audit.apply_file([entry], "data/f.json", root)
    assert w2_audit.residue([entry], {"data/f.json"}, root) == []


def test_render_sets_each_line_beside_its_old_one() -> None:
    rows = [Row(3, "thought", "Who knows?", "(cut)", "edge: a note")]
    entry = Entry("data/f.json", ".a", "Old line.", new="New line.", disposition=ADOPT, rows=rows)
    entry.flags = ["EDGE"]
    text = w2_audit.render([entry])
    assert "## data/f.json" in text
    assert "EDGE, adopt" in text
    assert "- Row 3 (thought). Excerpt: Who knows? Suggestion: (cut) Note: edge: a note" in text
    assert text.index("> Old line.") < text.index("> New line.")


def test_merge_drafts_refuses_a_skipped_entry() -> None:
    entry = Entry("data/f.json", ".a", "Left.", disposition=SKIP, owner="W3")
    try:
        w2_audit.merge_drafts([entry], {entry.id: "New."})
    except ValueError as error:
        assert "skipped" in str(error)
    else:
        raise AssertionError("a skipped entry took a draft")
