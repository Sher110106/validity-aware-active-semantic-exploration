# Campaign status reconciliation: 26 September 2026

The host file `runs/prospective_gemini/scientific_campaign_20260922/campaign_status.json` is an earlier breadth snapshot, not the final record. It lists 11 blocks (v1 and v2 attempts only), snapshots $13.805244 settled, and finalizes at $17.310224 settled with 7 unresolved requests. It omits the v3 through v6 attempts entirely.

The ledger aggregates queried read-only on the same date supersede it: 2,233 settled requests, $36.783435 settled, $159.976812 summed reservations, zero unresolved in the scientific ledger. The v6 subset alone (898 requests, $18.552664 settled) postdates the status file. The v6 watchdog status and derived metrics corroborate the later spend.

The original status file was left untouched on the host. Read the ledger summary (`2026-09-26-ledger-summary.json`) and the audit (`2026-09-26-remote-audit.md`) as the accounting sources of truth.
