import yaml, ast
base='/Users/sher/cvp_live_campaign_copy/runs/live_campaign/e5_00853_s42_placebo_15m_'
def pred(q, st, g):
    d = yaml.safe_load(open(f'{base}{q}/stages/{st}/habitat_scene_graph_new_graph_{g}.yaml'))
    o = yaml.safe_load(open(f'{base}{q}/stages/{st}/habitat_scene_graph_original_graph{g//4}.yaml'))
    oid = {n['id'] for n in o['nodes']}
    out=[]
    for n in d['nodes']:
        if n['id'] in oid: continue
        p=ast.literal_eval(n['position']) if isinstance(n['position'],str) else n['position']
        out.append((n.get('name'), n.get('node_type'), round(p[0],2), round(p[1],2), n.get('is_predicted')))
    return out
for g in range(8):
    p = {q: pred(q, '0', g) for q in ['q1','q2','q3']}
    lab={q:[x[:2] for x in v] for q,v in p.items()}
    print('graph', g, {q: len(v) for q,v in p.items()}, 'labels eq q1q2', lab['q1']==lab['q2'], 'q1q3', lab['q1']==lab['q3'], 'q2q3', lab['q2']==lab['q3'], '| full eq', p['q1']==p['q2'], p['q1']==p['q3'], p['q2']==p['q3'])
    if g in (0,4):
        for q in p: print('   ',q, p[q][:3])
