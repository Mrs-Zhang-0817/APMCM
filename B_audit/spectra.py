"""Diagnostic surfaces; only display copies are filtered."""
from pathlib import Path
import numpy as np,json,csv
from PIL import Image,ImageDraw
p=Path(__file__).resolve().parent
canvas=Image.new('RGB',(1040,1140),'white');draw=ImageDraw.Draw(canvas)
records=[]
for idx,path in enumerate(sorted(p.glob('6*.npy'))):
    a=np.load(path);s=a[:,1:-3];h=path.stem
    wl=np.array(json.loads(path.with_suffix('.json').read_text())['header'][1:-3])
    # Only flag impulses isolated along both axes. Keep clipped values marked separately.
    core=s[1:-1,1:-1]
    nb=np.stack([s[2:,1:-1],s[:-2,1:-1],s[1:-1,2:],s[1:-1,:-2]])
    mid=np.median(nb,axis=0);scale=np.median(abs(nb-mid),axis=0)
    flag=(abs(core-mid)>np.maximum(1000,8*1.4826*scale))&((core>nb.max(0))|(core<nb.min(0)))&(core<65535)
    cleaned=s.copy();cleaned[1:-1,1:-1][flag]=mid[flag]
    # Block means for display. Coordinates are actual mean time and wavelength.
    ti=np.array_split(np.arange(len(s)),48);wi=np.array_split(np.arange(len(wl)),60)
    z=np.array([[row[j].mean() for j in wi] for row in [cleaned[i].mean(0) for i in ti]])
    left=idx%2*520+48;top=idx//2*218+30
    def point(i,j):
        u=(wl[wi[j]].mean()-339)/690;v=ti[i].mean()*.5/780
        return (left+345*u+85*v,top+95+70*v-100*z[i,j]/65535)
    for i in range(47):
        for j in range(59):
            f=min(1,z[i:i+2,j:j+2].mean()/50000)
            draw.polygon([point(i,j),point(i,j+1),point(i+1,j+1),point(i+1,j)],fill=(int(48+195*f),int(90+110*f),int(142-98*f)))
    draw.text((left,top-18),f'{h}   {len(s)} samples   {(len(s)-1)*.5:g} s',fill='black')
    draw.text((left,top+172),'wavelength ->     depth: time     height: intensity',fill='black')
    o,c,g=a[:,-3:].T
    records.append(dict(heat=h,flagged=int(flag.sum()),fraction=flag.mean(),clip=int((s==65535).sum()),gas2_zero=int((c==0).sum()),gas_zero=int((g==0).sum()),flow_mean=(o[-1]-o[0])/((len(o)-1)*.5),flow_max=2*np.diff(o).max(),gas2_unchanged=np.mean(np.diff(c)==0),gas_unchanged=np.mean(np.diff(g)==0)))
canvas.save(p/'spectra.png')
with (p/'diagnostics.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
