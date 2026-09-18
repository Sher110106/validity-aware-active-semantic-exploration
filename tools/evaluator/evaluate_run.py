#!/usr/bin/env python3
"""
Independent evaluator for ASP replication runs (IMPLEMENTATION_PLAN.md Phase 6).

Reads exported artifacts only - never calls the LLM, never touches the
policy. Reproduces the author's own comparison rules exactly (see graph_io.py,
matching.py, ged.py docstrings for the specific fidelity claims and where
each threshold/rule comes from), while being our own independent
implementation per IMPLEMENTATION_RESEARCH.md section 3.3's decision that
the released plotting scripts are not directly reusable (hard-coded paths,
aggregation choices).

Usage:
    python evaluate_run.py --run <run_dir> --gt <ground_truth_yaml> [--out results.json]

<run_dir> is expected to contain numbered stage subdirectories (0, 1, 2, ...),
each with:
    navigation_stats.json      - {"total_path_length_meters": ..., "total_navigation_time_seconds": ...}
    habitat_scene_graph_original_graph0.yaml   (and/or graph1.yaml)

This mirrors exactly what exploration/scripts/f1_score_plot.py and
ged_score_plot.py expect, since that is the format the pipeline itself
produces. Any deviation found in a real run's directory layout should be
documented here, not silently worked around.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from graph_io import load_eval_graph
from matching import match_objects
from ged import compute_ged, DEFAULT_OBJECT_THRESHOLD, DEFAULT_ROOM_THRESHOLD


def find_stage_dirs(run_dir):
    stages = []
    for entry in os.listdir(run_dir):
        full = os.path.join(run_dir, entry)
        if os.path.isdir(full) and entry.isdigit():
            stages.append((int(entry), full))
    return sorted(stages)


def evaluate_stage(stage_dir, gt_graph, object_threshold, room_threshold, ged_timeout):
    nav_stats_path = os.path.join(stage_dir, "navigation_stats.json")
    graph_paths = [
        os.path.join(stage_dir, "habitat_scene_graph_original_graph0.yaml"),
        os.path.join(stage_dir, "habitat_scene_graph_original_graph1.yaml"),
    ]
    graph_paths = [p for p in graph_paths if os.path.exists(p)]

    if not os.path.exists(nav_stats_path) or not graph_paths:
        return None

    with open(nav_stats_path) as f:
        nav_stats = json.load(f)
    path_length = nav_stats.get("total_path_length_meters")
    nav_time = nav_stats.get("total_navigation_time_seconds")
    if path_length is None:
        return None

    per_graph = []
    for graph_path in graph_paths:
        pred_graph = load_eval_graph(graph_path)
        match_result = match_objects(gt_graph.objects, pred_graph.objects, threshold=object_threshold)
        ged_value, ref_nodes, ref_edges = compute_ged(
            pred_graph, gt_graph, object_threshold=object_threshold,
            room_threshold=room_threshold, timeout=ged_timeout,
        )
        per_graph.append({
            "source_file": os.path.basename(graph_path),
            "precision": match_result.precision,
            "recall": match_result.recall,
            "f1": match_result.f1,
            "true_positives": match_result.true_positives,
            "false_positives": match_result.false_positives,
            "false_negatives": match_result.false_negatives,
            "ged": ged_value,
            "ged_reference_nodes": ref_nodes,
            "ged_reference_edges": ref_edges,
            "ged_normalized": (ged_value / (ref_nodes + ref_edges)) if ged_value is not None and (ref_nodes + ref_edges) > 0 else None,
        })

    def _avg(key):
        values = [g[key] for g in per_graph if g[key] is not None]
        return sum(values) / len(values) if values else None

    return {
        "path_length_m": path_length,
        "navigation_time_s": nav_time,
        "n_graphs_averaged": len(per_graph),
        "precision": _avg("precision"),
        "recall": _avg("recall"),
        "f1": _avg("f1"),
        "ged": _avg("ged"),
        "ged_normalized": _avg("ged_normalized"),
        "per_graph": per_graph,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True, help="Run directory containing numbered stage subdirectories")
    parser.add_argument("--gt", required=True, help="Ground-truth scene graph YAML (habitat_scene_graph_original_graph*.yaml format)")
    parser.add_argument("--object-threshold", type=float, default=DEFAULT_OBJECT_THRESHOLD)
    parser.add_argument("--room-threshold", type=float, default=DEFAULT_ROOM_THRESHOLD)
    parser.add_argument("--ged-timeout", type=float, default=60.0, help="Per-checkpoint GED computation timeout in seconds")
    parser.add_argument("--out", default=None, help="Write JSON results here (default: print to stdout)")
    args = parser.parse_args()

    if not os.path.isdir(args.run):
        print(f"Error: run directory not found: {args.run}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.gt):
        print(f"Error: ground-truth file not found: {args.gt}", file=sys.stderr)
        sys.exit(1)

    gt_graph = load_eval_graph(args.gt)
    if not gt_graph.objects and not gt_graph.rooms:
        print("Error: ground-truth graph has no object/room nodes after filtering.", file=sys.stderr)
        sys.exit(1)

    stage_dirs = find_stage_dirs(args.run)
    if not stage_dirs:
        print(f"Error: no numbered stage subdirectories found under {args.run}", file=sys.stderr)
        sys.exit(1)

    results = {"run_dir": args.run, "ground_truth": args.gt, "stages": {}}
    for stage_num, stage_dir in stage_dirs:
        stage_result = evaluate_stage(stage_dir, gt_graph, args.object_threshold, args.room_threshold, args.ged_timeout)
        if stage_result is None:
            print(f"Warning: stage {stage_num} missing navigation_stats.json or graph YAML(s), skipping.", file=sys.stderr)
            continue
        results["stages"][stage_num] = stage_result
        print(
            f"Stage {stage_num}: path={stage_result['path_length_m']:.2f}m "
            f"F1={stage_result['f1']:.3f} P={stage_result['precision']:.3f} "
            f"R={stage_result['recall']:.3f} GED={stage_result['ged']} "
            f"(normalized={stage_result['ged_normalized']})"
        )

    if not results["stages"]:
        print("Error: no stages produced valid results.", file=sys.stderr)
        sys.exit(1)

    output = json.dumps(results, indent=2, default=str)
    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
        print(f"\nResults written to {args.out}")
    else:
        print("\n" + output)


if __name__ == "__main__":
    main()
