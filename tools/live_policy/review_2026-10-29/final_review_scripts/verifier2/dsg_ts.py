import json, os, glob
base="/home/sher/active-semantic-perception-workspace/runs/live_campaign"
for run in ["e5_00853_s42_placebo_15m_q1","e5_00853_s42_placebo_15m_q2","e5_00853_s42_placebo_15m_q3"]:
    for g in [0,1]:
        p=f"{base}/{run}/stages/0/graph{g}_dsg.json"
        d=json.load(open(p))
        ts=sorted(n["timestamp"]/1e9 for n in d["nodes"] if n["attributes"]["type"]=="AgentNodeAttributes")
        gaps=[b-a for a,b in zip(ts,ts[1:])]
        print(run[-2:], g, "n",len(ts),"first %.2f last %.2f span %.2f maxgap %.2f mtime %.2f"%(ts[0],ts[-1],ts[-1]-ts[0],max(gaps),os.path.getmtime(p)))
