# ASP matrix supervisor

This host-side service historically supervised the sequential 4-scene ×
3-seed ASP matrix. The final control state capped the campaign at three
completed seed-42 runs; the queue is now frozen and no new launch is planned.
It does not modify the pinned author checkout and does not implement resume. A
failed run is restarted from zero at most once and its old artifacts are
archived rather than overwritten.

## Operator commands

```bash
python3 tools/matrix_supervisor/supervisor.py --check
python3 tools/matrix_supervisor/supervisor.py --once --dry-run
cat runs/matrix_supervisor/status.json
tail -f runs/matrix_supervisor/events.jsonl
systemctl --user status asp-matrix-supervisor.service
journalctl --user -u asp-matrix-supervisor.service -f
```

Set `"paused": true` in `CONTROL.json` to block launches and retries. Budget
monitoring remains active, so an already-running experiment is still stopped
at the first completed checkpoint at or beyond 120 m. Set it back to `false`
to resume an operator pause. A safety pause (for example, host GPU failure,
ambiguous stall, or artifact-validation failure) requires an explicit review:
fix the cause, then increment `resume_generation` by one. A generation written
while healthy is consumed and cannot silently resume a later safety event.

The service checks once per minute. Human or agent check-ins may remain at a
30-minute cadence because they are reporting only; safety does not depend on
their SSH connection.

## Recovery policy

- Host GPU failure on two consecutive checks: pause for human review.
- Container GPU fails twice while host GPU is healthy: full Docker stop/start,
  followed by GPU verification.
- Before each launch, remove only the selected display's stale X lock/socket,
  and only when no live Xvfb process owns that display. Docker stop/start does
  not clear these container-filesystem locks.
- Clear process/container failure before 120 m: archive and retry if this was
  attempt 1; pause if this was attempt 2.
- Ambiguous 30-minute stall: pause automation without killing the process.
- Free disk below 25 GB: finish monitoring the active run but do not launch the
  next one.
- Path at or above 120 m: double-Escape shutdown, artifact validation, clean
  container restart, then advance the queue.

Runtime truth is under `runs/matrix_supervisor/`. `state.json` is machine
state, `status.json` is the current operator view, and `events.jsonl` is an
append-only transition log.
