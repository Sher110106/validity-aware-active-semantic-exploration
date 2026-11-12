import yaml, ast
base='/Users/sher/cvp_live_campaign_copy/runs/live_campaign/e5_00853_s42_placebo_15m_'
def pred(q, st, g):
    d = yaml.safe_load(open(f'{base}{q}/stages/{st}/habitat_scene_graph_new_graph_{g}.yaml'))
    o = yaml.safe_load(open(f'{base}{q}/stages/{st}/habitat_scene_graph_original_graph{g//4}.yaml'))
    oid = {n['id'] for n in o['nodes']}
    return sorted((n.get('name'), n.get('node_type'), tuple(round(x,2) for x in ast.literal_eval(n['position'])[:2])) for n in d['nodes'] if n['id'] not in oid)
for g in [0, 4]:
    p = {q: pred(q, '0', g) for q in ['q1','q2','q3']}
    print('graph', g, {q: len(v) for q,v in p.items()})
    print('  q1==q2', p['q1']==p['q2'], ' q1==q3', p['q1']==p['q3'], ' labels q1==q2', [x[:2] for x in p['q1']]==[x[:2] for x in p['q2']])
    print('  q1 sample', p['q1'][:4]); print('  q2 sample', p['q2'][:4]); print('  q3 sample', p['q3'][:4])
