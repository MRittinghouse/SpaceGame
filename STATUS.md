# Ralph Status

_Updated: 2026-08-29 11:33:55_

## CRASH-LOOP

Supervisor stopped after repeated failures.
Reason: stopping: 3 consecutive failures
Nothing will resume until a human intervenes.

## NO LIVE HARNESS

The heartbeat names a process that is not running (or is no longer the ralph harness). Beat age alone cannot see this: a heartbeat file outlives the process that wrote it, so a machine that rebooted two minutes ago leaves a two-minute-old beat that reads as perfectly healthy.

## Now

- Sprint: **(between sprints)**
- Phase: **-**
- Last beat: **49 seconds ago**
- Beat PID: 19032 -- **NOT RUNNING**

## Queue

- total: 88
- todo: 34
- eligible: 4
- in flight: none
- blocked: SA-F2, UI-BOUNDS-1

## Push

- last push: **OK** (26 seconds ago)
- last successful push: 26 seconds ago

## Blocks drift

- 19 disagreement(s) between `Blocks:` and `Depends on:` (cross-check only -- does not affect scheduling)
- CB-2: Blocks names unknown sprint "SA-X6 (which authors anchor-specific lines using CB-2's extended infrastructure)"
- SA-B-EXT-1: Blocks claims SA-B3, but SA-B3 does not list SA-B-EXT-1 in Depends on
- SA-B-EXT-1: Blocks claims SA-B4, but SA-B4 does not list SA-B-EXT-1 in Depends on
- SA-F3: Blocks claims SA-F4, but SA-F4 does not list SA-F3 in Depends on
- SA-F3: Blocks claims SA-F7, but SA-F7 does not list SA-F3 in Depends on
- (+14 more)

## Recent

- harness exit rc=3
- harness exit rc=4
- harness exit rc=3
