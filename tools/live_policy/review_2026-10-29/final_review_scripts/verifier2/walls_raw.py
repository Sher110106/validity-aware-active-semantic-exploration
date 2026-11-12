import glob, json, numpy as np
W='/Users/sher/project/cvp/project/tools/live_policy/review_2026-10-29/bench/walls'
L='/Users/sher/cvp_live_campaign_copy/runs/live_campaign'
F='/Users/sher/cvp_live_campaign_copy/runs/frontier_seeds'
for scene in ("00853","00871"):
    d=np.load(f"{W}/{scene}_walls.npz"); org=d["origin"]; res=float(d["res"]); occ=d["occ"][1]>0
    for name,pat in (("ASP",f"{L}/e[123]_{scene}_*/stages/*/executed_path.json"),("FR",f"{F}/e4_{scene}_*/stages/*/executed_path.json")):
        steps=[]; raw=[]
        for f in glob.glob(pat):
            if 'FAILED' in f or 'ABORTED' in f: continue
            p=np.array(json.load(open(f))['world_frame_path'],float)[:,:2]
            if len(p)<2: continue
            steps+=list(np.linalg.norm(np.diff(p,axis=0),axis=1)); raw.append(p)
        P=np.concatenate(raw); ij=np.floor((P-org)/res).astype(int)
        v=occ[ij[:,0],ij[:,1]]
        s=np.array(steps)
        print(scene,name,"raw pts",len(P),"raw in occ %.4f"%v.mean(),"step median %.3f p90 %.3f max %.3f"%(np.median(s),np.percentile(s,90),s.max()))
