import json, numpy as np
from collections import defaultdict
S=[json.loads(l) for l in open('/tmp/cvp_review/audit/audit/stages.jsonl')]
U=[r for r in S if r.get('top10_match') and 'rho_total_U360' in r]
def within(rows,seed):
    by=defaultdict(list)
    for r in rows: by[r['run']].append(r['pct_stop'])
    rng=np.random.default_rng(seed); m=[]
    for _ in range(2000):
        m.append(np.concatenate([np.array(v)[rng.integers(0,len(v),len(v))] for v in by.values()]).mean())
    return np.percentile(m,[2.5,97.5])
def cluster(rows,seed=0):
    by=defaultdict(list)
    for r in rows: by[r['run']].append(r['pct_stop'])
    runs=list(by.values()); rng=np.random.default_rng(seed); m=[]
    for _ in range(2000):
        pick=[runs[i] for i in rng.integers(0,len(runs),len(runs))]
        m.append(np.concatenate([np.array(v)[rng.integers(0,len(v),len(v))] for v in pick]).mean())
    return np.percentile(m,[2.5,97.5])
out={}
for key in ['official','placebo','filter_only','oracle_visible','official/00853','placebo/00871','filter_only/00871']:
    a,_,s=key.partition('/')
    rows=[r for r in U if r['arm']==a and (not s or r['scene']==s)]
    lows=[within(rows,sd)[0] for sd in range(20)]
    cl=cluster(rows)
    out[key]={'within_lo_over_20_seeds':[round(min(lows),3),round(max(lows),3)],'frac_seeds_lo_gt_0.5':float(np.mean(np.array(lows)>0.5)),'cluster_ci':[round(x,3) for x in cl]}
    print(key,out[key])
json.dump(out,open('/tmp/cvp_review/audit/verify_audit/boot_sens.json','w'),indent=1)
