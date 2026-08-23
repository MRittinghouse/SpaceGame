"""Compliance: the pre-commit hook must actually be installed locally.

Committing ``.pre-commit-config.yaml`` installs nothing. ``.git/hooks/`` is not
tracked by git, so every fresh clone starts with no gate at all until somebody
runs ``pre-commit install``.

This failed silently once already. QF-1 committed the config, and the planning
agent, the implementing agent, and a human diff review all concluded the gate
was live. It was not -- ``.git/hooks/pre-commit`` did not exist, and nothing was
enforced on any commit. The config being present is not evidence that the hook
runs.

A note in CLAUDE.md would not have caught that, because nobody was misinformed;
we simply never checked whether the thing was wired up. So the check lives here,
where the suite runs it constantly for every author: human, Claude, and the
ralph loop.

Skipped in CI, where the workflow invokes ruff and mypy directly and git hooks
are irrelevant, and skipped outside a git worktree (installed package, source
archive, vendored copy).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INSTALL_HINT = (
    "The pre-commit hook is not installed, so commits are ungated on this "
    "machine.\n"
    "Fix:  python -m pre_commit install\n"
    "See docs/superpowers/specs/2026-08-23-quality-foundation-design.md "
    "Section 2."
)


def _git_dir() -> Path | None:
    """Resolve the .git directory, tolerating worktrees where .git is a file.

    Returns None when this is not a git checkout at all.
    """
    dot_git = PROJECT_ROOT / ".git"
    if dot_git.is_dir():
        return dot_git
    if dot_git.is_file():
        # Linked worktree / submodule: ".git" is a file containing "gitdir: <path>".
        content = dot_git.read_text(encoding="utf-8").strip()
        prefix = "gitdir:"
        if content.startswith(prefix):
            target = Path(content[len(prefix) :].strip())
            if not target.is_absolute():
                target = (PROJECT_ROOT / target).resolve()
            return target if target.is_dir() else None
    return None


pytestmark = [
    pytest.mark.skipif(
        os.environ.get("CI") is not None,
        reason="CI runs ruff/mypy directly; git hooks are not used there.",
    ),
    pytest.mark.skipif(
        _git_dir() is None,
        reason="Not a git worktree; there is no hooks directory to check.",
    ),
]


class TestPreCommitHookInstalled:
    def test_hook_file_exists(self) -> None:
        """``pre-commit install`` must have been run in this clone."""
        git_dir = _git_dir()
        assert git_dir is not None  # guarded by pytestmark
        hook = git_dir / "hooks" / "pre-commit"
        assert hook.exists(), INSTALL_HINT

    def test_hook_is_the_precommit_framework(self) -> None:
        """Guard against a stale or hand-rolled hook masquerading as the gate.

        Git ships ``pre-commit.sample`` and some tooling writes its own hook.
        Either would satisfy an existence check while running none of our
        configured gates.
        """
        git_dir = _git_dir()
        assert git_dir is not None  # guarded by pytestmark
        hook = git_dir / "hooks" / "pre-commit"
        if not hook.exists():
            pytest.fail(INSTALL_HINT)

        text = hook.read_text(encoding="utf-8", errors="replace")
        assert "pre-commit" in text, (
            f"{hook} exists but does not look like the pre-commit framework's "
            f"hook, so the configured gates are not running.\n{INSTALL_HINT}"
        )

    def test_config_declares_the_expected_gates(self) -> None:
        """The config must still declare ruff, ruff-format, and the mypy ratchet.

        An installed hook running a gutted config is the same failure wearing a
        different hat.
        """
        config = PROJECT_ROOT / ".pre-commit-config.yaml"
        assert config.exists(), "`.pre-commit-config.yaml` is missing."

        text = config.read_text(encoding="utf-8")
        for expected in ("ruff", "ruff-format", "mypy"):
            assert expected in text, (
                f"`.pre-commit-config.yaml` no longer declares a {expected!r} "
                f"hook. The local gate has been weakened."
            )
