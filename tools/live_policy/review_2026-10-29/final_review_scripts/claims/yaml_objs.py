import yaml, sys, ast, os
base='/Users/sher/cvp_live_campaign_copy/runs/live_campaign/e5_00853_s42_placebo_15m_'
for q in ['q1','q2','q3']:
    for st in ['0','1']:
        for g in ['0','1']:
            f=f'{base}{q}/stages/{st}/habitat_scene_graph_original_graph{g}.yaml'
            d=yaml.safe_load(open(f))
            objs=[(n['name'], [round(x,2) for x in ast.literal_eval(n['position'])][:2]) for n in d['nodes'] if n.get('node_type')=='object']
            print(q, 'stage', st, 'track', g, len(objs), sorted(objs))
