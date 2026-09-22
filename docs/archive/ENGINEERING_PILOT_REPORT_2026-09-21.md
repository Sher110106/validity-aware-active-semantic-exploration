# Engineering pilot report — 2026-09-21

## Bottom line

The pilot (scene 00069, seed 42, one stage) did not complete. It never made
a paid Gemini call. Zero dollars were spent or are at risk:
`settled_microusd: 0`, `reserved_microusd: 0`, `unresolved_requests: 0`.
Two real bugs were found and one is fixed; the other needs your decision
before any further paid attempt. Nothing else was started or changed
beyond what is listed here.

## What stopped it

Every one of the 8 concurrent ensemble-member workers builds a request
whose body includes six ~500KB scene-slice JPEGs as base64. The reservation
code (`conservative_input_bound()` in `transport.py`) charges one token per
byte of that request. For the real scene-0/member-0 request this bound is
4,104,516 "tokens" — about $3.08 of input alone — against a $2.50 pilot
allocation. `AccountingHalt("allocation exhausted")` fired correctly,
before any HTTP call. This is not a sizing problem with this one pilot: it
would exhaust any allocation up to the full $190 ceiling, since one stage's
8 simultaneous first-turn reservations alone would ask for roughly $25 at
this bound.

## What it actually costs

I measured it for free. Google's `countTokens` endpoint (no charge, no
ledger interaction) on the exact same real request — the real images and
YAML already sat on disk from the run that hit this wall — returned
**9,317 tokens**, not 4.1 million. Overshoot: **440.5x**.

At the real count, one turn's reservation is `cost_microdollars(9317, 8192)`
= **$0.0377**, not ~$3. Your existing $2.50 pilot cap and $18/$160 caps all
have wide headroom once the reservation uses a real count instead of a byte
count. The fix is measuring the request, not raising any cap. The seams
for this already exist and are unused: `RequestContext
.trusted_input_token_bound`, `NativeTokenCounter`, `validate_native_count`.
I did not wire any of them into `reserve()` — that changes a financial
control and needs your sign-off, not mine, unsupervised. I only ran the
free measurement.

## A second, independent problem: allocations never release

`Ledger.allocate()` has no release, deallocate, or cancel method.
`_allocated_total()` sums every allocation ever created, whether or not
anything against it ever settles, and `remaining_microusd = ceiling -
allocated`. This pilot's one $2.50 allocation is now permanently gone from
the $190 ceiling even though nothing was spent. This campaign has already
had two abandoned launch attempts tonight (a `roslaunch` config error, then
this one) — each one a small, irreversible debit. This is a design
decision for you: whether allocations should be revocable while unsettled,
or whether the ratchet is intentional.

## Bug found and fixed: seed derivation

`deterministic_seed()` (`prospective_integration/overlay_runtime.py`)
derived each call's seed from a SHA-256 hash truncated to 4 bytes and read
as an unsigned 32-bit integer, but the API requires a signed 31-bit seed.
About half of all possible hash values overflow that range. Live, about
half of the 8 concurrent workers failed with `seed must be an explicit
deterministic integer` — raised before any reservation, so this cost
nothing, but it means half the ensemble was silently unable to run at all.

Fixed with a bitmask (`& 0x7FFFFFFF`), already committed
(`4b1a477`). I also added a pinned regression test
(`test_deterministic_seed_masks_a_known_overflowing_hash`) using a specific
input whose unmasked hash is known to overflow — the existing test sampled
one random value, which has roughly even odds of missing this bug, and did.
Masking changes every derived seed; nothing has ever settled under the old
one, so there's no reproducibility continuity broken by changing it now,
but it's worth recording before anything real runs on it.

## Known finding from earlier tonight: the race condition

`complete_scene_graph()`'s `as_completed()` loop yields ensemble-member
results in completion order, not submission order — so `generated_graphs[0]`
is whichever worker finished first, not "ensemble member 0." I added
opt-in instrumentation (`race_instrumentation.py`) that records which
member actually produced which graph, but the underlying indexing in the
pinned pipeline is unchanged (by design — I don't edit the pinned
checkout). Anything downstream that has assumed `graphs[i]` means "member
i" should be checked against this.

## One item I can't stand behind right now

Earlier in tonight's session — before a context compaction — I apparently
flagged a finding I noted only as "a missing policy hook." That happened
before this report and I do not have the technical specifics anymore; I
looked for it in code comments, commit messages, and the campaign docs and
could not re-find it. Rather than guess at a technical claim I can't
verify, I'm flagging that it's missing rather than inventing plausible
details. If it still matters, tell me and I'll re-derive it from scratch —
and put it in `DEVIATIONS.md` immediately this time, before it can be lost
again.

## Integrity and cleanup

- The pinned checkout (`active_semantic_perception`) is confirmed
  byte-identical against a pre-pilot hash of every `.py`/`.yaml`/`.launch`
  file. The only change under its tree is one new file, hydra's own output
  snapshot at the isolated path this pilot chose
  (`mapping/hydra/output/prospective_pilot_20260921/hydra_config.yaml`) —
  the same behavior every prior run has already exhibited under
  `realsense`/`realsense_frontier`.
- Two orphaned zombie processes (`Xvfb`, `roslaunch`) left over from the
  crashed run were reaped on tyrone. Display `:99` (the paused matrix run's
  own display) was never touched.
- The sibling checkout's config edits for this pilot are mine to own and
  were left in place; nothing in the pinned checkout needed restoring.
- Full detail recorded as entry #81 in `tyrone_mirror/DEVIATIONS.md`.

## What I did not do

No relaunch. No cap raised. No change to `reserve()` or any other
financial control. No scientific-phase planning. No branch merge or push.
No touching the matrix_supervisor's own blocker. This campaign has made
zero paid Gemini calls to date.

## Recommended next step

Decide whether to wire a real (`countTokens`-based) input bound into
`reserve()` — a financial-control change I'm not making without your
sign-off — and separately, whether `allocate()` should support releasing
an unsettled allocation. Once either or both land, the existing pilot cap
is almost certainly enough to run the real thing; the money was never the
constraint, the byte-counting was.
