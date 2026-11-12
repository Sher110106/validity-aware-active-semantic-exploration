"""Independent recomputation of summary numbers from audit/stages.jsonl and cf_stages.jsonl."""
import json, itertools
import numpy as np
from collections import defaultdict
from scipy.stats import binomtest
S=[json.loads(l) for l in open('/tmp/cvp_review/audit/audit/stages.jsonl')]
U=[r for r in S if r.get('top10_match') and 'rho_total_U360' in r]
ARMS=['official','placebo','filter_only','oracle_visible']
out={}
def boot(rows,key,B=2000,seed=123):
    by=defaultdict(list)
    for r in rows: by[r['run']].append(r[key])
    rng=np.random.default_rng(seed); m=[]
    for _ in range(B):
        m.append(np.mean(np.concatenate([np.random.default_rng(rng.integers(1<<31)).choice(v,len(v)) for v in by.values()])))
    return float(np.mean([x for v in by.values() for x in v])), [float(x) for x in np.percentile(m,[2.5,97.5])]
def runtest(rows,key):
    by=defaultdict(list)
    for r in rows: by[r['run']].append(r[key])
    d=np.array([np.mean(v)-.5 for v in by.values()])
    cnt=sum(1 for s in itertools.product([-1,1],repeat=len(d)) if np.dot(s,abs(d))>=d.sum()-1e-12)
    return int((d>0).sum()), len(d), cnt/2**len(d)
def sign(rows,key):
    w=l=t=0
    for r in rows:
        U3=None
        u=r['U360_'+key]; med=r['U360_median']
        if u>med: w+=1
        elif u<med: l+=1
        else: t+=1
    return w,l,t,binomtest(w,w+l,.5,alternative='greater').pvalue
def yard(rows):
    ys=[r['yard'] for r in rows if r.get('yard')]
    a=sum(y['in_mapped_sl'] for y in ys)/sum(y['n_in'] for y in ys)
    b=sum(y['out_mapped_sl'] for y in ys)/sum(y['n_out'] for y in ys)
    c=sum(y['in_mapped_any'] for y in ys)/sum(y['n_in'] for y in ys)
    d=sum(y['out_mapped_any'] for y in ys)/sum(y['n_out'] for y in ys)
    return len(ys),round(a,4),round(b,4),round(c,4),round(d,4)
def med(rows,k):
    x=np.array([r[k] for r in rows if r.get(k) is not None]); return [round(float(np.median(x)),3),round(float(np.percentile(x,25)),3),round(float(np.percentile(x,75)),3),len(x)]
groups=[(a,None) for a in ARMS]+[(a,s) for a in ARMS for s in ('00853','00871')]+[('all',None)]
for a,s in groups:
    rows=[r for r in U if (a=='all' or r['arm']==a) and (s is None or r['scene']==s)]
    o={'n':len(rows),'runs':len({r['run'] for r in rows})}
    for k in ['rho_total_U360','rho_total_Ucone','rho_ig_U360','rho_negdist_U360','rho_total_U360_sl']:
        o[k]=med(rows,k)
    for k in ['stop','best','final']:
        rr=[r for r in rows if r.get('pct_'+k) is not None]
        mn,ci=boot(rr,'pct_'+k); o['pct_'+k]=[round(mn,3),[round(x,3) for x in ci],len(rr)]
    o['sign_stop']=sign(rows,'stop'); o['run_stop']=runtest(rows,'pct_stop')
    o['yard']=yard(rows)
    o['stop_to_final_med']=round(float(np.median([r['stop_to_final_m'] for r in rows if 'stop_to_final_m' in r])),3)
    o['stop_to_best_med']=round(float(np.median([r['stop_to_best_m'] for r in rows])),3)
    out[f'{a}/{s}' if s else a]=o
    print(f'{a}/{s}' if s else a, json.dumps(o))
# counterfactual
C=[json.loads(l) for l in open('/tmp/cvp_review/audit/audit/cf_stages.jsonl')]
print('cf n',len(C),sum('error' in r for r in C))
for a in ARMS+['ALL']:
    rows=[r for r in C if a=='ALL' or r['arm']==a]
    o={'n':len(rows)}
    for c in ('actual','obs','plc','orc'):
        o[c]=(round(float(np.median([r[c]['rho_total_U360'] for r in rows if r[c]['rho_total_U360'] is not None])),3),
              round(float(np.median([r[c]['rho_total_Ucone'] for r in rows if r[c]['rho_total_Ucone'] is not None])),3),
              round(float(np.mean([r[c]['ig_zero_frac'] for r in rows])),3))
    for m in ('rho_total_U360','rho_total_Ucone'):
        o['act-plc:'+m]=round(float(np.median([r['actual'][m]-r['plc'][m] for r in rows])),3)
        o['orc-plc:'+m]=round(float(np.median([r['orc'][m]-r['plc'][m] for r in rows])),3)
    fp=[r['frontier_proxy']['rho_dwalk_U360'] for r in rows if r.get('frontier_proxy') and r['frontier_proxy']['rho_dwalk_U360'] is not None]
    o['frontier']=(round(float(np.median(fp)),3),len(fp))
    if a=='official':
        w=sum(1 for r in rows if r['actual']['rho_total_U360']>r['plc']['rho_total_U360']); n=len(rows)
        o['act>plc']=(w,n,binomtest(w,n,.5,alternative='greater').pvalue)
        by=defaultdict(list)
        for r in rows: by[r['run']].append(r['actual']['rho_total_U360']-r['plc']['rho_total_U360'])
        o['runmed']={k:round(float(np.median(v)),3) for k,v in by.items()}
    print('CF',a,json.dumps(o))
json.dump(out,open('/tmp/cvp_review/audit/verify_audit/resummary.json','w'),indent=1)
