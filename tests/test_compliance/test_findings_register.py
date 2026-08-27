"""Every finding in the register must carry a class and a disposition.

`requirements/findings_register.md` exists so observations can be routed by kind
instead of triaged one at a time. That only works if nothing sits in it without
a decision attached -- otherwise the register becomes the place findings go to
quietly rot, which is the failure it was created to prevent.

So the rule is enforced rather than documented: every open finding needs a
recognised class and a disposition (a sprint ID, a spec name, a `wontfix` with a
reason, or an explicit `needs decision`). A rule that cannot fail is a rule that
gets forgotten -- a lesson this project learned the expensive way when a
committed pre-commit config was mistaken for an installed hook.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTER = PROJECT_ROOT / "requirements" / "findings_register.md"

VALID_CLASSES = {
    "crash",
    "softlock",
    "affordance",
    "balance",
    "content",
    "hygiene",
    "infra",
}

# A disposition is meaningful if it names a sprint, a spec, or an explicit
# decision. Bare "TBD"/"TODO"/empty is exactly what this test rejects.
_DISPOSITION_OK = re.compile(
    r"(^[A-Z]{2,6}-[0-9A-Z]+)|(Spec [A-Z])|(wontfix)|(needs decision)|(track$)|(track\b)",
    re.IGNORECASE,
)

_ROW = re.compile(r"^\|\s*(F-\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|", re.MULTILINE)


def _open_findings() -> list[tuple[str, str, str]]:
    """Return (id, class, disposition) for each row in the Open findings table."""
    text = REGISTER.read_text(encoding="utf-8")
    start = text.index("## Open findings")
    end = text.index("## Closed findings")
    return [
        (m.group(1), m.group(2).strip(), m.group(5).strip()) for m in _ROW.finditer(text[start:end])
    ]


class TestFindingsRegister:
    def test_register_exists_and_has_rows(self) -> None:
        """Guard against the scan silently passing over an empty table."""
        assert REGISTER.exists(), f"{REGISTER} is missing."
        findings = _open_findings()
        assert findings, (
            "No open findings parsed. Either the table is empty or its shape "
            "changed and this scan is now checking nothing."
        )

    def test_every_finding_has_a_valid_class(self) -> None:
        bad = [(fid, cls) for fid, cls, _ in _open_findings() if cls not in VALID_CLASSES]
        assert not bad, (
            "Findings with an unrecognised class: "
            + ", ".join(f"{fid}={cls!r}" for fid, cls in bad)
            + f". Valid classes: {sorted(VALID_CLASSES)}. Add a new class to both "
            "the register's Classes table and VALID_CLASSES here if one is "
            "genuinely needed."
        )

    def test_every_finding_has_a_disposition(self) -> None:
        bad = [
            (fid, disp)
            for fid, _, disp in _open_findings()
            if not disp or not _DISPOSITION_OK.search(disp)
        ]
        assert not bad, (
            "Findings with no actionable disposition: "
            + ", ".join(f"{fid}={disp!r}" for fid, disp in bad)
            + ". Every finding needs a sprint ID, a spec name, `wontfix` with a "
            "reason, or `needs decision`. 'TBD' is not a disposition."
        )

    def test_ids_are_unique(self) -> None:
        ids = [fid for fid, _, _ in _open_findings()]
        dupes = {i for i in ids if ids.count(i) > 1}
        assert not dupes, f"Duplicate finding IDs: {sorted(dupes)}"
