# PLAN

## Goal

~~Deploy a resource-safe host supervisor for the active ASP 12-run matrix without restarting run 1.~~ Deploy a resource-safe host supervisor for the active ASP matrix without restarting run 1. **Scope note (2026-09-16):** the matrix's final size was descoped for cost/time to 3 runs (00069/42, 00573/42, 00853/42), not the original 12 — see `IMPLEMENTATION_PLAN.md` section 0. This supervisor's own design is unaffected: it now stops after run 3 via `CONTROL.json`'s `max_completed_runs`.

## Current strategy

Build a standard-library Python state machine and host runtime adapter with vertical TDD, validate it in read-only mode against tyrone, then enable a user systemd service and verify adoption.

## Phases

- [x] Audit the live run and existing monitoring claims.
- [x] Freeze queue, retry, call-budget, disk, and stall policy with the user.
- [x] Implement queue/adoption and status reporting.
- [x] Implement safety transitions and process controls.
- [x] Run local and remote dry-run verification.
- [x] Install and verify persistent host service.
- [x] Confirm two healthy cycles and unchanged experiment PID.

## Open decisions

- None. Any need to touch pinned code or increase retry limits returns to the user.

## Deployment state

- User service: `asp-matrix-supervisor.service` active and enabled on tyrone.
- Persistence: `Linger=yes`; the service does not depend on an SSH session.
- Active experiment: `scene00069_seed42_matrix120m`, attempt 2, adopted without restart.
- Pipeline identity: PID 933 and `ASP_LLM_LOG_DIR` both match the expected run.
- Runtime truth: `/home/sher/active-semantic-perception-workspace/runs/matrix_supervisor/`.
