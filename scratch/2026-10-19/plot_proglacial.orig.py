"""Satellite images of each glacier's terminus and gauge: plot_proglacial.py <out.pdf>

Esri World Imagery (WorldView-2: Wolverine 29 Sep 2025, Gulkana 22 Jul 2024), fetched in Alaska Albers (EPSG:3338)
so the axes are in metres. Gauges from the USGS monitoring-location service.
"""
import io, sys, urllib.request
import numpy as np
from PIL import Image
from pyproj import Transformer
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

out = sys.argv[1]
T = Transformer.from_crs(4326, 3338, always_xy=True)
URL = ('https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?'
       'bbox={},{},{},{}&bboxSR=3338&imageSR=3338&size={},{}&format=png&f=image')
# name, gauge (lon, lat), terminus (lon, lat), panel centre (lon, lat), half width (m), features (label, lon, lat)
SITES = [('Wolverine Glacier and USGS 15236900', (-148.896667, 60.370556), (-148.9170, 60.3805), (-148.9065, 60.3755), 1100,
          [('proglacial lake\n0.021 km$^2$', -148.9113, 60.3745), ('delta', -148.9160, 60.3772), ('bedrock gorge', -148.9200, 60.3792)]),
         ('Gulkana Glacier and USGS 15478040', (-145.468056, 63.240278), (-145.4260, 63.2586), (-145.4470, 63.2500), 2100,
          [('moraine and\nbraided outwash', -145.4420, 63.2470), ('Phelan Creek', -145.4640, 63.2440)])]

fig, axes = plt.subplots(1, 2, figsize=(12, 6.2))
for ax, (title, gauge, term, centre, half, feats) in zip(axes, SITES):
    cx, cy = T.transform(*centre)
    n = 1400
    img = Image.open(io.BytesIO(urllib.request.urlopen(URL.format(cx - half, cy - half, cx + half, cy + half, n, n), timeout=120).read()))
    ext = [-half / 1000, half / 1000, -half / 1000, half / 1000]
    ax.imshow(np.asarray(img.convert('RGB')), extent=ext)
    km = lambda lon, lat: ((T.transform(lon, lat)[0] - cx) / 1000, (T.transform(lon, lat)[1] - cy) / 1000)
    gx, gy = km(*gauge); tx, ty = km(*term)
    ax.plot(gx, gy, marker='^', ms=12, mfc='red', mec='white', mew=1.5, ls='none')
    ax.annotate('gauge', (gx, gy), xytext=(8, -14), textcoords='offset points', color='white', fontsize=10, weight='bold')
    ax.plot(tx, ty, marker='o', ms=9, mfc='none', mec='yellow', mew=2, ls='none')
    ax.annotate('terminus', (tx, ty), xytext=(8, 6), textcoords='offset points', color='yellow', fontsize=10, weight='bold')
    for lab, lon, lat in feats:
        fx, fy = km(lon, lat)
        ax.annotate(lab, (fx, fy), color='white', fontsize=9, ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.2', fc='black', alpha=0.35, lw=0))
    # 500 m scale bar
    x0, y0 = ext[0] + 0.1 * (ext[1] - ext[0]), ext[2] + 0.06 * (ext[3] - ext[2])
    ax.plot([x0, x0 + 0.5], [y0, y0], color='white', lw=3)
    ax.text(x0 + 0.25, y0 + 0.03 * (ext[3] - ext[2]), '500 m', color='white', ha='center', fontsize=9)
    ax.set_title(title, fontsize=10); ax.set_xticks([]); ax.set_yticks([])
fig.tight_layout(); fig.savefig(out, dpi=200); print('wrote', out)
