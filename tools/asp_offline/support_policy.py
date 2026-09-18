"""Support-threshold policy for the extension-replay ablation, uncalibrated
and (since 2026-09-15) real-LOSO-calibrated.

IMPLEMENTATION_PLAN.md section 17 step 2 compares four policies on the same
cached ensemble completions: official ASP, filter-only (the structural
validator, validator.py), support-threshold-only, and filter+support-
threshold. This module implements the two support-threshold variants, each
in both an uncalibrated and a calibrated flavor.

Per IMPLEMENTATION_RESEARCH.md section 4.2, raw support s_j is the fraction
of K completions containing a matching node (by label + parent room +
spatial threshold - the same hypothesis-matching rule calibration.py already
uses via match_hypotheses). Thresholding raw, uncalibrated support (`tau` in
{0, .25, .5, .75, 1.0}, `calibrator=None`) is a real, nameable policy in its
own right - the control a fitted calibrator must beat - not a placeholder
for one it can't yet compute.

Real calibration IS computable now: all 4 scenes (00069, 00573, 00853,
00871) have a ground-truth reference graph (DEVIATIONS.md #61-62), so
`fit_loso_calibrator` below fits a genuine leave-one-scene-out isotonic
calibrator per held-out scene and `support_filtered_graph`'s `calibrator`
parameter maps `tau` into calibrated-probability space when one is passed.
`extension_policy_replay.py` wires this in for real (audit finding H2,
REVIEW_2026-09-14.md - the earlier claim that it was already wired in was
false, see DEVIATIONS.md #62's correction and #66).

K is 4, per scene-track, not a pooled 8 (2026-09-14 correction, see
REVIEW_2026-09-14.md and DEVIATIONS.md). The pipeline's config has
LLM_ENSEMBLE_COUNT=4 and SCENE_GRAPH_COUNT=2: at every checkpoint the
pipeline tracks TWO independent scene-graph instances (graph0, graph1),
each completed by its own 4-member ensemble and scored separately, then
averaged. The paper's stated "m=4 completions x 2 scene graphs = 8
samples" is exactly this - 4-per-track x 2 tracks, never a pooled
8-member set. Pooling would also be wrong, not just architecturally
untidy: room ids are a raw per-graph integer namespace assigned
independently per track (author_io.py), so the same id in graph0 and
graph1 can name two different rooms in two different places - comparing
across tracks on `parent_room` would silently match unrelated rooms.
`expected_size` is therefore always 4 at every call site in this module
and in extension_policy_replay.py, never 8 and never len(ensemble).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from .author_io import load_author_graph
from .calibration import fit_leave_one_scene_out, label_hypotheses_against_reference, match_hypotheses, _hypotheses
from .models import Graph, Hypothesis
from .validator import _edges, _graph, _nodes


def support_filtered_graph(
    observed: Mapping[str, Any],
    completion: Mapping[str, Any],
    ensemble: Sequence[Mapping[str, Any]],
    tau: float,
    *,
    expected_size: int,
    object_threshold: float = 0.5,
    room_threshold: float = 4.0,
    calibrator: Optional[Callable[[float], float]] = None,
) -> Dict[str, Any]:
    """One completion's predicted nodes, kept only where support >= tau.

    `ensemble` is the completions that survived upstream parsing for this
    scene-track (may be fewer than `expected_size`); `completion` itself is
    included in its own denominator, matching match_hypotheses' existing
    semantics (calibration.py) exactly. `expected_size` is the intended
    per-scene-track ensemble size (LLM_ENSEMBLE_COUNT) - support is always
    hits / expected_size, never hits / len(ensemble); see calibration.py's
    match_hypotheses docstring for why.

    `calibrator` is None by default (raw, uncalibrated support - `tau` is
    then a raw-support cutoff in {0, .25, .5, .75, 1.0}). When a fitted
    `IsotonicCalibrator` is passed, each hypothesis's raw support is mapped
    through it first and `tau` is then a CALIBRATED-PROBABILITY cutoff, not
    a raw-support one - same convention as scoring.py's score_viewpoint.
    Because the calibrator is a monotone function of a small discrete
    domain (raw support only takes 5 values under a fixed K=4), passing a
    calibrator can only RELABEL or MERGE raw-support levels, never reorder
    them: for every calibrated tau there is some raw-support tau (or a
    contiguous range of them, if the fitted calibrator's PAVA step merged
    several levels into one block - real behavior, not a bug, when the
    calibration data shows no discriminative signal between adjacent
    levels) that selects the identical kept/dropped node set. Verified
    directly on real data (2026-09-15): 3 of 4 scenes' leave-one-scene-out
    folds kept all 4 support levels distinct; scene 00573's fold merged
    0.25/0.5/0.75 into one calibrated value (0.0047) because that fold's
    training data (the other 3 scenes) showed no real increase across
    that range - a calibrated tau at that value reproduces raw-tau=0.25's
    (the least restrictive merged level's) behavior, not raw-tau=0.5 or
    0.75's specifically. See DEVIATIONS.md #61-62 for the full picture,
    including why this project treats that as the honest, disclosed shape
    of calibration in this static-filtering ablation, not something to
    work around.
    """
    predicted_hypotheses = _hypotheses(completion, include_observed=False)
    scored = match_hypotheses(
        predicted_hypotheses, list(ensemble), expected_size=expected_size,
        object_threshold=object_threshold, room_threshold=room_threshold,
    )
    if calibrator is not None:
        kept_ids = {h.node_id for h in scored if calibrator(h.support) >= tau}
    else:
        kept_ids = {h.node_id for h in scored if h.support >= tau}
    observed_nodes = _nodes(observed, observed=True)
    predicted_nodes = [n for n in _nodes(completion, observed=False) if n.id in kept_ids]
    kept_node_ids = {n.id for n in observed_nodes} | kept_ids
    edges = [e for e in _edges(completion) if e.source in kept_node_ids and e.target in kept_node_ids]
    edges += [e for e in _edges(observed) if e.source in kept_node_ids and e.target in kept_node_ids]
    graph: Graph = _graph(observed_nodes + predicted_nodes, edges, observed)
    graph["support_threshold"] = {
        "tau": tau,
        "calibrated": calibrator is not None,
        "expected_size": expected_size,
        "available": len(ensemble),
        "missing": expected_size - len(ensemble),
        "kept": len(predicted_nodes),
        "dropped": len(predicted_hypotheses) - len(predicted_nodes),
    }
    return graph


def support_scores(
    completion: Mapping[str, Any],
    ensemble: Sequence[Mapping[str, Any]],
    *,
    expected_size: int,
    object_threshold: float = 0.5,
    room_threshold: float = 4.0,
) -> List[Hypothesis]:
    """Raw (uncalibrated) support per predicted node in `completion` - for inspection/reporting."""
    predicted_hypotheses = _hypotheses(completion, include_observed=False)
    return match_hypotheses(
        predicted_hypotheses, list(ensemble), expected_size=expected_size,
        object_threshold=object_threshold, room_threshold=room_threshold,
    )


UNCALIBRATED_STATUS = {
    "method": "none",
    "fitted_on_scenes": [],
    "held_out": False,
    "loso_scenes_available": 1,
    "loso_scenes_required": 4,
    "status": "UNCALIBRATED_PROVISIONAL",
}
"""Stamp this (or a copy with `loso_scenes_available` updated) into every
support-threshold-policy output record, per the Opus advisor's review of
this ablation (2026-09-14): the plan's "calibration-only"/"combined"
language must never appear unqualified next to a result produced with
calibrator=None. See scoring.py and DEVIATIONS.md for the full reasoning."""


def _scene_track_paths(stage_dir: Path, scene_index: int, expected_size: int) -> List[Path]:
    lo, hi = scene_index * expected_size, scene_index * expected_size + expected_size
    return [p for gid in range(lo, hi) if (p := stage_dir / f"habitat_scene_graph_new_graph_{gid}.yaml").exists()]


def collect_calibration_samples(run_dir: Any, reference_path: Any, *, expected_size: int = 4) -> List[Tuple[float, int, str]]:
    """(raw_support, label, kind) triples for every predicted node across
    every stage/track of one scene's calibration-data-collection run,
    labeled against that scene's real reference graph via
    `label_hypotheses_against_reference`. Same recipe as
    `decision_replay.py`'s `collect_samples` (DEVIATIONS.md #61-62),
    factored out here so both callers fit calibrators from one shared
    implementation instead of two that could silently drift apart. `kind`
    ("room" or "object", from Hypothesis.kind) lets callers separate the
    two populations for reporting - see `fit_loso_calibrator`'s docstring
    (audit finding H1, REVIEW_2026-09-14.md) for why pooling them in the
    single fitted calibrator misrepresented both."""
    reference = load_author_graph(Path(reference_path), observed=True)
    run_dir = Path(run_dir)
    stage_dirs = sorted((d for d in run_dir.iterdir() if d.is_dir() and d.name.isdigit()), key=lambda d: int(d.name))
    samples: List[Tuple[float, int, str]] = []
    for stage_dir in stage_dirs:
        for scene_index in (0, 1):
            paths = _scene_track_paths(stage_dir, scene_index, expected_size)
            if not paths:
                continue
            completions = [load_author_graph(p) for p in paths]
            for completion in completions:
                scored = support_scores(completion, completions, expected_size=expected_size)
                labels = label_hypotheses_against_reference(scored, reference)
                samples.extend((h.support, label, h.kind) for h, label in zip(scored, labels))
    return samples


def fit_loso_calibrator(scene_configs: Mapping[str, Mapping[str, Any]], held_out_scene: str, *, expected_size: int = 4) -> Tuple[Callable[[float], float], Dict[str, Any]]:
    """Real leave-one-scene-out calibrator for `held_out_scene`, trained on
    every OTHER scene in `scene_configs` (each a {"run": ..., "reference":
    ...} mapping) - the same recipe validated end-to-end in
    `decision_replay.py` (DEVIATIONS.md #61-62/#65: gate_check.py-verified
    against the live pipeline, real LOSO fit over the other 3 scenes'
    2829 hypotheses). `held_out_scene`'s own data never enters training.

    The FITTED CALIBRATOR returned is still one map over pooled room+
    object samples - unchanged filtering behavior from before this
    docstring's 2026-09-15 update. What changed (audit finding H1,
    REVIEW_2026-09-14.md): status_dict now ALSO reports each kind's own
    sample/positive count separately (status["by_kind"]), because on real
    data the two populations do not carry the same signal - rooms (16
    samples, 8 positives in the 00069 fold) carry essentially all of the
    positive signal that produces the pooled fit's "45-56% chance correct
    at unanimity" headline (DEVIATIONS.md #62), while objects (39 samples
    at support>=0.75) showed ZERO positives in that same fold. A single
    pooled probability describes neither population correctly on its
    own - report status["by_kind"] alongside any pooled-calibrator number
    rather than repeating the "chance correct" framing unqualified.
    Splitting the FILTER itself (not just the report) into two per-kind
    calibrators is a larger, not-yet-implemented change (it needs a
    principled way to pick one shared probability tau across two
    differently-scaled populations); this function deliberately does not
    attempt that yet - see the surrounding audit-response notes for why.

    Returns (calibrator, status_dict); status_dict replaces
    UNCALIBRATED_STATUS wholesale in a result record - it carries real
    fitted_on_scenes/n_training_samples/n_training_positives (pooled) plus
    by_kind (split) instead of the placeholder's empty/zero values, so a
    reader can tell a real LOSO fit from the uncalibrated control, and
    tell which kind actually drove it, without cross-referencing code."""
    if held_out_scene not in scene_configs:
        raise ValueError(f"{held_out_scene!r} missing from scene_configs")
    scene_samples = {
        scene: collect_calibration_samples(cfg["run"], cfg["reference"], expected_size=expected_size)
        for scene, cfg in scene_configs.items()
    }
    pooled_scene_samples = {scene: [(s, y) for s, y, _ in triples] for scene, triples in scene_samples.items()}
    folds = fit_leave_one_scene_out(pooled_scene_samples)
    fold = folds[held_out_scene]
    train_scenes = [s for s in scene_configs if s != held_out_scene]
    n_training_samples = sum(len(pooled_scene_samples[s]) for s in train_scenes)
    n_training_positives = sum(sum(1 for _, y in pooled_scene_samples[s] if y) for s in train_scenes)

    by_kind: Dict[str, Dict[str, int]] = {}
    for kind in ("room", "object"):
        kind_train = [(s, y) for scene in train_scenes for s, y, k in scene_samples[scene] if k == kind]
        by_kind[kind] = {
            "n_training_samples": len(kind_train),
            "n_training_positives": sum(1 for _, y in kind_train if y),
        }

    status = {
        "method": "isotonic_leave_one_scene_out",
        "fitted_on_scenes": train_scenes,
        "held_out": True,
        "held_out_scene": held_out_scene,
        "loso_scenes_available": len(scene_configs),
        "loso_scenes_required": 4,
        "n_training_samples": n_training_samples,
        "n_training_positives": n_training_positives,
        "by_kind": by_kind,
        "by_kind_note": (
            "n_training_samples/n_training_positives above are POOLED "
            "(room+object together) and describe the fitted calibrator's "
            "own training set. by_kind splits the same training samples "
            "by Hypothesis.kind for diagnostic honesty only - the fitted "
            "calibrator itself is still the pooled one (see "
            "fit_loso_calibrator's docstring, audit finding H1)."
        ),
        "status": "LOSO_CALIBRATED",
    }
    return fold.calibrator, status
