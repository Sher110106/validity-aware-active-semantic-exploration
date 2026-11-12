import json, numpy as np
from collections import defaultdict
R=[json.loads(l) for l in open('/tmp/cvp_review/audit/verify_audit/sens_stages.jsonl')]
print('errors',sum('error' in r for r in R), len(R))
A={(r['run'],r['stage']):r for r in map(json.loads,open('/tmp/cvp_review/audit/audit/stages.jsonl'))}
# consistency of r0.5 with audit
bad=[(r['run'],r['stage']) for r in R if abs(r['r0.5']['rho']-A[(r['run'],r['stage'])]['rho_total_U360'])>1e-9 or abs(r['r0.5']['pct_stop']-A[(r['run'],r['stage'])]['pct_stop'])>1e-9]
print('r0.5 mismatches vs audit',len(bad))
def boot(rows,key,seed=0):
    by=defaultdict(list)
    for r in rows:
        if r[key] is not None: by[r['run']].append(r[key])
    rng=np.random.default_rng(seed); m=[]
    for _ in range(2000): m.append(np.concatenate([np.array(v)[rng.integers(0,len(v),len(v))] for v in by.values()]).mean())
    allv=[x for v in by.values() for x in v]
    return round(float(np.mean(allv)),3),[round(float(x),3) for x in np.percentile(m,[2.5,97.5])],len(allv)
out={}
for a in ['official','placebo','filter_only','oracle_visible']:
    rows=[r for r in R if r['arm']==a]
    o={'rho_r1.0_median':round(float(np.median([r['r1.0']['rho'] for r in rows if r['r1.0']['rho'] is not None])),3),
       'pct_stop_r1.0':boot([dict(run=r['run'],v=r['r1.0']['pct_stop']) for r in rows],'v'),
       'n_unmapped_r0.5_mean':round(float(np.mean([r['r0.5']['n_unmapped'] for r in rows])),1),
       'n_unmapped_r1.0_mean':round(float(np.mean([r['r1.0']['n_unmapped'] for r in rows])),1),
       'nav_frac_mean':round(float(np.mean([r['nav_frac'] for r in rows])),3),
       'U360_nav_mean':round(float(np.nanmean([r['U360_nav_mean'] if r['U360_nav_mean'] is not None else np.nan for r in rows])),2),
       'U360_offnav_mean':round(float(np.nanmean([r['U360_offnav_mean'] if r['U360_offnav_mean'] is not None else np.nan for r in rows])),2),
       'pct_stop_nav':boot(rows,'pct_stop_nav'),
       'rho_nav_median':round(float(np.median([r['rho_nav'] for r in rows if r['rho_nav'] is not None])),3),
       'pct_stop_band':boot(rows,'pct_stop_band')}
    out[a]=o; print(a,json.dumps(o))
json.dump(out,open('/tmp/cvp_review/audit/verify_audit/sens_summary.json','w'),indent=1)
