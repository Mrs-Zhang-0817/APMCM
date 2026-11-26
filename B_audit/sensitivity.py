from pathlib import Path
import csv,numpy as np
from lag_scan import signed_lags
p=Path(__file__).resolve().parent
rows=[]
for path in sorted(p.glob('6*.npy')):
    a=np.load(path);o,c,g=a[:,-3:].T
    rows.extend(signed_lags(path.stem,o,c,g))
with (p/'signed_lags.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
