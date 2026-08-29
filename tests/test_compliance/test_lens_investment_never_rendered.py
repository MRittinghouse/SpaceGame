"""Structural invariant guard: raw lens investment must not reach the UI.

Sprint A2-4, AC4. Spec F telegraphs *behaviour* (an NPC line change, an
offered contract shift) rather than *numbers* (a meter, a percentage, a
raw counter). Enforcing this behaviourally alone is porous — a future
developer could quietly wire ``player.lens_investment.get_investment(...)``
into a HUD label and no unit test would catch it. The invariant is
enforced structurally instead: no file under ``spacegame/views/`` or
``spacegame/engine/`` may import :class:`LensInvestment` or reach into
``player.lens_investment``.

Legitimate readers live in the model layer (dilemma engine, telegraph,
oblique NPC-address / offered-work reactor). If a view or engine module
ever needs to *read* investment — for example to render a completed
capstone celebration in A2-10 — that sprint must first extend the
allowlist below with a narrow entry and justify the reader in a code
comment. The friction of touching this file is deliberate.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPACEGAME_ROOT = REPO_ROOT / "spacegame"

# Forbidden tokens: any of these appearing in a scanned .py file is a
# violation. The scan is deliberately blunt — a rendered value is *any*
# access at all.
_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "LensInvestment",
    "lens_investment",
    "from spacegame.models.lens_investment",
)

# Allowlist. Format: ``str(rel_path)`` (POSIX-style). Empty by design;
# populate only with strong rationale.
_ALLOWLIST: set[str] = set()


def _iter_python_files(root: Path) -> list[Path]:
    """Return every ``.py`` file under ``root``, skipping caches."""
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts and p.suffix == ".py"]


def _scan(root: Path) -> list[tuple[str, int, str, str]]:
    """Return ``(rel_path, line_no, token, line_text)`` for every hit."""
    hits: list[tuple[str, int, str, str]] = []
    for path in _iter_python_files(root):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in _ALLOWLIST:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for token in _FORBIDDEN_TOKENS:
                if token in line:
                    hits.append((rel, lineno, token, line.strip()))
                    break
    return hits


class TestLensInvestmentNeverRendered:
    def test_no_view_imports_lens_investment(self) -> None:
        """Scan ``spacegame/views/`` for any reference to LensInvestment."""
        views_root = SPACEGAME_ROOT / "views"
        hits = _scan(views_root)
        assert not hits, (
            "spacegame/views/ must not reference LensInvestment. "
            "A2-4 AC4 forbids raw investment numbers in the UI; the invariant "
            "is telegraph via behaviour, never via meters. Offending lines:\n"
            + "\n".join(f"  {rel}:{lineno} [{token}] {line}" for rel, lineno, token, line in hits)
        )

    def test_no_engine_module_imports_lens_investment(self) -> None:
        """Scan ``spacegame/engine/`` for any reference to LensInvestment."""
        engine_root = SPACEGAME_ROOT / "engine"
        hits = _scan(engine_root)
        assert not hits, (
            "spacegame/engine/ must not reference LensInvestment. "
            "A2-4 AC4 forbids raw investment numbers in the UI; the engine "
            "belongs to the render path. Offending lines:\n"
            + "\n".join(f"  {rel}:{lineno} [{token}] {line}" for rel, lineno, token, line in hits)
        )

    def test_forbidden_tokens_are_findable_in_the_model_layer(self) -> None:
        """Guardrail: the scan is not vacuously green.

        If ``LensInvestment`` were ever renamed or removed, the two scans
        above would still pass — an empty search of the codebase is 'no
        hits'. This test proves the token exists somewhere it is *supposed*
        to exist: ``spacegame/models/lens_investment.py``. If this test
        fails, the model itself has moved or been renamed, and the
        invariant scans above are stale.
        """
        model_file = SPACEGAME_ROOT / "models" / "lens_investment.py"
        assert model_file.exists(), (
            f"Expected {model_file} to exist. If the model moved, update "
            f"the scanner in {Path(__file__).name}."
        )
        text = model_file.read_text(encoding="utf-8")
        assert "class LensInvestment" in text, (
            "The LensInvestment class was not found in its canonical module. "
            "Either the class was renamed (update the forbidden-tokens list) "
            "or the model was moved (update this scanner)."
        )
