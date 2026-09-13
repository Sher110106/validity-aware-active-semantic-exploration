"""Offline, deterministic components for the ASP extension experiments.

The package is deliberately independent of ROS, Habitat, and an LLM.  It can
consume exported graph/completion artifacts from the simulation host and is
therefore useful on the development machine as well as in replay jobs.
"""

from .models import Graph, Node, Edge, ValidationResult, Hypothesis
from .validator import ValidationConfig, label_against_reference, validate_completion, validate_ensemble
from .calibration import (
    IsotonicCalibrator,
    fit_leave_one_scene_out,
    match_hypotheses,
)
from .scoring import score_viewpoint
from .evaluator import evaluate_graph, evaluate_run, area_under_curve, summarize_metrics
from .author_io import load_author_graph, load_author_graph_text, normalize_author_graph

__all__ = [
    "Graph", "Node", "Edge", "ValidationResult", "Hypothesis",
    "ValidationConfig", "validate_completion", "validate_ensemble", "label_against_reference",
    "IsotonicCalibrator", "fit_leave_one_scene_out", "match_hypotheses",
    "score_viewpoint", "evaluate_graph", "evaluate_run", "area_under_curve", "summarize_metrics",
    "load_author_graph", "load_author_graph_text", "normalize_author_graph",
]
