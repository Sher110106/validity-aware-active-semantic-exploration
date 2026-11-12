import json, numpy as np
rows=[json.loads(l) for l in open('/Users/sher/project/cvp/project/tools/live_policy/review_2026-10-29/bench/build/stages.jsonl')]
print(len(rows), len(set(r['run'] for r in rows)))
# recompute regrets from Uwall and picks
mis=0
for r in rows:
    U=np.array(r['Uwall']); mx=U.max()
    for g,pk in r['picks'].items():
        for rule,i in pk.items():
            if abs((mx-U[i]) - r['regret']['Uwall'][g][rule])>1e-9: mis+=1
print('regret mismatches', mis)
def mean(arm, g, rule):
    v=[r['regret']['Uwall'][g][rule] for r in rows if arm is None or r['arm']==arm]
    return np.mean(v), len(v)
for rule in ['R1','R2','R3','R4']:
    o,_=mean(None,'oracle',rule); a,_=mean(None,'placebo_A',rule)
    l,n=mean('official','actual',rule); la,_=mean('official','placebo_A',rule)
    print(rule, round(o,3), round(a,3), round(o/a,4), 'official', n, round(l-la,3))
print('maxmean', np.mean([max(r['Uwall']) for r in rows]))
picks=[]
for r in rows:
    U=np.array(r['Uwall']); mx=U.max()
    for g,pk in r['picks'].items():
        for rule,i in pk.items(): pass
# yardstick
s={'Uwall':[0,0,0,0],'U360':[0,0,0,0]}
n=0
for r in rows:
    if r.get('yard') is None: continue
    n+=1
    for k in s:
        y=r['yard'][k]; s[k][0]+=y['n_in']; s[k][1]+=y['in_mapped']; s[k][2]+=y['n_out']; s[k][3]+=y['out_mapped']
print('yard stages', n, s, {k:(v[1]/v[0], v[3]/v[2], v[1]+v[3]) for k,v in s.items()})
print('mean pick U by rule/set range:')
vals=[]
for g in ['actual','none','placebo_A','placebo_B','oracle']:
    for rule in ['R1','R2','R3','R4','R5','R6']:
        m,_=mean(None,g,rule); vals.append((12.658854-m, g, rule))
print(min(vals), max(vals))
