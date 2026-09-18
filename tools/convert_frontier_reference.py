#!/usr/bin/env python3
"""Convert a frontier_baseline.py run's final-stage graph{0,1}_dsg.json into
the evaluator's habitat_scene_graph_original_graph{0,1}.yaml reference
format, using the author's own f1_score_plot.py:convert_dsg_to_yaml exactly
(imported directly, not reimplemented) - this is a manual post-processing
step frontier_baseline.py does not do itself (confirmed by grep: it never
writes habitat_scene_graph_original_graph* files at runtime).

Usage: python3 convert_frontier_reference.py <stage_dir>
Writes habitat_scene_graph_original_graph{0,1}.yaml into <stage_dir>.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/workspace/catkin_ws/src/active_semantic_perception/exploration/scripts")
from f1_score_plot import convert_dsg_to_yaml

stage_dir = Path(sys.argv[1])
for graph_idx in (0, 1):
    dsg_path = stage_dir / f"graph{graph_idx}_dsg.json"
    if not dsg_path.exists():
        print(f"MISSING: {dsg_path}")
        continue
    convert_dsg_to_yaml(dsg_path)
    out_path = stage_dir / f"habitat_scene_graph_original_graph{graph_idx}.yaml"
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
