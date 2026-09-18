# Implementation plan

- [x] Add fixed contract, policy vocabulary, model/reasoning constraints.
- [x] Add deterministic paired queue, ladder, budget and technical admission.
- [x] Add fail-closed controls, atomic state/events, isolated attempts and
  completion validation.
- [x] Add redacted manifest extension and claim gates.
- [x] Add fakes and tests.
- [ ] Future integration: implement adapters for the budget broker and
  motion/detour runner in separate cherry-pickable branches.

## Scope decision procedure

The controller writes a terminal scope decision after the pilot containing the
pilot ledger, worst-case pair estimate, selected horizon, reservations, and
whether each complete block fit. This is a decision artifact, not a promise
to run a fixed number of attempts.
