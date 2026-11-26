from pathlib import Path
import csv,numpy as np
p=Path(__file__).resolve().parent
rows=[]
for path in sorted(p.glob('6*.npy')):
    a=np.load(path);o,c,g=a[:,-3:].T
    if not g.any():continue
    for w in [5,11,31]:
        d=np.diff(o,prepend=o[0])*2
        for method in ['box','triangle']:
            kernel=np.ones(w) if method=='box' else np.r_[np.arange(1,w//2+2),np.arange(w//2,0,-1)]
            def changes(x):
                v=np.convolve(np.pad(x,(w-1,0),mode='edge'),kernel/kernel.sum(),'valid')
                return v-np.roll(v,10)
            x=changes(d);i=np.arange(80+w+10,len(o)-80)
            for target,y in [('CO',g),('CO2',c)]:
                z=changes(y);ks=np.arange(-80,81);rs=np.array([np.corrcoef(x[i],z[i+k])[0,1] for k in ks])
                k=np.nanargmax(abs(rs))
                rows.append(dict(heat=path.stem,method=method,window=w*.5,target=target,lag=ks[k]*.5,r=rs[k]))
with (p/'signed_lags.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
