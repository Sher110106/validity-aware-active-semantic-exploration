import yaml, os, sys, ast, json
import numpy as np
RUNS = "/tmp/cvp_review/runs"
def load(p):
    with open(p) as f:
        return yaml.safe_load(f)
def vec(v):
    return np.array(ast.literal_eval(v) if isinstance(v, str) else v, dtype=float)
def summary(g):
    nodes = g.get('nodes', [])
    by = {}
    for n in nodes:
        by[n.get('node_type')] = by.get(n.get('node_type'), 0) + 1
    return by
for scene, seed in [("00853",42),("00853",43),("00871",42),("00871",43),("00871",44)]:
    print("==", scene, seed)
    for arm, run in [("official", f"e1_{scene}_s{seed}_official_60m"), ("placebo", f"e1_{scene}_s{seed}_placebo_60m"), ("filter_only", f"e2_{scene}_s{seed}_filter_only_60m"), ("oracle", f"e3_{scene}_s{seed}_oracle_visible_60m")]:
        d = os.path.join(RUNS, run, "stages", "0")
        if not os.path.isdir(d):
            d2 = os.path.join(RUNS, run + "_rerun1", "stages", "0")
            if os.path.isdir(d2): d = d2
            else: continue
        g0 = load(os.path.join(d, "habitat_scene_graph_original_graph0.yaml"))
        g1 = load(os.path.join(d, "habitat_scene_graph_original_graph1.yaml"))
        objs0 = sorted((n['name'], tuple(np.round(vec(n['position'])[:2],1))) for n in g0['nodes'] if n.get('node_type')=='object')
        objs1 = sorted((n['name'], tuple(np.round(vec(n['position'])[:2],1))) for n in g1['nodes'] if n.get('node_type')=='object')
        members = sorted(f for f in os.listdir(d) if f.startswith('habitat_scene_graph_new_graph_'))
        print(f"  {arm:12s} g0 {summary(g0)} g1 {summary(g1)} members={len(members)}")
        print(f"      g0 objects: {objs0[:12]}")
        print(f"      g1 objects: {objs1[:12]}")
