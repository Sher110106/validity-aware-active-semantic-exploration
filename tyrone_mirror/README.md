# Evidence mirror

This directory contains selected, read-only evidence copied from the remote GPU host. It is intentionally smaller than the live workspace: raw credentials, live SQLite ledgers, provider request bodies, images, and machine-local logs that are unnecessary to reproduce the reported numbers are excluded.

The top-level run groups are:

- `scene00069_*`, `scene00573_*`, `scene00853_*`, and `scene00871_*`: baseline, calibration, and short-run evidence.
- `matrix120m_scoring/`: the final three-scene matrix, corrected decision replays, and Phase 13 v5 diagnostics.
- `prospective_gemini/`: the fixed-parser Gemini v6 offline analysis and scoring summary.
- `DEVIATIONS.md`: the complete dated engineering log, including corrections and claim boundaries.

The canonical interpretation is in [../FINAL_REPORT.md](../FINAL_REPORT.md) and [../docs/RESULTS_INDEX.md](../docs/RESULTS_INDEX.md). Files in this mirror are evidence artifacts, not an active runtime workspace.
