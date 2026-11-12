import itertools, numpy as np
F={'00853':[0.1785,0.2156,0.2028],'00871':[0.0925,0.0957,0.1027]}
A={'official':{'00853':[0.1412,0.1531],'00871':[0.1314,0.1267,0.1165]},
   'placebo':{'00853':[0.1464,0.1722,0.1368],'00871':[0.1141,0.0826,0.0860]}}
F50={'00853':[0.1606,0.197,0.182],'00871':[0.0874,0.0908,0.0921]}
A50={'official':{'00853':[0.1169,0.1304],'00871':[0.1218,0.1124,0.1051]},
   'placebo':{'00853':[0.1333,0.1549,0.1188],'00871':[0.1035,0.0753,0.0822]}}
def test(a,f):
    scen=list(f)
    obs=np.mean([np.mean(a[s])-np.mean(f[s]) for s in scen])
    opts=[]
    for s in scen:
        pool=a[s]+f[s]; na=len(a[s]); L=[]
        for idx in itertools.combinations(range(len(pool)),na):
            aa=[pool[i] for i in idx]; ff=[pool[i] for i in range(len(pool)) if i not in idx]
            L.append(np.mean(aa)-np.mean(ff))
        opts.append(L)
    stats=[np.mean(c) for c in itertools.product(*opts)]
    stats=np.array(stats)
    p=np.mean(np.abs(stats)>=abs(obs)-1e-12)
    return obs,p,len(stats)
for arm in A:
    print(arm, test(A[arm],F), test(A50[arm],F50))
