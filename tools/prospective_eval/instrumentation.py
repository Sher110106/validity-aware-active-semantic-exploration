"""Passive command-boundary recorder for a sibling/overlay integration."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .auditor import AuditResult, PassiveNavmeshAuditor
from .schema import EventTaxonomy, MotionEvent, MotionOutcome, Pose, ControllerMode, position_error, rotation_error, pose_distance, stable_hash


class PassiveMotionRecorder:
    """Observe a command and audit it without executing or altering it."""

    def __init__(self, auditor: PassiveNavmeshAuditor) -> None:
        self.auditor = auditor

    def record(
        self,
        *,
        event_id: str,
        stage_id: str,
        segment_id: str,
        command_id: str,
        previous_pose: Pose,
        requested_pose: Pose,
        result_pose: Optional[Pose],
        planner_outcome: str = "not_observed",
        reachability_outcome: str = "not_observed",
        command: Any = None,
        observation: Any = None,
        reset: bool = False,
        teleport: bool = False,
        rotation_only: bool = False,
    ) -> MotionEvent:
        audit: AuditResult = self.auditor.audit(previous_pose, requested_pose)
        taxonomy = audit.taxonomy
        outcome = MotionOutcome.UNKNOWN
        if planner_outcome in {"failure", "failed"}:
            taxonomy = EventTaxonomy.PLANNER_FAILURE
            outcome = MotionOutcome.PLANNER_FAILED
        elif result_pose is not None:
            outcome = MotionOutcome.REACHED if position_error(result_pose, requested_pose) <= 1e-4 and rotation_error(result_pose, requested_pose) <= 1e-4 else MotionOutcome.PARTIAL
        return MotionEvent(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage_id=stage_id,
            segment_id=segment_id,
            command_id=command_id,
            previous_pose=previous_pose,
            requested_pose=requested_pose,
            result_pose=result_pose,
            requested_distance_m=pose_distance(previous_pose, requested_pose),
            actual_displacement_m=None if result_pose is None else pose_distance(previous_pose, result_pose),
            target_position_error_m=None if result_pose is None else position_error(result_pose, requested_pose),
            target_rotation_error=None if result_pose is None else rotation_error(result_pose, requested_pose),
            clipping_delta_m=None if result_pose is None else position_error(result_pose, requested_pose),
            outcome=outcome,
            taxonomy=taxonomy,
            planner_outcome=planner_outcome,
            reachability_outcome=reachability_outcome,
            passive_navmesh_admissible=audit.admissible,
            reset=reset,
            teleport=teleport,
            rotation_only=rotation_only,
            controller_mode=ControllerMode.PASSIVE,
            command_hash=stable_hash(command) if command is not None else None,
            observation_hash=stable_hash(observation) if observation is not None else None,
        )
