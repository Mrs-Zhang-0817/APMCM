"""Run after extract.py. Only numpy and the Python standard library required."""
from pathlib import Path
import numpy as np,json,csv
from collections import defaultdict
from lag_scan import corr, forward_lags, smooth
out=Path(__file__).resolve().parent
tables=defaultdict(list)
def save():
    for name,rows in tables.items():
        with (out/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
def desc(h,name,x):
    q=np.quantile(x,[0,.05,.5,.95,1])
    tables['distribution'].append(dict(heat=h,field=name,minimum=q[0],p05=q[1],median=q[2],p95=q[3],maximum=q[4],mean=x.mean(),sd=x.std(),first=x.flat[0],last=x.flat[-1],peak_index=x.argmax()+1))
def integrate(x):
    return np.r_[0,np.cumsum((x[1:]+x[:-1])*.25)]
sets={}; curves=[];ref=None
for file in sorted(out.glob('6*.npy')):
    a=np.load(file);h=file.stem
    meta=json.loads(file.with_suffix('.json').read_text()); head=meta['header']; wave=np.array(head[1:-3])
    if ref is None: ref=head
    seq=a[:,0];s=a[:,1:-3];o,c,g=a[:,-3:].T;n=len(o);t=(seq-1)*.5
    d=np.diff(o,prepend=o[0])*2;b=s.mean(1)
    q=smooth(d,11); edges=np.linspace(341,1023,17); features=np.column_stack([s[:,(wave>=lo)&(wave<hi)].mean(1) for lo,hi in zip(edges,edges[1:])])
    sets[h]=(features,np.c_[c,g],np.c_[t,o,q])
    dup=np.where((s[:,1:]==s[:,:-1]).all(0))[0]
    adj=np.abs(np.diff(s,axis=1));dt=np.abs(np.diff(s,axis=0))
    # Isolated impulse: deviation from both neighbours, same sign, threshold in instrument units
    l=s[:,1:-1]-s[:,:-2];r=s[:,1:-1]-s[:,2:]
    spikes=(l*r>0)&(np.minimum(abs(l),abs(r))>1000)
    row=dict(heat=h,sheet='|'.join(meta['sheets']),rows_with_header=n+1,n=n,columns=a.shape[1],seconds=t[-1]-t[0],sequence_errors=sum(np.diff(seq)!=1),seq_first=seq[0],seq_last=seq[-1],same_header=head==ref,wavelengths=len(wave),nm_first=wave[0],nm_last=wave[-1],step_min=np.diff(wave).min(),step_max=np.diff(wave).max(),missing=int((~np.isfinite(a)).sum()),spec_zero_rows=sum((s==0).all(1)),zero_bands=sum((s==0).all(0)),duplicate_spectra=n-len(np.unique(s,axis=0)),duplicate_adjacent_bands='|'.join(map(str,wave[dup])),oxygen_drops=sum(d<0),zero_increments=sum(d[1:]==0),max_count=int((s==s.max()).sum()),spec_max=s.max(),at_max_rows=sum((s==s.max()).any(1)),negative_spec=int((s<0).sum()),adj_diff_p95=np.quantile(adj,.95),time_diff_p95=np.quantile(dt,.95),isolated_1000=int(spikes.sum()),CO2_integral=integrate(c)[-1],CO_integral=integrate(g)[-1])
    tables['overview'].append(row)
    for k,x in [('O2cum',o),('flow_raw',d),('flow_5.5s',q),('CO2',c),('CO',g),('brightness',b),('spectral_cells',s)]:desc(h,k,x)
    for k,x in [('CO2',c),('CO',g),('CO2_integral',integrate(c)),('CO_integral',integrate(g)),('brightness',b)]:
        tables['association'].append(dict(heat=h,target=k,r_oxygen=corr(o,x),r_flow=corr(q,x),r_brightness=corr(b,x)))
    tables['lags'].extend(forward_lags(h,o,c,g,b))
    curves.append((h,t,[o,q,c,g,integrate(c),integrate(g),b]))
# PCA of 16 band means, descriptive pooled covariance
F=np.vstack([v[0] for v in sets.values()]); val,vec=np.linalg.eigh(np.cov(F.T)); frac=val[::-1]/val.sum()
for k,v in enumerate(frac):tables['pca'].append(dict(component=k+1,variance_fraction=v))
for h,(f,y,p) in sets.items():
    for horizon in [0,20]:
        def xy(v,mode):
            f,y,p=v
            X={'mean':np.ones((len(y),1)),'process':p,'spectrum':f,'fusion':np.c_[p,f]}[mode]
            return (X[:-horizon],y[horizon:]) if horizon else (X,y)
        for mode in ['mean','process','spectrum','fusion']:
            tr=[xy(v,mode) for name,v in sets.items() if name!=h and v[1].any()]
            x=np.vstack([v[0] for v in tr]);yt=np.vstack([v[1] for v in tr])
            xt,yy=xy(sets[h],mode);mu=x.mean(0);sd=x.std(0);sd[sd<1e-8]=1
            x=(x-mu)/sd;xt=(xt-mu)/sd; pred=yt.mean(0)+xt@np.linalg.solve(x.T@x+10*np.eye(x.shape[1]),x.T@(yt-yt.mean(0)))
            for j,k in enumerate(['CO2','CO']):
                err=pred[:,j]-yy[:,j]
                tables['validation'].append(dict(heat=h,horizon_s=horizon*.5,model=mode,target=k,n=len(err),MAE=np.mean(abs(err)),RMSE=np.sqrt(np.mean(err**2)),R2=(1-np.mean(err**2)/yy[:,j].var() if yy[:,j].var()>0 else None)))
# small multiples; independently scaled per column, shared across heats
labels=['O2 cumulative','Flow (5.5 s)','CO2','CO','CO2 integral','CO integral','Mean light']
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="820" style="background:white;font:13px Arial">']
for j,label in enumerate(labels):
    left=100+164*j
    svg.append(f'<text x="{left}" y="22">{label}</text>')
    lo=min(v[j].min() for _,_,v in curves);hi=max(v[j].max() for _,_,v in curves)
    for i,(h,t,v) in enumerate(curves):
        top=35+77*i
        if j==0:svg.append(f'<text x="7" y="{top+32}">{h}</text>')
        ids=np.unique(np.r_[np.arange(0,len(t),4),len(t)-1])
        pts=' '.join(f'{left+150*t[k]/max(a[1][-1] for a in curves):.1f},{top+56-52*(v[j][k]-lo)/(hi-lo):.1f}' for k in ids)
        svg.append(f'<path d="M{left} {top}v56h150" fill="none" stroke="#cccccc"/><polyline points="{pts}" fill="none" stroke="#176579" stroke-width="1"/>')
    svg.append(f'<text x="{left}" y="814">{lo:.1f} to {hi:.1f}</text>')
(out/'process.svg').write_text(''.join(svg)+'</svg>')
save()

