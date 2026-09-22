# Gemini campaign broker

Status: **complete and frozen**. The broker and audited runtime are retained
for offline inspection; the recorded campaign is closed and no new paid probe
or launch is planned.

## Security model
`load_credential()` requires an absolute path outside caller-supplied forbidden repository roots, a regular file owned by the current UID, exact mode `0400` or `0600`, and a bounded single-line value. It opens with `O_NOFOLLOW` where available and validates the opened descriptor with `fstat`; errors are generic and contain neither path nor value. Keys beginning `AQ.` are valid authorization API keys as of 2026 when sent through the `x-goog-api-key` header; this implementation never validates or embeds a real key.

Credentials are not accepted in environment inventories, CLI arguments, URLs, manifests, logs, exceptions, fixtures, or events. Events use an allowlist, identifier validation, exclusive no-follow opening, process locking, fsync, sequence numbers, and chained hashes. They never contain URLs, headers, bodies, raw responses, signatures, credentials, or arbitrary exception text.

## Budget invariants
The user cap is $200.00; the broker ceiling is $190.00, normal spending is $180.00, and the untouched/recovery reserve is at most $10.00. Exact integer microdollars are used. Phase caps are probe $2.00, engineering $18.00, scientific normal $160.00, and recovery $10.00. Recovery requires an explicit validated expiring `RecoveryControl`; a boolean cannot enable it.

Every complete request envelope gets either a trusted native count tied to its canonical request hash and exact model, or a conservative one-token-per-serialized-byte bound. Missing bounds fail closed. Every physical attempt allocates budget, reserves transactionally, writes a local dispatch receipt, then performs injected transport I/O. The provider response ID is never invented. Timeouts/unknown responses remain reserved. No SDK retries or provider fallbacks exist.

Gemini `max_output_tokens` is a hard cap including thought tokens. Reservations use the complete cap once; settlement charges candidate plus thought tokens and requires `candidate + thought <= max_output_tokens`. Cached input is conservatively charged at the full input rate. Settlement requires exact model, standard service tier, valid usage totals, finish reason, response ID, and dispatched state. Duplicate settlement is idempotent only when all immutable accounting fields match.

## Commands

```sh
python3 -m tools.gemini_campaign.cli probe       # dry-run only
python3 -m tools.gemini_campaign.cli summary ledger.sqlite
python3 -m tools.gemini_campaign.cli export ledger.sqlite
python3 -m tools.gemini_campaign.cli checksum ledger.sqlite
```

The CLI probe remains dry-run only, and this package does not authorize a new
paid launch. Probe allocations can never exceed $2.00.

## Official-source record
Operator confirmation supplied 2026-09-18 states the exact model, thinking level, limits, and pricing. Re-check before any future paid integration: [Gemini models](https://ai.google.dev/gemini-api/docs/models/gemini), [thinking](https://ai.google.dev/gemini-api/docs/thinking), [generate content](https://ai.google.dev/api/generate-content), [usage metadata](https://ai.google.dev/api/generate-content#v1beta.GenerateContentResponse), and [pricing](https://ai.google.dev/gemini-api/docs/pricing).
