"""SA-B4: Writing Bible scan over Crimson Reach Black Market content.

Scans:
* ``data/auctions/crimson_reach_lots.json`` headlines + descriptions
* ``data/auctions/crimson_reach_voices.json`` every template string
* Vex Tarn's dialogue tree (``reach_floor_manager_main``) every node text
* The 3 new auction journal entries (first Reach session, first Floor
  Manager encounter, first contraband lesson)

Rules enforced (per ``requirements/dialogue_writing_guide.md`` and the
project Writing Bible scanner):
* No em-dashes (``—`` / ``–`` / ``" -- "``)
* No "couldn't help but"
* No "a testament to"
* No parallel-negation rhetoric ("no X, no Y") -- with the
  ReachDarkLayout faction tagline (``No laws. No mercy. No refunds.``)
  reused as a quoted faction tagline; that single allowlisted instance
  is documented in the layout module's tests.

Also enforces voice-distinctness against Velo: the Floor Manager's
``auctioneer_lines`` and dialogue tree must NOT use Velo's ceremonial
register (no "ladies and gentlemen", no "we are at", no "the lot is
open" templates). Average sentence length <= 10 words on the Floor
Manager surface (per locked decision §B4.5 / acceptance criterion #7).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from spacegame.config import PROJECT_ROOT
from spacegame.data_loader import get_data_loader

_EM_DASH = "—"
_EN_DASH = "–"
_EM_DASHES = {_EM_DASH, _EN_DASH, " -- "}
_BANNED_PHRASES = ["couldn't help but", "a testament to"]
_PARALLEL_NEGATION = re.compile(r"\bno \w+,\s*no \w+", re.IGNORECASE)

_REACH_BANNED_NPC_NAMES: tuple[str, ...] = (
    "yara",
    "elara",
    "kael",
    "mara",
    "lydia",
    "clive",
    "magnus",
    "ambrose",
)


def _violations(text: str) -> list[str]:
    out: list[str] = []
    if not text:
        return out
    for d in _EM_DASHES:
        if d in text:
            out.append(f"em-dash {d!r}")
            break
    lowered = text.lower()
    for phrase in _BANNED_PHRASES:
        if phrase in lowered:
            out.append(f"banned phrase {phrase!r}")
    if _PARALLEL_NEGATION.search(text):
        out.append("parallel-negation rhetoric")
    return out


def _split_sentences(text: str) -> list[str]:
    # Lightweight sentence split. Periods, question marks, exclamation
    # points serve as boundaries; trailing whitespace is ignored.
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _avg_words_per_sentence(text: str) -> float:
    sentences = _split_sentences(text)
    if not sentences:
        return 0.0
    total_words = sum(len(s.split()) for s in sentences)
    return total_words / len(sentences)


class TestReachLotCatalogVoice:
    def test_no_violations(self) -> None:
        path = Path(PROJECT_ROOT) / "data" / "auctions" / "crimson_reach_lots.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        report: list[str] = []
        for entry in data["lots"]:
            for field_name in ("headline", "description"):
                violations = _violations(entry.get(field_name, ""))
                for v in violations:
                    report.append(f"lot {entry['id']}.{field_name}: {v}")
        assert not report, "Reach lot catalog Writing Bible violations:\n" + "\n".join(report)

    def test_no_banned_npc_names(self) -> None:
        path = Path(PROJECT_ROOT) / "data" / "auctions" / "crimson_reach_lots.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        report: list[str] = []
        for entry in data["lots"]:
            for field_name in ("headline", "description"):
                lowered = entry.get(field_name, "").lower()
                for banned in _REACH_BANNED_NPC_NAMES:
                    if re.search(rf"\b{banned}\b", lowered):
                        report.append(f"lot {entry['id']}.{field_name}: banned NPC name {banned!r}")
        assert not report, "Reach lot catalog banned NPC names:\n" + "\n".join(report)


class TestReachVoicesContent:
    def test_no_violations(self) -> None:
        path = Path(PROJECT_ROOT) / "data" / "auctions" / "crimson_reach_voices.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        report: list[str] = []

        def _scan(value: object, breadcrumb: str) -> None:
            if isinstance(value, str):
                # `tier_locked` template intentionally reuses ReachDark
                # faction-floor copy; the parallel-negation check is fine
                # against it because the template is concrete copy, not
                # generative rhetoric. Direct violation check applies.
                for v in _violations(value):
                    report.append(f"{breadcrumb}: {v}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    _scan(item, f"{breadcrumb}[{i}]")
            elif isinstance(value, dict):
                for k, v in value.items():
                    if k.startswith("_"):  # Skip metadata keys.
                        continue
                    _scan(v, f"{breadcrumb}.{k}")

        for k, v in data.items():
            if k.startswith("_"):
                continue
            _scan(v, k)
        assert not report, "Reach voice file Writing Bible violations:\n" + "\n".join(report)


class TestFloorManagerDialogueVoice:
    def test_no_violations(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("reach_floor_manager_main")
        assert tree is not None, "Floor Manager dialogue tree must be registered"
        report: list[str] = []
        for node_id, node in tree.nodes.items():
            for v in _violations(node.text):
                report.append(f"vex node {node_id}.text: {v}")
            for i, response in enumerate(node.responses):
                for v in _violations(response.text):
                    report.append(f"vex node {node_id}.response[{i}]: {v}")
        assert not report, "Vex dialogue Writing Bible violations:\n" + "\n".join(report)


class TestReachJournalEntriesVoice:
    @pytest.mark.parametrize(
        "entry_id",
        [
            "auto_auction_first_reach_session",
            "auto_auction_first_floor_manager_encounter",
            "auto_auction_first_contraband_lesson",
        ],
    )
    def test_no_violations(self, entry_id: str) -> None:
        dl = get_data_loader()
        dl.load_all()
        target = next(
            (e for e in dl.journal_entries if e.entry_id == entry_id),
            None,
        )
        assert target is not None, f"Journal entry {entry_id} must be present"
        violations = _violations(target.text)
        assert not violations, f"{entry_id} violations: {violations}"


class TestFloorManagerDistinctFromVelo:
    """AC7: voice-register distinctness.

    Floor Manager templates and dialogue must not match Velo's
    ceremonial cadence on a few coarse static checks.
    """

    _CEREMONIAL_KEYWORDS = (
        "ladies and gentlemen",
        "we are at",
        "the lot is open",
        "the session is open",
        "the session is closed",
    )

    def _vex_text(self) -> list[str]:
        # Aggregate all Floor Manager copy: voice templates + dialogue.
        out: list[str] = []
        path = Path(PROJECT_ROOT) / "data" / "auctions" / "crimson_reach_voices.json"
        with open(path, "r", encoding="utf-8") as f:
            voices = json.load(f)
        auctioneer_lines = voices.get("auctioneer_lines", {})
        if isinstance(auctioneer_lines, dict):
            for v in auctioneer_lines.values():
                if isinstance(v, str):
                    out.append(v)
        empty_state = voices.get("empty_state")
        if isinstance(empty_state, str):
            out.append(empty_state)
        tier_locked = voices.get("tier_locked")
        if isinstance(tier_locked, str):
            out.append(tier_locked)
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("reach_floor_manager_main")
        if tree is not None:
            for node in tree.nodes.values():
                out.append(node.text)
                for response in node.responses:
                    out.append(response.text)
        return out

    def test_no_ceremonial_keywords(self) -> None:
        report: list[str] = []
        for line in self._vex_text():
            lowered = line.lower()
            for keyword in self._CEREMONIAL_KEYWORDS:
                if keyword in lowered:
                    report.append(f"ceremonial keyword {keyword!r} in: {line!r}")
        assert not report, (
            "Floor Manager content must not echo Velo's ceremonial register:\n" + "\n".join(report)
        )

    def test_average_sentence_length_short(self) -> None:
        # The Floor Manager register is terse and declarative. Average
        # sentence length across all aggregated text must be <= 10 words.
        text = " ".join(self._vex_text())
        avg = _avg_words_per_sentence(text)
        assert avg > 0, "Floor Manager content must be non-empty"
        assert avg <= 10.0, (
            f"Floor Manager average sentence length {avg:.1f} > 10.0; "
            "content drifting toward Velo's ceremonial cadence"
        )

    def test_no_velo_honorific_register(self) -> None:
        # Velo opens with honorific "we" / "we are at"; Vex never says
        # honorifics or third-person plural. Hard scan: forbidden tokens.
        forbidden_starts = ("ladies", "gentlemen", "we are at", "do we hear")
        report: list[str] = []
        for line in self._vex_text():
            lowered = line.lower()
            for tok in forbidden_starts:
                if tok in lowered:
                    report.append(f"forbidden token {tok!r} in: {line!r}")
        assert not report, "\n".join(report)


class TestFloorManagerDialogueIntegrity:
    def test_floor_manager_branches_resolve(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("reach_floor_manager_main")
        assert tree is not None
        # Start node + at least 4 explicit branches.
        greet = tree.get_start_node()
        assert greet is not None
        assert len(greet.responses) >= 4
        # Every next_node_id must resolve.
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.next_node_id:
                    assert resp.next_node_id in tree.nodes, (
                        f"Floor Manager dialogue references unknown node {resp.next_node_id}"
                    )

    def test_first_encounter_flag_set_on_greet_branches(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("reach_floor_manager_main")
        assert tree is not None
        greet = tree.get_start_node()
        assert greet is not None
        flag_set_responses = [
            r for r in greet.responses if r.set_flag == "seen_first_floor_manager_encounter"
        ]
        assert flag_set_responses, (
            "At least one greet response must set seen_first_floor_manager_encounter"
        )

    def test_npc_entry_registered(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        npc = dl.npcs.get("reach_floor_manager")
        assert npc is not None, "reach_floor_manager NPC must be registered"
        assert npc.dialogue_id == "reach_floor_manager_main"
        assert npc.home_system_id == "crimson_reach"
