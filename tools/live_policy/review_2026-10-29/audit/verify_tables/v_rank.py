"""Independent re-run of B's rank definition (copied logic of work_B/reach.py) and A's (decisions.py) on raw logs."""
import json, os, re, numpy as np
RUNS="/tmp/cvp_review/runs"
B_runs = ["e1_00853_s42_official_60m","e1_00853_s43_official_60m","e1_00871_s42_official_60m","e1_00871_s43_official_60m","e1_00871_s44_official_60m",
        "e1_00853_s42_placebo_60m","e1_00853_s43_placebo_60m","e1_00853_s44_placebo_60m","e1_00871_s42_placebo_60m","e1_00871_s43_placebo_60m_rerun1","e1_00871_s44_placebo_60m",
        "e2_00853_s42_filter_only_60m","e2_00853_s43_filter_only_60m","e2_00853_s44_filter_only_60m","e2_00871_s42_filter_only_60m","e2_00871_s43_filter_only_60m","e2_00871_s44_filter_only_60m",
        "e3_00853_s42_oracle_visible_60m_rerun1","e3_00853_s43_oracle_visible_60m","e3_00871_s42_oracle_visible_60m","e3_00871_s43_oracle_visible_60m"]
A_runs=[l.strip() for l in open("/tmp/cvp_review/analysis_pre/runs.txt") if l.strip()]
def B_rows(runs):
    rows=[]
    for r in runs:
        sd=os.path.join(RUNS,r,"stages")
        for k in sorted(int(s) for s in os.listdir(sd) if s.isdigit()):
            pl=os.path.join(sd,str(k),"pose_log.json"); ep=os.path.join(sd,str(k+1),"executed_path.json")
            if not(os.path.exists(pl) and os.path.exists(ep)): continue
            lines=[json.loads(l) for l in open(pl) if l.strip()]
            tops=[l for l in lines if "best_sample_poses" in l]; finals=[l for l in lines if "final_pose" in l]
            if not finals or not finals[-1]["final_pose"]: continue
            fin=finals[-1]; tgt=np.array(fin["final_pose"][0])
            path=json.load(open(ep))["world_frame_path"]
            if not path: continue
            top=tops[-1]["best_filtered_poses"] or tops[-1]["best_sample_poses"]
            rank=None
            for i,p in enumerate(top):
                if np.allclose(p,tgt[:4]): rank=i+1
            # A-style: target from path_log, unfiltered list
            pa=os.path.join(sd,str(k),"path_log.json"); rA=None
            if os.path.exists(pa):
                pls=[json.loads(x) for x in open(pa) if x.strip()]
                if pls:
                    t=np.array(pls[-1]["final_path"][-1][:2]); un=np.array(tops[-1]["best_sample_poses"])
                    d=np.hypot(un[:,0]-t[0],un[:,1]-t[1]); rA=int(np.argmin(d)) if d.min()<1e-6 else None
            rows.append((r,k,rank,rA,len(top)))
    return rows
out={}
for name,runs in [("B_set",B_runs),("A_set",A_runs)]:
    R=B_rows(runs)
    m=[x for x in R if x[2]]
    out[name]={"n":len(R),"n_matchedB":len(m),"rank1B":sum(1 for x in m if x[2]==1),
               "shareB":sum(1 for x in m if x[2]==1)/len(m),
               "n_A_matched":sum(1 for x in R if x[3] is not None),"rank0A":sum(1 for x in R if x[3]==0)}
print(json.dumps(out,indent=1))
json.dump(out,open("/tmp/cvp_review/audit/verify_tables/v_rank.json","w"),indent=1)
