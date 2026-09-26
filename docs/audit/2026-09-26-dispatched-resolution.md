# DISPATCHED ledger resolution: 26 September 2026

Read-only inspection, no ledger writes, no model calls. All three entries keep `state=DISPATCHED` in their original databases with unknown settled cost. None is counted as zero.

## Verification ledger (`native_count_verify_20260922`), 1 entry

- Request `91e122b00ae743e5abe0102c7b14b407`, created and dispatched 1789973495, never settled, $0.008101 reserved.
- The sibling raw archive (`prompts/raw_archive.jsonl`, read read-only through the existing container) holds a real provider response for `attempt_id=verify-attempt` (`responseId -NOwat7-N47Eg8UP657DyQU`, `thoughtsTokenCount 121`). The follow-up `verify-attempt-2` settled normally.
- Conclusion: the provider responded and the attempt was deliberately left fail-closed because the thought-token count exceeded the bound. The ledger row is correctly unresolved. Settled cost: unknown.

## Capability probe (`capability_probe_20260919`), 2 entries

- Requests `59d71931150c46079577c328b1af8de9` and `7a05a5331e214079a0e1883756596d54`, dispatched 1789787432 and 1789788603, never settled, $0.001046 reserved combined.
- The run directory holds only ledger files, so no response archive exists to check against.
- Conclusion: no record either way. Settled cost: unknown.

## Totals unchanged

`docs/audit/2026-09-26-ledger-summary.json` still reports 3 unresolved requests with $0.009147 reserved. This note explains them; it does not close them.
