import glob, json, numpy as np
W='/Users/sher/project/cvp/project/tools/live_policy/review_2026-10-29/bench/walls'
L='/Users/sher/cvp_live_campaign_copy/runs/live_campaign'
F='/Users/sher/cvp_live_campaign_copy/runs/frontier_seeds'
def pts(files):
    P=[]
    for f in files:
        try: p=np.array(json.load(open(f))["world_frame_path"], float)[:, :2]
        except Exception: continue
        if len(p)<2: continue
        for a,b in zip(p[:-1],p[1:]):
            n=max(2,int(np.linalg.norm(b-a)/0.02)+1)
            P.append(a+np.linspace(0,1,n)[:,None]*(b-a))
    return np.concatenate(P) if P else np.zeros((0,2))
def share(P, occ, org, res):
    ij=np.floor((P-org)/res).astype(int)
    ok=(ij[:,0]>=0)&(ij[:,1]>=0)&(ij[:,0]<occ.shape[0])&(ij[:,1]<occ.shape[1])
    v=np.zeros(len(P),bool); v[ok]=occ[ij[ok,0],ij[ok,1]]
    return v.mean()
for scene in ("00853","00871"):
    d=np.load(f"{W}/{scene}_walls.npz"); org=d["origin"]; res=float(d["res"]); occ=d["occ"][1]>0
    asp=[f for f in glob.glob(f"{L}/e*_{scene}_*/stages/*/executed_path.json") if '/e5_' not in f and 'FAILED' not in f]
    fr=glob.glob(f"{F}/e4_{scene}_*/stages/*/executed_path.json")
    PA, PF = pts(asp), pts(fr)
    lo=np.minimum(PA.min(0),PF.min(0)); hi=np.maximum(PA.max(0),PF.max(0))
    R=np.random.default_rng(0).uniform(lo,hi,(200000,2))
    print(scene, 'ASP files', len(asp), 'pts', len(PA), 'in 1.1m occ %.3f' % share(PA,occ,org,res), '| frontier files', len(fr), 'pts', len(PF), 'in occ %.3f' % share(PF,occ,org,res), '| random %.3f' % share(R,occ,org,res))
print('--- bounds and distance check')
from scipy.ndimage import distance_transform_edt
for scene in ("00853","00871"):
    d=np.load(f"{W}/{scene}_walls.npz"); org=d["origin"]; res=float(d["res"]); occ=d["occ"][1]>0
    dt=distance_transform_edt(~occ)*res
    asp=[f for f in glob.glob(f"{L}/e*_{scene}_*/stages/*/executed_path.json") if '/e5_' not in f and 'FAILED' not in f]
    fr=glob.glob(f"{F}/e4_{scene}_*/stages/*/executed_path.json")
    for name,files in (('ASP',asp),('frontier',fr)):
        P=pts(files); ij=np.floor((P-org)/res).astype(int)
        ok=(ij[:,0]>=0)&(ij[:,1]>=0)&(ij[:,0]<occ.shape[0])&(ij[:,1]<occ.shape[1])
        dd=dt[ij[ok,0],ij[ok,1]]
        print(scene, name, 'in-bounds %.3f' % ok.mean(), 'xy range', P.min(0).round(1), P.max(0).round(1), 'wall dist<=0/0.1/0.2 m', [round(float(np.mean(dd<=t)),3) for t in (0,0.1,0.2)], 'median %.2f' % np.median(dd))
    # per-run ASP share
    for f in sorted(set('/'.join(x.split('/')[:-3]) for x in asp)):
        P=pts(glob.glob(f+'/stages/*/executed_path.json'))
        print('   ', f.split('/')[-1], '%.3f' % share(P,occ,org,res))
