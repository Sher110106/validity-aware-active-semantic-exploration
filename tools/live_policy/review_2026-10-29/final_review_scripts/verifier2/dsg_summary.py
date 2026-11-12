import json, sys, os, collections
base="/home/sher/active-semantic-perception-workspace/runs/live_campaign"
for run in ["e5_00853_s42_placebo_15m_q1","e5_00853_s42_placebo_15m_q2","e5_00853_s42_placebo_15m_q3"]:
    for g in [0,1]:
        p=f"{base}/{run}/stages/0/graph{g}_dsg.json"
        sz=os.path.getsize(p)
        d=json.load(open(p))
        cnt=collections.Counter(n["attributes"]["type"] for n in d["nodes"])
        # bytes per type
        by=collections.Counter()
        for n in d["nodes"]:
            by[n["attributes"]["type"]]+=len(json.dumps(n))
        ts=[]
        for n in d["nodes"]:
            a=n["attributes"]
            if a["type"]=="AgentNodeAttributes":
                ts.append(a.get("timestamp", a.get("last_update_time_ns")))
        ts=[t for t in ts if t is not None]
        print(run[-2:], "g",g, "size",sz, dict(cnt))
        print("   bytes", {k:round(v/1e6,3) for k,v in by.items()})
        if ts:
            ts=sorted(ts)
            print("   agent ts min/max (s)", ts[0]/1e9 if ts[0]>1e12 else ts[0], ts[-1]/1e9 if ts[-1]>1e12 else ts[-1], "n",len(ts))
        objs=[(n["attributes"].get("name"), [round(x,2) for x in n["attributes"]["position"]]) for n in d["nodes"] if n["attributes"]["type"]=="KhronosObjectAttributes"]
        print("   objs", objs)
