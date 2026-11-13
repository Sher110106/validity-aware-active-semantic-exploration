"""Export the inputs of chosen saved stages, so a model can be re-asked on them off the host.

Runs inside the asp-noetic container, CPU only. For each `<run_dir>:<stage>` it writes
`<out>/<row_id>/`:

    prompt.txt   the author's completion prompt, from the run's own pipeline_config.yaml
    graph.yaml   the observed track-0 graph the members were asked to complete, byte for byte
    slices/      the input slices, rendered again from that graph with the author's
                 create_scene_slices (the slices saved in a run were overwritten later
                 with the completed graph, as gemini_static.py notes)
    meta.json    run, scene, seed, stage, arm, file hashes, slice names and sizes

This follows tools/live_policy/gemini_static.py line for line up to the point where it
calls the model. It calls no model and reads no key.

Usage:
    python -B export_replay_inputs.py <out_dir> <rows_file>
rows_file: one `<row_id> <run_dir> <stage>` per line; `#` starts a comment.
"""
import hashlib
import json
import os
import re
import shutil
import sys

SCRIPTS = "/workspace/catkin_ws/src/active_semantic_perception/exploration/scripts"
OBSERVED = "habitat_scene_graph_original_graph0.yaml"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    out_root, rows_file = sys.argv[1], sys.argv[2]
    rows = []
    for line in open(rows_file):
        line = line.split("#", 1)[0].strip()
        if line:
            row_id, run_dir, stage = line.split()
            rows.append((row_id, run_dir, stage))
    os.makedirs(out_root, exist_ok=True)

    sys.path.insert(0, SCRIPTS)
    import yaml  # noqa: E402
    from scene_graph_visualize_2d import create_scene_slices  # noqa: E402

    index = []
    for row_id, run_dir, stage in rows:
        src = os.path.join(run_dir, "stages", stage)
        observed = os.path.join(src, OBSERVED)
        cfg_path = os.path.join(run_dir, "config", "pipeline_config.yaml")
        if not os.path.exists(observed) or not os.path.exists(cfg_path):
            index.append({"row_id": row_id, "error": "missing observed graph or config", "run_dir": run_dir, "stage": stage})
            print(json.dumps(index[-1]), flush=True)
            continue
        work = os.path.join(out_root, row_id)
        slices = os.path.join(work, "slices")
        if os.path.isdir(work):
            shutil.rmtree(work)
        os.makedirs(work)
        shutil.copy(observed, os.path.join(work, "graph.yaml"))
        cfg = yaml.safe_load(open(cfg_path))
        with open(os.path.join(work, "prompt.txt"), "w") as f:
            f.write(cfg["LLM_COMPLETION_PROMPT"])
        # Render from a private copy, exactly as gemini_static.py does.
        create_scene_slices(os.path.join(work, "graph.yaml"), scene_slice_folder_name=slices)
        names = sorted(os.listdir(slices)) if os.path.isdir(slices) else []
        run = os.path.basename(run_dir.rstrip("/"))
        m = re.match(r"(?:e\d+|dryrun\w*?)_(\d{5})_s(\d+)_([a-z_]+?)_\d+m", run)
        meta = {
            "row_id": row_id,
            "run": run,
            "stage": int(stage),
            "scene": m.group(1) if m else None,
            "seed": int(m.group(2)) if m else None,
            "arm": m.group(3) if m else None,
            "config_seed": cfg.get("SEED"),
            "track": 0,
            "graph_sha256": sha256(os.path.join(work, "graph.yaml")),
            "graph_bytes": os.path.getsize(os.path.join(work, "graph.yaml")),
            "prompt_sha256": sha256(os.path.join(work, "prompt.txt")),
            "slices": [{"name": n, "bytes": os.path.getsize(os.path.join(slices, n)),
                        "sha256": sha256(os.path.join(slices, n))} for n in names],
            "saved_members": sorted(n for n in os.listdir(src) if n.startswith("habitat_scene_graph_new_graph_")),
        }
        json.dump(meta, open(os.path.join(work, "meta.json"), "w"), indent=1)
        index.append({k: meta[k] for k in ("row_id", "run", "stage", "scene", "seed", "arm", "graph_bytes")}
                     | {"n_slices": len(names), "slice_bytes": sum(s["bytes"] for s in meta["slices"])})
        print(json.dumps(index[-1]), flush=True)

    json.dump(index, open(os.path.join(out_root, "index.json"), "w"), indent=1)
    bad = [r for r in index if "error" in r]
    print(json.dumps({"rows": len(index), "errors": len(bad)}))


if __name__ == "__main__":
    main()
