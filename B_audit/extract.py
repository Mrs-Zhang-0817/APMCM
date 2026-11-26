from pathlib import Path
import sys,json
import numpy as np
from concurrent.futures import ProcessPoolExecutor
out=Path(__file__).resolve().parent
root=out.parent
sys.path.insert(0,str(root/'work_b/deps'))
from pyxlsb import open_workbook
def extract(p):
    with open_workbook(p) as w, w.get_sheet(1) as sheet:
        rows=sheet.rows()
        header=[c.v for c in next(rows)]
        heat=p.stem.split()[-1]
        a=np.array([[c.v for c in row] for row in rows],dtype=float)
        np.save(out/(heat+'.npy'),a)
        (out/(heat+'.json')).write_text(json.dumps(dict(sheets=w.sheets,header=header,dimension=list(sheet.dimension))),encoding='utf8')
        return heat,a.shape
if __name__=='__main__':
    with ProcessPoolExecutor(4) as pool:
        for result in pool.map(extract,sorted((root/'work_b/Data').glob('*.xlsb'))): print(result,flush=True)
