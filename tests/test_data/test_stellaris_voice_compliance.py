"""SA-B3: Writing Bible scan over Stellaris auction content.

Scans:
* ``data/auctions/stellaris_lots.json`` headlines + descriptions
* ``data/auctions/stellaris_voices.json`` every template string
* Cassian Velo's dialogue tree (``cassian_velo_main``) every node text
* The new ``auto_auction_first_velo_encounter`` journal entry

Rules enforced (per ``requirements/dialogue_writing_guide.md`` and the
project Writing Bible scanner):
* No em-dashes (``—`` / ``–`` / ``" -- "``)
* No "couldn't help but"
* No "a testament to"
* No parallel-negation rhetoric ("no X, no Y")
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from spacegame.config import PROJECT_ROOT
from spacegame.data_loader import get_data_loader

_EM_DASH = "—"
_EM_DASHES = {_EM_DASH, "–", " -- "}
_BANNED_PHRASES = ["couldn't help but", "a testament to"]
_PARALLEL_NEGATION = re.compile(r"\bno \w+,\s*no \w+", re.IGNORECASE)


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


class TestStellarisLotCatalogVoice:
    def test_no_violations(self) -> None:
        path = Path(PROJECT_ROOT) / "data" / "auctions" / "stellaris_lots.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        report: list[str] = []
        for entry in data["lots"]:
            for field_name in ("headline", "description"):
                violations = _violations(entry.get(field_name, ""))
                for v in violations:
                    report.append(f"lot {entry['id']}.{field_name}: {v}")
        assert not report, "Lot catalog Writing Bible violations:\n" + "\n".join(report)


class TestStellarisVoicesContent:
    def test_no_violations(self) -> None:
        path = Path(PROJECT_ROOT) / "data" / "auctions" / "stellaris_voices.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        report: list[str] = []

        def _scan(value: object, breadcrumb: str) -> None:
            if isinstance(value, str):
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
        assert not report, "Voice file Writing Bible violations:\n" + "\n".join(report)


class TestCassianVeloDialogueVoice:
    def test_no_violations(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("cassian_velo_main")
        assert tree is not None, "Velo dialogue tree must be registered"
        report: list[str] = []
        for node_id, node in tree.nodes.items():
            for v in _violations(node.text):
                report.append(f"velo node {node_id}.text: {v}")
            for i, response in enumerate(node.responses):
                for v in _violations(response.text):
                    report.append(f"velo node {node_id}.response[{i}]: {v}")
        assert not report, "Velo dialogue Writing Bible violations:\n" + "\n".join(report)


class TestVeloJournalEntryVoice:
    def test_no_violations(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        target = next(
            (e for e in dl.journal_entries if e.entry_id == "auto_auction_first_velo_encounter"),
            None,
        )
        assert target is not None, "Velo journal entry must be present"
        violations = _violations(target.text)
        assert not violations, f"Velo journal entry violations: {violations}"


class TestVeloDialogueIntegrity:
    def test_velo_branches_resolve(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("cassian_velo_main")
        assert tree is not None
        # Start node + at least 4 explicit branches (preview / rivals /
        # history / exit).
        assert tree.start_node_id == "greet"
        greet = tree.nodes["greet"]
        assert len(greet.responses) >= 4
        # Every next_node_id must resolve.
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.next_node_id:
                    assert resp.next_node_id in tree.nodes, (
                        f"Velo dialogue references unknown node {resp.next_node_id}"
                    )

    def test_first_velo_encounter_flag_set_on_first_branch(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("cassian_velo_main")
        assert tree is not None
        greet = tree.nodes["greet"]
        # All response branches set the flag (one-shot regardless of which
        # branch the player picks first).
        flag_set_responses = [
            r for r in greet.responses if r.set_flag == "seen_first_velo_encounter"
        ]
        assert flag_set_responses, "At least one greet response must set seen_first_velo_encounter"
