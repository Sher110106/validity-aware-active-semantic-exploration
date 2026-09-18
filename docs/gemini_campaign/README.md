# Gemini campaign broker

Status: **no-paid-call implementation**. This branch contains an injectable adapter and an offline ledger; it does not invoke Gemini or probe provider capabilities.

## Security model
Credentials are loaded only from an operator-provisioned regular file whose group/other permission bits are zero (`load_credential(path)`). The value is never logged, serialized, placed in an exception, passed in a URL, or accepted via environment inventory/CLI arguments. Transport is injected by the caller and broker events allowlist fields; raw requests/responses and authorization headers are not logged.

## Budget invariants
The stable allowlist is `gemini-3.8-flash`, `thinking_level="medium"`, explicit `max_output_tokens`, context bound 1,048,576 and output bound 65,536. Pricing is standard paid pricing through 2026-12-31: $0.75/M input and $3.75/M output (thinking included). The ledger uses integer microdollars and atomically reserves before dispatch. Reservations plus settled spend cannot exceed the $190 campaign ceiling. Missing usage, model/price mismatch, malformed responses, timeouts, lock errors, and corrupt ledgers fail closed with the reservation unresolved. No fallback and no automatic retries.

Normal ceiling is $180, recovery reserve is $10, and $10 remains untouched. Recovery controls are intentionally not implemented as an implicit path in this no-paid-call branch.

## Commands

```sh
python -m tools.gemini_campaign.cli summary ledger.sqlite
python -m tools.gemini_campaign.cli export ledger.sqlite
python -m tools.gemini_campaign.cli checksum ledger.sqlite
python -m tools.gemini_campaign.cli probe                 # always dry-run
```

Exports contain ledger metadata only and should be treated as campaign artifacts. `summary` reconciles reserved, settled, unresolved, and remaining amounts.

## Official-source record
Operator confirmation supplied 2026-09-18 states the exact model, thinking setting, limits, and pricing above. Reference URLs to re-check before any paid integration: [models](https://ai.google.dev/gemini-api/docs/models/gemini), [thinking](https://ai.google.dev/gemini-api/docs/thinking), and [pricing](https://ai.google.dev/gemini-api/docs/pricing). This branch makes no network/API calls and leaves paid invocation disabled.
