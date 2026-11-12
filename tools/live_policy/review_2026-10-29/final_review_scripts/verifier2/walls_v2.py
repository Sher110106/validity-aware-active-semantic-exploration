import glob, json, numpy as np
W='/Users/sher/project/cvp/project/tools/live_policy/review_2026-10-29/bench/walls'
L='/Users/sher/cvp_live_campaign_copy/runs/live_campaign'
F='/Users/sher/cvp_live_campaign_copy/runs/frontier_seeds'
FT=json.load(open(L+'/hm3d_refs_work/frame_transform.json'))
def load(f, key):
    d=json.load(open(f)); return np.array(d[key], float)
def dens(p):
    out=[]
    for a,b in zip(p[:-1],p[1:]):
        n=max(2,int(np.linalg.norm(b-a)/0.02)+1)
        out.append(a+np.linspace(0,1,n)[:,None]*(b-a))
    return np.concatenate(out) if out else np.zeros((0,2))
def run_pts(rundir, scene, use_hab=False):
    P=[]; maxres=0
    R=np.array(FT[scene]['code_R']); t=np.array(FT[scene]['code_t'])
    for f in sorted(glob.glob(rundir+'/stages/*/executed_path.json')):
        d=json.load(open(f)); w=np.array(d['world_frame_path'],float); h=np.array(d['habitat_frame_path'],float)
        if len(w)<2: continue
        w2=h@R.T+t
        maxres=max(maxres, np.abs(w2[:,:2]-w[:,:2]).max())
        P.append(dens((w2 if use_hab else w)[:,:2]))
    return (np.concatenate(P) if P else np.zeros((0,2))), maxres
def share(P, occ, org, res):
    ij=np.floor((P-org)/res).astype(int)
    ok=(ij[:,0]>=0)&(ij[:,1]>=0)&(ij[:,0]<occ.shape[0])&(ij[:,1]<occ.shape[1])
    v=np.zeros(len(P),bool); v[ok]=occ[ij[ok,0],ij[ok,1]]
    return v.mean(), ok.mean()
for scene in ("00853","00871"):
    d=np.load(f"{W}/{scene}_walls.npz"); org=d["origin"]; res=float(d["res"]); occ=d["occ"][1]>0
    print("scene",scene)
    allA=[]
    runs=sorted(set(f.split('/stages/')[0] for f in glob.glob(f"{L}/e*_{scene}_*/stages/*/executed_path.json")))
    for r in runs:
        P,mr=run_pts(r,scene)
        s,ok=share(P,occ,org,res)
        tag=r.split('/')[-1]
        if '/e5_' not in r and 'FAILED' not in r: allA.append(P)
        print("  ASP %-55s pts %6d occ %.4f inb %.3f frame_resid %.3f"%(tag,len(P),s,ok,mr))
    for r in sorted(glob.glob(f"{F}/e4_{scene}_*")):
        P,mr=run_pts(r,scene)
        s,ok=share(P,occ,org,res)
        print("  FR  %-55s pts %6d occ %.4f inb %.3f frame_resid %.3f"%(r.split('/')[-1],len(P),s,ok,mr))
    PA=np.concatenate(allA)
    lo,hi=PA.min(0),PA.max(0)
    Rr=np.random.default_rng(1).uniform(lo,hi,(200000,2))
    print("  pooled ASP (no e5/FAILED) %.4f  random %.4f"%(share(PA,occ,org,res)[0], share(Rr,occ,org,res)[0]))
