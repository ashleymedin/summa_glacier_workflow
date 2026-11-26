import json, rasterio, numpy as np, sys
from rasterio.warp import transform_bounds
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S=json.load(open('stac.json')); want=["20180916","20190830","20200913","20210831","20220824","20230821","20240818","20250904","20260904"]
boxes={'lakes':(-134.395,58.395,-134.355,58.420),'head':(-134.385,58.350,-134.320,58.378),'ptarm':(-134.395,58.370,-134.36,58.40)}
for n,b in boxes.items():
    fig,ax=plt.subplots(3,3,figsize=(15,15))
    for a,w in zip(ax.flat,want):
        c=[s for s in S if w in s[3]]
        for s in c:
            try:
                with rasterio.open(s[2]) as r:
                    q=transform_bounds('EPSG:4326',r.crs,*b); im=r.read([1,2,3],window=r.window(*q),boundless=True,fill_value=0).astype(float).transpose(1,2,0)
                if im.max()==0 or (im.sum(2)==0).mean()>.3: continue
                a.imshow(np.clip(im/min(255,np.percentile(im,98)*1.05),0,1)**.8); a.set_title(s[3][:22]+f' {s[1]}%',fontsize=8); break
            except Exception as e: a.set_title(str(e)[:40])
        a.axis('off')
    plt.tight_layout(); plt.savefig(f'chip_{n}.png',dpi=75); print(n)
