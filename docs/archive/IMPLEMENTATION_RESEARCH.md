# Implementation Research & Decision Notes

**Project:** Validity-Aware and Calibrated Active Semantic Exploration (CVP course proposal)
**Status:** Proposal complete and audited (PASS on content, template-compliant except one missing field). These notes are the implementation contract for the build phase.
**Last updated:** 2026-08-31

---

## 1. Sources of truth

| File | What it is | Use |
|---|---|---|
| `output/docx/Validity_Aware_Active_Semantic_Exploration_Proposal.docx` | Final proposal (spec) | Canonical statement of what we promised |
| `output/pdf/Validity_Aware_Active_Semantic_Exploration_Proposal.pdf` | Rendered 2-page A4 | Submission copy |
| `.firecrawl/active-semantic-perception-full.md` | ASP paper v2 (arXiv 2510.05430) | Method details, LLM prompt rules, evaluation |
| `.firecrawl/active-semantic-repo.md` | ASP GitHub repo (grasp-lyrl/active_semantic_perception) | Install steps, repo layout, launch procedure |
| `.firecrawl/clio.md`, `conceptgraphs.md`, `ssmi.md`, `yoloe.md`, `habitat.md`, `hm3d.md` | Related-work papers | Baseline justification, citations |
| `Report_Template (1).doc` | Course submission template | Final-report formatting rules (Section 6) |
| `output/...proposal.pdf` (rev 2026-08-31) | Readability revision per Ananya: 3 pages A4, Figure 1 (failure mode + pipeline), Table 1 (validator invariants), Table 2 (evaluation protocol), bold lead-ins in Problem Formulation. Protocol numbers unchanged — this revision only repackages the contract. | Build scripts: `/tmp/build_proposal_v2.py`, `/tmp/make_proposal_figure.py` |
| `Computer_Vision_Perception_Projects(Projects).csv` | Course project list | Deliverable context |

Two independent audits ran on the final proposal:
- **FinalContentAudit** — verified every technical claim against the ASP paper + released source. Verdict: **PASS**, no blocking defects.
- **FinalTemplateAudit** — checked against Report_Template. Verdict: compliant except one missing field (corresponding-author email, Section 6).

All findings below marked **verified** were confirmed against primary sources by those audits; **decided** = our locked choice.

---

## 2. What the project is

Reproduce the ASP pipeline (LLM-guided semantic exploration of HM3D scenes in Habitat), then fix two narrow gaps:
1. LLM support counts (frequency across K=8 completions) are not calibrated probabilities.
2. Local collision checks do not guarantee the completed graph satisfies global schema/topology/containment/geometry.

Add: deterministic whole-graph validation, held-out calibration of ensemble support, and risk-sensitive viewpoint scoring.

**Explicit non-claims (do not regress on these):** not first uncertainty-aware exploration; not introducing confidence or constrained generation; not a new mapping representation. ASP already has collision checks, structural context, completion frequency, entropy-based scoring.

---

## 3. ASP internals (verified against paper + source)

### 3.1 Pipeline (three modules)

- **A. Mapping:** RGB-D + pose from Habitat Simulator. Object segmentation: **YOLOE** (single-stage, better recall than FastSAM+CLIP). Wall segmentation: **YOSO** (`yoso_res50_coco.pth` weights). Builds a multi-layer scene graph with four node types: **objects, rooms, structures (walls/doors/windows), "nothing" (free space)**.
  - Object tracks: voxel IoU association, category must match, track timeout `τ` seconds, marching-cubes meshes for tight bboxes.
  - Rooms: TSDF → ESDF (brushfire, Voxblox) → generalized Voronoi "places" → agglomerative clustering into rooms → CLIP feature averaging → room label from closest category. Occlusion checking added over Clio.
  - "Nothing": largest free-space cuboid from thresholded TSDF occupancy (3D largest-rectangle-in-histogram).
- **B. Reasoning:** LLM (Gemini, cloud API) gets current scene graph as YAML + prompt, returns plausible completions. **K=8 samples per query, 2×4 structure**; waypoint score from ensemble disagreement + spatial perturbations; entropy score. (Verified: 8 samples, structure nodes, 2x4 completions, entropy scoring are in the released code.)
- **C. Planning:** global **A\* planner** on an **nvblox** occupancy grid; 360° sensing motion; per-object collision tool (`check_collision`).

### 3.2 LLM prompt rules (the validator must enforce exactly these)

From the paper's prompt box — these are the graph invariants ASP asks the LLM to respect:

- "You are an architect." Given YAML scene graph + matching images, add plausible new rooms and **at least 5 new objects**.
- `check_collision` for every new object; keep only if **IoU = 0**, otherwise move and retry. Tool not used for rooms.
- New rooms placed logically by extending from existing exits into empty space.
- Edges allowed: new objects↔rooms, new rooms↔rooms. Nothing else.
- No overlap with existing objects, structure nodes, or nothing nodes.
- Walls, curtains, windows, blinds are **impassable unless a door exists**; if a door exists and no room is defined beyond it, add a room there.
- **Do not create new nothing, structure, or door nodes.** No outdoor spaces, no dining rooms. Multiple bedrooms/bathrooms allowed.
- Output exactly **one YAML code block** containing only items that pass validation.

### 3.3 Source-code facts that affect our design (verified)

- `LLMCompletion` stores a `seed` field, but the released Gemini `GenerateContentConfig` **never passes a generation seed** → completions are non-deterministic; hosted model versions can drift. → Our fix: share cached completions at matched checkpoints across policies.
- "Confident" = appears in ≥2 of 8 completions is used **only in ASP's post-hoc room-prediction analysis**, not as a general planner mechanism. Our proposal states this scoped correctly.
- ASP evaluator matching thresholds: **same-category objects with centroid ≤ 0.5 m**; **rooms within 4 m** for GED; **structure/nothing nodes excluded** from matching.
- Released GED script computes over **object/room nodes only, skips door + other structure/nothing nodes**. Our "normalized GED" keeps this node set for comparability; normalization is by reference node+edge count.
- ASP timing metrics **exclude trajectory-compute and LLM-query time**. We report cached-replay time and live LLM time separately so comparisons are honest.
- Released plotting scripts contain **hard-coded paths and aggregation choices** → we must implement our own parameterized evaluator (already decided).

### 3.4 Baseline scenes (verified)

Four HM3D scenes from the latest paper revision: **00069, 00573, 00853, 00871**.

---

## 4. Locked design — the implementation spec (decided, in the proposal)

### 4.1 Validator (fail-soft, deterministic, no ground truth)

Processes each sampled completion after LLM generation. Checks:
1. Parseability (exactly one YAML block per prompt rule).
2. Allowed node and edge schemas (see 3.2 edge rules).
3. Finite dimensions and poses.
4. Unique identifiers.
5. Valid edge endpoints.
6. Preservation of observed nodes.
7. Object→room parent relations.
8. Room containment.
9. AABB conflicts (observed-to-predicted and predicted-to-predicted).
10. Crossings of impassable structures without a door.

Behavior: remove invalid predicted nodes with logged reasons; reject a completion that cannot preserve the observed graph. If **all** completions fail: use observed graph + geometric frontier fallback, never terminate. Extends ASP's local collision tool with whole-graph checks; exposes validity as a measurable quantity.

Constraints use **only the partial observed graph and fixed geometric rules — never hidden ground truth**. For every removal/rejection, log: violated invariant, original support, and whether the hypothesis matches the fully-explored reference graph (this last only for post-hoc analysis, not for decisions).

### 4.2 Calibration

- Hypothesis matching across samples: semantic label + parent room + spatial thresholds.
- Raw support `s_j` = fraction of K completions containing node j.
- **Leave-one-scene-out**: fit monotone map on 3 scenes, test on the 4th, rotate. β and acceptance threshold set **only on calibration scenes**.
- Label = hypothesis matches the fully-explored reference under the evaluator thresholds.

### 4.3 Score

`U(x) = I_object(x) + λ_r I_room(x) − λ_d d(x) − β R(x)`

- `R(x)` = mean of (1 − calibrated support) over predicted nodes visible from x; **0 if none visible** (avoids count-based penalty).
- **Calibration-only** variant: calibrated support in the original ASP gain with β=0.
- **Combined** variant adds βR.
- Ablations: filter-only, calibration-only, combined — isolates each stage.

### 4.4 Policies compared

Frontier, official ASP, filter-only ASP, calibration-only ASP, combined calibrated-risk ASP.
**SSMI only if** its separate implementation + native-planner comparison passes a fair-reproduction gate (expected to stay out — treat as non-goal until proven).

### 4.5 Evaluation protocol

- 4 scenes × seeds **42, 43, 44** = 12 runs. Each reported scene is the **held-out fold**; its 3 seeds never tune calibration/β/thresholds.
- Preregistered **120 m path budget**; checkpoints at **0, 25, 50, 75, 100, 120 m**.
- **Primary outcomes:** path-normalized area under the curves for object precision/recall/F1; reference-size-normalized GED AUC.
- **Diagnostic outcomes:** completion validity, survivor recall/diversity, Brier score, expected calibration error, reliability plots, evaluator-matched unseen-room discovery, false-positive detours, collisions, cached-replay time, live LLM time, query count, API cost.
- Reporting: per-scene results + paired scene-seed differences with **scene-cluster bootstrap 95% CIs**.

### 4.6 Guardrails

- Zero unhandled parse failures required.
- Report every scene-seed run; include CIs even when they contain zero.
- Combined method counts as useful only if it reduces invalid hypotheses + false-positive detours **without** > 0.05 loss in object-F1 AUC or > 10% increase in normalized-GED AUC vs official ASP. Otherwise document the trade-off, don't claim improvement.

### 4.7 Freeze rules (before any comparison)

- Model name, prompt, sensor configuration, candidate-view seeds frozen.
- Policies share cached completions at matched checkpoints wherever possible (Gemini non-determinism).
- **No manual prediction rejection** in scored runs.
- Cache: every partial graph, prompt, raw LLM response, parsed completion, candidate score, path, runtime, API cost — keyed by scene, checkpoint, model version, seed.

### 4.8 Non-goals

Real-robot deployment, detector/mapper training, NeRF/Gaussian splatting, local-LLM fine-tuning.

---

## 5. Team & roadmap (decided)

| Phase | Weeks | Deliverable | Gate |
|---|---|---|---|
| 1 | 1–4 | One-scene pipeline, cached completions, independent evaluator, frontier/ASP baselines | runnable on 1 scene |
| 2 | 5–7 | Second scene + validator | **midterm gate** |
| 3 | 8–9 | Calibration + risk-sensitive scoring | — |
| 4 | 10–11 | Preregistered evaluation | — |
| 5 | 12 | Freeze code, plots, report, demo | — |

Roles:
- **Member A:** Docker/ROS/Habitat, baseline replay.
- **Member B:** parsing, graph validation, identity matching, calibration.
- **Member C:** scoring, planning integration, metrics, plots.

**Fallback:** offline cached-graph replay if the full ROS/Clio stack misses the week-3 integration gate.

---

## 6. Template compliance rules (final report must match; proposal already does)

From `Report_Template (1).doc`, verified by FinalTemplateAudit:

- Title: **24 pt Regular** (not bold).
- Level-1 headings (I/II/III + REFERENCES): **10 pt small-caps regular** (not bold).
- Level-2 headings (A–E): **10 pt italic** (not bold).
- Abstract: heading **9 pt bold** ("Abstract-"), body **9 pt regular**; Keywords same pattern.
- References: **8 pt**, publication fields (journal/proceedings/venue names) **italic**, author/title regular.
- **Corresponding-author email is compulsory** ("Email address is compulsory for the corresponding author") — 9 pt Courier beneath affiliation. **MISSING in proposal: we do not have a real email; must add before submission.**
- No page numbers, headers, or footers. A4, single column, 2 pages.
- Six keywords, Roman numeral section headings.

---

## 7. Risks & open items

1. **[Open] Corresponding-author email** — template requires it; proposal lacks it. Ask the team for a real address, add beneath affiliation in 9 pt Courier before submission.
2. **Gemini drift / cost** — non-deterministic generations; shared cached completions mitigate; budget API cost early (diagnostic tracks it).
3. **SSMI baseline** — fair reproduction of separate implementation + native planner is high-effort; treat as optional, gated.
4. **ROS/Clio stack weight** — Pangolin v0.8, habitat-sim **v0.3.3** (`WITH_BULLET=1 WITH_CUDA=1 HEADLESS=0 CMAKE_ARGS="-DCMAKE_POLICY_VERSION_MINIMUM=3.5"`), Python **3.9** venv, catkin build with nvblox (needs cmake ≥ 3.27.9), rosdep installs, YOSO weights download, PyKDL 1.5.2, `GEMINI_API_KEY`/`GOOGLE_API_KEY` env. High memory risk → set occlusion check false in `clio.launch`. Keep offline cached-graph replay as the escape hatch.
5. **Evaluator must be ours** — released plotting scripts are hard-coded; replicate ASP's exact thresholds (3.3) for comparability with the 0.05/10% guardrails.
6. **Matching ambiguity** — one-to-one object matching, evaluator-matched unseen-room discovery: implement strictly per ASP thresholds; document any deviation.

---

## 8. Decisions log (why we chose what)

- **Leave-one-scene-out calibration** instead of random split: only 4 scenes, so per-scene generalization is the honest estimate; each reported scene is a held-out fold, eliminating calibration/test leakage.
- **R(x) = mean(1 − p̂) over visible predicted nodes, 0 if none** instead of a count: a count penalizes viewpoints merely for containing more predictions.
- **β=0 calibration-only variant** separates "does calibration alone change the score" from "does the risk term help".
- **AUC over path (not endpoint metrics) for guardrails**: matches the primary outcome; single endpoint is noise.
- **Normalized GED by reference node+edge count** with ASP's node set (object/room only): keeps comparability while making scenes of different sizes comparable.
- **Cached completions shared across policies**: the only way to make a fair comparison when the generator is non-deterministic; also cuts API cost.

---

## 9. First implementation steps (next session)

1. Clone `grasp-lyrl/active_semantic_perception` + submodules; follow Section 3.1 install (Pangolin, catkin workspace, habitat-sim v0.3.3, YOSO weights, PyKDL).
2. Stand up Habitat-Sim with HM3D scene 00069; capture RGB-D + pose at fixed path to validate mapper inputs.
3. Run `exploration_pipeline.py` end-to-end once; cache all artifacts (4.7 schema) — this becomes the baseline corpus.
4. Write the independent evaluator (ASP thresholds) and reproduce ASP's reported metrics on the cached run before touching any new code.
5. Then: validator (Section 4.1) → calibration (4.2) → score (4.3).
