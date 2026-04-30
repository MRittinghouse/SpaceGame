"""Tests for ralph.agents.

Covers:
  - Sentinel detection from Activity log
  - Prompt building / template substitution
  - Outcome decisions: OK / BLOCKED / NEEDS_REWORK / ERROR
  - PHASE_ALLOWS_NEW_SPRINTS membership
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ralph import agents, roadmap_state
from ralph.agents import Outcome, Phase, _PHASE_ALLOWS_NEW_SPRINTS


_ROADMAP_WITH_SENTINEL = """\
# Test

### SA-1 — First sprint

**Status**: in-progress
**Depends on**: none

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 14:00 — implementation complete. PHASE_OK
"""

_ROADMAP_WITH_BLOCKED = """\
# Test

### SA-1 — First

**Status**: in-progress
**Depends on**: none

**Activity log.**
- 2026-04-26 — todo
- 2026-04-26 14:00 — PHASE_BLOCKED: missing infrastructure
"""

_ROADMAP_WITH_REWORK = """\
# Test

### SA-1 — First

**Status**: in-progress
**Depends on**: none

**Activity log.**
- 2026-04-26 — todo
- 2026-04-26 14:00 — review complete. PHASE_NEEDS_REWORK: tests insufficient
"""

_ROADMAP_NO_SENTINEL = """\
# Test

### SA-1 — First

**Status**: in-progress
**Depends on**: none

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 14:00 — agent didn't write a sentinel
"""

_ROADMAP_MULTIPLE_SENTINELS = """\
# Test

### SA-1 — First

**Status**: in-progress
**Depends on**: none

**Activity log.**
- 2026-04-26 — todo
- 2026-04-26 14:00 — first attempt PHASE_OK (but rolled back later)
- 2026-04-26 14:30 — PHASE_NEEDS_REWORK: actually no, more work needed
"""


@pytest.fixture
def roadmap_factory(tmp_path, monkeypatch):
    """Factory: write controlled content to a temp ROADMAP.md.

    Patches ROADMAP_PATH on both `roadmap_state` and `agents` because each
    module imports the path from config at module-load time.
    """

    def _make(content: str):
        roadmap_file = tmp_path / "ROADMAP.md"
        roadmap_file.write_text(content, encoding="utf-8")
        monkeypatch.setattr(roadmap_state, "ROADMAP_PATH", roadmap_file)
        monkeypatch.setattr(agents, "ROADMAP_PATH", roadmap_file)
        return roadmap_file

    return _make


# ---------------------------------------------------------------------------
# Sentinel detection
# ---------------------------------------------------------------------------


class TestDetectOutcome:
    def test_phase_ok_detected(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_WITH_SENTINEL)
        outcome, reason = agents._detect_outcome("SA-1", returncode=0)
        assert outcome == Outcome.OK

    def test_phase_blocked_detected_with_reason(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_WITH_BLOCKED)
        outcome, reason = agents._detect_outcome("SA-1", returncode=0)
        assert outcome == Outcome.BLOCKED
        assert "missing infrastructure" in reason

    def test_phase_needs_rework_detected(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_WITH_REWORK)
        outcome, reason = agents._detect_outcome("SA-1", returncode=0)
        assert outcome == Outcome.NEEDS_REWORK
        assert "tests insufficient" in reason

    def test_no_sentinel_returns_error(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        outcome, reason = agents._detect_outcome("SA-1", returncode=0)
        assert outcome == Outcome.ERROR
        assert "no sentinel" in reason

    def test_no_sentinel_with_returncode_error(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        outcome, reason = agents._detect_outcome("SA-1", returncode=1)
        assert outcome == Outcome.ERROR
        assert "returncode 1" in reason

    def test_last_sentinel_wins(self, roadmap_factory) -> None:
        """When multiple sentinels appear, the last one is the agent's final
        decision (e.g., reviewer finds an issue after initially passing)."""
        roadmap_factory(_ROADMAP_MULTIPLE_SENTINELS)
        outcome, reason = agents._detect_outcome("SA-1", returncode=0)
        assert outcome == Outcome.NEEDS_REWORK


class TestStdoutFallback:
    """When ROADMAP.md has no sentinel, fall back to scanning agent stdout.

    Only BLOCKED and NEEDS_REWORK are honored from stdout. PHASE_OK in
    stdout is treated as ERROR — the agent claimed success without
    persisting the work to ROADMAP.md, which is a protocol violation.
    """

    def test_stdout_blocked_honored(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        stdout = (
            "I'll plan SA-1.\n"
            "I notice the prerequisite doc is missing.\n"
            "PHASE_BLOCKED: missing context — requirements/foo.md\n"
        )
        outcome, reason = agents._detect_outcome("SA-1", returncode=0, stdout=stdout)
        assert outcome == Outcome.BLOCKED
        assert "missing context" in reason
        assert "stdout fallback" in reason

    def test_stdout_needs_rework_honored(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        stdout = "Reviewing.\nPHASE_NEEDS_REWORK: tests don't cover the new path\n"
        outcome, reason = agents._detect_outcome("SA-1", returncode=0, stdout=stdout)
        assert outcome == Outcome.NEEDS_REWORK
        assert "tests don't cover" in reason
        assert "stdout fallback" in reason

    def test_stdout_ok_not_honored(self, roadmap_factory) -> None:
        """PHASE_OK in stdout without ROADMAP write is a protocol violation,
        not a success. The agent must persist work for OK to count."""
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        stdout = "All done.\nPHASE_OK\n"
        outcome, reason = agents._detect_outcome("SA-1", returncode=0, stdout=stdout)
        assert outcome == Outcome.ERROR
        assert "no sentinel" in reason

    def test_roadmap_sentinel_takes_precedence(self, roadmap_factory) -> None:
        """If ROADMAP has a sentinel, stdout is ignored — canonical wins."""
        roadmap_factory(_ROADMAP_WITH_BLOCKED)
        stdout = "PHASE_NEEDS_REWORK: nope\n"  # contradictory stdout
        outcome, _reason = agents._detect_outcome("SA-1", returncode=0, stdout=stdout)
        assert outcome == Outcome.BLOCKED  # roadmap wins


class TestNoSentinelDiagnostic:
    """The error reason for no-sentinel should be specific and actionable."""

    def test_includes_returncode_when_nonzero(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        _outcome, reason = agents._detect_outcome("SA-1", returncode=137)
        assert "returncode 137" in reason

    def test_flags_permission_keyword_in_stdout(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        stdout = "I tried to use Write but got: Permission denied at the sandbox level."
        _outcome, reason = agents._detect_outcome("SA-1", returncode=0, stdout=stdout)
        assert "permission-denial signal" in reason
        assert "dangerously-skip-permissions" in reason

    def test_flags_empty_stdout(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        _outcome, reason = agents._detect_outcome("SA-1", returncode=0, stdout="")
        assert "empty" in reason

    def test_flags_short_stdout(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        stdout = "early bail\n"
        _outcome, reason = agents._detect_outcome("SA-1", returncode=0, stdout=stdout)
        assert "short" in reason


class TestInfraErrorDetection:
    """`_looks_like_infra_error` distinguishes CLI/network/auth failures
    (transient, re-runnable) from agent disobedience or scope failures
    (terminal, needs human review).
    """

    def test_clean_exit_is_not_infra(self) -> None:
        # Returncode 0 means the agent finished cleanly. Even with infra
        # patterns in stdout, this isn't an infra error.
        stdout = "API Error: socket connection was closed unexpectedly"
        assert not agents._looks_like_infra_error(returncode=0, stdout=stdout)

    def test_empty_stdout_is_not_infra(self) -> None:
        # No positive signal — leave as ERROR.
        assert not agents._looks_like_infra_error(returncode=1, stdout="")

    def test_long_stdout_is_not_infra(self) -> None:
        # Agent ran meaningfully before failing — that's a sprint problem.
        long_stdout = "x" * (agents._INFRA_ERROR_STDOUT_THRESHOLD + 100)
        long_stdout += "\nAPI Error: connection closed unexpectedly"
        assert not agents._looks_like_infra_error(returncode=1, stdout=long_stdout)

    def test_socket_error_short_stdout_is_infra(self) -> None:
        # The exact SA-F2 scenario.
        stdout = "API Error: The socket connection was closed unexpectedly."
        assert agents._looks_like_infra_error(returncode=1, stdout=stdout)

    def test_auth_403_is_infra(self) -> None:
        # The exact UI-BOUNDS-1 scenario.
        stdout = (
            "Failed to authenticate. API Error: 403 "
            '{"error":"Account is no longer a member of the organization"}'
        )
        assert agents._looks_like_infra_error(returncode=1, stdout=stdout)

    def test_rate_limit_is_infra(self) -> None:
        stdout = "Error: rate limit exceeded; please retry"
        assert agents._looks_like_infra_error(returncode=1, stdout=stdout)

    def test_generic_failure_is_not_infra(self) -> None:
        # No infra pattern matches — even with non-zero returncode and
        # short stdout, this is a regular ERROR.
        stdout = "TypeError: object is not subscriptable"
        assert not agents._looks_like_infra_error(returncode=1, stdout=stdout)

    def test_detect_outcome_returns_infra_error(self, roadmap_factory) -> None:
        roadmap_factory(_ROADMAP_NO_SENTINEL)
        stdout = "API Error: socket connection was closed unexpectedly"
        outcome, reason = agents._detect_outcome("SA-1", returncode=1, stdout=stdout)
        assert outcome == Outcome.INFRA_ERROR
        # Reason still describes the diagnostic; just the classification flips.
        assert "no sentinel" in reason


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def test_substitutes_sprint_id(self) -> None:
        for phase in (Phase.PLAN, Phase.IMPLEMENT, Phase.REVIEW):
            prompt = agents._build_prompt(phase, "SA-1")
            assert "{SPRINT_ID}" not in prompt
            assert "SA-1" in prompt

    def test_substitutes_doc_paths(self) -> None:
        prompt = agents._build_prompt(Phase.PLAN, "SA-1")
        assert "{ROADMAP_PATH}" not in prompt
        assert "{CONVENTIONS_PATH}" not in prompt
        assert "{AGENT_GUIDE_PATH}" not in prompt
        # Path strings should appear in the rendered prompt.
        assert "ROADMAP.md" in prompt or "roadmap" in prompt.lower()

    def test_each_phase_has_distinct_prompt(self) -> None:
        plan_prompt = agents._build_prompt(Phase.PLAN, "SA-1")
        impl_prompt = agents._build_prompt(Phase.IMPLEMENT, "SA-1")
        review_prompt = agents._build_prompt(Phase.REVIEW, "SA-1")
        # Each role should appear in its own prompt only.
        assert "PLANNING agent" in plan_prompt
        assert "IMPLEMENTATION agent" in impl_prompt
        assert "REVIEW agent" in review_prompt
        assert "PLANNING agent" not in impl_prompt
        assert "PLANNING agent" not in review_prompt


# ---------------------------------------------------------------------------
# Phase membership constants
# ---------------------------------------------------------------------------


class TestPhaseAllowsNewSprints:
    def test_plan_can_add_sprints(self) -> None:
        assert Phase.PLAN in _PHASE_ALLOWS_NEW_SPRINTS

    def test_review_can_add_sprints(self) -> None:
        assert Phase.REVIEW in _PHASE_ALLOWS_NEW_SPRINTS

    def test_implement_cannot_add_sprints(self) -> None:
        assert Phase.IMPLEMENT not in _PHASE_ALLOWS_NEW_SPRINTS


# ---------------------------------------------------------------------------
# Model selection (agency upgrade)
# ---------------------------------------------------------------------------


class TestModelForPhase:
    def test_plan_uses_opus(self) -> None:
        from ralph.config import model_for_phase, MODEL_PLAN

        assert model_for_phase("plan") == MODEL_PLAN
        assert "opus" in MODEL_PLAN.lower()

    def test_review_uses_sonnet(self) -> None:
        from ralph.config import model_for_phase, MODEL_REVIEW

        assert model_for_phase("review") == MODEL_REVIEW
        assert "sonnet" in MODEL_REVIEW.lower()

    def test_implement_small_uses_default(self) -> None:
        from ralph.config import model_for_phase, MODEL_IMPLEMENT_DEFAULT

        assert model_for_phase("implement", "S") == MODEL_IMPLEMENT_DEFAULT
        assert model_for_phase("implement", "M") == MODEL_IMPLEMENT_DEFAULT

    def test_implement_large_uses_heavy(self) -> None:
        from ralph.config import model_for_phase, MODEL_IMPLEMENT_HEAVY

        assert model_for_phase("implement", "L") == MODEL_IMPLEMENT_HEAVY
        assert model_for_phase("implement", "XL") == MODEL_IMPLEMENT_HEAVY

    def test_implement_unknown_size_uses_default(self) -> None:
        from ralph.config import model_for_phase, MODEL_IMPLEMENT_DEFAULT

        assert model_for_phase("implement", "") == MODEL_IMPLEMENT_DEFAULT
        assert model_for_phase("implement", "?") == MODEL_IMPLEMENT_DEFAULT

    def test_size_is_case_insensitive(self) -> None:
        from ralph.config import model_for_phase, MODEL_IMPLEMENT_HEAVY

        assert model_for_phase("implement", "l") == MODEL_IMPLEMENT_HEAVY
        assert model_for_phase("implement", "xl") == MODEL_IMPLEMENT_HEAVY

    def test_phase_is_case_insensitive(self) -> None:
        from ralph.config import model_for_phase, MODEL_PLAN

        assert model_for_phase("PLAN") == MODEL_PLAN
        assert model_for_phase("Plan") == MODEL_PLAN


class TestTimeoutForPhase:
    def test_implement_longer_than_plan_or_review(self) -> None:
        from ralph.config import timeout_for_phase

        assert timeout_for_phase("implement") >= timeout_for_phase("plan")
        assert timeout_for_phase("implement") >= timeout_for_phase("review")

    def test_each_phase_has_positive_timeout(self) -> None:
        from ralph.config import timeout_for_phase

        for phase in ("plan", "implement", "review"):
            assert timeout_for_phase(phase) > 0

    def test_unknown_phase_falls_back(self) -> None:
        from ralph.config import timeout_for_phase, PHASE_TIMEOUT_SECONDS

        assert timeout_for_phase("nonsense") == PHASE_TIMEOUT_SECONDS


class TestBuildClaudeCmd:
    def test_includes_model_flag(self) -> None:
        from ralph.config import build_claude_cmd

        cmd = build_claude_cmd("plan")
        assert "--model" in cmd
        # The model arg follows --model.
        idx = cmd.index("--model")
        assert idx + 1 < len(cmd)
        assert cmd[idx + 1].startswith("claude-")

    def test_includes_dangerously_skip_permissions(self) -> None:
        from ralph.config import build_claude_cmd

        cmd = build_claude_cmd("plan")
        assert "--dangerously-skip-permissions" in cmd

    def test_implement_heavy_size_picks_heavy_model(self) -> None:
        from ralph.config import build_claude_cmd, MODEL_IMPLEMENT_HEAVY

        cmd = build_claude_cmd("implement", "L")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == MODEL_IMPLEMENT_HEAVY

    def test_implement_small_size_picks_default_model(self) -> None:
        from ralph.config import build_claude_cmd, MODEL_IMPLEMENT_DEFAULT

        cmd = build_claude_cmd("implement", "S")
        idx = cmd.index("--model")
        assert cmd[idx + 1] == MODEL_IMPLEMENT_DEFAULT
