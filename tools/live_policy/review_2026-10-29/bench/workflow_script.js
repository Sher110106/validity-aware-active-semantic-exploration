export const meta = {
  name: 'decision-bench',
  description: 'Plan step 6: build and run the pre-registered offline decision bench with a wall-aware yardstick, then verify it adversarially',
  phases: [
    { title: 'Build', detail: 'wall-aware yardstick, six rules x five guess sets, regret' },
    { title: 'Verify', detail: 'independent recompute and refutation' },
  ],
}

const RULES = `Rules:
- spend no money; no SSH; do not run Habitat or the robot pipeline; never open credential files;
- do not edit anything outside /tmp/cvp_bench/bench/<your label>/ (create it);
- use /Users/sher/project/cvp/project/.venv_offline/bin/python, with -B so no bytecode is written into other folders;
- label each claim verified or inferred.`

const OUT = {
  type: 'object',
  properties: {
    scripts: { type: 'array', items: { type: 'string' } },
    outputs: { type: 'array', items: { type: 'string' } },
    method: { type: 'string' },
    yardstick_check: { type: 'string' },
    results_markdown: { type: 'string' },
    decision: { type: 'string' },
    caveats: { type: 'array', items: { type: 'string' } },
  },
  required: ['scripts', 'outputs', 'method', 'yardstick_check', 'results_markdown', 'decision', 'caveats'],
}
const VER = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['holds', 'holds_with_corrections', 'does_not_hold'] },
    checks: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, how_checked: { type: 'string' }, result: { type: 'string' }, ok: { type: 'boolean' } },
      required: ['claim', 'how_checked', 'result', 'ok'] } },
    corrections: { type: 'array', items: { type: 'string' } },
    corrected_results_markdown: { type: 'string' },
    corrected_decision: { type: 'string' },
  },
  required: ['verdict', 'checks', 'corrections', 'corrected_results_markdown', 'corrected_decision'],
}

const BUILD = `Your label is build. Implement and run the offline decision bench exactly as the frozen pre-registration specifies:
/Users/sher/project/cvp/project/tools/live_policy/PREREGISTRATION_BENCH.md (sha256 in PREREGISTRATION_BENCH.sha256; do not edit it). Read it first and follow it to the letter. Where it is ambiguous, choose the reading closest to its words, and list each choice under caveats.

Inputs:
- Wall maps (pipeline frame): /tmp/cvp_bench/refs/<scene>_walls.npz, with occ[height, i, j] (uint8), origin (x0, y0), res 0.05 and heights. Cell (i, j) covers x0 + i·res, y0 + j·res. /tmp/cvp_bench/refs/*_check.png shows walked paths drawn over the walls; they line up.
- Earlier objective audit, verified: /tmp/cvp_review/audit/audit/ (audit.py, counterfactual.py, summarize.py, stages.jsonl, cf_stages.jsonl, summary.json, cf_summary.json; its tmp/ holds cached placebo and oracle hypothesis files). It already:
  - regenerates the 300 candidates per stage;
  - computes U_360 without walls;
  - draws placebo and oracle sets with live_policy's own generators;
  - scores ASP's first-stage total.
  Reuse it read-only, by import or by copying code into your folder.
- Reviewer A's replay of the author's scorer: /tmp/cvp_review/work_A/ (fastig.py, replay.py, replay2.py).
- Pinned author code: /tmp/cvp_review/pipeline_pinned_copy/scripts/.
- Copied runs: /tmp/cvp_review/runs/; run list: /tmp/cvp_review/analysis_pre/runs.txt (24 runs).
- References and oracle sets: /tmp/cvp_review/refs/ (<scene>_hm3d_reference.yaml, oracle_sets.json).
- live_policy.py: /Users/sher/project/cvp/project/tools/live_policy/live_policy.py (placebo_graph, oracle_graph, oracle_eligible; placebo_calibration.json beside it).

Deliver:
1. The yardstick check from the pre-registration (U_wall against U_360 as a predictor of mapping at k+1), with numbers.
2. The full regret table: rules R1-R6 × guess sets (actual, none, placebo A, placebo B, oracle), by arm and pooled, with stage-bootstrap CIs.
   - Also the U_wall_cone version.
   - Also normalised regret.
   - Use fixed seeds for the placebo and oracle draws (distinct per stage), and record them.
3. The decision rule applied exactly as written, with every number it uses: for each of R1-R4, the oracle/placebo-A regret ratio and its CI; on official stages, LLM − placebo-A against the noise floor.
4. Per-stage outputs as JSONL and a summary JSON in your folder.

Report how many stages enter each summary, and why any were dropped. Keep a run time under about 2 hours of CPU; if the full 384 stages would take longer, say how you sped it up (vectorising, caching) rather than sampling stages.

${RULES}`

phase('Build')
const built = await agent(BUILD, { label: 'build:bench', phase: 'Build', schema: OUT, effort: 'high' })
if (!built) return { error: 'builder returned nothing' }
phase('Verify')
const verified = await agent(`You are an adversarial verifier. Another agent built and ran the analysis below. Find what is wrong; do not agree by default.

Its brief:
---
${BUILD}
---

Its return value:
---
${JSON.stringify(built, null, 1)}
---

Steps:
1. Read the frozen pre-registration (/Users/sher/project/cvp/project/tools/live_policy/PREREGISTRATION_BENCH.md) and the builder's scripts line by line. Check each rule, the guess sets, the yardstick (wall ray casting, cell indexing, the 0.15 m end allowance, range, the unmapped rule), the move cost, the regret definition, the bootstrap, the noise floor and the decision rule against the text.
2. Recompute independently, with your own code in /tmp/cvp_bench/bench/verify/: at least 10 stages spread over arms and scenes, covering U_wall for a sample of candidates, each rule's pick, and regret. Also recompute the decision-rule numbers from the per-stage outputs.
3. Check the wall ray cast on a few hand-picked cases: a candidate and an object in the same room should be visible; ones on opposite sides of a wall should not.
4. Check that every number in results_markdown matches the outputs.

Return a verdict, each check, any corrections, and the corrected results and decision.

${RULES}`, { label: 'verify:bench', phase: 'Verify', schema: VER, effort: 'high' })
return { built, verified }
