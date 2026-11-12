"""Independent spot checks of Table 3 (E1/E2 + frontier only; no e3 score rows read)."""
import json, numpy as np
AP="/tmp/cvp_review/analysis_pre"
S={r["run_dir"].rstrip("/").split("/")[-1]:r for r in json.load(open(f"{AP}/scores_e1_e2.json"))}
assert not any(k.startswith("e3_") for k in S)
def at60(st,m):
    xs=np.array([s["path_m"] for s in st]); ys=np.array([s[m] for s in st]); o=np.argsort(xs)
    return float(np.interp(60.0,xs[o],ys[o]))  # np.interp holds ends
out={}
rng=np.random.default_rng(3)
pick=list(rng.choice(sorted(k for k in S if S[k]["final_path_m"]>0),6,replace=False))+["e1_00853_s43_official_60m","e2_00871_s43_filter_only_60m"]
for k in pick:
    st=S[k]["hm3d_stages"]; out[k]={"rec60":at60(st,"af_recall"),"f160":at60(st,"af_f1"),"final_m":S[k]["final_path_m"]}
for f in json.load(open(f"{AP}/frontier_60m_scores.json")):
    st=f["hm3d_stages"]; last=max(st,key=lambda s:s["path_m"])
    out["frontier_"+f["scene"]]={"final_rec":last["af_recall"],"final_f1":last["af_f1"],"final_m":last["path_m"],"rec60":at60(st,"af_recall"),"f160":at60(st,"af_f1")}
SD=[x for x in json.load(open(f"{AP}/stage_diagnostics.json")) if not x["run"].startswith("e3_")]
drop={"e1_00853_s44_official_60m","e1_00853_s44_official_60m_rerun1","e1_00871_s43_placebo_60m"}
for arm in ["official","placebo","filter_only"]:
    for sc in ["853","871"]:
        R=[x for x in SD if x["arm"]==arm and x["scene"]==sc and x["run"] not in drop]
        nn=sum(x["base_rate"]["n_near"] for x in R)
        out[f"br_{arm}_{sc}"]={"runs":len(R),"pooled":sum(x["base_rate"]["mapped_k1"]*x["base_rate"]["n_near"] for x in R)/nn,
                               "range":[min(x["base_rate"]["mapped_k1"] for x in R),max(x["base_rate"]["mapped_k1"] for x in R)],
                               "scan_mean_of_runs":float(np.mean([x["scanned_share_of_new_hypotheses"] for x in R]))}
pre=json.load(open("/tmp/cvp_review/gates/base_rates_pre_E3.json"))
out["pre_E3_runs"]=[x["run"] for x in pre]
print(json.dumps(out,indent=1))
json.dump(out,open("/tmp/cvp_review/audit/verify_tables/v_headroom.json","w"),indent=1)
