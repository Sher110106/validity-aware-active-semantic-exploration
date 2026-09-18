#!/usr/bin/env python3
"""Extension-replay ablation over the frozen v3 cache (IMPLEMENTATION_PLAN.md
section 17 step 2): compare official ASP, filter-only, support-threshold-only,
and filter+support-threshold (each of the latter two in both a raw/
uncalibrated and a real-LOSO-calibrated variant, see below) on the SAME
cached ensemble completions, scored against a real ground-truth reference
graph.

What "official ASP" means here, confirmed by reading the pinned
llm_completion.py directly rather than guessing (2026-09-14): the baseline
pipeline's tracked/scored graph (habitat_scene_graph_original_graph{0,1}.yaml)
is produced by _preprocess_dsg() converting the raw SLAM/DSG output BEFORE any
LLM completion runs - it is never a merge of the LLM's proposed completions.
The 8 raw completions (habitat_scene_graph_new_graph_0..7.yaml, 2 scenes x 4
ensemble members, graph_id = scene_index*4 + ensemble_index) feed only
uncertainty_calc.select_next_target() for viewpoint scoring. So this ablation
does NOT compare four ways of merging predictions into the tracked graph
(the baseline never merges predictions into it at all) - it compares four
ways of FILTERING the LLM's raw predictions before scoring them against
ground truth, using shared completions across all four policies. This
answers: how good are the LLM's own proposals under each policy, not how
the pipeline's real trajectory would change (that needs a live re-run,
which is explicitly NOT what this step does - see IMPLEMENTATION_PLAN.md
section 17 step 1's "replay").

"support-threshold-only" and "filter+support-threshold" run CALIBRATED by
default now (2026-09-15, closing REVIEW_2026-09-14.md's audit finding H2):
once all 4 scenes had real ground-truth reference graphs (DEVIATIONS.md
#61-62), a real leave-one-scene-out calibrator became fittable - `replay()`
fits one held out on whichever scene `--reference` names, trained on the
other 3, via `support_policy.fit_loso_calibrator` (the SAME implementation
`decision_replay.py` uses and validated end to end - not a second,
independently-written fit that could silently disagree with it). If
`--reference` names a scene absent from SCENE_CALIBRATION_CONFIGS, this
falls back to UNCALIBRATED_STATUS rather than guessing at a calibrator.
Every record carries an explicit calibration-status block - check
`calibration.status` (`LOSO_CALIBRATED` vs `UNCALIBRATED_PROVISIONAL`)
before reading "support-threshold" results as a calibration result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from asp_offline.author_io import load_author_graph
from asp_offline.evaluator import area_under_curve, evaluate_graph
from asp_offline.support_policy import UNCALIBRATED_STATUS, fit_loso_calibrator, support_filtered_graph
from asp_offline.validator import ValidationConfig, validate_completion

LLM_ENSEMBLE_COUNT = 4

# Must match decision_replay.py's RUN_DIR/REFERENCE_PATH/OTHER_SCENES
# exactly (DEVIATIONS.md #61-62) - these are the 4 scenes with a real
# ground-truth reference graph, the full LOSO calibration set.
SCENE_CALIBRATION_CONFIGS = {
    "00069": {
        "run": "/workspace/runs/scene00069_seed42_25m_20260914_v3/stages",
        "reference": "/workspace/runs/scene00069_frontier_reference/stages/25/habitat_scene_graph_original_graph0.yaml",
    },
    "00573": {
        "run": "/workspace/runs/scene00573_seed42_calib_high32k/stages",
        "reference": "/workspace/runs/scene00573_frontier_reference/stages/53/habitat_scene_graph_original_graph0.yaml",
    },
    "00853": {
        "run": "/workspace/runs/scene00853_seed42_calib_high32k/stages",
        "reference": "/workspace/runs/scene00853_frontier_reference/stages/33/habitat_scene_graph_original_graph0.yaml",
    },
    "00871": {
        "run": "/workspace/runs/scene00871_seed42_calib_high32k/stages",
        "reference": "/workspace/runs/scene00871_frontier_reference/stages/54/habitat_scene_graph_original_graph0.yaml",
    },
}


def _resolve_calibrator(reference_path: Path) -> Tuple[Optional[Callable[[float], float]], Dict[str, Any]]:
    """Real LOSO calibrator held out on whichever scene `reference_path`
    names, or (None, UNCALIBRATED_STATUS) if that scene isn't one of the
    4 with a ground-truth reference graph - matched by resolved path so
    this works regardless of the caller's cwd."""
    resolved = str(Path(reference_path).resolve())
    held_out = next((scene for scene, cfg in SCENE_CALIBRATION_CONFIGS.items()
                      if str(Path(cfg["reference"]).resolve()) == resolved), None)
    if held_out is None:
        status = dict(UNCALIBRATED_STATUS)
        status["note"] = f"{reference_path} is not one of SCENE_CALIBRATION_CONFIGS' 4 scenes - no LOSO fold to hold it out on."
        return None, status
    return fit_loso_calibrator(SCENE_CALIBRATION_CONFIGS, held_out)
# 2026-09-14 correction (REVIEW_2026-09-14.md): support is hits / 4 (see
# support_policy.py's module docstring for why 4, not 8). Under a fixed K=4
# denominator, support only ever takes values {0, .25, .5, .75, 1.0} - a tau
# grid finer than that oversells a 4-point sweep as continuous, and every
# completion is in its own denominator so tau in [0, .25] is always a no-op.
# Collapsed per the review's advisor consult; the old 9-point grid is kept
# only as DEFAULT_TAU_GRID_LEGACY for reproducing the pre-correction numbers.
DEFAULT_TAU_GRID = [0.0, 0.5, 0.75, 1.0]
DEFAULT_TAU_GRID_LEGACY = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0]


def _scene_completion_paths(stage_dir: Path, scene_index: int) -> Tuple[List[Path], List[int]]:
    """Returns (paths that exist, graph_ids that were expected but missing)."""
    lo, hi = scene_index * LLM_ENSEMBLE_COUNT, scene_index * LLM_ENSEMBLE_COUNT + LLM_ENSEMBLE_COUNT
    paths, missing = [], []
    for graph_id in range(lo, hi):
        p = stage_dir / f"habitat_scene_graph_new_graph_{graph_id}.yaml"
        if p.exists():
            paths.append(p)
        else:
            missing.append(graph_id)
    return paths, missing


def _merge_observed(observed: Mapping[str, Any], predicted_nodes: List[Dict[str, Any]], predicted_edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"nodes": list(observed["nodes"]) + predicted_nodes, "edges": list(observed["edges"]) + predicted_edges}


def _official_graph(observed: Mapping[str, Any], completion: Mapping[str, Any]) -> Dict[str, Any]:
    """Raw, unfiltered completion merged onto observed - the "if every
    prediction were trusted wholesale" control."""
    predicted_nodes = [n for n in completion["nodes"] if not n.get("observed", False)]
    return _merge_observed(observed, predicted_nodes, completion["edges"])


def _filter_only_graph(observed: Mapping[str, Any], completion: Mapping[str, Any], config: ValidationConfig) -> Tuple[Dict[str, Any], ValidationConfig]:
    result = validate_completion(completion, observed, config)
    return result.graph, result


def score_scene(
    stage_dir: Path,
    scene_index: int,
    reference: Mapping[str, Any],
    config: ValidationConfig,
    tau_grid: Sequence[float],
    *,
    calibrator: Optional[Callable[[float], float]] = None,
    calibrated_tau_grid: Optional[Sequence[Tuple[float, float]]] = None,
) -> Dict[str, Any]:
    """`calibrated_tau_grid` is [(raw_tau, calibrator(raw_tau)), ...] - the
    SAME raw-support levels as `tau_grid`, expressed as calibrated-
    probability cutoffs, so the calibrated policies stay one-to-one
    comparable with their uncalibrated counterparts rather than sweeping
    an unrelated set of cutoffs. Required together with `calibrator`
    (both None = no calibrated policies computed for this scene)."""
    observed_path = stage_dir / f"habitat_scene_graph_original_graph{scene_index}.yaml"
    observed = load_author_graph(observed_path, observed=True)
    completion_paths, missing_ids = _scene_completion_paths(stage_dir, scene_index)
    completions = [load_author_graph(p) for p in completion_paths]
    ensemble = completions  # match_hypotheses' own denominator input - the EXPECTED size (LLM_ENSEMBLE_COUNT) is passed separately below, not inferred from len(ensemble)

    per_completion: Dict[str, List[Dict[str, Any]]] = {"official": [], "filter_only": []}
    for tau in tau_grid:
        per_completion[f"support_threshold_tau_{tau}"] = []
        per_completion[f"filter_plus_support_threshold_tau_{tau}"] = []
    if calibrator is not None:
        for raw_tau, _ in calibrated_tau_grid:
            per_completion[f"support_threshold_calibrated_tau_{raw_tau}"] = []
            per_completion[f"filter_plus_support_threshold_calibrated_tau_{raw_tau}"] = []

    for completion in completions:
        official = _official_graph(observed, completion)
        per_completion["official"].append(evaluate_graph(official, reference))

        filtered_graph, validation = _filter_only_graph(observed, completion, config)
        per_completion["filter_only"].append(evaluate_graph(filtered_graph, reference))
        filtered_predicted_ids = {n["id"] for n in filtered_graph["nodes"] if not n.get("observed", False)}

        for tau in tau_grid:
            support_graph = support_filtered_graph(observed, completion, ensemble, tau, expected_size=LLM_ENSEMBLE_COUNT)
            per_completion[f"support_threshold_tau_{tau}"].append(evaluate_graph(support_graph, reference))

            combined_nodes = [n for n in support_graph["nodes"] if n.get("observed", False) or n["id"] in filtered_predicted_ids]
            combined_ids = {n["id"] for n in combined_nodes}
            combined_edges = [e for e in support_graph["edges"] if e["source"] in combined_ids and e["target"] in combined_ids]
            combined_graph = {"nodes": combined_nodes, "edges": combined_edges}
            per_completion[f"filter_plus_support_threshold_tau_{tau}"].append(evaluate_graph(combined_graph, reference))

        if calibrator is not None:
            for raw_tau, calibrated_cutoff in calibrated_tau_grid:
                cal_support_graph = support_filtered_graph(
                    observed, completion, ensemble, calibrated_cutoff,
                    expected_size=LLM_ENSEMBLE_COUNT, calibrator=calibrator,
                )
                per_completion[f"support_threshold_calibrated_tau_{raw_tau}"].append(evaluate_graph(cal_support_graph, reference))

                combined_nodes = [n for n in cal_support_graph["nodes"] if n.get("observed", False) or n["id"] in filtered_predicted_ids]
                combined_ids = {n["id"] for n in combined_nodes}
                combined_edges = [e for e in cal_support_graph["edges"] if e["source"] in combined_ids and e["target"] in combined_ids]
                combined_graph = {"nodes": combined_nodes, "edges": combined_edges}
                per_completion[f"filter_plus_support_threshold_calibrated_tau_{raw_tau}"].append(evaluate_graph(combined_graph, reference))

    def _avg(rows: List[Dict[str, float]]) -> Dict[str, float]:
        if not rows:
            return {}
        keys = rows[0].keys()
        return {k: sum(r[k] for r in rows) / len(rows) for k in keys}

    return {
        "scene_index": scene_index,
        "completion_count": len(completions),
        "expected_completion_count": LLM_ENSEMBLE_COUNT,
        "missing_completion_ids": missing_ids,
        "policies": {name: _avg(rows) for name, rows in per_completion.items()},
    }


def replay(
    run_dir: Path,
    reference_path: Path,
    tau_grid: Sequence[float] = DEFAULT_TAU_GRID,
    budget_m: Optional[float] = None,
) -> Dict[str, Any]:
    reference = load_author_graph(reference_path, observed=True)
    config = ValidationConfig(allow_parsed_mapping=True)
    stage_dirs = sorted((d for d in run_dir.iterdir() if d.is_dir() and d.name.isdigit()), key=lambda d: int(d.name))

    calibrator, calibration_status = _resolve_calibrator(reference_path)
    calibrated_tau_grid = [(t, calibrator(t)) for t in tau_grid] if calibrator is not None else None

    stages: List[Dict[str, Any]] = []
    for stage_dir in stage_dirs:
        stage_num = int(stage_dir.name)
        nav_stats_path = stage_dir / "navigation_stats.json"
        path_m = None
        if nav_stats_path.exists():
            path_m = json.loads(nav_stats_path.read_text()).get("total_path_length_meters")
        scenes = [
            score_scene(stage_dir, i, reference, config, tau_grid, calibrator=calibrator, calibrated_tau_grid=calibrated_tau_grid)
            for i in (0, 1) if (stage_dir / f"habitat_scene_graph_original_graph{i}.yaml").exists()
        ]

        stage_policies: Dict[str, Dict[str, float]] = {}
        policy_names = scenes[0]["policies"].keys() if scenes else []
        for name in policy_names:
            rows = [s["policies"][name] for s in scenes if s["policies"].get(name)]
            if not rows:
                continue
            keys = rows[0].keys()
            stage_policies[name] = {k: sum(r[k] for r in rows) / len(rows) for k in keys}

        stages.append({
            "stage": stage_num,
            "path_m": path_m,
            "scenes": scenes,
            "policies": stage_policies,
        })

    # 2026-09-17: budget_m used to always default to this run's own max
    # observed path, so three scenes overshooting 120m by different
    # amounts (125.325/121.875/... m) each normalized their AUC over a
    # different range - not comparable to each other or to the
    # pre-registered 0-120m contract in IMPLEMENTATION_PLAN.md section 13.
    # Additive fix, decided before looking at any of tonight's numbers:
    # keep the existing max-path AUC exactly as before (nothing that
    # reads path_normalized_auc changes), and additionally compute the
    # same metrics capped at an explicit budget_m when the caller passes
    # one, reported alongside under a separate key.
    aucs: Dict[str, Dict[str, float]] = {}
    aucs_capped: Dict[str, Dict[str, float]] = {}
    rows_with_path = [s for s in stages if s["path_m"] is not None]
    max_path_m = max((s["path_m"] for s in rows_with_path), default=None)
    if rows_with_path:
        policy_names = rows_with_path[0]["policies"].keys()
        for name in policy_names:
            metric_rows = [{"path_m": s["path_m"], **s["policies"][name]} for s in rows_with_path if name in s["policies"]]
            if not metric_rows:
                continue
            aucs[name] = {
                metric: area_under_curve(metric_rows, metric, budget_m=max_path_m)
                for metric in ("object_precision", "object_recall", "object_f1", "normalized_ged")
            }
            if budget_m is not None:
                aucs_capped[name] = {
                    metric: area_under_curve(metric_rows, metric, budget_m=budget_m)
                    for metric in ("object_precision", "object_recall", "object_f1", "normalized_ged")
                }

    return {
        "run_dir": str(run_dir),
        "reference": str(reference_path),
        "tau_grid": list(tau_grid),
        "support_denominator": {
            "mode": "expected_per_scene_track",
            "expected_size": LLM_ENSEMBLE_COUNT,
            "note": (
                "support = hits / 4 always, never hits / (surviving completion "
                "count) - see support_policy.py's module docstring. Any JSON "
                "without this field predates the 2026-09-14 denominator fix "
                "(REVIEW_2026-09-14.md) and used hits / len(available), which "
                "inflates support on stages with more parsing failures."
            ),
        },
        "calibrated_tau_grid": [{"raw_tau": t, "calibrated_cutoff": c} for t, c in calibrated_tau_grid] if calibrated_tau_grid is not None else None,
        "calibration": calibration_status,
        "note": (
            "official/filter_only score the LLM's raw ensemble predictions "
            "(never merged into the pipeline's own tracked graph - see module "
            "docstring) filtered by each policy, not the pipeline's real "
            "navigation trajectory. support_threshold_tau_* and "
            "filter_plus_support_threshold_tau_* are always UNCALIBRATED raw-"
            "support cutoffs - do not read them as the paper's proposed "
            "calibration result regardless of 'calibration' below. "
            "support_threshold_calibrated_tau_* and "
            "filter_plus_support_threshold_calibrated_tau_* are present only "
            "when 'calibration'.status == 'LOSO_CALIBRATED', and ARE the "
            "calibration result: the same raw-support levels as *_tau_*, "
            "re-expressed as calibrated-probability cutoffs via a real leave-"
            "one-scene-out fit (see 'calibration' for which scenes trained it "
            "and 'calibrated_tau_grid' for the raw-tau -> cutoff mapping used)."
        ),
        "stages": stages,
        "path_normalized_auc": aucs,
        "path_normalized_auc_budget_m": max_path_m,
        "path_normalized_auc_capped": aucs_capped if budget_m is not None else None,
        "path_normalized_auc_capped_budget_m": budget_m,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True, type=Path, help="stages/ directory of a run (e.g. scene00069_seed42_25m_20260914_v3/stages)")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--tau-grid", type=float, nargs="*", default=DEFAULT_TAU_GRID)
    parser.add_argument(
        "--budget-m",
        type=float,
        default=None,
        help=(
            "Pre-registered path budget (e.g. 120.0, IMPLEMENTATION_PLAN.md "
            "section 13's contract) to additionally cap the AUC at, reported "
            "alongside the run's own max-path AUC without changing it."
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = replay(args.run, args.reference, args.tau_grid, budget_m=args.budget_m)
    text = json.dumps(payload, indent=2, default=str)
    if args.output:
        args.output.write_text(text + "\n")
        print(f"Results written to {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
