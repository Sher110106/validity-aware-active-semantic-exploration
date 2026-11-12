import csv, json, sys, os
base='/Users/sher/project/cvp/project/tools/live_policy/results_2026-10-31'
rows=list(csv.reader(open(base+'/numbers.csv')))
cache={}
def load(p):
    if p not in cache: cache[p]=json.load(open(os.path.join(base,p)))
    return cache[p]
for i,r in enumerate(rows[1:],start=2):
    if i<960: continue
    k,v,src=r
    if '.json:' not in src: print(i,k,v,'| NONJSON', src); continue
    f,path=src.split('.json:',1); f+='.json'
    try:
        o=load(f)
        path=path.strip()
        cnt=False
        if path.endswith(' (count)'): path=path[:-8]; cnt=True
        if path.startswith('1 - min'):
            print(i,k,v,'| special',path); continue
        for part in path.split('/'):
            if isinstance(o,list): o=o[int(part)]
            else: o=o[part]
        if cnt: o=len(o)
        print(i,k,v,'|',o)
    except Exception as e:
        print(i,k,v,'| ERR',e, src)
