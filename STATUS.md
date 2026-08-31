# Ralph Status

_Updated: 2026-08-31 08:37:13_

## STARVED

```
STARVED: 28 todo, 0 eligible.
  A2-8 is IN FLIGHT (in-progress (planning)) and nothing is running it
  SA-F2 (blocked) strands SA-F3, SA-F4, SA-F5, SA-F6, SA-F7, SA-X1, SA-X10, SA-X2, SA-X3, SA-X4, SA-X5, SA-X6, SA-X7, SA-X8, SA-X9
```

## STRANDED

Sprints below are marked started and unfinished, and nothing is running them. This page used to render exactly this state as a calm, green, permanently-final summary reading `todo: 0, eligible: 0` -- because a sprint at `in-progress` counted as neither todo nor eligible nor blocked, so it counted as nothing at all, and the supervisor read that as completion and stopped for the week.

```
STRANDED: 1 sprint(s) started and unfinished, 0 eligible. This is NOT completion.
  A2-8 is IN FLIGHT (in-progress (planning)) and nothing is running it
  A run was killed or stopped mid-sprint. Stuck-sprint recovery resets these to todo once they have gone untouched for IN_PROGRESS_STALE_MINUTES, so the next harness launch reclaims them; nothing further happens until then.
```

## Now

- Sprint: **(between sprints)**
- Phase: **-**
- Last beat: **12 seconds ago**
- Beat PID: 46472 -- alive

## Queue

- total: 88
- todo: 28
- eligible: 0
- in flight: A2-8 (in-progress (planning))
- blocked: SA-F2, UI-BOUNDS-1

## Push

- last push: **OK** (55 minutes ago)
- last successful push: 55 minutes ago

## Blocks drift

- 19 disagreement(s) between `Blocks:` and `Depends on:` (cross-check only -- does not affect scheduling)
- CB-2: Blocks names unknown sprint "SA-X6 (which authors anchor-specific lines using CB-2's extended infrastructure)"
- SA-B-EXT-1: Blocks claims SA-B3, but SA-B3 does not list SA-B-EXT-1 in Depends on
- SA-B-EXT-1: Blocks claims SA-B4, but SA-B4 does not list SA-B-EXT-1 in Depends on
- SA-F3: Blocks claims SA-F4, but SA-F4 does not list SA-F3 in Depends on
- SA-F3: Blocks claims SA-F7, but SA-F7 does not list SA-F3 in Depends on
- (+14 more)
