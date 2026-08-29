# Ralph Status

_Updated: 2026-08-29 14:41:47_

## CRASH-LOOP

Supervisor stopped after repeated failures.
Reason: stopping: 3 consecutive failures
Nothing will resume until a human intervenes.

## NO LIVE HARNESS

The heartbeat names a process that is not running (or is no longer the ralph harness). Beat age alone cannot see this: a heartbeat file outlives the process that wrote it, so a machine that rebooted two minutes ago leaves a two-minute-old beat that reads as perfectly healthy.

## STALE HEARTBEAT

No beat in over 10 minutes (24 minutes ago) -- past the age at which the supervisor kills a harness as wedged. The process may have died, or the machine rebooted mid-sprint and left this file behind; its age alone does not mean a run is live.

## Now

- Sprint: **A2-6**
- Phase: **implement**
- Last beat: **24 minutes ago** -- **STALE**
- Beat PID: 38720 -- **NOT RUNNING**

## Queue

- total: 88
- todo: 32
- eligible: 2
- in flight: A2-5 (in-progress (reviewing)), A2-6 (in-progress (implementing))
- blocked: SA-F2, UI-BOUNDS-1

## Push

- last push: **OK** (just now)
- last successful push: just now

## Blocks drift

- 19 disagreement(s) between `Blocks:` and `Depends on:` (cross-check only -- does not affect scheduling)
- CB-2: Blocks names unknown sprint "SA-X6 (which authors anchor-specific lines using CB-2's extended infrastructure)"
- SA-B-EXT-1: Blocks claims SA-B3, but SA-B3 does not list SA-B-EXT-1 in Depends on
- SA-B-EXT-1: Blocks claims SA-B4, but SA-B4 does not list SA-B-EXT-1 in Depends on
- SA-F3: Blocks claims SA-F4, but SA-F4 does not list SA-F3 in Depends on
- SA-F3: Blocks claims SA-F7, but SA-F7 does not list SA-F3 in Depends on
- (+14 more)

## Recent

- harness exit rc=4
- harness exit rc=4
- harness exit rc=4
