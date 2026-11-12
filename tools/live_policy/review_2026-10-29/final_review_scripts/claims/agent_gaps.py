import json, sys, numpy as np
scan = {'q1': (1793303325.28, 1793303349.28), 'q2': (1793310724.46, 1793310748.46), 'q3': (1793314083.38, 1793314107.38)}
for f in sys.argv[1:]:
    q = f.split('/')[-1][:2]
    d = json.load(open(f))
    ts = sorted(n['timestamp']/1e9 for n in d['nodes'] if n.get('attributes',{}).get('type')=='AgentNodeAttributes')
    ts = np.array(ts); s0, s1 = scan[q]
    gaps = np.diff(ts)
    print(f.split('/')[-1], 'n', len(ts), 'first-scanstart %.2f' % (ts[0]-s0), 'scanend-last %.2f' % (s1-ts[-1]), 'median gap %.3f' % np.median(gaps), 'max gap %.2f at +%.1f s' % (gaps.max(), ts[gaps.argmax()]-s0))
    # coverage by 4 s bins
    bins = np.arange(0, 25, 4)
    h,_ = np.histogram(ts - s0, bins=bins)
    print('   per 4 s bin:', h.tolist())
