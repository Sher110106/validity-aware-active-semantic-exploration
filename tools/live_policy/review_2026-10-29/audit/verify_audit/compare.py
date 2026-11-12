import json
A={(r['run'],r['stage']):r for r in map(json.loads,open('/tmp/cvp_review/audit/audit/stages.jsonl'))}
out=[]
for v in map(json.loads,open('/tmp/cvp_review/audit/verify_audit/verify_stages.jsonl')):
    a=A[(v['run'],v['stage'])]
    if 'error' in v: print('ERR',v); continue
    c={'run':v['run'],'stage':v['stage'],'match_me':v['top10_match'],'match_audit':a['top10_match']}
    for k in ['n_unmapped','n_unmapped_sl','rho_total_U360','rho_total_Ucone','rho_total_U360_sl','U360_mean','U360_stop','pct_stop','U360_best','pct_best']:
        if k in a: c[k]=(round(v[k],4) if isinstance(v[k],float) else v[k], round(a[k],4) if isinstance(a[k],float) else a[k])
    if a.get('yard') and v.get('yard'):
        c['yard']=(v['yard'],{k:a['yard'][k] for k in ['n_in','in_mapped_sl','n_out','out_mapped_sl']})
    c['path_start_gap']=v['path_start_to_cur_m']
    c['all_equal']=all((x[0]==x[1]) if not isinstance(x[0],float) else abs(x[0]-x[1])<1e-3 for kk,x in c.items() if isinstance(x,tuple))
    out.append(c); print(json.dumps(c))
json.dump(out,open('/tmp/cvp_review/audit/verify_audit/compare.json','w'),indent=1)
print('all equal:',all(c['all_equal'] for c in out), len(out))
