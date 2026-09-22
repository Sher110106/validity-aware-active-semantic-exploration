# Decision-replay reference

`calculate_uncertainty.py` is the operative reference implementation captured
from the pinned ASP checkout and used by `tools/decision_replay.py`. Keeping it
under a separate namespace prevents the project's validator and policy code
from silently replacing the author's geometry, visibility, and entropy logic.

The replay script still prefers an explicitly deployed pinned checkout when it
is available on the Linux host. The vendored copy is the deterministic offline
fallback used by local tests and by readers who only have this repository.
