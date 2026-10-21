import io, sys, urllib.request
import numpy as np
from PIL import Image
from pyproj import Transformer
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
T = Transformer.from_crs(4326, 3338, always_xy=True)
Ti = Transformer.from_crs(3338, 4326, always_xy=True)
URL = ('https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?'
       'bbox={},{},{},{}&bboxSR=3338&imageSR=3338&size={},{}&format=png&f=image')
name, lon, lat, half = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
cx, cy = T.transform(lon, lat); n = int(sys.argv[0] and 1000)
img = Image.open(io.BytesIO(urllib.request.urlopen(URL.format(cx-half, cy-half, cx+half, cy+half, n, n), timeout=120).read()))
fig, ax = plt.subplots(figsize=(11, 11))
ax.imshow(np.asarray(img.convert('RGB')), extent=[-half, half, -half, half])
step = half/5
for v in np.arange(-half, half+1, step):
    ax.axvline(v, color='cyan', lw=0.5); ax.axhline(v, color='cyan', lw=0.5)
ax.set_xticks(np.arange(-half, half+1, step)); ax.set_yticks(np.arange(-half, half+1, step))
for gx in np.arange(-half, half+1, step):
    for gy in np.arange(-half, half+1, step):
        lo, la = Ti.transform(cx+gx, cy+gy)
        ax.text(gx+5, gy+5, f'{lo:.4f}\n{la:.4f}', color='yellow', fontsize=6)
for (lo, la, c) in [(float(a.split(',')[0]), float(a.split(',')[1]), 'red') for a in sys.argv[5:]]:
    x, y = T.transform(lo, la); ax.plot(x-cx, y-cy, 'o', mfc='none', mec=c, ms=12, mew=2)
fig.tight_layout(); fig.savefig(name, dpi=110)
