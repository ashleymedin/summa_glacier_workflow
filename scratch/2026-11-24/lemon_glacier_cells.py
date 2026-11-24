#!/usr/bin/env python3
"""Per RGI glacier of each Lemon Creek domain: start cells, cells with room to advance, and the area in each (on the domain's glacier raster)."""
import os, numpy as np, rasterio
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for d in ("LemonCreek_general", "LemonCreek", "LemonCreek_grus"):
    b = f"data/domain_{d}/attributes/glaciers/domain_LemonCreek_rgi_id"
    with rasterio.open(b + ".tif") as r, rasterio.open(b + "_extend.tif") as e: g, x, res = r.read(1), e.read(1), (r.res, r.crs, r.shape, e.shape)
    print(d, res)
    for i in np.union1d(np.unique(g), np.unique(x)):
        if i > 0: print("  ", int(i), "start", (g == i).sum(), "extend", (x == i).sum(), "room", ((x == i) & (g <= 0)).sum(), "of its start in extend of others", ((g == i) & (x != i) & (x > 0)).sum())
