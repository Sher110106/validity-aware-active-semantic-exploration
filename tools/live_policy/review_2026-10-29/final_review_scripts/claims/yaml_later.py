import yaml, ast, os
base='/Users/sher/cvp_live_campaign_copy/runs/live_campaign/e5_00853_s42_placebo_15m_q3/stages/'
for st in sorted(os.listdir(base), key=int):
    f=f'{base}{st}/habitat_scene_graph_original_graph0.yaml'
    if not os.path.exists(f): continue
    d=yaml.safe_load(open(f))
    objs=[(n['name'], [round(x,2) for x in ast.literal_eval(n['position'])][:2]) for n in d['nodes'] if n.get('node_type')=='object']
    near=[o for o in objs if o[0] in ('duvet','nightstand','cabinet') or (o[0]=='lamp' and o[1][1]<-5.5)]
    print('stage', st, 'n', len(objs), 'start-room objects:', near)
