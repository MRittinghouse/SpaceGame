# Ralph Status

_Updated: 2026-08-31 21:49:37_

## Harness Did Not Run

harness exited with code 4 (a pre-flight check failed before the main loop started) without writing STATUS.md. This happens on two paths, both before the harness's main loop starts: a pre-flight check failure, or a lock already held by another instance. Exit code 2 means the latter (normal, not reported); this one means a pre-flight check failed. The pre-flight message itself is in `ralph/logs/harness.log` (the harness's stdout, captured by the supervisor); the supervisor's own account of the run is in `ralph/logs/supervisor.log`. Failing that, run `python -m ralph.harness` by hand.

## NO LIVE HARNESS

The heartbeat names a process that is not running (or is no longer the ralph harness). Beat age alone cannot see this: a heartbeat file outlives the process that wrote it, so a machine that rebooted two minutes ago leaves a two-minute-old beat that reads as perfectly healthy.

## Now

- Sprint: **(between sprints)**
- Phase: **-**
- Last beat: **3 minutes ago**
- Beat PID: 21844 -- **NOT RUNNING**

## Queue

- total: 88
- todo: 25
- eligible: 9
- in flight: none
- blocked: SA-F2, UI-BOUNDS-1

## Push

- last push: **OK** (3 minutes ago)
- last successful push: 3 minutes ago

## Blocks drift

- 19 disagreement(s) between `Blocks:` and `Depends on:` (cross-check only -- does not affect scheduling)
- CB-2: Blocks names unknown sprint "SA-X6 (which authors anchor-specific lines using CB-2's extended infrastructure)"
- SA-B-EXT-1: Blocks claims SA-B3, but SA-B3 does not list SA-B-EXT-1 in Depends on
- SA-B-EXT-1: Blocks claims SA-B4, but SA-B4 does not list SA-B-EXT-1 in Depends on
- SA-F3: Blocks claims SA-F4, but SA-F4 does not list SA-F3 in Depends on
- SA-F3: Blocks claims SA-F7, but SA-F7 does not list SA-F3 in Depends on
- (+14 more)

## Recent

- harness exit rc=1
