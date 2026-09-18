from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from asp_offline.support_policy import support_filtered_graph
from asp_offline.validator import ValidationConfig, validate_completion


def _yaml_scalar(value: Any) -> str:
    if value is None: return "null"
    if value is True: return "true"
    if value is False: return "false"
    if isinstance(value, (int, float)): return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def yaml_dump(value: Any, indent: int = 0) -> str:
    """Small deterministic YAML emitter for JSON-like graph artifacts."""
    pad = " " * indent
    if isinstance(value, Mapping):
        lines: List[str] = []
        for key in sorted(value, key=str):
            child = value[key]
            if isinstance(child, (Mapping, list)):
                lines.append(f"{pad}{key}:")
                lines.append(yaml_dump(child, indent + 2))
            else: lines.append(f"{pad}{key}: {_yaml_scalar(child)}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for child in value:
            if isinstance(child, Mapping):
                items = list(child.items())
                if not items: lines.append(f"{pad}- {{}}")
                else:
                    key, first = items[0]
                    if isinstance(first, (Mapping, list)):
                        lines.append(f"{pad}- {key}:")
                        lines.append(yaml_dump(first, indent + 4))
                    else: lines.append(f"{pad}- {key}: {_yaml_scalar(first)}")
                    for key, value in items[1:]:
                        if isinstance(value, (Mapping, list)):
                            lines.append(f"{pad}  {key}:")
                            lines.append(yaml_dump(value, indent + 4))
                        else: lines.append(f"{pad}  {key}: {_yaml_scalar(value)}")
            elif isinstance(child, list):
                lines.append(f"{pad}-")
                lines.append(yaml_dump(child, indent + 2))
            else: lines.append(f"{pad}- {_yaml_scalar(child)}")
        return "\n".join(lines)
    return pad + _yaml_scalar(value)


def apply_unanimity_policy(observed: Mapping[str, Any], completions: Sequence[Mapping[str, Any]], *,
                           track_id: str, member_ids: Sequence[str],
                           output_path: Optional[Union[str, Path]] = None) -> dict[str, Any]:
    if len(completions) != 4 or len(member_ids) != 4 or len(set(member_ids)) != 4 or any(not x for x in member_ids):
        raise ValueError(f"track {track_id}: exactly four unique intended member IDs are required")
    validated = []
    provenance = []
    for index, completion in enumerate(completions):
        result = validate_completion(completion, observed, ValidationConfig(allow_parsed_mapping=True))
        if result.rejected:
            raise ValueError(f"track {track_id}: member {member_ids[index]} was rejected")
        validated.append(result.graph)
        provenance.append({"member_id": member_ids[index], "removed_nodes": list(result.removed_nodes)})
    outputs = []
    for completion in validated:
        filtered = support_filtered_graph(observed, completion, validated, 1.0, expected_size=4)
        filtered["prospective_policy"] = {"name": "validator_plus_unanimity_raw_tau_1_0",
            "track_id": track_id, "denominator": 4, "source_members": 4,
            "removed_node_provenance": provenance}
        outputs.append(filtered)
    if output_path is not None:
        path = Path(output_path)
        if path.exists() or path.is_symlink(): raise ValueError("policy output must be new")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml_dump(outputs[0]) + "\n")
    return outputs[0]


def process_cards(cards: Sequence[Mapping[str, Any]], output_dir: Union[str, Path]) -> List[dict[str, Any]]:
    """Process exactly 16 cards: four independent tracks × four unique members."""
    if len(cards) != 16: raise ValueError("expected exactly 16 cards")
    ordered = sorted(cards, key=lambda card: (int(card["source_order"]), str(card["source_path"])))
    groups: Dict[str, List[Mapping[str, Any]]] = {}
    for card in ordered:
        required = ("track_id", "member_id", "source_path", "source_order", "observed", "completion")
        if any(key not in card for key in required): raise ValueError("ambiguous card metadata")
        track, member = str(card["track_id"]), str(card["member_id"])
        if not track or not member or Path(str(card["source_path"])).is_symlink(): raise ValueError("invalid card identity/source")
        groups.setdefault(track, []).append(card)
    if len(groups) != 4 or any(len(group) != 4 for group in groups.values()): raise ValueError("tracks must be four cards each")
    if any(len({str(card["member_id"]) for card in group}) != 4 for group in groups.values()): raise ValueError("duplicate member in track")
    result: List[dict[str, Any]] = []
    root = Path(output_dir)
    if root.exists() or root.is_symlink(): raise ValueError("output directory must be new")
    root.mkdir(parents=True)
    for track, group in sorted(groups.items()):
        observed = group[0]["observed"]
        if any(card["observed"] != observed for card in group): raise ValueError("observed graph mismatch within track")
        validated = []
        for card in group:
            check = validate_completion(card["completion"], observed, ValidationConfig(allow_parsed_mapping=True))
            if check.rejected: raise ValueError("invalid member")
            validated.append(check.graph)
        for card, completion in zip(group, validated):
            filtered = support_filtered_graph(observed, completion, validated, 1.0, expected_size=4)
            filtered["prospective_policy"] = {"name": "validator_plus_unanimity_raw_tau_1_0", "track_id": track, "denominator": 4}
            target = root / Path(str(card["source_path"])).name
            if target.exists(): raise ValueError("duplicate output name")
            target.write_text(yaml_dump(filtered) + "\n")
            result.append({"source_path": str(card["source_path"]), "output_path": str(target), "graph": filtered})
    return sorted(result, key=lambda item: item["source_path"])


def equivalent_graph(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return left.get("nodes") == right.get("nodes") and left.get("edges") == right.get("edges")
