#!/usr/bin/env python3
"""Extension-replay ablation over the frozen v3 cache (IMPLEMENTATION_PLAN.md
section 17 step 2): compare official ASP, filter-only, support-threshold-only
(uncalibrated), and filter+support-threshold on the SAME cached ensemble
completions, scored against a real ground-truth reference graph.

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

"support-threshold-only" and "filter+support-threshold" are UNCALIBRATED
(calibrator=None; see scoring.py and support_policy.py for why real
leave-one-scene-out calibration isn't computable with only one scene's
ground-truth graph). Every record carries an explicit calibration-status
block - never read "support-threshold" results as a calibration result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from asp_offline.author_io import load_author_graph
from asp_offline.evaluator import area_under_curve, evaluate_graph
from asp_offline.support_policy import UNCALIBRATED_STATUS, support_filtered_graph
from asp_offline.validator import ValidationConfig, validate_completion

LLM_ENSEMBLE_COUNT = 4
DEFAULT_TAU_GRID = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0]


def _scene_completion_paths(stage_dir: Path, scene_index: int) -> List[Path]:
    lo, hi = scene_index * LLM_ENSEMBLE_COUNT, scene_index * LLM_ENSEMBLE_COUNT + LLM_ENSEMBLE_COUNT
    paths = []
    for graph_id in range(lo, hi):
        p = stage_dir / f"habitat_scene_graph_new_graph_{graph_id}.yaml"
        if p.exists():
            paths.append(p)
    return paths


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


def score_scene(stage_dir: Path, scene_index: int, reference: Mapping[str, Any], config: ValidationConfig, tau_grid: Sequence[float]) -> Dict[str, Any]:
    observed_path = stage_dir / f"habitat_scene_graph_original_graph{scene_index}.yaml"
    observed = load_author_graph(observed_path, observed=True)
    completion_paths = _scene_completion_paths(stage_dir, scene_index)
    completions = [load_author_graph(p) for p in completion_paths]
    ensemble = completions  # match_hypotheses' own denominator - see support_policy.py

    per_completion: Dict[str, List[Dict[str, Any]]] = {"official": [], "filter_only": []}
    for tau in tau_grid:
        per_completion[f"support_threshold_tau_{tau}"] = []
        per_completion[f"filter_plus_support_threshold_tau_{tau}"] = []

    for completion in completions:
        official = _official_graph(observed, completion)
        per_completion["official"].append(evaluate_graph(official, reference))

        filtered_graph, validation = _filter_only_graph(observed, completion, config)
        per_completion["filter_only"].append(evaluate_graph(filtered_graph, reference))

        for tau in tau_grid:
            support_graph = support_filtered_graph(observed, completion, ensemble, tau)
            per_completion[f"support_threshold_tau_{tau}"].append(evaluate_graph(support_graph, reference))

            filtered_predicted_ids = {n["id"] for n in filtered_graph["nodes"] if not n.get("observed", False)}
            combined_nodes = [n for n in support_graph["nodes"] if n.get("observed", False) or n["id"] in filtered_predicted_ids]
            combined_ids = {n["id"] for n in combined_nodes}
            combined_edges = [e for e in support_graph["edges"] if e["source"] in combined_ids and e["target"] in combined_ids]
            combined_graph = {"nodes": combined_nodes, "edges": combined_edges}
            per_completion[f"filter_plus_support_threshold_tau_{tau}"].append(evaluate_graph(combined_graph, reference))

    def _avg(rows: List[Dict[str, float]]) -> Dict[str, float]:
        if not rows:
            return {}
        keys = rows[0].keys()
        return {k: sum(r[k] for r in rows) / len(rows) for k in keys}

    return {
        "scene_index": scene_index,
        "completion_count": len(completions),
        "policies": {name: _avg(rows) for name, rows in per_completion.items()},
    }


def replay(run_dir: Path, reference_path: Path, tau_grid: Sequence[float] = DEFAULT_TAU_GRID) -> Dict[str, Any]:
    reference = load_author_graph(reference_path, observed=True)
    config = ValidationConfig(allow_parsed_mapping=True)
    stage_dirs = sorted((d for d in run_dir.iterdir() if d.is_dir() and d.name.isdigit()), key=lambda d: int(d.name))

    stages: List[Dict[str, Any]] = []
    for stage_dir in stage_dirs:
        stage_num = int(stage_dir.name)
        nav_stats_path = stage_dir / "navigation_stats.json"
        path_m = None
        if nav_stats_path.exists():
            path_m = json.loads(nav_stats_path.read_text()).get("total_path_length_meters")
        scenes = [score_scene(stage_dir, i, reference, config, tau_grid) for i in (0, 1) if (stage_dir / f"habitat_scene_graph_original_graph{i}.yaml").exists()]

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

    aucs: Dict[str, Dict[str, float]] = {}
    rows_with_path = [s for s in stages if s["path_m"] is not None]
    if rows_with_path:
        budget_m = max(s["path_m"] for s in rows_with_path)
        policy_names = rows_with_path[0]["policies"].keys()
        for name in policy_names:
            metric_rows = [{"path_m": s["path_m"], **s["policies"][name]} for s in rows_with_path if name in s["policies"]]
            if not metric_rows:
                continue
            aucs[name] = {
                metric: area_under_curve(metric_rows, metric, budget_m=budget_m)
                for metric in ("object_precision", "object_recall", "object_f1", "normalized_ged")
            }

    return {
        "run_dir": str(run_dir),
        "reference": str(reference_path),
        "tau_grid": list(tau_grid),
        "calibration": dict(UNCALIBRATED_STATUS),
        "note": (
            "official/filter_only score the LLM's raw ensemble predictions "
            "(never merged into the pipeline's own tracked graph - see module "
            "docstring) filtered by each policy, not the pipeline's real "
            "navigation trajectory. support_threshold_* and "
            "filter_plus_support_threshold_* are UNCALIBRATED (see "
            "'calibration' field) - do not read them as the paper's proposed "
            "calibration result."
        ),
        "stages": stages,
        "path_normalized_auc": aucs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True, type=Path, help="stages/ directory of a run (e.g. scene00069_seed42_25m_20260914_v3/stages)")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--tau-grid", type=float, nargs="*", default=DEFAULT_TAU_GRID)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = replay(args.run, args.reference, args.tau_grid)
    text = json.dumps(payload, indent=2, default=str)
    if args.output:
        args.output.write_text(text + "\n")
        print(f"Results written to {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
