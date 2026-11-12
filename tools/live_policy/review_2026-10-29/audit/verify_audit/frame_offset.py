import json, yaml, ast, glob, numpy as np
REF=json.load(open('/tmp/cvp_review/refs/oracle_sets.json'))['scenes']
L=lambda n:str(n).lower().replace('_',' ').strip()
V=lambda x:np.array(ast.literal_eval(x) if isinstance(x,str) else x,float)
out={}
for run in ['e1_00853_s42_official_60m','e1_00853_s43_placebo_60m','e1_00871_s42_placebo_60m','e1_00871_s44_official_60m','e3_00871_s42_oracle_visible_60m']:
    sc=str(int(run.split('_')[1])); refs=REF[sc]['objects']
    rxy=np.array([o['position'][:2] for o in refs]); rl=np.array([L(o['name']) for o in refs]); rz=np.array([o['position'][2] for o in refs])
    ks=sorted(int(p.split('/')[-1]) for p in glob.glob(f'/tmp/cvp_review/runs/{run}/stages/*'))
    k=ks[-2]
    g=yaml.safe_load(open(f'/tmp/cvp_review/runs/{run}/stages/{k}/habitat_scene_graph_original_graph0.yaml'))
    off=[];d=[]
    for n in g['nodes']:
        if n.get('node_type')!='object' or L(n['name']) not in set(rl): continue
        p=V(n['position']); m=rl==L(n['name'])
        dd=np.hypot(*(rxy[m]-p[:2]).T); j=np.argmin(dd); d.append(dd[j])
        if dd[j]<1.5: off.append(np.r_[p[:2]-rxy[m][j], p[2]-rz[m][j]])
    off=np.array(off); d=np.array(d)
    out[run]={'stage':k,'n':len(d),'share_le_0.5':float(np.mean(d<=0.5)),'share_le_1.0':float(np.mean(d<=1.0)),'mean_offset_xyz_of_pairs_lt1.5m':off.mean(0).round(3).tolist(),'median_abs':np.median(np.abs(off),0).round(3).tolist()}
    print(run,out[run])
json.dump(out,open('/tmp/cvp_review/audit/verify_audit/frame_offset.json','w'),indent=1)
