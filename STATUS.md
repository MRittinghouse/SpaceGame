# Ralph Status

_Updated: 2026-08-29 00:50:45_

## Harness Did Not Run

harness exited with code 1 (an exit code this supervisor does not recognise) and STATUS.md was NOT updated. This is NOT a pre-flight failure: that code is 4, and this is not it. The harness got as far as its own exit handler and tried to write STATUS.md; the WRITE failed -- a full or read-only disk, a permissions change on STATUS.md, or a rendering bug. `_write_status_snapshot` swallows that failure by design (a broken status file must never end a run it is only trying to report on), so the reason is a single line in `ralph/logs/harness.log`: search it for `STATUS.md write failed`. The run itself may well have been fine.

## NO LIVE HARNESS

The heartbeat names a process that is not running (or is no longer the ralph harness). Beat age alone cannot see this: a heartbeat file outlives the process that wrote it, so a machine that rebooted two minutes ago leaves a two-minute-old beat that reads as perfectly healthy.

## Now

- Sprint: **(between sprints)**
- Phase: **-**
- Last beat: **16 seconds ago**
- Beat PID: 43556 -- **NOT RUNNING**

## Queue

- total: 88
- todo: 33
- eligible: 2
- in flight: A2-5 (in-progress (implementing))
- blocked: A2-4, SA-F2, UI-BOUNDS-1

## Push

- last push: **OK** (15 seconds ago)
- last successful push: 15 seconds ago

## Blocks drift

- 19 disagreement(s) between `Blocks:` and `Depends on:` (cross-check only -- does not affect scheduling)
- CB-2: Blocks names unknown sprint "SA-X6 (which authors anchor-specific lines using CB-2's extended infrastructure)"
- SA-B-EXT-1: Blocks claims SA-B3, but SA-B3 does not list SA-B-EXT-1 in Depends on
- SA-B-EXT-1: Blocks claims SA-B4, but SA-B4 does not list SA-B-EXT-1 in Depends on
- SA-F3: Blocks claims SA-F4, but SA-F4 does not list SA-F3 in Depends on
- SA-F3: Blocks claims SA-F7, but SA-F7 does not list SA-F3 in Depends on
- (+14 more)

## Recent

- harness exit rc=0
- harness exit rc=0
- harness exit rc=3
