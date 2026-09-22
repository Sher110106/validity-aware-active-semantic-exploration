# NOTES

## Chronological notes

- 2026-09-16 10:46 IST: Active run was healthy, with working container GPU, ROS stack, and pipeline.
- 2026-09-16 10:49 IST: Run reached 35.1 m; observed call/path fits forecast roughly 2,067–2,265 calls at 120 m, so the current 2,500 cap is likely sufficient but not generous.
- 2026-09-16 10:50 IST: `restart=unless-stopped` restarts only the container's `sleep infinity`; Docker-exec children do not resume.
- 2026-09-16 10:51 IST: No crontab, matrix systemd timer/service, tmux queue, or active path-budget watcher exists. Only run 1 is launched.
- 2026-09-16 11:10 IST: `asp-matrix-supervisor.service` was enabled under the user manager and user lingering was enabled, making supervision independent of SSH sessions.
- 2026-09-16 11:22 IST: All four frozen scene paths were verified readable. The active run manifest confirms low reasoning effort, 16,000 max tokens, and its original 2,500-call cap; future runs use the user-approved 3,000 cap.
- 2026-09-16 11:27 IST: The active pipeline routes logging to `/workspace/runs/scene00069_seed42_matrix120m/prompts`, so the supervisor can reject a stale pipeline belonging to another run.
- 2026-09-16 11:27 IST: The final remote suite has 36 passing tests. Transient Docker/process-inspection errors produce no destructive action, launch intent is write-ahead, failed-run archiving is idempotent, and safety pauses require an explicit `resume_generation` increment.
- 2026-09-16 11:27 IST: Pinned-checkout status hash `c9193c5e...` and diff hash `20874bc5...` match their pre-deployment values exactly.
- 2026-09-16 11:30 IST: Regression checks passed: 36 supervisor tests on tyrone, 38 offline ASP tests locally, and 11 evaluator tests in the pinned container environment.
- 2026-09-16 13:27 IST: Run 1 reached its first completed checkpoint beyond budget at 125.325 m (stage 27), used 1,922 calls, and passed artifact validation.
- 2026-09-16 13:28 IST: Docker creates run directories as `root:root`; host-side completion-marker writes therefore failed safely after the pipeline had stopped. Marker writes now use an atomic Python operation inside `asp-noetic`, preserving ownership and avoiding chmod/chown of evidence.
- 2026-09-16 13:29 IST: Run 2's first launch exposed a second container-restart edge case: `/tmp/.X99-lock` and `/tmp/.X11-unix/X99` survive Docker stop/start even though Xvfb does not. The pipeline failed before any LLM call. Launch preflight now removes only display 99's stale files after proving no live Xvfb owns the display.
- 2026-09-16 13:35 IST: Run 2 attempt 2 is healthy on scene 00573 / seed 42 with the frozen DeepSeek configuration and 3,000-call cap. The first attempt used zero calls and remains archived.
