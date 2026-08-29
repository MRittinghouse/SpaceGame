# Ralph Status

_Updated: 2026-08-29 10:17:02_

## Harness Did Not Run

Baseline capture FAILED: pytest exited 1; tail: s\SpaceGame\tests\test_engine\test_display_flags.py:67: Warning: no fast renderer available
    surf = pygame.display.set_mode((1280, 720), flags=flags)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_compliance/test_roadmap_index_sync.py::TestRoadmapIndexInSync::test_index_status_matches_sections
1 failed, 11036 passed, 100 skipped, 41 warnings in 1248.79s (0:20:48). Aborting run to avoid running agents with no baseline.

## Now

- Sprint: **(between sprints)**
- Phase: **-**
- Last beat: **just now**
- Beat PID: 41216 -- alive

## Queue

- total: 88
- todo: 34
- eligible: 4
- in flight: none
- blocked: SA-F2, UI-BOUNDS-1

## Push

- last push: **OK** (7 hours ago)
- last successful push: 7 hours ago

## Blocks drift

- 19 disagreement(s) between `Blocks:` and `Depends on:` (cross-check only -- does not affect scheduling)
- CB-2: Blocks names unknown sprint "SA-X6 (which authors anchor-specific lines using CB-2's extended infrastructure)"
- SA-B-EXT-1: Blocks claims SA-B3, but SA-B3 does not list SA-B-EXT-1 in Depends on
- SA-B-EXT-1: Blocks claims SA-B4, but SA-B4 does not list SA-B-EXT-1 in Depends on
- SA-F3: Blocks claims SA-F4, but SA-F4 does not list SA-F3 in Depends on
- SA-F3: Blocks claims SA-F7, but SA-F7 does not list SA-F3 in Depends on
- (+14 more)
