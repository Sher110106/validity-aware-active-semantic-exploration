#!/usr/bin/env python3
"""Held-out tau selection for the support-threshold ablation
(IMPLEMENTATION_PLAN.md section 17 step 2), closing REVIEW_2026-09-14.md's
"support threshold tau is currently tuned on the same reference used for
scoring" finding (audit H5): tau=0.75 was previously picked by eye from a
sweep scored against the only reference graph that existed (00069) - in-
sample selection bias (DEVIATIONS.md #56/#66's H5 note).

Now that all 4 scenes have real reference graphs (DEVIATIONS.md #61-62),
this script implements the review's own prescribed fix exactly: for each
held-out scene, average the OTHER 3 scenes' path-normalized-AUC curve
across the raw-support tau grid {0.0, 0.5, 0.75, 1.0}, pick the tau that
optimizes a criterion using ONLY that 3-scene average, then report the
SELECTED tau's real performance on the held-out scene. The held-out
scene's own curve is never consulted when choosing tau for it - each
scene gets its own independent selection, run over the other 3.

Uses `object_f1` (maximize) and `normalized_ged` (minimize) as two
independent criteria and reports both, rather than picking whichever one
selects the more flattering tau - if they disagree that is itself a
finding worth surfacing, not something to average away.

Reads each scene's `extension_policy_replay_v2_realcalib.json` (produced
by `extension_policy_replay.py`, real LOSO-calibrated ablation, not the
older `_validatorfix.json` uncalibrated-only files) - the same file for
every scene, so tau selection and calibration status are on a consistent
footing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

TAU_GRID = [0.0, 0.5, 0.75, 1.0]
POLICY_PREFIX = "support_threshold_tau_"

SCENE_FILES = {
    "00069": Path("/workspace/runs/scene00069_seed42_25m_20260914_v3/extension_policy_replay_v2_realcalib.json"),
    "00573": Path("/workspace/runs/scene00573_seed42_calib_high32k/extension_policy_replay_v2_realcalib.json"),
    "00853": Path("/workspace/runs/scene00853_seed42_calib_high32k/extension_policy_replay_v2_realcalib.json"),
    "00871": Path("/workspace/runs/scene00871_seed42_calib_high32k/extension_policy_replay_v2_realcalib.json"),
}
# 2026-09-17: kept as-is - this is the original 4-scene diagnostic (one
# low-effort scene, three effort=high/32k-token scenes, a real reasoning-
# effort/token-ceiling confound - see PAPER_ASSESSMENT_2026-09-16.md
# section 3.7c). Never edit this dict for the new uniform-config 3-scene
# matrix run - pass a different `scene_files` to select_and_evaluate()/
# `--scene-files` on the CLI instead, so this original result stays
# exactly reproducible.
DEFAULT_AUC_FIELD = "path_normalized_auc"


def _mean_by_tau(data: Dict[str, Dict[str, Any]], train_scenes: List[str], criterion: str, auc_field: str) -> Dict[float, float]:
    means = {}
    for tau in TAU_GRID:
        key = f"{POLICY_PREFIX}{tau}"
        vals = [
            data[s][auc_field][key][criterion]
            for s in train_scenes
            if data[s].get(auc_field) and key in data[s][auc_field]
        ]
        if vals:
            means[tau] = sum(vals) / len(vals)
    return means


def _is_tie(values_by_tau: Dict[float, float], selected: float, *, atol: float = 1e-9) -> bool:
    """True if any OTHER tau is within atol of the selected tau's value -
    i.e. argmax/argmin broke a tie by grid order (ascending tau) rather
    than picking a strict winner. Callers should treat a tied selection
    as "no discriminating signal in the training scenes", not as a real
    preference for the selected tau."""
    selected_value = values_by_tau[selected]
    return any(abs(v - selected_value) <= atol for t, v in values_by_tau.items() if t != selected)


def select_and_evaluate(scene_files: Dict[str, Path], auc_field: str = DEFAULT_AUC_FIELD) -> Dict[str, Any]:
    """auc_field selects which AUC to select/evaluate on: the default
    "path_normalized_auc" (each scene's own max-observed-path budget,
    the original behavior) or "path_normalized_auc_capped" (a shared
    pre-registered budget_m across all scenes, added 2026-09-17 to
    extension_policy_replay.py specifically so scenes overshooting 120m
    by different amounts are comparable - see that script's own
    2026-09-17 note). Held-out selection logic itself is unchanged.

    2026-09-17: with fewer than 4 scene_files (e.g. the 3-scene final
    matrix, dropping 00871), each fold now trains on len(scene_files)-1
    scenes, not always 3 - the original module docstring's "average the
    OTHER 3 scenes" is only true for the original 4-scene call. Every
    result now records train_scenes explicitly (already did) plus
    n_training_scenes and a tie flag, so a 2-scene fold's selection
    can't be silently read as the same strength of evidence as a
    3-scene one, and a grid-order tie-break can't be silently read as a
    real preference."""
    data = {scene: json.loads(p.read_text()) for scene, p in scene_files.items()}
    results: Dict[str, Any] = {}
    for held_out in data:
        train_scenes = [s for s in data if s != held_out]

        f1_means = _mean_by_tau(data, train_scenes, "object_f1", auc_field)
        ged_means = _mean_by_tau(data, train_scenes, "normalized_ged", auc_field)
        selected_tau_f1 = max(f1_means, key=lambda t: f1_means[t])
        selected_tau_ged = min(ged_means, key=lambda t: ged_means[t])

        def held_out_perf(tau: float) -> Dict[str, float]:
            key = f"{POLICY_PREFIX}{tau}"
            return data[held_out][auc_field].get(key, {})

        results[held_out] = {
            "train_scenes": train_scenes,
            "n_training_scenes": len(train_scenes),
            "auc_field": auc_field,
            "train_mean_object_f1_by_tau": f1_means,
            "train_mean_normalized_ged_by_tau": ged_means,
            "selected_tau_by_f1": selected_tau_f1,
            "selected_tau_by_ged": selected_tau_ged,
            "selected_tau_by_f1_is_tie": _is_tie(f1_means, selected_tau_f1),
            "selected_tau_by_ged_is_tie": _is_tie(ged_means, selected_tau_ged),
            "criteria_agree": selected_tau_f1 == selected_tau_ged,
            "held_out_performance_at_f1_selected_tau": held_out_perf(selected_tau_f1),
            "held_out_performance_at_ged_selected_tau": held_out_perf(selected_tau_ged),
            "held_out_official_performance": data[held_out][auc_field].get("official", {}),
        }
    return results


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--scene-files", type=json.loads, default=None,
        help='JSON object {"scene_id": "path/to/extension_policy_replay_output.json"} - overrides the default 4-scene short-run diagnostic set (SCENE_FILES) without editing it.',
    )
    parser.add_argument("--auc-field", default=DEFAULT_AUC_FIELD, choices=["path_normalized_auc", "path_normalized_auc_capped"])
    parser.add_argument("--output", type=Path, default=Path("/workspace/runs/tau_selection_loso_results.json"))
    args = parser.parse_args()

    scene_files = {scene: Path(path) for scene, path in args.scene_files.items()} if args.scene_files else SCENE_FILES
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing {args.output} - pass a different --output")

    results = select_and_evaluate(scene_files, auc_field=args.auc_field)
    print(json.dumps(results, indent=2))
    args.output.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
