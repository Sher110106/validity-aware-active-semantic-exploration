import glob, json, numpy as np, sys
sys.path.insert(0,'/tmp/cvp_final_review/claims')
W='/Users/sher/project/cvp/project/tools/live_policy/review_2026-10-29/bench/walls'
F='/Users/sher/cvp_live_campaign_copy/runs/frontier_seeds'
exec(open('/tmp/cvp_final_review/claims/wall_cross.py').read().split("for scene in")[0])
for scene in ("00853","00871"):
    d=np.load(f"{W}/{scene}_walls.npz"); org=d["origin"]; res=float(d["res"])
    for lvl in (0,1,2):
        occ=d["occ"][lvl]>0
        for r in sorted(glob.glob(f"{F}/e4_{scene}_*")):
            P=pts(glob.glob(r+'/stages/*/executed_path.json'))
            if lvl==1: print(scene, 'slice', lvl, r.split('/')[-1], 'pts', len(P), 'share %.4f' % share(P,occ,org,res))
    print(scene, 'union all frontier %.4f' % share(pts(glob.glob(f"{F}/e4_{scene}_*/stages/*/executed_path.json")), d["occ"].max(0)>0, org, res))
