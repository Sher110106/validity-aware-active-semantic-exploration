"""Independent recomputation of Table 1 cells from replay2_results.jsonl.
Own bootstrap (different seed, cluster-preserving within run). Also a run-level (cluster) bootstrap as a sensitivity."""
import json, numpy as np, collections
rows=[json.loads(l) for l in open("/tmp/cvp_review/work_A/replay2_results.jsonl")]
rows=[r for r in rows if "error" not in r and r.get("n_cand",0)>0 and r["run"]!="e1_00871_s43_placebo_60m"]
def arr(R,f): return np.array([f(r) for r in R],float)
def cell(R):
    da=arr(R,lambda r:r["fixed"]["plc_a"]["top1_dist"]); db=arr(R,lambda r:r["fixed"]["plc_b"]["top1_dist"])
    fl=arr(R,lambda r:r["fixed_plc_a_vs_b"]["top1_dist"]); ob=arr(R,lambda r:r["fixed"]["obs"]["top1_dist"]); oc=arr(R,lambda r:r["fixed"]["orc"]["top1_dist"])
    return dict(move_plc=np.median(np.r_[da,db]), floor=np.median(fl), diff=np.median(np.r_[da,db])-np.median(fl),
                move_obs=np.median(ob), move_orc=np.median(oc),
                same_plc=np.mean(np.r_[arr(R,lambda r:r["fixed"]["plc_a"]["top1_same"]),arr(R,lambda r:r["fixed"]["plc_b"]["top1_same"])]),
                same_floor=np.mean(arr(R,lambda r:r["fixed_plc_a_vs_b"]["top1_same"])),
                same_obs=np.mean(arr(R,lambda r:r["fixed"]["obs"]["top1_same"])),same_orc=np.mean(arr(R,lambda r:r["fixed"]["orc"]["top1_same"])),
                ovl_plc=np.mean(np.r_[arr(R,lambda r:r["fixed"]["plc_a"]["top10_overlap"]),arr(R,lambda r:r["fixed"]["plc_b"]["top10_overlap"])]),
                ovl_floor=np.mean(arr(R,lambda r:r["fixed_plc_a_vs_b"]["top10_overlap"])),
                rho_plc=np.nanmedian(np.r_[arr(R,lambda r:r["fixed"]["plc_a"]["rho_total"]),arr(R,lambda r:r["fixed"]["plc_b"]["rho_total"])]),
                rho_floor=np.nanmedian(arr(R,lambda r:r["fixed_plc_a_vs_b"]["rho_total"])),
                rho_obs=np.nanmedian(arr(R,lambda r:r["fixed"]["obs"]["rho_total"])))
def boot(R,B=2000,seed=7,cluster=False):
    byrun=collections.defaultdict(list)
    for r in R: byrun[r["run"]].append(r)
    runs=sorted(byrun); rng=np.random.default_rng(seed); out=collections.defaultdict(list)
    for _ in range(B):
        if cluster:
            pick=rng.integers(0,len(runs),len(runs)); S=[x for i in pick for x in byrun[runs[i]]]
        else:
            S=[byrun[u][i] for u in runs for i in rng.integers(0,len(byrun[u]),len(byrun[u]))]
        c=cell(S)
        for k in ("move_plc","floor","diff","move_obs","move_orc"): out[k].append(c[k])
    return {k:[float(np.percentile(v,2.5)),float(np.percentile(v,97.5))] for k,v in out.items()}
res={}
groups={"official":[r for r in rows if r["arm"]=="official"],"placebo":[r for r in rows if r["arm"]=="placebo"],
        "filter_only":[r for r in rows if r["arm"]=="filter_only"],"oracle_visible":[r for r in rows if r["arm"]=="oracle_visible"],"ALL":rows,
        "official_00853":[r for r in rows if r["arm"]=="official" and "_00853_" in r["run"]],
        "official_00871":[r for r in rows if r["arm"]=="official" and "_00871_" in r["run"]]}
for g,R in groups.items():
    c={k:float(v) for k,v in cell(R).items()}
    res[g]={"n":len(R),"runs":len({r['run'] for r in R}),"point":c,"ci_within_run":boot(R)}
    if g in("official","ALL"): res[g]["ci_cluster_runs"]=boot(R,cluster=True)
    print(g,res[g]["n"],res[g]["runs"],{k:round(v,3) for k,v in c.items()})
    print("   within",{k:[round(x,2) for x in v] for k,v in res[g]["ci_within_run"].items()})
    if "ci_cluster_runs" in res[g]: print("   cluster",{k:[round(x,2) for x in v] for k,v in res[g]["ci_cluster_runs"].items()})
json.dump(res,open("/tmp/cvp_review/audit/verify_tables/v_replay.json","w"),indent=1)
