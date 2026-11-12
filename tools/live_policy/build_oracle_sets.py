#!/usr/bin/env python3
"""Build oracle_sets.json for the oracle_visible arm (E3).

The candidate set per scene is every object node of the primary HM3D
reference graph: the human annotation, restricted to labels that map into
the pipeline's object vocabulary, in the pipeline frame. It is the same
graph the runs are scored against, and no run's map is involved in choosing
it. Records each source file's sha256 so a run's manifest pins the set.

Usage: build_oracle_sets.py <refs_dir> <out.json>
"""
import hashlib
import json
import sys
from pathlib import Path

import yaml

SCENES = {"00853": 853, "00871": 871}


def vec(value):
    import ast

    return [float(x) for x in (ast.literal_eval(value) if isinstance(value, str) else value)]


def main() -> int:
    refs, out = Path(sys.argv[1]), Path(sys.argv[2])
    sets = {"source": "primary HM3D reference graphs (<scene>_hm3d_reference.yaml)", "scenes": {}}
    for scene, number in SCENES.items():
        path = refs / f"{scene}_hm3d_reference.yaml"
        graph = yaml.safe_load(path.read_text())
        objects = [{"name": n["name"], "position": vec(n["position"]), "dimension": vec(n["dimension"])}
                   for n in graph["nodes"] if n.get("node_type") == "object"]
        sets["scenes"][str(number)] = {"scene": scene, "file": path.name,
                                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                       "n_objects": len(objects), "objects": objects}
        print(scene, len(objects), "objects")
    out.write_text(json.dumps(sets, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
