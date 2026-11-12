"""Checks C1-C5 of PREREGISTRATION_PAPER.md section 3, for the APR tours."""
import collections, json, sys
from pathlib import Path
import yaml
sys.path.insert(0, "/Users/sher/project/cvp/project/tools/live_policy")
import paper_compare as pc

R = Path("/Users/sher/cvp_paper_scale_copy/runs")
CAMP = Path("/Users/sher/cvp_live_campaign_copy/runs")
LABELS = [l.strip("- \n") for l in open("/tmp/cvp_c_checks/objects_habitat_apartment.yaml") if l.strip()]
PAPER = {"00853": (6, 207.63), "00871": (9, 235.03)}
FINAL = {"00853": 85, "00871": 66}
FRONTIER_REF = {"00853": ("scene00853_frontier_reference", 33), "00871": ("scene00871_frontier_reference", 54)}

def nodes(p):
    return (yaml.load(open(p), Loader=pc._LOADER) or {}).get("nodes", []) or []

def mean_f1(pred_yamls, ref_objs):
    vals = [pc.f1_score(ref_objs, pc.parse_objects(p)) for p in pred_yamls]
    return [sum(v[i] for v in vals) / len(vals) for i in range(3)]

out = {"labels_in_file": len(LABELS)}
for sc in ("00853", "00871"):
    a = R / "apr" / f"apr_{sc}_a"; b = R / "apr" / f"apr_{sc}_b"
    fin = FINAL[sc]
    ga = a / "stages" / str(fin) / "habitat_scene_graph_original_graph0.yaml"
    na = nodes(ga)
    types = collections.Counter(n.get("node_type") for n in na)
    rooms = [n.get("name") for n in na if n.get("node_type") == "room"]
    wp = json.load(open(a / "config" / "waypoints.json"))
    ts = json.load(open(a / "config" / "tour_summary.json"))
    obj_a = pc.parse_objects(ga)
    classes = sorted({o[0] for o in obj_a})
    hm3d = pc.parse_objects(CAMP / "live_campaign" / "hm3d_refs_work" / f"{sc}_hm3d_reference.yaml")
    d, st = FRONTIER_REF[sc]
    fm = pc.parse_objects(CAMP / d / "stages" / str(st) / "habitat_scene_graph_original_graph0.yaml")
    a_yamls = sorted((a / "stages" / str(fin)).glob("habitat_scene_graph_original_graph*.yaml"))
    b_yamls = sorted((b / "stages" / str(fin)).glob("habitat_scene_graph_original_graph*.yaml"))
    b0 = b / "stages" / "0" / "habitat_scene_graph_original_graph0.yaml"
    f1_c3 = pc.f1_score(hm3d, obj_a)            # APR-a as prediction, HM3D as reference
    out[sc] = {
        "use_rule": {"reached": ts["waypoints_reached"], "listed": ts["waypoints_listed"], "fraction": ts["reached_fraction"]},
        "C1": {"room_nodes": len(rooms), "room_names": rooms, "paper_rooms": PAPER[sc][0],
               "start_island_area_m2": wp["navmesh"]["start_island_area"], "kept_area_estimate_m2": wp["kept_area_estimate_m2"],
               "paper_area_m2": PAPER[sc][1], "node_types": dict(types)},
        "C2": {"apr_b_final_vs_a_final_f1_prec_rec": mean_f1(b_yamls, pc.parse_objects(ga)) if b_yamls else None,
               "apr_b_objects_final": len(pc.parse_objects(b_yamls[0])) if b_yamls else None,
               "apr_b_final_identical_to_stage0": b_yamls and open(b_yamls[0]).read() == open(b0).read()},
        "C3": {"apr_a_recall_vs_hm3d": f1_c3[2], "apr_a_precision_vs_hm3d": f1_c3[1], "f1": f1_c3[0],
               "apr_a_objects": len(obj_a), "hm3d_objects": len(hm3d)},
        "C4": {"classes_in_apr_a": len(classes), "classes_not_in_label_file": [c for c in classes if c not in LABELS],
               "labels_never_seen": len([l for l in LABELS if l not in classes])},
        "C5": {"apr_a_vs_frontier_made_f1_prec_rec": pc.f1_score(fm, obj_a), "frontier_made_objects": len(fm)},
    }
json.dump(out, sys.stdout, indent=1, default=float)
