from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union

from asp_offline.support_policy import support_filtered_graph
from asp_offline.validator import ValidationConfig, validate_completion


def apply_unanimity_policy(observed: Mapping[str, Any], completions: Sequence[Mapping[str, Any]], *,
                           track_id: str, output_path: Optional[Union[str, Path]] = None,
                           member_ids: Optional[Sequence[str]] = None) -> dict[str, Any]:
    """Apply validator then raw 4/4 support to one independent graph track."""
    if len(completions) != 4:
        raise ValueError(f"track {track_id}: exactly four intended members are required")
    ids = list(member_ids) if member_ids is not None else [c.get("member_id") for c in completions]
    if any(value is not None for value in ids) and (len(ids) != 4 or any(value is None for value in ids) or len(set(ids)) != 4):
        raise ValueError(f"track {track_id}: member identities are missing or duplicated")
    validated = []
    provenance = []
    for index, completion in enumerate(completions):
        result = validate_completion(completion, observed, ValidationConfig(allow_parsed_mapping=True))
        if result.rejected:
            raise ValueError(f"track {track_id}: member {index} was rejected")
        validated.append(result.graph)
        provenance.append({"member": index, "removed_nodes": list(result.removed_nodes)})
    filtered = support_filtered_graph(observed, validated[0], validated, 1.0, expected_size=4)
    filtered["prospective_policy"] = {
        "name": "validator_plus_unanimity_raw_tau_1_0", "track_id": track_id,
        "denominator": 4, "source_members": 4, "removed_node_provenance": provenance,
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        import json
        path.write_text(json.dumps(filtered, sort_keys=True, indent=2) + "\n")
    return filtered
