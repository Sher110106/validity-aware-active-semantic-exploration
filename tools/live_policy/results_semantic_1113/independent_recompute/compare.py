"""Compare /tmp/recompute/out_<model>.json with the scorer's results and records."""
import json, sys
import numpy as np
model = sys.argv[1] if len(sys.argv) > 1 else 'deepseek'
EXP = '/Users/sher/project/cvp/project/tools/live_policy/results_semantic_1113/' + ('exploratory' if model in ('deepseek','gemini','placebo') else 'claude')
mine = json.load(open(sys.argv[2] if len(sys.argv) > 2 else f'/tmp/recompute/out_{model}.json'))
theirs = json.load(open(f'{EXP}/results.json'))['models'][model]['analysis']['levels']
recs = {r['row_id']: r for r in json.load(open(f'{EXP}/records_{model}.json'))['records']}
A = mine['analysis']
print('== headline')
for L in ('L1', 'L2', 'L3'):
    ts = theirs[L]['model_cluster_scores']
    ms = A[L]['model_cluster_scores']
    print(L, 'mine mean %.4f theirs mean %.4f' % (A[L]['mean'], np.mean(list(ts.values()))),
          'impossible', A[L]['n_rows_impossible'], theirs[L]['n_rows_impossible'],
          'max|cluster diff| %.2e' % max(abs(ms[c] - ts[c]) for c in ts))
    for comp in (('B3', 'B1') if L != 'L3' else ('D', 'B5', 'B3L')):
        a, b = A[L][comp], theirs[L]['comparators'][comp]
        mx = max(abs(a['clusters'][c] - b['clusters'][c]) for c in b['clusters'])
        print('  %s mine diff %.4f p %.6f ci %s n_rows %d | theirs diff %.4f p %.6f ci %s n_rows %d | max cluster gap %.4f' % (
            comp, a['mean_diff'], a['p'], [round(x, 4) for x in a['ci']], a['n_rows'],
            b['mean_diff'], b['p'], [round(x, 4) for x in b['ci']], b['n_rows'], mx))
print('== per row/member')
nbad = 0
for r in mine['rows']:
    t = recs[r['row_id']]
    if t['n_unobserved'] != len(r['unobs']):
        print('n_unobs', r['row_id'], len(r['unobs']), t['n_unobserved']); nbad += 1
    for L in ('L1', 'L2', 'L3'):
        if t['possible'][L] != r['possible'][L]:
            print('possible', r['row_id'], L, r['possible'][L], t['possible'][L]); nbad += 1
    if sorted(t['model'].keys()) != sorted(str(m) for m in r['members']):
        print('members', r['row_id']); nbad += 1
    for m, mm in r['members'].items():
        tm = t['model'][str(m)]
        c = tm['counts']
        mine_c = dict(l1_hits=mm['l1_hits'], l1_n=len(mm['l1']), l2_hits=mm['l2_hits'], l2_n=len(mm['l2']),
                      l3_hits=mm['l3_hits'], l3_n=mm['n_items'])
        for k, v in mine_c.items():
            if float(c[k]) != float(v):
                print('count', r['row_id'], m, k, 'mine', v, 'theirs', c[k]); nbad += 1
        tb3 = t['comparators']['B3'][str(m)]
        for L in ('L1', 'L2'):
            a, b = mm[f'B3_{L}'], tb3[L]
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9):
                print('B3', r['row_id'], m, L, 'mine', a, 'theirs', b); nbad += 1
print('mismatches:', nbad)
# D / B5 per-member noise
for comp in ('D', 'B5'):
    gaps = []
    for r in mine['rows']:
        t = recs[r['row_id']]
        for m, mm in r['members'].items():
            a = mm[comp]
            b = t['comparators'][comp].get(str(m), {}).get('L3')
            if (a is None) != (b is None):
                print(comp, 'presence', r['row_id'], m, a, b)
            elif a is not None:
                gaps.append(a - b)
    g = np.array(gaps)
    print(comp, 'member gaps n=%d mean %.5f sd %.5f max|.| %.4f' % (len(g), g.mean(), g.std(), np.abs(g).max()))
