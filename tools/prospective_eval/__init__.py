"""Passive motion and prospective false-positive detour instrumentation.

This package is deliberately adapter-based: importing it never imports Habitat,
starts a simulator, or changes an author's controller.
"""

from .schema import (
    Classification,
    ControllerMode,
    EvidenceReceipt,
    EventTaxonomy,
    MotionEvent,
    MotionOutcome,
    Pose,
)

__all__ = [
    "Classification",
    "ControllerMode",
    "EvidenceReceipt",
    "EventTaxonomy",
    "MotionEvent",
    "MotionOutcome",
    "Pose",
]
