"""Independent E3 ceiling recomputation (own eligible-set code from live_policy constants,
REACH 5.0, NEW 0.5). Paths + hypothesis files + observed graphs only; no mapping, no F1/AUC."""
import json, os, glob, re, ast, numpy as np, yaml
RUNS="/tmp/cvp_review/runs"; SETS=json.load(open("/tmp/cvp_review/refs/oracle_sets.json"))["scenes"]
def vec(v): return [float(x) for x in (ast.literal_eval(v) if isinstance(v,str) else v)]
def lab(n): return str(n).lower().replace("_"," ").strip()
def ld(p):
    with open(p) as f: return yaml.safe_load(f) or {"nodes":[]}
def elig(g,cands):
    P=[n for n in g.get("nodes") or [] if "position" in n]
    if not P: return []
    oo=[vec(n["position"])[:2] for n in P if n.get("node_type")=="object"]
    st={}
    for n in P:
        if n.get("node_type")=="structure": st.setdefault(lab(n.get("name","")),[]).append(vec(n["position"])[:2])
    rooms=[n for n in P if n.get("node_type")=="room"]; anc=np.array([vec(n["position"])[:2] for n in (rooms or P)])
    oo=np.array(oo) if oo else np.zeros((0,2))
    out=[]
    for c in cands:
        x,y=c["position"][:2]
        m=(len(oo) and np.min(np.hypot(oo[:,0]-x,oo[:,1]-y))<=0.5) or any((x-a)**2+(y-b)**2<=0.25 for a,b in st.get(lab(c["name"]),[]))
        if not m and np.min(np.hypot(anc[:,0]-x,anc[:,1]-y))<=5.0: out.append(c)
    return out
def units(run, need_k1=True):
    scene=str(int(re.search(r"_(\d{5})_s",run).group(1))); C=SETS[scene]["objects"]; sd=f"{RUNS}/{run}/stages"
    U=[]
    for k in sorted(int(d) for d in os.listdir(sd) if d.isdigit()):
        n=f"{sd}/{k+1}"; ep=f"{n}/executed_path.json"
        if not os.path.exists(ep): continue
        w=json.load(open(ep)).get("world_frame_path") or []
        if not w: continue
        if need_k1 and not any(os.path.exists(f"{n}/habitat_scene_graph_original_graph{t}.yaml") for t in (0,1)): continue
        rx,ry=float(w[-1][0]),float(w[-1][1])
        for t in (0,1):
            op=f"{sd}/{k}/habitat_scene_graph_original_graph{t}.yaml"
            if not os.path.exists(op): continue
            g=ld(op); E=elig(g,C)
            if not E: continue
            ids={x["id"] for x in g.get("nodes") or []}; dk=set()
            for f in glob.glob(f"{sd}/{k}/habitat_scene_graph_new_graph_*.yaml"):
                if int(re.search(r"_(\d+)\.yaml$",f).group(1))//4!=t: continue
                for x in ld(f).get("nodes") or []:
                    if x.get("node_type")=="object" and x["id"] not in ids and "position" in x:
                        dk.add((lab(x.get("name","")),tuple(round(v,3) for v in vec(x["position"]))))
            pts=np.array([c["position"][:2] for c in E],float)
            dr=np.array([(lab(c["name"]),tuple(round(v,3) for v in c["position"])) in dk for c in E])
            U.append(dict(k=k,t=t,pts=pts,dr=dr,live=(rx,ry)))
    return U
def ap(pts,x,y): return np.hypot(pts[:,0]-x,pts[:,1]-y)<=3.5
res={}
for run in ["e3_00871_s42_oracle_visible_60m","e3_00853_s42_oracle_visible_60m_rerun1","e3_00853_s43_oracle_visible_60m","e3_00871_s43_oracle_visible_60m","e3_00853_s42_oracle_visible_60m_FAILED_ATTEMPT1_gate"]:
    U=units(run); Uno=units(run,need_k1=False)
    acc={s:[0.,0.] for s in ("live","rand","maxd","best")}; per={s:[] for s in acc}; nd=nu=0
    for u in U:
        p,d=u["pts"],u["dr"]
        if not d.any() or d.all(): continue
        nd+=d.sum(); nu+=(~d).sum()
        L=ap(p,*u["live"]); vals={"live":(L[d].sum(),L[~d].sum())}
        Ms=[ap(p,*p[j]) for j in np.flatnonzero(d)]
        vals["rand"]=(np.mean([m[d].sum() for m in Ms]),np.mean([m[~d].sum() for m in Ms]))
        xs=np.arange(p[:,0].min()-1,p[:,0].max()+1,0.5); ys=np.arange(p[:,1].min()-1,p[:,1].max()+1,0.5)
        best_cd=-1; ties=[]; bg=-9; bv=None
        for x in xs:
            for y in ys:
                a=ap(p,x,y); cd,cu=a[d].sum(),a[~d].sum()
                if cd>best_cd: best_cd=cd; ties=[(cd,cu)]
                elif cd==best_cd: ties.append((cd,cu))
                gg=cd/d.sum()-cu/(~d).sum()
                if gg>bg: bg=gg; bv=(cd,cu)
        vals["maxd"]=tuple(np.mean(ties,axis=0)); vals["best"]=bv
        for s,(a,b) in vals.items():
            acc[s][0]+=a; acc[s][1]+=b; per[s].append(a/d.sum()-b/(~d).sum())
    pooled={s:acc[s][0]/nd-acc[s][1]/nu for s in acc}; um={s:float(np.mean(per[s])) for s in per}
    res[run]={"units":len(U),"units_without_k1_rule":len(Uno),"n_d":int(nd),"n_u":int(nu),"pooled":pooled,"unit_mean":um,
              "share_pooled":pooled["live"]/pooled["maxd"],"share_um":um["live"]/um["maxd"]}
    print(run,json.dumps(res[run],default=float))
json.dump(res,open("/tmp/cvp_review/audit/verify_tables/v_e3.json","w"),indent=1,default=float)
