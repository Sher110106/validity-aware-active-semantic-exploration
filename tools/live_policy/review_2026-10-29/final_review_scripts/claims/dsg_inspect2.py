import json, sys, collections
for f in sys.argv[1:]:
    d = json.load(open(f))
    c = collections.Counter(); ts_by_layer = collections.defaultdict(list); sizes=collections.Counter()
    for n in d['nodes']:
        a = n.get('attributes', {})
        key=(n.get('layer'), a.get('type'))
        c[key]+=1
        sizes[key]+=len(json.dumps(n))
        if 'timestamp' in n: ts_by_layer[key].append(n['timestamp'])
    print(f.split('/')[-1])
    for k in sorted(c, key=str):
        ts = ts_by_layer[k]
        print('  ', k, c[k], 'bytes', sizes[k], 'ts', (min(ts)/1e9, max(ts)/1e9) if ts else None)
    print('   edges', len(d['edges']), 'edge bytes', len(json.dumps(d['edges'])), 'metadata bytes', len(json.dumps(d.get('metadata'))))
