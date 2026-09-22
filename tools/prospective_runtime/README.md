# Prospective runtime overlay

This package is an **offline-safe** integration seam for the prospective
campaign. The historical live overlay used a sibling checkout; this repository
does not edit the pinned author checkout, start Habitat/ROS, or authorize a new
paid campaign.

* `transport.py` is a direct `generateContent` adapter for Python 3.9. It uses an `x-goog-api-key` header, no SDK retry, and an injectable HTTP callable. A broker reservation is required immediately before each physical attempt. API keys are never included in URLs, response objects, or logs.
* `author.py` keeps the author tool-loop shape, explicit `gemini-3.8-flash`/medium request configuration, deterministic request seed, bounded output, and opaque thought signatures only in the same tool turn.
* `policy.py` applies the existing deterministic validator followed by raw 4/4 per-track unanimity. It fails closed on missing or rejected members, preserves observed nodes/edges, and writes new output when requested.
* `passive_nav.py` wraps pose commands without altering commands, observations, RNG, or viewpoints. Pathfinder auditing is passive and is not a collision signal; genuine contact requires a separate controller-altered executor (not provided here).
* `deploy.py` is hash-checked and dry-run by default. `run_campaign.py` is dry-run by default and always refuses live mode until audited broker/campaign contracts exist.

The `120`, `75`, `50`, and `25` values are meter path-distance budgets. Wall-clock limits are separate manifest fields. Causal mid-run snapshot restoration is not claimed; independent full-run pairing and branch-level attribution remain limited until a demonstrable restore hook exists.

Remaining real-runtime checks: author checkout paths/API signatures, Habitat-Sim pathfinder behavior, broker atomicity across workers, secure credential-file handling, controller contact signals, and end-to-end campaign contract audit. Offline tests establish adapter semantics only and do not establish navigation, collision, detour, or false-positive claims.
