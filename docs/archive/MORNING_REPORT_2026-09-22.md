# Morning report — 2026-09-22

You asked me to fix the reservation bug, get the best results out of the
$200 overnight, and present it this morning. Here it is.

## Bottom line

The fix works. Real money moved, real completions settled, real per-turn
cost came in at pennies, exactly as measured last night. But a second real
bug surfaced during the actual run — Gemini's own response IDs can start
with a hyphen, and the ledger rejects any identifier that does, so about a
quarter of last night's real, valid, correctly-priced completions can
never be marked settled. Nothing is overspent and nothing is unsafe — the
money for those calls is still reserved, not lost or double-spent — but
the ledger's own settled total undercounts real spend, and I stopped
before going further. Total real spend across every ledger tonight and
last night: **under $1**, against the $200 cap.

## What happened, in order

1. **You authorized overnight work.** I forked a background session with
   full context and instructions to: implement a real-token-count fix for
   the reservation bug, get an independent design review before deploying
   it, run the real pilot, and — only if that went cleanly and only with
   sign-off — consider extending further, all within the existing caps.

2. **The fix was built and reviewed.** `transport.count_tokens()` /
   `native_input_bound()`: a free `countTokens` call gives the real input
   token count instead of the old byte-count guess, with a safety margin
   on top (`count + max(256, count/8)`, capped at the old byte bound) and
   full logging of every count and fallback. An independent design review
   caught that a bare count could under-reserve and leave real spend
   stuck unpriced — the margin and logging were added specifically to
   close that gap. Opt-in via `ASP_PROSPECTIVE_NATIVE_COUNT=1`; nothing
   changes for anyone who doesn't set it. Full detail and commit hashes:
   `tyrone_mirror/DEVIATIONS.md` #82–#83.

3. **It was deployed and run for real.** A one-call $1 verification run
   settled cleanly with `promptTokenCount: 9317` — an exact match to last
   night's free measurement, zero discrepancy. Then the real ≤$18
   engineering-pilot re-attempt: **29 real completions settled** across
   both stages of scene 00069 (all 8 ensemble members, several tool-loop
   turns each). Real per-turn cost: $0.0096–$0.0207. This is the number
   that matters — it confirms the whole campaign is affordable once the
   reservation uses real counts, exactly as predicted.

4. **A second real bug stopped it.** 8 of those calls (plus 1 in the
   verification ledger) came back with valid, successful responses —
   correct `finishReason: STOP`, correct usage — but the ledger refused to
   settle them: `LedgerError("provider response is invalid")`. The cause:
   Google's real response IDs can start with `-` (e.g.
   `-NWwasf4MsGlg8UP69rl8QU`), and the ledger's identifier check requires
   the first character to be alphanumeric. That check exists for good
   reason elsewhere — it's just wrong for this one real-world case. About
   24% of last night's real calls hit it. Compounding this: once any call
   goes unresolved for any reason, the pipeline's own retry logic reruns
   that ensemble member from scratch using the same deterministic ID,
   which then collides forever against the ledger's own duplicate-request
   guard — an infinite but harmless (zero-cost) loop. The overnight fork
   caught this live and stopped the pilot rather than let it spin. I
   verified that stop myself this morning: no live processes remained on
   tyrone, only harmless leftover zombies, which I cleaned up.

5. **I reconciled every dollar by hand.** For the 8 stuck completions, I
   replayed their real, already-received responses against a disposable
   copy of the ledger (never the live one) to confirm exactly why they
   failed and what they would have cost. Real additional spend: $0.1014.
   True total for the pilot run: **≈$0.55**, not the $0.448 the ledger
   itself reports — still trivial against the $18 allocation, but worth
   knowing the ledger's own number is currently an undercount.

## What's fixed

- The core reservation bug from last night (byte count vs. real count) —
  fixed, deployed, and proven against real settled data.
- Nothing else. Both bugs found tonight are left exactly as found.

## What's found but not fixed — needs your decision

1. **The `responseId` regex.** It's used to validate several different
   identifier fields across the ledger, not just this one, so loosening it
   needs a real look, not a 3am patch. The fix is probably narrow (allow a
   leading `-` specifically for provider response IDs, or use a different
   check for that one field) but I didn't make it unsupervised.
2. **The retry/attempt-ID collision.** The schema already has an unused
   `retry_of` field meant for exactly this — a fresh, provenance-tracked
   attempt ID for a genuine retry. Wiring it into the pipeline glue is the
   likely fix; also not made unsupervised.
3. **Two smaller structural findings**, lower priority: `Ledger.allocate()`
   still has no way to release an unsettled allocation (every abandoned
   attempt permanently eats ceiling), and the $190/$180 ceilings are
   enforced per ledger file, not once globally — nothing stops separate
   run directories from summing past $200 except tracking it by hand.

## What I did not do

No further live runs after finding the second bug. No scientific-phase
work. No cap raised beyond what already existed. No branch merged or
pushed. "Best results" tonight meant proving the fix works and finding
what still breaks it cleanly enough to hand you a real decision — not
maximizing dollars spent.

## Recommended next step

Decide on the `responseId` regex and the retry/attempt-ID scheme. Once
either lands, the existing caps have wide headroom — a full engineering
pilot costs under a dollar, not $18, at real prices. After that, the
$160 scientific-phase allocation is very likely enough for the full
preregistered design (00069/00573/00853 × three seeds × both scoring
policies).

Full technical detail: `tyrone_mirror/DEVIATIONS.md` entries #81–#84.
Last night's original report: `ENGINEERING_PILOT_REPORT_2026-09-21.md`.
