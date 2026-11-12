import yaml, glob, os, math, sys
base="/Users/sher/cvp_live_campaign_copy/runs/live_campaign"
targets={"duvet":(0.4,-5.2),"nightstand":(-0.6,-6.9),"lamp":(-0.47,-6.18),"cabinet":(1.52,-2.78)}
for q in ["q1","q2","q3"]:
    run=f"{base}/e5_00853_s42_placebo_15m_{q}"
    for st in sorted(os.listdir(run+"/stages"), key=int):
        for g in [0,1]:
            p=f"{run}/stages/{st}/habitat_scene_graph_original_graph{g}.yaml"
            if not os.path.exists(p): continue
            d=yaml.safe_load(open(p))
            objs=[(n["name"],eval(n["position"])) for n in d["nodes"] if n.get("node_type")=="object"]
            hits=[]
            for name,(x,y) in targets.items():
                best=None
                for nm,pos in objs:
                    if nm==name:
                        dd=math.hypot(pos[0]-x,pos[1]-y)
                        if best is None or dd<best: best=dd
                hits.append(f"{name}:{'-' if best is None else round(best,2)}")
            print(q,"st",st,"g",g,"nobj",len(objs)," ".join(hits))
