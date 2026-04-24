"""One-off cleanup: replace em/en-dashes and ` -- ` in encounter JSON.

Each occurrence becomes a sentence break (`.`) followed by a space and
capitalized next word. Skips strings with no offenders for speed.

Run from project root:
    python scripts/fix_encounter_dashes.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DASHES = ["\u2014", "\u2013", " -- "]
# Capture the dash variant + the next non-space char so we can capitalize.
_DASH_RE = re.compile(r"(\u2014|\u2013|\s--\s)\s*([a-zA-Z])")


def _replace(match: re.Match[str]) -> str:
    next_char = match.group(2)
    return f". {next_char.upper()}"


def _clean_text(text: str) -> str:
    if not any(d in text for d in DASHES):
        return text
    cleaned = _DASH_RE.sub(_replace, text)
    # Catch trailing dashes with no following letter (rare): collapse to "."
    for d in DASHES:
        cleaned = cleaned.replace(d, ".")
    # Tidy double-period that may sneak in
    cleaned = re.sub(r"\.\s*\.", ".", cleaned)
    return cleaned


def _walk(obj):
    if isinstance(obj, str):
        return _clean_text(obj)
    if isinstance(obj, list):
        return [_walk(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _walk(v) for k, v in obj.items()}
    return obj


def main() -> int:
    enc_dir = Path(__file__).parent.parent / "data" / "encounters"
    if not enc_dir.exists():
        print(f"Encounters dir not found: {enc_dir}", file=sys.stderr)
        return 1
    changed_files = 0
    for path in sorted(enc_dir.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        cleaned = _walk(data)
        new_text = json.dumps(cleaned, indent=2, ensure_ascii=False)
        if new_text + "\n" != text and new_text != text:
            path.write_text(new_text + "\n", encoding="utf-8")
            changed_files += 1
            print(f"updated: {path.name}")
    print(f"\nTotal files updated: {changed_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
