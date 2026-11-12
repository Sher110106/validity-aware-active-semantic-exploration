import os, json, yaml, ast, math, itertools, re, glob
B='/Users/sher/cvp_live_campaign_copy/runs/live_campaign/'
reps=['e5_00853_s42_placebo_15m_q%d'%i for i in (1,2,3)]
base=['e1_00853_s42_placebo_60m','e1_00853_s42_placebo_60m_FAILED_ATTEMPT1_retry_loop','e1_00853_s42_placebo_60m_FAILED_ATTEMPT2_false_exit']
def objs(r,k,g):
    p=f'{B}{r}/stages/{k}/habitat_scene_graph_original_graph{g}.yaml'
    if not os.path.exists(p): return None
    y=yaml.safe_load(open(p))
    out=[]
    for n in y['nodes']:
        if n.get('node_type')=='object':
            pos=n['position']; pos=ast.literal_eval(pos) if isinstance(pos,str) else pos
            out.append((n['name'],tuple(pos[:2])))
    return out
def stopxy(r,k):
    p=f'{B}{r}/stages/{k+1}/executed_path.json'
    if not os.path.exists(p): return None
    j=json.load(open(p)); w=j['world_frame_path']
    return w[-1][:2] if w else None
for grp in (reps,base):
    for r in grp:
        sizes=[os.path.getsize(f'{B}{r}/stages/0/habitat_scene_graph_original_graph{g}.yaml') for g in (0,1)]
        print(r, 'stage0 n_obj', [len(objs(r,0,g)) for g in (0,1)], 'sizes', sizes, 'labels', [sorted(n for n,_ in objs(r,0,g)) for g in (0,1)])
    for a,b in itertools.combinations(grp,2):
        ds=[]
        for k in (0,1,2):
            s1,s2=stopxy(a,k),stopxy(b,k)
            ds.append(None if s1 is None or s2 is None else round(math.dist(s1,s2),3))
        print(' ',a[-12:],b[-12:],'stops',ds)
print('--- track1 stage0 nearest')
for a,b in itertools.combinations(reps,2):
    A=objs(a,0,1); Bo=objs(b,0,1)
    d=[(n, round(min(math.dist(p,q) for m,q in Bo if m==n),3)) for n,p in A]
    print(a[-2:],b[-2:],d)
