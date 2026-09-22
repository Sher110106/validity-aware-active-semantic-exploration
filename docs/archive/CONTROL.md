# CONTROL

## Status contract

- Implementation plan: `PLAN.md`
- Attempt log: `ATTEMPTS.md`
- Durable notes: `NOTES.md`
- Runtime status after deployment: `runs/matrix_supervisor/status.json` on tyrone
- Runtime event log: `runs/matrix_supervisor/events.jsonl` on tyrone

## Priorities

- Primary: resource safety and evidence preservation
- Secondary: unattended throughput

## Scope

- Allowed: `tools/matrix_supervisor/**`, supervisor documentation, user-level service files, and supervisor runtime state.
- Protected: pinned author checkout, existing run artifacts, credentials, unrelated local changes.

## Resource policy

- One GPU experiment at a time.
- 60-second checks.
- 25 GB free-disk launch floor.
- 120 m path target.
- 3,000 calls for future runs.
- One automatic retry after an initial failure.
- Ambiguous 30-minute stalls pause for review without killing.

## Approval gates

Explicit approval is required for pinned-code changes, deletion, retry-limit increases, lower disk floors, concurrent runs, or changes to scientific parameters.
