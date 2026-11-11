# Execution contract (runner, iteration 3)

Owner: `src/causalguard/runner.py`. Repairs R2-01..R2-04 of the Codex R2 review. Studies (S1/S2/S3, development,
fixture, confirmatory) all execute and read through this module.

## Ownership

- `Run(run_id, plan, resume=...)` takes an exclusive, non-blocking `flock` on
  `<runs_root>/.locks/<run_id>.owner.lock` before it inspects, recovers or creates anything.
- A second live opener gets `RunBusy` and touches nothing: no ledger line, no quarantine, no recovery. The test
  `test_second_opener_refused_and_live_temporary_not_quarantined` checks this.
- The kernel ties a `flock` to an open file description and releases it when the holder closes it, exits or dies.
  A crashed owner therefore never leaves a stale lock. The PID written into the lock file is diagnostic only and is
  never used as an identity.
- Ownership is released when `execute` returns, or by `close()`.

## Worker groups and supervisor death

- Each worker calls `setsid()` and holds a **shared** `flock` on `<run_id>.workers.lock` for its whole life.
- Each worker starts a watchdog process inside its own group. The watchdog blocks on a lifeline pipe whose only
  write end belongs to the supervisor.
- If the supervisor exits or is killed, including by SIGKILL of its whole process group, the kernel closes the write
  end. The watchdog then sends SIGKILL to the entire worker group: the worker, the watchdog itself and every
  descendant still in the group.
- Before recovery, a new owner must obtain the workers lock **exclusively**. It waits at most `WORKER_DRAIN_S = 30 s`
  and otherwise refuses with `RunBusy`. So an immediate resume never overlaps old computation.
- Startup race: if the supervisor dies before a worker is set up, the worker's lifeline is already at EOF. Its
  watchdog kills the group, and no payload is ever received.
- Out of scope: descendants that deliberately leave the group (their own `setsid`). Workers are never used to start
  such processes.
- Tests:
  - `test_hard_supervisor_group_kill_cleans_worker_group_and_resume_does_not_overlap` (noncooperating worker plus
    child; group SIGKILL; immediate resume; worker and child dead within 5 s);
  - `test_worker_started_after_supervisor_death_never_runs_work`;
  - `test_normal_end_leaves_no_watchdog_or_worker`.
- Mutation check: disabling the watchdog's kill makes the parent-death test fail. The 30 s drain refusal fires.

## Immutable attempts

- Attempt records are published no-clobber: write `NNN.json.tmp<pid>`, fsync, `link()` to `NNN.json`, then unlink
  the temporary and fsync the directory. `link()` fails if the name exists, so an existing attempt is never
  replaced (`RunCorruption`, original bytes untouched).
- Failed and superseded attempts are never deleted.
- A kill between publishing an attempt and appending its `attempt_end` line is reconciled by the next owner, which
  appends an explicit `attempt_end` with `reconciled: true` (the attempt file is authoritative).
- A stray temporary file from an interrupted publication is the only permitted attempt-level recovery. Its exact
  bytes go to `quarantine/` with a ledger event. Only the owning process does this, after ownership and after
  validation.

## Strict validation (resume and read time)

- `validate_plan` recomputes the plan digest, the config hash and every payload hash, and checks schema, run id and
  unique items. On resume the stored plan must also be canonically identical to the requested plan.
- `validate_attempt` applies to every attempt, superseded failures included. It checks:
  - the exact key set;
  - schema;
  - run, plan, source and payload identity;
  - item/directory key;
  - status in {ok, error, timeout, oom, worker_died};
  - numbering;
  - `supersedes == [1..n-1]`;
  - types.
  Read-side checks also forbid more than one ok attempt, or an attempt after an ok attempt.
- On resume, all of this runs **before** any recovery mutates storage. An inconsistent run fails closed with its
  torn ledger tail and stray temporaries left untouched (`test_wrong_identity_on_any_attempt_is_corruption_before_mutation`).
- Every iteration-2 (v2-layout) run directory passes these rules unchanged (v1-layout iteration-1 runs keep their strict legacy reader). No legacy-validation path was needed.

## Status

- `run_status` derives the run-level **execution** status from the latest stored attempt of every planned item:
  - `complete`: all ok;
  - `complete_with_failures`: all items terminal, some failed;
  - `incomplete`: some items have no attempt.
- The `end` event, the registry, the confirmatory access ledger and `load_run(...)["execution_status"]` all report
  this, with this invocation's own counts kept separately (`invocation`).
- A failed item stays failed after a no-op resume. The CLIs exit 0 only for `complete`.
- Execution status is not scientific completeness. Each analysis applies its study's completeness policy (S2:
  structured primary, required null and overall study; S1: the 24-query grid), and an `ok` attempt that lacks a
  planned cell is a missing outcome.

## Retries and phase

- `retry_failed` is a development-only facility. It is refused for fixture/confirmatory modes, because no
  confirmatory retry policy is frozen.
- Successful items are never re-run. S1 per-query timeouts and resource limits are scientific outcomes inside an
  ok item, not retry opportunities.
- `run_phase` derives `development` / `fixture` / `confirmatory` from the plan (freeze block plus declared phase) and
  every `start` event's mode. Contradictions are refused. Analyses label results and figures from it and refuse
  mixed-phase inputs.

## Shared ledgers

`registry.jsonl` and `access_ledger.jsonl` are shared by runs. Their torn-tail recovery and appends are serialized
by an exclusive lock on `<name>.lock` (`test_shared_registry_concurrent_writers_do_not_corrupt`: 4 processes × 300
appends, all intact).
