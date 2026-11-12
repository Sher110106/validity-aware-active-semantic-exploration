import json, sys, collections
for f in sys.argv[1:]:
    d = json.load(open(f))
    keys = list(d.keys())
    nodes = d.get('nodes', [])
    layers = collections.Counter()
    tmax = []; tmin=[]
    names = collections.Counter()
    for n in nodes:
        layers[(n.get('layer'), n.get('partition'))] += 1
        a = n.get('attributes', {})
        for k in ('last_update_time_ns','first_observed_ns','last_observed_ns'):
            pass
        if 'timestamp' in n: tmax.append(n['timestamp'])
        if a.get('type') in ('KhronosObjectAttributes','ObjectNodeAttributes','SemanticNodeAttributes') or 'name' in a:
            if n.get('layer') in (2, 'OBJECTS') or str(n.get('id'))[:3]=='799':
                names[a.get('name')] += 1
    mesh = d.get('mesh', None)
    print(f, 'keys', keys)
    print('  layers', dict(layers))
    if tmax: print('  ts min/max', min(tmax), max(tmax))
    print('  objects', dict(names))
    if isinstance(mesh, dict): print('  mesh keys', list(mesh.keys())[:10], {k: (len(v) if hasattr(v,'__len__') else v) for k,v in mesh.items()})
